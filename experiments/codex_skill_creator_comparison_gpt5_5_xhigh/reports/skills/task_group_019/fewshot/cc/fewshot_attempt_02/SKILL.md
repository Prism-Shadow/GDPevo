---
name: licensing-env-review
description: Solve structured licensing review tasks against a provided task environment. Use this skill when Codex is asked to return schema-constrained JSON for contractor application eligibility batches, restricted liquor-license staff packages, alcohol or liquor renewal manual-review queues, or similar licensing endpoint reviews involving /api/policies, contractor, liquor, alcohol, renewal, or optional SQL endpoints plus input/payloads/answer_template.json.
---

# Licensing Environment Review

Use this skill for endpoint-backed licensing tasks where the answer must be a single JSON object matching a staged template.

## Core Workflow

1. Read the prompt and `input/payloads/answer_template.json` before fetching data.
2. Extract the target IDs, location IDs, license numbers, review dates, release boundary, requested queue size, and all endpoint paths named in the prompt.
3. Read the task's environment access instructions only to obtain the base URL and allowed endpoints. Replace `<TASK_ENV_BASE_URL>` with that base URL.
4. Fetch only the endpoint families needed for the prompt. Prefer targeted GET filters when an endpoint supports them. If a filter returns an error or an endpoint is naturally global, fetch the endpoint and filter locally by target application ID, license number, prior license ID, location ID, or successor license.
5. Treat `POST /api/sql` as optional. Use it only when the environment credentials make it work; otherwise fall back to GET data.
6. Build a casebook keyed by the target identifiers. Parse any `details_json` or `controls_json` fields before applying business rules.
7. Apply the domain-specific rules in [references/decision-rules.md](references/decision-rules.md).
8. Emit only the JSON object requested by the template. Do not include prose, citations, markdown fences, comments, or keys absent from the template.
9. Validate the draft with `scripts/validate_answer_template.py` when local files are available.

## Helper Scripts

Use `scripts/fetch_casebook.py` to gather a compact casebook from the allowed API endpoints:

```bash
python skill/scripts/fetch_casebook.py \
  --base-url "$TASK_ENV_BASE_URL" \
  --family contractor \
  --ids C-EXAMPLE-001 C-EXAMPLE-002
```

Supported families are `contractor`, `liquor`, and `renewal`. For liquor tasks, pass `--locations` when the prompt gives location IDs. For renewal queues, pass license numbers with `--ids`; the script also keeps successor records when present.

Use `scripts/validate_answer_template.py` after drafting `answer.json`:

```bash
python skill/scripts/validate_answer_template.py input/payloads/answer_template.json answer.json
```

The validator checks top-level keys, common list lengths, queue ranks, and summary consistency. Passing validation does not prove the business decision is correct; it catches schema and arithmetic mistakes before final output.

## Output Discipline

- Use the template's exact key names, enum values, casing, and required list/object structure.
- Sort and deduplicate arrays when the template requests ordering. Use empty arrays for no applicable codes.
- Recompute summary counts from the per-item decisions or queue you produced.
- When a template uses different code names for the same idea, map the business finding into the enum names present in that template.
- Prefer evidence from current, target-linked records. Ignore distractors, post-boundary records, dismissed or resolved enforcement records unless the template asks for exclusions or history.
