# Task Playbooks — field-by-field derivation

Each archetype below lists how to derive the template fields from environment records.
Rules reference column names, not any specific answer. Always defer to the task's own
`prompt.txt`/`answer_template.json` when it states a rule (rounding, ordering, window
length, null handling); the template's enum `choices` are authoritative for allowed values.

---

## A. UM nurse prior-authorization determination  (`CASE-…`)
Source precedence: `current_clinical_records_over_stale_export`.
Pull: `cases`, `request_lines`, `case_criteria`, `authorizations`, `documents`,
policy via `cases.policy_id` → `policy_criteria`.

- `case_id` = target case id.
- `criteria_results` = map each template-required criterion id → `case_criteria.result`.
- Decision from criteria vs `policy_criteria.result_if_missing`:
  - all required met → `recommendation=approve`, `final_status=approved`,
    `route=nurse_approval`, `determination_letter=approval`, `next_action=issue_approval`.
  - a met-if-missing→`pend` criterion unmet → pend / `pending_information` /
    `request_more_information`; a `deny` criterion unmet → deny; ambiguous/clinical →
    `escalate_to_md`/`medical_director_review`; use the template enums.
- `authorization` (when approving) from the `authorizations` row:
  `auth_number`; `approved_units` = the row's units (equals the sum of
  `request_lines.requested_units`); `approved_start`/`approved_end`; `approved_cpt` =
  split `approved_cpt` on commas, sorted **ascending**; `modifier` = `approved_modifier`.
- `evidence_documents` = `documents` with `is_current = 1`, ascending by `document_id`.
- `excluded_documents` = `documents` with `is_current = 0` (stale export), ascending.
- `basis_audit`: controlling = the current evidence documents (evidence order);
  exception = the stale document(s); precedence_order = controlling then exception.

## B. Pharmacy coverage appeal + manufacturer-assistance intake  (`APPEAL-…`)
Source precedence: `payer_appeal_before_manufacturer_assistance`.
Pull: `appeals` (target appeal id), `drug_trials`, `assistance_screen`, `case_criteria`,
policy/document context.

- `appeal_id` from `appeals.appeal_id`; `appeal_path` = `appeals.appeal_path`;
  `expedited` = whether `expedited_attestation` indicates an expedited request
  (`not_requested` → false); `appeal_deadline` = `appeals.appeal_deadline`;
  `owner` = `appeals.owner`.
- `drug` = the medication under appeal (from case/appeal context), matched to the enum.
- `documented_failures` = `drug_trials.medication` where `documented = 1`; 
  `undocumented_or_insufficient_failures` = where `documented = 0`. Each list lowercase,
  alphabetical by medication.
- `criteria_results` = map template criterion ids → `case_criteria.result` (a step-
  therapy criterion with one documented + one undocumented failure is typically `partial`).
- `required_packet_items` / `missing_packet_items`: choose from the template enum.
  Required = the payer-appeal evidence items plus any assistance items in scope.
  Missing = the specific gaps: appeal-evidence gaps (e.g. the fill record for the
  undocumented trial) **before** assistance-info gaps (e.g. income proof). Ordering per
  template (payer-appeal items before assistance items; appeal gaps before assistance gaps).
- `assistance`: `program_name` = `assistance_screen.program_name`; map
  `assistance_status` to the template status (e.g. pending-missing-info →
  `eligible_missing_information`, ready → `eligible_ready`); `missing_fields` =
  `assistance_screen.missing_fields` (alphabetical).
- `next_action`: missing info → `request_more_information`; complete + expedited →
  the expedited action; ready to submit assistance → `submit_assistance_application`;
  etc. — per template enum.
- `basis_audit`: controlling = appeal id + documented trial id(s); exception =
  undocumented trial id(s) then assistance missing-field token(s); precedence_order =
  appeal/clinical records first, assistance items last.

## C. Payment-integrity claim repricing  (`CLAIM-…`)
Source precedence: `effective_benchmark_by_plan_modifier_and_date`.
Pull: `claims` (target), `claim_lines` (ORDER BY line_number), member `plan_type`,
`payment_benchmarks` for the `service_domain`.

- `claim_id`, `case_id` from the claim; `auth_number` = `claims.auth_number`.
- Benchmark selection per line: match `payment_benchmarks` on payer + member `plan_type`
  + `service_domain` + `cpt_code` + `modifier` whose `effective_start..effective_end`
  covers the service/reporting date. That current schedule's `source_name`/`source_version`
  are the answer's `benchmark_source`/`benchmark_version`. The expired/legacy schedule for
  the same CPT is `stale_source_rejected`; a distractor schedule is neither used nor cited.
- Per line: `line_id`, `cpt_code`, `modifier` (`null` if absent), `units`;
  `paid_amount` = `claim_lines.paid_amount`;
  `correct_allowed_amount` = benchmark `allowed_amount` × `units` (round to cents);
  `recovery_amount` = `correct_allowed_amount − paid_amount` (underpayment when positive);
  `disposition` = `correct_upward` if allowed>paid, `correct_downward` if allowed<paid,
  `no_change` if equal. Keep lines in `line_number` order.
- Totals: `paid_total` = Σ line paid; `correct_allowed_total` = Σ line allowed;
  `recovery_amount` = `correct_allowed_total − paid_total`. `resubmission_route` /
  `priority` per template enums (a standard underpayment correction →
  `payment_integrity_correction` / `standard`).
- `basis_audit`: controlling = the claim line ids **plus** the chosen current benchmark
  ids (evidence order); exception = the stale/legacy benchmark id(s); precedence_order =
  benchmark ids first, then the stale id.

## D. Peer-to-peer (P2P) final summary  (`P2P-…`)
Source precedence: `new_patient_specific_p2p_information`.
Pull: `p2p_events` (target), `case_criteria`, `request_lines`, `authorizations`,
`documents`.

- `p2p_id`, `p2p_outcome`, `final_status` from `p2p_events`; `requested_cpt` =
  `request_lines.cpt_code`.
- `criteria_results` = template criterion ids → `case_criteria.result`;
  `unresolved_criteria` = criterion ids not `met` (i.e. not_met/unclear), ascending.
- `new_information_changed_review` = whether the P2P supplied new patient-specific info
  that changed the decision. If `p2p_events.new_information` states the deciding factors
  were absent and the outcome upholds the adverse decision → `false`.
- `missing_pet_factors` = the PET-over-SPECT factors from the template enum that remain
  unsupported (per `new_information`/document summary), in the template's listed order.
- `letter_type`: approval / denial / partial_denial / no_letter per final_status.
- `recommended_alternative`: when the requested advanced modality is denied for a missing
  modality-specific factor, recommend the covered alternative (e.g. SPECT MPI when PET is
  denied); else `none`.
- `internal_appeal_deadline`: only when the final result is adverse — add the plan's
  internal-appeal window (e.g. 180 days, per prompt/memo) to the **final adverse
  determination date** (the P2P event/decision date). Otherwise `null`.
  Use `scripts/date_add.py <YYYY-MM-DD> <days>` for exact calendar arithmetic.
- `basis_audit`: controlling = the deciding clinical document(s) + the P2P event id;
  exception = the unmet criterion id then the missing modality-factor tokens;
  precedence_order = P2P event first (new info), then clinical doc, then the unmet criterion.

## E. Service-margin queue analysis  (`QUEUE-…`)
Source precedence: `margin_threshold_then_charge_sensitivity`.
Pull: `service_margin` for **only** the listed `queue_row_ids`, in that order.

Per row (definitions from `task_context.finance_memo` / template):
- `month_id`, `payer_segment`, `service_domain`, `cpt_code` from the row.
- `total_cost` = `variable_cost + fixed_cost_allocated` (round to cents).
- `margin` = `net_revenue − total_cost`.
- `revenue_to_cost_ratio` = `net_revenue / total_cost` (round to the template precision, e.g. 4dp).
- `below_threshold` = ratio < `threshold_revenue_to_cost_ratio` (e.g. 1.2).
- `charge_sensitive` = `service_margin.charge_sensitive == 1`.
- `recommended_action`: below-threshold → `payer_contract_review`; else charge-sensitive
  → `monitor_charge_sensitive`; else `monitor_no_action`.

Aggregates:
- `below_threshold_segments` = payer_segments of below-threshold rows, alphabetical.
- `charge_sensitive_segments` = payer_segments of charge-sensitive rows, alphabetical.
- `top_issue` = the worst below-threshold row as `"{payer_segment}_{cpt_code}"` (lowest
  ratio / most negative margin); `none` if no row is below threshold.
- `gap_to_120pct` = `threshold × total_cost − net_revenue` for the top-issue row
  (dollar gap to reach the threshold ratio), round to cents.
- `basis_audit`: controlling = all queue rows in queue order; exception = the
  below-threshold row(s); precedence_order = queue order (below-threshold ranked first
  under the margin-threshold precedence).

---

## Validation checklist (run before emitting)

1. Every required top-level key present, in the template's order; no extra keys if
   `additional_fields_allowed`/`additional_properties` is false.
2. Every enum value is one of the template's `choices` (exact spelling/case).
3. Lists obey the stated `ordering` (ascending id, alphabetical, claim-line order,
   queue-row order, template-choice order).
4. Numbers at the stated precision (currency 2dp, ratios to N dp); integers where
   required (units).
5. Dates in `YYYY-MM-DD`; `null` (not `""`/`0`) where the template says a value may be absent.
6. `basis_audit` has all four keys; ids in it are real environment record ids from the
   target scope; controlling vs exception split is correct; `precedence_record_order`
   is highest-priority-first.
7. Output is a single JSON object only — no markdown, no prose.
