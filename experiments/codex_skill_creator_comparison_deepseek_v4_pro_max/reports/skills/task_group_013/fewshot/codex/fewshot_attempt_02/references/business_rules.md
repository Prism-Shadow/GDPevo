# Cedar Ridge Intake Coordination Portal — Business Rules

## Access Verification

This workflow covers new-patient intake roster processing. Input: a roster ID, a set of target patient IDs, and an answer template specifying per-patient and cohort output shape.

### Data Sources

1. **Roster data:** Use `POST /query` with `SELECT * FROM intake_rosters WHERE roster_id = '<roster_id>'` to obtain `requested_service_date` and `service_line` for the batch.
2. **Patient profiles:** Use `GET /patients/<patient_id>` for each target patient. This returns their insurance coverage, PBM, pharmacy, lifestyle, clinical history, demographics, etc.

### Insurance Status Rules

Evaluate the first (or only) coverage record:

- **`valid`** — `coverage.status` is `"active"` AND `coverage.service_lines` (comma-split) contains the roster's `service_line`.
- **`invalid`** — `coverage` is present but either `status` is not `"active"` (e.g., `"expired"`, `"pending"`) OR the roster's `service_line` is not in the coverage `service_lines` list.
- **`missing`** — No coverage records exist (`coverage` array is empty).

### Prescription Status (PBM) Rules

Evaluate the first (or only) PBM record:

- **`valid`** — `pbm.active` is 1 AND `pbm.status` is `"approved"`.
- **`invalid`** — PBM exists but either `active` is 0 OR `status` is not `"approved"` (e.g., `"rejected"`, `"pending"`).
- **`missing`** — No PBM records exist.

### Pharmacy Status Rules

Evaluate the patient's pharmacy list (rank-ordered by `preference_rank`):

- **`in_network`** — At least one pharmacy has `network_status` == `"in_network"`.
- **`out_of_network`** — Pharmacies exist but all are `"out_of_network"`.
- **`unknown`** — No pharmacy records exist.

### Lifestyle Risk Rules

Determine from the `lifestyle` object:

- **`high`** — `smoking_status` is `"Current"` OR `alcohol_use` is `"Heavy"`.
- **`medium`** — `smoking_status` is `"Former"` OR `alcohol_use` is `"Moderate"` (and not already high).
- **`low`** — Neither high nor medium criteria apply (i.e., `smoking_status` is `"Never"` AND `alcohol_use` is `"None"` or `"Occasional"`).

Priority: high > medium > low. Evaluate high first, then medium, default to low.

### Overall Risk Rules

Aggregate all signals into an overall risk level:

- **`high`** — Lifestyle risk is `"high"` OR coverage `status` is `"expired"` or `"pending"` OR `existing_chart` is 0 OR `emergency_contact_present` is 0 OR `clinical_history.risk_flags` is non-empty.
- **`medium`** — Any moderate signal but none of the high triggers.
- **`low`** — No high or medium signals.

### Registration Status Rules

Determine final registration outcome using this priority order (first match wins):

1. **`rejected`** — Insurance is `"invalid"` AND coverage `status` is `"expired"` (coverage_expired) OR PBM is `"invalid"` with `active` == 0 (pbm_invalid); OR the roster's `service_line` is not in coverage `service_lines` (excluded_service_line); OR PBM `policy_number` does not match coverage `policy_number` (pbm_policy_mismatch); OR `emergency_contact_present` is 0 (emergency_contact_missing).
2. **`clinical_review`** — Overall risk is `"high"` (overall_risk_high) OR PBM is `"invalid"` but `active` is 1 (pbm_invalid) OR preferred pharmacy is out-of-network (pharmacy_out_of_network) OR coverage `status` is `"pending"` (coverage_pending) OR `preferred_contact` is unavailable/null (preferred_contact_unavailable) OR `address` is null (missing_address) OR pharmacy status is `"unknown"` (pharmacy_unknown).
3. **`hold`** — Insurance is `"invalid"` for non-expired non-pending reasons, OR PBM is `"missing"`.
4. **`approved`** — Insurance is `"valid"`, PBM is `"valid"`, pharmacy is `"in_network"`, and overall risk is not `"high"`.

### Blocked Reason Codes

Build code lists from each patient's evaluation. When a condition triggers both a registration status and a reason code, include the reason code:

- `coverage_expired` — coverage `status` is `"expired"`
- `coverage_pending` — coverage `status` is `"pending"`
- `excluded_service_line` — roster's `service_line` not in coverage `service_lines`
- `emergency_contact_missing` — `emergency_contact_present` is 0
- `pbm_invalid` — PBM exists but `active` is 0 or `status` is `"rejected"`
- `pbm_missing` — no PBM records
- `pbm_policy_mismatch` — PBM `policy_number` differs from coverage `policy_number`
- `pharmacy_out_of_network` — all pharmacies are out-of-network
- `pharmacy_unknown` — no pharmacy records
- `preferred_contact_unavailable` — `preferred_contact` is null or unavailable
- `missing_address` — `address` is null
- `overall_risk_high` — overall risk determined as `"high"`

### Cohort Summary

Count fields from individual patient results: totals by registration status, overall risk, and lifestyle risk.

---

## Referral Readiness Audit

This workflow audits a batch of specialty referrals. Input: a batch ID and an answer template.

### Data Sources

1. **Referral batch:** `GET /referrals?batch_id=<batch_id>`
2. **Patient profiles:** `GET /patients/<patient_id>` for each patient referenced by a batch referral.
3. **ICD metadata:** `GET /icd/<icd10_code>` for each distinct ICD-10 code in the batch.
4. **Chart data:** `GET /chart/<patient_id>` as needed.

### ICD Discrepancy Detection

For each referral, compare `/icd/<code>` metadata against the referral record:

- **`icd_chapter_mismatch`** — `icd.service_family` does not match `referral.service_line`. Example: code from chapter S00-T88 (orthopedics) on a pulmonary referral. The `observed_chapter` is `icd.chapter`, `expected_chapter` is the chapter that corresponds to the referral's `service_line`.
- **`narrative_mismatch`** — The `icd.description` does not semantically match the referral's `referral_reason`.
- **`laterality_mismatch`** — The referral's `referral_reason` or `diagnosis_description` implies laterality, but `icd.laterality` is null or mismatched.

Note: ICD chapter to service_line mapping is determined by the ICD endpoint's `service_family` field — always query it rather than guessing.

### Duplicate Detection

When two referrals in the same batch share the same `patient_id`:

- Check if they have identical or near-identical `icd10_code`, `referral_reason`, and `referring_physician`.
- Check referral `notes` for `"possible duplicate"` or `"duplicate faxed by second practice"`.
- The earlier `referral_id` (lower numeric suffix) is the primary.
- **`consolidate_to_primary`** — Same patient, same code, duplicate signals present.
- **`keep_separate`** — Different codes or no duplicate indicators.

### Shared Insurance Anomalies

When two referrals in the same batch reference the same `insurance_id` but different `patient_id` values:

- If the same patient owns both (patient IDs match), disposition is `"legitimate_duplicate_same_patient"`.
- If different patients share the same insurance ID, disposition is `"verify_distinct_patient_policy_id"`.

### Authorization Blockers

Each referral has `auth_required` (0/1) and `auth_status`:

- `auth_status` == `"approved"` — OK.
- `auth_status` == `"denied"` — `auth_blocker` with `auth_status` `"denied"`.
- `auth_status` == `"pending"` — `auth_blocker` with `auth_status` `"pending"`.

### Missing Records/Imaging

- `records_received` == 0 — issue code `missing_records`.
- `imaging_received` == 0 — issue code `missing_imaging`.

### Readiness Status

Synthesize per-referral status from its issue codes:

- **`ready`** — No issue codes.
- **`blocked`** — Has issue codes from: `auth_blocker`, `missing_records`, `missing_imaging`.
- **`under_review`** — Has issue codes from: `icd_chapter_mismatch`, `narrative_mismatch`, `laterality_mismatch`, `duplicate_referral`, `already_scheduled`.
- **`admin_followup`** — Has `shared_insurance_anomaly` and no blocking/clinical issues.

If multiple categories apply, use precedence: blocked > under_review > admin_followup > ready.

### Already Scheduled

If `appointment_scheduled` is 1, add issue code `already_scheduled`.

### Priority Tiers

- **`tier_1_immediate`** — `urgency` is `"urgent"` AND readiness is `under_review` or `blocked`.
- **`tier_2_short_term`** — `urgency` is `"routine"` AND readiness is `blocked` or `under_review`; OR any referral with `already_scheduled`.
- **`tier_3_administrative`** — Readiness is `admin_followup`.
- **`null`** — Readiness is `ready`.

### Action Codes

Map issue codes to action codes:

- `icd_chapter_mismatch`, `narrative_mismatch`, `laterality_mismatch` → `request_corrected_icd` and/or `confirm_narrative` and/or `confirm_laterality`
- `duplicate_referral` → `consolidate_duplicate`
- `shared_insurance_anomaly` → `verify_insurance_id`
- `missing_records` → `request_records`
- `missing_imaging` → `request_imaging`
- `auth_blocker` → `resolve_authorization`
- `already_scheduled` → `review_existing_appointment`

---

## Transfer Review

This workflow reviews a batch of dialysis transfer packets. Input: a batch ID and answer template.

### Data Sources

1. **Transfer batch:** `GET /transfers?batch_id=<batch_id>`
2. **Documents:** `GET /documents` — filter by `transfer_id` in the batch and by `content_tag` == `"transfer_packet"`.
3. **Patient profiles:** `GET /patients/<patient_id>` for background.
4. **Chart data:** `GET /chart/<patient_id>` for clinical history.

### Required Transfer Packet Documents

The full set of document types that must be present (finalized/`status` == `"final"`) in the transfer packet:

- `allergy_list`
- `face_sheet`
- `flu_vaccine`
- `hbsag`
- `hep_b_antibody_core`
- `history_physical`
- `insurance_proof`
- `medication_list`
- `monthly_labs`
- `physician_orders`
- `pneumonia_vaccine`
- `ppd_or_cxr`
- `transportation`
- `treatment_flowsheets`
- `vascular_access_report`

### Packet Completeness

For each transfer, collect all documents with matching `transfer_id` and `content_tag` == `"transfer_packet"`. A document is "received" only if `status` == `"final"` (draft documents do not count).

- **`complete`** — All 15 required doc types are present as final documents.
- **`incomplete`** — At least one required doc type is missing or only in draft status.

Build the `missing_required_documents` list from the doc types that are absent or non-final.

### Stale Document Detection

Documents with known freshness limits:

| Doc Type | Freshness Limit (days) |
|---|---|
| `hbsag` | 30 |
| `hep_b_antibody_core` | 30 |
| `history_physical` | 365 |
| `monthly_labs` | 30 |
| `ppd_or_cxr` | 30 |

For each received document of one of these types, compare `received_date` to the current date. If `(current_date - received_date) > freshness_limit_days`, the document is stale. Include it in `stale_documents` with `doc_type`, `received_date`, and `freshness_limit_days`.

Use the date the task was generated as current date (typically visible in task context or prompt). If no date is given, assume today's date.

### Chair Capacity Assessment

Each transfer has `requested_start_date` and `chair_window` (morning|midday|evening). The task environment provides capacity data. Based on the training examples, capacity is a shared pool:

- Check if the requested start date has available chairs.
- `capacity_status` is `"available"` if `open_chairs_total` > 0, otherwise `"unavailable"`.
- `open_chairs_total` is the count of open chairs across Cedar Ridge in-center hemodialysis locations for the given date/window.

### Requested Start Feasibility

Combine packet readiness and capacity:

- **`ready_on_requested_start`** — Packet is complete AND capacity is available.
- **`packet_not_ready_capacity_available`** — Packet is incomplete AND capacity is available.
- **`packet_not_ready_capacity_unavailable`** — Packet is incomplete AND capacity is unavailable.
- **`capacity_unavailable`** — Packet is complete AND capacity is unavailable.

### Final Intake Decision

- **`accept`** — Packet is complete, no stale documents, capacity is available.
- **`clinical_review`** — Packet is incomplete OR has stale documents OR capacity is unavailable.
- **`hold`** — Specific administrative hold (not seen in training data for this workflow).

### Next Contact

- **`clinical_nurse`** — Decision is `clinical_review`. Route is `fax_referring_facility`.
- **`intake_coordinator`** — Decision is `hold` or `accept`. Route is `phone_patient`.
- **`scheduling_coordinator`** — Decision is `accept`. Route is `internal_queue`.
- **`none`** — No follow-up needed.

---

## Enrollment Panel

This workflow prepares a chronic-care program enrollment panel. Input: a program code and answer template.

### Data Sources

1. **Candidates:** `GET /programs/<program_code>/candidates`
2. **Patient charts:** `GET /chart/<patient_id>` for each candidate.
3. **Patient profiles:** `GET /patients/<patient_id>` for each candidate.

### Eligibility Rules

A candidate is eligible when:
- `target_condition` matches the program's target (e.g., `"diabetes_hypertension"` for `DMHTN-2026A`).
- `existing_chart` is 1 (has a chart record).
- `consent_status` is not `"declined"`.

A candidate is ineligible when:
- `target_condition` does not match (reason: `wrong_target_condition`).
- `existing_chart` is 0 (reason: `chart_not_active`).
- `consent_status` is `"declined"` (reason: `consent_declined`).

Also check that the chart has `active_problems` containing the diagnosis for the target condition. If missing, reason: `missing_active_dmhtn_diagnosis`.

### Enrollment Status

- **`enroll`** — Eligible AND no blockers (consent exists, chart is active, all required artifacts are current).
- **`hold`** — Eligible but chart artifacts are missing/stale OR consent is missing (not declined).
- **`reject`** — Ineligible (wrong condition, consent declined, chart not active, missing diagnosis).

### Reason Codes

- `meets_dmhtn_criteria` — Target condition matches and chart diagnosis present.
- `recent_hospitalization_high_touch` — `clinical_history.recent_hospitalization` is 1 or non-zero.
- `low_adherence_high_touch` — `adherence_score` < 50.
- `ckd_biweekly_monitoring` — `clinical_history.chronic_conditions` contains `"ckd"`.
- `recent_ed_high_touch` — Derived from clinical history or encounter data; present when risk_flags or history indicate recent ER use.
- `consent_declined` — `consent_status` is `"declined"`.
- `consent_missing` — `consent_status` is `"missing"` (not `"signed"` and not `"declined"`).
- `chart_not_active` — `existing_chart` is 0 OR chart endpoint returns no artifacts.
- `stale_active_problems` — `active_problems` has `status` == `"stale"`.
- `missing_recent_vitals` — `recent_vitals_labs` is empty or missing vitals.
- `missing_recent_labs` — `recent_vitals_labs` is empty or missing labs.
- `missing_medication_list` — `meds_allergies` is empty or medications artifact is missing.
- `wrong_target_condition` — `target_condition` does not match program target.
- `missing_active_dmhtn_diagnosis` — Chart `active_problems` does not contain the DMHTN diagnosis.

### Follow-Up Cadence

- **`weekly`** — High-touch reasons present (`recent_hospitalization_high_touch`, `low_adherence_high_touch`, `recent_ed_high_touch`).
- **`biweekly`** — `ckd_biweekly_monitoring` present.
- **`monthly`** — Standard enrollment (eligible, no high-touch or CKD triggers).
- **`deferred`** — Status is `hold` (chart issues pending).
- **`none`** — Status is `reject`.

### Outreach Channel

Use the candidate's `preferred_outreach` field:

- `portal` → `"portal"`
- `phone` → `"phone"`
- `sms` → `"sms"`
- `email` → `"email"`
- If `preferred_outreach` is null, map to the patient profile's `preferred_contact`. If still null, use `"none"`.

### Initial Monitoring Package

- **`high_touch_dm_htn`** — Status is `enroll` AND high-touch reasons present.
  - Components: `bp_cuff`, `glucometer`, `lab_order_a1c_cmp_lipid`, `medication_reconciliation`, `care_plan_setup`.
  - `first_checkin_days`: 7
- **`standard_dm_htn`** — Status is `enroll` AND no high-touch reasons.
  - Components: `bp_cuff`, `glucometer`, `lab_order_a1c_cmp_lipid`. Add `medication_reconciliation` when `medication_count` > 0. Add `care_plan_setup` when `medication_count` > 0 or `allergy_count` > 0.
  - `first_checkin_days`: 14 for biweekly, 30 for monthly.
- **`deferred`** — Status is `hold`.
  - Components: `consent_packet` (if consent missing), `chart_update_request` (if chart issues).
  - `first_checkin_days`: null
- **`not_applicable`** — Status is `reject`.
  - Components: [] (empty).
  - `first_checkin_days`: null

---

## Referral-to-Chart Activation

This workflow bridges referral intake to chart activation. Input: a batch ID and answer template.

### Data Sources

1. **Referral batch:** `GET /referrals?batch_id=<batch_id>`
2. **Patient charts:** `GET /chart/<patient_id>` for each referral's patient.
3. **ICD metadata:** `GET /icd/<code>` for each ICD code.
4. **Patient profiles:** `GET /patients/<patient_id>` for demographics.

### Readiness Assessment

For each referral, determine `readiness_status` and `blocker_codes`:

- **`ready`** — No blockers: auth approved/not_required, records received, imaging received, ICD matches service line, no duplicate issues, not already scheduled.
- **`blocked`** — Has at least one of: `authorization_blocked`, `records_missing`, `imaging_missing`.
- **`under_review`** — Has `clinical_code_discrepancy` (ICD service_family mismatch with service_line) and no blocking issues.
- **`admin_followup`** — Has `duplicate_review` or `scheduled_before_clearance` and no blocking/clinical issues.

Precedence: blocked > under_review > admin_followup > ready.

### Blocker Code Details

- `clinical_code_discrepancy` — ICD `service_family` != referral `service_line`.
- `records_missing` — `records_received` == 0.
- `imaging_missing` — `imaging_received` == 0.
- `authorization_blocked` — `auth_status` is `"denied"` or `"pending"`.
- `duplicate_review` — Referral `notes` contains `"possible duplicate"`.
- `scheduled_before_clearance` — `appointment_scheduled` == 1.

### Duplicate Handling

Identify referral pairs with same `patient_id` or same `icd10_code` + `referral_reason` where notes indicate duplication. The lower `referral_id` is `keep_referral_id`. The other is the duplicate.

`cleared_duplicate_review_referrals` contains referrals whose noted duplicate status was resolved (e.g., different ICD code for same patient, kept as separate).

### Ready Referral Chart Needs

For referrals with `readiness_status` == `ready`, examine the patient's chart:

- **`create_chart`** — `existing_chart` == 0. Need to create all foundational artifacts.
- **`update_chart`** — `existing_chart` == 1 but artifacts are missing or stale. List the artifact types that need creation/update.
- **`no_chart_action`** — Chart is complete and current.

Artifact types to check: `demographics`, `active_problems`, `medications`, `allergies`, `vitals`, `labs`, `consent`.

### Correspondence Queue

For non-ready referrals, map issue codes to correspondence templates:

- `clinical_code_discrepancy` + `wrong_service_family` → `clinical_code_clarification`, reason: `wrong_service_family`
- `clinical_code_discrepancy` + `clinical_reason_mismatch` → `clinical_code_clarification`, reason: `clinical_reason_mismatch`
- `authorization_blocked` → `auth_records_request`, reason: `authorization_denied`
- `records_missing` → `auth_records_request`, reason: `records_missing`
- `duplicate_review` → `duplicate_resolution`, reason: `duplicate_review`
- `scheduled_before_clearance` → `appointment_hold_notice`, reason: `appointment_already_scheduled`

When a referral has multiple issue codes, combine all matching reasons into one entry with the most severe `template_type`.

### Priority Order

Rank non-ready referrals by urgency and issue severity:

- **`tier_1_immediate`** — `urgency` == `"urgent"` and readiness is `under_review`.
- **`tier_2_short_term`** — Blocked referrals or routine under_review referrals.
- **`tier_3_administrative`** — `admin_followup` referrals.

Rank from 1 ascending. Only non-ready referrals are included.
