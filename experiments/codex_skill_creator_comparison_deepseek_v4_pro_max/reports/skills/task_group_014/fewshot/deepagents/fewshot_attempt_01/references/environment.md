# Northstar Payer Operations Environment

## Base URL

The task environment base URL is provided in your task context (typically
`<TASK_ENV_BASE_URL>` or a concrete URL like `http://task-env:9014/`).

## SQL Endpoint

```
POST /sql/query
Authorization: Bearer pa-review-token-014
Content-Type: application/json
```

Send SQL queries as JSON with a `query` field:

```json
{"query": "SELECT ... FROM ..."}
```

The bearer token is `pa-review-token-014`. Always include it.

Use SQL for direct table access when you need to pull records, claim lines, margin
rows, drug trials, rate benchmarks, appeal records, or other structured data not
available through REST endpoints.

## Business REST Endpoints

| Method | Path | Description |
|--------|------|-------------|
| GET | `/` | Environment root / health check |
| GET | `/portal` | Portal overview |
| GET | `/api/tables` | List available tables |
| GET | `/api/cases` | List all cases |
| GET | `/api/cases/{case_id}` | Get a specific case |
| GET | `/api/policies` | List all policies |
| GET | `/api/policies/{policy_id}` | Get a specific policy |
| GET | `/api/documents/{document_id}` | Get a specific document |
| GET | `/api/rate-schedules` | List all rate schedules |
| GET | `/api/appeals` | List all appeals |

Use REST endpoints for case facts, policy criteria, clinical documents, and appeal
records. Use SQL when you need cross-table queries, filtered subsets, or data not
exposed via REST.

## Query Strategy

1. Start with REST endpoints for case and policy context
2. Use SQL for claim lines, rate benchmarks, margin rows, drug trials, or any
   multi-table analysis
3. Always pull enough data to populate every required field in the answer template
4. Do not assume data exists -- verify each required piece with a query or endpoint call

## Authorization

All SQL requests require the header `Authorization: Bearer pa-review-token-014`.
REST endpoints may not require explicit auth, but include it on SQL calls without
exception.
