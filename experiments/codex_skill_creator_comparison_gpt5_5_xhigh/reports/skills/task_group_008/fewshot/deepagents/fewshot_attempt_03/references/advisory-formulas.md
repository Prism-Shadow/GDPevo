# Advisory Formulas

Use current API constants rather than hard-coded tax values.

## Shared Resolution

- Use `SIGNED_PROFILE` facts for `annual_non_ira_income`, `marginal_tax_rate`, `beneficiary_count`, goals, age, filing status, marital status, liquid assets, planning year, and estate value when present.
- Use `/api/clients/{client_id}` only to backfill missing signed-profile facts.
- Use `CUSTODIAN_EXPORT` retirement records for traditional and Roth balances, return, RMD start age, and recommended conversion years.
- Use life-insurance records for proposed ILIT policy facts; report their controlling policy source as `SIGNED_PROFILE`.
- Use trust-candidate records for GRAT/CRAT economics; report their controlling asset source as `ATTORNEY_MEMO`.

## Roth Conversion And RMD

- `first_conversion_year = planning_year`.
- `annual_conversion_amount = max(conversion_bracket_targets[filing_status] - annual_non_ira_income, 0)`.
- `conversion_years = recommended_conversion_years`.
- `conversion_years_positive = count of years with positive conversion amount`.
- `total_converted = annual_conversion_amount * conversion_years_positive`.
- `total_conversion_tax = total_converted * marginal_tax_rate`.
- `first_rmd_year = planning_year + max(rmd_start_age - age, 0)`.
- For each year from `planning_year` through horizon:
  - If in the conversion window, move the annual conversion from traditional to Roth before RMDs.
  - If current age is at least RMD start age, RMD tax is `traditional_balance / rmd_factor[current_age] * marginal_tax_rate`; subtract the RMD from traditional balance.
  - Grow traditional and Roth balances by `expected_return` after conversions and RMDs.
- Baseline RMD tax uses the same loop without conversions.
- Conversion RMD tax uses the conversion loop.
- `rmd_tax_savings_through_horizon = baseline_rmd_tax - conversion_rmd_tax`.
- Roth and traditional horizon balances are the balances after the horizon year's growth.
- `heir_tax_profile` is `MIXED_TAXABLE_AND_TAX_FREE` when both horizon balances are positive, `MOSTLY_TAX_FREE` when Roth is positive and traditional is zero, otherwise `MOSTLY_TAXABLE`.

## ILIT Crummey Funding

- `annual_exclusion_per_beneficiary = annual_gift_exclusion[planning_year]`.
- `annual_exclusion_capacity = annual_exclusion_per_beneficiary * beneficiary_count`.
- `premium_gap = max(annual_premium - annual_exclusion_capacity, 0)`.
- `notices_required = beneficiary_count`.
- `notice_due_date = contribution_date + 7 days`.
- `withdrawal_window_end = notice_due_date + 30 days`.
- `earliest_premium_payment_date = withdrawal_window_end + 1 day`.
- `dedicated_bank_account_required = true` for ILIT-owned proposed policies.
- Risk flag:
  - Existing policy transfer and premium gap: `THREE_YEAR_LOOKBACK_AND_EXCLUSION_SHORTFALL`.
  - Existing policy transfer only: `THREE_YEAR_LOOKBACK`.
  - Premium gap only: `EXCLUSION_SHORTFALL`.
  - Otherwise: `LOW_IF_FORMALITIES_MET`.
- Primary action:
  - No transfer and no gap: `FUND_WITH_CRUMMEY_NOTICES`.
  - No transfer and gap: `USE_LIFETIME_EXEMPTION_FOR_SHORTFALL`.
  - Transfer and no gap: `USE_NEW_POLICY_OR_ACCEPT_LOOKBACK`.
  - Transfer and gap: `DISCLOSE_LOOKBACK_AND_USE_EXEMPTION`.
- Suitability is `SUITABLE_WITH_ADMINISTRATION` for low-risk cases, `BORDERLINE` for one risk, and `NOT_SUITABLE` for combined risks.
- `projected_outside_estate_if_implemented = death_benefit`.
- `tax_liquidity_support = death_benefit * estate_tax_rate`.

## GRAT And CRAT

- Exemption used is `estate_tax_exemption[planning_year] * 2` for married households, otherwise one exemption.
- `taxable_estate = max(estate_value - exemption_used, 0)`.
- `estate_tax_exposure = taxable_estate * estate_tax_rate`.
- `liquidity_gap_before_planning = max(estate_tax_exposure - liquid_assets, 0)`.
- `projected_remainder_to_heirs = asset_value * (1 + expected_growth_rate) ^ grat_term_years - asset_value * grat_annuity_rate * grat_term_years`.
- `estimated_estate_tax_reduction = projected_remainder_to_heirs * estate_tax_rate`.
- `projected_charitable_remainder = asset_value * (1 + expected_growth_rate) ^ crat_term_years - asset_value * crat_payout_rate * crat_term_years`.
- `estimated_income_tax_deduction = projected_charitable_remainder * charitable_deduction_rate`.
- Prefer `GRAT` when family-transfer priority is high and at least as strong as philanthropic intent. Prefer `CRAT` when philanthropic intent is high and stronger than family-transfer priority.
- GRAT rationale is `CHILDREN_TRANSFER_PRIORITY` with alternate role `SECONDARY_CHARITABLE_TOOL`.
- CRAT rationale is `PHILANTHROPIC_PRIORITY` with alternate role `SECONDARY_FAMILY_TRANSFER_TOOL`.
- CRAT `family_transfer_fit` is `LOW` when CRAT is not preferred for a family-transfer-priority client, otherwise `MODERATE` unless family-transfer priority is high.

## Estate Liquidity Action Plan

Compute estate context, ILIT, and trust-transfer sections with the formulas above.

- Primary action is `COMBINE_ILIT_AND_GRAT` when GRAT is preferred and ILIT risk is low.
- Use `CRAT_WITH_LIQUIDITY_REVIEW` when CRAT is preferred.
- Use `ILIT_WITH_EXEMPTION_REVIEW` when ILIT has a shortfall or lookback risk and no stronger combined action applies.
- Sequencing is `ILIT_FIRST_THEN_GRAT` for combined low-risk GRAT plans, `TRUST_DECISION_FIRST` for CRAT plans, and `ILIT_FIRST_THEN_ATTORNEY_REVIEW` when ILIT risk needs review.
- `action_set` includes:
  - `ATTORNEY_DRAFT_REVIEW` when a trust transfer is part of the plan.
  - `GRAT_FOR_APPRECIATING_SHARES` when GRAT is preferred.
  - `CRAT_FOR_CHARITABLE_REMAINDER` when CRAT is preferred.
  - `ILIT_CRUMMEY_NOTICE_CYCLE` when an ILIT policy is present.
  - `LIFETIME_EXEMPTION_ALLOCATION` when `premium_gap > 0`.
- Sort `action_set` alphabetically.
