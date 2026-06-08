---
name: demonstration-skill-attempt-03
description: Solve private-wealth advisory input/output JSON tasks that require reading a local request memo and answer template, querying the advisory API, resolving conflicting client sources, and computing Roth/RMD, ILIT Crummey, GRAT/CRAT, or estate-liquidity planning outputs.
---

# Private Wealth Advisory JSON SOP

## Workflow

1. Read the task prompt, `input/payloads/request_memo.md`, and `input/payloads/answer_template.json`. Use the memo for client ID, engagement type, planning horizon, requested dates, and output-only constraint. Use the template as the contract for top-level keys, enums, field names, and sorting/date/number rules.
2. Query the advisory API at `API_BASE`. Start with `/api/health`, then fetch:
   - `/api/clients?search=<client_id_or_name>` and `/api/clients/<client_id>`
   - `/api/source-documents?client_id=<client_id>`
   - `/api/retirement-accounts?client_id=<client_id>`
   - `/api/life-insurance?client_id=<client_id>`
   - `/api/trust-candidates?client_id=<client_id>`
   - `/api/policies/tax`
   - `/api/rmd-factors`
   Use `/portal/client/<client_id>` only as a sanity check; calculations come from JSON endpoints.
3. Resolve conflicting facts before calculating. Track the enum source that controls each requested `source_resolution` field.
4. Compute with full precision and round only final USD outputs to cents. Emit JSON numbers, not strings. Emit ISO `YYYY-MM-DD` dates and booleans as booleans.
5. Return only the final JSON object. Do not include notes, citations, or markdown.

## Source Resolution

Use the source that directly controls the fact being used, not merely the newest object returned by the API.

- Prefer `SIGNED_PROFILE` for household facts: age, planning year, filing status, marital status, annual non-IRA income, marginal tax rate, beneficiary count, liquid assets, and stated family/philanthropic priorities when present.
- Prefer `ATTORNEY_MEMO` for attorney planning assumptions and legal/estate asset context when the template asks for an asset, goal, or policy/legal source and the memo is the only direct provenance for that assumption.
- Prefer `CUSTODIAN_EXPORT` for retirement-account balances, Roth balances, expected return, RMD start age, and recommended conversion years.
- Use life-insurance endpoint facts for policy amounts, premiums, contribution date, ILIT owner, and existing-policy-transfer status. If the endpoint has no explicit `source_type`, choose the source document that controls the associated policy/beneficiary profile fact.
- Treat `CRM_NOTE` and `STALE_MARKETING_INTAKE` as fallback sources. Do not average conflicts or let an older CRM value override a signed profile.

## Shared Calculations

Pull policy constants from `/api/policies/tax`: annual gift exclusion by year, estate tax exemption by year, estate tax rate, conversion-bracket target by filing status, max CRAT term, and charitable deduction rate.

For estate context:

- `exemption_used` = annual estate exemption for planning year times 2 for married/MFJ households, otherwise times 1.
- `taxable_estate` = `max(0, estate_value - exemption_used)`.
- `estate_tax_exposure` = `taxable_estate * estate_tax_rate`.
- `liquidity_gap_before_planning` = `max(0, estate_tax_exposure - liquid_assets_available)`.

For recommendations, choose the enum whose name matches the computed economics and controlling goal: family-transfer priority generally favors GRAT/children-transfer actions; philanthropic priority favors CRAT/charitable actions; estate liquidity with a clean ILIT and strong GRAT economics favors combining ILIT and GRAT.

## Roth Conversion And RMD

Use for `analysis_type: roth_conversion_rmd`.

- `first_conversion_year` = planning year.
- `conversion_years` = account `recommended_conversion_years`.
- Annual conversion room = `conversion_bracket_targets[filing_status] - annual_non_ira_income`; floor at 0. Cap each conversion by remaining traditional balance if needed.
- `conversion_years_positive` = count of years with a positive conversion.
- `annual_conversion_amount` = positive annual conversion room, rounded to cents.
- `total_converted` = sum of actual conversions.
- `total_conversion_tax` = `total_converted * marginal_tax_rate`.
- `first_rmd_year` = `planning_year + (rmd_start_age - current_age)`.

Projection loop, for each year from planning year through horizon inclusive:

1. Set current age from planning-year age.
2. In conversion scenario, convert the annual amount during each conversion year before RMDs and growth.
3. If current age is at least RMD start age, compute `rmd = traditional_balance / rmd_factors[current_age]`, subtract it from traditional balance, and add `rmd * marginal_tax_rate` to RMD tax.
4. Grow remaining traditional balance and Roth balance by account `expected_return`.

Run once with no conversions for baseline RMD tax and once with conversions. Existing Roth balance starts in the Roth bucket. `rmd_tax_savings_through_horizon` = baseline RMD tax minus conversion-scenario RMD tax. Horizon balances are the ending balances after the final year's growth. Use `MOSTLY_TAXABLE` when there is no meaningful Roth balance, `MOSTLY_TAX_FREE` when nearly all remaining retirement wealth is Roth, otherwise `MIXED_TAXABLE_AND_TAX_FREE`.

## ILIT Crummey Implementation

Use for `analysis_type: ilit_crummey_implementation` and the ILIT portion of estate-liquidity tasks.

- `annual_exclusion_per_beneficiary` = policy annual gift exclusion for planning year.
- `annual_exclusion_capacity` = exclusion per beneficiary times controlling beneficiary count.
- `premium_gap` = `max(0, annual_premium - annual_exclusion_capacity)`.
- `notices_required` = beneficiary count.
- `notice_due_date` = contribution date plus 7 days.
- `withdrawal_window_end` = notice due date plus 30 days.
- `earliest_premium_payment_date` = withdrawal-window end plus 1 day.
- `dedicated_bank_account_required` = true for ILIT administration.
- `tax_liquidity_support` = death benefit times estate tax rate.
- `projected_outside_estate_if_implemented` generally equals death benefit, but keep the three-year-lookback risk if an existing policy is transferred.

Risk/action mapping:

- No premium gap and no existing-policy transfer: `LOW_IF_FORMALITIES_MET`, `FUND_WITH_CRUMMEY_NOTICES`.
- Premium gap only: `EXCLUSION_SHORTFALL`, use lifetime exemption for the shortfall.
- Existing-policy transfer only: `THREE_YEAR_LOOKBACK`, use a new policy or accept/disclose the lookback.
- Both: `THREE_YEAR_LOOKBACK_AND_EXCLUSION_SHORTFALL`, disclose lookback and use exemption for the shortfall.

## GRAT And CRAT

Use for `analysis_type: trust_comparison` and `trust_transfer` blocks.

- GRAT projected remainder = `asset_value * (1 + expected_growth_rate) ^ grat_term_years - asset_value * grat_annuity_rate * grat_term_years`.
- GRAT estate-tax reduction = GRAT remainder times estate tax rate.
- GRAT mortality risk enum is `TERM_SURVIVAL_REQUIRED`.
- CRAT projected charitable remainder = `asset_value * (1 + expected_growth_rate) ^ crat_term_years - asset_value * crat_payout_rate * crat_term_years`.
- CRAT income-tax deduction = CRAT projected charitable remainder times charitable deduction rate.
- Prefer GRAT when family transfer to heirs is the controlling priority. Prefer CRAT when philanthropy is the controlling priority. Set the alternate role to the opposite charitable/family-transfer tool.
- Set CRAT `family_transfer_fit` from the client goal: high if family transfer remains compatible with the charitable strategy, moderate if mixed, low if children/family transfer is the dominant goal and CRAT is secondary.

## Estate Liquidity Action Plan

Use for `analysis_type: estate_liquidity_action_plan`.

Combine estate context, ILIT calculations, and trust-transfer calculations. Typical action-set rules:

- Include `ATTORNEY_DRAFT_REVIEW` when an ILIT or trust transfer is recommended.
- Include `ILIT_CRUMMEY_NOTICE_CYCLE` when the ILIT is funded.
- Include `GRAT_FOR_APPRECIATING_SHARES` or `CRAT_FOR_CHARITABLE_REMAINDER` according to the preferred trust strategy.
- Include `LIFETIME_EXEMPTION_ALLOCATION` when premium gap or estate planning shortfall requires exemption use.
- Sort `action_set` alphabetically exactly as the template requires.

## Pitfalls

- Do not use the client summary alone when source documents conflict.
- Do not hard-code tax constants; pull them from `/api/policies/tax`.
- Do not round inside projection loops.
- Do not calculate RMDs after year-end growth; in these tasks, RMD/conversion steps occur before annual growth.
- Do not ignore the memo's planning horizon.
- Do not output enum labels outside the template's allowed values.
- Do not stringify money, years, booleans, or arrays.
