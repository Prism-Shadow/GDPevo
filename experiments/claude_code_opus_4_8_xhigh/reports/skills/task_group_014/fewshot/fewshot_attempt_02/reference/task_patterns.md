# Task-family derivation recipes

Five families have appeared. Identify the family from the answer_template, then derive
each field from the environment as below. The template is always the authority on shape;
these recipes tell you *where the values come from* and *what logic to apply*. Never copy
values from another task — recompute from this target's records.

Each family maps to exactly one `basis_audit.source_precedence` enum (last column).

| Family | `source_precedence` |
|---|---|
| UM nurse prior-auth determination | `current_clinical_records_over_stale_export` |
| Pharmacy appeal + assistance intake | `payer_appeal_before_manufacturer_assistance` |
| Payment-integrity claim repricing | `effective_benchmark_by_plan_modifier_and_date` |
| Peer-to-peer closure | `new_patient_specific_p2p_information` |
| UM-finance margin queue | `margin_threshold_then_charge_sensitivity` |

A sixth precedence, `appeal_deadline_then_clinical_then_payment_integrity`, is offered by
the templates for a task that blends an appeal deadline with clinical + payment-integrity
signals; use it if a future task's structure matches that description.

---

## A. UM nurse prior-authorization determination

Sources: `cases`, `request_lines`, `case_criteria` (+ policy `result_if_missing`),
`documents`, `authorizations`. Pull via `GET /api/cases/{case_id}`.

- `criteria_results`: map each required criterion id → `case_criteria.result`.
- `recommendation` / `final_status` / `route` / `determination_letter` / `next_action`:
  driven by the criteria and the pre-staged `authorizations.status`.
  - All approval-required criteria `met` → approve / approved / nurse_approval /
    approval / issue_approval (`authorizations.status` = `recommended_approval`).
  - A criterion `not_met`/`unclear`: use its `result_if_missing` — `pend` → pend path
    (pended / pending_information / information_request / request_more_information);
    `deny` → deny path; ambiguous clinical judgement → escalate/MD review. Confirm
    against `authorizations.status`/`denial_reason`.
- `authorization` object: take `auth_number`, `approved_units`, `approved_start`,
  `approved_end`, `approved_cpt` (split the comma-joined string into a list, sorted
  ascending by code), `modifier` from the `authorizations` row. `approved_units` is the
  authorized total (matches the summed requested units when fully approved).
- `evidence_documents`: `documents` with `is_current = 1`, as `document_id`s ascending.
- `excluded_documents`: `documents` with `is_current = 0` (stale/superseded exports),
  ascending.
- **basis_audit:** controlling = the current evidence `document_id`s (ascending);
  exception = the stale/non-current `document_id`s; precedence_order = evidence docs then
  stale docs.

## B. Pharmacy coverage appeal + manufacturer assistance intake

Sources: `appeals`, `drug_trials`, `case_criteria`, `assistance_screen`, `policies`.

- `appeal_id`, `appeal_path`, `expedited` (from `expedited_attestation`), `appeal_deadline`,
  `owner`, `drug`: from the `appeals` row (and case/policy context).
- `documented_failures`: `drug_trials.medication` where `documented = 1`, lowercased,
  alphabetical.
- `undocumented_or_insufficient_failures`: `drug_trials` where `documented = 0`,
  lowercased, alphabetical.
- `criteria_results`: each required `DRUG-*` id → `case_criteria.result` (a step-therapy
  criterion with one documented + one undocumented failure is typically `partial`).
- `required_packet_items`: the payer-appeal items named in `appeals.notes`, then the
  assistance item(s) — operational order = appeal items before assistance items.
- `missing_packet_items`: gaps, appeal-evidence gaps before assistance gaps — e.g. a
  fill-record for the undocumented trial, plus any `assistance_screen.missing_fields`.
- `assistance`: `program_name`, `status` (map `assistance_status`, e.g.
  pending-missing-income → `eligible_missing_information`), `missing_fields`
  (from `assistance_screen.missing_fields`, alphabetical).
- `next_action`: driven by the gaps (missing info → `request_more_information`, etc.).
- **basis_audit:** controlling = `appeal_id` then the documented trial id(s) (evidence
  order); exception = the undocumented trial id(s) then the missing assistance field
  token(s) (criteria/route gaps before missing-info); precedence_order = appeal id,
  documented trial(s), undocumented trial(s), missing field token(s) — payer appeal
  before manufacturer assistance.

## C. Payment-integrity claim repricing

Sources: `claims`, `claim_lines`, `payment_benchmarks`.

- `auth_number`, `paid_total`: from `claims`.
- For each `claim_lines` row (in `line_number` order) find the benchmark matching
  payer + plan_type + service_domain + `cpt_code` + `modifier`, whose
  `effective_start..effective_end` covers the line's `service_date`. That current row is
  the benchmark; an older/expired row from a legacy/stale source is the rejected one.
  Ignore "Distractor Schedule" rows and rows from other id namespaces.
- Per line: `correct_allowed_amount` = benchmark `allowed_amount` × `units`
  (round to cents); `paid_amount` from the line; `recovery_amount` = correct − paid;
  `modifier` = the code or `null`; `disposition` = `correct_upward` when correct > paid,
  `correct_downward` when correct < paid, `no_change` when equal.
- Totals: `correct_allowed_total` = Σ corrected; `recovery_amount` = correct_total −
  paid_total (an underpayment when positive).
- `benchmark_source` / `benchmark_version` = the current source's `source_name` /
  `source_version`; `stale_source_rejected` = the stale source's `source_name` (or `none`).
- `resubmission_route` / `priority`: operational (e.g. `payment_integrity_correction`,
  `standard`).
- **basis_audit:** controlling = the `claim_line_id`s (claim-line order) then the current
  benchmark ids used; exception = the stale benchmark id(s); precedence_order = the
  current benchmark ids then the stale benchmark id (effective-benchmark rule, current
  before stale).

## D. Peer-to-peer closure

Sources: `p2p_events`, `case_criteria`, `request_lines`, `documents`, `document_facts`,
`authorizations`.

- `p2p_id`, `p2p_outcome`, and (adverse) `final_status`: from the `p2p_events` row.
- `requested_cpt`: from the authorization/request line.
- `criteria_results`: required `PET-*` ids → `case_criteria.result`.
- `unresolved_criteria`: criterion ids not `met`, ascending (empty only if none).
- `new_information_changed_review`: whether the P2P supplied new patient-specific info
  that changed the outcome (read `p2p_events.new_information`; typically `false` when the
  intended adverse decision is upheld).
- `missing_pet_factors`: from the `choices`, each PET-over-SPECT factor still unsupported
  (all three when the PET-factor criterion is `not_met` and none is documented), in the
  order shown in `choices`.
- `letter_type` / `recommended_alternative`: e.g. denial → `denial` letter and
  `SPECT MPI` alternative when PET is denied.
- `internal_appeal_deadline`: **only when the final result is adverse** — add the plan's
  internal-appeal window (e.g. 180 days, per the prompt/memo) to the **final adverse
  determination date** (the P2P/decision date), formatted `YYYY-MM-DD`; else `null`.
- **basis_audit:** controlling = the clinical evidence doc id(s) and the P2P event id;
  exception = the unmet criterion id then the missing factor tokens (gaps first);
  precedence_order = P2P event, clinical doc, unmet criterion (new-P2P-information rule).

## E. UM-finance margin queue

Sources: `service_margin`, using the exact `month_id`s from the memo, in that order.

Per row (definitions come from the memo, e.g. total-cost = variable + fixed-allocated,
threshold ratio e.g. 1.2):
- `total_cost` = `variable_cost` + `fixed_cost_allocated` (2 decimals).
- `margin` = `net_revenue` − `total_cost` (2 decimals).
- `revenue_to_cost_ratio` = `net_revenue` / `total_cost` (4 decimals).
- `below_threshold` = ratio < threshold.
- `charge_sensitive` = the row's `charge_sensitive` flag (bool).
- `recommended_action`: `below_threshold` → `payer_contract_review`; else if
  `charge_sensitive` → `monitor_charge_sensitive`; else `monitor_no_action`.
- `payer_segment` / `service_domain` / `cpt_code` / `month_id`: from the row.

Aggregates:
- `below_threshold_segments`: segments of below-threshold rows, alphabetical.
- `charge_sensitive_segments`: segments flagged charge-sensitive, alphabetical
  (memo: keep below-threshold issues separate from charge-sensitive rows).
- `top_issue`: the worst below-threshold row as `"{segment}_{cpt}"` (or `none`).
- `gap_to_120pct` = threshold × total_cost − net_revenue for that top issue (2 decimals).
- **basis_audit:** controlling = all queue `month_id`s in the memo's listed order;
  exception = the below-threshold row id(s); precedence_order = the rows in listed order
  (margin-threshold-then-charge-sensitivity rule).

---

## basis_audit — general construction (all families)

The object always has four keys:

- `source_precedence`: the single enum for the family (table above).
- `controlling_record_ids`: environment ids that directly produce the result, in
  operational evidence order (the "winning" records).
- `exception_record_ids`: gap/exclusion records explaining what was set aside —
  **criteria/route gaps before stale/excluded records** when both appear. For drivers
  that are requirements rather than stored rows, use the template's own token (e.g.
  `household_income_proof`, `PET-FACTOR`, `prior_equivocal_spect`).
- `precedence_record_order`: the controlling records then the exception records, ordered
  highest-priority-first under the precedence rule. It may be a curated subset that
  captures the "what superseded what" narrative (e.g. current benchmarks then the stale
  one; evidence docs then the stale export; P2P then note then unmet criterion) rather
  than repeating every controlling id.
