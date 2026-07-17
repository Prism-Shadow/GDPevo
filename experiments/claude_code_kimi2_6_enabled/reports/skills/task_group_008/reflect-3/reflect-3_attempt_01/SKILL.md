# Estate and Tax Planning Computation Skill

## Overview

Tasks in this family require computing detailed financial projections for estate planning, tax optimization, and wealth transfer strategies. Each task involves reading a client request memo, performing calculations based on the provided financial data, and producing a structured JSON answer matching a specific template.

## General Approach

1. **Parse the request memo carefully**: Extract all numerical values (ages, balances, rates, premiums, beneficiary counts, dates, tax brackets).
2. **Identify the analysis type**: This determines which set of calculations and enums apply.
3. **Compute all required fields**: Use the formulas and rules documented below.
4. **Resolve source priorities**: Determine the most authoritative source for each data type.
5. **Validate enum values**: Ensure all enum fields use exact allowed values.
6. **Format numbers correctly**: Use JSON numbers (not strings), rounded to cents (2 decimal places). Dates must be ISO `YYYY-MM-DD`.

## Analysis Types and Rules

### 1. Roth Conversion RMD (`roth_conversion_rmd`)

**Key Parameters**
- Current year is implied by memo date (typically 2024).
- RMD start age: **73** for clients born 1951–1959 (SECURE 2.0). Verify by computing: `RMD_year = birth_year + 73`.
- Horizon year: `birth_year + horizon_age`.
- Conversion period: from current year through the year the client turns the specified max age.

**Calculations**
- `conversion_years`: Number of calendar years from current year through max conversion age year, inclusive.
- `conversion_years_positive`: Same as `conversion_years` (all years have positive conversion amounts).
- `annual_conversion_amount`: Typically `initial_traditional_balance / conversion_years`, unless a specific target is stated. Include annual contributions in account growth projections.
- `total_converted`: `annual_conversion_amount × conversion_years`.
- `total_conversion_tax`: `total_converted × current_tax_bracket`.
- Account growth: Apply expected return to beginning balance, then add annual contribution, then subtract conversion.
- RMD baseline (no conversion): Project account growth without conversion; compute RMDs from RMD start age through horizon using the IRS Uniform Lifetime Table.
- `baseline_rmd_tax_through_horizon`: Sum of RMDs × tax bracket without conversion.
- `conversion_rmd_tax_through_horizon`: Sum of RMDs × tax bracket with conversion.
- `rmd_tax_savings_through_horizon`: `baseline_rmd_tax − conversion_rmd_tax`.
- `projected_roth_balance_horizon`: Cumulative converted amounts grown at expected return through horizon.
- `projected_traditional_balance_horizon`: Remaining traditional balance at horizon after conversions and RMDs.

**Recommendation**
- `primary_action`: Usually `STAGED_ROTH_CONVERSION` if the client explicitly requests systematic conversion.
- `suitability`: `SUITABLE` when heirs are in a higher tax bracket and no liquidity constraints exist; `BORDERLINE` or `DEFER` otherwise.
- `risk_flag`: `TAX_BRACKET_MANAGEMENT` when the main consideration is current vs. heir tax rates; `RMD_NEAR_TERM` when RMDs start within ~5 years; `LIQUIDITY_CONSTRAINT` when conversion taxes would impair cash flow.

**IRS Uniform Lifetime Table (key ages)**
- 73: 26.5, 74: 25.5, 75: 24.6, 76: 23.7, 77: 22.9, 78: 22.0, 79: 21.1, 80: 20.2

### 2. ILIT Crummey Implementation (`ilit_crummey_implementation`)

**Key Parameters**
- Annual gift exclusion: **$18,000 per beneficiary** (2024 amount).
- `annual_exclusion_capacity`: `$18,000 × beneficiary_count`.
- `premium_gap`: `annual_premium − annual_exclusion_capacity` (zero if negative).

**Calculations**
- `notices_required`: Equal to `beneficiary_count` (one Crummey notice per beneficiary per contribution).
- `contribution_date`: Typically the ILIT creation date or policy anniversary in the planning year.
- `notice_due_date`: `contribution_date + 30 days` (Crummey notices must be sent promptly, usually within 30 days).
- `withdrawal_window_end`: Same as or shortly after `notice_due_date` (typically 30-day window).
- `earliest_premium_payment_date`: Same as or shortly after `contribution_date`.
- `dedicated_bank_account_required`: `true` (best practice for ILIT administration).

**Recommendation**
- `primary_action`:
  - `FUND_WITH_CRUMMEY_NOTICES` if premium ≤ exclusion capacity.
  - `USE_LIFETIME_EXEMPTION_FOR_SHORTFALL` if there is a premium gap and the client has exemption available.
- `suitability`: `SUITABLE_WITH_ADMINISTRATION` when formalities (notices, bank account) can be maintained; `BORDERLINE` or `NOT_SUITABLE` otherwise.
- `risk_flag`: `EXCLUSION_SHORTFALL` when premium exceeds exclusion capacity; `LOW_IF_FORMALITIES_MET` when everything fits; `THREE_YEAR_LOOKBACK` only if the client has made prior transfers subject to lookback.

**Estate Result**
- `projected_outside_estate_if_implemented`: Full death benefit (ILIT removes insurance from estate).
- `estate_inclusion_risk`: Same as `recommendation.risk_flag`.
- `tax_liquidity_support`: Usually `0.00` or the death benefit amount depending on whether the death benefit is considered available for estate tax liquidity. When the ILIT is properly structured, the death benefit is outside the estate and does not directly pay estate taxes, so `0.00` is often appropriate unless the prompt explicitly frames it as providing family liquidity.

### 3. Trust Comparison (`trust_comparison`)

**Key Parameters**
- GRAT and CRAT are compared using the same funding amount, term, and growth assumptions.
- IRS 7520 rate is given; use it for annuity factor and present value calculations.

**GRAT Calculations**
- Annuity factor: `(1 − (1 + 7520_rate)^−term) / 7520_rate`.
- Annuity payment: `funding_amount / annuity_factor`.
- Project remainder year-by-year: `balance = balance × (1 + growth_rate) − annuity`.
- `projected_remainder_to_heirs`: Final balance after term.
- `estimated_estate_tax_reduction`: `projected_remainder_to_heirs × 0.40` (40% federal estate tax rate).
- `mortality_inclusion_risk`: `TERM_SURVIVAL_REQUIRED` (grantor must outlive the GRAT term).

**CRAT Calculations**
- Payout: `funding_amount × payout_percentage` (e.g., 5%).
- Project remainder: `balance = balance × (1 + growth_rate) − annual_payout`.
- `projected_charitable_remainder`: Final balance after term.
- `estimated_income_tax_deduction`: Approximate present value of charitable remainder at the 7520 rate. Simplified: `funding_amount − (annual_payout × annuity_factor_at_7520_rate)`.
- `family_transfer_fit`: `LOW` for CRAT (charity gets remainder, not family).

**Recommendation**
- `preferred_strategy`: `GRAT` when family/children are the priority; `CRAT` when charitable giving is primary.
- `rationale_code`: `CHILDREN_TRANSFER_PRIORITY` or `PHILANTHROPIC_PRIORITY` matching the primary goal.
- `alternate_role`: `SECONDARY_CHARITABLE_TOOL` for CRAT when GRAT is primary; `SECONDARY_FAMILY_TRANSFER_TOOL` for GRAT when CRAT is primary.

### 4. Estate Liquidity Action Plan (`estate_liquidity_action_plan`)

**Key Parameters**
- Combines ILIT, GRAT/CRAT, and estate tax/liquidity analysis.
- `action_set`: Must be a list of enums sorted **alphabetically**.

**ILIT Section**
- Same calculations as ILIT Crummey analysis.
- `annual_exclusion_capacity`, `premium_gap`, `estate_inclusion_risk`, `projected_outside_estate_if_implemented`.

**Trust Transfer Section**
- Same GRAT/CRAT calculations as Trust Comparison.
- `preferred_strategy`: `GRAT` for family priority, `CRAT` for charitable priority.
- `projected_remainder_to_heirs`, `estimated_estate_tax_reduction`: GRAT outputs.
- `projected_charitable_remainder`: CRAT output.

**Recommendation**
- `primary_action`:
  - `COMBINE_ILIT_AND_GRAT` when both life insurance liquidity and family wealth transfer are goals.
  - `CRAT_WITH_LIQUIDITY_REVIEW` when charitable remainder is primary.
  - `ILIT_WITH_EXEMPTION_REVIEW` when insurance/estate liquidity is the main focus.
- `sequencing`: `ILIT_FIRST_THEN_GRAT` when insurance funding precedes trust setup; `TRUST_DECISION_FIRST` when trust structure drives the plan; `ILIT_FIRST_THEN_ATTORNEY_REVIEW` when legal review is needed after initial ILIT funding.

## Source Resolution Rules

Source fields are heavily scored. Apply these heuristics:

- **Controlling profile/beneficiary/goal source**: Use `SIGNED_PROFILE` when a signed client profile is the most recent and authoritative source. Use `ATTORNEY_MEMO` when legal documents override. Use `CUSTODIAN_EXPORT` for account-level data. Use `CRM_NOTE` for informal updates. Use `STALE_MARKETING_INTAKE` only when no better source exists.
- **Controlling account/asset/policy source**: Use `CUSTODIAN_EXPORT` for account balances and holdings (most recent statement). Use `SIGNED_PROFILE` only if no custodian data is available. Use `ATTORNEY_MEMO` for trust-owned assets.
- **Recency matters**: A custodian statement from April 2024 beats a signed profile from March 2024 for account data. A signed profile from March 2024 beats a stale marketing intake.
- **Hierarchy** (from most to least authoritative): `SIGNED_PROFILE` ≈ `ATTORNEY_MEMO` > `CUSTODIAN_EXPORT` > `CRM_NOTE` > `STALE_MARKETING_INTAKE`.

## Common Pitfalls

- **Do not use strings for numbers**: All monetary amounts and counts must be JSON numbers, not strings.
- **Round to cents**: Use 2 decimal places for USD amounts (e.g., `54000.00`).
- **ISO dates**: Administration dates must be `YYYY-MM-DD`.
- **Sort action_set alphabetically**: For `estate_liquidity_action_plan`, the `action_set` list must be sorted alphabetically.
- **Enum exactness**: Use exact enum strings. Common valid values include:
  - `recommendation.suitability`: `SUITABLE`, `BORDERLINE`, `DEFER`, `SUITABLE_WITH_ADMINISTRATION`, `NOT_SUITABLE`
  - `recommendation.risk_flag`: `TAX_BRACKET_MANAGEMENT`, `LIQUIDITY_CONSTRAINT`, `RMD_NEAR_TERM`, `LOW_IF_FORMALITIES_MET`, `EXCLUSION_SHORTFALL`, `THREE_YEAR_LOOKBACK`, `THREE_YEAR_LOOKBACK_AND_EXCLUSION_SHORTFALL`
  - `heir_tax_profile`: `MOSTLY_TAX_FREE`, `MIXED_TAXABLE_AND_TAX_FREE`, `MOSTLY_TAXABLE`
- **Use the correct task_id**: Must match the input task identifier exactly (e.g., `train_001`, `test_001`).
- **RMD age verification**: Always verify the client's birth year against current RMD rules. Do not assume RMD age 72 for clients born after 1950.
- **Annual exclusion amount**: Use the correct year’s amount. For 2024, it is $18,000 per beneficiary.
- **Estate tax rate**: Federal estate tax rate above exemption is 40% unless the prompt specifies otherwise.
