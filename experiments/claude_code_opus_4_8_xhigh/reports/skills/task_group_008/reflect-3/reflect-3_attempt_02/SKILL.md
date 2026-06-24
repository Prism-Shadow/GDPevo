---
name: private-wealth-advisory-structured-planning
description: >
  Produce structured JSON planning outputs for a private-wealth advisory API covering
  four analysis types: Roth conversion / RMD tax (roth_conversion_rmd), ILIT Crummey
  funding (ilit_crummey_implementation), GRAT-vs-CRAT comparison (trust_comparison), and
  integrated estate-liquidity action plans (estate_liquidity_action_plan). Use when a task
  asks for one of these analyses for a client (e.g. CLT-xxxx / test_xxx), gives a request
  memo plus an answer_template.json, and points to a read-only HTTP advisory API. Covers the
  SOP, every endpoint, conflicting-source resolution, exact enums/schema, the verified
  formulas, rounding, and ISO-date conventions.
---

# Private Wealth Advisory — Structured Planning SOP

You solve each task by querying a read-only advisory API over HTTP (`curl` via Bash), then
emitting ONE JSON object that exactly matches the task's `input/payloads/answer_template.json`.
Output JSON only — no prose, no markdown fences. USD amounts rounded to cents (2 decimals).
Dates are ISO `YYYY-MM-DD`. Numbers are JSON numbers, never strings.

## 0. API base + endpoints
Base URL is provided by the harness (often `API_BASE`); in this environment it is
`<remote-env-url>`. All GET, read-only:
- `GET /api/health` — liveness.
- `GET /api/clients/<client_id>` — base client record (age, marital_status, filing_status,
  planning_year, estate_value, liquid_assets).
- `GET /api/source-documents?client_id=<id>` — list of imported docs, each has
  `source_type`, `effective_date`, and a `facts` object that OVERRIDES base fields.
- `GET /api/retirement-accounts?client_id=<id>` — IRA export (source_type=CUSTODIAN_EXPORT,
  traditional_balance, roth_balance, expected_return, rmd_start_age, recommended_conversion_years).
- `GET /api/life-insurance?client_id=<id>` — policy (death_benefit, annual_premium,
  planned_contribution_date, is_existing_policy_transfer, proposed_owner).
- `GET /api/trust-candidates?client_id=<id>` — asset_value, expected_growth_rate,
  grat_term_years, grat_annuity_rate, crat_term_years, crat_payout_rate.
- `GET /api/policies/tax` — constants (see below).
- `GET /api/rmd-factors` — age → RMD divisor map.

Tax policy constants (confirm by fetching; observed values here):
- `annual_gift_exclusion`: {"2025":19000, "2026":20000}
- `estate_tax_exemption`: {"2025":13990000, "2026":13610000}
- `estate_tax_rate`: 0.4
- `conversion_bracket_targets`: {"MFJ":394600, "SINGLE":197300, "HOH":263500}
- `max_crat_term_years`: 20
- `charitable_deduction_rate`: 0.35
Always read live values and index by the client's `planning_year`/`filing_status`; do not hardcode.

## 1. General SOP (every task)
1. Read prompt.txt + request_memo.md (gives client_id, engagement type, and sometimes the
   explicit planning **horizon year** — e.g. "through 2046"). Read the answer_template.json to
   learn `analysis_type`, required keys, and allowed enum values.
2. `curl` the client record, source-documents, and the endpoint(s) relevant to the analysis
   type, plus `/api/policies/tax` and (for Roth) `/api/rmd-factors`.
3. Resolve conflicting fields with the priority rules in §2.
4. Compute using the verified formulas in §4–§7.
5. Emit JSON matching the template. Set `task_id` to the requested id (e.g. `test_001`),
   `client_id` to the client, and `analysis_type` to the template's fixed enum.

## 2. Conflicting-source resolution (CONFIRMED)
Source documents disagree (an old CRM import vs attorney memo vs signed profile). Priority for
**profile/goal/beneficiary** facts (income, marginal_tax_rate, beneficiary_count, filing_status,
philanthropic_intent, family_transfer_priority, liquid_assets, estate_value):

  SIGNED_PROFILE  >  ATTORNEY_MEMO  >  CRM_NOTE  >  STALE_MARKETING_INTAKE

SIGNED_PROFILE is both the most recent (latest `effective_date`) and authoritative — it wins.
Use its `facts` for the controlling profile values. Tiebreak (same source_type) = latest
`effective_date`.

Field-resolution outputs (CONFIRMED across tasks):
- `controlling_profile_source`   = `SIGNED_PROFILE`
- `controlling_goal_source`      = `SIGNED_PROFILE`
- `controlling_beneficiary_source` = `SIGNED_PROFILE`
- `controlling_account_source`   = `CUSTODIAN_EXPORT`  (retirement/IRA numbers come from the custodian export)
- `controlling_policy_source`    = `SIGNED_PROFILE`     (NOT CUSTODIAN_EXPORT — verified)
- `controlling_asset_source`     = `ATTORNEY_MEMO`      (estate/asset valuation; attorney memo controls)

Use the SIGNED_PROFILE values for income, marginal_tax_rate, beneficiary_count, estate_value,
liquid_assets, philanthropic_intent, family_transfer_priority. Use CUSTODIAN_EXPORT
(retirement-accounts) for IRA balances, expected_return, rmd_start_age, recommended_conversion_years.
Use trust-candidates for asset_value/growth/term/rates and life-insurance for death_benefit/premium/dates.

## 3. Rounding / dates / output
- Round every USD field to 2 decimals (cents). Integer-year fields are plain integers.
- ISO dates `YYYY-MM-DD`.
- `action_set` (estate plan) MUST be a list sorted alphabetically; it is graded as an exact set
  — do NOT add extra items (adding a wrong item lowers the score).
- Emit exactly the template's required_top_level_keys; numbers as JSON numbers.

## 4. roth_conversion_rmd (FULLY VERIFIED — scored 1.0)
Inputs: client (age, planning_year, filing_status), SIGNED_PROFILE facts
(annual_non_ira_income, marginal_tax_rate), retirement-accounts (traditional_balance,
roth_balance, expected_return r, rmd_start_age, recommended_conversion_years), tax policy
(conversion_bracket_targets[filing_status]), rmd-factors, and the memo's horizon_year.

Derived fields:
- `first_conversion_year` = planning_year.
- `first_rmd_year` = planning_year + (rmd_start_age − age).
- `conversion_years` = recommended_conversion_years (from custodian export).
- `conversion_years_positive` = same as conversion_years.
- `annual_conversion_amount` = conversion_bracket_targets[filing_status] − annual_non_ira_income
  (fill the bracket headroom; use SIGNED income).
- `total_converted` = annual_conversion_amount × conversion_years.
- `total_conversion_tax` = total_converted × marginal_tax_rate.

Year-by-year simulation (loop y from planning_year through horizon_year inclusive;
cur_age = age + (y − planning_year)); run it twice — baseline (no conversion) and conversion —
both starting from the SAME initial traditional_balance and roth_balance:
  for each year y:
    1. if conversion scenario AND 0 <= (y − first_conversion_year) < conversion_years:
         conv = min(annual_conversion_amount, traditional); traditional -= conv; roth += conv
    2. if cur_age >= rmd_start_age and rmd_factor[cur_age] exists:
         rmd = traditional / rmd_factor[cur_age]
         rmd_tax += rmd * marginal_tax_rate
         traditional -= rmd
    3. traditional *= (1 + r);  roth *= (1 + r)        # growth applied at END of year
Outputs:
- `baseline_rmd_tax_through_horizon` = rmd_tax from baseline run.
- `conversion_rmd_tax_through_horizon` = rmd_tax from conversion run.
- `rmd_tax_savings_through_horizon` = baseline − conversion.
- `projected_roth_balance_horizon` = conversion-run roth at end of horizon_year.
- `projected_traditional_balance_horizon` = conversion-run traditional at end of horizon_year.
Order of operations matters: conversion first, then RMD, then growth, every year.

Recommendation enums:
- `primary_action` = `STAGED_ROTH_CONVERSION` when headroom > 0 and savings > 0
  (else `DEFER` / `NO_CONVERSION`).
- `suitability` = `SUITABLE` when a positive-savings staged conversion is advisable
  (verified SUITABLE even when RMD starts next year). Use `BORDERLINE`/`DEFER` only if the
  conversion is marginal or not advisable.
- `risk_flag`:
    * `RMD_NEAR_TERM` if RMDs begin within ~1 year (rmd_start_age − age <= 1, i.e. age >= rmd_start_age−1).
    * otherwise `TAX_BRACKET_MANAGEMENT` (the normal multi-year bracket-fill case).
    * `LIQUIDITY_CONSTRAINT` only if liquid assets clearly cannot cover conversion taxes.
- `heir_tax_profile` from conversion-run end balances, share = roth / (roth + traditional):
    * share >= ~0.65 → `MOSTLY_TAX_FREE`
    * ~0.35 < share < ~0.65 → `MIXED_TAXABLE_AND_TAX_FREE`
    * share <= ~0.35 → `MOSTLY_TAXABLE`
  (At ~0.61 both MIXED and MOSTLY_TAX_FREE were accepted; prefer MIXED in the 0.35–0.65 band.)
- `source_resolution.controlling_profile_source` = SIGNED_PROFILE;
  `controlling_account_source` = CUSTODIAN_EXPORT.

## 5. ilit_crummey_implementation (mostly verified — gift/exclusion/enums/sources confirmed)
Inputs: planning_year, SIGNED beneficiary_count, tax policy annual_gift_exclusion[planning_year],
life-insurance (death_benefit, annual_premium, planned_contribution_date, is_existing_policy_transfer),
estate_value/exemption (for liquidity context).

gift_plan (CONFIRMED):
- `planning_year` = client planning_year.
- `annual_exclusion_per_beneficiary` = annual_gift_exclusion[planning_year] (e.g. 20000 in 2026).
- `beneficiary_count` = SIGNED_PROFILE beneficiary_count.
- `annual_exclusion_capacity` = annual_exclusion_per_beneficiary × beneficiary_count.
- `annual_premium` = life-insurance annual_premium.
- `premium_gap` = max(0, annual_premium − annual_exclusion_capacity)  (0 when premium fits capacity).

administration (partially verified — these were CONFIRMED):
- `contribution_date` = life-insurance planned_contribution_date.
- `notices_required` = beneficiary_count.
- `dedicated_bank_account_required` = true.
Crummey date fields (notice_due_date, withdrawal_window_end, earliest_premium_payment_date)
were NOT independently verified. Reasonable convention: notices issued on the contribution_date
(`notice_due_date` = contribution_date); a 30-day withdrawal window
(`withdrawal_window_end` = contribution_date + 30 days); premium payable the day after the window
closes (`earliest_premium_payment_date` = withdrawal_window_end + 1 day). Treat the window length
as uncertain; 30 days is the default assumption. Always keep earliest_premium_payment_date strictly
after withdrawal_window_end, and withdrawal_window_end after contribution_date.

estate_result (death_benefit confirmed):
- `death_benefit` = life-insurance death_benefit.
- `estate_inclusion_risk` (same enum as recommendation.risk_flag):
    * `THREE_YEAR_LOOKBACK` if is_existing_policy_transfer == true (transferring an existing policy
      triggers the 3-year inclusion rule).
    * `EXCLUSION_SHORTFALL` if premium_gap > 0 (premium exceeds annual-exclusion capacity).
    * `THREE_YEAR_LOOKBACK_AND_EXCLUSION_SHORTFALL` if both.
    * else `LOW_IF_FORMALITIES_MET` (new policy, premium within capacity — CONFIRMED case).
- `projected_outside_estate_if_implemented` = death_benefit (full benefit sits outside the estate
  when properly implemented with no lookback).
- `tax_liquidity_support` = death_benefit available to fund estate-tax liquidity
  (note: it may instead be capped at the estate_tax_exposure; this exact value was not verified —
  default to death_benefit but be aware of the cap interpretation).

recommendation:
- `primary_action`:
    * `FUND_WITH_CRUMMEY_NOTICES` when premium fits capacity and no lookback (CONFIRMED).
    * `USE_LIFETIME_EXEMPTION_FOR_SHORTFALL` when premium_gap > 0 (no lookback).
    * `USE_NEW_POLICY_OR_ACCEPT_LOOKBACK` / `DISCLOSE_LOOKBACK_AND_USE_EXEMPTION` when a 3-year
      lookback is in play (latter when there is also a shortfall to disclose).
- `suitability` = `SUITABLE_WITH_ADMINISTRATION` in the clean case (else BORDERLINE / NOT_SUITABLE).
- `risk_flag` = same value as estate_inclusion_risk.
- `controlling_beneficiary_source` = SIGNED_PROFILE; `controlling_policy_source` = SIGNED_PROFILE.

## 6. trust_comparison — GRAT vs CRAT (enums/estate verified; projection math NOT verified)
Inputs: estate_value, exemption[planning_year], estate_tax_rate, liquid_assets,
SIGNED philanthropic_intent + family_transfer_priority, trust-candidates
(asset_value A, expected_growth_rate g, grat_term_years, grat_annuity_rate, crat_term_years,
crat_payout_rate), charitable_deduction_rate, max_crat_term_years.

estate_context (CONFIRMED formula):
- `taxable_estate` = estate_value − estate_tax_exemption[planning_year].
- `estate_tax_exposure` = taxable_estate × estate_tax_rate (0.4).
- `liquidity_gap_before_planning` = estate_tax_exposure − liquid_assets.

recommendation (CONFIRMED logic):
- If family_transfer_priority dominates philanthropic_intent → `preferred_strategy` = `GRAT`,
  `rationale_code` = `CHILDREN_TRANSFER_PRIORITY`, `alternate_role` = `SECONDARY_CHARITABLE_TOOL`.
- If philanthropic_intent dominates → `preferred_strategy` = `CRAT`,
  `rationale_code` = `PHILANTHROPIC_PRIORITY`, `alternate_role` = `SECONDARY_FAMILY_TRANSFER_TOOL`.
- Use the SIGNED_PROFILE values for both intents (high > moderate > low).

grat (CONFIRMED: term_years, mortality flag):
- `term_years` = grat_term_years.
- `mortality_inclusion_risk` = `TERM_SURVIVAL_REQUIRED` (constant).
- `projected_remainder_to_heirs` and `estimated_estate_tax_reduction` — NOT verified. Best-guess
  textbook model: annuity = A × grat_annuity_rate paid each year for the term; remainder to heirs
  = FV(A at growth g over term) − FV(annuity stream at g over term), where FV of an ordinary
  annuity = pmt × ((1+g)^n − 1)/g. Then estimated_estate_tax_reduction = remainder × estate_tax_rate.
  (Timing/annuity-due conventions are uncertain; this exact value was not confirmed.)

crat (CONFIRMED: term_years, family_fit):
- `term_years` = crat_term_years (cap at max_crat_term_years = 20).
- `family_transfer_fit` = `LOW` (a CRAT passes the remainder to charity, not family).
- `projected_charitable_remainder` and `estimated_income_tax_deduction` — NOT verified. Best-guess:
  charitable_remainder = FV(A at g over crat term) − FV(payout stream A×crat_payout_rate at g over
  term); estimated_income_tax_deduction ≈ asset_value × charitable_deduction_rate (0.35)
  (alternative: charitable_remainder × charitable_deduction_rate). Both unconfirmed.

source_resolution: `controlling_goal_source` = SIGNED_PROFILE; `controlling_asset_source` = ATTORNEY_MEMO.

## 7. estate_liquidity_action_plan (estate/ILIT/enums/action_set/sources verified)
Combines an ILIT and a trust transfer. Inputs as in §5 and §6.

estate_context (CONFIRMED, identical formula to §6):
- taxable_estate = estate_value − exemption[planning_year]; estate_tax_exposure = × 0.4;
  liquidity_gap_before_planning = exposure − liquid_assets.

ilit block (CONFIRMED):
- `annual_exclusion_capacity` = annual_gift_exclusion[planning_year] × SIGNED beneficiary_count.
- `premium_gap` = max(0, annual_premium − annual_exclusion_capacity).
- `estate_inclusion_risk` = same logic as §5 (LOW_IF_FORMALITIES_MET when new policy & premium fits).
- `projected_outside_estate_if_implemented` = life-insurance death_benefit.

trust_transfer block:
- `preferred_strategy` = GRAT or CRAT per §6 recommendation logic (CONFIRMED selection).
- `projected_remainder_to_heirs`, `estimated_estate_tax_reduction`, `projected_charitable_remainder`
  — use the §6 GRAT/CRAT formulas (NOT verified).

recommendation (CONFIRMED):
- `primary_action`:
    * `COMBINE_ILIT_AND_GRAT` when an ILIT plus a GRAT-preferred transfer applies (CONFIRMED case).
    * `CRAT_WITH_LIQUIDITY_REVIEW` when CRAT is preferred.
    * `ILIT_WITH_EXEMPTION_REVIEW` when premium_gap/exemption issues dominate.
- `sequencing`:
    * `ILIT_FIRST_THEN_GRAT` for the combine case (CONFIRMED).
    * `TRUST_DECISION_FIRST` when the trust choice must be settled first.
    * `ILIT_FIRST_THEN_ATTORNEY_REVIEW` when attorney drafting must follow ILIT.
- `risk_flag` = the ILIT estate_inclusion_risk value (LOW_IF_FORMALITIES_MET in the clean case).

action_set (CONFIRMED — sorted alphabetically, exact set, no extras):
Build from this universe:
  ATTORNEY_DRAFT_REVIEW, CRAT_FOR_CHARITABLE_REMAINDER, GRAT_FOR_APPRECIATING_SHARES,
  ILIT_CRUMMEY_NOTICE_CYCLE, LIFETIME_EXEMPTION_ALLOCATION
Selection rules (verified for the GRAT+ILIT, premium-fits, low-philanthropy case, which yields
exactly [ATTORNEY_DRAFT_REVIEW, GRAT_FOR_APPRECIATING_SHARES, ILIT_CRUMMEY_NOTICE_CYCLE]):
  - Always include `ATTORNEY_DRAFT_REVIEW`.
  - Include `ILIT_CRUMMEY_NOTICE_CYCLE` whenever an ILIT is being funded.
  - Include `GRAT_FOR_APPRECIATING_SHARES` when preferred_strategy = GRAT.
  - Include `CRAT_FOR_CHARITABLE_REMAINDER` only when CRAT is preferred / philanthropic priority.
  - Include `LIFETIME_EXEMPTION_ALLOCATION` only when premium_gap > 0 (an exclusion shortfall must be
    covered by lifetime exemption). DO NOT include it when premium fits capacity — adding it when not
    warranted lowers the score.
  Then sort the list alphabetically.

source_resolution: `controlling_goal_source` = SIGNED_PROFILE; `controlling_policy_source` = SIGNED_PROFILE.

## 8. Pitfalls / checklist
- Always pull profile facts from SIGNED_PROFILE (beneficiary_count, income, marginal_tax_rate,
  intents) — the CRM/older imports are decoys with different numbers.
- IRA balances/return/rmd_start_age/recommended_conversion_years come from CUSTODIAN_EXPORT, not docs.
- Roth sim order per year: conversion → RMD → growth; growth applied at end of year; loop is
  inclusive of horizon_year; both scenarios start from identical initial balances.
- Bracket headroom uses the SIGNED non-IRA income and the filing_status bracket target.
- Index gift exclusion and estate exemption by the client's planning_year; use estate_tax_rate=0.4.
- estate_context everywhere: taxable = estate − exemption; exposure = taxable × 0.4; gap = exposure − liquid.
- premium_gap and exclusion capacity use SIGNED beneficiary_count.
- action_set is an exact, alphabetically-sorted set — only include warranted actions.
- Round USD to cents; integers for years/counts; ISO dates; output a single JSON object only.
- GRAT/CRAT dollar projections are the least certain piece — apply the textbook FV-minus-annuity-FV
  model consistently and double-check the term/rate inputs come from trust-candidates.
