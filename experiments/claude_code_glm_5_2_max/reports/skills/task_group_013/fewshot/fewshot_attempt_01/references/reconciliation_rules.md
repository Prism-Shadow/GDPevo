# Reconciliation Rules

Generic, reusable detection rules for the issue / code classes the templates use. These describe
**method**, keyed to portal fields — never hard-code a result. Always confirm the code/status you
assign exists in the current task's `answer_template.json` `allowed_values` before emitting it.

The rule families below cover the five task archetypes (access verification, referral readiness
audit, transfer packet review, program enrollment panel, referral-to-chart activation). A given
task uses only the families its template references.

---

## A. Clinical-code discrepancy (referral tasks)

Fetch `GET /icd/{referral.icd10_code}` (or use the `icd` block from
`GET /referrals/{referral_id}`).

- **Service-family / chapter mismatch.** Determine the service family the batch expects from the
  batch context and `referral.service_line`. Compare to `icd.service_family` (and `icd.chapter`
  to the chapter range expected for that service line). If they disagree, flag a chapter /
  service-family discrepancy. Record `observed_chapter = icd.chapter` and `expected_chapter` =
  the chapter appropriate to the expected service line.
- **Narrative mismatch.** Compare `icd.description` against `referral.diagnosis_description` and
  `referral.referral_reason`. If they describe different anatomy or pathology, flag a narrative
  mismatch.
- **Laterality mismatch.** Compare `icd.laterality` to the laterality implied by
  `referral.diagnosis_description` / `referral.referral_reason`. If the code is laterality-specific
  and the narrative implies the opposite side (or vice-versa), flag a laterality mismatch.

The exact issue-type codes come from the template (e.g. an `icd_chapter_mismatch`,
`narrative_mismatch`, `laterality_mismatch` set, or a single `clinical_code_discrepancy` blocker).
Collect every referral with any such issue into the template's discrepancy list, ordered ascending
by `referral_id`.

## B. Duplicates & shared-insurance anomalies (referral tasks)

Use `POST /query` to group the in-scope referrals:

- **Duplicate referrals.** Group by `patient_id` (and overlapping clinical intent — same/adjacent
  `icd10_code` or `referral_reason`). Two or more referrals for the same patient with overlapping
  intent form a duplicate group. Choose the **primary** as the earliest `date_received` (tie-break
  lowest `referral_id`). Recommendation is `consolidate_to_primary` unless the referrals are
  clinically distinct, in which case `keep_separate`. Group ids / `keep_referral_id` follow the
  template's naming and ordering.
- **Shared-insurance anomaly.** Group in-scope referrals by `insurance_id`. If one `insurance_id`
  appears on referrals for **more than one distinct `patient_id`**, flag it as
  `verify_distinct_patient_policy_id`. If it appears on multiple referrals for the **same**
  `patient_id`, flag it as `legitimate_duplicate_same_patient`. Collect the `referral_ids` and
  `patient_ids` for each, ordered ascending.

## C. Records, imaging, authorization, scheduling (referral tasks)

- **Missing records.** `referral.records_received` is `0` (or absent) → missing-records blocker.
- **Missing imaging.** `referral.imaging_received` is `0` (or absent) when imaging is expected for
  the service line → missing-imaging blocker.
- **Authorization blocker.** `referral.auth_required == 1` and `auth_status` is one of the
  non-final statuses the template lists (e.g. `pending`, `denied`, `not_submitted`) → auth blocker.
  Record the `auth_status` where the template asks for it.
- **Already scheduled.** `referral.appointment_scheduled == 1` → an "already scheduled" issue;
  this usually routes the referral to review rather than ready, and may trigger a
  review-existing-appointment action.

## D. Readiness status & priority (referral tasks)

Derive `readiness_status` per referral using a precedence that matches the template's allowed set.
Typical precedence (most-blocking first):

1. **blocked** — a hard blocker is present (missing records, missing imaging, authorization
   blocker).
2. **under_review** — a clinical-code discrepancy, a duplicate awaiting consolidation, or an
   already-scheduled appointment needing review.
3. **admin_followup** — an administrative issue only (shared-insurance anomaly, duplicate
   admin).
4. **ready** — no issues.

A referral with **no issues and no blockers** is `ready` and goes in the
`ready_to_schedule` / `ready_referral_chart_needs` list.

`priority_tier` follows urgency + issue severity (use the template's allowed tiers):

- **tier_1_immediate** — urgent referral with a clinical-code discrepancy.
- **tier_2_short_term** — routine clinical discrepancy, missing records/imaging, or authorization
  blocker.
- **tier_3_administrative** — administrative-only issue (shared insurance, duplicate admin).

`priority_order` (where the template has one) ranks **non-ready** referrals highest-priority
first: order by `priority_tier` (tier_1 before tier_2 before tier_3), then by urgency within a
tier, and assign `rank` starting at 1.

Action / correspondence codes map one-to-one from the issues found on a referral
(request corrected ICD, confirm narrative/laterality, consolidate duplicate, verify insurance,
request records, request imaging, resolve authorization, review existing appointment, etc.). Emit
only codes the template lists.

## E. Access verification (roster / new-patient tasks)

For each patient on the roster, use `GET /patients/{patient_id}`:

- **insurance_status** — from `coverage[]`: `valid` when there is an active row whose
  `service_lines` contains the roster's service line, `effective_date` is in the past, and
  `termination_date` is in the future; `invalid` when a row exists but is expired/terminated or
  excludes the service line; `missing` when no coverage row exists.
- **prescription_status** — from `pbm[]`: `valid` when a row is `active`, `status` approved, and
  `formulary_status` covered; `invalid` when a row exists but is not approved/covered (or policy
  mismatch); `missing` when no `pbm` row exists.
- **pharmacy_status** — from the preferred pharmacy row (`preference_rank` lowest): `in_network` /
  `out_of_network` from `network_status`; `unknown` when no preferred pharmacy.
- **lifestyle_risk** — from `lifestyle` (`smoking_status`, `alcohol_use`, `exercise_frequency`,
  `sleep_hours`) banded into `low` / `medium` / `high` per the template.
- **overall_risk** — combines `lifestyle_risk` with `clinical_history.risk_flags` and
  `recent_hospitalization` into `low` / `medium` / `high`.
- **registration_status** + **blocked_reason_codes** — derived from the combination of the above
  plus identity gaps (`address` missing, `emergency_contact_present == 0`, `preferred_contact`
  unavailable, `service_line` excluded by coverage). `approved` = no blockers and low/medium risk;
  `clinical_review` = high overall risk or a clinical/policy flag without a hard exclusion;
  `rejected` = a hard exclusion (e.g. coverage expired, service line excluded); `hold` = a
  pending/fixable blocker. Emit only the reason codes the template lists; the set is unordered.

## F. Transfer packet & capacity (transfer tasks)

For each transfer in the batch, use `GET /transfers/{transfer_id}` and the `documents`
collection:

- **Packet completeness.** The template lists the required document set. A required document is
  present only if a `documents[]` row with that `doc_type` is linked to the `transfer_id` and is
  finalized (per the document's `status`/`finalized`). Any missing required document →
  `incomplete`, and list them in `missing_required_documents` (alphabetical by code).
- **Stale documents.** For doc types that carry a freshness limit, compute age from
  `received_date` against the task's "as of" date. If age exceeds the freshness limit (days), add
  a `stale_documents` entry `{ doc_type, received_date, freshness_limit_days }` (alphabetical by
  `doc_type`). Staleness can apply even when the packet is otherwise complete.
- **Capacity feasibility.** From the transfer's `capacity[]` rows, sum `open_chairs` across all
  `location_id`s for `requested_start_date` → `open_chairs_total`.
  `capacity_status` = `available` if that total > 0, else `unavailable`.
- **feasibility** — combine packet readiness with capacity per the template's four-value enum
  (ready-on-requested-start vs. packet-not-ready with capacity available/unavailable vs.
  capacity-unavailable).
- **final_intake_decision / next_contact_owner / next_contact_route** — driven by packet readiness
  and capacity per the template's allowed enums; a not-ready packet or unavailable capacity routes
  to clinical review and the referring-facility route.

## G. Program eligibility & enrollment (program tasks)

For each candidate from `GET /programs/{program_code}/candidates`, also pull
`GET /patients/{patient_id}` and `GET /chart/{patient_id}`:

- **eligible** — `target_condition` matches the program's target **and** an active target-condition
  diagnosis is present in the chart (`active_problems` / `clinical_history.chronic_conditions`)
  **and** `consent_status` is signed **and** the chart is active (`existing_chart` / chart
  artifacts present). Wrong target condition or missing active diagnosis → not eligible.
- **enrollment_status** — `enroll` (eligible, consent signed, chart active); `hold` (eligible but
  missing consent or chart artifacts that can be remediated); `reject` (consent declined, wrong
  target condition, or missing active diagnosis).
- **reason_codes** — from the template's set (meets-criteria, recent hospitalization / ED /
  low-adherence high-touch, CKD biweekly, consent declined/missing, chart not active, stale active
  problems, missing recent vitals/labs/medication list, wrong target condition, missing active
  diagnosis). The set is unordered.
- **follow_up_cadence** — high-touch flags (recent hospitalization, recent ED, low adherence) →
  weekly; CKD → biweekly; standard eligible → monthly; hold → deferred; reject → none.
- **missing_chart_artifacts** — from `/chart` gaps (chart_record, active_problems, vitals, labs,
  medications, consent), unordered.
- **outreach_channel** — from `candidate.preferred_outreach` (phone/portal/sms/email), `none` for
  rejects with no channel.
- **initial_monitoring_package** — `high_touch_dm_htn` for high-touch cadence, `standard_dm_htn`
  for standard, `deferred` for holds, `not_applicable` for rejects; `components` and
  `first_checkin_days` follow the cadence (weekly → 7, biweekly → 14, monthly → 30; null for
  deferred/not_applicable).

## H. Chart activation (referral-to-chart tasks)

For each **ready** referral, compare the referral + patient data to `GET /chart/{patient_id}`:

- **chart_action** — `create_chart` if the patient has no existing chart; `update_chart` if a chart
  exists but is missing artifacts the referral requires; `no_chart_action` if the chart already
  has everything.
- **artifacts_to_create** — the missing artifact enums (demographics, active_problems,
  medications, allergies, vitals, labs, consent), alphabetical by the artifact enum string.

Non-ready referrals get a **correspondence_queue** entry: choose `template_type` from the referral's
blockers (clinical-code clarification, auth/records request, duplicate resolution, appointment-hold
notice) and `reason_codes` from the template's set (wrong service family, clinical-reason
mismatch, records missing, authorization denied, duplicate review, appointment already
scheduled), unordered.
