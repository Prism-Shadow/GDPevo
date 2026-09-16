# Atlas API Reference

All endpoints share the same base URL (`task_env_base_url`) and the same
authorization header. The base URL is always provided in the task prompt as
`<TASK_ENV_BASE_URL>`.

## Authorization

Every request must include this header:

    Authorization: Bearer atlas-ops-token-022

The token is fixed across all tasks in this environment.

## Endpoints

### GET /api/schema

Returns the full database schema: every table, every column name, and the SQL
type of each column. Call this first so you know what tables and columns exist.

Response is a JSON object keyed by table name. Each table lists its columns
with names and SQL types.

### GET /api/data-dictionary

Returns business-facing descriptions of each table and column, including enum
values, foreign-key relationships, and domain notes. Call this second to
understand what each column means.

Response is a JSON object keyed by table name, then column name, with
descriptions, enum values, and relationship annotations.

### POST /api/sql

Read-only query endpoint. Submit a JSON body with a `sql` string field:

    {"sql": "SELECT column FROM table WHERE condition"}

This endpoint is for analysis only. It does not modify data. Use it for all
cohort filtering, aggregation, ranking, and classification queries.

Response is a JSON object with a `rows` array of row objects and a
`row_count` integer.

### POST /api/sql/transaction

Controlled write endpoint. Use this **only** for data-correction tasks that
explicitly require a mutation. Submit a JSON body with a `sql` string field
containing an UPDATE statement.

The endpoint validates that exactly one business row is affected and records
an audit trail row. The response includes the number of affected business rows
and the number of audit rows committed.

    {"sql": "UPDATE table SET column = 'new_value' WHERE row_id = 'id'"}

Do not use this endpoint unless the task explicitly calls for a data
correction. All analytical work uses `POST /api/sql`.

### GET /api/correction-audit

Returns audit records for past corrections. Use this to verify that a
correction was recorded correctly after applying one via the transaction
endpoint.

Query parameters may include `audit_id`, `correction_key`, `entity_type`, or
`source_row_id`. Response is a JSON object with audit row details including
field_name, old_value, new_value, reason_code, corrected_at, and actor.
