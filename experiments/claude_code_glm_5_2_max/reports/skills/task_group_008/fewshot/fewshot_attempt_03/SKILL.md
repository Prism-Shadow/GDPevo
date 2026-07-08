# Private-Wealth Advisory Solver SOP

Executable procedure for producing the single JSON object each engagement asks for.
Inputs per task: `input/prompt.txt`, `input/payloads/request_memo.md`,
`input/payloads/answer_template.json`. Return ONLY a JSON object conforming to the
template — no prose. All USD numbers are JSON numbers rounded to cents; all dates are
ISO `YYYY-MM-DD`.

## 1. Remote API workflow

Base URL: `<remote-env-url>` (the harness may expose it as `API_BASE`; prefer
`$API_BASE` when set, otherwise the URL above). Use only this remote API.

Endpoint call order (GET, all take `client_id` except where noted):
1. `GET /api/health` -> sanity check `{"ok": true}`.
2. `GET /api/clients/<client_id>` -> base record: `age`, `marital_status`,
   `filing_status`, `planning_year`, `estate_value`, `liquid_assets`.
3. `GET /api/source-documents?client_id=<id>` -> the CONFLICTING docs (each has
   `source_type` in {`CRM_NOTE`, `ATTORNEY_MEMO`, `SIGNED_PROFILE`,
   `STALE_MARKETING_INTAKE`} plus `effective_date` and a `facts` map).
4. `GET /api/retirement-accounts?client_id=<id>` -> retirement account(s), each tagged
   `source_type: CUSTODIAN_EXPORT`: `traditional_balance`, `roth_balance`,
   `expected_return`, `rmd_start_age`, `recommended_conversion_years`.
5. `GET /api/life-insurance?client_id=<id>` -> proposed ILIT policy: `death_benefit`,
   `annual_premium`, `planned_contribution_date`, `is_existing_policy_transfer`.
6. `GET /api/trust-candidates?client_id=<id>` -> one trust case: `asset_value`,
   `expected_growth_rate`, `grat_term_years`, `grat_annuity_rate`, `crat_term_years`,
   `crat_payout_rate`.
7. `GET /api/policies/tax` -> constants (see §3).
8. `GET /api/rmd-factors` -> `{age: divisor}` (73->26.5, 74->25.5, ... 99->6.8).

Only fetch endpoints the analysis type needs, but always fetch `clients`,
`source-documents`, and the relevant detail endpoint(s).

## 2. Reading the engagement & planning horizon

- `analysis_type`: determined by the memo engagement line. Four types:
  `roth_conversion_rmd`, `ilit_crummey_implementation`, `trust_comparison`,
  `estate_liquidity_action_plan`.
- `planning_year`: take from the client base record / signed profile (e.g. 2026). It is
  the base year for conversions, estate context, and contribution dates.
- RMD horizon (roth only): parse the request memo for the literal
  `Planning horizon year: YYYY` (or a `... through YYYY` phrase). That year is
  `rmd_projection.horizon_year` and the RMD simulation runs through it inclusive. The
  other three analysis types have no horizon concept.
- `task_id`, `client_id`: copy from the prompt/template verbatim.

## 3. Tax / policy constants (`/api/policies/tax`)

- `annual_gift_exclusion` keyed by year; use the entry for `planning_year`
  (per-beneficiary Crummey exclusion).
- `estate_tax_exemption` keyed by year; use the entry for `planning_year`.
- `estate_tax_rate` (e.g. 0.40).
- `conversion_bracket_targets` keyed by `filing_status` (MFJ/SINGLE/HOH) -> the
  taxable-income ceiling to fill with conversions each year.
- `max_crat_term_years` (e.g. 20) and `charitable_deduction_rate` (e.g. 0.35).

## 4. Source-resolution precedence

Conflict resolution is by FACT-FAMILY AUTHORITY, not a single global ranking. For each
family, the AUTHORITY source type controls both the value used and the reported
`source_resolution` field; if the authority is absent for a client, fall back by the
precedence chain `SIGNED_PROFILE > ATTORNEY_MEMO > CUSTODIAN_EXPORT > CRM_NOTE >
STALE_MARKETING_INTAKE` (STALE_MARKETING_INTAKE is always lowest; treat it as
unreliable).

Authority by family:
- Personal profile, beneficiary count, planning goals (`family_transfer_priority`,
  `philanthropic_intent`), `annual_non_ira_income`, `marginal_tax_rate`, `age`,
  `planning_year`, filing/marital status, `liquid_assets` -> **SIGNED_PROFILE**
  (fall back to ATTORNEY_MEMO, then CRM_NOTE).
- Retirement-account balances, `expected_return`, `rmd_start_age`,
  `recommended_conversion_years` -> **CUSTODIAN_EXPORT** (these come from
  `/api/retirement-accounts`, whose records are tagged CUSTODIAN_EXPORT).
- Estate / trust-asset valuation (`estate_value`, trust `asset_value`,
  GRAT/CRAT assumptions) -> **ATTORNEY_MEMO** (the attorney memo is the estate/trust
  valuation authority; fall back to SIGNED_PROFILE, then CRM_NOTE).
- Insurance policy terms (`death_benefit`, `annual_premium`,
  `planned_contribution_date`, `is_existing_policy_transfer`) -> **SIGNED_PROFILE**
  (the policy is authorized under the signed engagement; values are read from
  `/api/life-insurance`).

Reported `source_resolution` (fields depend on analysis type):
- roth: `controlling_profile_source` = SIGNED_PROFILE,
  `controlling_account_source` = CUSTODIAN_EXPORT.
- ilit: `controlling_beneficiary_source` = SIGNED_PROFILE,
  `controlling_policy_source` = SIGNED_PROFILE.
- trust_comparison: `controlling_goal_source` = SIGNED_PROFILE,
  `controlling_asset_source` = ATTORNEY_MEMO.
- estate_liquidity: `controlling_goal_source` = SIGNED_PROFILE,
  `controlling_policy_source` = SIGNED_PROFILE.

## 5. Common calculation conventions

- Round every USD output to cents (round half up) as the LAST step; for derived
  products (e.g. estate-tax-reduction = remainder * rate), compute from the UNROUNDED
  intermediate, then round.
- Growth: compound annually as `(1+rate)**years` (use full float precision, do not
  round intermediate powers).
- Dates: ISO `YYYY-MM-DD`; use true calendar-day arithmetic (Python `date + timedelta`).
- `marginal_tax_rate` (SIGNED_PROFILE) is the tax rate applied to conversions AND to
  each year's RMD amount.

## 6. Analysis A — `roth_conversion_rmd`

Inputs: `/retirement-accounts` (T0=`traditional_balance`, R0=`roth_balance`, `r`=
`expected_return`, `rmd_start_age`, `conv_years`=`recommended_conversion_years`),
SIGNED_PROFILE (`mtr`, `inc`=`annual_non_ira_income`, `age0`=`age`,
`filing_status`), `/policies/tax` bracket target, `/rmd-factors`, memo horizon.

Conversion plan:
- `first_conversion_year` = `planning_year`.
- `conversion_years` = `conv_years` (CUSTODIAN_EXPORT).
- `annual_conversion_amount` = `max(0, bracket_target[filing_status] - inc)`
  (flat each year; income does NOT grow).
- `conversion_years_positive` = count of conversion years with a positive amount
  (capped by remaining balance; equals `conversion_years` when bracket > income and
  balance suffices).
- `total_converted` = `annual_conversion_amount * conversion_years_positive`.
- `total_conversion_tax` = `total_converted * mtr`.
- `first_rmd_year` = `planning_year + (rmd_start_age - age0)`
  (age0 is the client's age IN the planning year).

Year-by-year RMD projection (loop `y` from `planning_year` through `horizon`
INCLUSIVE; `age = age0 + (y - planning_year)`):

BASELINE (no conversion): `trad = T0`; `base_tax = 0`.
```
for each y:
    if y >= first_rmd_year:
        rmd_amt = trad / rmd_factor[age]
        base_tax += rmd_amt * mtr
        trad = (trad - rmd_amt) * (1 + r)
    else:
        trad = trad * (1 + r)
```
CONVERSION scenario: `trad = T0`; `roth = R0`; `conv_tax = 0`; conversion years =
`{planning_year .. planning_year + conv_years - 1}`.
```
for each y:
    conv = annual_conversion_amount if y in conversion_years else 0
    trad = trad - conv           # conversion taken first, at start of year
    roth = roth + conv           # into Roth before this year's growth
    if y >= first_rmd_year:
        rmd_amt = trad / rmd_factor[age]   # RMD base is AFTER conversion
        conv_tax += rmd_amt * mtr
        trad = (trad - rmd_amt) * (1 + r)
    else:
        trad = trad * (1 + r)
    roth = roth * (1 + r)        # Roth (incl. this year's conversion) grows
```
- `baseline_rmd_tax_through_horizon` = `base_tax`.
- `conversion_rmd_tax_through_horizon` = `conv_tax`.
- `rmd_tax_savings_through_horizon` = `base_tax - conv_tax`.
- `projected_roth_balance_horizon` = `roth` at end of horizon (CONVERSION scenario).
- `projected_traditional_balance_horizon` = `trad` at end of horizon (CONVERSION
  scenario).
- `horizon_year` = memo horizon.

Recommendation:
- `primary_action` = `STAGED_ROTH_CONVERSION` if `annual_conversion_amount > 0` and
  `conv_years > 0`, else `NO_CONVERSION` (or `DEFER`).
- `suitability` = `SUITABLE` when positive conversion, else `DEFER`/`BORDERLINE`.
- `risk_flag`: `TAX_BRACKET_MANAGEMENT` (default). Use `LIQUIDITY_CONSTRAINT` if
  `liquid_assets < total_conversion_tax`; use `RMD_NEAR_TERM` if
  `first_rmd_year <= planning_year` (already at/ past RMD age).
- `heir_tax_profile`: `MIXED_TAXABLE_AND_TAX_FREE` if both projected balances > 0;
  `MOSTLY_TAX_FREE` if traditional balance <= 0 and roth > 0; `MOSTLY_TAXABLE` if
  roth balance <= 0.

## 7. Analysis B — `ilit_crummey_implementation`

Inputs: `/life-insurance` policy, SIGNED_PROFILE `beneficiary_count`,
`/policies/tax` `annual_gift_exclusion[planning_year]`, `estate_tax_rate`.

gift_plan:
- `planning_year` = client planning year.
- `annual_exclusion_per_beneficiary` = `annual_gift_exclusion[planning_year]`.
- `beneficiary_count` = from SIGNED_PROFILE.
- `annual_exclusion_capacity` = `annual_exclusion_per_beneficiary * beneficiary_count`.
- `annual_premium` = policy `annual_premium`.
- `premium_gap` = `max(0, annual_premium - annual_exclusion_capacity)`.

administration (calendar-day arithmetic):
- `notices_required` = `beneficiary_count` (one Crummey notice per beneficiary).
- `contribution_date` = policy `planned_contribution_date`.
- `notice_due_date` = `contribution_date + 7 days`.
- `withdrawal_window_end` = `notice_due_date + 30 days`.
- `earliest_premium_payment_date` = `withdrawal_window_end + 1 day`.
- `dedicated_bank_account_required` = `true` (always for an ILIT Crummey cycle).

estate_result:
- `death_benefit` = policy `death_benefit`.
- `estate_inclusion_risk` = the risk_flag (see below).
- `projected_outside_estate_if_implemented` = `death_benefit` (the ILIT removes the
  full death benefit from the gross estate when formalities are met).
- `tax_liquidity_support` = `death_benefit * estate_tax_rate`.

risk_flag / primary_action decision tree (from `is_existing_policy_transfer` +
`premium_gap`):
- not existing AND gap 0 -> `LOW_IF_FORMALITIES_MET`, action
  `FUND_WITH_CRUMMEY_NOTICES`, suitability `SUITABLE_WITH_ADMINISTRATION`.
- not existing AND gap > 0 -> `EXCLUSION_SHORTFALL`, action
  `USE_LIFETIME_EXEMPTION_FOR_SHORTFALL`.
- existing AND gap 0 -> `THREE_YEAR_LOOKBACK`, action
  `USE_NEW_POLICY_OR_ACCEPT_LOOKBACK`.
- existing AND gap > 0 -> `THREE_YEAR_LOOKBACK_AND_EXCLUSION_SHORTFALL`, action
  `DISCLOSE_LOOKBACK_AND_USE_EXEMPTION`.

## 8. Analysis C — `trust_comparison`

Inputs: `/trust-candidates` (`asset_value` V, `expected_growth_rate` g,
`grat_term_years`, `grat_annuity_rate`, `crat_term_years`, `crat_payout_rate`),
SIGNED_PROFILE goals (`family_transfer_priority`, `philanthropic_intent`) + estate
facts, `estate_tax_rate`, `charitable_deduction_rate`, `max_crat_term_years`.

estate_context:
- `planning_year` = client planning year.
- `exemption_used` = `(2 if married/MFJ else 1) * estate_tax_exemption[planning_year]`.
- `taxable_estate` = `estate_value - exemption_used` (estate_value from ATTORNEY_MEMO
  authority, fallback SIGNED_PROFILE).
- `estate_tax_exposure` = `taxable_estate * estate_tax_rate`.
- `liquid_assets_available` = `liquid_assets` (SIGNED_PROFILE).
- `liquidity_gap_before_planning` = `max(0, estate_tax_exposure - liquid_assets_available)`.

Formulas (compute from UNROUNDED values, round outputs to cents):
- GRAT `projected_remainder_to_heirs` =
  `V*(1+g)**grat_term_years - grat_annuity_rate*V*grat_term_years`.
- GRAT `estimated_estate_tax_reduction` =
  `round(projected_remainder_to_heirs_unrounded * estate_tax_rate, 2)`.
- GRAT `term_years` = `grat_term_years`; `mortality_inclusion_risk` =
  `TERM_SURVIVAL_REQUIRED`.
- CRAT `projected_charitable_remainder` =
  `V*(1+g)**crat_term_years - crat_payout_rate*V*crat_term_years`.
- CRAT `estimated_income_tax_deduction` =
  `round(projected_charitable_remainder_unrounded * charitable_deduction_rate, 2)`.
- CRAT `term_years` = `crat_term_years` (== `max_crat_term_years`).

Recommendation:
- `preferred_strategy` = `GRAT` if `family_transfer_priority` == high; `CRAT` if
  `philanthropic_intent` == high.
- `rationale_code` = `CHILDREN_TRANSFER_PRIORITY` (GRAT) or `PHILANTHROPIC_PRIORITY`
  (CRAT).
- `alternate_role` = `SECONDARY_CHARITABLE_TOOL` (if GRAT preferred) or
  `SECONDARY_FAMILY_TRANSFER_TOOL` (if CRAT preferred).
- CRAT `family_transfer_fit` = `LOW` when GRAT is preferred; else `MODERATE`/`HIGH`.

## 9. Analysis D — `estate_liquidity_action_plan`

Combines an estate_context, a condensed ILIT block, a trust_transfer block, and an
action_set. Inputs: same as B + C for the same client.

estate_context: same formulas as §8.

ilit (condensed):
- `annual_exclusion_capacity` = `annual_gift_exclusion[planning_year] * beneficiary_count`.
- `premium_gap` = `max(0, annual_premium - annual_exclusion_capacity)`.
- `estate_inclusion_risk` = risk_flag from the same decision tree as §7.
- `projected_outside_estate_if_implemented` = `death_benefit`.

trust_transfer:
- `preferred_strategy` = GRAT if `family_transfer_priority` == high else CRAT.
- `projected_remainder_to_heirs` = GRAT remainder formula (§8).
- `estimated_estate_tax_reduction` = `round(remainder_unrounded * estate_tax_rate, 2)`.
- `projected_charitable_remainder` = CRAT remainder formula (§8).

recommendation:
- `primary_action` = `COMBINE_ILIT_AND_GRAT` when ILIT is fundable (gap 0) and GRAT is
  preferred; `CRAT_WITH_LIQUIDITY_REVIEW` when CRAT preferred with a liquidity gap;
  `ILIT_WITH_EXEMPTION_REVIEW` when ILIT has a premium_gap and no trust driver.
- `sequencing` = `ILIT_FIRST_THEN_GRAT` when combining ILIT + GRAT;
  `TRUST_DECISION_FIRST` when CRAT; `ILIT_FIRST_THEN_ATTORNEY_REVIEW` when ILIT-only.
- `risk_flag` = the ILIT risk_flag (decision tree §7).

action_set: choose from the enum set {`ATTORNEY_DRAFT_REVIEW`,
`CRAT_FOR_CHARITABLE_REMAINDER`, `GRAT_FOR_APPRECIATING_SHARES`,
`ILIT_CRUMMEY_NOTICE_CYCLE`, `LIFETIME_EXEMPTION_ALLOCATION`} and SORT ALPHABETICALLY.
Selection:
- Always include `ATTORNEY_DRAFT_REVIEW` (combined plan needs attorney drafting).
- Include `ILIT_CRUMMEY_NOTICE_CYCLE` when an ILIT is being funded.
- Include `GRAT_FOR_APPRECIATING_SHARES` when `preferred_strategy` == GRAT.
- Include `CRAT_FOR_CHARITABLE_REMAINDER` when `preferred_strategy` == CRAT.
- Include `LIFETIME_EXEMPTION_ALLOCATION` when `premium_gap > 0`.

## 10. Common mistakes to avoid

- Wrong source winning: do NOT let CRM_NOTE or STALE_MARKETING_INTAKE override
  SIGNED_PROFILE for profile/goal facts, and do NOT let SIGNED_PROFILE override
  ATTORNEY_MEMO for estate/trust-asset valuation. Use the family-authority rule in §4.
- Wrong horizon year: read the horizon ONLY from the memo's `Planning horizon year:
  YYYY` line (roth tasks). Do not infer it from age or RMD start.
- Off-by-one conversion years: conversions run `planning_year ..
  planning_year + recommended_conversion_years - 1`; RMDs run `first_rmd_year ..
  horizon` INCLUSIVE. They may overlap (near-RMD client) — that is correct.
- RMD base wrong: in a year that is BOTH a conversion year and an RMD year, the RMD is
  computed AFTER subtracting the conversion (`trad = trad - conv` first).
- RMD factor lookup: use the client's age IN that year (`age0 + (y - planning_year)`),
  keyed on `/rmd-factors` (73->26.5, etc.). Do not recompute the table.
- Roth/ traditional balances at horizon: taken from the CONVERSION scenario, after
  conversions AND RMDs both deplete the balance; baseline is only used for the
  `baseline_rmd_tax` number.
- GRAT/CRAT rounding: `estimated_estate_tax_reduction` and
  `estimated_income_tax_deduction` MUST be computed from the UNROUNDED remainder, then
  rounded — rounding the remainder first loses a cent.
- Non-ISO dates: all `administration` dates must be `YYYY-MM-DD` strings produced by
  calendar-day arithmetic (`+7`, `+30`, `+1`), not month-string math.
- action_set not sorted: emit the estate-liquidity `action_set` in strict alphabetical
  order.
- Numbers as strings: every USD figure must be a JSON number (e.g. `80000.0`), never a
  quoted string.
- Exemption multiplier: married/MFJ uses `2 *` the per-person exemption; single uses
  `1 *`. Wrong multiplier cascades into taxable_estate, exposure, and liquidity_gap.
