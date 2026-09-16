## Analysis Type Reference

Read [api_surface.md](api_surface.md) for endpoint shapes before starting any analysis.

### 1. roth_conversion_rmd

**Triggers**: Client has retirement accounts, horizon year in memo.

**Data gathering**: clients/{id}, source-documents?client_id={id}, retirement-accounts?client_id={id}, policies/tax, rmd-factors.

**Approach**:

From retirement-accounts: extract traditional_balance, roth_balance, expected_return, rmd_start_age, recommended_conversion_years.
From SIGNED_PROFILE facts: marginal_tax_rate, annual_non_ira_income, filing_status.
From policies/tax: conversion_bracket_targets[filing_status].

**Conversion plan**:
- first_conversion_year = planning_year
- conversion_years = recommended_conversion_years from account
- conversion_years_positive = same as conversion_years
- annual_conversion_amount: fill the remaining space in the current tax bracket. Compute as bracket_target - annual_non_ira_income, rounded to a reasonable round number.
- total_converted = annual_conversion_amount * conversion_years
- total_conversion_tax = total_converted * marginal_tax_rate

**RMD projection**:
- first_rmd_year = planning_year + (rmd_start_age - age)
- Simulate year-by-year from planning_year through horizon_year (inclusive).
- Baseline (no conversion): grow traditional by expected_return each year; when age >= rmd_start_age, compute RMD = balance / rmd_factor[age], tax it at marginal_tax_rate, subtract from balance.
- Conversion scenario: convert annual_conversion_amount from traditional to Roth during conversion years; grow both balances each year; take RMDs from traditional when eligible.
- The within-year ordering (conversion, growth, RMD) must be consistent between baseline and conversion scenarios.
- Cumulative RMD taxes summed across all years yield baseline_rmd_tax and conversion_rmd_tax.
- rmd_tax_savings = baseline - conversion.

**Legacy**:
- After simulating through horizon_year: projected_roth_balance_horizon and projected_traditional_balance_horizon are the remaining balances.
- heir_tax_profile: MOSTLY_TAX_FREE if roth > 2 * traditional, MOSTLY_TAXABLE if traditional > 2 * roth, else MIXED_TAXABLE_AND_TAX_FREE.

**Recommendation**:
- primary_action: STAGED_ROTH_CONVERSION if savings > 0, DEFER if borderline, NO_CONVERSION if no benefit.
- suitability: SUITABLE if substantial savings, BORDERLINE if marginal, DEFER if liquidity constrained.
- risk_flag: TAX_BRACKET_MANAGEMENT (default), LIQUIDITY_CONSTRAINT if liquid_assets < total_conversion_tax, RMD_NEAR_TERM if first_rmd_year <= planning_year + 2.

### 2. ilit_crummey_implementation

**Triggers**: Client has life insurance, ILIT structure, Crummey cycle in memo.

**Data gathering**: clients/{id}, source-documents?client_id={id}, life-insurance?client_id={id}, policies/tax.

**Gift plan**:
- planning_year from client record
- annual_exclusion_per_beneficiary from policies/tax annual_gift_exclusion for planning_year
- beneficiary_count from SIGNED_PROFILE facts
- annual_exclusion_capacity = exclusion * count
- annual_premium from life-insurance record
- premium_gap = max(0, annual_premium - annual_exclusion_capacity)

**Administration (Crummey timeline)**:
- contribution_date from life-insurance planned_contribution_date
- notices_required = beneficiary_count
- notice_due_date = contribution_date + 7 days
- withdrawal_window_end = contribution_date + 37 days
- earliest_premium_payment_date = withdrawal_window_end + 1 day
- dedicated_bank_account_required: always true for ILIT

**Estate result**:
- death_benefit from life-insurance record
- estate_inclusion_risk: LOW_IF_FORMALITIES_MET if new policy and gap=0; EXCLUSION_SHORTFALL if gap>0; THREE_YEAR_LOOKBACK if is_existing_policy_transfer; THREE_YEAR_LOOKBACK_AND_EXCLUSION_SHORTFALL if both.
- projected_outside_estate_if_implemented = death_benefit if LOW_IF_FORMALITIES_MET, else 0
- tax_liquidity_support = death_benefit * 0.4

**Recommendation**:
- primary_action: FUND_WITH_CRUMMEY_NOTICES if no gap and no lookback; USE_LIFETIME_EXEMPTION_FOR_SHORTFALL if gap; USE_NEW_POLICY_OR_ACCEPT_LOOKBACK or DISCLOSE_LOOKBACK_AND_USE_EXEMPTION if existing transfer.
- suitability: SUITABLE_WITH_ADMINISTRATION if LOW risk; BORDERLINE if EXCLUSION_SHORTFALL; NOT_SUITABLE if lookback.
- risk_flag: same as estate_inclusion_risk.

### 3. trust_comparison

**Triggers**: Client choosing GRAT vs CRAT, trust candidate data available.

**Data gathering**: clients/{id}, source-documents?client_id={id}, trust-candidates?client_id={id}, policies/tax.

**Estate context**:
- planning_year from client record
- exemption_used: estate_tax_exemption[planning_year] from policies/tax, doubled for MFJ filing_status
- taxable_estate = max(0, estate_value - exemption_used)
- estate_tax_exposure = taxable_estate * 0.4
- liquid_assets_available from SIGNED_PROFILE
- liquidity_gap_before_planning = max(0, estate_tax_exposure - liquid_assets_available)

**GRAT**:
- term_years from trust-candidates grat_term_years
- Project trust asset year by year: grow at expected_growth_rate, subtract annuities (asset_value * grat_annuity_rate each year).
- projected_remainder_to_heirs = remaining trust balance after term
- estimated_estate_tax_reduction = remainder * 0.4
- mortality_inclusion_risk: always TERM_SURVIVAL_REQUIRED

**CRAT**:
- term_years from trust-candidates crat_term_years (capped at max_crat_term_years 20)
- Project: grow at expected_growth_rate, subtract payouts (asset_value * crat_payout_rate each year).
- projected_charitable_remainder = remaining balance at end
- estimated_income_tax_deduction = remainder * charitable_deduction_rate (0.35 from tax policy)
- family_transfer_fit: LOW (CRAT primarily benefits charity), MODERATE, HIGH

**Recommendation**:
- preferred_strategy: GRAT if family_transfer_priority = "high", CRAT if philanthropic_intent = "high"
- rationale_code: CHILDREN_TRANSFER_PRIORITY when GRAT, PHILANTHROPIC_PRIORITY when CRAT
- alternate_role: SECONDARY_CHARITABLE_TOOL for GRAT, SECONDARY_FAMILY_TRANSFER_TOOL for CRAT

### 4. estate_liquidity_action_plan

**Triggers**: Combined ILIT + trust transfer analysis, estate liquidity focus.

**Data gathering**: clients/{id}, source-documents?client_id={id}, life-insurance?client_id={id}, trust-candidates?client_id={id}, policies/tax.

Reuse computations from types 2 and 3 above for the ILIT and trust_transfer sections.

**action_set** (sorted alphabetically):
- ATTORNEY_DRAFT_REVIEW: always include
- CRAT_FOR_CHARITABLE_REMAINDER: include if philanthropic_intent != "low"
- GRAT_FOR_APPRECIATING_SHARES: include if family_transfer_priority = "high"
- ILIT_CRUMMEY_NOTICE_CYCLE: include if life insurance exists and premium_gap = 0
- LIFETIME_EXEMPTION_ALLOCATION: include if estate_tax_exposure > 0

**Recommendation**:
- primary_action: COMBINE_ILIT_AND_GRAT when both ILIT and GRAT are applicable; CRAT_WITH_LIQUIDITY_REVIEW when philanthropic intent dominates; ILIT_WITH_EXEMPTION_REVIEW otherwise.
- sequencing: ILIT_FIRST_THEN_GRAT if GRAT in action_set; ILIT_FIRST_THEN_ATTORNEY_REVIEW otherwise.
- risk_flag: from ILIT section.

### General Notes

- monetary values: USD, 2 decimal places, JSON numbers (not strings)
- years: integers
- dates: ISO YYYY-MM-DD
- enums: exact strings from answer_template.json
- estate_tax_rate: always 0.4
- marginal_tax_rate and beneficiary_count: from SIGNED_PROFILE facts
- rmd_factors: from /api/rmd-factors endpoint
- tax policy constants: from /api/policies/tax endpoint
