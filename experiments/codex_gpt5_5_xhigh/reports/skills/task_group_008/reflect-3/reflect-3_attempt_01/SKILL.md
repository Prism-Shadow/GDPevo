# Reflect-3 Advisory Planning SOP

Use this skill for private-wealth advisory tasks that ask for a structured JSON planning output from staged prompt files and the advisory data API. Do not add prose outside the JSON answer.

## Required Workflow

1. Read the staged `prompt.txt`, `input/payloads/request_memo.md`, and `input/payloads/answer_template.json` for the current task.
2. Build the answer shape from `answer_template.json`; use the exact enum strings, required top-level keys, and field names.
3. Pull only the current client’s relevant advisory records: client profile, source documents, retirement accounts, life-insurance records, trust candidates, tax policy constants, and RMD factors as needed.
4. Resolve conflicting facts before calculating. Then calculate from resolved facts and return JSON numbers, not strings. Round USD values to cents and use ISO `YYYY-MM-DD` dates.

## Source Resolution

- Use `SIGNED_PROFILE` for household facts when present: age, filing status, marital status, income, marginal rate, beneficiaries, liquid assets, estate value, and stated family/philanthropic priorities.
- Use `CUSTODIAN_EXPORT` for retirement-account balances, Roth balances, expected returns, RMD start age, and recommended conversion years.
- For proposed life-insurance policy fields, use the life-insurance record values. If the policy record has no explicit source type and the template requires a policy source enum, prefer `SIGNED_PROFILE`.
- Use older CRM data only when no later controlling source supplies the field.
- Attorney memos are useful for confirming planning goals, but a later signed profile controls direct conflicts unless the template/memo clearly elevates attorney instructions.

## Roth Conversion / RMD Tasks

- `first_rmd_year = planning_year + (rmd_start_age - age)`.
- Bracket-cap conversion amount:
  `annual_conversion_amount = max(0, conversion_bracket_targets[filing_status] - annual_non_ira_income)`.
- In ordinary pre-RMD cases, use the lesser of account-recommended years and years before RMD start. In near-RMD comparison cases, preserve the custodian’s recommended conversion-year count even if it continues after RMDs begin, and use `risk_flag: RMD_NEAR_TERM`.
- `total_converted = annual_conversion_amount * conversion_years`.
- `total_conversion_tax = total_converted * marginal_tax_rate`.
- Projection convention:
  - For conversion years before RMD age, subtract the conversion from traditional assets, add it to Roth assets, then apply annual growth.
  - In RMD years, take the RMD first using that year’s age factor, tax the RMD at the marginal rate, then apply any planned Roth conversion, then grow remaining traditional and Roth balances.
  - Baseline RMD tax uses the same RMD loop with no conversions.
  - Include existing Roth balances in horizon Roth projections.
- Sum RMD taxes from the first RMD year through the horizon year, inclusive.
- Use `STAGED_ROTH_CONVERSION` when there is positive bracket capacity. Use `SUITABLE` for multi-year pre-RMD plans with adequate liquidity; use `BORDERLINE` when RMDs are near-term. Use `TAX_BRACKET_MANAGEMENT` for bracket-cap plans and `RMD_NEAR_TERM` for near-RMD plans.
- `heir_tax_profile` is usually `MIXED_TAXABLE_AND_TAX_FREE` when both traditional and Roth balances remain at the horizon.

## ILIT / Crummey Tasks

- Use the signed-profile beneficiary count.
- `annual_exclusion_capacity = annual_gift_exclusion[planning_year] * beneficiary_count` unless the memo explicitly instructs gift splitting.
- `premium_gap = max(0, annual_premium - annual_exclusion_capacity)`.
- `notices_required = beneficiary_count`.
- Use the planned contribution date from the life-insurance record. Unless the memo gives different formalities, set notice due date to the contribution date, use a 30-day withdrawal window, and set earliest premium payment after the window.
- `dedicated_bank_account_required` should be `true` for ILIT funding-cycle outputs.
- Risk flags:
  - No existing-policy transfer and no premium gap: `LOW_IF_FORMALITIES_MET`.
  - Premium gap only: `EXCLUSION_SHORTFALL`.
  - Existing policy transfer only: `THREE_YEAR_LOOKBACK`.
  - Both issues: `THREE_YEAR_LOOKBACK_AND_EXCLUSION_SHORTFALL`.
- Recommended actions:
  - No gap/lookback: `FUND_WITH_CRUMMEY_NOTICES`.
  - Gap: use the lifetime-exemption shortfall action.
  - Existing policy transfer: disclose/review lookback or use a new policy, depending on the enum choices.
- Death benefit and projected outside-estate amount normally equal the proposed policy death benefit.

## Estate Liquidity / Trust Comparison Tasks

- Estate context:
  - `taxable_estate = max(0, estate_value - estate_tax_exemption[planning_year])`.
  - `estate_tax_exposure = taxable_estate * estate_tax_rate`.
  - `liquidity_gap_before_planning = max(0, estate_tax_exposure - liquid_assets)`.
- Recommendation logic:
  - High family-transfer priority with low/moderate philanthropy favors `GRAT`, rationale `CHILDREN_TRANSFER_PRIORITY`, and CRAT only as a secondary charitable tool.
  - High philanthropic priority favors `CRAT`, rationale `PHILANTHROPIC_PRIORITY`, and GRAT as a secondary family-transfer tool.
- GRAT/CRAT projections are the easiest place to miss conventions. Prefer a cash-flow-first model when no other formula is specified:
  - GRAT: each year subtract `asset_value * grat_annuity_rate`, then grow by `expected_growth_rate`; estate-tax reduction is projected heir remainder times the estate-tax rate.
  - CRAT: each year subtract the payout, then grow by `expected_growth_rate`; use the resulting remainder for charitable-remainder fields.
  - If a task clearly frames rates as spreads rather than cash flows, use the spread only after confirming the template language supports it.
- `mortality_inclusion_risk` for GRATs is `TERM_SURVIVAL_REQUIRED`.
- For integrated liquidity action plans, include ILIT actions when a policy is proposed, GRAT/CRAT action matching the preferred trust strategy, `ATTORNEY_DRAFT_REVIEW` when the memo asks for attorney coordination, and `LIFETIME_EXEMPTION_ALLOCATION` only when a premium/exclusion shortfall exists.
- Always sort `action_set` alphabetically exactly as enum strings.

## Common Pitfalls

- Do not rely on the top-level client record when a signed profile supplies a more specific current fact.
- Do not multiply ILIT annual exclusion capacity by two for married households unless the memo explicitly calls for gift splitting.
- Do not forget existing Roth balances in Roth horizon projections.
- Do not cap near-RMD conversion years at pre-RMD years when the custodian record calls for a longer comparison period.
- Do not include explanatory prose, raw calculations, or citations in the JSON output.
