# Private Wealth Advisory – Structured JSON Output Skill

## 1. Input Workflow
For each task:
1. **Read `input/payloads/answer_template.json` first.** It defines the exact `analysis_type`, required top-level keys, field enums, and data types.
2. **Read `input/payloads/request_memo.md`** for all client facts, goals, account balances, policy details, and dates.
3. **Read `input/prompt.txt`** only for any special instructions; it is usually a generic directive to analyze the memo and template.
4. Produce **only** a JSON object matching the template schema. No markdown fences, no prose outside the JSON.

## 2. Output Format Conventions
- `task_id` must match the task identifier from the directory/prompt (e.g. `train_001`, `test_001`).
- `client_id` comes from the request memo (pattern `CLT-XXXX`).
- `analysis_type` must match the template exactly.
- **USD amounts** are JSON **numbers** (not strings). The training data uses one decimal place for whole-dollar amounts (e.g. `105300.0`) and two for cents when present.
- **Dates** are ISO-8601 (`YYYY-MM-DD`).
- **Enums** must match the template exactly (case-sensitive, underscores preserved). Common enums observed:
  - `primary_action`: `FUND_WITH_CRUMMEY_NOTICES`, `REPLACE_WITH_GRAT`, `STAGED_ROTH_CONVERSION`, `COMBINE_ILIT_AND_GRAT`, etc.
  - `suitability`: `SUITABLE`, `SUITABLE_WITH_ADMINISTRATION`, `SUITABLE_WITH_RISK_ACKNOWLEDGMENT`
  - `risk_flag`: `LOW_IF_FORMALITIES_MET`, `TAX_BRACKET_MANAGEMENT`, `HIGH_DUE_TO_LIQUIDITY_GAP`
  - `heir_tax_profile`: `MIXED_TAXABLE_AND_TAX_FREE`, `MOSTLY_TAX_FREE`, `MOSTLY_TAXABLE`
  - `estate_inclusion_risk`: `LOW_IF_FORMALITIES_MET`

## 3. Source-Resolution Hierarchy
When data conflicts appear in the memo (e.g., profile vs. email vs. custodian), resolve with this priority:

| Data Category | Preferred Source | Fallback Order |
|---------------|------------------|----------------|
| **Profile facts** (estate value, goals, tax rates, ages, marital status) | `SIGNED_PROFILE` | `ATTORNEY_MEMO` → `CUSTODIAN_EXPORT` → `EMAIL` → `CRM_NOTE` |
| **Account balances & holdings** | `CUSTODIAN_EXPORT` | `SIGNED_PROFILE` → `CRM_NOTE` |
| **Policy details** (premiums, death benefits) | `CUSTODIAN_EXPORT` | `SIGNED_PROFILE` → `CRM_NOTE` |

Always record the final choices in a `source_resolution` block at the end of the JSON. Keys vary by analysis type but commonly include:
- `controlling_profile_source` / `controlling_goal_source` / `controlling_estate_source`
- `controlling_account_source` / `controlling_liquid_source`
- `controlling_policy_source` / `controlling_beneficiary_source`

**Rule of thumb:** `SIGNED_PROFILE` wins for any fact the client personally attested to; `CUSTODIAN_EXPORT` wins for hard financial data.

## 4. Estate-Tax Calculation Rules
- **Federal estate tax rate is consistently 40%** in the training data.
- `taxable_estate = gross_estate_value - exemption_used`
- `estate_tax_exposure = taxable_estate × 0.40`
- `liquidity_gap = estate_tax_exposure - liquid_assets_available` (can be negative, indicating surplus liquidity)
- `tax_liquidity_support` from an ILIT = `death_benefit × 0.40` (the estate-tax-equivalent liquidity provided by insurance)

## 5. GRAT Calculation Rules
- Use the **Section 7520 rate** provided in the request memo.
- `annuity_payment = grattable_value / IRS_annuity_factor(term_years, section_7520_rate)`
  - The annuity factor is the present-value-of-an-annuity factor for the given term and 7520 rate (exact IRS Table B or equivalent). Do not invent the factor; derive or verify it from the memo/context.
- `projected_remainder` = the expected trust assets remaining after the annuity term, given the asset growth assumption.
- `estate_tax_reduction = projected_remainder × 0.40`
- `tax_liquidity_support = estate_tax_reduction + liquid_assets_available` (total liquidity created by the strategy)
- `remaining_liquidity_gap = estate_tax_exposure - tax_liquidity_support`

## 6. ILIT / Crummey Administration Rules
- `annual_exclusion_per_beneficiary` is typically **$20,000** in the 2026 planning-year context (verify in memo).
- `annual_exclusion_capacity = per_beneficiary_amount × beneficiary_count`
- `premium_gap = max(0, annual_premium - annual_exclusion_capacity)`
- **Crummey timeline** (strict 7-day / 30-day convention):
  - `contribution_date` from memo
  - `notice_due_date = contribution_date + 7 days`
  - `withdrawal_window_end = notice_due_date + 30 days` (or `contribution_date + 37 days`)
  - `earliest_premium_payment_date = day_after(withdrawal_window_end)`
- `dedicated_bank_account_required = true` for ILITs
- `estate_inclusion_risk = "LOW_IF_FORMALITIES_MET"` when Crummey notices are administered properly
- `projected_outside_estate_if_implemented` = the policy death benefit

## 7. Roth Conversion & RMD Rules
- **RMD start age is 75** under SECURE 2.0 for the clients in the training set (verify birth year; age 74 in 2026 → first RMD year 2027).
- `first_rmd_year = year client turns 75`
- `conversion_years = first_rmd_year - planning_year` (years available to convert before RMDs begin)
- `conversion_years_positive = max(0, conversion_years)`
- `annual_conversion_amount` is either:
  - `total_traditional_balance / conversion_years` when converting the full balance, or
  - The bracket-limited amount when the memo specifies staying within a marginal bracket.
- `total_converted = annual_conversion_amount × conversion_years`
- **Conversion tax rate pitfall:** The effective tax rate applied to conversions may differ from the stated marginal rate. In training data, a stated 24% marginal rate produced a 32% effective rate (`total_conversion_tax / total_converted = 0.32`). Always compute or verify the implied rate from the context rather than blindly using the stated marginal rate.
- **RMD projection through horizon_year:**
  - `baseline_rmd_tax_through_horizon` = tax on RMDs if no conversion occurs
  - `conversion_rmd_tax_through_horizon` = tax on RMDs after reducing the traditional balance
  - `rmd_tax_savings_through_horizon = baseline - conversion`
- **Legacy projection:**
  - `projected_roth_balance_horizon` = converted principal grown tax-free at the assumed rate through the horizon year
  - `projected_traditional_balance_horizon` = residual traditional balance after conversions, RMD withdrawals, and growth
  - `heir_tax_profile`: `MIXED_TAXABLE_AND_TAX_FREE` when both Roth and traditional balances are projected at horizon; use `MOSTLY_TAX_FREE` or `MOSTLY_TAXABLE` when one dominates.

## 8. Combined Strategy Rules (`estate_liquidity_action_plan`)
- When the memo asks for a combined ILIT + GRAT strategy:
  - `primary_action = "COMBINE_ILIT_AND_GRAT"`
  - `sequencing = "ILIT_FIRST_THEN_GRAT"` (standard order observed)
  - Calculate each component separately (ILIT exclusion capacity, GRAT remainder, estate tax reduction) and roll them into the combined JSON.
  - `action_set` is an array of exact strings from the template enum (e.g. `["ATTORNEY_DRAFT_REVIEW", "GRAT_FOR_APPRECIATING_SHARES", "ILIT_CRUMMEY_NOTICE_CYCLE"]`).

## 9. Common Pitfalls
- **Source priority errors:** Defaulting to `EMAIL` or `CRM_NOTE` when `SIGNED_PROFILE` or `CUSTODIAN_EXPORT` is available.
- **Type errors:** Returning `"20000"` or `"20000.0"` instead of `20000.0`. The template expects JSON numbers.
- **Missing `source_resolution`:** Every output must include the `source_resolution` block.
- **Crummey date math:** Using calendar-month approximations instead of exact day counts (7 days for notice, 30 days for withdrawal window).
- **Estate tax rate assumption:** Using a rate other than 40% when the context is federal estate tax.
- **Premium gap sign error:** Reporting a negative gap when the capacity exceeds the premium; gap must be `max(0, premium - capacity)`.
- **Prose leakage:** Any text, comments, or markdown outside the JSON object causes validation failure.

## 10. Pre-Submission Checklist
1. `task_id` and `client_id` match the input.
2. `analysis_type` matches the template exactly.
3. All required top-level keys from `answer_template.json` are present.
4. All enums match the template exactly (case-sensitive).
5. All monetary values are JSON numbers.
6. `source_resolution` reflects the correct hierarchy.
7. Dates are ISO-8601.
8. No markdown, no comments, no trailing text outside the JSON object.
