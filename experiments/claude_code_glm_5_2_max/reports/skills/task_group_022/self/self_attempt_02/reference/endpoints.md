# Atlas Commerce Operations — Endpoint Reference

Source of truth: `environment_access.md` (use that file **only** for network access: base URL + bearer token). All endpoints require:

```
Authorization: Bearer <token>          # the token from environment_access.md
```

JSON bodies also require `Content-Type: application/json`.

## Base URL

The literal base URL is printed in `environment_access.md` (e.g. `http://task-env:9022/`). Prefer the `<TASK_ENV_BASE_URL>` / `GDPEVO_ENV_BASE_URL` env var when it is populated; if that env var is empty, fall back to the literal URL from the file.

## Read-only endpoints

### GET /api/schema
Returns `{ schema_version, tables: [ { name, ddl } ] }`. Use DDL for column names/types, `CHECK` constraints (enums), and foreign keys.

### GET /api/data-dictionary
Returns `{ schema_version, conventions: {...}, tables: [ { name, description, columns: [ { name, type, nullable, description } ] } ] }`. The `conventions` block is authoritative for cross-table rules (timestamps/dates/money/source-rows). See `schema_map.md`.

### GET /api/correction-audit
Returns the public audit view: `{ columns: [...], rows: [[...]], row_count, truncated }`. Starts empty. After a successful correction it must contain your newly inserted audit row.

### POST /api/sql  (read-only analysis)
Request:
```json
{ "sql": "<SELECT or WITH query string>", "params": ["<string|number|boolean|null>"] }
```
- `sql` (string) required; `params` (array) optional, defaults to `[]`.
- Only `SELECT` / `WITH` queries.
- Response: `{ columns, rows, row_count, truncated }`.
- Example: `curl -sS -X POST "$BASE/api/sql" -H "Authorization: Bearer <token>" -H "Content-Type: application/json" -d '{"sql":"SELECT ? AS one","params":[1]}'`

## Controlled write endpoint (correction variant only)

### POST /api/sql/transaction
Request:
```json
{
  "statements": [
    { "sql": "<SELECT/WITH | guarded UPDATE | correction_audit INSERT>", "params": [...] }
  ],
  "expected_total_changes": 0
}
```
- `statements`: 1 to 6 statement objects. Each has `sql` (required) and `params` (optional, defaults to `[]`).
- `expected_total_changes`: integer, 0 to 12.
- **Allowed SQL inside a transaction:**
  1. `SELECT` / `WITH` queries,
  2. guarded `UPDATE` on `carrier_scans` **or** `inventory_movements` (limit to the single target row, set canonical field + `corrected_at` + `correction_reason`),
  3. `INSERT INTO correction_audit` with **all** audit columns populated.
- Anything else is rejected.
- Use `expected_total_changes` to assert the exact number of business rows + audit rows changed (per the payload's `correction_status_rule`). A mismatch ⇒ treat as `NOT_APPLIED`.
- Example shell:
  ```bash
  curl -sS -X POST "$BASE/api/sql/transaction" \
    -H "Authorization: Bearer <token>" -H "Content-Type: application/json" \
    -d '{"statements":[{"sql":"SELECT ? AS one","params":[1]}],"expected_total_changes":0}'
  ```

## Operational notes

- Always pass `curl -sS` and pipe through `python3 -m json.tool` (or `jq`) to read responses reliably.
- `truncated: true` in any response means the full set was not returned — re-query with a tighter filter or `LIMIT/OFFSET` paging rather than assuming completeness.
- Do not invent endpoints. The four above plus the schema/data-dictionary/correction-audit GETs are the entire surface.
