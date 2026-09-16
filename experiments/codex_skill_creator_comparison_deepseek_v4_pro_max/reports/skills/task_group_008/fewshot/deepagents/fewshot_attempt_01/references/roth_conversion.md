## Roth Conversion and RMD Projection

Use when `analysis_type` is `roth_conversion_rmd`. This covers staged Roth conversions
before/during Required Minimum Distributions.

### Input Sources

- Client record: age, filing_status, planning_year, liquid_assets, estate_value
- Signed profile: annual_non_ira_income, marginal_tax_rate, beneficiary_count
- Custodian export: traditional_balance, roth_balance, expected_return, rmd_start_age,
  recommended_conversion_years
- Tax policy: conversion_bracket_targets[filing_status]
- RMD factors: divisor by age

### Source Document Resolution

When multiple source documents exist for the same client, resolve conflicts by
selecting the most recent authoritative source. Precedence order from strongest to
weakest:

1. SIGNED_PROFILE — most recent; signed by client
2. ATTORNEY_MEMO — attorney call notes, typically slightly older
3. CUSTODIAN_EXPORT — authoritative for account balances and return rates
4. CRM_NOTE — older CRM import, may be stale
5. STALE_MARKETING_INTAKE — oldest, least reliable

For retirement-account data specifically, prefer CUSTODIAN_EXPORT for balances and
expected_return. For profile data (income, marginal rate, beneficiaries, intent),
prefer SIGNED_PROFILE.

### Computation Model

#### Annual Conversion Amount

Compute the annual conversion amount that fills the filing-status bracket target
without exceeding it:

```
annual_conversion = conversion_bracket_targets[filing_status] - annual_non_ira_income
```

If annual_conversion <= 0, no conversion is recommended (DEFER).

#### Conversion Plan Fields

- **first_conversion_year**: planning_year
- **conversion_years**: recommended_conversion_years from custodian export
- **conversion_years_positive**: same as conversion_years
- **annual_conversion_amount**: as computed above, rounded to cents
- **total_converted**: annual_conversion_amount * conversion_years, rounded to cents
- **total_conversion_tax**: annual_conversion_amount * marginal_tax_rate * conversion_years,
  rounded to cents

#### RMD Projection (year-by-year simulation)

Use a year-by-year loop from planning_year through horizon_year.

**Baseline (no conversion):**

```
trad = traditional_balance
tax = 0
for year in planning_year .. horizon_year:
    age = client_age + (year - planning_year)
    if age >= rmd_start_age:
        rmd = trad / RMD_FACTORS[age]
        trad = trad - rmd
        tax = tax + rmd * marginal_rate
    trad = trad * (1 + expected_return)
```

**Conversion scenario:**

```
trad = traditional_balance
roth = roth_balance
tax = 0
for year in planning_year .. horizon_year:
    age = client_age + (year - planning_year)
    # Convert before RMD
    if (year - planning_year) < conversion_years:
        trad = trad - annual_conversion
        roth = roth + annual_conversion
    if age >= rmd_start_age:
        rmd = trad / RMD_FACTORS[age]
        trad = trad - rmd
        tax = tax + rmd * marginal_rate
    trad = trad * (1 + expected_return)
    roth = roth * (1 + expected_return)
```

- **baseline_rmd_tax_through_horizon**: tax from baseline simulation, rounded to cents
- **conversion_rmd_tax_through_horizon**: tax from conversion simulation, rounded to cents
  (excludes conversion tax itself)
- **rmd_tax_savings_through_horizon**: baseline - conversion, rounded to cents
- **projected_roth_balance_horizon**: final roth value from conversion simulation, rounded to cents
- **projected_traditional_balance_horizon**: final trad value from conversion simulation,
  rounded to cents

The conversion tax itself (total_conversion_tax) is separate and is NOT included in
conversion_rmd_tax_through_horizon. The RMD projection fields only count RMD taxes.

#### Recommendation Logic

- **primary_action**:
  - STAGED_ROTH_CONVERSION: when total_converted > 0 and annual_conversion > 0
  - DEFER: when annual_conversion <= 0 or rmd_tax_savings is negligible
  - NO_CONVERSION: when there is no traditional balance to convert

- **suitability**:
  - SUITABLE: rmd_tax_savings_through_horizon is meaningfully positive and
    liquid_assets can cover total_conversion_tax
  - BORDERLINE: marginal case where savings exist but constraints apply
  - DEFER: savings are negative or negligible

- **risk_flag**:
  - TAX_BRACKET_MANAGEMENT: annual_conversion fills bracket exactly; need to
    monitor for bracket creep
  - LIQUIDITY_CONSTRAINT: liquid_assets < total_conversion_tax
  - RMD_NEAR_TERM: client age is already at or near rmd_start_age

#### Legacy Projection

- **heir_tax_profile**: based on ratio of projected roth vs traditional at horizon
  - MOSTLY_TAX_FREE: roth >> traditional
  - MIXED_TAXABLE_AND_TAX_FREE: both meaningful
  - MOSTLY_TAXABLE: traditional >> roth

### Script

Use `scripts/roth_projection.py` for deterministic projection. See SKILL.md for
invocation patterns.

