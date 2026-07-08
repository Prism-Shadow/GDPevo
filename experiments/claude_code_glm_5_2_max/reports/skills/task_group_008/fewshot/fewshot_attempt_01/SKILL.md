# Private-Wealth Advisory Solver SKILL

Executable SOP for producing a single JSON planning object for an unseen private-wealth
client. The remote advisory API is the single source of truth; do not invent numbers.

## 0. Golden rules (always)
1. Output is ONE JSON object only, conforming to the task's `answer_template.json`. No prose.
2. All USD numbers are JSON numbers rounded to cents (2 decimals). Years are integers.
   Dates are ISO `YYYY-MM-DD`. Booleans are `true`/`false`.
3. Never call any judge/evaluator endpoint. Never read `env/`, `task_group/`, `runs/`, or
   other attempts. Use only the remote API below + the task's own `input/` payload.
4. `task_id` and `client_id` come from the task itself (memo + prompt); never hardcode train ids.

## 1. Remote API workflow
Base URL: `<remote-env-url>` (from `environment_access.md`). All endpoints are GET.

Call in this order; fetch client + sources + policy + factors first, then only the
domain endpoints the analysis type needs:
1. `GET /api/health` — confirm `{"ok": true}`.
2. `GET /api/clients/<client_id>` — base record (birth_year, heirs, age).
3. `GET /api/source-documents?client_id=<id>` — the conflicting sources (CRM_NOTE,
   ATTORNEY_MEMO, CUSTODIAN_EXPORT, SIGNED_PROFILE, STALE_MARKETING_INTAKE). This drives
   every `source_resolution` field.
4. `GET /api/policies/tax` — planning constants: `planning_year`, `estate_tax_rate`,
   `marginal_tax_rate` (used for conversion tax AND RMD tax), `income_tax_deduction_rate` /
   `section_7520_rate`, `growth_rate`, `rmd_start_age`, `annual_gift_exclusion`, bracket
   thresholds. Current-environment values: planning_year 2026, estate_tax_rate 0.40,
   marginal_tax_rate 0.32, income/7520 ~0.35 (5.39%), rmd_start_age 73, gift exclusion 20000.
   Re-read each run; do not assume.
5. `GET /api/rmd-factors` — age -> divisor table (roth/RMD tasks only).
6. `GET /api/retirement-accounts?client_id=<id>` — traditional + Roth balances, staged
   conversion parameters (roth tasks).
7. `GET /api/life-insurance?client_id=<id>` — ILIT policy, death benefit, premium,
   beneficiaries, owner, issue/transfer date (ilit + estate_liquidity tasks).
8. `GET /api/trust-candidates?client_id=<id>` — GRAT/CRAT candidate terms, funding asset,
   post-liquidity-event asset composition (trust_comparison + estate_liquidity tasks).

Engagement keyword -> `analysis_type`: "Roth conversion"/"RMD" -> `roth_conversion_rmd`;
"ILIT"/"Crummey" -> `ilit_crummey_implementation`; "GRAT versus CRAT" -> `trust_comparison`;
"estate liquidity action plan" -> `estate_liquidity_action_plan`.

## 2. Source-resolution precedence
The API returns CONFLICTING source docs imported from different systems. The controlling
source is chosen PER OUTPUT FIELD by the fact-type that field depends on, using this
fact-specific precedence (highest wins; fall to the next only if the higher source is
silent on that fact):

- Client-stated facts (identity, age/birth_year, beneficiary list, planning goals,
  policy elections, conversion intent): `SIGNED_PROFILE` > `ATTORNEY_MEMO` >
  `CUSTODIAN_EXPORT` > `CRM_NOTE` > `STALE_MARKETING_INTAKE`.
- Account/balance facts (IRA/Roth balances, account values): `CUSTODIAN_EXPORT` >
  `SIGNED_PROFILE` > `CRM_NOTE` > `STALE_MARKETING_INTAKE`. The custodian is the system
  of record for balances; never let a CRM note or marketing intake override it.
- Legal/asset-composition facts (estate asset list, trust funding asset, post-liquidity-
  event holdings, exemption used): `ATTORNEY_MEMO` > `SIGNED_PROFILE` > `CRM_NOTE`
  > `STALE_MARKETING_INTAKE`. Counsel's memo governs the legal state of assets.

Map the `source_resolution` block by analysis type:
- roth_conversion_rmd: `controlling_profile_source` (identity/age/heirs) -> SIGNED_PROFILE;
  `controlling_account_source` (balances) -> CUSTODIAN_EXPORT.
- ilit_crummey_implementation: `controlling_beneficiary_source` -> SIGNED_PROFILE;
  `controlling_policy_source` -> SIGNED_PROFILE (policy elections are client-attested).
- trust_comparison: `controlling_goal_source` (transfer vs philanthropic) -> SIGNED_PROFILE;
  `controlling_asset_source` (estate/trust asset composition) -> ATTORNEY_MEMO.
- estate_liquidity_action_plan: `controlling_goal_source` -> SIGNED_PROFILE;
  `controlling_policy_source` -> SIGNED_PROFILE.

STALE_MARKETING_INTAKE should essentially never win; it only appears in the enum for the
case where it is the sole source of a fact.

## 3. Shared computations
- `planning_year` = tax policy `planning_year` (2026). It is `first_conversion_year`,
  `gift_plan.planning_year`, and `estate_context.planning_year`.
- `estate_tax_exposure` = `taxable_estate` × `estate_tax_rate` (0.40). `taxable_estate`,
  `exemption_used`, `liquid_assets_available` come from the controlling asset/goal source.
- `liquidity_gap_before_planning` = `max(0, estate_tax_exposure − liquid_assets_available)`.
  Floor at 0; a surplus of liquid assets is not a negative gap.
- ILIT/GRAT `estimated_estate_tax_reduction` = `projected_remainder_to_heirs` ×
  `estate_tax_rate` (0.40).
- CRAT `estimated_income_tax_deduction` = `projected_charitable_remainder` ×
  `(1 + section_7520_rate)^(−crat_term_years)` (discount the projected charitable
  remainder at the 7520 rate over the CRAT term). For a 20-year CRAT at the current 7520
  rate this factor is ~0.35.
- `tax_liquidity_support` (ILIT) = `death_benefit` × `estate_tax_rate` (0.40).
- `premium_gap` = `max(0, annual_premium − annual_exclusion_capacity)`. Not the reverse.

## 4. roth_conversion_rmd
Inputs: CUSTODIAN_EXPORT balances (traditional `trad_0`, Roth `roth_0`), client birth_year,
tax policy (growth_rate g, marginal_tax_rate m=0.32, rmd_start_age=73), rmd-factors table,
staged-conversion record (annual amount + term/end-year).

- `first_conversion_year` = planning_year.
- `first_rmd_year` = `birth_year + rmd_start_age` (year client turns RMD age; not the
  following year, not the April-1 deferral year).
- `conversion_years`: the staged-conversion window. Prefer the conversion term/end-year in
  the client's retirement-account / signed-profile record. If the record expresses a full
  pre-RMD window, `conversion_years = first_rmd_year − first_conversion_year` (conversions
  occupy `[first_conversion_year, first_rmd_year − 1]`). For near-RMD clients the record
  may specify a fixed staging window that extends a few years PAST first RMD; use that
  recorded term. **Off-by-one trap:** the count is `first_rmd_year − first_conversion_year`,
  not `− 1`. Conversions do not include the first RMD year when using the pre-RMD window.
- `annual_conversion_amount` = headroom in the client's target marginal bracket for the
  planning year (target bracket ceiling − projected non-conversion taxable income), from
  the policy brackets + client income. Keeps the conversion taxed at `m`.
- `total_converted` = `annual_conversion_amount × conversion_years`.
- `total_conversion_tax` = `total_converted × m` (0.32).
- `conversion_years_positive` = `conversion_years` when `annual_conversion_amount > 0`,
  else 0 (count of years with a positive conversion).
- `horizon_year` = the "Planning horizon year" line in the request memo (see §8).

RMD projection (year loop y = planning_year .. horizon_year):
- Baseline: `trad` starts at `trad_0`. If `y >= first_rmd_year`: `factor = rmd_factors[age_y]`,
  `rmd = trad_prev / factor`, `tax += rmd × m`, `trad = trad_prev × (1+g) − rmd`. Else
  `trad = trad_prev × (1+g)`. `baseline_rmd_tax_through_horizon` = round(sum, 2).
- Conversion: same loop but in each conversion year subtract `annual_conversion_amount`
  from `trad` and add it to `roth` (then grow); RMDs computed on the reduced `trad`.
  `conversion_rmd_tax_through_horizon` = round(sum, 2).
- `rmd_tax_savings_through_horizon` = round(baseline − conversion, 2).
- `projected_traditional_balance_horizon` = round(`trad` at horizon, 2).
- `projected_roth_balance_horizon` = round(`roth` at horizon, 2) (conversions + existing
  Roth grown at `g`).
- `heir_tax_profile`: R = roth horizon, T = trad horizon, total = R+T. If `R/total > 0.75`
  -> `MOSTLY_TAX_FREE`; elif `T/total > 0.75` -> `MOSTLY_TAXABLE`; else
  `MIXED_TAXABLE_AND_TAX_FREE`.
- Recommendation: staged conversion viable -> `STAGED_ROTH_CONVERSION` / `SUITABLE` /
  `TAX_BRACKET_MANAGEMENT`. Use `RMD_NEAR_TERM` only when first RMD is within ~1-2 years and
  the staging window is constrained.

## 5. ilit_crummey_implementation
- `annual_exclusion_per_beneficiary` = tax policy `annual_gift_exclusion` (20000).
- `beneficiary_count` = Crummey beneficiaries from SIGNED_PROFILE. `notices_required` =
  `beneficiary_count` (one notice per beneficiary).
- `annual_exclusion_capacity` = `annual_exclusion_per_beneficiary × beneficiary_count`.
- `annual_premium` = ILIT policy premium (life-insurance record, SIGNED_PROFILE-controlled).
- `premium_gap` = `max(0, annual_premium − annual_exclusion_capacity)`.
- `dedicated_bank_account_required` = true (always for an ILIT gift cycle).
- Crummey date arithmetic (real calendar dates, ISO output):
  - `contribution_date`: planned gift date from the trust/policy record.
  - `notice_due_date` = `contribution_date + 7 days`.
  - `withdrawal_window_end` = `notice_due_date + 30 days` (the 30-day withdrawal right).
  - `earliest_premium_payment_date` = `withdrawal_window_end + 1 day` (pay the premium only
    after withdrawal rights expire).
- Estate result: `death_benefit` from policy; `projected_outside_estate_if_implemented` =
  `death_benefit` (full benefit outside estate when ILIT owns the policy and no incidents of
  ownership retained); `tax_liquidity_support` = `death_benefit × estate_tax_rate` (0.40).
- Risk mapping: new ILIT-owned policy with `premium_gap == 0` ->
  `FUND_WITH_CRUMMEY_NOTICES` / `SUITABLE_WITH_ADMINISTRATION` / `LOW_IF_FORMALITIES_MET`.
  `premium_gap > 0` -> `USE_LIFETIME_EXEMPTION_FOR_SHORTFALL`, `EXCLUSION_SHORTFALL`.
  Existing policy transferred within 3 years -> add `THREE_YEAR_LOOKBACK` (use
  `THREE_YEAR_LOOKBACK_AND_EXCLUSION_SHORTFALL` if also a gap); action
  `DISCLOSE_LOOKBACK_AND_USE_EXEMPTION`. Determine lookback from the policy issue/transfer
  date vs planning_year.

## 6. trust_comparison (GRAT vs CRAT)
- `estate_context`: `exemption_used`, `taxable_estate`, `liquid_assets_available` from
  ATTORNEY_MEMO (asset source). `estate_tax_exposure` = `taxable_estate × 0.40`;
  `liquidity_gap_before_planning` = `max(0, exposure − liquid_assets)`.
- `grat.term_years` and `crat.term_years` from the trust-candidates record.
- `grat.projected_remainder_to_heirs`: project the funding asset at expected growth over the
  GRAT term, subtract the grantor's annuity/hurdle return (zeroed-out GRAT at the section
  7520 hurdle); the excess appreciation is the remainder to heirs.
- `grat.estimated_estate_tax_reduction` = `projected_remainder_to_heirs × 0.40`.
- `grat.mortality_inclusion_risk` = `TERM_SURVIVAL_REQUIRED` (GRAT assets return to the
  estate if the grantor dies during the term — always this enum).
- `crat.projected_charitable_remainder`: projected value going to charity over the CRAT term.
- `crat.estimated_income_tax_deduction` = `projected_charitable_remainder ×
  (1+section_7520_rate)^(−crat_term_years)` (PV of the charitable remainder at the 7520 rate).
- `crat.family_transfer_fit` = `LOW` for a CRAT (charitable remainder; family gets only the
  income stream). `MODERATE`/`HIGH` only in unusual income-focused cases.
- Recommendation: goal source = SIGNED_PROFILE. If goal prioritizes family transfer ->
  `preferred_strategy` `GRAT`, `rationale_code` `CHILDREN_TRANSFER_PRIORITY`,
  `alternate_role` `SECONDARY_CHARITABLE_TOOL`. If philanthropic priority -> `CRAT`,
  `PHILANTHROPIC_PRIORITY`, `SECONDARY_FAMILY_TRANSFER_TOOL`.

## 7. estate_liquidity_action_plan
- `estate_context`: same as §6 (ATTORNEY_MEMO assets, SIGNED_PROFILE goal);
  `estate_tax_exposure = taxable_estate × 0.40`; `liquidity_gap = max(0, exposure − liquid)`.
- `ilit`: `annual_exclusion_capacity` = `gift_exclusion × beneficiary_count`;
  `premium_gap = max(0, premium − capacity)`; `estate_inclusion_risk` from the same risk
  mapping as §5; `projected_outside_estate_if_implemented` = `death_benefit`.
- `trust_transfer`: `preferred_strategy` GRAT/CRAT per goal source (same rule as §6).
  `projected_remainder_to_heirs` (GRAT remainder) and `estimated_estate_tax_reduction`
  (= remainder × 0.40) per §6. `projected_charitable_remainder` = the CRAT alternative's
  charitable remainder (include for comparison even when GRAT is preferred).
- Recommendation: when both an ILIT and a GRAT candidate exist and the goal is family
  transfer -> `primary_action` `COMBINE_ILIT_AND_GRAT`, `sequencing` `ILIT_FIRST_THEN_GRAT`.
  ILIT-only liquidity focus -> `ILIT_WITH_EXEMPTION_REVIEW` / `ILIT_FIRST_THEN_ATTORNEY_REVIEW`.
  Philanthropic goal -> `CRAT_WITH_LIQUIDITY_REVIEW` / `TRUST_DECISION_FIRST`. `risk_flag`
  mirrors the ILIT risk assessment (§5).
- `action_set` construction (then SORT ALPHABETICALLY):
  - `ATTORNEY_DRAFT_REVIEW` when attorney drafting/coordination is needed (include whenever
    a trust is created).
  - `ILIT_CRUMMEY_NOTICE_CYCLE` when the ILIT path is `FUND_WITH_CRUMMEY_NOTICES`
    (premium within capacity).
  - `GRAT_FOR_APPRECIATING_SHARES` when `preferred_strategy` = GRAT.
  - `CRAT_FOR_CHARITABLE_REMAINDER` when `preferred_strategy` = CRAT.
  - `LIFETIME_EXEMPTION_ALLOCATION` ONLY when `premium_gap > 0` (exclusion shortfall). Do
    NOT include it when `premium_gap == 0`.
  - Sort the resulting string list with a standard ascending string compare.

## 8. Reading the request memo
- `client_id`: the `Client ID: CLT-XXXX` line.
- `analysis_type`: from the `Engagement:` line keywords (§1).
- `planning_year`: not always in the memo; use the tax-policy `planning_year` (2026).
- Planning horizon (roth/RMD tasks): find the literal line `Planning horizon year: YYYY`
  and use that exact year as `rmd_projection.horizon_year`. If absent, parse "through YYYY"
  in the prose. Do NOT substitute planning_year or planning_year+20 when the memo states a
  horizon. The horizon is the RMD-projection end year, not the conversion window end.

## 9. Common mistakes / exclusions
- Letting a CRM_NOTE or STALE_MARKETING_INTAKE balance/beneficiary win over CUSTODIAN_EXPORT
  / SIGNED_PROFILE.
- Wrong `first_rmd_year` (using birth_year+75, or the April-1 deferral year). It is
  `birth_year + rmd_start_age` (73).
- Off-by-one `conversion_years`: using `first_rmd_year − first_conversion_year − 1`, or
  running conversions through the first RMD year when the record gives a pre-RMD window.
- `first_conversion_year` set to a future/RMD year; it is always `planning_year`.
- Wrong `horizon_year` (using planning_year, or memo horizon + 1).
- `premium_gap` computed as `capacity − premium`; un-floored `liquidity_gap` (negative).
- `estimated_estate_tax_reduction` / `tax_liquidity_support` not equal to base × 0.40.
- ILIT dates not ISO, or computed with month-arithmetic instead of real calendar days.
- `action_set` not sorted alphabetically; including `LIFETIME_EXEMPTION_ALLOCATION` when
  `premium_gap == 0`; including a CRAT action when GRAT is preferred (or vice versa).
- Picking CRAT when the goal is family transfer, or GRAT when philanthropic.
- Emitting numbers as strings, missing cents rounding, or extra prose outside the JSON.
- Hardcoding a train `task_id`/`client_id`; use the task's own identifiers.

## 10. Output formatting
Emit exactly one top-level JSON object matching `answer_template.json`'s required keys.
Numbers are JSON numbers with 2-decimal USD (e.g. `1467200.0`), years are bare integers,
dates are `YYYY-MM-DD` strings, booleans are JSON booleans. `action_set` (estate_liquidity)
must be sorted alphabetically; no other ordering is scored. No trailing prose, no markdown
fences.
