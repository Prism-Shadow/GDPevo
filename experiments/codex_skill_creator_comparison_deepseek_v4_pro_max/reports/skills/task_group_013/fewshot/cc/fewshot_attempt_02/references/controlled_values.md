# Controlled Values by Intake Type

This reference lists the complete set of allowed enum values organized by
intake type. Always consult the answer template first — it might have a
subset of these values for the specific batch. Use values exactly as written
here (lowercase, underscores).

## New-Patient Access Verification

**insurance_status**: `valid`, `invalid`, `missing`
**prescription_status**: `valid`, `invalid`, `missing`
**pharmacy_status**: `in_network`, `out_of_network`, `unknown`
**lifestyle_risk**: `low`, `medium`, `high`
**overall_risk**: `low`, `medium`, `high`
**registration_status**: `approved`, `hold`, `clinical_review`, `rejected`
**blocked_reason_codes**:
- `coverage_expired` — insurance end date is past
- `coverage_pending` — insurance verification in progress
- `emergency_contact_missing` — no emergency contact on file
- `excluded_service_line` — service line not covered by plan
- `missing_address` — patient address is missing or incomplete
- `pbm_invalid` — prescription benefit check failed
- `pbm_missing` — no prescription benefit record found
- `pbm_policy_mismatch` — PBM policy does not cover the medication
- `pharmacy_out_of_network` — preferred pharmacy is out of network
- `pharmacy_unknown` — preferred pharmacy not found in pharmacy records
- `preferred_contact_unavailable` — patient cannot be reached at preferred contact
- `overall_risk_high` — cumulative risk factors exceed threshold

## Referral Batch Audit

**readiness_status**: `ready`, `blocked`, `under_review`, `admin_followup`
**issue_codes**:
- `icd_chapter_mismatch` — ICD-10 code's chapter does not match the specialty
- `narrative_mismatch` — referral narrative contradicts the ICD code
- `laterality_mismatch` — laterality in narrative doesn't match code
- `duplicate_referral` — same patient referred more than once for the same condition
- `shared_insurance_anomaly` — same insurance ID on different patients
- `missing_records` — required patient records not found
- `missing_imaging` — required imaging not found
- `auth_blocker` — authorization is denied or pending
- `already_scheduled` — patient already has an appointment

**priority_tier**: `tier_1_immediate`, `tier_2_short_term`, `tier_3_administrative`

**icd_discrepancy issue_types**: `icd_chapter_mismatch`, `narrative_mismatch`, `laterality_mismatch`

**duplicate recommendation**: `consolidate_to_primary`, `keep_separate`

**shared_insurance disposition**: `verify_distinct_patient_policy_id`, `legitimate_duplicate_same_patient`

**auth_status**: `pending`, `denied`, `not_submitted`

**action_codes**:
- `request_corrected_icd`, `confirm_narrative`, `confirm_laterality`
- `consolidate_duplicate`, `verify_insurance_id`
- `request_records`, `request_imaging`, `resolve_authorization`
- `review_existing_appointment`

**urgency**: `urgent`, `routine`, `admin`

## Dialysis Transfer Review

**packet_completeness_status**: `complete`, `incomplete`

**document types** (allowed for both missing_required_documents and stale_documents.doc_type):
`allergy_list`, `face_sheet`, `flu_vaccine`, `hbsag`, `hep_b_antibody_core`,
`history_physical`, `insurance_proof`, `medication_list`, `monthly_labs`,
`physician_orders`, `pneumonia_vaccine`, `ppd_or_cxr`, `transportation`,
`treatment_flowsheets`, `vascular_access_report`

**stale document types** (subset checked for staleness):
`hbsag` (30 days), `hep_b_antibody_core` (30 days), `history_physical` (365 days),
`monthly_labs` (30 days), `ppd_or_cxr` (30 days)

**capacity_status**: `available`, `unavailable`

**feasibility**:
- `ready_on_requested_start` — packet complete and chairs available
- `packet_not_ready_capacity_available` — packet incomplete but chairs available
- `packet_not_ready_capacity_unavailable` — packet incomplete and no chairs
- `capacity_unavailable` — packet complete but no chairs

**final_intake_decision**: `accept`, `hold`, `clinical_review`

**next_contact_owner**: `clinical_nurse`, `intake_coordinator`, `scheduling_coordinator`, `none`

**next_contact_route**: `fax_referring_facility`, `phone_patient`, `internal_queue`, `none`

## Chronic-Care Program Enrollment

**eligible**: `true`, `false` (boolean)

**enrollment_status**: `enroll`, `hold`, `reject`

**reason_codes**:
- `meets_dmhtn_criteria` — patient meets program clinical criteria
- `recent_hospitalization_high_touch` — recent inpatient stay requires intensive monitoring
- `low_adherence_high_touch` — medication adherence below threshold
- `ckd_biweekly_monitoring` — CKD comorbidity requires biweekly follow-up
- `recent_ed_high_touch` — recent ED visit requires intensive monitoring
- `consent_declined` — patient declined consent
- `consent_missing` — consent not obtained yet
- `chart_not_active` — no active chart record
- `stale_active_problems` — active problems list out of date
- `missing_recent_vitals` — no recent vitals in chart
- `missing_recent_labs` — no recent labs in chart
- `missing_medication_list` — no medication list in chart
- `wrong_target_condition` — patient does not have the target condition
- `missing_active_dmhtn_diagnosis` — no active DM/HTN diagnosis on file

**follow_up_cadence**: `weekly`, `biweekly`, `monthly`, `deferred`, `none`

**missing_chart_artifacts**: `chart_record`, `active_problems`, `vitals`, `labs`, `medications`, `consent`

**outreach_channel**: `phone`, `portal`, `sms`, `email`, `none`

**package_type**: `standard_dm_htn`, `high_touch_dm_htn`, `deferred`, `not_applicable`

**package_components**: `bp_cuff`, `glucometer`, `lab_order_a1c_cmp_lipid`, `medication_reconciliation`,
`care_plan_setup`, `consent_packet`, `chart_update_request`

## Referral-to-Chart Activation

**readiness_status**: `ready`, `blocked`, `under_review`, `admin_followup`

**blocker_codes**:
- `clinical_code_discrepancy` — ICD code doesn't match service line or clinical reason
- `records_missing` — required patient records not found
- `imaging_missing` — required imaging not found
- `authorization_blocked` — authorization denied or pending
- `duplicate_review` — referral flagged as potential duplicate
- `scheduled_before_clearance` — appointment exists before chart is ready

**chart_action**: `create_chart`, `update_chart`, `no_chart_action`

**chart_artifacts**: `demographics`, `active_problems`, `medications`, `allergies`, `vitals`, `labs`, `consent`

**template_type**: `clinical_code_clarification`, `auth_records_request`, `duplicate_resolution`, `appointment_hold_notice`

**correspondence_reason_codes**: `wrong_service_family`, `clinical_reason_mismatch`, `records_missing`,
`authorization_denied`, `duplicate_review`, `appointment_already_scheduled`

**priority_tier**: `tier_1_immediate`, `tier_2_short_term`, `tier_3_administrative`
