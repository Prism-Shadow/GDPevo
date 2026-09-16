# Cedar Ridge Business Rules

This reference defines the rules for deriving controlled template values from
raw API data. Apply these rules per patient/referral/transfer, then aggregate
the cohort summaries.

---

## Operation Type 1: Patient Access Verification (New Patient Intake)

This operation evaluates whether a patient on a roster can be registered for a
given service line and date.

### Input data per patient

- Patient demographics from `/patients/<id>` (address, emergency_contact_present, preferred_contact, email, phone)
- Coverage records from the `coverage` array
- PBM records from the `pbm` array
- Pharmacy records from the `pharmacies` array
- Lifestyle from the `lifestyle` object
- Roster record from the `rosters` array (gives `requested_service_date` and `service_line`)

### Determining insurance_status

| API condition | insurance_status |
|---------------|------------------|
| No coverage records at all | `missing` |
| All coverage records have status `expired` | `invalid` |
| At least one coverage is `active` or `pending` | `valid` |

However, even when status is `valid`, additional checks apply:
- If the coverage's `service_lines` field does NOT include the roster's `service_line`, add `excluded_service_line` to blocked codes.
- If the coverage status is `pending`, add `coverage_pending` to blocked codes.
- If the coverage status is `expired`, add `coverage_expired` to blocked codes.

### Determining prescription_status

| API condition | prescription_status |
|---------------|---------------------|
| No PBM records at all | `missing` |
| PBM record exists but `status` is `rejected` or `active` is 0 | `invalid` |
| PBM record exists, `status` is `approved`, `active` is 1 | `valid` |

Additional PBM checks:
- If the PBM `policy_number` does not match the coverage `policy_number`, add `pbm_policy_mismatch`.
- If PBM status is `rejected` or `active` is 0, add `pbm_invalid`.
- If no PBM record exists at all, add `pbm_missing`.

### Determining pharmacy_status

Look at the patient's preferred pharmacy (lowest `preference_rank` in the `pharmacies` array):

| API condition | pharmacy_status |
|---------------|-----------------|
| No pharmacy records | `unknown` |
| Preferred pharmacy `network_status` is `in_network` | `in_network` |
| Preferred pharmacy `network_status` is `out_of_network` | `out_of_network` |

Add `pharmacy_out_of_network` to blocked codes when status is `out_of_network`.
Add `pharmacy_unknown` to blocked codes when status is `unknown`.

### Determining lifestyle_risk

Risk factors: smoking_status is `Current`, alcohol_use is `Heavy`,
exercise_frequency is `None` (or null), sleep_hours < 6.

| Risk factor count | lifestyle_risk |
|-------------------|----------------|
| 3 or more risk factors | `high` |
| 1-2 risk factors | `medium` |
| 0 risk factors | `low` |

Note: `exercise_frequency` of `null` should be treated as `None` (it is a risk factor).

### Determining overall_risk

Start with `lifestyle_risk`. Then escalate:

| Condition | overall_risk |
|-----------|-------------|
| `risk_flags` is non-empty (any string other than `""`) | `high` |
| `medication_count` >= 5 | `high` |
| `chronic_conditions` contains 3+ comma-separated conditions | `high` |
| `recent_hospitalization` is 1 | `high` |
| None of the above | Same as `lifestyle_risk` |

The `overall_risk_high` blocked reason code is added whenever overall_risk is `high`.

### Other blocked reason codes

| API condition | Code |
|---------------|------|
| `emergency_contact_present` is 0 | `emergency_contact_missing` |
| `address` is null | `missing_address` |
| `email` is null AND `preferred_contact` is `email` | `preferred_contact_unavailable` |
| `phone` is null AND `preferred_contact` is `phone` | `preferred_contact_unavailable` |
| `phone` is null AND `preferred_contact` is `sms` | `preferred_contact_unavailable` |
| `email` is null AND `preferred_contact` is `portal` | `preferred_contact_unavailable` |

### Determining registration_status

| blocked_reason_codes contains... | registration_status |
|----------------------------------|---------------------|
| `coverage_expired` OR `excluded_service_line` | `rejected` |
| `overall_risk_high` AND any other blocked code | `clinical_review` |
| `overall_risk_high` only (no other codes) | `clinical_review` |
| Any blocked code (but not rejected-level) | `hold` |
| No blocked codes | `approved` |

---

## Operation Type 2: Referral Readiness Audit

This operation evaluates referrals in a batch for scheduling readiness.

### Per-referral checks

#### ICD chapter mismatch

For each referral, fetch the ICD metadata at `/icd/<code>`. Compare the ICD
`service_family` to the referral's `service_line`:

- If they do NOT match, flag `icd_chapter_mismatch`.
- The `observed_chapter` is the chapter from the ICD metadata.
- The `expected_chapter` is the chapter range that maps to the referral's `service_line`.

Service line to expected ICD chapter mapping:
- `orthopedics` -> `M00-M99`
- `pulmonary` -> `J00-J99`
- `cardiology` -> `I00-I99`

#### Narrative/laterality mismatch

Check the ICD code description against the referral's narrative fields:
- If the ICD `laterality` value conflicts with what the `diagnosis_description` or `referral_reason` implies, flag `laterality_mismatch`.
- If the `referral_reason` is inconsistent with the ICD code's purpose, flag `narrative_mismatch`.

Only flag these when a specific inconsistency is evident from the data.

#### Already scheduled

If `appointment_scheduled` is 1, flag `already_scheduled`.

#### Authorization blockers

| auth_required | auth_status | Action |
|---------------|-------------|--------|
| 1 | denied | Flag `auth_blocker` |
| 1 | pending | Flag `auth_blocker` |
| 1 | not_required | No block |
| 0 | any | No block |
| 1 | approved | No block |

#### Missing records/imaging

| Condition | Flag |
|-----------|------|
| `records_received` is 0 | `missing_records` |
| `imaging_received` is 0 | `missing_imaging` |

#### Duplicate detection

Two referrals are duplicates when they share the same `patient_id` AND the same
`icd10_code`, and additionally exhibit one of: notes mentioning "duplicate" or
"possible duplicate", or the same `referring_fax`/`referring_phone` from
different practices. The referral with the lower referral_id is the primary.

Flag with `duplicate_referral` on both. The primary gets `consolidate_to_primary`
recommendation.

#### Shared insurance anomaly

Two referrals from different patients sharing the same `insurance_id` is an
anomaly. Flag both with `shared_insurance_anomaly`. Disposition is
`verify_distinct_patient_policy_id`.

If the same patient shares the insurance_id across referrals, disposition is
`legitimate_duplicate_same_patient`.

### Determining readiness_status

| Condition | readiness_status |
|-----------|-----------------|
| No issues at all | `ready` |
| Any `auth_blocker`, `missing_records`, or `missing_imaging` | `blocked` |
| `already_scheduled` present (without blocked-level) | `under_review` |
| `icd_chapter_mismatch`, `duplicate_referral`, `narrative_mismatch`, `laterality_mismatch` (without blocked-level) | `under_review` |
| `shared_insurance_anomaly` only (no other issues) | `admin_followup` |

### Determining priority_tier

| urgency value | priority_tier |
|---------------|---------------|
| `urgent` | `tier_1_immediate` |
| `routine` | `tier_2_short_term` |
| `admin` | `tier_3_administrative` |

### Action plan codes

| Issue | Action code |
|-------|-------------|
| `icd_chapter_mismatch` | `request_corrected_icd` |
| `narrative_mismatch` | `confirm_narrative` |
| `laterality_mismatch` | `confirm_laterality` |
| `duplicate_referral` | `consolidate_duplicate` |
| `shared_insurance_anomaly` | `verify_insurance_id` |
| `missing_records` | `request_records` |
| `missing_imaging` | `request_imaging` |
| `auth_blocker` | `resolve_authorization` |
| `already_scheduled` | `review_existing_appointment` |

---

## Operation Type 3: Dialysis Transfer Review

This operation evaluates seasonal dialysis transfer packets for intake readiness.

### Packet completeness

The required documents for a complete dialysis transfer packet are:
`allergy_list`, `face_sheet`, `flu_vaccine`, `hbsag`, `hep_b_antibody_core`,
`history_physical`, `insurance_proof`, `medication_list`, `monthly_labs`,
`physician_orders`, `pneumonia_vaccine`, `ppd_or_cxr`, `transportation`,
`treatment_flowsheets`, `vascular_access_report`.

For each transfer, check the patient's `documents` array for documents linked
to that transfer (matching `transfer_id`). Any required document type not present
is missing. List missing documents alphabetically.

If any required document is missing, `packet_completeness_status` is `incomplete`;
otherwise `complete`.

### Stale documents

Documents with temporal validity windows. Check each document's `received_date`
against the current date in the environment:

| doc_type | freshness_limit_days |
|----------|---------------------|
| `hbsag` | 30 |
| `hep_b_antibody_core` | 365 |
| `history_physical` | 365 |
| `monthly_labs` | 30 |
| `ppd_or_cxr` | 30 |

A document is stale if `current_date - received_date > freshness_limit_days`.
List stale documents alphabetically by doc_type.

### Capacity and feasibility

Cedar Ridge has limited in-center hemodialysis chairs. The portal supplies
capacity data (open chairs count). Check each transfer's requested start date
against available capacity on that date (capacity is shared across all
transfers in the batch; dates with chairs available are `available`, those with
0 are `unavailable`).

| Condition | feasibility |
|-----------|------------|
| Packet complete AND capacity available on requested date | `ready_on_requested_start` |
| Packet incomplete AND capacity available | `packet_not_ready_capacity_available` |
| Packet incomplete AND capacity unavailable | `packet_not_ready_capacity_unavailable` |
| Packet complete AND capacity unavailable | `capacity_unavailable` |

### Final intake decision

| Condition | decision |
|-----------|----------|
| `feasibility` is `ready_on_requested_start` | `accept` |
| `feasibility` is `capacity_unavailable` | `hold` |
| All other cases | `clinical_review` |

### Next contact

| Condition | next_contact_owner | next_contact_route |
|-----------|-------------------|--------------------|
| `decision` is `clinical_review` | `clinical_nurse` | `fax_referring_facility` |
| `decision` is `hold` | `scheduling_coordinator` | `phone_patient` |
| `decision` is `accept` | `intake_coordinator` | `internal_queue` |

---

## Operation Type 4: Chronic-Care Enrollment Panel

This operation evaluates program candidates for enrollment in a chronic-care
management program (such as DMHTN-2026A).

### Eligibility

A candidate is eligible (`eligible: true`) when:
- `target_condition` matches the program's target condition (for DMHTN-2026A: `diabetes_hypertension`)
- At least one coverage record has `status` `active` (check `/patients/<id>`)

If the target condition does NOT match, the patient is ineligible.
Add `wrong_target_condition` and `missing_active_dmhtn_diagnosis`.

### Enrollment status

| Condition | enrollment_status |
|-----------|-------------------|
| Eligible AND `consent_status` is `signed` AND chart is active | `enroll` |
| Eligible AND `consent_status` is `signed` BUT chart not active OR has stale/missing artifacts | `hold` |
| Eligible AND `consent_status` is `missing` | `hold` |
| `consent_status` is `declined` | `reject` |
| Not eligible | `reject` |

### Chart activation checks

A chart is active when:
- `existing_chart` is 1 on the candidate record
- `/chart/<patient_id>` returns artifacts that are current (not stale, not empty)

Missing chart artifacts are determined by which expected artifact types are
absent or stale. Check: `chart_record`, `active_problems`, `vitals`, `labs`,
`medications`, `consent`.

### Reason codes

| Condition | Code |
|-----------|------|
| `target_condition` matches program | `meets_dmhtn_criteria` |
| `recent_hospitalization` is 1 (from clinical_history) | `recent_hospitalization_high_touch` |
| `adherence_score` < 50 | `low_adherence_high_touch` |
| Chronic conditions string contains `ckd` | `ckd_biweekly_monitoring` |
| `recent_hospitalization` is 1 OR risk_flags suggest ED visit | `recent_ed_high_touch` |
| `consent_status` is `declined` | `consent_declined` |
| `consent_status` is `missing` | `consent_missing` |
| `existing_chart` is 0 OR chart has no artifacts | `chart_not_active` |
| Active problems have `last_updated` older than 90 days | `stale_active_problems` |
| Vitals missing from chart artifacts | `missing_recent_vitals` |
| Labs missing from chart artifacts | `missing_recent_labs` |
| Medications missing from chart artifacts | `missing_medication_list` |
| `target_condition` does NOT match program | `wrong_target_condition` |
| No active DMHTN diagnosis in chart problems | `missing_active_dmhtn_diagnosis` |

### Follow-up cadence

| Condition | cadence |
|-----------|---------|
| High-touch reason codes present (recent_hospitalization_high_touch, low_adherence_high_touch, recent_ed_high_touch) | `weekly` |
| `ckd_biweekly_monitoring` present AND no high-touch codes | `biweekly` |
| Eligible, no special flags | `monthly` |
| Chart not active / consent missing (hold) | `deferred` |
| Rejected / not eligible | `none` |

### Outreach channel

Use the candidate's `preferred_outreach` field directly:
- `portal` -> `portal`
- `phone` -> `phone`
- `sms` -> `sms`
- `email` -> `email`

If rejected (enrollment_status is `reject`), use `none`.

### Initial monitoring package

| enrollment_status + flags | package_type | components | first_checkin_days |
|---------------------------|-------------|------------|-------------------|
| `enroll` + high-touch | `high_touch_dm_htn` | bp_cuff, glucometer, lab_order_a1c_cmp_lipid, medication_reconciliation, care_plan_setup | 7 |
| `enroll` + no high-touch | `standard_dm_htn` | bp_cuff, glucometer, lab_order_a1c_cmp_lipid, medication_reconciliation | 14 (biweekly) or 30 (monthly) |
| `hold` | `deferred` | consent_packet, chart_update_request | null |
| `reject` | `not_applicable` | (empty array) | null |

---

## Operation Type 5: Referral-to-Chart Activation

This operation reconciles referrals in a pulmonary batch to determine which
can proceed to chart activation.

### Per-referral checks

Same core checks as Operation Type 2 (referral audit), plus chart-specific
evaluation.

#### Clinical code discrepancy

ICD `service_family` mismatch with referral `service_line`:
- Pulmonary referrals expect codes whose service_family is `pulmonary` (J chapter).
- Codes from `cardiology` (I chapter), `symptoms` (R chapter), or other non-pulmonary
  families on a pulmonary referral are discrepancies.

Flag with `clinical_code_discrepancy`. Add to `clinical_code_discrepancy_referrals`.

#### Authorization, records, imaging blockers

Same as Operation Type 2. Flag `authorization_blocked`, `records_missing`,
`imaging_missing` respectively.

#### Duplicate handling

Same detection logic as Operation Type 2. Both referrals in a duplicate pair get
`duplicate_review` blocker. After review, cleared duplicates may be marked in
`cleared_duplicate_review_referrals`.

#### Scheduled before clearance

If `appointment_scheduled` is 1 AND any other issue exists, flag
`scheduled_before_clearance`. If `appointment_scheduled` is 1 but no other
issues, treat as ready (this is an anomaly but the referral can proceed).

### Readiness status

| Condition | readiness_status |
|-----------|-----------------|
| No issues at all | `ready` |
| `authorization_blocked`, `records_missing`, or `imaging_missing` present | `blocked` |
| `clinical_code_discrepancy` only | `under_review` |
| `duplicate_review` present (and no blocked-level) | `under_review` |
| `scheduled_before_clearance` + other issues | `blocked` |

### Chart needs for ready referrals

For referrals with `readiness_status` `ready`, determine what chart artifacts
are missing by examining the patient record and `/chart/<patient_id>`:

| Chart action | Condition |
|-------------|-----------|
| `create_chart` | Patient has `existing_chart` 0 AND no chart artifacts |
| `update_chart` | Patient has a chart but some expected artifacts are missing |
| `no_chart_action` | All required artifacts present |

Artifacts to create are all missing artifact types from the expected set:
`demographics`, `active_problems`, `medications`, `allergies`, `vitals`, `labs`,
`consent`. List them alphabetically.

### Correspondence queue

| Blocker / issue | template_type | reason_codes |
|-----------------|--------------|--------------|
| `clinical_code_discrepancy` with wrong service_family | `clinical_code_clarification` | `wrong_service_family` |
| `clinical_code_discrepancy` with clinical reason mismatch | `clinical_code_clarification` | `clinical_reason_mismatch` |
| `authorization_blocked` OR `records_missing` | `auth_records_request` | `authorization_denied` and/or `records_missing` |
| `duplicate_review` | `duplicate_resolution` | `duplicate_review` |
| `scheduled_before_clearance` | `appointment_hold_notice` | `appointment_already_scheduled` plus any co-occurring codes |

### Priority order

Rank non-ready referrals by urgency then by severity:
1. `tier_1_immediate` first (urgent referrals with discrepancies)
2. `tier_2_short_term` next (routine referrals with blocked-level issues)
3. `tier_3_administrative` last

Within each tier, order ascending by referral_id.
Assign rank integers starting from 1.
