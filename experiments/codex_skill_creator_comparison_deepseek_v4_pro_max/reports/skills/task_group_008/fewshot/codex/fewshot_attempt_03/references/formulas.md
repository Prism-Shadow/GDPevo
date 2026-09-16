# Computation Formulas

All USD amounts rounded to two decimal places. Use the planning year from tax
policies for the current-year exemption and gift exclusion values.

## Common Parameters

From `/api/policies/tax`:
- `annual_gift_exclusion[planning_year]` — per-beneficiary annual gift exclusion.
- `estate_tax_exemption[planning_year]` — per-person lifetime exemption.
- `estate_tax_rate` — 0.40.
- `conversion_bracket_targets[filing_status]` — top-of-bracket income.
- `charitable_deduction_rate` — 0.35.

From `/api/rmd-factors`:
- `rmd_factors[age]` — IRS life-expectancy divisor for age.

## roth_conversion_rmd

Compute the conversion plan from the signed profile (income, tax rate,
filing_status, age) and the custodian export (traditional_balance,
roth_balance, expected_return, rmd_start_age, recommended_conversion_years).

### conversion_plan

```
first_conversion_year = planning_year
conversion_years = recommended_conversion_years (from custodian export)
conversion_years_positive = conversion_years  (same value)
annual_conversion_amount = conversion_bracket_targets[filing_status] - annual_non_ira_income
total_converted = annual_conversion_amount * conversion_years
total_conversion_tax = total_converted * marginal_tax_rate
```

### rmd_projection

The horizon year comes from the request memo. The first RMD year is `rmd_start_age`
converted to the calendar year: `planning_year + (rmd_start_age - age)`.

**Baseline (no conversion)**: Project traditional_balance forward each year at
`expected_return`. Starting at `first_rmd_year`, subtract each year's RMD (balance
divided by the age-appropriate rmd factor). Accumulate RMD amounts multiplied by
`marginal_tax_rate` through the horizon year. Sum to get
`baseline_rmd_tax_through_horizon`.

**Conversion scenario**: Subtract `annual_conversion_amount` from the
traditional balance each conversion year (years planning_year through
planning_year + conversion_years - 1). Concurrently grow the roth_balance and
the converted amounts at the same `expected_return`. After conversions end, the
remaining traditional balance grows and undergoes RMDs as in the baseline.
Accumulate RMD tax through horizon to get `conversion_rmd_tax_through_horizon`.

```
rmd_tax_savings_through_horizon = baseline_rmd_tax_through_horizon - conversion_rmd_tax_through_horizon
```

### legacy_projection

```
projected_roth_balance_horizon = roth_balance grown at expected_return through horizon
    plus all converted amounts grown at expected_return from their conversion year onward
projected_traditional_balance_horizon = traditional_balance after last RMD through horizon
heir_tax_profile = "MIXED_TAXABLE_AND_TAX_FREE" (default for mixed portfolios)
```

### recommendation

```
primary_action = "STAGED_ROTH_CONVERSION" (always for this analysis type)
suitability = "SUITABLE" (default) or "BORDERLINE" (marginal) or "DEFER" (not recommended)
risk_flag =
  "TAX_BRACKET_MANAGEMENT" — conversion pushes near bracket limit
  "RMD_NEAR_TERM" — first RMD year is within 2 years
  "LIQUIDITY_CONSTRAINT" — conversion tax exceeds liquid assets significantly
```

## ilit_crummey_implementation

Use the signed profile for beneficiary_count (controlling source for household
facts) and the life-insurance record for policy details.

### gift_plan

```
planning_year = from tax policies
annual_exclusion_per_beneficiary = annual_gift_exclusion[planning_year]
beneficiary_count = from signed profile
annual_exclusion_capacity = annual_exclusion_per_beneficiary * beneficiary_count
annual_premium = from life-insurance record
premium_gap = max(0, annual_premium - annual_exclusion_capacity)
```

### administration

```
notices_required = beneficiary_count
contribution_date = planned_contribution_date from life-insurance record
notice_due_date = contribution_date + 7 days
withdrawal_window_end = contribution_date + 37 days
earliest_premium_payment_date = withdrawal_window_end + 1 day
dedicated_bank_account_required = true (always for proper ILIT administration)
```

### recommendation

```
primary_action =
  "FUND_WITH_CRUMMEY_NOTICES" — premium fits within exclusion capacity
  "USE_LIFETIME_EXEMPTION_FOR_SHORTFALL" — gap > 0 but no lookback
  "USE_NEW_POLICY_OR_ACCEPT_LOOKBACK" — existing policy transfer
  "DISCLOSE_LOOKBACK_AND_USE_EXEMPTION" — existing transfer AND gap > 0
suitability =
  "SUITABLE_WITH_ADMINISTRATION" — premium fits, no issues
  "BORDERLINE" — small gap or minor concern
  "NOT_SUITABLE" — major exclusion shortfall or lookback
risk_flag =
  "LOW_IF_FORMALITIES_MET" — premium within capacity, new policy
  "EXCLUSION_SHORTFALL" — premium exceeds exclusion capacity
  "THREE_YEAR_LOOKBACK" — existing policy transfer
  "THREE_YEAR_LOOKBACK_AND_EXCLUSION_SHORTFALL" — both concerns
```

### estate_result

```
death_benefit = from life-insurance record
estate_inclusion_risk = same value as recommendation.risk_flag
projected_outside_estate_if_implemented = death_benefit (new policy)
    or 0 (existing policy under lookback, inclusion risk)
tax_liquidity_support = death_benefit * estate_tax_rate
```

## trust_comparison

Use the signed profile for client facts (age, filing_status, family_transfer_priority,
philanthropic_intent) and the trust-candidates record for trust parameters.
Use the tax policies for exemption and rate.

### estate_context

```
planning_year = from tax policies
exemption_per_person = estate_tax_exemption[planning_year]
exemption_used =
  exemption_per_person * 2   if filing_status is "MFJ"
  exemption_per_person       if filing_status is "SINGLE" or "HOH"
taxable_estate = max(0, estate_value - exemption_used)
estate_tax_exposure = taxable_estate * estate_tax_rate
liquid_assets_available = liquid_assets from signed profile
liquidity_gap_before_planning = max(0, estate_tax_exposure - liquid_assets_available)
```

### grat

```
term_years = grat_term_years from trust candidate
g = expected_growth_rate from trust candidate
n = grat_term_years
a = grat_annuity_rate from trust candidate
asset = asset_value from trust candidate

projected_remainder_to_heirs = asset * ((1 + g)^n - n * a)
estimated_estate_tax_reduction = projected_remainder_to_heirs * estate_tax_rate
mortality_inclusion_risk = "TERM_SURVIVAL_REQUIRED"
```

### crat

```
term_years = min(crat_term_years from trust candidate, max_crat_term_years from tax policies)
    (in practice this is always 20)
g = expected_growth_rate
n = term_years
p = crat_payout_rate

projected_charitable_remainder = asset * ((1 + g)^n - n * p)
estimated_income_tax_deduction = projected_charitable_remainder * charitable_deduction_rate
family_transfer_fit =
  "LOW" — family_transfer_priority is "high"
  "MODERATE" — family_transfer_priority is "moderate"
  "HIGH" — family_transfer_priority is "low" and philanthropic_intent is "high"
```

### recommendation

```
preferred_strategy =
  "GRAT" — family_transfer_priority is "high" or "moderate"
  "CRAT" — family_transfer_priority is "low" AND philanthropic_intent is "high"
rationale_code =
  "CHILDREN_TRANSFER_PRIORITY" — when GRAT is preferred
  "PHILANTHROPIC_PRIORITY" — when CRAT is preferred
alternate_role =
  "SECONDARY_CHARITABLE_TOOL" — when GRAT is preferred
  "SECONDARY_FAMILY_TRANSFER_TOOL" — when CRAT is preferred
```

## estate_liquidity_action_plan

Combine estate-tax liquidity analysis, ILIT Crummey funding, and a trust
transfer recommendation. Use the signed profile, life-insurance record, and
trust-candidates record.

### estate_context

Same computation as trust_comparison: taxable_estate, estate_tax_exposure,
liquidity_gap_before_planning.

### ilit

```
annual_exclusion_capacity = annual_exclusion_per_beneficiary * beneficiary_count
annual_premium = from life-insurance
premium_gap = max(0, annual_premium - annual_exclusion_capacity)
estate_inclusion_risk =
  "LOW_IF_FORMALITIES_MET" — new policy, no gap
  "EXCLUSION_SHORTFALL" — gap > 0
  "THREE_YEAR_LOOKBACK" — existing transfer
  "THREE_YEAR_LOOKBACK_AND_EXCLUSION_SHORTFALL" — both
projected_outside_estate_if_implemented = death_benefit (new policy) or 0 (existing)
```

### trust_transfer

```
preferred_strategy = "GRAT" (same priority logic as trust_comparison)
projected_remainder_to_heirs = asset * ((1 + g)^n - n * a)  [GRAT formula]
estimated_estate_tax_reduction = projected_remainder_to_heirs * estate_tax_rate
projected_charitable_remainder = asset * ((1 + g)^n - n * p)  [CRAT formula, for context]
```

### action_set

Alphabetically sorted list from the following candidates:

- `ATTORNEY_DRAFT_REVIEW` — always include
- `GRAT_FOR_APPRECIATING_SHARES` — include when GRAT is preferred
- `CRAT_FOR_CHARITABLE_REMAINDER` — include when CRAT is preferred
- `ILIT_CRUMMEY_NOTICE_CYCLE` — include when ILIT is recommended
- `LIFETIME_EXEMPTION_ALLOCATION` — include when premium_gap > 0

### recommendation

```
primary_action =
  "COMBINE_ILIT_AND_GRAT" — liquidity gap > 0 and both tools needed
  "CRAT_WITH_LIQUIDITY_REVIEW" — CRAT preferred, gap significant
  "ILIT_WITH_EXEMPTION_REVIEW" — ILIT only, gap manageable
sequencing =
  "ILIT_FIRST_THEN_GRAT" — when using both ILIT and GRAT
  "TRUST_DECISION_FIRST" — when trust choice is the primary decision
  "ILIT_FIRST_THEN_ATTORNEY_REVIEW" — when attorney review needed
risk_flag = same as ilit.estate_inclusion_risk
```

## source_resolution

For every analysis, annotate the controlling document type for each fact domain.
These values come from the source resolution logic in SKILL.md, never from
computation.

Common fields:
- `controlling_profile_source`: The document type that provided household facts
  (beneficiary count, income, tax rate, intent). Always SIGNED_PROFILE when
  a signed profile exists for that client. Use ATTORNEY_MEMO only when no
  SIGNED_PROFILE exists for the fact.
- `controlling_account_source`: Always CUSTODIAN_EXPORT for retirement-account
  facts.
- `controlling_beneficiary_source`: Same logic as controlling_profile_source.
- `controlling_policy_source`: SIGNED_PROFILE when it confirms the insurance
  details; otherwise ATTORNEY_MEMO or CUSTODIAN_EXPORT.
- `controlling_goal_source`: SIGNED_PROFILE when family_transfer_priority and
  philanthropic_intent are in the signed profile; otherwise ATTORNEY_MEMO.
- `controlling_asset_source`: ATTORNEY_MEMO for trust asset values when it is
  the most recent source; otherwise SIGNED_PROFILE.
