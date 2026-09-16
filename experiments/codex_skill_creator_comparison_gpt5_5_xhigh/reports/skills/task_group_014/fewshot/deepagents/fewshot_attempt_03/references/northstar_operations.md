# Northstar Operations Reference

## Environment Access

Use the base URL and credentials provided in the current task prompt or
`task_context.json`. The SQL endpoint accepts:

```json
{"sql": "SELECT ..."}
```

with an `Authorization: Bearer ...` header when the task provides a token. Use
`GET /api/tables` to inspect table names and columns. Use business endpoints
such as cases, policies, documents, rate schedules, and appeals when they are
faster than SQL, but keep all evidence from the live environment.

Useful SQL discovery pattern:

```sql
SELECT * FROM cases WHERE case_id = 'TARGET_ID';
SELECT * FROM request_lines WHERE case_id = 'TARGET_ID' ORDER BY line_id;
SELECT * FROM case_criteria WHERE case_id = 'TARGET_ID' ORDER BY criterion_id;
SELECT * FROM documents WHERE case_id = 'TARGET_ID'
  ORDER BY is_current DESC, document_date DESC, document_id;
SELECT * FROM document_facts WHERE case_id = 'TARGET_ID'
  ORDER BY document_id, fact_key;
```

## Table Map

- `cases`: core case metadata, service domain, policy ID, dates, status, and summary.
- `members`, `plans`, `providers`: eligibility, plan type, payer, network, and provider context.
- `request_lines`: requested CPT/HCPCS, modifier, units, diagnosis, dates, and charges.
- `authorizations`: authorization status, approved units/dates/CPT/modifier, auth number, and denial reason.
- `policies`, `policy_criteria`, `case_criteria`: applicable policy versions, criterion text, case-specific results, evidence facts, and gaps.
- `documents`, `document_facts`: clinical and administrative evidence, current/stale markers, source systems, summaries, and structured facts.
- `appeals`, `drug_trials`, `assistance_screen`: appeal route/deadline/owner, medication failure evidence, and manufacturer assistance status or missing fields.
- `claims`, `claim_lines`, `payment_benchmarks`: payment-integrity repricing inputs, service dates, line order, paid amounts, and effective benchmark schedules.
- `p2p_events`: completed peer-to-peer discussion, new information, outcome, final status, reviewer, and notes.
- `service_margin`: finance queue rows, net revenue, variable cost, fixed cost allocation, payer segment, CPT, and charge-sensitive flag.

## Output Contract Rules

- The answer template is authoritative. Use its required keys, enums, list ordering, nullability, date format, and precision rules.
- Return one JSON object only. Do not wrap it in markdown.
- Do not add fields unless the template explicitly permits additional properties.
- For ordered IDs, follow the template's operational order. For alphabetical segments or medications, normalize case as requested and sort by the normalized string.
- For current versus stale evidence, current clinical or operational records control; stale exports and stale documents usually belong in exclusions or exceptions.

## Prior Authorization UM Reviews

Use for therapy or other authorization determination summaries.

1. Query the target case, request lines, member/plan, policy and policy criteria, case criteria, current and stale documents, document facts, and authorization record.
2. Evaluate each required criterion key from the template against `case_criteria`, supported document facts, and current documents.
3. Prefer current clinical records over stale exports. Include relied-upon current document IDs as evidence and stale or irrelevant case document IDs as excluded documents when the template asks.
4. If all nurse-review criteria are met and an approval authorization exists or can be supported by the records, route to nurse approval and issue approval. If criteria are unclear, pend for information. If criteria are not met or require physician judgment, route to medical director review or adverse determination according to the template choices.
5. Use authorization table values for auth number, approved units, approved date span, approved CPT list, and modifier. Sort CPT codes if required.

## Pharmacy Appeal and Assistance Intake

Use for coverage appeals paired with manufacturer assistance screening.

1. Query the case, appeal, drug trial records, denial and rationale documents, criteria, and assistance screen.
2. Payer appeal disposition controls before manufacturer assistance. Assistance status and gaps can affect packet requirements and next action, but should not override appeal eligibility/deadline/route.
3. Classify medication failures from `drug_trials`: documented failures go in the documented list; undocumented, missing, or insufficient trials go in the insufficient list.
4. Required packet items usually include denial notice, member authorization, prescriber rationale, formulary failure evidence, and assistance-specific proofs when assistance is in scope. Missing packet items should reflect appeal evidence gaps before assistance information gaps.
5. Use appeal records for appeal path, expedited flag, owner, and deadline. Use assistance records for program name, status, and missing fields.

## Payment Integrity Claim Repricing

Use for claim correction packets and rate schedule disputes.

1. Query the target claim and claim lines. Keep line output in source claim-line order.
2. Join member/plan context when needed to select payer, plan type, and service domain.
3. Select `payment_benchmarks` by payer, plan type, service domain, CPT code, modifier, and service date within effective start/end. Prefer the effective benchmark for the service date over legacy or distractor schedules.
4. Calculate `correct_allowed_amount = allowed_amount * units` per line, rounded to cents. Compare with `paid_amount` to set line `recovery_amount` and disposition: upward correction when correct allowed is greater, downward correction when lower, no change when equal.
5. Sum paid and corrected totals from line values. The packet-level recovery amount is the difference requested by the template, rounded to cents.
6. Put rejected stale or inapplicable benchmark IDs in `exception_record_ids`; controlling benchmark and line IDs belong in the audit trail.

## Peer-to-Peer Dispositions

Use for completed P2P summaries after medical director discussion.

1. Query case, request line, policy criteria, case criteria, current clinical documents, document facts, P2P event, and authorization status.
2. New patient-specific information from the P2P controls the final review if it materially changes criteria. If no new patient-specific information changes the review, preserve the criteria result supported by current evidence.
3. Populate unresolved criteria from criteria still not met or unclear. For modality-specific factors, use the gap descriptions, criteria text, or P2P notes to list unsupported factors in the template's required order.
4. If final result is adverse, calculate internal appeal deadline from the adverse determination date and plan appeal window when provided. Use JSON `null` when no appeal deadline applies.
5. Use the P2P event for P2P ID, outcome, final status, and whether new information changed the review.

## Therapy Finance Margin Queues

Use for UM-finance margin queue summaries.

1. Use only queue row IDs identified by task context. Preserve that exact row order.
2. For each `service_margin` row, calculate:

```text
total_cost = variable_cost + fixed_cost_allocated
margin = net_revenue - total_cost
revenue_to_cost_ratio = net_revenue / total_cost
gap_to_threshold = threshold * total_cost - net_revenue
```

3. Round money to cents and ratios to the template precision.
4. `below_threshold` is true when the ratio is below the threshold. `charge_sensitive` comes from the row flag.
5. Recommended action precedence is threshold failure first, then charge sensitivity, then monitor/no action. Segment lists follow the template ordering rule.
6. The top issue is the below-threshold row with the largest positive gap to threshold; use `none` and zero only when no row is below threshold and the template permits that.

## Cross-Type Precedence

Choose the source-precedence enum that matches the decisive workflow:

- `current_clinical_records_over_stale_export`: current clinical evidence decides authorization criteria; stale documents are exceptions.
- `payer_appeal_before_manufacturer_assistance`: appeal eligibility, deadline, and evidence control before assistance intake gaps.
- `effective_benchmark_by_plan_modifier_and_date`: effective rate schedule by payer/plan/service/CPT/modifier/date controls repricing.
- `new_patient_specific_p2p_information`: P2P information controls only when it is new and patient specific.
- `margin_threshold_then_charge_sensitivity`: below-threshold margin issues outrank charge-sensitive monitoring.
- `appeal_deadline_then_clinical_then_payment_integrity`: when a mixed task spans appeal, clinical, and payment issues, decide appeal timeliness/route first, then clinical criteria, then payment correction.
