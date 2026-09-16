---
name: northstar-payer-ops
description: Solve Northstar Health Plan payer-operations tasks by querying the provided environment and returning schema-conforming JSON for prior authorization, pharmacy appeals and assistance intake, claim repricing, peer-to-peer closure, service-margin queues, and mixed UM-finance triage. Use when prompts mention Northstar payer operations, UM nurse determination summaries, appeals coordinators, payment integrity correction packets, P2P summaries, queue analysis, answer_template.json, or the task environment SQL/API endpoints.
---

# Northstar Payer Operations

## Core Workflow

1. Read the user prompt, `input/payloads/task_context.json`, and `input/payloads/answer_template.json`.
2. Extract the target business IDs, reporting date or period, SQL base URL, bearer token, required output keys, enum choices, ordering rules, and numeric precision from those files.
3. Query only the running environment endpoints named by the prompt or context. Do not inspect local environment source, SQLite files, generated data, manifests, hidden tests, or broad distractor records when a target ID is known.
4. Treat `answer_template.json` as the output contract. Return exactly one JSON object, use only requested keys unless the template permits extras, and use enum strings exactly as listed.
5. Build a `basis_audit` for every answer when requested: choose the matching `source_precedence`, list direct controlling environment records, list gaps/exceptions/stale records, and order the precedence trail from highest-priority controlling source to lower-priority exceptions.

## Environment Access

Use the base URL and token supplied by the prompt or task context. The SQL endpoint accepts JSON with an `sql` key:

```bash
curl -sS "$BASE_URL/sql/query" \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d "{\"sql\":\"SELECT * FROM cases WHERE case_id = 'TARGET_ID'\"}"
```

Useful endpoints:

- `GET /api/tables` for table and column discovery.
- `GET /api/cases/{case_id}` for bundled case, member, provider, request line, document, fact, criteria, authorization, appeal, claim, assistance, and P2P records.
- `GET /api/policies/{policy_id}` or SQL over `policies` and `policy_criteria` when criterion text or missing-result rules are needed.
- SQL over `claims`, `claim_lines`, `payment_benchmarks`, and `service_margin` for calculations.
- SQL over `appeals`, `drug_trials`, and `assistance_screen` for pharmacy appeal and assistance intake.

Prefer targeted SQL or `GET /api/cases/{case_id}`. Use broad list endpoints only if the prompt does not provide the target ID and the task context cannot identify it.

## Common Tables

The environment is normalized around these tables:

- `cases`: target case metadata, `member_id`, `provider_id`, `policy_id`, `request_type`, `service_domain`, dates, stage, status, urgency.
- `members`, `plans`, `providers`: active coverage, plan type, payer, network, and provider context.
- `request_lines`: authorization lines with CPT, modifier, requested units, service dates, diagnoses, and charges.
- `documents`, `document_facts`: current and stale evidence, document summaries, criterion-supported facts.
- `policies`, `policy_criteria`, `case_criteria`: applicable policy, criterion text, final criterion results, evidence references, and gap descriptions.
- `authorizations`: authorization status, auth number, approved units, CPTs, modifier, dates, denial reason.
- `appeals`, `drug_trials`, `assistance_screen`: appeal route, deadlines, packet notes, medication failures, and assistance missing fields.
- `claims`, `claim_lines`, `payment_benchmarks`: paid claim, claim-line order, service dates, and effective rate schedules.
- `p2p_events`: completed peer-to-peer event, new information, outcome, final status, reviewer notes.
- `service_margin`: finance queue rows, revenue, variable cost, fixed allocated cost, and charge sensitivity.

## Source Precedence

Choose the `basis_audit.source_precedence` value that matches the business problem:

- `current_clinical_records_over_stale_export`: clinical prior authorization where current documents control and stale exports are excluded.
- `payer_appeal_before_manufacturer_assistance`: pharmacy coverage appeals with an associated manufacturer assistance screen; payer appeal packet gaps come before assistance gaps.
- `effective_benchmark_by_plan_modifier_and_date`: claim repricing; current effective benchmark records control over stale schedules.
- `new_patient_specific_p2p_information`: completed P2P closure; new patient-specific P2P information controls whether the review changes.
- `margin_threshold_then_charge_sensitivity`: service-margin queue analysis; below-threshold rows are addressed before charge-sensitive monitoring.
- `appeal_deadline_then_clinical_then_payment_integrity`: mixed UM-finance queue triage; open appeal deadlines come before clinical review gaps, which come before payment-integrity corrections.

For `controlling_record_ids`, include records that directly determine the result: current documents, P2P events, appeal IDs, documented trial IDs, claim lines, benchmark IDs, service-margin row IDs, or authorization IDs as applicable. For `exception_record_ids`, include stale document IDs, missing criteria IDs, unsupported factors, undocumented trial IDs, missing packet item strings, stale benchmark IDs, or below-threshold row IDs. Keep strings exactly as the environment or template names them.

## Prior Authorization Summaries

Use this flow for UM nurse determinations over therapy or similar clinical requests:

1. Load the case bundle and policy criteria for `case_id`.
2. Use `case_criteria.result` for each criterion required by the template; do not recompute a criterion unless the row is missing or contradicted by current evidence.
3. Rely on documents where `is_current = 1` and document facts support criteria. Exclude documents where `is_current = 0`, stale export summaries, unrelated episodes, or evidence not tied to the requested service.
4. If all approval-required criteria are `met` and coverage is active, recommend approval through the nurse route when allowed by the template.
5. If information is missing but not an automatic denial, pend for information. If a required criterion is `not_met` and nurse denial is not appropriate, route to medical director review. If the task is already a completed adverse review, return the final adverse status.
6. Fill authorization details from `authorizations` when present. Otherwise derive requested CPTs, modifier, dates, and units from `request_lines`. Split comma-separated CPT strings and sort when the template requires ascending CPT order.

Evidence documents are usually current documents supporting criteria. Excluded documents are usually stale or non-current documents for the same case. Use empty lists only when the template and evidence justify no records.

## Pharmacy Appeals And Assistance

Use this flow for coverage exception appeals and manufacturer assistance intake:

1. Load the case bundle, the target `appeals` row, current packet `documents`, `document_facts`, `drug_trials`, and `assistance_screen`.
2. Fill appeal route fields from the appeal row: path, expedited flag, deadline, owner, and appeal ID. Treat expedited as true only when the appeal path or attestation supports expedited handling.
3. Identify the drug from the case summary, document titles/summaries, appeal notes, or assistance program; use the exact enum from the template.
4. Use `case_criteria` for `criteria_results`.
5. Put `drug_trials.documented = 1` medications in `documented_failures`; put `documented = 0` medications in `undocumented_or_insufficient_failures`. Sort medication names alphabetically and lowercase them when required.
6. Build required packet items from appeal notes, policy criteria, and assistance requirements. Include payer appeal items before assistance items.
7. Build missing packet items from criterion gaps, undocumented trials, and assistance missing fields. When a missing fill record is named by medication, use the exact template item if present.
8. Map assistance rows conservatively: ready and no missing fields means `eligible_ready`; missing fields with otherwise eligible facts means `eligible_missing_information`; ineligible facts mean `not_eligible`; absent rows mean `not_applicable` when the template allows it.

Next action normally follows the highest-priority gap: missing appeal evidence means request more information; complete appeal packet with only assistance gaps follows the combined appeal/assistance action if the enum exists; ready assistance means submit the application; ineligible or unsupported appeal facts mean close or deny according to template choices.

## Claim Repricing

Use this flow for payment-integrity correction packets:

1. Load the target claim by `claim_id`; if the case ID differs, load the associated case and member.
2. Load claim lines ordered by `line_number`.
3. For each line, select the benchmark where payer, member `plan_type`, case `service_domain`, CPT, modifier, and service date match. Treat `NULL` modifiers as equal only to `NULL`; do not match them to non-null modifiers.
4. Apply the benchmark active on the line service date using `effective_start <= service_date <= effective_end`. If multiple current matches remain, use the latest `effective_start` and the source/version aligned with the case policy. Treat expired or legacy records for the same CPT/modifier as rejected stale sources.
5. Compute `correct_allowed_amount = benchmark.allowed_amount * line.units`, rounded to cents.
6. Compute line and total difference according to the template wording. If the template describes recovery as the correction difference, use corrected allowed minus paid; if it explicitly asks for overpayment recovery, use paid minus corrected allowed. Keep signs consistent with the requested disposition enum.
7. Set line disposition from the comparison: corrected greater than paid is `correct_upward`, corrected less than paid is `correct_downward`, equal is `no_change`, and a zero/non-covered benchmark or denial code may be `deny_line` if the template permits.
8. Sum paid and corrected totals from the claim and repriced lines. Round currency fields to two decimal places and output JSON numbers.

For the audit, controlling records include the relevant claim lines and selected benchmark rows. Exception records include stale or rejected benchmark rows that explain why the paid source should not control.

## Peer-To-Peer Closure

Use this flow for completed P2P summaries:

1. Load the case bundle, request line, current clinical documents/facts, `case_criteria`, `p2p_events`, and `authorizations`.
2. Use the completed P2P row for `p2p_id`, `p2p_outcome`, `final_status`, and whether new patient-specific information changed the review.
3. Use the request line for the requested CPT.
4. Use `case_criteria` for criterion results and list unresolved criteria where the final result is not `met` and the criterion remains applicable.
5. For PET MPI tasks, list missing PET-over-SPECT factors from the template choices when current evidence and P2P information do not support them. If PET is denied for missing PET-specific factors and the template permits an alternative, use SPECT MPI; otherwise use `none`.
6. For adverse final outcomes, compute the internal appeal deadline from the final adverse determination date using the plan rule in the prompt or case notes. If the prompt specifies a 180-day window, add 180 calendar days to the adverse determination date, usually the completed P2P event date. Use `null` only when no appeal deadline applies.

For the audit, the completed P2P event usually has higher precedence than earlier clinical documentation. Unsupported criteria or missing PET factors are exceptions.

## Service-Margin Queue Analysis

Use this flow for UM-finance margin queues:

1. Use row IDs from `task_context.finance_memo.queue_row_ids`; preserve that order in the output `rows`.
2. Query `service_margin` only for those row IDs and reporting period.
3. Compute `total_cost = variable_cost + fixed_cost_allocated`.
4. Compute `margin = net_revenue - total_cost`.
5. Compute `revenue_to_cost_ratio = net_revenue / total_cost`, rounded to the precision requested by the template.
6. Mark `below_threshold` when the ratio is less than the threshold from task context or template. Mark `charge_sensitive` from the row flag.
7. Choose `recommended_action`: below threshold gets payer contract review; otherwise charge-sensitive rows get charge-sensitive monitoring; otherwise monitor with no action.
8. Build `below_threshold_segments` and `charge_sensitive_segments` from affected payer segments, sorted as the template requires.
9. Choose `top_issue` from the below-threshold row with the largest positive gap to threshold; format as the template enum pattern. If no row is below threshold, use the no-issue enum if present.
10. Compute `gap_to_120pct` or similarly named gap as `threshold * total_cost - net_revenue` for the top below-threshold row, rounded to cents. Use zero only when no below-threshold issue exists and the template allows it.

For the audit, controlling records are the queue row IDs in task-context order. Exception records are below-threshold rows first, then other gap rows if requested. Charge-sensitive rows are controlling monitoring records, not exceptions unless the template treats sensitivity as a gap.

## Mixed Queue Triage

Use this flow when a queue contains appeal, clinical, and payment-integrity work items together:

1. Parse all queue item IDs and categories from task context, then query the relevant tables for each target.
2. Triage open appeal deadlines first, earliest deadline first.
3. Triage clinical authorization or P2P items next, prioritizing adverse or unresolved criteria over already-complete approvals.
4. Triage claim or margin payment-integrity items last, prioritizing stale benchmark corrections and below-threshold financial gaps over monitoring-only charge-sensitive rows.
5. Use `appeal_deadline_then_clinical_then_payment_integrity` for the audit source precedence when the template offers it.

## Output Normalization

- Return JSON only: no markdown, explanation, comments, or trailing text.
- Preserve template key names and nesting exactly.
- Use `null` where the template says null is allowed; otherwise use empty lists for no items.
- Sort lists according to template rules: document IDs ascending, medication names alphabetical, line rows by source line order, finance rows by task-context order, criteria IDs ascending when requested.
- Parse comma-separated environment strings into arrays only when the template expects lists.
- Round currency to two decimal places and ratios to the requested number of decimals. Avoid stringifying numeric fields.
- Use booleans as JSON booleans, not strings.
- Before finalizing, compare the produced object against every required key and enum in `answer_template.json`.
