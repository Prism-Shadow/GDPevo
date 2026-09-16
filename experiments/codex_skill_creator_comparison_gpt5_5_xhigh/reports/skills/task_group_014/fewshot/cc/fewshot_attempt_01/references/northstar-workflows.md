# Northstar Workflow Reference

This reference summarizes reusable patterns for Northstar payer-operations JSON tasks. It intentionally uses generic identifiers; derive all final values from the current task environment.

## Common tables

Use `/api/tables` or targeted SQL to confirm schema if needed. Common tables include:

- `cases`: case identity, member/provider links, request type, service domain, stage, status, due dates, urgency, summary.
- `members`, `plans`, `providers`: active member, plan, and provider context.
- `request_lines`: requested CPT/HCPCS, modifier, units, dates, diagnosis codes, billed charge.
- `policies`, `policy_criteria`, `case_criteria`: active policy version, criterion definitions, and case-specific criterion results/gaps.
- `documents`, `document_facts`: clinical or administrative documents, current/stale flags, extracted facts, supported criteria.
- `authorizations`: authorization number, status, approved units/dates/CPT/modifier, denial reason.
- `appeals`, `drug_trials`, `assistance_screen`: appeal path/deadline/owner, medication trial documentation, assistance program eligibility and missing fields.
- `claims`, `claim_lines`, `payment_benchmarks`: claim context, ordered claim lines, and effective allowed amounts by payer, plan type, service domain, CPT, modifier, and date.
- `p2p_events`: completed peer-to-peer discussion, new information, outcome, final status.
- `service_margin`: period queue rows, revenue, variable and fixed cost, payer segment, service domain, CPT, charge sensitivity.

## Retrieval checklist

Start with the target ID from the prompt and task context.

- Case-based work: query `cases` by `case_id`, then join or query member, plan, provider, request lines, policy, case criteria, documents, document facts, and authorizations for that case.
- Appeal work: query `appeals` by target appeal ID or case ID, then query the same case context plus `drug_trials` and `assistance_screen`.
- Claim repricing: query `claims` by claim ID, ordered `claim_lines`, member/plan context, and matching `payment_benchmarks`.
- Queue margin work: use the row IDs listed in task context and query only those `service_margin` rows, in that same order.
- P2P work: query `p2p_events` for the case along with current case criteria, request line, clinical documents, and authorization status.

Prefer SQL that is narrow and auditable. Example patterns:

```sql
SELECT * FROM cases WHERE case_id = :case_id;
SELECT * FROM request_lines WHERE case_id = :case_id ORDER BY line_id;
SELECT * FROM documents WHERE case_id = :case_id ORDER BY document_id;
SELECT * FROM case_criteria WHERE case_id = :case_id ORDER BY criterion_id;
SELECT * FROM claim_lines WHERE claim_id = :claim_id ORDER BY line_number;
```

## Source precedence

Set `basis_audit.source_precedence` to the rule that actually controls the result:

- `current_clinical_records_over_stale_export`: prior authorization or clinical determinations where current documents and facts override stale exports.
- `payer_appeal_before_manufacturer_assistance`: pharmacy coverage appeal work where appeal eligibility and packet gaps are resolved before assistance intake.
- `effective_benchmark_by_plan_modifier_and_date`: claim repricing where the current benchmark schedule is selected by payer, plan type, service domain, CPT, modifier, and service date.
- `new_patient_specific_p2p_information`: peer-to-peer closure where new patient-specific information can change, or fail to change, the final review.
- `margin_threshold_then_charge_sensitivity`: UM-finance margin queues where below-threshold economics are prioritized before charge-sensitive monitoring.
- `appeal_deadline_then_clinical_then_payment_integrity`: mixed queues where appeal deadlines outrank clinical review, which outranks payment-integrity correction unless the task states a different priority.

For `basis_audit.controlling_record_ids`, include the records that directly determine the answer. For `exception_record_ids`, include missing criteria IDs, stale records, rejected schedules, unsupported factors, or packet gaps. For `precedence_record_order`, list controlling and exception records in business precedence order, highest priority first.

## Prior authorization determinations

Retrieve case, member, plan, provider, request lines, policy criteria, case criteria, current documents/facts, stale or excluded documents, and authorization.

Apply the current clinical record rule:

- Current documents and their facts determine whether criteria are met.
- Stale exports or superseded documents should not control the determination; list them in excluded or exception fields when the template asks.
- If all approval-required criteria are met and an authorization record supports the approved details, route to nurse approval and issue approval.
- If information is missing or a criterion is unclear, pend or route according to the template choices.
- If required criteria are not met and nurse approval is not allowed, route to medical director review or denial as the task context requires.

Use authorization fields from `authorizations`, not from requested lines, when approved details are available. Sort approved CPT codes as the template requires.

## Pharmacy appeals and assistance

Retrieve the appeal record, case context, denial date, received date, appeal path, expedited attestation, owner, drug trial evidence, assistance screen, documents, and policy criteria.

Apply payer appeal before assistance:

- Use the appeal record for appeal path, expedited flag, owner, and deadline.
- Classify medication failures from `drug_trials`: documented failures go in the documented list; undocumented or insufficient trials go in the gap list. Sort medication names as requested.
- Required packet items come from appeal policy and assistance requirements. Missing packet items should separate payer appeal evidence gaps from assistance information gaps in the order required by the template.
- Assistance status and missing fields come from `assistance_screen`; keep assistance gaps separate from payer appeal criteria unless the template combines them.
- Choose the next action based on the blocking gap. Request more information when required appeal evidence or assistance fields are missing; file or submit only when the packet is ready.

## Payment integrity claim repricing

Retrieve the claim, ordered claim lines, member/plan context, and all benchmark rows matching payer, plan type, service domain, CPT, modifier, and service date.

Apply effective benchmark by plan, modifier, and date:

- Select benchmark rows whose effective range covers the claim line service date and whose CPT and modifier match the claim line. A null modifier matches a line with no modifier.
- Reject stale schedules outside the service date range or rows that match only by CPT while failing plan, modifier, service domain, or effective-date requirements.
- Calculate each line's correct allowed amount as benchmark allowed amount times units, rounded to cents.
- Compare correct allowed amount to paid amount. Use `correct_upward` when the correct allowed amount is greater than paid, `correct_downward` when it is lower, `no_change` when equal, and `deny_line` only when the benchmark or policy supports denial.
- Sum paid amounts and correct allowed amounts from the lines. The total correction amount is the absolute payment difference unless the template defines a directional field.
- Use claim-line order from the environment and use `null` for absent modifiers.

## Peer-to-peer closure

Retrieve the case, requested line, applicable policy criteria, case criteria, current clinical documents, P2P event, and authorization status.

Apply new patient-specific P2P information:

- Use the completed `p2p_events` record for outcome, final status, reviewer notes, and whether new information materially changed review.
- If the P2P supplies new patient-specific evidence that satisfies previously unresolved criteria, update criteria results and outcome accordingly.
- If no new information supports the missing factors, preserve the adverse result and list unresolved criteria and missing factors as the template requires.
- For PET MPI tasks, a covered indication alone is not enough; at least one supported PET-over-SPECT factor is needed unless the policy says otherwise.
- Use an internal appeal deadline only when an adverse final determination applies. If the plan specifies a 180-day window, add 180 calendar days to the final adverse determination date.

## UM-finance margin queues

Use only the queue row IDs supplied in task context and keep the output rows in that order.

Calculations:

- `total_cost = variable_cost + fixed_cost_allocated`
- `margin = net_revenue - total_cost`
- `revenue_to_cost_ratio = net_revenue / total_cost`
- `below_threshold = revenue_to_cost_ratio < threshold`
- `gap_to_threshold = threshold * total_cost - net_revenue` for the top below-threshold issue

Apply margin threshold before charge sensitivity:

- Rows below threshold get payer contract review before charge-sensitive monitoring.
- Rows at or above threshold with `charge_sensitive` true get charge-sensitive monitoring.
- Rows at or above threshold without charge sensitivity get monitor-no-action treatment.
- Below-threshold segments and charge-sensitive segments follow the ordering required by the template, often alphabetical.
- The top issue is the below-threshold payer/CPT issue with the largest positive gap to the threshold; use `none` when no row is below threshold.

## Final JSON checks

Before answering:

- Verify every required top-level key is present and no forbidden extra key is present.
- Verify every enum value appears exactly as listed in the template.
- Verify all dates are ISO calendar dates or `YYYY-MM` periods as requested.
- Verify list ordering against the template's ordering rule.
- Verify numbers use the requested precision and remain JSON numbers.
- Verify the basis audit names the correct source-precedence rule and does not include unrelated records.
