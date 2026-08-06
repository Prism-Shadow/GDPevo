# Cedar Ridge Portal — Field Derivation Rules

Rules are stated generically so they transfer to any batch of the same archetype. Apply each rule
uniformly to every item; derive cross-item structures (duplicates, shared-insurance, blocker sets,
summaries) from the per-item results. Where a rule has known edge-case sensitivity, it is flagged.

## Cross-cutting: status = conjunctive validity

A "status: valid/invalid/missing" field is **valid only when every sub-condition holds**; any single
failure makes it **invalid** with a specific reason code; absence of the record makes it **missing**.
Always emit the most specific reason code for the failure rather than a generic one.

## New-patient access verification (roster)

Reference the roster's `requested_service_date` and `service_line` for every patient.

- **insurance_status**: `valid` only if coverage `status=active`, `termination_date` ≥ requested
  service date (a `null` termination is unbounded), **and** the roster `service_line` is present in
  `coverage.service_lines`. `expired` (or termination before the service date) → `invalid` +
  `coverage_expired`. `pending` → `invalid` + `coverage_pending`. Service line not in
  `service_lines` → `invalid` + `excluded_service_line` (the insurance is invalid *for this service*,
  even when the coverage record is otherwise active). No coverage row → `missing`.
- **prescription_status** (PBM): `valid` only if `active=1` AND `status=approved` AND
  `formulary_status=covered` AND PBM `policy_number` == coverage `policy_number`. Failures:
  inactive/rejected/pending/not_found → `pbm_invalid`; policy mismatch → `pbm_policy_mismatch`;
  no PBM row → `pbm_missing`.
- **pharmacy_status**: take the `preference_rank=1` pharmacy. `in_network` → `in_network`;
  `out_of_network` → `out_of_network` + `pharmacy_out_of_network`; no pharmacy → `unknown` +
  `pharmacy_unknown`.
- **preferred_contact_unavailable**: the patient's `preferred_contact` channel has no backing data —
  `email` with null email, `phone`/`sms` with null phone, `portal` with null email.
- **emergency_contact_missing**: `emergency_contact_present != 1`. **missing_address**: `address` is null.
- **overall_risk_high** is added to `blocked_reason_codes` whenever `overall_risk` evaluates to high.
- **lifestyle_risk / overall_risk**: derive by a fixed scoring rule applied identically to all
  patients. Lifestyle is driven by smoking/alcohol/exercise/sleep; overall combines lifestyle with
  chronic-condition burden, `recent_hospitalization`, and non-empty `risk_flags`. Pick one rule and
  apply it consistently (the exact thresholds are the main source of error — prefer a simple,
  defensible rule over an elaborate one).
- **registration_status** precedence: a hard coverage blocker (`excluded_service_line`) → `rejected`;
  else `overall_risk_high` → `clinical_review`; else any remaining blocker → `hold`; else `approved`.

## Referral readiness audit (batch)

- **Blocker detection (data-grounded, high confidence):**
  - `records_received=0` → `missing_records` (and add referral to `blocker_sets.missing_records`).
  - `imaging_received=0` → `missing_imaging` (`blocker_sets.missing_imaging`).
  - `auth_required=1` with `auth_status` in {denied, pending, not_submitted} → `auth_blocker`
    (`blocker_sets.auth_blockers` with the auth_status).
  - `appointment_scheduled=1` → `already_scheduled`.
- **Duplicate groups**: same `patient_id` with multiple referrals in the batch (or a flagged
  "duplicate" referral) → one group with the ascending referral IDs, the patient, the primary
  (lowest ID / original), `recommendation: consolidate_to_primary`.
- **Shared-insurance anomalies**: group referrals by `insurance_id` where count > 1. Different
  patients → `verify_distinct_patient_policy_id`; same patient → `legitimate_duplicate_same_patient`.
- **ICD discrepancies**: compare the referral's `icd10_code` `service_family` (from `icd_codes`) to
  the referral `service_line`; a mismatch is a `clinical_code_discrepancy` (wrong service family).
  Narrative/laterality mismatches apply when the ICD carries a laterality or specific description that
  conflicts with the referral narrative — only flag a discrepancy when there is a concrete conflict,
  not merely a generic diagnosis description.
- **readiness_status / priority_tier / action_codes**: these interpretive fields are the hardest to
  calibrate from feedback alone. Use a fixed precedence (hard blockers → blocked; admin actions like
  duplicate/shared-insurance/already-scheduled → admin_followup; clinical-code review → under_review;
  clean → ready) and map each issue to a concrete action code. Keep the mapping uniform across all
  referrals.

## Transfer packet review (batch)

- **packet_completeness_status**: `complete` only if **every** required doc type is present **and**
  finalized. A doc that is absent **or** draft/not-finalized makes the packet `incomplete` **and** the
  doc type is listed in `missing_required_documents` (drafts count as missing). `transportation` is
  satisfied by the transfer's `transportation` field (null ⇒ missing).
- **stale_documents**: only among freshness-limited types (hbsag, hep_b_antibody_core,
  history_physical, monthly_labs, ppd_or_cxr), only for **finalized** documents, comparing
  `received_date` to the transfer's `requested_start_date` against the type's freshness limit. Report
  `doc_type`, `received_date`, `freshness_limit_days`. (The exact per-type limits are the main
  uncertainty — use standard dialysis-packet intervals: monthly labs/HBsAg ~30d, annual items ~365d.)
- **requested_start**: `date` = `requested_start_date`; `open_chairs_total` = sum of `open_chairs`
  across all locations for that exact date+modality (no row ⇒ 0); `capacity_status` = `available` iff
  total > 0; `feasibility` from the 2×2 of (packet complete?) × (capacity available?):
  complete+available → `ready_on_requested_start`; complete+unavailable → `capacity_unavailable`;
  incomplete+available → `packet_not_ready_capacity_available`; incomplete+unavailable →
  `packet_not_ready_capacity_unavailable`.
- **final_intake_decision**: `accept` when ready_on_requested_start; otherwise `hold` (resolvable
  packet/capacity issues) or `clinical_review` (stale critical clinical docs such as an expired
  history_physical or ppd/tb screen). **next_contact_owner/route** follow the dominant issue:
  packet gaps → intake_coordinator / fax_referring_facility; capacity → scheduling_coordinator /
  internal_queue; clinical staleness → clinical_nurse / fax_referring_facility; accepted → none/none.

## Program enrollment panel (program_code)

- **eligible** (boolean) = **clinical criteria only**: `target_condition` matches the program's target
  **and** the program's required diagnoses are present in `clinical_history.chronic_conditions`.
  Consent, chart, and artifact problems do **not** flip eligible — they drive enrollment_status.
- **enrollment_status**: `enroll` when eligible AND `consent_status=signed` AND `existing_chart=1` AND
  required chart artifacts are current; `reject` when `consent_status=declined` OR not eligible
  (wrong target / missing diagnosis); `hold` when eligible but `consent_status=missing` or chart not
  active (resolvable).
- **reason_codes**: eligible patients get `meets_dmhtn_criteria` plus any high-touch/monitoring
  modifiers (`recent_hospitalization_high_touch`, `recent_ed_high_touch`, `low_adherence_high_touch`,
  `ckd_biweekly_monitoring`). Ineligible patients get the disqualifiers (`wrong_target_condition`,
  `missing_active_dmhtn_diagnosis`, `consent_declined`/`consent_missing`, `chart_not_active`, …) plus
  artifact-gap codes (`stale_active_problems`, `missing_recent_vitals`, `missing_recent_labs`,
  `missing_medication_list`).
- **missing_chart_artifacts**: `chart_record` when `existing_chart=0`; each of
  `active_problems`/`vitals`/`labs`/`medications` when the artifact is absent (a stale artifact is
  noted via `stale_active_problems`, not necessarily listed as missing); `consent` when there is no
  consent artifact.
- **follow_up_cadence / initial_monitoring_package**: high-touch factors (recent hospitalization,
  recent ED, low adherence) → high_touch package + weekly; CKD → standard + biweekly; otherwise
  standard + monthly. Hold → deferred; reject → not_applicable / none.
- **outreach_channel**: the candidate's `preferred_outreach` for enroll/hold; `none` for reject.
- **as_of_date**: the panel generation date (use the current/run date unless the task states
  otherwise).

## Referral-to-chart activation (batch)

- **readiness_by_referral**: per referral, `readiness_status` + `blocker_codes`. Blocker codes:
  `clinical_code_discrepancy` (ICD service_family ≠ referral service_line), `records_missing`,
  `imaging_missing`, `authorization_blocked` (auth denied/pending), `duplicate_review`,
  `scheduled_before_clearance` (appointment_scheduled before the referral is cleared).
- **clinical_code_discrepancy_referrals**: ascending list of referral IDs whose ICD service_family
  ≠ the referral service_line.
- **blocker_sets**: `{authorization, records, imaging}` — ascending referral-ID lists.
- **duplicate_handling**: `duplicate_groups` (actual duplicates with `keep_referral_id`) and
  `cleared_duplicate_review_referrals` (referrals flagged "possible duplicate" that resolve to
  non-duplicates — these are ready, not blocked).
- **ready_referral_chart_needs**: for referrals that may move forward, `chart_action`
  (`create_chart` when `existing_chart=0`; `update_chart` when the chart exists but artifacts are
  missing/stale; `no_chart_action` when complete) and `artifacts_to_create` (absent or non-current
  artifacts, alphabetical).
- **correspondence_queue**: one entry per distinct follow-up needed —
  `clinical_code_clarification` (code discrepancy), `auth_records_request` (records/auth),
  `duplicate_resolution` (actual duplicate), `appointment_hold_notice` (scheduled before clearance).
  A referral with multiple concerns may yield multiple entries.
- **priority_order**: non-ready referrals only, ranked highest-priority first, with a priority tier
  (immediate for time-sensitive issues like a pre-scheduled appointment; short-term for hard
  blockers; administrative for clarifications).

## Common failure modes to avoid

- Inventing an enum value or reason code not in the template's allowed set.
- Omitting a required key (especially zero-valued count keys, or `null`-allowed priority tiers).
- Ordering a list by the wrong key, or forgetting that some arrays are unordered sets.
- Letting per-item rules drift so cohort counts become internally inconsistent.
- Treating a draft document as "present" for completeness, or treating `transportation` as a doc_type.
- Conflating clinical eligibility with enrollment action.
- Outputting anything other than the single JSON object.
