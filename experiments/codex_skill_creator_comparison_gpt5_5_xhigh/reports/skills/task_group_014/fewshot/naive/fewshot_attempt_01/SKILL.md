---
name: northstar-payer-ops-json
description: Solve Northstar Health Plan payer-operations tasks that require querying the shared task environment and returning structured JSON for utilization management authorizations, pharmacy appeals and assistance intake, payment-integrity claim repricing, peer-to-peer summaries, and service-margin queues. Use when the task mentions Northstar, payer operations, UM, appeals, claims, P2P, margin queues, an answer_template.json contract, or the SQL endpoint.
---

# Northstar Payer Ops JSON

## Core Workflow

1. Read the user prompt, `input/payloads/task_context.json`, and `input/payloads/answer_template.json` before querying.
2. Treat the answer template as the output contract. Return exactly one JSON object, with no markdown or explanatory prose.
3. Use only the task environment business endpoints and SQL endpoint. Do not inspect environment source files, database files, generated data, manifests, setup scripts, judge APIs, test answers, or unrelated local files.
4. Resolve the target identifiers from the prompt/context: case ID, appeal ID, claim ID, queue ID, row IDs, reporting date, and reporting period.
5. Query narrowly for records tied to those identifiers, then join outward by stable IDs such as `case_id`, `member_id`, `plan_id`, `policy_id`, `claim_id`, `appeal_id`, and row IDs.
6. Compute fields from current environment records. Do not infer from record names alone when table fields, criteria rows, documents, or benchmark rows provide the value.
7. Build `basis_audit` last from the evidence that actually controlled the output.
8. Validate the JSON against the template: required keys, enums, nullability, ordering, numeric precision, and no extra fields when disallowed.

For endpoint syntax, table names, and query patterns, read [Northstar data map](references/northstar-data-map.md) when working a task.

## Source Precedence

Select the `basis_audit.source_precedence` enum that matches the business workflow and apply it consistently:

- `current_clinical_records_over_stale_export`: use current clinical documents, facts, criteria, request lines, and authorization records before stale exports or non-current documents.
- `payer_appeal_before_manufacturer_assistance`: decide payer appeal path, deadline, criteria, and evidence gaps before manufacturer assistance status.
- `effective_benchmark_by_plan_modifier_and_date`: reprice claim lines with the benchmark effective for payer/plan, service domain, CPT, modifier, and service date; reject stale or nonmatching schedules.
- `new_patient_specific_p2p_information`: for peer-to-peer tasks, give priority to the completed P2P event and only change review when it supplies new patient-specific information that satisfies criteria.
- `margin_threshold_then_charge_sensitivity`: for margin queues, identify below-threshold payer-service issues first, then charge-sensitive monitoring rows.
- `appeal_deadline_then_clinical_then_payment_integrity`: when a task combines appeal timeliness, clinical review, and payment integrity, resolve deadline/route first, clinical sufficiency second, and payment correction facts third.

`controlling_record_ids` should include the environment records directly used to determine the result, in operational evidence order. `exception_record_ids` should include gaps, stale records, missing fields, rejected benchmarks, unmet criteria, or route-priority exceptions. `precedence_record_order` should list the decision-driving records or gap IDs in source-precedence order, highest priority first; keep it concise and do not pad it with every detail row when those rows do not explain precedence.

## Domain Rules

### UM Authorization

- Query the case, member, plan, provider, request lines, policy, policy criteria, case criteria, documents, document facts, and authorization.
- Use current documents and facts for `evidence_documents`; put stale or non-current documents in `excluded_documents` when the template asks for exclusions.
- Map required criteria IDs from the template to `case_criteria.result`; if missing, use policy `result_if_missing` or `unclear` when the template supports it.
- Use authorization fields for auth number, status, approved units, dates, CPT list, and modifier. Sort CPT/document lists as the template specifies.
- Route nurse approval only when all required nurse-scope approval criteria are met and an approval authorization is present. Use pending information or medical-director review when evidence gaps or reviewer scope require it.

### Pharmacy Appeal and Assistance

- Query the case, appeal, case criteria, drug trials, documents, policy criteria, and assistance screen.
- Use appeal records for path, expedited flag, deadline, owner, and outcome. A standard path is not expedited unless the appeal record or template criteria show expedited attestation.
- Classify drug failures from `drug_trials`: documented trials go in documented failures; undocumented, insufficient, missing, or unsupported trials go in the gap list. Normalize medication names to lowercase and sort alphabetically when required.
- Build payer appeal packet requirements before assistance requirements. Missing payer evidence remains a gap even if assistance screening is otherwise eligible.
- Use `assistance_screen.program_name`, status, and missing fields for the assistance object. Sort missing assistance fields alphabetically when required.
- Choose next action from the highest-priority gap: request information for missing appeal or assistance evidence; file or submit only when required evidence is complete.

### Payment Integrity Claim Repricing

- Query claim header, claim lines, member/plan context, related case/authorization when present, and payment benchmarks.
- Match benchmarks by payer/plan type, service domain, CPT, modifier including null modifier, and service date within effective start/end.
- Use the current effective benchmark source/version. Treat older, outside-date, wrong-plan, wrong-modifier, or distractor schedules as rejected sources.
- For each line: `correct_allowed_amount = benchmark_allowed_amount * units`; compare with paid amount to choose `correct_upward`, `correct_downward`, `no_change`, or `deny_line` using template enums.
- Totals are sums of line paid amounts and corrected allowed amounts. Correction/recovery amount is the dollar difference needed to correct payment; follow the template if it specifies underpayment or overpayment wording.
- Keep claim lines in source claim-line order and use JSON `null` for absent modifiers.

### Peer-to-Peer Summary

- Query the authorization case, request line, policy criteria, case criteria, current documents/facts, P2P event, and authorization status.
- Use the completed P2P event for P2P ID, outcome, final status, reviewer notes, and whether new information changed review.
- Mark `new_information_changed_review` true only when the P2P supplies new patient-specific evidence that changes applicable criteria results.
- Unresolved criteria are applicable criteria still `not_met` or `unclear`, ordered as the template specifies.
- For PET-over-SPECT tasks, list unsupported PET factors from policy/case criteria gaps in the template's choice order.
- If the final status is adverse, calculate the internal appeal deadline from the final adverse determination date and the plan's appeal window. Use `null` only when the template permits no deadline.

### Service Margin Queue

- Use only the queue row IDs listed in task context and preserve that row order.
- For each `service_margin` row: `total_cost = variable_cost + fixed_cost_allocated`, `margin = net_revenue - total_cost`, and `revenue_to_cost_ratio = net_revenue / total_cost`.
- `below_threshold` is true when the ratio is less than the task threshold. `charge_sensitive` follows the environment row flag.
- Recommended action priority: below-threshold rows use payer contract review; otherwise charge-sensitive rows use charge-sensitive monitoring; otherwise monitor with no action.
- Sort segment summary lists alphabetically unless the template says otherwise.
- Choose `top_issue` from below-threshold rows before charge-sensitive rows, using the largest dollar gap to the threshold when more than one row qualifies; use `none` only when no listed enum fits.
- `gap_to_120pct` or equivalent threshold gap is `max(0, threshold * total_cost - net_revenue)` for the selected below-threshold issue, rounded as required.

## Output Discipline

- Copy enum strings exactly from the answer template.
- Use ISO dates from environment records and compute deadlines with calendar-day arithmetic.
- Use JSON numbers, not strings, for numeric fields. Round currency to two decimals, ratios to the template precision, and units to integers.
- Normalize list ordering exactly as requested: source row order, claim-line order, ascending IDs, alphabetical medication/segment order, or enum-choice order.
- Parse JSON-like text fields and comma-separated fields into arrays only when the output template expects arrays.
- Prefer empty arrays for no items unless the template explicitly requires `null`.
- Before finalizing, mentally check every output value against an environment record, a formula, or a documented missing-information rule.
