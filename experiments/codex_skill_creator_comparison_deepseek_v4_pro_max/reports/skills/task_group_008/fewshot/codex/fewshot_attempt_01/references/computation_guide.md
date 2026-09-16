# Computation Guide

Formulas and decision logic for each analysis type. All USD values rounded to cents. Use Python for calculations; prefer precise float arithmetic with final rounding.

## Source Resolution

When source documents for a client disagree, resolve by this priority chain and recency.

### Priority Hierarchy

For profile-level facts (income, beneficiaries, intent, tax rate, estate value):
1. SIGNED_PROFILE
2. ATTORNEY_MEMO 
3. CRM_NOTE
4. STALE_MARKETING_INTAKE

For account-level data (IRA balances, returns):
1. CUSTODIAN_EXPORT
2. SIGNED_PROFILE
3. CRM_NOTE

Within the same source type, prefer the document with the latest effective_date.

### Applying Resolution

Build a merged fact set by starting with the lowest-priority source and overlaying higher-priority sources. If a higher-priority source omits a field, keep the lower-priority value for that field.

### Controlling Source Selection in Output

For source_resolution fields:
- controlling_profile_source: The source type that provided the key profile facts. For train examples this was SIGNED_PROFILE.
- controlling_account_source: The source for account data. For train examples CUSTODIAN_EXPORT.
- controlling_beneficiary_source: The source for beneficiary count. For train examples SIGNED_PROFILE.
- controlling_policy_source: The source for life insurance policy data.
- controlling_goal_source: The source for philanthropic/family-transfer intent. For train examples SIGNED_PROFILE.
- controlling_asset_source: The source for trust asset values. For train examples ATTORNEY_MEMO or SIGNED_PROFILE.

---

## Roth Conversion RMD (analysis_type: roth_conversion_rmd)

### Data Sources
- Client profile: age, filing_status, marginal_tax_rate, annual_non_ira_income, liquid_assets
- IRA account: traditional_balance, roth_balance, expected_return, recommended_conversion_years, rmd_start_age (73)
- Tax policies: conversion_bracket_targets[filing_status], marginal_tax_rate
- RMD factors: divisors by age

### Conversion Plan

1. first_conversion_year: planning_year (typically 2026).
2. conversion_years: recommended_conversion_years from the IRA account record.
3. conversion_years_positive: Same as conversion_years.
4. annual_conversion_amount: conversion_bracket_targets[filing_status] - annual_non_ira_income. This fills the remaining tax-bracket room each year.
5. total_converted: annual_conversion_amount * conversion_years.
6. total_conversion_tax: total_converted * marginal_tax_rate.

### Recommendation

- primary_action: STAGED_ROTH_CONVERSION when conversion_years >= 1 and annual_conversion_amount > 0. DEFER when annual_conversion_amount <= 0. NO_CONVERSION when already fully Roth.
- suitability: SUITABLE when primary_action is STAGED_ROTH_CONVERSION. BORDERLINE when annual_conversion_amount is small. DEFER when liquidity gap exists.
- risk_flag: TAX_BRACKET_MANAGEMENT (default), LIQUIDITY_CONSTRAINT (liquid_assets < total_conversion_tax), RMD_NEAR_TERM (first_rmd_year very close).

### RMD Projection

1. horizon_year: From the request memo.
2. first_rmd_year: planning_year + (rmd_start_age - client_age). Use client_age from resolved profile.

3. Compute baseline RMD tax (no conversions):
   - Start with traditional_balance at beginning of planning_year.
   - For each year from planning_year through horizon_year:
     a. Determine client age in that year: age_at_year = client_age + (year - planning_year).
     b. If year >= first_rmd_year: RMD = balance / RMD_divisor_for_age[age_at_year]. Tax = RMD * marginal_tax_rate. Subtract RMD from balance.
     c. Grow remaining balance: balance *= (1 + expected_return).
   - Sum all RMD taxes = baseline_rmd_tax_through_horizon.

4. Compute conversion RMD tax (with staged conversions):
   - Start with initial traditional_balance and initial roth_balance.
   - For each year from planning_year through horizon_year:
     a. If year is within the conversion window (first_conversion_year through first_conversion_year + conversion_years - 1):
        - Convert annual_conversion_amount from traditional to Roth: add annual_conversion_amount to Roth, subtract from traditional.
     b. Determine client age in that year.
     c. If year >= first_rmd_year: RMD = traditional_balance / RMD_divisor[age]. Tax = RMD * marginal_tax_rate. Subtract RMD from traditional.
     d. Grow both traditional and Roth balances by expected_return.
   - Sum RMD taxes = conversion_rmd_tax_through_horizon.

5. rmd_tax_savings_through_horizon: baseline_rmd_tax - conversion_rmd_tax.

### Legacy Projection

1. projected_roth_balance_horizon: Roth balance at horizon_year after all growth and conversion additions.
   - Start with initial roth_balance. Each conversion year add annual_conversion_amount to Roth. Grow at expected_return each year through horizon_year.
2. projected_traditional_balance_horizon: Traditional balance at horizon_year after conversions, RMDs, and growth.
3. heir_tax_profile:
   - MOSTLY_TAX_FREE when projected_roth_balance significantly exceeds projected_traditional_balance.
   - MIXED_TAXABLE_AND_TAX_FREE when both are substantial.
   - MOSTLY_TAXABLE when traditional dominates.

---
## ILIT Crummey Implementation (analysis_type: ilit_crummey_implementation)

### Data Sources
- Client profile: age, filing_status
- Source documents (resolved): beneficiary_count
- Life insurance: death_benefit, annual_premium, planned_contribution_date, is_existing_policy_transfer
- Tax policies: annual_gift_exclusion for planning_year

### Recommendation

- primary_action:
  - FUND_WITH_CRUMMEY_NOTICES: New policy, premium <= exclusion capacity, no existing transfer.
  - USE_LIFETIME_EXEMPTION_FOR_SHORTFALL: Premium gap exists but manageable.
  - USE_NEW_POLICY_OR_ACCEPT_LOOKBACK: Existing policy transfer with lookback risk.
  - DISCLOSE_LOOKBACK_AND_USE_EXEMPTION: Existing policy transfer with shortfall.
- suitability:
  - SUITABLE_WITH_ADMINISTRATION: Normal case, premium fits within exclusion.
  - BORDERLINE: Shortfall or lookback present.
  - NOT_SUITABLE: Severe issues.
- risk_flag:
  - LOW_IF_FORMALITIES_MET: New policy, premium <= exclusion.
  - EXCLUSION_SHORTFALL: Premium > exclusion capacity.
  - THREE_YEAR_LOOKBACK: Existing policy transfer.
  - THREE_YEAR_LOOKBACK_AND_EXCLUSION_SHORTFALL: Both issues.

### Gift Plan

1. planning_year: Current planning year (2026).
2. annual_exclusion_per_beneficiary: annual_gift_exclusion for planning_year (20000 for 2026).
3. beneficiary_count: From resolved profile.
4. annual_exclusion_capacity: annual_exclusion_per_beneficiary * beneficiary_count.
5. annual_premium: From life insurance policy.
6. premium_gap: max(0, annual_premium - annual_exclusion_capacity). Use 0.0 when premium fits within exclusion.

### Administration

1. notices_required: beneficiary_count (one Crummey notice per beneficiary).
2. contribution_date: planned_contribution_date from life insurance.
3. notice_due_date: contribution_date + 7 calendar days.
4. withdrawal_window_end: contribution_date + 37 calendar days (7-day notice + 30-day window).
5. earliest_premium_payment_date: withdrawal_window_end + 1 calendar day.
6. dedicated_bank_account_required: true (best practice for ILIT).

Use Python datetime for date arithmetic: datetime.date.fromisoformat() + datetime.timedelta(days=N).

### Estate Result

1. death_benefit: From life insurance policy.
2. estate_inclusion_risk: Same value as recommendation risk_flag.
3. projected_outside_estate_if_implemented: death_benefit (full value kept outside estate if ILIT works).
4. tax_liquidity_support: death_benefit * 0.4 (estate tax rate applied to death benefit).

---
## Trust Comparison (analysis_type: trust_comparison)

### Data Sources
- Client profile: estate_value, liquid_assets, filing_status
- Source documents (resolved): philanthropic_intent, family_transfer_priority
- Trust candidate: asset_value, expected_growth_rate, grat_term_years, grat_annuity_rate, crat_term_years, crat_payout_rate
- Tax policies: estate_tax_exemption, estate_tax_rate, charitable_deduction_rate

### Recommendation

- preferred_strategy:
  - GRAT when family_transfer_priority = "high" and philanthropic_intent != "high".
  - CRAT when philanthropic_intent = "high".
- rationale_code:
  - CHILDREN_TRANSFER_PRIORITY when GRAT is preferred.
  - PHILANTHROPIC_PRIORITY when CRAT is preferred.
- alternate_role:
  - SECONDARY_CHARITABLE_TOOL when GRAT preferred.
  - SECONDARY_FAMILY_TRANSFER_TOOL when CRAT preferred.

### Estate Context

1. planning_year: 2026.
2. exemption_used: estate_tax_exemption for planning_year (13610000 for 2026).
   IMPORTANT: For MFJ (married filing jointly) clients, double the exemption: exemption_used = estate_tax_exemption * 2.
3. taxable_estate: max(0, estate_value - exemption_used).
4. estate_tax_exposure: taxable_estate * estate_tax_rate.
5. liquid_assets_available: From client profile.
6. liquidity_gap_before_planning: max(0, estate_tax_exposure - liquid_assets_available).

### GRAT Calculation

1. term_years: grat_term_years from trust candidate.
2. projected_remainder_to_heirs:
   - Future value: asset_value * (1 + expected_growth_rate) ^ grat_term_years
   - Total annuity: asset_value * grat_annuity_rate * grat_term_years
   - Remainder: max(0, future_value - total_annuity)
3. estimated_estate_tax_reduction: projected_remainder_to_heirs * estate_tax_rate.
4. mortality_inclusion_risk: TERM_SURVIVAL_REQUIRED (grantor must survive the term).

### CRAT Calculation

1. term_years: crat_term_years from trust candidate (typically 20).
2. projected_charitable_remainder:
   - Annual payout: asset_value * crat_payout_rate
   - Total payouts: annual_payout * crat_term_years
   - Future value: asset_value * (1 + expected_growth_rate) ^ crat_term_years
   - Remainder: max(0, future_value - total_payouts)
3. estimated_income_tax_deduction: projected_charitable_remainder * charitable_deduction_rate.
4. family_transfer_fit: LOW (CRAT remainder goes to charity, not family).

---

## Estate Liquidity Action Plan (analysis_type: estate_liquidity_action_plan)

### Data Sources
- All data from client profile, source documents, life insurance, trust candidates, tax policies.
- Resolve source conflicts as above.

### Recommendation

- primary_action:
  - COMBINE_ILIT_AND_GRAT when ILIT is viable and family transfer is the priority.
  - CRAT_WITH_LIQUIDITY_REVIEW when philanthropic intent dominates.
  - ILIT_WITH_EXEMPTION_REVIEW when ILIT is central but premium gap exists.
- sequencing:
  - ILIT_FIRST_THEN_GRAT when ILIT should be executed before trust planning.
  - TRUST_DECISION_FIRST when the trust strategy drives the sequence.
  - ILIT_FIRST_THEN_ATTORNEY_REVIEW when legal review is the next step after ILIT.
- risk_flag: Same enum values as ILIT risk flags. Choose LOW_IF_FORMALITIES_MET for standard cases.

### Estate Context

Same formulas as Trust Comparison estate context section.

### ILIT Section

Same formulas as ILIT Crummey section: annual_exclusion_capacity, premium_gap, estate_inclusion_risk, projected_outside_estate_if_implemented (= death_benefit).

### Trust Transfer Section

- preferred_strategy: GRAT or CRAT based on family vs philanthropic intent (same logic as trust comparison).
- projected_remainder_to_heirs: GRAT remainder calculation (always computed).
- estimated_estate_tax_reduction: projected_remainder_to_heirs * estate_tax_rate.
- projected_charitable_remainder: CRAT charitable remainder (always computed as the alternate).

### Action Set

Pick from these actions, sort alphabetically:
- ATTORNEY_DRAFT_REVIEW: Always include when any trust or ILIT is recommended.
- CRAT_FOR_CHARITABLE_REMAINDER: Include when CRAT is the alternate/secondary tool and philanthropic intent exists.
- GRAT_FOR_APPRECIATING_SHARES: Include when GRAT is recommended or is the alternate.
- ILIT_CRUMMEY_NOTICE_CYCLE: Include when ILIT is part of the plan.
- LIFETIME_EXEMPTION_ALLOCATION: Include when premium_gap > 0 or estate_tax_exposure > 0.

Always include ATTORNEY_DRAFT_REVIEW when any structured plan is recommended.
