# Task archetypes

Five recurring patterns. Match the task by its target and its template key set,
then follow that section. Enum/code names in the templates are self-documenting;
map each raw field to the template value whose name matches its meaning, and use
**only** the template's allowed values. Apply thresholds/policies consistently
across every item, and recompute all summary counts from the rows you emit.

Illustrative target-naming (family, not a fixed list): access rosters `NPI-*`;
referral batches `ORTHO-*`, `PULM-*`, `CARD-*`, `GEN-*`, `COMMUNITY-*`; transfer
batches `DIAL-*`; program codes `DMHTN-*`, `RENAL-*`, `COPD-*`, `CAD-*`.

---

## A. New-patient access verification (roster) — e.g. template with
`roster_id`, `requested_service_date`, `service_line`, `patient_results`,
`cohort_summary`.

Tables: intake_rosters, patients, coverage, pbm, patient_pharmacy+pharmacies,
lifestyle. Read `requested_service_date` and `service_line` from the roster row
(do not hardcode). One `patient_results` item per required patient_id.

Per-patient derivations (into template enums/codes):
- **insurance_status** from that patient's `coverage`, considering the roster
  `service_line`: `valid` when an active, in-scope policy exists;
  `invalid` when the best policy is expired/otherwise unusable; `missing` when
  none on file. Reason codes: `coverage_expired` (status=expired),
  `coverage_pending` (status=pending), `excluded_service_line`
  (roster service_line not in the policy's `service_lines`).
- **prescription_status** from `pbm`: `valid` (active & covered/approved),
  `invalid` (rejected / not_found / inactive), `missing` (no row). Reason codes:
  `pbm_invalid`, `pbm_missing`, `pbm_policy_mismatch` (e.g. formulary=review /
  specialty_required conflict).
- **pharmacy_status** from the top-ranked `patient_pharmacy` → `pharmacies`:
  `in_network`, `out_of_network`, or `unknown` (none on file). Reason codes:
  `pharmacy_out_of_network`, `pharmacy_unknown`.
- **lifestyle_risk** `low|medium|high` from `lifestyle` (smoking Current, Heavy
  alcohol, no/low exercise raise risk; None/Never/regular exercise lower it).
- **overall_risk** `low|medium|high` combining lifestyle with any access
  blockers; `overall_risk_high` reason code when high.
- **Demographic blockers**: `missing_address` (patients.address null),
  `emergency_contact_missing` (emergency_contact_present=0),
  `preferred_contact_unavailable` (preferred_contact channel not usable — e.g.
  preferred=email but email null).
- **registration_status** `approved|hold|clinical_review|rejected` from the
  blocker set: hard coverage/pbm/demographic blockers push to hold/rejected;
  high overall risk to clinical_review; clean records to approved. Populate
  `blocked_reason_codes` with every applicable code (unordered set, deduped) —
  and keep them consistent with the status.

`cohort_summary`: total_patients + counts_by_registration_status /
_overall_risk / _lifestyle_risk, each summed from the emitted items.

---

## B. Referral readiness audit (batch) — e.g. template with `referral_reviews`,
`icd_discrepancies`, `duplicate_groups`, `shared_insurance_anomalies`,
`blocker_sets`, `ready_to_schedule`, `action_plan`, `summary`.

Tables: referrals (batch_id filter), icd_codes, patients, coverage/insurance,
documents. Per referral compute `issue_codes` (unordered set) and
`readiness_status` (`ready|blocked|under_review|admin_followup`):
- **icd_chapter_mismatch**: `icd_codes.service_family` for the referral's
  `icd10_code` ≠ the referral's `service_line` (e.g. an orthopedics referral
  coded to a pulmonary ICD). Report in `icd_discrepancies` with
  observed vs expected chapter (null when unknown).
- **narrative_mismatch**: `diagnosis_description`/`referral_reason` inconsistent
  with the ICD's meaning.
- **laterality_mismatch**: narrative laterality (left/right) ≠
  `icd_codes.laterality`.
- **duplicate_referral**: same patient + same clinical intent within the batch;
  group in `duplicate_groups`, choose a `primary_referral_id` (deterministic —
  e.g. earliest date_received / smallest referral_id),
  `recommendation` consolidate_to_primary vs keep_separate.
- **shared_insurance_anomaly**: one `insurance_id` across >1 distinct patient →
  `verify_distinct_patient_policy_id`; same-patient repeats →
  `legitimate_duplicate_same_patient`.
- **missing_records** (`records_received=0`), **missing_imaging**
  (`imaging_received=0`), **auth_blocker** (`auth_required=1` and auth_status in
  pending/denied/not-submitted; record `auth_status`), **already_scheduled**
  (`appointment_scheduled=1`).

`readiness_status`: `ready` = no blocking issues (records+imaging present, auth
satisfied or not required, not a duplicate/coding problem) → also goes in
`ready_to_schedule`. Coding/narrative/laterality problems → `under_review`;
missing records/imaging/auth → `blocked`; duplicate/insurance/scheduling
cleanup → `admin_followup`. `priority_tier`:
tier_1_immediate (urgent + resolvable clinical blocker), tier_2_short_term,
tier_3_administrative; `null` only where the template allows it (a clean `ready`
referral). `action_plan` maps each non-ready referral's issues to `action_codes`
(request_corrected_icd, confirm_narrative/laterality, consolidate_duplicate,
verify_insurance_id, request_records/imaging, resolve_authorization,
review_existing_appointment). `summary`: counts by urgency (urgent/routine/admin
from `referrals.urgency`), by readiness_status, the urgency×status matrix
(ordered urgency then status), and issue_counts — all tallied from emitted rows.

---

## C. Referral-to-chart activation (batch) — e.g. template with
`readiness_by_referral`, `clinical_code_discrepancy_referrals`, `blocker_sets`,
`duplicate_handling`, `ready_referral_chart_needs`, `correspondence_queue`,
`priority_order`.

Same referral/icd/document logic as B, plus chart activation. Per referral,
`blocker_codes`: clinical_code_discrepancy, records_missing, imaging_missing,
authorization_blocked, duplicate_review, scheduled_before_clearance.
- `duplicate_handling`: groups with a `keep_referral_id`;
  `cleared_duplicate_review_referrals` are the non-kept ones resolved.
- `ready_referral_chart_needs` (only referrals that reach `ready`): decide
  `chart_action` from `patients.existing_chart` — `create_chart` if 0,
  `update_chart` if 1 but artifacts are missing/stale, else `no_chart_action`.
  `artifacts_to_create` from missing/stale `chart_artifacts` for that patient
  (demographics, active_problems, medications, allergies, vitals, labs,
  consent), **sorted alphabetically** per the template.
- `correspondence_queue`: one letter per non-ready referral —
  `template_type` (clinical_code_clarification / auth_records_request /
  duplicate_resolution / appointment_hold_notice) with matching `reason_codes`.
- `priority_order`: **non-ready referrals only**, highest priority first, dense
  `rank` starting at 1, each with a `priority_tier`. Keep IDs uppercase as shown.

---

## D. Dialysis transfer review (batch) — e.g. template with `batch_id`,
`patients` (per transfer), `cohort_summary`.

Tables: transfer_requests (batch_id filter), patients, documents
(transfer_id, content_tag='transfer_packet'), facility_capacity. One item per
transfer, ordered by transfer_id.
- **Required packet** = the template's `missing_required_documents`
  allowed_values (the dialysis document set). A required doc is satisfied only by
  a **finalized/final** document of that `doc_type`; otherwise list its code in
  `missing_required_documents` (alphabetical).
  `packet_completeness_status` = complete only when none are missing.
- **stale_documents**: the freshness-limited doc types the template enumerates
  (e.g. hbsag, hep_b_antibody_core, history_physical, monthly_labs, ppd_or_cxr).
  A present doc is stale when `received_date` is older than its
  `freshness_limit_days` relative to the reference date. Emit
  `{doc_type, received_date, freshness_limit_days}` sorted by doc_type. Use the
  freshness limits stated by the task/template; do not invent numbers.
- **requested_start**: `open_chairs_total` = SUM of `facility_capacity.open_chairs`
  across Cedar Ridge locations for `requested_start_date` &
  modality=in_center_hemodialysis. `capacity_status` available when >0.
  `feasibility` combines packet readiness × capacity:
  ready_on_requested_start / packet_not_ready_capacity_available /
  packet_not_ready_capacity_unavailable / capacity_unavailable.
- **final_intake_decision** accept|hold|clinical_review; **next_contact_owner**
  (clinical_nurse for clinical/stale-clinical gaps, intake_coordinator for
  packet/admin, scheduling_coordinator for capacity, none when accepted clean)
  and **next_contact_route** (fax_referring_facility, phone_patient,
  internal_queue, none) consistent with the owner.

`cohort_summary`: total_transfers, complete_documents_count,
missing/stale patient counts, capacity_available_count,
requested_start_ready_count, decision_counts, next_contact_owner_counts — all
from emitted rows.

---

## E. Chronic-care enrollment panel (program) — e.g. template with
`program_code`, `as_of_date`, `patients`, `summary`.

Tables: program_candidates (`/programs/{code}/candidates` = authoritative
membership — one row per returned candidate), patients, chart_artifacts,
clinical_history. `as_of_date` = the panel/reference date (YYYY-MM-DD).
- **eligible** (bool) + **enrollment_status** enroll|hold|reject:
  reject on `wrong_target_condition` (candidate `target_condition` ≠ the
  program's condition), `consent_declined`, or `missing_active_dmhtn_diagnosis`;
  hold on `consent_missing` or missing chart artifacts; enroll when criteria met
  (`meets_dmhtn_criteria`).
- **reason_codes** (unordered set) from the template list, including high-touch
  drivers: recent_hospitalization_high_touch (clinical_history), 
  low_adherence_high_touch (low adherence_score), recent_ed_high_touch
  (risk_flags ~ recent_ed_visit), ckd_biweekly_monitoring
  (chronic_conditions ~ ckd), and chart gaps
  (chart_not_active / stale_active_problems / missing_recent_vitals / _labs /
  _medication_list).
- **missing_chart_artifacts** from `chart_artifacts`/`/chart` (chart_record,
  active_problems, vitals, labs, medications, consent) — missing or stale.
- **follow_up_cadence** weekly|biweekly|monthly|deferred|none and
  **initial_monitoring_package** (package_type standard_dm_htn /
  high_touch_dm_htn / deferred / not_applicable; components from the allowed set;
  first_checkin_days integer or null): high-touch drivers → high_touch package +
  weekly/biweekly + shorter first check-in; standard enroll → standard package +
  monthly; hold → deferred/chart_update components; reject → not_applicable +
  none + null check-in.
- **outreach_channel** phone|portal|sms|email|none from
  `preferred_outreach` (none when rejected / not contacting).

`summary`: total_candidates, eligible/ineligible counts, status_counts,
follow_up_counts, outreach_counts, monitoring_package_counts — from emitted rows.
