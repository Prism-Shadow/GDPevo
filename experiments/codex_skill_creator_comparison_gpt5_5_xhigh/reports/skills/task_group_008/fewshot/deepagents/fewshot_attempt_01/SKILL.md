---
name: private-wealth-advisory-planner
description: Structured private wealth advisory case solving from staged API data and request memos. Use when producing final JSON for Roth conversion and RMD summaries, ILIT Crummey funding checks, GRAT versus CRAT comparisons, or estate liquidity plans that require source conflict resolution, tax-policy lookups, account exports, and ISO date or USD normalization.
---

# Private Wealth Advisory Planner

## Workflow

1. Read the request memo and answer template first.
2. Fetch the target client from the advisory API, then collect matching rows from:
   - `/api/source-documents`
   - `/api/retirement-accounts`
   - `/api/life-insurance`
   - `/api/trust-candidates`
   - `/api/policies/tax`
   - `/api/rmd-factors`
3. Resolve conflicting facts by source authority, not by convenience:
   - Use `SIGNED_PROFILE` for household facts, beneficiary counts, priorities, and default policy facts.
   - Use `ATTORNEY_MEMO` for trust-asset facts and trust-planning intent when the task centers on GRAT or CRAT work.
   - Use `CUSTODIAN_EXPORT` for balances, account terms, and retirement-account inputs.
   - Use `CRM_NOTE` only as fallback.
   - Use `STALE_MARKETING_INTAKE` only if no better source exists.
4. Select the playbook that matches the template.
5. Return JSON only. Match the template exactly. Round USD to cents and use ISO `YYYY-MM-DD` dates.

## Common Rules

- Use the planning year from the memo when looking up tax-policy constants.
- Prefer the most authoritative source for the relevant field family, even when older sources disagree.
- Keep all derived numbers numeric JSON values, not strings.
- Do not add commentary, markdown, or code fences to the final answer.

## Source Resolution

Use these defaults when the template asks for a controlling source field:

- `controlling_profile_source`: prefer `SIGNED_PROFILE`, then `ATTORNEY_MEMO`, then `CRM_NOTE`, then `STALE_MARKETING_INTAKE`.
- `controlling_goal_source`: prefer `SIGNED_PROFILE`, then `ATTORNEY_MEMO`, then `CRM_NOTE`, then `STALE_MARKETING_INTAKE`.
- `controlling_beneficiary_source`: prefer `SIGNED_PROFILE`, then `ATTORNEY_MEMO`, then `CRM_NOTE`.
- `controlling_policy_source`: prefer `SIGNED_PROFILE`, then `ATTORNEY_MEMO`, then `CRM_NOTE`.
- `controlling_account_source`: prefer `CUSTODIAN_EXPORT`, then `SIGNED_PROFILE`, then `CRM_NOTE`.
- `controlling_asset_source`: prefer `ATTORNEY_MEMO`, then `SIGNED_PROFILE`, then `CRM_NOTE`.

## Roth Conversion and RMD

- Set `analysis_type` to `roth_conversion_rmd`.
- Read `conversion_bracket_targets[filing_status]` from the tax policy endpoint.
- Set annual conversion amount to `max(0, bracket_target - annual_non_ira_income)`, then clip it to the available traditional balance if needed.
- Set `first_conversion_year` to the planning year.
- Set `conversion_years` from the custodian account record.
- Set `conversion_years_positive` equal to `conversion_years`.
- Set `total_converted` to `annual_conversion_amount * conversion_years`.
- Set `total_conversion_tax` to `total_converted * marginal_tax_rate`.
- Set `first_rmd_year` to `planning_year + (rmd_start_age - age)`.
- Roll forward the traditional balance year by year:
  - Grow the balance by `expected_return`.
  - Subtract scheduled conversions during the conversion window.
  - Once the first RMD year arrives, compute each RMD from the current balance and the age factor for that year.
  - Tax each RMD at the marginal tax rate.
- Use the memo horizon year for both the baseline and conversion scenario.
- Set `rmd_tax_savings_through_horizon` to baseline tax minus the conversion-scenario RMD tax through horizon.
- Use `MIXED_TAXABLE_AND_TAX_FREE` when both Roth and traditional balances remain material at horizon.

## ILIT Crummey Implementation

- Set `analysis_type` to `ilit_crummey_implementation`.
- Set `annual_exclusion_per_beneficiary` from the planning-year gift exclusion.
- Set `annual_exclusion_capacity` to `annual_exclusion_per_beneficiary * beneficiary_count`.
- Set `premium_gap` to `max(0, annual_premium - annual_exclusion_capacity)`.
- Set `notices_required` to `beneficiary_count`.
- Derive dates from the planned contribution date:
  - `notice_due_date` = contribution date + 7 days
  - `withdrawal_window_end` = notice due date + 30 days
  - `earliest_premium_payment_date` = withdrawal window end + 1 day
- Set `dedicated_bank_account_required` to `true`.
- Treat the policy as outside the estate when formalities are met and no lookback issue applies.
- Choose `FUND_WITH_CRUMMEY_NOTICES` when the annual premium fits the exclusion capacity.
- Choose the exemption or lookback fallback actions only when the premium gap or a transfer issue requires them.

## GRAT Versus CRAT

- Set `analysis_type` to `trust_comparison`.
- Compute GRAT remainder as:
  - `asset_value * (1 + expected_growth_rate)^term_years - asset_value * grat_annuity_rate * term_years`
- Compute CRAT charitable remainder as:
  - `asset_value * (1 + expected_growth_rate)^term_years - asset_value * crat_payout_rate * term_years`
- Set GRAT estate tax reduction to `projected_remainder_to_heirs * estate_tax_rate`.
- Set CRAT income tax deduction to `projected_charitable_remainder * charitable_deduction_rate`.
- Prefer `GRAT` when family-transfer priority dominates.
- Prefer `CRAT` when philanthropic intent dominates.
- Set `alternate_role` to the opposite planning role.
- Mark `family_transfer_fit` low when charity is not the primary goal.

## Estate Liquidity Action Plan

- Set `analysis_type` to `estate_liquidity_action_plan`.
- Compute taxable estate as `estate_value - estate_tax_exemption[planning_year]`.
- Compute estate tax exposure as `taxable_estate * estate_tax_rate`.
- Compute liquidity gap as `max(0, estate_tax_exposure - liquid_assets)`.
- Reuse the ILIT rules for the insurance section.
- Reuse the GRAT versus CRAT rules for the trust-transfer section.
- Build `action_set` from the relevant actions and sort it alphabetically.
- Choose `ILIT_FIRST_THEN_GRAT` when both ILIT and GRAT are needed.
- Choose `TRUST_DECISION_FIRST` when the trust choice should lead the plan.
- Choose `ILIT_FIRST_THEN_ATTORNEY_REVIEW` when formalities or lookback issues require legal review before implementation.

## Final Check

- Confirm the top-level keys exactly match the template.
- Confirm every amount is rounded to cents.
- Confirm every date is ISO formatted.
- Return the JSON object and nothing else.
