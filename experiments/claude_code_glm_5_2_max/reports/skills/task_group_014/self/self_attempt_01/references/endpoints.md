# Environment Access Reference

## Base URL

The prompt and `task_context.json` carry the placeholder `<TASK_ENV_BASE_URL>`. Resolve it from `environment_access.md` in the work directory (e.g. `http://task-env:9014/`). All requests target that host. If `environment_access.md` is missing or the host is unreachable, stop and report — do not guess another host.

## SQL endpoint — `POST /sql/query`

| Part | Value |
|---|---|
| Method/path | `POST /sql/query` |
| Auth header | `Authorization: Bearer pa-review-token-014` (required) |
| Content-Type | `application/json` |
| Body | `{"sql": "<a single SELECT statement>"}` |

**The JSON key is `sql`.** Sending `{"query": ...}` returns `{"error":"invalid_sql","message":"sql must be a non-empty string"}`. Missing or wrong token → HTTP 401.

Response shape:
```json
{
  "columns": ["col_a", "col_b"],
  "rows": [{"col_a": ..., "col_b": ...}],
  "row_count": 12,
  "max_rows": 500,
  "limited": false
}
```
- Capped at 500 rows. If `"limited": true`, narrow the `WHERE` and re-query — you are seeing a truncated set.
- Read-only: only `SELECT` returns useful data. Quote string literals with single quotes inside the SQL (`WHERE case_id = 'CASE-XYZ-001'`); when embedding SQL inside a JSON string, escape double quotes or prefer single-quoted literals.

### SQL-only tables (no business endpoint)

These have **no** `GET /api/...` endpoint and must be queried via SQL:

| Table | Why you need it | Typical filter |
|---|---|---|
| `claims` | claim repricing header (`paid_total`, `billed_total`, `auth_number`, `claim_status`) | `WHERE claim_id = '...'` |
| `claim_lines` | per-line paid/billed/units/modifier/service_date | `WHERE claim_id = '...' ORDER BY line_number` |
| `service_margin` | margin queue rows | `WHERE month_id IN (...)` using `task_context` queue row IDs |
| `members`, `providers`, `plans`, `policies`, `policy_criteria`, `request_lines`, `document_facts`, `drug_trials`, `p2p_events`, `payment_benchmarks`, `case_criteria` | usually arrived pre-nested via `/api/cases/{id}` or `/api/policies/{id}`, but available directly via SQL for cross-case or filtered queries | as needed |

## Business endpoints (open, no auth)

| Method/path | Returns |
|---|---|
| `GET /portal` | HTML landing page (human-readable entry points) |
| `GET /api/tables` | full schema: every table + columns (name, type, primary_key, not_null) |
| `GET /api/cases` | list of cases (with member/provider/plan fields denormalized) |
| `GET /api/cases/{case_id}` | **the hub**: one case object with nested `authorizations`, `appeals`, `assistance_screen`, `claims`, `criteria`, `documents`, `document_facts`, `drug_trials`, `p2p_events`, `request_lines` |
| `GET /api/policies` | list of policies (`precedence`, `version`, effective dates) |
| `GET /api/policies/{policy_id}` | policy + nested criteria definitions (`criterion_id`, `criterion_key`, `criterion_text`, `approval_required`, `result_if_missing`) |
| `GET /api/documents/{document_id}` | single document + its facts |
| `GET /api/rate-schedules` | list of `payment_benchmarks` rows (`source_name`, `source_version`, effective dates, `allowed_amount`) |
| `GET /api/appeals` | list of appeals |

## Prohibited

- Do not open, `cat`, or read environment source files, SQLite database files, data manifests, or setup scripts. The HTTP API is the only allowed interface.
- Do not call any judge/evaluation endpoint — none is available, and none is needed to produce the answer.
