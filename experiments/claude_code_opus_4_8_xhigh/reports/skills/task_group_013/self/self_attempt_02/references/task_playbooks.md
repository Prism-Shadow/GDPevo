# Per-archetype playbooks

Each section: what to pull, how to classify each item, and how to roll up. The
**controlled vocabulary in the task's `answer_template.json` is authoritative** —
these rules map data conditions onto those code names, which are self-describing.
Where a numeric threshold is a judgement call, it is flagged; keep it consistent
across all members and make the summary reconcile.

Reference date per archetype: **A** = roster `requested_service_date`;
**B** = `date_received` / "today" for scheduling checks; **C** = transfer
`requested_start_date`; **D** = program `candidate_date` (as-of).

---

## A. Primary-care access verification (roster → `patient_results`)

Pull the roster: `SELECT patient_id, requested_service_date, service_line FROM
intake_rosters WHERE roster_id = ?` — this fixes the member list and the output's
`requested_service_date` + `service_line`. For each member join `coverage`,
`pbm`, top-ranked `patient_pharmacy`+`pharmacies`, `lifestyle`, `patients`.

**insurance_status** (`valid`|`invalid`|`missing`):
- no coverage row → `missing`.
- `status='active'` AND requested `service_line` ∈ `service_lines` AND
  `network_status='in_network'` AND `effective_date ≤ service_date ≤
  termination_date` → `valid`.
- `status='expired'` or `termination_date < service_date` → `invalid`
  (+ `coverage_expired`).
- `status='pending'` → not yet effective → `invalid`/hold-driving
  (+ `coverage_pending`).
- requested `service_line` ∉ `service_lines` → `invalid` (+ `excluded_service_line`).
- `network_status='out_of_network'` → `invalid`.

**prescription_status** (`valid`|`invalid`|`missing`) from `pbm`:
- no pbm row → `missing` (+ `pbm_missing`).
- `active=1` AND `formulary_status='covered'` AND `status='approved'` → `valid`.
- `status='rejected'` / `formulary_status='not_found'` / `active=0` → `invalid`
  (+ `pbm_invalid`).
- `formulary_status='review'` / `status='pending'` → pending → hold-driving.
- PBM payer/policy not reconciling with the medical `coverage` payer/policy →
  `pbm_policy_mismatch`.

**pharmacy_status** (`in_network`|`out_of_network`|`unknown`) from the
`preference_rank=1` pharmacy:
- no preferred pharmacy → `unknown` (+ `pharmacy_unknown`).
- top pharmacy `network_status='out_of_network'` → `out_of_network`
  (+ `pharmacy_out_of_network`).
- else → `in_network`.

**lifestyle_risk** (`low`|`medium`|`high`): score the lifestyle factors and
bucket. Higher risk from `smoking_status='Current'`, `alcohol_use='Heavy'`,
`exercise_frequency` `None`/NULL, low `sleep_hours` (e.g. <6). A common,
consistent scheme: +1 per adverse factor → 0–1 `low`, 2 `medium`, ≥3 `high`
(`Former` smoking and `Moderate` alcohol are mild). Keep whatever scheme you
pick uniform across the cohort.

**overall_risk** (`low`|`medium`|`high`): combine lifestyle risk with
access/eligibility problems (expired/pending coverage, invalid/missing PBM,
excluded service line). Hard eligibility failures or `lifestyle_risk='high'`
push toward `high`; a single soft issue → `medium`; clean → `low`. When
`overall_risk='high'`, add `overall_risk_high` to blocked codes.

**blocked_reason_codes** — the set of every condition that is true, from the
template's allowed list. Patient-data codes: `missing_address`
(`patients.address` NULL); `emergency_contact_missing`
(`emergency_contact_present=0`); `preferred_contact_unavailable` (the channel in
`preferred_contact` has no value — e.g. `email` preferred but `email` NULL,
`phone`/`sms` preferred but `phone` NULL, `mail` preferred but `address` NULL).

**registration_status** (`approved`|`hold`|`clinical_review`|`rejected`):
- hard eligibility failure (`coverage_expired`, `excluded_service_line`,
  `pbm_invalid`/`pbm_missing`) → `rejected`.
- clinical concern (`overall_risk_high`) with no hard eligibility failure →
  `clinical_review`.
- recoverable admin gaps only (`coverage_pending`, PBM review, pharmacy OON,
  missing address/contact) → `hold`.
- nothing blocking → `approved`.
Resolve to the single worst applicable status.

**cohort_summary:** `total_patients` = member count; `counts_by_registration_status`
over {approved,hold,clinical_review,rejected}; `counts_by_overall_risk` and
`counts_by_lifestyle_risk` over {low,medium,high}. Each must sum to the total.

---

## B. Referral readiness / chart activation (batch → per-referral)

Pull the batch: `SELECT * FROM referrals WHERE batch_id = ? ORDER BY
referral_id`, and the ICD rows for the codes used. Two template variants share
this data (see below). Per-referral issue signals:

- **ICD / clinical-code discrepancy** — join `icd10_code` → `icd_codes`:
  - `icd_chapter_mismatch` / wrong service family: the code's `service_family`
    ≠ the batch/referral `service_line` (e.g. a cardiology `I25.10` on a
    pulmonary referral). (Chapter vs. expected chapter for that specialty.)
  - `laterality_mismatch`: the code carries a `laterality` (left/right) that
    conflicts with the laterality stated in the referral narrative
    (`diagnosis_description`/`referral_reason`).
  - `narrative_mismatch`: the narrative text is inconsistent with the code's
    clinical meaning / referral reason for that specialty.
  In the activation variant these collapse into a single
  `clinical_code_discrepancy` blocker; in correspondence they map to
  `wrong_service_family` / `clinical_reason_mismatch`.
- **missing_records / records_missing**: `records_received=0`.
- **missing_imaging / imaging_missing**: `imaging_received=0`.
- **auth_blocker / authorization_blocked**: `auth_required=1` AND `auth_status`
  ∈ {`pending`,`denied`} (or `not_submitted`). Report `auth_status`
  (`pending`|`denied`|`not_submitted`) where the template asks.
- **already_scheduled / scheduled_before_clearance**: `appointment_scheduled=1`
  (with an `appointment_date`). In the activation variant, a scheduled referral
  that still has open blockers is `scheduled_before_clearance`.
- **duplicate_referral / duplicate_review**: two+ referrals in the batch for the
  **same `patient_id`** (same clinical intent, typically same `insurance_id`).
  Group them; keep one primary (lowest `referral_id`), recommend
  `consolidate_to_primary` / set `keep_referral_id`; the non-kept members carry
  the duplicate code.
- **shared_insurance_anomaly**: the same `insurance_id` used by referrals for
  **different `patient_id`s** (e.g. a shared/placeholder `DUP-INS-…`).
  Disposition `verify_distinct_patient_policy_id` when patients differ;
  `legitimate_duplicate_same_patient` when it's the same patient.

**readiness_status** (`ready`|`blocked`|`under_review`|`admin_followup`):
- clean (records+imaging in, auth ok, no discrepancy, not a stale duplicate,
  not prematurely scheduled) → `ready`.
- hard blocker (auth denied/pending, missing records/imaging, code discrepancy)
  → `blocked`.
- needs clinical judgement (e.g. narrative/laterality ambiguity) →
  `under_review`.
- clerical only (duplicate consolidation, shared-insurance verification,
  reviewing an existing appointment) → `admin_followup`.

**priority_tier**: urgent+blocked clinical → `tier_1_immediate`; routine
substantive follow-up → `tier_2_short_term`; clerical/administrative →
`tier_3_administrative`. (Batch-audit template allows `null` for ready items.)

**action_codes / correspondence** map 1:1 to issues: `request_corrected_icd`,
`confirm_narrative`, `confirm_laterality`, `consolidate_duplicate`,
`verify_insurance_id`, `request_records`, `request_imaging`,
`resolve_authorization`, `review_existing_appointment` (audit variant);
templates `clinical_code_clarification` / `auth_records_request` /
`duplicate_resolution` / `appointment_hold_notice` with reason codes
(activation variant).

**Batch-audit variant** (top keys include `referral_reviews`,
`icd_discrepancies`, `duplicate_groups`, `shared_insurance_anomalies`,
`blocker_sets`, `ready_to_schedule`, `action_plan`, `summary`): emit each list
sorted as specified; `ready_to_schedule` = referrals with `readiness='ready'`;
`summary` includes `total_referrals`, `ready_to_schedule_count`,
`follow_up_count` (= not ready), `counts_by_urgency`
({urgent,routine,admin} — `admin` = admin-followup items),
`counts_by_readiness_status`, `counts_by_urgency_and_status` (enumerate the
urgency×status grid in order), and `issue_counts`.

**Activation variant** (top keys include `readiness_by_referral`,
`clinical_code_discrepancy_referrals`, `blocker_sets`
{authorization,records,imaging}, `duplicate_handling`
{duplicate_groups, cleared_duplicate_review_referrals},
`ready_referral_chart_needs`, `correspondence_queue`, `priority_order`):
- `ready_referral_chart_needs`: for referrals cleared to proceed, set
  `chart_action` = `create_chart` if `patients.existing_chart=0`,
  `update_chart` if `=1` but artifacts need refresh, else `no_chart_action`;
  `artifacts_to_create` = the missing chart artifacts (alphabetized) from
  {demographics,active_problems,medications,allergies,vitals,labs,consent}.
- `priority_order`: **non-ready referrals only**, highest priority first,
  `rank` starting at 1, each with a `priority_tier`.

---

## C. Dialysis transfer packet review (batch → per-transfer)

Pull `SELECT * FROM transfer_requests WHERE batch_id = ? ORDER BY transfer_id`,
each patient's `documents` (`content_tag='transfer_packet'`), and
`facility_capacity` for `in_center_hemodialysis`.

**Required packet items** = the template's `missing_required_documents`
`allowed_values` list (15 items incl. `transportation`). Derive the required set
from the template, not from memory.

**packet_completeness_status / missing_required_documents:** an item is present
only if a matching finalized document exists (`finalized=1`/`status='final'`).
`draft`/absent → missing. **`transportation`** is satisfied by
`transfer_requests.transportation` being non-null (it's a request field, not a
document). List every missing required item, **alphabetical by code**; status is
`complete` iff none missing.

**stale_documents:** only these doc types carry a freshness window (per the
template's `stale_documents.doc_type` allowed set): `monthly_labs`,
`history_physical`, `hbsag`, `hep_b_antibody_core`, `ppd_or_cxr`. A present
(finalized) doc is stale when `requested_start_date − received_date` (in days)
exceeds the doc type's `freshness_limit_days`. Emit `{doc_type, received_date,
freshness_limit_days}`, **alphabetical by doc_type**, and output the limit you
used. Use standard dialysis-packet windows — short recurring items (monthly
labs, H&P) have short windows (~30 days); serology/TB screens are ~annual (~365
days). *These specific day counts are a domain constant, not visible in the DB;
apply one consistent window per doc type across the whole cohort.*

**requested_start** object: `date` = `requested_start_date`; `open_chairs_total`
= sum of `open_chairs` across all locations for that date +
`in_center_hemodialysis`; `capacity_status` = `available` if
`open_chairs_total > 0` else `unavailable`; `feasibility`:
- packet complete AND capacity available → `ready_on_requested_start`.
- packet incomplete AND capacity available → `packet_not_ready_capacity_available`.
- packet incomplete AND capacity unavailable → `packet_not_ready_capacity_unavailable`.
- packet complete but capacity unavailable → `capacity_unavailable`.

**final_intake_decision** (`accept`|`hold`|`clinical_review`): fully ready
(complete, fresh, capacity) → `accept`; missing/stale docs or capacity gap →
`hold`; clinical-safety concerns (e.g. stale serology/vascular access issues
needing nurse review) → `clinical_review`.

**next_contact_owner / next_contact_route:** choose the owner responsible for
the top gap and a matching route:
- missing clinical docs / stale serology → `clinical_nurse`, route
  `fax_referring_facility`.
- missing administrative packet items → `intake_coordinator`, route
  `fax_referring_facility` or `internal_queue`.
- packet ready but capacity/scheduling gap → `scheduling_coordinator`, route
  `internal_queue` (or `phone_patient`).
- fully accepted, nothing needed → `none`, route `none`.

**cohort_summary:** `total_transfers`; `complete_documents_count` (packets with
no missing items); `missing_document_patient_count`; `stale_document_patient_count`;
`capacity_available_count`; `requested_start_ready_count`
(feasibility=`ready_on_requested_start`); `decision_counts`
{accept,hold,clinical_review}; `next_contact_owner_counts`
{clinical_nurse,intake_coordinator,scheduling_coordinator,none}. All must
reconcile with the rows.

---

## D. Chronic-care program enrollment (program → per-candidate)

Pull `GET /programs/{program_code}/candidates` (or `SELECT * FROM
program_candidates WHERE program_code = ?`) — **one output row per candidate
returned**, sorted by `patient_id`. For each candidate get `GET /chart/{patient_id}`
(bundles `clinical_history` + `chart_artifacts`). Reference date = `candidate_date`.

**Target-condition eligibility:** the program encodes a target condition
(DMHTN = diabetes + hypertension). If `target_condition` ≠ the program's
condition, or the patient's active problems lack the required diagnosis →
`wrong_target_condition` / `missing_active_dmhtn_diagnosis`, `eligible=false`.

**Chart readiness → `missing_chart_artifacts`** (from {chart_record,
active_problems, vitals, labs, medications, consent}) and matching reason codes:
- no chart / `patients.existing_chart=0` or no artifacts → `chart_record` +
  `chart_not_active`.
- `active_problems` missing or `status='stale'` → `active_problems` +
  `stale_active_problems`.
- `vitals` not `current` (stale/draft/absent) → `vitals` + `missing_recent_vitals`.
- `labs` not `current` → `labs` + `missing_recent_labs`.
- `medications` not `current`/absent → `medications` + `missing_medication_list`.
- `consent` artifact absent and consent needed → `consent`.

**Consent** (`program_candidates.consent_status`): `declined` →
`consent_declined` (reject); `missing` → `consent_missing` (hold, gather
consent); `signed` → ok.

**High-touch flags** (drive cadence + package, add reason codes):
`recent_hospitalization=1` → `recent_hospitalization_high_touch`; `risk_flags`
contains `recent_ed_visit` → `recent_ed_high_touch`; low `adherence_score`
(e.g. <50) → `low_adherence_high_touch`; `chronic_conditions` contains `ckd` →
`ckd_biweekly_monitoring`. A clean, eligible candidate → `meets_dmhtn_criteria`.

**eligible / enrollment_status** (`enroll`|`hold`|`reject`):
- wrong condition / missing diagnosis, or `consent_declined` → `reject`,
  `eligible=false`.
- eligible but blocked on consent-missing or missing chart artifacts → `hold`.
- eligible, consented, chart adequate → `enroll`.

**follow_up_cadence** (`weekly`|`biweekly`|`monthly`|`deferred`|`none`):
enrolled high-touch (recent hospitalization/ED, low adherence) → `weekly`; CKD
monitoring → `biweekly`; standard enrolled → `monthly`; `hold` → `deferred`;
`reject` → `none`.

**outreach_channel** (`phone`|`portal`|`sms`|`email`|`none`) =
`preferred_outreach` when enrolling/holding; `none` when rejected or the channel
is unusable.

**initial_monitoring_package:**
- `package_type`: `standard_dm_htn` (enroll, no high-touch), `high_touch_dm_htn`
  (enroll + any high-touch flag), `deferred` (hold), `not_applicable` (reject).
- `components` (subset, unordered) from {bp_cuff, glucometer,
  lab_order_a1c_cmp_lipid, medication_reconciliation, care_plan_setup,
  consent_packet, chart_update_request}: DM/HTN enrollees get `bp_cuff`,
  `glucometer`, `lab_order_a1c_cmp_lipid`, `medication_reconciliation`,
  `care_plan_setup`; add `consent_packet` when consent is missing/needed and
  `chart_update_request` when chart artifacts are missing/stale. Reject → empty
  or minimal.
- `first_checkin_days` (int or null): matches cadence — weekly ≈ 7,
  biweekly ≈ 14, monthly ≈ 30; `null` for deferred/rejected (no active start).

**summary:** `total_candidates`, `eligible_count`, `ineligible_count`,
`status_counts` {enroll,hold,reject}, `follow_up_counts`
{weekly,biweekly,monthly,deferred,none}, `outreach_counts`
{phone,portal,sms,email,none}, `monitoring_package_counts`
{standard_dm_htn,high_touch_dm_htn,deferred,not_applicable}. All reconcile with
the rows; include zero-valued keys.
