# API Usage

Load base URL and bearer token from `environment_access.md` at runtime. Do not hard-code them.

## Bootstrapping shell variables

```sh
# Parse environment_access.md for the base URL and token the env provides.
export GDPEVO_ENV_BASE_URL="http://task-env:9022/"   # value from environment_access.md
AUTH="Authorization: Bearer atlas-ops-token-022"     # token from environment_access.md
JSON_CT="Content-Type: application/json"
```

All `curl` calls use `-sS` and include the auth header. Read-only analysis uses only `GET` and `POST /api/sql`.

## 1. GET /api/schema  — table/column catalog

```sh
curl -sS "$GDPEVO_ENV_BASE_URL/api/schema" -H "$AUTH"
```

Returns table names, columns, types, primary/foreign keys. Use it to translate request nouns into concrete columns.

## 2. GET /api/data-dictionary  — semantic field meanings

```sh
curl -sS "$GDPEVO_ENV_BASE_URL/api/data-dictionary" -H "$AUTH"
```

The source of truth for canonical vs raw values, what "effective"/"settled"/"active"/"final" mean, identifier shapes, and reversal/reconciliation relationships. Always consult it before assuming a column's meaning.

## 3. GET /api/correction-audit  — existing audit rows (read-only context)

```sh
curl -sS "$GDPEVO_ENV_BASE_URL/api/correction-audit" -H "$AUTH"
```

Lists previously committed correction-audit records. Useful when verifying a correction's audit row landed, or confirming a target was not already corrected.

## 4. POST /api/sql  — single read-only query (analysis tasks)

Body shape:
```json
{"sql": "<SELECT or WITH query with ? placeholders>", "params": ["<string|number|boolean|null>"]}
```

```sh
curl -sS -X POST "$GDPEVO_ENV_BASE_URL/api/sql" -H "$AUTH" -H "$JSON_CT" \
  -d '{"sql":"SELECT ? AS one","params":[1]}'
```

Rules:
- One query per call. `SELECT`/`WITH` only (read-only).
- Use `?` placeholders for **every** literal value; supply them positionally in `params`. Never string-interpolate dates, ids, or thresholds.
- `params` may be omitted (defaults to `[]`) but prefer explicit arrays.
- Run as many separate calls as needed to discover, compute, and verify; this endpoint performs no writes.

## 5. POST /api/sql/transaction  — guarded correction (correction tasks only)

Body shape:
```json
{
  "statements": [
    {"sql": "<guarded UPDATE or correction_audit INSERT, or SELECT/WITH>", "params": [...]}
  ],
  "expected_total_changes": 0
}
```

```sh
curl -sS -X POST "$GDPEVO_ENV_BASE_URL/api/sql/transaction" -H "$AUTH" -H "$JSON_CT" \
  -d '{"statements":[{"sql":"SELECT ? AS one","params":[1]}],"expected_total_changes":0}'
```

Rules:
- 1–6 statements per transaction. SELECTs inside a transaction do not change rows.
- Allowed writes: guarded `UPDATE` of `carrier_scans` or `inventory_movements`; `INSERT INTO correction_audit` with **all** audit columns. Nothing else may mutate.
- `expected_total_changes` is an integer 0–12 and must equal the actual number of rows the writes change. Set it truthfully — the server uses it to validate.
- Never call this endpoint for purely analytical (scorecard/reconciliation/health) tasks. See `controlled_mutation.md` for the full protocol.

## Discovery order

schema → data-dictionary → (correction-audit, if correcting) → SQL queries. Never query blind.
