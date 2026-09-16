# Northstar Payer Environment

## Base URL

```
<TASK_ENV_BASE_URL>
```

Resolve `<TASK_ENV_BASE_URL>` from `environment_access.md` or the task context's `environment.base_url` field.

## SQL Endpoint

**Method:** POST
**Path:** `/sql/query`
**Authorization Header:** `Bearer pa-review-token-014`

Send a JSON body with a `query` key containing the SQL statement:

```json
{"query": "SELECT * FROM table_name WHERE condition"}
```

Valid database tables include: `cases`, `policies`, `documents`, `appeals`, `claims`, `claim_lines`, `rate_schedules`, `benchmarks`, `service_margin`, `drug_trials`, `authorizations`, `p2p_events`.

## REST Endpoints

All are GET requests. Append to the base URL. No additional auth beyond what the environment already handles.

| Endpoint | Description |
|---|---|
| `/` | Root health check |
| `/portal` | Payer portal summary |
| `/api/tables` | List available tables/records |
| `/api/cases` | All cases |
| `/api/cases/{case_id}` | Single case |
| `/api/policies` | All policies |
| `/api/policies/{policy_id}` | Single policy |
| `/api/documents/{document_id}` | Single document |
| `/api/rate-schedules` | All rate schedules |
| `/api/appeals` | All appeals |

## Credentials

Use the same bearer token for all SQL requests: `pa-review-token-014`.
