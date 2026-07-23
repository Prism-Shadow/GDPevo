# Task-Family Field Derivation Rules

General rules for deriving each output field from environment records, by task family. These
are **patterns**, not specific answers — apply them to the records you actually retrieve.

## 1. UM nurse prior-authorization determination

Target: a `case_id` in `nurse_review` / `ready_for_determination` stage.

- **case_id** ← `task_context.target_business_id`.
- **criteria_results** ← `case_criteria` rows for the case: map `criterion_id` → `result`.
- **authorization** ← `authorizations` row for the case: `auth_number`, `approved_units`,
  `approved_start`, `approved_end`, `approved_cpt` (split the comma string into an **ascending**
  list), `modifier` ← `approved_modifier`.
- **evidence_documents** ← document IDs with `is_current=1` that are relied on, **ascending
  document_id**. (Cross-check via `document_facts.supports_criteria` — relied-on docs have facts
  that support a criterion.)
- **excluded_documents** ← document IDs with `is_current=0` (stale/non-current), ascending.
- **recommendation / final_status / route / determination_letter / next_action** ← derive from
  criteria + `policy_criteria.result_if_missing` + case stage + authorization `status`:
  - All applicable criteria **met** + nurse scope + authorization `recommended_approval`/approved
    → `approve` / `approved` / `nurse_approval` / `approval` / `issue_approval`.
  - Any required criterion `not_met` with `result_if_missing=deny` → `deny` / `denied` /
    `medical_director_review` (or nurse denial per scope) / `adverse_determination` / `issue_denial`.
  - A required criterion `unclear`/missing with `result_if_missing=pend` →
    `pend_for_information` / `pended` / `pending_information` / `information_request` /
    `request_more_information`.
- **basis_audit.source_precedence** ← `current_clinical_records_over_stale_export`.
  `controlling_record_ids` = current clinical document IDs (operational evidence order);
  `exception_record_ids` = stale document IDs.

## 2. Pharmacy coverage appeal + manufacturer-assistance intake

Target: an `appeal_id` / `case_id` with a specialty-drug coverage exception.

- **case_id, appeal_id** ← `task_context`. **drug** ← the requested drug (from case summary /
  appeal notes / assistance `program_name`).
- **appeal_path, expedited, appeal_deadline, owner** ← `appeals` row. `expedited` is true only
  when `expedited_attestation` indicates an expedited request; `standard_internal` path ⇒ false.
- **documented_failures** ← `drug_trials` rows with `documented=1`, **lowercase medication
  name**, **alphabetical**.
- **undocumented_or_insufficient_failures** ← `drug_trials` rows with `documented=0`, lowercase,
  alphabetical. (A trial "mentioned but fill missing" is undocumented/insufficient.)
- **criteria_results** ← `case_criteria` (DRUG-* keys); value enum includes `partial`.
- **required_packet_items** ← the union of appeal-packet items (from `policy_criteria`
  `criterion_key` mapping and the appeal `notes`), ordered **payer-appeal items before assistance
  items**. Typical appeal items: denial_notice, member_authorization, prescriber_rationale,
  formulary_failure_evidence; assistance item: household_income_proof.
- **missing_packet_items** ← gap items, ordered **appeal-evidence gaps before assistance-info
  gaps**. Derive appeal gaps from `case_criteria.gap_description` (e.g., a referenced-but-
  undocumented fill record → `lurasidone_fill_record` analog) and assistance gaps from
  `assistance_screen.missing_fields` (e.g., `household_income_proof`).
- **assistance** ← `assistance_screen` row:
  - `program_name` ← the program (map to the template enum).
  - `status`: `denial_on_file=1` (when `denial_required=1`) and only income/info missing ⇒
    `eligible_missing_information`; fully ready ⇒ `eligible_ready`; not eligible ⇒ `not_eligible`;
    no assistance track ⇒ `not_applicable`.
  - `missing_fields` ← split `assistance_screen.missing_fields`, **alphabetical**.
- **next_action** ← per precedence (payer appeal before assistance): if the packet is incomplete
  → `request_more_information`; if expedited and only income proof missing →
  `complete_expedited_appeal_and_request_income_proof`; etc. Assistance submission is secondary.
- **basis_audit.source_precedence** ← `payer_appeal_before_manufacturer_assistance`.
  `controlling_record_ids` = appeal-packet document IDs + documented drug-trial IDs (operational
  packet order); `exception_record_ids` = undocumented drug-trial ID(s).

## 3. Payment-integrity claim repricing

Target: a `claim_id` flagged `paid_stale_schedule` / `needs_repricing`.

- **claim_id, case_id, auth_number** ← `claims` row. **paid_total** ← `claims.paid_total`.
- **Benchmark selection** — for each `claim_lines` row (ordered by `line_number`), find the
  `payment_benchmarks` row matching `payer` + `plan_type` (from `members`/`plans`) +
  `service_domain` + `cpt_code` + `modifier` (match the line's modifier, or null) AND
  `service_date` ∈ [effective_start, effective_end]. Reject any benchmark whose
  `effective_end` < `service_date` (stale). Ignore distractor schedules whose `cpt_code` or
  `service_domain` does not match the line.
- **benchmark_source, benchmark_version** ← the selected benchmark's `source_name`,
  `source_version` (commonly the current commercial imaging schedule, e.g. a quarterly version).
- **stale_source_rejected** ← the stale source's `source_name` (or `none` if no stale source).
- **Per line:** `correct_allowed_amount` = `allowed_amount` × `units` (round to cents);
  `paid_amount` ← `claim_lines.paid_amount`; `recovery_amount` = `correct_allowed_amount` −
  `paid_amount` (positive = underpayment); `disposition` = `correct_upward` if correct > paid,
  `correct_downward` if correct < paid, `no_change` if equal, `deny_line` if the line is denied.
  `modifier` ← the line's modifier or `null`.
- **correct_allowed_total** ← sum of line `correct_allowed_amount` (cents).
- **recovery_amount** (claim level) ← `correct_allowed_total` − `paid_total` when correct > paid
  (underpayment); use the underpayment magnitude per the template's rule.
- **resubmission_route** ← `payment_integrity_correction` for a PI correction packet
  (alternatives: `provider_adjustment`, `appeal_reopen`, `no_resubmission`).
- **priority** ← from case `urgency`/stage (`standard` for routine; `expedited`/`urgent`/`monitor_only`
  as warranted).
- **basis_audit.source_precedence** ← `effective_benchmark_by_plan_modifier_and_date`.
  `controlling_record_ids` = the selected benchmark IDs, in claim-line order;
  `exception_record_ids` = the rejected stale benchmark ID(s).

## 4. Peer-to-peer (P2P) final summary

Target: a `case_id` with a completed P2P (`p2p_complete`).

- **case_id, p2p_id** ← case + `p2p_events.p2p_id`. **requested_cpt** ← `request_lines.cpt_code`
  for the case.
- **p2p_outcome, final_status** ← `p2p_events.outcome` / `p2p_events.final_status`.
- **criteria_results** ← `case_criteria` (PET-* keys).
- **unresolved_criteria** ← criterion IDs whose result is `not_met`/`unclear`, **ascending
  criterion ID**. Empty list only if none remain unresolved.
- **new_information_changed_review** ← true only if the P2P supplied new patient-specific
  information that materially changed the review (check `p2p_events.new_information` and the
  `PET-NEWINFO`-type criterion if present). Default false when the P2P notes no new factor.
- **missing_pet_factors** ← each PET-over-SPECT factor that remains unsupported, in the
  template's fixed choice order (e.g., prior_equivocal_spect, bmi_limitation, attenuation_artifact).
  Derive from `p2p_events.new_information` and the `document_facts` that record absent factors.
- **letter_type** ← `approval` if approved, `denial` if fully denied, `partial_denial` if partial,
  `no_letter` if none.
- **recommended_alternative** ← `SPECT MPI` when PET is denied solely for lack of a
  PET-over-SPECT factor; `PET MPI`/`none` per the outcome.
- **internal_appeal_deadline** ← if the final determination is **adverse**, compute the plan's
  internal appeal window (commonly **180 days**) from the **final adverse determination date**
  (the P2P event date), as `YYYY-MM-DD`. Use `null` when no internal appeal deadline applies
  (non-adverse). Compute the date by adding the window days to the determination date.
- **basis_audit.source_precedence** ← `new_patient_specific_p2p_information`.
  `controlling_record_ids` = the P2P event ID + supporting clinical-evidence document ID(s);
  `exception_record_ids` = the `document_facts` row(s) that record an absent factor.

## 5. Therapy margin-queue summary

Target: a queue business ID + a set of `queue_row_ids` (service_margin `month_id`s) for a period.

- **case_id** ← the queue business ID. **period** ← the reporting period (`YYYY-MM`).
- **threshold_revenue_to_cost_ratio** ← from `task_context.finance_memo` (e.g., 1.2).
- **rows** ← one per `queue_row_id`, **in `task_context.finance_memo.queue_row_ids` order**:
  - `total_cost` = `variable_cost` + `fixed_cost_allocated` (2 decimals)
  - `margin` = `net_revenue` − `total_cost` (2 decimals)
  - `revenue_to_cost_ratio` = `net_revenue` / `total_cost` (4 decimals)
  - `below_threshold` = ratio < threshold
  - `charge_sensitive` = the `charge_sensitive` flag (0/1 → false/true)
  - `recommended_action`: `payer_contract_review` if `below_threshold`; else
    `monitor_charge_sensitive` if `charge_sensitive`; else `monitor_no_action`.
  - `payer_segment`, `service_domain`, `cpt_code` ← from the row.
- **below_threshold_segments** ← payer_segments of below-threshold rows, **alphabetical**.
- **charge_sensitive_segments** ← payer_segments of charge-sensitive rows, **alphabetical**
  (independent of below-threshold).
- **top_issue** ← the below-threshold row's `{segment}_{cpt}` (e.g., `medicaid_97110`), or
  `none` if no below-threshold row.
- **gap_to_120pct** ← for the top below-threshold issue: `threshold × total_cost − net_revenue`
  (the positive shortfall to reach the threshold on cost), 2 decimals.
- **basis_audit.source_precedence** ← `margin_threshold_then_charge_sensitivity`.
  `controlling_record_ids` = the queue row IDs in row order; `exception_record_ids` = `[]`
  (all rows are analyzed; none excluded) unless a row is explicitly out of scope.

## Cross-family reminders
- Always reconcile line-level and summary-level numbers (sums must match).
- `result_if_missing` on `policy_criteria` is the key to deny-vs-pend routing.
- `is_current` on `documents` and `effective_end` on `payment_benchmarks` are the staleness
  signals that populate `exception_record_ids`.
- Distractor data exists (wrong-CPT schedules, duplicate benchmark rows from other cases,
  unrelated documents) — match on the target's exact keys and ignore the rest.
