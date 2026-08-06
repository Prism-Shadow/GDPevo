# Deal Workbench API Reference

All routes are relative to `<TASK_ENV_BASE_URL>` as configured in `environment_access.md`.

## Authentication

- Most GET endpoints are unauthenticated or use ambient session auth.
- `POST /api/query` requires a token: send `{"token": "deal-workbench-readonly", "query": "<sql>"}`.

## Discovery

| Method | Route | Description |
|---|---|---|
| GET | `/` | Root — workbench landing page |
| GET | `/workspace` | Workspace overview with deal list and status |

## Deal records

| Method | Route | Description |
|---|---|---|
| GET | `/api/deals` | List all deals |
| GET | `/api/deals/<deal_id>` | Deal record: parties, headline price, deal type, status, dates |
| GET | `/api/deals/<deal_id>/terms` | Current draft terms with stable term IDs, clause references, values |
| GET | `/api/deals/<deal_id>/documents` | Deal documents and exhibits |
| GET | `/api/deals/<deal_id>/notes` | Negotiation notes and counsel commentary |

## Risk and benchmarks

| Method | Route | Description |
|---|---|---|
| GET | `/api/deals/<deal_id>/benchmarks` | Market benchmarks: median, upper quartile, sample size per metric |
| GET | `/api/deals/<deal_id>/risk-estimates` | Quantified risk estimates with stable estimate IDs, low/high ranges, and categories |

## Consents and contracts

| Method | Route | Description |
|---|---|---|
| GET | `/api/deals/<deal_id>/consents` | Required third-party consents: counterparty, condition type, amount at risk |
| GET | `/api/deals/<deal_id>/material-contracts` | Material contracts: counterparty, annual revenue, consent requirements |

## People

| Method | Route | Description |
|---|---|---|
| GET | `/api/deals/<deal_id>/employees` | Employee roster: service credit eligibility, PTO liability, WARN risk |
| GET | `/api/deals/<deal_id>/cap-table` | Cap table: holders, security classes, fully-diluted percentages, as-converted shares |

## Regulatory and diligence

| Method | Route | Description |
|---|---|---|
| GET | `/api/deals/<deal_id>/regulatory` | HSR thresholds, filing requirements, industry approvals |
| GET | `/api/deals/<deal_id>/diligence-findings` | Due diligence findings: stable finding IDs, categories, quantified impact |

## Playbooks and policies

| Method | Route | Description |
|---|---|---|
| GET | `/api/playbooks` | List available playbooks |
| GET | `/api/playbooks/<playbook_id>/rules` | Playbook rules: term category, preferred position, fallback position, rationale |
| GET | `/api/policies` | List committee/board policies |
| GET | `/api/policies/<policy_id>/thresholds` | Policy thresholds: term category, threshold value, approval routing |

## SQL access

| Method | Route | Description |
|---|---|---|
| POST | `/api/query` | Read-only SQL. Body: `{"token": "deal-workbench-readonly", "query": "<sql>"}`. Use for cross-table joins, aggregates, or consistency checks not covered by the REST endpoints. |
