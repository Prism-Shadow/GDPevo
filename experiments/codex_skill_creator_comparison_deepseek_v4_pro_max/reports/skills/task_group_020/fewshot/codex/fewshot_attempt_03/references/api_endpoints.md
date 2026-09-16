# M&A Deal Workbench API Reference

Base URL: `<TASK_ENV_BASE_URL>` (provided in the task prompt).

## Read-Only SQL

`POST /api/query`
- JSON body: `{"token": "deal-workbench-readonly", "sql": "<single SELECT or WITH statement>"}`
- Use for cross-table verification when a single endpoint does not cover the needed join.
- Only SELECT and WITH (CTE) statements are allowed.

## Deal Endpoints

| Endpoint | Method | Description |
|---|---|---|
| `/api/deals/<deal_id>` | GET | Deal header: headline value, parties, structure, currency, signing date |
| `/api/deals/<deal_id>/terms` | GET | Current draft terms with term IDs, clause references, values (percents, months, dollars) |
| `/api/deals/<deal_id>/documents` | GET | Related documents (e.g., the draft APA/SPA) |
| `/api/deals/<deal_id>/notes` | GET | Negotiation notes and commentary |

## Playbooks and Policies

| Endpoint | Method | Description |
|---|---|---|
| `/api/playbooks` | GET | List available playbooks |
| `/api/playbooks/<playbook_id>/rules` | GET | Playbook rules: preferred, fallback, and required positions by issue category |
| `/api/policies` | GET | List available policies |
| `/api/policies/<policy_id>/thresholds` | GET | Policy thresholds: maximum/minimum values, required triggers, approved carveout groups |

## Consents and Contracts

| Endpoint | Method | Description |
|---|---|---|
| `/api/deals/<deal_id>/consents` | GET | Third-party consent records with consent IDs, contract names, counterparties, condition types, amounts at risk |
| `/api/deals/<deal_id>/material-contracts` | GET | Material contract records with contract IDs, names, annual revenue, condition types |
| `/api/deals/<deal_id>/cap-table` | GET | Capitalization table: holder groups, security classes, fully diluted percentages, as-converted share counts |

## Regulatory

| Endpoint | Method | Description |
|---|---|---|
| `/api/deals/<deal_id>/regulatory` | GET | HSR applicability, threshold basis, regulatory approval type, hell-or-high-water requirements |

## Risk and Benchmarks

| Endpoint | Method | Description |
|---|---|---|
| `/api/deals/<deal_id>/risk-estimates` | GET | Risk estimates with estimate IDs, types, low/high dollar exposure ranges |
| `/api/deals/<deal_id>/benchmarks` | GET | Market benchmarks: sample sizes, medians, upper quartiles for fee percents, survival months, etc. |

## Employees

| Endpoint | Method | Description |
|---|---|---|
| `/api/deals/<deal_id>/employees` | GET | Employee records: employee IDs, groups, PTO liability, service credit requirements, WARN risk indicators |

## Diligence

| Endpoint | Method | Description |
|---|---|---|
| `/api/deals/<deal_id>/diligence-findings` | GET | Diligence findings: finding IDs, descriptions, quantified impacts, categories |

## Workspace

| Endpoint | Method | Description |
|---|---|---|
| `/workspace` | GET | Workspace-level overview |
| `/api/search` | GET | General search across the workbench |
