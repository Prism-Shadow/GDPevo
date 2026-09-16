# Environment Interaction Guide

This skill assumes a payer operations environment is running at a base URL provided in the prompt (typically `<TASK_ENV_BASE_URL>`). Follow these interaction patterns.

## Endpoints

| Method | Path | Purpose |
|--------|------|---------|
| GET | `/` | Environment health check |
| GET | `/portal` | Portal overview |
| GET | `/api/tables` | List available tables |
| GET | `/api/cases` | List all cases |
| GET | `/api/cases/{case_id}` | Single case record |
| GET | `/api/policies` | List all policies |
| GET | `/api/policies/{policy_id}` | Single policy record |
| GET | `/api/documents/{document_id}` | Single clinical document |
| GET | `/api/rate-schedules` | List rate schedules |
| GET | `/api/appeals` | List all appeals |
| POST | `/sql/query` | Execute a SQL query |

## SQL access

Send a POST to `/sql/query` with the bearer token from the prompt. The request body is JSON:

```json
{"query": "SELECT ..."}
```

The response is a JSON array of row objects.

## Environment discovery sequence

When approaching a new task in an unfamiliar environment:

1. **List tables** via `POST /sql/query` with `SELECT name FROM sqlite_master WHERE type='table' ORDER BY name`
2. **Inspect schemas** for tables that match the task domain (case, claim, appeal, policy, document, etc.)
3. **Spot-check rows** with `SELECT * FROM <table> LIMIT 3`
4. **Pull by target ID** using both SQL queries and REST endpoints
5. **Cross-reference** records: a case may link to policies, documents, appeals, or authorizations through shared IDs or foreign keys

## REST versus SQL

REST endpoints return structured JSON for single records by ID. Use them for case, policy, and document lookups when you know the record ID.

SQL is better for:
- Listing all records of a type
- Filtering by foreign key or date
- Joining across tables
- Spot-checking schemas
- Verifying that no records were missed

Use both. REST gives you fast single-record access; SQL lets you be thorough.

## Authorization

Every SQL request must include the header:

```
Authorization: Bearer pa-review-token-014
```

The exact token value is in the prompt. Use it as given; do not guess or substitute.

## Response shapes

- SQL responses return `{"result": [...]}` with the result key holding an array of row objects
- REST responses return JSON objects with record-specific fields
- All dates are ISO 8601 (`YYYY-MM-DD`)
- All currency values are JSON numbers (not strings)

## Common pitfalls

- **Querying the wrong column name**: run `PRAGMA table_info(<table>)` if column names are unclear
- **Missing the stale record**: when rate schedules or documents have multiple versions, compare effective dates to decide which is current
- **Stopping too early**: always run a final SQL query grouping by the target business ID to confirm you have every linked record
- **Forgetting the bearer token**: SQL queries silently fail or return errors without it
