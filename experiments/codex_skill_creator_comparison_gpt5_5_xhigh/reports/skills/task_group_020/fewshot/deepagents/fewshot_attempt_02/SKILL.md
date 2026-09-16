---
name: ma-workbench-json
description: Solve M&A deal workbench JSON tasks by collecting deal APIs, comparing draft terms to playbooks or policy thresholds, calculating dollar, percent, and month metrics, classifying issues, blockers, and priorities, and returning schema-conformant JSON. Use for buyer or seller APA/SPA transition reviews, closing packages, economics allocations, deviation matrices, committee escalations, and issue registers involving TASK_ENV_BASE_URL and answer_template.json.
license: MIT
compatibility: Codex
---

# M&A Workbench JSON Solver

## Core Rules

- Treat the prompt and `input/payloads/answer_template.json` as the output contract.
- Return only the requested JSON when the prompt requires JSON-only output.
- Use stable IDs from the workbench records and template enums exactly.
- Do not invent missing source facts. Use `null`, `[]`, or a template-approved status when a fact is not in the records.
- Do not copy examples from this skill into an answer. Derive every value from the current task environment.
- For detailed issue modeling and calculations, read [references/workbench-method.md](references/workbench-method.md).

## Workflow

1. Parse the prompt for the deal ID, client side, agreement type, requested work product, playbook or policy ID, precision rules, ordering rules, and required coverage areas.
2. Read the answer template completely. Decide whether the template itself is the output shape or whether it contains a `required_output_shape` or `required_top_level_fields` description.
3. Collect workbench records for the exact deal ID. At minimum fetch deal details, terms, playbook rules or policy thresholds, benchmarks, risk estimates, consents, employees, material contracts, regulatory records, diligence findings, documents, and notes when the prompt mentions them.
4. Build a source map keyed by stable record IDs: current draft terms, governing playbook or policy rules, quantified risk estimates, required consents, material contracts, employee liabilities, regulatory facts, benchmarks, and notes.
5. Determine the included issues from the prompt:
   - Include current draft terms that are out of policy or outside playbook limits.
   - Treat absent seller-protective or buyer-protective terms as `missing_required_term` when the prompt, playbook, policy, or surrounding deal facts require an affirmative term.
   - For committee escalations, include only current draft terms requiring committee approval and exclude stale, in-policy, or non-committee distractors.
6. Populate the JSON in template shape. Use exact enum strings, stable IDs, integer dollars, requested percent precision, integer months, and `YYYY-MM-DD` dates where required.
7. Compute summaries from the populated issue and blocker arrays. Avoid double-counting the same exposure source unless the prompt asks for separate categories.
8. Validate the final answer as JSON and check that required top-level fields are present.

## Helpful Scripts

Use the collector when API access is available and you want one local evidence bundle:

```bash
python skill/scripts/collect_workbench_records.py \
  --base-url "$TASK_ENV_BASE_URL" \
  --deal-id "$DEAL_ID" \
  --out workbench_records.json
```

Pass `--playbook-id` or `--policy-id` when the prompt names one and it is not obvious from the deal record.

Use the shape checker before final response:

```bash
python skill/scripts/check_json_shape.py input/payloads/answer_template.json candidate_answer.json
```

The checker is a guardrail, not a substitute for legal and business analysis. Always manually confirm nested fields, enum values, precision, ordering, and calculations against the template and prompt.
