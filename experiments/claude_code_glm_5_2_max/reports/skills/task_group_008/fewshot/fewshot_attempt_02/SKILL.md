# Private-Wealth Advisory Solver SOP

Executable procedure for producing the structured planning JSON for an unseen
advisory client. Four analysis types: `roth_conversion_rmd`,
`ilit_crummey_implementation`, `trust_comparison`, `estate_liquidity_action_plan`.

## 0. Inputs / output contract
- Input bundle: `input/prompt.txt` (engagement), `input/payloads/request_memo.md`
  (context + planning horizon), `input/payloads/answer_template.json` (exact schema).
- Output: ONE JSON object conforming to `answer_template.json`. No prose outside
  JSON. Numbers are JSON numbers (not strings). Money rounded to cents. Dates ISO `YYYY-MM-DD`.
- Keep all intermediate math at full float precision; round each numeric OUTPUT
  field independently to 2 decimals (round-half-up) only at the end.

## 1. Remote advisory API workflow
Base URL is in `environment_access.md`. All endpoints are GET, anonymous, no key.
Call in this order so constants are loaded before any calculation:

1. `GET /api/health` — confirm `{"ok": true}`.
2. `GET /api/clients/<client_id>` — base record (age, marital_status, filing_status,
   planning_year, estate_value, liquid_assets).
3. `GET /api/policies/tax` — planning constants:
   `annual_gift_exclusion[year]`, `estate_tax_exemption[year]`, `estate_tax_rate`,
   `conversion_bracket_targets[filing_status]`, `max_crat_term_years`,
   `charitable_deduction_rate`.
4. `GET /api/rmd-factors` — age(string) -> divisor.
5. `GET /api/source-documents?client_id=<id>` — conflicting source docs.
6. `GET /api/retirement-accounts?client_id=<id>` — roth tasks only.
7. `GET /api/life-insurance?client_id=<id>` — ilit / estate tasks.
8. `GET /api/trust-candidates?client_id=<id>` — trust / estate tasks.

Always read constants from `/policies/tax` and `/rmd-factors`; never hardcode.
Each source doc carries `source_type` ∈ {SIGNED_PROFILE, ATTORNEY_MEMO,
CUSTODIAN_EXPORT, CRM_NOTE, STALE_MARKETING_INTAKE}. The data endpoints imply a
source type: `retirement-accounts` -> CUSTODIAN_EXPORT; `trust-candidates` ->
ATTORNEY_MEMO; `life-insurance` policy facts are SIGNED_PROFILE-controlled.

## 2. Source-resolution precedence
Clients have CONFLICTING records (stale CRM import etc.). For every output
`source_resolution` field, pick the controlling source per fact-category using the
"natural authority" source if it provides a value, else fall back along the chain:

| output field | natural-authority source | fallback chain |
|---|---|---|
| `controlling_profile_source` (roth) | SIGNED_PROFILE | ATTORNEY_MEMO -> CUSTODIAN_EXPORT -> CRM_NOTE -> STALE_MARKETING_INTAKE |
| `controlling_account_source` (roth) | CUSTODIAN_EXPORT | SIGNED_PROFILE -> CRM_NOTE |
| `controlling_beneficiary_source` (ilit) | SIGNED_PROFILE | ATTORNEY_MEMO -> CRM_NOTE -> STALE_MARKETING_INTAKE |
| `controlling_policy_source` (ilit/estate) | SIGNED_PROFILE | ATTORNEY_MEMO -> CUSTODIAN_EXPORT -> CRM_NOTE |
| `controlling_goal_source` (trust/estate) | SIGNED_PROFILE | ATTORNEY_MEMO -> CRM_NOTE -> STALE_MARKETING_INTAKE |
| `controlling_asset_source` (trust) | ATTORNEY_MEMO | SIGNED_PROFILE -> CRM_NOTE |

CRITICAL: use the CONTROLLING source's VALUE in every calculation, not just any
source. Example: `annual_non_ira_income` differs between CRM and SIGNED_PROFILE —
use SIGNED_PROFILE's value. `beneficiary_count` likewise. The controlling-source
label you emit must be the one whose value you actually used.

## 3. Cross-cutting rules
- `planning_year` = `client.planning_year` (matches SIGNED facts and memo year).
- Horizon (roth only): scan `request_memo.md` for the literal `Planning horizon year: YYYY`.
  Use that integer as `rmd_projection.horizon_year` and as the inclusive end year of
  every year-by-year projection. If the line is absent, default to `planning_year + 20`.
- `first_rmd_year` (roth) = `planning_year + (rmd_start_age - age)` where age comes
  from the controlling profile (SIGNED_PROFILE) and `rmd_start_age` from the
  retirement account (CUSTODIAN_EXPORT).
- Couple factor for estate exemption: `exemption_used = (marital_status == "married" ? 2 : 1) * estate_tax_exemption[planning_year]`.
- ISO date arithmetic is calendar (not business) days, formatted `YYYY-MM-DD`.
- `action_set` arrays must be sorted alphabetically (plain string sort).
- Heir/asset enums are uppercase tokens exactly as in the template.

## 4. roth_conversion_rmd
Resolve `controlling_profile_source` = SIGNED_PROFILE (age, filing_status,
`annual_non_ira_income`, `marginal_tax_rate`) and `controlling_account_source` =
CUSTODIAN_EXPORT (`traditional_balance`, `roth_balance`, `expected_return`,
`rmd_start_age`, `recommended_conversion_years`).

`conversion_plan`:
- `first_conversion_year` = planning_year.
- `conversion_years` = retirement-account `recommended_conversion_years`.
- `annual_conversion_amount` = `conversion_bracket_targets[filing_status] - annual_non_ira_income` (controlling).
  If `<= 0`, recommendation becomes DEFER/NO_CONVERSION.
- `conversion_years_positive` = number of conversion years with annual amount > 0
  (equals `conversion_years` when the annual amount is positive).
- `total_converted` = `annual_conversion_amount * conversion_years`.
- `total_conversion_tax` = `total_converted * marginal_tax_rate` (controlling).

`rmd_projection`:
- `first_rmd_year` = planning_year + (rmd_start_age - age).
- `horizon_year` = from memo.
- `baseline_rmd_tax_through_horizon`: simulate the traditional balance with NO
  conversion. 
- `conversion_rmd_tax_through_horizon`: same loop but apply the conversion branch.
- `rmd_tax_savings_through_horizon` = baseline - conversion.

Year loop (inclusive `y` from planning_year to horizon_year). `age_y = age + (y - planning_year)`:
1. CONVERSION BRANCH (conversion scenario only): if `y` is in
   `[planning_year, planning_year + conversion_years - 1]`: subtract
   `annual_conversion_amount` from traditional `B` and add it to Roth `R` (done at
   the START of the year, before growth and before any RMD).
2. RMD: if `age_y >= rmd_start_age`,
   `rmd = B / rmd_factors[str(age_y)]`; `rmd_tax = rmd * marginal_tax_rate`;
   `B -= rmd`. (RMD taken at START of year, before growth.) Accumulate `rmd_tax`
   into the matching scenario total (`baseline_rmd_tax` for the no-conversion run,
   `conversion_rmd_tax` for the conversion run).
3. GROW: `B *= (1 + expected_return)`; in the conversion scenario also `R *= (1 + expected_return)`.

Run the loop twice: baseline omits step 1 (and Roth is irrelevant there).
`conversion_rmd_tax_through_horizon` counts RMDs in EVERY RMD year, including years
that are also conversion years and years after conversions end.

`legacy_projection` (all from the CONVERSION scenario run):
- `projected_traditional_balance_horizon` = `B` at end of horizon.
- `projected_roth_balance_horizon` = `R` at end of horizon (starts from the
  account's existing `roth_balance`, receives conversions, grows at `expected_return`).
- `heir_tax_profile`: `MIXED_TAXABLE_AND_TAX_FREE` when both projected balances are
  material (> 0); `MOSTLY_TAX_FREE` when traditional is depleted (~0) while Roth
  remains; `MOSTLY_TAXABLE` when Roth is ~0 while traditional remains.

`recommendation`: `primary_action` = STAGED_ROTH_CONVERSION when the annual amount
is positive; `suitability` = SUITABLE (BORDERLINE if conversion window or liquidity
is tight); `risk_flag` = TAX_BRACKET_MANAGEMENT normally, RMD_NEAR_TERM when the
conversion window is <= 0 years, LIQUIDITY_CONSTRAINT when `liquid_assets <
total_conversion_tax`.

## 5. ilit_crummey_implementation
`controlling_beneficiary_source` = SIGNED_PROFILE, `controlling_policy_source` =
SIGNED_PROFILE. Pull policy facts from `life-insurance`, beneficiary count from
SIGNED_PROFILE.

`gift_plan`:
- `planning_year` = client planning_year.
- `annual_exclusion_per_beneficiary` = `annual_gift_exclusion[planning_year]`.
- `beneficiary_count` = SIGNED_PROFILE `beneficiary_count`.
- `annual_exclusion_capacity` = `annual_exclusion_per_beneficiary * beneficiary_count`.
- `annual_premium` = life-insurance `annual_premium`.
- `premium_gap` = `max(0, annual_premium - annual_exclusion_capacity)`.

`administration`:
- `notices_required` = `beneficiary_count` (one Crummey notice per beneficiary).
- `contribution_date` = life-insurance `planned_contribution_date`.
- `notice_due_date` = `contribution_date + 7 days`.
- `withdrawal_window_end` = `notice_due_date + 30 days`.
- `earliest_premium_payment_date` = `withdrawal_window_end + 1 day`.
- `dedicated_bank_account_required` = true.

`estate_result`:
- `death_benefit` = life-insurance `death_benefit`.
- `estate_inclusion_risk` = risk flag (see below).
- `projected_outside_estate_if_implemented` = `death_benefit`.
- `tax_liquidity_support` = `death_benefit * estate_tax_rate`.

Risk flag (from `is_existing_policy_transfer` and `premium_gap`):
- new policy + gap 0 -> `LOW_IF_FORMALITIES_MET`
- new policy + gap > 0 -> `EXCLUSION_SHORTFALL`
- existing transfer + gap 0 -> `THREE_YEAR_LOOKBACK`
- existing transfer + gap > 0 -> `THREE_YEAR_LOOKBACK_AND_EXCLUSION_SHORTFALL`

`recommendation` mapping (by the same two inputs):
- new + gap 0 -> `FUND_WITH_CRUMMEY_NOTICES` / `SUITABLE_WITH_ADMINISTRATION`
- new + gap > 0 -> `USE_LIFETIME_EXEMPTION_FOR_SHORTFALL` / `BORDERLINE`
- existing + gap 0 -> `USE_NEW_POLICY_OR_ACCEPT_LOOKBACK` / `BORDERLINE`
- existing + gap > 0 -> `DISCLOSE_LOOKBACK_AND_USE_EXEMPTION` / `NOT_SUITABLE`
`risk_flag` copies the risk-flag token above.

## 6. trust_comparison
`controlling_goal_source` = SIGNED_PROFILE (`family_transfer_priority`,
`philanthropic_intent`); `controlling_asset_source` = ATTORNEY_MEMO
(trust-candidates: `asset_value`, `expected_growth_rate`, `grat_term_years`,
`grat_annuity_rate`, `crat_term_years`, `crat_payout_rate`).

`estate_context`:
- `planning_year` = client planning_year.
- `exemption_used` = couple factor (Section 3) * `estate_tax_exemption[planning_year]`.
- `taxable_estate` = controlling `estate_value` - `exemption_used`.
- `estate_tax_exposure` = `taxable_estate * estate_tax_rate`.
- `liquid_assets_available` = controlling `liquid_assets`.
- `liquidity_gap_before_planning` = `max(0, estate_tax_exposure - liquid_assets_available)`.

`grat`:
- `term_years` = `grat_term_years`.
- annuity_payment = `asset_value * grat_annuity_rate`.
- remainder_unrounded = `asset_value * (1 + expected_growth_rate) ** grat_term_years - annuity_payment * grat_term_years`.
- `projected_remainder_to_heirs` = `round(remainder_unrounded, 2)`.
- `estimated_estate_tax_reduction` = `round(remainder_unrounded * estate_tax_rate, 2)`
  (use the UNROUNDED remainder, then round once).
- `mortality_inclusion_risk` = `TERM_SURVIVAL_REQUIRED`.

`crat`:
- `term_years` = `crat_term_years` (<= `max_crat_term_years`).
- annuity_payment = `asset_value * crat_payout_rate`.
- charitable_unrounded = `asset_value * (1 + expected_growth_rate) ** crat_term_years - annuity_payment * crat_term_years`.
- `projected_charitable_remainder` = `round(charitable_unrounded, 2)`.
- `estimated_income_tax_deduction` = `round(charitable_unrounded * charitable_deduction_rate, 2)`.
- `family_transfer_fit` = `LOW` (CRAT remainder passes to charity).

`recommendation` (drive from controlling goals):
- If SIGNED `family_transfer_priority == "high"` (and >= philanthropic_intent) ->
  `preferred_strategy` = GRAT, `rationale_code` = CHILDREN_TRANSFER_PRIORITY,
  `alternate_role` = SECONDARY_CHARITABLE_TOOL.
- If SIGNED `philanthropic_intent == "high"` (and > family_transfer_priority) ->
  `preferred_strategy` = CRAT, `rationale_code` = PHILANTHROPIC_PRIORITY,
  `alternate_role` = SECONDARY_FAMILY_TRANSFER_TOOL.
- When both are equal/non-high, prefer GRAT (children transfer).

## 7. estate_liquidity_action_plan
`controlling_goal_source` = SIGNED_PROFILE; `controlling_policy_source` = SIGNED_PROFILE.

`estate_context`: same formulas as trust_comparison (couple factor for exemption).

`ilit`:
- `annual_exclusion_capacity` = `annual_gift_exclusion[planning_year] * SIGNED beneficiary_count`.
- `premium_gap` = `max(0, life-insurance annual_premium - annual_exclusion_capacity)`.
- `estate_inclusion_risk` = ILIT risk flag (Section 5).
- `projected_outside_estate_if_implemented` = `life-insurance death_benefit`.

`trust_transfer` (always compute BOTH vehicles; strategy only labels the pick):
- `preferred_strategy` = GRAT/CRAT per the Section 6 goal rule.
- `projected_remainder_to_heirs` = GRAT remainder (Section 6 formula, always).
- `estimated_estate_tax_reduction` = `round(GRAT remainder_unrounded * estate_tax_rate, 2)`.
- `projected_charitable_remainder` = CRAT charitable remainder (Section 6 formula, always).

`recommendation`:
- `primary_action`: COMBINE_ILIT_AND_GRAT when ILIT is fundable (premium_gap == 0,
  new policy) and preferred_strategy == GRAT; CRAT_WITH_LIQUIDITY_REVIEW when
  preferred_strategy == CRAT; ILIT_WITH_EXEMPTION_REVIEW when premium_gap > 0.
- `sequencing`: ILIT_FIRST_THEN_GRAT (COMBINE_ILIT_AND_GRAT) /
  TRUST_DECISION_FIRST (CRAT_WITH_LIQUIDITY_REVIEW) /
  ILIT_FIRST_THEN_ATTORNEY_REVIEW (ILIT_WITH_EXEMPTION_REVIEW).
- `risk_flag` = ILIT risk flag (Section 5).

`action_set` — build from these membership rules, then SORT ALPHABETICALLY:
- `ATTORNEY_DRAFT_REVIEW`: always include.
- `ILIT_CRUMMEY_NOTICE_CYCLE`: include if ILIT funded via Crummey (premium_gap == 0 and new policy).
- `LIFETIME_EXEMPTION_ALLOCATION`: include if `premium_gap > 0`.
- `GRAT_FOR_APPRECIATING_SHARES`: include if `preferred_strategy == GRAT`.
- `CRAT_FOR_CHARITABLE_REMAINDER`: include if `preferred_strategy == CRAT`.

## 8. Common mistakes to avoid
- Letting a stale CRM_NOTE value win for `annual_non_ira_income` or
  `beneficiary_count` — SIGNED_PROFILE controls those; using CRM's number shifts the
  annual conversion amount and every downstream figure.
- Wrong horizon: ignoring the memo's `Planning horizon year:` line, or using
  planning_year + a fixed offset instead of the stated year. The horizon is the
  inclusive last projected year.
- Off-by-one in conversion years: conversion years span
  `[planning_year, planning_year + conversion_years - 1]`; do not subtract an extra
  year or stop at RMD start when `recommended_conversion_years` exceeds the gap to RMD.
- RMD/growth ordering: RMD is taken at the START of the year (before growth); growing
  first then taking RMD produces different (wrong) tax and balance totals.
- Forgetting that RMDs still occur during conversion years and after conversions end
  in the conversion scenario.
- Rounding `estimated_estate_tax_reduction` from the already-rounded remainder
  instead of the unrounded remainder (loses/raises a cent).
- `estate_tax_exposure` using the estate_tax_rate from memory — always pull
  `estate_tax_rate` (0.40) and `charitable_deduction_rate` (0.35) from `/api/policies/tax`.
- `action_set` not sorted alphabetically, or omitting `ATTORNEY_DRAFT_REVIEW`.
- Non-ISO dates (use `YYYY-MM-DD`), or business-day instead of calendar-day arithmetic
  for the Crummey notice/withdrawal/premium dates.
- Reporting baseline-scenario balances for `legacy_projection` — both
  `projected_*_balance_horizon` values come from the CONVERSION scenario.
- Using single exemption when the client is married (couple = 2x exemption), or vice versa.
