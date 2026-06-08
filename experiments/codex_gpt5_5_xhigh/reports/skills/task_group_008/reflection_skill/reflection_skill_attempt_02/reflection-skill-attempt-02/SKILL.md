---
name: reflection-skill-attempt-02
description: Prepare task_group_008 private wealth advisory JSON outputs from the local advisory API for Roth conversion/RMD, ILIT Crummey funding, GRAT vs CRAT, and estate-liquidity action-plan requests with conflicting client source records.
---

# Task Group 008 Advisory Workflow

## API Use

Use the harness-provided `API_BASE` (fallback: `http://127.0.0.1:8021`). Fetch, at minimum:

- `GET /api/clients/<client_id>`
- `GET /api/source-documents?client_id=<client_id>`
- `GET /api/retirement-accounts?client_id=<client_id>`
- `GET /api/life-insurance?client_id=<client_id>`
- `GET /api/trust-candidates?client_id=<client_id>`
- `GET /api/policies/tax`
- `GET /api/rmd-factors`

Use the local `input/payloads/answer_template.json` for required fields/enums and the memo for `client_id`, engagement type, horizon year, and `task_id`. Return only the final JSON object.

## Source Resolution

Prefer source records by fact type, not by whichever value is largest.

- Profile facts: use `SIGNED_PROFILE` for age, filing status, marital status, planning year, non-IRA income, marginal tax rate, beneficiary count, liquid assets, and estate value when present.
- Goals: use `SIGNED_PROFILE` for `family_transfer_priority` and `philanthropic_intent`; use CRM only as a stale fallback.
- Retirement account facts: use `CUSTODIAN_EXPORT` for traditional/Roth balances, return assumptions, RMD age, and recommended conversion years.
- Trust asset/planning context: use the trust-candidate endpoint for trust math; when an attorney memo supplies estate/asset context, set trust-comparison `controlling_asset_source` to `ATTORNEY_MEMO`.
- Life-insurance facts: use the life-insurance endpoint for premium, death benefit, contribution date, owner, and existing-policy-transfer flag; set policy source to `SIGNED_PROFILE` unless a stronger explicit policy source is present.

## Shared Estate Fields

For estate-context outputs, include these fields when applicable even if the template lists only the core numeric fields:

- `planning_year`: controlling planning year.
- `exemption_used`: estate-tax exemption for the year times 2 for married households, otherwise times 1.
- `taxable_estate`: `max(0, estate_value - exemption_used)`.
- `estate_tax_exposure`: `taxable_estate * estate_tax_rate`.
- `liquid_assets_available`: controlling liquid assets.
- `liquidity_gap_before_planning`: `max(0, estate_tax_exposure - liquid_assets_available)`.

Round money to cents only after completing each calculation.

## Roth Conversion/RMD SOP

Use signed-profile income/tax facts and custodian account facts.

1. `first_conversion_year = planning_year`.
2. `conversion_years = recommended_conversion_years`; do not cap this at the first RMD year.
3. `annual_conversion_amount = min(max(0, bracket_target[filing_status] - annual_non_ira_income), traditional_balance / conversion_years)`.
4. `conversion_years_positive = conversion_years` when the annual amount is positive, otherwise `0`.
5. `total_converted = annual_conversion_amount * conversion_years_positive`.
6. `total_conversion_tax = total_converted * marginal_tax_rate`.
7. `first_rmd_year = planning_year + (rmd_start_age - current_age)`.

Project baseline and conversion scenarios from `planning_year` through the horizon, inclusive:

```text
for each year:
  age = current_age + (year - planning_year)
  if conversion scenario and year is within conversion_years_positive:
    move annual_conversion_amount from traditional to Roth before RMDs
  if age >= rmd_start_age:
    rmd = traditional_balance / rmd_factor[age]
    rmd_tax += rmd * marginal_tax_rate
    traditional_balance -= rmd
  traditional_balance *= (1 + expected_return)
  roth_balance *= (1 + expected_return)
```

`baseline_rmd_tax_through_horizon` is the baseline tax sum; `conversion_rmd_tax_through_horizon` is the conversion-scenario sum; savings is baseline minus conversion. Conversion tax is separate and is not added to RMD tax. Use `STAGED_ROTH_CONVERSION`, `SUITABLE`, and `TAX_BRACKET_MANAGEMENT` when there is positive bracket room and liquidity is not constraining.

## ILIT Crummey SOP

Use the policy year gift exclusion from `/api/policies/tax`.

- `annual_exclusion_capacity = annual_exclusion_per_beneficiary * beneficiary_count`.
- `premium_gap = max(0, annual_premium - annual_exclusion_capacity)`.
- `notices_required = beneficiary_count`.
- `contribution_date = planned_contribution_date`.
- `notice_due_date = contribution_date + 7 calendar days`.
- `withdrawal_window_end = notice_due_date + 30 calendar days`.
- `earliest_premium_payment_date = withdrawal_window_end + 1 calendar day`.
- `dedicated_bank_account_required = true`.
- `projected_outside_estate_if_implemented = death_benefit`.
- In ILIT-only outputs, `tax_liquidity_support` is the controlling liquid-assets amount, not the death benefit.

Risk flag:

- No premium gap and no existing policy transfer: `LOW_IF_FORMALITIES_MET`.
- Premium gap only: `EXCLUSION_SHORTFALL`.
- Existing policy transfer only: `THREE_YEAR_LOOKBACK`.
- Both: `THREE_YEAR_LOOKBACK_AND_EXCLUSION_SHORTFALL`.

Action:

- Low risk: `FUND_WITH_CRUMMEY_NOTICES`, `SUITABLE_WITH_ADMINISTRATION`.
- Exclusion shortfall: `USE_LIFETIME_EXEMPTION_FOR_SHORTFALL`, usually `BORDERLINE`.
- Existing transfer: use a lookback-disclosure/new-policy action from the template and flag the lookback risk.

## GRAT/CRAT SOP

Choose the preferred strategy from controlling goals:

- Prefer `GRAT` with `CHILDREN_TRANSFER_PRIORITY` and `SECONDARY_CHARITABLE_TOOL` when family transfer priority is high or exceeds philanthropic intent.
- Prefer `CRAT` with `PHILANTHROPIC_PRIORITY` and `SECONDARY_FAMILY_TRANSFER_TOOL` when philanthropic intent is high and family transfer priority is not high.

Calculations:

- `projected_remainder_to_heirs = asset_value * (1 + expected_growth_rate) ^ grat_term_years - asset_value * grat_annuity_rate * grat_term_years`.
- `estimated_estate_tax_reduction = projected_remainder_to_heirs * estate_tax_rate`.
- `projected_charitable_remainder = asset_value * (1 + expected_growth_rate) ^ crat_term_years - asset_value * crat_payout_rate * crat_term_years`.
- `estimated_income_tax_deduction = projected_charitable_remainder * charitable_deduction_rate`.
- `mortality_inclusion_risk = TERM_SURVIVAL_REQUIRED`.
- `family_transfer_fit` for CRAT is `LOW` when family transfer is the dominant goal; otherwise use `MODERATE` unless the facts strongly show CRAT is family-transfer aligned.

Do not simulate GRAT/CRAT annuity payments year-by-year; subtract the simple total payout shown above.

## Estate Liquidity Action Plan

Combine the shared estate context, ILIT metrics, and trust-transfer metrics.

- If ILIT risk is low and GRAT is preferred: `primary_action = COMBINE_ILIT_AND_GRAT`, `sequencing = ILIT_FIRST_THEN_GRAT`.
- If CRAT is preferred: use `CRAT_WITH_LIQUIDITY_REVIEW` and `TRUST_DECISION_FIRST`.
- If ILIT has a premium gap or lookback issue: use `ILIT_WITH_EXEMPTION_REVIEW` or the nearest template action and `ILIT_FIRST_THEN_ATTORNEY_REVIEW`.
- Always sort `action_set` alphabetically.
- Include `ATTORNEY_DRAFT_REVIEW` for estate-liquidity action plans, plus `ILIT_CRUMMEY_NOTICE_CYCLE`, `GRAT_FOR_APPRECIATING_SHARES` or `CRAT_FOR_CHARITABLE_REMAINDER`, and `LIFETIME_EXEMPTION_ALLOCATION` when a premium gap or exemption allocation is needed.

## Pitfalls

- Do not use stale CRM values when signed profile facts exist.
- Do not reduce Roth conversion years just because RMDs start soon.
- Do not apply only one estate exemption to married households.
- Do not use the CRAT asset value for the charitable deduction; use projected charitable remainder.
- Do not use death benefit as ILIT-only `tax_liquidity_support`.
- Keep JSON numbers as numbers, dates as `YYYY-MM-DD`, and output no prose outside JSON.
