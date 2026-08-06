# Decision-rule library

Rules below are grouped by task family. Each family = detect boolean flags from
the raw fields, then map the flag set to the template's enums and reason-code
lists. Map every reason/blocker code the template lists to a concrete data
signal before you start — an enum value that never fires and one that should
have fired are equally wrong.

Confidence key: **[firm]** = validated detection rule; **[tune]** = the direction
is right but the exact threshold / tie-break should be read off the template's
enum names and the cohort's data spread.

---

## A. New-patient access verification (roster → per-patient statuses)

Reference values come from the roster row: `requested_service_date`,
`service_line`. Per patient produce insurance / prescription / pharmacy status,
lifestyle & overall risk, a registration status, and a blocked-reason-code set.

**insurance_status** [firm]
- `missing` if no coverage row.
- Else `valid` only if ALL of: coverage `status` active; `network_status`
  in_network; `requested_service_date` within `effective_date`..`termination_date`;
  and `service_line` is in the coverage `service_lines` list.
- Otherwise `invalid`, and add the reason(s):
  - `coverage_expired` — status expired/terminated OR `termination_date` < service date.
  - `coverage_pending` — status pending.
  - `excluded_service_line` — active, in-date coverage but the requested
    `service_line` is not in `service_lines`.

**prescription_status** [firm] (from `pbm`)
- `missing` / `pbm_missing` if no row.
- `invalid` + `pbm_policy_mismatch` if `pbm.policy_number != coverage.policy_number`.
- `invalid` + `pbm_invalid` if not (`active`=1 AND `formulary_status`=covered AND
  `status`=approved) — i.e. rejected, not_found, review, pending, inactive.
- else `valid`.

**pharmacy_status** [firm] — network_status of the rank-1 preferred pharmacy →
`in_network` / `out_of_network`; no preferred pharmacy → `unknown`.
Add `pharmacy_out_of_network` / `pharmacy_unknown` accordingly.

**Demographic blockers** [firm]
- `emergency_contact_missing` — `emergency_contact_present`=0.
- `missing_address` — address null/empty.
- `preferred_contact_unavailable` — the preferred channel's backing field is
  empty (`email` preferred but no email; `phone`/`sms` preferred but no phone).

**lifestyle_risk** [tune] — points model: smoking Current=2 / Former=1 / Never=0;
alcohol Heavy=2 / Moderate=1 / else 0; exercise `None` or null = +1; sleep_hours
< 6 = +1. Bands: **medium = 2–3** (validated); low = 0–1; high = 4+ (high cutoff
is the uncertain part — 4 vs 5).

**overall_risk** [firm direction] — `max(lifestyle_risk, clinical_risk)` where
clinical_risk = high if `risk_flags` non-empty or `recent_hospitalization`=1;
medium if `chronic_conditions` count ≥ 3 or `medication_count` ≥ 5; else low.
When overall_risk = high, add `overall_risk_high` to the blocked codes.

**registration_status** [tune]
- `clinical_review` when overall_risk = high.
- `hold` when there are blockers but risk is not high.
- `approved` when there are no blockers.
- `rejected` is severe — reserve it for genuinely un-processable coverage
  (e.g. missing coverage). Do **not** route merely-expired/pending coverage to
  rejected by default; those tend to be hold/clinical_review with a coverage
  reason code.

**blocked_reason_codes** = union of all reasons detected above (unordered set).

Cohort summary = counts of registration_status, overall_risk, lifestyle_risk.

---

## B. Referral readiness audit (batch → per-referral readiness + rollups)

Scope to the target `batch_id`. Per referral detect issue codes, set a readiness
status, then build the batch-level discrepancy/duplicate/blocker/action rollups.

**Coding discrepancies** (via `icd_codes`) [firm]
- Compute the batch's expected chapter = dominant `chapter` among icd codes whose
  `service_family` = the batch service line.
- chapter mismatch = the referral code's `chapter` ≠ expected chapter.
- service-family mismatch = the code's `service_family` ≠ the batch service line.
- reason/laterality mismatch = the `referral_reason` (or narrative/laterality) is
  clinically inappropriate for the batch specialty — e.g. a `pain evaluation`
  reason in a pulmonary batch. (What reads as normal in one specialty is a
  mismatch in another; assess relative to the batch's service line.)

**Duplicates** [firm] — same `patient_id` appearing on more than one referral in
the batch = a duplicate group; keep the lowest referral_id as primary/keep.
A "possible duplicate" note whose patient has only one referral in the batch is
**not** a real duplicate — it is a duplicate-review item that clears (no group).

**Shared insurance** [firm] — one `insurance_id` on multiple referrals: different
patients → `verify_distinct_patient_policy_id`; same patient → legitimate
same-patient duplicate. Both are reported when the template asks for shared-
insurance anomalies.

**Clinical/admin blockers** [firm]
- `missing_records` — `records_received`=0.
- `missing_imaging` — `imaging_received`=0.
- auth blocker — `auth_required`=1 AND `auth_status` ≠ approved (report the status).
- already-scheduled / scheduled-before-clearance — `appointment_scheduled`=1.

**readiness_status** [firm] precedence (highest wins):
`blocked` (missing records/imaging or auth blocker) >
`under_review` (coding discrepancy) >
`admin_followup` (duplicate / shared insurance / already scheduled) >
`ready` (no issues). A referral is only in the *ready-to-schedule* list if it has
no issues at all.

**priority_tier** [firm] — `urgent` urgency → `tier_1_immediate`; routine with a
clinical blocker (records/imaging/auth) → `tier_2_short_term`; routine with only
administrative/coding issues → `tier_3_administrative`. Ready → null/omit.

**action / correspondence codes** [firm mapping] — one code per detected issue:
chapter/service-family/narrative → request-corrected-icd / clarify-code /
confirm-narrative-or-laterality; duplicate → consolidate / duplicate_resolution;
shared insurance → verify insurance id; missing records/imaging → request them;
auth blocker → resolve authorization / auth_records_request; scheduled → review
existing appointment / appointment_hold_notice. When a template asks for a single
correspondence `template_type` per referral, pick by the dominant issue
(scheduled > records/auth > duplicate > coding is a reasonable severity order)
and list every applicable reason code alongside it.

Rollups: discrepancy list, duplicate groups, shared-insurance anomalies, blocker
sets, ready list, and summary counts by urgency and by readiness status — each a
tally of the per-referral results.

---

## C. Transfer / dialysis packet review (batch → per-transfer packet + capacity)

Reference value = the transfer's `requested_start_date`.

**Packet completeness** [firm]
- The template lists the required document types. A required item is satisfied
  only by a **finalized** document (`finalized`=1 / status final); a draft counts
  as *missing*.
- A `transportation` requirement is satisfied by the transfer row's
  `transportation` field (null → missing), not by a document.
- `missing_required_documents` = required items not satisfied (order as the
  template says, usually alphabetical). Packet is `complete` iff none missing.

**Capacity / feasibility** [firm]
- `open_chairs_total` = sum of `facility_capacity.open_chairs` across all
  locations for the transfer `modality` on the `requested_start_date`
  (0 when no capacity rows exist for that date). `capacity_status` = available
  iff > 0.
- feasibility (4-way): complete+available → `ready_on_requested_start`;
  incomplete+available → `packet_not_ready_capacity_available`;
  incomplete+unavailable → `packet_not_ready_capacity_unavailable`;
  complete+unavailable → `capacity_unavailable`.

**Stale documents** [tune] — for the freshness-tracked doc types the template
lists, a finalized doc is stale if its `received_date` is older than the type's
freshness limit measured back from the requested start date. Freshness limits are
fixed per doc type (report the limit you used); a complete, clean packet should
come out with no stale items, so choose limits that keep the clean member clean.

**Decision / owner / route** [tune] — a complete, fresh, capacity-available packet
→ `accept` (owner none). Incomplete or stale packets route to `hold` /
`clinical_review` with an intake/clinical/scheduling owner and a
fax-referring-facility / phone-patient / internal-queue route; read the exact
mapping off the template's enums and which gap dominates.

Summary = counts of complete packets, patients with missing/stale items,
capacity-available, ready-on-start, and tallies of decision and next-owner.

---

## D. Chronic-care program enrollment panel (program → per-candidate disposition)

Include every candidate the program returns. Reference = an as-of date.

**Eligibility** [firm]
- `wrong_target_condition` — candidate `target_condition` ≠ the program's target.
- `missing_active_dmhtn_diagnosis` (or the program's analogue) — the required
  conditions are not both present in `chronic_conditions`.
- Eligible = right target AND has the required diagnosis.

**Consent** [firm] — `consent_status` declined → reject (`consent_declined`);
missing → hold (`consent_missing`).

**Chart artifacts** [firm] — using `chart_artifacts.status`: an artifact counts as
present only when `current`. Emit `stale_active_problems` (active_problems stale),
`chart_not_active` (active_problems stale/absent), and
`missing_recent_vitals`/`missing_recent_labs`/`missing_medication_list` when the
matching artifact is not current. `missing_chart_artifacts` = the tracked
artifacts (active_problems, vitals, labs, medications, consent, …) that are not
current.

**enrollment_status** [tune] — enroll (eligible, consent signed, chart complete);
hold (eligible but consent missing or chart gaps); reject (ineligible or consent
declined). Positive code `meets_dmhtn_criteria` (or analogue) for eligible rows.

**follow_up_cadence & monitoring** [tune]
- high-touch → `weekly`: low adherence (score below the program's cut, ~50),
  `recent_hospitalization`, or a recent-ED `risk_flag`.
- CKD in `chronic_conditions` → `biweekly` (`ckd_biweekly_monitoring`).
- otherwise enrolled → `monthly`; hold → `deferred`; reject → `none`.
- monitoring package: standard vs high-touch (elevated cadence) vs deferred
  (hold) vs not_applicable (reject); `first_checkin_days` follows cadence
  (weekly ≈ 7, biweekly ≈ 14, monthly ≈ 30; deferred/none = null).
- `outreach_channel` follows `preferred_outreach`.

Summary = eligible/ineligible counts and tallies of status, cadence, outreach,
and monitoring package.

---

## E. Referral-to-chart activation (batch → readiness + chart needs + correspondence)

A referral-audit variant (family B) whose extra outputs are chart-activation work
and a correspondence queue.

- **blocker_codes** [firm]: `clinical_code_discrepancy` (wrong service family OR a
  referral_reason clinically wrong for the specialty), `records_missing`,
  `imaging_missing`, `authorization_blocked` (auth_required + non-approved),
  `duplicate_review` ("possible duplicate" note), `scheduled_before_clearance`
  (appointment already scheduled). Same readiness precedence as family B.
- **duplicate_handling** [firm]: real same-patient groups vs
  `cleared_duplicate_review_referrals` for flagged-but-not-actually-duplicate rows.
- **ready_referral_chart_needs** [tune] — only for `ready` referrals. `chart_action`
  = create_chart (no existing chart) / update_chart (chart exists but artifacts
  stale/missing) / no_chart_action (all current). `artifacts_to_create` = the
  tracked artifacts not currently present (alphabetical).
- **correspondence_queue** [firm mapping] — one entry per non-ready referral:
  `template_type` (clinical_code_clarification / auth_records_request /
  duplicate_resolution / appointment_hold_notice) chosen by the dominant issue,
  with reason codes `wrong_service_family` / `clinical_reason_mismatch` /
  `records_missing` / `authorization_denied` / `duplicate_review` /
  `appointment_already_scheduled`.
- **priority_order** [firm] — non-ready referrals ranked, tier by the family-B
  tier rule (urgent → tier_1; routine clinical blocker → tier_2; routine
  admin-only → tier_3), tie-break by urgency then referral_id.
