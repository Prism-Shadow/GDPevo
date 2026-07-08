---
name: reflect-3
description: Use this skill for private wealth advisory structured JSON tasks that require reading a staged prompt/memo/template, querying the advisory API, resolving conflicting client/source records, and computing Roth conversion/RMD, ILIT Crummey, GRAT/CRAT, or estate-liquidity planning outputs. Use whenever the user mentions private wealth advisory clients, Roth conversions, RMDs, ILITs, Crummey notices, life insurance estate liquidity, GRATs, CRATs, trust-transfer comparisons, or asks for a final JSON object from advisory API records.
---

# Reflect-3 Advisory Planning

## Core Workflow

1. Read the staged `prompt.txt`, request memo, and `answer_template.json`. Extract the client id, horizon year, required top-level keys, allowed enum values, date format, rounding rules, and any ordering constraints.
2. Query only the advisory API records needed for the requested analysis:
   - Client profile: `/api/clients/<client_id>`
   - Source facts: `/api/source-documents?client_id=<client_id>`
   - Retirement account/RMD work: `/api/retirement-accounts?client_id=<client_id>`, `/api/rmd-factors`, `/api/policies/tax`
   - ILIT/life insurance work: `/api/life-insurance?client_id=<client_id>`, `/api/policies/tax`
   - GRAT/CRAT work: `/api/trust-candidates?client_id=<client_id>`, `/api/policies/tax`
3. Resolve sources before doing math. Prefer the current signed profile for household facts, filing status, age, income, marginal tax rate, beneficiary count, liquid assets, and client goals when it is complete. Use custodian/account exports for retirement balances, returns, RMD start ages, and conversion-year recommendations. Use structured life-insurance records for policy economics, mapped to the closest allowed source enum. Use trust-candidate records for transfer economics, with attorney memo as the closest allowed asset-source enum when no structured enum exists. Treat stale CRM notes as fallback only.
4. Compute with unrounded intermediate values and round USD outputs to cents at the end. Return JSON numbers, not strings. Return only the JSON object.

## Roth Conversion and RMD

Use the signed profile plus custodian retirement account. Let:

- `annual_room = max(0, conversion_bracket_targets[filing_status] - annual_non_ira_income)`
- `conversion_years = recommended_conversion_years`
- `conversion_years_positive = conversion_years` when `annual_room > 0`, otherwise `0`
- `first_rmd_year = planning_year + max(0, rmd_start_age - current_age)`

Simulate baseline and conversion cases year by year, inclusive through the horizon. The ordering matters:

```text
for each year:
  if conversion case and year is inside the conversion schedule:
    conversion = min(annual_room, traditional_balance)
    traditional_balance -= conversion
    roth_balance += conversion
    conversion_tax += conversion * marginal_tax_rate

  if age_for_year >= rmd_start_age:
    rmd = traditional_balance / rmd_factor[age_for_year]
    traditional_balance -= rmd
    rmd_tax += rmd * marginal_tax_rate

  traditional_balance *= (1 + expected_return)
  roth_balance *= (1 + expected_return)
```

Baseline uses the same RMD-then-growth loop without conversions. Include any starting Roth balance in both scenarios. `rmd_tax_savings_through_horizon = baseline_rmd_tax - conversion_rmd_tax`; do not net conversion taxes against RMD-tax savings.

Qualitative labels:

- Use `STAGED_ROTH_CONVERSION` when there is bracket room and liquidity to pay conversion tax.
- Use `SUITABLE` when bracket room is positive and liquidity is adequate, even if RMDs start soon.
- Use `RMD_NEAR_TERM` when the first RMD year is the planning year or next year; otherwise use `TAX_BRACKET_MANAGEMENT` unless liquidity is the real constraint.
- Use `MIXED_TAXABLE_AND_TAX_FREE` when both projected traditional and Roth balances remain material.

## ILIT and Crummey Funding

Use the signed profile beneficiary count and current-year annual gift exclusion:

```text
annual_exclusion_capacity = annual_gift_exclusion[current_year] * beneficiary_count
premium_gap = max(0, annual_premium - annual_exclusion_capacity)
notices_required = beneficiary_count
```

Do not double exclusion capacity for a married household unless the staged records explicitly say gift-splitting is part of the plan.

Crummey administration dates:

- `contribution_date`: planned contribution date from the policy record.
- `notice_due_date`: five business days after contribution.
- `withdrawal_window_end`: 30 calendar days after the notice due date.
- `earliest_premium_payment_date`: the next calendar day after the withdrawal window ends.
- `dedicated_bank_account_required`: `true`.

Risk and action mapping:

- New ILIT-owned policy with no premium gap: `FUND_WITH_CRUMMEY_NOTICES`, `SUITABLE_WITH_ADMINISTRATION`, `LOW_IF_FORMALITIES_MET`.
- Premium gap only: use lifetime exemption for the shortfall and flag `EXCLUSION_SHORTFALL`.
- Existing policy transfer only: disclose/handle the three-year lookback and flag `THREE_YEAR_LOOKBACK`.
- Existing transfer plus premium gap: combine both risks.

Estate impact:

- `projected_outside_estate_if_implemented` is the death benefit expected outside the estate if implemented.
- When a liquidity-support field is requested, use `min(death_benefit, estate_tax_exposure)`.
- Map structured policy records to the closest allowed policy-source enum, usually `CUSTODIAN_EXPORT` when the template has no life-insurance-specific source enum.

## Estate Liquidity

Use current tax policy constants:

```text
taxable_estate = max(0, estate_value - estate_tax_exemption[current_year])
estate_tax_exposure = taxable_estate * estate_tax_rate
liquidity_gap_before_planning = max(0, estate_tax_exposure - liquid_assets)
```

For combined action plans:

- Prefer `COMBINE_ILIT_AND_GRAT` when a low-risk ILIT and family-transfer trust strategy both fit.
- Use `ILIT_FIRST_THEN_GRAT` for new ILIT funding plus a GRAT transfer.
- Add `ATTORNEY_DRAFT_REVIEW` for attorney-coordination action plans.
- Add `ILIT_CRUMMEY_NOTICE_CYCLE` when funding an ILIT.
- Add `GRAT_FOR_APPRECIATING_SHARES` or `CRAT_FOR_CHARITABLE_REMAINDER` according to the trust recommendation.
- Add `LIFETIME_EXEMPTION_ALLOCATION` only when a premium shortfall, transfer lookback, or exemption allocation is part of the recommended action.
- Sort `action_set` alphabetically exactly as requested by the template.

## GRAT and CRAT

Use the trust-candidate economics and current tax policy. Prefer GRAT when the controlling current goal source shows high family-transfer priority and low or moderate philanthropic intent. Prefer CRAT only when the controlling current source clearly prioritizes philanthropy. Do not let an older CRM philanthropy note override a complete current signed profile.

GRAT projection:

```text
balance = asset_value
annual_annuity = asset_value * grat_annuity_rate
for each GRAT term year:
  balance = balance * (1 + expected_growth_rate) - annual_annuity
projected_remainder_to_heirs = max(0, balance)
estimated_estate_tax_reduction = projected_remainder_to_heirs * estate_tax_rate
```

CRAT projection:

```text
term = min(crat_term_years, max_crat_term_years)
balance = asset_value
annual_payout = asset_value * crat_payout_rate
for each CRAT term year:
  balance = balance * (1 + expected_growth_rate) - annual_payout
projected_charitable_remainder = max(0, balance)
estimated_income_tax_deduction = asset_value * charitable_deduction_rate
```

Set `mortality_inclusion_risk` to `TERM_SURVIVAL_REQUIRED` for GRATs. Use `SECONDARY_CHARITABLE_TOOL` when GRAT is preferred, and `SECONDARY_FAMILY_TRANSFER_TOOL` when CRAT is preferred.

## Common Pitfalls

- Do not use stale CRM facts when a signed profile supplies the same field.
- Do not omit starting Roth balances from Roth/RMD legacy projections.
- Do not take RMDs after growth; take RMDs before the annual growth step.
- Do not subtract conversion tax from RMD-tax savings.
- Do not report gross estate as `taxable_estate`; use estate value above the current exemption.
- Do not add unsorted or extra action-set enums.
- Do not include prose outside the final JSON object.
