---
name: private-wealth-advisory-json
description: Use this skill for private wealth advisory tasks that ask for a structured planning JSON object for a CLT client using the advisory API, especially Roth conversion/RMD, ILIT Crummey funding, GRAT versus CRAT, or estate liquidity action-plan analyses. Trigger whenever the prompt mentions the private wealth advisory team, CLT client IDs, advisory API records, answer_template.json, RMD factors, life insurance, trust candidates, Roth conversions, ILITs, GRATs, CRATs, or estate liquidity planning.
---

# Private Wealth Advisory JSON

Use this workflow to prepare the final JSON answer for the advisory planning tasks. The goal is not a narrative memo; it is a schema-conforming JSON object whose numbers come from the staged request files and the advisory API.

## Boundaries

- Use only the staged task input files and the advisory API described by `environment_access.md` or `API_BASE`.
- Do not inspect answer files, judge feedback, evaluation files, local environment source, run artifacts, or other skill attempts.
- Return only the final JSON object. No Markdown, citations, comments, or prose outside the JSON.
- Use JSON numbers for money, rounded to cents. Do not stringify numbers or include commas.
- Use ISO `YYYY-MM-DD` dates.

## Standard Workflow

1. Read the task prompt, `payloads/request_memo.md`, and `payloads/answer_template.json`.
2. Extract `client_id`, planning horizon if the memo supplies one, and the required enum values and top-level keys from the template.
3. Set `task_id` from the task folder when available: `train_tasks/001` becomes `train_001`, `test_tasks/001` becomes `test_001`.
4. Query the API records for the client:
   - `/api/clients/<client_id>`
   - `/api/source-documents?client_id=<client_id>`
   - `/api/retirement-accounts?client_id=<client_id>`
   - `/api/life-insurance?client_id=<client_id>`
   - `/api/trust-candidates?client_id=<client_id>`
   - `/api/policies/tax`
   - `/api/rmd-factors`
5. Resolve conflicting sources before calculating.
6. Fill exactly the keys required by `answer_template.json`, using only allowed enum values.
7. Validate the output as JSON and check all required top-level keys are present.

## Source Resolution

Resolve source conflicts by field family, not by whichever record appears first.

- Household profile facts such as age, planning year, filing status, income, marginal tax rate, beneficiary count, liquid assets, estate value, philanthropic intent, and family transfer priority: prefer `SIGNED_PROFILE` when present.
- Attorney planning intent or trust/insurance implementation facts: use `ATTORNEY_MEMO` when the specialized API endpoint has no `source_type`.
- Retirement account balances, Roth balances, return assumptions, RMD start age, and recommended conversion years: use `/api/retirement-accounts`, normally reported as `CUSTODIAN_EXPORT`.
- Older CRM or stale intake records are fallback sources only.

Use these common source-resolution outputs:

- Roth/RMD: `controlling_profile_source` is usually `SIGNED_PROFILE`; `controlling_account_source` is usually `CUSTODIAN_EXPORT`.
- ILIT: `controlling_beneficiary_source` is usually `SIGNED_PROFILE`; `controlling_policy_source` is usually `ATTORNEY_MEMO` unless the policy record gives another source.
- GRAT/CRAT: `controlling_goal_source` is usually `SIGNED_PROFILE`; `controlling_asset_source` is usually `ATTORNEY_MEMO` unless the trust candidate gives another source.

## Shared Constants

From `/api/policies/tax`:

- `annual_gift_exclusion[planning_year]`
- `estate_tax_exemption[planning_year]`
- `estate_tax_rate`
- `conversion_bracket_targets[filing_status]`
- `max_crat_term_years`
- `charitable_deduction_rate`

If a year key is missing, use the most recent available policy year not after the planning year. Do not double the estate tax exemption for marital status unless an input record explicitly says to do so.

Estate calculations:

```text
taxable_estate = max(0, estate_value - estate_tax_exemption)
estate_tax_exposure = taxable_estate * estate_tax_rate
liquidity_gap_before_planning = max(0, estate_tax_exposure - liquid_assets)
```

## Roth Conversion And RMD

Use this for `analysis_type: roth_conversion_rmd`.

Core dates and conversion capacity:

```text
first_rmd_year = planning_year + (rmd_start_age - current_age)
pre_rmd_years = max(0, first_rmd_year - planning_year)
conversion_years = min(recommended_conversion_years, pre_rmd_years)
bracket_room = max(0, conversion_bracket_target - annual_non_ira_income)
annual_conversion_amount = 0 if conversion_years is 0, else min(bracket_room, traditional_balance / conversion_years)
conversion_years_positive = conversion_years if annual_conversion_amount > 0 else 0
total_converted = annual_conversion_amount * conversion_years_positive
total_conversion_tax = total_converted * marginal_tax_rate
```

Projection convention:

- Simulate from `planning_year` through the requested horizon, inclusive.
- For the baseline scenario, grow the traditional IRA at `expected_return`; once the client reaches RMD age, calculate each year's RMD from the current traditional balance divided by that age's RMD factor, subtract it, and tax it at `marginal_tax_rate`.
- For the conversion scenario, make equal annual Roth conversions before RMD years, limited by remaining traditional balance. Track converted dollars in Roth, grow both balances at `expected_return`, and calculate RMD tax only on the remaining traditional balance.
- `baseline_rmd_tax_through_horizon` and `conversion_rmd_tax_through_horizon` are RMD taxes only. Do not include Roth conversion tax in these fields.
- `rmd_tax_savings_through_horizon = baseline_rmd_tax_through_horizon - conversion_rmd_tax_through_horizon`.
- `projected_roth_balance_horizon` includes existing Roth balance plus converted amounts and growth.
- `projected_traditional_balance_horizon` is the remaining traditional balance after conversions, RMDs, and growth.

Recommended enums:

- `primary_action`: use `STAGED_ROTH_CONVERSION` when there is positive bracket room, positive pre-RMD conversion time, and conversion taxes are affordable from liquid assets. Use `DEFER` when bracket room or pre-RMD time is inadequate. Use `NO_CONVERSION` when the conversion is clearly unsuitable.
- `suitability`: `SUITABLE` for meaningful multi-year pre-RMD conversions with liquidity; `BORDERLINE` for near-RMD or tight liquidity cases; `DEFER` when the model should not convert now.
- `risk_flag`: `RMD_NEAR_TERM` when RMDs begin within about one year or materially truncate recommended conversion years; `LIQUIDITY_CONSTRAINT` when conversion tax strains liquid assets; otherwise `TAX_BRACKET_MANAGEMENT`.
- `heir_tax_profile`: `MOSTLY_TAX_FREE` when Roth is the dominant projected retirement legacy, `MIXED_TAXABLE_AND_TAX_FREE` when both Roth and traditional balances remain material, and `MOSTLY_TAXABLE` when Roth remains a small minority.

## ILIT Crummey Funding

Use this for `analysis_type: ilit_crummey_implementation`.

Gift and administration calculations:

```text
annual_exclusion_capacity = beneficiary_count * annual_gift_exclusion
premium_gap = max(0, annual_premium - annual_exclusion_capacity)
notices_required = beneficiary_count
contribution_date = planned_contribution_date
notice_due_date = contribution_date + 5 calendar days
withdrawal_window_end = notice_due_date + 30 calendar days
earliest_premium_payment_date = withdrawal_window_end + 1 calendar day
```

Do not adjust dates for weekends unless the prompt says to. The dedicated bank account flag is `true` for ILIT-owned policy funding.

Risk and recommendation mapping:

```text
exclusion_shortfall = premium_gap > 0
lookback = is_existing_policy_transfer
```

- No shortfall and no lookback: risk `LOW_IF_FORMALITIES_MET`, action `FUND_WITH_CRUMMEY_NOTICES`, suitability `SUITABLE_WITH_ADMINISTRATION`.
- Shortfall only: risk `EXCLUSION_SHORTFALL`, action `USE_LIFETIME_EXEMPTION_FOR_SHORTFALL`, suitability `BORDERLINE`.
- Existing-policy transfer only: risk `THREE_YEAR_LOOKBACK`, action `USE_NEW_POLICY_OR_ACCEPT_LOOKBACK`, suitability `BORDERLINE`.
- Both: risk `THREE_YEAR_LOOKBACK_AND_EXCLUSION_SHORTFALL`, action `DISCLOSE_LOOKBACK_AND_USE_EXEMPTION`, suitability `NOT_SUITABLE` or `BORDERLINE` depending on severity.

Estate result:

```text
death_benefit = policy death_benefit
estate_inclusion_risk = recommendation.risk_flag
projected_outside_estate_if_implemented = death_benefit
tax_liquidity_support = min(death_benefit, liquidity_gap_before_planning)
```

## GRAT Versus CRAT

Use this for `analysis_type: trust_comparison`.

Goals:

- Convert goal strings such as `low`, `moderate`, and `high` to an ordered scale.
- Prefer `GRAT` when family transfer priority is greater than or equal to philanthropic intent.
- Prefer `CRAT` when philanthropic intent is higher than family transfer priority.
- If `GRAT` is preferred, use rationale `CHILDREN_TRANSFER_PRIORITY` and alternate role `SECONDARY_CHARITABLE_TOOL`.
- If `CRAT` is preferred, use rationale `PHILANTHROPIC_PRIORITY` and alternate role `SECONDARY_FAMILY_TRANSFER_TOOL`.

GRAT:

```text
grat.term_years = trust_candidate.grat_term_years
projected_remainder_to_heirs =
  asset_value * max(0, (1 + expected_growth_rate)^grat_term_years - (1 + grat_annuity_rate)^grat_term_years)
estimated_estate_tax_reduction = projected_remainder_to_heirs * estate_tax_rate
mortality_inclusion_risk = TERM_SURVIVAL_REQUIRED
```

CRAT:

```text
crat.term_years = min(trust_candidate.crat_term_years, max_crat_term_years)
projected_charitable_remainder =
  asset_value * (1 + expected_growth_rate - crat_payout_rate)^crat.term_years
estimated_income_tax_deduction = asset_value * charitable_deduction_rate
```

For `family_transfer_fit`, use `LOW` when CRAT conflicts with a high family-transfer goal, `HIGH` when philanthropy is clearly dominant, and `MODERATE` for mixed goals.

## Estate Liquidity Action Plan

Use this for `analysis_type: estate_liquidity_action_plan`. Combine the estate, ILIT, and trust-transfer recipes above.

Recommendation mapping:

- Use `COMBINE_ILIT_AND_GRAT` with sequencing `ILIT_FIRST_THEN_GRAT` when ILIT formalities are manageable and the trust transfer preference is `GRAT`.
- Use `CRAT_WITH_LIQUIDITY_REVIEW` with sequencing `TRUST_DECISION_FIRST` when the client-specific goals prefer `CRAT`.
- Use `ILIT_WITH_EXEMPTION_REVIEW` with sequencing `ILIT_FIRST_THEN_ATTORNEY_REVIEW` when ILIT premium gaps or lookback issues drive the recommendation.

Build `action_set` from applicable actions, then sort alphabetically:

- `ATTORNEY_DRAFT_REVIEW`: include for estate liquidity action plans.
- `ILIT_CRUMMEY_NOTICE_CYCLE`: include when funding an ILIT.
- `LIFETIME_EXEMPTION_ALLOCATION`: include when `premium_gap > 0` or a lookback/exemption disclosure is needed.
- `GRAT_FOR_APPRECIATING_SHARES`: include when the preferred trust transfer is `GRAT`.
- `CRAT_FOR_CHARITABLE_REMAINDER`: include when the preferred trust transfer is `CRAT`.

## Final Checks

- The top-level keys match `required_top_level_keys`.
- Every enum value is copied exactly from the template.
- `action_set`, when present, is alphabetically sorted.
- Money is rounded to cents as JSON numbers.
- Dates are ISO strings.
- Source-resolution fields reflect the source family used for the calculation.
- The response contains one JSON object and nothing else.
