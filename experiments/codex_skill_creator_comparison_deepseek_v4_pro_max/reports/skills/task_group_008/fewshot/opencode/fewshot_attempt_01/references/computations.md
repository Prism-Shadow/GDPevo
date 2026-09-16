# Computation Guide by Analysis Type

This reference gives formulas and workflows for each analysis type. All formulas use data from the resolved sources (see SKILL.md Step 3 for source resolution).

Common conventions:
- `(1 + r)^n` means compound growth over n years at rate r
- Round all USD amounts to two decimal places before output
- Use the 2026 tax policy values unless the memo specifies a different planning year
- For MFJ filers, the estate tax exemption is **doubled** (2x the single value)

---

## roth_conversion_rmd

Used for: Roth conversion staging and RMD tax projections.

### Data sources

| Data | Source |
|---|---|
| age, filing_status, annual_non_ira_income, marginal_tax_rate | SIGNED_PROFILE |
| traditional_balance, roth_balance, expected_return, rmd_start_age, recommended_conversion_years | CUSTODIAN_EXPORT (retirement-accounts API) |
| conversion_bracket_targets | /api/policies/tax |
| rmd_factors | /api/rmd-factors |
| horizon_year | request memo (e.g., 2046, 2042) |

### Recommendation

**primary_action:**
- `STAGED_ROTH_CONVERSION` -- when total_converted is positive and horizon extends well past first RMD year
- `DEFER` -- when the client is very close to RMD age with limited runway
- `NO_CONVERSION` -- when tax bracket already at top or no traditional balance

**suitability:**
- `SUITABLE` when conversion tax bracket management is feasible
- `BORDERLINE` when the benefit is marginal
- `DEFER` when conversion would create liquidity constraints or bracket jumps

**risk_flag:**
- `TAX_BRACKET_MANAGEMENT` -- primary concern is staying within target bracket during conversion years
- `LIQUIDITY_CONSTRAINT` -- concern is having enough liquid assets outside the IRA to pay conversion taxes
- `RMD_NEAR_TERM` -- RMDs begin before conversion years complete

### Conversion plan

```
annual_conversion_amount = conversion_bracket_targets[filing_status] - annual_non_ira_income
```

The annual conversion amount fills the gap between non-IRA income and the bracket ceiling. This keeps the conversion within the current marginal bracket.

```
total_converted = annual_conversion_amount * recommended_conversion_years
total_conversion_tax = total_converted * marginal_tax_rate
conversion_years = recommended_conversion_years
conversion_years_positive = recommended_conversion_years
first_conversion_year = planning_year (usually 2026)
```

### RMD projection

```
first_rmd_year = planning_year + (rmd_start_age - age)
```

**Year-by-year simulation (run twice: once without conversions, once with):**

For each year from `planning_year` through `horizon_year`:

1. Apply growth: `traditional_balance *= (1 + expected_return)` and `roth_balance *= (1 + expected_return)`
2. If in conversion years and doing the conversion run: subtract `annual_conversion_amount` from traditional, add same to Roth
3. If current_age >= rmd_start_age: compute RMD = `traditional_balance / rmd_factor[current_age]`, add `RMD * marginal_tax_rate` to total RMD tax, subtract RMD from traditional_balance

Current age in year Y = age + (Y - planning_year).

**Output fields:**

- `baseline_rmd_tax_through_horizon` -- total RMD tax from the no-conversion simulation
- `conversion_rmd_tax_through_horizon` -- total RMD tax from the with-conversion simulation
- `rmd_tax_savings_through_horizon` = baseline - conversion

### Legacy projection

From the with-conversion simulation's final state:

- `projected_roth_balance_horizon` -- final Roth balance
- `projected_traditional_balance_horizon` -- final traditional balance
- `heir_tax_profile`:
  - `MOSTLY_TAX_FREE` when Roth >> traditional (most assets pass tax-free)
  - `MIXED_TAXABLE_AND_TAX_FREE` when both balances are substantial
  - `MOSTLY_TAXABLE` when traditional >> Roth

### Source resolution

- `controlling_profile_source`: `SIGNED_PROFILE` (most authoritative profile document)
- `controlling_account_source`: `CUSTODIAN_EXPORT` (only source for account data)

---

## ilit_crummey_implementation

Used for: ILIT Crummey funding cycle verification for the first premium payment.

### Data sources

| Data | Source |
|---|---|
| beneficiary_count | SIGNED_PROFILE |
| annual_gift_exclusion | /api/policies/tax (use planning year) |
| death_benefit, annual_premium, planned_contribution_date, is_existing_policy_transfer | /api/life-insurance |
| estate_tax_rate | /api/policies/tax |

### Recommendation

**primary_action:**
- `FUND_WITH_CRUMMEY_NOTICES` -- full premium covered by annual exclusions, standard Crummey process
- `USE_LIFETIME_EXEMPTION_FOR_SHORTFALL` -- premium exceeds exclusion capacity, need to use lifetime exemption for the gap
- `USE_NEW_POLICY_OR_ACCEPT_LOOKBACK` -- existing policy transfer triggers three-year lookback
- `DISCLOSE_LOOKBACK_AND_USE_EXEMPTION` -- transfer plus shortfall

**suitability:**
- `SUITABLE_WITH_ADMINISTRATION` -- process works with formalities met
- `BORDERLINE` -- some risk or complexity
- `NOT_SUITABLE` -- significant risks or conflicts

**risk_flag:**
- `LOW_IF_FORMALITIES_MET` -- new policy, premium fits within exclusions
- `EXCLUSION_SHORTFALL` -- premium exceeds annual exclusion capacity
- `THREE_YEAR_LOOKBACK` -- existing policy transfer triggers Section 2035 lookback
- `THREE_YEAR_LOOKBACK_AND_EXCLUSION_SHORTFALL` -- both conditions apply

### Gift plan

```
annual_exclusion_per_beneficiary = annual_gift_exclusion[planning_year]  (e.g., 20000 for 2026)
beneficiary_count = from SIGNED_PROFILE
annual_exclusion_capacity = annual_exclusion_per_beneficiary * beneficiary_count
annual_premium = from life-insurance API
premium_gap = max(0, annual_premium - annual_exclusion_capacity)
```

### Administration (Crummey timeline)

```
contribution_date = planned_contribution_date from life-insurance API
notice_due_date = contribution_date + 7 days
withdrawal_window_end = notice_due_date + 30 days
earliest_premium_payment_date = withdrawal_window_end + 1 day
notices_required = beneficiary_count
dedicated_bank_account_required = true  (always required for Crummey formalities)
```

The Crummey process: contributions go into ILIT bank account, then Crummey withdrawal notices sent to beneficiaries within 7 days, then beneficiaries have 30-day withdrawal window, then after window closes trustee pays premium.

### Estate result

```
death_benefit = from life-insurance API
estate_inclusion_risk = same enum as recommendation.risk_flag (mirrors the risk assessment)
projected_outside_estate_if_implemented = death_benefit  (policy outside estate when ILIT owns it)
tax_liquidity_support = death_benefit * estate_tax_rate
```

### Source resolution

- `controlling_beneficiary_source`: `SIGNED_PROFILE`
- `controlling_policy_source`: `SIGNED_PROFILE` (profile governs policy interpretation)

---

## trust_comparison

Used for: GRAT versus CRAT numerical comparison and recommendation.

### Data sources

| Data | Source |
|---|---|
| estate_value, liquid_assets, filing_status | SIGNED_PROFILE |
| estate_tax_exemption, estate_tax_rate, charitable_deduction_rate | /api/policies/tax |
| asset_value, expected_growth_rate, grat_term_years, grat_annuity_rate, crat_term_years, crat_payout_rate | /api/trust-candidates |
| family_transfer_priority, philanthropic_intent | SIGNED_PROFILE |

### Estate context

```
planning_year = 2026 (from client record)
exemption_used = estate_tax_exemption[planning_year] * (2 if MFJ else 1)
taxable_estate = max(0, estate_value - exemption_used)
estate_tax_exposure = taxable_estate * estate_tax_rate
liquid_assets_available = liquid_assets (from profile)
liquidity_gap_before_planning = max(0, estate_tax_exposure - liquid_assets_available)
```

### GRAT

```
term_years = grat_term_years (from trust candidate)
projected_remainder_to_heirs = asset_value * (1 + expected_growth_rate)^term_years
                               - term_years * asset_value * grat_annuity_rate
estimated_estate_tax_reduction = projected_remainder_to_heirs * estate_tax_rate
mortality_inclusion_risk = "TERM_SURVIVAL_REQUIRED"
```

The GRAT remainder is what passes to heirs after the grantor receives annuity payments for the term. The annuity is a fixed dollar amount each year (`asset_value * grat_annuity_rate`). The remainder grows outside the estate, reducing future estate tax. The grantor must survive the term for the remainder to pass estate-tax-free.

### CRAT

```
term_years = crat_term_years (from trust candidate, typically 20)
projected_charitable_remainder = asset_value * (1 + expected_growth_rate)^term_years
                                 - term_years * asset_value * crat_payout_rate
estimated_income_tax_deduction = projected_charitable_remainder * charitable_deduction_rate
family_transfer_fit = "LOW" | "MODERATE" | "HIGH"
```

The CRAT remainder goes to charity. The payout rate is typically 0.055. The income tax deduction is based on the charitable deduction rate (0.35).

**family_transfer_fit assessment:**
- `LOW` when family_transfer_priority is high and philanthropic_intent is at most moderate (CRAT gives nothing to family)
- `MODERATE` when philanthropic and family goals are balanced
- `HIGH` when philanthropic_intent is high and family_transfer_priority is moderate (CRAT aligns with charitable goals)

### Recommendation

**preferred_strategy:**
- `GRAT` when family_transfer_priority is `"high"` (GRAT transfers appreciating assets to heirs)
- `CRAT` when philanthropic_intent is `"high"` and family_transfer_priority is at most `"moderate"`

**rationale_code:**
- `CHILDREN_TRANSFER_PRIORITY` when family transfer is the primary driver
- `PHILANTHROPIC_PRIORITY` when charitable giving is the primary driver

**alternate_role:**
- `SECONDARY_CHARITABLE_TOOL` when GRAT is preferred (CRAT plays secondary charitable role)
- `SECONDARY_FAMILY_TRANSFER_TOOL` when CRAT is preferred

### Source resolution

- `controlling_goal_source`: `SIGNED_PROFILE` (goals and priorities come from client profile)
- `controlling_asset_source`: `ATTORNEY_MEMO` (attorney is the more specific document for trust asset decisions)

---

## estate_liquidity_action_plan

Used for: Combined estate liquidity analysis with ILIT and trust transfer recommendations.

### Data sources

| Data | Source |
|---|---|
| estate_value, liquid_assets, filing_status, beneficiary_count | SIGNED_PROFILE |
| estate_tax_exemption, estate_tax_rate | /api/policies/tax |
| annual_gift_exclusion | /api/policies/tax |
| death_benefit, annual_premium, is_existing_policy_transfer | /api/life-insurance |
| asset_value, expected_growth_rate, grat_term_years, grat_annuity_rate, crat_term_years, crat_payout_rate | /api/trust-candidates |

### Estate context

Same computation as trust_comparison (see above). Include `planning_year`, `exemption_used`, `liquid_assets_available`.

### ILIT

```
annual_exclusion_capacity = annual_gift_exclusion[planning_year] * beneficiary_count
premium_gap = max(0, annual_premium - annual_exclusion_capacity)
estate_inclusion_risk = "LOW_IF_FORMALITIES_MET" (new policy) or risk flag if existing policy transfer
projected_outside_estate_if_implemented = death_benefit
```

### Trust transfer

Same GRAT and CRAT computations as trust_comparison. Include both GRAT remainder (for the preferred strategy) and CRAT remainder (for the charitable alternative).

```
preferred_strategy = "GRAT" | "CRAT"  (same logic as trust_comparison)
projected_remainder_to_heirs = GRAT remainder
estimated_estate_tax_reduction = GRAT remainder * estate_tax_rate
projected_charitable_remainder = CRAT remainder
```

### Recommendation

**primary_action:**
- `COMBINE_ILIT_AND_GRAT` -- ILIT covers liquidity gap, GRAT transfers appreciating assets
- `CRAT_WITH_LIQUIDITY_REVIEW` -- philanthropic priority with liquidity review
- `ILIT_WITH_EXEMPTION_REVIEW` -- ILIT with lifetime exemption allocation review

**sequencing:**
- `ILIT_FIRST_THEN_GRAT` -- set up ILIT first to secure estate liquidity, then implement GRAT
- `TRUST_DECISION_FIRST` -- decide trust strategy before ILIT
- `ILIT_FIRST_THEN_ATTORNEY_REVIEW` -- ILIT first, then attorney review of full plan

**risk_flag:** Same enums as ILIT risk flags. `LOW_IF_FORMALITIES_MET` when policies are new and formalities are followed.

### Action set

The `action_set` is an alphabetically sorted array of action enums. Choose actions based on the recommendation:

| Recommendation | Typical actions |
|---|---|
| COMBINE_ILIT_AND_GRAT | ATTORNEY_DRAFT_REVIEW, GRAT_FOR_APPRECIATING_SHARES, ILIT_CRUMMEY_NOTICE_CYCLE |
| CRAT_WITH_LIQUIDITY_REVIEW | ATTORNEY_DRAFT_REVIEW, CRAT_FOR_CHARITABLE_REMAINDER, LIFETIME_EXEMPTION_ALLOCATION |
| ILIT_WITH_EXEMPTION_REVIEW | ATTORNEY_DRAFT_REVIEW, ILIT_CRUMMEY_NOTICE_CYCLE, LIFETIME_EXEMPTION_ALLOCATION |

Available action enum values (pick the subset that matches the recommendation):
- `ATTORNEY_DRAFT_REVIEW`
- `CRAT_FOR_CHARITABLE_REMAINDER`
- `GRAT_FOR_APPRECIATING_SHARES`
- `ILIT_CRUMMEY_NOTICE_CYCLE`
- `LIFETIME_EXEMPTION_ALLOCATION`

Always sort the chosen actions alphabetically.

### Source resolution

- `controlling_goal_source`: `SIGNED_PROFILE`
- `controlling_policy_source`: `SIGNED_PROFILE`

---

## Source Resolution Reference

This table summarizes which source type controls each data category, based on the training patterns:

| Data category | Controlling source | Rationale |
|---|---|---|
| Client profile (age, income, beneficiaries, goals, estate value, liquid assets) | SIGNED_PROFILE | Most recent, formally signed by client |
| Retirement account balances and parameters | CUSTODIAN_EXPORT | Trade-date-accurate, only source for accounts |
| Life insurance policy facts | /api/life-insurance (SIGNED_PROFILE for interpretation) | API provides factual policy records |
| Trust asset decisions | ATTORNEY_MEMO | Attorney is the specific planning source for trust assets |
| Tax and RMD constants | /api/policies/tax, /api/rmd-factors | Shared policy environment |

When sources conflict, prefer the more recent and more authoritative document. Use `effective_date` to compare recency when source type is the same.
