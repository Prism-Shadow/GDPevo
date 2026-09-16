# Calculation Patterns

These rules cover the advisory planning families shown by the staged examples. Use the live API values for the current client; do not reuse example-specific client IDs, answers, or dollar amounts.

## Shared Estate Context

Use the current planning year from the signed profile or client record unless the memo states otherwise.

- `exemption_used = estate_tax_exemption[planning_year] * 2` for married/MFJ households, otherwise one exemption.
- `taxable_estate = max(0, estate_value - exemption_used)`.
- `estate_tax_exposure = taxable_estate * estate_tax_rate`.
- `liquidity_gap_before_planning = max(0, estate_tax_exposure - liquid_assets_available)`.
- `liquid_assets_available` comes from the controlling profile/client record.

## Roth Conversion and RMD

Use signed profile facts for income, marginal rate, filing status, age, and planning year. Use the custodian export for balances, expected return, RMD start age, and recommended conversion years.

- `first_conversion_year = planning_year`.
- `conversion_years = recommended_conversion_years`.
- `annual_conversion_amount = max(0, conversion_bracket_targets[filing_status] - annual_non_ira_income)`.
- `conversion_years_positive` is the number of conversion years with a positive conversion amount.
- `total_converted = annual_conversion_amount * conversion_years_positive`, capped if the traditional balance would be exhausted.
- `total_conversion_tax = total_converted * marginal_tax_rate`.
- `first_rmd_year = planning_year + max(0, rmd_start_age - current_age)`.

RMD projection timeline:

1. For each year from `planning_year` through `horizon_year`, compute age as `current_age + (year - planning_year)`.
2. Baseline case: if age is at least the RMD start age, take `rmd = traditional_balance / rmd_factor[age]`, add `rmd * marginal_tax_rate` to baseline RMD tax, subtract the RMD from traditional balance, then grow the remaining traditional balance by expected return.
3. Conversion case: in each conversion year, convert the annual conversion amount from traditional to Roth first. If age is at least the RMD start age, then take that year's RMD from the post-conversion traditional balance. Grow the remaining traditional balance and Roth balance by expected return at year end.
4. `rmd_tax_savings_through_horizon = baseline_rmd_tax_through_horizon - conversion_rmd_tax_through_horizon`.
5. `projected_roth_balance_horizon` and `projected_traditional_balance_horizon` are the conversion-case balances after year-end growth in the horizon year.

For recommendation enums, favor staged conversion when there is positive bracket capacity and enough liquidity to absorb the conversion tax. Use a liquidity or near-term RMD risk flag only when those facts are the binding issue; otherwise bracket management is the usual risk theme.

## ILIT and Crummey Administration

Use signed profile facts for beneficiary count and planning year. Use tax policy for the annual gift exclusion. Use the life-insurance record for policy facts.

- `annual_exclusion_per_beneficiary = annual_gift_exclusion[planning_year]`.
- `annual_exclusion_capacity = annual_exclusion_per_beneficiary * beneficiary_count`.
- `premium_gap = max(0, annual_premium - annual_exclusion_capacity)`.
- `notices_required = beneficiary_count`.
- `contribution_date = planned_contribution_date`.
- `notice_due_date = contribution_date + 7 calendar days`.
- `withdrawal_window_end = notice_due_date + 30 calendar days`.
- `earliest_premium_payment_date = withdrawal_window_end + 1 calendar day`.
- `dedicated_bank_account_required = true` for formal ILIT administration.
- `projected_outside_estate_if_implemented = death_benefit` when the policy is owned by the ILIT and implementation formalities are met.
- `tax_liquidity_support = death_benefit * estate_tax_rate` when the field is requested.

Risk flag mapping:

- No premium gap and no existing-policy transfer: `LOW_IF_FORMALITIES_MET`.
- Premium gap only: `EXCLUSION_SHORTFALL`.
- Existing-policy transfer only: `THREE_YEAR_LOOKBACK`.
- Both issues: `THREE_YEAR_LOOKBACK_AND_EXCLUSION_SHORTFALL`.

Choose the action enum that directly matches the risk: fund with Crummey notices for low-risk funding, use lifetime exemption for exclusion shortfall, and disclose or review lookback risk for transferred existing policies.

## GRAT and CRAT

Use `/api/trust-candidates` for asset value, expected growth, GRAT term/rate, and CRAT term/payout. Use tax policy for estate tax and charitable deduction rates.

GRAT:

- `projected_remainder_to_heirs = asset_value * (1 + expected_growth_rate) ^ grat_term_years - asset_value * grat_annuity_rate * grat_term_years`.
- `estimated_estate_tax_reduction = projected_remainder_to_heirs * estate_tax_rate`.
- `mortality_inclusion_risk = TERM_SURVIVAL_REQUIRED` when the template requests that enum.

CRAT:

- Use the lesser of the candidate CRAT term and policy `max_crat_term_years` if both are present.
- `projected_charitable_remainder = asset_value * (1 + expected_growth_rate) ^ crat_term_years - asset_value * crat_payout_rate * crat_term_years`.
- `estimated_income_tax_deduction = projected_charitable_remainder * charitable_deduction_rate`.

Recommendation logic:

- Prefer `GRAT` when family transfer priority is stronger than philanthropic priority; rationale `CHILDREN_TRANSFER_PRIORITY`, alternate role `SECONDARY_CHARITABLE_TOOL`.
- Prefer `CRAT` when philanthropic priority is stronger; rationale `PHILANTHROPIC_PRIORITY`, alternate role `SECONDARY_FAMILY_TRANSFER_TOOL`.
- Set `family_transfer_fit` for the CRAT based on how well the charitable structure matches the family-transfer goal; it is low when family transfer is the dominant client goal.

## Estate Liquidity Action Plan

For combined estate liquidity tasks, calculate the shared estate context, ILIT values, and trust-transfer values separately, then synthesize:

- Use ILIT + GRAT when the ILIT can add liquidity outside the estate and the trust candidate favors family transfer.
- Use a CRAT path when philanthropic priority is dominant.
- Include `ILIT_CRUMMEY_NOTICE_CYCLE` when funding an ILIT with Crummey notices.
- Include `GRAT_FOR_APPRECIATING_SHARES` when GRAT is the preferred trust-transfer strategy.
- Include `CRAT_FOR_CHARITABLE_REMAINDER` when CRAT is the preferred strategy or expressly retained as an action.
- Include `LIFETIME_EXEMPTION_ALLOCATION` only when annual exclusion capacity does not cover the premium or the plan needs exemption allocation.
- Include `ATTORNEY_DRAFT_REVIEW` for trust/ILIT implementation and attorney coordination.
- Sort `action_set` alphabetically exactly as the template requires.
