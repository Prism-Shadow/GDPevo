---
name: northstar-payer-ops
description: Solve Northstar Health Plan payer-operations tasks across UM authorization, pharmacy appeals, payment integrity, peer-to-peer, and finance margin queues using the shared environment, structured JSON answer templates, and business-audit precedence rules.
---

# Northstar Payer Operations

This skill covers five Northstar Health Plan workflows run against the shared
payer-operations environment: utilization management (UM) authorization
determinations, pharmacy coverage appeals, payment integrity claim repricing,
peer-to-peer (P2P) final summaries, and therapy margin queue analysis.

## Environment

Every task uses the same Northstar payer-operations environment. The solver
receives `<TASK_ENV_BASE_URL>` as the base URL.

- **SQL endpoint**: `POST /sql/query`
- **Authorization header**: `Authorization: Bearer pa-review-token-014`
- **Business REST endpoints** (all `GET` unless noted):

| Endpoint | Purpose |
|---|---|
| `/` or `/health` | Connectivity check |
| `/portal` | Portal overview or summary index |
| `/api/tables` | Available database tables |
| `/api/cases` | Case list |
| `/api/cases/{case_id}` | Single case record |
| `/api/policies` | Policy list |
| `/api/policies/{policy_id}` | Single policy with criteria |
| `/api/documents/{document_id}` | Single clinical or administrative document |
| `/api/rate-schedules` | Rate benchmark schedules |
| `/api/appeals` | Appeal records |

Always confirm the environment is reachable before gathering task-specific data.

## Workflow

1. **Read the task context** — Identify the target business ID (case, claim,
   appeal, or queue), the requester role, the reporting date, and any
   local memo detail about service domain, known deadlines, or special
   instructions.

2. **Read the answer template** — Note every required top-level key and every
   enum/choice constraint. The template is the contract: do not add fields it
   forbids, and do not omit a required key.

3. **Query the environment** — Pull the target record, its related records
   (policies, documents, appeals, rate schedules, or margin rows), and any
   reference data needed to apply criteria. Use the business endpoints for
   direct lookups and SQL for cross-entity queries.

4. **Apply criteria** — Evaluate each required criterion against the
   environment evidence. Classify every criterion as `met`, `not_met`,
   `partial`, `unclear`, or `not_applicable` per the template's allowed values.

5. **Classify records by source precedence** — Separate records that control the
   result from records that are stale, incomplete, or excluded. Use the
   correct precedence rule (see below).

6. **Fill the answer template** — Produce exactly one JSON object. Currency in
   dollars rounded to two decimal places; ratios to four decimal places;
   dates in `YYYY-MM-DD`; missing modifiers as `null` (not empty string).
   Lists follow template-specified ordering.

7. **Build the basis audit** — The `basis_audit` block is required in every
   answer. See [Basis Audit](#basis-audit) below.

## Source Precedence Rules

The `source_precedence` in the `basis_audit` identifies which rule governs.
Choose the rule that matches the task type:

| Rule | Workflow | Meaning |
|---|---|---|
| `current_clinical_records_over_stale_export` | UM authorization | Current clinical documents (eval, POC, imaging) override stale exports or superseded records. |
| `payer_appeal_before_manufacturer_assistance` | Pharmacy appeal | Resolve the payer appeal path and criteria before screening manufacturer assistance eligibility. |
| `effective_benchmark_by_plan_modifier_and_date` | Payment integrity | Use the current rate schedule effective for the plan, modifier, and service date; reject stale schedule sources. |
| `new_patient_specific_p2p_information` | Peer-to-peer | The P2P event supplies new patient-specific information that governs whether the review changed. |
| `margin_threshold_then_charge_sensitivity` | Finance margin queue | Classify each row first by the revenue-to-cost threshold, then by charge sensitivity flag. |

The solver maps the task to the rule by matching the workflow type (UM auth,
appeal, claim repricing, P2P, or margin queue) to the rule in the table above.

## Basis Audit

Every answer includes a `basis_audit` object with these keys:

- `source_precedence` — The rule from the table above.
- `controlling_record_ids` — Environment record IDs that directly control the
  result (active case, current documents, effective benchmarks, valid appeal
  records, P2P event, margin rows). List in operational evidence order.
- `exception_record_ids` — Records that explain gaps, exclusions, denials,
  missing information, or route priority. List criteria/routing gaps before
  stale or excluded records when both appear.
- `precedence_record_order` — The controlling and exception records combined,
  in source-precedence order from highest to lowest priority.

## Workflow-Specific Patterns

### UM Authorization (Physical Therapy, Imaging, etc.)

- Pull the case from `/api/cases/{case_id}`.
- Pull the policy from `/api/policies/{policy_id}` to get the criteria IDs.
- Pull each document referenced by the case from `/api/documents/{document_id}`.
- Classify documents as evidence (current clinical) or excluded (stale,
  superseded, or not relevant to the requested service).
- Evaluate each criterion. If all criteria are `met`, recommend `approve`;
  if any are `not_met` or `unclear`, escalate or deny accordingly.
- Set `authorization` fields from the active auth record or case plan.
- Choose the `determination_letter` matching the final status.
- The route follows the recommendation: nurse-approval path for clear
  approvals, MD review for unclear/denied cases.

### Pharmacy Appeal and Manufacturer Assistance

- Pull the appeal from `/api/appeals`.
- Pull the case from `/api/cases/{case_id}`.
- Identify the drug; pull policy criteria and trial/drug records.
- Classify each trial/failure record as `documented_failures` or
  `undocumented_or_insufficient_failures`. A documented failure means a
  completed trial with clinical evidence. An undocumented or insufficient
  record means a trial that was started but not completed, lacks sufficient
  documentation, or is ambiguous.
- Evaluate DRUG-AUTH, DRUG-DENIAL, DRUG-RATIONALE, and DRUG-FAILURES criteria.
- Determine the appeal path: `standard_internal` for routine appeals,
  `expedited_internal` when medically urgent, `external_review` after
  internal exhaustion, `not_eligible` when deadlines or conditions fail.
- Compute the appeal deadline: 180 calendar days from the adverse
  determination date for internal appeals (check the plan's window in the
  task context if specified). For task types that specify a 180-day window,
  calculate `denial_date + 180 days`.
- List `required_packet_items` in operational order (payer appeal items before
  assistance items). List `missing_packet_items` with appeal evidence gaps
  before assistance information gaps.
- For manufacturer assistance: check the program name against the drug,
  determine eligibility status, and list missing documentation fields in
  alphabetical order by field ID.

### Payment Integrity Claim Repricing

- Pull the claim and claim lines from the environment.
- Pull rate schedules from `/api/rate-schedules` to find the current and
  stale benchmark sources.
- Match each claim line's CPT code (and modifier, when present) against the
  correct benchmark schedule to get the `correct_allowed_amount` per unit.
- Multiply by line units to get the line-level correct allowed total.
- Recovery amount per line = `correct_allowed_amount - paid_amount` (positive
  means underpayment/correct-upward, negative means overpayment/correct-downward,
  zero means no change).
- Sum across lines for the claim-level totals.
- Identify the current benchmark used (`benchmark_source` and
  `benchmark_version`) and the rejected stale source (`stale_source_rejected`).
  Use `"none"` only when no stale source exists.
- The `disposition` for each line is `correct_upward` (recovery > 0),
  `correct_downward` (recovery < 0), `no_change` (recovery = 0), or
  `deny_line` when the line should not be paid.
- `recovery_amount` at the claim level is the net underpayment amount
  (correct_allowed_total - paid_total). When this is negative, it represents
  an overpayment recovery.

### Peer-to-Peer Final Summary

- Pull the case, policy criteria, clinical documents, and the P2P event record.
- Identify the requested CPT from the authorization line.
- Set `p2p_outcome`: `overturn_to_approval` when the P2P reverses a denial,
  `uphold_intended_adverse_decision` when it confirms the denial,
  `not_applicable` when no P2P occurred.
- Evaluate each applicable criterion (e.g., PET-IND, PET-FACTOR for PET MPI).
  Mark criteria that remain unresolved after P2P in `unresolved_criteria`.
- `new_information_changed_review` is `true` only when the P2P supplied
  material new patient-specific evidence (not just a restatement).
- `missing_pet_factors`: for PET MPI tasks, list each factor from the set
  `[prior_equivocal_spect, bmi_limitation, attenuation_artifact]` that remains
  unsupported after the P2P, in the order shown.
- `recommended_alternative`: `SPECT MPI` when PET is denied and SPECT is
  appropriate, `PET MPI` when approved, `none` otherwise.
- `internal_appeal_deadline`: when the final determination is adverse, compute
  as `adverse_determination_date + 180 calendar days`. Use `null` when no
  appeal deadline applies (e.g., approved cases).
- `letter_type`: matches the final status.

### Therapy Margin Queue

- Pull the queue rows identified by the task context.
- For each row compute:
  - `total_cost = variable_cost + fixed_cost_allocated`
  - `margin = revenue - total_cost`
  - `revenue_to_cost_ratio = revenue / total_cost`
- Classify `below_threshold`: `true` when `revenue_to_cost_ratio < threshold`
  (default 1.2 unless the task specifies otherwise).
- Classify `charge_sensitive` from the environment data.
- Assign `recommended_action`:
  - `payer_contract_review` when below threshold
  - `monitor_charge_sensitive` when above threshold but charge-sensitive
  - `monitor_no_action` otherwise
- The `below_threshold_segments` list contains the payer segments (alphabetical)
  where at least one row is below threshold.
- The `charge_sensitive_segments` list contains the payer segments (alphabetical)
  where at least one row is charge-sensitive.
- `top_issue`: the most impactful below-threshold row, identified by the
  largest dollar gap. Format as `{segment}_{cpt_code}`. Use `"none"` when no
  rows are below threshold.
- `gap_to_120pct`: the dollar shortfall from actual revenue to 1.2 × total_cost
  for the top below-threshold row.

## Common Conventions

- **Currency**: JSON numbers in dollars rounded to two decimal places.
- **Ratios**: Four decimal places (e.g., 0.9028).
- **Dates**: `YYYY-MM-DD` for calendar dates; `YYYY-MM` for periods.
- **Null modifiers**: use `null`, never an empty string.
- **List ordering**: Follow the template's ordering rule for each list. Default
  to alphabetical by ID or ascending by code unless specified otherwise.
- **Evidence classification**: A document is "excluded" when it is stale
  (superseded by a newer version or export), not relevant to the requested
  service, or insufficient to support a criterion. Current, service-relevant,
  and criterion-supporting documents are "evidence."
- **ID formats**: Cases are `CASE-*`, appeals `APL-*`, claims `CLAIM-*`, P2P
  events `P2P-*-E*`, margin rows `SM-*`, documents `DOC-*`, benchmarks `BM-*`,
  trials `TRIAL-*`, auth numbers `NPA-*`.
- **No narrative**: Return only the JSON object. Do not include markdown,
  comments, or prose outside the JSON.
- **Do not inspect filesystem**: Use only the environment endpoints and SQL.
  Do not read environment source files, database files, manifests, or
  construction scripts.
