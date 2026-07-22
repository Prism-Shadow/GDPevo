---
name: northstar-payer-ops
description: Assemble Northstar payer-operations JSON packets for prior authorization, appeal intake, peer-to-peer closure, claim repricing, and margin-queue analysis. Use when a task provides a Northstar task context and answer template and asks for a structured JSON-only disposition from case, claim, policy, document, rate, or finance records.
---

# Northstar Payer Ops

## Workflow

1. Read the task prompt, `task_context.json`, and `answer_template.json` first.
2. Identify the target object, reporting date or period, and the exact output schema.
3. Pull only the records needed for that target from the shared payer-operations environment.
4. Derive values from returned facts and tables, not from memory.
5. Build the output with the exact keys, enums, ordering, rounding, and null-handling the template requires.

## General Rules

- Return JSON only.
- Use exact field names from the template; do not add extras.
- Follow list ordering rules exactly.
- Use ISO dates and round monetary values to cents.
- Use `null` for absent modifiers or other nullable fields only when the schema allows it.
- Keep controlling records in `basis_audit.controlling_record_ids` and stale, excluded, or gap records in `basis_audit.exception_record_ids`.
- Order `basis_audit.precedence_record_order` from highest-priority controlling record to lower-priority exceptions.
- Use the schema's `source_precedence` rule to resolve conflicts between current, stale, and incomplete records.

## Packet Families

### Prior authorization / nurse review

- Review case, member, plan, request lines, clinical documents, policy criteria, and any authorization record.
- Map each required criterion to the schema's result enum.
- Include current evidence documents and excluded stale documents.
- Set recommendation, route, final status, letter type, next action, and authorization terms from the controlling records.

### Appeal / assistance intake

- Review the appeal packet, medication failure evidence, drug trials or fills, and any assistance screen facts.
- Separate documented failures from undocumented or insufficient ones.
- Reflect required packet items, missing packet items, assistance status, and missing assistance fields exactly.
- Route standard, expedited, or assistance-only gaps to the next operational action.

### Claim repricing / payment integrity

- Use the current benchmark schedule that matches payer, plan type, service domain, CPT, modifier, and effective date.
- Reject stale exports when a current schedule applies.
- For each line, compute correct allowed amount, line recovery amount, and total recovery in claim-line order.
- Use the current schedule source and version in the top-level packet.

### Peer-to-peer closure

- Use the completed P2P event plus current clinical evidence and policy criteria.
- Decide whether the P2P changed the review.
- If adverse, supply the appeal deadline from the task rule and list unsupported PET factors or unresolved criteria.
- Set the recommended alternative modality only when the packet asks for one and the policy supports it.

### Margin queue

- For each listed queue row, compute `total_cost = variable_cost + fixed_cost_allocated`.
- Compute `margin = revenue - total_cost`.
- Compute `revenue_to_cost_ratio = revenue / total_cost`.
- Mark rows below the threshold and rows flagged as charge sensitive separately.
- Identify the top below-threshold issue and the dollar gap to 120% of cost.

## Final Check

- Verify the JSON parses.
- Verify enums, booleans, list order, and numeric precision against the template.
- Return only the JSON object.
