# Advisory Benchmark — Formulas, Field Definitions, and Decision Rules

Every formula below was verified to reproduce gold answers to the cent. Treat these
as the controlling specification. Section numbers are referenced from SKILL.md.

## Table of contents
1. API endpoints and what to pull
2. Source precedence (which document controls)
3. Roth conversion / RMD engine (`roth_conversion_rmd`)
4. ILIT / Crummey (`ilit_crummey_implementation`)
5. GRAT vs CRAT (`trust_comparison`)
6. Integrated estate-liquidity plan (`estate_liquidity_action_plan`)
7. Rounding, dates, output hygiene

---

## 1. API endpoints and what to pull

Base `http://127.0.0.1:8066`, GET only.

- `/api/clients/{id}` — header: age, marital_status, filing_status, planning_year, estate_value, liquid_assets.
- `/api/source-documents?client_id=` — list of CRM_NOTE / ATTORNEY_MEMO / SIGNED_PROFILE, each with `facts` that may conflict.
- `/api/retirement-accounts?client_id=` — IRA export (`source_type: CUSTODIAN_EXPORT`): traditional_balance, roth_balance, expected_return, rmd_start_age, recommended_conversion_years.
- `/api/life-insurance?client_id=` — policy: death_benefit, annual_premium, planned_contribution_date, is_existing_policy_transfer, proposed_owner. (Treat this record as the **CUSTODIAN_EXPORT** policy source.)
- `/api/trust-candidates?client_id=` — asset_value, expected_growth_rate, grat_term_years, grat_annuity_rate, crat_term_years, crat_payout_rate.
- `/api/policies/tax` — annual_gift_exclusion, estate_tax_exemption, estate_tax_rate, conversion_bracket_targets {MFJ, SINGLE, HOH}, max_crat_term_years, charitable_deduction_rate.
- `/api/rmd-factors` — divisor by age (string keys "73".."99").

Always pull constants from `/api/policies/tax` and `/api/rmd-factors` — never use built-in knowledge of IRS numbers. The benchmark uses its own 2026 planning constants.

---

## 2. Source precedence (which document controls)

Three source docs per client, by recency: CRM_NOTE (2025-11-20, oldest, stale import — distrust),
ATTORNEY_MEMO (2026-01-18), SIGNED_PROFILE (2026-02-06, newest + signed).

Resolution rules (verified on all 5 train tasks):

| Fact category | Controlling source | Enum value to report |
|---|---|---|
| Profile / goal / beneficiary facts: non-IRA income, marginal_tax_rate, beneficiary_count, philanthropic_intent, family_transfer_priority, filing_status | **SIGNED_PROFILE** | `SIGNED_PROFILE` |
| IRA account facts: balances, returns, rmd_start_age, recommended_conversion_years | retirement-accounts export | `CUSTODIAN_EXPORT` |
| Life-insurance policy facts: death_benefit, premium, contribution date, transfer flag | life-insurance record | `CUSTODIAN_EXPORT` |
| Estate ASSET facts for a **trust comparison** | attorney memo confirms estate value | `ATTORNEY_MEMO` |

Pitfalls (these were actual blind-solver errors):
- `controlling_policy_source` is **CUSTODIAN_EXPORT**, NOT SIGNED_PROFILE. The policy facts come from the life-insurance export, even though the SIGNED_PROFILE is the newest household doc. Don't let "newest doc wins" override "the policy export is the authoritative policy source."
- SIGNED_PROFILE wins over CRM_NOTE for `beneficiary_count` and intents (CRM is the stale import the memo warns about).

---

## 3. Roth conversion / RMD engine — `roth_conversion_rmd`

### Inputs
- From SIGNED_PROFILE: age, planning_year, filing_status, marginal_tax_rate, annual_non_ira_income.
- From CUSTODIAN_EXPORT (retirement-accounts): traditional_balance, roth_balance, expected_return, rmd_start_age, recommended_conversion_years.
- horizon_year: from the request memo ("Planning horizon year: YYYY").
- Constants: conversion_bracket_targets[filing_status], rmd-factors.

### Derived values
- `birth_year = planning_year - age`
- `first_rmd_year = birth_year + rmd_start_age` (RMDs begin the calendar year the client reaches rmd_start_age)
- `annual_conversion_amount = conversion_bracket_targets[filing_status] - annual_non_ira_income`
- `first_conversion_year = planning_year`
- `conversion_years = recommended_conversion_years`
- `conversion_years_positive = recommended_conversion_years` — conversions run the FULL window; they are **not** truncated when RMDs start.
- `total_converted = annual_conversion_amount * conversion_years`
- `total_conversion_tax = total_converted * marginal_tax_rate`

### Year-by-year simulation (planning_year .. horizon_year INCLUSIVE)
ORDER PER YEAR — verified to the cent on tasks 001 and 005:
1. **CONVERT** (conversion scenario only, while `year < planning_year + conversion_years`): move `min(annual_conversion_amount, traditional)` from traditional to roth.
2. **RMD** (when `current_age >= rmd_start_age`): `rmd = traditional / rmd_factor[current_age]`; subtract from traditional; `rmd_tax += rmd * marginal_tax_rate`.
3. **GROW**: multiply both balances by `(1 + expected_return)`.

Run twice: baseline (no conversions) and conversion scenario.
- `baseline_rmd_tax_through_horizon` = baseline run's rmd_tax.
- `conversion_rmd_tax_through_horizon` = conversion run's rmd_tax.
- `rmd_tax_savings_through_horizon = baseline - conversion`.
- `projected_roth_balance_horizon`, `projected_traditional_balance_horizon` = conversion run's ending balances.

WHY convert-before-RMD matters: when the conversion window overlaps RMD years, converting first shrinks the traditional balance so that year's RMD is computed on the smaller balance. RMD-first vs convert-first changes the answer by hundreds to thousands of dollars (it was a blind error on task 005). Never round mid-loop; round only the final outputs.

### `heir_tax_profile`
`roth_fraction = roth_end / (roth_end + traditional_end)`:
- `>= 0.7` → `MOSTLY_TAX_FREE`
- `<= 0.3` → `MOSTLY_TAXABLE`
- otherwise → `MIXED_TAXABLE_AND_TAX_FREE`

### Recommendation enum
- If conversions yield meaningful positive savings (positive `rmd_tax_savings`, real conversion window): `primary_action = STAGED_ROTH_CONVERSION`, `suitability = SUITABLE`, `risk_flag = TAX_BRACKET_MANAGEMENT`.
- This holds **even when the client is near RMD age**. A memo that frames the case as "near-RMD" is a distractor — base the call on whether the staged conversion actually saves tax, not on proximity to RMDs. (Blind solver wrongly chose DEFER / RMD_NEAR_TERM on a near-RMD case that gold scored as STAGED / SUITABLE.)
- Reserve `DEFER` / `NO_CONVERSION` for cases where conversions produce no/negative benefit or there is a genuine liquidity constraint (`LIQUIDITY_CONSTRAINT`).

---

## 4. ILIT / Crummey — `ilit_crummey_implementation`

### Inputs
- beneficiary_count: SIGNED_PROFILE → `controlling_beneficiary_source = SIGNED_PROFILE`.
- policy facts: life-insurance record → `controlling_policy_source = CUSTODIAN_EXPORT`.
- planning_year, estate_value, liquid_assets: client header. Constants from tax policy.

### gift_plan
- `annual_exclusion_per_beneficiary = annual_gift_exclusion[planning_year]` (e.g. 20000 for 2026).
- `annual_exclusion_capacity = per_beneficiary * beneficiary_count`.
- `annual_premium` = policy premium.
- `premium_gap = max(0, annual_premium - annual_exclusion_capacity)`. **Floored at 0** — when capacity exceeds premium the gap is 0, never negative.

### administration (Crummey dates)
- `notices_required = beneficiary_count`.
- `contribution_date` = policy `planned_contribution_date`.
- `notice_due_date` = **same as contribution_date** (notices issued the day of contribution). Do NOT add a lag.
- `withdrawal_window_end` = contribution_date **+ 30 days**.
- `earliest_premium_payment_date` = withdrawal_window_end **+ 1 day** (= contribution + 31 days).
- `dedicated_bank_account_required` = `true` (standard ILIT formality).

(Blind errors: added a 7-day notice lag and used a longer window. The correct convention is notice_due = contribution day, 30-day window, pay the day after the window closes.)

### estate_result
- `death_benefit` = policy death_benefit.
- `projected_outside_estate_if_implemented` = full death_benefit (ILIT-owned policy sits outside the estate).
- `tax_liquidity_support = min(death_benefit, estate_tax_exposure)` where
  `estate_tax_exposure = (estate_value - SINGLE estate_tax_exemption) * estate_tax_rate`.
  **Use the single (un-doubled) exemption here even for married clients** — verified on the married Keating case where doubling would have driven exposure negative and the gold support to 0, but gold was the positive `min(DB, exposure)`.
  (Blind error: used `liquid_assets` for tax_liquidity_support. It is min(death benefit, estate tax exposure), not liquidity on hand.)

### Risk / recommendation enums
- No existing-policy transfer (`is_existing_policy_transfer == false`) AND `premium_gap == 0`:
  `primary_action = FUND_WITH_CRUMMEY_NOTICES`, `suitability = SUITABLE_WITH_ADMINISTRATION`,
  `risk_flag = LOW_IF_FORMALITIES_MET`. `estate_inclusion_risk` mirrors `risk_flag`.
- If `premium_gap > 0` (exclusion shortfall): risk includes `EXCLUSION_SHORTFALL`; consider `USE_LIFETIME_EXEMPTION_FOR_SHORTFALL`.
- If transferring an existing policy (`is_existing_policy_transfer == true`): 3-year lookback applies → `THREE_YEAR_LOOKBACK` (and `..._AND_EXCLUSION_SHORTFALL` if both).

---

## 5. GRAT vs CRAT — `trust_comparison`

### Source resolution
- `controlling_goal_source = SIGNED_PROFILE` (philanthropic_intent, family_transfer_priority).
- `controlling_asset_source = ATTORNEY_MEMO`.

### estate_context (marital-doubled exemption)
- `exemption_used = estate_tax_exemption * 2 if married else estate_tax_exemption`.
- `taxable_estate = estate_value - exemption_used`.
- `estate_tax_exposure = taxable_estate * estate_tax_rate`.
- `liquidity_gap_before_planning = max(0, estate_tax_exposure - liquid_assets)`.
- The required template fields are `taxable_estate`, `estate_tax_exposure`, `liquidity_gap_before_planning`. Gold also emitted helper fields `planning_year`, `exemption_used`, `liquid_assets_available`; including them is harmless, but the three required fields above must be present and correct.

### GRAT block (term/rates from trust-candidates)
- `projected_remainder_to_heirs = asset_value*(1+growth)^grat_term - asset_value*grat_annuity_rate*grat_term`.
  The asset compounds at growth for the full term; the annuity is subtracted at its **nominal sum** (rate*term), NOT future-valued and NOT compounded.
- `estimated_estate_tax_reduction = projected_remainder_to_heirs * estate_tax_rate`.
- `mortality_inclusion_risk = TERM_SURVIVAL_REQUIRED` (only enum).
- `term_years = grat_term_years`.

### CRAT block
- `projected_charitable_remainder = asset_value*(1+growth)^crat_term - asset_value*crat_payout_rate*crat_term`.
- `estimated_income_tax_deduction = projected_charitable_remainder * charitable_deduction_rate`. **Deduction is on the CRAT remainder, NOT on the raw asset value.** (Blind error: used asset_value*rate.)
- `family_transfer_fit = LOW` (a CRAT directs the remainder to charity, not heirs).
- `term_years = crat_term_years` (capped by `max_crat_term_years`).

### Recommendation enum
Compare `family_transfer_priority` vs `philanthropic_intent` from SIGNED_PROFILE:
- family transfer high / philanthropy low or moderate → `preferred_strategy = GRAT`, `rationale_code = CHILDREN_TRANSFER_PRIORITY`, `alternate_role = SECONDARY_CHARITABLE_TOOL`.
- philanthropy dominant → `preferred_strategy = CRAT`, `rationale_code = PHILANTHROPIC_PRIORITY`, `alternate_role = SECONDARY_FAMILY_TRANSFER_TOOL`.

---

## 6. Integrated estate-liquidity plan — `estate_liquidity_action_plan`

Combines the ILIT and trust pieces. Pull life-insurance + trust-candidates + tax policy.

- `estate_context`: same marital-doubled-exemption math as §5 (`taxable_estate`, `estate_tax_exposure`, `liquidity_gap_before_planning`). Single client → single exemption (verified on the single Chen case: exemption_used = single value, taxable = estate - single).
- `ilit`:
  - `annual_exclusion_capacity = annual_gift_exclusion[year] * beneficiary_count`.
  - `premium_gap = max(0, annual_premium - capacity)`.
  - `estate_inclusion_risk` per §4 rules.
  - `projected_outside_estate_if_implemented = death_benefit`.
- `trust_transfer`:
  - `preferred_strategy` per §5 recommendation logic.
  - `projected_remainder_to_heirs` = GRAT remainder (§5).
  - `estimated_estate_tax_reduction` = GRAT remainder * estate_tax_rate.
  - `projected_charitable_remainder` = CRAT remainder (§5) — reported even when GRAT is preferred.

### `action_set` (sorted alphabetically) — membership rules
Enum: ATTORNEY_DRAFT_REVIEW, CRAT_FOR_CHARITABLE_REMAINDER, GRAT_FOR_APPRECIATING_SHARES, ILIT_CRUMMEY_NOTICE_CYCLE, LIFETIME_EXEMPTION_ALLOCATION.

- `ATTORNEY_DRAFT_REVIEW` — always include (the engagement is attorney coordination).
- `ILIT_CRUMMEY_NOTICE_CYCLE` — include when a life policy is proposed for an ILIT.
- `GRAT_FOR_APPRECIATING_SHARES` — include when `preferred_strategy == GRAT`.
- `CRAT_FOR_CHARITABLE_REMAINDER` — include only when philanthropy is the dominant goal (CRAT preferred / high philanthropy). EXCLUDE when philanthropy is low.
- `LIFETIME_EXEMPTION_ALLOCATION` — include **only when the ILIT premium_gap > 0** (an exclusion shortfall that must be covered with lifetime exemption). DO **NOT** add it merely because there is an estate liquidity gap. (Blind error: added it because of a $4.6M liquidity gap even though premium_gap was 0; gold excluded it.)

Sort the final list alphabetically before emitting.

### Recommendation / sequencing
- Policy + trust both present, GRAT preferred: `primary_action = COMBINE_ILIT_AND_GRAT`, `sequencing = ILIT_FIRST_THEN_GRAT`, `risk_flag = LOW_IF_FORMALITIES_MET` (when no transfer and no shortfall).

---

## 7. Rounding, dates, output hygiene

- All USD amounts: JSON numbers rounded to 2 decimals (`round(x, 2)`). Never strings. Never round mid-calculation.
- Dates: ISO `YYYY-MM-DD`.
- Emit ONLY the JSON object, no prose, no markdown fences.
- `task_id`: echo the task identifier (e.g. `train_00N` / `test_00N`). `client_id` and `analysis_type`: copy exactly as the template specifies.
- Include every required top-level key from the answer_template. Extra helper fields are tolerated but the required fields must be present and correct.
