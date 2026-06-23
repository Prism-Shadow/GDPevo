# Reflect-3 Advisory Planning SOP

Use this skill for structured private-wealth advisory tasks that ask for Roth/RMD projections, ILIT Crummey funding, GRAT/CRAT comparisons, or combined estate-liquidity action plans.

## Workflow

1. Read the staged prompt, request memo, and answer template first. The template is the contract: return exactly one JSON object, use the enum strings verbatim, and emit numbers as JSON numbers rounded to cents.
2. Query only the task-provided advisory API records needed for the requested output: client profile, source documents, retirement accounts, life insurance, trust candidates, tax policy, and RMD factors.
3. Resolve conflicts before calculating. Do not average conflicting facts.
4. Build the JSON from the template fields, not from prose labels. Sort any `action_set` alphabetically.

## Source Resolution

- Use `SIGNED_PROFILE` for current household facts: age, planning year, filing status, marital status, non-IRA income, marginal rate, beneficiary count, estate value, liquid assets, and repeated profile goals when it is the latest signed source.
- Use `CUSTODIAN_EXPORT` for retirement account balances, expected return, Roth/traditional split, RMD start age, and recommended conversion years.
- Use `SIGNED_PROFILE` for life-insurance policy resolution unless the staged facts explicitly point policy terms to another source.
- Use `ATTORNEY_MEMO` for attorney-led trust/estate planning judgments when the task asks for trust assets, attorney coordination, or goal control and the memo supplies the controlling family/philanthropy priorities.
- Treat older `CRM_NOTE` values as stale when a signed profile or attorney memo disagrees.

## Roth Conversion And RMD

- First RMD year:
  `planning_year + (rmd_start_age - current_age)`.
- Annual conversion amount:
  `max(0, conversion_bracket_targets[filing_status] - annual_non_ira_income)`.
- Use the account export's `recommended_conversion_years` when bracket room is positive, even if the client is already near RMD age. Set `conversion_years_positive` to the count of positive conversion years; use zero when annual conversion amount is zero.
- Total converted:
  `annual_conversion_amount * conversion_years_positive`.
- Total conversion tax:
  `total_converted * marginal_tax_rate`.
- Baseline RMD projection: for each year through the horizon, take RMD when age is at least `rmd_start_age`, using that year's factor, then grow the remaining traditional balance by `expected_return`.
- Conversion projection: in each conversion year, move the annual conversion amount from traditional to Roth at the start of the year; then apply any RMD for that year; then grow both balances by `expected_return`.
- RMD tax each year:
  `rmd_amount * marginal_tax_rate`.
- RMD savings:
  `baseline_rmd_tax_through_horizon - conversion_rmd_tax_through_horizon`.
- Legacy balances are the conversion-scenario Roth and traditional balances at the horizon. Include any existing Roth balance before applying conversions and annual growth.
- Recommendation conventions:
  use `STAGED_ROTH_CONVERSION` when bracket room is positive and liquidity can cover conversion tax; use `TAX_BRACKET_MANAGEMENT` for ordinary bracket-fill cases; use `RMD_NEAR_TERM` when RMDs begin during or immediately after the conversion window. Near-RMD can still be `SUITABLE` if liquidity and bracket room are adequate.

## Estate And ILIT

- Taxable estate:
  `max(0, estate_value - estate_tax_exemption)`. For married households, apply the household/marital exemption treatment implied by the profile; otherwise use the single policy exemption.
- Estate tax exposure:
  `taxable_estate * estate_tax_rate`.
- Liquidity gap before planning:
  `max(0, estate_tax_exposure - liquid_assets)`.
- Annual exclusion capacity:
  `beneficiary_count * annual_gift_exclusion[planning_year]`. Do not double for gift splitting unless the staged facts explicitly provide that convention.
- Premium gap:
  `max(0, annual_premium - annual_exclusion_capacity)`.
- ILIT risk flags:
  `LOW_IF_FORMALITIES_MET` for a new ILIT-owned policy with no premium gap; `EXCLUSION_SHORTFALL` when the premium exceeds exclusion capacity; `THREE_YEAR_LOOKBACK` for an existing policy transfer; combine both when both risks apply.
- Crummey administration:
  notices required equals beneficiary count; contribution date comes from the policy record; require a dedicated bank account. If no separate notice rule is supplied, use prompt notice and a 30-calendar-day withdrawal period before premium payment.
- Projected outside-estate amount for a clean ILIT implementation is the policy death benefit.

## GRAT And CRAT

- Prefer `GRAT` when the controlling goals emphasize family transfer or children/heirs. Prefer `CRAT` when philanthropic intent is controlling and high.
- Rationale codes mirror the preference: `CHILDREN_TRANSFER_PRIORITY` for GRAT and `PHILANTHROPIC_PRIORITY` for CRAT. The alternate role is the opposite secondary tool.
- GRAT transfer impact:
  `asset_value * max(expected_growth_rate - grat_annuity_rate, 0) * grat_term_years`.
- GRAT estate-tax reduction:
  `projected_remainder_to_heirs * estate_tax_rate`.
- CRAT charitable remainder impact:
  `asset_value * max(expected_growth_rate - crat_payout_rate, 0) * min(crat_term_years, max_crat_term_years)`.
- CRAT income-tax deduction:
  `asset_value * charitable_deduction_rate`.
- CRAT family-transfer fit is usually `LOW` when GRAT is preferred for high family-transfer goals, `MODERATE` when the goals are mixed, and `HIGH` only when the CRAT is itself the preferred fit.
- Mortality inclusion risk for GRAT fields is `TERM_SURVIVAL_REQUIRED`.

## Combined Action Plans

- Use `COMBINE_ILIT_AND_GRAT` when the ILIT is clean and family-transfer goals favor a GRAT.
- Use `CRAT_WITH_LIQUIDITY_REVIEW` when philanthropy controls and liquidity still needs review.
- Use `ILIT_WITH_EXEMPTION_REVIEW` when the policy is useful but gift-tax/exemption or lookback issues dominate.
- Sequencing:
  `ILIT_FIRST_THEN_GRAT` for clean ILIT plus GRAT; `TRUST_DECISION_FIRST` when the trust choice controls the plan; `ILIT_FIRST_THEN_ATTORNEY_REVIEW` when policy risk or exemption allocation needs legal review.
- Action-set entries should be included only when they correspond to the selected plan, then sorted alphabetically:
  `ATTORNEY_DRAFT_REVIEW`, `CRAT_FOR_CHARITABLE_REMAINDER`, `GRAT_FOR_APPRECIATING_SHARES`, `ILIT_CRUMMEY_NOTICE_CYCLE`, `LIFETIME_EXEMPTION_ALLOCATION`.

## Common Pitfalls

- Do not use stale CRM values when signed or attorney records conflict.
- Do not cap Roth conversion years merely because RMDs begin soon; model conversions and RMDs in the same year when the account export recommends a multi-year plan.
- Do not include conversion tax inside `rmd_projection`; that section sums only tax on RMDs.
- Do not output dollar amounts as strings.
- Do not leave `action_set` in reasoning order; sort it alphabetically.
