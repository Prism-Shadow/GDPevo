# Determination Patterns — field-by-field derivation

For each task type, derive the substantive fields from the environment records. The
`basis_audit` block and cross-cutting rules are handled in `SKILL.md`. Enum choices and
ordering rules live in the task's own `answer_template.json` — always re-read them.

---

## 1. UM nurse authorization determination
*(physical/occupational/speech therapy, imaging, etc. — `request_type = prior_authorization`)*

Records: `cases` → `members`/`plans`/`providers`; `request_lines`; `policies` + `policy_criteria`;
`case_criteria`; `documents` + `document_facts`; `authorizations`.

- **criteria_results** — for each required criterion ID, take `case_criteria.result` and map to the
  template enum (`met`/`not_met`/`unclear`/`not_applicable`). Apply `policy_criteria.result_if_missing`
  when evidence is absent (`pend` ⇒ unclear/pended, `deny` ⇒ not_met/denied).
- **recommendation / final_status / route / determination_letter / next_action** — flow from the criteria:
  - All approval-required criteria `met` ⇒ `approve` / `approved` / `nurse_approval` / `approval` / `issue_approval`.
  - Any `not_met` with `result_if_missing = deny` ⇒ `deny` / `denied` / route per policy / `adverse_determination` / `issue_denial`.
  - Any `pend` gap (missing info) ⇒ `pend_for_information` / `pended` / `pending_information` / `information_request` / `request_more_information`.
  - Needs medical judgment ⇒ `escalate_to_md` / `md_review_required` / `medical_director_review` / `route_md_review`.
  - Peer review indicated ⇒ `peer_to_peer` route / `schedule_p2p`.
- **authorization** — echo the `authorizations` row: `auth_number`, `approved_units` (int),
  `approved_start`/`approved_end` (`YYYY-MM-DD`), `approved_cpt` (split the env comma-string into a
  **list sorted ascending by CPT code**), `modifier`. On a denial, units may be 0 and dates/auth_number null.
- **evidence_documents** — `document_id`s that are current (`is_current = 1`) and relied upon, ascending.
- **excluded_documents** — `document_id`s that are stale/non-current/non-applicable (e.g., a `stale_export`
  with `is_current = 0`), ascending.
- `basis_audit.source_precedence` = `current_clinical_records_over_stale_export` when a stale export is excluded.

---

## 2. Pharmacy coverage appeal + manufacturer assistance
*(specialty-drug coverage-exception appeal)*

Records: `cases`; `appeals`; `drug_trials`; `documents`; `assistance_screen`; `case_criteria`/`policy_criteria`.

- **appeal_id / case_id / drug** — from `task_context` and the case/appeal records. `drug` = the requested
  medication (enum).
- **appeal_path / expedited / owner / appeal_deadline** — from `appeals` (`appeal_path` is already an enum value;
  `expedited` = whether `expedited_attestation` indicates an expedited request; `owner`, `appeal_deadline` direct).
- **documented_failures** — `drug_trials` rows with `documented = 1`, medication lowercased, alphabetical.
- **undocumented_or_insufficient_failures** — `documented = 0`, same format/order.
- **criteria_results** — required keys (e.g., `DRUG-AUTH`, `DRUG-DENIAL`, `DRUG-RATIONALE`, `DRUG-FAILURES`)
  ← `case_criteria.result` (`partial` is a valid value here).
- **required_packet_items** — the standard packet (from `appeals.notes` and/or the policy), ordered
  **payer-appeal items before assistance items**.
- **missing_packet_items** — the **specific** case-level gaps: the precise missing evidence item (e.g., the fill
  record for an undocumented prior medication) and any missing assistance info. Order: **appeal-evidence gaps
  before assistance-info gaps**. Use the specific item, not the general category, when the category is partly present.
- **assistance** — `program_name` (enum); `status` mapped from `assistance_screen.assistance_status`
  (`pending_missing_*` ⇒ `eligible_missing_information`; ready ⇒ `eligible_ready`; etc.); `missing_fields`
  split from the env comma-string, alphabetical by field id.
- **next_action** — payer appeal takes precedence over manufacturer assistance
  (`source_precedence = payer_appeal_before_manufacturer_assistance`). Standard + incomplete packet ⇒
  `request_more_information`; expedited + missing income proof ⇒ `complete_expedited_appeal_and_request_income_proof`;
  eligible & ready ⇒ `submit_assistance_application`; not eligible ⇒ `close_not_eligible`; failures unmet ⇒ `issue_denial`.

---

## 3. Payment-integrity claim repricing
*(paid claim re-priced against the current rate schedule)*

Records: `claims`; `claim_lines` (order by `line_number`); `cases` (for `plan_type`); `payment_benchmarks`.

- **benchmark_source / benchmark_version** — from the **current** `payment_benchmarks` row(s) matching
  `payer` + `plan_type` + `service_domain` + `cpt_code` + `modifier` whose `effective_start` ≤ service_date
  ≤ `effective_end`. This is the schedule effective on the line's `service_date`.
- **stale_source_rejected** — the `source_name` of the expired/stale schedule (e.g., one with `effective_end` <
  service_date), or `"none"` if no stale source was involved. Distractor schedules (CPT not on the claim) are
  ignored, not listed here.
- Per line: **correct_allowed_amount** = `allowed_amount` × `units` (round to cents after multiplying);
  **paid_amount** = `paid_amount`; **recovery_amount** = correct − paid (positive when underpaid);
  **disposition** = `correct_upward` (correct > paid) / `correct_downward` (correct < paid) / `no_change` /
  `deny_line`. **modifier** = the line's modifier or `null`.
- **paid_total / correct_allowed_total / recovery_amount (top-level)** — sums across lines. Top-level
  `recovery_amount` is the underpayment total (positive) when correct > paid.
- **resubmission_route** — `payment_integrity_correction` for a repricing correction (other choices:
  `provider_adjustment`, `appeal_reopen`, `no_resubmission`). **priority** from case `urgency` (routine ⇒ `standard`).
- `basis_audit.source_precedence` = `effective_benchmark_by_plan_modifier_and_date`.

---

## 4. Peer-to-peer (P2P) final summary
*(completed P2P; close the authorization file)*

Records: `cases`; `p2p_events`; `request_lines`; `policy_criteria` + `case_criteria`; `documents`/`document_facts`;
`authorizations`.

- **p2p_id / requested_cpt** — from `p2p_events.p2p_id` and `request_lines.cpt_code`.
- **p2p_outcome / final_status** — from the `p2p_events` row (`outcome`, `final_status`).
- **criteria_results** — **only** the template's required keys (e.g., `PET-IND`, `PET-FACTOR`). Exclude
  non-required meta-criteria (e.g., a "new P2P information" criterion that is not in the required keys).
  Map `case_criteria.result` to the enum.
- **unresolved_criteria** — approval-required criteria that remain `not_met`/`unclear`, ascending criterion ID.
  Empty list only if none remain unresolved.
- **new_information_changed_review** — `true` only if `p2p_events.new_information` supplied new patient-specific
  info that materially changed the review; `false` when it confirms no new info was supplied.
- **missing_pet_factors** — every PET-over-SPECT factor that remains unsupported, **in the order shown in the
  template's choices** (typically: prior equivocal SPECT, BMI limitation, attenuation artifact).
- **letter_type** — `approval` / `denial` / `partial_denial` / `no_letter` from `final_status`.
- **recommended_alternative** — the standard modality when the requested advanced modality is denied for lacking
  the superiority factor (e.g., `SPECT MPI` when PET MPI is denied). `none` if no alternative applies.
- **internal_appeal_deadline** — if the final determination is adverse, compute **final adverse determination
  date + the plan's internal-appeal window** (e.g., 180 days). Use the P2P / final-review date as the start.
  `null` only when no internal appeal deadline applies (non-adverse).
- `basis_audit.source_precedence` = `new_patient_specific_p2p_information`.

---

## 5. UM-finance margin queue
*(therapy/service margin queue for payer-service actioning)*

Records: `service_margin` rows for the `month_id`s listed in `task_context.finance_memo.queue_row_ids`
(keep that order in the answer).

- Per row: **total_cost** = `variable_cost` + `fixed_cost_allocated`; **margin** = `net_revenue` − `total_cost`;
  **revenue_to_cost_ratio** = `net_revenue` / `total_cost` (4 decimals).
- **below_threshold** = `revenue_to_cost_ratio` < `threshold_revenue_to_cost_ratio` (from `task_context`, e.g., 1.2).
- **charge_sensitive** = the row's `charge_sensitive` flag.
- **recommended_action** — `below_threshold` (a payer-service issue) ⇒ `payer_contract_review`;
  `charge_sensitive` and not below ⇒ `monitor_charge_sensitive`; neither ⇒ `monitor_no_action`.
  (Separate below-threshold payer-service issues from charge-sensitive rows.)
- **below_threshold_segments / charge_sensitive_segments** — distinct `payer_segment`s, alphabetical by enum value.
- **top_issue** — the below-threshold row encoded as `{payer_segment}_{cpt_code}` per the template's `top_issue` enum, or `none` when no row is below threshold.
- **gap_to_120pct** — `(threshold × total_cost) − net_revenue` for the top below-threshold row, dollars, 2 decimals.
- `basis_audit.source_precedence` = `margin_threshold_then_charge_sensitivity`.
