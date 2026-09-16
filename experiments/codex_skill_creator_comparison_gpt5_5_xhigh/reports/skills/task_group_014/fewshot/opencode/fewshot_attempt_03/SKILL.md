---
name: northstar-payer-ops-json
description: Solve Northstar Health Plan payer-operations tasks by using the shared task environment to produce exact JSON outputs for prior authorization determinations, pharmacy appeals, manufacturer assistance intake, payment-integrity claim repricing, peer-to-peer summaries, UM-finance margin queues, and related case/policy/document/rate-schedule workflows. Use when a prompt mentions Northstar, UM review, appeals, P2P, claim correction, rate schedules, margin queues, or an answer_template JSON contract.
---

# Northstar Payer Operations JSON

Use this skill to produce a single JSON answer from Northstar payer-operations records. The task-specific `answer_template.json` is the contract; environment records are the facts. Do not reuse values from examples or infer a result from similar-looking IDs.

## Operating Boundary

- Use only the task prompt, local payloads, and the network environment endpoints supplied by the task.
- Do not inspect task environment source files, generated data files, SQLite files, manifests, or setup scripts.
- Extract the base URL and bearer token from the task. Send SQL requests to `POST /sql/query` only when the task exposes it.
- Return JSON only when the prompt asks for JSON. Do not include markdown, comments, or explanation around the object.

## One-Pass Workflow

1. Read the prompt, `input/payloads/task_context.json`, and `input/payloads/answer_template.json`.
2. List the required output keys, enum choices, precision rules, null rules, and ordering rules before querying data.
3. Identify target business IDs, reporting dates, appeal IDs, claim IDs, queue row IDs, requested service/drug, and requester role from the prompt and task context.
4. Discover only the needed environment facts. Start with targeted business endpoints when available, and use SQL for joins or table-specific filtering.
5. Retrieve every record that can directly control the answer: case, member/plan, request lines, authorization, appeal, P2P event, policy criteria, documents, claim lines, rate schedules, queue rows, and assistance records as relevant.
6. Retrieve document bodies for every current or potentially excluded document ID referenced by the case.
7. Resolve conflicts with the source-precedence rule that fits the task.
8. Build the answer exactly to the template, then run the QA checklist.

Use targeted queries rather than broad dumps. A useful first SQL pass is to inspect table names or columns, then query by the target IDs from the task context.

## Evidence Rules

- Prefer current, patient-specific, effective records over stale exports or generic summaries.
- Treat explicit gap records, unsupported criteria, missing packet fields, stale documents, and rejected benchmark records as exceptions, not as controlling evidence.
- Include current evidence document IDs that the decision relied on. Put stale or non-controlling case documents in excluded document lists when the template asks for them.
- Do not mark a criterion `met` from narrative hints alone. Tie it to a document, claim/history record, policy criterion, appeal record, P2P event, or other environment record.
- When a record is missing or insufficient, represent the gap using the template's requested field IDs, criterion IDs, document IDs, or operational gap IDs.

## Source Precedence

Populate `basis_audit.source_precedence` with the rule that actually controlled the answer. Use the template's enum values when present.

- `current_clinical_records_over_stale_export`: Use current clinical documents, plans of care, evaluations, and active authorization records before stale summaries or exports.
- `payer_appeal_before_manufacturer_assistance`: Decide payer appeal path, deadline, criteria, and packet gaps before manufacturer assistance readiness. Assistance gaps can still drive the next action when the appeal packet is not ready.
- `effective_benchmark_by_plan_modifier_and_date`: Select the rate schedule effective for the claim date, plan/product, CPT/HCPCS, modifier, and service context. Reject stale or mismatched schedules.
- `new_patient_specific_p2p_information`: Let the completed P2P event and any new patient-specific information control the final authorization status over earlier intended decisions.
- `margin_threshold_then_charge_sensitivity`: Classify below-threshold margin rows first; only then separate rows that are charge sensitive but not below threshold.
- `appeal_deadline_then_clinical_then_payment_integrity`: When a task combines appeal operations, clinical merits, and payment integrity, route by deadline/appeal eligibility first, then clinical criteria, then payment correction details.

For `basis_audit`:

- `controlling_record_ids`: List the environment records that directly determine the result in operational evidence order.
- `exception_record_ids`: List gaps, unsupported criteria, stale records, rejected benchmarks, or missing field IDs in business gap order.
- `precedence_record_order`: List the highest-priority controlling and exception records in source-precedence order. Do not pad this list with every fetched record if only some records establish precedence.

## Domain Playbooks

### Authorization And Therapy Review

- Verify active member/plan context, covered diagnosis, requested CPT/HCPCS lines, modifier, start/end dates, requested units, and current authorization record.
- Evaluate policy criteria against current clinical documents. Common therapy concepts include active coverage, functional deficit, covered diagnosis, plan of care, and unit limits.
- Approve through nurse review only when all nurse-approvable criteria are met and requested units fit policy limits. Otherwise pend for information, route to medical director, deny, or partially approve according to the template's choices.
- Sort approved CPT codes as the template requires. Use current authorization values for authorization number, approved units, dates, modifier, and final route.

### Pharmacy Appeal And Assistance

- Use the appeal record for appeal ID, appeal path, expedited status, owner, deadline, denial context, and payer packet requirements.
- Classify medication failures as documented only when claim history, pharmacy records, or clinical documents substantiate them. Put absent, ambiguous, or insufficient trials in the undocumented/insufficient list.
- Build required packet items in payer-appeal order first, then assistance items. Missing packet items should list appeal evidence gaps before assistance information gaps.
- Determine manufacturer assistance readiness separately from payer appeal readiness. Assistance `missing_fields` should be sorted exactly as the template specifies.
- If required payer evidence is missing, the next action is normally to request more information rather than file a complete appeal.

### Payment-Integrity Claim Repricing

- Retrieve the claim header, associated case/auth, claim lines, paid amounts, units, CPT/HCPCS, modifiers, dates of service, plan/product, and applicable rate schedules.
- Select the benchmark schedule by effective date, plan/product, CPT/HCPCS, and modifier. Reject stale or mismatched schedules explicitly when the template asks.
- Preserve claim-line order. Use `null`, not an empty string, for absent modifiers.
- Compute `correct_allowed_amount = units * allowed_rate`, rounded to cents. Compute line and total correction amounts from the difference between correct allowed and paid amounts, rounded to cents. Use the line disposition to show direction (`correct_upward`, `correct_downward`, `no_change`, or denial).
- Totals must equal the rounded line values. Recalculate totals rather than copying a header summary unless the header is the controlling record.

### Peer-To-Peer Summary

- Retrieve the P2P event, final authorization status, requested line, policy criteria, current clinical evidence, and plan appeal window.
- Decide whether new patient-specific information changed the review. If it did not resolve a required factor, keep the factor in unresolved criteria and missing-factor fields.
- For adverse outcomes, set the letter type and calculate the internal appeal deadline from the final adverse determination date and the plan's appeal window. Use `null` only when no deadline applies.
- Include recommended alternatives only when supported by the policy or P2P outcome.

### UM-Finance Margin Queue

- Use only the queue row IDs in task context when a finance memo scopes the request.
- Compute `total_cost` from the definition in task context, commonly variable cost plus fixed cost allocation.
- Compute `margin = revenue - total_cost` and `revenue_to_cost_ratio = revenue / total_cost`. Follow the template precision, commonly cents for dollars and four decimals for ratios.
- Mark `below_threshold` when the ratio is below the stated threshold. Handle below-threshold rows before charge-sensitive rows.
- `gap_to_120pct` or similar gap fields should be the threshold revenue target minus actual revenue for the top below-threshold issue.
- Recommended actions usually follow this order: payer contract review for below-threshold rows, charge-sensitive monitoring for non-threshold charge-sensitive rows, then monitor/no action.

## Output Assembly

- Use every required top-level key from the template and no extra keys when the template disallows them.
- Match enum strings exactly, including case and underscores.
- Use JSON numbers for currency and ratios; do not quote numeric fields.
- Apply list ordering rules from the template: source claim-line order, task-context row order, ascending document/CPT/criterion order, enum choice order, or alphabetical order as specified.
- Use empty lists only when no applicable entries exist. Use `null` only when the template permits an absent value.
- Cross-check that evidence, exclusions, criteria results, next action, letter type, route, and basis audit tell the same story.

## Optional Template Check

After drafting `answer.json`, run the bundled structural validator from the workspace root or adapt the paths:

```bash
python skill/scripts/validate_answer.py input/payloads/answer_template.json answer.json
```

The validator catches missing required keys, disallowed top-level extras, obvious enum mismatches, missing nested required keys, and malformed JSON. It does not verify business correctness; still perform the evidence and calculation checks above.
