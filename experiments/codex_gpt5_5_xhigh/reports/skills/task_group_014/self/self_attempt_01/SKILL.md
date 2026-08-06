---
name: northstar-payer-ops
description: Structure Northstar payer-operations outputs for authorization, appeals, claim repricing, peer-to-peer, and finance queue tasks. Use when a prompt references the shared Northstar environment, a target case/claim/appeal/queue ID, a task_context payload, and a required JSON answer template.
---

# Northstar Payer Ops

## Workflow

1. Read `prompt.txt`, `payloads/task_context.json`, `payloads/answer_template.json`, and `environment_access.md` when provided.
2. Identify the target business IDs, reporting date or period, and the exact schema family.
3. Use the Northstar environment API with the provided bearer token, typically `POST /sql/query`, plus any listed business endpoints. Do not inspect local source or generated data files directly.
4. Pull current controlling records first. Prefer live case, claim, appeal, policy, document, authorization, rate schedule, or queue records over stale exports, distractor schedules, or incomplete references.
5. Build exactly one JSON object. Match the template shape exactly, use only declared values, preserve requested ordering, and keep numeric/date formats precise.
6. Fill any basis or audit trail with real record IDs only. Put controlling records first, then gap or exception records.
7. Return no markdown, prose, or code fences.

## Basis Precedence

Use the source-precedence label that matches the task:

- `current_clinical_records_over_stale_export`: current clinical packet beats stale exports.
- `payer_appeal_before_manufacturer_assistance`: appeal evidence controls before assistance screening.
- `effective_benchmark_by_plan_modifier_and_date`: current benchmark or rate schedule beats legacy or distractor schedules.
- `new_patient_specific_p2p_information`: peer-to-peer discussion can change the review.
- `margin_threshold_then_charge_sensitivity`: threshold status controls before charge sensitivity.
- `appeal_deadline_then_clinical_then_payment_integrity`: deadline controls route, then clinical evidence, then payment integrity.

## Output Rules

- Match required keys exactly.
- Omit unsupported keys unless the schema explicitly allows extras and the prompt requires them.
- Use the template's enum values verbatim.
- Use `null` only where the schema allows it.
- Round currency to cents, ratios to the requested precision, and dates to ISO format.
- Keep list ordering exactly as requested: source order, queue order, ascending IDs, or alphabetical order.

## Case Patterns

### UM and authorization summaries

- Determine recommendation, final status, route, letter type, and next action from current clinical evidence, policy criteria, and authorization records.
- Include current evidence documents relied on and exclude documents that were not used.
- Map criteria to `met`, `not_met`, `unclear`, or `not_applicable` exactly as the template allows.

### Pharmacy appeals

- Separate documented medication failures from failures that are undocumented or insufficient.
- Use the appeal deadline, packet completeness, and assistance screening status to choose the route and next action.
- Keep assistance missing fields and packet gaps in the order required by the template.

### Claim repricing

- Use the current benchmark schedule for the plan, modifier, and date.
- Reject stale or distractor schedules explicitly.
- Compute line amounts in claim-line order, use `null` for absent modifiers, and round monetary values to cents.

### Peer-to-peer reviews

- Use the completed P2P discussion to decide whether new patient-specific information materially changed the review.
- Populate unresolved criteria, missing PET factors, recommended alternative, and the internal appeal deadline when the result is adverse.

### Finance margin queues

- Keep rows in the exact `queue_row_ids` order from `task_context`.
- Split below-threshold segments from charge-sensitive segments.
- Compute the 120 percent gap from the top below-threshold issue.

