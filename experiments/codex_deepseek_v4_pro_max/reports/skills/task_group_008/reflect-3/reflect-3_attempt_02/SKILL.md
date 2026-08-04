 # Private Wealth Advisory Planning Skill

 ## Overview

 This skill enables solving structured private wealth advisory planning tasks. Each task provides a client ID, an engagement memo, and an answer template schema. The advisory environment exposes client records, source documents, retirement accounts, life insurance policies, trust candidates, tax policy constants, and RMD factors through REST API endpoints.

 ## Gathering Client Data

 Use the advisory environment API to collect all relevant data before computing any answer:

 - `GET /api/clients` — list all clients; filter by `client_id`
 - `GET /api/clients/{client_id}` — single client demographics and overview
 - `GET /api/source-documents` — signed profiles, attorney memos, CRM notes; filter by `client_id`
 - `GET /api/retirement-accounts` — traditional/Roth balances, expected returns, RMD start age, recommended conversion years
 - `GET /api/life-insurance` — death benefit, annual premium, planned contribution date, ILIT ownership flag
 - `GET /api/trust-candidates` — asset value, growth rate, GRAT/CRAT terms and rates
 - `GET /api/policies/tax` — annual gift exclusion, estate tax exemption, estate tax rate, conversion bracket targets, charitable deduction rate
 - `GET /api/rmd-factors` — IRS life-expectancy divisors keyed by age

 ## Source Resolution

 Multiple source documents may report conflicting facts (e.g., different beneficiary counts or income figures from CRM imports vs signed profiles). Follow this priority order:

 1. **SIGNED_PROFILE** — most recent, signed by client; preferred when available
 2. **CUSTODIAN_EXPORT** — preferred for account balances and retirement data
 3. **ATTORNEY_MEMO** — preferred for trust-asset-related facts when SIGNED_PROFILE does not directly address them
 4. **CRM_NOTE** — older import; use only when newer sources are absent

 For `source_resolution` fields in the answer:
 - `controlling_profile_source` / `controlling_goal_source` / `controlling_beneficiary_source`: **SIGNED_PROFILE**
 - `controlling_account_source`: **CUSTODIAN_EXPORT**
 - `controlling_asset_source`: **ATTORNEY_MEMO**
 - `controlling_policy_source`: **SIGNED_PROFILE**

 ## Roth Conversion & RMD Analysis

 Applies to tasks with `analysis_type: "roth_conversion_rmd"`.

 ### Computing the conversion amount

 1. Determine headroom within the current tax bracket:
   - `headroom = conversion_bracket_target[filing_status] - annual_non_ira_income`
   - The annual conversion amount equals this headroom (convert only up to the bracket top to avoid bracket creep).

 2. Conversion years come from the retirement account's `recommended_conversion_years`.

 3. `first_conversion_year` is the planning year (e.g., 2026).

 4. `conversion_years_positive` equals `conversion_years`.

 ### Conversion and RMD timing model

 Each year follows this order of operations:
 1. **Subtract the conversion amount** (at the start of the year, before growth and before any RMD).
 2. If the client has reached RMD age this year, **compute the RMD from the post-conversion balance** using the IRS divisor for that age.
 3. **Subtract the RMD**.
 4. **Apply growth** to the remaining balance: `balance = (balance - conversion - rmd) * (1 + expected_return)`.

 For years before RMD age, skip steps 2–3 (only subtract conversion, then grow).
 For years after the conversion window but during the RMD window, skip step 1 (only compute RMD, subtract it, then grow).

 ### Computing RMD tax

 - For each RMD year from `first_rmd_year` through `horizon_year`, compute `rmd = balance_at_start / rmd_factor[age]`.
 - RMD tax in a year = `rmd * marginal_tax_rate`.
 - Sum these over the horizon for both baseline (no conversion) and conversion scenarios.

 ### Legacy projection

 - **Roth balance**: Start with existing Roth balance. Each conversion year: `roth = (roth + annual_conversion) * (1 + expected_return)`. Grow through the horizon.
 - **Traditional balance**: The remaining traditional balance at the end of the projection (after all conversions, RMDs, and growth).
 - **heir_tax_profile**: `MIXED_TAXABLE_AND_TAX_FREE` when both Roth and traditional balances remain; `MOSTLY_TAX_FREE` if traditional is near zero; `MOSTLY_TAXABLE` if Roth is near zero.

 ### Recommendation enums

 - `primary_action`: `STAGED_ROTH_CONVERSION` when headroom permits meaningful conversion.
 - `suitability`: `SUITABLE`.
 - `risk_flag`: `TAX_BRACKET_MANAGEMENT` when conversion years precede RMD age by several years; `RMD_NEAR_TERM` when RMDs begin within 1–2 years.

 ## ILIT Crummey Implementation

 Applies to tasks with `analysis_type: "ilit_crummey_implementation"`.

 ### Gift plan

 - `planning_year`: current planning year (e.g., 2026).
 - `annual_exclusion_per_beneficiary`: from tax policy (e.g., $20,000 for 2026).
 - `beneficiary_count`: from the controlling source (SIGNED_PROFILE).
 - `annual_exclusion_capacity`: `beneficiary_count * annual_exclusion_per_beneficiary`.
 - `annual_premium`: from the life-insurance policy record.
 - `premium_gap`: `max(0, annual_premium - annual_exclusion_capacity)`. This is the shortfall — zero when capacity covers the premium.

 ### Administration dates

 - `contribution_date`: the planned contribution date from the life-insurance record.
 - `notice_due_date`: same as contribution date.
 - `withdrawal_window_end`: 30 days after contribution date.
 - `earliest_premium_payment_date`: 31 days after contribution date (one day after the Crummey withdrawal window closes).
 - `notices_required`: equals `beneficiary_count`.
 - `dedicated_bank_account_required`: `true` (ILIT needs a segregated account for Crummey contributions).

 ### Estate result

 - `death_benefit`: from life-insurance record.
 - `estate_inclusion_risk`: `LOW_IF_FORMALITIES_MET` for new policies with sufficient exclusion capacity and proper Crummey process.
 - `projected_outside_estate_if_implemented`: equals `death_benefit`.
 - `tax_liquidity_support`: `death_benefit * estate_tax_rate`.

 ### Recommendation enums

 - `primary_action`: `FUND_WITH_CRUMMEY_NOTICES` when exclusion capacity ≥ premium.
 - `suitability`: `SUITABLE_WITH_ADMINISTRATION`.
 - `risk_flag`: `LOW_IF_FORMALITIES_MET` for new policies with no lookback issue.

 ## Trust Comparison (GRAT vs CRAT)

 Applies to tasks with `analysis_type: "trust_comparison"`.

 ### Estate context

 - `taxable_estate`: from the signed profile or client record.
 - `estate_tax_exposure`: `(taxable_estate - estate_tax_exemption) * estate_tax_rate`.
 - `liquidity_gap_before_planning`: `estate_tax_exposure - liquid_assets`.

 ### GRAT computation (zeroed-out)

 1. Compute the annuity factor: `pv_factor = (1 - (1 + grat_annuity_rate)^(-grat_term_years)) / grat_annuity_rate`.
 2. Annual annuity payment: `asset_value / pv_factor`.
 3. Project forward, each year: `balance = balance * (1 + expected_growth_rate) - annual_annuity`.
 4. `projected_remainder_to_heirs` is the balance after the final year (zero if negative).
 5. `estimated_estate_tax_reduction`: `projected_remainder * estate_tax_rate`.
 6. `term_years`: from trust candidate record.
 7. `mortality_inclusion_risk`: `TERM_SURVIVAL_REQUIRED` (grantor must survive the GRAT term).

 ### CRAT computation

 1. Annual payout: `asset_value * crat_payout_rate`.
 2. Project forward, each year: `balance = balance * (1 + expected_growth_rate) - annual_payout`.
 3. `projected_charitable_remainder` is the balance after the final year (zero if negative).
 4. `estimated_income_tax_deduction`: `projected_charitable_remainder * charitable_deduction_rate`.
 5. `term_years`: from trust candidate record (capped at `max_crat_term_years` from tax policy).
 6. `family_transfer_fit`: `LOW` (CRAT remainder goes to charity, limiting family transfer).

 ### Recommendation enums

 - `preferred_strategy`: `GRAT` when `family_transfer_priority` is "high"; `CRAT` when `philanthropic_intent` is "high".
 - `rationale_code`: `CHILDREN_TRANSFER_PRIORITY` for GRAT; `PHILANTHROPIC_PRIORITY` for CRAT.
 - `alternate_role`: `SECONDARY_CHARITABLE_TOOL` when GRAT is primary; `SECONDARY_FAMILY_TRANSFER_TOOL` when CRAT is primary.

 ## Estate Liquidity Action Plan

 Applies to tasks with `analysis_type: "estate_liquidity_action_plan"`.

 ### Estate context

 - Same as trust comparison: taxable estate, exposure, and liquidity gap.

 ### ILIT component

 - Same gift-plan logic as the ILIT Crummey task: capacity, gap, inclusion risk, projected outside estate.

 ### Trust transfer component

 - `preferred_strategy`: `GRAT` when family transfer priority is high and philanthropic intent is low.
 - Apply the GRAT and CRAT computations described above.

 ### Action set

 - Build a list of applicable actions, then sort alphabetically:
   - `GRAT_FOR_APPRECIATING_SHARES` — always when GRAT is the preferred strategy.
   - `ILIT_CRUMMEY_NOTICE_CYCLE` — always when an ILIT is involved.
   - `ATTORNEY_DRAFT_REVIEW` — include when attorney coordination is noted in the memo.
   - `LIFETIME_EXEMPTION_ALLOCATION` — include when premium exceeds exclusion capacity.

 ### Recommendation enums

 - `primary_action`: `COMBINE_ILIT_AND_GRAT` when both life insurance and appreciating assets are in play.
 - `sequencing`: `ILIT_FIRST_THEN_GRAT` (handle insurance first, then trust transfer).
 - `risk_flag`: `LOW_IF_FORMALITIES_MET` for properly structured new policies.

 ## General Rules

 - All monetary amounts in USD, rounded to two decimal places.
 - All dates in ISO 8601 format (`YYYY-MM-DD`).
 - Numbers must be JSON numbers, never strings.
 - Enum values must match the template choices exactly.
 - The `task_id` field must match the task identifier (e.g., `train_001` or `test_001`).
 - Return only the JSON object; no prose outside it.
 - When source documents conflict, use the priority order described in Source Resolution above.
