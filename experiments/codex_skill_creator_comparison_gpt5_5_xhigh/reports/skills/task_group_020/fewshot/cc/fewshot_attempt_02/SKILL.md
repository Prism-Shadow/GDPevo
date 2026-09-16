---
name: ma-workbench-json
description: Use this skill for M&A deal workbench tasks that require a strict JSON answer from a running TASK_ENV_BASE_URL, answer_template.json, deal IDs, draft terms, playbooks, policy thresholds, consents, employees, material contracts, benchmarks, risk estimates, diligence findings, documents, or notes. Use it for counsel-style issue registers, closing/economics packages, committee escalation packages, carveout transition reviews, and SPA deviation matrices, even when the user only says to review a project or produce a deal package.
---

# M&A Workbench JSON

Produce a schema-conforming JSON answer from the M&A workbench. The hard part is not prose drafting; it is collecting the right deal-scoped records, comparing draft terms to the applicable playbook or policy, doing the arithmetic consistently, and preserving the requested output shape.

## Required Workflow

1. Read the user prompt and every file under `input/payloads/`, especially `answer_template.json`.
2. Extract the exact deal ID, client side, required package type, output ordering rules, numeric precision rules, and any named playbook or policy.
3. Resolve `<TASK_ENV_BASE_URL>` from the prompt, `TASK_ENV_BASE_URL`, `WORKBENCH_BASE_URL`, or a local `environment_access.md`.
4. Fetch the workbench data for the exact deal ID. Do not use similarly named projects or records from other deals.
5. Read `references/analysis_patterns.md` before classifying issues or calculating totals.
6. Draft the answer directly against the template shape. Treat template metadata sections as instructions unless they are actual required answer fields.
7. Validate the JSON structure and arithmetic before final response. Return only valid JSON, with no explanatory prose.

## Fetching Data

Use direct API endpoints before SQL. The helper below fetches the standard deal-scoped records and the linked playbook or policy when available:

```bash
python skill/scripts/fetch_workbench.py --deal-id "$DEAL_ID" --out /tmp/workbench-"$DEAL_ID"
```

If your skill path is not `skill/`, adjust the script path. The output directory contains `deal.json`, each endpoint response, and a `manifest.json` showing successes and failures.

Fetch or verify these records when relevant to the template:

- `GET /api/deals/<deal_id>`
- `GET /api/deals/<deal_id>/terms`
- `GET /api/deals/<deal_id>/documents`
- `GET /api/deals/<deal_id>/benchmarks`
- `GET /api/deals/<deal_id>/risk-estimates`
- `GET /api/deals/<deal_id>/cap-table`
- `GET /api/deals/<deal_id>/consents`
- `GET /api/deals/<deal_id>/employees`
- `GET /api/deals/<deal_id>/material-contracts`
- `GET /api/deals/<deal_id>/regulatory`
- `GET /api/deals/<deal_id>/diligence-findings`
- `GET /api/deals/<deal_id>/notes`
- `GET /api/playbooks/<playbook_id>/rules`
- `GET /api/policies/<policy_id>/thresholds`

Use `POST /api/query` with the read-only token only as a cross-check or when direct endpoint joins are ambiguous. Every SQL query should filter by the exact deal ID.

## Output Shape

The template may be a direct skeleton or an instructional schema:

- If it contains actual top-level answer keys with placeholder values, fill those keys.
- If it contains `required_top_level_fields`, build an answer with those listed fields.
- If it contains `required_output_shape`, build an answer from that nested shape.
- Do not echo helper sections such as `allowed_enums`, `instructions`, `schema_name`, `schema_version`, or `required_output_shape` unless the template explicitly makes them answer fields.

Use stable IDs from source records and template enum lists. Use `null` for genuinely absent numeric/string values, not `0` or an empty string. Use empty arrays only when the schema calls for an array and the issue is a required-but-missing term.

Before finalizing, save the draft JSON to a temp file and run:

```bash
python skill/scripts/check_json_shape.py input/payloads/answer_template.json /tmp/answer.json
```

Fix any reported missing keys, wrong container types, or invalid JSON. The checker is intentionally structural; still verify legal classifications and arithmetic yourself.

## Precision Rules

Follow the prompt over defaults. In general:

- Currency values are integer USD.
- Percentages are percent points, not fractions.
- Month values are integers.
- Holder percentages use the precision requested by the prompt or template.
- Sort arrays exactly as requested. If no ordering is specified, use template issue order, stable ID order, or negotiation priority as the business task implies.

## Final Response

Return only the JSON object. Do not add markdown fences, citations, caveats, or narrative outside the JSON.
