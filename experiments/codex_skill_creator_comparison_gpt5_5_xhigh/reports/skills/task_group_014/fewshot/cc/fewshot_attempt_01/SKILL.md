---
name: northstar-payer-ops-json
description: Use this skill for Northstar Health Plan payer-operations tasks that require a strict JSON answer from the shared task environment, including prior authorization determinations, pharmacy appeals, manufacturer assistance intake, peer-to-peer summaries, payment integrity claim repricing, and UM-finance margin queues. Use it whenever a task mentions Northstar, payer operations, authorization cases, appeals, claims, service margins, policies, criteria, or answer_template JSON.
---

# Northstar Payer Ops JSON

Use this skill to solve Northstar payer-operations tasks by querying the running environment, applying the applicable business precedence rule, and returning only the JSON object required by the provided answer template.

## Core workflow

1. Read the task prompt, `input/payloads/task_context.json`, and `input/payloads/answer_template.json` before querying data.
2. Resolve the task environment base URL from the prompt or the task's environment access file. Use only the listed HTTP endpoints and the SQL endpoint. Do not inspect environment source files, generated data files, database files, manifests, or setup scripts.
3. Use targeted SQL queries keyed by the target case, claim, appeal, queue, document, or row IDs from the prompt and task context. Avoid broad list endpoints unless you only need endpoint shape.
4. Treat the answer template as the output contract: required keys, enums, ordering, precision, null handling, and whether extra fields are allowed all come from the template.
5. Build a basis audit for every answer. The audit should explain the source-precedence rule, the records that directly control the result, and the records or gaps that explain exclusions, missing information, denial, route priority, or stale evidence.
6. Return valid JSON only. Do not include markdown fences, explanations, citations, or comments outside the JSON.

## Data access

For SQL calls, post JSON shaped as `{"sql": "SELECT ..."}` to `/sql/query` and include `Authorization: Bearer pa-review-token-014` unless the task supplies a different token.

You can use [scripts/northstar_sql.py](scripts/northstar_sql.py) to run a query. From the skill directory:

```bash
python scripts/northstar_sql.py --base-url "$TASK_ENV_BASE_URL" \
  --sql "SELECT * FROM cases WHERE case_id = 'TARGET_ID'"
```

Read [references/northstar-workflows.md](references/northstar-workflows.md) when deciding which records to retrieve and how to apply the business rules for each work type.

## Output discipline

- Populate every required key from the current task's template.
- Use the template's enum spellings exactly.
- Preserve required ordering: claim-line order, queue-row order, ascending document IDs, alphabetical medication names or segments, or the operational order specified by the template.
- Round currency to two decimal places and ratios to the requested precision. Keep JSON numbers as numbers, not strings.
- Use `null` where the template says null is required for an absent value.
- Use empty lists only when the template permits them and the environment evidence confirms no matching values.
- Before finalizing, parse the JSON mentally or with a local validator and compare every key against the answer template.

Do not reuse values from prior examples or from memory. Derive the answer from the current task's environment records and the current task's template.
