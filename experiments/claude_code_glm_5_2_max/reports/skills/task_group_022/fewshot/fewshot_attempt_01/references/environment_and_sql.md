# Environment access and SQL mechanics

This file describes how to reach the running Atlas Commerce Operations service. The host, token, and exact endpoint rules live in `environment_access.md` at the workspace root — **read it fresh each task**; do not rely on the values below, which are examples only. Use this file for the immutable mechanics (curl shapes, response shapes, transaction constraints).

## Locating the base URL and token
- `environment_access.md` defines `GDPEVO_ENV_BASE_URL` and the required `Authorization: Bearer <token>`.
- If a prompt refers to `<TASK_ENV_BASE_URL>`, resolve it from that file. Do not hardcode a host anywhere.

## Endpoints

### GET /api/schema
Returns the DDL for every table. Use it to learn column names, types, CHECK constraints, and foreign keys.
```sh
curl -sS -m 30 "$GDPEVO_ENV_BASE_URL/api/schema" -H "Authorization: Bearer $TOKEN"
# {"schema_version":"...","tables":[{"name":..,"ddl":"CREATE TABLE ..."}]}
```

### GET /api/data-dictionary
Returns per-table descriptions plus storage **conventions** (timestamp/date format, money minors, FX basis, raw-vs-canonical fields). Read the conventions block once per task.
```sh
curl -sS -m 30 "$GDPEVO_ENV_BASE_URL/api/data-dictionary" -H "Authorization: Bearer $TOKEN"
```

### GET /api/correction-audit
Public audit rows for controlled canonical corrections. Read this **before** applying any write task, both to learn the `correction_audit` column shape and to confirm your intended audit row does not collide.
```sh
curl -sS -m 30 "$GDPEVO_ENV_BASE_URL/api/correction-audit" -H "Authorization: Bearer $TOKEN"
```

### POST /api/sql — read-only analysis
```sh
curl -sS -m 60 -X POST "$GDPEVO_ENV_BASE_URL/api/sql" \
  -H "Authorization: Bearer $TOKEN" -H "Content-Type: application/json" \
  -d '{"sql":"SELECT ? AS one","params":[1]}'
# {"columns":["one"],"rows":[[1]],"row_count":1,"truncated":false}
```
- Body: `{"sql": "<SELECT or WITH query>", "params": [...]}`. `params` is optional, defaults to `[]`.
- Always parameterize variable values with `?` and `params`. Never interpolate.
- `rows` is an array of arrays in `columns` order. Watch `truncated` — if true, your result was cut off; narrow the query or page it.
- Prefer CTEs (`WITH`) so you can carry both unrounded intermediates and final rounded values in one round trip.

### POST /api/sql/transaction — controlled write
```sh
curl -sS -m 60 -X POST "$GDPEVO_ENV_BASE_URL/api/sql/transaction" \
  -H "Authorization: Bearer $TOKEN" -H "Content-Type: application/json" \
  -d '{"statements":[{"sql":"SELECT 1","params":[]}],"expected_total_changes":0}'
```
- Body: `{"statements": [...], "expected_total_changes": <int 0..12>}`. `statements` has 1–6 objects; each has required `sql` and optional `params`.
- **Allowed SQL** (per `environment_access.md`, re-read for the authoritative list): SELECT/WITH; guarded `UPDATE` of `carrier_scans` or `inventory_movements`; `INSERT INTO correction_audit` with **all** audit columns. Anything else is rejected.
- `expected_total_changes` must equal the total rows the guarded UPDATE actually changes in this transaction; mismatches abort. Set it deliberately (for a single-row correction it is `1`).
- The transaction commits all-or-nothing. Structure write tasks as: (a) one guarded `UPDATE` for the single minimal canonical field, (b) one `INSERT INTO correction_audit` with the full audit row, with `expected_total_changes` set so only the business row counts toward it (audit INSERTs are not "changes").

## Common SQL tips for these scorecards
- Use `WITH` CTEs to materialize: the eligible cohort, per-entity facts, then aggregates, then final rounded selects — all in one `/api/sql` call where possible.
- Keep an unrounded rate column *and* a rounded rate column so tie-breaks can use the unrounded value while output uses the rounded one.
- SQLite-style `?` placeholders and `params` ordering must match.
- For ordered/limited lists, do the `ORDER BY ... LIMIT n` inside SQL so the server gives you the exact top-N with documented tie-breaks; assert `row_count` equals the expected size afterward.
- Money: store as minors in the row currency. Convert with `fx_rates.usd_per_unit` for the row's `service_date`/currency, summing minors before converting, then present to the template's precision.
