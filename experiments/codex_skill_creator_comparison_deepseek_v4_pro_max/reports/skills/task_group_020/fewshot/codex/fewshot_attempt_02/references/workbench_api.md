# Workbench API Reference

Base URL: `<TASK_ENV_BASE_URL>` (set by the task environment).

## Deal Records

| Method | Path | Description |
|--------|------|-------------|
| GET | `/workspace` | Workspace overview |
| GET | `/api/deals` | List all deals |
| GET | `/api/deals/{deal_id}` | Deal detail: headline value, parties, deal type, signing date |
| GET | `/api/deals/{deal_id}/terms` | Draft term records: term_id, category, draft values |
| GET | `/api/deals/{deal_id}/cap-table` | Cap table: holder groups, security classes, percentages, shares |
| GET | `/api/deals/{deal_id}/consents` | Consent records: consent_id, contract name, counterparty, condition type, amount at risk |
| GET | `/api/deals/{deal_id}/employees` | Employee records: employee_id, group, PTO liability, service credit, WARN risk |
| GET | `/api/deals/{deal_id}/material-contracts` | Material contracts: contract_id, name, annual revenue, condition type |
| GET | `/api/deals/{deal_id}/regulatory` | Regulatory facts: HSR required, hell-or-high-water, effort code |
| GET | `/api/deals/{deal_id}/benchmarks` | Market benchmarks: metric, sample_size, median, upper_quartile |
| GET | `/api/deals/{deal_id}/risk-estimates` | Risk estimates: estimate_id, type, low, high |
| GET | `/api/deals/{deal_id}/diligence-findings` | Diligence findings: finding_id, category, quantified amounts |
| GET | `/api/deals/{deal_id}/documents` | Document references: document_id, type |
| GET | `/api/deals/{deal_id}/notes` | Deal notes: note_id, text |

## Playbooks and Policies

| Method | Path | Description |
|--------|------|-------------|
| GET | `/playbooks` | List playbooks |
| GET | `/api/playbooks` | List playbooks |
| GET | `/api/playbooks/{playbook_id}/rules` | Playbook rules: category, preferred thresholds, fallback thresholds |
| GET | `/policies` | List policies |
| GET | `/api/policies` | List policies |
| GET | `/api/policies/{policy_id}/thresholds` | Policy thresholds: category, hard caps, required triggers |

## Search and SQL

| Method | Path | Description |
|--------|------|-------------|
| GET | `/api/search` | Search records by attribute; accepts query parameters |
| POST | `/api/query` | Read-only SQL. Body: `{"token": "deal-workbench-readonly", "sql": "<statement>"}`. Single SELECT or WITH statement only. |
