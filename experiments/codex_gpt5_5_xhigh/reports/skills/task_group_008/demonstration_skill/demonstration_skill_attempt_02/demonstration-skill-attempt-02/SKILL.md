---
name: task-group-008-fewshot-attempt-02
description: Solve private wealth advisory benchmark tasks that ask for structured JSON planning outputs using the advisory API, local request memo, and answer template. Use for Roth conversion/RMD summaries, ILIT Crummey funding cycles, GRAT versus CRAT comparisons, and combined estate liquidity action plans where source records may conflict.
---

# Private Wealth Advisory JSON SOP

## Workflow

1. Read only the task prompt, request memo, and `answer_template.json` supplied for the current task. Extract `client_id`, planning horizon, engagement type, required top-level keys, enum values, and date/rounding requirements.
2. Query the API, starting with `/api/health`, `/api/clients/<client_id>`, `/api/source-documents?client_id=<client_id>`, and `/api/policies/tax`. Add `/api/rmd-factors` for Roth/RMD work, `/api/retirement-accounts?client_id=<client_id>` for retirement work, `/api/life-insurance?client_id=<client_id>` for ILIT work, and `/api/trust-candidates?client_id=<client_id>` for GRAT/CRAT work.
3. Build a normalized facts sheet before calculating: controlling profile facts, account facts, insurance facts, trust candidate facts, policy constants, and the output field map.
4. Calculate with full precision, then round final USD outputs to cents. Return JSON only, with JSON numbers and booleans, not strings.
5. Set `task_id` from the task split and number, such as `train_###` or `test_###`, and set `client_id` to the stable client identifier.

Prefer the JSON API endpoints over the portal page. Use `/api/clients?search=` only when the prompt does not provide a usable client ID.

## Source Resolution

Resolve conflicts by fact type, not by whichever endpoint was read first.

- Profile facts: prefer `SIGNED_PROFILE`, then `ATTORNEY_MEMO`, then `CUSTODIAN_EXPORT`, then `CRM_NOTE`, then `STALE_MARKETING_INTAKE`.
- Retirement balances and return assumptions: use `/api/retirement-accounts` and report `CUSTODIAN_EXPORT` for controlling account source when the template asks.
- Insurance facts: use `/api/life-insurance` for policy economics and dates. For template source fields, report the highest-precedence planning document that controls the policy/beneficiary facts, usually `SIGNED_PROFILE` unless attorney records are the only current authority.
- Trust candidate economics: use `/api/trust-candidates`. When the template asks for the asset source, these planning assets are usually attorney-driven; use `ATTORNEY_MEMO` unless a higher-precedence source explicitly controls the asset facts.
- Goals such as family transfer priority and philanthropic intent: prefer current signed profile facts over older CRM notes, even if the older source has a stronger stated preference.

Echo the chosen source type in the matching `source_resolution` field. Do not use stale CRM or marketing intake values when a signed profile or attorney memo supplies the same fact.

## Output Families

Choose the output family from `analysis_type` and the required keys in `answer_template.json`.

- `roth_conversion_rmd`: `recommendation`, `conversion_plan`, `rmd_projection`, `legacy_projection`, `source_resolution`.
- `ilit_crummey_implementation`: `recommendation`, `gift_plan`, `administration`, `estate_result`, `source_resolution`.
- `trust_comparison`: `recommendation`, `estate_context`, `grat`, `crat`, `source_resolution`.
- `estate_liquidity_action_plan`: `recommendation`, `estate_context`, `ilit`, `trust_transfer`, `action_set`, `source_resolution`.

For estate-context outputs, include the requested fields and, when useful for parity with this task family, `planning_year`, `exemption_used`, and `liquid_assets_available`.

## Roth Conversion And RMD Rules

Use the signed profile for `annual_non_ira_income`, `marginal_tax_rate`, `filing_status`, `age`, and `planning_year`. Use the custodian retirement account for balances, expected return, RMD start age, and recommended conversion years.

Core formulas:

- `first_rmd_year = planning_year + (rmd_start_age - age)`.
- `annual_conversion_amount = max(conversion_bracket_targets[filing_status] - annual_non_ira_income, 0)`.
- `conversion_years = recommended_conversion_years`.
- `conversion_years_positive = conversion_years` when the annual conversion amount is positive, otherwise `0`.
- `total_converted` is the sum of actual scheduled conversions. Cap a year's conversion at the remaining traditional balance if necessary.
- `total_conversion_tax = total_converted * marginal_tax_rate`.

Projection convention:

1. Baseline scenario starts with the traditional IRA balance and no conversions.
2. For each year from planning year through horizon, compute age for that year.
3. If age is at least RMD start age, calculate `rmd = opening_traditional_balance / rmd_factor[age]`, add `rmd * marginal_tax_rate` to the scenario RMD tax, and subtract the RMD from traditional balance.
4. Apply annual growth to the remaining traditional balance after any RMD.

Conversion scenario:

1. Start with traditional and Roth custodian balances.
2. At the start of each scheduled conversion year, move the annual conversion amount from traditional to Roth.
3. If an RMD is due in that same year, compute it from the post-conversion traditional balance, subtract it, and tax it.
4. Apply the account expected return to both ending traditional and Roth balances.

Then set:

- `baseline_rmd_tax_through_horizon` from the baseline scenario.
- `conversion_rmd_tax_through_horizon` from the conversion scenario, excluding conversion taxes.
- `rmd_tax_savings_through_horizon = baseline_rmd_tax_through_horizon - conversion_rmd_tax_through_horizon`.
- `projected_roth_balance_horizon` and `projected_traditional_balance_horizon` from the conversion scenario ending balances.
- `heir_tax_profile` to `MOSTLY_TAX_FREE` when traditional assets are essentially depleted, `MOSTLY_TAXABLE` when Roth assets are negligible, otherwise `MIXED_TAXABLE_AND_TAX_FREE`.

Recommendation defaults: positive bracket room with sufficient liquidity supports `STAGED_ROTH_CONVERSION`, `SUITABLE`, and `TAX_BRACKET_MANAGEMENT`. Use `LIQUIDITY_CONSTRAINT` when conversion tax cannot plausibly be paid from liquid assets; use `RMD_NEAR_TERM` only when the template facts make near-term RMD timing the main risk rather than bracket management.

## ILIT Crummey Rules

Use the policy annual gift exclusion for the planning year and the controlling beneficiary count.

- `annual_exclusion_capacity = annual_exclusion_per_beneficiary * beneficiary_count`.
- `premium_gap = max(annual_premium - annual_exclusion_capacity, 0)`.
- `notices_required = beneficiary_count`.
- `contribution_date = planned_contribution_date`.
- `notice_due_date = contribution_date + 7 calendar days`.
- `withdrawal_window_end = notice_due_date + 30 calendar days`.
- `earliest_premium_payment_date = withdrawal_window_end + 1 calendar day`.
- `dedicated_bank_account_required = true` for ILIT funding administration.
- `tax_liquidity_support = death_benefit * estate_tax_rate`.

Risk flags:

- No gap and no existing-policy transfer: `LOW_IF_FORMALITIES_MET`.
- Premium exceeds exclusion capacity: `EXCLUSION_SHORTFALL`.
- Existing policy transfer: `THREE_YEAR_LOOKBACK`.
- Both: `THREE_YEAR_LOOKBACK_AND_EXCLUSION_SHORTFALL`.

Recommendation mapping:

- Low risk: `FUND_WITH_CRUMMEY_NOTICES`, `SUITABLE_WITH_ADMINISTRATION`.
- Exclusion shortfall only: `USE_LIFETIME_EXEMPTION_FOR_SHORTFALL`; suitability is usually `BORDERLINE` unless liquidity and exemption facts are clearly comfortable.
- Three-year lookback only: `USE_NEW_POLICY_OR_ACCEPT_LOOKBACK`.
- Both lookback and shortfall: `DISCLOSE_LOOKBACK_AND_USE_EXEMPTION`.

For `projected_outside_estate_if_implemented`, use the death benefit for a properly implemented new ILIT policy. If the case is an existing-policy transfer and the chosen action accepts lookback risk, treat outside-estate status as conditional until the lookback clears.

## GRAT, CRAT, And Estate Context Rules

Use policy constants for estate exemption, estate tax rate, CRAT maximum term, and charitable deduction rate.

Estate context:

- Double the estate tax exemption for married/MFJ households; otherwise use one exemption.
- `taxable_estate = max(estate_value - exemption_used, 0)`.
- `estate_tax_exposure = taxable_estate * estate_tax_rate`.
- `liquidity_gap_before_planning = max(estate_tax_exposure - liquid_assets, 0)`.

GRAT:

- `term_years = grat_term_years`.
- `projected_remainder_to_heirs = asset_value * (1 + expected_growth_rate) ^ grat_term_years - asset_value * grat_annuity_rate * grat_term_years`.
- `estimated_estate_tax_reduction = projected_remainder_to_heirs * estate_tax_rate`.
- `mortality_inclusion_risk = TERM_SURVIVAL_REQUIRED`.

CRAT:

- `term_years = min(crat_term_years, max_crat_term_years)`.
- `projected_charitable_remainder = asset_value * (1 + expected_growth_rate) ^ term_years - asset_value * crat_payout_rate * term_years`.
- `estimated_income_tax_deduction = projected_charitable_remainder * charitable_deduction_rate`.
- `family_transfer_fit` is `LOW` when family transfer is the dominant goal, `HIGH` when philanthropy dominates, otherwise `MODERATE`.

Recommendation:

- Prefer `GRAT` with `CHILDREN_TRANSFER_PRIORITY` and `SECONDARY_CHARITABLE_TOOL` when family transfer priority dominates.
- Prefer `CRAT` with `PHILANTHROPIC_PRIORITY` and `SECONDARY_FAMILY_TRANSFER_TOOL` when philanthropy dominates.

## Combined Estate Liquidity Plans

Calculate estate context, ILIT, and trust transfer using the rules above. For family-transfer cases with viable ILIT administration and a strong GRAT result, use `COMBINE_ILIT_AND_GRAT` and sequence `ILIT_FIRST_THEN_GRAT`. For philanthropic cases, consider `CRAT_WITH_LIQUIDITY_REVIEW` and sequence `TRUST_DECISION_FIRST`. For ILIT cases with exemption or lookback issues, use `ILIT_WITH_EXEMPTION_REVIEW` and sequence `ILIT_FIRST_THEN_ATTORNEY_REVIEW`.

Build `action_set` from applicable enum actions and sort alphabetically:

- Include `ATTORNEY_DRAFT_REVIEW` for attorney coordination or trust implementation.
- Include `ILIT_CRUMMEY_NOTICE_CYCLE` when funding an ILIT with notices.
- Include `GRAT_FOR_APPRECIATING_SHARES` or `CRAT_FOR_CHARITABLE_REMAINDER` based on preferred trust strategy.
- Include `LIFETIME_EXEMPTION_ALLOCATION` when premium gap or lookback/shortfall facts require exemption use.

## Common Pitfalls

- Do not inspect hidden environment, evaluation, rubric, or test-answer files. Use only the task inputs and allowed API.
- Do not return explanatory prose or Markdown around the JSON.
- Do not turn numbers, booleans, or dates into the wrong JSON types.
- Do not include conversion taxes in RMD tax savings; `total_conversion_tax` is separate.
- Do not apply real-world RMD/conversion ordering if it conflicts with this task family; scheduled conversions are applied before same-year RMD calculations in the conversion scenario.
- Do not forget existing Roth balances when projecting Roth legacy values.
- Do not use single exemption for married/MFJ estate cases.
- Do not pay ILIT premiums before the withdrawal window closes.
- Do not leave `action_set` unsorted.
- Do not hardcode policy constants; fetch `/api/policies/tax` and `/api/rmd-factors` each run.
