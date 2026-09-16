# Advisory API Reference

Base URL: {API_BASE} (typically set as API_BASE env var by the harness)
Auth: none

All responses are JSON. Use curl -s and pipe through Python for filtering when needed.

## Clients

**GET /api/clients**

Returns all clients. Each record:

    client_id (string)
    household_name (string)
    age (integer)
    marital_status (string: married or single)
    filing_status (string: MFJ, SINGLE, or HOH)
    planning_year (integer)
    estate_value (number)
    liquid_assets (number)
    record_status (string)
    advisor_team (string)

**GET /api/clients/{client_id}**

Returns a single client record by client ID (e.g., CLT-1001).

## Source Documents

**GET /api/source-documents**

Returns all source documents. Filter by client_id in your code. Each record:

    document_id (string)
    client_id (string)
    source_type (string enum): SIGNED_PROFILE, ATTORNEY_MEMO, CRM_NOTE, CUSTODIAN_EXPORT, STALE_MARKETING_INTAKE
    effective_date (string ISO date)
    title (string)
    facts (object): client-specific facts including annual_non_ira_income, marginal_tax_rate,
          beneficiary_count, philanthropic_intent (low/moderate/high),
          family_transfer_priority (low/moderate/high),
          age, planning_year, filing_status, marital_status, liquid_assets, estate_value

CRM_NOTE documents typically have older dates and fewer fields. SIGNED_PROFILE has the most complete data and the most recent dates.

## Retirement Accounts

**GET /api/retirement-accounts**

Returns all retirement accounts. Filter by client_id. Each record:

    account_id (string)
    client_id (string)
    source_type (string): CUSTODIAN_EXPORT
    traditional_balance (number)
    roth_balance (number)
    expected_return (number, decimal like 0.065)
    rmd_start_age (integer, always 73 in this dataset)
    recommended_conversion_years (integer)

## Life Insurance

**GET /api/life-insurance**

Returns all life insurance policies. Filter by client_id. Each record:

    policy_id (string)
    client_id (string)
    proposed_owner (string, e.g. ILIT)
    death_benefit (number)
    annual_premium (number)
    planned_contribution_date (string ISO date)
    is_existing_policy_transfer (boolean)

## Trust Candidates

**GET /api/trust-candidates**

Returns all trust candidate cases. Filter by client_id. Each record:

    trust_case_id (string)
    client_id (string)
    asset_value (number)
    expected_growth_rate (number, decimal)
    grat_term_years (integer)
    grat_annuity_rate (number, decimal)
    crat_term_years (integer)
    crat_payout_rate (number, decimal)

## Tax Policy Constants

**GET /api/policies/tax**

Returns current tax planning constants:

    policy_label (string)
    annual_gift_exclusion (object): {"2025": 19000, "2026": 20000}
    estate_tax_exemption (object): {"2025": 13990000, "2026": 13610000}
    estate_tax_rate (number): 0.4
    conversion_bracket_targets (object): {"MFJ": 394600, "SINGLE": 197300, "HOH": 263500}
    max_crat_term_years (integer): 20
    charitable_deduction_rate (number): 0.35

## RMD Factors

**GET /api/rmd-factors**

Returns RMD divisors keyed by age (string keys):

    "73": 26.5, "74": 25.5, ..., "99": 6.8

## Portal

**GET /portal/client/{client_id}**

Returns human-readable HTML for the client portal page. Optional context; use API endpoints for structured data.
