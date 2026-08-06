# Atlas Commerce Operations API

Base URL and bearer token are provided per task in `environment_access.md`. Read them at
runtime; never hardcode. All endpoints require `Authorization: Bearer <token>`; unauthenticated
calls return `{"error":"unauthorized"}`.

## Endpoints

| Method | Path                   | Purpose                                                        |
|--------|------------------------|---------------------------------------------------------------|
| GET    | `/api/schema`          | Table/column structure of the operations DB.                  |
| GET    | `/api/data-dictionary` | Business-term → column/code-value context. Read before querying. |
| GET    | `/api/correction-audit`| Existing correction audit rows.                               |
| POST   | `/api/sql`             | Read-only analytical queries.                                 |
| POST   | `/api/sql/transaction` | Controlled mutation + audit (correction tasks only).          |

Discovery first: always resolve business terms to concrete columns/values via `/api/schema` and
`/api/data-dictionary` before writing SQL. If a discovery endpoint is transiently unavailable,
retry; do not fall back to guessing table/column names.

## POST /api/sql

Request body:

```json
{"sql": "SELECT ..."}
```

Response body:

```json
{"columns": ["..."], "rows": [["..."]], "row_count": 0, "truncated": false}
```

- `columns` — output column labels (as written in the SELECT).
- `rows` — array of row arrays, aligned to `columns`.
- `row_count` — number of returned rows.
- `truncated` — `true` means the result set was capped; narrow the query or aggregate in SQL.

Observed policy:
- **Exactly one statement.** A trailing `;` is rejected (`{"error":"query rejected"}`).
- `WITH` (CTEs), `WHERE`, `UNION`, joins, and aggregate functions are accepted.
- Read-only: use for all analytical tasks. Do not attempt writes here.
- A rejected query returns `{"error":"query rejected"}`; a server-side issue returns
  `{"error":"service error"}`. Treat both as "fix or retry", not as data.

## POST /api/sql/transaction

For correction tasks only, when the prompt authorizes a minimal canonical correction. Use it to
apply the single field update and its audit row atomically, then verify with a follow-up
`/api/sql` read and `/api/correction-audit`. Success is defined by the request's
`correction_status_rule` (typically exactly one business row + one audit row committed, with the
post-change value confirmed). Never touch raw source values, source-identity fields, or unrelated
rows.

## scripts/atlas_query.sh

Convenience wrapper: reads the base URL and token from `environment_access.md`, JSON-escapes the
SQL argument, and POSTs to `/api/sql`.

```
scripts/atlas_query.sh "SELECT 1 AS x"
```
