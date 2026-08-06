# Environment access & query mechanics

## Where the access details live

`environment_access.md` (in the task root) is the **only** source for network
access. Read it fresh every run — the base URL and token can change between
environments. It provides:

- `GDPEVO_ENV_BASE_URL` — the environment base URL.
- `X-Env-Token` — the token sent as the `X-Env-Token` header on every request.
- An allowed-endpoint list.

Do not hardcode the URL or token anywhere in answers or code. The prompt may
refer to it as `<TASK_ENV_BASE_URL>`; substitute the value from
`environment_access.md`.

## REST endpoints

All `GET` unless noted. Send `X-Env-Token: <token>` on every call.

| Method | Path                       | Returns (top-level key)                         |
|--------|----------------------------|--------------------------------------------------|
| GET    | `/api/work-items`          | `{"count", "work_items": [...]}`                |
| GET    | `/api/work-items/{id}`     | a single work item object                        |
| GET    | `/api/mix-targets`         | `{"mix_targets": [...]}`                         |
| GET    | `/api/sla-policy`          | `{"sla_policy": [...]}`                          |
| GET    | `/api/releases`            | `{"releases": [...]}`                            |
| GET    | `/api/releases/{id}`       | a single release object                           |
| GET    | `/api/milestones`          | `{"milestones": [...]}`                          |
| GET    | `/api/dependencies`        | `{"dependencies": [...]}`                        |
| GET    | `/api/blockers`            | `{"blockers": [...]}`                            |
| POST   | `/api/query`               | SQL result (see below)                            |

Whole-collection `GET`s are usually the simplest way to load a table. Filter and
aggregate in your own code so the logic is transparent and auditable.

## SQL query endpoint (`POST /api/query`)

For filtered / aggregated reads you can run SQL directly. Contract:

- **Body**: `{"sql": "<SELECT statement>"}` — the key is `sql` (a string).
  Any other key returns `{"error": "sql must be a string"}`.
- **Only `SELECT` is allowed.** `PRAGMA`, `INSERT`/`UPDATE`/`DELETE`, `CREATE`,
  etc. are rejected with `{"error": "only SELECT statements are allowed"}`. To
  inspect a table's columns, run `SELECT * FROM <table> LIMIT 1` and read the
  `columns` field — `PRAGMA table_info` will not work.
- **Response shape**:
  ```json
  {
    "columns": ["col1", "col2"],
    "row_count": 123,
    "rows": [["v1", "v2"], ...],
    "truncated": false
  }
  ```
  `rows` is an array of arrays, positionally aligned with `columns`. If
  `"truncated": true`, the result was capped — narrow the query (tighter
  `WHERE`, `LIMIT`, or `GROUP BY`) and re-run rather than assuming completeness.

## Tables available via SQL

`blockers`, `dependencies`, `milestones`, `mix_targets`, `releases`,
`sla_policy`, `work_items`. Column details are in `data_model.md`.

## Example calls

```bash
BASE="$(grep GDPEVO_ENV_BASE_URL environment_access.md | cut -d= -f2)"
TOKEN="$(grep X-Env-Token environment_access.md | sed 's/.*: //')"

# whole collection
curl -s -H "X-Env-Token: $TOKEN" "$BASE/api/sla-policy"

# SQL aggregate
curl -s -H "X-Env-Token: $TOKEN" -H "Content-Type: application/json" \
  -X POST "$BASE/api/query" \
  -d '{"sql":"SELECT status, COUNT(*) c FROM work_items GROUP BY status ORDER BY status"}'
```
