 # Private Wealth Advisory Structured Output Skill

 ## Purpose

 Generate structured JSON planning outputs for private wealth advisory engagements by gathering data from the advisory API environment, resolving conflicts across data sources, performing financial computations, and formatting results to match the supplied answer template.

 ## Environment

 The advisory API is reachable through a base URL exposed by the harness (typically `API_BASE` or `GDPEVO_ENV_BASE_URL`). All endpoints are relative to this base.

 ### Available Endpoints

 | Endpoint | Content |
 |---|---|
 | `GET /api/clients` | All client records (demographics, estate value, liquid assets, filing status) |
 | `GET /api/clients/{client_id}` | Single client record |
 | `GET /api/source-documents` | Signed profiles, attorney memos, CRM notes — may conflict |
 | `GET /api/retirement-accounts` | Custodian exports: traditional/Roth IRA balances, expected returns, RMD start age, recommended conversion years |
 | `GET /api/life-insurance` | Policy records: death benefit, annual premium, planned contribution date, new vs existing transfer |
 | `GET /api/trust-candidates` | Trust parameters: asset value, growth rate, GRAT/CRAT terms and rates |
 | `GET /api/policies/tax` | Annual gift exclusion, estate tax exemption, estate tax rate, conversion bracket targets, charitable deduction rate, max CRAT term |
 | `GET /api/rmd-factors` | IRS RMD Uniform Lifetime Table factors keyed by age (73–99) |

 ## Core Workflow

 1. **Read the request memo** (usually at `input/payloads/request_memo.md`) to extract the client ID, engagement type, and planning horizon.
 2. **Read the answer template** (usually at `input/payloads/answer_template.json`) to understand the exact output schema, field types, enums, and required keys.
 3. **Fetch all API data** relevant to that client — clients, source documents, retirement accounts, life insurance, trust candidates, tax policies, and RMD factors.
 4. **Resolve data conflicts** by selecting the most authoritative source for each disputed fact (see Source Resolution below).
 5. **Compute financial projections** using the resolved data and formulas in this guide.
 6. **Return only a JSON object** conforming to the answer template; no prose outside the JSON.

 ## Source Resolution

 Client data may come from multiple sources that disagree. The hierarchy from most to least authoritative is:

 1. **SIGNED_PROFILE** — latest client-signed planning document (most recent effective date, usually 2026-02-06)
 2. **ATTORNEY_MEMO** — attorney planning notes (usually 2026-01-18)
 3. **CUSTODIAN_EXPORT** — direct custodian account data
 4. **CRM_NOTE** — older CRM import (usually 2025-11-20)
 5. **STALE_MARKETING_INTAKE** — oldest/unreliable

 **Resolution rules:**
- For profile facts (income, marginal tax rate, beneficiary count, age, filing status, marital status, philanthropic intent, family transfer priority, liquid assets, estate value), prefer the highest-ranked source that contains the fact.
- For account data (IRA balances, expected return), the `CUSTODIAN_EXPORT` is the controlling account source.
- When a field exists in multiple sources, use the value from the highest-ranked source. If a source does not have the field, fall back to the next source down the hierarchy.
- The `controlling_profile_source` in the output should be the source used for the majority of profile-level facts. The `controlling_account_source` (or `controlling_beneficiary_source`, `controlling_policy_source`, `controlling_goal_source`, `controlling_asset_source`) should name the source actually used for those facts.

 ## Analysis Types

 ### 1. `roth_conversion_rmd` — Roth Conversion & RMD Tax Summary

 **Required API data:** Client record, source documents, retirement account, tax policies, RMD factors.

 **Key computations:**

 *Annual conversion amount:*
 ```
 annual_conversion_amount = bracket_target[filing_status] - annual_non_ira_income
 ```
 where `bracket_target` comes from `GET /api/policies/tax` → `conversion_bracket_targets` (e.g. MFJ=394600, SINGLE=197300) and `annual_non_ira_income` is the resolved profile income.

 *Total converted and tax:*
 ```
 total_converted = annual_conversion_amount × recommended_conversion_years
 total_conversion_tax = total_converted × marginal_tax_rate
 ```
 `recommended_conversion_years` comes from the retirement account custodian export.

 *Conversion years positive:* Same as `conversion_years`.

 *First conversion year:* The `planning_year` from the resolved client profile (typically 2026).

 *RMD projection:*
- `first_rmd_year` = planning_year + (rmd_start_age − client_age)  [from custodian export → `rmd_start_age`, resolved profile → `age`]
- `horizon_year` = the planning horizon from the request memo
- **Baseline (no conversion):** Start with `traditional_balance`. For each year from planning_year+1 to horizon_year: compound at `expected_return`. From first_rmd_year onward, compute RMD = balance / rmd_factor[age], RMD tax = RMD × marginal_tax_rate, and subtract RMD from balance. Sum all RMD taxes.
- **Conversion scenario:** Annual conversions of `annual_conversion_amount` for `conversion_years` starting at `first_conversion_year`. The traditional balance is reduced by the conversion amount each year. RMDs are computed on the reduced traditional balance. Roth balance grows at `expected_return` compounded, receiving the annual conversions.
- `rmd_tax_savings_through_horizon` = baseline RMD tax − conversion RMD tax

 *Legacy projection:*
- `projected_roth_balance_horizon` = Roth balance after conversions + growth to horizon year
- `projected_traditional_balance_horizon` = Traditional balance after conversions, growth, and RMDs through horizon year
- `heir_tax_profile`: `MOSTLY_TAX_FREE` if Roth >> Traditional at horizon; `MOSTLY_TAXABLE` if Traditional >> Roth; otherwise `MIXED_TAXABLE_AND_TAX_FREE`

 *Recommendation:*
- `primary_action`: `STAGED_ROTH_CONVERSION` if savings are positive and suitability holds; `DEFER` if borderline; `NO_CONVERSION` if unsuitable
- `suitability`: `SUITABLE` if tax savings justify the conversion; `BORDERLINE` if marginal; `DEFER` if not recommended
- `risk_flag`: `TAX_BRACKET_MANAGEMENT` (default for staged conversions), `LIQUIDITY_CONSTRAINT`, or `RMD_NEAR_TERM` (when RMD start is imminent)

 ### 2. `ilit_crummey_implementation` — ILIT Crummey Funding Cycle

 **Required API data:** Client record, source documents, life insurance, tax policies.

 **Key computations:**

 *Gift plan:*
- `planning_year` = resolved profile `planning_year` (typically 2026)
- `annual_exclusion_per_beneficiary` = from `GET /api/policies/tax` → `annual_gift_exclusion` for the planning year
- `beneficiary_count` = resolved profile `beneficiary_count`
- `annual_exclusion_capacity` = annual_exclusion_per_beneficiary × beneficiary_count
- `annual_premium` = life insurance `annual_premium` for the client
- `premium_gap` = max(0, annual_premium − annual_exclusion_capacity)

 *Administration dates (Crummey timeline):*
 Starting from `planned_contribution_date` (from life insurance):
- `notice_due_date` = contribution_date + 7 days
- `withdrawal_window_end` = notice_due_date + 30 days
- `earliest_premium_payment_date` = withdrawal_window_end + 1 day
- `notices_required` = beneficiary_count
- `dedicated_bank_account_required` = always `true` for ILIT administration

 *Estate result:*
- `death_benefit` = from life insurance policy
- `estate_inclusion_risk` = same flags as `risk_flag`
- `projected_outside_estate_if_implemented` = death_benefit (excluded if formalities met)
- `tax_liquidity_support` = death_benefit × estate_tax_rate (0.40)

 *Recommendation:*
- `primary_action`: `FUND_WITH_CRUMMEY_NOTICES` if premium ≤ exclusion capacity and no lookback issues; `USE_LIFETIME_EXEMPTION_FOR_SHORTFALL` if premium gap > 0; `USE_NEW_POLICY_OR_ACCEPT_LOOKBACK` for existing policy transfers within 3-year window; `DISCLOSE_LOOKBACK_AND_USE_EXEMPTION` for both issues
- `suitability`: `SUITABLE_WITH_ADMINISTRATION` if formalities can be met; `BORDERLINE` if minor issues; `NOT_SUITABLE` if major obstacles
- `risk_flag`: `LOW_IF_FORMALITIES_MET` for clean new policy; `EXCLUSION_SHORTFALL` if premium > exclusion; `THREE_YEAR_LOOKBACK` for existing policy transfer; `THREE_YEAR_LOOKBACK_AND_EXCLUSION_SHORTFALL` for both

 ### 3. `trust_comparison` — GRAT vs. CRAT Recommendation

 **Required API data:** Client record, source documents, trust candidates, tax policies.

 **Key computations:**

 *Estate context:*
- `planning_year` = resolved profile `planning_year`
- `exemption_used` = resolved estate_value − estate_tax_exemption from tax policies (for the planning year), but cap at estate_value
- Actually: `exemption_used` = the estate_tax_exemption amount; `taxable_estate` = max(0, estate_value − estate_tax_exemption); `estate_tax_exposure` = taxable_estate × estate_tax_rate (0.40)
- `liquid_assets_available` = resolved profile `liquid_assets`
- `liquidity_gap_before_planning` = max(0, estate_tax_exposure − liquid_assets_available)

 *GRAT:*
- `term_years` = trust candidate `grat_term_years`
- `projected_remainder_to_heirs` = asset_value × (1+expected_growth_rate)^term_years − annuity_value × Σ(1+expected_growth_rate)^(term_years−t) for t=1 to term_years, where annuity_value = asset_value × grat_annuity_rate / (1 − (1+grat_annuity_rate)^(−term_years)) × (actuarial or fixed computation)
- A simplified approximation: remainder ≈ asset_value × ((1 + expected_growth)^grat_term − grat_annuity_rate × grat_term)
- `estimated_estate_tax_reduction` = projected_remainder_to_heirs × estate_tax_rate
- `mortality_inclusion_risk` = `TERM_SURVIVAL_REQUIRED`

 *CRAT:*
- `term_years` = trust candidate `crat_term_years`
- `projected_charitable_remainder` = asset_value × (1 + expected_growth)^crat_term − crat_payout_rate × asset_value × crat_term × (1+expected_growth_rate/2)^crat_term (or similar present-value calculation)
- `estimated_income_tax_deduction` = projected_charitable_remainder × charitable_deduction_rate (0.35)
- `family_transfer_fit`: `HIGH` if family_transfer_priority is high and remainder is substantial; `LOW` if philanthropic intent high/low remainder; `MODERATE` otherwise

 *Recommendation:*
- `preferred_strategy`: `GRAT` if family_transfer_priority is high and remainder significant; `CRAT` if philanthropic intent is high
- `rationale_code`: `CHILDREN_TRANSFER_PRIORITY` for GRAT-favored; `PHILANTHROPIC_PRIORITY` for CRAT-favored
- `alternate_role`: `SECONDARY_CHARITABLE_TOOL` if GRAT preferred (for the CRAT)

 ### 4. `estate_liquidity_action_plan` — Estate Liquidity Action Plan

 **Required API data:** Client record, source documents, life insurance, trust candidates, tax policies.

 Combines estate context computation (from trust_comparison), ILIT analysis (from ilit_crummey_implementation), and trust comparison (from trust_comparison) into one output.

 *Additional fields:*
- `action_set`: Alphabetically sorted list of actions from: `ATTORNEY_DRAFT_REVIEW`, `CRAT_FOR_CHARITABLE_REMAINDER`, `GRAT_FOR_APPRECIATING_SHARES`, `ILIT_CRUMMEY_NOTICE_CYCLE`, `LIFETIME_EXEMPTION_ALLOCATION`. Include only those relevant to the engagement.
- `recommendation.primary_action`: `COMBINE_ILIT_AND_GRAT` (most common), `CRAT_WITH_LIQUIDITY_REVIEW`, or `ILIT_WITH_EXEMPTION_REVIEW`
- `recommendation.sequencing`: `ILIT_FIRST_THEN_GRAT`, `TRUST_DECISION_FIRST`, or `ILIT_FIRST_THEN_ATTORNEY_REVIEW`

 *Trust transfer section:*
- `projected_remainder_to_heirs` and `estimated_estate_tax_reduction` use the preferred trust strategy (GRAT or CRAT)
- `projected_charitable_remainder` shows the CRAT scenario

 ## Computation Utilities

 ### Compound growth
 ```
 future_value = principal × (1 + rate)^years
 ```

 ### RMD for a given age
 ```
 rmd = traditional_balance / rmd_factor[age]
 ```
 Use `GET /api/rmd-factors` for the factor table.

 ### Year-by-year projection
 Loop year from planning_year+1 to horizon_year:
 1. Apply growth: `balance *= (1 + expected_return)`
 2. If age ≥ rmd_start_age: compute RMD, subtract from balance, accumulate RMD tax
 3. If year is a conversion year (for `roth_conversion_rmd`): subtract conversion from traditional, add to Roth

 ### Estate tax
 ```
 taxable_estate = max(0, estate_value − estate_tax_exemption)
 estate_tax_exposure = taxable_estate × 0.40
 liquidity_gap = max(0, estate_tax_exposure − liquid_assets)
 ```

 ## Output Rules

- Return **only** a single JSON object — no markdown fences, no explanatory prose.
- All monetary values are in USD rounded to two decimal places.
- Dates use ISO 8601 format (`YYYY-MM-DD`).
- Numbers must be JSON numbers (not strings).
- Object keys must match the answer template exactly.
- `action_set` lists (for `estate_liquidity_action_plan`) must be sorted alphabetically.
- `task_id` should match the task identifier provided by the harness (e.g. `train_001`, `test_001`).
- `analysis_type` must match the enum value from the answer template:
  - `roth_conversion_rmd`
  - `ilit_crummey_implementation`
  - `trust_comparison`
  - `estate_liquidity_action_plan`

 ## Edge Cases & Gotchas

- **Near-RMD clients:** When the client age is already at or past `rmd_start_age`, `first_rmd_year` equals the planning year (current year). The first RMD is taken immediately.
- **Zero Roth starting balance:** Some clients have `roth_balance: 0` — this is normal and conversions build from scratch.
- **Premium gap zero:** When `annual_premium ≤ annual_exclusion_capacity`, `premium_gap` is `0.0` (not negative).
- **Estate within exemption:** When `estate_value ≤ estate_tax_exemption`, taxable estate and exposure are zero; liquidity gap is zero.
- **Existing policy transfers:** An `is_existing_policy_transfer: true` flag on a life insurance policy triggers three-year lookback risk. The recommendation and risk flag should reflect this.
- **Empty `action_set`:** Always include at least one relevant action. If no planning actions apply, include `ATTORNEY_DRAFT_REVIEW` as the minimum.
- **Date arithmetic:** Crummey notice dates are computed as calendar days from the contribution date. The `notice_due_date` is contribution_date + 7 days; `withdrawal_window_end` is notice_due_date + 30 days; `earliest_premium_payment_date` is withdrawal_window_end + 1 day.
