---
name: atlas-commerce-ops-solver
description: Solve Atlas Commerce Operations workplace tasks that require authenticated schema discovery, read-only SQL analysis, strict answer_template.json output, and occasionally an explicitly approved canonical correction through /api/sql/transaction and correction audit verification. Use when a prompt mentions TASK_ENV_BASE_URL, Atlas Commerce Operations, /api/schema, /api/data-dictionary, /api/sql, /api/sql/transaction, correction-audit, fulfillment scorecards, refund reconciliation, carrier scan quality, warehouse productivity, or support health analytics.
---

# Atlas Commerce Operations Solver

## Workflow

1. Read the user prompt, every request payload, and the answer template before querying data.
2. Use the task's environment-access instructions only to obtain the base URL and API token. Never call `/api/judge`.
3. Fetch `/api/schema` and `/api/data-dictionary` for the live task; do not assume the schema is unchanged.
4. Load [references/query-patterns.md](references/query-patterns.md) before writing nontrivial SQL, money logic, active-time logic, or a correction transaction.
5. Build SQL as layered CTEs: cohort, effective source rows, per-entity rollups, final aggregations, ranked rows, and output checks.
6. Prefer several narrow verification queries over one opaque query. Reconcile cohort counts, denominator counts, status distributions, and top/bottom rankings before writing `answer.json`.
7. Write exactly one JSON object matching the template. Include no commentary, no extra fields, and no trailing narrative.

Use [scripts/atlas_api.py](scripts/atlas_api.py) when it helps:

```bash
python skill/scripts/atlas_api.py --env-file environment_access.md get schema
python skill/scripts/atlas_api.py --env-file environment_access.md sql query.sql
python skill/scripts/atlas_api.py --env-file environment_access.md get audit
```

The script is optional; direct `curl` calls are fine when faster.

## Endpoint Rules

- `GET /health`, `/api/schema`, and `/api/data-dictionary` are discovery endpoints.
- `POST /api/sql` is read-only. Send JSON with a `sql` string and expect `columns`, `rows`, `row_count`, and `truncated`.
- `POST /api/sql/transaction` is only for prompts that explicitly authorize a controlled correction. Do not mutate data for analytical-only tasks.
- `GET /api/correction-audit` verifies audit records after a correction.

## Analysis Rules

- Treat request JSON definitions as authoritative when they conflict with column names or snapshot fields.
- Use UTC timestamp text boundaries exactly as requested. ISO-8601 `Z` strings compare lexicographically in SQLite, but use `datetime()` for interval math.
- Preserve denominator rules. Incomplete, unresolved, unreversed, or active-at-cutoff entities often remain in denominators.
- Rank by unrounded values and only round final reported numbers to the template precision.
- Apply tie-breaks exactly, usually ascending stable IDs or labels after the metric sort.
- Return ID arrays sorted exactly as requested, with unique values.
- Evaluate risk/status policies in listed priority order and respect strict wording such as "below" versus "at least".
- For imported event/source tables with `source_system`, `external_event_id`, and `ingested_at`, dedupe retries before lifecycle analysis unless the request explicitly wants raw rows.

## Corrections

Only perform a mutation when the prompt requests it and gives the approved scope. For a correction task:

1. Identify the single target row with read-only SQL, including the stable row ID, business entity ID, corrected field, old value, and new value.
2. Compute the pre-correction business metric from the same cohort definition that will be used after the correction.
3. Submit one transaction that updates only the approved canonical field and inserts the required audit row.
4. Verify exactly one business row and one audit row committed, then re-query the corrected field and the post-correction metric.
5. Report `NOT_APPLIED` if any success condition fails; otherwise report the applied result. Never alter raw source values, source identity fields, or unrelated rows.

## Output Checks

Before finalizing:

- Compare every required template key against `answer.json`.
- Check array length, uniqueness, sort order, enum values, and decimal precision.
- Run `python -m json.tool answer.json` to catch invalid JSON.
- If a mutable correction was applied, include the observed transaction and audit counts from the API response or verification queries, not assumed counts.
