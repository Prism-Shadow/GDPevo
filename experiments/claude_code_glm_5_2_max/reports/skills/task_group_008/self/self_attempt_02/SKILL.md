# Private Wealth Advisory — Structured Planning Output SOP

Use this for personal-financial-advisory engagement tasks that ask for a single JSON
object conforming to a per-task `answer_template.json`. Domain covers Roth conversion +
RMD projection, ILIT Crummey implementation, GRAT-vs-CRAT trust comparison, and integrated
estate-liquidity action planning. The advisory API serves client records plus CONFLICTING
source documents (CRM note, attorney memo, custodian export, signed profile, stale
marketing intake). You must resolve which source controls each fact before computing.

## 0. Output contract (all task types)
- Return ONLY a JSON object matching the task's `answer_template.json` required top-level
  keys. No prose, no markdown fences.
- All USD amounts are JSON numbers rounded to cents (2 decimals), e.g. `469504.00`.
- Dates are ISO `YYYY-MM-DD`.
- `task_id` = the task identifier supplied by the harness, formatted `train_NNN` /
  `test_NNN` (derive from the task folder name if not explicit, e.g. folder `005` +
  harness phase `train` -> `train_005`).
- `client_id` = the stable client id from the request memo (see section 2).
- `analysis_type` = the enum string from the answer template's `analysis_type` field.

## 1. Read engagement inputs (memo vs prompt)
1. Read `input/payloads/request_memo.md` FIRST. It is the authoritative engagement record.
2. Extract from the memo:
   - `Client ID:` line -> `client_id` (USE THIS, not the client name in `prompt.txt`).
   - `Engagement:` line -> confirms which analysis type.
   - `Planning horizon year: NNNN` line -> the RMD projection horizon (Roth tasks only).
     If absent, the task is point-in-time / term-based (ILIT, GRAT/CRAT, estate-liquidity)
     and needs no multi-year horizon.
3. `input/prompt.txt` is generic boilerplate; its client name line can be STALE and may
   disagree with the memo. Always trust the memo's `Client ID:` over the prompt prose.
4. `input/payloads/answer_template.json` defines the exact required keys, enums, and any
   ordering constraint (e.g. `action_set` sorted alphabetically). Build the JSON to match.

## 2. Remote API workflow + endpoint order
Base URL is in `environment_access.md` (e.g. `http://HOST:PORT`). GET only.

Fetch in this order per engagement:
1. `GET /api/health` -> confirm `{"ok": true}`.
2. `GET /api/policies/tax` -> planning constants (cache once, reuse for every client):
   - `annual_gift_exclusion` (by year, e.g. `{"2025":19000,"2026":20000}`)
   - `estate_tax_exemption` (by year, e.g. `{"2025":13990000,"2026":13610000}`)
   - `estate_tax_rate` (e.g. `0.4`)
   - `conversion_bracket_targets` by filing status (`MFJ`/`SINGLE`/`HOH`)
   - `max_crat_term_years` (e.g. `20`)
   - `charitable_deduction_rate` (e.g. `0.35`)
3. `GET /api/rmd-factors` -> map of age (string) -> IRS Uniform Lifetime Table divisor
   (73->26.5, 74->25.5, ...). Used only for Roth RMD projection.
4. `GET /api/clients/<client_id>` -> base client record (age, filing_status, marital_status,
   planning_year, estate_value, liquid_assets).
5. `GET /api/source-documents?client_id=<id>` -> array of conflicting source docs. Each has
   `source_type`, `effective_date`, and a `facts` object. THIS IS THE CONFLICT SURFACE.
6. Analysis-type-specific records:
   - Roth: `GET /api/retirement-accounts?client_id=<id>`
   - ILIT: `GET /api/life-insurance?client_id=<id>`
   - GRAT/CRAT or estate-liquidity: `GET /api/trust-candidates?client_id=<id>` AND
     `GET /api/life-insurance?client_id=<id>` (estate-liquidity needs both).

## 3. Source-resolution precedence (inferred rule)
For any fact, resolve conflicts using this authority ladder, HIGHEST to LOWEST:

1. **SIGNED_PROFILE** — client-signed, newest effective_date. Controls personal/demographic
   profile AND stated client goals: `age`, `annual_non_ira_income`, `marginal_tax_rate`,
   `filing_status`, `marital_status`, `liquid_assets`, `estate_value`, `beneficiary_count`,
   `planning_year`, `philanthropic_intent`, `family_transfer_priority`.
2. **ATTORNEY_MEMO** — attorney planning-call notes. Controls LEGAL trust/estate STRUCTURE
   characterization: ILIT trust design, GRAT/CRAT vehicle choice, and which asset is placed
   in trust. Wins for `controlling_asset_source` (trust assets are legal structures, not
   custodian holdings).
3. **CUSTODIAN_EXPORT** — account/policy holdings of record. Controls money-on-hand facts:
   `traditional_balance`, `roth_balance`, `expected_return`, `rmd_start_age`,
   `recommended_conversion_years`, and policy `death_benefit`/`annual_premium` (the
   retirement-accounts and life-insurance records are custodian-type data).
4. **CRM_NOTE** — older CRM import. Fallback only; never controls when a higher source
   states the same fact.
5. **STALE_MARKETING_INTAKE** — lowest; marketing-only. Never controls a material fact.

### Per-task `source_resolution` output mapping
| Output field | Controlling source | Why |
|---|---|---|
| `controlling_profile_source` (Roth) | `SIGNED_PROFILE` | demographics + tax rate |
| `controlling_account_source` (Roth) | `CUSTODIAN_EXPORT` | retirement account record |
| `controlling_beneficiary_source` (ILIT) | `SIGNED_PROFILE` | beneficiary_count appears in signed vs CRM -> signed wins |
| `controlling_policy_source` (ILIT, estate) | `CUSTODIAN_EXPORT` | life-insurance record is custodian-type; override to `ATTORNEY_MEMO`/`SIGNED_PROFILE` only if that higher source explicitly documents the policy |
| `controlling_goal_source` (GRAT/CRAT, estate) | `SIGNED_PROFILE` | client-signed philanthropic_intent / family_transfer_priority supersede attorney/CRM |
| `controlling_asset_source` (GRAT/CRAT) | `ATTORNEY_MEMO` | trust is an attorney-drafted legal structure; enum excludes CUSTODIAN, confirming trust assets are legal not custodian |

Note the enum composition is itself a hint: `controlling_asset_source` never includes
`CUSTODIAN_EXPORT` (a trust asset is not a brokerage holding), while
`controlling_policy_source` does include it (an insurance policy is a financial product).

## 4. Shared formulas
- `first_rmd_year` = `planning_year + max(0, rmd_start_age - age)` (RMD begins at age 73).
- `taxable_estate` = `max(0, estate_value - estate_tax_exemption[planning_year])`
  (`estate_value` from controlling source, typically signed profile).
- `estate_tax_exposure` = `taxable_estate * estate_tax_rate`.
- `liquidity_gap_before_planning` = `max(0, estate_tax_exposure - liquid_assets)`.
- `annual_gift_exclusion` for the plan = `annual_gift_exclusion[planning_year]`.

## 5. Analysis type A — `roth_conversion_rmd`
Resolved inputs: `age`, `annual_non_ira_income`, `marginal_tax_rate`, `filing_status`
(from SIGNED_PROFILE); `traditional_balance` (T0), `roth_balance` (R0), `expected_return`
(g), `rmd_start_age`, `recommended_conversion_years` (from CUSTODIAN_EXPORT);
`conversion_bracket_targets[filing_status]` (bt); RMD factor table; `horizon_year` (memo).

### conversion_plan (BRACKET-FILL method — `conversion_bracket_targets` is load-bearing)
- `first_conversion_year` = `planning_year`.
- `conversion_years` = `recommended_conversion_years`.
- `annual_conversion_amount` = `max(0, bt - annual_non_ira_income)` (fill remaining bracket
  room each year), capped in the final year at the remaining traditional balance.
- `total_converted` = sum of per-year conversions across the window (<= T0). Round cents.
- `total_conversion_tax` = `total_converted * marginal_tax_rate`. Round cents.
- `conversion_years_positive` = count of conversion years falling BEFORE `first_rmd_year`
  (the pre-RMD window), capped at `conversion_years`:
  `max(0, min(conversion_years, first_rmd_year - first_conversion_year))`.
  These are the years conversion is unambiguously beneficial.

### rmd_projection (year-by-year simulation, planning_year..horizon_year)
Define `factor(age_in_year)` from the RMD table (age attained that year).
BASELINE (no conversion):
  For each year Y, beginning balance B_Y:
  - if Y >= first_rmd_year: `rmd_Y = B_Y / factor(age_Y)`; `tax_Y = rmd_Y * mtr`;
    `B_{Y+1} = (B_Y - rmd_Y) * (1+g)`.
  - else: `rmd_Y = 0`; `B_{Y+1} = B_Y * (1+g)`.
  `baseline_rmd_tax_through_horizon` = sum of `tax_Y` for Y in [first_rmd_year, horizon].
CONVERSION scenario: same loop, but in each conversion year reduce the traditional balance
by that year's conversion amount (after taking any RMD first in overlap years), and credit
the conversion to the Roth balance which then grows at g. Take RMDs on the reduced balance.
  `conversion_rmd_tax_through_horizon` = sum of `tax_Y` under conversion.
- `horizon_year` = memo horizon.
- `first_rmd_year` = as above.
- `rmd_tax_savings_through_horizon` =
  `baseline_rmd_tax_through_horizon - conversion_rmd_tax_through_horizon`. Round cents.

### legacy_projection (end of horizon_year, conversion scenario)
- `projected_roth_balance_horizon` = R0 grown to horizon + each conversion grown the
  remaining years at g. Round cents.
- `projected_traditional_balance_horizon` = remaining traditional balance at end of horizon
  (after conversions and RMDs). Round cents.
- `heir_tax_profile`: let `r = projected_roth_balance_horizon / (roth + trad)` at horizon.
  `r > 0.6` -> `MOSTLY_TAX_FREE`; `r < 0.4` -> `MOSTLY_TAXABLE`; else `MIXED_TAXABLE_AND_TAX_FREE`.

### recommendation
- `primary_action`: `STAGED_ROTH_CONVERSION` if T0 > 0 and pre-RMD window >= 1; `DEFER` if
  RMD imminent and bracket/liquidity poor; `NO_CONVERSION` if T0 == 0.
- `suitability`: `SUITABLE` if window >= ~3 yrs and liquid_assets cover conversion tax;
  `BORDERLINE` if window 1-2 yrs or tax exceeds liquid_assets; `DEFER` if no viable window.
- `risk_flag` (most salient wins, priority order): `RMD_NEAR_TERM` if
  `first_rmd_year - planning_year <= 2`; else `LIQUIDITY_CONSTRAINT` if
  `total_conversion_tax > liquid_assets`; else `TAX_BRACKET_MANAGEMENT` (bracket-fill
  inherently involves managing the bracket).

### source_resolution
`controlling_profile_source = SIGNED_PROFILE`; `controlling_account_source = CUSTODIAN_EXPORT`.

## 6. Analysis type B — `ilit_crummey_implementation`
Resolved inputs: `beneficiary_count` (SIGNED_PROFILE); `planning_year` (client record);
policy `death_benefit`, `annual_premium`, `planned_contribution_date`,
`is_existing_policy_transfer` (life-insurance record); `annual_gift_exclusion[planning_year]`.

### gift_plan
- `planning_year` = client.planning_year.
- `annual_exclusion_per_beneficiary` = `annual_gift_exclusion[planning_year]` (e.g. 20000 for 2026).
- `beneficiary_count` = from SIGNED_PROFILE.
- `annual_exclusion_capacity` = `annual_exclusion_per_beneficiary * beneficiary_count`.
- `annual_premium` = policy.annual_premium.
- `premium_gap` = `annual_premium - annual_exclusion_capacity` (raw; positive => shortfall).

### administration (Crummey notice formalities)
- `notices_required` = `beneficiary_count` (one notice per beneficiary).
- `contribution_date` = policy.planned_contribution_date (ISO).
- `notice_due_date` = `contribution_date` (notice delivered at/with the contribution).
- `withdrawal_window_end` = `contribution_date + 30 days` (30-day Crummey withdrawal right).
  ISO date arithmetic: add 30 days to the contribution date.
- `earliest_premium_payment_date` = `withdrawal_window_end` (pay premium after the
  withdrawal right lapses so funds are clearly trust property).
- `dedicated_bank_account_required` = `true` (ILIT must hold gifts in a dedicated trust account).

### estate_result
- `death_benefit` = policy.death_benefit.
- `estate_inclusion_risk` = same value as `recommendation.risk_flag`.
- `projected_outside_estate_if_implemented` = `death_benefit` when no 3-year lookback
  (`is_existing_policy_transfer == false`); `0` when lookback applies within 3 years.
- `tax_liquidity_support` = `death_benefit` (liquidity the ILIT provides to the estate).

### recommendation
- `risk_flag`: if `is_existing_policy_transfer` AND `premium_gap > 0` ->
  `THREE_YEAR_LOOKBACK_AND_EXCLUSION_SHORTFALL`; elif lookback -> `THREE_YEAR_LOOKBACK`;
  elif `premium_gap > 0` -> `EXCLUSION_SHORTFALL`; else `LOW_IF_FORMALITIES_MET`.
- `primary_action`: if lookback and shortfall -> `DISCLOSE_LOOKBACK_AND_USE_EXEMPTION`;
  elif lookback -> `USE_NEW_POLICY_OR_ACCEPT_LOOKBACK`; elif shortfall ->
  `USE_LIFETIME_EXEMPTION_FOR_SHORTFALL`; else `FUND_WITH_CRUMMEY_NOTICES`.
- `suitability`: `SUITABLE_WITH_ADMINISTRATION` (no lookback, no shortfall);
  `BORDERLINE` (shortfall only); `NOT_SUITABLE` (lookback present).

### source_resolution
`controlling_beneficiary_source = SIGNED_PROFILE`; `controlling_policy_source = CUSTODIAN_EXPORT`
(default; override to a higher source only if that source explicitly documents the policy).

## 7. Analysis type C — `trust_comparison` (GRAT vs CRAT)
Resolved inputs: goals `philanthropic_intent`, `family_transfer_priority` (SIGNED_PROFILE);
`estate_value` (SIGNED_PROFILE); trust candidate `asset_value` (A), `expected_growth_rate` (g),
`grat_term_years` (nG), `grat_annuity_rate` (aG), `crat_term_years` (= `max_crat_term_years`,
e.g. 20), `crat_payout_rate` (aC); `estate_tax_rate`, `charitable_deduction_rate`.

### estate_context
- `taxable_estate` = `max(0, estate_value - exemption[planning_year])`.
- `estate_tax_exposure` = `taxable_estate * estate_tax_rate`.
- `liquidity_gap_before_planning` = `max(0, estate_tax_exposure - liquid_assets)`.

### grat (fixed-amount annuity on initial value)
- `term_years` = `grat_term_years`.
- annuity payment P = `A * aG` per year.
- `FV_asset = A * (1+g)^nG`.
- `FV_annuity = P * ((1+g)^nG - 1) / g`.
- `projected_remainder_to_heirs` = `max(0, FV_asset - FV_annuity)`. Round cents.
- `estimated_estate_tax_reduction` = `projected_remainder_to_heirs * estate_tax_rate`.
  (remainder passes to heirs free of estate tax via the GRAT).
- `mortality_inclusion_risk` = `TERM_SURVIVAL_REQUIRED` (always; grantor must survive term).

### crat
- `term_years` = `crat_term_years` (== `max_crat_term_years`).
- charity payout C = `A * aC` per year.
- `projected_charitable_remainder` = `C * ((1+g)^term - 1) / g` (FV of charitable payouts).
  Round cents.
- `estimated_income_tax_deduction` = `A * charitable_deduction_rate`. Round cents.
- `family_transfer_fit` = `LOW` (CRAT is charity-first; family transfer is incidental).

### recommendation
- If `family_transfer_priority == "high"` -> `preferred_strategy = GRAT`,
  `rationale_code = CHILDREN_TRANSFER_PRIORITY`, `alternate_role = SECONDARY_CHARITABLE_TOOL`.
- Elif `philanthropic_intent == "high"` -> `preferred_strategy = CRAT`,
  `rationale_code = PHILANTHROPIC_PRIORITY`, `alternate_role = SECONDARY_FAMILY_TRANSFER_TOOL`.
- Default (no "high") -> GRAT (family transfer is the harder wealth-transfer problem).

### source_resolution
`controlling_goal_source = SIGNED_PROFILE`; `controlling_asset_source = ATTORNEY_MEMO`.

## 8. Analysis type D — `estate_liquidity_action_plan`
Combines ILIT + trust transfer. Resolved inputs as in B and C, plus estate context.

### estate_context
Same as section 7 (`taxable_estate`, `estate_tax_exposure`, `liquidity_gap_before_planning`).

### ilit
- `annual_exclusion_capacity`, `premium_gap` as in section 6.
- `estate_inclusion_risk` = the ILIT risk_flag (section 6 logic).
- `projected_outside_estate_if_implemented` = `death_benefit` (no lookback) or `0`.

### trust_transfer
- `preferred_strategy` = GRAT or CRAT (section 7 goal logic).
- `projected_remainder_to_heirs` = GRAT remainder (section 7) if GRAT chosen.
- `estimated_estate_tax_reduction` = `projected_remainder_to_heirs * estate_tax_rate`.
- `projected_charitable_remainder` = CRAT charitable FV (section 7) — the alternate
  charitable tool's figure, reported for the combined plan.

### action_set (sorted alphabetically; include applicable subset)
- `ATTORNEY_DRAFT_REVIEW` — always (trust docs need drafting).
- `ILIT_CRUMMEY_NOTICE_CYCLE` — if ILIT funded via Crummey (no lookback-blocking issue).
- `LIFETIME_EXEMPTION_ALLOCATION` — if `premium_gap > 0` (shortfall).
- `GRAT_FOR_APPRECIATING_SHARES` — if `preferred_strategy == GRAT`.
- `CRAT_FOR_CHARITABLE_REMAINDER` — if `preferred_strategy == CRAT`.
Sort the included values alphabetically before emitting.

### recommendation
- `primary_action`: if ILIT viable and GRAT preferred -> `COMBINE_ILIT_AND_GRAT`;
  if CRAT preferred -> `CRAT_WITH_LIQUIDITY_REVIEW`;
  if ILIT shortfall dominates -> `ILIT_WITH_EXEMPTION_REVIEW`.
- `sequencing`: `COMBINE_ILIT_AND_GRAT` -> `ILIT_FIRST_THEN_GRAT`;
  `CRAT_WITH_LIQUIDITY_REVIEW` -> `TRUST_DECISION_FIRST`;
  `ILIT_WITH_EXEMPTION_REVIEW` -> `ILIT_FIRST_THEN_ATTORNEY_REVIEW`.
- `risk_flag` = ILIT risk_flag (section 6 logic).

### source_resolution
`controlling_goal_source = SIGNED_PROFILE`; `controlling_policy_source = CUSTODIAN_EXPORT`.

## 9. Formatting & rounding rules
- Round every USD amount to cents (2 decimals). Apply rounding only at the final emitted
  value, not at intermediate simulation steps, to avoid drift.
- Years are integers; ISO dates are `YYYY-MM-DD`.
- `action_set` must be sorted alphabetically (estate-liquidity task).
- Numbers are JSON numbers, never quoted strings.
- Use the controlling-source values for every computation; never average conflicting sources.

## 10. Common mistakes / pitfalls
- Trusting `prompt.txt` client name over the memo's `Client ID:` line. The prompt can be
  stale; the memo is authoritative.
- Forgetting to read `Planning horizon year:` from the memo (Roth tasks) and defaulting to
  a wrong horizon.
- Using CRM_NOTE `beneficiary_count` / `annual_non_ira_income` instead of the SIGNED_PROFILE
  values (they disagree by design).
- Computing `taxable_estate` as gross `estate_value` instead of
  `max(0, estate_value - exemption)`.
- Treating `conversion_years_positive` as equal to `conversion_years` by default; for a
  near-RMD client the pre-RMD window is much shorter than the recommended conversion window.
- Ignoring that bracket-fill makes `conversion_bracket_targets` the conversion-sizing driver
  (annual = bracket_target - non_ira_income), not an even split.
- Forgetting RMD-must-come-out-first in years that are both conversion and RMD years.
- Setting `earliest_premium_payment_date` to the contribution date instead of after the
  30-day Crummey withdrawal window closes.
- Setting `dedicated_bank_account_required` to false (an ILIT always needs one).
- Not flagging `THREE_YEAR_LOOKBACK` when `is_existing_policy_transfer == true`.
- Putting CRAT/GRAT numbers from the non-preferred strategy in the preferred-strategy
  fields, or forgetting `projected_charitable_remainder` in the combined estate plan.
- Emitting `action_set` unsorted.
- Rounding intermediate values and propagating error; round only final emitted amounts.
