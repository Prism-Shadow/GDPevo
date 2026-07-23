# Atlas API Quick Reference

All requests use the `base_url` and `Authorization` header from
`environment_access.md`.

## Read-only discovery

### GET /api/schema
Returns table names, column names, and data types.

```bash
curl -sS -H 'Authorization: Bearer <token>' '<base_url>/api/schema'
```

### GET /api/data-dictionary
Returns human-readable descriptions of tables and columns.

```bash
curl -sS -H 'Authorization: Bearer <token>' '<base_url>/api/data-dictionary'
```

## Read-only queries

### POST /api/sql
```bash
curl -sS -X POST '<base_url>/api/sql' \
  -H 'Authorization: Bearer <token>' \
  -H 'Content-Type: application/json' \
  -d '{"sql":"<SELECT or WITH>", "params":[]}'
```

- Only SELECT and WITH (CTE) statements are allowed.
- Use parameterized queries (`$1`, `$2`, …) with `params` when needed.
- Returns a JSON array of result rows.

## Controlled writes

### POST /api/sql/transaction
```bash
curl -sS -X POST '<base_url>/api/sql/transaction' \
  -H 'Authorization: Bearer <token>' \
  -H 'Content-Type: application/json' \
  -d '{"statements":[{"sql":"<UPDATE>","params":[]}],"expected_total_changes":<N>}'
```

- Each statement's `sql` must be exactly one UPDATE.
- `expected_total_changes` = business rows changed + audit rows inserted.
  The transaction is atomic — it rolls back if the actual count differs.
- Do not use for SELECT-only work.

## Audit verification

### GET /api/correction-audit
```bash
curl -sS -H 'Authorization: Bearer <token>' '<base_url>/api/correction-audit'
```

- Returns all correction audit records.
- Use after a transaction to verify the audit row was created with the
  expected `audit_id`, `correction_key`, `entity_id`, `field_name`,
  `old_value`, `new_value`, `reason_code`, and `actor`.
