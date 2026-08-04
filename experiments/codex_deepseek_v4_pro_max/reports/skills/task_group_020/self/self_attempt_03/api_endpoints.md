## M&A Deal Workbench — API Endpoints

All endpoints are relative to the environment base URL (provided at runtime as `<TASK_ENV_BASE_URL>`).
Every endpoint returns JSON. No authentication headers are required beyond the read-only SQL token.

### Discovery & Metadata

| Method | Path | Description |
|--------|------|-------------|
| GET | `/` | Root / health check |
| GET | `/workspace` | Workspace-wide metadata |
| GET | `/api/search` | Search across deals and records |

### Deal Records

| Method | Path | Description |
|--------|------|-------------|
| GET | `/deals/<deal_id>` | Deal summary (web UI route) |
| GET | `/api/deals` | List all deals |
| GET | `/api/deals/<deal_id>` | Full deal record |
| GET | `/api/deals/<deal_id>/terms` | Current draft terms |
| GET | `/api/deals/<deal_id>/documents` | Document index |
| GET | `/api/deals/<deal_id>/benchmarks` | Market benchmarks |
| GET | `/api/deals/<deal_id>/risk-estimates` | Risk estimates |
| GET | `/api/deals/<deal_id>/cap-table` | Capitalisation table |
| GET | `/api/deals/<deal_id>/consents` | Required third-party consents |
| GET | `/api/deals/<deal_id>/employees` | Employee roster and details |
| GET | `/api/deals/<deal_id>/material-contracts` | Material contracts |
| GET | `/api/deals/<deal_id>/regulatory` | Regulatory status (HSR, etc.) |
| GET | `/api/deals/<deal_id>/diligence-findings` | Due diligence findings |
| GET | `/api/deals/<deal_id>/notes` | Negotiation / counsel notes |

### Rules & Policies

| Method | Path | Description |
|--------|------|-------------|
| GET | `/playbooks` | List playbooks |
| GET | `/api/playbooks` | List playbooks |
| GET | `/api/playbooks/<playbook_id>/rules` | Rules for a specific playbook |
| GET | `/policies` | List policies |
| GET | `/api/policies` | List policies |
| GET | `/api/policies/<policy_id>/thresholds` | Thresholds for a specific policy |

### Read-Only SQL

| Method | Path | Description |
|--------|------|-------------|
| POST | `/api/query` | Execute a read-only SQL query |

**Request body:**
```json
{"token": "deal-workbench-readonly", "sql": "<SELECT or WITH statement>"}
```

**Example:**
```bash
curl -sS -X POST "<BASE>/api/query" \
  -H "Content-Type: application/json" \
  -d '{"token":"deal-workbench-readonly","sql":"SELECT deal_id, project_name FROM deals ORDER BY deal_id"}'
```

### Notes

- Only `SELECT` and `WITH` (CTE) statements are permitted.
- The token is always `deal-workbench-readonly`.
- Use SQL queries for cross-table checks that span multiple API resources.
- Prefer direct API GET calls over SQL when a dedicated endpoint exists — they are faster and return pre-joined structures.
