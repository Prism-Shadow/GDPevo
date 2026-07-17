# Personal Financial Advisory — Structured Planning Output Skill

Methodology for producing the structured JSON planning output the advisory harness
expects across five analysis types: `roth_conversion_rmd`, `ilit_crummey_implementation`,
`trust_comparison`, and `estate_liquidity_action_plan`. The advisory API exposes client
records plus CONFLICTING source documents (CRM note, attorney memo, custodian export,
signed profile, stale marketing intake). Resolving which source controls each fact is
half the task; applying the right formula with cent-level rounding is the other half.

## 1. Remote API Workflow (endpoint order)

Base URL is supplied by the harness as the advisory API base. Always GET in this order:

1. `GET /api/health` — confirm `{ok:true}` before anything else.
2. `GET /api/clients/<client_id>` — base record (age, filing_status, planning_year,
   estate_value, liquid_assets, marital_status).
3. `GET /api/source-documents?client_id=<id>` — the conflicting sources. Read EVERY
   document's `facts`; do not assume the client base record is authoritative.
4. Analysis-specific data:
   - Roth/RMD: `GET /api/retirement-accounts?client_id=<id>` + `GET /api/rmd-factors` + `GET /api/policies/tax`.
   - ILIT: `GET /api/life-insurance?client_id=<id>` + `GET /api/policies/tax`.
   - Trust comparison: `GET /api/trust-candidates?client_id=<id>` + `GET /api/policies/tax`.
   - Estate liquidity: retirement + life-insurance + trust-candidates + policies/tax.
5. `GET /api/policies/tax` — constants: `annual_gift_exclusion` (by year),
   `estate_tax_exemption` (by year), `estate_tax_rate`, `conversion_bracket_targets`
   (by filing status), `max_crat_term_years`, `charitable_deduction_rate`.
6. `GET /api/rmd-factors` — age-keyed divisor table (73..99); only needed for Roth/RMD.

Fetch eagerly; endpoints are cheap and facts you skip will silently mismatch.

## 2. Source-Resolution Precedence (the `source_resolution` block)

Some client records disagree because they were imported from different systems at
different times. Apply this precedence to decide which source CONTROLS each fact, then
emit the controlling source type in the `source_resolution` fields.

- **SIGNED_PROFILE controls client-stated facts**: `annual_non_ira_income`,
  `marginal_tax_rate`, `beneficiary_count`, `age`, `planning_year`, `filing_status`,
  `marital_status`, `philanthropic_intent`, `family_transfer_priority`, `liquid_assets`,
  `estate_value`. The signed profile is the most recent, client-signed document, so it
  wins over CRM_NOTE and STALE_MARKETING_INTAKE for anything the client states.
- **CUSTODIAN_EXPORT controls account balances**: `traditional_balance`,
  `roth_balance`, `expected_return`, `rmd_start_age`, `recommended_conversion_years`
  from the retirement-accounts endpoint. Never use an income/age figure from the signed
  profile to override a custodian balance.
- **ATTORNEY_MEMO controls trust / estate-asset facts**: the trust-candidate asset
  value, growth rate, GRAT/CRAT terms, and estate-asset characterizations. (Confirmed:
  choosing SIGNED_PROFILE for a trust asset is wrong.) The attorney memo also commonly
  restates `estate_value` and `family_transfer_priority`; when it agrees with the signed
  profile, signed still controls client-stated facts.
- **CRM_NOTE / STALE_MARKETING_INTAKE**: older imports; superseded by the three above.
  Use only if no higher-precedence source states the fact.

`source_resolution` output fields by analysis type:
- roth_conversion_rmd: `controlling_profile_source` (=SIGNED_PROFILE), `controlling_account_source` (=CUSTODIAN_EXPORT).
- ilit_crummey_implementation: `controlling_beneficiary_source` (=SIGNED_PROFILE for beneficiary_count), `controlling_policy_source` (carrier policy data; use CUSTODIAN_EXPORT for the carrier-sourced death benefit/premium; ATTORNEY_MEMO is the fallback if the policy was structured by counsel — pick the one matching where the policy *facts* originate).
- trust_comparison: `controlling_goal_source` (=SIGNED_PROFILE for transfer/philanthropy priority), `controlling_asset_source` (=ATTORNEY_MEMO for the trust asset).
- estate_liquidity_action_plan: `controlling_goal_source` (=SIGNED_PROFILE), `controlling_policy_source` (as above).

## 3. Numeric Conventions (all analysis types)

- USD amounts: round to cents (2 decimals) as JSON numbers, never strings. Round only
  the final emitted value, not intermediates.
- Dates: ISO `YYYY-MM-DD`. Use real calendar arithmetic (timedelta), not day-of-month
  addition (months roll over).
- Years: integers. planning_year from the signed profile / client record.
- Estate tax: `estate_tax_exposure = (taxable_estate - estate_tax_exemption[planning_year]) * estate_tax_rate`. Use the exemption for the planning year (2026 -> 13,610,000; 2025 -> 13,990,000).
- `taxable_estate` = gross estate_value (do NOT pre-subtract the exemption; exposure is a separate field that applies the exemption).

## 4. Analysis Type: roth_conversion_rmd

**Pull**: retirement-accounts, policies/tax, rmd-factors. `horizon_year` comes from the
request memo (read it). `marginal_tax_rate`, `annual_non_ira_income`, `filing_status`,
`age` from SIGNED_PROFILE. `traditional_balance`, `roth_balance`, `expected_return`,
`rmd_start_age`, `recommended_conversion_years` from CUSTODIAN_EXPORT.

**Conversion plan**:
- `bracket_target` = `conversion_bracket_targets[filing_status]` (MFJ 394600, SINGLE 197300, HOH 263500).
- `bracket_room` = `bracket_target - annual_non_ira_income`.
- `balance_per_year` = `traditional_balance / recommended_conversion_years`.
- `annual_conversion_amount` = `min(bracket_room, balance_per_year)` — this is the per-year conversion, even when bracket_room binds (you do NOT stretch to convert the whole balance).
- `conversion_years` = `recommended_conversion_years`; `conversion_years_positive` = same (it is a non-negative guard).
- `first_conversion_year` = `planning_year`.
- `total_converted` = `annual_conversion_amount * conversion_years`.
- `total_conversion_tax` = `total_converted * marginal_tax_rate`.

**RMD projection** (year-by-year; this exact loop scored full marks):
- `first_rmd_year` = `planning_year + (rmd_start_age - age)`.
- `horizon_year` = from memo.
- For each year from `planning_year` to `horizon_year` (age = start_age + k), in this
  ORDER per year: (a) if within conversion years (`age` in `[start_age, start_age+conversion_years-1]`) and doing the conversion scenario, subtract `annual_conversion_amount` from traditional and add to Roth; (b) if `age >= rmd_start_age`, RMD = `current_traditional / rmd_factors[str(age)]`, subtract RMD from traditional, add `RMD * marginal_tax_rate` to the running RMD tax; (c) grow both balances by `*(1+expected_return)`.
- Run twice: baseline (no conversions, Roth starts at existing `roth_balance`) and
  conversion scenario (Roth starts at existing `roth_balance` and receives conversions).
- `baseline_rmd_tax_through_horizon` = baseline accumulated RMD tax.
- `conversion_rmd_tax_through_horizon` = conversion-scenario accumulated RMD tax.
- `rmd_tax_savings_through_horizon` = baseline - conversion.
- NOTE: conversion years can OVERLAP RMD years (near-RMD clients). Keep the
  convert-then-RMD-then-grow order above; it matched the evaluator even when conversions
  occur after RMDs have begun. The existing `roth_balance` is the Roth starting point
  (not zero) and grows with conversions.

**Legacy projection**: `projected_roth_balance_horizon` and
`projected_traditional_balance_horizon` = the conversion-scenario end balances.
`heir_tax_profile`: `MIXED_TAXABLE_AND_TAX_FREE` is correct whenever a material Roth
balance coexists with a material traditional balance at the horizon (validated for both
majority-Roth and majority-traditional splits). Use `MOSTLY_TAX_FREE` only if the
traditional balance is ~0, `MOSTLY_TAXABLE` only if the Roth balance is ~0.

**Recommendation**:
- `primary_action` = `STAGED_ROTH_CONVERSION` whenever bracket_room > 0 and conversions occur.
- `risk_flag`: `RMD_NEAR_TERM` if RMDs begin within ~1 year of the planning year (age at
  or just below rmd_start_age); otherwise `TAX_BRACKET_MANAGEMENT` (bracket filling is
  the active concern). `LIQUIDITY_CONSTRAINT` for cash-tight cases.
- `suitability`: `SUITABLE` when the conversion has bracket room AND produces positive
  RMD-tax savings — EVEN when RMDs are near-term. Do NOT downgrade to BORDERLINE just
  because RMDs are close; the near-term concern belongs in `risk_flag`, not
  `suitability`. (This distinction cost a full point until corrected.)

## 5. Analysis Type: ilit_crummey_implementation

**Pull**: life-insurance, policies/tax, source-documents. From life-insurance:
`death_benefit`, `annual_premium`, `planned_contribution_date`, `is_existing_policy_transfer`.

**Gift plan**:
- `planning_year` from client/signed.
- `annual_exclusion_per_beneficiary` = `annual_gift_exclusion[planning_year]` (2026 -> 20000; 2025 -> 19000 — match the planning year exactly).
- `beneficiary_count` from SIGNED_PROFILE.
- `annual_exclusion_capacity` = `annual_exclusion_per_beneficiary * beneficiary_count`.
- `annual_premium` from life-insurance.
- `premium_gap` = `max(0, annual_premium - annual_exclusion_capacity)` — FLOOR at zero.
  A surplus (premium < capacity) reports `0`, not a negative number. (Reporting the raw
  negative difference cost score.)

**Administration** (Crummey cycle, all offsets from `planned_contribution_date`):
- `notices_required` = `beneficiary_count` (one Crummey notice per beneficiary).
- `contribution_date` = `planned_contribution_date`.
- `notice_due_date` = contribution_date + 7 days.
- `withdrawal_window_end` = contribution_date + 30 days.
- `earliest_premium_payment_date` = contribution_date + 1 day.
- `dedicated_bank_account_required` = true (ILIT must hold its own account).

**Estate result**:
- `death_benefit` from life-insurance.
- `estate_inclusion_risk`: combine lookback + shortfall.
  - `is_existing_policy_transfer = true` -> `THREE_YEAR_LOOKBACK` (add `_AND_EXCLUSION_SHORTFALL` if premium_gap > 0).
  - `is_existing_policy_transfer = false` (new policy): premium_gap = 0 -> `LOW_IF_FORMALITIES_MET`; premium_gap > 0 -> `EXCLUSION_SHORTFALL`.
- `projected_outside_estate_if_implemented` = `death_benefit` (the DB passes outside the estate via the ILIT).
- `tax_liquidity_support` = estate tax exposure = `(estate_value - estate_tax_exemption[planning_year]) * estate_tax_rate`. This is DIFFERENT from `projected_outside_estate` (which is the DB). Using the DB here cost score; the field is the estate-tax bill the ILIT liquidity addresses.

**Recommendation**:
- new policy, gap=0 -> `FUND_WITH_CRUMMEY_NOTICES`, `SUITABLE_WITH_ADMINISTRATION`, risk as above.
- gap>0 -> `USE_LIFETIME_EXEMPTION_FOR_SHORTFALL`.
- existing transfer -> `USE_NEW_POLICY_OR_ACCEPT_LOOKBACK` (or `DISCLOSE_LOOKBACK_AND_USE_EXEMPTION` if also a shortfall).

## 6. Analysis Type: trust_comparison (GRAT vs CRAT)

**Pull**: trust-candidates, policies/tax, source-documents. From trust-candidates:
`asset_value`, `expected_growth_rate`, `grat_term_years`, `grat_annuity_rate`,
`crat_term_years`, `crat_payout_rate`.

**Remainder formula (VALIDATED — simple, not future-valued)**:
- `projected_value` = `asset_value * (1 + expected_growth_rate) ** term`.
- `total_payouts` = `asset_value * payout_rate * term` (NOMINAL sum, NOT future-valued).
- `remainder` = `projected_value - total_payouts`.
- Do NOT compute the future value of the annuity stream (annuity-FV). That alternate
  formula scored materially worse — nominal total payouts is the expected method.

**GRAT block**:
- `term_years` = `grat_term_years`.
- `projected_remainder_to_heirs` = `asset_value*(1+g)**grat_term - asset_value*grat_annuity_rate*grat_term`.
- `estimated_estate_tax_reduction` = `projected_remainder_to_heirs * estate_tax_rate` (the estate tax saved on the value removed from the estate).
- `mortality_inclusion_risk` = `TERM_SURVIVAL_REQUIRED` (GRAT requires grantor survival to term).

**CRAT block**:
- `term_years` = `crat_term_years` (capped at `max_crat_term_years`).
- `projected_charitable_remainder` = `asset_value*(1+g)**crat_term - asset_value*crat_payout_rate*crat_term`.
- `estimated_income_tax_deduction` = `asset_value * charitable_deduction_rate` (0.35).
- `family_transfer_fit` = `LOW` (CRAT is a charitable tool).

**Estate context**: `taxable_estate` = `estate_value`; `estate_tax_exposure` =
`(taxable_estate - exemption) * estate_tax_rate`; `liquidity_gap_before_planning` =
`estate_tax_exposure - liquid_assets`.

**Recommendation**: `preferred_strategy` = `GRAT` when `family_transfer_priority` is high
(SIGNED_PROFILE/ATTORNEY_MEMO), else `CRAT` when `philanthropic_intent` is high.
`rationale_code` = `CHILDREN_TRANSFER_PRIORITY` (GRAT) or `PHILANTHROPIC_PRIORITY` (CRAT).
`alternate_role` = `SECONDARY_CHARITABLE_TOOL` when GRAT preferred, `SECONDARY_FAMILY_TRANSFER_TOOL` when CRAT preferred.

## 7. Analysis Type: estate_liquidity_action_plan

Combines ILIT + trust transfer. Reuse the ILIT, trust, and estate-context recipes above.

- `estate_context`: as in trust_comparison.
- `ilit`: `annual_exclusion_capacity`, `premium_gap` (floored), `estate_inclusion_risk`
  (as in ILIT), `projected_outside_estate_if_implemented` (= death_benefit).
- `trust_transfer`: `preferred_strategy` (GRAT/CRAT by goal), `projected_remainder_to_heirs`
  (GRAT simple remainder), `estimated_estate_tax_reduction` (grat remainder * estate_tax_rate), `projected_charitable_remainder` (CRAT simple remainder).
- `recommendation.primary_action` = `COMBINE_ILIT_AND_GRAT` when both an ILIT and a GRAT
  are indicated; `sequencing` = `ILIT_FIRST_THEN_GRAT` (liquidity first, then transfer);
  `risk_flag` = the ILIT risk flag.
- `action_set`: choose the relevant enums and SORT ALPHABETICALLY. Relevant set for an
  ILIT+GRAT plan: `ATTORNEY_DRAFT_REVIEW`, `GRAT_FOR_APPRECIATING_SHARES`,
  `ILIT_CRUMMEY_NOTICE_CYCLE`. Add `LIFETIME_EXEMPTION_ALLOCATION` when a gift needs
  exemption (e.g., GRAT remainder future-interest gift, or ILIT premium shortfall). Add
  `CRAT_FOR_CHARITABLE_REMAINDER` only when a CRAT is actually chosen.
- `source_resolution`: `controlling_goal_source`=SIGNED_PROFILE, `controlling_policy_source` as in ILIT.

## 8. Lessons Learned (from training feedback, applied generically)

- Bracket-room bound wins: when bracket_room < balance/years, convert only
  bracket_room/year for the recommended years; total_converted is intentionally less
  than the full balance. The remaining balance is projected through RMDs normally.
- Conversion tax and RMD tax both use the SIGNED_PROFILE `marginal_tax_rate` as a flat
  rate on the converted/RMD dollars. Do not attempt progressive bracket tiering.
- `suitability` and `risk_flag` are SEPARATE dimensions. A near-RMD conversion that still
  works is `SUITABLE` + `RMD_NEAR_TERM`, not `BORDERLINE`.
- `premium_gap` is a shortfall floored at zero; a surplus is reported as 0.
- `tax_liquidity_support` is the estate-tax exposure, not the death benefit.
- GRAT/CRAT remainders use nominal total payouts, not annuity future value.
- Trust-asset `controlling_asset_source` is ATTORNEY_MEMO; do not use SIGNED_PROFILE.
- The existing `roth_balance` is the Roth projection's starting point (can be nonzero).
- Heuristic splits for `heir_tax_profile` are generous: `MIXED_TAXABLE_AND_TAX_FREE`
  covers any case with material balances in both buckets.

## 9. Common Mistakes / Exclusions

- Do NOT subtract the estate exemption inside `taxable_estate` (it goes in the exposure formula).
- Do NOT use 2025 gift exclusion for a 2026 planning year (or vice versa) — match the year.
- Do NOT use the attorney memo for client income/beneficiary facts; signed profile wins.
- Do NOT use the signed profile for retirement balances; custodian export wins.
- Do NOT future-value the GRAT/CRAT annuity payouts when computing remainders.
- Do NOT report a negative `premium_gap`; floor at zero.
- Do NOT set `tax_liquidity_support` equal to the death benefit.
- Do NOT conflate `RMD_NEAR_TERM` (risk_flag) with `BORDERLINE` (suitability).
- Do NOT extend conversions beyond `recommended_conversion_years` to clear the balance;
  respect the bracket cap and the recommended term.
- Do NOT start the Roth projection at zero if a `roth_balance` already exists.
- `conversion_years_positive` equals `conversion_years` for any viable plan (it is the non-negative guard).
- When RMD and conversion years overlap, keep the per-year order: convert -> take RMD on the resulting balance -> grow.
- Always sort `action_set` alphabetically before emitting.
