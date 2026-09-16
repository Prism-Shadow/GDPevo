## Advisory API Surface

Base URL is supplied by the harness as `API_BASE`. Every endpoint is a GET. Append query params as needed (the API ignores unrecognized params).

### GET /api/clients

List all clients. Returns an array of client records, each with:

```
client_id, household_name, age, marital_status, filing_status,
planning_year, estate_value, liquid_assets, record_status, advisor_team
```

### GET /api/clients/{client_id}

Single client record, same shape.

### GET /api/source-documents

Returns an array of source documents. Always filter by `?client_id={id}`. Each document has:

```
document_id, client_id, source_type, effective_date, title, facts{}
```

`source_type` is one of: `SIGNED_PROFILE`, `ATTORNEY_MEMO`, `CRM_NOTE`, `STALE_MARKETING_INTAKE`.

`facts` contains a variable set of keys. Common keys include:
`annual_non_ira_income`, `marginal_tax_rate`, `beneficiary_count`,
`philanthropic_intent`, `family_transfer_priority`, `age`, `planning_year`,
`filing_status`, `marital_status`, `liquid_assets`, `estate_value`.

### GET /api/retirement-accounts

Filter by `?client_id={id}`. Each record:

```
account_id, client_id, source_type, traditional_balance, roth_balance,
expected_return, rmd_start_age, recommended_conversion_years
```

### GET /api/life-insurance

Filter by `?client_id={id}`. Each record:

```
policy_id, client_id, proposed_owner, death_benefit, annual_premium,
planned_contribution_date, is_existing_policy_transfer
```

### GET /api/trust-candidates

Filter by `?client_id={id}`. Each record:

```
trust_case_id, client_id, asset_value, expected_growth_rate,
grat_term_years, grat_annuity_rate, crat_term_years, crat_payout_rate
```

### GET /api/policies/tax

Global constants, no query params. Returns:

```
policy_label, annual_gift_exclusion (by year), estate_tax_exemption (by year),
estate_tax_rate (0.4), conversion_bracket_targets (by filing status),
max_crat_term_years (20), charitable_deduction_rate (0.35)
```

`conversion_bracket_targets` keys: `MFJ`, `SINGLE`, `HOH`.

### GET /api/rmd-factors

Global RMD divisor table, no query params. Returns a map of age (string key) to divisor (float). Ages range from 73 to 99.

### GET /portal/client/{client_id}

Returns an HTML portal page. Not needed for structured JSON output; use the API endpoints above.
