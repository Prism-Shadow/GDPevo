# Calculation Rules

Use these rules to audit or manually reproduce the bundled helper.

## API Records

Fetch these endpoint families for the target client:

- `/api/clients/{client_id}` for stable household record fields.
- `/api/source-documents` filtered by `client_id` for signed profiles, attorney memos, and CRM notes.
- `/api/retirement-accounts` filtered by `client_id` for IRA balances, expected return, RMD start age, and conversion years.
- `/api/life-insurance` filtered by `client_id` for ILIT policy amount, premium, contribution date, and transfer status.
- `/api/trust-candidates` filtered by `client_id` for GRAT and CRAT inputs.
- `/api/policies/tax` for gift exclusions, estate exemption, estate tax rate, Roth bracket targets, CRAT term cap, and charitable deduction rate.
- `/api/rmd-factors` for annual RMD divisors by age.

## Source Priority

Use `SIGNED_PROFILE` for current household facts and goals when present. Use `ATTORNEY_MEMO` for attorney-confirmed estate or trust asset facts. Use `CUSTODIAN_EXPORT` for retirement account data. Use `CRM_NOTE` only as fallback because it is an older import.

## Roth Conversion/RMD

Use the signed profile for age, planning year, filing status, non-IRA income, marginal tax rate, and liquidity. Use the retirement account for balances, expected return, RMD start age, and recommended conversion years.

- `annual_conversion_amount = max(0, conversion_bracket_target[filing_status] - annual_non_ira_income)`, capped so annual amount times conversion years does not exceed the traditional balance.
- `total_converted = annual_conversion_amount * conversion_years_positive`.
- `total_conversion_tax = total_converted * marginal_tax_rate`.
- `first_rmd_year = planning_year` if current age is at least RMD start age, otherwise `planning_year + (rmd_start_age - current_age)`.
- Baseline projection loop: for each year through the horizon, take the RMD from the beginning-of-year traditional balance if current age is at least the RMD start age, tax it at the marginal tax rate, subtract it, then grow the remaining traditional balance by expected return.
- Conversion projection loop: each year, convert the annual amount first while inside the conversion schedule, then calculate any RMD tax from the remaining traditional balance, subtract the RMD, and grow both traditional and Roth balances by expected return.

## ILIT Crummey Cycle

Use beneficiary count from the signed profile and policy data from the life-insurance endpoint.

- `annual_exclusion_capacity = annual_gift_exclusion[planning_year] * beneficiary_count`.
- `premium_gap = max(0, annual_premium - annual_exclusion_capacity)`.
- Notice due date is contribution date plus 7 days.
- Withdrawal window end is notice due date plus 30 days.
- Earliest premium payment date is one day after the withdrawal window end.
- Death benefit outside the estate equals the policy death benefit if implemented. Tax liquidity support equals death benefit times estate tax rate.
- Set risk to `LOW_IF_FORMALITIES_MET` when there is no premium gap and no existing policy transfer. Add `EXCLUSION_SHORTFALL`, `THREE_YEAR_LOOKBACK`, or both when those facts are present.

## GRAT/CRAT

Compute estate context first:

- Use the policy estate-tax exemption for the planning year, doubled for MFJ or married households.
- `taxable_estate = max(0, estate_value - exemption_used)`.
- `estate_tax_exposure = taxable_estate * estate_tax_rate`.
- `liquidity_gap_before_planning = max(0, estate_tax_exposure - liquid_assets)`.

Compute trust values from the trust-candidate record:

- `projected_remainder_to_heirs = asset_value * (1 + expected_growth_rate) ** grat_term_years - asset_value * grat_annuity_rate * grat_term_years`.
- `estimated_estate_tax_reduction = projected_remainder_to_heirs * estate_tax_rate`.
- `projected_charitable_remainder = asset_value * (1 + expected_growth_rate) ** crat_term_years - asset_value * crat_payout_rate * crat_term_years`.
- `estimated_income_tax_deduction = projected_charitable_remainder * charitable_deduction_rate`.

Prefer `GRAT` when family-transfer priority is at least philanthropic intent. Prefer `CRAT` when philanthropic intent is higher. If `GRAT` is preferred, use rationale `CHILDREN_TRANSFER_PRIORITY` and alternate role `SECONDARY_CHARITABLE_TOOL`; if `CRAT` is preferred, use rationale `PHILANTHROPIC_PRIORITY` and alternate role `SECONDARY_FAMILY_TRANSFER_TOOL`.

## Estate Liquidity Action Plan

Combine estate context, ILIT gap/risk, and trust metrics. Use `COMBINE_ILIT_AND_GRAT` with sequencing `ILIT_FIRST_THEN_GRAT` when ILIT formalities are low-risk and the trust preference is GRAT. Use `CRAT_WITH_LIQUIDITY_REVIEW` when CRAT is the preferred trust. Use `ILIT_WITH_EXEMPTION_REVIEW` when the ILIT has a premium gap or existing-policy lookback risk.

Build `action_set` from the recommended components, then sort it alphabetically:

- Always include `ATTORNEY_DRAFT_REVIEW` for an estate liquidity action plan.
- Include `ILIT_CRUMMEY_NOTICE_CYCLE` when an ILIT is part of the plan.
- Include `GRAT_FOR_APPRECIATING_SHARES` for GRAT.
- Include `CRAT_FOR_CHARITABLE_REMAINDER` for CRAT.
- Include `LIFETIME_EXEMPTION_ALLOCATION` when premium gap requires exemption allocation.
