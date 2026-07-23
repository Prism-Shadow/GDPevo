# Cedar Ridge Intake — Decision Rules by Work Family

Reusable rules distilled from the training tasks. Apply to any task of the same family. **Do not copy per-record results from training** — recompute from the live portal data using these rules. Rules marked *(inferred rubric)* were distilled from training evidence rather than read verbatim from the portal; apply them consistently.

---

## A. Patient Access Verification (roster, e.g. `NPI-*`)

Target: a roster id + patient list + `service_line` + `requested_service_date` (from `intake_rosters`). Per patient produce `insurance_status`, `prescription_status`, `pharmacy_status`, `lifestyle_risk`, `overall_risk`, `registration_status`, `blocked_reason_codes`; plus `cohort_summary`.

### insurance_status (valid / invalid / missing) — from `coverage`
- `missing`: no coverage row for the patient.
- `invalid`: `status != 'active'` OR `network_status != 'in_network'`.
- `valid`: `status='active'` AND `network_status='in_network'`.
- (Service-line coverage is a separate blocker, not part of validity.)

### prescription_status (valid / invalid / missing) — from `pbm`
- `missing`: no pbm row.
- `invalid`: `active != 1` OR `status != 'approved'` OR `formulary_status != 'covered'`.
- `valid`: `active=1` AND `status='approved'` AND `formulary_status='covered'`.
- A policy-number mismatch (`pbm.policy_number != coverage.policy_number`) does not by itself change `prescription_status`; it produces the `pbm_policy_mismatch` blocker.

### pharmacy_status (in_network / out_of_network / unknown) — from `patient_pharmacy`+`pharmacies`
- Take the preferred pharmacy (`preference_rank=1`).
- `in_network` if its `network_status='in_network'`; `out_of_network` if `out_of_network`; `unknown` if no preferred pharmacy row.

### lifestyle_risk (low / medium / high) *(inferred rubric)*
Point score over `lifestyle`:
- `smoking_status`: Current=2, Former=0, Never=0
- `alcohol_use`: Heavy=2, Moderate=1, Occasional=0, None=0
- `exercise_frequency`: None=2, null=1, `1-2`=1, `3-4`=0, `5+`=0
- `sleep_hours`: <5 or >9 ⇒2; <6 or >8 ⇒1; else 0
Sum: 0–1 ⇒ low, 2–3 ⇒ medium, ≥4 ⇒ high.

### clinical_risk (low / medium / high) *(inferred rubric)* — from `clinical_history`
- `high` if `recent_hospitalization=1` OR `risk_flags` non-empty.
- else `high` if ≥4 chronic conditions OR `medication_count≥8`; `medium` if ≥3 chronic conditions OR `medication_count≥6` OR ≥1 chronic condition; else `low`.
- (Any non-empty `risk_flags` ⇒ high; e.g. `complex_medication_reconciliation`.)

### overall_risk = max(lifestyle_risk, clinical_risk) *(inferred rubric)*

### blocked_reason_codes (set; emit each that applies)
- `coverage_expired`: `coverage.status='expired'`
- `coverage_pending`: `coverage.status='pending'`
- `excluded_service_line`: roster `service_line` NOT in `coverage.service_lines` (split on comma)
- `pbm_missing`: no pbm row
- `pbm_invalid`: pbm row present but not active/approved/covered
- `pbm_policy_mismatch`: `pbm.policy_number != coverage.policy_number`
- `pharmacy_out_of_network`: preferred pharmacy `out_of_network`
- `pharmacy_unknown`: no preferred pharmacy
- `missing_address`: `patients.address` is null
- `preferred_contact_unavailable`: the `preferred_contact` channel has no value (`email`⇒email null; `phone`/`sms`⇒phone null; `portal`⇒email null)
- `emergency_contact_missing`: `emergency_contact_present=0`
- `overall_risk_high`: `overall_risk='high'`

### registration_status (precedence top-down)
1. `rejected` if any hard blocker: `coverage_expired` OR `excluded_service_line` OR `pbm_missing`.
2. `clinical_review` if `overall_risk='high'` OR `risk_flags` non-empty.
3. `hold` if any remaining blocker (`coverage_pending`, `pbm_invalid`, `pbm_policy_mismatch`, `pharmacy_out_of_network`, `pharmacy_unknown`, `missing_address`, `preferred_contact_unavailable`, `emergency_contact_missing`).
4. `approved` otherwise.

### cohort_summary
- `total_patients`; `counts_by_registration_status`{approved,hold,clinical_review,rejected}; `counts_by_overall_risk`{low,medium,high}; `counts_by_lifestyle_risk`{low,medium,high}. All integer counts.

### Top-level fixed values
- `task_id`, `roster_id` from template/prompt; `requested_service_date` and `service_line` from `intake_rosters`. `patient_results` ascending by `patient_id`.

---

## B. Referral Readiness Audit (batch, e.g. `ORTHO-*`)

Target: a referral batch. Per referral produce `readiness_status`, `issue_codes`, `priority_tier`; plus `icd_discrepancies`, `duplicate_groups`, `shared_insurance_anomalies`, `blocker_sets`, `ready_to_schedule`, `action_plan`, `summary`.

### issue_codes (per referral; set)
- `missing_records`: `records_received=0`
- `missing_imaging`: `imaging_received=0`
- `auth_blocker`: `auth_required=1` AND `auth_status` IN (pending, denied, not_submitted)
- `duplicate_referral`: referral is in a true duplicate group (see below)
- `shared_insurance_anomaly`: referral's `insurance_id` is shared by another referral in the batch
- `already_scheduled`: `appointment_scheduled=1`
- `icd_chapter_mismatch` / `narrative_mismatch` / `laterality_mismatch`: see ICD discrepancy rule

### readiness_status (precedence: blocked > under_review > admin_followup > ready)
- `blocked`: has `missing_records` | `missing_imaging` | `auth_blocker`
- `under_review`: has an ICD discrepancy | `shared_insurance_anomaly`
- `admin_followup`: has `duplicate_referral` | `already_scheduled`
- `ready`: none of the above

### ICD discrepancy detection
- `icd_chapter_mismatch`: `icd_codes.service_family != referral.service_line` (code belongs to a different service family).
- `narrative_mismatch`: the referral's `diagnosis_description`/`referral_reason` indicates a different condition/body system than the ICD `description`.
- `laterality_mismatch`: ICD `laterality` (left/right) conflicts with the side in the referral narrative, or a unilateral code vs a bilateral narrative.
- `icd_discrepancies` list: one entry per affected referral with `icd10_code`, `issue_types` (subset of the three above), `observed_chapter`, `expected_chapter` (expected = chapter of the code that matches the referral's service line; null if not determinable).

### duplicate_groups
- Group referrals within the batch sharing `(patient_id, icd10_code)` (and typically the same `insurance_id`). `group_id` assigned ascending (e.g. `DG-1`, `DG-2`…). `referral_ids` ascending. `primary_referral_id` = `MIN(referral_id)`. `recommendation` = `consolidate_to_primary`. (If two referrals share an insurance id but are the same patient, that is the duplicate pair, not a distinct-patient anomaly.)

### shared_insurance_anomalies
- `insurance_id` shared by >1 referral in the batch. `referral_ids` ascending, `patient_ids` ascending.
- `disposition`: `verify_distinct_patient_policy_id` if the patient_ids are distinct; `legitimate_duplicate_same_patient` if all the same patient.

### blocker_sets
- `missing_records`: referral_ids with `missing_records`, ascending.
- `missing_imaging`: referral_ids with `missing_imaging`, ascending.
- `auth_blockers`: list of `{referral_id, auth_status}` for auth-blocked referrals, ascending by referral_id.

### ready_to_schedule
- referral_ids with `readiness_status='ready'`, ascending.

### priority_tier (null for ready referrals) *(inferred rubric)*
- `tier_1_immediate`: blocked AND `urgency='urgent'`; OR `auth_status='denied'`.
- `tier_2_short_term`: blocked AND routine; OR under_review AND urgent.
- `tier_3_administrative`: under_review AND routine; OR admin_followup.
- `null`: ready.

### action_plan (non-ready referrals, ascending referral_id; `action_codes` set)
Map issues to actions:
- `missing_imaging` ⇒ `request_imaging`
- `missing_records` ⇒ `request_records`
- `auth_blocker` ⇒ `resolve_authorization`
- ICD discrepancy ⇒ `request_corrected_icd` (and/or `confirm_narrative`/`confirm_laterality` as the issue types dictate)
- `shared_insurance_anomaly` ⇒ `verify_insurance_id`
- `duplicate_referral` ⇒ `consolidate_duplicate`
- `already_scheduled` ⇒ `review_existing_appointment`

### summary
- `total_referrals`; `ready_to_schedule_count`; `follow_up_count` (= total − ready count).
- `counts_by_urgency`{urgent, routine, admin}; `counts_by_readiness_status`{ready, blocked, under_review, admin_followup}; `counts_by_urgency_and_status` (list, ordered urgency then readiness_status).
- `issue_counts`: `icd_discrepancy_referrals`, `duplicate_groups`, `shared_insurance_anomalies`, `missing_records_referrals`, `missing_imaging_referrals`, `auth_blocker_referrals`.
- (`admin` urgency = referrals whose only follow-up is administrative; count urgency from the `urgency` field, with admin=0 unless the field says so.)

---

## C. Dialysis Transfer Review (batch, e.g. `DIAL-*`)

Target: a transfer batch. Per transfer (ordered ascending by `transfer_id`) produce packet `completeness`, `missing_required_documents`, `stale_documents`, `requested_start` feasibility, `final_intake_decision`, `next_contact_owner`/`route`; plus `cohort_summary`.

### Required packet documents (15)
`allergy_list, face_sheet, flu_vaccine, hbsag, hep_b_antibody_core, history_physical, insurance_proof, medication_list, monthly_labs, physician_orders, pneumonia_vaccine, ppd_or_cxr, treatment_flowsheets, vascular_access_report` (from `documents` rows where `transfer_id` matches) **plus** `transportation` (satisfied iff `transfer_requests.transportation` IS NOT NULL).

### Packet rules
- A required doc is satisfied only if a `documents` row exists with `finalized=1` (status `final`). Absent or draft (`finalized=0`) ⇒ missing.
- `missing_required_documents` = unsatisfied required items, **alphabetical by code**.
- `packet_completeness_status` = `complete` if `missing_required_documents` empty, else `incomplete`.

### stale_documents
- Applies only to finalized docs of types: `hbsag, hep_b_antibody_core, history_physical, monthly_labs, ppd_or_cxr`.
- `age_days = requested_start_date − received_date`. Stale if `age_days > freshness_limit_days`.
- Entry: `{doc_type, received_date, freshness_limit_days}`, **alphabetical by doc_type**.
- Freshness windows *(inferred clinical constants — apply consistently)*: `history_physical=30`, `monthly_labs=30`, `hbsag=30`, `hep_b_antibody_core=90`, `ppd_or_cxr=90`.

### requested_start feasibility
- `date` = `transfer_requests.requested_start_date`.
- `open_chairs_total` = `SUM(facility_capacity.open_chairs)` for that `date`+`modality` across all locations; `0` if no capacity row.
- `capacity_status` = `available` if `open_chairs_total>0` else `unavailable`.
- `feasibility`:
  - `ready_on_requested_start`: packet complete AND capacity available
  - `packet_not_ready_capacity_available`: packet incomplete AND capacity available
  - `packet_not_ready_capacity_unavailable`: packet incomplete AND capacity unavailable
  - `capacity_unavailable`: packet complete AND capacity unavailable

### final_intake_decision
- `accept` ⇔ `ready_on_requested_start`
- `hold` ⇔ `packet_not_ready_capacity_available` OR `capacity_unavailable`
- `clinical_review` ⇔ `packet_not_ready_capacity_unavailable`

### next_contact *(inferred mapping)*
- `accept` ⇒ owner `scheduling_coordinator`, route `internal_queue`
- `hold` ⇒ owner `intake_coordinator`, route `fax_referring_facility` (if `transportation` missing ⇒ route `phone_patient`)
- `clinical_review` ⇒ owner `clinical_nurse`, route `internal_queue` (if capacity unavailable ⇒ route `phone_patient`)

### cohort_summary
`total_transfers`, `complete_documents_count` (transfers with complete packet), `missing_document_patient_count`, `stale_document_patient_count`, `capacity_available_count`, `requested_start_ready_count`, `decision_counts`{accept,hold,clinical_review}, `next_contact_owner_counts`{clinical_nurse,intake_coordinator,scheduling_coordinator,none}.

---

## D. Chronic-Care Enrollment Panel (program, e.g. `DMHTN-*`)

Target: a program code. One row per current candidate (from `program_candidates`), ascending by `patient_id`. Program code ⇒ required target condition and required diagnoses (DMHTN ⇒ `diabetes_hypertension` ⇒ chronic_conditions must include `diabetes` and `hypertension`).

### Required chart artifacts (for `missing_chart_artifacts`)
`chart_record, active_problems, vitals, labs, medications, consent`.
- `chart_record` missing if `patients.existing_chart=0`.
- An artifact is missing if absent OR `chart_artifacts.status!='current'` (stale counts as missing).

### eligible (boolean)
True iff: `target_condition` == program's required condition AND `consent_status='signed'` AND chronic_conditions include the program's required diagnoses (both, for DMHTN) AND `existing_chart=1` AND all required chart artifacts current.

### enrollment_status
- `reject`: `consent_status='declined'` OR `target_condition` != required OR chronic_conditions missing a required diagnosis. (hard ineligibility)
- `hold`: not reject AND (`consent_status='missing'` OR `existing_chart=0` OR any required artifact missing/stale). (salvageable)
- `enroll`: eligible.

### reason_codes (set)
- `meets_dmhtn_criteria`: eligible/enroll
- `recent_hospitalization_high_touch`: `clinical_history.recent_hospitalization=1`
- `low_adherence_high_touch`: `adherence_score < 50` *(inferred threshold)*
- `ckd_biweekly_monitoring`: chronic_conditions contains `ckd`
- `recent_ed_high_touch`: `risk_flags` contains an ED-visit flag
- `consent_declined` / `consent_missing`: matching `consent_status`
- `chart_not_active`: `existing_chart=0`
- `stale_active_problems`: `active_problems` artifact `status='stale'`
- `missing_recent_vitals` / `missing_recent_labs` / `missing_medication_list`: that artifact missing/stale
- `wrong_target_condition`: `target_condition` != required
- `missing_active_dmhtn_diagnosis`: chronic_conditions lacks a required diagnosis
- (Add high-touch/CKD reasons only for enrollees; for non-enrollees add the blocking reasons.)

### follow_up_cadence
- enroll + high_touch (recent_hosp / low_adherence / recent_ed) ⇒ `weekly`
- enroll + CKD only (no high_touch) ⇒ `biweekly`
- enroll + standard ⇒ `monthly`
- hold ⇒ `deferred`
- reject ⇒ `none`

### outreach_channel
- enroll/hold: `program_candidates.preferred_outreach` if that channel's contact data is present; else fall back to a working channel from `patients.preferred_contact`; else `none`.
- reject: `none`.

### initial_monitoring_package
- `package_type`: `high_touch_dm_htn` (enroll + high_touch); `standard_dm_htn` (enroll standard / CKD-only); `deferred` (hold); `not_applicable` (reject).
- `components` (set): standard/high_touch = `[bp_cuff, glucometer, lab_order_a1c_cmp_lipid, medication_reconciliation, care_plan_setup]`; `deferred` = `[consent_packet, chart_update_request]`; `not_applicable` = `[]`. *(inferred)*
- `first_checkin_days`: weekly⇒7, biweekly⇒14, monthly⇒30, deferred/null, not_applicable/null.

### Top-level / summary
- `program_code` from prompt; `as_of_date` = latest `candidate_date` among returned candidates *(inferred)*.
- `summary`: `total_candidates`, `eligible_count`, `ineligible_count`, `status_counts`{enroll,hold,reject}, `follow_up_counts`{weekly,biweekly,monthly,deferred,none}, `outreach_counts`{phone,portal,sms,email,none}, `monitoring_package_counts`{standard_dm_htn,high_touch_dm_htn,deferred,not_applicable}.

---

## E. Referral-to-Chart Activation (batch, e.g. `PULM-*`)

Target: a referral batch. Per referral (ascending `referral_id`) produce `readiness_status` + `blocker_codes`; plus `clinical_code_discrepancy_referrals`, `blocker_sets`, `duplicate_handling`, `ready_referral_chart_needs`, `correspondence_queue`, `priority_order`.

### blocker_codes (per referral; set)
- `records_missing`: `records_received=0`
- `imaging_missing`: `imaging_received=0`
- `authorization_blocked`: `auth_required=1` AND `auth_status` IN (denied, pending, not_submitted)
- `clinical_code_discrepancy`: `icd_codes.service_family != referral.service_line`
- `duplicate_review`: referral is in a TRUE duplicate group (same `patient_id`+`icd10_code` within batch). Referrals merely flagged "possible duplicate" but with distinct keys are **cleared**, not blocked.
- `scheduled_before_clearance`: `appointment_scheduled=1` AND the referral still has unresolved blockers

### readiness_status
- `ready`: no blockers
- `blocked`: has `records_missing` | `imaging_missing` | `authorization_blocked` | `scheduled_before_clearance`
- `under_review`: has `clinical_code_discrepancy`
- `admin_followup`: has `duplicate_review`
- (Precedence as in family B when multiple apply.)

### clinical_code_discrepancy_referrals
- referral_ids (ascending) whose ICD `service_family` != `service_line`.

### blocker_sets
- `authorization`, `records`, `imaging`: ascending referral_id lists for each blocker type.

### duplicate_handling
- `duplicate_groups`: true duplicate groups (same patient_id+icd10_code), ascending `group_id`; each `{group_id, referral_ids (asc), keep_referral_id}` where `keep_referral_id = MIN(referral_id)`.
- `cleared_duplicate_review_referrals`: referral_ids flagged as possible duplicates but distinct (kept separate), ascending.

### ready_referral_chart_needs (ready referrals, ascending referral_id)
- `chart_action`: `create_chart` if `existing_chart=0`; `update_chart` if `existing_chart=1` but artifacts missing/stale; `no_chart_action` if all current.
- `artifacts_to_create` (alphabetical by enum string): from `demographics, active_problems, medications, allergies, vitals, labs, consent` — those absent OR `status!='current'`. (For `create_chart`, all seven.)

### correspondence_queue (ascending referral_id)
- One entry per referral needing outbound correspondence. `template_type` + `reason_codes` (set):
  - clinical code discrepancy ⇒ `clinical_code_clarification`, [`wrong_service_family`] (add `clinical_reason_mismatch` if the referral reason contradicts the code)
  - records/auth blockers, no appointment ⇒ `auth_records_request`, [`records_missing`, `authorization_denied`] (as applicable)
  - already-scheduled referral with unresolved blockers ⇒ `appointment_hold_notice`, [`authorization_denied`, `records_missing`, `appointment_already_scheduled`] (as applicable)
  - true duplicate group ⇒ `duplicate_resolution`, [`duplicate_review`]
  - Ready referrals and cleared duplicates need no correspondence.
- `reason_codes` allowed: `wrong_service_family, clinical_reason_mismatch, records_missing, authorization_denied, duplicate_review, appointment_already_scheduled`.

### priority_order (non-ready referrals only, highest priority first)
- `priority_tier` *(inferred rubric)*:
  - `tier_1_immediate`: `scheduled_before_clearance`; OR urgent+blocked.
  - `tier_2_short_term`: blocked (records/auth) without scheduled appointment; OR under_review with clinical code discrepancy.
  - `tier_3_administrative`: admin_followup (duplicate review).
- Order: tier_1 first, then tier_2, then tier_3; within a tier, blocked before under_review before admin_followup, then by referral_id. Emit `{rank (from 1), referral_id, priority_tier}`.

### Normalization
- All reason/blocker arrays are unordered sets (sort deterministically). Referral IDs uppercase as returned. No free-form explanation fields.

---

## Cross-family notes

- **Read the template first, always.** Where a rule here and the template disagree, the template wins (it is the graded contract). Use the template's exact enum strings, key names, and orderings.
- **Distractor records.** Filter to the target batch/roster/program. Ignore unrelated referrals/transfers/candidates and `notes` like "distractor referral".
- **Records/imaging flags vs documents.** Referral readiness uses `referrals.records_received`/`imaging_received`; transfer packets use `documents.finalized`.
- **Inferred rubrics** (lifestyle/clinical risk points, freshness day-limits, adherence threshold, monitoring-package components, as_of_date, priority tiers) are best-effort constants distilled from training. Apply them uniformly; if a held-out template explicitly states a different value, follow the template.
