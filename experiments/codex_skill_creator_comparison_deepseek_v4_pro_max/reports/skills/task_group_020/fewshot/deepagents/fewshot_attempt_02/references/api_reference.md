# M&A Deal Workbench API Reference

## Base URL

The workbench runs at a configurable base URL. The prompt provides this as `<TASK_ENV_BASE_URL>` or similar. All routes below are relative to that base.

## Standard Endpoints

### Deal Records

**GET /api/deals/<deal_id>**

Returns the deal header record. Key fields:
- `deal_id`: string matching the path parameter
- `project_name`: human-readable project name (e.g. "Project Juniper")
- `deal_type`: `asset_purchase`, `stock_purchase`, `merger`, `carveout`
- `target_name`: the target entity or business name
- `counterparty_name`: the other side's entity name
- `headline_value`: integer USD, the headline purchase price
- `signing_date`: ISO date string (YYYY-MM-DD) or null
- `status`: deal lifecycle status

**GET /api/deals/<deal_id>/terms**

Returns an array of current draft term objects. Key fields per term:
- `term_id`: stable string like `TERM_PRJ_EXAMPLE_01`
- `category`: term category (e.g. `indemnity`, `escrow`, `closing_conditions`, `restrictive_covenants`, `governing_law`)
- `clause_ref`: draft section reference
- `draft_provision`: the drafted text or summary
- Numeric fields where applicable: `cap_percent`, `survival_months`, `escrow_percent`, `escrow_release_months`, `basket_type`, `reverse_break_fee_percent`, `financing_condition_present`, `materiality_scrape_type`

**GET /api/deals/<deal_id>/documents**

Returns an array of deal document records. Use to verify document existence and references.

### Playbooks

**GET /api/playbooks**

Returns a list of available playbooks. Common IDs: `PB_SELLER_A`, `PB_BUYER_A`.

**GET /api/playbooks/<playbook_id>/rules**

Returns an array of playbook rules. Each rule typically includes:
- `rule_id`: stable string
- `category`: term category
- `rule_text`: description of the position
- `preferred_percent`, `fallback_percent`: percentages for numeric caps
- `preferred_months`, `fallback_months`: durations
- `preferred_amount`, `fallback_amount`: amounts where applicable
- Boolean flags: `service_credit_required`, `tsa_required`, `reverse_break_fee_required`, `hell_or_high_water_required`, `delaware_law_required`
- Struct fields for restrictive covenants, tax allocation, governing law

### Policies

**GET /api/policies**

Returns a list of available policies.

**GET /api/policies/<policy_id>/thresholds**

Returns committee policy thresholds. Key fields per threshold:
- `category`: term category
- `metric`: what is measured
- `threshold_value`: the policy limit
- `threshold_unit`: `percent_points`, `months`, `amount`, `carveouts`
- `approved_carveout_groups`: allowed carveout categories
- `required_triggers`: triggers that must be present

### Employees

**GET /api/deals/<deal_id>/employees**

Returns an array of employee records. Key fields:
- `employee_id`: stable string like `EMP_PRJ_EXAMPLE_01`
- `employee_group`: `field`, `operations`, `corporate`, `all`
- `service_years`: number
- `accrued_pto_dollars`: integer
- `warn_risk`: `low`, `medium`, `high`
- Fields for restrictive covenant status, retention status

### Consents

**GET /api/deals/<deal_id>/consents**

Returns an array of consent records. Key fields:
- `consent_id`: stable string like `CNS_PRJ_EXAMPLE_01`
- `contract_name`: the underlying contract
- `counterparty`: counterparty name
- `consent_type`: `closing_condition`, `notice_only`, `post_closing_covenant`
- `amount_at_risk`: integer USD
- `risk_rating`: `LOW`, `MEDIUM`, `HIGH`

### Material Contracts

**GET /api/deals/<deal_id>/material-contracts**

Returns an array of material contract records. Key fields:
- `contract_id`: stable string like `MAT_PRJ_EXAMPLE_01`
- `contract_name`: contract name
- `annual_revenue`: integer USD
- `consent_required`: boolean
- `condition_type`: `closing_condition`, `notice_only`, `post_closing_covenant`

### Regulatory

**GET /api/deals/<deal_id>/regulatory**

Returns regulatory records. Key fields:
- `record_id`: stable string like `REG_PRJ_EXAMPLE`
- `hsr_required`: boolean
- `threshold_basis`: `size-of-transaction`, `below threshold`
- `regulatory_approval_type`: `HSR only`, `HSR and industry review`, `none expected`
- `hell_or_high_water_required`: boolean or null

### Risk Estimates

**GET /api/deals/<deal_id>/risk-estimates**

Returns an array of risk estimate records. Key fields:
- `estimate_id`: stable string like `RSK_PRJ_EXAMPLE_01`
- `category`: risk category
- `low_estimate`: integer USD
- `high_estimate`: integer USD
- `description`: text

### Benchmarks

**GET /api/deals/<deal_id>/benchmarks**

Returns an array of benchmark records. Key fields:
- `benchmark_id`: stable string
- `metric`: what is measured
- `sample_size`: integer
- `median`: numeric value
- `upper_quartile`: numeric value

### Diligence Findings

**GET /api/deals/<deal_id>/diligence-findings**

Returns an array of diligence finding records. Key fields:
- `finding_id`: stable string like `FND_PRJ_EXAMPLE_01`
- `category`: finding category
- `description`: text
- `amount_at_risk`: integer USD or null

### Notes

**GET /api/deals/<deal_id>/notes**

Returns an array of negotiation notes. Key fields:
- `note_id`: stable string
- `content`: text
- `created_date`: ISO date string

### Cap Table

**GET /api/deals/<deal_id>/cap-table**

Returns cap table records with holder, security class, fully diluted percentage, and as-converted shares.

## Read-Only SQL

```
POST /api/query
Content-Type: application/json

{
  "token": "deal-workbench-readonly",
  "sql": "SELECT ... FROM ..."
}
```

The endpoint accepts a single SELECT or WITH (CTE) statement. Use for:
- Cross-referencing deal records with playbook rules
- Aggregating amounts across multiple records
- Verifying data consistency between records

## Stable ID Conventions

All workbench records use stable identifiers with consistent prefixes:

| Prefix | Record type | Example |
|---|---|---|
| `TERM_` | Draft term | `TERM_PRJ_EXAMPLE_01` |
| `CNS_` | Consent | `CNS_PRJ_EXAMPLE_01` |
| `MAT_` | Material contract | `MAT_PRJ_EXAMPLE_01` |
| `EMP_` | Employee | `EMP_PRJ_EXAMPLE_01` |
| `FND_` | Diligence finding | `FND_PRJ_EXAMPLE_01` |
| `RSK_` | Risk estimate | `RSK_PRJ_EXAMPLE_01` |
| `REG_` | Regulatory record | `REG_PRJ_EXAMPLE` |
| `DOC_` | Document | `DOC_PRJ_EXAMPLE_01` |
| `RUL_` | Playbook rule | `RUL_PB_SELLER_A_01` |
| `POL_` | Policy threshold | `POL_MA_COMMITTEE_01` |

IDs are case-sensitive. Quote them as-is from the workbench records. Do not invent IDs.

## Common Query Patterns

**Cross-check terms against a playbook**:
```sql
SELECT t.term_id, t.category, t.cap_percent, r.preferred_percent, r.fallback_percent
FROM deal_terms t
JOIN playbook_rules r ON t.category = r.category
WHERE t.deal_id = 'PRJ_EXAMPLE' AND r.playbook_id = 'PB_SELLER_A'
```

**Aggregate employee PTO liability**:
```sql
SELECT SUM(accrued_pto_dollars) AS total_pto
FROM employees
WHERE deal_id = 'PRJ_EXAMPLE'
```

**Identify closing-condition consents**:
```sql
SELECT consent_id, contract_name, amount_at_risk
FROM consents
WHERE deal_id = 'PRJ_EXAMPLE' AND consent_type = 'closing_condition'
```

## Response Format

All GET endpoints return `Content-Type: application/json`. Response bodies are either a single object or an array of objects. The SQL endpoint returns `{"rows": [...], "row_count": N}`.

Empty or null fields in API responses mean the data is not available in the workbench -- do not fabricate values for empty fields.
