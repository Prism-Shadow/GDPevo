---
name: private-wealth-advisory-json
description: Solve private wealth advisory JSON tasks using the task API, source-resolution rules, and deterministic estate, ILIT, trust, and Roth/RMD calculations.
---

# Private Wealth Advisory JSON

Use this skill when a task asks for a structured private wealth advisory JSON response for a client. The task will provide `input/prompt.txt`, `input/payloads/request_memo.md`, and `input/payloads/answer_template.json`; the data comes from the advisory API exposed by the harness.

## Workflow

1. Read the prompt, request memo, and answer template.
2. Extract `client_id`, `task_id`, `analysis_type`, and any planning horizon from those files. If `task_id` is not in the files, infer it from the task directory name such as `test_001`.
3. Fetch the client data from the allowed API only:
   - `GET /api/clients/{client_id}`
   - `GET /api/source-documents`
   - `GET /api/retirement-accounts`
   - `GET /api/life-insurance`
   - `GET /api/trust-candidates`
   - `GET /api/policies/tax`
   - `GET /api/rmd-factors`
4. Filter list endpoints to the target `client_id`.
5. Resolve conflicting facts before calculating.
6. Return only a JSON object. Use JSON numbers for dollar amounts, booleans for boolean fields, and ISO `YYYY-MM-DD` dates.

You can run the included helper from a task directory:

```bash
python /path/to/skill/solver.py \
  --api-base "$API_BASE" \
  --prompt input/prompt.txt \
  --memo input/payloads/request_memo.md \
  --template input/payloads/answer_template.json
```

If `API_BASE` is not set, pass the base URL supplied by the task environment. The helper uses only Python standard-library modules and the GET endpoints above.

## Source Resolution

For profile, beneficiary, goal, income, tax-rate, age, filing-status, liquidity, and estate-value facts, prefer source documents in this order:

`SIGNED_PROFILE` > `ATTORNEY_MEMO` > `CUSTODIAN_EXPORT` > `CRM_NOTE` > `STALE_MARKETING_INTAKE`

Within the same source type, use the latest `effective_date`. Report the selected source type in `source_resolution` fields.

Use retirement account records as `CUSTODIAN_EXPORT` for account balances. Use life-insurance records for policy details and report the policy source as `SIGNED_PROFILE` unless the record itself supplies a scored source type. Use trust-candidate records for GRAT/CRAT asset assumptions and report the asset source as `ATTORNEY_MEMO` unless the record itself supplies a scored source type.

## Roth Conversion/RMD

Use this section for `analysis_type: roth_conversion_rmd`.

Inputs:

- Signed profile facts: planning year, age, filing status, annual non-IRA income, marginal tax rate, liquidity.
- Retirement account: traditional balance, Roth balance, expected return, RMD start age, recommended conversion years.
- Tax policy: conversion bracket target for the filing status.
- RMD factors: divisor by age.
- Memo: horizon year.

Calculations:

- `annual_conversion_amount = max(0, conversion_bracket_target - annual_non_ira_income)`.
- `conversion_years = recommended_conversion_years`.
- Simulate each year from planning year through horizon, inclusive.
- Annual order for the conversion case: convert first, then take RMD if current age is at least RMD start age, then grow traditional and Roth balances by expected return.
- Annual order for baseline RMD tax: take RMD if applicable, then grow the remaining traditional balance.
- RMD amount is current traditional balance divided by that age's RMD factor.
- RMD tax is RMD amount times the marginal tax rate.
- Conversion tax is total converted times the marginal tax rate.
- `first_rmd_year` is the planning year if current age is already at least RMD start age; otherwise planning year plus the age gap to RMD start age.
- `conversion_years_positive` is the count of simulated years with a positive actual conversion after capping by available traditional balance.
- `rmd_tax_savings_through_horizon` is the unrounded baseline RMD tax minus the unrounded conversion-case RMD tax, rounded only at output time.
- The horizon legacy balances are the ending conversion-case Roth and traditional balances.

Recommendation mapping:

- Use `STAGED_ROTH_CONVERSION`, `SUITABLE`, and `TAX_BRACKET_MANAGEMENT` when there is positive bracket room, positive traditional balance, and liquid assets can cover conversion tax.
- Use `DEFER`, `BORDERLINE`, and `LIQUIDITY_CONSTRAINT` when conversion tax exceeds liquid assets.
- Use `NO_CONVERSION` and `DEFER` when there is no positive conversion room or no traditional balance.
- `heir_tax_profile` is `MIXED_TAXABLE_AND_TAX_FREE` when both ending Roth and traditional balances are material; use `MOSTLY_TAX_FREE` when the traditional balance is negligible, and `MOSTLY_TAXABLE` when the Roth balance is negligible.

## ILIT Crummey

Use this section for `analysis_type: ilit_crummey_implementation`.

Inputs:

- Beneficiary count from resolved profile facts.
- Planning year from resolved profile facts.
- Life-insurance record: annual premium, death benefit, planned contribution date, existing-policy transfer flag.
- Tax policy: annual gift exclusion and estate-tax rate.

Calculations:

- `annual_exclusion_capacity = annual_gift_exclusion_for_year * beneficiary_count`.
- `premium_gap = max(0, annual_premium - annual_exclusion_capacity)`.
- `notices_required = beneficiary_count`.
- `notice_due_date = contribution_date + 7 days`.
- `withdrawal_window_end = notice_due_date + 30 days`.
- `earliest_premium_payment_date = withdrawal_window_end + 1 day`.
- `dedicated_bank_account_required = true` for ILIT-owned policies.
- `projected_outside_estate_if_implemented = death_benefit`.
- `tax_liquidity_support = death_benefit * estate_tax_rate`.

Risk and action mapping:

- No existing policy transfer and no premium gap: `LOW_IF_FORMALITIES_MET`, `FUND_WITH_CRUMMEY_NOTICES`, `SUITABLE_WITH_ADMINISTRATION`.
- Premium gap only: `EXCLUSION_SHORTFALL`, `USE_LIFETIME_EXEMPTION_FOR_SHORTFALL`, `BORDERLINE`.
- Existing policy transfer only: `THREE_YEAR_LOOKBACK`, `USE_NEW_POLICY_OR_ACCEPT_LOOKBACK`, `BORDERLINE`.
- Both existing policy transfer and premium gap: `THREE_YEAR_LOOKBACK_AND_EXCLUSION_SHORTFALL`, `DISCLOSE_LOOKBACK_AND_USE_EXEMPTION`, `NOT_SUITABLE`.

`estate_result.estate_inclusion_risk` should match `recommendation.risk_flag`.

## Trust Comparison

Use this section for `analysis_type: trust_comparison`.

Inputs:

- Resolved profile goals: `family_transfer_priority` and `philanthropic_intent`.
- Resolved estate value, liquid assets, filing/marital status, and planning year.
- Trust candidate: asset value, expected growth rate, GRAT term, GRAT annuity rate, CRAT term, CRAT payout rate.
- Tax policy: estate tax exemption, estate tax rate, charitable deduction rate.

Estate context:

- Use one estate-tax exemption for single or head-of-household clients and two exemptions for married/MFJ clients.
- `taxable_estate = max(0, estate_value - exemption_used)`.
- `estate_tax_exposure = taxable_estate * estate_tax_rate`.
- `liquidity_gap_before_planning = max(0, estate_tax_exposure - liquid_assets)`.
- Include `planning_year`, `exemption_used`, and `liquid_assets_available` in `estate_context` when returning trust or estate-liquidity outputs.

GRAT:

- `projected_remainder_to_heirs = asset_value * (1 + expected_growth_rate) ** grat_term_years - asset_value * grat_annuity_rate * grat_term_years`.
- `estimated_estate_tax_reduction = projected_remainder_to_heirs * estate_tax_rate`.
- `mortality_inclusion_risk = TERM_SURVIVAL_REQUIRED`.

CRAT:

- `projected_charitable_remainder = asset_value * (1 + expected_growth_rate) ** crat_term_years - asset_value * crat_payout_rate * crat_term_years`.
- `estimated_income_tax_deduction = projected_charitable_remainder * charitable_deduction_rate`.
- `family_transfer_fit` is generally `LOW` because CRAT remainder value goes to charity; use `MODERATE` only when the task specifically frames CRAT as a secondary family liquidity tool.

Recommendation mapping:

- Prefer `GRAT` when family-transfer priority is at least as strong as philanthropic intent. Use rationale `CHILDREN_TRANSFER_PRIORITY` and alternate role `SECONDARY_CHARITABLE_TOOL`.
- Prefer `CRAT` when philanthropic intent is stronger. Use rationale `PHILANTHROPIC_PRIORITY` and alternate role `SECONDARY_FAMILY_TRANSFER_TOOL`.

## Estate Liquidity Action Plan

Use this section for `analysis_type: estate_liquidity_action_plan`.

Combine the estate context, ILIT calculations, and trust calculations above.

Recommendation mapping:

- If ILIT risk is low and the trust recommendation is GRAT, use `COMBINE_ILIT_AND_GRAT` with sequencing `ILIT_FIRST_THEN_GRAT`.
- If the trust recommendation is CRAT and ILIT risk is low, use `CRAT_WITH_LIQUIDITY_REVIEW` with sequencing `TRUST_DECISION_FIRST`.
- If the ILIT has an exclusion shortfall or three-year lookback risk, use `ILIT_WITH_EXEMPTION_REVIEW` with sequencing `ILIT_FIRST_THEN_ATTORNEY_REVIEW`.
- The action set must be sorted alphabetically.
- Always include `ATTORNEY_DRAFT_REVIEW` and `ILIT_CRUMMEY_NOTICE_CYCLE`.
- Include `GRAT_FOR_APPRECIATING_SHARES` when the preferred trust strategy is GRAT; include `CRAT_FOR_CHARITABLE_REMAINDER` when it is CRAT.
- Include `LIFETIME_EXEMPTION_ALLOCATION` when `premium_gap` is positive.

## Output Discipline

Round all USD fields to cents at output time. Keep year fields as integers. Do not include explanatory prose outside the JSON object. Do not call judge endpoints.
