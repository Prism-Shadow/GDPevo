# Formulas (verified to the cent against gold answers)

All constants (`annual_gift_exclusion`, `estate_tax_exemption`, `estate_tax_rate`,
`conversion_bracket_targets`, `max_crat_term_years`, `charitable_deduction_rate`) come from
`GET /api/policies/tax`, keyed by `planning_year` (string keys "2025"/"2026"). RMD divisors come from
`GET /api/rmd-factors`, keyed by age (string). Read constants from the API every run — do not hardcode.

Round every USD output to 2 decimals at the end (Python `round(x, 2)`). Keep full precision during
intermediate math.

## Table of contents
1. Shared estate math
2. Roth conversion / RMD (`roth_conversion_rmd`)
3. ILIT / Crummey (`ilit_crummey_implementation`)
4. Trust comparison GRAT vs CRAT (`trust_comparison`)
5. Estate-liquidity action plan (`estate_liquidity_action_plan`)

---

## 1. Shared estate math

Inputs from the controlling household facts: `estate_value`, `liquid_assets`, `marital_status`,
`planning_year`.

```
exemption_base   = estate_tax_exemption[str(planning_year)]          # from /api/policies/tax
exemption_used   = exemption_base * (2 if marital_status == "married" else 1)   # portability for married
taxable_estate   = max(0, estate_value - exemption_used)
estate_tax_exposure          = taxable_estate * estate_tax_rate       # estate_tax_rate from policy (0.4)
liquidity_gap_before_planning = max(0, estate_tax_exposure - liquid_assets)
```

Notes:
- The doubled exemption for married clients is essential. Single/HOH filers use `1 ×`.
- `estate_context` in some templates also wants `planning_year`, `exemption_used`,
  `liquid_assets_available` (= `liquid_assets`). Include whatever the template's `fields` list names.
- `liquidity_gap_before_planning` is floored at 0 (no negative gap).

---

## 2. Roth conversion / RMD (`roth_conversion_rmd`)

Profile facts (SIGNED_PROFILE): `age`, `planning_year`, `marginal_tax_rate`, `filing_status`,
`annual_non_ira_income`. Account facts (CUSTODIAN_EXPORT, `/api/retirement-accounts`):
`traditional_balance`, `roth_balance`, `expected_return`, `rmd_start_age`,
`recommended_conversion_years`. Horizon year from the request memo.

### Conversion plan

```
first_conversion_year   = planning_year
conversion_years        = recommended_conversion_years
bracket_headroom        = conversion_bracket_targets[filing_status] - annual_non_ira_income
annual_conversion_amount = min(traditional_balance / conversion_years, bracket_headroom)   # bracket-capped
total_converted          = annual_conversion_amount * conversion_years
total_conversion_tax     = total_converted * marginal_tax_rate
conversion_years_positive = number of simulated years with a positive conversion (= conversion_years
                            when annual_conversion_amount > 0 and the traditional balance is not exhausted)
```

`conversion_bracket_targets` is `{MFJ, SINGLE, HOH}` from policy. The conversion is **bracket-capped**:
fill the bracket headroom, but never exceed an even split of the balance over the term.

> `conversion_years_positive` is NOT "years before RMD onset". Conversions keep running through the
> whole window even after RMDs begin, so it equals `conversion_years` in the normal case.

### RMD projection — year-by-year simulation (order of operations matters)

```
first_rmd_year = planning_year + max(0, rmd_start_age - age)
```

Simulate two scenarios from `planning_year` through `horizon_year` inclusive:
- **baseline**: no conversions.
- **conversion**: the bracket-capped conversions above.

For each year `y` (age `a = age + (y - planning_year)`), in this exact order:

1. **Convert** (conversion scenario only), if `(y - planning_year) < conversion_years`:
   `c = min(annual_conversion_amount, traditional)`; `traditional -= c`; `roth += c`. Count the year as
   a positive-conversion year if `c > 0`.
2. **RMD**, if `a >= rmd_start_age` and `a` is in the RMD factor table:
   `rmd = traditional / rmd_factor[a]`; `traditional -= rmd`;
   add `rmd * marginal_tax_rate` to the scenario's cumulative RMD tax.
3. **Grow** both balances: `traditional *= (1 + expected_return)`; `roth *= (1 + expected_return)`.

Outputs:
```
baseline_rmd_tax_through_horizon   = cumulative RMD tax, baseline scenario
conversion_rmd_tax_through_horizon = cumulative RMD tax, conversion scenario
rmd_tax_savings_through_horizon    = baseline - conversion
```

### Legacy projection (conversion scenario, at horizon)

```
projected_roth_balance_horizon        = roth balance at end of horizon year (conversion scenario)
projected_traditional_balance_horizon = traditional balance at end of horizon year (conversion scenario)
```

`heir_tax_profile` from the Roth share `r = roth / (roth + traditional)` at horizon:
`r >= 0.70 → MOSTLY_TAX_FREE`; `r <= 0.30 → MOSTLY_TAXABLE`; else `MIXED_TAXABLE_AND_TAX_FREE`.
(Both verified train cases — shares ~0.61 and ~0.46 — land in `MIXED`.)

---

## 3. ILIT / Crummey (`ilit_crummey_implementation`)

Beneficiary facts: `beneficiary_count` (SIGNED_PROFILE). Policy facts (`/api/life-insurance`):
`death_benefit`, `annual_premium`, `planned_contribution_date`, `is_existing_policy_transfer`.
Household: `estate_value`, `liquid_assets`, `marital_status`.

### Gift plan
```
planning_year                  = planning_year
annual_exclusion_per_beneficiary = annual_gift_exclusion[str(planning_year)]   # 20000 in 2026
beneficiary_count              = beneficiary_count
annual_exclusion_capacity      = annual_exclusion_per_beneficiary * beneficiary_count
annual_premium                 = annual_premium
premium_gap                    = max(0, annual_premium - annual_exclusion_capacity)   # floored at 0
```

### Administration (Crummey date arithmetic)
```
contribution_date             = planned_contribution_date                      # from policy record
notice_due_date               = contribution_date + 7 days
withdrawal_window_end         = notice_due_date + 30 days   (== contribution_date + 37 days)
earliest_premium_payment_date = withdrawal_window_end + 1 day
notices_required              = beneficiary_count
dedicated_bank_account_required = true                                          # ILIT best practice
```
All dates ISO `YYYY-MM-DD`. (Verified: contribution 2026-03-10 → notice 2026-03-17 → window end
2026-04-16 → earliest premium 2026-04-17.)

### Estate result
```
death_benefit                            = death_benefit
projected_outside_estate_if_implemented  = death_benefit            # full DB outside the estate via ILIT
tax_liquidity_support                    = liquid_assets            # household liquid assets, NOT min(DB, exposure)
estate_inclusion_risk                    = same enum as recommendation.risk_flag (see decision_rules.md)
```

---

## 4. Trust comparison GRAT vs CRAT (`trust_comparison`)

Trust params (`/api/trust-candidates`): `asset_value` (A), `expected_growth_rate` (g),
`grat_term_years`, `grat_annuity_rate`, `crat_term_years`, `crat_payout_rate`. Goal facts
(SIGNED_PROFILE): `family_transfer_priority`, `philanthropic_intent`.

### Remainder formula — payments are NOT reinvested
```
FV_assets(n)        = A * (1 + g)**n
annuity_payment     = A * annuity_rate          # GRAT: grat_annuity_rate; CRAT: crat_payout_rate
remainder(n, rate)  = FV_assets(n) - annuity_payment * n     # subtract the PLAIN SUM of payments
```

```
grat.term_years                = grat_term_years
grat.projected_remainder_to_heirs   = remainder(grat_term_years, grat_annuity_rate)
grat.estimated_estate_tax_reduction = grat.projected_remainder_to_heirs * estate_tax_rate   # * 0.4
grat.mortality_inclusion_risk  = "TERM_SURVIVAL_REQUIRED"

crat.term_years                = min(crat_term_years, max_crat_term_years)        # cap at policy max (20)
crat.projected_charitable_remainder  = remainder(crat.term_years, crat_payout_rate)
crat.estimated_income_tax_deduction  = crat.projected_charitable_remainder * charitable_deduction_rate  # * 0.35
crat.family_transfer_fit       = see decision_rules.md (LOW when GRAT preferred for family transfer)
```

> The deduction is `charitable_remainder * charitable_deduction_rate`, **not** `asset_value * rate`.
> The remainder formula does NOT reinvest annuity payments. Both were verified to the cent on train_003
> (GRAT 10,154,624.61; CRAT 28,487,657.15; deduction 9,970,680.00) and train_004.

Also emit `estate_context` (shared estate math, section 1) when the template requires it.

---

## 5. Estate-liquidity action plan (`estate_liquidity_action_plan`)

Combines the estate math (section 1), one ILIT sub-block, and one trust sub-block.

- `estate_context`: section 1 (remember doubled exemption for married).
- `ilit`: `annual_exclusion_capacity`, `premium_gap` (floored at 0), `estate_inclusion_risk` (enum),
  `projected_outside_estate_if_implemented = death_benefit`.
- `trust_transfer`: pick the preferred strategy (decision rules), then report:
  `projected_remainder_to_heirs` (GRAT remainder), `estimated_estate_tax_reduction`
  (= GRAT remainder × estate_tax_rate), `projected_charitable_remainder` (CRAT remainder). Compute both
  trusts with the section-4 formula even though only one is "preferred".
- `action_set`: alphabetically-sorted list of enums — see `decision_rules.md`.
