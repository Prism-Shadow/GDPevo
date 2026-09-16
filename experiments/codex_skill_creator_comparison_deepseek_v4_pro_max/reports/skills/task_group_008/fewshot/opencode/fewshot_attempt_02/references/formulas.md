# Computation Formulas

All numeric outputs can be computed deterministically from API data. Use the bundled [scripts/compute.py](../scripts/compute.py) script, passing it the relevant parameters as a JSON argument. The script handles the iterative year-by-year projection and returns JSON with all needed numeric fields.

## Roth Conversion and RMD

### Conversion plan

- `annual_conversion_amount` = `bracket_target` - `annual_non_ira_income`
  - `bracket_target` comes from tax policies `conversion_bracket_targets[filing_status]`
  - `annual_non_ira_income` comes from the controlling profile source
  - If this value would exceed `traditional_balance / conversion_years`, cap it
- `conversion_years` = `recommended_conversion_years` from retirement account
- `conversion_years_positive` = `conversion_years` (same value)
- `total_converted` = `annual_conversion_amount` * `conversion_years`
- `total_conversion_tax` = `total_converted` * `marginal_tax_rate`

### RMD projection

- `horizon_year` = from request memo
- `first_rmd_year` = `planning_year` + (`rmd_start_age` - `age`)

**Baseline (no conversions):**

The traditional balance grows each year at `expected_return`. Starting at `first_rmd_year`, take annual RMDs and tax them at `marginal_tax_rate`.

RMD computation per year:
1. Start with traditional balance at beginning of year
2. RMD = balance / divisor for that age (from RMD factors table)
3. Tax on RMD = RMD * marginal_tax_rate
4. Balance after RMD = balance - RMD
5. Balance grows by (1 + expected_return) to next year

Baseline RMD tax = sum of all RMD taxes from first_rmd_year through horizon_year.

**Conversion scenario:**

The traditional balance is reduced by `annual_conversion_amount` each conversion year before growth and RMD computation. The Roth balance grows from its starting value plus each year's conversion amount.
When conversion years and RMD years overlap (client near RMD age), apply conversion first, then RMD, then growth.

Conversion RMD tax = sum of all RMD taxes under the conversion scenario from first_rmd_year through horizon_year.

- `baseline_rmd_tax_through_horizon` = baseline RMD tax sum
- `conversion_rmd_tax_through_horizon` = conversion RMD tax sum
- `rmd_tax_savings_through_horizon` = baseline - conversion

### Legacy projection

- `projected_roth_balance_horizon` = Roth balance at end of horizon_year under conversion scenario
- `projected_traditional_balance_horizon` = Traditional balance at end of horizon_year under conversion scenario

## ILIT Crummey Funding

### Gift plan

- `planning_year` = planning year from client record
- `annual_exclusion_per_beneficiary` = from tax policies `annual_gift_exclusion[planning_year]`
- `beneficiary_count` = from controlling profile source
- `annual_exclusion_capacity` = `annual_exclusion_per_beneficiary` * `beneficiary_count`
- `annual_premium` = from life insurance policy
- `premium_gap` = max(0, `annual_premium` - `annual_exclusion_capacity`)

### Administration

- `notices_required` = `beneficiary_count` (one Crummey notice per beneficiary)
- `contribution_date` = `planned_contribution_date` from life insurance policy
- `notice_due_date` = `contribution_date` + 7 days
- `withdrawal_window_end` = `contribution_date` + 30 days (Crummey withdrawal right window)
- `earliest_premium_payment_date` = `withdrawal_window_end` + 1 day
- `dedicated_bank_account_required` = `true` (best practice for ILIT administration)

### Estate result

- `death_benefit` = from life insurance policy
- `tax_liquidity_support` = `death_benefit` * `estate_tax_rate`
- `projected_outside_estate_if_implemented` = `death_benefit` (ILIT keeps policy outside taxable estate)

## Trust Comparison (GRAT vs CRAT)

### Estate context

- `planning_year` = from client record
- `exemption_used` = `estate_tax_exemption` for `planning_year` from tax policies
- `taxable_estate` = `estate_value` - `exemption_used` (floor at 0)
- `estate_tax_exposure` = `taxable_estate` * `estate_tax_rate`
- `liquid_assets_available` = `liquid_assets` from client record
- `liquidity_gap_before_planning` = max(0, `estate_tax_exposure` - `liquid_assets_available`)

### GRAT

- `term_years` = `grat_term_years` from trust candidate
- `projected_remainder_to_heirs` = `asset_value` * (1 + `expected_growth_rate`)^`term_years` - `asset_value` * `grat_annuity_rate` * `term_years`
- `estimated_estate_tax_reduction` = `projected_remainder_to_heirs` * `estate_tax_rate`

### CRAT

- `term_years` = `crat_term_years` from trust candidate
- `projected_charitable_remainder` = `asset_value` * (1 + `expected_growth_rate`)^`term_years` - `asset_value` * `crat_payout_rate` * `term_years`
- `estimated_income_tax_deduction` = `projected_charitable_remainder` * `charitable_deduction_rate`

## Estate Liquidity Action Plan

### Estate context

Same as trust comparison estate context.

### ILIT

- `annual_exclusion_capacity` = `annual_exclusion_per_beneficiary` * `beneficiary_count`
- `premium_gap` = max(0, `annual_premium` - `annual_exclusion_capacity`)
- `projected_outside_estate_if_implemented` = `death_benefit`

### Trust transfer

Same as trust comparison GRAT/CRAT fields, using trust candidate data.
- `projected_charitable_remainder` = CRAT computation (always included even if GRAT is preferred)
