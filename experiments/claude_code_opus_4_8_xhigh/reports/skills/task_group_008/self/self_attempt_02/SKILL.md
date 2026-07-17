---
name: private-wealth-advisory-structured-planning
description: >
  Solve private-wealth advisory planning tasks (Roth conversion / RMD tax,
  ILIT Crummey funding, GRAT-vs-CRAT comparison, integrated estate-liquidity
  action plans) by querying a read-only advisory HTTP API, resolving
  conflicting source documents by a fixed priority, and emitting a single
  strict JSON object that conforms to the task's answer_template. Use this
  whenever the prompt says "private wealth advisory team", references a client
  like CLT-####, and an answer_template.json defines analysis_type one of
  roth_conversion_rmd, ilit_crummey_implementation, trust_comparison, or
  estate_liquidity_action_plan.
---

# Private Wealth Advisory — Structured Planning SOP

You are given a client (e.g. `CLT-1003`), a `request_memo.md` with engagement
context (sometimes a planning horizon year), and an `answer_template.json` that
defines the EXACT output schema. The only data source is a remote HTTP API.
Return **one JSON object only**, no prose, USD rounded to cents, ISO dates
`YYYY-MM-DD`.

## 0. Standard operating procedure (do this every task)

1. Read `prompt.txt`, `payloads/request_memo.md`, and
   `payloads/answer_template.json`. The template's `analysis_type` enum tells
   you which of the 4 analyses to run; the `required_top_level_keys` and
   `fields` map tell you every key, type, and allowed enum value. **Mirror the
   template exactly** — produce every required key, use only listed enum values.
2. Pull all relevant API data for the client (see §1).
3. Resolve conflicting source documents (see §2) BEFORE computing anything.
4. Run the analysis-specific formulas (see §4–§7).
5. Set `task_id` to the task's stable id (e.g. `train_003` / `test_003`; infer
   from the task folder name; if unknown use `train_00X`/`test_00X` matching the
   client index), and `client_id` to the exact client id string.
6. Emit JSON. Numbers are JSON numbers (not strings), rounded to 2 decimals.
   Sort any `action_set` list ALPHABETICALLY.

## 1. API usage (base URL from `environment_access.md`, usually
`<remote-env-url>`)

Use `curl -s` via Bash. If you run helper scripts use `python` (not `python3`).

| Endpoint | Use for |
|---|---|
| `GET /api/health` | liveness sanity check |
| `GET /api/clients/<id>` | base client record (age, filing_status, planning_year, estate_value, liquid_assets, marital_status) |
| `GET /api/source-documents?client_id=<id>` | conflicting profile docs (CRM_NOTE, ATTORNEY_MEMO, SIGNED_PROFILE), each with `source_type`, `effective_date`, `facts{}` |
| `GET /api/retirement-accounts?client_id=<id>` | `CUSTODIAN_EXPORT`: traditional_balance, roth_balance, expected_return, rmd_start_age, recommended_conversion_years |
| `GET /api/life-insurance?client_id=<id>` | death_benefit, annual_premium, planned_contribution_date, proposed_owner, is_existing_policy_transfer |
| `GET /api/trust-candidates?client_id=<id>` | asset_value, expected_growth_rate, grat_term_years, grat_annuity_rate, crat_term_years, crat_payout_rate |
| `GET /api/policies/tax` | annual_gift_exclusion{year}, estate_tax_exemption{year}, estate_tax_rate, conversion_bracket_targets{MFJ/SINGLE/HOH}, max_crat_term_years, charitable_deduction_rate |
| `GET /api/rmd-factors` | age → RMD divisor map (73→26.5 … 99→6.8) |

**Always fetch the live tax policy and rmd-factors** — do not hardcode the
numbers below; they are illustrative of the observed shape and may change per
task. Observed constants: gift exclusion 2025=19000 / 2026=20000; estate
exemption 2025=13,990,000 / 2026=13,610,000; estate_tax_rate=0.40;
conversion bracket targets MFJ=394600 / SINGLE=197300 / HOH=263500;
max_crat_term_years=20; charitable_deduction_rate=0.35.

## 2. Conflicting-source resolution (THE central trap)

Each client has 3 profile docs that DISAGREE. The stale `CRM_NOTE` is a
distractor — it often inflates `philanthropic_intent` to "high" or lowers
`beneficiary_count`, which would flip the recommendation if you trusted it.
**Resolve by source priority, not by reading whichever doc you saw first.**

Priority (highest → lowest), matching the enum order in the templates:

```
SIGNED_PROFILE  >  ATTORNEY_MEMO  >  CUSTODIAN_EXPORT  >  CRM_NOTE  >  STALE_MARKETING_INTAKE
```

Tiebreak within equal priority: newer `effective_date` wins. (Observed dates:
CRM_NOTE 2025-11-20, ATTORNEY_MEMO 2026-01-18, SIGNED_PROFILE 2026-02-06 — so
recency and priority agree, but always apply PRIORITY first.)

Field-class controllers (what `source_resolution.*` must report):

- **Profile / goal / beneficiary facts** (annual_non_ira_income,
  marginal_tax_rate, beneficiary_count, philanthropic_intent,
  family_transfer_priority, age, filing_status, liquid_assets):
  `SIGNED_PROFILE` controls when present (it is the most complete doc). Report
  `controlling_profile_source` / `controlling_goal_source` /
  `controlling_beneficiary_source` = `SIGNED_PROFILE`.
- **Account facts** (traditional/roth balances, returns, rmd_start_age):
  the `retirement-accounts` export → `controlling_account_source` =
  `CUSTODIAN_EXPORT`.
- **Policy facts** (death_benefit, annual_premium, transfer flag): the
  `life-insurance` export. For `controlling_policy_source` choose the export
  source if the policy data comes from the custodian/insurer export, else
  `SIGNED_PROFILE`. Default to `CUSTODIAN_EXPORT` when the value originates from
  the life-insurance endpoint.
- **Asset facts** for trust comparison (estate_value, trust asset_value):
  `estate_value` appears in both ATTORNEY_MEMO and SIGNED_PROFILE (equal value);
  the trust `asset_value` comes from `trust-candidates`. For
  `controlling_asset_source`, prefer `ATTORNEY_MEMO` if its enum is offered and
  it supplies the estate/asset figure, otherwise `SIGNED_PROFILE`.

**Rule of thumb:** take each needed field from the highest-priority document
that actually contains it. SIGNED_PROFILE carries nearly everything; fall back
to ATTORNEY_MEMO then CRM_NOTE only for fields SIGNED_PROFILE omits.

## 3. Rounding, dates, enums

- Round every USD field to 2 decimals (cents). Keep year fields as integers.
- ISO dates `YYYY-MM-DD`.
- Use ONLY enum values listed in the template field descriptions. Never invent.
- `action_set` (estate plan) MUST be alphabetically sorted.

---

## 4. analysis_type = `roth_conversion_rmd`

Inputs: client (age, filing_status, planning_year), SIGNED_PROFILE
(marginal_tax_rate, annual_non_ira_income), retirement export
(traditional_balance, roth_balance, expected_return r, rmd_start_age,
recommended_conversion_years), tax policy (conversion_bracket_targets),
rmd-factors. Horizon year comes from the memo.

Definitions and formulas:

- `first_rmd_year = planning_year + (rmd_start_age - age)`.
- `years_until_rmd = first_rmd_year - planning_year`.
- `conversion_years = recommended_conversion_years`.
- `conversion_years_positive = min(conversion_years, max(0, years_until_rmd))`
  — the conversion years that actually fit BEFORE RMDs begin.
- `first_conversion_year = planning_year`.
- Bracket headroom: `headroom = conversion_bracket_targets[filing_status]
  - annual_non_ira_income`.
- `annual_conversion_amount = min(headroom, traditional_balance /
  conversion_years)` (limit conversions so taxable income stays under the
  bracket target; never exceed the balance pace).
- `total_converted = annual_conversion_amount * conversion_years_positive`
  (you can only convert in the years before RMD; this keeps the legacy
  projection self-consistent). If a task's numbers imply the full
  `conversion_years` were used, compute both and prefer the one consistent with
  the RMD simulation below.
- `total_conversion_tax = total_converted * marginal_tax_rate`.

RMD projection — simulate year by year from `planning_year` to `horizon_year`
(inclusive). For each year grow the traditional balance by `(1+r)`, then if
`current_age >= rmd_start_age` withdraw `RMD = balance / rmd_factor[age]`, tax
it at `marginal_tax_rate`, and subtract it. Run TWO scenarios:

- **Baseline** (no conversion): accumulate `baseline_rmd_tax_through_horizon`.
- **Conversion**: in years `first_conversion_year .. first_conversion_year +
  conversion_years_positive - 1`, move `annual_conversion_amount` from
  traditional → roth (capped at remaining traditional) BEFORE growth; grow both
  accounts; take RMDs only on the (smaller) traditional balance. Accumulate
  `conversion_rmd_tax_through_horizon`.
- `rmd_tax_savings_through_horizon = baseline_rmd_tax_through_horizon -
  conversion_rmd_tax_through_horizon` (positive = conversion helps).

Legacy projection (use the conversion scenario's end balances at horizon):

- `projected_roth_balance_horizon` = roth balance at horizon.
- `projected_traditional_balance_horizon` = traditional balance at horizon.
- `heir_tax_profile`: ratio `roth/(roth+trad)` at horizon →
  `MOSTLY_TAX_FREE` if roth fraction ≳ 0.6, `MOSTLY_TAXABLE` if ≲ 0.3,
  else `MIXED_TAXABLE_AND_TAX_FREE`.

Recommendation:

- `primary_action`: `NO_CONVERSION` if `headroom <= 0` (no room to convert in
  bracket); `DEFER` if the window is essentially gone (`years_until_rmd <= 0`,
  i.e. already at/over RMD age with negligible benefit); otherwise
  `STAGED_ROTH_CONVERSION` when `rmd_tax_savings_through_horizon > 0`.
- `suitability`: `SUITABLE` when staged conversion with clear savings and the
  conversion tax is comfortably covered by liquid assets; `DEFER` when
  primary_action is DEFER; else `BORDERLINE`.
- `risk_flag`: `RMD_NEAR_TERM` if the client is at/near RMD age
  (`years_until_rmd <= 1`); `LIQUIDITY_CONSTRAINT` if cumulative conversion tax
  approaches/exceeds `liquid_assets`; otherwise `TAX_BRACKET_MANAGEMENT`.

`source_resolution`: `controlling_profile_source = SIGNED_PROFILE`,
`controlling_account_source = CUSTODIAN_EXPORT`.

---

## 5. analysis_type = `ilit_crummey_implementation`

Inputs: client (planning_year, estate_value), SIGNED_PROFILE
(beneficiary_count — NOT the CRM count), life-insurance (death_benefit,
annual_premium, planned_contribution_date, is_existing_policy_transfer), tax
policy (annual_gift_exclusion, estate_tax_exemption, estate_tax_rate).

Gift plan:

- `planning_year` from client.
- `annual_exclusion_per_beneficiary = annual_gift_exclusion[planning_year]`.
- `beneficiary_count` = SIGNED_PROFILE beneficiary_count.
- `annual_exclusion_capacity = annual_exclusion_per_beneficiary *
  beneficiary_count`.
- `annual_premium` from policy.
- `premium_gap`: the shortfall of exclusion vs premium. Report
  `max(0, annual_premium - annual_exclusion_capacity)` (a "gap" is non-negative;
  if exclusion fully covers the premium the gap is 0). Keep the raw signed value
  internally to drive the risk flag.

Administration (Crummey 30-day withdrawal window):

- `contribution_date` = policy `planned_contribution_date`.
- `notice_due_date` = the contribution date (Crummey notices issued at/by the
  contribution date).
- `withdrawal_window_end` = `contribution_date + 30 days`.
- `earliest_premium_payment_date` = `withdrawal_window_end + 1 day` (premium
  paid only after the withdrawal window closes).
- `notices_required` = `beneficiary_count` (one notice per Crummey beneficiary).
- `dedicated_bank_account_required` = `true` (ILIT best practice; a separate
  trust account preserves the gift/Crummey formalities).

Estate result:

- `death_benefit` from policy.
- `estate_inclusion_risk` (= `recommendation.risk_flag`), decided by two flags:
  - lookback = `is_existing_policy_transfer` (transferring an EXISTING policy
    triggers the IRC 2035 three-year lookback).
  - shortfall = `annual_premium > annual_exclusion_capacity`.
  - Combine: both → `THREE_YEAR_LOOKBACK_AND_EXCLUSION_SHORTFALL`; only
    transfer → `THREE_YEAR_LOOKBACK`; only shortfall → `EXCLUSION_SHORTFALL`;
    neither → `LOW_IF_FORMALITIES_MET`.
- `projected_outside_estate_if_implemented` = `death_benefit` if the policy is
  newly issued by the ILIT (no lookback); if it's an existing-policy transfer
  under the 3-year lookback, treat it as still includible → `0` (or note the
  lookback) until 3 years pass.
- `tax_liquidity_support` = the portion of the death benefit usable to cover
  estate tax = `min(death_benefit, estate_tax_exposure)` where
  `estate_tax_exposure = max(0, estate_value - estate_tax_exemption[year]) *
  estate_tax_rate`. (If the policy fully covers exposure, this equals exposure;
  otherwise the death_benefit.)

Recommendation:

- `primary_action`: if no shortfall and no lookback →
  `FUND_WITH_CRUMMEY_NOTICES`; if shortfall only →
  `USE_LIFETIME_EXEMPTION_FOR_SHORTFALL`; if lookback (existing transfer) →
  `USE_NEW_POLICY_OR_ACCEPT_LOOKBACK`; if both →
  `DISCLOSE_LOOKBACK_AND_USE_EXEMPTION`.
- `suitability`: `SUITABLE_WITH_ADMINISTRATION` when risk is
  `LOW_IF_FORMALITIES_MET`; `BORDERLINE` for a single issue;
  `NOT_SUITABLE` only if structurally broken.
- `risk_flag` = the `estate_inclusion_risk` computed above.

`source_resolution`: `controlling_beneficiary_source = SIGNED_PROFILE`,
`controlling_policy_source = CUSTODIAN_EXPORT` (life-insurance export).

---

## 6. analysis_type = `trust_comparison` (GRAT vs CRAT)

Inputs: SIGNED_PROFILE goals (family_transfer_priority, philanthropic_intent),
client/ATTORNEY estate_value & liquid_assets, trust-candidates (asset_value V,
expected_growth_rate g, grat_term_years Tg, grat_annuity_rate ag,
crat_term_years Tc, crat_payout_rate pc), tax policy.

Estate context:

- `taxable_estate = max(0, estate_value - estate_tax_exemption[year])`.
- `estate_tax_exposure = taxable_estate * estate_tax_rate`.
- `liquidity_gap_before_planning = max(0, estate_tax_exposure - liquid_assets)`.

GRAT (annuity returns to grantor; remainder passes to heirs after term):

- annual annuity `A = V * ag`.
- `FV_assets = V * (1+g)^Tg`.
- `FV_annuity = A * ((1+g)^Tg - 1) / g` (ordinary-annuity future value).
- `projected_remainder_to_heirs = FV_assets - FV_annuity`.
- `estimated_estate_tax_reduction = projected_remainder_to_heirs *
  estate_tax_rate` (value removed from the taxable estate).
- `mortality_inclusion_risk = TERM_SURVIVAL_REQUIRED` (grantor must outlive the
  GRAT term or assets are pulled back into the estate).

CRAT (payout to income beneficiary for term; remainder to charity):

- payout `P = V * pc`; term `Tc` (cap at `max_crat_term_years`).
- `FV_assets = V * (1+g)^Tc`; `FV_payout = P * ((1+g)^Tc - 1)/g`.
- `projected_charitable_remainder = FV_assets - FV_payout`.
- `estimated_income_tax_deduction = V * charitable_deduction_rate` (charitable
  deduction approximated as asset value × the policy deduction rate).
- `family_transfer_fit`: CRAT sends the remainder to charity, so its fit for
  FAMILY transfer is `LOW` (use `MODERATE`/`HIGH` only if the data clearly shows
  family-directed remainder, which it normally does not for a CRAT).

Recommendation (driven by the CONTROLLING SIGNED_PROFILE goals, NOT the stale
CRM philanthropic_intent):

- If `philanthropic_intent == "high"` → `preferred_strategy = CRAT`,
  `rationale_code = PHILANTHROPIC_PRIORITY`,
  `alternate_role = SECONDARY_FAMILY_TRANSFER_TOOL`.
- Otherwise (family_transfer_priority high and philanthropy not the top goal) →
  `preferred_strategy = GRAT`, `rationale_code = CHILDREN_TRANSFER_PRIORITY`,
  `alternate_role = SECONDARY_CHARITABLE_TOOL`.
- IMPORTANT TRAP: CRM_NOTE may say philanthropic_intent="high" while the
  controlling SIGNED_PROFILE says "moderate"/"low". Use SIGNED_PROFILE → this
  usually yields GRAT. Do not be misled by the CRM into choosing CRAT.

`source_resolution`: `controlling_goal_source = SIGNED_PROFILE`,
`controlling_asset_source = ATTORNEY_MEMO` (or SIGNED_PROFILE if ATTORNEY_MEMO
lacks the figure).

---

## 7. analysis_type = `estate_liquidity_action_plan` (integrated)

Combines §5 (ILIT) and §6 (trust) plus an action set. Inputs: client,
SIGNED_PROFILE goals, life-insurance, trust-candidates, tax policy.

Estate context: same three formulas as §6 (taxable_estate, estate_tax_exposure,
liquidity_gap_before_planning).

`ilit` block:

- `annual_exclusion_capacity = annual_gift_exclusion[year] *
  beneficiary_count` (SIGNED_PROFILE count).
- `premium_gap = max(0, annual_premium - annual_exclusion_capacity)`.
- `estate_inclusion_risk`: same flag logic as §5 (lookback ∧/∨ shortfall).
- `projected_outside_estate_if_implemented` = death_benefit if no 3-year
  lookback, else 0.

`trust_transfer` block: run the §6 GRAT and CRAT math.

- `preferred_strategy` per §6 goal logic (usually GRAT).
- `projected_remainder_to_heirs` = GRAT remainder.
- `estimated_estate_tax_reduction` = GRAT remainder × estate_tax_rate.
- `projected_charitable_remainder` = CRAT remainder (report alongside).

`recommendation`:

- `primary_action`: if both an ILIT and a family-transfer GRAT are warranted →
  `COMBINE_ILIT_AND_GRAT`; if philanthropic priority dominates →
  `CRAT_WITH_LIQUIDITY_REVIEW`; if only the ILIT plus exemption work is needed →
  `ILIT_WITH_EXEMPTION_REVIEW`.
- `sequencing`: `ILIT_FIRST_THEN_GRAT` for the combined case;
  `TRUST_DECISION_FIRST` when the trust choice is the open question;
  `ILIT_FIRST_THEN_ATTORNEY_REVIEW` when legal drafting must follow funding.
- `risk_flag`: the ILIT `estate_inclusion_risk` flag.

`action_set`: list, **alphabetically sorted**, drawn ONLY from:
`ATTORNEY_DRAFT_REVIEW`, `CRAT_FOR_CHARITABLE_REMAINDER`,
`GRAT_FOR_APPRECIATING_SHARES`, `ILIT_CRUMMEY_NOTICE_CYCLE`,
`LIFETIME_EXEMPTION_ALLOCATION`. Include the items that apply: ILIT funding →
`ILIT_CRUMMEY_NOTICE_CYCLE`; appreciating-asset transfer via GRAT →
`GRAT_FOR_APPRECIATING_SHARES`; charitable remainder considered →
`CRAT_FOR_CHARITABLE_REMAINDER`; premium gap or estate above exemption →
`LIFETIME_EXEMPTION_ALLOCATION`; any trust drafting → `ATTORNEY_DRAFT_REVIEW`.
Always sort the final list alphabetically before output.

`source_resolution`: `controlling_goal_source = SIGNED_PROFILE`,
`controlling_policy_source = CUSTODIAN_EXPORT`.

---

## 8. Common pitfalls / self-checks

- **Do not trust CRM_NOTE.** It is the stale distractor. SIGNED_PROFILE controls
  beneficiary_count, philanthropic_intent, family_transfer_priority,
  marginal_tax_rate, income. Trusting CRM flips GRAT↔CRAT and the bene count.
- **`premium_gap` is a gap, not a signed difference** — report `max(0, …)`.
- **`conversion_years` vs `conversion_years_positive`**: only the positive
  (pre-RMD) years actually convert; keep total_converted and the legacy/RMD
  simulation consistent with `conversion_years_positive`.
- **RMD timing**: first RMD in the year the client reaches `rmd_start_age`
  (typically 73). Use the live rmd-factors map; for ages beyond the map clamp to
  the last available factor.
- **Estate exposure uses the planning-year exemption**, and rate is the policy
  `estate_tax_rate` (0.40). `liquidity_gap` is floored at 0.
- **Three-year lookback** is tied to `is_existing_policy_transfer == true`; a
  newly issued ILIT policy has NO lookback and the full death benefit sits
  outside the estate.
- **Output discipline**: single JSON object, every required key present, enums
  exact, USD to cents, dates ISO, `action_set` alphabetical, `task_id`/
  `client_id` strings. No prose, no markdown, no trailing commentary.
- **Always re-fetch tax policy and rmd-factors per task** — never assume the
  constants above are current for the specific task instance.

## 9. Minimal worked sanity numbers (method illustration, NOT answers)

These show the SHAPE of correct math; recompute from live data each time.

- Roth (MFJ, income 185k, target 394.6k): headroom = 209,600; with 7 conversion
  years and a 2.8M IRA, annual_conversion = min(209,600, 400,000) = 209,600;
  total_conversion_tax = 7×209,600×0.32. RMD savings come from the two-scenario
  year-by-year simulation through the horizon (baseline minus conversion).
- ILIT (4 beneficiaries, 2026): capacity = 20,000×4 = 80,000; premium 78,000 →
  premium_gap = 0, risk = LOW_IF_FORMALITIES_MET; notice window =
  contribution_date+30d, earliest premium = +1 more day.
- Estate (estate 24.6M, 2026 exemption 13.61M): taxable = 10.99M, exposure =
  4.396M, liquidity_gap = exposure − liquid_assets (floored at 0).
- GRAT (V=8M, g=8%, Tg=5, ag=4%): A=320k; FV_assets=8M×1.08^5;
  FV_annuity=320k×((1.08^5−1)/0.08); remainder = FV_assets − FV_annuity;
  estate_tax_reduction = remainder×0.40.
