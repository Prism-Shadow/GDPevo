# Per-family field reference and worked examples

This expands SKILL.md with (a) the API surface, (b) a field-by-field map of where
each output value comes from, and (c) a fully worked numeric example per family so
you can sanity-check your own computation. The examples below are illustrative
derivations from the public sample data — they are **method demonstrations, not
answers to copy**; every real task recomputes from that task's client record.

## API surface

| Endpoint | Use |
| --- | --- |
| `GET /api/clients/{id}` | header: age, marital_status, filing_status, planning_year, estate_value, liquid_assets |
| `GET /api/source-documents?client_id={id}` | CRM_NOTE / ATTORNEY_MEMO / SIGNED_PROFILE facts (may conflict) |
| `GET /api/retirement-accounts?client_id={id}` | traditional_balance, roth_balance, expected_return, rmd_start_age, recommended_conversion_years (CUSTODIAN_EXPORT) |
| `GET /api/life-insurance?client_id={id}` | death_benefit, annual_premium, planned_contribution_date, is_existing_policy_transfer |
| `GET /api/trust-candidates?client_id={id}` | asset_value, expected_growth_rate, grat_term_years, grat_annuity_rate, crat_term_years, crat_payout_rate |
| `GET /api/policies/tax` | annual_gift_exclusion[year], estate_tax_exemption[year], estate_tax_rate, conversion_bracket_targets[filing], max_crat_term_years, charitable_deduction_rate |
| `GET /api/rmd-factors` | divisor by age (string keys; cast to int) |

Note `source-documents` returns the same fact under multiple `source_type`s. SIGNED
profile is most recent + signed + most complete, so it governs profile/goal facts;
attorney memo governs the estate/asset valuation used for trust funding.

## Family 1 — roth_conversion_rmd

Profile from SIGNED, account from CUSTODIAN export, horizon from the memo.

| Output field | Formula / source |
| --- | --- |
| conversion_plan.first_conversion_year | planning_year |
| conversion_plan.conversion_years | recommended_conversion_years |
| conversion_plan.conversion_years_positive | same, but 0 if no bracket headroom |
| conversion_plan.annual_conversion_amount | conversion_bracket_targets[filing] − annual_non_ira_income |
| conversion_plan.total_converted | annual_conversion_amount × conversion_years |
| conversion_plan.total_conversion_tax | total_converted × marginal_tax_rate |
| rmd_projection.horizon_year | from memo |
| rmd_projection.first_rmd_year | (planning_year − age) + rmd_start_age |
| rmd_projection.baseline_rmd_tax_through_horizon | Σ RMD×marginal_rate, NO-conversion sim |
| rmd_projection.conversion_rmd_tax_through_horizon | Σ RMD×marginal_rate, conversion sim |
| rmd_projection.rmd_tax_savings_through_horizon | baseline − conversion |
| legacy_projection.projected_roth_balance_horizon | conversion-sim Roth bucket after horizon year |
| legacy_projection.projected_traditional_balance_horizon | conversion-sim traditional bucket after horizon year |

Per-year loop (planning_year .. horizon_year inclusive), order **convert → RMD → grow**:
```
for year in range(planning_year, horizon_year + 1):
    age_y = age + (year - planning_year)
    if conversion_scenario and first_conv_year <= year < first_conv_year + conv_years:
        c = min(annual_conversion_amount, traditional); traditional -= c; roth += c
    if age_y >= rmd_start_age and age_y in factors:
        r = traditional / factors[age_y]; traditional -= r; rmd_tax += r * marginal_rate
    traditional *= (1 + expected_return); roth *= (1 + expected_return)
```

Worked example (sample household: MFJ, age 66, non-IRA income 185000, marginal 0.32,
traditional 2,800,000, Roth 0, return 0.065, rmd_start 73, conv_years 7, horizon 2046;
MFJ bracket target 394600):
- annual_conversion = 394600 − 185000 = **209600**
- total_converted = 209600 × 7 = **1,467,200**; tax = ×0.32 = **469,504.00**
- first_rmd_year = (2026 − 66) + 73 = **2033**
- baseline RMD tax = **1,097,182.33**; conversion RMD tax = **617,448.59**; savings = **479,733.74**
- Roth horizon = **4,594,320.16**; traditional horizon = **2,895,040.03**; profile MIXED.

A second sample (single, age 72 — already one year from RMDs, small Roth already,
horizon 2042): conversions (2026–2029) and RMDs (from 2027) overlap; the loop handles
it with no special-casing. Even when the owner is at RMD age the train recommendation
stayed STAGED_ROTH_CONVERSION / SUITABLE because conversions still produced positive
savings — `risk_flag` flips to `RMD_NEAR_TERM` only if `age >= rmd_start_age` in the
planning year.

## Family 2 — ilit_crummey_implementation

| Output field | Formula / source |
| --- | --- |
| gift_plan.planning_year | planning_year |
| gift_plan.annual_exclusion_per_beneficiary | annual_gift_exclusion[planning_year] |
| gift_plan.beneficiary_count | SIGNED beneficiary_count (NOT CRM) |
| gift_plan.annual_exclusion_capacity | exclusion × beneficiary_count |
| gift_plan.annual_premium | policy annual_premium |
| gift_plan.premium_gap | max(0, premium − capacity) |
| administration.notices_required | beneficiary_count |
| administration.contribution_date | policy planned_contribution_date |
| administration.notice_due_date | contribution + 7 days |
| administration.withdrawal_window_end | notice_due + 30 days |
| administration.earliest_premium_payment_date | withdrawal_window_end + 1 day |
| administration.dedicated_bank_account_required | true |
| estate_result.death_benefit | policy death_benefit |
| estate_result.estate_inclusion_risk | = risk_flag |
| estate_result.projected_outside_estate_if_implemented | death_benefit (new policy) / 0 (existing transfer) |
| estate_result.tax_liquidity_support | death_benefit × estate_tax_rate (0.4) |

Worked example (4 beneficiaries from signed profile, 2026 exclusion 20000, premium
78000, death benefit 4,500,000, contribution 2026-03-10, new policy):
- per-beneficiary 20000; capacity 80000; premium_gap = max(0, 78000−80000) = **0**
- notices 4; notice_due **2026-03-17**; window_end **2026-04-16**; earliest_premium **2026-04-17**
- outside-estate **4,500,000**; tax_liquidity_support = 4,500,000 × 0.4 = **1,800,000**
- risk **LOW_IF_FORMALITIES_MET** → action FUND_WITH_CRUMMEY_NOTICES / SUITABLE_WITH_ADMINISTRATION

Branch reminders for harder cases (these appear in the broader client set):
- existing-policy transfer → `THREE_YEAR_LOOKBACK`, outside-estate 0
- premium > capacity → `EXCLUSION_SHORTFALL`, premium_gap > 0
- both → `THREE_YEAR_LOOKBACK_AND_EXCLUSION_SHORTFALL` / NOT_SUITABLE / DISCLOSE_LOOKBACK_AND_USE_EXEMPTION

## Family 3 — trust_comparison

Remainder shape is identical for GRAT and CRAT: FV of asset minus the **simple sum**
(not compounded) of the fixed annual payments.

| Output field | Formula / source |
| --- | --- |
| estate_context.* | §7 of SKILL.md (asset/estate value from ATTORNEY memo) |
| grat.term_years | grat_term_years |
| grat.projected_remainder_to_heirs | asset×(1+growth)^gterm − asset×grat_annuity_rate×gterm |
| grat.estimated_estate_tax_reduction | GRAT remainder × estate_tax_rate (0.4) |
| grat.mortality_inclusion_risk | TERM_SURVIVAL_REQUIRED (constant) |
| crat.term_years | min(crat_term_years, max_crat_term_years) |
| crat.projected_charitable_remainder | asset×(1+growth)^cterm − asset×crat_payout_rate×cterm |
| crat.estimated_income_tax_deduction | CRAT remainder × charitable_deduction_rate (0.35) |
| crat.family_transfer_fit | LOW if GRAT preferred, MODERATE if CRAT preferred |

Worked example (asset 8,000,000, growth 0.08, GRAT 5yr @ 0.04, CRAT 20yr @ 0.055):
- GRAT remainder = 8,000,000×1.08^5 − 8,000,000×0.04×5 = 11,754,624.61 − 1,600,000 = **10,154,624.61**
- GRAT tax reduction = ×0.4 = **4,061,849.85**
- CRAT remainder = 8,000,000×1.08^20 − 8,000,000×0.055×20 = 37,287,657.15 − 8,800,000 = **28,487,657.15**
- CRAT deduction = ×0.35 = **9,970,680.00**
- goals: family_transfer high ≥ philanthropic moderate → **GRAT** / CHILDREN_TRANSFER_PRIORITY / SECONDARY_CHARITABLE_TOOL / fit LOW.

## Family 4 — estate_liquidity_action_plan

Reuses estate context (§7), ILIT core (Family 2), and trust numbers (Family 3).

| Output field | Source |
| --- | --- |
| recommendation.primary_action | COMBINE_ILIT_AND_GRAT (GRAT pref) / CRAT_WITH_LIQUIDITY_REVIEW (CRAT pref) |
| recommendation.sequencing | ILIT_FIRST_THEN_GRAT / TRUST_DECISION_FIRST |
| recommendation.risk_flag | ILIT risk flag |
| ilit.annual_exclusion_capacity | exclusion × beneficiary_count |
| ilit.premium_gap | max(0, premium − capacity) |
| ilit.estate_inclusion_risk | ILIT risk flag |
| ilit.projected_outside_estate_if_implemented | death_benefit (new) / 0 (existing transfer) |
| trust_transfer.preferred_strategy | GRAT/CRAT goal rule |
| trust_transfer.projected_remainder_to_heirs | GRAT remainder |
| trust_transfer.estimated_estate_tax_reduction | GRAT remainder × 0.4 |
| trust_transfer.projected_charitable_remainder | CRAT remainder |
| action_set | alphabetic subset; see SKILL.md §6 |

Worked example (single, estate 31,200,000, liquid 2,400,000; 3 beneficiaries; premium
56000; death benefit 5,200,000; trust asset 9,500,000, growth 0.09, GRAT 6yr @ 0.045):
- exemption_used (single, 2026) = 13,610,000; taxable = **17,590,000**; exposure = **7,036,000**;
  liquidity_gap = 7,036,000 − 2,400,000 = **4,636,000**
- ILIT capacity = 20000×3 = **60,000**; premium_gap **0**; outside-estate **5,200,000**; risk LOW
- GRAT remainder = 9,500,000×1.09^6 − 9,500,000×0.045×6 = **13,367,451.05**; ×0.4 = **5,346,980.42**
- CRAT remainder (20yr @ 0.055) = 9,500,000×1.09^20 − 9,500,000×0.055×20 = **42,791,902.29**
- GRAT preferred → action_set = [ATTORNEY_DRAFT_REVIEW, GRAT_FOR_APPRECIATING_SHARES, ILIT_CRUMMEY_NOTICE_CYCLE]
  (LIFETIME_EXEMPTION_ALLOCATION would be added only if premium_gap > 0).

## Self-check before emitting

Run the bundled solver and diff against the task's gold when available
(`scripts/advisory_lib.py` reproduces all five train golds exactly). Confirm: numbers
are JSON numbers to cents, dates ISO, `action_set` sorted, `task_id` correct, output is
the bare JSON object.
