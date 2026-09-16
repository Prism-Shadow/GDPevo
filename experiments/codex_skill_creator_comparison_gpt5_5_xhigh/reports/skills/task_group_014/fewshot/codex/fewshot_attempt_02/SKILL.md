---
name: northstar-payer-ops-json
description: Solve Northstar payer operations tasks that require retrieving authorization, appeal, claim, policy, document, rate schedule, P2P, or service-margin records from the task environment and returning a strict JSON object matching an answer_template.json schema. Use for UM determinations, pharmacy appeal intake, payment integrity repricing, peer-to-peer summaries, and payer-service margin queue summaries.
---

# Northstar Payer Ops JSON

## Core Workflow

1. Read the prompt, `input/payloads/task_context.json`, and `input/payloads/answer_template.json` before querying. Treat the template as the output contract: exact required keys, allowed enums, ordering, null handling, numeric precision, and whether extra fields are allowed.
2. Use only the task environment endpoints provided in the prompt or context. Do not inspect source files, generated data files, database files, manifests, or setup scripts. If using SQL, post JSON with an `sql` string and the bearer token from the task.
3. Query narrowly by the target business identifiers from the prompt/context. Pull every record type needed to justify the output, not just the record that names the target.
4. Apply the source-precedence rule that matches the business workflow. Use the rule both to decide the outcome and to populate `basis_audit`.
5. Return JSON only. Use JSON numbers for currency/ratios, ISO dates, and `null` when the template asks for null rather than an empty string.

Read [references/northstar-environment.md](references/northstar-environment.md) for table names, join keys, query patterns, and calculation rules.

## Evidence Collection By Workflow

For authorization/UM cases, retrieve the case, member, plan, provider, request lines, policy, policy criteria, case criteria, authorizations, documents, and document facts. Use current clinical records over stale exports. Current documents that support criteria are evidence; stale or superseded documents are exclusions/exceptions.

For pharmacy appeals, retrieve the appeal, case, policy/criteria, drug trials, documents, and assistance screen. Payer appeal routing, deadline, denial, member authorization, prescriber rationale, and formulary failure evidence control before manufacturer assistance. Documented medication failures go in `documented_failures`; undocumented, missing, or insufficient failures go in the insufficient list and audit exceptions.

For claim repricing, retrieve the claim, claim lines, associated case/member/plan when needed, and payment benchmarks. Match benchmarks by payer, plan type, service domain, CPT, modifier including null modifiers, and service date within the effective window. Reject stale or non-applicable schedules. Keep line output in claim-line order.

For P2P summaries, retrieve the case, request line, current clinical evidence, policy/criteria, P2P event, and authorization/adverse determination record. New patient-specific P2P information controls whether review changes. If the final result is adverse, calculate appeal deadlines from the adverse determination date and the plan appeal window, not from the report date unless the records say so.

For service-margin queues, retrieve only the queue rows identified by `task_context` unless the prompt explicitly expands scope. Preserve the requested row order. Separate below-threshold segments from charge-sensitive monitoring rows.

## Source Precedence

Use the `basis_audit.source_precedence` enum from the answer template. Common mappings:

- `current_clinical_records_over_stale_export`: UM medical-necessity decisions where current clinical documents supersede stale exports.
- `payer_appeal_before_manufacturer_assistance`: pharmacy coverage appeal plus assistance intake, with payer appeal packet/deadline controlling before manufacturer program readiness.
- `effective_benchmark_by_plan_modifier_and_date`: payment repricing where the effective benchmark is chosen by plan, modifier, CPT, and service date.
- `new_patient_specific_p2p_information`: peer-to-peer closure where new patient-specific facts can alter or uphold the medical review.
- `margin_threshold_then_charge_sensitivity`: finance queue work where below-threshold revenue-to-cost issues outrank charge-sensitive monitoring.
- `appeal_deadline_then_clinical_then_payment_integrity`: mixed appeal work where filing/deadline eligibility controls first, clinical support second, and payment-integrity corrections third.

For `basis_audit.controlling_record_ids`, list records that directly determine the result in operational evidence order. For `exception_record_ids`, list gaps, stale records, unsupported criteria, missing packet items, rejected benchmarks, or below-threshold rows in business gap order. For `precedence_record_order`, list the high-priority controlling and exception sources in precedence order; use record IDs or stable gap IDs exactly as they appear in the environment/template.

## Determination Rules

Map criteria from `case_criteria.result` when available. If required criteria are absent, use the template's allowed missing state, usually `unclear` or `not_applicable`, based on policy applicability. Do not invent criteria keys beyond the template.

Use authorization records for auth number, status, approved units, dates, CPT list, modifier, and denial reason. If all required criteria are met and an approved authorization exists, route to approval. If required facts are missing, pend/request information. If criteria remain not met or the case requires physician judgment, route to MD, P2P, denial, or adverse letter according to the status and workflow records.

Classify packet requirements from the appeal and assistance records. Required packet items should follow the template's operational order. Missing packet items should put appeal evidence gaps before assistance information gaps unless the template says otherwise. Assistance `missing_fields` should follow the template ordering, often alphabetical.

For claim corrections, compute each corrected allowed amount as matched benchmark allowed amount times units. Round currency to cents after applying units. Use a positive difference amount with the disposition carrying direction: upward correction when corrected allowed is greater than paid, downward correction when less, no change when equal.

For margin rows, compute `total_cost = variable_cost + fixed_cost_allocated`, `margin = net_revenue - total_cost`, and `revenue_to_cost_ratio = net_revenue / total_cost`. Use the task threshold for `below_threshold`. A below-threshold row recommends payer contract review; otherwise a charge-sensitive row recommends charge-sensitive monitoring; otherwise monitor with no action. `gap_to_120pct` is the positive dollar gap between threshold revenue and actual revenue for the top below-threshold issue, or zero if none.
