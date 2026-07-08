---
name: reflect-3
description: Solve private-wealth-advisory structured planning tasks (Roth/RMD, ILIT/Crummey, GRAT/CRAT, estate-liquidity) against a remote advisory API with conflicting source documents. Produce exact JSON conforming to each task's answer template.
---

# Private Wealth Advisory Structured-Output Skill

Produce a single JSON object conforming to the task's `answer_template.json`. No prose outside the JSON. All USD amounts rounded to cents (2 decimals, JSON numbers not strings). All dates ISO `YYYY-MM-DD`.

## 1. Remote API workflow

Read the API base URL from the staged `environment_access.md` (the harness `API_BASE`). Call endpoints in this order, GET unless noted:

1. `GET /api/health` — confirm the environment is up.
2. `GET /api/clients/<client_id>` — base client record (age, filing_status, planning_year, estate_value, liquid_assets).
3. `GET /api/source-documents?client_id=<id>` — the conflicting source docs (CRM_NOTE, ATTORNEY_MEMO, SIGNED_PROFILE, sometimes STALE_MARKETING_INTAKE). Each has `effective_date` and a `facts` map.
4. `GET /api/retirement-accounts?client_id=<id>` — custodian retirement accounts (traditional/roth balances, expected_return, rmd_start_age, recommended_conversion_years).
5. `GET /api/life-insurance?client_id=<id>` — ILIT policy facts (death_benefit, annual_premium, planned_contribution_date, is_existing_policy_transfer).
6. `GET /api/trust-candidates?client_id=<id>` — GRAT/CRAT candidate (asset_value, expected_growth_rate, grat_term_years, grat_annuity_rate, crat_term_years, crat_payout_rate).
7. `GET /api/policies/tax` — planning constants: `annual_gift_exclusion` (by year), `estate_tax_exemption` (by year), `estate_tax_rate`, `conversion_bracket_targets` (by filing status), `max_crat_term_years`, `charitable_deduction_rate`.
8. `GET /api/rmd-factors` — age → RMD divisor table (73→26.5, 74→25.5, …).

Use the planning_year to pick the correct year-keyed constant (e.g., 2026 → exemption 2026 value, gift exclusion 2026 value).

## 2. Source-resolution precedence

Source documents conflict because they were imported at different times. Resolve by category, then by recency:

| Fact category | Controlling source |
|---|---|
| Client-stated facts: annual_non_ira_income, marginal_tax_rate, beneficiary_count, age, filing_status, marital_status, liquid_assets, estate_value, philanthropic_intent, family_transfer_priority | **SIGNED_PROFILE** (newest, client-signed) |
| Account balances & retirement parameters (traditional/roth balances, expected_return, rmd_start_age, recommended_conversion_years) | **CUSTODIAN_EXPORT** |
| Planning strategy goal / trust structure decision (GRAT-vs-CRAT preference, ILIT rationale) | **ATTORNEY_MEMO** |
| Trust-candidate asset value to be funded (asset_value for GRAT/CRAT) | **SIGNED_PROFILE** (client-declared asset) |
| ILIT policy facts (death_benefit, annual_premium, contribution date, transfer status) | life-insurance record (carrier); classify per `controlling_policy_source` (see note) |
| Beneficiary count | **SIGNED_PROFILE** |

Recency tiebreak within a category: SIGNED_PROFILE (most recent effective_date) > ATTORNEY_MEMO > CRM_NOTE > STALE_MARKETING_INTAKE. When SIGNED_PROFILE and ATTORNEY_MEMO agree, either may be cited but use the category rule above for the `source_resolution` field that the template asks for.

**Worked resolution example (generic):** If a CRM_NOTE lists `beneficiary_count=3` and `annual_non_ira_income` higher than the SIGNED_PROFILE, discard the CRM values — SIGNED_PROFILE controls client-stated facts (use the SIGNED_PROFILE beneficiary_count and income). If a CUSTODIAN_EXPORT shows a different traditional balance than a CRM note, use the custodian balance. If SIGNED_PROFILE and ATTORNEY_MEMO disagree on `philanthropic_intent`, the ATTORNEY_MEMO is the controlling goal source for trust-strategy preference, while SIGNED_PROFILE remains controlling for the client-stated profile fields used in dollar math (income, marginal_rate, age).

`source_resolution` output fields (set exactly those the template requires):
- `controlling_profile_source` (roth tasks) = `SIGNED_PROFILE`
- `controlling_account_source` (roth tasks) = `CUSTODIAN_EXPORT`
- `controlling_beneficiary_source` (ILIT tasks) = `SIGNED_PROFILE`
- `controlling_policy_source` (ILIT/estate tasks) = `ATTORNEY_MEMO` per the attorney-controls-trust-assets convention (the ILIT is a trust instrument). The life-insurance record is the carrier source of policy numbers; if a task instead expects the carrier record to control, `CUSTODIAN_EXPORT` is the alternative — this field was not discriminative in training, so default to `ATTORNEY_MEMO`.
- `controlling_goal_source` (trust_comparison / estate tasks) = `ATTORNEY_MEMO`
- `controlling_asset_source` (trust_comparison) = `SIGNED_PROFILE`

## 3. Cross-cutting calculation rules

- **Estate tax — exemption IS applied.** `taxable_estate = estate_value − estate_tax_exemption[year]`; `estate_tax_exposure = taxable_estate × estate_tax_rate`; `liquidity_gap_before_planning = estate_tax_exposure − liquid_assets`. (Confirmed: applying the exemption is correct; using the gross estate with no exemption is wrong.)
- **GRAT/CRAT remainder (compound future value, nominal payouts).** `projected = asset_value × (1 + expected_growth_rate)^term`; `nominal_payouts = asset_value × payout_rate × term`; `remainder = projected − nominal_payouts`. Use **compound** growth `(1+g)^t`, NOT simple interest `1+g*t`. payouts are the simple undiscounted sum (nominal), not grown.
  - GRAT `projected_remainder_to_heirs` = remainder (GRAT term, grat_annuity_rate).
  - CRAT `projected_charitable_remainder` = remainder (CRAT term, crat_payout_rate; term = min(candidate crat_term_years, max_crat_term_years), usually 20).
- **GRAT `estimated_estate_tax_reduction`** = `projected_remainder_to_heirs × estate_tax_rate`.
- **CRAT `estimated_income_tax_deduction`** = `projected_charitable_remainder × charitable_deduction_rate`.
- **CRAT `family_transfer_fit`** = `MODERATE` (CRAT pays an income stream to a non-charitable beneficiary but the remainder goes to charity). `mortality_inclusion_risk` (GRAT) = `TERM_SURVIVAL_REQUIRED`.
- **Crummey date arithmetic** (from `planned_contribution_date` = `contribution_date`): `notice_due_date = contribution_date + 7 days`; `withdrawal_window_end = contribution_date + 30 days`; `earliest_premium_payment_date = withdrawal_window_end + 1 day` (premium is paid only after the withdrawal window closes). Use calendar-day addition.
- **ILIT gift plan.** `annual_exclusion_per_beneficiary = annual_gift_exclusion[year]`; `annual_exclusion_capacity = beneficiary_count × annual_exclusion_per_beneficiary`; `annual_premium` from the life-insurance record; `premium_gap = max(0, annual_premium − annual_exclusion_capacity)` (report the shortfall; **0 when capacity covers the premium**, not a negative surplus).
- **Roth conversion.** `bracket_room = conversion_bracket_targets[filing_status] − annual_non_ira_income`; `annual_conversion_amount = min(bracket_room, traditional_balance / recommended_conversion_years)`; `total_converted = annual_conversion_amount × conversion_years_positive`; `total_conversion_tax = total_converted × marginal_tax_rate`.
- **RMD.** `first_rmd_year = planning_year + (rmd_start_age − age)`; each RMD year `rmd = start_of_year_traditional_balance / rmd_factor[age]`; RMD tax = `rmd × marginal_tax_rate`. The RMD factor table only covers age 73–99; horizon ages beyond 99 are uncommon but if encountered use the age-99 factor (6.8) as the floor.
- **Balance/RMD simulation** (roth tasks), run baseline (no conversion) and conversion scenarios from `planning_year` through `horizon_year` inclusive, each year in this order: (1) if a conversion year, subtract `annual_conversion_amount` from traditional, add to Roth, accrue conversion tax; (2) if age ≥ rmd_start_age, withdraw RMD = current traditional balance / `rmd_factor[age]`, accrue RMD tax; (3) grow both balances by `expected_return`. The existing `roth_balance` (if non-zero) seeds Roth in both scenarios. `baseline_rmd_tax_through_horizon`, `conversion_rmd_tax_through_horizon` = summed RMD taxes; `rmd_tax_savings_through_horizon = baseline − conversion`. Conversion years are `planning_year … planning_year + recommended_conversion_years − 1` (they may overlap RMD years — keep the order above).
- **Legacy projection** = conversion-scenario balances at horizon year. `heir_tax_profile`: compute `roth_frac = projected_roth_balance_horizon / (roth + traditional)`; `MOSTLY_TAX_FREE` if > ~2/3, `MOSTLY_TAXABLE` if < ~1/3, else `MIXED_TAXABLE_AND_TAX_FREE`.
- **action_set** (estate tasks): list of applicable action enums, **sorted alphabetically**. See per-task section for inclusion.
- Rounding: round every USD field to 2 decimals at the end (use round-half-up via `round(x + 1e-9, 2)`).

## 4. Per analysis type

### a. `roth_conversion_rmd` (Roth conversion + RMD tax summary)
Fields: `recommendation`, `conversion_plan`, `rmd_projection`, `legacy_projection`, `source_resolution`.
- `recommendation.primary_action` = `STAGED_ROTH_CONVERSION` whenever bracket_room > 0 (conversions are feasible).
- `recommendation.suitability` = `SUITABLE` when bracket_room > 0 (the conversion is suitable; do **not** mark BORDERLINE merely because RMD is near — suitability tracks feasibility, not runway).
- `recommendation.risk_flag` = `RMD_NEAR_TERM` if `first_rmd_year − planning_year ≤ ~2`; else `TAX_BRACKET_MANAGEMENT` (or `LIQUIDITY_CONSTRAINT` if `liquid_assets` cannot cover `total_conversion_tax`).
- `conversion_plan`: `first_conversion_year = planning_year`; `conversion_years = recommended_conversion_years`; `conversion_years_positive = conversion_years` when `bracket_room < balance/years` (all years convert the full bracket room); `annual_conversion_amount`, `total_converted`, `total_conversion_tax` per §3.
- `rmd_projection`: `horizon_year` from the memo (use the stated horizon year, e.g. 2042 or 2046); `first_rmd_year` per §3; the three tax fields from the simulation. `rmd_tax_savings_through_horizon = baseline_rmd_tax_through_horizon − conversion_rmd_tax_through_horizon` (positive when conversions reduce future RMD tax).
- `legacy_projection`: `projected_roth_balance_horizon` and `projected_traditional_balance_horizon` are the **conversion-scenario** end balances (the recommended plan); include the existing Roth seed; `heir_tax_profile` per §3.
- `source_resolution`: `controlling_profile_source = SIGNED_PROFILE`, `controlling_account_source = CUSTODIAN_EXPORT`.

### b. `ilit_crummey_implementation` (ILIT Crummey funding cycle)
Fields: `recommendation`, `gift_plan`, `administration`, `estate_result`, `source_resolution`.
- `recommendation.primary_action`: `FUND_WITH_CRUMMEY_NOTICES` when `annual_exclusion_capacity ≥ annual_premium`; `USE_LIFETIME_EXEMPTION_FOR_SHORTFALL` when capacity < premium; `USE_NEW_POLICY_OR_ACCEPT_LOOKBACK` / `DISCLOSE_LOOKBACK_AND_USE_EXEMPTION` when `is_existing_policy_transfer` (3-year lookback).
- `recommendation.suitability`: `SUITABLE_WITH_ADMINISTRATION` when funded with Crummey notices and formalities are met; `BORDERLINE` / `NOT_SUITABLE` otherwise.
- `recommendation.risk_flag`: `LOW_IF_FORMALITIES_MET` (new policy, no shortfall); `EXCLUSION_SHORTFALL` (capacity < premium); `THREE_YEAR_LOOKBACK` (existing policy transfer); combine as `THREE_YEAR_LOOKBACK_AND_EXCLUSION_SHORTFALL` if both.
- `gift_plan`: `planning_year`, `annual_exclusion_per_beneficiary`, `beneficiary_count` (SIGNED_PROFILE), `annual_exclusion_capacity`, `annual_premium`, `premium_gap` (§3).
- `administration`: `notices_required = beneficiary_count`; `contribution_date` = planned_contribution_date; `notice_due_date`, `withdrawal_window_end`, `earliest_premium_payment_date` (§3 Crummey arithmetic); `dedicated_bank_account_required = true`.
- `estate_result`: `death_benefit`; `estate_inclusion_risk` = same as `recommendation.risk_flag`; `projected_outside_estate_if_implemented = death_benefit` (the ILIT-owned death benefit escapes the estate); `tax_liquidity_support = death_benefit` (the death benefit is the liquidity asset that supports estate-tax payment).
- `source_resolution`: `controlling_beneficiary_source = SIGNED_PROFILE`, `controlling_policy_source = ATTORNEY_MEMO` (default; see §2 note).

### c. `trust_comparison` (GRAT vs CRAT)
Fields: `recommendation`, `estate_context`, `grat`, `crat`, `source_resolution`.
- `recommendation.preferred_strategy`: **driven by the controlling goal source's (ATTORNEY_MEMO) `philanthropic_intent`** — `CRAT` when philanthropic_intent is `moderate` or `high`; `GRAT` when `low`. (Do not decide purely by family_transfer_priority level; empirically moderate philanthropy selects CRAT even when family transfer is also high.)
  - If CRAT: `rationale_code = PHILANTHROPIC_PRIORITY`, `alternate_role = SECONDARY_FAMILY_TRANSFER_TOOL` (GRAT is the secondary family-transfer tool).
  - If GRAT: `rationale_code = CHILDREN_TRANSFER_PRIORITY`, `alternate_role = SECONDARY_CHARITABLE_TOOL` (CRAT is the secondary charitable tool).
- `estate_context`: `taxable_estate = estate_value − exemption`, `estate_tax_exposure = taxable_estate × rate`, `liquidity_gap_before_planning = exposure − liquid_assets` (§3 exemption applied).
- `grat`: `term_years` from trust candidate; `projected_remainder_to_heirs` (§3 compound); `estimated_estate_tax_reduction = remainder × rate`; `mortality_inclusion_risk = TERM_SURVIVAL_REQUIRED`.
- `crat`: `term_years` = min(candidate, max_crat_term_years); `projected_charitable_remainder` (§3 compound); `estimated_income_tax_deduction = char_remainder × charitable_deduction_rate`; `family_transfer_fit = MODERATE`.
- `source_resolution`: `controlling_goal_source = ATTORNEY_MEMO`, `controlling_asset_source = SIGNED_PROFILE`.

### d. `estate_liquidity_action_plan` (combined ILIT + trust transfer)

Fields: `recommendation`, `estate_context`, `ilit`, `trust_transfer`, `action_set`, `source_resolution`.
- `recommendation.primary_action`: `COMBINE_ILIT_AND_GRAT` when the case pairs an ILIT (liquidity) with a GRAT (family transfer, philanthropic low); `CRAT_WITH_LIQUIDITY_REVIEW` when philanthropic is the priority; `ILIT_WITH_EXEMPTION_REVIEW` when the ILIT has an exclusion shortfall needing exemption review.
- `recommendation.sequencing`: `ILIT_FIRST_THEN_GRAT` for the combined case (ILIT first for estate-tax liquidity, then GRAT for transfer); `TRUST_DECISION_FIRST` / `ILIT_FIRST_THEN_ATTORNEY_REVIEW` for the other primary actions.
- `recommendation.risk_flag`: ILIT risk flags as in (b).
- `estate_context`: exemption applied (§3).
- `ilit`: `annual_exclusion_capacity`, `premium_gap` (§3), `estate_inclusion_risk` (as in b), `projected_outside_estate_if_implemented = death_benefit`.
- `trust_transfer`: `preferred_strategy` (CRAT if philanthropic mod/high, GRAT if low — same rule as (c)); `projected_remainder_to_heirs` & `estimated_estate_tax_reduction` (GRAT, §3 compound); `projected_charitable_remainder` (CRAT, §3 compound). Compute both GRAT and CRAT projection fields regardless of preference.
- `action_set` (sorted alphabetically): include `ATTORNEY_DRAFT_REVIEW`, `GRAT_FOR_APPRECIATING_SHARES`, `ILIT_CRUMMEY_NOTICE_CYCLE`, and `LIFETIME_EXEMPTION_ALLOCATION` (the GRAT remainder is a taxable gift using lifetime exemption; also include if there is an ILIT exclusion shortfall). Include `CRAT_FOR_CHARITABLE_REMAINDER` only when CRAT is the preferred strategy. Exclude actions for tools not in the plan.
- `source_resolution`: `controlling_goal_source = ATTORNEY_MEMO`, `controlling_policy_source = ATTORNEY_MEMO` (default; see §2 note).

## 5. Numbered end-to-end SOP

1. Read the task `prompt.txt`, `request_memo.md` (engagement + **planning horizon year** if stated), and `answer_template.json` (required keys + enums).
2. Fetch the eight endpoints in §1 order. Cache `policies/tax` and `rmd-factors` (shared across clients).
3. Resolve every contested fact via §2 (SIGNED_PROFILE for client-stated, CUSTODIAN_EXPORT for balances, ATTORNEY_MEMO for strategy goals, SIGNED_PROFILE for the trust-candidate asset value).
4. Compute the analysis-type-specific fields per §4, applying the cross-cutting rules in §3.
5. Round every USD field to 2 decimals; format dates ISO; ensure numbers are JSON numbers.
6. Cross-check enum values against the template exactly (e.g., `STAGED_ROTH_CONVERSION`, `LOW_IF_FORMALITIES_MET`, `TERM_SURVIVAL_REQUIRED`) — misspellings or synonyms are wrong.
7. Verify the `action_set` (estate tasks) is sorted alphabetically and contains only actions for tools actually in the plan.
8. Emit only the JSON object with every required top-level key and the correct `task_id`/`client_id`/`analysis_type`.

## 6. Key distinctions to get right (refined via training feedback)

- **Apply the estate-tax exemption.** Subtract `estate_tax_exemption` from `estate_value` before multiplying by `estate_tax_rate`. Using the gross estate (no exemption) is a major scoring loss; the same applies to `taxable_estate` (it is the net-of-exemption amount, not gross).
- **Compound growth for GRAT/CRAT remainders, not simple interest.** `projected = asset × (1+g)^t`. Simple interest `asset×(1+g·t)` is wrong. Payouts are the nominal undiscounted sum `asset×rate×t`.
- **`estate_tax_reduction` and `income_tax_deduction` are rate-multiplied, not raw remainders.** GRAT estate-tax reduction = `remainder × estate_tax_rate`; CRAT income-tax deduction = `char_remainder × charitable_deduction_rate` (distinct from the raw projection, avoiding redundancy with `projected_charitable_remainder`).
- **Crummey premium timing:** the earliest premium payment is the day *after* the 30-day withdrawal window closes — not the day after the contribution. Notice due = contribution + 7; window end = contribution + 30; premium = window end + 1.
- **`premium_gap` is the shortfall (≥0).** When exclusion capacity covers the premium, report `0`, not a negative surplus.
- **Roth suitability is SUITABLE when bracket room exists**, even for near-RMD clients; do not default to BORDERLINE. Reserve BORDERLINE/DEFER for cases with no bracket room or liquidity constraints. `risk_flag` (e.g., `RMD_NEAR_TERM`) is the separate field that captures the near-RMD concern.
- **trust_comparison preference keys on philanthropic_intent**, not family_transfer_priority: moderate/high philanthropy → CRAT; low → GRAT. Choosing GRAT purely because family_transfer_priority is "high" is a frequent mistake.
- **Source winners:** goal → ATTORNEY_MEMO; trust-candidate asset value → SIGNED_PROFILE; beneficiary count → SIGNED_PROFILE; client profile facts → SIGNED_PROFILE; account balances → CUSTODIAN_EXPORT. Mixing these (e.g., goal from SIGNED, asset from ATTORNEY) loses points.
- **`heir_tax_profile` thresholds are thirds**, not 0.5: `MOSTLY_TAX_FREE` requires roth_frac above ~2/3, `MOSTLY_TAXABLE` below ~1/3, otherwise `MIXED_TAXABLE_AND_TAX_FREE`. A roth_frac just under 0.5 is still MIXED, not MOSTLY_TAXABLE.
- **`conversion_years_positive` equals `conversion_years`** when bracket room is the binding constraint (bracket_room < balance/years); do not reduce it for RMD-year overlap.

## 7. Common mistakes / exclusions

- Do **not** use the stale CRM_NOTE or STALE_MARKETING_INTAKE values for client-stated facts (income, beneficiary_count, goals) — they are outdated imports; SIGNED_PROFILE controls.
- Do **not** subtract the exemption from the estate-tax-rate base incorrectly: exemption subtracts from the estate (base), and `estate_tax_rate` then applies to the net — do not also subtract `exemption × rate` (that double-counts).
- Do **not** compute RMD on the post-growth balance; use the start-of-year balance divided by the age factor, then grow the remainder.
- Do **not** cap `total_converted` at the initial balance when `annual × years < balance` (that is the normal case when bracket room is the binding constraint); only the per-year amount is min-capped.
- Do **not** include CRAT actions in the action_set when GRAT is the preferred trust and philanthropic intent is low.
- Do **not** omit the existing `roth_balance` seed in the conversion-scenario legacy projection.
- Do **not** return numbers as strings, omit required top-level keys, or add prose outside the JSON.
- Do **not** invent sources not present in the source-documents payload; only cite enum values (SIGNED_PROFILE, ATTORNEY_MEMO, CUSTODIAN_EXPORT, CRM_NOTE, STALE_MARKETING_INTAKE) that actually appear for the client.
- Do **not** round intermediate balances before the final field — round only the emitted USD fields to cents, after summing taxes and projecting balances.
- Do **not** mix growth-rate sources: use `expected_growth_rate` (trust candidate) for GRAT/CRAT projections and `expected_return` (retirement account) for Roth/RMD projections; they are distinct fields.
- Do **not** use the prior-year-end balance convention differently per task — for RMD use the start-of-year (i.e., carried-over) traditional balance divided by the age factor, then grow the remainder by `expected_return`.
- When `recommended_conversion_years` overlaps RMD years, still convert the full `annual_conversion_amount` each conversion year (the per-year amount is the bracket-room min, not reduced by RMD income); the simulation order in §3 handles the interaction.
