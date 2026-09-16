# M&A Deal Workbench API Reference

Base URL: `<TASK_ENV_BASE_URL>`

## Deal Routes

| Method | Path | Description |
|--------|------|-------------|
| GET | `/workspace` | Workspace overview |
| GET | `/deals/<deal_id>` | Deal summary record |
| GET | `/api/deals` | List all deals |
| GET | `/api/deals/<deal_id>` | Full deal record (headline value, parties, dates, status) |
| GET | `/api/deals/<deal_id>/terms` | Current draft terms (percent values, months, clauses, amounts) |
| GET | `/api/deals/<deal_id>/documents` | Deal documents |
| GET | `/api/deals/<deal_id>/benchmarks` | Market benchmark data for comparable deals |
| GET | `/api/deals/<deal_id>/risk-estimates` | Risk estimate records with low/high exposure ranges |
| GET | `/api/deals/<deal_id>/cap-table` | Capitalization table (holders, security classes, share counts) |
| GET | `/api/deals/<deal_id>/consents` | Third-party consent records |
| GET | `/api/deals/<deal_id>/employees` | Employee records (counts, PTO liabilities, service credit) |
| GET | `/api/deals/<deal_id>/material-contracts` | Material contract records with annual revenue |
| GET | `/api/deals/<deal_id>/regulatory` | Regulatory records (HSR status, clearance requirements) |
| GET | `/api/deals/<deal_id>/diligence-findings` | Diligence findings (NWC issues, privacy, special indemnity) |
| GET | `/api/deals/<deal_id>/notes` | Deal negotiation notes |

## Playbook and Policy Routes

| Method | Path | Description |
|--------|------|-------------|
| GET | `/playbooks` | List available playbooks |
| GET | `/api/playbooks` | List available playbooks |
| GET | `/api/playbooks/<playbook_id>/rules` | Playbook rules (preferred and fallback positions per term) |
| GET | `/policies` | List available policies |
| GET | `/api/policies` | List available policies |
| GET | `/api/policies/<policy_id>/thresholds` | Policy thresholds for committee escalation |

## Search

| Method | Path | Description |
|--------|------|-------------|
| GET | `/api/search` | Search across workbench records |

## Read-Only SQL

| Method | Path | Description |
|--------|------|-------------|
| POST | `/api/query` | Submit a single SELECT or WITH SQL statement |

The SQL endpoint requires a JSON body:
```json
{"token": "deal-workbench-readonly", "sql": "SELECT ..."}
```

Use SQL for cross-table checks when relationships between records need verification (e.g., which consent IDs belong to which contracts, which employees belong to which group).

## ID Conventions

All record IDs follow stable patterns using the deal project ID:

- Terms: `TERM_<DEAL_ID>_<NN>`
- Consents: `CNS_<DEAL_ID>_<NN>`
- Material contracts: `MAT_<DEAL_ID>_<NN>`
- Employees: `EMP_<DEAL_ID>_<NN>`
- Risk estimates: `RSK_<DEAL_ID>_<NN>`
- Diligence findings: `FND_<DEAL_ID>_<NN>`
- Documents: `DOC_<DEAL_ID>_<NN>`
- Playbooks: `PB_SELLER_A`, `PB_SELLER_B`, `PB_BUYER_A`, etc.
- Policies: `POL_MA_<YEAR>_<VARIANT>`

Do not invent or truncate these IDs. Use exactly the values returned by the API.
