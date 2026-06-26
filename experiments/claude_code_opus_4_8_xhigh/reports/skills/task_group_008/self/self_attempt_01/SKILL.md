---
name: private-wealth-advisory-planner
description: >
  Solve private-wealth advisory planning tasks (Roth conversion / RMD tax, ILIT
  Crummey funding, GRAT-vs-CRAT comparison, integrated estate-liquidity action
  plans) by pulling client data from the remote advisory API, resolving
  conflicting source documents by a fixed priority, running the derived
  per-analysis formulas, and emitting a single JSON object that conforms to the
  task's answer_template.json. Use whenever a prompt says "private wealth
  advisory team" and references a CLT-#### client plus one of those four
  engagements.
---

# Private Wealth Advisory Planner

You are given a client id (e.g. `CLT-2003`), a `request_memo.md`, and an
`answer_template.json`. You must return ONE JSON object (no prose, no markdown
fences) that matches the template's `required_top_level_keys`, field types, and
enum values. All data comes from a remote HTTP API — there are no local data
files.

## 0. Golden output rules (apply to EVERY task)
- Output is a single JSON object only. No prose, no code fences, no trailing text.
- USD amounts: JSON numbers (never strings), rounded to 2 decimals (cents).
- Dates: ISO `YYYY-MM-DD` strings.
- Always echo `task_id` (from the prompt/filename, e.g. `train_003` or `test_012`)
  and `client_id` exactly.
- Set `analysis_type` to the fixed enum for the task type (see each section).
- Include EVERY `required_top_level_key`. Include every sub-field named in
  `fields`. Use the exact enum spellings from the template — they are case- and
  underscore-sensitive.
- `action_set` (estate-liquidity task only) MUST be sorted alphabetically.

## 1. API access
Base URL is given by the harness (env `API_BASE`, or in `environment_access.md`).
At time of writing: `<remote-env-url>`. Use `curl -s` via Bash.
If you run helper scripts use `python` (NOT `python3` — broken on the host).

Endpoints (all GET, read-only):
- `/api/health` — liveness sanity check.
- `/api/clients` / `/api/clients/<id>` — base client record.
- `/api/source-documents?client_id=<id>` — conflicting imported docs (see §2).
- `/api/retirement-accounts?client_id=<id>` — IRA export (CUSTODIAN_EXPORT).
- `/api/life-insurance?client_id=<id>` — policy / ILIT records.
- `/api/trust-candidates?client_id=<id>` — GRAT/CRAT parameters.
- `/api/policies/tax` — exemptions, rates, brackets, gift exclusion, limits.
- `/api/rmd-factors` — age → RMD divisor map.

Pull, for the engagement, only what you need, but it is cheap and safe to pull
all seven for the client. Always pull `/api/policies/tax` and (for Roth tasks)
`/api/rmd-factors`.

## 2. Conflicting-source resolution (CRITICAL — this is the trap)
`source-documents` returns multiple docs, each with `source_type`,
`effective_date`, and a `facts` object of overriding fields. Different docs
disagree on income, beneficiary_count, intent, estate_value, etc. You must pick
ONE controlling value per field, then report which source won.

**Authority priority (highest → lowest):**
1. `SIGNED_PROFILE`
2. `ATTORNEY_MEMO`
3. `CUSTODIAN_EXPORT` (only for account/IRA facts)
4. `CRM_NOTE`
5. `STALE_MARKETING_INTAKE`

Rules:
- For any **client-profile fact** (annual_non_ira_income, marginal_tax_rate,
  beneficiary_count, philanthropic_intent, family_transfer_priority, age,
  filing_status, estate_value, liquid_assets), take the value from the
  highest-priority `source_type` that supplies that field. SIGNED_PROFILE is the
  most complete and almost always controls; it is the tiebreak winner even when
  its `effective_date` is later OR earlier than the others.
- Tiebreak within the same `source_type` (rare): later `effective_date` wins.
- **Account facts** (traditional_balance, roth_balance, expected_return,
  rmd_start_age, recommended_conversion_years) come from the
  `retirement-accounts` endpoint, whose `source_type` is `CUSTODIAN_EXPORT`.
  That is the controlling account source. Do NOT take balances from the signed
  profile.
- **Policy facts** (death_benefit, annual_premium, planned_contribution_date,
  is_existing_policy_transfer) come from the `life-insurance` endpoint; report
  the controlling policy source as `CUSTODIAN_EXPORT` (the export-style record),
  unless an attorney memo/ signed profile explicitly overrides a policy field
  (then use that higher-priority source for the overridden field).
- **Asset facts** for trust math (asset_value, growth, term, rates) come from
  `trust-candidates`. For `source_resolution.controlling_asset_source`, prefer
  `ATTORNEY_MEMO` when the memo carries the relevant estate/asset figure, else
  `SIGNED_PROFILE`, else `CRM_NOTE` — i.e. the highest-priority source actually
  present that speaks to the asset/estate value.

Report fields you must set (names vary by template):
- `controlling_profile_source` / `controlling_goal_source` /
  `controlling_beneficiary_source` = the winning source_type for the profile
  facts the task needed (normally `SIGNED_PROFILE`).
- `controlling_account_source` = `CUSTODIAN_EXPORT`.
- `controlling_policy_source` = `CUSTODIAN_EXPORT` (life-insurance record).
- `controlling_asset_source` = highest-priority source present for the
  asset/estate value (often `ATTORNEY_MEMO`, else `SIGNED_PROFILE`).

Data-shape note: train clients (CLT-1xxx, CLT-2xxx) often have 3 docs
(CRM_NOTE + ATTORNEY_MEMO + SIGNED_PROFILE). Unseen clients (CLT-3xxx) often
have only 2 (SIGNED_PROFILE + CRM_NOTE) with varied effective_dates. The
priority rule handles both; do not assume an ATTORNEY_MEMO exists.

## 3. Shared constants (from /api/policies/tax, 2026 planning)
- `annual_gift_exclusion[year]`: 2025→19000, 2026→20000.
- `estate_tax_exemption[year]`: 2025→13,990,000, 2026→13,610,000.
- `estate_tax_rate` = 0.40.
- `conversion_bracket_targets`: MFJ 394600, SINGLE 197300, HOH 263500.
- `max_crat_term_years` = 20; `charitable_deduction_rate` = 0.35.
Use the `planning_year` from the controlling profile (normally 2026) to index
the year-keyed maps. Filing status drives the bracket target and can be MFJ,
SINGLE, or HOH (HOH appears in the unseen pool).

### Shared estate math (reused by tasks 3 & 4)
- `taxable_estate` = controlling `estate_value`.
- `estate_tax_exposure` = max(0, (estate_value − exemption[year]) × 0.40).
- `liquidity_gap_before_planning` = max(0, estate_tax_exposure − liquid_assets).

## 4. Analysis type A — Roth conversion + RMD (`roth_conversion_rmd`)
Template keys: recommendation, conversion_plan, rmd_projection,
legacy_projection, source_resolution.

Inputs: controlling profile (age, filing_status, marginal_tax_rate,
annual_non_ira_income, planning_year); account (traditional_balance,
roth_balance, expected_return `r`, rmd_start_age=73,
recommended_conversion_years `N`); horizon year from the memo (e.g. 2046, 2042);
rmd-factors map; bracket target for filing status.

Derived quantities:
- `first_conversion_year` = planning_year.
- `conversion_years` = N (recommended_conversion_years). `conversion_years_positive`
  = number of those years in which a positive conversion actually occurs
  (equals N unless the traditional balance is exhausted earlier; then it is the
  count of years with a real conversion).
- Bracket headroom = bracket_target − annual_non_ira_income.
- `annual_conversion_amount` = min(headroom, traditional_balance / N). This caps
  conversions to stay inside the target bracket. If headroom ≤ 0, no conversion.
- `total_converted` = sum of actual annual conversions (≈ annual × N, less if
  balance runs out).
- `total_conversion_tax` = total_converted × marginal_tax_rate.
- `first_rmd_year` = planning_year + (rmd_start_age − age).

Year-by-year simulation, planning_year … horizon, two scenarios
(baseline = no conversion; conversion = staged):
  For each year, with current age a = age + (year − planning_year):
    1. (conversion scenario only) if year is within the N-year window AND
       traditional>0: convert c = min(annual_conversion_amount, traditional);
       traditional −= c; roth += c.
    2. if a ≥ rmd_start_age AND traditional>0: rmd = traditional / factor[a];
       rmd_tax += rmd × marginal_tax_rate; traditional −= rmd.
    3. grow both: traditional ×= (1+r); roth ×= (1+r).
  Track cumulative `*_rmd_tax_through_horizon` for each scenario.
- `baseline_rmd_tax_through_horizon` = baseline cumulative RMD tax.
- `conversion_rmd_tax_through_horizon` = conversion-scenario cumulative RMD tax.
- `rmd_tax_savings_through_horizon` = baseline − conversion (positive = good).
- `projected_roth_balance_horizon` / `projected_traditional_balance_horizon` =
  end-of-horizon balances in the conversion scenario.

Keep the conversion window, RMD timing, and growth-order conventions IDENTICAL
across both scenarios so the comparison is apples-to-apples; the dollar levels
matter less than internal consistency of baseline vs conversion.

Enums:
- `recommendation.primary_action`: `STAGED_ROTH_CONVERSION` when headroom>0 and
  savings>0; `DEFER` when RMDs are imminent / bracket pressure makes staging
  marginal; `NO_CONVERSION` when headroom ≤ 0 or conversion never helps.
- `recommendation.suitability`: `SUITABLE` (clear net benefit, room to convert),
  `BORDERLINE` (thin headroom or small savings), `DEFER`.
- `recommendation.risk_flag`: `RMD_NEAR_TERM` if first_rmd_year is within ~1–2
  years of planning_year (e.g. age ≥ 71); `TAX_BRACKET_MANAGEMENT` if
  conversions are bracket-capped (annual = headroom < balance/N);
  `LIQUIDITY_CONSTRAINT` if liquid_assets are tight relative to conversion tax.
- `legacy_projection.heir_tax_profile`: compare end roth vs traditional. roth
  share ≳ 0.7 → `MOSTLY_TAX_FREE`; ≲ 0.3 → `MOSTLY_TAXABLE`; else
  `MIXED_TAXABLE_AND_TAX_FREE`.

## 5. Analysis type B — ILIT Crummey (`ilit_crummey_implementation`)
Template keys: recommendation, gift_plan, administration, estate_result,
source_resolution.

Inputs: controlling beneficiary_count; planning_year; policy
(death_benefit, annual_premium, planned_contribution_date `D`,
is_existing_policy_transfer); annual_gift_exclusion[year]; estate math.

gift_plan:
- `planning_year`.
- `annual_exclusion_per_beneficiary` = annual_gift_exclusion[planning_year].
- `beneficiary_count` = controlling beneficiary_count.
- `annual_exclusion_capacity` = per_beneficiary × beneficiary_count.
- `annual_premium` = policy premium.
- `premium_gap` = annual_premium − annual_exclusion_capacity. Positive =
  shortfall (premium exceeds gift-tax-free capacity); ≤ 0 = covered (a
  surplus/negative number; report the signed value).

administration (Crummey timeline off contribution date D):
- `notices_required` = beneficiary_count (one withdrawal notice each).
- `contribution_date` = D (ISO).
- `notice_due_date` = D (notices go out at/just after the gift; use D).
- `withdrawal_window_end` = D + 30 days (standard 30-day Crummey window).
- `earliest_premium_payment_date` = withdrawal_window_end + 1 day (premium only
  after the lapse of withdrawal rights).
- `dedicated_bank_account_required` = true (ILIT formalities require a separate
  trust account).

estate_result:
- `death_benefit` = policy death_benefit.
- `estate_inclusion_risk` = same enum as recommendation.risk_flag (see below).
- `projected_outside_estate_if_implemented` = death_benefit if proceeds stay
  outside the estate (new policy, formalities met). If
  is_existing_policy_transfer is true, the 3-year lookback (IRC §2035) can pull
  the benefit back in for 3 years → treat as not-yet-outside (0) until lookback
  clears.
- `tax_liquidity_support` = min(death_benefit, estate_tax_exposure) — how much
  estate-tax liquidity the policy actually covers.

Enums:
- `recommendation.primary_action`: `FUND_WITH_CRUMMEY_NOTICES` (capacity ≥
  premium, new policy); `USE_LIFETIME_EXEMPTION_FOR_SHORTFALL` (premium_gap>0,
  cover the excess with lifetime exemption); `USE_NEW_POLICY_OR_ACCEPT_LOOKBACK`
  (existing-policy transfer, no shortfall); `DISCLOSE_LOOKBACK_AND_USE_EXEMPTION`
  (existing-policy transfer AND shortfall).
- `recommendation.suitability`: `SUITABLE_WITH_ADMINISTRATION` (workable if
  formalities met), `BORDERLINE`, `NOT_SUITABLE`.
- `risk_flag` / `estate_inclusion_risk` (same enum):
  - shortfall? = premium_gap > 0.
  - lookback? = is_existing_policy_transfer == true.
  - neither → `LOW_IF_FORMALITIES_MET`
  - shortfall only → `EXCLUSION_SHORTFALL`
  - lookback only → `THREE_YEAR_LOOKBACK`
  - both → `THREE_YEAR_LOOKBACK_AND_EXCLUSION_SHORTFALL`
  Match primary_action to the same two booleans.

## 6. Analysis type C — GRAT vs CRAT (`trust_comparison`)
Template keys: recommendation, estate_context, grat, crat, source_resolution.

Inputs: controlling goal (philanthropic_intent, family_transfer_priority);
trust-candidate (asset_value `A`, expected_growth_rate `g`, grat_term_years,
grat_annuity_rate, crat_term_years (≤ max 20), crat_payout_rate); estate math.

estate_context: taxable_estate, estate_tax_exposure, liquidity_gap_before_planning
(see §3).

GRAT (zeroed-out remainder model):
- annuity payment = asset_value × grat_annuity_rate (level, paid yearly).
- asset FV = A × (1+g)^term.
- annuity FV (ordinary) = pmt × (((1+g)^term − 1) / g).
- `grat.projected_remainder_to_heirs` = asset FV − annuity FV.
- `grat.estimated_estate_tax_reduction` = remainder × estate_tax_rate (0.40).
- `grat.mortality_inclusion_risk` = `TERM_SURVIVAL_REQUIRED` (constant).
- `grat.term_years` = grat_term_years.

CRAT:
- payout = asset_value × crat_payout_rate (level, yearly), term = crat_term_years
  (capped at max_crat_term_years = 20).
- `crat.projected_charitable_remainder` = A × (1+g)^term − payout × (((1+g)^term
  − 1)/g).
- `crat.estimated_income_tax_deduction` = asset_value × charitable_deduction_rate
  (0.35).
- `crat.term_years` = crat_term_years.
- `crat.family_transfer_fit`: `LOW` (charity gets remainder, little to family) —
  in general CRAT family fit is LOW; raise to MODERATE/HIGH only if facts point
  to family-benefit features (default LOW).

Recommendation by goal:
- If family_transfer_priority is "high" and philanthropic_intent is "low"/"moderate":
  `preferred_strategy` = `GRAT`, `rationale_code` = `CHILDREN_TRANSFER_PRIORITY`,
  `alternate_role` = `SECONDARY_CHARITABLE_TOOL`.
- If philanthropic_intent is "high" (dominant) and family is secondary:
  `preferred_strategy` = `CRAT`, `rationale_code` = `PHILANTHROPIC_PRIORITY`,
  `alternate_role` = `SECONDARY_FAMILY_TRANSFER_TOOL`.
  (Tie / both high → favor the one matching the stronger stated priority; when
  family_transfer_priority="high" wins, choose GRAT.)

## 7. Analysis type D — Estate-liquidity action plan (`estate_liquidity_action_plan`)
Template keys: recommendation, estate_context, ilit, trust_transfer, action_set,
source_resolution. This integrates B + C.

estate_context: taxable_estate, estate_tax_exposure, liquidity_gap_before_planning
(§3).

ilit block (subset of §5):
- `annual_exclusion_capacity` = exclusion[year] × beneficiary_count.
- `premium_gap` = annual_premium − capacity (signed).
- `estate_inclusion_risk` = same risk-flag enum as §5 (from shortfall? +
  lookback? booleans).
- `projected_outside_estate_if_implemented` = death_benefit (0 if existing-policy
  transfer within lookback).

trust_transfer block (subset of §6):
- `preferred_strategy` = GRAT or CRAT chosen exactly as in §6.
- `projected_remainder_to_heirs` = GRAT remainder (§6).
- `estimated_estate_tax_reduction` = GRAT remainder × 0.40.
- `projected_charitable_remainder` = CRAT remainder (§6).

recommendation:
- `primary_action`: `COMBINE_ILIT_AND_GRAT` (family-transfer priority, new ILIT
  + GRAT both fit); `CRAT_WITH_LIQUIDITY_REVIEW` (philanthropic priority);
  `ILIT_WITH_EXEMPTION_REVIEW` (shortfall needs lifetime-exemption allocation).
- `sequencing`: `ILIT_FIRST_THEN_GRAT` (combine case);
  `TRUST_DECISION_FIRST` (CRAT/charitable case);
  `ILIT_FIRST_THEN_ATTORNEY_REVIEW` (shortfall/lookback needs counsel).
- `risk_flag`: same enum/logic as the ILIT risk flag (§5) — driven by the
  ILIT shortfall? + lookback? booleans.

`action_set` (list of enums, **sorted alphabetically**) — include those that apply:
- `ATTORNEY_DRAFT_REVIEW` — always include (every plan needs counsel).
- `ILIT_CRUMMEY_NOTICE_CYCLE` — when an ILIT/life policy is in play (usually yes).
- `GRAT_FOR_APPRECIATING_SHARES` — when preferred_strategy is GRAT.
- `CRAT_FOR_CHARITABLE_REMAINDER` — when CRAT is the chosen or strong secondary
  charitable tool (philanthropic_intent moderate/high).
- `LIFETIME_EXEMPTION_ALLOCATION` — when ilit premium_gap > 0 (shortfall) or
  estate_tax_exposure must be offset with lifetime exemption.
After selecting, sort the list alphabetically before emitting.

## 8. Procedure (SOP)
1. `curl /api/health` to confirm liveness; read base URL from environment.
2. Read prompt + request_memo (client_id, engagement, horizon year if any).
3. Read answer_template.json: note required keys, field list, enum sets,
   analysis_type, and any ordering rule (action_set sort).
4. Pull client, source-documents, and the relevant
   accounts/life-insurance/trust-candidates, plus policies/tax (+ rmd-factors
   for Roth tasks).
5. Resolve controlling values per §2; record the winning source_type per
   `source_resolution` field.
6. Run the formulas for the analysis type (§4–§7). Do arithmetic in `python`
   for accuracy; keep baseline vs scenario conventions consistent.
7. Round all USD to cents, format dates ISO, set enums from the booleans/
   thresholds above.
8. Assemble the JSON with all required keys (and only sensible values), echoing
   task_id, client_id, analysis_type.
9. Validate: every required_top_level_key present, every sub-field present,
   enums spelled exactly, action_set sorted, numbers are JSON numbers, output is
   a bare JSON object with no surrounding prose.

## 9. Common pitfalls / exclusions
- Do NOT take account balances or rates from the signed profile — they live in
  `retirement-accounts` (CUSTODIAN_EXPORT).
- Do NOT let a later-dated CRM_NOTE override a SIGNED_PROFILE; authority beats
  recency across different source_types. Recency only breaks ties within the
  same source_type.
- beneficiary_count drives BOTH gift capacity and notices_required — use the
  controlling (signed) value, not the CRM value.
- premium_gap is signed: positive means a true shortfall (drives
  EXCLUSION_SHORTFALL and lifetime-exemption actions); a negative value means
  surplus capacity — do not flag a shortfall.
- is_existing_policy_transfer == true is the ONLY trigger for the 3-year lookback
  flag; a brand-new policy never triggers it.
- estate_tax_exposure and liquidity_gap are floored at 0 (never negative). If
  estate_value < exemption, exposure = 0.
- HOH filing status is valid and has its own bracket target (263500); don't
  assume MFJ/SINGLE only.
- CRAT term is capped at max_crat_term_years (20).
- Emit numbers as numbers (no quotes), dates as ISO strings; never wrap the JSON
  in ``` fences or add explanation.
- planning_year indexes the year-keyed policy maps (exclusion, exemption); use it
  (normally 2026), not the current calendar year.
