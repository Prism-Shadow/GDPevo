# Private Wealth Advisory JSON Skill

Use this skill for structured private-wealth planning tasks that provide a prompt, request memo, answer template, and the advisory API. Produce only the JSON object requested by the template.

## Inputs And API

Read only the task input files: `input/prompt.txt`, `input/payloads/request_memo.md`, and `input/payloads/answer_template.json`. Extract the `client_id`, planning horizon if stated, required top-level keys, enum choices, date requirements, and any ordering constraints.

Fetch current records from the advisory API:

- `/api/clients/<client_id>` for household age, filing status, estate value, liquid assets, and planning year.
- `/api/source-documents?client_id=<client_id>` for conflicting household facts, goals, and source types.
- `/api/retirement-accounts?client_id=<client_id>` for IRA balances, expected return, RMD start age, and suggested conversion years.
- `/api/life-insurance?client_id=<client_id>` for ILIT policy terms.
- `/api/trust-candidates?client_id=<client_id>` for GRAT/CRAT asset assumptions.
- `/api/policies/tax` for annual exclusion, estate exemption, estate tax rate, conversion bracket targets, CRAT term cap, and charitable deduction rate.
- `/api/rmd-factors` for Uniform Lifetime RMD divisors.

Do not average conflicting facts. Choose the controlling source for each fact domain and report that source in `source_resolution`.

## Source Resolution

Prefer source types by domain, not by a single global rule:

- Household profile facts such as age, filing status, marital status, planning year, liquid assets, non-IRA income, marginal tax rate, beneficiary count, and client goals: use the newest `SIGNED_PROFILE`; fall back to `ATTORNEY_MEMO`, then `CRM_NOTE`, then `STALE_MARKETING_INTAKE`.
- Retirement account balances and return assumptions: use the retirement account record, normally `CUSTODIAN_EXPORT`, even when profile documents conflict.
- Beneficiary counts for ILIT Crummey capacity: use the controlling profile source, normally `SIGNED_PROFILE`.
- Life-insurance policy terms: use the life-insurance record; if it exposes `source_type`, report it, otherwise treat the current policy proposal as the controlling policy record and select the closest allowed template enum, usually `SIGNED_PROFILE`.
- Trust transfer asset, term, annuity, payout, and growth assumptions: use the trust-candidate record; if no source type is present, report `ATTORNEY_MEMO` for `controlling_asset_source`.
- Goal fields for GRAT/CRAT recommendations: use current signed goals unless a more specific attorney memo clearly controls legal strategy.

## Shared Calculations

Use JSON numbers, not strings. Round USD outputs to cents at the final field level. Dates are ISO `YYYY-MM-DD`. For estate calculations use the policy constants for the client planning year:

- `taxable_estate = max(estate_value - estate_tax_exemption[planning_year], 0)`
- `estate_tax_exposure = taxable_estate * estate_tax_rate`
- `liquidity_gap_before_planning = max(estate_tax_exposure - liquid_assets, 0)`

Apply one exemption to the household record unless the API explicitly provides a combined exemption count or separate spouse exemption field. Do not double the exemption merely because marital status is married.

## Roth Conversion And RMD

Use this for `analysis_type: roth_conversion_rmd`.

- `first_rmd_year = planning_year + max(rmd_start_age - age, 0)`.
- `pre_rmd_conversion_years = min(recommended_conversion_years, max(first_rmd_year - planning_year, 0))`.
- `annual_conversion_capacity = max(conversion_bracket_targets[filing_status] - annual_non_ira_income, 0)`.
- `annual_conversion_amount` is the annual bracket-fill amount, capped by remaining traditional balance if needed.
- `total_converted = min(traditional_balance, annual_conversion_amount * pre_rmd_conversion_years)`.
- `conversion_years` is the available pre-RMD conversion window. `conversion_years_positive` is the count of years with an actual positive conversion after balance caps.
- `total_conversion_tax = total_converted * marginal_tax_rate`.

Projection convention: run baseline and conversion scenarios with the same yearly loop from planning year through horizon. At the start of each conversion year, move the planned amount from traditional IRA to Roth. If the year is at or after `first_rmd_year`, compute `RMD = traditional_balance / rmd_factor[age_that_year]`, tax it at the controlling marginal tax rate, and subtract it from traditional balance. Then grow remaining traditional and Roth balances by `expected_return`. RMD tax fields include RMD taxes only, not conversion taxes.

- `rmd_tax_savings_through_horizon = baseline_rmd_tax_through_horizon - conversion_rmd_tax_through_horizon`.
- Horizon Roth/traditional balances come from the conversion scenario.
- `heir_tax_profile`: `MOSTLY_TAX_FREE` if Roth is at least 75% of combined IRA value, `MIXED_TAXABLE_AND_TAX_FREE` if Roth is at least 25%, otherwise `MOSTLY_TAXABLE`.
- Recommendation: use `STAGED_ROTH_CONVERSION` when there is positive capacity, a pre-RMD window, and liquid assets cover the conversion tax. Use `DEFER` when the RMD window is too near or tax/liquidity tradeoffs are weak. Use `NO_CONVERSION` when there is no positive capacity or no traditional balance. Risk flag is `RMD_NEAR_TERM` for one or fewer pre-RMD years, `LIQUIDITY_CONSTRAINT` when conversion tax is not comfortably covered by liquid assets, otherwise `TAX_BRACKET_MANAGEMENT`.

## ILIT Crummey Funding

Use this for `analysis_type: ilit_crummey_implementation` and the ILIT portion of estate-liquidity plans.

- `annual_exclusion_per_beneficiary = annual_gift_exclusion[planning_year]`.
- `annual_exclusion_capacity = beneficiary_count * annual_exclusion_per_beneficiary`.
- `premium_gap = max(annual_premium - annual_exclusion_capacity, 0)`.
- `notices_required = beneficiary_count`.
- `dedicated_bank_account_required = true` when the policy owner is an ILIT.

If explicit administration dates are absent, use calendar days:

- `notice_due_date = contribution_date + 5 days`.
- `withdrawal_window_end = notice_due_date + 30 days`.
- `earliest_premium_payment_date = withdrawal_window_end + 1 day`.

Risk flags:

- Existing policy transfer only: `THREE_YEAR_LOOKBACK`.
- Premium exceeds annual exclusion capacity only: `EXCLUSION_SHORTFALL`.
- Both issues: `THREE_YEAR_LOOKBACK_AND_EXCLUSION_SHORTFALL`.
- Neither: `LOW_IF_FORMALITIES_MET`.

Map the same risk into `estate_result.estate_inclusion_risk` or `ilit.estate_inclusion_risk`. `projected_outside_estate_if_implemented` is the death benefit for an ILIT-owned policy, with lookback risk reported separately. `tax_liquidity_support = min(death_benefit, liquidity_gap_before_planning)`.

Recommended actions:

- No gap and no transfer: `FUND_WITH_CRUMMEY_NOTICES`, `SUITABLE_WITH_ADMINISTRATION`.
- Gap only: `USE_LIFETIME_EXEMPTION_FOR_SHORTFALL`, usually `BORDERLINE`.
- Transfer only: `USE_NEW_POLICY_OR_ACCEPT_LOOKBACK`, usually `BORDERLINE`.
- Gap plus transfer: `DISCLOSE_LOOKBACK_AND_USE_EXEMPTION`, usually `NOT_SUITABLE`.

## GRAT Versus CRAT

Use this for `analysis_type: trust_comparison` and trust-transfer sections.

Score goal strength as `low = 1`, `moderate = 2`, `high = 3`. Prefer `GRAT` when family-transfer priority is at least philanthropic intent; prefer `CRAT` only when philanthropic intent is stronger. Then set:

- GRAT recommendation: `rationale_code = CHILDREN_TRANSFER_PRIORITY`, `alternate_role = SECONDARY_CHARITABLE_TOOL`.
- CRAT recommendation: `rationale_code = PHILANTHROPIC_PRIORITY`, `alternate_role = SECONDARY_FAMILY_TRANSFER_TOOL`.

GRAT calculations:

- `projected_remainder_to_heirs = max(asset_value * ((1 + expected_growth_rate) ^ grat_term_years - (1 + grat_annuity_rate) ^ grat_term_years), 0)`.
- `estimated_estate_tax_reduction = projected_remainder_to_heirs * estate_tax_rate`.
- `mortality_inclusion_risk = TERM_SURVIVAL_REQUIRED`.

CRAT calculations:

- `crat_term_years = min(recorded_crat_term_years, max_crat_term_years)`.
- `projected_charitable_remainder = max(asset_value * (1 + expected_growth_rate - crat_payout_rate) ^ crat_term_years, 0)`.
- `estimated_income_tax_deduction = asset_value * charitable_deduction_rate`.
- `family_transfer_fit` is `LOW` when family-transfer priority is high, `MODERATE` when it is moderate, and `HIGH` only when family-transfer priority is low.

## Estate Liquidity Action Plans

Use this for `analysis_type: estate_liquidity_action_plan`. Reuse the shared estate context, ILIT, and trust-transfer calculations.

- `primary_action = COMBINE_ILIT_AND_GRAT` when ILIT liquidity is useful and GRAT is the preferred trust strategy.
- `primary_action = CRAT_WITH_LIQUIDITY_REVIEW` when CRAT is preferred because philanthropy dominates.
- `primary_action = ILIT_WITH_EXEMPTION_REVIEW` when ILIT funding or lookback issues dominate and trust transfer is secondary.
- Sequencing is `ILIT_FIRST_THEN_GRAT` for the combined ILIT/GRAT plan, `TRUST_DECISION_FIRST` for CRAT-led plans, and `ILIT_FIRST_THEN_ATTORNEY_REVIEW` for exemption or lookback-heavy ILIT plans.

Build `action_set` from applicable enums and sort alphabetically:

- Include `ILIT_CRUMMEY_NOTICE_CYCLE` when ILIT funding is part of the plan.
- Include `LIFETIME_EXEMPTION_ALLOCATION` when there is a premium gap or policy-transfer gift issue.
- Include `GRAT_FOR_APPRECIATING_SHARES` when GRAT is preferred.
- Include `CRAT_FOR_CHARITABLE_REMAINDER` when CRAT is preferred or is a meaningful secondary charitable tool.
- Include `ATTORNEY_DRAFT_REVIEW` for combined estate/trust plans, lookback issues, exemption allocation, or attorney coordination.

## Final JSON Checks

Before finalizing, validate against the answer template:

- Include every required top-level key and every requested nested field.
- Use only the enum values listed in the template.
- Keep booleans as booleans and numbers as numbers.
- Use ISO dates and cents-rounded USD values.
- Sort only fields with explicit ordering constraints, especially `action_set`.
- Return no prose, markdown, comments, or citations outside the JSON object.
