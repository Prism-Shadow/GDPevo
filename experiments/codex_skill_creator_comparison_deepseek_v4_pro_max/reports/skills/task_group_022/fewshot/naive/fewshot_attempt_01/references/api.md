# Atlas Commerce Operations API

Base URL supplied as `<TASK_ENV_BASE_URL>`. All endpoints require:

```
Authorization: Bearer atlas-ops-token-022
Content-Type: application/json
```

## GET /health

Returns `{"status":"ok","schema_version":"atlas-commerce-1.0"}`. Use to confirm
the service is reachable.

## GET /api/schema

Returns full DDL for every table.

Response shape:

```json
{
  "schema_version": "atlas-commerce-1.0",
  "tables": [
    {
      "name": "accounts",
      "ddl": "CREATE TABLE accounts (\n    account_id TEXT PRIMARY KEY,\n    ...\n)"
    }
  ]
}
```

Always call this at the start of a task. It is the only source of truth for
column names, PRIMARY/UNIQUE keys, foreign-key relationships, CHECK
constraints, and NOT NULL annotations.

## GET /api/data-dictionary

Returns human-readable descriptions for every table and column, plus global
conventions for timestamps, dates, and money.

Response shape:

```json
{
  "schema_version": "atlas-commerce-1.0",
  "conventions": {
    "timestamps": "All stored timestamps use ISO-8601 UTC text ending in Z.",
    "dates": "Calendar dates use YYYY-MM-DD text.",
    "money": "Monetary minor fields use the smallest unit of the row currency; FX is USD per currency unit.",
    "source_rows": "Raw fields preserve source values; canonical fields hold normalized operational values."
  },
  "tables": [
    {
      "name": "accounts",
      "description": "Customer and company account master data...",
      "columns": [
        {"name": "account_id", "type": "TEXT", "nullable": false, "description": "Stable textual business or row identifier..."}
      ]
    }
  ]
}
```

## POST /api/sql

Execute a read-only `SELECT` query. Use for all analysis and fact-gathering.

Request body:

```json
{
  "sql": "SELECT ... FROM orders JOIN accounts ON ... WHERE ... ORDER BY ..."
}
```

- Only `SELECT` statements are permitted.
- All standard SQLite-compatible SQL is accepted.
- NULL comparisons use `IS NULL` / `IS NOT NULL`.

Response shape (success):

```json
{
  "columns": ["order_id", "account_id", "..."],
  "rows": [
    ["ORD-XXXXXX", "ACC-XXXX", "..."],
    ["ORD-YYYYYY", "ACC-YYYY", "..."]
  ]
}
```

- `columns` lists the result column names in order.
- `rows` is an array of arrays, each inner array containing string/float values
  in column order.
- Numeric results are returned as JSON numbers, text results as JSON strings.

Response shape (error):

```json
{
  "error": "Error message text"
}
```

## POST /api/sql/transaction

Apply a controlled data correction. Use only when a task explicitly requests a
correction and provides the approved correction parameters.

Request body:

```json
{
  "transaction": [
    "UPDATE carrier_scans SET canonical_status = 'CANONICAL_STATUS_VALUE', corrected_at = 'YYYY-MM-DDTHH:MM:SSZ', correction_reason = 'SOURCE_RECONCILIATION' WHERE scan_row_id = 'SCN-YYYYYYY'",
    "INSERT INTO correction_audit (audit_id, correction_key, entity_type, entity_id, source_row_id, field_name, old_value, new_value, reason_code, corrected_at, actor) VALUES ('AUD-YYYYMMDD-XXX', 'CQR-YYYYMMDD-REGION-XXX', 'carrier_scan', 'SHP-YYYYYY', 'SCN-YYYYYYY', 'canonical_status', 'RAW_STATUS_VALUE', 'CANONICAL_STATUS_VALUE', 'SOURCE_RECONCILIATION', 'YYYY-MM-DDTHH:MM:SSZ', 'correction-actor')"
  ]
}
```

- `transaction` is an array of SQL statements executed atomically.
- Statements accepted: `UPDATE`, `INSERT`. No `DELETE`, no `DROP`.
- Every `UPDATE` **must** set `corrected_at` and `correction_reason` on the
  corrected row.
- Every `UPDATE` **must** be accompanied by a matching `INSERT` into
  `correction_audit` with all required non-null columns filled from the
  approved correction parameters.
- Raw source values (`raw_status`, `raw_event_at`), source identity fields
  (`source_system`, `external_event_id`), and unrelated business rows must not
  be changed.
- The request's `approved_correction` block provides: `reason_code`, `actor`,
  `audit_id`, `correction_key`, and `corrected_at`.

Response shape (success):

```json
{
  "affected_business_rows": 1,
  "audit_rows": 1
}
```

Response shape (error):

```json
{
  "error": "Error message text"
}
```

## GET /api/correction-audit

Read the correction audit log after a transaction. Use to verify that the audit
record matches the approved parameters exactly.

No request body. Response is an array of audit records:

```json
[
  {
    "audit_id": "AUD-YYYYMMDD-XXX",
    "correction_key": "CQR-YYYYMMDD-REGION-XXX",
    "entity_type": "carrier_scan",
    "entity_id": "SHP-YYYYYY",
    "source_row_id": "SCN-YYYYYYY",
    "field_name": "canonical_status",
    "old_value": "RAW_STATUS_VALUE",
    "new_value": "CANONICAL_STATUS_VALUE",
    "reason_code": "SOURCE_RECONCILIATION",
    "corrected_at": "YYYY-MM-DDTHH:MM:SSZ",
    "actor": "ops-data-quality"
  }
]
```
