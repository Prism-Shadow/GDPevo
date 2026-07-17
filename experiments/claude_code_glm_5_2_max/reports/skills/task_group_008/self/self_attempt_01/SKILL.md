# SKILL: Private Wealth Advisory Structured Outputs

Executable SOP for producing roth-conversion/RMD, ILIT-Crummey, GRAT-vs-CRAT, and
estate-liquidity action-plan JSON against the remote advisory API. The API exposes one
client plus CONFLICTING source documents (CRM note, attorney memo, custodian export,
signed profile, sometimes stale marketing intake). The core of every task is deciding
WHICH source controls each fact, then applying a fixed formula set.

## 0. Universal conventions
- USD amounts: round to cents (2 decimals). Use JSON numbers, not strings.
- Dates: ISO `YYYY-MM-DD`, calendar-day arithmetic.
- Years: integers (no quotes).
- Rounding rule: round each computed monetary field independently to 2 decimals at the
  END of its formula (do not round intermediates used inside a multi-step projection;
  round only the final summed/projected value you place in the JSON).
- Output: a single JSON object matching the task's `answer_template.json`. Keys listed in
  template `fields` are the ones scored. Emit `task_id` as `train_NNN` for train or
  `test_NNN` for test (use the position implied by the engagement), `client_id` verbatim.
- Never invent fields; never add prose outside the JSON.

## 1. Remote API workflow (endpoint order)
Base URL is in the staged `environment_access.md` (field `API_BASE`). All endpoints are GET.

1. `GET /api/health` — confirm `{"ok": true}`.
2. `GET /api/policies/tax` — fetch ONCE and cache. Gives:
   `annual_gift_exclusion{2025,2026}`, `estate_tax_exemption{2025,2026}`,
   `estate_tax_rate` (0.4), `conversion_bracket_targets{MFJ,SINGLE,HOH}`,
   `max_crat_term_years` (20), `charitable_deduction_rate` (0.35).
3. `GET /api/rmd-factors` — fetch ONCE. Map age(int) -> divisor(float). Ages 73..99
   present. For an age > 99, clamp to the factor for 99.
4. `GET /api/clients?search=<client_id>` or `GET /api/clients/<client_id>` — base record
   (age, marital_status, filing_status, planning_year, estate_value, liquid_assets).
5. `GET /api/source-documents?client_id=<id>` — the conflicting docs. This is the critical
   call. Index by `source_type`. Each doc has `effective_date` and a `facts` map.
6. `GET /api/retirement-accounts?client_id=<id>` — needed for analysis_type
   `roth_conversion_rmd`. (source_type = CUSTODIAN_EXPORT.)
7. `GET /api/life-insurance?client_id=<id>` — needed for `ilit_crummey_implementation` and
   `estate_liquidity_action_plan` (the ILIT block).
8. `GET /api/trust-candidates?client_id=<id>` — needed for `trust_comparison` and the
   trust_transfer block of `estate_liquidity_action_plan`.

Call 2, 3 once. Calls 5-8 are per-client. Always fetch source-document before computing.

## 2. Source-resolution precedence (the master rule)
Sources conflict because they were imported at different times. Resolve per fact-category:

| Fact category | Controlling source | Notes |
|---|---|---|
| Profile facts: age, planning_year, marital_status, filing_status, annual_non_ira_income, marginal_tax_rate, beneficiary_count, liquid_assets | SIGNED_PROFILE | client-signed, most recent, most complete |
| Philanthropic intent, family transfer priority (goals) | SIGNED_PROFILE | confirmed by ATTORNEY_MEMO; SIGNED wins on conflict |
| Gross estate_value (taxable estate basis) | ATTORNEY_MEMO | attorney's estate-planning valuation; SIGNED confirms |
| Retirement account: balances, expected_return, rmd_start_age, recommended_conversion_years | CUSTODIAN_EXPORT (retirement-accounts endpoint) | endpoint rows literally carry source_type=CUSTODIAN_EXPORT |
| Life-insurance policy: death_benefit, annual_premium, planned_contribution_date, is_existing_policy_transfer | CUSTODIAN_EXPORT (life-insurance endpoint) | treat the life-insurance export as the custodian record of the policy |
| Trust candidate: asset_value, growth/term/rate fields | custodian-style export from trust-candidates endpoint | use directly |

General hierarchy (most -> least authoritative): SIGNED_PROFILE > ATTORNEY_MEMO >
CUSTODIAN_EXPORT (for account/policy data it is the ONLY source) > CRM_NOTE >
STALE_MARKETING_INTAKE. CRM_NOTE (dated ~2025-11) is a stale import; supersede it. If a
STALE_MARKETING_INTAKE doc appears, treat as lowest priority / unreliable.

These map to the `source_resolution` output fields:
- `controlling_profile_source` (roth tasks) -> SIGNED_PROFILE
- `controlling_account_source` (roth tasks) -> CUSTODIAN_EXPORT
- `controlling_beneficiary_source` (ilit/estate) -> SIGNED_PROFILE
- `controlling_policy_source` (ilit/estate) -> CUSTODIAN_EXPORT
- `controlling_goal_source` (trust/estate) -> SIGNED_PROFILE
- `controlling_asset_source` (trust) -> ATTORNEY_MEMO
(Override only if a higher-priority doc is genuinely absent for that fact.)

## 3. Reading the planning horizon from the memo
Open `input/payloads/request_memo.md`. Two cases:
- The memo states `Planning horizon year: YYYY` (roth tasks). Use that YYYY as
  `rmd_projection.horizon_year` and as the projection end year.
- If no horizon is stated (ILIT, trust_comparison, estate_liquidity), there is no horizon
  field; the planning_year (from base record / signed profile, 2026) governs date math
  instead. ILIT Crummey dates are anchored on the policy `planned_contribution_date`.
`client_id` and `engagement` are also in the memo; `task_id` follows the engagement order.

## 4. Analysis A — `roth_conversion_rmd`
Inputs: signed profile (income, marginal_tax_rate, filing_status, age), retirement-account
row (traditional_balance, roth_balance, expected_return, rmd_start_age=73,
recommended_conversion_years), tax policy (bracket targets), RMD factors.

Constants:
- bracket_target = conversion_bracket_targets[filing_status] (MFJ 394600, SINGLE 197300)
- g = expected_return ; tax = marginal_tax_rate

### 4.1 conversion_plan
- first_conversion_year = planning_year
- conversion_years = recommended_conversion_years (from the custodian retirement row)
- bracket_room = max(0, bracket_target - annual_non_ira_income)   [SIGNED income]
- annual_conversion_amount = round( min(bracket_room, traditional_balance / conversion_years), 2 )
  (i.e. fill the bracket or empty the IRA evenly, whichever is smaller)
- total_converted = round( annual_conversion_amount * conversion_years, 2 )
  (this is <= traditional_balance by construction of the min)
- total_conversion_tax = round( total_converted * marginal_tax_rate, 2 )
- conversion_years_positive = number of conversion-window years in which a strictly
  positive conversion was applied (balance was > 0 and annual > 0). Normally equals
  conversion_years; smaller only if the balance is exhausted mid-window.

### 4.2 rmd_projection (year-by-year simulation)
- horizon_year = from memo
- first_rmd_year = planning_year + max(0, rmd_start_age - age)   (age from SIGNED)
- age(y) = age + (y - planning_year); factor(y) = rmd_factors[age(y)] (clamp >99 to 99)
- Conversion window = [first_conversion_year, first_conversion_year + conversion_years - 1]

BASELINE (no conversion), sum taxes over y in [first_rmd_year, horizon_year]:
```
tb = traditional_balance
baseline_rmd_tax = 0
for y in planning_year..horizon_year:
    tb = tb * (1 + g)
    if y >= first_rmd_year:
        rmd = tb / factor(y)
        tb = tb - rmd
        baseline_rmd_tax += rmd * tax
```
CONVERSION (RMD taken BEFORE conversion in any overlap year, per IRS ordering):
```
tc = traditional_balance ; rc = roth_balance ; conv_rmd_tax = 0
for y in planning_year..horizon_year:
    tc = tc * (1 + g)
    rc = rc * (1 + g)
    if y >= first_rmd_year:                 # RMD first, on grown balance
        rmd = tc / factor(y)
        tc = tc - rmd
        conv_rmd_tax += rmd * tax
    if y in conversion_window:              # then convert
        conv = min(annual_conversion_amount, tc)
        tc = tc - conv ; rc = rc + conv
```
- baseline_rmd_tax_through_horizon = round(baseline_rmd_tax, 2)
- conversion_rmd_tax_through_horizon = round(conv_rmd_tax, 2)
- rmd_tax_savings_through_horizon = round(baseline_rmd_tax - conv_rmd_tax, 2)

### 4.3 legacy_projection
- projected_roth_balance_horizon = round(rc, 2)            (end-of-horizon Roth, conversion case)
- projected_traditional_balance_horizon = round(tc, 2)     (end-of-horizon traditional, conversion case)
- heir_tax_profile: ratio = projected_roth_balance_horizon / (projected_roth_balance_horizon
  + projected_traditional_balance_horizon).
  ratio >= 0.60 -> MOSTLY_TAX_FREE ; ratio <= 0.40 -> MOSTLY_TAXABLE ; else MIXED_TAXABLE_AND_TAX_FREE.

### 4.4 recommendation (roth)
- If bracket_room <= 0 or annual_conversion_amount <= 0: primary_action NO_CONVERSION,
  suitability DEFER, risk_flag TAX_BRACKET_MANAGEMENT.
- Else if first_rmd_year <= first_conversion_year + 1 (RMD imminent / within the window):
  risk_flag RMD_NEAR_TERM; suitability BORDERLINE; primary_action STAGED_ROTH_CONVERSION
  (still stage it, but flag).
- Else: primary_action STAGED_ROTH_CONVERSION, suitability SUITABLE, risk_flag
  TAX_BRACKET_MANAGEMENT.
- If the client has essentially no time and no room, primary_action DEFER / suitability DEFER.

## 5. Analysis B — `ilit_crummey_implementation`
Inputs: signed profile (beneficiary_count, planning_year), life-insurance row (death_benefit,
annual_premium, planned_contribution_date, is_existing_policy_transfer), tax policy
(annual_gift_exclusion[planning_year]).

### 5.1 gift_plan
- planning_year = base/signed planning_year
- annual_exclusion_per_beneficiary = annual_gift_exclusion[planning_year] (2026 -> 20000)
- beneficiary_count = signed profile beneficiary_count (controlling_beneficiary_source = SIGNED)
- annual_exclusion_capacity = round(annual_exclusion_per_beneficiary * beneficiary_count, 2)
- annual_premium = life-insurance annual_premium
- premium_gap = round(annual_premium - annual_exclusion_capacity, 2)
  (positive => shortfall; <=0 => covered)

### 5.2 administration (Crummey dates from planned_contribution_date = D)
- notices_required = beneficiary_count (one Crummey notice each)
- contribution_date = D (ISO)
- notice_due_date   = D + 7 calendar days
- withdrawal_window_end = D + 30 calendar days
- earliest_premium_payment_date = D + 1 calendar day
  (Offsets +7 / +30 / +1 are taken from the contribution_date. If a test rubric expects the
  premium after the window closes, use withdrawal_window_end + 1; both are documented here so
  the resolver can reconcile to the template. Prefer the literal +7/+30/+1-from-D unless the
  policy doc states otherwise.)
- dedicated_bank_account_required = true (ILIT always needs a dedicated trust account)

### 5.3 estate_result
- death_benefit = life-insurance death_benefit (controlling_policy_source = CUSTODIAN)
- estate_inclusion_risk = risk_flag value (see 5.4)
- projected_outside_estate_if_implemented = round(death_benefit, 2)  (DB removed from estate)
- tax_liquidity_support = round(death_benefit, 2)                    (DB funds estate-tax liquidity)

### 5.4 recommendation (ilit) — pick risk_flag first, then primary_action/suitability
- is_existing_policy_transfer == true and within 3 years of planning_year =>
  THREE_YEAR_LOOKBACK component.
- premium_gap > 0 => EXCLUSION_SHORTFALL component.
- Combine: both present -> THREE_YEAR_LOOKBACK_AND_EXCLUSION_SHORTFALL; only lookback ->
  THREE_YEAR_LOOKBACK; only shortfall -> EXCLUSION_SHORTFALL; neither -> LOW_IF_FORMALITIES_MET.
- primary_action: LOW_IF_FORMALITIES_MET -> FUND_WITH_CRUMMEY_NOTICES; EXCLUSION_SHORTFALL
  -> USE_LIFETIME_EXEMPTION_FOR_SHORTFALL; THREE_YEAR_LOOKBACK -> USE_NEW_POLICY_OR_ACCEPT_LOOKBACK
  (or DISCLOSE_LOOKBACK_AND_USE_EXEMPTION if lookback + shortfall).
- suitability: LOW_IF_FORMALITIES_MET -> SUITABLE_WITH_ADMINISTRATION; EXCLUSION_SHORTFALL ->
  BORDERLINE; any lookback -> NOT_SUITABLE.

## 6. Analysis C — `trust_comparison` (GRAT vs CRAT)
Inputs: signed profile (goals, liquid_assets), attorney memo (estate_value), trust-candidates
row (asset_value, expected_growth_rate, grat_term_years, grat_annuity_rate, crat_term_years,
crat_payout_rate), tax policy.

### 6.1 estate_context
- taxable_estate = estate_value resolved from ATTORNEY_MEMO (controlling_asset_source = ATTORNEY_MEMO)
- estate_tax_exposure = round( max(0, taxable_estate - estate_tax_exemption[planning_year]) *
  estate_tax_rate, 2 )     (use 2026 exemption 13610000)
- liquidity_gap_before_planning = round( max(0, estate_tax_exposure - liquid_assets), 2 )
  (liquid_assets from SIGNED)

### 6.2 grat (use grat_term_years n, grat_annuity_rate a, growth g = expected_growth_rate)
- annuity = asset_value * a
- FV_asset = asset_value * (1+g)^n
- FV_annuity = annuity * ((1+g)^n - 1) / g
- projected_remainder_to_heirs = round( max(0, FV_asset - FV_annuity), 2 )
- estimated_estate_tax_reduction = round( projected_remainder_to_heirs * estate_tax_rate, 2 )
- mortality_inclusion_risk = TERM_SURVIVAL_REQUIRED  (always for a GRAT)
- term_years = n

### 6.3 crat (term N = min(crat_term_years, max_crat_term_years); payout p = crat_payout_rate)
- annuity = asset_value * p
- FV_asset = asset_value * (1+g)^N
- FV_annuity = annuity * ((1+g)^N - 1) / g      (g = same expected_growth_rate)
- projected_charitable_remainder = round( max(0, FV_asset - FV_annuity), 2 )
- estimated_income_tax_deduction = round( charitable_deduction_rate * asset_value, 2 )  (=0.35*asset)
- family_transfer_fit: HIGH only if family_transfer_priority high AND philanthropic low;
  MODERATE if goals mixed; LOW if philanthropic high (remainder to charity, little to family)
- term_years = N

### 6.4 recommendation (trust)
Decision from resolved goals (controlling_goal_source = SIGNED):
- family_transfer_priority == "high" and philanthropic_intent != "high" => GRAT,
  rationale_code CHILDREN_TRANSFER_PRIORITY, alternate_role SECONDARY_CHARITABLE_TOOL.
- philanthropic_intent == "high" and family_transfer_priority != "high" => CRAT,
  rationale_code PHILANTHROPIC_PRIORITY, alternate_role SECONDARY_FAMILY_TRANSFER_TOOL.
- Both high => GRAT (family transfer dominates); both moderate => GRAT (default transfer tool).

## 7. Analysis D — `estate_liquidity_action_plan`
Combines estate_context (6.1), an ILIT block (5.1-5.3 style), a trust_transfer block
(both GRAT + CRAT remainders), and an action_set.

### 7.1 estate_context — identical to 6.1.

### 7.2 ilit
- annual_exclusion_capacity = annual_exclusion_per_beneficiary * beneficiary_count (SIGNED count)
- premium_gap = annual_premium - annual_exclusion_capacity (life-insurance premium)
- estate_inclusion_risk = same risk_flag logic as 5.4
- projected_outside_estate_if_implemented = death_benefit

### 7.3 trust_transfer
- preferred_strategy = GRAT or CRAT per 6.4
- projected_remainder_to_heirs = GRAT remainder (6.2)
- estimated_estate_tax_reduction = GRAT remainder * estate_tax_rate
- projected_charitable_remainder = CRAT charitable remainder (6.3)
(Compute both remainders regardless of which strategy is preferred; the template carries both.)

### 7.4 recommendation (estate_liquidity)
- primary_action: ILIT viable (no lookback) AND preferred_strategy GRAT =>
  COMBINE_ILIT_AND_GRAT; preferred CRAT => CRAT_WITH_LIQUIDITY_REVIEW; ILIT shortfall =>
  ILIT_WITH_EXEMPTION_REVIEW.
- sequencing: COMBINE_ILIT_AND_GRAT => ILIT_FIRST_THEN_GRAT; CRAT case =>
  TRUST_DECISION_FIRST; exemption-review case => ILIT_FIRST_THEN_ATTORNEY_REVIEW.
- risk_flag: same as 5.4 (LOW_IF_FORMALITIES_MET / EXCLUSION_SHORTFALL / THREE_YEAR_LOOKBACK /
  THREE_YEAR_LOOKBACK_AND_EXCLUSION_SHORTFALL).

### 7.5 action_set (sorted alphabetically as strings)
Build the list, then sort ascending:
- ATTORNEY_DRAFT_REVIEW — always include (estate plan needs counsel drafting)
- ILIT_CRUMMEY_NOTICE_CYCLE — include (ILIT is always part of this analysis)
- GRAT_FOR_APPRECIATING_SHARES — include if preferred_strategy == GRAT
- CRAT_FOR_CHARITABLE_REMAINDER — include if preferred_strategy == CRAT
- LIFETIME_EXEMPTION_ALLOCATION — include if ilit.premium_gap > 0 (shortfall needs exemption)
Then `action_set` = sorted(list). Emit only the included ones, alphabetized.

## 8. Common mistakes / pitfalls
- Using the CRM_NOTE income/beneficiary counts: CRM is the stale import; SIGNED overrides.
  Trust signed-profile numbers for income, tax rate, beneficiary_count, liquid_assets.
- Using the signed-profile estate_value for the GRAT/CRAT taxable_estate without confirming
  the attorney memo: ATTORNEY_MEMO controls gross estate_value (controlling_asset_source).
- Forgetting RMD-before-conversion ordering in overlap years (Patel-style near-RMD clients):
  the RMD must be computed on the grown balance BEFORE that year's conversion, or the
  conversion RMD tax is understated.
- Using the wrong gift-exclusion year: use annual_gift_exclusion[planning_year] (2026=20000),
  not the prior year.
- Using the wrong estate-exemption year: estate_tax_exemption[planning_year] (2026=13610000).
- Bracket room from the wrong filing status: pull filing_status from SIGNED, then map via
  conversion_bracket_targets.
- CRAT term not capped: use min(crat_term_years, max_crat_term_years=20).
- Forgetting to max(0, ...) on GRAT/CRAT remainders (a high payout vs growth can zero them).
- Round only final fields to cents; keep full precision inside the year loop.
- Dates: use calendar days (not business days). contribution_date + 7 / + 30 / + 1.
- heir_tax_profile is derived from the CONVERSION-scenario balances at horizon, not baseline.
- total_converted is annual * conversion_years (capped by the min so it never exceeds the
  starting traditional balance); do not also subtract RMDs from total_converted.
- For a client already at/above RMD age, first_rmd_year = planning_year (max(0,...) guard).
- If is_existing_policy_transfer is true, the 3-year lookback makes the policy's death benefit
  re-includible in the estate for 3 years; reflect via THREE_YEAR_LOOKBACK risk and
  projected_outside_estate handling (only fully outside estate after the lookback clears).
- action_set must be the alphabetically sorted list of included action enums, not a dict.
