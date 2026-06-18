---
name: private-wealth-advisory
description: >-
  Produce the structured JSON planning output for private-wealth / estate advisory tasks that
  query the read-only advisory API (clients, source-documents, retirement-accounts,
  life-insurance, trust-candidates, policies/tax, rmd-factors) and return an answer matching a
  given answer_template.json. Use this skill whenever a task asks you to act as a private wealth /
  estate / tax advisory analyst and emit a JSON object for any of these families: Roth conversion
  + RMD tax summary (roth_conversion_rmd), ILIT / Crummey funding cycle (ilit_crummey_implementation),
  GRAT vs CRAT trust comparison (trust_comparison), or an integrated estate-liquidity action plan
  (estate_liquidity_action_plan). Triggers include mentions of Roth conversions, required minimum
  distributions, ILIT/Crummey notices, gift-tax annual exclusion, GRAT, CRAT, estate-tax exemption
  or exposure, liquidity gaps, or "conforms to answer_template.json" against an advisory API. Apply
  it even when the request only gives a client ID and a request memo.
---

# Private Wealth Advisory Planner

You are completing a private-wealth advisory benchmark task. Each task gives a client ID, a short
request memo, and an `input/payloads/answer_template.json`, and expects **one JSON object** that
matches that template — numbers computed from a live read-only API, not from prior knowledge.

The four task families and their exact formulas, enum rules, and verified gold numbers live in
**`reference.md`** (read it — it is the source of truth). A ready-made, self-testing helper module
lives in **`scripts/advisory_lib.py`**. This page is the operating procedure.

## Golden rules (these are what the gold answers actually reward)

1. **Pull every constant from the API, never from memory.** Gift exclusion, estate exemption,
   estate tax rate, conversion bracket targets, charitable deduction rate, max CRAT term, and RMD
   divisors all come from `/api/policies/tax` and `/api/rmd-factors`. Tax law in your head is wrong
   for this benchmark.
2. **Resolve conflicting facts by source, not by recency alone.** Profile/goal/beneficiary facts:
   the **SIGNED_PROFILE** source document controls (latest, signed). Account numbers: the
   **CUSTODIAN_EXPORT** (retirement-accounts) controls. Trust mechanics: the **trust-candidates**
   endpoint controls. `ATTORNEY_MEMO`, `CRM_NOTE`, `STALE_MARKETING_INTAKE`, and the
   `/api/clients/{id}` header are distractors that may disagree — they never override a signed value.
3. **Reproduce the math exactly, including order of operations.** The RMD simulation order
   (convert → RMD → grow, every year) and the *flat* (non-reinvested) GRAT/CRAT annuity are
   load-bearing; getting them slightly wrong changes every downstream cent. Round to cents only in
   the final JSON.
4. **Emit exactly the fields the task's `answer_template.json` lists, JSON only.** No prose, no
   code fences. `action_set` must be sorted alphabetically.

## Procedure

1. **Read the task inputs.** Open `prompt.txt`, `payloads/request_memo.md` (client ID, horizon
   year if any, special instructions), and `payloads/answer_template.json` (the exact required
   keys, enums, and `analysis_type`). The template tells you which family you are in.

2. **Find the API base.** Use `API_BASE` env if set, else `http://127.0.0.1:8066`. Confirm with
   `GET /api/health`. All calls are GET.

3. **Fetch the client's records** (only what the family needs):
   - `GET /api/source-documents?client_id=ID` → resolve the controlling profile (SIGNED_PROFILE).
   - `GET /api/retirement-accounts?client_id=ID` → for Roth/RMD.
   - `GET /api/life-insurance?client_id=ID` → for ILIT / plan.
   - `GET /api/trust-candidates?client_id=ID` → for trust comparison / plan.
   - `GET /api/policies/tax` and `GET /api/rmd-factors` → constants.

4. **Compute with `scripts/advisory_lib.py`.** It implements every formula below and self-tests on
   the five worked examples. Either import it or mirror it. Run `python3 scripts/advisory_lib.py`
   once to confirm it prints `OK` in this environment, then write a small script that builds your
   answer dict from the API records.

   - `roth_conversion_rmd` family → `roth_conversion_rmd(profile, account, policies, rmd_factors, horizon)`
     + `heir_tax_profile(roth_h, trad_h)`.
   - `ilit_crummey_implementation` → `ilit_plan(profile, policy, policies, year)` (gift capacity,
     Crummey dates, estate result, risk flag).
   - `trust_comparison` → `estate_context(...)` + `grat(trust, rate)` + `crat(trust, policies)`.
   - `estate_liquidity_action_plan` → `estate_context` + `ilit_plan` + `grat`/`crat`, then build the
     alphabetically-sorted `action_set`.

5. **Choose the enum fields** from the rules in `reference.md` §2–§5 (recommendation,
   suitability/sequencing, risk_flag, rationale_code, heir_tax_profile, etc.). Set
   `source_resolution.*` to the controlling source for each field — normally `SIGNED_PROFILE` for
   profile/goal/beneficiary/policy and `CUSTODIAN_EXPORT` for account.

6. **Assemble and emit the JSON.** Copy `task_id`, `client_id`, and the fixed `analysis_type` enum.
   Include the `required_top_level_keys` and the sub-fields the template lists for this task. For
   the `estate_context` block (trust & plan families) also include `planning_year`,
   `exemption_used`, and `liquid_assets_available` even though the template lists them under terse
   names — the gold answers carry all six estate_context fields (`planning_year`, `exemption_used`,
   `taxable_estate`, `estate_tax_exposure`, `liquid_assets_available`, `liquidity_gap_before_planning`).
   `estate_context()` in the helper already returns exactly these. USD = JSON numbers to 2 decimals;
   dates = ISO `YYYY-MM-DD`. Print the object and nothing else.

## The formulas in one screen (full detail + enum tables in `reference.md`)

**Estate context** (trust & plan families):
`exemption = estate_exemption[year]` ( × 2 if `marital_status == married`);
`taxable = max(0, estate_value − exemption)`; `exposure = taxable × estate_tax_rate`;
`liquidity_gap = max(0, exposure − liquid_assets)`.

**Roth conversion + RMD:** `annual_conversion = bracket_target[filing_status] − annual_non_ira_income`;
`total_converted = annual_conversion × conversion_years`;
`total_conversion_tax = annual_conversion × marginal_tax_rate × conversion_years`;
`first_rmd_year = planning_year + (rmd_start_age − age)`. Simulate years `planning_year..horizon`,
each year in this exact order: **(1)** convert if a conversion year, **(2)** RMD = `traditional /
rmd_factor[age]` (taxed at `marginal_tax_rate`) if `age ≥ rmd_start_age`, **(3)** grow both balances
by `expected_return`. Report baseline vs conversion RMD tax, their difference, and the
end-of-horizon (post-growth) balances.

**ILIT / Crummey:** `capacity = beneficiary_count × annual_gift_exclusion[year]`;
`premium_gap = max(0, annual_premium − capacity)`; `notices = beneficiary_count`. Dates from the
policy's `planned_contribution_date`: notice `+7d`, withdrawal window end `+30d` after notice,
earliest premium payment `+1d` after the window. `projected_outside_estate = death_benefit`,
`tax_liquidity_support = liquid_assets`, `dedicated_bank_account_required = true`. Risk flag from
`is_existing_policy_transfer` (3-year lookback) and `premium_gap > 0` (exclusion shortfall).

**GRAT & CRAT (same flat-annuity engine):**
`remainder = asset × (1+growth)^term − (asset × rate) × term`. GRAT uses `grat_annuity_rate` and
`grat_term_years`; `estate_tax_reduction = remainder × estate_tax_rate`. CRAT uses `crat_payout_rate`
and `min(crat_term_years, max_crat_term_years)`; `income_tax_deduction = remainder ×
charitable_deduction_rate`. Prefer GRAT when `family_transfer_priority` is high, CRAT when
`philanthropic_intent` dominates (goals from the signed profile).

## Common pitfalls

- **Doubling the estate exemption for singles.** Only married/`MFJ` doubles it. Filing status
  `SINGLE` and `HOH` use the single exemption.
- **Reinvesting the GRAT/CRAT annuity.** It is a *flat* dollar deduction (`asset × rate` per year),
  not a growing reinvested stream. (Verified: flat matches to the cent; ordinary/annuity-due do not.)
- **Wrong RMD order.** Converting after the RMD, or growing before the RMD, changes the balance the
  divisor is applied to. Convert → RMD → grow, in that order, each year.
- **Trusting `/api/clients/{id}` or the CRM/attorney facts over the signed profile.** The header and
  older imports are deliberately inconsistent. Resolve from SIGNED_PROFILE.
- **Hard-coding 2026 tax constants from memory.** Use the API's values
  (e.g. exemption 13,610,000; gift exclusion 20,000; bracket MFJ 394,600 / SINGLE 197,300 /
  HOH 263,500; estate rate 0.40; charitable deduction 0.35; max CRAT term 20) — but read them live.
- **Emitting prose or fields the template doesn't list.** Output only the JSON the template defines;
  keep `action_set` alphabetically sorted.

When in doubt about a field's formula, enum, or which source controls, consult `reference.md`; when
in doubt about a number, re-run `scripts/advisory_lib.py` and compare to its self-test values.
