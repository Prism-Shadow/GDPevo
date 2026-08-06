# Deal Workbench API & Data Model

The workbench is a read-only M&A deal repository. Base URL and `/api/query` token come from `environment_access.md`. Every deal record exposes a `links` map to its sub-resources; the same data is available as SQL tables via `POST /api/query`.

## Auth & access

- All `GET /api/*` routes are open; no token needed.
- `POST /api/query` requires the token from `environment_access.md`, sent in the JSON body. Use it only for cross-table checks; prefer the path-scoped REST endpoints for single resources.
- Request shape: `{"token": "<token>", "sql": "SELECT ... FROM <table> WHERE deal_id = '<deal_id>'"}`. Response: `{"columns": [...], "row_count": N, "rows": [[...], ...]}`.

## Endpoint catalog

| Endpoint | Returns |
|---|---|
| `GET /` | HTML workbench UI (not for data) |
| `GET /api/deals` | `{count, deals:[...]}` — all deals (85+); use only to discover ids |
| `GET /api/deals/<deal_id>` | `{deal:{...}, links:{...}}` — the deal record + sub-resource links |
| `GET /api/deals/<deal_id>/terms` | `{draft_terms:[...]}` |
| `GET /api/deals/<deal_id>/consents` | `{consents:[...]}` |
| `GET /api/deals/<deal_id>/employees` | `{employees:[...]}` |
| `GET /api/deals/<deal_id>/regulatory` | `{regulatory:{...}}` |
| `GET /api/deals/<deal_id>/benchmarks` | `{benchmarks:[...]}` |
| `GET /api/deals/<deal_id>/risk-estimates` | `{risk_estimates:[...]}` |
| `GET /api/deals/<deal_id>/diligence-findings` | `{diligence_findings:[...]}` |
| `GET /api/deals/<deal_id>/notes` | `{deal_notes:[...]}` |
| `GET /api/deals/<deal_id>/material-contracts` | `{material_contracts:[...]}` |
| `GET /api/deals/<deal_id>/cap-table` | `{cap_table:[...]}` |
| `GET /api/deals/<deal_id>/documents` | `{documents:[...]}` |
| `GET /api/playbooks` | `{playbooks:[{playbook_id, rule_count}]}` |
| `GET /api/playbooks/<playbook_id>/rules` | `{playbook_id, rules:[...]}` — **scoped** to one playbook |
| `GET /api/policies` | `{policies:[{policy_id, threshold_count}]}` |
| `GET /api/policies/<policy_id>/thresholds` | `{policy_id, thresholds:[...]}` — **scoped** to one policy |
| `GET /api/search?q=<query>` | `{deals, documents, notes, terms, query}` — match by deal_id or text |

## The 14 SQL tables (names verified against `sqlite_master`)

`deals`, `draft_terms`, `playbook_rules`, `policy_thresholds`, `benchmarks`, `risk_estimates`, `cap_table`, `consents`, `employees`, `material_contracts`, `regulatory`, `diligence_findings`, `deal_notes`, `documents`.

## Key fields per resource

**deal** (`/api/deals/<id>` → `deal`)
`deal_id`, `client_name`, `client_side` (buyer/seller), `counterparty_name`, `target_name`, `project_name`, `transaction_type`, `currency`, `status`, `headline_value`, `upfront_cash`, `stock_value`, `milestone_value`, `signing_date`, `meeting_date`, `industry`, `playbook_id`, `policy_id`, `strategic_context`. → Use `headline_value`/`upfront_cash`/`stock_value`/`milestone_value` as the value base; `playbook_id`/`policy_id` as the governing standard; `client_side`/`transaction_type` to set posture. `strategic_context` sometimes flags stale/duplicate data — treat as a warning, then verify via `staleness_flag`.

**draft_terms** (`/terms`)
`term_id`, `deal_id`, `category`, `clause_ref`, `basis`, `unit` (percent_points / months / boolean / restricted_change / additional_carveouts), `numeric_value`, `draft_value` (prose), `source_document`, `last_updated`, `staleness_flag` (current/stale), `counterparty_rationale`. → **Filter `staleness_flag="current"`**. Match `category` to the playbook rule / policy threshold. `basis` selects the value base for quantification. `numeric_value` is the draft position; `unit` tells you how to read it.

**playbook_rules** (`/api/playbooks/<id>/rules`) — negotiation positions
`playbook_id`, `category`, `preferred_position` (prose + the target), `fallback_position` (prose + the walk-to), `limit_value`, `limit_unit`, `basis`, `required_action`, `risk_default`, `notes`. → `limit_value` is the fallback boundary. Preferred is the opening ask; fallback is the most the side will concede. Compare the draft `numeric_value` against preferred and fallback to set `issue_status`.

**policy_thresholds** (`/api/policies/<id>/thresholds`) — committee restrictions
`policy_id`, `category`, `policy_standard` (prose), `threshold_value`, `threshold_unit` (percent_points / months / carveouts / restricted_change / null), `restricted_flag` (yes/no), `approval_required` (M&A Committee / General Counsel / …), `basis`, `notes`. → Escalate only `restricted_flag="yes"` terms whose draft breaches `threshold_value`. `restricted_flag="no"` rows are not committee items (distractors for committee tasks).

**risk_estimates** (`/risk-estimates`)
`estimate_id`, `deal_id`, `category` (closing certainty / indemnity leakage / transition disruption / …), `exposure_low`, `exposure_high`, `confidence`, `method`, `notes`. → Sum the categories the task says to include for `total_quantified_exposure_low/high`; exclude the rest.

**benchmarks** (`/benchmarks`)
`benchmark_id`, `deal_id`, `category`, `metric`, `sample_size`, `mean_value`, `median_value`, `upper_quartile`, `notable_precedent`, `notes`. → Position the draft against `median_value` / `upper_quartile`.

**consents** (`/consents`)
`consent_id`, `deal_id`, `consent_type` (change of control / assignment / landlord consent / …), `contract_name`, `counterparty`, `required_for_closing` (yes/no), `amount_at_risk`, `risk_rating`, `notes`. → `required_for_closing="yes"` feeds required-closing-consent counts and amount-at-risk; `amount_at_risk` is a dollar base for exposure.

**material_contracts** (`/material-contracts`)
`contract_id`, `deal_id`, `contract_name`, `contract_type`, `annual_revenue`, `anti_assignment` (yes/no), `change_of_control` (yes/no), `consent_required` (yes / no / notice only), `notes`. → `consent_required="yes"` contracts are closing blockers; `annual_revenue` is the revenue at risk.

**employees** (`/employees`)
`employee_id`, `deal_id`, `employee_group`, `count`, `draft_treatment`, `playbook_requirement`, `service_credit_required` (yes/no), `pto_liability`, `warn_risk` (low/medium/high), `notes`. → Sum `count` for total employees; sum `pto_liability` for total PTO; flag groups where `service_credit_required="yes"` or `warn_risk` is elevated.

**regulatory** (`/regulatory`)
`deal_id`, `hsr_required` (yes/no), `hell_or_high_water_required` (yes/no/limited covenant), `regulatory_approval` (HSR only / HSR and industry review / none expected / other), `threshold_basis`, `notes`. → Feeds the regulatory/HSR closing-condition fields.

**diligence_findings** (`/diligence-findings`)
`finding_id`, `deal_id`, `topic`, `severity`, `amount`, `source`, `notes`. → `amount` is a dollar base for special indemnities / escrow-on-findings; `severity` and `topic` justify missing-term issues.

**deal_notes** (`/notes`)
`note_id`, `deal_id`, `author`, `note_date`, `source_document`, `topic`, `content`. → Negotiation posture and counterparty rationale; use to justify priority order and recommended actions, not as a numeric source.

**cap_table** (`/cap-table`) — SPA holder allocation
`holder`, `security_class`, `shares`, `as_converted_shares`, `fully_diluted_pct`, `role_notes`. → Allocate consideration pro-rata on `as_converted_shares` (or `fully_diluted_pct`). `fully_diluted_pct` is a fraction (e.g., 0.382 = 38.20%); emit at the precision the template requires.

**documents** (`/documents`)
`document_id`, `deal_id`, `document_type`, `title`, `version`, `effective_date`, `summary`. → Use `version`/`effective_date` to pick the latest source when terms conflict; `document_type` (draft agreement / negotiation notes / financial analysis) tells you whether a term is authoritative.
