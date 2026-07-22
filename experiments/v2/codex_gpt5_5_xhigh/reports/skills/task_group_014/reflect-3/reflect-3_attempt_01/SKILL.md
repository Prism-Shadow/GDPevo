---
name: payer-ops-structured-review
description: Produce structured JSON determinations for payer operations work such as utilization-management authorization review, pharmacy appeal intake, peer-to-peer closure, claim repricing, and finance margin queue analysis. Use when the task provides a payer operations environment plus an answer template and asks Codex to return schema-conformant operational JSON with criteria results, evidence records, calculations, routing, and basis audit fields.
---

# Payer Operations Structured Review

## Core Workflow

1. Read the prompt, task context, and answer template before querying data.
2. Treat the template as the contract: required keys, enum values, list ordering, date formats, numeric precision, null handling, and whether extra fields are allowed.
3. Use only the business environment access provided by the user. Do not inspect construction files, local databases, generated source data, manifests, or setup scripts.
4. Anchor all retrieval to the target business ID. Pull the primary record first, then related member, plan, provider, line, document, fact, criteria, authorization, appeal, P2P, claim, benchmark, or queue records as the work type requires.
5. Prefer current, patient-specific, effective-dated operational records over stale exports, generic distractors, or records for nearby non-target cases.
6. Produce JSON only. Do not include narrative explanation outside the object.

## Evidence And Criteria

- Join policy criteria to case criteria when available; case criteria normally carries the final result, supporting fact IDs, reviewer scope, and gaps.
- Use document facts to connect criteria to evidence. Evidence document lists should include the current documents relied on; excluded lists should include stale, non-current, or non-applicable documents.
- Preserve template-specified criterion IDs exactly. Use the template's required order unless it says to sort.
- For unmet or partial criteria, carry forward the explicit gap into missing-item, unresolved-criterion, or exception audit fields when the template provides those fields.
- If a missing item has both a generic category and a specific artifact choice in the template, prefer the specific artifact when the records identify it.

## Source-Precedence Patterns

- `current_clinical_records_over_stale_export`: base authorization determinations on current clinical documents, facts, request lines, active member/plan context, and authorization records. Exclude stale exports even when received with the case.
- `payer_appeal_before_manufacturer_assistance`: resolve payer appeal path, deadline, packet status, failures, and criteria before assistance screening. Assistance may affect next action and packet gaps, but it does not override payer appeal completeness.
- `effective_benchmark_by_plan_modifier_and_date`: select benchmark records matching payer, plan type, service domain, CPT/HCPCS, modifier including null modifiers, and service date. Reject stale schedules. Multiply allowed amount by units, then compare corrected allowed amounts with paid amounts.
- `new_patient_specific_p2p_information`: use the completed P2P event as the controlling record for outcome and final status. If the P2P upholds an adverse decision, list adverse criteria that remain not met as unresolved when the template asks for unresolved criteria. Calculate appeal deadlines from the final adverse or P2P completion date, not from queue/reporting dates.
- `margin_threshold_then_charge_sensitivity`: compute total cost first, then margin and revenue-to-cost ratio. Apply below-threshold action before charge-sensitive monitoring. Only use queue rows listed in the task context.
- `appeal_deadline_then_clinical_then_payment_integrity`: when mixed operational work is present, triage by deadline first, then clinical review gaps, then payment-integrity or finance corrections.

## Work-Type Notes

Authorization review:
- Sum requested units from request lines and compare with policy limits and authorization records.
- Approve only when active coverage, diagnosis, deficit, plan of care, and unit criteria are met within reviewer scope.
- Sort approved CPT/HCPCS codes as the template requires.

Pharmacy appeal intake:
- Classify documented medication failures separately from insufficiently documented failures.
- Build required packet items from appeal notes, criteria, policy, drug-trial evidence, and assistance requirements.
- Keep assistance status and missing assistance fields in the assistance object; also include them in packet gaps when the required packet includes assistance materials.

Claim repricing:
- Keep claim lines in source claim-line order.
- Use `null` for absent modifiers.
- Round currency to cents after applying units.
- For corrected allowed greater than paid, report the positive underpayment/recovery amount and an upward correction disposition.

Peer-to-peer closure:
- Use the P2P outcome and final status fields directly when present.
- A P2P statement that no new supporting factor was supplied usually does not mean the review changed.
- If the final result is adverse, set the adverse letter type and calculate the internal appeal deadline using the plan window from the adverse event date.

Margin queue analysis:
- `total_cost = variable_cost + fixed_cost_allocated`.
- `margin = net_revenue - total_cost`.
- `revenue_to_cost_ratio = net_revenue / total_cost`.
- `gap_to_threshold = threshold * total_cost - net_revenue` for the top below-threshold issue.
- Sort summary segment lists as directed by the template, not by row order.

## Basis Audit

Every answer with `basis_audit` should be reproducible from record IDs:

- `source_precedence`: choose the enum matching the controlling business rule.
- `controlling_record_ids`: list only records that directly determine the result, in operational evidence order.
- `exception_record_ids`: list records that explain exclusions, stale-source rejection, missing evidence, unmet criteria, below-threshold rows, or charge-sensitive routing.
- `precedence_record_order`: combine controlling and exception records in source-precedence order, highest priority first.

Use stable environment record IDs, not prose descriptions. Do not invent IDs. If a table uses a business ID as its primary key, use that business ID for the record.

## Final Checks

- Required top-level keys are present and spelled exactly.
- Enum values match the template exactly.
- Dates use `YYYY-MM-DD`; deadlines are calculated from the business event date specified by the record.
- Currency, ratios, and integer units use the requested precision.
- Lists follow the template's order rule.
- No unsupported extra fields are present when the template disallows them.
- The output is one valid JSON object and nothing else.
