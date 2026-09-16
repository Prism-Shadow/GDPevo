# Cedar Ridge Business Rules by Task Type

Read the section matching your task. Apply rules patient-by-patient or referral-by-referral, then compute the cohort summary from your own decisions.

---

## 1. New Patient Access Verification

**Input:** Roster ID, list of patient IDs, service line, requested service date.

### 1.1 Insurance Status

Query `coverage` for each patient. Determine `insurance_status`:

- **valid**: coverage.status is `"active"` AND the target `service_line` appears in coverage.service_lines (comma-separated).
- **invalid**: coverage.status is `"expired"`, `"pending"`, or the target service_line is NOT in coverage.service_lines.
- **missing**: no coverage record for the patient.

Blocked reason codes from insurance:
- `coverage_expired`: coverage.status is `"expired"`.
- `coverage_pending`: coverage.status is `"pending"`.
- `excluded_service_line`: coverage is active but target service_line is missing from coverage.service_lines.

### 1.2 Prescription (PBM) Status

Query `pbm` for each patient. Determine `prescription_status`:

- **valid**: pbm.status is `"approved"` AND pbm.active = 1 AND pbm.policy_number matches coverage.policy_number.
- **invalid**: pbm.status is not `"approved"`, or pbm.active = 0, or pbm.policy_number does not match coverage.policy_number.
- **missing**: no pbm record for the patient.

Blocked reason codes from PBM:
- `pbm_invalid`: pbm.status is `"rejected"` or `"pending"`, or pbm.active = 0.
- `pbm_missing`: no pbm record exists.
- `pbm_policy_mismatch`: pbm.policy_number != coverage.policy_number.

### 1.3 Pharmacy Network Status

Query `patient_pharmacy` (where preference_rank = 1 for each patient) and join to `pharmacies`. Determine `pharmacy_status`:

- **in_network**: the preferred pharmacy's network_status is `"in_network"`.
- **out_of_network**: the preferred pharmacy's network_status is `"out_of_network"`.
- **unknown**: no pharmacy record for the patient.

Blocked reason codes:
- `pharmacy_out_of_network`: pharmacy is out_of_network.
- `pharmacy_unknown`: no pharmacy record.

### 1.4 Lifestyle Risk

Query `lifestyle` for each patient. Determine `lifestyle_risk`:

- **high**: Any of these conditions is true:
  - `smoking_status` is `"Current"`
  - `alcohol_use` is `"Heavy"`
  - `exercise_frequency` is NULL or `"None"`
  - `sleep_hours` < 6
- **medium**: Not high, and not low.
- **low**: `smoking_status` is `"Never"`, `alcohol_use` is `"None"` or `"Occasional"`, `exercise_frequency` is `"3-4"` or `"5+"`, and `sleep_hours` >= 7.

### 1.5 Overall Risk

Query `clinical_history` for each patient. Determine `overall_risk`:

- **high**: Any of: `risk_flags` is non-empty, `chronic_conditions` lists multiple conditions, `medication_count` >= 5, `recent_hospitalization` = 1, or `allergy_count` >= 3.
- **medium**: Some chronic conditions or medications but no high-risk flags.
- **low**: No chronic conditions, no risk_flags, low medication/allergy counts.

Blocked reason code: `overall_risk_high` when overall_risk is `"high"`.

### 1.6 Patient-Level Blockers

Query `patients` for each patient. Check these additional blockers:

- `missing_address`: patient.address IS NULL.
- `emergency_contact_missing`: patient.emergency_contact_present = 0.
- `preferred_contact_unavailable`: patient.preferred_contact is `"email"` but email IS NULL, or preferred_contact is `"phone"` / `"sms"` but phone IS NULL.

### 1.7 Registration Status

Determine `registration_status` from all blocked_reason_codes:

- **rejected**: ANY of `coverage_expired` or `excluded_service_line` is present (hard insurance blockers).
- **clinical_review**: Any blocked_reason_codes exist but none of the hard-rejection codes are present. Also includes `coverage_pending` and `overall_risk_high`.
- **hold**: Minor admin issues only (e.g. missing_address, preferred_contact_unavailable) with no clinical concerns and coverage is active+valid. Only use when coverage is valid and overall_risk is not high.
- **approved**: No blocked_reason_codes at all. Coverage valid, PBM valid, pharmacy in_network, no risk flags, all contact info present.

### 1.8 Cohort Summary

Count each category from your patient_results rows. All counts must be integers that sum to total_patients.

---

## 2. Referral Audit (Orthopedic, Pulmonary, General)

**Input:** Batch ID.

### 2.1 Fetch All Referrals

Get all referrals for the batch via REST or SQL. For each referral, also fetch its ICD metadata (`/icd/{code}`) and patient info.

### 2.2 ICD Discrepancy

For each referral, compare the ICD code's `service_family` (from `/icd/{code}`) against the referral's `service_line`. Also compare `chapter` against the expected chapter for the service line:

| Service Line | Expected Chapter |
|-------------|-----------------|
| orthopedics | M00-M99 |
| pulmonary | J00-J99 |
| cardiology | I00-I99 |
| neurology | G00-G99 |
| dermatology | L00-L99 |

If the ICD chapter does not match the expected chapter for the referral's service_line, flag `icd_chapter_mismatch`. Set `observed_chapter` to the ICD's actual chapter and `expected_chapter` to what the service_line expects.

Also check `narrative_mismatch` (or `clinical_reason_mismatch`): when the referral_reason text (e.g. "pain evaluation") does not logically match the ICD description (e.g. a respiratory-code referral with a pain reason).

Also check `laterality_mismatch`: when the ICD code has laterality (left/right) but the referral narrative references the opposite side.

### 2.3 Duplicate Detection

Two referrals are duplicates when they share the same `patient_id` AND the same `icd10_code`. Portal signals include: `notes` = `"possible duplicate"`, `assigned_physician` containing text like `"duplicate faxed by second practice"`, or anomalous `referring_practice` names.

For each duplicate group:
- `recommendation`: `"consolidate_to_primary"` (keep the referral with the lower referral_id as primary).
- The primary referral absorbs the duplicate; the duplicate gets issue_code `duplicate_referral`.

### 2.4 Shared Insurance Anomaly

Multiple referrals sharing the same `insurance_id` but belonging to different `patient_id` values → shared_insurance_anomaly.
- `disposition`: `"verify_distinct_patient_policy_id"` (different patients should not share an insurance policy ID).
- If the same patient has multiple referrals with the same insurance → `"legitimate_duplicate_same_patient"`.

### 2.5 Missing Records / Imaging

- `missing_records`: referral.records_received = 0.
- `missing_imaging`: referral.imaging_received = 0.

### 2.6 Authorization Blockers

A referral has `auth_blocker` when `auth_required` = 1 AND `auth_status` is NOT `"approved"` or `"not_required"`. Specifically:
- `auth_status` = `"denied"` → blocker.
- `auth_status` = `"pending"` → blocker.
- `auth_status` = `"not_submitted"` → blocker.

### 2.7 Already Scheduled

A referral already has an appointment: `appointment_scheduled` = 1. Issue code: `already_scheduled`.

### 2.8 Readiness Status

Determine per referral from its issue_codes:

- **blocked**: ANY of `auth_blocker`, `missing_records`, or `missing_imaging` is present (hard blockers — cannot proceed).
- **under_review**: No hard blockers, but at least one of `icd_chapter_mismatch`, `narrative_mismatch`, `duplicate_referral`, `already_scheduled`, or `shared_insurance_anomaly` is present (needs clinical/admin review).
- **admin_followup**: Only `shared_insurance_anomaly` is present with no other issues.
- **ready**: No issue_codes at all.

### 2.9 Priority Tier

- **tier_1_immediate**: urgency is `"urgent"` AND readiness_status is `"under_review"`.
- **tier_2_short_term**: urgency is `"routine"` AND readiness_status is `"blocked"` or `"under_review"`.
- **tier_3_administrative**: readiness_status is `"admin_followup"`.
- **null**: readiness_status is `"ready"` (no action needed).

### 2.10 Action Codes

Map issue_codes to action_codes:

| Issue Code | Action Code |
|-----------|------------|
| icd_chapter_mismatch | request_corrected_icd |
| narrative_mismatch | confirm_narrative |
| laterality_mismatch | confirm_laterality |
| duplicate_referral | consolidate_duplicate |
| shared_insurance_anomaly | verify_insurance_id |
| missing_records | request_records |
| missing_imaging | request_imaging |
| auth_blocker | resolve_authorization |
| already_scheduled | review_existing_appointment |

### 2.11 Ready to Schedule

Referrals with readiness_status = `"ready"` and no blockers.

### 2.12 Summary Counts

- `counts_by_urgency`: urgent, routine, admin counts from referral.urgency.
- `counts_by_readiness_status`: ready, blocked, under_review, admin_followup.
- `counts_by_urgency_and_status`: cross-tabulation. Omit zero-count rows. Sort by urgency then readiness_status.
- `issue_counts`:
  - `icd_discrepancy_referrals`: count of referrals with icd_chapter_mismatch.
  - `duplicate_groups`: count of duplicate_groups.
  - `shared_insurance_anomalies`: count of shared_insurance_anomalies entries.
  - `missing_records_referrals`: count in blocker_sets.missing_records.
  - `missing_imaging_referrals`: count in blocker_sets.missing_imaging.
  - `auth_blocker_referrals`: count in blocker_sets.auth_blockers.

---

## 3. Dialysis Transfer Review

**Input:** Transfer batch ID.

### 3.1 Required Document Types

The 15 required documents for a complete dialysis transfer packet:

allergy_list, face_sheet, flu_vaccine, hbsag, hep_b_antibody_core, history_physical, insurance_proof, medication_list, monthly_labs, physician_orders, pneumonia_vaccine, ppd_or_cxr, transportation, treatment_flowsheets, vascular_access_report.

### 3.2 Packet Completeness

Query `documents` by `transfer_id` for each transfer. A document is "present" only when `finalized` = 1 (status = `"final"`). Documents with `finalized` = 0 (status = `"draft"`) count as missing.

- **complete**: All 15 doc_types present with finalized=1.
- **incomplete**: Any required doc_type missing or finalized=0.

`missing_required_documents`: list of doc_type codes that are absent or have finalized=0. Sort alphabetically.

### 3.3 Document Staleness (Freshness)

Five document types have freshness limits. For each of these that exists with finalized=1, check if the document is stale: `received_date` + `freshness_limit_days` is before `requested_start_date`.

| Doc Type | Freshness Limit (days) |
|----------|----------------------|
| hbsag | 30 |
| hep_b_antibody_core | 30 |
| history_physical | 365 |
| monthly_labs | 30 |
| ppd_or_cxr | 30 |

`stale_documents` lists only stale documents (not all five). Include `doc_type`, `received_date`, and `freshness_limit_days`. Sort alphabetically by doc_type.

### 3.4 Capacity Check

Query `facility_capacity` for the patient's `requested_start_date`. Sum `open_chairs` across all locations (CRIC-MAIN + CRIC-NORTH) for that date. If the date has no rows in facility_capacity, open_chairs_total = 0 and capacity_status = `"unavailable"`.

- **available**: open_chairs_total > 0.
- **unavailable**: open_chairs_total = 0.

### 3.5 Feasibility

Combine packet completeness and capacity:

- **ready_on_requested_start**: packet is complete AND capacity is available AND no stale documents.
- **packet_not_ready_capacity_available**: packet incomplete OR stale docs present, AND capacity available.
- **packet_not_ready_capacity_unavailable**: packet incomplete OR stale docs present, AND capacity unavailable.
- **capacity_unavailable**: packet is complete AND no stale docs, BUT capacity unavailable.

### 3.6 Final Intake Decision

- **accept**: packet is complete, no stale documents, AND capacity is available.
- **hold**: packet is complete AND no stale docs, BUT capacity unavailable.
- **clinical_review**: packet is incomplete, OR has stale documents, OR both.

### 3.7 Next Contact

- **owner**: `"clinical_nurse"` when decision is `"clinical_review"`; `"scheduling_coordinator"` when decision is `"hold"`; `"intake_coordinator"` when decision is `"accept"`; `"none"` otherwise.
- **route**: `"fax_referring_facility"` when packet is incomplete or has stale docs (need documents from referring facility); `"phone_patient"` when capacity is the only issue; `"internal_queue"` for scheduling; `"none"` for accepted transfers with no issues.

### 3.8 Cohort Summary

- `complete_documents_count`: count of transfers with packet_completeness_status = `"complete"`.
- `missing_document_patient_count`: count with at least one missing_required_document.
- `stale_document_patient_count`: count with at least one stale_document.
- `capacity_available_count`: count with capacity_status = `"available"`.
- `requested_start_ready_count`: count with feasibility = `"ready_on_requested_start"`.
- `decision_counts`: accept, hold, clinical_review counts.
- `next_contact_owner_counts`: clinical_nurse, intake_coordinator, scheduling_coordinator, none.

---

## 4. Chronic-Care Enrollment Panel

**Input:** Program code (e.g. DMHTN-2026A).

### 4.1 Candidate Eligibility

Fetch candidates from `/programs/{program_code}/candidates`. DMHTN targets diabetes and hypertension. Determine eligibility:

- **eligible (true)**: candidate.target_condition is `"diabetes_hypertension"`.
- **eligible (false)**: candidate.target_condition is anything else (e.g. `"copd"`).

Reason codes for ineligible:
- `wrong_target_condition`: target_condition does not match the program.
- `missing_active_dmhtn_diagnosis`: always paired with wrong_target_condition.

### 4.2 Chart Audit

For each eligible candidate, fetch `/chart/{patient_id}` or query `chart_artifacts`. Inspect:

- **existing_chart**: from candidate or chart. `chart_not_active` if existing_chart = 0.
- **chart_artifacts**: check status field. `"stale"` → artifact needs updating.
- **consent**: candidate.consent_status. `consent_declined` or `consent_missing`.

Missing chart artifacts: any of the seven tracked types (demographics, active_problems, vitals, labs, medications, allergies, consent) that either have no record or have status = `"stale"`.

Reason codes:
- `chart_not_active`: existing_chart = 0.
- `stale_active_problems`: active_problems artifact status = `"stale"`.
- `missing_recent_vitals`: no vitals artifact.
- `missing_recent_labs`: no labs artifact.
- `missing_medication_list`: no medications artifact.
- `consent_declined`: consent_status = `"declined"`.
- `consent_missing`: consent_status = `"missing"`.
- `meets_dmhtn_criteria`: eligible = true.
- `recent_hospitalization_high_touch`: clinical_history.recent_hospitalization = 1.
- `low_adherence_high_touch`: candidate.adherence_score < 50.
- `ckd_biweekly_monitoring`: chronic_conditions contains `"ckd"`.
- `recent_ed_high_touch`: recent emergency department visit (check clinical_history for ED flags).

### 4.3 Enrollment Status

- **enroll**: eligible AND consent = `"signed"` AND existing_chart = 1 AND chart artifacts are current (no stale, no missing).
- **hold**: eligible AND (consent = `"missing"` OR existing_chart = 0 OR stale/missing artifacts) — but consent is not `"declined"`.
- **reject**: consent = `"declined"` OR eligible = false.

### 4.4 Follow-Up Cadence

- **weekly**: has `recent_hospitalization_high_touch` OR `low_adherence_high_touch` OR `recent_ed_high_touch`.
- **biweekly**: has `ckd_biweekly_monitoring` (and no high-touch flags).
- **monthly**: standard enrollment, no special triggers.
- **deferred**: enrollment_status = `"hold"`.
- **none**: enrollment_status = `"reject"`.

### 4.5 Missing Chart Artifacts

List artifacts that are missing or stale:
- `chart_record`: existing_chart = 0.
- `active_problems`: no active_problems artifact or status = `"stale"`.
- `vitals`: no vitals artifact.
- `labs`: no labs artifact.
- `medications`: no medications artifact.
- `consent`: consent is missing or declined (or no consent artifact).

### 4.6 Outreach Channel

Default to candidate.preferred_outreach. May need to fall back to an available channel if the preferred channel is unavailable (e.g. preferred is `"email"` but email is null → fall back to `"phone"` if phone is non-null, or `"sms"` if phone is non-null and email is null, or `"portal"`).

### 4.7 Initial Monitoring Package

- **high_touch_dm_htn**: enrollment_status = `"enroll"` AND (recent_hospitalization OR low_adherence OR recent_ed).
  - components: `bp_cuff`, `glucometer`, `lab_order_a1c_cmp_lipid`, `medication_reconciliation`, `care_plan_setup`
  - first_checkin_days: 7
- **standard_dm_htn**: enrollment_status = `"enroll"` AND no high-touch triggers.
  - With ckd: components = `bp_cuff`, `glucometer`, `lab_order_a1c_cmp_lipid`, `medication_reconciliation`; first_checkin_days = 14
  - Without ckd: components = `bp_cuff`, `glucometer`, `lab_order_a1c_cmp_lipid`; first_checkin_days = 30
- **deferred**: enrollment_status = `"hold"`.
  - components: `consent_packet`, `chart_update_request`
  - first_checkin_days: null
- **not_applicable**: enrollment_status = `"reject"`.
  - components: []
  - first_checkin_days: null

### 4.8 Summary Counts

All integer counts that reconcile with patient rows:
- eligible_count + ineligible_count = total_candidates
- status_counts, follow_up_counts, outreach_counts, monitoring_package_counts all sum to total_candidates.

---

## 5. Pulmonary Referral-to-Chart Activation

**Input:** Batch ID (pulmonary service line).

### 5.1 Referral Readiness

For each referral in the batch, determine readiness_status:

- **ready**: No blockers. auth_status is `"approved"` or `"not_required"`, records_received = 1, imaging_received = 1, no ICD discrepancy, no duplicate issue, no scheduled appointment before clearance.
- **blocked**: ANY of: auth_status is `"denied"` or `"pending"` (with auth_required=1), records_received = 0, imaging_received = 0.
- **under_review**: ICD chapter mismatch or narrative/reason mismatch, but no hard blockers.

Blockers:
- `authorization_blocked`: auth_required=1 AND auth_status != `"approved"`.
- `records_missing`: records_received = 0.
- `imaging_missing`: imaging_received = 0.
- `clinical_code_discrepancy`: ICD chapter mismatch or narrative mismatch. Check `/icd/{code}`:
  - Chapter mismatch: ICD chapter is not J00-J99 for a pulmonary referral.
  - Narrative mismatch: referral_reason does not logically fit the ICD diagnosis (e.g. "pain evaluation" for a respiratory code).
- `scheduled_before_clearance`: appointment_scheduled = 1.
- `duplicate_review`: notes = `"possible duplicate"`.

### 5.2 Duplicate Handling

For referrals with `notes` = `"possible duplicate"`, check if they share patient_id AND icd10_code with another referral in the batch:
- If yes: create a duplicate_group with group_id, referral_ids, and keep_referral_id (lowest referral_id).
- If no: add to `cleared_duplicate_review_referrals` (flagged but no actual duplicate found).

### 5.3 Blocker Sets

- `authorization`: list of referral_ids with authorization_blocked.
- `records`: list with records_missing.
- `imaging`: list with imaging_missing.

### 5.4 Clinical Code Discrepancy Referrals

List of referral_ids with clinical_code_discrepancy. Sorted ascending.

### 5.5 Ready Referral Chart Needs

For each ready referral, inspect the patient's chart via `/chart/{patient_id}`:

- **chart_action**:
  - `"create_chart"`: existing_chart = 0.
  - `"update_chart"`: existing_chart = 1 but some artifacts are stale or missing.
  - `"no_chart_action"`: all artifacts present and current.
- **artifacts_to_create**: The set of artifact types that are either missing (no record) or stale (status = `"stale"`). Sorted alphabetically. The seven tracked artifact types are: demographics, active_problems, medications, allergies, vitals, labs, consent.

### 5.6 Correspondence Queue

For each non-ready referral, determine template_type and reason_codes:

| Blocker | Template Type | Reason Codes |
|---------|-------------|-------------|
| clinical_code_discrepancy (chapter) | clinical_code_clarification | wrong_service_family |
| clinical_code_discrepancy (narrative) | clinical_code_clarification | clinical_reason_mismatch |
| authorization_blocked + records_missing | auth_records_request | authorization_denied, records_missing |
| authorization_blocked only | auth_records_request | authorization_denied |
| scheduled_before_clearance (+ other blockers) | appointment_hold_notice | appointment_already_scheduled + any other reason codes |
| duplicate_review | duplicate_resolution | duplicate_review |

### 5.7 Priority Order

Rank non-ready referrals by priority (highest first):
1. urgency = `"urgent"` referrals (tier_1_immediate).
2. urgency = `"routine"` referrals sorted by severity: blocked before under_review (tier_2_short_term).

Within the same tier, sort by referral_id ascending. Assign rank starting at 1.

### 5.8 Correspondence Reason Code Mapping

| Condition | Reason Code |
|-----------|------------|
| ICD chapter doesn't match service line | wrong_service_family |
| Referral reason doesn't match ICD description | clinical_reason_mismatch |
| records_received = 0 | records_missing |
| auth_status = denied | authorization_denied |
| notes = possible duplicate (actual duplicate) | duplicate_review |
| appointment_scheduled = 1 | appointment_already_scheduled |

---

## Cross-Cutting Rules

### ID Ordering

All patient/referral/transfer lists are sorted ascending by their ID (P001 < P002, REF0001 < REF0002, TR0001 < TR0002).

### Code Sets

Arrays like blocked_reason_codes, issue_codes, reason_codes, missing_chart_artifacts, components, and action_codes are unordered sets. Order of elements within these arrays is not meaningful.

### Enum Discipline

Use only values from the template's allowed_values lists. Never invent new enum values.

### Summary Reconciliation

Every integer in a cohort summary must match what you produced in the per-row sections. If count mismatches occur, fix the rows, not the summary.
