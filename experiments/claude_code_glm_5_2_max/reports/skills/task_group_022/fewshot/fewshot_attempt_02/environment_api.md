# Atlas Commerce Operations — API Reference

This is a reusable reference for the workplace service endpoints. **Always read `environment_access.md` fresh** at the start of each run for the current base URL, token, and any per-run endpoint changes; the values below summarize the documented contract but must not be trusted over that file.

## Connection

- Base URL: given in `environment_access.md` (e.g. `GDPEVO_ENV_BASE_URL`).
- Auth header on **every** request: `Authorization: Bearer <token>` (token from `environment_access.md`).
- Content-Type for POSTs: `application/json`.
- The task prompt may refer to the base URL as `<TASK_ENV_BASE_URL>`; it is the same value.

Confirm reachability before real work with a trivial parameterized query, e.g.:
`POST /api/sql  {"sql":"SELECT ? AS one","params":[1]}`

## GET /api/schema
Returns table/view names with their columns. Use it to confirm which relations and columns exist before writing queries. No body.

## GET /api/data-dictionary
Returns the canonical meaning of each field: units, allowed enum/status values, raw-vs-canonical mappings, and effective-value rules. This is the authoritative translation layer from a business definition ("effective settled logical refund", "effectively DELIVERED", "active state", "reopened") to exact column predicates and enum values. No body.

## POST /api/sql — read-only analysis
Single statement, read-only.

Request body:
```json
{"sql": "<SELECT or WITH query string>", "params": ["<string|number|boolean|null>"]}
```
- `sql` (string, required): a single `SELECT` or `WITH` query.
- `params` (array, optional, default `[]`): bind values for `?` placeholders, in order. Use `?` parameters for **all** literals (ids, timestamps, amounts, enums). Do not interpolate values into the SQL string.

Response: the query result rows.

This endpoint is for analysis only. Never use it to change data.

## POST /api/sql/transaction — controlled multi-statement (correction tasks only)
Multi-statement, controlled. Use **only** when the task requests a correction.

Request body:
```json
{
  "statements": [
    {"sql": "<SELECT/WITH | guarded UPDATE | correction_audit INSERT>", "params": ["..."]}
  ],
  "expected_total_changes": <integer 0..12>
}
```
- `statements`: 1 to 6 statement objects (`sql` required, `params` optional).
- `expected_total_changes` (required): the exact number of changed rows the run should produce. The transaction commits **only** if the actual total matches.

Allowed SQL inside a transaction:
- `SELECT` / `WITH` queries (reads, including pre/post verification).
- Guarded `UPDATE` of **only** `carrier_scans` or `inventory_movements` — and only the single canonical field the request authorizes.
- `INSERT INTO correction_audit` — supplying **all** audit columns.

Disallowed: any other write, any unguarded update, any change to raw source values, source-identity fields, or unrelated business rows.

A typical correction transaction has two statements: one guarded `UPDATE` (one business row) + one audit `INSERT` (one audit row), with `expected_total_changes: 2`.

## GET /api/correction-audit
Audit view over committed corrections. Use it after a transaction to verify the audit row landed and the corrected canonical value is live. No body.

## Worked request forms (parameterized)

Read-only query:
```sh
curl -sS -X POST "$GDPEVO_ENV_BASE_URL/api/sql" \
  -H "Authorization: Bearer atlas-ops-token-022" \
  -H "Content-Type: application/json" \
  -d '{"sql":"SELECT region, COUNT(*) AS n FROM <t> WHERE created_at <= ? GROUP BY region","params":["2026-04-15T23:59:59Z"]}'
```
Correction transaction (shape only — fill the SQL from the request's authorized correction):
```sh
curl -sS -X POST "$GDPEVO_ENV_BASE_URL/api/sql/transaction" \
  -H "Authorization: Bearer atlas-ops-token-022" \
  -H "Content-Type: application/json" \
  -d '{"statements":[{"sql":"UPDATE carrier_scans SET canonical_status = ? WHERE scan_row_id = ?","params":["DELIVERED","SCN-..."]},{"sql":"INSERT INTO correction_audit (...) VALUES (?, ?, ...)","params":[...]}],"expected_total_changes":2}'
```

Always run these via the tool of your environment (e.g. `curl` over the network). If a request fails, re-read `environment_access.md` for the current token/base URL before retrying — do not invent alternatives.
