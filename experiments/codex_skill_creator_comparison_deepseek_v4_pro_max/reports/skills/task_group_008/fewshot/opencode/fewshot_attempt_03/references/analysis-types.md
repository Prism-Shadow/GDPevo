# Engagement Analysis Types

Four engagement types are supported. The request memo identifies the engagement and the answer template specifies the output shape. All computations use data from the API endpoints described in [api-endpoints.md](api-endpoints.md), source resolution from [source-resolution.md](source-resolution.md), and tax/RMD constants from `/api/policies/tax` and `/api/rmd-factors`.

---

## 1. Roth Conversion and RMD Tax Summary

**analysis_type**: `roth_conversion_rmd`

**API data required**: client record, source documents for this client, tax policies, RMD factors, retirement account for this client.

### Derive the client profile

From the signed profile (falling back through the source priority chain): `marginal_tax_rate`, `annual_non_ira_income`, `beneficiary_count`, `age`, `filing_status`. Use `planning_year` from the client record.

### Conversion plan

- `first_conversion_year`: the planning year (2026).
- `conversion_years`: `recommended_conversion_years` from the retirement account record.
- `conversion_years_positive`: same integer as `conversion_years`.
- `annual_conversion_amount`: the lesser of (a) tax-bracket headroom and (b) the per-year share of the traditional balance. Headroom = `conversion_bracket_targets[filing_status] - annual_non_ira_income`. Per-year share = `traditional_balance / conversion_years`. If headroom is negative, conversion may not be viable. Round to cents.
- `total_converted`: `annual_conversion_amount * conversion_years`.
- `total_conversion_tax`: `total_converted * marginal_tax_rate`.

### RMD projection

- `horizon_year`: from the request memo or answer template (typically 2042 or 2046).
- `first_rmd_year`: planning year + (rmd_start_age - current client age). Since `rmd_start_age` is 73, this is: `planning_year + (73 - age)`.
- **Baseline** (no conversion): Start with the full `traditional_balance`. Each year from planning_year through horizon_year:
  1. If the year is >= first_rmd_year, compute RMD = balance at start of year / rmd_factor for that age. Subtract RMD from balance. Accumulate RMD tax = RMD * marginal_tax_rate.
  2. Grow remaining balance by (1 + expected_return).
  3. The Roth balance (if any) grows by (1 + expected_return) but is untouched by RMDs.
- **Conversion scenario**: During conversion years (first_conversion_year through first_conversion_year + conversion_years - 1), move `annual_conversion_amount` from traditional to Roth each year before applying growth. After conversion years, both balances grow at expected_return and RMDs apply to the remaining traditional balance.
- `baseline_rmd_tax_through_horizon`: sum of all RMD taxes in the baseline scenario.
- `conversion_rmd_tax_through_horizon`: sum of all RMD taxes in the conversion scenario.
- `rmd_tax_savings_through_horizon`: `baseline_rmd_tax_through_horizon - conversion_rmd_tax_through_horizon`.

### Legacy projection

- `projected_roth_balance_horizon`: Roth balance at the end of horizon_year under the conversion scenario (after growth and any RMDs).
- `projected_traditional_balance_horizon`: Traditional balance at the end of horizon_year under the conversion scenario.
- `heir_tax_profile`: if Roth > 2x traditional → `MOSTLY_TAX_FREE`; if traditional > 2x Roth → `MOSTLY_TAXABLE`; otherwise → `MIXED_TAXABLE_AND_TAX_FREE`.

### Recommendation

- `primary_action`: `STAGED_ROTH_CONVERSION` if rmd_tax_savings > 0 and conversion is viable; `DEFER` if near RMD age with borderline savings; `NO_CONVERSION` if savings are zero or negative.
- `suitability`: `SUITABLE` if savings are meaningful and headroom is positive; `BORDERLINE` if savings are marginal; `DEFER` if near-term RMDs make conversion impractical.
- `risk_flag`: `TAX_BRACKET_MANAGEMENT` (most common — conversions fill brackets); `LIQUIDITY_CONSTRAINT` (if liquid assets may not cover conversion tax); `RMD_NEAR_TERM` (if first RMD year is within 2 years of planning year).

---

## 2. ILIT Crummey Funding Implementation

**analysis_type**: `ilit_crummey_implementation`

**API data required**: client record, source documents, tax policies, life insurance for this client.

### Derive the client profile

From source documents (signed profile priority): `beneficiary_count`, `marginal_tax_rate`.

### Gift plan

- `planning_year`: from client record.
- `annual_exclusion_per_beneficiary`: from `annual_gift_exclusion` in tax policies for the planning year.
- `beneficiary_count`: from signed profile.
- `annual_exclusion_capacity`: `annual_exclusion_per_beneficiary * beneficiary_count`.
- `annual_premium`: from the life insurance record.
- `premium_gap`: `annual_premium - annual_exclusion_capacity`. If capacity >= premium, gap is 0.0.

### Administration (Crummey notice cycle)

- `notices_required`: same as `beneficiary_count`.
- `contribution_date`: `planned_contribution_date` from the life insurance record.
- `notice_due_date`: 7 calendar days after contribution_date.
- `withdrawal_window_end`: 30 calendar days after notice_due_date.
- `earliest_premium_payment_date`: 1 day after withdrawal_window_end.
- `dedicated_bank_account_required`: true (standard for ILIT Crummey administration).

### Estate result

- `death_benefit`: from the life insurance record.
- `estate_inclusion_risk`: `LOW_IF_FORMALITIES_MET` (default for properly administered ILIT). Use `EXCLUSION_SHORTFALL` if the premium exceeds gift exclusion capacity. Use `THREE_YEAR_LOOKBACK` if `is_existing_policy_transfer` is true. Use `THREE_YEAR_LOOKBACK_AND_EXCLUSION_SHORTFALL` if both conditions apply.
- `projected_outside_estate_if_implemented`: same as `death_benefit` when risk is LOW_IF_FORMALITIES_MET (fully outside estate). If there is a lookback or shortfall, the portion at risk reduces this.
- `tax_liquidity_support`: `death_benefit * estate_tax_rate` (from tax policies, 0.4).

### Recommendation

- `primary_action`: `FUND_WITH_CRUMMEY_NOTICES` if premium_gap = 0 and no lookback. `USE_LIFETIME_EXEMPTION_FOR_SHORTFALL` if premium_gap > 0. `USE_NEW_POLICY_OR_ACCEPT_LOOKBACK` if existing policy transfer is the only issue. `DISCLOSE_LOOKBACK_AND_USE_EXEMPTION` if both shortfall and lookback.
- `suitability`: `SUITABLE_WITH_ADMINISTRATION` when formalities are manageable. `BORDERLINE` if gap or lookback creates uncertainty. `NOT_SUITABLE` if gap is large and no exemption headroom.
- `risk_flag`: matches `estate_inclusion_risk`.

---

## 3. GRAT versus CRAT Comparison

**analysis_type**: `trust_comparison`

**API data required**: client record, source documents, tax policies, trust candidates for this client.

### Derive preferences

From source documents: `philanthropic_intent` and `family_transfer_priority` from the signed profile (or attorney memo as fallback). These drive the recommendation.

### Estate context

- `taxable_estate`: `estate_value - estate_tax_exemption[planning_year]`. If negative, set to 0.
- `estate_tax_exposure`: `taxable_estate * estate_tax_rate` (0.4). If `taxable_estate` is 0, exposure is 0.
- `liquid_assets_available`: from the client record or signed profile.
- `liquidity_gap_before_planning`: `estate_tax_exposure - liquid_assets_available`. If negative, set to 0.0.
- `exemption_used`: `estate_tax_exemption[planning_year]`.

### GRAT computation

- `term_years`: `grat_term_years` from trust candidate record.
- `projected_remainder_to_heirs`: The GRAT remainder. Fund the trust with `asset_value`. The trust assets grow at `expected_growth_rate` each year. The grantor retains an annuity equal to `asset_value * grat_annuity_rate` paid at year-end. After `term_years`, the residual passes to heirs. Compute: start with asset_value, compound forward by expected_growth_rate each year, subtract the annuity payment at year-end, repeat for term_years. The final balance is the remainder. Round to cents.
- `estimated_estate_tax_reduction`: `projected_remainder_to_heirs * estate_tax_rate`. This is the estate tax saved by removing the remainder from the taxable estate.
- `mortality_inclusion_risk`: `TERM_SURVIVAL_REQUIRED` (standard for GRAT — grantor must survive the term for assets to pass estate-tax-free).

### CRAT computation

- `term_years`: `crat_term_years` from trust candidate (capped at `max_crat_term_years` from tax policy, 20).
- `projected_charitable_remainder`: CRAT remainder passing to charity. Fund with `asset_value`. Assets grow at `expected_growth_rate`. Each year the trust pays a fixed amount equal to `asset_value * crat_payout_rate` to the charity. After `term_years`, the remaining corpus passes to charity. Compute similarly to GRAT: compound with growth, subtract annual payout each year, final balance is the charitable remainder.
- `estimated_income_tax_deduction`: `projected_charitable_remainder * charitable_deduction_rate` (0.35 from tax policy).
- `family_transfer_fit`: `LOW` (CRAT primarily benefits charity, not family). `MODERATE` if philanthropic intent is moderate. `HIGH` only if philanthropic intent is high AND family transfer priority is low.

### Recommendation

- `preferred_strategy`: `GRAT` when `family_transfer_priority` = "high". `CRAT` when `philanthropic_intent` = "high" and family_transfer_priority is not "high".
- `rationale_code`: `CHILDREN_TRANSFER_PRIORITY` when GRAT is preferred. `PHILANTHROPIC_PRIORITY` when CRAT is preferred.
- `alternate_role`: `SECONDARY_CHARITABLE_TOOL` when GRAT is primary (CRAT can serve philanthropic goals). `SECONDARY_FAMILY_TRANSFER_TOOL` when CRAT is primary.

---

## 4. Estate Liquidity Action Plan

**analysis_type**: `estate_liquidity_action_plan`

**API data required**: client record, source documents, tax policies, life insurance for this client, trust candidates for this client.

This engagement combines ILIT analysis and trust transfer analysis into a coordinated action plan.

### Estate context

Compute identically to the trust comparison type: `taxable_estate`, `estate_tax_exposure`, `liquid_assets_available`, `liquidity_gap_before_planning`, `exemption_used`.

### ILIT section

Compute identically to the ILIT Crummey type: `annual_exclusion_capacity`, `premium_gap`, `estate_inclusion_risk`, `projected_outside_estate_if_implemented`.

### Trust transfer section

Compute identically to the trust comparison type, but report only one strategy (whichever is preferred): `preferred_strategy`, `projected_remainder_to_heirs`, `estimated_estate_tax_reduction`, `projected_charitable_remainder`. For the charitable remainder, compute the GRAT remainder even if GRAT is preferred — the value still matters for estate planning context.

### Recommendation

- `primary_action`: `COMBINE_ILIT_AND_GRAT` when both ILIT and GRAT are indicated. `CRAT_WITH_LIQUIDITY_REVIEW` when CRAT is preferred and liquidity gap exists. `ILIT_WITH_EXEMPTION_REVIEW` when ILIT alone is the primary tool.
- `sequencing`: `ILIT_FIRST_THEN_GRAT` (implement ILIT immediately for the Crummey cycle, then fund the GRAT). `TRUST_DECISION_FIRST` when the trust choice is the primary decision. `ILIT_FIRST_THEN_ATTORNEY_REVIEW` when attorney review of ILIT documents is needed before GRAT funding.
- `risk_flag`: same risk flags as ILIT type.

### Action set

A sorted array of enums describing the concrete steps. Select from: `ATTORNEY_DRAFT_REVIEW`, `CRAT_FOR_CHARITABLE_REMAINDER`, `GRAT_FOR_APPRECIATING_SHARES`, `ILIT_CRUMMEY_NOTICE_CYCLE`, `LIFETIME_EXEMPTION_ALLOCATION`. Always include `ATTORNEY_DRAFT_REVIEW` (every plan requires attorney coordination). Sort alphabetically.
