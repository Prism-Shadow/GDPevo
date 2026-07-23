# Decision Rules: Evidence → Controlled Values

Deterministic mappings per task family. Apply the same rule to every entity.
These are rules, not answers — the actual statuses/codes depend on the portal data for
the specific scope. Always trace an emitted value back to a field; when evidence is
genuinely absent, use the template's "missing/unknown" enum.

The allowed value sets live in each task's `answer_template.json` — re-read it for the
exact enum members; the sets below summarize them and may evolve between batches.

---

## A. New-Patient Access Verification (roster-scoped)

Scope: the `roster_id` from the prompt. Entity list: the `patient_id`s on that roster
(read `intake_rosters` or `GET /patients/{id}` → `rosters`). Carry the roster's
`requested_service_date` and `service_line` into the top-level fields.

Per patient (use `GET /patients/{id}` as the hub):

- **insurance_status** (`valid` / `invalid` / `missing`)
  - `valid`: a `coverage` row with `status='active'`, effective on/before the requested
    service date, not terminated before it, and `service_lines` contains the roster
    `service_line`.
  - `invalid`: coverage exists but inactive, expired, pending, or excludes the roster
    service line.
  - `missing`: no `coverage` rows.
  - Blocker codes: `coverage_expired`, `coverage_pending`, `excluded_service_line`.
- **prescription_status** (`valid` / `invalid` / `missing`)
  - `valid`: a `pbm` row with `active=1`, `status='approved'`, `formulary_status='covered'`.
  - `invalid`: pbm present but inactive/denied/non-formulary, or `specialty_required`
    policy mismatch.
  - `missing`: no `pbm` rows.
  - Blocker codes: `pbm_invalid`, `pbm_missing`, `pbm_policy_mismatch`.
- **pharmacy_status** (`in_network` / `out_of_network` / `unknown`)
  - Take the `preference_rank=1` pharmacy from `patient_pharmacy` → `pharmacies.network_status`.
  - `unknown` when the patient has no preferred pharmacy.
  - Blocker codes: `pharmacy_out_of_network`, `pharmacy_unknown`.
- **lifestyle_risk** (`low` / `medium` / `high`): score `lifestyle`
  (smoking_status, alcohol_use, exercise_frequency, sleep_hours) on a fixed rubric.
- **overall_risk** (`low` / `medium` / `high`): combine `lifestyle_risk` with
  `clinical_history.recent_hospitalization` and `risk_flags`. `overall_risk_high` is a
  blocker code when high.
- **registration_status** (`approved` / `hold` / `clinical_review` / `rejected`):
  - `approved`: all statuses valid, overall risk low/medium, no blockers.
  - `hold`: minor demographic/admin blockers only.
  - `clinical_review`: overall risk high or clinical concerns.
  - `rejected`: hard blockers (excluded service line, coverage missing/expired, etc.).
- **Demographic blocker codes**: `emergency_contact_present=0` → `emergency_contact_missing`;
  `address` null → `missing_address`; `preferred_contact` unusable →
  `preferred_contact_unavailable`.
- **cohort_summary**: integer counts by registration_status, overall_risk, lifestyle_risk
  (every bucket, zero included); `total_patients` == sum of registration-status counts.

---

## B. Referral Readiness Audit (batch-scoped)

Scope: the `batch_id` from the prompt. Entity list: `referrals` where `batch_id` matches
(ignore distractor rows and other batches).

Per referral, derive `readiness_status` + `issue_codes`:

- `icd_chapter_mismatch`: `referrals.service_line` vs `icd_codes.service_family`
  (look up `GET /icd/{icd10_code}`). `observed_chapter` = `icd.chapter`;
  `expected_chapter` = the chapter for the referral's service family.
- `narrative_mismatch`: `referrals.diagnosis_description` inconsistent with
  `icd_codes.description`.
- `laterality_mismatch`: `icd_codes.laterality` set but referral/diagnosis doesn't match.
- `missing_records`: `records_received=0`.
- `missing_imaging`: `imaging_received=0`.
- `auth_blocker`: `auth_required=1 AND auth_status IN (pending, denied, not_submitted)`.
- `duplicate_referral`: same patient + service line + overlapping icd/reason in the batch.
- `shared_insurance_anomaly`: `insurance_id` shared across distinct patients.
- `already_scheduled`: `appointment_scheduled=1`.

`readiness_status`: `ready` (no issues) / `blocked` (records/imaging/auth) /
`under_review` (clinical code discrepancies) / `admin_followup` (duplicates, shared
insurance, already scheduled).

`icd_discrepancies`: one row per referral with any of the three ICD issue types, carrying
`icd10_code`, `issue_types`, `observed_chapter`, `expected_chapter`.

`duplicate_groups`: group by patient; `group_id`, `referral_ids` (asc), `patient_id`,
`primary_referral_id`, `recommendation` (`consolidate_to_primary` / `keep_separate`).

`shared_insurance_anomalies`: group by `insurance_id`; `referral_ids` + `patient_ids`
(asc); `disposition` = `verify_distinct_patient_policy_id` (different patients) or
`legitimate_duplicate_same_patient` (same patient).

`blocker_sets`: `missing_records`, `missing_imaging` (referral_id lists asc), and
`auth_blockers` (referral_id + `auth_status`).

`ready_to_schedule`: referral_ids with `readiness_status='ready'` (asc).

`action_plan`: per referral, `priority_tier` + `action_codes` matched to its issues.
`priority_tier`: `tier_1_immediate` (urgent + blocked/under_review),
`tier_2_short_term` (routine + blocked), `tier_3_administrative` (admin/duplicates).

`summary`: total_referrals, ready_to_schedule_count, follow_up_count,
`counts_by_urgency`, `counts_by_readiness_status`, `counts_by_urgency_and_status`
(ordered urgency then readiness), `issue_counts`.

---

## C. Dialysis Transfer Review (batch-scoped)

Scope: the `batch_id` from the prompt. Entity list: `transfer_requests` where `batch_id`
matches; join `documents` by `transfer_id`.

Per transfer:

- **Required document set** comes from the template (e.g. allergy_list, face_sheet,
  flu_vaccine, hbsag, hep_b_antibody_core, history_physical, insurance_proof,
  medication_list, monthly_labs, physician_orders, pneumonia_vaccine, ppd_or_cxr,
  transportation, treatment_flowsheets, vascular_access_report). Re-read the template —
  the set is authoritative.
- `packet_completeness_status` (`complete` / `incomplete`): `complete` iff every required
  `doc_type` is present for the `transfer_id` with `status='final'`/`finalized=1`.
  Otherwise `incomplete` and list `missing_required_documents` (alphabetical by code).
- `stale_documents`: doc types that carry a freshness limit (e.g. hbsag,
  hep_b_antibody_core, history_physical, monthly_labs, ppd_or_cxr) whose
  `received_date` is older than the limit days. Row = `doc_type`, `received_date`,
  `freshness_limit_days` (alphabetical by doc_type).
- `requested_start`: `date` = `transfer_requests.requested_start_date`;
  `capacity_status` from `facility_capacity` for that `date` + `modality`
  (`available` if any open chairs, else `unavailable`);
  `open_chairs_total` = sum of `open_chairs` across locations for that date+modality;
  `feasibility` = `ready_on_requested_start` (packet complete AND capacity available) /
  `packet_not_ready_capacity_available` / `packet_not_ready_capacity_unavailable` /
  `capacity_unavailable`.
- `final_intake_decision` (`accept` / `hold` / `clinical_review`): `accept` when
  ready_on_requested_start; `hold` when packet not ready but capacity available;
  `clinical_review` when capacity unavailable or stale labs.
- `next_contact_owner` (`clinical_nurse` / `intake_coordinator` /
  `scheduling_coordinator` / `none`) and `next_contact_route`
  (`fax_referring_facility` / `phone_patient` / `internal_queue` / `none`): chosen from
  the decision and the gap (clinical gap → nurse; packet gap → coordinator; capacity →
  scheduling; accepted/none → none).
- Patients ordered ascending by `transfer_id`.

`cohort_summary`: total_transfers, complete_documents_count,
missing_document_patient_count, stale_document_patient_count, capacity_available_count,
requested_start_ready_count, `decision_counts` (accept/hold/clinical_review),
`next_contact_owner_counts`.

---

## D. Chronic-Care Enrollment Panel (program-scoped)

Scope: the `program_code` from the prompt. Entity list: `GET /programs/{code}/candidates`
— one row per current candidate. For each, also pull `GET /chart/{id}` and
`GET /patients/{id}` (clinical_history, existing_chart).

Per candidate:

- `eligible` (bool) and `enrollment_status` (`enroll` / `hold` / `reject`):
  - Eligible requires `target_condition` matching the program target, `consent_status`
    signed, an active DM/HTN diagnosis in the chart, `existing_chart=1`, and recent
    vitals/labs/medications present.
  - `enroll`: eligible and no blocking gaps.
  - `hold`: eligible but missing artifacts or needing high-touch setup.
  - `reject`: `consent_declined`/`consent_missing`, `wrong_target_condition`,
    `missing_active_dmhtn_diagnosis`, or `chart_not_active`.
- `reason_codes` (template set): `meets_dmhtn_criteria`, `recent_hospitalization_high_touch`,
  `low_adherence_high_touch`, `ckd_biweekly_monitoring`, `recent_ed_high_touch`,
  `consent_declined`, `consent_missing`, `chart_not_active`, `stale_active_problems`,
  `missing_recent_vitals`, `missing_recent_labs`, `missing_medication_list`,
  `wrong_target_condition`, `missing_active_dmhtn_diagnosis`.
- `follow_up_cadence` (`weekly` / `biweekly` / `monthly` / `deferred` / `none`):
  high-touch flags (recent hospitalization, low adherence, CKD, recent ED) → weekly/biweekly;
  standard enroll → monthly; hold → deferred; reject → none.
- `missing_chart_artifacts` (template set: `chart_record`, `active_problems`, `vitals`,
  `labs`, `medications`, `consent`): from `existing_chart=0` and empty/absent sections on
  `GET /chart/{id}` (`active_problems`, `recent_vitals_labs`, `meds_allergies`,
  `chart_artifacts`, consent).
- `outreach_channel` (`phone` / `portal` / `sms` / `email` / `none`): from
  `program_candidates.preferred_outreach`; `none` if no usable contact.
- `initial_monitoring_package`: `package_type`
  (`standard_dm_htn` / `high_touch_dm_htn` / `deferred` / `not_applicable`),
  `components` (template set), `first_checkin_days` (int or null).
- Patients sorted by `patient_id` ascending.

`summary`: total_candidates, eligible_count, ineligible_count, `status_counts`,
`follow_up_counts`, `outreach_counts`, `monitoring_package_counts` (each with all template
buckets, zero included).

---

## E. Referral-to-Chart Activation (batch-scoped)

Scope: the `batch_id` from the prompt. Entity list: `referrals` where `batch_id` matches.

- `readiness_by_referral`: per referral `referral_id`, `patient_id`, `readiness_status`
  (`ready` / `blocked` / `under_review` / `admin_followup`), `blocker_codes`
  (`clinical_code_discrepancy`, `records_missing`, `imaging_missing`,
  `authorization_blocked`, `duplicate_review`, `scheduled_before_clearance`). Map from the
  same evidence as family B (records/imaging/auth = `records_missing`/`imaging_missing`/
  `authorization_blocked`; ICD discrepancy = `clinical_code_discrepancy`; duplicate =
  `duplicate_review`; already scheduled = `scheduled_before_clearance`). Ordered asc by
  referral_id.
- `clinical_code_discrepancy_referrals`: referral_ids with an ICD discrepancy (asc).
- `blocker_sets`: `authorization`, `records`, `imaging` — referral_id lists (asc).
- `duplicate_handling`: `duplicate_groups` (`group_id`, `referral_ids` asc,
  `keep_referral_id`) ordered asc by group_id, plus `cleared_duplicate_review_referrals`
  (asc) for duplicates resolved without blocking.
- `ready_referral_chart_needs`: per ready referral, `chart_action`
  (`create_chart` if `existing_chart=0`; `update_chart` if chart exists but artifacts
  missing; `no_chart_action` if chart complete) and `artifacts_to_create`
  (`demographics`, `active_problems`, `medications`, `allergies`, `vitals`, `labs`,
  `consent` — alphabetical by artifact) derived from `GET /chart/{id}` gaps. Asc by
  referral_id.
- `correspondence_queue`: per non-ready referral, `template_type`
  (`clinical_code_clarification` / `auth_records_request` / `duplicate_resolution` /
  `appointment_hold_notice`) and `reason_codes` (`wrong_service_family`,
  `clinical_reason_mismatch`, `records_missing`, `authorization_denied`,
  `duplicate_review`, `appointment_already_scheduled`). Asc by referral_id.
- `priority_order`: non-ready referrals ranked highest-priority first with `rank` (from 1),
  `referral_id`, `priority_tier` (`tier_1_immediate` / `tier_2_short_term` /
  `tier_3_administrative`).

Reason-code and blocker-code arrays are unordered sets — emit sorted for determinism.
Uppercase IDs exactly as returned by the portal.
