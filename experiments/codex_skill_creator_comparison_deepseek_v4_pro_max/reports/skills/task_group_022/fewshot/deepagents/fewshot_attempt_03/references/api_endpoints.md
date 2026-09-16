## Atlas Commerce Operations API

Base URL is provided by the task environment (typically `<TASK_ENV_BASE_URL>`).
Every endpoint below requires this header:

```
Authorization: Bearer atlas-ops-token-022
```

### GET /api/schema

Returns the full relational schema: table names, column names, data types,
nullable flags, and primary/foreign key relationships.

Always call this first when starting a new task. Use the output to identify
which tables and columns are relevant to the request.

### GET /api/data-dictionary

Returns human-readable descriptions for tables and columns, plus enum/value-set
documentation. Use this to understand column semantics (e.g. which status labels
mean "delivered", what account tiers exist, how priority levels map to real
workflows).

### POST /api/sql

Read-only SQL query endpoint. Submit a single `SELECT` statement. No writes,
transaction control, or multi-statement batches.

Request body:

```json
{"sql": "SELECT ..."}
```

Returns a JSON array of result rows. Use for all analytics, discovery, and
pre-correction lookups.

### POST /api/sql/transaction

Controlled write endpoint for data corrections. Accepts a transaction block
with one or more SQL statements. Every mutation must reference an approved
`reason_code` and `correction_key`. For the full protocol see
[transaction_protocol.md](transaction_protocol.md).

### GET /api/correction-audit

Returns audit records for past corrections. Use to verify that a transaction's
audit row was committed. Look up by `correction_key` or `audit_id`.
