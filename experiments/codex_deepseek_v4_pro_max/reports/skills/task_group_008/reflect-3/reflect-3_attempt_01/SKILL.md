 # Private Wealth Advisory Structured Planning Skill
 
 Generate structured JSON planning outputs for private wealth advisory engagements using a task-group advisory API.
 
 ## API Data Sources
 
 Query the advisory API base URL (provided by the harness as `API_BASE` or `GDPEVO_ENV_BASE_URL`) for all available data before computing any answer.
 
 Endpoints to query:
 - `GET /api/clients` — all client records
 - `GET /api/clients/{client_id}` — specific client detail
 - `GET /api/source-documents` — CRM notes, attorney memos, signed profiles; used for source resolution
 - `GET /api/retirement-accounts` — IRA balances, expected returns, RMD start ages, recommended conversion years
 - `GET /api/life-insurance` — death benefits, annual premiums, planned contribution dates, existing-policy-transfer flags
 - `GET /api/trust-candidates` — asset values, growth rates, GRAT/CRAT terms and rates
 - `GET /api/policies/tax` — gift exclusions, estate tax exemptions/rates, conversion bracket targets, charitable deduction rates
 - `GET /api/rmd-factors` — distribution period factors keyed by age
 
 ## Source Resolution Rules
 
 When multiple source documents exist for a client, resolve conflicts using recency and completeness:
 - **SIGNED_PROFILE** controls profile facts (income, marginal rate, beneficiary count, priorities) — it is the most recent and comprehensive.
 - **CUSTODIAN_EXPORT** controls account balances and IRA parameters.
 - **ATTORNEY_MEMO** may control asset-source designations in trust-comparison contexts.
 - CRM_NOTE and STALE_MARKETING_INTAKE are superseded by more recent documents.
 
 ## Task-Type-Specific Computation Rules
 
 ### roth_conversion_rmd (train_001, train_005 pattern)
 
 1. Compute bracket headroom:
    - headroom = conversion_bracket_target[filing_status] - annual_non_ira_income (from SIGNED_PROFILE)
    - If headroom ≤ 0, headroom = 0
 
 2. Conversion plan:
    - annual_conversion_amount = headroom (NOT traditional_balance / conversion_years)
    - total_converted = annual_conversion_amount × conversion_years (capped at traditional_balance)
    - total_conversion_tax = total_converted × marginal_tax_rate
    - first_conversion_year = planning_year
    - conversion_years = recommended_conversion_years from retirement account
 
 3. RMD projection — use this exact order within each year (jan-1 to dec-31):
    a. Convert (remove from traditional, add to Roth) if within conversion window
    b. Take RMD from traditional: RMD = traditional_balance / rmd_factor[current_age]
       RMD tax = RMD × marginal_tax_rate
    c. Grow remaining traditional and all Roth by expected_return
 
 4. Baseline RMD projection: same as above but skip the conversion step (a).
 
 5. Legacy projection uses the conversion-scenario ending balances.
 
 6. Key dates:
    - planning_year = client.planning_year
    - first_rmd_year = planning_year + (rmd_start_age - client_age)
    - horizon_year = from request memo
 
 ### ilit_crummey_implementation (train_002 pattern)
 
 1. Gift plan:
    - annual_exclusion_per_beneficiary = annual_gift_exclusion[planning_year]
    - beneficiary_count from SIGNED_PROFILE
    - annual_exclusion_capacity = beneficiary_count × annual_exclusion_per_beneficiary
    - annual_premium from life-insurance record
    - premium_gap = max(0, annual_premium - annual_exclusion_capacity)
 
 2. Administration dates (from planned_contribution_date):
    - contribution_date = planned_contribution_date
    - notice_due_date = contribution_date
    - withdrawal_window_end = contribution_date + 30 days
    - earliest_premium_payment_date = withdrawal_window_end
    - dedicated_bank_account_required = true
    - notices_required = beneficiary_count
 
 3. Risk assessment:
    - If is_existing_policy_transfer = true → THREE_YEAR_LOOKBACK concerns
    - If premium_gap > 0 → EXCLUSION_SHORTFALL
    - Otherwise → LOW_IF_FORMALITIES_MET
 
 4. Estate result:
    - death_benefit from life-insurance record
    - projected_outside_estate_if_implemented = death_benefit
    - tax_liquidity_support = death_benefit × estate_tax_rate (provides liquidity for that much estate tax)
 
 ### trust_comparison (train_003 pattern)
 
 1. Estate context:
    - taxable_estate = estate_value from SIGNED_PROFILE
    - estate_tax_exposure = max(0, (taxable_estate - estate_tax_exemption) × estate_tax_rate)
    - liquidity_gap_before_planning = max(0, estate_tax_exposure - liquid_assets - life_insurance_death_benefit)
 
 2. GRAT remainder (end-of-year annuity payment model):
    - Annual payment P = asset_value × grat_annuity_rate
    - After n = grat_term_years at growth g:
      remainder = A × (1+g)^n - P × ((1+g)^n - 1) / g
    - estimated_estate_tax_reduction = remainder × estate_tax_rate
    - mortality_inclusion_risk = TERM_SURVIVAL_REQUIRED
 
 3. CRAT remainder (same formula with crat parameters):
    - Annual payment P = asset_value × crat_payout_rate
    - remainder = A × (1+g)^n - P × ((1+g)^n - 1) / g
    - estimated_income_tax_deduction = remainder × charitable_deduction_rate
 
 4. Recommendation:
    - If family_transfer_priority = "high" and philanthropic_intent ≠ "high" → GRAT, CHILDREN_TRANSFER_PRIORITY, SECONDARY_CHARITABLE_TOOL
    - If philanthropic_intent = "high" → CRAT, PHILANTHROPIC_PRIORITY, SECONDARY_FAMILY_TRANSFER_TOOL
 
 ### estate_liquidity_action_plan (train_004 pattern)
 
 1. Estate context (same as trust_comparison above).
 
 2. ILIT section:
    - Same gift-plan and capacity rules as ilit_crummey_implementation
    - projected_outside_estate_if_implemented = death_benefit
 
 3. Trust transfer:
    - Use GRAT formulas above
    - Also compute CRAT charitable remainder
 
 4. Action set — include only applicable actions, then sort alphabetically:
    - ATTORNEY_DRAFT_REVIEW: always include (implementation requires legal review)
    - GRAT_FOR_APPRECIATING_SHARES: include when family_transfer_priority = "high" and there are trust assets with expected growth > annuity/hurdle rate
    - ILIT_CRUMMEY_NOTICE_CYCLE: include when there is a life-insurance policy
    - LIFETIME_EXEMPTION_ALLOCATION: include only when premium_gap > 0 (shortfall requires exemption)
    - CRAT_FOR_CHARITABLE_REMAINDER: include only when philanthropic_intent = "high"
 
 ## General Rules
 
 - All USD amounts rounded to cents (2 decimal places).
 - ISO 8601 dates (YYYY-MM-DD).
 - Numbers must be JSON numbers, not strings.
 - Return only the JSON object — no prose outside the JSON.
 - Top-level keys must match the answer template exactly, including all required_keys.
 - Enum values must match the template exactly (case-sensitive).
 - The `task_id` field must be the stable task identifier (e.g., `"train_001"`, `"test_001"`).
