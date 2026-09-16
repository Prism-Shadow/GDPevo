# Advisory Planning Workflow

## 1. Resolve sources

Use the newest record inside each source class, then apply this precedence:

- `SIGNED_PROFILE` for household facts, priorities, age, filing status, beneficiary count, marginal tax rate, liquid assets, and planning year
- `CUSTODIAN_EXPORT` for retirement balances, expected return, RMD start age, and recommended conversion years
- `ATTORNEY_MEMO` for estate and trust asset context
- life-insurance records for policy owner, death benefit, premium, and planned contribution date
- tax policy constants for gift exclusion, estate exemption, estate tax rate, conversion brackets, CRAT limit, and charitable deduction rate
- RMD factors for distribution divisors
- CRM notes only as fallback context

When more than one record exists in the same class, pick the latest `effective_date`.

## 2. Common rules

- Use the planning year from the signed profile or memo.
- Round currency only at the end.
- Use JSON numbers, not strings.
- Clamp negative dollar results to `0.0` when the field represents capacity, exposure, or gap.

## 3. Roth conversion and RMD

Use the filing-status bracket target from tax policy:

`annual_conversion_amount = max(0, bracket_target - annual_non_ira_income)`

`first_rmd_year = planning_year + max(0, rmd_start_age - age)`

`total_converted = annual_conversion_amount * conversion_years`

`total_conversion_tax = total_converted * marginal_tax_rate`

Project RMD tax with this yearly order:

1. Subtract the annual conversion amount in conversion years.
2. If the year is at or after `first_rmd_year`, take the RMD from the current traditional balance.
3. Subtract the RMD.
4. Grow the remaining balance by `expected_return`.

Use the same loop with no conversions for the baseline case. The RMD tax is the sum of annual RMDs times the marginal tax rate.

Decision rule:

- Choose `STAGED_ROTH_CONVERSION` when bracket headroom is positive and the household can absorb the tax.
- Choose `NO_CONVERSION` when headroom is non-positive.
- Choose `DEFER` when liquidity is tight or the first RMD year is immediate.
- Use `TAX_BRACKET_MANAGEMENT` for a staged conversion, `LIQUIDITY_CONSTRAINT` for cash pressure, and `RMD_NEAR_TERM` when the current planning year is the first RMD year.

Set suitability to `SUITABLE` for a staged conversion, `BORDERLINE` when liquidity or timing is close, and `DEFER` when no conversion is justified.

## 4. ILIT Crummey funding

`annual_exclusion_capacity = annual_exclusion_per_beneficiary * beneficiary_count`

`premium_gap = max(0, annual_premium - annual_exclusion_capacity)`

Date rules:

- `notice_due_date = contribution_date + 7 days`
- `withdrawal_window_end = notice_due_date + 30 days`
- `earliest_premium_payment_date = withdrawal_window_end + 1 day`

Decision rule:

- New policy and no shortfall: `FUND_WITH_CRUMMEY_NOTICES`
- New policy and shortfall: `USE_LIFETIME_EXEMPTION_FOR_SHORTFALL`
- Existing transfer and no shortfall: `USE_NEW_POLICY_OR_ACCEPT_LOOKBACK`
- Existing transfer and shortfall: `DISCLOSE_LOOKBACK_AND_USE_EXEMPTION`

Use `LOW_IF_FORMALITIES_MET` for a clean new-policy funding path, `EXCLUSION_SHORTFALL` for a clean shortfall, `THREE_YEAR_LOOKBACK` for transfer timing risk, and `THREE_YEAR_LOOKBACK_AND_EXCLUSION_SHORTFALL` when both apply.

Set suitability to `SUITABLE_WITH_ADMINISTRATION` for a clean new-policy Crummey cycle, `BORDERLINE` when a shortfall or lookback issue must be managed, and `NOT_SUITABLE` only when the structure cannot be made compliant.

Set `projected_outside_estate_if_implemented` to the death benefit when the policy is structured cleanly.

## 5. GRAT versus CRAT

Use signed-profile priorities to choose the strategy:

- Choose `GRAT` when family transfer priority is at least as strong as philanthropic intent.
- Choose `CRAT` only when philanthropic intent clearly dominates.

Estate context:

`taxable_estate = max(0, estate_value - estate_tax_exemption)`

`estate_tax_exposure = taxable_estate * estate_tax_rate`

`liquidity_gap_before_planning = max(0, estate_tax_exposure - liquid_assets_available)`

GRAT:

`projected_remainder_to_heirs = asset_value * (1 + growth_rate) ^ term_years - asset_value * annuity_rate * term_years`

`estimated_estate_tax_reduction = projected_remainder_to_heirs * estate_tax_rate`

`mortality_inclusion_risk = TERM_SURVIVAL_REQUIRED`

CRAT:

`projected_charitable_remainder = asset_value * (1 + growth_rate) ^ term_years - asset_value * payout_rate * term_years`

`estimated_income_tax_deduction = projected_charitable_remainder * charitable_deduction_rate`

Set `crat.family_transfer_fit` to `LOW` when transfer priority dominates, `MODERATE` when the priorities are mixed, and `HIGH` only when philanthropy clearly dominates and transfer priority is low.

## 6. Estate liquidity action plan

Combine the ILIT and trust rules.

- Use `COMBINE_ILIT_AND_GRAT` when estate tax exposure exceeds liquid assets and both tools are viable.
- Use `ILIT_FIRST_THEN_GRAT` when the liquidity gap is the main pressure and the ILIT is clean.
- Use `ILIT_FIRST_THEN_ATTORNEY_REVIEW` when lookback or transfer-formality risk needs legal review before funding.
- Use `TRUST_DECISION_FIRST` when the trust choice must be settled before insurance funding.

Populate `action_set` only with applicable enums and sort it alphabetically.
Always compute both GRAT and CRAT dollar outputs when the schema includes them.
