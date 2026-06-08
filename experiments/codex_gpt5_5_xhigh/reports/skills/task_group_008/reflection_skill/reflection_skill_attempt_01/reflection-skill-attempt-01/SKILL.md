---
name: reflection-skill-attempt-01
description: Solve private-wealth advisory benchmark tasks that ask for structured JSON planning outputs using the local advisory API. Use for Roth conversion/RMD projections, ILIT Crummey funding, GRAT versus CRAT comparisons, and estate liquidity action plans with conflicting source documents and tax-policy constants.
---

# Private Wealth Advisory JSON Workflow

## Standard Workflow

1. Read only the task prompt, request memo, and `answer_template.json`.
2. Get `API_BASE` from the harness or user. Verify `GET /api/health`.
3. Fetch the needed records:
   - `GET /api/clients?search=` if the client id is not explicit.
   - `GET /api/clients/<client_id>`
   - `GET /api/source-documents?client_id=<client_id>`
   - `GET /api/retirement-accounts?client_id=<client_id>`
   - `GET /api/life-insurance?client_id=<client_id>`
   - `GET /api/trust-candidates?client_id=<client_id>`
   - `GET /api/policies/tax`
   - `GET /api/rmd-factors`
4. Build the JSON exactly from the template enums. Use JSON numbers for money, rounded to cents; use ISO `YYYY-MM-DD` dates; return no prose.

## Source Resolution

Use the source with the best authority for each fact, not merely the latest API object:

- `SIGNED_PROFILE` controls household profile facts: age, filing status, marital status, annual non-IRA income, marginal tax rate, beneficiary count, goals, estate value, and liquid assets when present.
- `CUSTODIAN_EXPORT` controls retirement-account fields: traditional balance, Roth balance, expected return, RMD start age, and recommended conversion years.
- `ATTORNEY_MEMO` controls trust-transfer asset sourcing when a trust candidate has no explicit source type; report `controlling_asset_source: "ATTORNEY_MEMO"` for GRAT/CRAT candidate values.
- Life-insurance policy details come from the life-insurance endpoint. If the template asks for a policy source and there is no explicit source type on the policy, use `SIGNED_PROFILE` unless a document directly supersedes it.
- `CRM_NOTE` is older support only. `STALE_MARKETING_INTAKE` is last resort.

Record the controlling enum in `source_resolution` for the specific fact family requested.

## Shared Calculations

- Planning year: prefer signed profile fact, then client record.
- Estate exemption: use `tax.estate_tax_exemption[planning_year]`; multiply by `2` for married/MFJ households, otherwise `1`.
- `taxable_estate = max(estate_value - exemption_used, 0)`.
- `estate_tax_exposure = taxable_estate * estate_tax_rate`.
- `liquidity_gap_before_planning = max(estate_tax_exposure - liquid_assets, 0)`.
- When an `estate_context` object is requested, include `planning_year`, `exemption_used`, and `liquid_assets_available` if the task shape allows supplemental estate fields.

Round only final reported amounts unless an intermediate is itself a reported field.

## Roth Conversion And RMD SOP

Inputs: signed profile income/tax facts, custodian IRA record, tax `conversion_bracket_targets`, and `rmd-factors`.

1. `first_conversion_year = planning_year`.
2. `first_rmd_year = planning_year + (rmd_start_age - age)`.
3. `conversion_years = recommended_conversion_years`.
4. `bracket_capacity = conversion_bracket_targets[filing_status] - annual_non_ira_income`.
5. `annual_conversion_amount = max(0, min(traditional_balance / conversion_years, bracket_capacity))`.
6. `conversion_years_positive = conversion_years` when the annual amount is positive, even if RMDs begin during the schedule; otherwise `0`.
7. `total_converted = annual_conversion_amount * conversion_years_positive`.
8. `total_conversion_tax = total_converted * marginal_tax_rate`.

For each projection, iterate from planning year through horizon year inclusive:

```text
for each year:
  age_y = age + (year - planning_year)
  if conversion scenario and year is in conversion schedule:
    conversion = min(annual_conversion_amount, traditional_balance)
    traditional_balance -= conversion
    roth_balance += conversion
  if age_y >= rmd_start_age:
    rmd = traditional_balance / rmd_factor[age_y]
    rmd_tax += rmd * marginal_tax_rate
    traditional_balance -= rmd
  traditional_balance *= (1 + expected_return)
  roth_balance *= (1 + expected_return)
```

Baseline RMD tax uses the same loop without conversions. Conversion RMD tax uses the loop with conversions. Report `rmd_tax_savings = baseline - conversion`.

Set `heir_tax_profile` from the horizon balances: `MIXED_TAXABLE_AND_TAX_FREE` when both traditional and Roth balances remain material; `MOSTLY_TAX_FREE` when traditional is negligible; `MOSTLY_TAXABLE` when Roth is negligible. Use `STAGED_ROTH_CONVERSION`/`SUITABLE`/`TAX_BRACKET_MANAGEMENT` when bracket capacity is positive and liquidity can absorb the conversion tax. Use `DEFER` or `NO_CONVERSION` only when capacity, liquidity, or projected benefit is weak.

## ILIT Crummey SOP

Inputs: signed beneficiary count, life-insurance record, annual gift exclusion, estate tax rate.

- `annual_exclusion_per_beneficiary = tax.annual_gift_exclusion[planning_year]`.
- `annual_exclusion_capacity = beneficiary_count * annual_exclusion_per_beneficiary`.
- `premium_gap = max(annual_premium - annual_exclusion_capacity, 0)`.
- `notices_required = beneficiary_count`.
- `notice_due_date = contribution_date + 7 calendar days`.
- `withdrawal_window_end = notice_due_date + 30 calendar days`.
- `earliest_premium_payment_date = withdrawal_window_end + 1 calendar day`.
- `dedicated_bank_account_required = true`.
- `projected_outside_estate_if_implemented = death_benefit`.
- `tax_liquidity_support = death_benefit * estate_tax_rate`.

Risk/action mapping:

- No premium gap and no existing policy transfer: `LOW_IF_FORMALITIES_MET`, `FUND_WITH_CRUMMEY_NOTICES`, `SUITABLE_WITH_ADMINISTRATION`.
- Premium gap only: `EXCLUSION_SHORTFALL`, `USE_LIFETIME_EXEMPTION_FOR_SHORTFALL`, usually `BORDERLINE`.
- Existing policy transfer only: `THREE_YEAR_LOOKBACK`, `USE_NEW_POLICY_OR_ACCEPT_LOOKBACK`, usually `BORDERLINE`.
- Both: `THREE_YEAR_LOOKBACK_AND_EXCLUSION_SHORTFALL`, `DISCLOSE_LOOKBACK_AND_USE_EXEMPTION`.

## GRAT/CRAT SOP

Inputs: trust candidate, estate context, signed goals, tax charitable deduction rate.

Use simple total annuity/payout subtraction; do not compound the payout streams:

- `grat_future_value = asset_value * (1 + expected_growth_rate) ^ grat_term_years`.
- `grat_remainder = max(grat_future_value - asset_value * grat_annuity_rate * grat_term_years, 0)`.
- `estimated_estate_tax_reduction = grat_remainder * estate_tax_rate`.
- `crat_future_value = asset_value * (1 + expected_growth_rate) ^ crat_term_years`.
- `projected_charitable_remainder = max(crat_future_value - asset_value * crat_payout_rate * crat_term_years, 0)`.
- `estimated_income_tax_deduction = projected_charitable_remainder * charitable_deduction_rate`.

Prefer `GRAT` when family transfer priority outranks or equals philanthropic intent; rationale `CHILDREN_TRANSFER_PRIORITY`, alternate role `SECONDARY_CHARITABLE_TOOL`, and CRAT family-transfer fit usually `LOW`. Prefer `CRAT` when philanthropy clearly outranks family transfer; rationale `PHILANTHROPIC_PRIORITY`, alternate role `SECONDARY_FAMILY_TRANSFER_TOOL`.

## Estate Liquidity Action Plan SOP

Combine the estate context, ILIT, and GRAT/CRAT calculations.

- Use the ILIT risk flag as the recommendation risk flag.
- Prefer `COMBINE_ILIT_AND_GRAT` with sequencing `ILIT_FIRST_THEN_GRAT` when family transfer priority is high and ILIT formalities are workable.
- Use `CRAT_WITH_LIQUIDITY_REVIEW` and `TRUST_DECISION_FIRST` when philanthropic priority controls.
- Use `ILIT_WITH_EXEMPTION_REVIEW` and `ILIT_FIRST_THEN_ATTORNEY_REVIEW` when ILIT issues dominate the planning path.
- Include actionable enums only, then sort `action_set` alphabetically:
  `ATTORNEY_DRAFT_REVIEW`, `CRAT_FOR_CHARITABLE_REMAINDER`, `GRAT_FOR_APPRECIATING_SHARES`, `ILIT_CRUMMEY_NOTICE_CYCLE`, `LIFETIME_EXEMPTION_ALLOCATION`.
  Add `LIFETIME_EXEMPTION_ALLOCATION` when there is a premium gap; add the GRAT or CRAT action matching the preferred trust strategy.

## Pitfalls

- Do not let older CRM facts override a signed profile.
- Married estate exemption is doubled; single exemption is not.
- Roth conversions happen before same-year RMDs, then both balances grow after the RMD.
- Recommended Roth conversion years can continue after the first RMD year.
- RMD tax and conversion tax are separate fields; do not combine them.
- Crummey notices use `+7`, then a 30-day withdrawal window, then premium payment the next day.
- `tax_liquidity_support` is death benefit times estate tax rate, not the estate liquidity gap.
- CRAT income tax deduction uses projected charitable remainder times the policy deduction rate.
- Always sort `action_set` alphabetically and emit enum spelling exactly as the template states.
