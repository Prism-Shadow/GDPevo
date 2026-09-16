---
name: northstar-payer-ops
description: Produce strict JSON determinations, appeal dispositions, payment correction packets, peer-to-peer summaries, and UM-finance queue summaries from the Northstar payer-operations environment. Use when prompts reference Northstar Health Plan, prior authorization or UM nurse review, pharmacy appeals, manufacturer assistance, payment integrity claim repricing, peer-to-peer closure, or service margin queue analysis with provided answer templates and task_context payloads.
---

# Northstar Payer Ops

Use this skill to turn Northstar payer-operations records into the exact JSON object requested by a task's `answer_template.json`.

## Required Workflow

1. Read the user prompt, `input/payloads/task_context.json`, and `input/payloads/answer_template.json` before querying the environment.
2. Extract the target business IDs, reporting date or period, bearer token, base URL, required output keys, enum choices, precision rules, and ordering rules.
3. Query only records needed for the target IDs. Prefer `GET /api/cases/{case_id}` for case-centered tasks, then use narrow SQL for cross-table records such as service-margin rows or benchmark matches.
4. Keep a source ledger while working: record ID, table or endpoint, role in the decision, whether it is current or stale, and whether it is controlling evidence or an exception/gap.
5. Read [references/workflows.md](references/workflows.md) for domain decision rules, calculations, and `basis_audit` construction.
6. Emit one JSON object only. Match the template keys, enum spellings, date formats, numeric precision, list ordering, and null handling exactly. Do not add narrative text.

## Environment Access

Use the endpoints named in the prompt or task context. Do not inspect environment source files, database files, generated data, manifests, or setup scripts.

The optional helper [scripts/northstar_env.py](scripts/northstar_env.py) uses only Python standard-library modules:

```bash
python skill/scripts/northstar_env.py --base-url "$TASK_ENV_BASE_URL" --token "$TOKEN" case "$CASE_ID"
python skill/scripts/northstar_env.py --base-url "$TASK_ENV_BASE_URL" --token "$TOKEN" sql "select * from service_margin where month_id in (...)"
python skill/scripts/northstar_env.py --base-url "$TASK_ENV_BASE_URL" --token "$TOKEN" tables
```

The SQL endpoint expects JSON shaped as `{"sql": "select ..."}` and returns `columns` plus `rows`.

## Output Discipline

- Treat the answer template as authoritative over general habits.
- Preserve requested list ordering: source line order, task-context row order, alphabetic order, ascending code/ID order, or enum order as specified.
- For absent modifiers or optional dates, use JSON `null` when the template allows null; do not use an empty string.
- Round currency to two decimals and ratios to the precision in the template.
- Populate `basis_audit` from actual environment record IDs and gap identifiers. Do not invent IDs.
