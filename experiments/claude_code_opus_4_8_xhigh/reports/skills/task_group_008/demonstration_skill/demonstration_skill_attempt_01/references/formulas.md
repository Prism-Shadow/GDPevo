# Formula cards (verified to the cent against gold answers)

All constants come from `GET /api/policies/tax` and `GET /api/rmd-factors`. Symbols below: read tax
constants per planning year (typically 2026). `estate_tax_rate` = 0.4 and `charitable_deduction_rate`
= 0.35 in the current policy object, but always read them live.

## Source resolution (by fact type)
- goals / profile / tax facts / beneficiary_count / liquid_assets → **SIGNED_PROFILE**
- estate_value / asset valuations → **ATTORNEY_MEMO**
- retirement accounts → **CUSTODIAN_EXPORT**
- CRM_NOTE → stale, never controls

## Roth conversion + RMD
```
annual_conversion_amount = conversion_bracket_targets[filing_status] - annual_non_ira_income
conversion_years         = recommended_conversion_years          # from IRA export
first_conversion_year    = planning_year
total_converted          = annual_conversion_amount * conversion_years
total_conversion_tax     = total_converted * marginal_tax_rate
first_rmd_year           = planning_year + (rmd_start_age - current_age)

# Per year, year = planning_year .. horizon, age = start_age + (year - planning_year):
#   1) if converting this year: amt = min(annual_conversion_amount, traditional)
#                               traditional -= amt ; roth += amt
#   2) if age >= rmd_start_age and age in rmd_factor:
#          rmd = traditional / rmd_factor[age]
#          traditional -= rmd ; rmd_tax += rmd * marginal_tax_rate
#   3) traditional *= (1+expected_return) ; roth *= (1+expected_return)   # growth LAST
baseline_rmd_tax_through_horizon   = rmd_tax with NO conversions
conversion_rmd_tax_through_horizon = rmd_tax WITH conversions
rmd_tax_savings_through_horizon    = baseline - conversion
projected_*_balance_horizon        = ending balances from the CONVERSION run
heir_tax_profile: share = roth/(roth+trad); >=0.7 MOSTLY_TAX_FREE, <=0.3 MOSTLY_TAXABLE, else MIXED_TAXABLE_AND_TAX_FREE
```

## ILIT / Crummey
```
annual_exclusion_per_beneficiary = annual_gift_exclusion[planning_year]
annual_exclusion_capacity        = annual_exclusion_per_beneficiary * beneficiary_count
premium_gap                      = max(0, annual_premium - annual_exclusion_capacity)
notices_required                 = beneficiary_count
dedicated_bank_account_required  = true

contribution_date             = policy.planned_contribution_date
notice_due_date               = contribution_date      + 7 days
withdrawal_window_end         = notice_due_date         + 30 days
earliest_premium_payment_date = withdrawal_window_end   + 1 day

death_benefit                          = policy.death_benefit
projected_outside_estate_if_implemented= death_benefit
tax_liquidity_support                  = death_benefit * estate_tax_rate
estate_inclusion_risk                  = recommendation.risk_flag

# risk flag:
#   base LOW_IF_FORMALITIES_MET
#   is_existing_policy_transfer  -> THREE_YEAR_LOOKBACK
#   premium_gap > 0              -> EXCLUSION_SHORTFALL
#   both                         -> THREE_YEAR_LOOKBACK_AND_EXCLUSION_SHORTFALL
```

## Estate context (used by trust_comparison and estate_liquidity_action_plan)
```
exemption_used               = estate_tax_exemption[planning_year] * (2 if married else 1)
taxable_estate               = max(0, estate_value - exemption_used)        # estate_value from ATTORNEY_MEMO
estate_tax_exposure          = taxable_estate * estate_tax_rate
liquid_assets_available      = signed_profile.liquid_assets
liquidity_gap_before_planning= max(0, estate_tax_exposure - liquid_assets_available)
```

## GRAT / CRAT (nominal annuity subtracted — do NOT future-value the stream)
```
A = trust.asset_value ; g = trust.expected_growth_rate

GRAT_remainder         = A*(1+g)**grat_term_years - A*grat_annuity_rate*grat_term_years
GRAT_est_tax_reduction = GRAT_remainder * estate_tax_rate

CRAT_remainder         = A*(1+g)**crat_term_years - A*crat_payout_rate*crat_term_years
CRAT_income_deduction  = CRAT_remainder * charitable_deduction_rate
```

## Worked numeric check (recompute these to validate your script)
Using live API data (planning_year 2026, estate_tax_rate 0.4, charitable_deduction_rate 0.35):

- Roth, MFJ client, non-IRA income 185000, MTR 0.32, trad 2,800,000, return 0.065, conv_years 7,
  rmd_start 73, current age 66, horizon 2046, MFJ bracket target 394600:
  - annual_conversion_amount = 394600 - 185000 = **209600.0**
  - total_converted = **1467200.0**; total_conversion_tax = **469504.0**; first_rmd_year = **2033**
  - baseline_rmd_tax = **1097182.33**; conversion_rmd_tax = **617448.59**; savings = **479733.74**
  - projected_roth = **4594320.16**; projected_traditional = **2895040.03** (MIXED)

- ILIT, gift excl 20000, beneficiary_count 4, premium 78000, contribution 2026-03-10, death_benefit 4,500,000:
  - capacity = **80000.0**; premium_gap = **0.0**; notice_due **2026-03-17**;
    withdrawal_window_end **2026-04-16**; earliest_premium **2026-04-17**
  - tax_liquidity_support = 4,500,000 * 0.4 = **1800000.0**; risk LOW_IF_FORMALITIES_MET

- GRAT/CRAT, A=8,000,000, g=0.08, grat_term 5, grat_annuity_rate 0.04, crat_term 20, crat_payout 0.055:
  - GRAT_remainder = 8e6*1.08**5 - 8e6*0.04*5 = **10154624.61**; est_tax_reduction = **4061849.85**
  - CRAT_remainder = 8e6*1.08**20 - 8e6*0.055*20 = **28487657.15**; income_deduction = **9970680.0**

- Estate context, married, estate 38,800,000, exemption 13,610,000, liquid 6,200,000:
  - exemption_used = **27220000.0**; taxable = **11580000.0**; exposure = **4632000.0**;
    liquidity_gap = max(0, 4632000 - 6200000) = **0.0**

- Estate context, single, estate 31,200,000, liquid 2,400,000:
  - exemption_used = **13610000.0**; taxable = **17590000.0**; exposure = **7036000.0**;
    liquidity_gap = **4636000.0**

If your code reproduces every bolded number, the formulas and ordering are wired correctly.
