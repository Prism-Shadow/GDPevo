# Decision Trees by Intake Type

These rules map portal data into controlled output values. Always consult
the answer template first — it may restrict which values are active for
a specific batch. Apply the rules in the order given.

## 1. New-Patient Access Verification

### insurance_status

- `valid` — insurance record exists, coverage end date is in the future,
  and the patient's service line is covered.
- `invalid` — insurance record exists but coverage end date is in the past
  (`coverage_expired`), coverage verification is pending (`coverage_pending`),
  or the service line is excluded (`excluded_service_line`). Also `invalid`
  when address or emergency contact data is missing and that prevents
  completing verification.
- `missing` — no insurance record found for the patient.

### prescription_status (PBM check)

- `valid` — PBM record exists and returns an active policy matching the
  patient's prescriptions.
- `invalid` — PBM record exists but policy is inactive, mismatched, or
  verification failed. Sub-codes: `pbm_invalid`, `pbm_policy_mismatch`.
- `missing` — no PBM record found. Sub-code: `pbm_missing`.

### pharmacy_status

- `in_network` — patient's preferred pharmacy is found in `/pharmacies` and
  its `network_status` is `in_network`.
- `out_of_network` — pharmacy found but `network_status` is `out_of_network`.
- `unknown` — pharmacy not found in `/pharmacies` or patient has no preferred
  pharmacy on file.

### lifestyle_risk

Determined by patient chart data (smoking status, BMI, substance use flags,
etc.). The portal provides this as a direct field on the patient or chart
record. Use the value as-is: `low`, `medium`, or `high`.

### overall_risk

Compute from insurance status, prescription status, pharmacy status, and
lifestyle risk:
- `high` — any of: insurance is `invalid` or `missing`, prescription is
  `invalid` or `missing`, pharmacy is `out_of_network` or `unknown`, or
  lifestyle risk is `high`.
- `medium` — lifestyle risk is `medium` AND all other statuses are `valid`
  or `in_network`.
- `low` — lifestyle risk is `low` AND all other statuses are `valid` or
  `in_network`.

### registration_status

- `approved` — insurance `valid`, prescription `valid`, pharmacy `in_network`,
  overall_risk `low` or `medium`.
- `hold` — any required data is genuinely missing (not invalid — missing)
  and the remaining profile is otherwise approvable.
- `clinical_review` — overall_risk is `high` but no single factor is an
  outright reject condition. The patient needs a clinician to review.
- `rejected` — insurance `invalid` due to `excluded_service_line` or
  `coverage_expired`, or any combination that includes hard-blocker codes.

### blocked_reason_codes

Collect all reason codes that apply. A patient can have multiple codes.
- `excluded_service_line` forces `rejected`.
- `coverage_expired` forces `rejected`.
- `coverage_pending` with otherwise clean profile → `clinical_review`.
- `pharmacy_out_of_network` → contributes to `clinical_review` unless
  other hard blockers push to `rejected`.
- `overall_risk_high` → included whenever overall_risk is `high`.

## 2. Referral Batch Audit

### readiness_status

- `ready` — no issues found; referral can proceed to scheduling.
- `blocked` — has `auth_blocker`, `missing_records`, or `missing_imaging`
  (any one is enough to block).
- `under_review` — has `icd_chapter_mismatch`, `narrative_mismatch`,
  `laterality_mismatch`, `duplicate_referral`, or `already_scheduled`
  but no blocking issues.
- `admin_followup` — has `shared_insurance_anomaly` only (or predominantly).

### icd_chapter_mismatch

An ICD-10 code's chapter (obtained from `GET /icd/{code}`) does not match
the expected chapter for the referral's service line. For example, an
orthopedic referral expects chapter `M00-M99` (musculoskeletal); an
`S00-T88` code (injury) is a mismatch when the referral narrative describes
a chronic musculoskeletal condition.

### duplicate_referral

Two or more referrals share the same patient AND the same ICD-10 code or
closely related codes. The primary (earliest or most complete) is kept;
others are consolidated. Recommendation: `consolidate_to_primary`.

### shared_insurance_anomaly

The same `insurance_id` appears on referrals for different patients. This
could be a data error or a legitimate family plan. Disposition:
`verify_distinct_patient_policy_id` when patients are different.

### auth_blockers

Check the `authorization.status` field on each referral:
- `denied` → `auth_blocker` issue code, readiness_status `blocked`.
- `pending` → `auth_blocker` issue code, readiness_status `blocked`.
- `approved` or absent → no auth blocker.

### priority_tier assignment

- `tier_1_immediate` — `auth_blocker` with `denied` status, or referrals
  with multiple high-severity issues that would block scheduling if
  unresolved.
- `tier_2_short_term` — most non-ready referrals; coding discrepancies,
  missing records/imaging, duplicates.
- `tier_3_administrative` — insurance anomalies only, no clinical blockers.

### ready_to_schedule

List of referral IDs where `readiness_status` is `ready`. Empty list when
none are ready.

### urgency classification

- `urgent` — referral narrative or metadata indicates time-sensitive
  condition (e.g. acute injury, pain, neurological symptoms).
- `routine` — standard referral language, chronic condition management.
- `admin` — purely administrative follow-up with no clinical urgency.

## 3. Dialysis Transfer Review

### packet_completeness_status

- `complete` — all required document types for dialysis intake are present
  in the transfer's documents array.
- `incomplete` — one or more required document types are missing.

Required document types for a hemodialysis transfer packet:
`allergy_list`, `face_sheet`, `flu_vaccine`, `hbsag`, `hep_b_antibody_core`,
`history_physical`, `insurance_proof`, `medication_list`, `monthly_labs`,
`physician_orders`, `pneumonia_vaccine`, `ppd_or_cxr`, `transportation`,
`treatment_flowsheets`, `vascular_access_report`.

### stale_documents

Check each document in the transfer packet against its freshness limit.
A document is stale when `(as_of_date - received_date) > freshness_limit_days`:

| doc_type | freshness_limit_days |
|---|---|
| `hbsag` | 30 |
| `hep_b_antibody_core` | 30 |
| `history_physical` | 365 |
| `monthly_labs` | 30 |
| `ppd_or_cxr` | 30 |

Other document types are not subject to staleness checks.

### requested_start feasibility

Cross-reference `requested_start_date` with facility capacity. The portal
provides capacity data (open chairs) through the transfer or a related
endpoint.

- `capacity_status`: `available` when `open_chairs_total > 0`, otherwise
  `unavailable`.
- `feasibility`:
  - `ready_on_requested_start` — packet complete AND capacity available.
  - `packet_not_ready_capacity_available` — packet incomplete, capacity OK.
  - `packet_not_ready_capacity_unavailable` — packet incomplete, no capacity.
  - `capacity_unavailable` — packet complete but no capacity.

### final_intake_decision

- `accept` — packet complete, all documents fresh, capacity available.
- `hold` — packet nearly complete (minor gaps), capacity issues only.
- `clinical_review` — packet incomplete or documents stale; needs clinical
  nurse review before decision.

### next_contact_owner and route

- `clinical_nurse` / `fax_referring_facility` — when packet is incomplete
  and referring facility must send missing documents.
- `intake_coordinator` / `phone_patient` — when the issue is patient-side
  (missing insurance proof, transportation, etc.).
- `scheduling_coordinator` / `internal_queue` — when packet is ready but
  capacity is the blocker.
- `none` / `none` — when `final_intake_decision` is `accept`.

## 4. Chronic-Care Program Enrollment

### eligible determination

A patient is `eligible` (`true`) when:
- The program candidates endpoint includes them, AND
- Their chart contains diagnoses matching the program's target condition
  (e.g. active diabetes and hypertension diagnoses for the target program), AND
- They have not explicitly declined consent.

A patient is `eligible: false` when:
- They have `wrong_target_condition` — no matching diagnosis, OR
- They are in the candidate list but the chart confirms mismatched condition.

### enrollment_status

- `enroll` — eligible, consent present, chart active, can start monitoring.
- `hold` — eligible but consent is missing or chart artifacts are stale/missing.
  Deferred for follow-up to collect missing items.
- `reject` — not eligible, consent declined, or chart not active with no
  path to resolution.

### reason_codes

Collect all that apply per patient:
- Eligibility reasons: `meets_dmhtn_criteria`, `wrong_target_condition`,
  `missing_active_dmhtn_diagnosis`.
- Intensity modifiers: `recent_hospitalization_high_touch`, `low_adherence_high_touch`,
  `ckd_biweekly_monitoring`, `recent_ed_high_touch`.
- Blocker reasons: `consent_declined`, `consent_missing`, `chart_not_active`,
  `stale_active_problems`, `missing_recent_vitals`, `missing_recent_labs`,
  `missing_medication_list`.

### follow_up_cadence

- `weekly` — high-touch patients (recent hospitalization, ED visit, low adherence).
- `biweekly` — CKD comorbidity present.
- `monthly` — standard enrollment, no intensity modifiers.
- `deferred` — `hold` status, follow-up after blockers resolve.
- `none` — `reject` status.

### outreach_channel

Use the patient's preferred contact method from their patient record:
- Phone number present and marked primary → `phone`.
- Email present and marked primary → `email`.
- Portal account active → `portal`.
- SMS-enabled mobile on file → `sms`.
- No contact method available → `none`.

### initial_monitoring_package

- `high_touch_dm_htn` — weekly cadence. Components: `bp_cuff`, `glucometer`,
  `lab_order_a1c_cmp_lipid`, `medication_reconciliation`, `care_plan_setup`.
  `first_checkin_days`: 7.
- `standard_dm_htn` — biweekly or monthly cadence. Components: `bp_cuff`,
  `glucometer`, `lab_order_a1c_cmp_lipid`, `medication_reconciliation`
  (add `care_plan_setup` for biweekly with CKD). `first_checkin_days`:
  14 for biweekly, 30 for monthly.
- `deferred` — `hold` status. Components: `consent_packet`, `chart_update_request`.
  `first_checkin_days`: null.
- `not_applicable` — `reject` status. Components: `[]`. `first_checkin_days`: null.

### missing_chart_artifacts

List every chart artifact type that is absent, stale, or incomplete:
- `chart_record` — no chart exists or chart is inactive.
- `active_problems` — missing or stale.
- `vitals` — missing or no recent entry.
- `labs` — missing or no recent labs.
- `medications` — medication list missing.
- `consent` — consent form not on file.

## 5. Referral-to-Chart Activation

### readiness_status

- `ready` — no blockers; referral can proceed to chart activation.
- `blocked` — has `authorization_blocked`, `records_missing`, or
  `imaging_missing`.
- `under_review` — has `clinical_code_discrepancy` or `duplicate_review`
  but no hard blockers.
- `admin_followup` — has `scheduled_before_clearance` as primary issue.

### blocker_codes

- `clinical_code_discrepancy` — ICD code chapter does not match the
  service line's expected chapter, OR the clinical narrative contradicts
  the code.
- `records_missing` — required patient records absent from chart or documents.
- `imaging_missing` — required imaging studies not found.
- `authorization_blocked` — authorization status is `denied` or `pending`.
- `duplicate_review` — referral appears to be a duplicate.
- `scheduled_before_clearance` — an appointment already exists before
  chart activation is complete.

### ready_referral_chart_needs

For each ready referral, check the patient's chart (`GET /chart/{patient_id}`).
List every required chart artifact that is missing or incomplete.

Required chart artifacts for activation: `demographics`, `active_problems`,
`medications`, `allergies`, `vitals`, `labs`, `consent`.

`chart_action`:
- `create_chart` — no chart exists (404 from `/chart/{patient_id}`).
- `update_chart` — chart exists but one or more required artifacts are
  missing or incomplete.
- `no_chart_action` — chart is complete with all required artifacts.

Sort `artifacts_to_create` alphabetically by artifact enum string.

### correspondence_queue

For non-ready referrals, generate correspondence entries:
- `clinical_code_clarification` — when `clinical_code_discrepancy` is
  present. Reason codes: `wrong_service_family` (ICD chapter doesn't
  match service line), `clinical_reason_mismatch` (narrative contradicts
  code).
- `auth_records_request` — when `authorization_blocked` or `records_missing`
  is present. Reason codes: `authorization_denied`, `records_missing`.
- `duplicate_resolution` — when `duplicate_review` is present.
- `appointment_hold_notice` — when `scheduled_before_clearance` is present
  alongside other blockers. Reason code: `appointment_already_scheduled`.

### priority_order

Rank non-ready referrals by urgency, highest first:
- `tier_1_immediate` — authorization denied, multiple severe blockers.
- `tier_2_short_term` — clinical code discrepancies, missing records/imaging.
- `tier_3_administrative` — duplicate review, scheduled-before-clearance
  without clinical blockers.

Rank within each tier by number of blocker codes (more blockers = higher
priority). Assign sequential `rank` starting from 1.
