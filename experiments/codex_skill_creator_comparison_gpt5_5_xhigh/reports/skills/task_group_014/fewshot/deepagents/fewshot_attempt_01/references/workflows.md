# Northstar Workflow Reference

## Record Discovery

Use `GET /api/tables` when schema is unclear. Common tables are:

- `cases`, `members`, `plans`, `providers`
- `request_lines`, `authorizations`
- `documents`, `document_facts`
- `policies`, `policy_criteria`, `case_criteria`
- `appeals`, `drug_trials`, `assistance_screen`
- `claims`, `claim_lines`, `payment_benchmarks`
- `p2p_events`, `service_margin`

Use `GET /api/cases/{case_id}` as the first pull for authorization, appeal, claim, and P2P tasks because it bundles related records. Use SQL when the task gives row IDs, claim IDs, benchmark matching requirements, or needs ordered joins.

## Basis Audit

Choose `source_precedence` from the template according to the controlling business conflict:

- `current_clinical_records_over_stale_export`: current documents and criteria control; stale or unrelated exports are excluded.
- `payer_appeal_before_manufacturer_assistance`: payer appeal eligibility, deadline, criteria, and medication-trial evidence control before assistance intake.
- `effective_benchmark_by_plan_modifier_and_date`: current benchmark schedules matching payer or plan, service domain, CPT, modifier, and service date control over stale schedules.
- `new_patient_specific_p2p_information`: the completed P2P event controls when it adds patient-specific information; if it only confirms missing facts, existing criteria gaps remain controlling.
- `margin_threshold_then_charge_sensitivity`: below-threshold revenue-to-cost issues control before charge-sensitive monitoring rows.
- `appeal_deadline_then_clinical_then_payment_integrity`: for mixed operations queues, sort appeal deadline risk before clinical-review items, then payment-integrity items unless the task states another priority.

Populate audit lists this way:

- `controlling_record_ids`: environment records that directly determine the result, in operational evidence order. Include line or row IDs when calculations depend on them.
- `exception_record_ids`: stale records, unsupported criteria IDs, missing packet fields, missing clinical factors, stale benchmark IDs, or below-threshold row IDs that explain gaps or exclusions.
- `precedence_record_order`: the precedence trail, highest-priority source first. This can be narrower than `controlling_record_ids` when many line or row records feed the same source decision.

## Authorization and UM Criteria

Use case, member, plan, request line, policy, case criteria, current documents, document facts, and authorization rows.

- Copy or normalize criterion results from `case_criteria` for the required criterion IDs.
- Treat `documents.is_current = 1` with facts supporting criteria as evidence. Treat `is_current = 0`, stale exports, unrelated episodes, or facts outside the requested service as excluded documents.
- If all approval-required criteria are met and an authorization row recommends or records approval, route to nurse approval and use the authorization row for auth number, units, dates, CPT list, and modifier.
- If a criterion with `result_if_missing = pend` is missing or unclear, pend for information before denial. If a required criterion with `result_if_missing = deny` is not met and no higher-priority route applies, prepare adverse determination or medical-director routing per the template.
- Split comma-separated CPT fields and sort if the template requires ascending CPT order.

## Pharmacy Appeal and Assistance

Use the case bundle plus appeals, case criteria, documents, document facts, drug trials, and assistance screen.

- Appeal path, deadline, expedited flag, owner, and outcome come from the appeal row unless the template supplies a stricter rule.
- `expedited` is true when the appeal path is expedited or the attestation documents serious health risk; otherwise false.
- Classify `drug_trials`: documented trials go to documented failures; undocumented trials or trials lacking required fill evidence go to insufficient failures. Normalize medication names to lowercase and sort as requested.
- Required packet items come from appeal notes, policy criteria, and template choices. Missing packet items include appeal evidence gaps before assistance-only gaps.
- Assistance program and missing fields come from `assistance_screen`. Map statuses containing ready or complete to `eligible_ready`, missing information to `eligible_missing_information`, explicit ineligibility to `not_eligible`, and absence of an applicable screen to `not_applicable`.
- Choose the next action from the highest-priority unresolved item: request missing appeal evidence before submitting assistance-only materials.

## Claim Repricing

Use claims, claim lines, member or plan type, case policy, payment benchmarks, and remittance/document facts.

- Preserve claim-line order from `claim_lines.line_number`.
- Match benchmarks by payer if available, plan type, service domain, CPT, modifier, and service date within `effective_start` through `effective_end`. A null claim modifier matches a null benchmark modifier.
- Reject stale benchmark rows whose effective period does not include the service date, even if their paid amounts match the claim.
- Calculate `correct_allowed_amount = benchmark.allowed_amount * units`.
- Calculate totals as sums of rounded line amounts. Use the claim's paid amounts for paid totals unless the template requires recalculation from lines.
- Set line disposition to `correct_upward` when corrected allowed is above paid, `correct_downward` when below paid, `no_change` when equal, and `deny_line` when the applicable benchmark or policy allows zero.
- Follow the template wording for correction or recovery sign. When the template treats underpayment correction as recovery, use a positive amount for corrected allowed minus paid.

## P2P Closure

Use the request line, current documents, case criteria, P2P event, and authorization row.

- Requested CPT comes from the authorization request line.
- P2P outcome and final status usually come from the completed `p2p_events` row, cross-checked against authorization status.
- `new_information_changed_review` is true only when the P2P event supplies new patient-specific facts that change a criterion result or final outcome.
- For PET MPI, the covered indication criterion and PET-over-SPECT factor criterion are separate. Missing factor outputs should follow the template's factor-choice order.
- If the final result is adverse and the task gives an internal appeal window, compute the deadline from the final adverse determination date. Use the P2P completion date when it is the final adverse action date.
- Recommend an alternative only when the policy or P2P record supports one; otherwise use the template's none value.

## Service Margin Queue

Use `task_context` row IDs and query `service_margin` narrowly.

- Preserve the exact row order supplied by `task_context`.
- `total_cost = variable_cost + fixed_cost_allocated`.
- `margin = net_revenue - total_cost`.
- `revenue_to_cost_ratio = net_revenue / total_cost`; if total cost is zero, follow the template or task-specific instruction rather than inventing a ratio.
- `below_threshold` is true when the ratio is below the provided threshold.
- `charge_sensitive` is true when the source row flag is truthy.
- Recommended action precedence is payer contract review for below-threshold rows, charge-sensitive monitoring for rows above threshold with the charge-sensitive flag, and monitor/no action otherwise.
- `below_threshold_segments` and `charge_sensitive_segments` should be unique, sorted as the template says, and derived only from rows in scope.
- `top_issue` should identify the highest-priority below-threshold payer/CPT issue. If none are below threshold, use the template's none value.
- `gap_to_120pct` or equivalent gap equals `(threshold * total_cost) - net_revenue` for the top below-threshold row, rounded as specified.
