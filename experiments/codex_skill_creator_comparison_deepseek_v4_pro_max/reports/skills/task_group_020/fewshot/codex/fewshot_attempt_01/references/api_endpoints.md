# M&A Deal Workbench API Endpoints

Base URL is provided via `TASK_ENV_BASE_URL` in the task prompt. All `GET` endpoints return JSON arrays or objects.

## Deal Records

| Method | Path | Description |
|--------|------|-------------|
| GET | `/api/deals` | List all deals. Returns array of deal objects with `deal_id`, `project_name`, `client_side`, `status`, `headline_value`, `deal_type`. |
| GET | `/api/deals/<deal_id>` | Single deal record. Returns the deal object with full metadata including `deal_id`, `project_name`, `client_name`, `counterparty_name`, `deal_type` (`asset_purchase` or `stock_purchase` or `merger`), `headline_value`, `currency`, `status`, `signing_date`, `target_name`. |
| GET | `/api/deals/<deal_id>/terms` | Current draft terms for the deal. Returns array of term objects with `term_id`, `clause_ref`, `category`, `draft_value` (may contain `percent`, `amount_dollars`, `months`, `boolean`, or structured sub-objects). |
| GET | `/api/deals/<deal_id>/benchmarks` | Market benchmarks for the deal type and size. Returns array of benchmark objects with `metric`, `sample_size`, `median`, `upper_quartile`, and optionally `lower_quartile`. |
| GET | `/api/deals/<deal_id>/risk-estimates` | Modeled risk estimates. Returns array of risk objects with `estimate_id`, `risk_category`, `exposure_low_dollars`, `exposure_high_dollars`, `description`. |
| GET | `/api/deals/<deal_id>/notes` | Negotiation or deal-team notes. Returns array of note objects with `note_id`, `author`, `date`, `content`, `category`. |
| GET | `/api/deals/<deal_id>/documents` | Ancillary or reference documents linked to the deal. Returns array of document objects with `doc_id`, `title`, `type`, `date`, and optionally `summary`. |

## Diligence Records

| Method | Path | Description |
|--------|------|-------------|
| GET | `/api/deals/<deal_id>/employees` | Employee data for the target. Returns array of employee objects with `employee_id`, `group`, `count`, `accrued_pto_liability_dollars`, `service_credit_years`, `warn_risk` (if applicable), `continuing` flag. |
| GET | `/api/deals/<deal_id>/consents` | Third-party consents required for the transaction. Returns array of consent objects with `consent_id`, `contract_name`, `counterparty`, `condition_type` (`closing_condition`, `notice_only`, `post_closing_covenant`), `amount_at_risk_dollars`, `risk_rating`. |
| GET | `/api/deals/<deal_id>/material-contracts` | Material contracts of the target. Returns array of contract objects with `contract_id`, `contract_name`, `counterparty`, `annual_revenue_dollars`, `consent_required`, `condition_type`. |
| GET | `/api/deals/<deal_id>/regulatory` | Regulatory review status. Returns object (sometimes array) with `hsr_required` (boolean), `threshold_basis`, `approval_type`, `hell_or_high_water_required` (boolean or string), `closing_condition_required` (boolean). |
| GET | `/api/deals/<deal_id>/diligence-findings` | Diligence findings or red flags. Returns array of finding objects with `finding_id`, `category`, `description`, `amount_at_risk_dollars`, `severity`. |
| GET | `/api/deals/<deal_id>/cap-table` | Capitalization table (for stock/equity deals). Returns array of holder objects with `holder_group`, `security_class`, `fully_diluted_pct`, `as_converted_shares`, and optionally `liquidation_preference`. |

## Playbooks and Policies

| Method | Path | Description |
|--------|------|-------------|
| GET | `/api/playbooks` | List available playbooks. Returns array with `playbook_id` and `description`. |
| GET | `/api/playbooks/<playbook_id>/rules` | Rules for a playbook. Returns array of rule objects with `rule_id`, `category`, `term_name`, `preferred_value` and `fallback_value` (each may contain `percent`, `amount_dollars`, `months`, `boolean`, or structured objects). |
| GET | `/api/policies` | List available policies. Returns array with `policy_id` and `description`. |
| GET | `/api/policies/<policy_id>/thresholds` | Thresholds for a policy. Returns array of threshold objects with `threshold_id`, `category`, `metric`, `max_allowed_value` or `allowed_values`, `committee_approval_required` flag. |

## Search and Workspace

| Method | Path | Description |
|--------|------|-------------|
| GET | `/api/search` | Search across deals, terms, and records. Query-string parameters vary. |
| GET | `/workspace` | Top-level workspace listing. Returns available deals, playbooks, and policies. |

## Read-Only SQL

| Method | Path | Description |
|--------|------|-------------|
| POST | `/api/query` | Execute a read-only SQL query. Body: `{"token": "deal-workbench-readonly", "sql": "<single SELECT or WITH>"}`. Returns JSON array of row objects. |

## Quick Reference by Task Type

### Issue Register (seller APA)
Pull: `/api/deals/<id>`, `/api/deals/<id>/terms`, `/api/playbooks/<playbook>/rules`, `/api/deals/<id>/risk-estimates`, `/api/deals/<id>/employees`, `/api/deals/<id>/consents`, `/api/deals/<id>/regulatory`, `/api/deals/<id>/benchmarks`, `/api/deals/<id>/notes`.

### Closing & Economics Package (buyer SPA)
Pull: `/api/deals/<id>`, `/api/deals/<id>/terms`, `/api/deals/<id>/cap-table`, `/api/deals/<id>/consents`, `/api/deals/<id>/employees`, `/api/deals/<id>/material-contracts`, `/api/deals/<id>/regulatory`, `/api/deals/<id>/diligence-findings`, `/api/playbooks/<playbook>/rules`.

### Committee Escalation
Pull: `/api/deals/<id>`, `/api/deals/<id>/terms`, `/api/policies/<policy>/thresholds`, `/api/deals/<id>/benchmarks`, `/api/deals/<id>/risk-estimates`, `/api/deals/<id>/notes`.

### Transition Review (seller carveout APA)
Pull: `/api/deals/<id>`, `/api/deals/<id>/terms`, `/api/deals/<id>/documents`, `/api/deals/<id>/employees`, `/api/deals/<id>/consents`, `/api/deals/<id>/material-contracts`, `/api/deals/<id>/regulatory`, `/api/deals/<id>/risk-estimates`, `/api/playbooks/<playbook>/rules`.

### Deviation Matrix (buyer SPA)
Pull: `/api/deals/<id>`, `/api/deals/<id>/terms`, `/api/playbooks/<playbook>/rules`, `/api/deals/<id>/consents`, `/api/deals/<id>/material-contracts`, `/api/deals/<id>/regulatory`, `/api/deals/<id>/employees`, `/api/deals/<id>/risk-estimates`, `/api/deals/<id>/diligence-findings`.
