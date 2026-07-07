# Skill: Roth Conversion RMD Analysis for Wealth Advisory

## Overview
Generate a structured JSON comparison of Roth conversion versus RMD baseline for a private-wealth advisory client. The procedure queries an advisory API, resolves conflicting multi-source records, projects taxes and balances through a planning-horizon year, and produces a recommendation.

## API Usage
1. Obtain the advisory API base URL from the environment (commonly exposed as `API_BASE` after the shared environment starts).
2. Query all relevant endpoints for the given `client_id`:
   - Client profile and demographics
   - Account holdings and custodian exports
   - Tax-policy constants (brackets, rates, thresholds)
   - RMD factors / uniform lifetime table
   - Any source documents, life-insurance records, or trust candidates
3. Conflicts are expected because records were imported from different systems. Keep every source value and its provenance tag for resolution.

## Source Resolution Rules
Apply these hierarchies **before** using any data in calculations.

- **Profile / demographic data** (highest priority first):
  1. `SIGNED_PROFILE`
  2. `ATTORNEY_MEMO`
  3. `CUSTODIAN_EXPORT`
  4. `CRM_NOTE`
  5. `STALE_MARKETING_INTAKE`
- **Account / balance data** (highest priority first):
  1. `CUSTODIAN_EXPORT`
  2. `SIGNED_PROFILE`
  3. `CRM_NOTE`

Report the winning source tags in:
- `source_resolution.controlling_profile_source`
- `source_resolution.controlling_account_source`

## Analysis Steps

### 1. Anchor dates and horizon
- `client_id` and the **planning horizon year** come from the advisor request memo.
- Determine the client’s birth year / age from the resolved profile.
- Compute the **first RMD year** using the resolved tax-policy constants (e.g., SECURE 2.0 rules: age 73 for birth years 1951–1959, age 75 for 1960+).

### 2. Baseline scenario (no conversion)
- Project the resolved traditional retirement-account balance forward year by year through the horizon.
- Starting in the first RMD year, apply the applicable RMD factor each year to determine the required distribution.
- Tax each distribution using the resolved ordinary-income brackets.
- Accumulate the taxes → `baseline_rmd_tax_through_horizon`.

### 3. Conversion scenario
- If the memo explicitly states **"no conversion is requested"** (or the client is clearly unsuitable), set all conversion amounts to `0` and skip to step 5, but still keep any baseline plan years in `conversion_plan` with zeroed amounts.
- Otherwise, build a **staged conversion plan**:
  - `first_conversion_year` is normally the current / next year.
  - `conversion_years` is the count of years over which conversions are spread.
  - `conversion_years_positive` equals `conversion_years` when conversion is positive; in no-conversion cases it may match the planned window but amounts must be `0`.
  - `annual_conversion_amount` = `total_converted / conversion_years`, rounded to cents.
  - `total_conversion_tax` = sum of tax on each year’s converted amount, rounded to cents.
- After removing converted amounts, reproject the remaining traditional balance and its yearly RMDs.
- Accumulate post-conversion RMD taxes → `conversion_rmd_tax_through_horizon`.

### 4. Savings and legacy projection
- `rmd_tax_savings_through_horizon` = `baseline_rmd_tax_through_horizon - conversion_rmd_tax_through_horizon`.
  - Allow a one-cent tolerance because intermediate year-by-year rounding can propagate.
- Project the Roth balance at horizon by growing the converted amounts.
- Project the remaining traditional balance at horizon.
- Set `heir_tax_profile`:
  - `MOSTLY_TAXABLE` when the Roth balance is negligible (e.g., no conversion occurred).
  - `MIXED_TAXABLE_AND_TAX_FREE` when both Roth and traditional balances are materially positive.
  - `MOSTLY_TAX_FREE` when the traditional balance is negligible.

### 5. Recommendation
- `primary_action`:
  - `NO_CONVERSION` when the memo explicitly says no conversion is requested, or when analysis shows conversion is unsuitable.
  - `STAGED_ROTH_CONVERSION` otherwise.
- `suitability`:
  - `SUITABLE` for staged conversions.
  - `DEFER` for no-conversion recommendations.
- `risk_flag` (choose the best fit):
  - `TAX_BRACKET_MANAGEMENT` — default for most staged conversions where the main concern is staying within favorable brackets.
  - `LIQUIDITY_CONSTRAINT` — when the conversion period is long or the client has liquidity concerns.
  - `RMD_NEAR_TERM` — when the reason to defer is unfavorable RMD timing (e.g., conversion would start after RMDs have already begun and the analysis recommends no conversion).

## Output Format
- Return **only** a single JSON object. No markdown fences, no explanatory prose outside the JSON.
- Required top-level keys (order does not matter):
  - `task_id`, `client_id`, `analysis_type`, `recommendation`, `conversion_plan`, `rmd_projection`, `legacy_projection`, `source_resolution`
- `task_id`: use the task identifier supplied by the harness (e.g., `train_001`, `test_001`).
- `client_id`: from the memo.
- `analysis_type`: always `"roth_conversion_rmd"`.
- All monetary values must be JSON **numbers** (not strings), rounded to exactly two decimal places (cents).
- All years must be JSON integer numbers.
- Enum strings must match the template exactly (all caps with underscores).

## Calculation Checks
- `annual_conversion_amount × conversion_years` should equal `total_converted` (within rounding).
- `baseline_rmd_tax_through_horizon - conversion_rmd_tax_through_horizon` should equal `rmd_tax_savings_through_horizon` (within rounding).
- In a no-conversion case:
  - `total_converted = 0`
  - `total_conversion_tax = 0`
  - `rmd_tax_savings_through_horizon = 0`
  - `baseline_rmd_tax_through_horizon` should equal `conversion_rmd_tax_through_horizon`
  - `annual_conversion_amount = 0`
- Ensure `conversion_years_positive` is consistent with the sign of `annual_conversion_amount`.

## Pitfalls
- **Conflicting sources:** Never blindly use the first record returned. Always apply the source-resolution hierarchy.
- **Numeric types:** Outputting `"1234.56"` (a string) instead of `1234.56` (a number) will fail validation.
- **Horizon year:** It comes from the memo, not from a hard-coded default.
- **RMD age rules:** Use the API’s tax-policy constants if available; do not hard-code outdated RMD ages.
- **No-conversion edge case:** Even when the recommendation is `NO_CONVERSION`, the `conversion_plan` object may still contain a `first_conversion_year` and `conversion_years` describing the theoretical window, but all monetary fields must be zero.
- **One-cent rounding drift:** When summing year-by-year taxes, carry cents each year or round only the final total; if you round every year independently, a 1-cent discrepancy in `rmd_tax_savings_through_horizon` is possible and acceptable.
