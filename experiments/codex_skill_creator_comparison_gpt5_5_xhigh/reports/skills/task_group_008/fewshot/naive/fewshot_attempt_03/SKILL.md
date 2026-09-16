---
name: wealth-advisory-planning-json
description: Solve private wealth advisory planning tasks that require JSON outputs from the advisory API, including Roth/RMD projections, ILIT Crummey funding checks, GRAT/CRAT comparisons, and estate liquidity action plans.
---

# Wealth Advisory Planning JSON

Use this skill when a task asks for a structured JSON planning output for a private wealth advisory client and provides an advisory API base URL, request memo, and `answer_template.json`.

## Required Workflow

1. Read the task prompt, `input/payloads/request_memo.md`, and `input/payloads/answer_template.json`.
2. Extract `client_id`, engagement type, planning horizon if stated, and the output schema.
3. Use the API base supplied by the harness, usually `$API_BASE`. Query only business-data endpoints needed for the current `client_id`; do not call judge or evaluator endpoints.
4. Fetch:
   - Always: `GET /api/clients/{client_id}`, `GET /api/source-documents?client_id={client_id}`, `GET /api/policies/tax`.
   - Roth/RMD: `GET /api/retirement-accounts?client_id={client_id}` and `GET /api/rmd-factors`.
   - ILIT: `GET /api/life-insurance?client_id={client_id}`.
   - GRAT/CRAT or estate liquidity: `GET /api/trust-candidates?client_id={client_id}`; estate liquidity also needs life-insurance.
5. Build the JSON object exactly in the template shape. Return only JSON, no prose.

Derive `task_id` from the current task directory or prompt identifier. Use the current task's `client_id`; never reuse example client IDs or values.

## Source Resolution

Source records can conflict. Resolve facts by type, then report the controlling source enum requested by the template.

- Household/profile facts such as `age`, `planning_year`, `filing_status`, `annual_non_ira_income`, `marginal_tax_rate`, `beneficiary_count`, `family_transfer_priority`, `philanthropic_intent`, `liquid_assets`, and `estate_value`: prefer `SIGNED_PROFILE`, then `ATTORNEY_MEMO`, then `CUSTODIAN_EXPORT`, then `CRM_NOTE`, then `STALE_MARKETING_INTAKE`, then the client endpoint.
- Retirement account balances, Roth balances, expected return, RMD start age, and recommended conversion years: use the retirement account record; source is normally `CUSTODIAN_EXPORT`.
- Life-insurance policy facts: use the life-insurance record. If it lacks an explicit source, report `SIGNED_PROFILE` for policy source unless the task data clearly labels another controlling source.
- Trust candidate economics: use the trust-candidates record. If it lacks an explicit source, report `ATTORNEY_MEMO` for asset source.
- Goal source is the source of the controlling priority facts, usually `SIGNED_PROFILE` when present.

## Money, Dates, And Rounding

- USD outputs are JSON numbers rounded to two decimals, not strings.
- Keep intermediate calculations unrounded; round only final fields. For difference fields, subtract unrounded source totals, then round.
- Use ISO `YYYY-MM-DD` dates.
- Sort enum arrays when the template says to sort them.

## Roth Conversion And RMD

Use when `analysis_type` is `roth_conversion_rmd`.

Inputs:

- Profile: `planning_year`, `age`, `filing_status`, `annual_non_ira_income`, `marginal_tax_rate`, `liquid_assets`.
- Account: `traditional_balance`, `roth_balance`, `expected_return`, `rmd_start_age`, `recommended_conversion_years`.
- Policy: `conversion_bracket_targets[filing_status]`.
- RMD factors: map age to factor.
- Horizon: from the request memo.

Calculations:

- `first_conversion_year = planning_year`.
- `annual_conversion_amount = max(0, bracket_target - annual_non_ira_income)`.
- `conversion_years = recommended_conversion_years`.
- Simulate actual conversions; `conversion_years_positive` is the count of years where a positive conversion occurs.
- `total_converted` is the sum of actual conversions.
- `total_conversion_tax = total_converted * marginal_tax_rate`.
- `first_rmd_year = planning_year + max(0, rmd_start_age - age)`.

Annual simulation order runs from `planning_year` through `horizon_year`, inclusive:

Baseline:

1. Start with current traditional balance.
2. For each year, compute current age as `age + year - planning_year`.
3. If current age is at least `rmd_start_age`, calculate `rmd = traditional_balance / rmd_factor[current_age]`, add `rmd * marginal_tax_rate` to baseline RMD tax, and subtract the RMD.
4. Grow the remaining traditional balance by `expected_return`.

Conversion scenario:

1. Start with current traditional and Roth balances.
2. In each conversion year from `planning_year` through `planning_year + conversion_years - 1`, convert `min(annual_conversion_amount, traditional_balance)` before taking any RMD. Move the converted amount from traditional to Roth.
3. If current age is at least `rmd_start_age`, calculate and subtract RMD from the post-conversion traditional balance and add tax.
4. Grow both traditional and Roth balances by `expected_return`.

Output:

- `baseline_rmd_tax_through_horizon`: baseline RMD tax sum.
- `conversion_rmd_tax_through_horizon`: conversion-scenario RMD tax sum.
- `rmd_tax_savings_through_horizon`: baseline tax minus conversion-scenario tax.
- `projected_roth_balance_horizon`: post-growth Roth balance at horizon.
- `projected_traditional_balance_horizon`: post-growth traditional balance at horizon.
- `heir_tax_profile`: `MOSTLY_TAX_FREE` if Roth dominates, `MOSTLY_TAXABLE` if traditional dominates, otherwise `MIXED_TAXABLE_AND_TAX_FREE`.

Recommendation:

- Use `STAGED_ROTH_CONVERSION` and `SUITABLE` when a positive bracket-space conversion is possible and liquidity can cover conversion tax.
- Use `LIQUIDITY_CONSTRAINT` when liquid assets cannot cover projected conversion tax.
- Use `DEFER` or `NO_CONVERSION` when no positive bracket space or no practical conversion remains.
- Use `TAX_BRACKET_MANAGEMENT` when the plan is mainly filling the target bracket.

## ILIT Crummey Implementation

Use when `analysis_type` is `ilit_crummey_implementation`.

Inputs:

- Profile: `planning_year`, `beneficiary_count`.
- Policy: `annual_gift_exclusion[planning_year]`, `estate_tax_rate`.
- Life insurance: `death_benefit`, `annual_premium`, `planned_contribution_date`, `proposed_owner`, `is_existing_policy_transfer`.

Calculations:

- `annual_exclusion_capacity = annual_exclusion_per_beneficiary * beneficiary_count`.
- `premium_gap = max(0, annual_premium - annual_exclusion_capacity)`.
- `notices_required = beneficiary_count`.
- `notice_due_date = contribution_date + 7 calendar days`.
- `withdrawal_window_end = notice_due_date + 30 calendar days`.
- `earliest_premium_payment_date = withdrawal_window_end + 1 calendar day`.
- `dedicated_bank_account_required = true` when the proposed owner is an ILIT.
- `tax_liquidity_support = death_benefit * estate_tax_rate`.
- `projected_outside_estate_if_implemented = death_benefit`; express transfer risk through the risk flag.

Risk flag:

- No premium gap and no existing-policy transfer: `LOW_IF_FORMALITIES_MET`.
- Premium gap only: `EXCLUSION_SHORTFALL`.
- Existing-policy transfer only: `THREE_YEAR_LOOKBACK`.
- Both: `THREE_YEAR_LOOKBACK_AND_EXCLUSION_SHORTFALL`.

Recommendation:

- Low risk: `FUND_WITH_CRUMMEY_NOTICES`, `SUITABLE_WITH_ADMINISTRATION`.
- Premium gap without lookback: `USE_LIFETIME_EXEMPTION_FOR_SHORTFALL`, usually `BORDERLINE`.
- Lookback without premium gap: `USE_NEW_POLICY_OR_ACCEPT_LOOKBACK`.
- Lookback plus premium gap: `DISCLOSE_LOOKBACK_AND_USE_EXEMPTION`.

## GRAT Versus CRAT

Use when `analysis_type` is `trust_comparison`.

Estate context:

- `exemption_used = estate_tax_exemption[planning_year] * 2` for married households, otherwise one exemption.
- `taxable_estate = max(0, estate_value - exemption_used)`.
- `estate_tax_exposure = taxable_estate * estate_tax_rate`.
- `liquidity_gap_before_planning = max(0, estate_tax_exposure - liquid_assets)`.
- Include `planning_year`, `exemption_used`, and `liquid_assets_available` when the task's pattern asks for estate context detail, even if the compact template text omits them.

Trust calculations:

- `grat.projected_remainder_to_heirs = asset_value * (1 + expected_growth_rate) ** grat_term_years - asset_value * grat_annuity_rate * grat_term_years`.
- `grat.estimated_estate_tax_reduction = grat.projected_remainder_to_heirs * estate_tax_rate`.
- `grat.mortality_inclusion_risk = TERM_SURVIVAL_REQUIRED`.
- `crat.projected_charitable_remainder = asset_value * (1 + expected_growth_rate) ** crat_term_years - asset_value * crat_payout_rate * crat_term_years`.
- `crat.estimated_income_tax_deduction = crat.projected_charitable_remainder * charitable_deduction_rate`.
- `crat.family_transfer_fit = LOW` when family transfer is the primary client goal; otherwise choose `MODERATE` or `HIGH` based on how strongly philanthropy dominates.

Recommendation:

- If family transfer priority is at least as strong as philanthropic intent, choose `GRAT`, `CHILDREN_TRANSFER_PRIORITY`, and `SECONDARY_CHARITABLE_TOOL`.
- If philanthropic intent is stronger, choose `CRAT`, `PHILANTHROPIC_PRIORITY`, and `SECONDARY_FAMILY_TRANSFER_TOOL`.

## Estate Liquidity Action Plan

Use when `analysis_type` is `estate_liquidity_action_plan`.

Combine the estate context, ILIT summary, and trust transfer calculations above.

- `ilit.annual_exclusion_capacity`, `premium_gap`, `estate_inclusion_risk`, and `projected_outside_estate_if_implemented` come from the ILIT rules.
- `trust_transfer.preferred_strategy`, `projected_remainder_to_heirs`, `estimated_estate_tax_reduction`, and `projected_charitable_remainder` come from the GRAT/CRAT rules.
- Recommendation:
  - Low-risk ILIT plus GRAT preference: `COMBINE_ILIT_AND_GRAT` with `ILIT_FIRST_THEN_GRAT`.
  - CRAT preference: `CRAT_WITH_LIQUIDITY_REVIEW` with `TRUST_DECISION_FIRST`.
  - ILIT gap or lookback requiring attorney/exemption review: `ILIT_WITH_EXEMPTION_REVIEW` with `ILIT_FIRST_THEN_ATTORNEY_REVIEW`.
- `recommendation.risk_flag` should match the ILIT risk flag.

Build `action_set` from applicable actions, then sort alphabetically:

- Always include `ATTORNEY_DRAFT_REVIEW`.
- Include `ILIT_CRUMMEY_NOTICE_CYCLE` when an ILIT policy is being implemented.
- Include `GRAT_FOR_APPRECIATING_SHARES` when GRAT is preferred.
- Include `CRAT_FOR_CHARITABLE_REMAINDER` when CRAT is preferred.
- Include `LIFETIME_EXEMPTION_ALLOCATION` when a premium shortfall or other exemption allocation is needed.

## Final Checks

- Confirm every required top-level key from `answer_template.json` is present.
- Use enum strings exactly as shown in the template.
- Ensure JSON parses with no comments, markdown fences, or trailing text.
- Do not include source documents, raw API records, or copied example outputs in the answer.
