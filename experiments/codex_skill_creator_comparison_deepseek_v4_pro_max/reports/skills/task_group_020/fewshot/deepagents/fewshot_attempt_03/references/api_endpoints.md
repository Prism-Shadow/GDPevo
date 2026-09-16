# Deal Workbench API Endpoints

Base URL: `<TASK_ENV_BASE_URL>`. All requests are read-only GET unless noted.

## Core Endpoints

| Method | Path | Returns |
|--------|------|---------|
| GET | `/workspace` | Top-level workspace metadata |
| GET | `/api/deals` | List of all deal IDs |
| GET | `/api/deals/<deal_id>` | Full deal record (id, parties, structure, purchase price, status) |
| GET | `/api/deals/<deal_id>/terms` | Draft term objects ordered by term_id |
| GET | `/api/deals/<deal_id>/documents` | Document metadata for the deal |
| GET | `/api/deals/<deal_id>/notes` | Negotiation notes |

## Playbooks and Policies

| Method | Path | Returns |
|--------|------|---------|
| GET | `/api/playbooks` | List of playbook IDs |
| GET | `/api/playbooks/<playbook_id>/rules` | Playbook rules with preferred and fallback positions |
| GET | `/api/policies` | List of policy IDs |
| GET | `/api/policies/<policy_id>/thresholds` | Policy threshold values and descriptions |

## Supporting Records

| Method | Path | Returns |
|--------|------|---------|
| GET | `/api/deals/<deal_id>/benchmarks` | Market benchmark data (sample size, median, quartiles) |
| GET | `/api/deals/<deal_id>/risk-estimates` | Risk estimates with quantified exposure ranges |
| GET | `/api/deals/<deal_id>/cap-table` | Capitalization table (holders, security classes, ownership percentages, shares) |
| GET | `/api/deals/<deal_id>/consents` | Third-party consent records with contract, counterparty, risk ratings, amounts |
| GET | `/api/deals/<deal_id>/employees` | Employee records (IDs, groups, counts, PTO liability, service-credit status) |
| GET | `/api/deals/<deal_id>/material-contracts` | Material contract records with annual revenue, counterparty, condition type |
| GET | `/api/deals/<deal_id>/regulatory` | Regulatory status (HSR applicability, HSR threshold basis, industry reviews, hell-or-high-water) |
| GET | `/api/deals/<deal_id>/diligence-findings` | Diligence findings (IDs, categories, amounts, remediation status) |

## Search

| Method | Path | Description |
|--------|------|-------------|
| GET | `/api/search` | Cross-deal search endpoint |

## Read-Only SQL

If the workbench offers SQL:

| Method | Path | Body |
|--------|------|------|
| POST | `/api/query` | `{"token": "deal-workbench-readonly", "sql": "<single SELECT or WITH statement>"}` |

Use SQL for cross-table checks: validate term coverage against playbook rules, confirm employee counts against PTO totals, check consent conditional relationships across records.

## Resource ID Patterns

- Terms: `TERM_<deal_id>_NN`
- Consents: `CNS_<deal_id>_NN`
- Employees: `EMP_<deal_id>_NN`
- Material contracts: `MAT_<deal_id>_NN`
- Regulatory: `REG_<deal_id>`
- Documents: `DOC_<deal_id>_NN`
- Risk estimates: `RSK_<deal_id>_NN`
- Findings: `FND_<deal_id>_NN`
- Playbooks: `PB_<role>_<variant>` (e.g. `PB_SELLER_A`, `PB_BUYER_A`)
- Policies: `POL_<context>_<year>_<variant>` (e.g. `POL_MA_2025_A`)

## Typical Record Shapes

### Deal Record
- `deal_id`, `project_name`, `client_name`, `target_name`, `counterparty_name`
- `deal_structure` (asset_purchase, stock_purchase, merger)
- `headline_purchase_price` (integer dollars)
- `upfront_cash`, `stock_value`, `milestone_value` (may be null)
- `currency`, `signing_date`, `status`

### Term Record
- `term_id`, `label`, `category`
- Numerical fields: `percent`, `amount_dollars`, `months`
- Boolean/flag fields: present or absent
- Text fields: `clause_ref`, `governing_law`, `forum`, `tax_allocation_method`, `transfer_tax_split`

### Playbook Rule
- `rule_id`, `category`, `term_label`
- `preferred`: object with target values
- `fallback`: object with negotiable minimum/maximum values
- `required`: boolean (whether the term must appear)
- `description`

### Consent Record
- `consent_id`, `contract_name`, `counterparty`
- `condition_type` (closing_condition, notice_only, post_closing_covenant)
- `risk_rating`, `amount_at_risk`

### Employee Record
- `employee_id`, `name` or `group`
- `service_credit_status`, `pto_accrued_dollars`, `warn_risk`, `continuing`

### Material Contract Record
- `contract_id`, `contract_name`, `counterparty`
- `condition_type`, `annual_revenue`

### Regulatory Record
- `hsr_required` (boolean), `threshold_basis`
- `regulatory_approval` type, `hell_or_high_water_required` (boolean)

### Risk Estimate
- `estimate_id`, `category`, `exposure_low_dollars`, `exposure_high_dollars`

### Diligence Finding
- `finding_id`, `category`, `amount_dollars`, `status`

### Cap Table Record
- Holder groups, security classes (common stock, preferred stock, options)
- Fully-diluted percentages, as-converted shares
