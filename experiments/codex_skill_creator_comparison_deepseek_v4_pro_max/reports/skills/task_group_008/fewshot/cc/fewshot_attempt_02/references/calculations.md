# Calculation Formulas

This reference contains the step-by-step formulas for each analysis type. Read the section matching your engagement type.

## Shared Formulas

### Marginal Tax Rate

Given `taxable_income` and `filing_status`, find the highest bracket the income reaches in `marginal_rate_schedule`. The rate from that bracket is the client's marginal rate. For Roth conversions, the conversion amount pushes income up; decide how many bracket steps the conversion can fill without exceeding the target threshold (usually the top of the current bracket or one bracket above).

### Remaining Estate Tax Exemption

```
remaining_exemption = max(0, lifetime_estate_exemption - exemption_used)
```

Where `exemption_used` comes from the client profile or trust-candidate data. If not explicitly given, assume zero.

### Estate Tax Exposure

```
estate_tax_exposure = max(0, taxable_estate - remaining_exemption) * estate_tax_rate
```

### Liquidity Gap

```
liquidity_gap_before_planning = max(0, estate_tax_exposure - liquid_assets_available)
```

### Tax Liability on Conversion

```
conversion_tax = conversion_amount * marginal_rate
```

---

## roth_conversion_rmd

### Determine Client Age and RMD First Year

Read `age` and `birth_date` from the chosen client profile source. Compute `first_rmd_year` as the calendar year the client reaches `rmd_starting_age` (from `/api/policies/tax`):

```
first_rmd_year = birth_year + rmd_starting_age
```

### Aggregate Traditional IRA Balance

Sum the `balance` of all `tax_deferred` accounts for the client (TRADITIONAL_IRA, 401K, 403B, ROLLOVER_IRA, etc.). This is the `total_traditional_balance`.

### Plan Staged Conversions

1. The conversion window is `first_rmd_year - planning_year` (the years before RMDs begin).
2. Divide `total_traditional_balance` into equal annual conversions that stay within the chosen tax bracket.
3. `annual_conversion_amount = total_traditional_balance / conversion_years`, rounded to cents.
4. `conversion_years` = the number of years in the conversion window, but capped so `annual_conversion_amount` does not push the client above the chosen bracket ceiling.
5. `conversion_years_positive = conversion_years` (always the same value).
6. `total_converted = annual_conversion_amount * conversion_years`.
7. `total_conversion_tax = total_converted * marginal_rate`.

### RMD Projection

For each year from `first_rmd_year` through `horizon_year`:

**Baseline (no conversion):**
- Start with `total_traditional_balance` as the beginning-of-year balance.
- RMD = `balance / distribution_period(age)` where `distribution_period` comes from `/api/rmd-factors` for the client's age that year.
- RMD tax = `RMD * marginal_rate`.
- New balance = `old_balance - RMD` (no growth assumed for simplicity, or use growth rate if supplied by API).
- Sum all RMD taxes to get `baseline_rmd_tax_through_horizon`.

**With conversion:**
- Start with `total_traditional_balance - total_converted`.
- Same RMD calculation on the reduced balance.
- RMD tax = `RMD * marginal_rate`.
- Sum all RMD taxes to get `conversion_rmd_tax_through_horizon`.

```
rmd_tax_savings_through_horizon = baseline_rmd_tax_through_horizon - conversion_rmd_tax_through_horizon
```

### Legacy Projection

**Roth balance at horizon:**
```
projected_roth_balance_horizon = existing_roth_balance + total_converted
```
(Plus any growth if a growth rate is specified from the API. Apply growth compounded annually from each conversion year to horizon year.)

**Traditional balance at horizon:**
The traditional balance remaining after all RMD withdrawals through the horizon year.

**Heir tax profile:**
- If `projected_roth_balance_horizon > projected_traditional_balance_horizon * 2`: `MOSTLY_TAX_FREE`
- If `projected_traditional_balance_horizon > projected_roth_balance_horizon * 2`: `MOSTLY_TAXABLE`
- Otherwise: `MIXED_TAXABLE_AND_TAX_FREE`

### Recommendation Logic

- `STAGED_ROTH_CONVERSION` when `rmd_tax_savings_through_horizon > 0` and conversion fits bracket.
- `DEFER` when savings are positive but the timeline is tight or bracket management is uncertain.
- `NO_CONVERSION` when savings are zero or negative.

- `SUITABLE` when savings > 0 and conversion fits within bracket.
- `BORDERLINE` when savings are small or bracket headroom is limited.
- `DEFER` when no clear benefit.

- `TAX_BRACKET_MANAGEMENT`: the main concern is staying within brackets.
- `LIQUIDITY_CONSTRAINT`: the client may not have cash to pay conversion tax.
- `RMD_NEAR_TERM`: RMDs begin soon, limiting the conversion window.

---

## ilit_crummey_implementation

### Gift Plan

```
annual_exclusion_per_beneficiary = annual_gift_exclusion (from /api/policies/tax)
annual_exclusion_capacity = annual_exclusion_per_beneficiary * beneficiary_count
premium_gap = max(0, annual_premium - annual_exclusion_capacity)
```

### Administration Timeline

All dates are in `planning_year` (default to current year from context if not specified):

- `contribution_date`: the date contributions are made to the ILIT (use the request memo date or a reasonable early-year date like March 10 of the planning year).
- `notice_due_date`: `contribution_date + 7 days`.
- `withdrawal_window_end`: `notice_due_date + 30 days`.
- `earliest_premium_payment_date`: `withdrawal_window_end + 1 day`.
- `dedicated_bank_account_required`: `true` (best practice for Crummey administration).
- `notices_required = beneficiary_count`.

### Estate Result

```
death_benefit: from the chosen policy source
estate_inclusion_risk: same as recommendation.risk_flag
projected_outside_estate_if_implemented = death_benefit (if formalities met)
tax_liquidity_support = death_benefit * estate_tax_rate
```

### Recommendation Logic

- `FUND_WITH_CRUMMEY_NOTICES` when `premium_gap = 0` and policy is under 3 years old.
- `USE_LIFETIME_EXEMPTION_FOR_SHORTFALL` when `premium_gap > 0`.
- `USE_NEW_POLICY_OR_ACCEPT_LOOKBACK` when policy is over 3 years old and gap is zero.
- `DISCLOSE_LOOKBACK_AND_USE_EXEMPTION` when policy is over 3 years old and gap exists.

- `SUITABLE_WITH_ADMINISTRATION` when formalities can cover the setup.
- `BORDERLINE` when there's a gap or timing issue.
- `NOT_SUITABLE` when risks outweigh benefits.

- `LOW_IF_FORMALITIES_MET` when `premium_gap = 0` and no lookback concern.
- `EXCLUSION_SHORTFALL` when `premium_gap > 0`.
- `THREE_YEAR_LOOKBACK` when policy is within IRC 2035 lookback period.
- `THREE_YEAR_LOOKBACK_AND_EXCLUSION_SHORTFALL` when both apply.

---

## trust_comparison

### Estate Context

```
taxable_estate: from the client profile or trust-candidate data
exemption_used: from the client profile (may be a field like exemption_used or computed from prior gifts)
estate_tax_exposure = max(0, taxable_estate - max(0, lifetime_estate_exemption - exemption_used)) * estate_tax_rate
liquid_assets_available: from client profile or trust-candidate assets_available
liquidity_gap_before_planning = max(0, estate_tax_exposure - liquid_assets_available)
```

### GRAT Projection

```
grat_term_years: from trust-candidates entry with trust_type = "GRAT"
section_7520_rate: from /api/policies/tax
assets_available: from the GRAT trust-candidate
```

GRAT remainder to heirs (zeroed-out GRAT):
- The grantor receives an annuity equal to `assets_available / term_years` each year, discounted at the 7520 rate.
- Any growth above the 7520 rate passes to remainder beneficiaries (heirs) free of gift tax.
- If the API provides explicit `projected_remainder_to_heirs` and `estimated_estate_tax_reduction` in the trust-candidate data, use those directly.
- Otherwise compute: `projected_remainder_to_heirs = assets_available * ((1 + growth_rate)^term_years - (1 + section_7520_rate)^term_years)`.
- `estimated_estate_tax_reduction = projected_remainder_to_heirs * estate_tax_rate`.
- `mortality_inclusion_risk = "TERM_SURVIVAL_REQUIRED"` (always, because GRAT benefits require the grantor to survive the term).

### CRAT Projection

```
crat_term_years: from trust-candidates entry with trust_type = "CRAT"
section_7520_rate: from /api/policies/tax
assets_available: from the CRAT trust-candidate
```

CRAT charitable remainder:
- The trust pays a fixed annuity to the income beneficiaries (usually the donors) for the term.
- The remainder goes to charity.
- If the API provides explicit `projected_charitable_remainder` and `estimated_income_tax_deduction` in the trust-candidate data, use those directly.
- Otherwise: `annual_payment = assets_available * payout_rate` (typically 5% or as specified in trust-candidate). `present_value_payments = annual_payment * ((1 - (1 + section_7520_rate)^(-term_years)) / section_7520_rate)`. `projected_charitable_remainder = assets_available * (1 + section_7520_rate)^term_years - annual_payment * (( (1 + section_7520_rate)^term_years - 1) / section_7520_rate)`.
- `estimated_income_tax_deduction`: use the value from the trust-candidate or compute as `projected_charitable_remainder * top_income_tax_rate` (simplified; actual deduction has AGI limits).

### Family Transfer Fit for CRAT

- `LOW` when the CRAT remainder goes mostly to charity and little to family.
- `MODERATE` when there's a meaningful split.
- `HIGH` when family gets substantial benefit.

### Recommendation Logic

- `GRAT` with `CHILDREN_TRANSFER_PRIORITY` when family transfer is the primary goal.
- `CRAT` with `PHILANTHROPIC_PRIORITY` when charitable intent dominates.
- The alternate role is the secondary use of the non-preferred tool: `SECONDARY_CHARITABLE_TOOL` when GRAT is primary, or `SECONDARY_FAMILY_TRANSFER_TOOL` when CRAT is primary.

---

## estate_liquidity_action_plan

This analysis type combines ILIT and trust transfer computations. Compute each independently, then synthesize.

### Estate Context

Same as trust_comparison estate context above.

### ILIT Sub-analysis

Same as ilit_crummey_implementation above, using the policy data for the client.

### Trust Transfer Sub-analysis

Same as trust_comparison above, using the trust-candidates data.

### Action Set Assembly

Based on the computed results, select actions from this universe:

- `ATTORNEY_DRAFT_REVIEW`: always include -- an attorney must review and draft documents.
- `GRAT_FOR_APPRECIATING_SHARES`: include when GRAT is the preferred trust strategy.
- `ILIT_CRUMMEY_NOTICE_CYCLE`: include when ILIT is actionable and premium_gap is zero.
- `CRAT_FOR_CHARITABLE_REMAINDER`: include when CRAT is the preferred or alternate strategy and charitable intent exists.
- `LIFETIME_EXEMPTION_ALLOCATION`: include when `premium_gap > 0` or `liquidity_gap_before_planning > 0`.

Always sort the `action_set` array alphabetically.

### Recommendation Logic

- `COMBINE_ILIT_AND_GRAT` when both ILIT and GRAT are viable.
- `CRAT_WITH_LIQUIDITY_REVIEW` when CRAT is preferred and liquidity gap is a concern.
- `ILIT_WITH_EXEMPTION_REVIEW` when ILIT is the primary tool and exemption allocation is needed.

- `ILIT_FIRST_THEN_GRAT`: sequence ILIT before the GRAT (estate inclusion risk managed first).
- `TRUST_DECISION_FIRST`: the trust comparison decision drives sequencing.
- `ILIT_FIRST_THEN_ATTORNEY_REVIEW`: ILIT first, then attorney coordinates the trust transfer.

- Risk flags: same enum values as the ILIT analysis (`LOW_IF_FORMALITIES_MET`, `EXCLUSION_SHORTFALL`, `THREE_YEAR_LOOKBACK`, `THREE_YEAR_LOOKBACK_AND_EXCLUSION_SHORTFALL`).
