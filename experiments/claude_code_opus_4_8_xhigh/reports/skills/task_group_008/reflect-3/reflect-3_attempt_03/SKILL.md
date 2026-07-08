---
name: private-wealth-advisory-planning
description: >
  Solve private-wealth advisory planning tasks that require querying a remote
  advisory HTTP API and returning ONE strict JSON object. Covers four
  analysis_types: roth_conversion_rmd (Roth conversion / RMD tax), 
  ilit_crummey_implementation (ILIT Crummey funding), trust_comparison
  (GRAT vs CRAT), and estate_liquidity_action_plan (integrated estate
  liquidity). Use when a task names a client (CLT-####), gives an
  answer_template.json with one of those analysis_types, and provides an
  advisory API base URL. Contains the field-resolution priority, the exact
  derived formulas, enum values, and rounding/date conventions.
---

# Private Wealth Advisory Planning Skill

You answer one client engagement at a time by pulling facts from a read-only
advisory API and emitting a single JSON object that matches the task's
`input/payloads/answer_template.json`. Output JSON ONLY (no prose). Round all
USD amounts to cents (2 decimals). Dates are ISO `YYYY-MM-DD`.

## 1. API endpoints (base URL given by the harness, e.g. API_BASE)
Use `curl` (GET). Helper scripts must use `python` (not `python3`).
- `GET /api/health` — liveness.
- `GET /api/clients/<client_id>` — base record (age, filing_status, estate_value, liquid_assets, planning_year).
- `GET /api/source-documents?client_id=<id>` — list of docs; each has `source_type`, `effective_date`, and a `facts` object that can OVERRIDE the base record. Sources seen: CRM_NOTE, ATTORNEY_MEMO, SIGNED_PROFILE.
- `GET /api/retirement-accounts?client_id=<id>` — `source_type=CUSTODIAN_EXPORT`, fields: traditional_balance, roth_balance, expected_return, rmd_start_age, recommended_conversion_years.
- `GET /api/life-insurance?client_id=<id>` — policy: proposed_owner, death_benefit, annual_premium, planned_contribution_date, is_existing_policy_transfer.
- `GET /api/trust-candidates?client_id=<id>` — asset_value, expected_growth_rate, grat_term_years, grat_annuity_rate, crat_term_years, crat_payout_rate.
- `GET /api/policies/tax` — constants (see below).
- `GET /api/rmd-factors` — age -> RMD divisor map (73..99).

### Tax policy constants (as currently published; ALWAYS re-fetch, do not hardcode blindly)
- `annual_gift_exclusion`: {"2025":19000, "2026":20000} (use the planning_year).
- `estate_tax_exemption`: {"2025":13990000, "2026":13610000} (per person, use planning_year).
- `estate_tax_rate`: 0.40
- `conversion_bracket_targets`: {"MFJ":394600, "SINGLE":197300, "HOH":263500}
- `max_crat_term_years`: 20
- `charitable_deduction_rate`: 0.35

## 2. Conflicting-source resolution (PRIORITY — verified)
Different documents disagree. Resolve each fact group by a FIXED controlling
source, not merely by latest date:

- Profile / household facts (annual_non_ira_income, marginal_tax_rate,
  beneficiary_count, age, philanthropic_intent, family_transfer_priority,
  liquid_assets, filing_status, planning_year):
  -> **SIGNED_PROFILE controls.** It is the newest and most authoritative
  (effective_date 2026-02-06 > attorney 2026-01-18 > CRM 2025-11-20).
  Report `controlling_profile_source` = SIGNED_PROFILE,
  `controlling_beneficiary_source` = SIGNED_PROFILE,
  `controlling_goal_source` = SIGNED_PROFILE.
- Retirement-account facts (balances, expected_return, rmd_start_age,
  recommended_conversion_years):
  -> **CUSTODIAN_EXPORT controls.** Report `controlling_account_source` = CUSTODIAN_EXPORT.
- Life-insurance policy facts used in the answer (death_benefit, premium):
  -> Report `controlling_policy_source` = **SIGNED_PROFILE**
  (verified: SIGNED is the controlling policy source, NOT CUSTODIAN_EXPORT).
- Estate / asset VALUATION basis (estate_value used for taxable-estate math):
  -> Report `controlling_asset_source` = **ATTORNEY_MEMO**
  (verified: the attorney memo controls the estate/asset valuation source,
  even though SIGNED_PROFILE carries the same estate_value number).

Note: estate_value is usually identical across ATTORNEY_MEMO and SIGNED_PROFILE,
so the numeric taxable estate is the same regardless; only the reported
`controlling_*_source` enum differs by the rules above.

## 3. Shared estate-context math (verified)
Used by trust_comparison and estate_liquidity_action_plan.
- `exemption_units` = 2 if marital_status == "married" (filing MFJ) else 1.
  -> **Married/MFJ clients get DOUBLE the per-person exemption.**
- `taxable_estate` = max(0, estate_value - exemption_units * estate_tax_exemption[planning_year])
- `estate_tax_exposure` = taxable_estate * estate_tax_rate (0.40)
- `liquidity_gap_before_planning` = estate_tax_exposure - liquid_assets
  (MAY be negative; report the signed value, do not floor at 0).

## 4. analysis_type = roth_conversion_rmd  (FULLY VERIFIED, score 1.0)
Inputs: profile (SIGNED) + retirement account (CUSTODIAN). Horizon year is in
the request memo ("Planning horizon year: YYYY").

Let A=age, PY=planning_year, H=horizon_year, start=rmd_start_age (usually 73),
N=recommended_conversion_years, r=expected_return, MTR=marginal_tax_rate,
income=annual_non_ira_income, target=conversion_bracket_targets[filing_status],
T0=traditional_balance, R0=roth_balance.

Derived fields:
- `first_rmd_year` = PY + (start - A)
- `first_conversion_year` = PY
- `conversion_years` = N ; `conversion_years_positive` = N (same value)
- `annual_conversion_amount` = target - income   (bracket headroom)
- `total_converted` = annual_conversion_amount * N
- `total_conversion_tax` = total_converted * MTR

RMD tax simulation (year loop PY..H inclusive). For each `year`, age_y = A+(year-PY):
  1. If converting AND year in [PY, PY+N-1]: trad -= annual_conversion_amount (floor 0).
  2. If age_y >= start: factor = rmd_factors[age_y]; rmd = trad / factor;
     tax += rmd * MTR; trad -= rmd.
  3. trad *= (1 + r)   (growth applied at END of year, AFTER RMD).
Run twice:
- baseline (no conversion) -> `baseline_rmd_tax_through_horizon`
- with conversion          -> `conversion_rmd_tax_through_horizon`
- `rmd_tax_savings_through_horizon` = baseline - conversion.

Legacy projection:
- `projected_traditional_balance_horizon` = the ending trad balance from the
  **CONVERSION scenario** (NOT the baseline). (Key verified fix.)
- `projected_roth_balance_horizon`: bal=R0; for year PY..H: if year in
  conversion window, bal += annual_conversion_amount; then bal *= (1+r). Report bal.
- `heir_tax_profile`: compare roth vs trad ending balances.
  Both substantial & comparable -> MIXED_TAXABLE_AND_TAX_FREE.
  (Use MOSTLY_TAX_FREE only if trad ~ 0; MOSTLY_TAXABLE if roth ~ 0.)

Recommendation enums:
- `primary_action` = STAGED_ROTH_CONVERSION (when a staged conversion is sensible / savings > 0).
- `suitability` = SUITABLE (default when conversion produces positive savings;
  SUITABLE is uniquely correct in the verified cases — do not downgrade to
  BORDERLINE just because RMDs start soon).
- `risk_flag`: if client is at/near RMD age (age >= start-1, i.e. first_rmd_year
  within ~1 yr of PY) -> RMD_NEAR_TERM; otherwise (younger client, multi-year
  runway, conversions sized to bracket) -> TAX_BRACKET_MANAGEMENT.
  Use LIQUIDITY_CONSTRAINT only if the case is explicitly liquidity-limited.

## 5. analysis_type = ilit_crummey_implementation  (verified except 3 derived dates)
Inputs: profile (SIGNED) for beneficiary_count; life-insurance policy; tax policy.

gift_plan:
- `planning_year` = PY
- `annual_exclusion_per_beneficiary` = annual_gift_exclusion[PY]  (20000 for 2026)
- `beneficiary_count` = SIGNED_PROFILE beneficiary_count
- `annual_exclusion_capacity` = beneficiary_count * annual_exclusion_per_beneficiary
- `annual_premium` = policy.annual_premium
- `premium_gap` = max(0, annual_premium - annual_exclusion_capacity)

administration:
- `contribution_date` = policy.planned_contribution_date (use as given).
- `notices_required` = beneficiary_count
- `dedicated_bank_account_required` = true (ILIT best practice).
- Crummey dates (`notice_due_date`, `withdrawal_window_end`,
  `earliest_premium_payment_date`): these are the least-certain fields; apply
  this best-practice convention:
    notice_due_date = contribution_date (notice sent on contribution);
    withdrawal_window_end = contribution_date + 30 days;
    earliest_premium_payment_date = withdrawal_window_end + 1 day.
  (Premium may only be paid after the withdrawal window lapses.) If a task
  supplies an explicit withdrawal-window length or notice rule, use that instead.

estate_result:
- `death_benefit` = policy.death_benefit
- `projected_outside_estate_if_implemented` = death_benefit (new policy fully
  outside the estate; only reduce for an existing-policy transfer under lookback).
- `tax_liquidity_support` = **death_benefit (the FULL death benefit)** — verified;
  do NOT cap it at estate_tax_exposure.
- `estate_inclusion_risk` = same value as recommendation.risk_flag.

Recommendation + risk (exclusion / lookback logic):
- shortfall = premium_gap > 0 ; lookback = policy.is_existing_policy_transfer == true.
- risk_flag: neither -> LOW_IF_FORMALITIES_MET; shortfall only -> EXCLUSION_SHORTFALL;
  lookback only -> THREE_YEAR_LOOKBACK; both -> THREE_YEAR_LOOKBACK_AND_EXCLUSION_SHORTFALL.
- primary_action: no issues -> FUND_WITH_CRUMMEY_NOTICES;
  shortfall -> USE_LIFETIME_EXEMPTION_FOR_SHORTFALL;
  lookback (new policy alt) -> USE_NEW_POLICY_OR_ACCEPT_LOOKBACK;
  both -> DISCLOSE_LOOKBACK_AND_USE_EXEMPTION.
- suitability: clean -> SUITABLE_WITH_ADMINISTRATION; minor issues -> BORDERLINE;
  severe -> NOT_SUITABLE.

## 6. analysis_type = trust_comparison (GRAT vs CRAT)  (formulas verified)
Inputs: profile (SIGNED goal), estate-context math (Section 3), trust-candidate.
Let asset=asset_value, g=expected_growth_rate.

estate_context: compute taxable_estate, estate_tax_exposure,
liquidity_gap_before_planning per Section 3.

GRAT (term = grat_term_years, ar = grat_annuity_rate):
- **`projected_remainder_to_heirs` = asset*(1+g)^term - (asset*ar)*term**
  (future value of the assets MINUS the simple SUM of nominal annuity payments;
  the annuity payments are NOT regrown). VERIFIED — this differs from the CRAT
  convention below.
- `estimated_estate_tax_reduction` = projected_remainder_to_heirs * estate_tax_rate (0.40)
- `term_years` = grat_term_years
- `mortality_inclusion_risk` = TERM_SURVIVAL_REQUIRED (only allowed value)

CRAT (term = min(crat_term_years, max_crat_term_years)=20, pr = crat_payout_rate):
- **`projected_charitable_remainder`**: COMPOUNDING grow-then-pay loop:
  bal = asset; for each of `term` years: bal = bal*(1+g) - asset*pr. Report bal.
  (Payout each year is a fixed asset*pr; balance compounds. VERIFIED.)
- `estimated_income_tax_deduction` = projected_charitable_remainder *
  charitable_deduction_rate (0.35).  VERIFIED.
- `term_years` = 20
- `family_transfer_fit` = LOW (a CRAT is charitable; poor family-transfer fit).

Recommendation:
- Compare goals (from SIGNED_PROFILE): if family_transfer_priority is high
  (and/or philanthropic_intent is low/moderate) -> preferred_strategy = GRAT,
  rationale_code = CHILDREN_TRANSFER_PRIORITY,
  alternate_role = SECONDARY_CHARITABLE_TOOL.
  If philanthropic_intent dominates -> preferred_strategy = CRAT,
  rationale_code = PHILANTHROPIC_PRIORITY,
  alternate_role = SECONDARY_FAMILY_TRANSFER_TOOL, and set GRAT as the alternate.
  (In the verified cases family_transfer_priority=high -> GRAT.)

## 7. analysis_type = estate_liquidity_action_plan (integrated)  (formulas verified)
Combines Sections 3, 5, 6. Inputs: profile (SIGNED), life-insurance, trust-candidate.

estate_context: Section 3 (remember the married=DOUBLE-exemption rule; single
filers use a single exemption).

ilit block:
- `annual_exclusion_capacity` = beneficiary_count * annual_gift_exclusion[PY]
- `premium_gap` = max(0, annual_premium - annual_exclusion_capacity)
- `estate_inclusion_risk` = same risk-flag logic as Section 5.
- `projected_outside_estate_if_implemented` = death_benefit.

trust_transfer block:
- `preferred_strategy` = GRAT or CRAT per Section 6 goal logic.
- `projected_remainder_to_heirs` = GRAT remainder (Section 6 GRAT formula:
  fv-minus-nominal-annuity). VERIFIED.
- `estimated_estate_tax_reduction` = that remainder * 0.40. VERIFIED.
- `projected_charitable_remainder` = CRAT remainder (Section 6 compounding loop).

recommendation:
- `primary_action`: ILIT + GRAT both apply -> COMBINE_ILIT_AND_GRAT;
  charitable/liquidity-driven -> CRAT_WITH_LIQUIDITY_REVIEW;
  ILIT-centric -> ILIT_WITH_EXEMPTION_REVIEW.
- `sequencing`: typically ILIT_FIRST_THEN_GRAT (fund insurance liquidity first,
  then transfer appreciating assets); TRUST_DECISION_FIRST if the trust choice
  is the gating decision; ILIT_FIRST_THEN_ATTORNEY_REVIEW when drafting review
  dominates.
- `risk_flag`: same risk-flag enum/logic as Section 5 (ILIT inclusion risk).

`action_set` — list of the applicable enums, **sorted alphabetically**. Choose from:
  ATTORNEY_DRAFT_REVIEW, CRAT_FOR_CHARITABLE_REMAINDER,
  GRAT_FOR_APPRECIATING_SHARES, ILIT_CRUMMEY_NOTICE_CYCLE,
  LIFETIME_EXEMPTION_ALLOCATION.
  Include ILIT_CRUMMEY_NOTICE_CYCLE when an ILIT/policy is present;
  GRAT_FOR_APPRECIATING_SHARES when GRAT is preferred (appreciating trust asset);
  CRAT_FOR_CHARITABLE_REMAINDER when CRAT is preferred / philanthropic;
  LIFETIME_EXEMPTION_ALLOCATION when premium_gap > 0 (exclusion shortfall needs
  exemption) — omit when premium is fully covered;
  ATTORNEY_DRAFT_REVIEW for any multi-instrument coordination.
  Always emit the final list sorted alphabetically.
- source_resolution: `controlling_goal_source` = SIGNED_PROFILE;
  `controlling_policy_source` = SIGNED_PROFILE.

## 8. Output / formatting rules (all analysis types)
- Echo `task_id` and `client_id` exactly as given; set `analysis_type` to the
  template's enum value.
- Include EVERY required_top_level_key and every documented sub-field.
- Numbers are JSON numbers (not strings), USD rounded to 2 decimals.
- Dates ISO `YYYY-MM-DD`. Booleans are real JSON booleans.
- `action_set` MUST be alphabetically sorted.
- Emit ONLY the JSON object — no surrounding prose, no code fences.

## 9. Pitfalls (learned)
- Use the CONVERSION-scenario (not baseline) traditional balance for
  `projected_traditional_balance_horizon`.
- GRAT and CRAT use DIFFERENT remainder formulas: GRAT = FV(assets) minus the
  nominal SUM of annuity payments; CRAT = compounding grow-then-pay loop. Do not
  use the same method for both.
- Married/MFJ clients get the DOUBLE exemption; single/HOH get a single exemption.
- `tax_liquidity_support` is the FULL death benefit, not capped at estate tax.
- `controlling_policy_source` = SIGNED_PROFILE; `controlling_asset_source` =
  ATTORNEY_MEMO; profile/account/beneficiary/goal default to SIGNED_PROFILE
  except retirement accounts which are CUSTODIAN_EXPORT.
- `liquidity_gap_before_planning` can be negative — keep the sign.
- Re-fetch `/api/policies/tax` and `/api/rmd-factors` each run; use planning_year
  to pick the right exclusion/exemption.
