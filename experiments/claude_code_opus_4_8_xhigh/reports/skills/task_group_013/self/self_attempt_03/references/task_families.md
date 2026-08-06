# Task-family playbooks

Each family maps portal data → the template's controlled vocabulary. Rules split
into two kinds:

- **Deterministic checks** — read directly from a structured field (present here
  as hard rules).
- **Policy rubrics** — thresholds/aggregations the portal does not expose (risk
  scoring, tiering, package composition, freshness windows). Apply the standard
  below **consistently** for every row, and keep every value inside the
  template's `allowed_values`. Where a task or payload states an explicit value,
  that overrides the standard.

Always: filter to the named target only; sort/emit exactly as the template says;
compute summary counts from the rows you emit; return JSON only.

---

## Family A — New-patient access verification (roster intake)

**Recognize:** template keys `roster_id`, `requested_service_date`,
`service_line`, `patient_results`, `cohort_summary`.

**Pull:** `intake_rosters WHERE roster_id=<target>` → gives each patient's
`requested_service_date` and `service_line` (use the roster's own recorded values
for the top-level fields; do not read the date from prose). Patient ids come from
the roster (and any `target_roster.json`). For each patient use `/patients/{id}`
(coverage, pbm, pharmacies, lifestyle, clinical_history, patient core).

Per patient (`patient_results`, ascending `patient_id`):

- **insurance_status** (enum valid|invalid|missing) from `coverage`:
  - `missing` — no coverage row.
  - `invalid` — `status` not `active`, OR `termination_date` < service_date, OR
    `effective_date` > service_date.
  - else `valid`.
- **prescription_status** (valid|invalid|missing) from `pbm`:
  - `missing` — no pbm row.
  - `invalid` — `active=0` OR `formulary_status != covered` OR `status != approved`,
    OR `pbm.policy_number != coverage.policy_number` (mismatch).
  - else `valid`.
- **pharmacy_status** (in_network|out_of_network|unknown): rank-1 preferred
  pharmacy's `network_status`; `unknown` if no preferred pharmacy.
- **lifestyle_risk** (low|medium|high) — *policy rubric*: count risk factors:
  current smoker; `alcohol_use = Heavy`; `exercise_frequency` None/null;
  `sleep_hours < 6`. 0 → low, 1–2 → medium, ≥3 → high.
- **overall_risk** (low|medium|high) — *policy rubric*: high if lifestyle_risk is
  high, OR `recent_hospitalization=1`, OR `risk_flags` non-empty, OR ≥3
  chronic_conditions; low if lifestyle low and none of those; else medium.
- **blocked_reason_codes** (unordered set; only template codes) — include each
  that applies:
  - `coverage_expired` — coverage terminated/expired before service_date (status
    `expired` or `termination_date` < service_date).
  - `coverage_pending` — coverage `status` pending, or `effective_date` after
    service_date.
  - `excluded_service_line` — coverage record valid but the roster's
    `service_line` is not in `coverage.service_lines`.
  - `pbm_missing` / `pbm_invalid` / `pbm_policy_mismatch` — per the pbm check
    above.
  - `pharmacy_out_of_network` / `pharmacy_unknown` — per pharmacy_status.
  - `missing_address` — `address` null/empty.
  - `emergency_contact_missing` — `emergency_contact_present=0`.
  - `preferred_contact_unavailable` — the channel named by `preferred_contact`
    lacks its contact datum: `email`→email null, `phone`→phone null, `sms`→phone
    null (`portal` is always available).
  - `overall_risk_high` — when `overall_risk = high`.
- **registration_status** (approved|hold|clinical_review|rejected) — *decision
  ladder*, first match wins:
  1. `rejected` — insurance missing/invalid OR `excluded_service_line`
     (no valid coverage for this service).
  2. `clinical_review` — `overall_risk = high`.
  3. `hold` — any administrative blocker present (pbm issue, pharmacy
     out/unknown, missing_address, emergency_contact_missing,
     preferred_contact_unavailable).
  4. `approved` — otherwise.

**cohort_summary:** `total_patients`; `counts_by_registration_status`
(approved/hold/clinical_review/rejected); `counts_by_overall_risk`
(low/medium/high); `counts_by_lifestyle_risk` (low/medium/high). All integers,
all keys present, reconcile with `patient_results`.

---

## Family B — Referral readiness audit (specialty batch)

**Recognize:** template keys `referral_reviews`, `icd_discrepancies`,
`duplicate_groups`, `shared_insurance_anomalies`, `blocker_sets`,
`ready_to_schedule`, `action_plan`, `summary`.

**Pull:** `referrals WHERE batch_id=<target>`; the batch's specialty =
`referrals.service_line`. Join each `icd10_code` to `icd_codes`.

Per-referral signals:
- **ICD discrepancy** — compare `icd_codes.service_family` of the code to the
  batch specialty. Mismatch (e.g. a `cardiology` code in a `pulmonary`/ortho
  batch) → `icd_chapter_mismatch`; record `observed_chapter` = the code's
  `chapter`, `expected_chapter` = the chapter block for the batch specialty.
  `narrative_mismatch` / `laterality_mismatch` fire only when a referral's
  narrative/reason actually names a condition or a side (left/right) that
  contradicts the code (generic descriptions like "specialty consultation" do
  **not** trigger these).
- **missing_records** — `records_received=0`.
- **missing_imaging** — `imaging_received=0`.
- **auth_blocker** — `auth_required=1` AND `auth_status != approved`; carry
  `auth_status` mapped to pending|denied|not_submitted.
- **already_scheduled** — `appointment_scheduled=1`.
- **duplicate_referral** — two+ referrals in the batch with the **same
  patient_id** (detect by patient_id, *not* by the `notes` text). Group them:
  `primary_referral_id` = lowest referral_id; `recommendation`
  `consolidate_to_primary` (same patient) vs `keep_separate`.
- **shared_insurance_anomaly** — same `insurance_id` across ≥2 referrals. Distinct
  patients → `verify_distinct_patient_policy_id`; same patient → the shared id is
  a `legitimate_duplicate_same_patient`.

**readiness_status** (ready|blocked|under_review|admin_followup):
- `blocked` — any clinical blocker (missing_records, missing_imaging,
  auth_blocker, icd/narrative/laterality mismatch).
- `under_review` — no clinical blocker but a duplicate or shared-insurance
  anomaly to verify.
- `admin_followup` — only `already_scheduled` / purely administrative.
- `ready` — none of the above.

**priority_tier** (referral_reviews: enum or `null`; ready → `null`):
- `tier_1_immediate` — `urgency=urgent` with a clinical blocker.
- `tier_2_short_term` — `urgency=routine` with a clinical blocker.
- `tier_3_administrative` — duplicate / shared-insurance / already-scheduled /
  auth-admin only.

**icd_discrepancies** (ascending referral_id): one row per referral with a code
issue: `{referral_id, icd10_code, issue_types[], observed_chapter,
expected_chapter}`.

**duplicate_groups** (ascending group_id): `{group_id, referral_ids[] asc,
patient_id, primary_referral_id, recommendation}`.

**shared_insurance_anomalies** (ascending insurance_id): `{insurance_id,
referral_ids[] asc, patient_ids[] asc, disposition}`.

**blocker_sets:** `missing_records` [referral_id…], `missing_imaging`
[referral_id…], `auth_blockers` [{referral_id, auth_status}] — all ascending.

**ready_to_schedule:** referral_ids with `readiness_status = ready`, ascending.

**action_plan** (ascending referral_id; every non-ready referral): `priority_tier`
+ `action_codes` (unordered set) mapped from its issues:
`request_corrected_icd` (icd mismatch), `confirm_narrative`, `confirm_laterality`,
`consolidate_duplicate`, `verify_insurance_id` (distinct-patient shared
insurance), `request_records`, `request_imaging`, `resolve_authorization`,
`review_existing_appointment` (already scheduled).

**summary:** `total_referrals`; `ready_to_schedule_count`; `follow_up_count`
(non-ready); `counts_by_urgency` {urgent, routine, admin} — bucket a referral as
`admin` when its readiness is `admin_followup` / its only issues are
administrative, else use its `urgency`; `counts_by_readiness_status` (all four);
`counts_by_urgency_and_status` (list ordered urgency then readiness_status, one
`{urgency, readiness_status, count}` per occurring combo); `issue_counts`
{icd_discrepancy_referrals, duplicate_groups, shared_insurance_anomalies,
missing_records_referrals, missing_imaging_referrals, auth_blocker_referrals}.

---

## Family C — Dialysis transfer review (packet + chair capacity)

**Recognize:** template keys `batch_id`, `patients` (rows keyed by `transfer_id`),
packet completeness/freshness, `requested_start`, `cohort_summary`.

**Pull:** `transfer_requests WHERE batch_id=<target>`; documents per transfer
(`/documents?transfer_id=` or the `/transfers/{id}` aggregator); facility_capacity
for each `requested_start_date`.

**Required packet items (15)** = the template's `missing_required_documents`
`allowed_values`: allergy_list, face_sheet, flu_vaccine, hbsag,
hep_b_antibody_core, history_physical, insurance_proof, medication_list,
monthly_labs, physician_orders, pneumonia_vaccine, ppd_or_cxr, transportation,
treatment_flowsheets, vascular_access_report.

- An item is **present** only if a document of that `doc_type` exists with
  `finalized=1`. Drafts (`finalized=0`) count as **not** received.
- `transportation` is satisfied by `transfer_requests.transportation` being
  non-null/non-empty (it is a packet requirement, not a document row).
- **missing_required_documents** = required set − present, sorted alphabetically.
- **packet_completeness_status** = `complete` if none missing, else `incomplete`.

**stale_documents** — only the freshness-tracked doc types {hbsag,
hep_b_antibody_core, history_physical, monthly_labs, ppd_or_cxr}. A present
(finalized) doc is stale when `received_date + freshness_limit_days <
requested_start_date`. Emit `{doc_type, received_date, freshness_limit_days}`,
sorted alphabetically by doc_type. *Policy rubric — Cedar Ridge freshness
windows (days):* history_physical 30, monthly_labs 30, hbsag 30,
hep_b_antibody_core 365, ppd_or_cxr 365. (If the portal ever exposes explicit
limits, prefer those.)

**requested_start** `{date, capacity_status, open_chairs_total, feasibility}`:
- `date` = `requested_start_date`.
- `open_chairs_total` = SUM(`open_chairs`) over all Cedar Ridge HD locations
  (CRIC-MAIN + CRIC-NORTH) in `facility_capacity` for that **exact** date; 0 if
  no rows (requested date not a clinic day).
- `capacity_status` = `available` if `open_chairs_total > 0` else `unavailable`.
- `feasibility`: `ready_on_requested_start` (packet complete & fresh AND capacity
  available); `packet_not_ready_capacity_available` (packet incomplete/stale,
  capacity available); `packet_not_ready_capacity_unavailable` (packet not ready
  AND capacity unavailable); `capacity_unavailable` (packet ready but capacity
  unavailable).

**final_intake_decision** (accept|hold|clinical_review) — *decision ladder*:
- `accept` — packet complete, no stale docs, and `feasibility =
  ready_on_requested_start`.
- `clinical_review` — a stale clinical doc or missing clinical item (labs, H&P,
  serologies/vaccines, vascular_access_report) needs clinician review.
- `hold` — otherwise blocked on administrative items (missing insurance_proof /
  transportation / face_sheet, or capacity unavailable).

**next_contact_owner / next_contact_route** — *policy mapping* (choose the top
applicable; `none`/`none` when accepted with nothing outstanding):
- missing/stale **clinical** docs → `clinical_nurse` / `fax_referring_facility`.
- missing **administrative** docs (insurance_proof, transportation, face_sheet)
  → `intake_coordinator` / `fax_referring_facility` (or `phone_patient` when the
  gap is patient-side, e.g. transportation).
- packet OK but **capacity** unavailable → `scheduling_coordinator` /
  `internal_queue`.
- accepted / ready → `none` / `none`.

**cohort_summary:** `total_transfers`; `complete_documents_count` (packets with
no missing item); `missing_document_patient_count`; `stale_document_patient_count`;
`capacity_available_count`; `requested_start_ready_count` (feasibility
`ready_on_requested_start`); `decision_counts` {accept, hold, clinical_review};
`next_contact_owner_counts` {clinical_nurse, intake_coordinator,
scheduling_coordinator, none}. Rows ordered ascending by `transfer_id`.

---

## Family D — Chronic-care program enrollment panel

**Recognize:** template keys `program_code`, `as_of_date`, `patients`, `summary`.

**Pull:** `/programs/{program_code}/candidates` (or `program_candidates WHERE
program_code=`). Emit **one row per current candidate**. For each candidate:
`chart_artifacts` + `clinical_history` (+ `/chart/{id}`). Set `as_of_date` to the
task's current date (`YYYY-MM-DD`) unless a payload specifies one.

**Program target condition** is implied by the program code (e.g. `DMHTN-*` =
`diabetes_hypertension`). A candidate whose `target_condition` differs is off-target.

Per candidate:
- **Off-target** — `target_condition` ≠ program target → `eligible=false`,
  `enrollment_status=reject`, reasons `wrong_target_condition` (+
  `missing_active_dmhtn_diagnosis`), package `not_applicable`, cadence `none`,
  `first_checkin_days=null`, outreach `none`.
- **Consent** — `declined` → reject, `consent_declined`. `missing` → hold,
  `consent_missing`.
- **Chart readiness** — required artifacts (status must be `current`):
  `active_problems`, `vitals`, `labs`, `medications`, `consent`, plus an active
  chart (`existing_chart`/chart present = `chart_record`). Populate
  `missing_chart_artifacts` (subset of {chart_record, active_problems, vitals,
  labs, medications, consent}) and reasons: `chart_not_active` (no active chart),
  `stale_active_problems` (active_problems `stale`), `missing_recent_vitals`,
  `missing_recent_labs`, `missing_medication_list`. Any chart gap → `hold`
  (deferred), unless already rejected above.
- **Enroll** — on-target, consent `signed`, chart complete → `eligible=true`,
  `enrollment_status=enroll`, reason `meets_dmhtn_criteria`.
- **follow_up_cadence** (weekly|biweekly|monthly|deferred|none) & high-touch
  reasons — *policy rubric* (for enrolled): `weekly` if `adherence_score < 50`
  (`low_adherence_high_touch`), or `recent_hospitalization=1`
  (`recent_hospitalization_high_touch`), or recent ED (`recent_ed_high_touch`);
  `biweekly` if CKD in `chronic_conditions` (`ckd_biweekly_monitoring`); else
  `monthly`. Hold → `deferred`; reject → `none`.
- **initial_monitoring_package** `{package_type, components, first_checkin_days}`:
  - `high_touch_dm_htn` (enroll + any high-touch reason): components bp_cuff,
    glucometer, lab_order_a1c_cmp_lipid, medication_reconciliation,
    care_plan_setup.
  - `standard_dm_htn` (enroll, routine): bp_cuff, glucometer,
    lab_order_a1c_cmp_lipid, care_plan_setup.
  - `deferred` (hold): components addressing the gap (e.g. consent_packet,
    chart_update_request).
  - `not_applicable` (reject): components `[]`.
  - `first_checkin_days`: weekly→7, biweekly→14, monthly→30; deferred/none→`null`.
- **outreach_channel** = candidate `preferred_outreach` (phone|portal|email|sms);
  `none` when rejected / no outreach planned.

**summary:** `total_candidates`, `eligible_count`, `ineligible_count`,
`status_counts` {enroll,hold,reject}, `follow_up_counts`
{weekly,biweekly,monthly,deferred,none}, `outreach_counts`
{phone,portal,sms,email,none}, `monitoring_package_counts`
{standard_dm_htn,high_touch_dm_htn,deferred,not_applicable}. Rows ascending by
`patient_id`.

---

## Family E — Referral-to-chart activation

**Recognize:** template keys `readiness_by_referral`,
`clinical_code_discrepancy_referrals`, `blocker_sets`
{authorization,records,imaging}, `duplicate_handling`,
`ready_referral_chart_needs`, `correspondence_queue`, `priority_order`.

**Pull:** `referrals WHERE batch_id=<target>`; icd_codes; patient/chart for ready
referrals. Blocker detection mirrors Family B, mapped to this template's codes.

**readiness_by_referral** (ascending referral_id): `{referral_id, patient_id,
readiness_status, blocker_codes[]}` where blocker_codes ⊆
{clinical_code_discrepancy, records_missing, imaging_missing,
authorization_blocked, duplicate_review, scheduled_before_clearance}:
- `clinical_code_discrepancy` — `icd_codes.service_family` ≠ batch specialty (e.g.
  cardiology code in a pulmonary batch). Add the referral to
  `clinical_code_discrepancy_referrals`.
- `records_missing` — `records_received=0`.
- `imaging_missing` — `imaging_received=0`.
- `authorization_blocked` — `auth_required=1` AND `auth_status != approved`.
- `duplicate_review` — same-patient duplicate pending resolution.
- `scheduled_before_clearance` — `appointment_scheduled=1` before clearance.
- **readiness_status:** `blocked` (records/imaging/auth/code), `under_review`
  (duplicate_review), `admin_followup` (scheduled_before_clearance), else `ready`.

**blocker_sets:** `authorization`, `records`, `imaging` — referral_id lists,
ascending.

**duplicate_handling:** `duplicate_groups` (ascending group_id) each
`{group_id, referral_ids[] asc, keep_referral_id}` (keep = lowest referral_id);
`cleared_duplicate_review_referrals` = referrals flagged as possible duplicates
(e.g. by `notes`) that turn out **not** to be true same-patient duplicates.

**ready_referral_chart_needs** (ascending referral_id; ready referrals): `{referral_id,
patient_id, chart_action, artifacts_to_create}`:
- `chart_action`: `create_chart` if patient has no active chart
  (`existing_chart=0`); `update_chart` if chart exists but artifacts are
  missing/stale; `no_chart_action` if fully current.
- `artifacts_to_create` ⊆ {demographics, active_problems, medications, allergies,
  vitals, labs, consent}, **sorted alphabetically**. For a new chart, list the
  core set to build; for an update, the missing/stale ones.

**correspondence_queue** (ascending referral_id; referrals needing outreach):
`{referral_id, template_type, reason_codes[]}`:
- `template_type`: `clinical_code_clarification` (code discrepancy),
  `auth_records_request` (auth/records/imaging gap), `duplicate_resolution`
  (duplicate), `appointment_hold_notice` (scheduled before clearance).
- `reason_codes` ⊆ {wrong_service_family, clinical_reason_mismatch,
  records_missing, authorization_denied, duplicate_review,
  appointment_already_scheduled}.

**priority_order** (highest priority first; **non-ready referrals only**):
`{rank (1..n), referral_id, priority_tier}` with
`tier_1_immediate` (urgent clinical blocker), `tier_2_short_term` (routine
clinical blocker), `tier_3_administrative` (duplicate / auth-admin /
scheduled-before-clearance). Rank tier_1 before tier_2 before tier_3.
