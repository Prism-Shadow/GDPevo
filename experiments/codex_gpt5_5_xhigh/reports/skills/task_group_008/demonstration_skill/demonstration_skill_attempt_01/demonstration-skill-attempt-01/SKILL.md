---
name: demonstration-skill-attempt-01
description: Solve private wealth advisory input/output tasks that require reading a request memo and answer template, querying the local advisory API, resolving conflicting client sources, calculating Roth/RMD, ILIT Crummey, GRAT/CRAT, and estate-liquidity outputs, and returning strict JSON.
---

# Private Wealth Advisory JSON SOP

## Intake

1. Read the task prompt, request memo, and `answer_template.json`.
2. Extract `client_id`, engagement type, planning year, horizon year if stated, and the required output shape.
3. Query the advisory API using `API_BASE`:
   - `/api/clients/<client_id>` for household demographics, estate value, liquid assets, filing status.
   - `/api/source-documents?client_id=<client_id>` for signed profile, attorney memo, CRM/stale facts.
   - `/api/retirement-accounts?client_id=<client_id>` for IRA balances, return, RMD age, conversion years.
   - `/api/life-insurance?client_id=<client_id>` for ILIT policy/premium dates and death benefit.
   - `/api/trust-candidates?client_id=<client_id>` for GRAT/CRAT asset and payout assumptions.
   - `/api/policies/tax` for gift exclusion, estate exemption/rate, conversion bracket targets, CRAT constants.
   - `/api/rmd-factors` for age-based RMD divisors.
4. Return only the final JSON object. Use JSON numbers for money, rounded to cents at final output only. Use ISO `YYYY-MM-DD` dates.

## Source Resolution

Use source-of-truth by field domain; do not average conflicting records.

- Profile facts, beneficiaries, income, marginal tax rate, client goals: prefer `SIGNED_PROFILE`, then `ATTORNEY_MEMO`, then `CUSTODIAN_EXPORT`, then `CRM_NOTE`, then `STALE_MARKETING_INTAKE`.
- Retirement account facts: prefer `CUSTODIAN_EXPORT`, then `SIGNED_PROFILE`, then `CRM_NOTE`.
- Trust candidate asset assumptions: use the trust-candidate endpoint; report `ATTORNEY_MEMO` as controlling asset source unless a more explicit source type is present.
- Life-insurance policy facts: use the life-insurance endpoint; report the policy source indicated by the endpoint/source documents, usually `SIGNED_PROFILE` for proposed ILIT policy terms.
- Fill each `source_resolution` field with the source type that actually controlled that output family.

## Field Families

- `task_id`: derive from the task context/folder naming convention, such as `train_###` or `test_###`.
- `client_id`: exact stable client ID from the request.
- `analysis_type`: exact enum from the answer template.
- Follow the template's required top-level keys and enum values exactly. Include template-family context fields such as `planning_year`, `exemption_used`, or `liquid_assets_available` when the requested output family expects estate context.
- For sorted lists such as `action_set`, sort enum strings alphabetically.

## Roth Conversion And RMD

Use signed profile facts for `age`, `planning_year`, `filing_status`, `annual_non_ira_income`, and `marginal_tax_rate`. Use custodian export for IRA balances, expected return, RMD start age, and recommended conversion years.

Calculations:

- `first_rmd_year = planning_year + (rmd_start_age - age)`.
- `annual_conversion_amount = max(0, conversion_bracket_targets[filing_status] - annual_non_ira_income)`.
- `conversion_years = recommended_conversion_years`.
- `conversion_years_positive = conversion_years` if annual conversion is positive, else `0`.
- `total_converted = annual_conversion_amount * conversion_years_positive`.
- `total_conversion_tax = total_converted * marginal_tax_rate`.
- Baseline RMD simulation: start with traditional balance. For each year from planning year through horizon, grow the balance first when `year > planning_year`; if current age is at least RMD start age, compute `rmd = balance / rmd_factor[age]`, add `rmd * marginal_tax_rate` to tax, then subtract the RMD.
- Conversion simulation: start with traditional and Roth balances. Each year, grow both balances first when `year > planning_year`; if inside positive conversion years, move `min(annual_conversion_amount, traditional_balance)` from traditional to Roth; then compute same-year RMD/tax from the post-conversion traditional balance when applicable.
- `rmd_tax_savings_through_horizon = baseline_rmd_tax - conversion_rmd_tax`.
- After the horizon-year RMD/tax step, apply one additional year of expected return to both balances for `projected_roth_balance_horizon` and `projected_traditional_balance_horizon`.

Recommendation defaults: use `STAGED_ROTH_CONVERSION` and `SUITABLE` when positive bracket capacity exists and the staged plan reduces RMD tax. Use `TAX_BRACKET_MANAGEMENT` for normal positive-capacity conversions; reserve `LIQUIDITY_CONSTRAINT`, `RMD_NEAR_TERM`, `DEFER`, or `NO_CONVERSION` for cases where the data shows little/no bracket room, liquidity strain, or no useful runway.

## ILIT Crummey Implementation

Use signed beneficiary count and policy/tax endpoints.

- `annual_exclusion_per_beneficiary = annual_gift_exclusion[planning_year]`.
- `annual_exclusion_capacity = annual_exclusion_per_beneficiary * beneficiary_count`.
- `premium_gap = max(0, annual_premium - annual_exclusion_capacity)`.
- `notices_required = beneficiary_count`.
- `contribution_date = planned_contribution_date`.
- `notice_due_date = contribution_date + 7 calendar days`.
- `withdrawal_window_end = notice_due_date + 30 calendar days`.
- `earliest_premium_payment_date = withdrawal_window_end + 1 calendar day`.
- `dedicated_bank_account_required = true`.
- `tax_liquidity_support = death_benefit * estate_tax_rate`.

Risk/action mapping:

- No premium gap and no existing policy transfer: `LOW_IF_FORMALITIES_MET`, `FUND_WITH_CRUMMEY_NOTICES`, `SUITABLE_WITH_ADMINISTRATION`.
- Premium gap only: `EXCLUSION_SHORTFALL`, `USE_LIFETIME_EXEMPTION_FOR_SHORTFALL`, usually `BORDERLINE`.
- Existing policy transfer only: `THREE_YEAR_LOOKBACK`, `USE_NEW_POLICY_OR_ACCEPT_LOOKBACK`, usually `BORDERLINE` or `NOT_SUITABLE` depending on the request.
- Both gap and transfer: `THREE_YEAR_LOOKBACK_AND_EXCLUSION_SHORTFALL`, `DISCLOSE_LOOKBACK_AND_USE_EXEMPTION`.

## GRAT, CRAT, And Estate Liquidity

Estate context:

- `exemption_used = estate_tax_exemption[planning_year] * 2` for married/MFJ households, otherwise the single exemption.
- `taxable_estate = max(0, estate_value - exemption_used)`.
- `estate_tax_exposure = taxable_estate * estate_tax_rate`.
- `liquidity_gap_before_planning = max(0, estate_tax_exposure - liquid_assets)`.

Trust projections:

- `grat.projected_remainder_to_heirs = asset_value * (1 + expected_growth_rate) ^ grat_term_years - asset_value * grat_annuity_rate * grat_term_years`.
- `grat.estimated_estate_tax_reduction = projected_remainder_to_heirs * estate_tax_rate`.
- `grat.mortality_inclusion_risk = TERM_SURVIVAL_REQUIRED`.
- `crat.term_years = min(crat_term_years, max_crat_term_years)`.
- `crat.projected_charitable_remainder = asset_value * (1 + expected_growth_rate) ^ crat.term_years - asset_value * crat_payout_rate * crat.term_years`.
- `crat.estimated_income_tax_deduction = projected_charitable_remainder * charitable_deduction_rate`.

Strategy selection:

- Prefer `GRAT` when signed/controlling goals emphasize family or children transfer at least as much as philanthropy. Use `CHILDREN_TRANSFER_PRIORITY`, `SECONDARY_CHARITABLE_TOOL`, and low CRAT family-transfer fit.
- Prefer `CRAT` when philanthropy is the dominant controlling goal. Use `PHILANTHROPIC_PRIORITY` and `SECONDARY_FAMILY_TRANSFER_TOOL`.
- For estate-liquidity action plans, combine ILIT and the preferred trust strategy when both are useful. Include `ATTORNEY_DRAFT_REVIEW`; include `ILIT_CRUMMEY_NOTICE_CYCLE` when an ILIT policy is part of the plan; include `GRAT_FOR_APPRECIATING_SHARES` or `CRAT_FOR_CHARITABLE_REMAINDER` based on the preferred strategy; include `LIFETIME_EXEMPTION_ALLOCATION` when premium gaps or exemption usage require it.

## Common Pitfalls

- Do not use stale CRM or marketing intake facts when a signed profile conflicts.
- Do not use top-level client records for income or marginal tax rate when signed profile facts provide them.
- Do not round during annual simulations; round only final JSON values.
- Do not apply RMDs before same-year Roth conversions in the conversion scenario.
- Do not forget the extra post-horizon growth step for Roth/RMD legacy balances.
- Do not compute CRAT deduction from initial asset value; use projected charitable remainder.
- Do not compound GRAT/CRAT payout deductions; subtract `asset_value * payout_rate * term`.
- Do not emit money as strings or include prose outside the JSON.
