## Advisory API Reference

Base URL: provided by harness as `API_BASE` environment variable or configured URL.
All endpoints return JSON arrays or objects. No authentication required.

### GET /api/clients
Returns all client records. Each entry:

| Field | Type | Description |
|-------|------|-------------|
| client_id | string | Stable identifier (e.g. CLT-1001) |
| household_name | string | Household display name |
| age | integer | Client age in planning year |
| marital_status | string | married or single |
| filing_status | string | MFJ, SINGLE, or HOH |
| planning_year | integer | Current planning year |
| estate_value | number | Total estate value in USD |
| liquid_assets | number | Liquid assets in USD |
| record_status | string | active or monitoring |
| advisor_team | string | Advisory team name |

### GET /api/clients/{client_id}
Returns a single client record with the same shape as the list entries.

### GET /api/source-documents
Returns all source documents across clients. Each entry:

| Field | Type | Description |
|-------|------|-------------|
| document_id | string | Document identifier |
| client_id | string | Owning client |
| source_type | string | SIGNED_PROFILE, ATTORNEY_MEMO, CUSTODIAN_EXPORT, CRM_NOTE, or STALE_MARKETING_INTAKE |
| effective_date | string | ISO date YYYY-MM-DD |
| title | string | Document title |
| facts | object | Key-value facts from the document |

Facts may include: annual_non_ira_income, marginal_tax_rate, beneficiary_count,
philanthropic_intent, family_transfer_priority, age, planning_year, filing_status,
marital_status, liquid_assets, estate_value.

### GET /api/retirement-accounts
Returns all retirement account records. Each entry:

| Field | Type | Description |
|-------|------|-------------|
| account_id | string | Account identifier |
| client_id | string | Owning client |
| source_type | string | Typically CUSTODIAN_EXPORT |
| traditional_balance | number | Current traditional IRA balance |
| roth_balance | number | Current Roth IRA balance |
| expected_return | number | Annual expected return (decimal) |
| rmd_start_age | integer | Age RMDs begin (typically 73) |
| recommended_conversion_years | integer | Advisory-recommended conversion span |

### GET /api/life-insurance
Returns all life insurance policies. Each entry:

| Field | Type | Description |
|-------|------|-------------|
| policy_id | string | Policy identifier |
| client_id | string | Owning client |
| proposed_owner | string | ILIT or personal |
| death_benefit | number | Death benefit in USD |
| annual_premium | number | Annual premium in USD |
| planned_contribution_date | string | Intended contribution date ISO |
| is_existing_policy_transfer | boolean | Whether this is a transfer of an existing policy |

### GET /api/trust-candidates
Returns trust candidate records. Each entry:

| Field | Type | Description |
|-------|------|-------------|
| trust_case_id | string | Trust case identifier |
| client_id | string | Owning client |
| asset_value | number | Asset value to place in trust |
| expected_growth_rate | number | Annual growth rate (decimal) |
| grat_term_years | integer | Recommended GRAT term |
| grat_annuity_rate | number | GRAT annuity rate (decimal of asset) |
| crat_term_years | integer | CRAT term (typically 20) |
| crat_payout_rate | number | CRAT payout rate (decimal, typically 0.055) |

### GET /api/policies/tax
Returns a single JSON object with tax constants:

| Field | Type | Description |
|-------|------|-------------|
| annual_gift_exclusion | object | Map of year to exclusion amount |
| estate_tax_exemption | object | Map of year to exemption amount |
| estate_tax_rate | number | Estate tax rate (0.4) |
| conversion_bracket_targets | object | MFJ, SINGLE, HOH bracket targets |
| max_crat_term_years | integer | Max CRAT term |
| charitable_deduction_rate | number | Charitable deduction rate (0.35) |

### GET /api/rmd-factors
Returns an object mapping age (integer key) to divisor (number value). Divisors start at
age 73 and extend through age 99+.

### GET /portal/client/{client_id}
May be available as an alternative source of aggregated client data.

