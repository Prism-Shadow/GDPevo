---
name: northstar-payer-ops-json
description: Solve Northstar Health Plan payer-operations tasks that require a strict JSON answer from the shared task environment, including utilization-management determinations, pharmacy appeals and assistance intake, payment-integrity claim repricing, peer-to-peer outcomes, and UM-finance margin queues. Use when a prompt mentions Northstar, payer operations, a SQL/query endpoint, case/claim/appeal/queue records, answer_template.json, task_context.json, criteria results, source precedence, basis_audit, or returning JSON only.
---

# Northstar Payer Operations JSON

Use this skill to produce one schema-conforming JSON object for Northstar payer operations tasks. The stable challenge is not writing prose; it is retrieving the right operational records, applying the correct source-precedence rule, calculating/classifying fields exactly, and preserving an audit trail.

## Operating Boundary

- Use only the environment endpoints and credentials supplied by the task prompt or payload. Do not inspect task-environment source files, database files, generated data files, manifests, or setup scripts.
- Treat `input/payloads/answer_template.json` as the output contract. Read it before calculating final fields.
- Treat `input/payloads/task_context.json` as the scoped work order. Use target IDs, reporting dates/periods, queue row IDs, requester role, and any local finance or routing definitions from it.
- Return JSON only. Do not include Markdown fences, comments, or explanatory text outside the object.
- Do not copy fields from a local memo when environment records disagree. The memo scopes the task; current operational records supply the facts.

## One-Pass Workflow

1. Read the prompt, answer template, and task context. Extract the target business ID, reporting date or period, required top-level keys, enums, ordering rules, numeric precision, and whether additional fields are allowed.
2. Connect to the approved environment. Prefer business endpoints for obvious objects; use the SQL endpoint for joins, filtering, and table discovery when needed.
3. Retrieve the target record and all directly related records: member/plan, authorization or appeal status, request lines, claim lines, policies/criteria, clinical documents, rate schedules, drug trials, assistance intake, P2P events, or finance rows according to the task type.
4. Separate current controlling records from stale exports, distractor schedules, incomplete evidence, unsupported criteria, and missing packet fields.
5. Apply the domain-specific precedence pattern below. Let precedence choose the result when sources conflict.
6. Fill every required template field, preserving template ordering rules. Use only allowed enum values.
7. Build `basis_audit` last from the records that actually controlled the result and the exception/gap records that explain exclusions, missing information, denials, or routing priority.
8. Validate the final object against the template: exact required keys, enum spelling, list ordering, null handling, date format, rounding, and no extra fields when disallowed.

## Environment Querying

- Start with target-specific endpoints when available, such as cases, appeals, policies, documents, rate schedules, and SQL query.
- If table names or relationships are unclear, call the environment's table-list endpoint if the prompt allows it, then query only records needed for the target ID or scoped row IDs.
- Use parameter-like discipline even if writing raw SQL: filter by the target ID, appeal ID, claim ID, document ID, policy ID, service date, plan, modifier, CPT/HCPCS, period, or queue row IDs from the prompt/context.
- Pull enough fields to prove the answer. For example, do not price a claim from summary totals alone; retrieve line-level paid amounts, units, modifiers, service dates, and effective benchmark rates.
- Keep a scratch list of record IDs by role: controlling facts, stale/rejected sources, missing evidence, unresolved criteria, and calculated rows.

## Source Precedence Patterns

Choose the `basis_audit.source_precedence` value that matches the business conflict the task asks you to resolve:

- `current_clinical_records_over_stale_export`: use for UM clinical authorization reviews where current evaluations, plans of care, and active policy/member records outweigh stale exports or outdated documents.
- `payer_appeal_before_manufacturer_assistance`: use for pharmacy appeal plus assistance intake. Resolve coverage appeal eligibility, criteria, packet gaps, and filing readiness before manufacturer assistance status.
- `effective_benchmark_by_plan_modifier_and_date`: use for payment-integrity repricing. The controlling benchmark is the effective schedule matching service date, plan/network context, CPT/HCPCS, modifier, and units; stale or nonmatching schedules are exceptions.
- `new_patient_specific_p2p_information`: use for peer-to-peer closure. New patient-specific P2P evidence can change review; generic discussion or no new support leaves unresolved criteria in place.
- `margin_threshold_then_charge_sensitivity`: use for finance margin queues. Below-threshold revenue-to-cost issues drive payer contract action before charge-sensitive monitoring.
- `appeal_deadline_then_clinical_then_payment_integrity`: use only when the task and records require prioritizing appeal deadline/routing before clinical or payment-integrity factors.

## Domain Playbooks

### UM Authorization Determination

- Verify active member/plan coverage, requested therapy lines, applicable policy criteria, current clinical documents, plan of care, authorization record, and any stale/distractor documents.
- Mark each required criterion independently. Use `met` only when the current records support the criterion; use `not_met` or `unclear` for missing or conflicting support according to template choices.
- Approve through nurse review when all required nurse-approvable criteria are met and requested units/dates/CPT/modifier align with policy and authorization records.
- Pend when curable information is missing. Escalate to medical director or deny only when the records/policy require that route.
- Evidence document lists should include current documents relied on. Excluded document lists should include stale, superseded, or irrelevant documents, ordered as the template requires.

### Pharmacy Appeal and Assistance Intake

- Retrieve the appeal, denial/authorization history, drug policy, prescriber rationale, medication trial/failure evidence, packet documents, and assistance screening facts.
- Classify medication failures by evidence quality. A documented failure needs a sufficient record; missing fill history, unclear duration, or unsupported medication history belongs in the insufficient list.
- Determine appeal path, expedited flag, owner, and deadline from appeal status and plan rules. Do not infer expedited status from urgency language unless required clinical-risk evidence is present.
- Required packet items should cover payer appeal needs first, then assistance needs. Missing packet items should list appeal evidence gaps before assistance information gaps.
- Assistance status follows coverage appeal facts: identify the program, eligibility, and missing fields, but do not let assistance readiness override an incomplete payer appeal packet.
- Choose the next action from the highest-priority operational gap, usually requesting information before filing or submitting.

### Claim Repricing and Payment Integrity

- Retrieve the target claim, claim lines, associated case/auth/payment records, and all candidate rate schedules.
- Pick the current effective benchmark by service date, plan/network, CPT/HCPCS, modifier, and units. Reject stale or nonmatching schedules explicitly.
- For each line, compute `correct_allowed_amount = benchmark_rate * units` unless the environment specifies a different formula. Round currency to cents after applying units.
- Compute line recovery as the difference between correct allowed and paid according to the template's direction. Use a positive underpayment amount when corrected allowed is greater than paid; use the equivalent overpayment/correction amount when paid is greater if the task calls for recovery.
- Totals must equal the sum of line amounts after rounding. Preserve claim-line order and use `null`, not an empty string, for absent modifiers.
- Set dispositions from line differences: upward correction, downward correction, no change, or denial as allowed by the template.

### Peer-to-Peer Closure

- Retrieve the authorization case, request line, current imaging or therapy policy, clinical evidence, completed P2P event, authorization status, and final adverse/decision dates.
- Decide whether P2P supplied new patient-specific information. Only material new support should change the review.
- Keep unresolved criteria when the P2P did not resolve required factors. For PET MPI-like tasks, list unsupported PET-over-alternative factors in the template's specified order.
- If the final result is adverse, compute internal appeal deadline from the final adverse determination date and the plan's appeal window in the records. Use `null` only when no appeal deadline applies.
- Recommend an alternative modality only when policy/records support it and the template has an allowed value.

### Finance Margin Queue

- Use only queue rows scoped by the task context. Preserve the row order from the context.
- Calculate `total_cost` from the finance definition, commonly variable cost plus fixed allocated cost.
- Calculate `margin = revenue - total_cost` unless the environment gives a precomputed authoritative margin.
- Calculate `revenue_to_cost_ratio = revenue / total_cost` and round to the template precision.
- A row is below threshold when its ratio is less than the threshold. Charge sensitivity is a separate flag from the environment; do not treat it as the same as below-threshold.
- Recommended action precedence: below threshold -> payer contract review; else charge sensitive -> monitor charge sensitive; else monitor with no action.
- `gap_to_120pct` or similar threshold gap equals `(threshold * total_cost) - revenue` for the top below-threshold issue, rounded as requested. Use zero or the template's no-issue convention only when there is no below-threshold issue.

## Basis Audit Rules

- `controlling_record_ids`: include only records that directly determined the answer, such as current clinical documents, appeal records, sufficient trial records, claim lines plus selected benchmarks, P2P event/evidence records, or scoped finance rows.
- `exception_record_ids`: include stale sources, rejected benchmarks, unsupported criterion IDs, missing packet fields, insufficient evidence records, and unresolved factors that explain gaps or adverse routing. If no environment record ID exists for a missing item, use the template's field or criterion identifier.
- `precedence_record_order`: list records in business source-precedence order, highest priority first. This may differ from simple chronological order or from the full controlling-record list.
- Do not pad the audit with every related record. The audit should explain why the result is correct.

## Output Validation Checklist

- Top-level keys match the template. Omit additional fields when `additional_fields_allowed` or equivalent says false.
- Enum values exactly match allowed spelling and casing.
- Required criteria keys are all present, even when the result is `not_applicable`, `unclear`, or `not_met`.
- Lists follow template ordering: document IDs ascending, medications alphabetical, claim lines in claim-line order, queue rows in context order, PET factors in choice order, segment summaries alphabetical unless otherwise specified.
- Dates are ISO calendar dates. Use the task reporting date only as context; compute deadlines from plan rules and source dates.
- Currency values are JSON numbers rounded to cents. Ratios use the requested decimal precision.
- Use JSON `null` where the template says null is appropriate; do not substitute empty strings.
- Reconcile totals against line/row calculations before finalizing.
- Final response is exactly one JSON object and nothing else.
