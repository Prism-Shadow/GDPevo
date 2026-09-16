---
name: advisory-planning-json
description: Use this skill for private wealth advisory JSON tasks that mention the advisory API, client records, source documents, retirement accounts, life insurance, trust candidates, tax policy constants, RMD factors, Roth conversion/RMD summaries, ILIT Crummey cycles, GRAT vs CRAT comparisons, or estate liquidity action plans. It fetches the client-specific API records, resolves source conflicts, applies the planning formulas, and returns only the requested JSON object.
---

# Advisory Planning JSON

Use this skill when the user asks for a structured private-wealth advisory output against the task-group advisory API. The common prompt shape asks for a JSON object conforming to `input/payloads/answer_template.json` and provides a local `request_memo.md`.

## Fast Path

Use the bundled solver first:

```bash
python /path/to/skill/scripts/solve_advisory_task.py --task-dir /path/to/task --api-base "$API_BASE"
```

If the task id cannot be derived from the task directory name, pass `--task-id test_001` or the corresponding stable task id. Return the script's JSON output verbatim after checking that it conforms to the template. Do not add prose outside the JSON.

The helper uses only the Python standard library and the allowed advisory API endpoints. It does not contain task-specific client IDs or answer records.

## Manual Workflow

When solving manually, follow this order:

1. Read `input/payloads/request_memo.md`, `input/payloads/answer_template.json`, and the prompt. Extract `client_id`, `task_id`, `analysis_type`, and any planning horizon year.
2. Fetch only records for the requested client:
   - `GET /api/clients/{client_id}`
   - `GET /api/source-documents?client_id={client_id}`
   - For Roth tasks: `GET /api/retirement-accounts?client_id={client_id}` and `GET /api/rmd-factors`
   - For ILIT tasks: `GET /api/life-insurance?client_id={client_id}`
   - For trust tasks: `GET /api/trust-candidates?client_id={client_id}`
   - Always fetch `GET /api/policies/tax`
3. Resolve source conflicts by data domain:
   - Household profile facts, tax rate, filing status, beneficiary count, and planning goals use `SIGNED_PROFILE`.
   - Retirement account balances use `CUSTODIAN_EXPORT`.
   - Trust asset context uses the attorney planning record where the output asks for an asset source.
   - Proposed ILIT policy and beneficiary administration outputs use `SIGNED_PROFILE` for source-resolution fields.
4. Compute values with full precision, then round USD outputs to two decimals as JSON numbers.
5. Return exactly one JSON object with the keys requested by the template. Include the extra estate-context fields shown by the task pattern when relevant: `planning_year`, `exemption_used`, and `liquid_assets_available`.

## Roth Conversion And RMD

Use this for `analysis_type: roth_conversion_rmd`.

- `annual_conversion_amount = max(0, conversion_bracket_targets[filing_status] - annual_non_ira_income)`.
- `conversion_years` comes from the custodian account's `recommended_conversion_years`.
- Conversions occur at the start of each conversion year, beginning in `planning_year`, before RMDs and before annual growth.
- `total_converted` is the sum actually moved from traditional to Roth; `total_conversion_tax = total_converted * marginal_tax_rate`.
- `first_rmd_year = planning_year + max(0, rmd_start_age - current_age)`.
- For each projection year through the horizon:
  - If the year is in the conversion window, move the annual conversion amount from traditional to Roth.
  - If age is at least `rmd_start_age`, compute `RMD = beginning_traditional_balance / rmd_factor[age]`, add `RMD * marginal_tax_rate` to RMD tax, and subtract the RMD from traditional.
  - Grow both remaining traditional and Roth balances by `expected_return`.
- Baseline RMD tax uses the same loop without conversions.
- `rmd_tax_savings_through_horizon = baseline_rmd_tax - conversion_rmd_tax`.
- Use `MIXED_TAXABLE_AND_TAX_FREE` when both Roth and traditional balances remain, `MOSTLY_TAX_FREE` when the traditional balance is essentially depleted, and `MOSTLY_TAXABLE` when no Roth balance remains.
- Recommend `STAGED_ROTH_CONVERSION` with `SUITABLE` and `TAX_BRACKET_MANAGEMENT` when there is positive bracket room and enough liquid assets to pay the annual conversion tax. Use the template's defer or liquidity flags only when the computed data supports them.

## ILIT Crummey Cycle

Use this for `analysis_type: ilit_crummey_implementation`.

- `annual_exclusion_per_beneficiary` comes from `annual_gift_exclusion[planning_year]`.
- `annual_exclusion_capacity = annual_exclusion_per_beneficiary * beneficiary_count`.
- `premium_gap = max(0, annual_premium - annual_exclusion_capacity)`.
- `notices_required = beneficiary_count`.
- `contribution_date` is the policy's `planned_contribution_date`.
- `notice_due_date = contribution_date + 7 days`.
- `withdrawal_window_end = notice_due_date + 30 days`.
- `earliest_premium_payment_date = withdrawal_window_end + 1 day`.
- A dedicated bank account is required.
- `tax_liquidity_support = death_benefit * estate_tax_rate`.
- If there is no existing policy transfer and no premium gap, use `FUND_WITH_CRUMMEY_NOTICES`, `SUITABLE_WITH_ADMINISTRATION`, and `LOW_IF_FORMALITIES_MET`. Use the shortfall and three-year-lookback enum values when the policy data shows a gap or existing-policy transfer.

## GRAT/CRAT Trust Comparison

Use this for `analysis_type: trust_comparison`.

Estate context:

- `exemption_used = estate_tax_exemption[planning_year] * 2` for `MFJ`, otherwise use one exemption.
- `taxable_estate = max(0, estate_value - exemption_used)`.
- `estate_tax_exposure = taxable_estate * estate_tax_rate`.
- `liquidity_gap_before_planning = max(0, estate_tax_exposure - liquid_assets)`.

Trust values:

- `projected_remainder_to_heirs = asset_value * (1 + expected_growth_rate) ^ grat_term_years - asset_value * grat_annuity_rate * grat_term_years`.
- `estimated_estate_tax_reduction = projected_remainder_to_heirs * estate_tax_rate`.
- `projected_charitable_remainder = asset_value * (1 + expected_growth_rate) ^ crat_term_years - asset_value * crat_payout_rate * crat_term_years`.
- `estimated_income_tax_deduction = projected_charitable_remainder * charitable_deduction_rate`.
- GRAT mortality risk is `TERM_SURVIVAL_REQUIRED`; CRAT family transfer fit is usually `LOW`.

Recommendation:

- Prefer `GRAT` with `CHILDREN_TRANSFER_PRIORITY` when the signed profile shows high family-transfer priority.
- Prefer `CRAT` with `PHILANTHROPIC_PRIORITY` when philanthropic intent is high and family-transfer priority is not high.
- Set the alternate role to the other strategy's secondary use.

## Estate Liquidity Action Plan

Use this for `analysis_type: estate_liquidity_action_plan`.

Combine the estate-context, ILIT, and trust calculations above:

- `ilit.annual_exclusion_capacity`, `premium_gap`, and `estate_inclusion_risk` come from the ILIT calculation.
- `ilit.projected_outside_estate_if_implemented` is the ILIT death benefit when implemented.
- `trust_transfer` carries the GRAT/CRAT preferred strategy plus the GRAT remainder, GRAT estate-tax reduction, and CRAT charitable remainder.
- Use `COMBINE_ILIT_AND_GRAT` and `ILIT_FIRST_THEN_GRAT` when the client needs liquidity and the preferred trust transfer is GRAT.
- Include `ATTORNEY_DRAFT_REVIEW`, `ILIT_CRUMMEY_NOTICE_CYCLE`, and either `GRAT_FOR_APPRECIATING_SHARES` or `CRAT_FOR_CHARITABLE_REMAINDER`. Add `LIFETIME_EXEMPTION_ALLOCATION` when there is an ILIT premium gap. Sort `action_set` alphabetically.

## Output Discipline

The final answer must be only valid JSON. Keep enum strings exactly as the template names them. Do not cite calculations, explain assumptions, or include Markdown in the final task response.
