# Analysis Type Procedures

Each analysis type has a specific set of fields and calculations.  Match the
analysis_type from the answer template and follow the corresponding procedure.

---

## roth_conversion_rmd

Used for: Roth conversion planning with RMD projections and legacy estimates.

### Data Sources

- Client record or signed profile for age, filing_status, marginal_tax_rate
- Retirement account for traditional_balance, roth_balance, expected_return,
  rmd_start_age, recommended_conversion_years
- Tax policy for conversion_bracket_targets[filing_status], estate_tax_rate
- RMD factors table

### Calculations

**Conversion plan:**

- `first_conversion_year` = client's `planning_year` (2026 in evidence)
- `conversion_years` = `recommended_conversion_years` from the retirement
  account record
- `conversion_years_positive` = same as `conversion_years`
- `annual_conversion_amount` = `conversion_bracket_targets[filing_status]`
  for the client's filing status, rounded to cents
- `total_converted` = `annual_conversion_amount` * `conversion_years`,
  rounded to cents
- `total_conversion_tax` = `total_converted` * `marginal_tax_rate`,
  rounded to cents

**RMD projection:**

Given a `horizon_year` from the request memo:

- `first_rmd_year` = `planning_year` + (`rmd_start_age` - client age)
- For each year from `first_rmd_year` through `horizon_year`, compute RMD:

  **Baseline (no conversion):**

  Start with `baseline_balance` = `traditional_balance`.
  For each year from `planning_year` through `horizon_year`:

  1. Grow balance: `balance *= (1 + expected_return)`
  2. If year is before `first_rmd_year`, skip RMD.
  3. If year >= `first_rmd_year`:
     - client_age_in_year = client_age + (year - planning_year)
     - factor = rmd_factors[str(client_age_in_year)]
     - rmd = balance / factor
     - balance -= rmd
     - rmd_tax = rmd * marginal_tax_rate
     - Accumulate `baseline_rmd_tax_through_horizon` += rmd_tax

  **With conversion (same growth, but deduct conversions first):**

  Start with `conversion_balance` = `traditional_balance`.
  For each conversion year (first_conversion_year through
  first_conversion_year + conversion_years - 1):

  1. Grow balance: `balance *= (1 + expected_return)`
  2. Deduct conversion: `balance -= annual_conversion_amount`
  3. Also accrue the converted amount into a Roth balance tracker:

     `roth_balance += annual_conversion_amount`
     `roth_balance *= (1 + expected_return)` (grow Roth each year)

  After conversion years end, continue growing both balances and
  computing RMDs on the traditional balance exactly as in baseline.

  Accumulate `conversion_rmd_tax_through_horizon` the same way.

- `rmd_tax_savings_through_horizon` =
  `baseline_rmd_tax_through_horizon` - `conversion_rmd_tax_through_horizon`,
  rounded to cents

**Legacy projection:**

- `projected_roth_balance_horizon` = final Roth balance at horizon_year
  (initial roth_balance grown plus converted amounts grown)
- `projected_traditional_balance_horizon` = final traditional balance at
  horizon_year after all RMDs (conversion scenario)
- `heir_tax_profile`:
  - `MOSTLY_TAX_FREE` if projected_roth_balance_horizon >
    projected_traditional_balance_horizon by a clear margin
  - `MOSTLY_TAXABLE` if traditional dominates
  - `MIXED_TAXABLE_AND_TAX_FREE` otherwise

**Recommendation:**

- `primary_action`: `STAGED_ROTH_CONVERSION` when conversion makes sense
  (positive savings), `DEFER` when near-term RMDs make conversion less
  beneficial, `NO_CONVERSION` when conversion adds no value.
- `suitability`: `SUITABLE` when strongly beneficial, `BORDERLINE` when
  marginal, `DEFER` when better to wait.
- `risk_flag`: `TAX_BRACKET_MANAGEMENT` when conversion size is driven by
  bracket targets, `LIQUIDITY_CONSTRAINT` when liquid assets are tight,
  `RMD_NEAR_TERM` when RMDs start within 1-2 years.

---

## ilit_crummey_implementation

Used for: ILIT funding-cycle checks with Crummey notice administration.

### Data Sources

- Client record / signed profile for age, beneficiary_count, marginal_tax_rate
- Life-insurance policy for death_benefit, annual_premium,
  planned_contribution_date, is_existing_policy_transfer
- Tax policy for annual_gift_exclusion[planning_year_str]

### Calculations

**Gift plan:**

- `planning_year` = client's planning_year
- `annual_exclusion_per_beneficiary` = annual_gift_exclusion[str(planning_year)]
- `beneficiary_count` = from the controlling source document
- `annual_exclusion_capacity` = `annual_exclusion_per_beneficiary` *
  `beneficiary_count`, rounded to cents
- `annual_premium` = from the life-insurance policy
- `premium_gap` = max(0, `annual_premium` - `annual_exclusion_capacity`),
  rounded to cents.  If annual_premium <= annual_exclusion_capacity, gap is 0.

**Administration:**

- `notices_required` = `beneficiary_count`
- `contribution_date` = `planned_contribution_date` from the policy
- `notice_due_date` = `contribution_date` + 7 calendar days
- `withdrawal_window_end` = `contribution_date` + 37 calendar days
  (the standard Crummey window)
- `earliest_premium_payment_date` = `withdrawal_window_end` + 1 day
- `dedicated_bank_account_required` = true (always in the evidence)

**Estate result:**

- `death_benefit` = from the life-insurance policy
- `estate_inclusion_risk`:
  - `LOW_IF_FORMALITIES_MET` if `is_existing_policy_transfer` is false
    and premiums fit within exclusion capacity
  - `EXCLUSION_SHORTFALL` if premium_gap > 0
  - `THREE_YEAR_LOOKBACK` if is_existing_policy_transfer is true
  - `THREE_YEAR_LOOKBACK_AND_EXCLUSION_SHORTFALL` if both conditions hold
- `projected_outside_estate_if_implemented` = `death_benefit` when
  formalities are met (estate_inclusion_risk is LOW_IF_FORMALITIES_MET);
  otherwise use 0
- `tax_liquidity_support` = `death_benefit` * `estate_tax_rate`,
  rounded to cents

**Recommendation:**

- `primary_action`:
  - `FUND_WITH_CRUMMEY_NOTICES` when premium fits within exclusion capacity
    and no lookback issue
  - `USE_LIFETIME_EXEMPTION_FOR_SHORTFALL` when premium_gap > 0
  - `USE_NEW_POLICY_OR_ACCEPT_LOOKBACK` when lookback applies
  - `DISCLOSE_LOOKBACK_AND_USE_EXEMPTION` when both apply
- `suitability`: `SUITABLE_WITH_ADMINISTRATION` when formalities are clear,
  `BORDERLINE` when mild issues exist, `NOT_SUITABLE` when too many risks
- `risk_flag`: same enum as estate_inclusion_risk

---

## trust_comparison

Used for: GRAT vs CRAT numerical comparison with estate context.

### Data Sources

- Client record / signed profile for estate_value, liquid_assets, age,
  filing_status, marginal_tax_rate, philanthropic_intent,
  family_transfer_priority
- Tax policy for estate_tax_exemption, estate_tax_rate,
  charitable_deduction_rate
- Trust candidate for asset_value, expected_growth_rate, grat_term_years,
  grat_annuity_rate, crat_term_years, crat_payout_rate

### Calculations

**Estate context:**

- `planning_year` = client's planning_year (2026)
- `exemption_used` = estate_tax_exemption[str(planning_year)].
  For MFJ, double it.  For SINGLE/HOH, use as-is.
- `taxable_estate` = client's `estate_value` - `exemption_used`,
  rounded to cents.  If negative, use 0.
- `estate_tax_exposure` = `taxable_estate` * `estate_tax_rate`,
  rounded to cents
- `liquid_assets_available` = client's `liquid_assets`
- `liquidity_gap_before_planning` = max(0,
  `estate_tax_exposure` - `liquid_assets_available`), rounded to cents

**GRAT:**

- `term_years` = `grat_term_years` from the trust case
- `projected_remainder_to_heirs`:
  1. Compute the annual annuity:
     `annuity = asset_value * grat_annuity_rate`
  2. For each year of the GRAT term:
     - Grow the trust corpus by expected_growth_rate
     - Subtract the annuity payment
  3. The remainder after all annuity payments is the projected
     remainder to heirs.
  4. Subtract the initial asset_value from the final corpus to get the
     net remainder.  This is `projected_remainder_to_heirs`.
- `estimated_estate_tax_reduction` = `projected_remainder_to_heirs` *
  `estate_tax_rate`, rounded to cents
- `mortality_inclusion_risk` = `TERM_SURVIVAL_REQUIRED` (always, because
  GRAT remainder requires the grantor to survive the term)

**CRAT:**

- `term_years` = `crat_term_years` from the trust case (always 20)
- `projected_charitable_remainder`:
  1. Compute the annual payout to the grantor:
     `payout = asset_value * crat_payout_rate`
  2. For each year of the CRAT term:
     - Grow the trust corpus by expected_growth_rate
     - Subtract the payout
  3. The remainder after all payouts goes to charity.
     This is `projected_charitable_remainder`.
- `estimated_income_tax_deduction` = `projected_charitable_remainder` *
  `charitable_deduction_rate`, rounded to cents
- `family_transfer_fit`:
  - `LOW` — CRAT primarily benefits charity, little family transfer
  - `MODERATE` — some family benefit from payout stream
  - `HIGH` — payout stream materially benefits family

**Recommendation:**

- `preferred_strategy`: `GRAT` or `CRAT` based on client priorities.
  If family_transfer_priority is "high" and philanthropic_intent is not
  "high", prefer GRAT.  If philanthropic_intent is "high", prefer CRAT.
- `rationale_code`:
  - `CHILDREN_TRANSFER_PRIORITY` when family transfer is the priority
  - `PHILANTHROPIC_PRIORITY` when charitable giving is the priority
- `alternate_role`:
  - `SECONDARY_CHARITABLE_TOOL` when GRAT is primary (CRAT can handle
    charitable remainder)
  - `SECONDARY_FAMILY_TRANSFER_TOOL` when CRAT is primary

---

## estate_liquidity_action_plan

Used for: Combined ILIT + trust-transfer plans with action sets.

### Data Sources

Combine the ILIT analysis and trust comparison analysis above for the
same client.  Additionally:

- Life-insurance policy
- Trust candidate record
- Tax policy

### Calculations

**Estate context:** same as trust_comparison.

**ILIT section:** same as ilit_crummey_implementation for the key ILIT
fields (annual_exclusion_capacity, premium_gap, estate_inclusion_risk,
projected_outside_estate_if_implemented).

**Trust transfer section:**

- `preferred_strategy`: GRAT or CRAT as per trust_comparison logic
- `projected_remainder_to_heirs`: same GRAT calculation
- `estimated_estate_tax_reduction`: same GRAT calculation
- `projected_charitable_remainder`: same CRAT calculation (always
  computed even if CRAT is secondary)

**Action set:**

Build a sorted list (alphabetically) of actions from these candidates:

- `ATTORNEY_DRAFT_REVIEW` — always include; attorney review is universal
- `GRAT_FOR_APPRECIATING_SHARES` — include when GRAT is preferred
- `ILIT_CRUMMEY_NOTICE_CYCLE` — include when ILIT implementation is
  recommended
- `CRAT_FOR_CHARITABLE_REMAINDER` — include when philanthropic intent is
  high or CRAT is preferred
- `LIFETIME_EXEMPTION_ALLOCATION` — include when liquidity gap exists and
  exemption allocation can help

**Recommendation:**

- `primary_action`:
  - `COMBINE_ILIT_AND_GRAT` when both ILIT and GRAT are recommended
  - `CRAT_WITH_LIQUIDITY_REVIEW` when CRAT is preferred
  - `ILIT_WITH_EXEMPTION_REVIEW` when ILIT is primary and exemption
    planning is needed
- `sequencing`:
  - `ILIT_FIRST_THEN_GRAT` — typical when both used
  - `TRUST_DECISION_FIRST` — when trust choice is the key decision
  - `ILIT_FIRST_THEN_ATTORNEY_REVIEW` — when ILIT is the primary action
- `risk_flag`: same as ILIT estate_inclusion_risk
