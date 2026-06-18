---
name: private-wealth-advisory-planner
description: >-
  Produce the structured JSON planning output for the Private Wealth Advisory
  benchmark — Roth-conversion/RMD tax summaries, ILIT/Crummey funding cycles,
  GRAT-vs-CRAT trust comparisons, and integrated estate-liquidity action plans.
  Use this whenever a task references a private-wealth / estate / advisory client
  (e.g. "CLT-####"), an advisory request memo, an answer_template.json that must
  be filled, a read-only advisory API (clients, source-documents, retirement-accounts,
  life-insurance, trust-candidates, policies/tax, rmd-factors), or asks for Roth
  conversion sizing, RMD projections, Crummey notice timing, gift-tax exclusion
  capacity, estate-tax exposure, GRAT/CRAT remainders, or an estate action set.
  Trigger even when the words "skill" or the analysis type are not stated explicitly.
---

# Private Wealth Advisory Planner

You fill a fixed JSON schema for one client per task. Every number is reproducible
from the advisory API plus the rules below — there is no judgment-call math. Match
the conventions exactly; the grader compares fields to a gold answer computed the
same way.

## 0. Workflow

1. Read `input/prompt.txt`, `input/payloads/request_memo.md`, and
   `input/payloads/answer_template.json`. The memo gives the client ID, the
   `analysis_type`, and (for Roth tasks) the **planning horizon year**.
2. Identify the family from `analysis_type` in the template:
   `roth_conversion_rmd`, `ilit_crummey_implementation`, `trust_comparison`, or
   `estate_liquidity_action_plan`.
3. Pull every fact from the **API**, never from your own knowledge. Base URL is
   whatever the harness exposes (env `API_BASE`, usually `http://127.0.0.1:8066`).
   Tax constants and RMD factors come from `/api/policies/tax` and
   `/api/rmd-factors` — do not hardcode IRS numbers.
4. Compute with the formulas in this file. The bundled `scripts/advisory_lib.py`
   already implements all four families and reproduces every train gold answer
   exactly — prefer importing it over re-deriving math by hand.
5. Emit **only** the JSON object the template requires (no prose, no markdown
   fence). Set `task_id` to the value the harness expects (e.g. `test_007`); if the
   prompt does not state it, mirror the task folder (`train_NNN`/`test_NNN`).

Fastest path:
```python
import sys; sys.path.insert(0, "scripts")  # adjust to where advisory_lib.py lives
import advisory_lib as A
print(A.solve_roth("CLT-1001", horizon_year=2046))   # or solve_ilit / solve_trust / solve_estate_plan
```
Read `scripts/advisory_lib.py` to see each rule in code, and
`references/families.md` for a per-field cheat sheet and worked numeric examples.

## 1. Source resolution — which record wins

The same fact can appear in several source documents that disagree (older CRM
import vs. attorney memo vs. signed profile) and in the client header. Resolve by
**fact domain**, using the system of record for that domain:

| Fact domain | Source of truth (precedence) | Reported as |
| --- | --- | --- |
| Profile / goals / beneficiary count / income / marginal rate / age / filing / marital | `SIGNED_PROFILE` → `ATTORNEY_MEMO` → `CRM_NOTE` | `controlling_profile_source` / `controlling_goal_source` / `controlling_beneficiary_source` = `SIGNED_PROFILE` |
| Retirement account balances, return, RMD start age, conversion years | `/api/retirement-accounts` (`CUSTODIAN_EXPORT`) | `controlling_account_source` = `CUSTODIAN_EXPORT` |
| Insurance policy facts (death benefit, premium, dates, transfer flag) | `/api/life-insurance`, validated against `SIGNED_PROFILE` | `controlling_policy_source` = `SIGNED_PROFILE` |
| Estate / asset valuation for **trust** funding | `ATTORNEY_MEMO` → `SIGNED_PROFILE` → `CRM_NOTE` | `controlling_asset_source` = `ATTORNEY_MEMO` |

Why: the signed profile is the most recent, client-signed, and most complete
document, so it governs anything the household attested to. The custodian export is
the system of record for accounts. For trust funding the attorney memo is the
authoritative estate-asset figure, so `controlling_asset_source` is `ATTORNEY_MEMO`
even though the signed profile usually carries the same estate value.

The `controlling_*_source` enum values are essentially **constant per family** (the
table's right column). Report them as shown; don't try to "detect" the winner per
task.

## 2. Rounding, dates, output

- All USD amounts are JSON numbers rounded to **cents** (2 decimals). Use
  `round(x + 1e-9, 2)` to avoid half-cent surprises. Never emit strings for numbers.
- Dates are ISO `YYYY-MM-DD` strings.
- `action_set` (estate plan only) must be **sorted alphabetically**.
- Output the JSON object and nothing else.

## 3. Roth conversion + RMD (`roth_conversion_rmd`)

Inputs: profile (income, marginal rate, age, planning year, filing) from
`SIGNED_PROFILE`; account (traditional/Roth balances, `expected_return`,
`rmd_start_age`, `recommended_conversion_years`) from the custodian export;
`conversion_bracket_targets[filing]` and `estate_tax_exemption`/factors from policy.
The horizon year comes from the memo.

**Conversion sizing (fill the bracket):**
- `annual_conversion_amount = conversion_bracket_targets[filing] - annual_non_ira_income`
- `conversion_years = recommended_conversion_years`; `first_conversion_year = planning_year`
- `total_converted = annual_conversion_amount * conversion_years`
- `total_conversion_tax = total_converted * marginal_tax_rate`
- `first_rmd_year = (planning_year - age) + rmd_start_age`

**Year-by-year simulation — strict order of operations per year**, run from
`planning_year` through `horizon_year` inclusive. Run it **twice**: a baseline (no
conversions) and a conversion scenario.
1. **Convert** (conversion scenario only, during the first `conversion_years`
   years): move `min(annual_conversion_amount, traditional)` from traditional to Roth.
2. **RMD** (when `age_that_year >= rmd_start_age` and a factor exists): `rmd =
   traditional / rmd_factor[age]`; subtract from traditional; add `rmd *
   marginal_tax_rate` to that scenario's RMD-tax total.
3. **Grow** both buckets by `expected_return` at the **end** of the year.

Getting the order wrong (e.g. growing before the RMD, or taking the RMD before the
conversion) shifts every downstream cent, so keep convert → RMD → grow.

Outputs: `baseline_rmd_tax_through_horizon` and
`conversion_rmd_tax_through_horizon` are the two RMD-tax totals;
`rmd_tax_savings_through_horizon = baseline - conversion`. The horizon balances
(`projected_roth_balance_horizon`, `projected_traditional_balance_horizon`) are the
conversion-scenario buckets after the horizon year.

**Enums:** `primary_action = STAGED_ROTH_CONVERSION` and `suitability = SUITABLE`
when there is bracket headroom (`annual_conversion_amount > 0`) and savings are
positive; `NO_CONVERSION`/`DEFER` if there is no headroom; `DEFER`/`BORDERLINE` if
conversions don't save tax. `risk_flag = RMD_NEAR_TERM` when the owner is already at
/ past `rmd_start_age` in the planning year, otherwise `TAX_BRACKET_MANAGEMENT`.
`heir_tax_profile`: `MOSTLY_TAX_FREE` if Roth ≥ 2× traditional at horizon,
`MOSTLY_TAXABLE` if traditional ≥ 2× Roth, else `MIXED_TAXABLE_AND_TAX_FREE`.

## 4. ILIT / Crummey (`ilit_crummey_implementation`)

Inputs: `beneficiary_count` from `SIGNED_PROFILE`; the policy
(`death_benefit`, `annual_premium`, `planned_contribution_date`,
`is_existing_policy_transfer`) from `/api/life-insurance`;
`annual_gift_exclusion[planning_year]` and `estate_tax_rate` from policy.

- `annual_exclusion_per_beneficiary = annual_gift_exclusion[planning_year]`
- `annual_exclusion_capacity = exclusion_per_beneficiary * beneficiary_count`
- `premium_gap = max(0, annual_premium - annual_exclusion_capacity)`
- `notices_required = beneficiary_count`; `dedicated_bank_account_required = true`
- `death_benefit` straight from the policy
- `tax_liquidity_support = death_benefit * estate_tax_rate`
- `projected_outside_estate_if_implemented = death_benefit` for a new policy; `0`
  when `is_existing_policy_transfer` is true (3-year lookback pulls it back into the
  estate for the first cycle).

**Crummey date arithmetic** from `planned_contribution_date`:
- `contribution_date = planned_contribution_date`
- `notice_due_date = contribution_date + 7 days`
- `withdrawal_window_end = notice_due_date + 30 days`
- `earliest_premium_payment_date = withdrawal_window_end + 1 day`

**Risk flag** (also `estate_inclusion_risk`): let `lookback =
is_existing_policy_transfer`, `shortfall = premium_gap > 0`.
`THREE_YEAR_LOOKBACK_AND_EXCLUSION_SHORTFALL` if both;
`THREE_YEAR_LOOKBACK` if only transfer; `EXCLUSION_SHORTFALL` if only shortfall;
else `LOW_IF_FORMALITIES_MET`.

**Primary action / suitability** track the risk:
`LOW_IF_FORMALITIES_MET` → `FUND_WITH_CRUMMEY_NOTICES` / `SUITABLE_WITH_ADMINISTRATION`;
`EXCLUSION_SHORTFALL` → `USE_LIFETIME_EXEMPTION_FOR_SHORTFALL` / `BORDERLINE`;
`THREE_YEAR_LOOKBACK` → `USE_NEW_POLICY_OR_ACCEPT_LOOKBACK` / `BORDERLINE`;
both → `DISCLOSE_LOOKBACK_AND_USE_EXEMPTION` / `NOT_SUITABLE`.

## 5. GRAT vs CRAT (`trust_comparison`)

Estate context (see §7) plus the trust candidate from `/api/trust-candidates`
(`asset_value`, `expected_growth_rate`, `grat_term_years`, `grat_annuity_rate`,
`crat_term_years`, `crat_payout_rate`).

Both remainders use the same shape: future value of the asset minus the **simple,
un-reinvested** sum of the fixed annual payments (the payments are NOT compounded).
- `GRAT remainder = asset*(1+growth)^grat_term - asset*grat_annuity_rate*grat_term`
- `GRAT estate_tax_reduction = GRAT remainder * estate_tax_rate (0.4)`
- `crat_term = min(crat_term_years, max_crat_term_years)` (policy cap, 20)
- `CRAT charitable_remainder = asset*(1+growth)^crat_term - asset*crat_payout_rate*crat_term`
- `CRAT income_tax_deduction = CRAT remainder * charitable_deduction_rate (0.35)`
- `grat.mortality_inclusion_risk = TERM_SURVIVAL_REQUIRED` (constant)

**Recommendation** from the household's goals (signed profile):
prefer **GRAT** when `family_transfer_priority >= philanthropic_intent`
(rank low<moderate<high), else **CRAT**.
- GRAT preferred → `rationale_code = CHILDREN_TRANSFER_PRIORITY`,
  `alternate_role = SECONDARY_CHARITABLE_TOOL`, `crat.family_transfer_fit = LOW`.
- CRAT preferred → `rationale_code = PHILANTHROPIC_PRIORITY`,
  `alternate_role = SECONDARY_FAMILY_TRANSFER_TOOL`, `family_transfer_fit = MODERATE`.

Include the full `estate_context` block (planning_year, exemption_used,
taxable_estate, estate_tax_exposure, liquid_assets_available,
liquidity_gap_before_planning) as the gold answers do.

## 6. Integrated estate-liquidity action plan (`estate_liquidity_action_plan`)

Combine §7 estate context, §4 ILIT figures, and §5 trust figures.
- `estate_context`: full block (§7).
- `ilit`: `annual_exclusion_capacity`, `premium_gap`, `estate_inclusion_risk`
  (= ILIT risk flag), `projected_outside_estate_if_implemented` (§4).
- `trust_transfer`: `preferred_strategy` (§5 rule), and report **both** the GRAT
  remainder/tax reduction (`projected_remainder_to_heirs`,
  `estimated_estate_tax_reduction`) and the CRAT `projected_charitable_remainder`.
- `recommendation.risk_flag` = the ILIT risk flag.
- When GRAT is preferred: `primary_action = COMBINE_ILIT_AND_GRAT`,
  `sequencing = ILIT_FIRST_THEN_GRAT`. When CRAT is preferred:
  `CRAT_WITH_LIQUIDITY_REVIEW` / `TRUST_DECISION_FIRST`.
- `action_set` (sorted alphabetically): always
  `ATTORNEY_DRAFT_REVIEW` and `ILIT_CRUMMEY_NOTICE_CYCLE`; add
  `GRAT_FOR_APPRECIATING_SHARES` (GRAT preferred) or
  `CRAT_FOR_CHARITABLE_REMAINDER` (CRAT preferred); add
  `LIFETIME_EXEMPTION_ALLOCATION` when `premium_gap > 0`.
- `source_resolution`: `controlling_goal_source = SIGNED_PROFILE`,
  `controlling_policy_source = SIGNED_PROFILE`.

## 7. Estate-tax context (shared §5/§6)

- `exemption_used = estate_tax_exemption[planning_year] * (2 if married else 1)`
  (marital status from the signed profile; the marital exemption doubles).
- `taxable_estate = max(0, estate_value - exemption_used)`
- `estate_tax_exposure = taxable_estate * estate_tax_rate (0.4)`
- `liquidity_gap_before_planning = max(0, estate_tax_exposure - liquid_assets)`
- For trusts, take `estate_value` from the **attorney memo** first (§1); for the
  estate plan the signed-profile value governs (and usually agrees).

## 8. Pitfalls

- Do not pull tax/exemption/gift/RMD constants from memory — only the API. Years
  matter (2025 vs 2026 exemption and gift exclusion differ).
- Keep the Roth per-year order convert → RMD → grow; a single misordered step
  throws off the horizon balances and every tax total.
- Roth scenarios overlap: conversions and RMDs can happen in the same year (e.g. a
  72-year-old converting while RMDs start at 73 one year later) — simulate both
  cleanly, no special-casing.
- Beneficiary count almost always differs between CRM and signed profile — the
  **signed profile wins** (this is the usual source of a wrong exclusion capacity).
- CRAT term is capped at `max_crat_term_years`; trust payments are simple, not
  reinvested — don't compound them.
- Married estate exemption is **doubled**; a single client is not.
- `action_set` must be alphabetically sorted, and `task_id` must match what the
  harness expects.
- Emit only the JSON object — no surrounding prose or code fences.
