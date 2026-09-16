# Atlas Task API

Use only the task environment endpoints documented in the task prompt or environment access file. Do not inspect server source or call undocumented endpoints.

## Environment

The usual runtime variables are:

- `TASK_ENV_BASE_URL`: base URL for the workplace API. If absent, try the base URL shown in the task prompt.
- `TASK_ENV_API_TOKEN`: bearer token for authenticated requests.

Every request uses:

```text
Authorization: Bearer $TASK_ENV_API_TOKEN
Content-Type: application/json
```

## Helper

From the task workspace, call the bundled helper by path:

```bash
python3 /path/to/skill/scripts/atlas_api.py schema
python3 /path/to/skill/scripts/atlas_api.py dictionary
python3 /path/to/skill/scripts/atlas_api.py sql --sql "select 1 as ok"
python3 /path/to/skill/scripts/atlas_api.py sql --dicts < query.sql
python3 /path/to/skill/scripts/atlas_api.py audit
python3 /path/to/skill/scripts/atlas_api.py transaction < transaction_body.json
```

Useful flags:

- `--base-url URL`: override `TASK_ENV_BASE_URL`.
- `--token-env NAME`: read the bearer token from a different env var.
- `--output FILE`: write the JSON response to a file.
- `--dicts`: for SQL responses, convert `columns` and row arrays into row dictionaries.

The read-only SQL endpoint accepts JSON shaped like:

```json
{"sql": "select 1 as ok"}
```

It returns:

```json
{"columns": ["ok"], "rows": [[1]], "row_count": 1, "truncated": false}
```

If `truncated` is true, do not use the response for final list output. Add aggregation, filtering, or pagination-style predicates.

## Corrections

Only use the transaction endpoint when the request explicitly approves a data correction. The expected operation is atomic:

1. Update exactly the approved canonical field on exactly the identified business row.
2. Insert exactly one row into `correction_audit` using the request's approved audit fields.
3. Verify the business row, the audit row, and any requested post-correction metric with read-only SQL or `GET /api/correction-audit`.

If the transaction endpoint rejects a body shape, adjust the JSON wrapper and retry only with the same minimal SQL statements. Do not split an approved correction into separate non-atomic calls.
