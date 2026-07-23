---
name: atlas-commerce-ops
description: Solve Atlas Commerce Operations workplace tasks that require authenticated schema/data-dictionary discovery, SQL analysis, strict JSON answers, and controlled canonical data corrections with audit records. Use when a prompt references an Atlas/GDPEVO workplace service, TASK_ENV_BASE_URL or GDPEVO_ENV_BASE_URL, /api/schema, /api/sql, /api/sql/transaction, answer_template.json, fulfillment, refunds, carrier quality, warehouse productivity, support health, or correction-audit workflows.
---

# Atlas Commerce Ops

## Core Workflow

1. Read the prompt, every request payload, and the answer template before querying data.
2. Read the provided environment access file or user-provided connection details. Do not infer credentials from placeholders.
3. Query `/api/schema` and `/api/data-dictionary` fresh for the current environment. Treat the live metadata as authoritative.
4. Translate the request into exact cohorts, cutoff logic, status rules, rounding rules, and output ordering before writing SQL.
5. Use `POST /api/sql` only for `SELECT` or `WITH` analysis queries. Use `POST /api/sql/transaction` only when the request explicitly asks for a controlled correction.
6. Build results from the live database every time. Do not reuse example counts, IDs, statuses, or answer values.
7. Validate the final JSON against the supplied answer template and write only the JSON object requested by the user.

## API Helpers

Use bundled scripts when they reduce copy/paste mistakes:

- `scripts/atlas_api.py`: call `schema`, `dictionary`, `audit`, `sql`, or `transaction`.
- `scripts/validate_answer.py`: check a produced answer JSON against the request's answer template.

Set `GDPEVO_ENV_BASE_URL` or `ATLAS_BASE_URL` to the service base URL, and set `ATLAS_AUTH_TOKEN` or `GDPEVO_AUTH_TOKEN` to the bearer token. Do not hardcode credentials in saved files.

Example read-only query:

```bash
python skill/scripts/atlas_api.py sql --sql "SELECT COUNT(*) AS n FROM orders"
```

Example validation:

```bash
python skill/scripts/validate_answer.py input/payloads/answer_template.json answer.json
```

## Query Discipline

- Keep SQL in CTEs so cohort membership, effective rows, rollups, and final formatting are inspectable.
- Confirm denominators separately from metric queries.
- Inspect distinct status, event type, priority, currency, and reason-code values before assuming enum contents.
- Use ISO-8601 UTC text comparisons directly only when both sides use the same stored UTC format.
- Apply inclusive and exclusive boundaries exactly as written. If the request says a date range is inclusive, include both endpoints.
- Round only final reported metrics unless the request says intermediate rounding is required.
- Order ranked output by unrounded metric values first, then apply the stated tie breakers.
- Return arrays in the stated order; use ascending identifier order when the template or request requires sorted IDs.

## Atlas Data Patterns

- Treat production account filters as excluding internal and test accounts when the request refers to production accounts or production customers.
- Prefer append-only event tables for time-at-cutoff questions when the request defines effective status from events. Use denormalized `current_status` fields only when the request allows snapshot status.
- For imported source rows that can recur on retries, deduplicate by the source identity described in the dictionary, usually `(source_system, external_event_id)`, keeping the latest `ingested_at` and a stable row-id tie breaker.
- For money, convert minor-unit fields to major currency units before FX conversion, join daily FX by row service date or requested valuation date, and round final displayed money to the requested decimals.
- For fulfillment, evaluate eligible orders against campaign/account/warehouse scope, then determine completion from physical shipments and effective carrier delivery state at the cutoff.
- For refunds, distinguish logical refund IDs from retry rows, subtract effective linked reversals, rank normalized reasons by effective net amount, and test leakage candidates at the order level.
- For warehouse productivity, scope eligible tasks by warehouse, production work class, and created window; derive completion, units, productive minutes, rework, delay, employee, and team metrics at the requested cutoff.
- For support health, scope eligible cases through accounts and opened-window criteria, reconstruct active state and response/resolution timing from case events, and use cutoff elapsed active time for unresolved obligations.

## Controlled Corrections

Use mutations only when the request explicitly asks for a correction.

1. Identify the single approved target row and canonical field with read-only SQL.
2. Preserve raw source fields, source identity fields, and unrelated rows.
3. Check existing audit rows for the target correction key and source row before mutating.
4. Submit one transaction containing a guarded `UPDATE` and one `correction_audit` `INSERT`.
5. Set `expected_total_changes` to the exact number of intended changed rows.
6. Guard the update by row id, old value, and relevant scope fields so repeated or wrong-scope runs do not modify extra rows.
7. Verify affected business rows, inserted audit rows, post-change canonical value, and any requested pre/post metric delta.
8. Report the template's success status only if the request's success rule is satisfied; otherwise report the template's failure status with the actual observed result.

## Output Rules

- Match the answer template exactly, including required fields, nested object shapes, enum values, arrays, and `additionalProperties` or `additional_properties` restrictions.
- Emit JSON numbers for numeric metrics, not strings.
- Use `null` only if the template permits it.
- Do not include markdown, comments, SQL, explanation, or extra fields in the answer file.
