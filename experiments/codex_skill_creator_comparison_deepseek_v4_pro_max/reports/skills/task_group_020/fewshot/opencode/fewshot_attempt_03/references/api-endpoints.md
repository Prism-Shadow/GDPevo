# Workbench API Endpoints Catalog

Base URL: `<TASK_ENV_BASE_URL>` (provided in the prompt).

All endpoints use GET unless noted. The read-only SQL endpoint uses POST.

## Deal record

- `GET /api/deals/<deal_id>` — top-level deal record: deal name, parties, headline purchase price, signing date, closing date, status, side, transaction type (APA/SPA).

## Terms and playbooks

- `GET /api/deals/<deal_id>/terms` — current draft terms with term IDs, category, clause references, drafted values (percentages, months, dollar amounts, boolean flags).
- `GET /api/playbooks` — list of available playbooks.
- `GET /api/playbooks/<playbook_id>/rules` — playbook rules: each rule has a category, preferred position, fallback position, thresholds, and applicability conditions.

## Policies and thresholds

- `GET /api/policies` — list of available policy documents.
- `GET /api/policies/<policy_id>/thresholds` — committee policy thresholds: approval limits for reverse termination fees, fiduciary outs, rep-and-warranty survival, MAE carveouts, and similar governance terms. Each threshold has a numeric limit and unit.

## Supporting deal records

- `GET /api/deals/<deal_id>/risk-estimates` — risk estimates linked to findings, with dollar exposure ranges and risk ratings.
- `GET /api/deals/<deal_id>/benchmarks` — market benchmarks: sample size, median, upper quartile for indemnity caps, survival periods, escrow percentages, and other common terms.
- `GET /api/deals/<deal_id>/consents` — third-party consents: consent ID, contract name, counterparty, type (closing condition, notice only, post-closing covenant), risk rating, amount at risk.
- `GET /api/deals/<deal_id>/employees` — employee records: employee ID, name, group, jurisdiction, service credit requirements, PTO liability, WARN Act risk flags.
- `GET /api/deals/<deal_id>/regulatory` — regulatory record: HSR applicability, threshold basis, hell-or-high-water covenant status, effort standard.
- `GET /api/deals/<deal_id>/cap-table` — capitalization table: holder groups, security classes, fully diluted percentages, as-converted share counts.
- `GET /api/deals/<deal_id>/material-contracts` — material contracts: contract ID, name, counterparty, annual revenue, change-of-control consent requirement.
- `GET /api/deals/<deal_id>/diligence-findings` — diligence findings: finding ID, category, description, severity, linked term IDs, quantified impact where available.
- `GET /api/deals/<deal_id>/documents` — deal documents: document ID, type, date, associated terms.
- `GET /api/deals/<deal_id>/notes` — negotiation notes: timestamped notes with author, topic, and content.

## Web UI

- `GET /workspace` — workspace overview.
- `GET /deals/<deal_id>` — deal detail page.

## Search

- `GET /api/search` — search across deals, terms, and records.

## Read-only SQL

- `POST /api/query` — send `{"token": "deal-workbench-readonly", "sql": "<single SELECT or WITH statement>"}`. Returns JSON rows. Use for cross-table joins: verify term-to-finding mapping, validate counts across endpoints, check for missing linkages.
