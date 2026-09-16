---
name: atlas-commerce-ops
description: Solve Atlas Commerce Operations analytical and controlled-correction tasks against authenticated workplace APIs. Use when prompts require strict answer.json outputs from the Atlas database, schema and data-dictionary discovery, read-only SQL analysis, fulfillment, refunds, warehouse, support, carrier, inventory, or approved minimal canonical corrections with correction_audit verification.
---

# Atlas Commerce Ops

## Operating Rules

- Read the user prompt, every file under `input/payloads/`, and especially `answer_template.json` before querying.
- Treat the payload request as the business contract. Use the schema and data dictionary only to map those definitions to tables and columns.
- Derive every answer value from the current task database. Do not reuse IDs, counts, rates, audit records, or final values from prior examples.
- Use read-only SQL for analytical tasks. Use the transaction endpoint only when the request explicitly approves a workplace correction.
- Preserve raw source fields, source identity fields, and unrelated rows. For correction tasks, update only the approved canonical field and append exactly the required audit row.
- Write only the final JSON object to `answer.json`; include no narrative in the file.

## API Setup

Fetch schema and dictionary at the start of each task, because the prompt can depend on exact field wording:

```bash
python scripts/atlas_api.py schema > /tmp/atlas_schema.json
python scripts/atlas_api.py dictionary > /tmp/atlas_dictionary.json
```

`scripts/atlas_api.py` reads:

- `TASK_ENV_BASE_URL`, defaulting to `http://task-env:9022`
- `TASK_ENV_API_TOKEN`, used as `Authorization: Bearer ...`

Run read-only SQL with:

```bash
python scripts/atlas_api.py sql --file /tmp/query.sql
```

The SQL endpoint returns `columns`, `rows`, `row_count`, and `truncated`. If `truncated` is true, narrow the query or aggregate in SQL before trusting list outputs.

## Workflow

1. Parse the answer template into an exact output checklist: required keys, nested keys, array lengths, ordering rules, precision, enum values, and `additionalProperties` constraints.
2. Parse the request payload into cohort filters, cutoff timestamps, inclusive or strict boundaries, ranking tie-breaks, status/risk rules, and rounding rules.
3. Fetch schema and dictionary. Identify all relevant header, event, dimension, FX, and audit tables.
4. Build CTE-based SQL that keeps cohort construction, event deduplication, cutoff state, metric aggregation, ranking, and exception lists separate.
5. Preserve unrounded values for ranking and status/risk classification. Round only final reported numeric fields unless the request says otherwise.
6. Cross-check metrics with independent denominator and sample queries before writing the answer.
7. For controlled corrections, run pre-correction analysis first, commit one minimal transaction only after the target is unique, then verify the business row, audit row, and post-correction metric.
8. Assemble `answer.json` in the template key order. Validate JSON syntax and manually check arrays are sorted and unique where required.

## SQL Patterns

Read [references/atlas_sql_patterns.md](references/atlas_sql_patterns.md) when deriving SQL for:

- effective source-event rows and cutoff state
- production account/order cohorts
- fulfillment and carrier delivery metrics
- refund settlement, reversals, FX, and leakage checks
- warehouse productivity and task state metrics
- support active-time SLA calculations
- controlled canonical corrections with audit verification

## Output Discipline

- Use UTC timestamp text comparisons only when all compared values are ISO-8601 UTC strings in the same format; otherwise convert with SQLite date functions.
- Use `julianday()` differences for elapsed hours or days.
- For rates, divide by the exact requested denominator and guard zero denominators deliberately.
- For medians, compute from the ordered numeric population after all cohort filters.
- For arrays of IDs, return stable business IDs, not row IDs, unless the template asks for row IDs.
- If a correction transaction is not applied exactly as requested, report the observed `NOT_APPLIED` result rather than pretending success.
