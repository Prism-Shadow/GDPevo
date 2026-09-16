 # Analysis Types and Computation Guides
 
 Four analysis types appear in the advisory domain. Each has a specific
 answer template and computational approach. The request memo and answer
 template together determine which type applies and which fields are required.
 
 ## Type 1: Roth Conversion RMD (`roth_conversion_rmd`)
 
 **Endpoints needed:** `/api/clients/{id}`, `/api/retirement-accounts`,
 `/api/source-documents`, `/api/policies/tax`, `/api/rmd-factors`,
 `/portal/client/{id}`.
 
 ### Procedure
 
 1. Get client profile. Determine age from `dob` and current year.
    RMDs begin in the year the client turns 73 (current law). Calculate
    `first_rmd_year = birth_year + 73`.
 2. Get retirement accounts. Sum traditional IRA/401k balances and existing
    Roth balances separately. Use the controlling account source.
 3. Get tax policy: `marginal_tax_rate`, `income_tax_rate_top`, `capital_gains_rate`.
 4. Get RMD factor table for divisor-per-age lookups.
 
 ### Conversion Plan
 
 Determine the client's current marginal bracket. Compute the maximum annual
 conversion amount that stays within the current bracket (or the next bracket
 if the strategy targets it). The conversion runs from `first_conversion_year`
 (current year) through the year before `first_rmd_year`.
 
 - `first_conversion_year`: current planning year
 - `conversion_years`: years from current year to `first_rmd_year - 1`, capped
   by available traditional balance
 - `annual_conversion_amount`: total traditional balance divided by conversion_years,
   rounded and adjusted to stay within bracket headroom
 - `total_converted = annual_conversion_amount * conversion_years_positive`
 - `total_conversion_tax = total_converted * marginal_tax_rate`
 - `conversion_years_positive`: same as conversion_years unless zero
 
 ### RMD Projection
 
 Project two scenarios year-by-year from current year through horizon_year:
 
 **Baseline (no conversion):** Traditional balance grows at assumed rate
 (e.g. 6%). Starting in first_rmd_year, compute RMD = prior-year balance /
 divisor for that age. Subtract RMD from balance each year. Accumulate
 RMD * marginal_tax_rate as `baseline_rmd_tax_through_horizon`.
 
 **With conversion:** Same growth logic but the traditional starting balance
 is reduced by total_converted (depleted over conversion_years), and the
 Roth balance grows independently. Compute RMDs on the reduced traditional
 balance. Accumulate RMD * marginal_tax_rate as
 `conversion_rmd_tax_through_horizon`.
 
 - `rmd_tax_savings_through_horizon = baseline - conversion` (should be positive
   when conversion is beneficial)
 
 ### Legacy Projection
 
 Project both balances to horizon_year using the assumed growth rate:
 - `projected_roth_balance_horizon`: Roth starting balance + total_converted,
   grown at assumed rate
 - `projected_traditional_balance_horizon`: Traditional balance after conversions
   and RMDs, grown to horizon
 - `heir_tax_profile`: MOSTLY_TAX_FREE if Roth > 70% of total; MIXED if 30-70%;
   MOSTLY_TAXABLE if traditional > 70%
 
 ### Recommendation Enums
 
 - `primary_action`: STAGED_ROTH_CONVERSION when savings positive and feasible;
   DEFER when near-term RMD complicates; NO_CONVERSION when tax cost outweighs savings
 - `suitability`: SUITABLE when savings substantial; BORDERLINE when marginal;
   DEFER when first_rmd_year <= current_year + 1
 - `risk_flag`: TAX_BRACKET_MANAGEMENT (default), LIQUIDITY_CONSTRAINT (when
   conversion tax strains liquid assets), RMD_NEAR_TERM (when first RMD year
   is imminent)
 
 ## Type 2: ILIT Crummey Implementation (`ilit_crummey_implementation`)
 
 **Endpoints needed:** `/api/clients/{id}`, `/api/life-insurance`,
 `/api/source-documents`, `/api/policies/tax`, `/portal/client/{id}`.
 
 ### Gift Plan
 
 - `planning_year`: current year
 - `annual_exclusion_per_beneficiary`: from tax policy `annual_gift_exclusion`
 - `beneficiary_count`: count of distinct beneficiaries on the policy
 - `annual_exclusion_capacity = exclusion_per_beneficiary * beneficiary_count`
 - `annual_premium`: from life insurance policy record
 - `premium_gap = max(0, annual_premium - annual_exclusion_capacity)`
   (zero when premium fits within exclusion capacity)
 
 ### Administration (Crummey Timing)
 
 The Crummey withdrawal window creates a time buffer between contribution
 and premium payment:
 - `notices_required`: same as beneficiary_count
 - `contribution_date`: a reasonable near-future date (use March of current year
   or the date suggested by source documents)
 - `notice_due_date`: contribution_date + 7 calendar days
 - `withdrawal_window_end`: notice_due_date + 30 calendar days
 - `earliest_premium_payment_date`: withdrawal_window_end + 1 calendar day
 - `dedicated_bank_account_required`: true (standard ILIT administration)
 
 ### Estate Result
 
 - `death_benefit`: from life insurance policy
 - `estate_inclusion_risk`: LOW_IF_FORMALITIES_MET when annual exclusion covers
   premium and no 3-year lookback applies; EXCLUSION_SHORTFALL when premium_gap > 0;
   THREE_YEAR_LOOKBACK when policy transferred within 3 years;
   THREE_YEAR_LOOKBACK_AND_EXCLUSION_SHORTFALL when both apply
 - `projected_outside_estate_if_implemented`: death_benefit (full amount stays
   outside estate when formalities are met); adjust downward if lookback applies
 - `tax_liquidity_support = death_benefit * estate_tax_rate`
 
 ### Recommendation Enums
 
 - `primary_action`: FUND_WITH_CRUMMEY_NOTICES when exclusion capacity covers
   premium; USE_LIFETIME_EXEMPTION_FOR_SHORTFALL when gap exists;
   USE_NEW_POLICY_OR_ACCEPT_LOOKBACK when lookback is the only issue;
   DISCLOSE_LOOKBACK_AND_USE_EXEMPTION when both issues present
 - `suitability`: SUITABLE_WITH_ADMINISTRATION when formalities can be met;
   BORDERLINE when gap or lookback complicates; NOT_SUITABLE when both severe
 - `risk_flag`: matches estate_inclusion_risk
 
 ## Type 3: Trust Comparison (`trust_comparison`)
 
 **Endpoints needed:** `/api/clients/{id}`, `/api/trust-candidates`,
 `/api/source-documents`, `/api/policies/tax`, `/portal/client/{id}`.
 
 ### Estate Context
 
 - `taxable_estate`: total estate value from client profile/assets
 - `estate_tax_exposure = taxable_estate * estate_tax_rate` (only the portion
   above the lifetime exemption)
 - `liquid_assets_available`: from client records
 - `liquidity_gap_before_planning = max(0, estate_tax_exposure - liquid_assets)`
 - `exemption_used`: lifetime exemption amount already consumed
 
 ### GRAT Computation
 
 - `term_years`: from trust candidate record or standard short-term (typically 2-5)
 - `projected_remainder_to_heirs`: the present value of the remainder interest
   that passes to heirs at end of term. Computed by the server based on section
   7520 rate, asset growth assumptions, and annuity payments back to grantor.
   Read from trust candidate record when available.
 - `estimated_estate_tax_reduction = projected_remainder * estate_tax_rate`
 - `mortality_inclusion_risk`: TERM_SURVIVAL_REQUIRED (the grantor must survive
   the GRAT term for the remainder to pass estate-tax-free)
 
 ### CRAT Computation
 
 - `term_years`: from trust candidate record (typically longer: 10-20 years)
 - `projected_charitable_remainder`: present value of the remainder that goes
   to charity at end of term. Read from trust candidate record.
 - `estimated_income_tax_deduction = projected_charitable_remainder * charitable_deduction_rate`
   (charitable_deduction_rate is typically 0.35 from tax policy)
 - `family_transfer_fit`: LOW when primary goal is family transfer (CRAT gives
   to charity); MODERATE when some family benefit exists; HIGH when CRAT
   structure includes family income stream or remainder
 
 ### Recommendation Enums
 
 - `preferred_strategy`: GRAT when family/heir transfer is primary goal;
   CRAT when philanthropic intent dominates
 - `rationale_code`: CHILDREN_TRANSFER_PRIORITY when GRAT chosen;
   PHILANTHROPIC_PRIORITY when CRAT chosen
 - `alternate_role`: SECONDARY_CHARITABLE_TOOL when GRAT primary;
   SECONDARY_FAMILY_TRANSFER_TOOL when CRAT primary
 
 ## Type 4: Estate Liquidity Action Plan (`estate_liquidity_action_plan`)
 
 **Endpoints needed:** `/api/clients/{id}`, `/api/life-insurance`,
 `/api/trust-candidates`, `/api/source-documents`, `/api/policies/tax`,
 `/portal/client/{id}`.
 
 This type combines ILIT analysis with trust comparison and produces an
 ordered action set for attorney coordination.
 
 ### Estate Context
 
 Same computation as Type 3.
 
 ### ILIT Section
 
 Same computation as Type 2's gift plan and estate result, but only the
 fields listed in the template: `annual_exclusion_capacity`, `premium_gap`,
 `estate_inclusion_risk`, `projected_outside_estate_if_implemented`.
 
 ### Trust Transfer Section
 
 Same computation as Type 3 but with combined fields from both GRAT and CRAT:
 `preferred_strategy`, `projected_remainder_to_heirs`,
 `estimated_estate_tax_reduction`, `projected_charitable_remainder`.
 Fill the GRAT remainder fields with the preferred strategy's values;
 fill `projected_charitable_remainder` from the CRAT candidate regardless
 of which is preferred (it informs the alternate tool).
 
 ### Action Set
 
 Build from the following candidates, include only those applicable,
 and sort alphabetically:
 
 - `ATTORNEY_DRAFT_REVIEW`: always included (attorney must draft/review docs)
 - `CRAT_FOR_CHARITABLE_REMAINDER`: include when CRAT is the preferred or
   alternate strategy
 - `GRAT_FOR_APPRECIATING_SHARES`: include when GRAT is the preferred or
   alternate strategy
 - `ILIT_CRUMMEY_NOTICE_CYCLE`: include when ILIT is part of the plan
   (premium_gap is manageable and estate_inclusion_risk is acceptable)
 - `LIFETIME_EXEMPTION_ALLOCATION`: include when premium_gap > 0 or liquidity
   gap requires exemption allocation
 
 ### Recommendation Enums
 
 - `primary_action`: COMBINE_ILIT_AND_GRAT when both are feasible;
   CRAT_WITH_LIQUIDITY_REVIEW when CRAT is better fit;
   ILIT_WITH_EXEMPTION_REVIEW when only ILIT is feasible
 - `sequencing`: ILIT_FIRST_THEN_GRAT (default when both used);
   TRUST_DECISION_FIRST (when trust choice dominates);
   ILIT_FIRST_THEN_ATTORNEY_REVIEW (when only ILIT applies)
 - `risk_flag`: same enums as ILIT risk
 
 ## General Computational Constants
 
 These are representative; always read actual values from `/api/policies/tax`.
 
 - `estate_tax_rate`: typically 0.40
 - `income_tax_rate_top`: 0.37
 - `marginal_tax_rate`: client-specific, from profile
 - `annual_gift_exclusion`: typically $18,000-$20,000 per beneficiary depending
   on year (read from tax policy)
 - `lifetime_exemption`: per-person exemption amount
 - `charitable_deduction_rate`: 0.35
 - `section_7520_rate`: published monthly, used by server for GRAT/CRAT
   present-value computation
 - `growth_rate_assumption`: 0.06 for retirement account projections unless
   server data specifies otherwise
