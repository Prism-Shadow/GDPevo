# Decision rubrics by task family

These rules were reverse-engineered from the portal data and are consistent with every
worked example seen so far. They are **rules, not answers** — apply them to whatever roster/
batch/program the current prompt names. The provided `answer_template.json` is always the
final authority on keys, controlled values, and ordering; where a template's enum list
differs from what's below, follow the template.

Identify the family from the prompt + template:

| signal in prompt / template | family |
|---|---|
| `roster_id`, `service_line`, `patient_results`, registration_status | **A. Patient access verification** |
| `batch_id` on referrals, `referral_reviews`, `duplicate_groups`, `action_plan` | **B. Referral readiness audit** |
| `batch_id` on transfers, `packet_completeness_status`, `requested_start` | **C. Dialysis transfer review** |
| `program_code`, `candidates`, `enrollment_status`, monitoring package | **D. Program enrollment panel** |
| `batch_id` on referrals, `readiness_by_referral`, `chart_needs`, `correspondence_queue` | **E. Referral-to-chart activation** |

Constants (`task_id`, `roster_id`/`batch_id`/`program_code`) come straight from the prompt/
template. Date fields come from the data: a roster's `requested_service_date` and
`service_line` from `intake_rosters`; a transfer's start date from `transfer_requests`. A
top-level `as_of_date` (family D) is the panel review date — use the environment/prompt's
effective review date if given, otherwise the current date; it is a single low-weight field.

---

## Shared primitives

**Coverage (medical insurance) status** for a requested `service_line`:
- `missing` — no coverage row.
- `invalid` if any of: `status='expired'` → reason `coverage_expired`; `status='pending'`
  → reason `coverage_pending`; requested service line **not** in `service_lines`
  → reason `excluded_service_line`. (These stack — an expired policy that also excludes the
  line emits both codes.)
- `valid` otherwise (`status='active'` and service line covered).

**PBM (prescription) status:**
- `missing` — no pbm row → reason `pbm_missing`.
- `invalid` if `status != 'approved'` or `active=0` or `formulary_status != 'covered'`
  → reason `pbm_invalid`; **or** `specialty_required=1` → reason `pbm_policy_mismatch`.
- `valid` otherwise.

**Preferred-pharmacy network status:** take the rank-1 (`preference_rank=1`) pharmacy and
read `pharmacies.network_status` → `in_network` / `out_of_network`. No pharmacy or unknown
status → `unknown`.

**Preferred-contact reachability** (patient's `preferred_contact` vs contact data):
`email` needs a non-null `email`; `phone` needs a non-null `phone`; `sms` needs a non-null
`phone`; `portal` is always reachable. If the chosen channel's data is missing →
`preferred_contact_unavailable`.

**Referral hard blockers** (used by families B & E):
- `records_received=0` → missing records.
- `imaging_received=0` → missing imaging.
- `auth_required=1` and `auth_status ∈ {pending, denied, not_submitted}` → auth blocker
  (carry the `auth_status`).
- `appointment_scheduled=1` on a not-yet-cleared referral → already-scheduled / scheduled-
  before-clearance.

**Referral coding discrepancies** (look the `icd10_code` up in `icd_codes`):
- **chapter mismatch** — the code's `chapter` ≠ the batch service line's canonical chapter
  (see data_model.md). `observed_chapter` = code's chapter, `expected_chapter` = the line's
  canonical chapter.
- **wrong service family** — the code's `service_family` ≠ the batch service line.
- **narrative / clinical-reason mismatch** — `diagnosis_description` or `referral_reason` is
  clinically inconsistent with the code / service line (e.g. a musculoskeletal
  "pain evaluation" reason on a pulmonary referral). Judgment call; use the code description.
- **laterality mismatch** — code `laterality` contradicts the stated side.

**Duplicates:** same `patient_id` + same `icd10_code` within a batch = a duplicate group.
`primary`/`keep` referral = lowest `referral_id`; group_id convention `DUP-<batch_id>-NNN`
(zero-padded, ascending). Different patients sharing one `insurance_id` = a *shared-insurance
anomaly* (not a duplicate) → `verify_distinct_patient_policy_id`; same patient reusing an
insurance id across their own referrals → `legitimate_duplicate_same_patient`.

**Readiness status** (families B & E), by worst issue present:
`blocked` (any hard blocker: missing records/imaging, auth blocker, scheduled-before-
clearance) > `under_review` (coding/narrative/laterality/duplicate/already-scheduled review
issue) > `admin_followup` (only administrative issues, e.g. shared insurance) > `ready`
(no issues).

**Priority tier:** `tier_1_immediate` if referral `urgency='urgent'`; else
`tier_3_administrative` if the only issues are administrative (admin_followup); else
`tier_2_short_term`.

---

## A. Patient access verification (e.g. NPI-* primary-care roster)

Per patient (ascending `patient_id`) emit: `insurance_status`, `prescription_status`,
`pharmacy_status`, `lifestyle_risk`, `overall_risk`, `registration_status`,
`blocked_reason_codes`. Get the roster's `requested_service_date` + `service_line` from
`intake_rosters`.

`insurance_status` / `prescription_status` / `pharmacy_status` — shared primitives above.

`lifestyle_risk` (low|medium|high) — composite of `lifestyle` fields. A scoring that
reproduces every worked example: smoking Current=2 / Former=1 / Never=0; alcohol Heavy=2 /
Moderate=1 / Occasional|None=0; exercise None or null=1 / else 0; sleep_hours <6=1 / else 0.
Sum → **high if ≥3, medium if 2, low if ≤1**. Apply it consistently; treat the exact cut
points as a heuristic and sanity-check against the cohort spread.

`overall_risk` (low|medium|high) — escalates `lifestyle_risk` by clinical burden from
`clinical_history`: `recent_hospitalization=1`, a non-empty `risk_flags`, high
`medication_count`, or several `chronic_conditions` push it up; overall is `high` when
lifestyle is high **or** clinical burden is high. When `overall_risk='high'`, add reason
`overall_risk_high`.

`blocked_reason_codes` — union of every code triggered (order not meaningful; template treats
it as a set): the coverage/pbm/pharmacy/contact codes above, plus `missing_address` (patient
`address` null), `emergency_contact_missing` (`emergency_contact_present=0`), and
`overall_risk_high`.

`registration_status`, by precedence:
- `rejected` — a definitive coverage denial: `excluded_service_line` or `coverage_expired`.
- else `clinical_review` — `overall_risk='high'` (or other clinical flag) with no hard denial.
- else `hold` — recoverable blockers only (e.g. pending coverage, pharmacy/contact issues)
  without high risk.
- else `approved` — clean, low/medium risk, no blockers.

`cohort_summary`: `total_patients` plus `counts_by_registration_status` /
`counts_by_overall_risk` / `counts_by_lifestyle_risk`, each keyed by its full enum. Counts
must equal the per-patient tallies.

---

## B. Referral readiness audit (e.g. ORTHO-* batch)

Pull all `referrals` for the `batch_id`. For each (ascending `referral_id`) build the set of
issue codes from the shared primitives: `icd_chapter_mismatch`, `narrative_mismatch`,
`laterality_mismatch`, `duplicate_referral`, `shared_insurance_anomaly`, `missing_records`,
`missing_imaging`, `auth_blocker`, `already_scheduled`. Then:

- `referral_reviews[]`: `readiness_status`, `issue_codes` (set), `priority_tier`
  (per shared rules; may be null only if the template allows).
- `icd_discrepancies[]`: one row per referral with a coding issue — `icd10_code`,
  `issue_types` (subset of chapter/narrative/laterality), `observed_chapter`,
  `expected_chapter`.
- `duplicate_groups[]`: per shared duplicate rule; `recommendation=consolidate_to_primary`
  for a real duplicate.
- `shared_insurance_anomalies[]`: per shared rule, sorted by `insurance_id`; `referral_ids`
  and `patient_ids` ascending.
- `blocker_sets`: `missing_records` (ids), `missing_imaging` (ids), `auth_blockers`
  (`{referral_id, auth_status}`), all ascending `referral_id`.
- `ready_to_schedule[]`: referrals with **no** issues (ascending).
- `action_plan[]`: per referral, `priority_tier` + `action_codes` mapped 1:1 from issues:
  `icd_chapter_mismatch→request_corrected_icd`, `narrative_mismatch→confirm_narrative`,
  `laterality_mismatch→confirm_laterality`, `duplicate_referral→consolidate_duplicate`,
  `shared_insurance_anomaly→verify_insurance_id`, `missing_records→request_records`,
  `missing_imaging→request_imaging`, `auth_blocker→resolve_authorization`,
  `already_scheduled→review_existing_appointment`.
- `summary`: `total_referrals`, `ready_to_schedule_count`, `follow_up_count`
  (= not-ready), `counts_by_urgency` (from `referrals.urgency`; enum urgent/routine/admin),
  `counts_by_readiness_status`, `counts_by_urgency_and_status` (only non-zero cells, ordered
  urgency then readiness_status), and `issue_counts` (referrals-with-that-issue tallies).
  Every count must reconcile with the detail lists.

---

## C. Dialysis transfer review (e.g. DIAL-* batch)

Pull `transfer_requests` for the `batch_id`. Per transfer (ascending `transfer_id`):

**Required-document set** = the 14 finalized `documents` doc_types *plus* transportation:
`allergy_list, face_sheet, flu_vaccine, hbsag, hep_b_antibody_core, history_physical,
insurance_proof, medication_list, monthly_labs, physician_orders, pneumonia_vaccine,
ppd_or_cxr, treatment_flowsheets, vascular_access_report`, and `transportation` (satisfied by
`transfer_requests.transportation` being non-null). A doc is **missing** if absent **or**
`finalized=0` (draft). `missing_required_documents` is sorted alphabetically by code;
`packet_completeness_status` = `complete` iff that list is empty else `incomplete`.

**Stale documents** — only these finalized doc types have a freshness limit, measured from
the **`requested_start_date`** back to `received_date`:
`hbsag`=30d, `monthly_labs`=30d, `ppd_or_cxr`=30d, `hep_b_antibody_core`=365d,
`history_physical`=365d. Emit `{doc_type, received_date, freshness_limit_days}` for each that
exceeds its limit, sorted alphabetically by `doc_type`.

**requested_start** — `date` = `requested_start_date`;
`open_chairs_total` = SUM(`facility_capacity.open_chairs`) over all locations for that date &
`in_center_hemodialysis` (absent date ⇒ 0); `capacity_status` = `available` if total>0 else
`unavailable`. `feasibility`: packet **ready** means complete AND no stale docs.
- ready + available → `ready_on_requested_start`
- not-ready + available → `packet_not_ready_capacity_available`
- not-ready + unavailable → `packet_not_ready_capacity_unavailable`
- ready + unavailable → `capacity_unavailable`

**final_intake_decision / next_contact:**
- `clinical_review` when clinical items are missing/stale (labs, hbsag, ppd_or_cxr, H&P, hep
  B, vascular access, etc.) → owner `clinical_nurse`, route `fax_referring_facility`.
- `hold` when only administrative items are missing (insurance_proof, transportation, face
  sheet, vaccines) → owner `intake_coordinator` (patient-side items → `phone_patient`;
  otherwise `internal_queue`).
- `accept` only when packet is complete, nothing stale, capacity available (fully ready) →
  owner `none`, route `none`.
(Every worked transfer had stale clinical labs ⇒ clinical_review / clinical_nurse / fax.)

`cohort_summary`: `total_transfers`, `complete_documents_count`,
`missing_document_patient_count`, `stale_document_patient_count`, `capacity_available_count`,
`requested_start_ready_count` (= feasibility `ready_on_requested_start`), `decision_counts`
(accept/hold/clinical_review), `next_contact_owner_counts` (all four owners). Reconcile all.

---

## D. Program enrollment panel (e.g. DMHTN-2026A)

Include a row for **every** candidate from `GET /programs/{code}/candidates` (ascending
`patient_id`). Read chart freshness from `chart_artifacts.status` (current/stale); read chart
existence from `patients.existing_chart`.

**eligible** = `target_condition` is the program's condition (DMHTN ⇒ `diabetes_hypertension`)
**and** the patient's `chronic_conditions` include that condition. If the target condition is
wrong → `eligible=false`, reasons `wrong_target_condition` + `missing_active_dmhtn_diagnosis`.

**For ineligible candidates**, only emit eligibility reasons plus `consent_declined` (if
consent declined) and `chart_not_active` (if `existing_chart=0`); leave
`missing_chart_artifacts=[]`, `follow_up_cadence='none'`, package `not_applicable`,
`enrollment_status='reject'`. (Chart-artifact gaps are **not** enumerated for ineligibles.)

**For eligible candidates**, evaluate chart artifacts against the required set
{chart_record, active_problems, vitals, labs, medications, consent}:
- `existing_chart=0` → missing `chart_record` + reason `chart_not_active`.
- `active_problems` stale/absent → missing `active_problems` + `stale_active_problems`.
- `vitals` stale/absent → missing `vitals` + `missing_recent_vitals`.
- `labs` stale/absent → missing `labs` + `missing_recent_labs`.
- `medications` stale/absent → missing `medications` + `missing_medication_list`.
- consent not on file (`consent_status='missing'` / no consent artifact) → missing `consent`
  + `consent_missing`.

**enrollment_status:**
- `reject` — ineligible **or** `consent_status='declined'` (declined adds `consent_declined`;
  reasons also carry `chart_not_active` when `existing_chart=0`).
- `hold` — eligible but blocked by missing consent or missing/stale required chart artifacts.
- `enroll` — eligible, consent signed, chart active with all required artifacts current;
  reason `meets_dmhtn_criteria` plus one high-touch driver if applicable.

**High-touch driver** (choose one, precedence recent_hospitalization > recent_ed >
low_adherence): `recent_hospitalization=1` → `recent_hospitalization_high_touch`;
`risk_flags` contains recent ED → `recent_ed_high_touch`; low `adherence_score` (≈ <50) →
`low_adherence_high_touch`. CKD in `chronic_conditions` → `ckd_biweekly_monitoring`.

**follow_up_cadence:** enrolled → `weekly` if any high-touch driver, else `biweekly` if CKD,
else `monthly`. `hold` → `deferred`. `reject` → `none`.

**initial_monitoring_package:**
- high-touch/weekly → `high_touch_dm_htn`, components
  {bp_cuff, glucometer, lab_order_a1c_cmp_lipid, medication_reconciliation, care_plan_setup},
  `first_checkin_days=7`.
- biweekly (CKD) → `standard_dm_htn`, {bp_cuff, glucometer, lab_order_a1c_cmp_lipid,
  medication_reconciliation}, `first_checkin_days=14`.
- monthly → `standard_dm_htn`, {bp_cuff, glucometer, lab_order_a1c_cmp_lipid},
  `first_checkin_days=30`.
- hold → `deferred`, components {consent_packet (if consent missing), chart_update_request
  (if chart artifacts missing)}, `first_checkin_days=null`.
- reject → `not_applicable`, components [], `first_checkin_days=null`.

**outreach_channel** = the program `preferred_outreach` if that channel is reachable for the
patient, else fall back to the patient's `preferred_contact`. Reachability: `portal` needs
`existing_chart=1`; `phone`/`sms` need a non-null `phone`; `email` needs a non-null `email`.
Computed for every candidate (including rejects).

`summary`: `total_candidates`, `eligible_count`, `ineligible_count`, and `status_counts`,
`follow_up_counts`, `outreach_counts`, `monitoring_package_counts`, each keyed by its full
enum and reconciling with the rows.

---

## E. Referral-to-chart activation (e.g. PULM-* batch)

Pull `referrals` for the `batch_id`. Blocker codes here:
`clinical_code_discrepancy` (wrong service family OR narrative/clinical-reason mismatch),
`records_missing`, `imaging_missing`, `authorization_blocked`, `duplicate_review`,
`scheduled_before_clearance` (`appointment_scheduled=1` while not clear).

- `readiness_by_referral[]` (ascending `referral_id`): `{referral_id, patient_id,
  readiness_status, blocker_codes}`. Readiness precedence as in the shared rules; a lone
  `clinical_code_discrepancy` → `under_review`; any hard blocker → `blocked`.
- `clinical_code_discrepancy_referrals[]`: ids flagged for coding, ascending.
- `blocker_sets`: `authorization`, `records`, `imaging` — id lists, ascending.
- `duplicate_handling`: `duplicate_groups` (`{group_id, referral_ids, keep_referral_id}`) and
  `cleared_duplicate_review_referrals` (referrals reviewed for duplication and cleared).
- `ready_referral_chart_needs[]`: **only ready referrals**. `chart_action` =
  `create_chart` if `existing_chart=0`, `update_chart` if `existing_chart=1` with gaps,
  `no_chart_action` if fully current. `artifacts_to_create` = the artifact types from
  {demographics, active_problems, medications, allergies, vitals, labs, consent} whose
  chart_artifact is **not** `current` (stale or absent), sorted alphabetically.
- `correspondence_queue[]`: **non-ready referrals** needing office follow-up. `template_type`
  by precedence: `appointment_hold_notice` (already scheduled) > `auth_records_request`
  (auth/records) > `clinical_code_clarification` (coding) > `duplicate_resolution`.
  `reason_codes` (set) from {wrong_service_family, clinical_reason_mismatch, records_missing,
  authorization_denied, duplicate_review, appointment_already_scheduled}.
- `priority_order[]`: **non-ready referrals only**, `{rank, referral_id, priority_tier}`,
  rank starting at 1. Primary sort by tier (tier_1 < tier_2 < tier_3, per shared rule); break
  ties by putting time-sensitive already-scheduled referrals first, then ascending
  `referral_id`. Ready referrals are excluded.

Keep referral-id lists uppercase exactly as the portal returns them.
