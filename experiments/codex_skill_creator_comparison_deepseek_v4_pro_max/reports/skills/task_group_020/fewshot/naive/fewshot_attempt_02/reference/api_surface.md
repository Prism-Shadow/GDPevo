# Deal Workbench API Surface

Base URL: `<TASK_ENV_BASE_URL>` (substituted from the task prompt).

All GET endpoints return JSON. All IDs are stable strings from the workbench.

## Deal Endpoints

### GET /api/deals/<deal_id>

Returns deal metadata: `deal_id`, `project_name`, `client_name`, `counterparty_name`, `headline_value`, `currency`, `deal_type` (asset_purchase or stock_purchase), `status`, `signing_date`, `client_side` (if relevant).

### GET /api/deals/<deal_id>/terms

Returns array of draft term objects. Each term has at minimum: `term_id` (e.g., `TERM_PRJ_<PROJECT>_NN`), `category`, `clause_ref`, `draft_value` (numeric or structured), and `unit` where applicable. Categories include:

- `financing_condition`, `reverse_break_fee`, `escrow`, `indemnity_cap`, `indemnity_basket`, `survival_period`, `non_compete_non_solicit`, `employee_continuity`, `transition_services`, `tax_allocation`, `governing_law_forum`, `consent_condition`, `materiality_scrape`, `hsr_covenant`, `mae_carveouts`, `fiduciary_out`, `rw_survival`, and others.

### GET /api/deals/<deal_id>/documents

Returns array of document objects: `document_id`, `title`, `type`, `contents` or `url`.

### GET /api/deals/<deal_id>/benchmarks

Returns array of benchmark data points. Each has: `metric` (description), `sample_size`, `median`, `upper_quartile`, `lower_quartile`. Often used for term-level comparisons.

### GET /api/deals/<deal_id>/risk-estimates

Returns array of risk estimates: `risk_id` (e.g., `RSK_PRJ_<PROJECT>_NN`), `description`, `category`, `low_dollars`, `high_dollars`, `source`.

### GET /api/deals/<deal_id>/cap-table

Returns cap table for stock purchase deals. Array of holder rows: `holder`, `security_class`, `fully_diluted_pct`, `as_converted_shares`, `liquidation_preference` (for preferred).

### GET /api/deals/<deal_id>/consents

Returns array of third-party consent requirements: `consent_id` (e.g., `CNS_PRJ_<PROJECT>_NN`), `contract_name`, `counterparty`, `condition_type` (closing_condition, notice_only, post_closing_covenant), `amount_at_risk`, `risk_rating`.

### GET /api/deals/<deal_id>/employees

Returns: `total_employee_count`, `continuing_employee_count`, and an `employees` array with: `employee_id` (e.g., `EMP_PRJ_<PROJECT>_NN`), `group`, `service_years`, `pto_liability`, `warn_risk`, `transfer_status`.

### GET /api/deals/<deal_id>/material-contracts

Returns array of material contracts: `contract_id` (e.g., `MAT_PRJ_<PROJECT>_NN`), `contract_name`, `counterparty`, `annual_revenue`, `consent_required`, `change_of_control_clause`, `condition_type`.

### GET /api/deals/<deal_id>/regulatory

Returns regulatory facts: `hsr_required` (boolean), `threshold_basis`, `filing_status`, `hell_or_high_water` (or similar effort covenant), `industry_review_expected`, and any additional approval types.

### GET /api/deals/<deal_id>/diligence-findings

Returns array of diligence findings: `finding_id` (e.g., `FND_PRJ_<PROJECT>_NN`), `description`, `category`, `amount` (if quantified), `recommendation`.

### GET /api/deals/<deal_id>/notes

Returns array of deal notes: `note_id`, `author`, `date`, `text`. Useful for negotiation context.

## Playbook and Policy Endpoints

### GET /api/playbooks

Returns list of playbook IDs and descriptions. Common IDs: `PB_SELLER_A`, `PB_BUYER_A`.

### GET /api/playbooks/<playbook_id>/rules

Returns array of playbook rules. Each rule: `rule_id`, `category`, `preferred_value`, `fallback_value`, `position_code`, `required` (boolean), `unit`. Rules define the client's preferred and fallback negotiating positions. Compare draft terms from `/api/deals/<id>/terms` against these values.

### GET /api/policies

Returns list of policy IDs. Common IDs: `POL_MA_2025_A`.

### GET /api/policies/<policy_id>/thresholds

Returns array of policy thresholds. Each: `threshold_id`, `category`, `threshold_value`, `threshold_unit`, `threshold_amount`, `approved_carveouts`, `required_triggers`. Compare draft terms against thresholds; anything exceeding the threshold is `out_of_policy` and subject to escalation.

## Search and SQL

### GET /api/search?q=<text>

Cross-deal text search. Returns matching records.

### POST /api/query

Read-only SQL. Body: `{"token": "deal-workbench-readonly", "query": "<SQL>"}`. Returns query results. Use for joins, aggregations, or when REST endpoints do not expose needed relationships.
