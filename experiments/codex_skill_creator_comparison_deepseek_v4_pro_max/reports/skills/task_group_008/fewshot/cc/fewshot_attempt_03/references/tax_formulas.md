# Tax and Planning Formulas

All amounts are in USD, rounded to two decimal places. Use standard Python
`round(x, 2)` semantics.

## Constants

Fetch once from `GET /api/policies/tax`:

- `annual_gift_exclusion` — keyed by year (e.g. `"2026": 20000`). Use the
  planning year's value.
- `estate_tax_exemption` — keyed by year. Use the planning year's value.
- `estate_tax_rate` — flat rate (e.g. 0.4).
- `conversion_bracket_targets` — keyed by filing status (`"MFJ"`, `"SINGLE"`,
  `"HOH"`). This is the top of the target bracket for Roth conversions.
- `max_crat_term_years` — maximum CRAT term.
- `charitable_deduction_rate` — rate for charitable deduction from CRAT
  remainder.

RMD divisor factors from `GET /api/rmd-factors` are keyed by age as strings
(e.g. `"73": 26.5`).

## Roth conversion RMD analysis (`roth_conversion_rmd`)

### Inputs

From client profile (resolved source): `annual_non_ira_income`,
`marginal_tax_rate`, `age`, `filing_status`, `planning_year`.

From tax policies: `conversion_bracket_targets[filing_status]`.

From retirement account: `traditional_balance`, `roth_balance`,
`expected_return`, `rmd_start_age`, `recommended_conversion_years`.

From request memo: `horizon_year` (if specified; otherwise `planning_year + 20`).

### Conversion plan

1. **annual_conversion_amount** = `conversion_bracket_target` – `annual_non_ira_income`
   Round to cents. If non-positive, the conversion is not viable.

2. **conversion_years** = `recommended_conversion_years` (from the custodian export).

3. **conversion_years_positive** = same as `conversion_years` (the number of years
   in which conversions actually occur).

4. **first_conversion_year** = `planning_year`.

5. **total_converted** = `annual_conversion_amount` × `conversion_years`.

6. **total_conversion_tax** = `total_converted` × `marginal_tax_rate`.

### RMD projection

**First RMD year** = `planning_year` + (`rmd_start_age` – `age`).

#### Baseline (no conversions)

1. Start with `traditional_balance`.
2. Grow each year from `planning_year` to `first_rmd_year – 1`: multiply by
   `(1 + expected_return)`.
3. For each year from `first_rmd_year` through `horizon_year`:
   - `rmd` = `balance` / `rmd_factor` for that age.
   - `tax_on_rmd` = `rmd` × `marginal_tax_rate`.
   - Accumulate `baseline_rmd_tax_through_horizon`.
   - `balance` = (`balance` – `rmd`) × `(1 + expected_return)`.

The age for each RMD year is `age + (year – planning_year)`.

#### With conversions

1. Start with `traditional_balance`.
2. For each year from `planning_year` through `horizon_year`:
   a. **If within the conversion window** (year < `planning_year + conversion_years`):
      `balance` = `balance` – `annual_conversion_amount`.
   b. **If within the RMD window** (year ≥ `first_rmd_year`):
      - `rmd` = `balance` / `rmd_factor` for the current age.
      - `conv_rmd_tax` += `rmd` × `marginal_tax_rate`.
      - `balance` = `balance` – `rmd`.
   c. `balance` = `balance` × `(1 + expected_return)`.
3. Accumulate `conversion_rmd_tax_through_horizon`.

**rmd_tax_savings_through_horizon** = `baseline_rmd_tax_through_horizon` –
`conversion_rmd_tax_through_horizon`.

### Legacy projection

1. **Roth balance at horizon**: start with `roth_balance`. For each conversion
   year, add `annual_conversion_amount` then grow by `(1 + expected_return)`.
   After the conversion period, grow each year through `horizon_year`.

2. **Traditional balance at horizon**: this is the final `balance` value
   from the "with conversions" RMD projection at the end of `horizon_year`.

**heir_tax_profile**:
- `MOSTLY_TAX_FREE` when Roth at horizon > 3 × Traditional at horizon.
- `MOSTLY_TAXABLE` when Traditional at horizon > 3 × Roth at horizon.
- `MIXED_TAXABLE_AND_TAX_FREE` otherwise.

## ILIT Crummey implementation (`ilit_crummey_implementation`)

### Inputs

From client profile: `beneficiary_count`, `planning_year`.
From tax policies: `annual_gift_exclusion[planning_year]`.
From life insurance: `death_benefit`, `annual_premium`,
`planned_contribution_date`, `is_existing_policy_transfer`.

### Gift plan

1. **annual_exclusion_per_beneficiary** = `annual_gift_exclusion[planning_year]`.
2. **beneficiary_count** as resolved from source documents.
3. **annual_exclusion_capacity** = `annual_exclusion_per_beneficiary` ×
   `beneficiary_count`.
4. **annual_premium** from policy record.
5. **premium_gap** = `max(0, annual_premium – annual_exclusion_capacity)`.
   If capacity exceeds premium, gap = 0.

### Administration dates

Compute from `planned_contribution_date` as an ISO date string:

- `contribution_date` = `planned_contribution_date`.
- `notice_due_date` = contribution + 7 calendar days.
- `withdrawal_window_end` = contribution + 30 calendar days.
- `earliest_premium_payment_date` = withdrawal_window_end + 1 calendar day.

Use Python `datetime` or equivalent to add days correctly.

`notices_required` = `beneficiary_count`.

`dedicated_bank_account_required` = `true`.

### Estate result

- `death_benefit` from policy record.
- `estate_inclusion_risk`: same logic as `recommendation.risk_flag`.
- `projected_outside_estate_if_implemented` = `death_benefit` when formalities
  are met (full exclusion).
- `tax_liquidity_support` = `death_benefit` × `estate_tax_rate`.

## Trust comparison (`trust_comparison`)

### Inputs

From client profile: `estate_value`, `liquid_assets`, `philanthropic_intent`,
`family_transfer_priority`.

From tax policies: `estate_tax_rate`, `estate_tax_exemption[planning_year]`,
`charitable_deduction_rate`.

From trust candidate: `asset_value`, `expected_growth_rate`, `grat_term_years`,
`grat_annuity_rate`, `crat_term_years`, `crat_payout_rate`.

### Estate context

- **taxable_estate** = `max(0, estate_value – effective_exemption)`.
  The `effective_exemption` is `estate_tax_exemption[planning_year]` for SINGLE/HOH
  filers and `2 × estate_tax_exemption[planning_year]` for MFJ filers.
  Use the client's `filing_status` to determine whether to double the exemption.
- **estate_tax_exposure** = `taxable_estate` × `estate_tax_rate`.
- **liquidity_gap_before_planning** = `max(0, estate_tax_exposure – liquid_assets)`.

Include additional context fields from the answer template when present:
`planning_year`, `exemption_used`, `liquid_assets_available`.

### GRAT

1. **projected_remainder_to_heirs** = `asset_value` ×
   `(1 + expected_growth_rate)^grat_term_years` –
   `asset_value` × `grat_annuity_rate` × `grat_term_years`.
   Round to cents.

2. **estimated_estate_tax_reduction** = `projected_remainder_to_heirs` ×
   `estate_tax_rate`. Round to cents.

3. **mortality_inclusion_risk** = `"TERM_SURVIVAL_REQUIRED"` (standard GRAT
   property).

### CRAT

1. **projected_charitable_remainder** = `asset_value` ×
   `(1 + expected_growth_rate)^crat_term_years` –
   `asset_value` × `crat_payout_rate` × `crat_term_years`.
   Round to cents.

2. **estimated_income_tax_deduction** = `projected_charitable_remainder` ×
   `charitable_deduction_rate`. Round to cents.

## Estate liquidity action plan (`estate_liquidity_action_plan`)

This combines ILIT and trust comparison computations.

### Estate context

Same as trust comparison (with MFJ exemption doubling): `taxable_estate`, `estate_tax_exposure`,
`liquidity_gap_before_planning`. Include `planning_year`, `exemption_used`,
and `liquid_assets_available` when the template requires them.

### ILIT block

Compute as in the ILIT section:
- `annual_exclusion_capacity`
- `premium_gap`
- `estate_inclusion_risk`
- `projected_outside_estate_if_implemented` = `death_benefit`.

### Trust transfer block

- `preferred_strategy`: choose between `GRAT` and `CRAT` using the same logic
  as trust comparison.
- Compute `projected_remainder_to_heirs`, `estimated_estate_tax_reduction`,
  and `projected_charitable_remainder` using the trust candidate formulas above.

### action_set

Build a list of applicable action enums, then sort alphabetically:

- Include `ILIT_CRUMMEY_NOTICE_CYCLE` when an ILIT policy is present.
- Include `GRAT_FOR_APPRECIATING_SHARES` when preferred strategy is `GRAT`.
- Include `CRAT_FOR_CHARITABLE_REMAINDER` when preferred strategy is `CRAT`.
- Include `LIFETIME_EXEMPTION_ALLOCATION` when `premium_gap` > 0 or when
  `taxable_estate` > 0 and a trust transfer absorbs some exposure.
- Include `ATTORNEY_DRAFT_REVIEW` always (standard for attorney coordination
  meetings).
