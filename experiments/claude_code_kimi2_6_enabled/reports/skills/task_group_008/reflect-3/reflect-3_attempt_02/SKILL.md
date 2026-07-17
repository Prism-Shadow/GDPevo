# Private Wealth Advisory API Skill

## API Base URL
- Use `GDPEVO_ENV_BASE_URL` from the environment. Do not use localhost.

## Available Endpoints
- `GET /api/clients` – list all clients (summary: client_id, household_name, age, marital_status, filing_status, planning_year, estate_value, liquid_assets, record_status, advisor_team)
- `GET /api/clients/{client_id}` – single client summary
- `GET /api/source-documents?client_id={client_id}` – source documents with facts (CRM_NOTE, ATTORNEY_MEMO, SIGNED_PROFILE)
- `GET /api/retirement-accounts?client_id={client_id}` – IRA data: traditional_balance, roth_balance, expected_return, rmd_start_age, recommended_conversion_years
- `GET /api/life-insurance?client_id={client_id}` – life insurance policies: death_benefit, annual_premium, planned_contribution_date, is_existing_policy_transfer
- `GET /api/trust-candidates?client_id={client_id}` – trust data: asset_value, expected_growth_rate, grat_term_years, grat_annuity_rate, crat_term_years, crat_payout_rate
- `GET /api/rmd-factors` – RMD distribution period factors by age (73–99)

## Source Resolution Rules
- **Controlling profile source:** Always prefer `SIGNED_PROFILE` when available. It is the most recent (typically 2026-02-06) and most comprehensive. Fallback order: ATTORNEY_MEMO → CRM_NOTE.
- **Controlling account source:** Use `CUSTODIAN_EXPORT` because the retirement-accounts endpoint returns source_type=CUSTODIAN_EXPORT.
- **Controlling beneficiary source:** Use `SIGNED_PROFILE` for beneficiary_count.
- **Controlling policy source:** For life-insurance, use `SIGNED_PROFILE` if present; otherwise CUSTODIAN_EXPORT.
- **Controlling goal source:** Use `SIGNED_PROFILE` for family_transfer_priority, philanthropic_intent, etc.
- **Controlling asset source:** Use `SIGNED_PROFILE` for asset-related facts (estate_value, liquid_assets). Fallback to ATTORNEY_MEMO.

## Task Types and Templates

### 1. Roth Conversion RMD (analysis_type: `roth_conversion_rmd`)
**Required keys:** task_id, client_id, analysis_type, recommendation, conversion_plan, rmd_projection, legacy_projection, source_resolution

**Key calculations:**
- `first_rmd_year` = planning_year + (rmd_start_age - current_age)
- `conversion_years` = recommended_conversion_years from retirement-accounts
- `conversion_years_positive` = same as conversion_years (must be > 0)
- `annual_conversion_amount` = traditional_balance / conversion_years (rounded to cents)
- `total_converted` = traditional_balance
- `total_conversion_tax` = total_converted * marginal_tax_rate (from signed profile)
- `horizon_year` from request_memo
- RMD tax projections: simulate year-by-year through horizon_year
  - Apply expected_return growth first
  - Then take RMD = traditional_balance / rmd_factor for current_age
  - RMD tax = RMD * marginal_tax_rate
  - For conversion scenario: convert annual amount first, then apply growth, then RMD
- `heir_tax_profile`: if projected_roth_balance_horizon >> projected_traditional_balance_horizon, use `MOSTLY_TAX_FREE`. If mixed, use `MIXED_TAXABLE_AND_TAX_FREE`. If mostly traditional, use `MOSTLY_TAXABLE`.

### 2. ILIT Crummey Implementation (analysis_type: `ilit_crummey_implementation`)
**Required keys:** task_id, client_id, analysis_type, recommendation, gift_plan, administration, estate_result, source_resolution

**Key calculations:**
- `annual_exclusion_per_beneficiary` = $18,000 for 2026
- For **MFJ**: `annual_exclusion_capacity` = beneficiary_count * 2 * $18,000 (both spouses can gift)
- For **SINGLE**: `annual_exclusion_capacity` = beneficiary_count * $18,000
- `premium_gap` = max(0, annual_premium - annual_exclusion_capacity)
- If premium_gap > 0: risk_flag = `EXCLUSION_SHORTFALL`
- If premium_gap == 0: risk_flag = `LOW_IF_FORMALITIES_MET`
- `notices_required` = beneficiary_count
- `contribution_date` = planned_contribution_date from life-insurance
- `notice_due_date` = same as contribution_date
- `withdrawal_window_end` = contribution_date + 30 days (e.g., 2026-03-10 → 2026-04-10)
- `earliest_premium_payment_date` = planned_contribution_date
- `dedicated_bank_account_required` = true
- `tax_liquidity_support` = liquid_assets from client profile

### 3. Trust Comparison (analysis_type: `trust_comparison`)
**Required keys:** task_id, client_id, analysis_type, recommendation, estate_context, grat, crat, source_resolution

**Key data:**
- `preferred_strategy`: GRAT if family_transfer_priority is high and philanthropic_intent is low/moderate; CRAT if philanthropic_intent is high
- `rationale_code`: CHILDREN_TRANSFER_PRIORITY for GRAT; PHILANTHROPIC_PRIORITY for CRAT
- `alternate_role`: SECONDARY_CHARITABLE_TOOL when GRAT is primary; SECONDARY_FAMILY_TRANSFER_TOOL when CRAT is primary
- `taxable_estate` = estate_value from signed profile
- `estate_tax_exposure` = taxable_estate * marginal_tax_rate
- `liquidity_gap_before_planning` = liquid_assets from client profile
- GRAT calculations: use trust-candidates data (asset_value, grat_term_years, grat_annuity_rate, expected_growth_rate)
- CRAT calculations: use trust-candidates data (asset_value, crat_term_years, crat_payout_rate, expected_growth_rate)

### 4. Estate Liquidity Action Plan (analysis_type: `estate_liquidity_action_plan`)
**Required keys:** task_id, client_id, analysis_type, recommendation, estate_context, ilit, trust_transfer, action_set, source_resolution

**Key data:**
- `primary_action`: COMBINE_ILIT_AND_GRAT, CRAT_WITH_LIQUIDITY_REVIEW, or ILIT_WITH_EXEMPTION_REVIEW
- `sequencing`: ILIT_FIRST_THEN_GRAT, TRUST_DECISION_FIRST, or ILIT_FIRST_THEN_ATTORNEY_REVIEW
- `risk_flag`: same risk flags as ILIT tasks
- `taxable_estate` = estate_value
- `estate_tax_exposure` = taxable_estate * marginal_tax_rate
- `liquidity_gap_before_planning` = liquid_assets
- `annual_exclusion_capacity` = beneficiary_count * 2 * $18,000 (MFJ) or beneficiary_count * $18,000 (SINGLE)
- `premium_gap` = max(0, annual_premium - annual_exclusion_capacity)
- `action_set`: sorted alphabetically from [ATTORNEY_DRAFT_REVIEW, CRAT_FOR_CHARITABLE_REMAINDER, GRAT_FOR_APPRECIATING_SHARES, ILIT_CRUMMEY_NOTICE_CYCLE, LIFETIME_EXEMPTION_ALLOCATION]

### 5. GRAT Structured Transfer (analysis_type: `grat_structured_transfer`)
**Required keys:** task_id, client_id, analysis_type, recommendation, grat_details, tax_and_transfer, source_resolution

**Key calculations:**
- `annual_annuity` = asset_value * grat_annuity_rate
- `total_annuity_payments` = annual_annuity * grat_term_years
- `projected_remainder_to_heirs` = asset_value * (1 + expected_growth_rate)^grat_term_years - total_annuity_payments * (1 + expected_growth_rate)^(grat_term_years/2)  [approximate]
- `taxable_gift` = max(0, asset_value - present value of annuity payments)
- `estate_tax_exposure_if_retained` = asset_value * marginal_tax_rate
- `net_estate_tax_savings` = estate_tax_exposure_if_retained - (taxable_gift * marginal_tax_rate)

## Important Pitfalls
1. **MFJ doubles gift exclusion:** For ILIT tasks with married filing jointly, both spouses can gift $18,000 per beneficiary, so capacity = beneficiary_count * 2 * $18,000.
2. **Date formats:** Use ISO YYYY-MM-DD for all dates.
3. **Currency rounding:** Round all USD amounts to cents (2 decimal places).
4. **Source conflicts:** Always prefer SIGNED_PROFILE over CRM_NOTE and ATTORNEY_MEMO for personal facts. Prefer CUSTODIAN_EXPORT for account balances.
5. **Action set sorting:** For estate_liquidity_action_plan, action_set must be sorted alphabetically.
6. **Enum exactness:** Use exact enum values as specified in templates (all caps, underscores).
7. **Missing tax brackets:** No tax bracket endpoint exists; use marginal_tax_rate from signed_profile for all tax calculations.
8. **RMD simulation:** RMDs start at rmd_start_age (typically 73). Use /api/rmd-factors for the divisor. Apply growth before RMD in each year.
9. **Conversion order:** In the conversion scenario, subtract conversion amount first, then apply growth, then take RMD.
10. **Heir tax profile:** Based on relative sizes of Roth vs Traditional at horizon year, not just whether any traditional remains.
11. **Analysis type exactness:** The analysis_type must match the template exactly. Common types: roth_conversion_rmd, ilit_crummey_implementation, trust_comparison, estate_liquidity_action_plan, grat_structured_transfer.
