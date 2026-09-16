---
name: wealth-advisory-api-planning
description: Solve private wealth advisory task-group API planning outputs as schema-conforming JSON. Use when Codex must read a local prompt, request memo, and answer_template.json, fetch advisory records from the provided API, resolve conflicting client/source data, and compute Roth conversion/RMD, ILIT Crummey, GRAT/CRAT, or estate-liquidity action-plan fields.
---

# Wealth Advisory API Planning

## Workflow

1. Read the task prompt, `input/payloads/request_memo.md`, and `input/payloads/answer_template.json`.
2. Extract `client_id`, engagement type, planning horizon if supplied, and the required output fields. Set `task_id` from the current task directory name unless the harness provides it directly.
3. Use `API_BASE` if set; otherwise read the local environment access note for the base URL. Fetch only documented GET endpoints. Never call a judge endpoint.
4. Fetch:
   - `/api/clients/{client_id}`
   - `/api/source-documents?client_id={client_id}`
   - `/api/retirement-accounts?client_id={client_id}`
   - `/api/life-insurance?client_id={client_id}`
   - `/api/trust-candidates?client_id={client_id}`
   - `/api/policies/tax`
   - `/api/rmd-factors`
5. Compute every requested field from the API records and policy constants. Return only one JSON object, with JSON numbers for amounts and booleans as booleans.

Round USD outputs to cents at final assignment. For savings/differences, subtract unrounded values first, then round the result.

## Source Resolution

Use source-specific controls instead of blindly taking the newest record.

- Household profile facts: prefer `SIGNED_PROFILE` for age, planning year, filing status, marital status, annual non-IRA income, marginal tax rate, beneficiary count, liquid assets, estate value, and client goals.
- Retirement account facts: use the `CUSTODIAN_EXPORT` account record for traditional balance, Roth balance, expected return, RMD start age, and recommended conversion years.
- ILIT policy facts: use the life-insurance endpoint for premium, death benefit, planned contribution date, owner, and transfer flag. If the output asks for a policy source and the policy record has no source type, use `SIGNED_PROFILE` when signed household facts control implementation assumptions; otherwise use the most specific attorney/policy source present.
- Trust transfer asset facts: use the trust-candidate endpoint for asset value, growth, term, annuity, and payout inputs. If the output asks for the controlling trust asset source and the endpoint has no source type, use `ATTORNEY_MEMO` for attorney-led trust/asset candidates.
- Goals and beneficiaries: prefer `SIGNED_PROFILE`; use attorney or CRM facts only when signed facts are absent.

Populate `source_resolution` with the source type that controlled that category, not the endpoint name.

## Estate Context

For trust and estate-liquidity outputs:

- `planning_year`: controlling profile planning year.
- `exemption_used`: policy estate-tax exemption for the planning year, doubled for married/MFJ households and single for single filers.
- `taxable_estate = max(estate_value - exemption_used, 0)`.
- `estate_tax_exposure = taxable_estate * estate_tax_rate`.
- `liquid_assets_available`: controlling liquid assets.
- `liquidity_gap_before_planning = max(estate_tax_exposure - liquid_assets_available, 0)`.

Include these context fields when the estate-context object is part of the observed task pattern, even if the template lists only a subset.

## Roth Conversion And RMD

Use this for `analysis_type: roth_conversion_rmd`.

Inputs:

- Profile: planning year, age, filing status, annual non-IRA income, marginal tax rate, liquid assets.
- Policy: conversion bracket target for the filing status.
- Account: traditional balance, Roth balance, expected return, RMD start age, recommended conversion years.
- Memo/template: horizon year.

Conversion plan:

- `annual_conversion_amount = max(bracket_target - annual_non_ira_income, 0)`, capped only if total planned conversions would exceed the remaining traditional balance.
- `first_conversion_year = planning_year` when the annual amount is positive.
- `conversion_years = recommended_conversion_years`.
- `conversion_years_positive` is the count of planned years with a positive conversion amount.
- `total_converted = annual_conversion_amount * conversion_years_positive`, capped by available traditional balance.
- `total_conversion_tax = total_converted * marginal_tax_rate`.

RMD simulation through the horizon is year-inclusive. Maintain separate baseline and conversion paths.

For each year from `planning_year` through `horizon_year`:

1. Compute current age as `age + (year - planning_year)`.
2. In the conversion path only, before any RMD, convert the planned annual amount while the year is within the planned conversion window and traditional balance remains.
3. If current age is at least the RMD start age, compute `rmd = traditional_balance / rmd_factor[current_age]`, add `rmd * marginal_tax_rate` to that path's RMD tax, and subtract the RMD from traditional balance.
4. Grow ending traditional and Roth balances by `1 + expected_return`.

Outputs:

- `first_rmd_year = planning_year + max(rmd_start_age - age, 0)`.
- `baseline_rmd_tax_through_horizon`: baseline accumulated RMD tax.
- `conversion_rmd_tax_through_horizon`: conversion-path accumulated RMD tax, excluding conversion tax.
- `rmd_tax_savings_through_horizon`: baseline RMD tax minus conversion-path RMD tax.
- Horizon legacy balances come from the conversion path after the horizon year's growth.
- `heir_tax_profile`: use `MIXED_TAXABLE_AND_TAX_FREE` when both Roth and traditional balances remain material, `MOSTLY_TAX_FREE` when the horizon balance is predominantly Roth, and `MOSTLY_TAXABLE` when little or no Roth balance remains.

Recommendation:

- Choose `STAGED_ROTH_CONVERSION` and `SUITABLE` when bracket headroom is positive, conversion tax is supportable from liquid assets, and RMD tax savings are positive.
- Use `LIQUIDITY_CONSTRAINT` when projected conversion taxes cannot be paid from available liquid assets.
- Use `RMD_NEAR_TERM` only when near-term RMD timing is the dominant reason to defer or reduce the plan; otherwise use `TAX_BRACKET_MANAGEMENT` for suitable staged conversions.
- Use `DEFER`/`NO_CONVERSION` when there is no bracket headroom or the simulation does not support conversion.

## ILIT Crummey Implementation

Use this for `analysis_type: ilit_crummey_implementation` and for ILIT sections in combined estate plans.

Inputs:

- Planning year and beneficiary count from the controlling profile.
- Annual gift exclusion and estate tax rate from policy constants.
- Policy death benefit, premium, contribution date, and existing-transfer flag from life insurance.

Gift and administration calculations:

- `annual_exclusion_per_beneficiary` is the policy annual exclusion for the planning year.
- `annual_exclusion_capacity = annual_exclusion_per_beneficiary * beneficiary_count`.
- `premium_gap = max(annual_premium - annual_exclusion_capacity, 0)`.
- `notices_required = beneficiary_count`.
- `notice_due_date = contribution_date + 7 calendar days`.
- `withdrawal_window_end = notice_due_date + 30 calendar days`.
- `earliest_premium_payment_date = withdrawal_window_end + 1 calendar day`.
- `dedicated_bank_account_required = true` for ILIT funding cycles.

Risk flag:

- No premium gap and no existing policy transfer: `LOW_IF_FORMALITIES_MET`.
- Premium gap only: `EXCLUSION_SHORTFALL`.
- Existing policy transfer only: `THREE_YEAR_LOOKBACK`.
- Both issues: `THREE_YEAR_LOOKBACK_AND_EXCLUSION_SHORTFALL`.

Recommendation mapping:

- Low risk: `FUND_WITH_CRUMMEY_NOTICES`, `SUITABLE_WITH_ADMINISTRATION`.
- Premium gap only: `USE_LIFETIME_EXEMPTION_FOR_SHORTFALL`, usually `BORDERLINE`.
- Existing transfer only: `USE_NEW_POLICY_OR_ACCEPT_LOOKBACK`, usually `BORDERLINE`.
- Both issues: `DISCLOSE_LOOKBACK_AND_USE_EXEMPTION`, usually `NOT_SUITABLE` or `BORDERLINE` depending on template choices and facts.

Estate result:

- `estate_inclusion_risk` equals the risk flag.
- `projected_outside_estate_if_implemented` is the death benefit when the ILIT is implemented, with the risk flag disclosing inclusion concerns.
- `tax_liquidity_support = death_benefit * estate_tax_rate`.

## GRAT Versus CRAT

Use this for `analysis_type: trust_comparison` and trust-transfer sections in combined estate plans.

Inputs:

- Client goals from the controlling profile: rank `low < moderate < high` for family transfer priority and philanthropic intent.
- Estate context as above.
- Trust candidate asset value, growth rate, GRAT term, GRAT annuity rate, CRAT term, and CRAT payout rate.
- Policy estate tax rate and charitable deduction rate.

GRAT:

- `projected_remainder_to_heirs = asset_value * (1 + expected_growth_rate) ^ grat_term_years - asset_value * grat_annuity_rate * grat_term_years`.
- `estimated_estate_tax_reduction = projected_remainder_to_heirs * estate_tax_rate`.
- `mortality_inclusion_risk = TERM_SURVIVAL_REQUIRED`.

CRAT:

- `projected_charitable_remainder = asset_value * (1 + expected_growth_rate) ^ crat_term_years - asset_value * crat_payout_rate * crat_term_years`.
- `estimated_income_tax_deduction = projected_charitable_remainder * charitable_deduction_rate`.
- `family_transfer_fit` is `LOW` when family transfer priority dominates philanthropy, `HIGH` when philanthropy dominates, and `MODERATE` when the goals are balanced.

Recommendation:

- Prefer `GRAT` when family transfer priority is at least as strong as philanthropic intent; use `CHILDREN_TRANSFER_PRIORITY` and set CRAT as `SECONDARY_CHARITABLE_TOOL`.
- Prefer `CRAT` when philanthropic intent clearly dominates; use `PHILANTHROPIC_PRIORITY` and set GRAT as `SECONDARY_FAMILY_TRANSFER_TOOL`.

## Estate Liquidity Action Plan

Use this for `analysis_type: estate_liquidity_action_plan`.

Combine the estate context, ILIT, and GRAT/CRAT calculations.

Recommendation:

- Use `COMBINE_ILIT_AND_GRAT` when the ILIT is administratively workable and GRAT is the preferred trust strategy.
- Use `CRAT_WITH_LIQUIDITY_REVIEW` when CRAT is preferred because philanthropic intent dominates.
- Use `ILIT_WITH_EXEMPTION_REVIEW` when ILIT premium gaps, transfer lookback, or exemption allocation issues dominate the plan.

Sequencing:

- `ILIT_FIRST_THEN_GRAT` for workable ILIT plus GRAT strategy.
- `TRUST_DECISION_FIRST` when CRAT or trust selection must be resolved before implementation.
- `ILIT_FIRST_THEN_ATTORNEY_REVIEW` when ILIT formalities or exemption issues need attorney review before broader execution.

Action set:

- Always sort alphabetically.
- Include `ATTORNEY_DRAFT_REVIEW` for attorney-coordinated estate liquidity plans.
- Include `ILIT_CRUMMEY_NOTICE_CYCLE` when an ILIT premium cycle is part of the plan.
- Include `LIFETIME_EXEMPTION_ALLOCATION` when premium gaps or exemption use must be addressed.
- Include `GRAT_FOR_APPRECIATING_SHARES` when GRAT is preferred.
- Include `CRAT_FOR_CHARITABLE_REMAINDER` when CRAT is preferred.

## Final JSON Checks

- Include every required top-level key from the template.
- Use only enum values allowed by the template.
- Keep `action_set` alphabetically sorted.
- Use ISO `YYYY-MM-DD` dates.
- Do not include explanatory prose, Markdown, citations, or code fences outside the JSON.
