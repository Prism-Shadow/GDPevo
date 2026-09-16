# Decision Logic Reference

This document describes how to map raw portal data into the controlled vocabularies used by answer templates. The rules are organized by workflow type. Always defer to the answer template for the exact set of allowed values — the rules below explain how to determine which value applies.

---

## Workflow 1: Patient Access Verification

Used when the task involves a new-patient intake roster and asks for insurance, prescription, pharmacy, risk, and registration determinations per patient.

### Insurance Status

- **`valid`**: At least one coverage record with `status` = `"active"` AND the requested `service_line` is listed in that coverage's `service_lines` (comma-separated field).
- **`invalid`**: Coverage records exist but none meet both conditions above — either all are expired/terminated/pending, or the active coverage does not include the requested service line.
- **`missing`**: The `coverage` array is empty.

### Prescription (PBM) Status

- **`valid`**: At least one PBM record with `status` = `"approved"` AND `active` = 1 AND the PBM `policy_number` matches the coverage `policy_number`, AND `specialty_required` = 0.
- **`invalid`**: PBM records exist but none meet all the valid criteria (status is rejected/pending, active=0, formulary_status is "not_found", policy_number mismatch, or specialty_required=1).
- **`missing`**: The `pbm` array is empty.

### Pharmacy Network Status

Use the patient's preferred pharmacy (lowest `preference_rank`):

- **`in_network`**: Preferred pharmacy `network_status` = `"in_network"`.
- **`out_of_network`**: Preferred pharmacy `network_status` = `"out_of_network"`.
- **`unknown`**: The `pharmacies` array is empty.

### Lifestyle Risk

Assess from the `lifestyle` object:

- **`high`**: Any of: `alcohol_use` = `"Heavy"`, `smoking_status` = `"Current"`, `sleep_hours` < 6.0.
- **`medium`**: Any of: `alcohol_use` = `"Moderate"`, `smoking_status` = `"Former"`, `sleep_hours` between 6.0 and 7.0 (inclusive), `exercise_frequency` is `"None"` combined with other moderate indicators. Also use medium when multiple moderate indicators are present even if no single one crosses the high threshold.
- **`low`**: None of the above risk factors are present. `alcohol_use` = `"None"` or `"Occasional"`, `smoking_status` = `"Never"`, `sleep_hours` ≥ 7.0, and `exercise_frequency` indicates regular activity.

### Overall Risk

Map each dimension to a risk level, then take the maximum:

| Dimension | → low | → medium | → high |
|-----------|-------|----------|--------|
| Insurance | valid | — | invalid, missing |
| Prescription | valid | invalid, missing | — |
| Pharmacy | in_network | out_of_network, unknown | — |
| Lifestyle | low | medium | high |

`overall_risk` = max(low, medium, high) across the four dimensions above.

### Registration Status

- **`approved`**: insurance_status = `"valid"`, prescription_status = `"valid"`, pharmacy_status = `"in_network"`, overall_risk ≤ `"medium"`, and no demographic gaps (address present, emergency contact present, preferred contact method available).
- **`rejected`**: Hard blocks — insurance_status = `"invalid"` due to excluded service line (coverage is active but does not include the requested service_line), OR insurance_status = `"invalid"` due to expired coverage AND the service line is also excluded. The key trigger for rejection is `excluded_service_line`.
- **`hold`**: Coverage status is `"pending"` — not yet active but not definitively rejected. Use this when the primary blocker is pending coverage.
- **`clinical_review`**: All other cases — issues exist but none rise to the level of hard rejection. This is the default when there are PBM issues, pharmacy network issues, missing address, missing emergency contact, unavailable preferred contact, or elevated risk, but the insurance can potentially be resolved.

### Blocked Reason Codes

Apply every code that is true for the patient. The template defines the allowed set; common codes:

| Code | Condition |
|------|-----------|
| `coverage_expired` | Any coverage record has `status` = `"expired"` or `"terminated"` |
| `coverage_pending` | Coverage `status` = `"pending"` |
| `excluded_service_line` | The requested `service_line` is absent from all active coverage `service_lines` |
| `emergency_contact_missing` | `emergency_contact_present` = 0 |
| `missing_address` | Patient `address` is null |
| `pbm_invalid` | PBM exists but status is rejected, inactive, or formulary not found |
| `pbm_missing` | No PBM record at all |
| `pbm_policy_mismatch` | PBM `policy_number` ≠ coverage `policy_number`, or `specialty_required` = 1 |
| `pharmacy_out_of_network` | Preferred pharmacy `network_status` = `"out_of_network"` |
| `pharmacy_unknown` | No pharmacy records |
| `preferred_contact_unavailable` | Patient's `preferred_contact` method has no corresponding value (e.g., preferred_contact is "email" but email is null, or "phone" but phone is null, or "sms" but phone is null) |
| `overall_risk_high` | `overall_risk` = `"high"` |

---

## Workflow 2: Referral Batch Audit

Used when the task asks to audit a referral batch for readiness, ICD discrepancies, duplicates, authorization gaps, and missing records/imaging.

### ICD Discrepancy Detection

For each referral, fetch the ICD metadata via `GET /icd/{icd10_code}`. Check:

1. **ICD chapter mismatch** (`icd_chapter_mismatch`): The ICD `chapter` does not match the expected chapter for the referral's `service_line`. Typical expected chapters:
   - orthopedics → M00-M99
   - pulmonary → J00-J99
   - cardiology → I00-I99
   - neurology → G00-G99
   
   Even when the ICD's `service_family` matches the referral `service_line`, the chapter may still differ — the `service_family` and `chapter` are independent attributes. Always check both.

2. **Narrative mismatch** (`narrative_mismatch`): The ICD `description` or clinical category contradicts the `diagnosis_description` or `referral_reason` on the referral. Only flag this when the answer template includes it as an allowed issue type.

3. **Laterality mismatch** (`laterality_mismatch`): The ICD `laterality` field conflicts with laterality implied by the referral notes or diagnosis. Only flag when the template allows it.

Record each ICD discrepancy with the `referral_id`, `icd10_code`, the `issue_types` found, the `observed_chapter` (ICD actual chapter), and `expected_chapter` (chapter expected for the service line). Use null for `observed_chapter` and `expected_chapter` when the issue type does not involve chapter mismatch.

### Duplicate Detection

Group referrals that share the same `patient_id` AND the same `icd10_code`. A group with 2+ referrals is a duplicate group. 

The primary referral is the one with the earliest `date_received` (lowest `referral_id` as tiebreaker). Recommendation is `consolidate_to_primary` unless there are clinical reasons to keep both (different laterality documented in ICD metadata, different referring providers with distinct clinical questions).

Also check the referral `notes` field for "possible duplicate" markers — these indicate potential duplicates across different ICD codes that need human review.

### Shared Insurance Anomalies

When two referrals for **different** patients share the same `insurance_id`, flag as a shared insurance anomaly. Disposition:

- `verify_distinct_patient_policy_id` — default; the same insurance ID on different patients suggests a data error.
- `legitimate_duplicate_same_patient` — only when the two patients are confirmed to share a policy legitimately.

### Blocker Detection

| Blocker | Condition |
|---------|-----------|
| `auth_blocker` | `auth_required` = 1 AND `auth_status` is `"denied"`, `"pending"`, or `"not_submitted"` |
| `missing_records` | `records_received` = 0 |
| `missing_imaging` | `imaging_received` = 0 |
| `already_scheduled` | `appointment_scheduled` = 1 |

### Readiness Status

Determine per referral, using the first applicable status in priority order:

1. **`blocked`**: Has any of: `auth_blocker`, `missing_records`, or `missing_imaging`. These require action before the referral can move forward. Blocked status takes precedence — if a referral has both blocking issues and review issues, it's blocked.
2. **`under_review`**: Has any of: ICD discrepancy, duplicate, or `already_scheduled`. These need clinical or administrative review but aren't hard-blocked.
3. **`admin_followup`**: Only has a `shared_insurance_anomaly` (and no other issues). Purely administrative.
4. **`ready`**: No issues at all. The referral can proceed to scheduling.

### Priority Tier

- **`tier_1_immediate`**: `urgency` = `"urgent"` with clinical issues (ICD discrepancy, duplicate requiring consolidation).
- **`tier_2_short_term`**: Non-urgent referrals with blocking or review issues, or urgent referrals with only non-clinical issues.
- **`tier_3_administrative`**: `admin_followup` referrals or referrals with `urgency` = `"admin"`.
- **`null`**: Ready referrals (no priority tier, they go straight to scheduling).

### Action Codes

Map issues to the corresponding action:

| Issue | Action Code |
|-------|-------------|
| ICD chapter mismatch | `request_corrected_icd` |
| ICD narrative mismatch | `confirm_narrative` |
| ICD laterality mismatch | `confirm_laterality` |
| Duplicate | `consolidate_duplicate` |
| Shared insurance anomaly | `verify_insurance_id` |
| Missing records | `request_records` |
| Missing imaging | `request_imaging` |
| Auth blocked | `resolve_authorization` |
| Already scheduled | `review_existing_appointment` |

### Summary Guidelines

- `counts_by_urgency`: count referrals by their `urgency` field. Use only the keys defined in the template (typically `urgent`, `routine`, `admin`).
- `counts_by_readiness_status`: use the template's status keys (typically `ready`, `blocked`, `under_review`, `admin_followup`).
- `counts_by_urgency_and_status`: cross-tabulation sorted by urgency then readiness_status. Only include combinations with count > 0 unless the template requires all combinations.
- `issue_counts`: count distinct referrals/groups for each issue category:
  - `icd_discrepancy_referrals`: number of referrals with at least one ICD issue.
  - `duplicate_groups`: number of duplicate groups (not number of referrals in groups).
  - `shared_insurance_anomalies`: number of anomaly records.
  - `missing_records_referrals`: number of referrals with `records_received` = 0.
  - `missing_imaging_referrals`: number of referrals with `imaging_received` = 0.
  - `auth_blocker_referrals`: number of referrals with an authorization blocker.

---

## Workflow 3: Dialysis Transfer Review

Used when the task asks to review dialysis transfer packets for completeness, document freshness, capacity feasibility, and intake decisions.

### Required Transfer Packet Documents

The standard required document set for a dialysis transfer packet:
```
allergy_list, face_sheet, flu_vaccine, hbsag, hep_b_antibody_core,
history_physical, insurance_proof, medication_list, monthly_labs,
physician_orders, pneumonia_vaccine, ppd_or_cxr, transportation,
treatment_flowsheets, vascular_access_report
```

### Packet Completeness

For each transfer:
1. Pull all documents for the patient from `GET /patients/{patient_id}` → `documents[]`, filtered to entries where `transfer_id` matches.
2. Only count documents where `finalized` = 1 AND `status` = `"final"`. Documents in `"draft"` status or with `finalized` = 0 are treated as absent.
3. Compare the set of present `doc_type` values against the required set.
4. If all 15 required types are present → `packet_completeness_status` = `"complete"`. Otherwise → `"incomplete"`.
5. List missing types in `missing_required_documents`, sorted alphabetically by code.

### Document Freshness

For each finalized document of a type with a freshness limit, check staleness using the **requested start date** as the evaluation date:

| Doc Type | Freshness Limit |
|----------|----------------|
| hbsag | 30 days |
| hep_b_antibody_core | 30 days |
| history_physical | 365 days |
| monthly_labs | 30 days |
| ppd_or_cxr | 30 days |

A document is **stale** when `requested_start_date − received_date > freshness_limit_days`. Compute as the difference in calendar days. Only include stale documents in the `stale_documents` array (with `doc_type`, `received_date`, `freshness_limit_days`), sorted alphabetically by `doc_type`. Documents of types not listed above have no freshness limit and are never reported as stale.

### Chair Capacity Feasibility

For each transfer's `requested_start_date`:

1. **`capacity_status`**: Determine whether Cedar Ridge has open in-center hemodialysis chairs on that date. Query capacity data through the portal (check for capacity-related tables via the SQL endpoint, or look at transfer-level capacity indicators). 
2. **`open_chairs_total`**: The number of open in-center hemodialysis chairs across Cedar Ridge locations on that date. Use 0 when capacity is unavailable.
3. **`feasibility`**:
   - `"ready_on_requested_start"` — packet is complete, all documents are fresh, AND capacity is available.
   - `"packet_not_ready_capacity_available"` — packet has issues (missing or stale documents) but capacity is available.
   - `"packet_not_ready_capacity_unavailable"` — packet has issues AND capacity is unavailable.
   - `"capacity_unavailable"` — packet is ready (complete and fresh) but capacity is unavailable.

### Final Intake Decision

- **`accept`**: Packet complete, all documents fresh, capacity available on requested start date.
- **`hold`**: Packet is ready but capacity unavailable (waiting for chair availability).
- **`clinical_review`**: Any packet issues (missing or stale documents) regardless of capacity. This is the default when the packet isn't fully ready.

### Next Contact

- **`next_contact_owner`**: `"clinical_nurse"` when clinical review is needed (missing/stale clinical documents); `"intake_coordinator"` for administrative follow-up (missing insurance/transportation); `"scheduling_coordinator"` when ready to schedule but capacity unavailable; `"none"` when accepted with no further action.
- **`next_contact_route`**: `"fax_referring_facility"` for missing or stale documents that the referring facility must provide; `"phone_patient"` for patient-outreach scenarios; `"internal_queue"` for capacity waitlist; `"none"` when no contact needed.

### Cohort Summary

- `total_transfers`: count of transfers in the batch.
- `complete_documents_count`: number of transfers with `packet_completeness_status` = `"complete"`.
- `missing_document_patient_count`: number of transfers with at least one missing document.
- `stale_document_patient_count`: number of transfers with at least one stale document.
- `capacity_available_count`: number of transfers with `capacity_status` = `"available"`.
- `requested_start_ready_count`: number of transfers with `feasibility` = `"ready_on_requested_start"`.
- `decision_counts`: breakdown by `final_intake_decision`.
- `next_contact_owner_counts`: breakdown by `next_contact_owner`.

---

## Workflow 4: Chronic-Care Enrollment Panel

Used when the task asks to prepare an enrollment panel from program candidates.

### Eligibility

A candidate is eligible (`eligible: true`) when:
- Their `target_condition` matches the program's target condition (e.g., `"diabetes_hypertension"` for DMHTN programs, verified against the program metadata from the candidates endpoint).
- The patient has an active diagnosis for the target condition, verified via the patient's `clinical_history.chronic_conditions` (comma-separated) containing both relevant conditions (e.g., both "diabetes" and "hypertension" for DMHTN).

A candidate is ineligible (`eligible: false`) when either condition fails — wrong target condition OR no active diagnosis for the required conditions.

### Enrollment Status

- **`enroll`**: Eligible AND `consent_status` = `"signed"` AND chart is active (`existing_chart` = 1, chart artifacts are `"current"` not `"stale"`). The patient is ready for enrollment.
- **`hold`**: Eligible but has resolvable blockers — `consent_status` = `"missing"`, or chart is inactive/has stale artifacts. These patients need follow-up before enrollment can proceed. Consent missing alone is not a rejection; it's a hold.
- **`reject`**: Ineligible (wrong target condition), OR `consent_status` = `"declined"`. Declined consent is a hard rejection regardless of eligibility.

### Reason Codes

Apply every code that matches the patient's situation:

| Code | Condition |
|------|-----------|
| `meets_dmhtn_criteria` | Eligible for the program — target condition matches and diagnosis is present. Always include for eligible patients. |
| `recent_hospitalization_high_touch` | `clinical_history.recent_hospitalization` = 1 |
| `low_adherence_high_touch` | `adherence_score` < 50 |
| `ckd_biweekly_monitoring` | `clinical_history.chronic_conditions` contains "ckd" |
| `recent_ed_high_touch` | Indicated by ED-related flags in the patient record (check `risk_flags`, chart data, or clinical history for ED visit indicators) |
| `consent_declined` | `consent_status` = `"declined"` |
| `consent_missing` | `consent_status` = `"missing"` |
| `chart_not_active` | `existing_chart` = 0 OR chart artifacts are absent/stale |
| `stale_active_problems` | `active_problems` artifact `status` = `"stale"` or absent |
| `missing_recent_vitals` | No `vitals` artifact present OR status = `"stale"` |
| `missing_recent_labs` | No `labs` artifact present OR status = `"stale"` |
| `missing_medication_list` | No `medications` artifact present OR status = `"stale"` |
| `wrong_target_condition` | `target_condition` does not match the program's expected condition |
| `missing_active_dmhtn_diagnosis` | No active diagnosis for the target condition in `clinical_history.chronic_conditions` or `active_problems` |

### Follow-up Cadence

- **`weekly`**: High-touch patients — those with `recent_hospitalization_high_touch`, `low_adherence_high_touch`, or `recent_ed_high_touch`.
- **`biweekly`**: Standard monitoring with CKD comorbidity (`ckd_biweekly_monitoring`).
- **`monthly`**: Standard monitoring, no complicating factors, no high-touch indicators.
- **`deferred`**: On hold — waiting for consent, chart updates, or other resolution.
- **`none`**: Rejected patients, no follow-up needed.

### Missing Chart Artifacts

List artifact types that are missing (absent from chart) or stale. Check the `/chart/{patient_id}` endpoint for `chart_artifacts` and their `status` values. Possible values to report: `chart_record` (when `existing_chart` = 0, indicating the whole chart is absent), `active_problems`, `vitals`, `labs`, `medications`, `consent`. Sort alphabetically. Use an empty array when nothing is missing.

### Outreach Channel

Based on the candidate's `preferred_outreach` field (or fall back to the patient's `preferred_contact` from the patient record):
- `"portal"` → `"portal"`
- `"phone"` → `"phone"`
- `"sms"` → `"sms"`
- `"email"` → `"email"`
- No usable contact method available → `"none"`

Use `"none"` only when the patient genuinely has no reachable contact method — when the preferred method is unavailable AND no alternative exists.

### Initial Monitoring Package

| Package Type | When to Assign | Components |
|-------------|----------------|------------|
| `high_touch_dm_htn` | `enrollment_status` = `"enroll"` AND any high-touch indicator (recent hospitalization, low adherence, recent ED) | bp_cuff, glucometer, lab_order_a1c_cmp_lipid, medication_reconciliation, care_plan_setup |
| `standard_dm_htn` | `enrollment_status` = `"enroll"`, no high-touch indicators | bp_cuff, glucometer, lab_order_a1c_cmp_lipid — plus medication_reconciliation when the patient has multiple chronic conditions or high medication_count |
| `deferred` | `enrollment_status` = `"hold"` | consent_packet, chart_update_request |
| `not_applicable` | `enrollment_status` = `"reject"` | Empty components list |

**First check-in days**: 7 for weekly cadence, 14 for biweekly, 30 for monthly, `null` for deferred and not_applicable.

### Summary

- `total_candidates`: count of all candidates returned for the program.
- `eligible_count`: count with `eligible` = true.
- `ineligible_count`: count with `eligible` = false.
- All `*_counts` fields: breakdown by the corresponding field. Every key in the template must appear even when the count is 0.

---

## Workflow 5: Referral-to-Chart Activation

Used when the task asks to reconcile referrals against chart readiness and produce a chart-activation plan with correspondence and priorities.

### Clinical Code Discrepancy

For each referral, compare the ICD metadata against the referral data:

1. **Wrong service family** (`wrong_service_family`): The ICD's `service_family` does not match the referral's `service_line`. For example, a cardiology ICD code (I25.10, service_family "cardiology") on a pulmonary referral.

2. **Clinical reason mismatch** (`clinical_reason_mismatch`): The `referral_reason` is inconsistent with what the ICD code represents — e.g., "pain evaluation" for an asthma code (J45.40), "transfer of care" for a symptom code rather than a disease code, or "previsit clearance" for an acute injury code.

Flag referrals with either issue as `clinical_code_discrepancy`. Only include issue types that the answer template allows.

### Readiness Determination

For each referral:

- **`ready`**: No authorization blockers, records received, imaging received, no clinical code discrepancy, not part of an unresolved duplicate, not scheduled before clearance. The referral can proceed to chart activation.
- **`blocked`**: Has authorization blocker (`auth_required` = 1 AND `auth_status` in ("denied", "pending")), OR records missing (`records_received` = 0), OR imaging missing (`imaging_received` = 0). Blocked takes precedence over other non-ready statuses.
- **`under_review`**: Has clinical code discrepancy, OR is part of a duplicate group (but no hard blockers). Needs clinical review.
- **`admin_followup`**: Has only administrative issues (e.g., insurance anomaly with no clinical or blocking concerns).

### Blocker Sets

Organize referrals with issues into named lists (sorted ascending by referral_id):

- **`authorization`**: Referrals where `auth_required` = 1 AND `auth_status` is `"denied"` or `"pending"`.
- **`records`**: Referrals where `records_received` = 0.
- **`imaging`**: Referrals where `imaging_received` = 0.

### Duplicate Handling

Two parts:

1. **`duplicate_groups`**: Same logic as Workflow 2. Group referrals by shared `patient_id` + `icd10_code`. For each group with 2+ referrals, record the `group_id`, `referral_ids` (sorted), and the `keep_referral_id` (primary — earliest date received). Empty array if no duplicates found.

2. **`cleared_duplicate_review_referrals`**: Referrals marked "possible duplicate" in `notes` that, upon review, are confirmed as distinct (different patients, different ICDs, or different clinical contexts) — they were flagged but cleared. List their referral IDs sorted ascending.

### Ready Referral Chart Needs

For each referral with `readiness_status` = `"ready"`:

1. Fetch `/chart/{patient_id}` to inspect chart artifacts.
2. Determine `chart_action`:
   - `"create_chart"` — patient has `existing_chart` = 0. All standard artifacts need creation.
   - `"update_chart"` — patient has a chart (`existing_chart` = 1) but some required artifacts are missing or stale. The chart needs updating, not creating from scratch.
   - `"no_chart_action"` — all required artifacts are present and current.
3. `artifacts_to_create`: the set of artifact types that need to be added or refreshed. Check which of these standard artifact types are missing or stale: `demographics`, `active_problems`, `medications`, `allergies`, `vitals`, `labs`, `consent`. List alphabetically. Use an empty array when `chart_action` = `"no_chart_action"`.

### Correspondence Queue

For each non-ready referral, determine what communication is needed:

| Template Type | When to Use |
|---------------|-------------|
| `clinical_code_clarification` | ICD discrepancy — `wrong_service_family` or `clinical_reason_mismatch` |
| `auth_records_request` | Authorization blocked OR records missing. Include both `authorization_denied` and `records_missing` reason codes as applicable. |
| `duplicate_resolution` | Referral is part of a duplicate group |
| `appointment_hold_notice` | Referral was scheduled before clearance (`appointment_scheduled` = 1), especially when combined with other issues |

Include `reason_codes` that explain why, using only the template's allowed values (e.g., `wrong_service_family`, `clinical_reason_mismatch`, `authorization_denied`, `records_missing`, `duplicate_review`, `appointment_already_scheduled`). Sort reason codes alphabetically.

### Priority Order

Rank non-ready referrals by urgency and clinical impact. Only include referrals that are not `"ready"`. Assign `rank` starting from 1:

- **`tier_1_immediate`**: Urgent referrals with clinical code discrepancies — these need fast clinical clarification to avoid care delays.
- **`tier_2_short_term`**: Blocked referrals (auth/records/imaging issues) regardless of urgency, or routine referrals with ICD discrepancies.
- **`tier_3_administrative`**: Admin-urgency referrals or those with only administrative issues.

Within the same tier, order by urgency (urgent before routine before admin), then by referral_id ascending.

---

## Cross-Workflow Patterns

### Risk Stratification

Several workflows use risk levels (low/medium/high). The general approach:

1. Map each data point to a risk level using domain-appropriate thresholds (documented per workflow above).
2. Take the maximum risk across all dimensions as the overall risk.
3. Use the overall risk to influence the final status and reason codes.

### Status Determination

Status fields across all workflows follow a consistent pattern. For each entity, cascade from worst to best:

1. Check for hard blockers first → rejected / blocked.
2. Check for soft issues → clinical_review / under_review / hold.
3. If nothing found → approved / ready / enroll / accept.

When an entity has both hard blockers and soft issues, the hard-blocker status takes precedence.

### Counting and Summaries

Every workflow ends with a summary object defined by the answer template:

- `total_*` = count of all entities in scope.
- `counts_by_*` = breakdown by a categorical field. Every category key in the template must appear even when the count is 0.
- `*_count` = count of entities with a specific property.

Always ensure summary counts are internally consistent and match the per-entity results exactly. Cross-check: the sum of all status/decision counts should equal the total.
