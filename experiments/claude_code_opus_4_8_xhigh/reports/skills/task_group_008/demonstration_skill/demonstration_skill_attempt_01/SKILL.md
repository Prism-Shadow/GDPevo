---
name: private-wealth-advisory-planning
description: >
  Produce structured JSON planning outputs for a private-wealth advisory benchmark backed by a
  read-only advisory API (Roth-conversion/RMD tax summaries, ILIT/Crummey funding cycles,
  GRAT-vs-CRAT trust comparisons, and integrated estate-liquidity action plans). Use this skill
  whenever a task asks for a structured advisory planning JSON for a client ID (e.g. CLT-xxxx),
  references an answer_template.json with fields like conversion_plan, rmd_projection, gift_plan,
  administration, grat/crat, estate_context, ilit, trust_transfer, action_set, or source_resolution,
  or mentions Roth conversions, RMDs, ILIT Crummey notices, GRAT, CRAT, estate-tax exemption, or
  estate liquidity. It encodes the exact source-conflict resolution rules, numeric formulas, RMD
  year-by-year simulation order, date arithmetic, enum decision rules, rounding, and output schema
  the gold answers require, so apply it even when the prompt does not name a specific strategy by name.
---

# Private Wealth Advisory Planning

You are producing a single JSON object that conforms to a provided `answer_template.json`. All numbers
come from a live read-only API, never from your own tax knowledge. Reproduce the exact conventions
below — they were reverse-engineered from verified gold answers and every formula here was checked to
reproduce real gold numbers to the cent.

## 0. Workflow

1. Read `input/prompt.txt`, `input/payloads/request_memo.md`, and `input/payloads/answer_template.json`.
   The memo gives the `client_id`, the engagement type, and sometimes a **planning horizon year**.
   The template's `analysis_type` enum tells you which of the four task families you are in.
2. Resolve the API base URL. It is usually the env var `API_BASE`; otherwise default to
   `http://127.0.0.1:8066`. The API is GET-only.
3. Pull every relevant record for the client (see §1) and resolve conflicting facts (§2).
4. Compute the family-specific fields using the formulas in this file (and `references/formulas.md`).
   **Do the math in code (Python), not by hand.** A small script eliminates arithmetic and
   compounding-order errors and lets you re-run cleanly.
5. Fill the template, applying rounding and date rules (§3), and emit **only** the JSON object — no
   prose, no markdown fences.

The four families and their reference sections:

| `analysis_type`               | Family                          | Section |
| ----------------------------- | ------------------------------- | ------- |
| `roth_conversion_rmd`         | Roth conversion + RMD summary   | §4      |
| `ilit_crummey_implementation` | ILIT / Crummey funding cycle    | §5      |
| `trust_comparison`            | GRAT vs CRAT comparison         | §6      |
| `estate_liquidity_action_plan`| Integrated estate-liquidity plan| §7      |

## 1. API endpoints

| Endpoint | Use |
| --- | --- |
| `GET /api/clients/{client_id}` | header record (name, age, marital_status, filing_status, estate_value, liquid_assets) |
| `GET /api/source-documents?client_id=...` | conflicting fact documents (CRM_NOTE, ATTORNEY_MEMO, SIGNED_PROFILE) |
| `GET /api/retirement-accounts?client_id=...` | IRA export (CUSTODIAN_EXPORT): traditional/roth balances, expected_return, rmd_start_age, recommended_conversion_years |
| `GET /api/life-insurance?client_id=...` | policy: death_benefit, annual_premium, planned_contribution_date, is_existing_policy_transfer |
| `GET /api/trust-candidates?client_id=...` | GRAT/CRAT params: asset_value, expected_growth_rate, grat_term_years, grat_annuity_rate, crat_term_years, crat_payout_rate |
| `GET /api/policies/tax` | planning constants (see below) |
| `GET /api/rmd-factors` | RMD divisor by age (integer-keyed) |

Always read tax constants and RMD divisors **from the API**, never from memory. The constants object
includes: `annual_gift_exclusion` (by year), `estate_tax_exemption` (by year), `estate_tax_rate`,
`conversion_bracket_targets` (by filing status: MFJ/SINGLE/HOH), `max_crat_term_years`,
`charitable_deduction_rate`. Use the planning year (typically 2026) to index the year-keyed maps.

## 2. Source-of-truth resolution (critical)

The same fact can appear in several `source-documents` with different values because they were imported
from different systems at different times. Resolution is **by the type of fact**, not simply "most
recent wins". Each fact category has a designated authoritative source type:

- **Client goals & profile facts** (philanthropic_intent, family_transfer_priority, beneficiary_count,
  marginal_tax_rate, annual_non_ira_income, age, filing_status, marital_status, liquid_assets) →
  **SIGNED_PROFILE**. It is the most recent (2026-02-06), it is signed, and it is the only document
  carrying the full tax/beneficiary detail. It overrides the older CRM_NOTE (2025-11-20, treat as
  stale) and the ATTORNEY_MEMO for these fields.
- **Estate / asset valuations** (estate_value and other asset figures) → **ATTORNEY_MEMO**. The
  attorney is the authority for estate valuation. Record the controlling asset/estate source as
  `ATTORNEY_MEMO` even when the signed profile happens to agree on the number.
- **Retirement / IRA accounts** → **CUSTODIAN_EXPORT** (the `retirement-accounts` endpoint).
- **Insurance policy facts** → the `life-insurance` endpoint, reported as **SIGNED_PROFILE** for the
  `controlling_policy_source` field (the signed profile governs the household's policy/beneficiary
  intent in these tasks).
- **CRM_NOTE is always stale** — never select it as a controlling source.

Fill the `source_resolution.*` enum fields accordingly. Observed gold pattern across families:
`controlling_profile_source`/`controlling_goal_source`/`controlling_beneficiary_source`/
`controlling_policy_source` = `SIGNED_PROFILE`; `controlling_account_source` = `CUSTODIAN_EXPORT`;
`controlling_asset_source` = `ATTORNEY_MEMO`.

When a numeric input has both a client-header value and a signed-profile value and they agree, either
works; if they disagree, use the signed-profile value for profile facts and the attorney-memo value
for estate/asset facts.

## 3. Output conventions

- **Money**: JSON numbers (not strings), rounded to **2 decimals (cents)**. Round once at the end of
  each field's computation. Integer-valued dollars still render with `.0` (e.g. `80000.0`).
- **Years / counts / beneficiary_count / notices_required**: integers.
- **Dates**: ISO `YYYY-MM-DD` strings.
- **Booleans**: real JSON booleans.
- **`task_id`**: use the task id implied by the harness (e.g. `train_00N` / `test_00N`). If the input
  folder name encodes it, mirror it; otherwise echo what the prompt/memo gives.
- Echo `client_id` and the template's fixed `analysis_type` literal verbatim.
- `action_set` (family §7) must be **sorted alphabetically**.
- Emit only the JSON object. No surrounding prose or code fences.

## 4. Roth conversion + RMD (`roth_conversion_rmd`)

Inputs: signed profile (`annual_non_ira_income`, `marginal_tax_rate`, `age`, `filing_status`,
`planning_year`); IRA export (`traditional_balance`, `roth_balance`, `expected_return`,
`rmd_start_age`, `recommended_conversion_years`); `conversion_bracket_targets[filing_status]`;
`rmd-factors`; horizon year from the memo.

**Conversion sizing**
- `annual_conversion_amount = conversion_bracket_targets[filing_status] − annual_non_ira_income`
  (fill the top of the bracket each year).
- `conversion_years = conversion_years_positive = recommended_conversion_years` (from the IRA export).
- `first_conversion_year = planning_year`.
- `total_converted = annual_conversion_amount × conversion_years`.
- `total_conversion_tax = total_converted × marginal_tax_rate`.
- `first_rmd_year = planning_year + (rmd_start_age − current_age)`.

**Year-by-year simulation (planning_year … horizon, inclusive).** This exact order of operations
matters — it was the only ordering that reproduced gold to the cent. For each year, with
`age = start_age + (year − planning_year)`:

1. **Conversion** (conversion scenario only, and only while `year < planning_year + conversion_years`):
   `amt = min(annual_conversion_amount, traditional)`; `traditional −= amt`; `roth += amt`.
2. **RMD** (only if `age ≥ rmd_start_age` and the age exists in the factor table):
   `rmd = traditional / rmd_factor[age]`; `traditional −= rmd`;
   `rmd_tax += rmd × marginal_tax_rate`.
3. **Growth** (apply last): `traditional ×= (1 + expected_return)`; `roth ×= (1 + expected_return)`.

Run the simulation twice:
- **Baseline** (no conversions) → `baseline_rmd_tax_through_horizon` = accumulated `rmd_tax`.
- **Conversion** (with conversions) → `conversion_rmd_tax_through_horizon` = accumulated `rmd_tax`,
  and the ending balances are `projected_traditional_balance_horizon` and
  `projected_roth_balance_horizon`.
- `rmd_tax_savings_through_horizon = baseline − conversion`.

The projected balances reported are from the **conversion** scenario.

**Enums**
- `primary_action`: `STAGED_ROTH_CONVERSION` when `annual_conversion_amount > 0` and conversions reduce
  RMD tax (savings > 0) — the normal case. Use `DEFER` if filling the bracket leaves no room
  (`annual_conversion_amount ≤ 0`) but conversion may help later; `NO_CONVERSION` if conversion gives
  no benefit.
- `suitability`: `SUITABLE` when staged conversion is recommended with positive savings; `BORDERLINE`
  if savings are marginal or liquidity is tight; `DEFER` to wait.
- `risk_flag`: `TAX_BRACKET_MANAGEMENT` (default — the plan is about filling brackets);
  `RMD_NEAR_TERM` if the client is already at/over RMD age with little runway;
  `LIQUIDITY_CONSTRAINT` if paying conversion tax strains liquid assets.
- `heir_tax_profile` from the ending balance mix `share = roth / (roth + traditional)`:
  `MOSTLY_TAX_FREE` if `share ≥ 0.7`, `MOSTLY_TAXABLE` if `share ≤ 0.3`, else
  `MIXED_TAXABLE_AND_TAX_FREE`.

## 5. ILIT / Crummey implementation (`ilit_crummey_implementation`)

Inputs: gift exclusion for the planning year; signed-profile `beneficiary_count`; life-insurance
record (`death_benefit`, `annual_premium`, `planned_contribution_date`, `is_existing_policy_transfer`);
estate constants for the estate-inclusion side.

**Gift plan**
- `annual_exclusion_per_beneficiary = annual_gift_exclusion[planning_year]`.
- `beneficiary_count` = signed profile value.
- `annual_exclusion_capacity = annual_exclusion_per_beneficiary × beneficiary_count`.
- `annual_premium` = policy value.
- `premium_gap = max(0, annual_premium − annual_exclusion_capacity)`.

**Administration / Crummey dates** (start from policy `planned_contribution_date`):
- `contribution_date = planned_contribution_date`.
- `notice_due_date = contribution_date + 7 days` (notices go out within a week).
- `withdrawal_window_end = notice_due_date + 30 days` (30-day Crummey withdrawal window).
- `earliest_premium_payment_date = withdrawal_window_end + 1 day` (pay only after the window closes).
- `notices_required = beneficiary_count` (one Crummey notice per beneficiary).
- `dedicated_bank_account_required = true` (ILIT formalities require a dedicated account).

**Estate result**
- `death_benefit` = policy value.
- `projected_outside_estate_if_implemented = death_benefit` (a properly funded ILIT keeps the proceeds
  out of the estate).
- `tax_liquidity_support = death_benefit × estate_tax_rate` (the estate-tax-equivalent liquidity the
  policy provides).
- `estate_inclusion_risk` = the same value as `recommendation.risk_flag` (see below).

**Enums**
- `risk_flag` / `estate_inclusion_risk` logic:
  - Start from `LOW_IF_FORMALITIES_MET`.
  - If `is_existing_policy_transfer` is true → `THREE_YEAR_LOOKBACK` (transferring an existing policy
    triggers the IRC §2035 three-year lookback).
  - If `premium_gap > 0` → `EXCLUSION_SHORTFALL` (premium exceeds annual-exclusion capacity).
  - If both apply → `THREE_YEAR_LOOKBACK_AND_EXCLUSION_SHORTFALL`.
- `primary_action`:
  - `FUND_WITH_CRUMMEY_NOTICES` when `premium_gap == 0` and not a transfer (clean new-policy funding).
  - `USE_LIFETIME_EXEMPTION_FOR_SHORTFALL` when `premium_gap > 0` only.
  - `USE_NEW_POLICY_OR_ACCEPT_LOOKBACK` when it is an existing-policy transfer (lookback) only.
  - `DISCLOSE_LOOKBACK_AND_USE_EXEMPTION` when both shortfall and lookback apply.
- `suitability`: `SUITABLE_WITH_ADMINISTRATION` in the clean case (workable if formalities are kept);
  `BORDERLINE` if there is a shortfall or lookback wrinkle to manage; `NOT_SUITABLE` only if the plan
  fundamentally fails.

## 6. GRAT vs CRAT comparison (`trust_comparison`)

Inputs: trust candidate (`asset_value` A, `expected_growth_rate` g, `grat_term_years`,
`grat_annuity_rate`, `crat_term_years`, `crat_payout_rate`); estate constants; signed-profile goals.

**Estate context** (estate_value from attorney memo; marital status from signed profile):
- `exemption_used = estate_tax_exemption[planning_year] × (2 if married else 1)`.
- `taxable_estate = max(0, estate_value − exemption_used)`.
- `estate_tax_exposure = taxable_estate × estate_tax_rate`.
- `liquid_assets_available` = signed-profile `liquid_assets`.
- `liquidity_gap_before_planning = max(0, estate_tax_exposure − liquid_assets_available)`.
- Include `planning_year` and these fields per the template (some templates list them under
  `estate_context`).

**GRAT** (zeroed-out-style annuity, nominal annuity payments — *not* future-valued):
- `projected_remainder_to_heirs = A × (1 + g)^grat_term − A × grat_annuity_rate × grat_term`.
- `estimated_estate_tax_reduction = projected_remainder_to_heirs × estate_tax_rate`.
- `mortality_inclusion_risk = TERM_SURVIVAL_REQUIRED` (grantor must outlive the term).
- `grat.term_years = grat_term_years`.

**CRAT** (same nominal-payout structure):
- `projected_charitable_remainder = A × (1 + g)^crat_term − A × crat_payout_rate × crat_term`.
- `estimated_income_tax_deduction = projected_charitable_remainder × charitable_deduction_rate`.
- `crat.term_years = crat_term_years` (use the candidate's term, typically capped at `max_crat_term_years`).
- `family_transfer_fit`: `LOW` when family transfer is the priority (a CRAT gives nothing to heirs),
  `MODERATE`/`HIGH` only if the goals lean charitable enough that a CRAT serves the family too.

**Recommendation** (driven by signed-profile goals):
- If `family_transfer_priority` outranks `philanthropic_intent` (high vs lower) →
  `preferred_strategy = GRAT`, `rationale_code = CHILDREN_TRANSFER_PRIORITY`,
  `alternate_role = SECONDARY_CHARITABLE_TOOL`.
- If `philanthropic_intent` outranks family transfer → `preferred_strategy = CRAT`,
  `rationale_code = PHILANTHROPIC_PRIORITY`, `alternate_role = SECONDARY_FAMILY_TRANSFER_TOOL`.
- Treat the ordinal scale `low < moderate < high`. A tie defaults to the family-transfer (GRAT) reading
  unless the engagement clearly emphasizes philanthropy.

## 7. Integrated estate-liquidity action plan (`estate_liquidity_action_plan`)

Combine the estate context (§6), the ILIT (§5), and the trust transfer (§6) for one client.

- **estate_context**: same formulas as §6 (`exemption_used`, `taxable_estate`, `estate_tax_exposure`,
  `liquid_assets_available`, `liquidity_gap_before_planning`, `planning_year`).
- **ilit** block: `annual_exclusion_capacity` and `premium_gap` from §5; `estate_inclusion_risk` from
  §5 risk logic; `projected_outside_estate_if_implemented = death_benefit`.
- **trust_transfer** block: pick the preferred strategy with §6's goal rule, then report
  `preferred_strategy`, `projected_remainder_to_heirs` (GRAT remainder), `estimated_estate_tax_reduction`
  (GRAT remainder × estate_tax_rate), and `projected_charitable_remainder` (CRAT remainder). All three
  trust figures are reported regardless of which strategy is preferred.
- **recommendation**:
  - `primary_action`: `COMBINE_ILIT_AND_GRAT` when an ILIT plus a GRAT both fit (family-transfer
    priority, manageable ILIT); `CRAT_WITH_LIQUIDITY_REVIEW` when philanthropy leads;
    `ILIT_WITH_EXEMPTION_REVIEW` when a premium/exemption shortfall dominates.
  - `sequencing`: `ILIT_FIRST_THEN_GRAT` in the combined case (stand up the ILIT, then the GRAT);
    `TRUST_DECISION_FIRST` when the GRAT/CRAT choice gates everything;
    `ILIT_FIRST_THEN_ATTORNEY_REVIEW` when the ILIT is clear but the rest needs counsel.
  - `risk_flag`: the ILIT estate-inclusion risk (§5 logic) — `LOW_IF_FORMALITIES_MET` in the clean case.
- **action_set**: build from these enums and **sort alphabetically**:
  - `ATTORNEY_DRAFT_REVIEW` — essentially always (trust/ILIT docs need counsel).
  - `ILIT_CRUMMEY_NOTICE_CYCLE` — when an ILIT/policy is in play.
  - `GRAT_FOR_APPRECIATING_SHARES` — when the preferred trust strategy is GRAT.
  - `CRAT_FOR_CHARITABLE_REMAINDER` — when the preferred trust strategy is CRAT.
  - `LIFETIME_EXEMPTION_ALLOCATION` — when there is a `premium_gap > 0` (or exemption must absorb a
    shortfall). Include only the items the case actually calls for.

## 8. Pitfalls

- **Do not future-value the GRAT/CRAT annuity/payout stream.** The verified formula subtracts the
  *nominal* sum of payments (`A × rate × term`), not an annuity future value. An annuity-FV formula
  produces numbers that look plausible but are wrong.
- **RMD order is conversion → RMD → growth, every year.** Growing first, or taking the RMD before
  growth in the wrong order, changes every downstream balance. Apply growth last.
- **Conversions stop after `recommended_conversion_years`** but the simulation continues to the horizon.
- **Projected balances come from the conversion scenario**, not the baseline.
- **Married estate exemption is doubled** (`× 2`); single/HOH is not.
- **CRM_NOTE never controls.** Estate/asset facts come from the attorney memo; goals/profile from the
  signed profile; accounts from the custodian export.
- **`estate_inclusion_risk` mirrors `recommendation.risk_flag`** in the ILIT family.
- **Round to cents at the end**, keep numbers as JSON numbers, and emit only the JSON object.

See `references/formulas.md` for compact formula cards and a worked numeric check you can compare your
script against, and `references/worked_examples.md` for end-to-end traces of each family.
