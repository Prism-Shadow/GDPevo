## Controlled Vocabularies

Every Cedar Ridge intake workflow uses a fixed vocabulary. Use only the values
listed in the answer template for each field. This reference collects all values
that appear across the five workflow types.

### Insurance / Pharmacy / Registration (Patient Access Verification)

**insurance_status**: `valid`, `invalid`, `missing`
**prescription_status**: `valid`, `invalid`, `missing`
**pharmacy_status**: `in_network`, `out_of_network`, `unknown`
**lifestyle_risk**: `low`, `medium`, `high`
**overall_risk**: `low`, `medium`, `high`
**registration_status**: `approved`, `hold`, `clinical_review`, `rejected`

**blocked_reason_codes**:
- `coverage_expired` — insurance end date before requested service date
- `coverage_pending` — insurance start date after requested service date
- `emergency_contact_missing` — no emergency contact on file
- `excluded_service_line` — service line not in covered_service_lines
- `missing_address` — address field is null or empty
- `pbm_invalid` — PBM record present but not active or plan mismatch
- `pbm_missing` — no PBM record
- `pbm_policy_mismatch` — PBM plan does not match insurance plan
- `pharmacy_out_of_network` — pharmacy not in preferred plan network
- `pharmacy_unknown` — pharmacy or network status data absent
- `preferred_contact_unavailable` — preferred contact method has no value
- `overall_risk_high` — overall_risk is `high`

### Referral Audit (Orthopedic / Pulmonary Referral Intake)

**readiness_status**: `ready`, `blocked`, `under_review`, `admin_followup`

**issue_codes** (referral_reviews):
- `icd_chapter_mismatch` — code chapter does not match service line
- `narrative_mismatch` — narrative text conflicts with ICD description
- `laterality_mismatch` — laterality field conflicts with ICD or narrative
- `duplicate_referral` — same patient, overlapping clinical scenario
- `shared_insurance_anomaly` — two different patients share same policy ID
- `missing_records` — no associated chart or documents
- `missing_imaging` — required imaging not present
- `auth_blocker` — authorization is denied, pending, or not submitted
- `already_scheduled` — appointment scheduled before clearance

**priority_tier**: `tier_1_immediate`, `tier_2_short_term`, `tier_3_administrative`, `null`
- `tier_1_immediate`: clinical safety (wrong chapter, active schedule)
- `tier_2_short_term`: missing records, imaging, or auth; duplicates needing consolidation
- `tier_3_administrative`: insurance verification, non-urgent admin

**blocker_codes** (chart activation variant):
- `clinical_code_discrepancy`
- `records_missing`
- `imaging_missing`
- `authorization_blocked`
- `duplicate_review`
- `scheduled_before_clearance`

**template_type** (correspondence_queue):
- `clinical_code_clarification`
- `auth_records_request`
- `duplicate_resolution`
- `appointment_hold_notice`

**reason_codes** (correspondence_queue):
- `wrong_service_family`
- `clinical_reason_mismatch`
- `records_missing`
- `authorization_denied`
- `duplicate_review`
- `appointment_already_scheduled`

**chart_action**: `create_chart`, `update_chart`, `no_chart_action`

**artifacts_to_create** (ordered alphabetically): `active_problems`, `allergies`, `consent`, `demographics`, `labs`, `medications`, `vitals`

### Dialysis Transfer Review

**packet_completeness_status**: `complete`, `incomplete`

**missing_required_documents** (ordered alphabetically by code):
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

**stale document types**: `hbsag`, `hep_b_antibody_core`, `history_physical`, `monthly_labs`, `ppd_or_cxr`

**capacity_status**: `available`, `unavailable`

**feasibility**: `ready_on_requested_start`, `packet_not_ready_capacity_available`, `packet_not_ready_capacity_unavailable`, `capacity_unavailable`

**final_intake_decision**: `accept`, `hold`, `clinical_review`

**next_contact_owner**: `clinical_nurse`, `intake_coordinator`, `scheduling_coordinator`, `none`

**next_contact_route**: `fax_referring_facility`, `phone_patient`, `internal_queue`, `none`

### Chronic-Care Enrollment Panel

**eligible**: boolean (`true` / `false`)

**enrollment_status**: `enroll`, `hold`, `reject`

**reason_codes**:
- `meets_dmhtn_criteria` — patient has qualifying DM/HTN diagnoses
- `recent_hospitalization_high_touch` — recent hospitalization triggers high-touch
- `low_adherence_high_touch` — poor medication adherence triggers high-touch
- `ckd_biweekly_monitoring` — CKD comorbidity requires biweekly follow-up
- `recent_ed_high_touch` — recent ED visit triggers high-touch
- `consent_declined` — patient declined consent
- `consent_missing` — no consent record on file
- `chart_not_active` — patient chart is inactive
- `stale_active_problems` — active problem list out of date
- `missing_recent_vitals` — no recent vitals in chart
- `missing_recent_labs` — no recent labs in chart
- `missing_medication_list` — no medication list in chart
- `wrong_target_condition` — patient condition does not match program target
- `missing_active_dmhtn_diagnosis` — no active DM/HTN diagnosis in chart

**follow_up_cadence**: `weekly`, `biweekly`, `monthly`, `deferred`, `none`

**missing_chart_artifacts** (unordered set): `chart_record`, `active_problems`, `vitals`, `labs`, `medications`, `consent`

**outreach_channel**: `phone`, `portal`, `sms`, `email`, `none`

**package_type**: `standard_dm_htn`, `high_touch_dm_htn`, `deferred`, `not_applicable`

**components** (unordered set):
- `bp_cuff`
- `glucometer`
- `lab_order_a1c_cmp_lipid`
- `medication_reconciliation`
- `care_plan_setup`
- `consent_packet`
- `chart_update_request`

**first_checkin_days**: integer or `null`, calendar days after enrollment start

### Summary Count Keys

All summary objects count integer occurrences. Common keys across workflows:

- **Registration status counts**: `approved`, `hold`, `clinical_review`, `rejected`
- **Risk counts**: `low`, `medium`, `high`
- **Urgency counts**: `urgent`, `routine`, `admin`
- **Readiness status counts**: `ready`, `blocked`, `under_review`, `admin_followup`
- **Decision counts**: `accept`, `hold`, `clinical_review`
- **Contact owner counts**: `clinical_nurse`, `intake_coordinator`, `scheduling_coordinator`, `none`
- **Follow-up cadence counts**: `weekly`, `biweekly`, `monthly`, `deferred`, `none`
- **Outreach channel counts**: `phone`, `portal`, `sms`, `email`, `none`
- **Package type counts**: `standard_dm_htn`, `high_touch_dm_htn`, `deferred`, `not_applicable`

Counts must sum to the total number of patients/referrals/transfers in the cohort.
