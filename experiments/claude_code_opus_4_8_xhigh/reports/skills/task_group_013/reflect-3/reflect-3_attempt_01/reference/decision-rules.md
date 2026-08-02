# Decision Rules by Task Type

Identify the task type from the prompt + template, then apply that playbook.
Enum spellings shown are the usual controlled values, but always take the exact
`allowed_values` from the task's own template. Codes/reasons are collected as the
**union of independent checks**; overall status is chosen by the severity
precedence listed.

Where a rule is a graded threshold (risk tiers, freshness windows), treat the
value given here as a sensible default and confirm the exact cut with the
template's structure and any figures in the prompt — these are the parts most
worth double-checking.

---

## Type A — New Patient Access Verification (roster → per-patient registration)

Inputs: roster (`requested_service_date`, `service_line`), patients, coverage,
pbm, patient_pharmacy/pharmacies, lifestyle, clinical_history.

Per patient:

- **insurance_status**: `valid` if a coverage row is `active` and the requested
  service date is within `effective_date`..`termination_date`; `invalid` if
  `expired`/out-of-window or `pending`; `missing` if no row.
- **prescription_status** (PBM): `valid` if `active=1` + `status=approved` +
  `formulary_status=covered`; `invalid` if `rejected`/`active=0`/`not_found`/
  `pending`/`review`; `missing` if no row.
- **pharmacy_status**: network status of the **rank-1** preferred pharmacy →
  `in_network` / `out_of_network` / `unknown` (no pharmacy).
- **lifestyle_risk** (low/medium/high): score risk factors — current smoker
  (highest), former smoker (lower); heavy alcohol (high), moderate (some);
  no/low exercise; short sleep (< ~6h). Sum → low / medium / high bands.
- **overall_risk**: start from lifestyle_risk and escalate for clinical severity
  — `recent_hospitalization`, any `risk_flags`, high chronic-condition count, or
  high `medication_count` push toward high.
- **blocked_reason_codes** (unordered set) — add each that applies:
  `coverage_expired`, `coverage_pending`, `excluded_service_line` (roster
  `service_line` not in `coverage.service_lines`), `missing_address`,
  `emergency_contact_missing` (`emergency_contact_present=0`),
  `preferred_contact_unavailable` (preferred channel's contact point is null),
  `pbm_invalid`, `pbm_missing`, `pbm_policy_mismatch` (pbm policy ≠ coverage
  policy), `pharmacy_out_of_network`, `pharmacy_unknown`, `overall_risk_high`.
- **registration_status** precedence: `rejected` (ineligible: coverage expired /
  excluded service line / coverage missing) > `clinical_review` (overall_risk
  high) > `hold` (any other fixable blocker) > `approved` (no blockers).

Summary: `total_patients` + counts by registration_status, overall_risk, and
lifestyle_risk (every enum key initialized to 0).

---

## Type B — Referral Readiness Audit (referral batch → schedule readiness)

Inputs: referrals in the batch, icd_codes, (documents if present).

Per referral, collect **issue_codes**:

- `icd_chapter_mismatch` — `icd_codes.service_family` ≠ referral `service_line`
  (a code already in the right service family is fine even if its chapter letter
  differs).
- `narrative_mismatch` / `laterality_mismatch` — only when the referral text /
  stated side contradicts the ICD description / `laterality` (generic
  placeholder descriptions are not mismatches).
- `duplicate_referral` — same `patient_id` repeated in the batch (same service
  line).
- `shared_insurance_anomaly` — same `insurance_id` across **different** patients.
- `missing_records` (`records_received=0`), `missing_imaging`
  (`imaging_received=0`).
- `auth_blocker` — `auth_required=1` and `auth_status` in
  {`pending`,`denied`,`not_submitted`}.
- `already_scheduled` — `appointment_scheduled=1`.

**readiness_status** precedence: `blocked` (missing records/imaging or auth
blocker) > `under_review` (any coding/narrative/laterality mismatch) >
`admin_followup` (duplicate / shared-insurance / already scheduled) > `ready`.

Derived collections:

- **duplicate_groups**: group same-patient referrals; `primary_referral_id` =
  lowest id; recommendation `consolidate_to_primary` (else `keep_separate`).
- **shared_insurance_anomalies**: per shared `insurance_id`, list referral ids +
  patient ids; disposition `verify_distinct_patient_policy_id` (different
  patients) or `legitimate_duplicate_same_patient` (same patient).
- **blocker_sets**: `missing_records`, `missing_imaging` id lists; `auth_blockers`
  as `{referral_id, auth_status}`.
- **ready_to_schedule**: referrals whose readiness is `ready`.
- **action_plan** (non-ready): map each issue to an action —
  `request_corrected_icd`, `confirm_narrative`, `confirm_laterality`,
  `consolidate_duplicate`, `verify_insurance_id`, `request_records`,
  `request_imaging`, `resolve_authorization`, `review_existing_appointment`; plus
  a `priority_tier`.
- **priority_tier**: `tier_1_immediate` (urgent clinical blocker / denied auth),
  `tier_2_short_term` (routine clinical follow-up), `tier_3_administrative`
  (duplicate / insurance / scheduling).

Summary: totals, ready vs follow-up counts, counts by urgency
(`urgent`/`routine`/`admin`, where admin ≈ administrative-only referrals), by
readiness_status, the urgency×status cross-tab, and issue counts.

---

## Type C — Dialysis Transfer Review (transfer batch → intake feasibility)

Inputs: transfer_requests, documents (transfer packets), facility_capacity.

Per transfer:

- **packet_completeness / missing_required_documents**: the required packet is a
  fixed list of `doc_type`s (see the template's `allowed_values`). An item is
  present only if a **finalized** document of that type exists; `draft`/absent ⇒
  in `missing_required_documents`. The `transportation` requirement is met by the
  transfer's own `transportation` field being non-null. `complete` iff nothing
  missing.
- **stale_documents**: time-sensitive doc types (labs, serologies, TB screen,
  H&P — see template) whose `received_date` is older than a freshness window
  measured back from `requested_start_date`. Monthly labs use the tightest window
  (~30 days); serology/TB/H&P use longer windows. Report `{doc_type,
  received_date, freshness_limit_days}`.
- **requested_start**: `date`; `open_chairs_total` = Σ `open_chairs` for the
  modality on that date across locations; `capacity_status` `available` if > 0
  else `unavailable` (a date with no capacity row = closed/0). **feasibility**:
  `ready_on_requested_start` (packet ready + capacity), 
  `packet_not_ready_capacity_available`, `packet_not_ready_capacity_unavailable`,
  or `capacity_unavailable` (packet ready but no capacity).
- **final_intake_decision**: `accept` (complete + fresh + capacity), `hold`
  (missing docs or capacity gap — administrative), `clinical_review` (stale
  clinical documents needing nurse sign-off).
- **next_contact_owner / route**: pair the owner to the blocker —
  missing docs ⇒ `intake_coordinator` / `fax_referring_facility`; capacity ⇒
  `scheduling_coordinator` / `internal_queue`; clinical/stale ⇒ `clinical_nurse`
  / `phone_patient`; clean ⇒ `none` / `none`. Pick by a fixed precedence.

Summary: total, complete count, missing-doc patient count, stale-doc patient
count, capacity-available count, requested-start-ready count, decision counts,
next-contact-owner counts.

---

## Type D — Program Enrollment Panel (program candidates → enroll disposition)

Inputs: program candidate list, patient demographics, chart_artifacts,
clinical_history. One row per candidate returned for the program.

Per candidate:

- **eligible**: candidate `target_condition` matches the program's condition
  (mismatch ⇒ `wrong_target_condition`, ineligible).
- **reason_codes** (union): `meets_dmhtn_criteria` (eligible + confirmed active
  problem list); `wrong_target_condition`; `consent_declined` / `consent_missing`
  (from `consent_status`); chart gaps `chart_not_active` (no current
  active-problems chart), `stale_active_problems`, `missing_recent_vitals`,
  `missing_recent_labs`, `missing_medication_list`, `missing_active_..._diagnosis`;
  high-touch modifiers `recent_hospitalization_high_touch`, `recent_ed_high_touch`
  (from `risk_flags`), `low_adherence_high_touch` (adherence below the program
  threshold, ~<50), `ckd_biweekly_monitoring` (ckd in chronic conditions).
- **missing_chart_artifacts** (subset of `chart_record`, `active_problems`,
  `vitals`, `labs`, `medications`, `consent`): any required artifact absent /
  not current; `chart_record` keyed to the chart-existence flag.
- **enrollment_status** precedence: `reject` (wrong target OR consent declined) >
  `hold` (consent missing OR chart gaps) > `enroll`.
- **follow_up_cadence**: `weekly` (high-touch: recent hosp/ED, low adherence),
  `biweekly` (ckd), `monthly` (standard enroll), `deferred` (hold), `none`
  (reject).
- **initial_monitoring_package**: `package_type` `high_touch_dm_htn` (elevated
  monitoring) / `standard_dm_htn` / `deferred` (hold) / `not_applicable` (reject);
  `components` from {`bp_cuff`, `glucometer`, `lab_order_a1c_cmp_lipid`,
  `medication_reconciliation`, `care_plan_setup`, `consent_packet`,
  `chart_update_request`} matching the disposition; `first_checkin_days` = 7 /
  14 / 30 for weekly / biweekly / monthly, null for deferred/none.
- **outreach_channel**: candidate's `preferred_outreach` validated against
  available contact points (phone/sms need a phone; email needs an email; else
  fall back to portal); `none` for reject.

Summary: totals, eligible/ineligible, and counts by enrollment_status,
follow_up_cadence, outreach_channel, and package_type.

---

## Type E — Referral-to-Chart Activation (referral batch → activation file)

Inputs: referrals, icd_codes, patients (`existing_chart`), chart_artifacts.

Per referral, collect **blocker_codes**:

- `clinical_code_discrepancy` — `icd_codes.service_family` ≠ referral
  `service_line`.
- `records_missing` (`records_received=0`), `imaging_missing`
  (`imaging_received=0`).
- `authorization_blocked` — `auth_required=1` and `auth_status` in
  {`denied`,`pending`,`not_submitted`}.
- `duplicate_review` — referral carries a possible-duplicate marker.
- `scheduled_before_clearance` — `appointment_scheduled=1`.

**readiness_status** precedence: `under_review` (clinical code discrepancy) >
`blocked` (records/imaging/auth) > `admin_followup` (scheduled / open duplicate
review) > `ready`.

Derived collections:

- **clinical_code_discrepancy_referrals**: ids with the code discrepancy.
- **blocker_sets**: `authorization`, `records`, `imaging` id lists.
- **duplicate_handling**: `duplicate_groups` only for **same-patient** repeats
  (`keep_referral_id` = lowest id); `cleared_duplicate_review_referrals` =
  possible-duplicate referrals that turn out to be distinct patients (they clear
  and may proceed).
- **ready_referral_chart_needs** (for ready referrals only): `chart_action`
  `create_chart` (no existing chart), `update_chart` (chart exists but artifacts
  missing/stale), or `no_chart_action`; `artifacts_to_create` = required chart
  artifacts ({`demographics`, `active_problems`, `medications`, `allergies`,
  `vitals`, `labs`, `consent`}) not currently present, alphabetical.
- **correspondence_queue** (non-ready needing office contact): `template_type`
  `clinical_code_clarification` (reason `wrong_service_family` /
  `clinical_reason_mismatch`), `auth_records_request` (`records_missing`,
  `authorization_denied`), `duplicate_resolution` (`duplicate_review`),
  `appointment_hold_notice` (`appointment_already_scheduled`, plus underlying
  blockers).
- **priority_order** (non-ready only, highest priority first): rank with
  `priority_tier` `tier_1_immediate` (urgent / denied auth) > `tier_2_short_term`
  (clinical) > `tier_3_administrative`.
