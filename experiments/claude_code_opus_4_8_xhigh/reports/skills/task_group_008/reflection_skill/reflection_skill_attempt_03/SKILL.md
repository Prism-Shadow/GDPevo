---
name: private-wealth-advisory-planner
description: >-
  Produce structured JSON planning outputs for the private-wealth advisory benchmark backed by the
  read-only advisory API at http://127.0.0.1:8066 (or the harness API_BASE). Use this whenever a task
  asks you to prepare an advisory planning JSON for a client (IDs like CLT-xxxx) for any of these four
  analysis families: (1) Roth-conversion / RMD tax summaries (analysis_type roth_conversion_rmd),
  (2) ILIT / Crummey premium-cycle implementation (ilit_crummey_implementation), (3) GRAT-vs-CRAT
  trust comparisons (trust_comparison), or (4) integrated estate-liquidity action plans
  (estate_liquidity_action_plan). Trigger it for any "request_memo + answer_template" planning task
  involving Roth conversions, RMDs, ILITs, Crummey notices, gift-tax exclusion, GRATs/CRATs, estate-tax
  exemption, estate liquidity gaps, or source-document conflict resolution, even if the word "skill" is
  not used.
---

# Private Wealth Advisory Planner

You produce one strict JSON object that conforms to the task's `answer_template.json`, computed from
the live advisory API. The numbers are graded to the cent and the enums/dates exactly, so precision and
the right conventions matter more than anything else.

## Operating rules (read first)

- **Return only the JSON object.** No prose, no markdown fences, no trailing commentary. Numbers are
  JSON numbers (never strings). USD rounded to cents. Dates are ISO `YYYY-MM-DD`.
- **All client data comes from the API**, never your own knowledge. Base URL `http://127.0.0.1:8066`
  (use the harness `API_BASE` if provided). It is GET-only. Tax constants and RMD factors come from
  `/api/policies/tax` and `/api/rmd-factors`, not from memory of real-world IRS numbers.
- **Echo identifiers from the task**: `task_id` (e.g. `train_003`/`test_003`), `client_id`,
  `analysis_type` (the fixed enum for that family).
- **Compute, don't guess.** Write a small Python script that pulls the API, applies the formulas in
  `references/formulas.md`, and emits the JSON. A reusable helper lives in
  `scripts/advisory.py` — import it or copy its functions. Re-run and sanity-check before answering.

## Workflow

1. Read `prompt.txt`, `request_memo.md`, and `answer_template.json`. The template's `fields` block and
   `required_top_level_keys` are authoritative for which keys and enums to emit. The memo gives the
   `planning_year`, the `horizon_year` (Roth tasks), and engagement context.
2. Pull the client data you need:
   - `GET /api/clients/{client_id}` — header (age, marital_status, filing_status, planning_year, estate_value, liquid_assets).
   - `GET /api/source-documents?client_id=...` — the conflicting profile/goal documents. **Resolve conflicts** (see below).
   - `GET /api/retirement-accounts?client_id=...` — IRA export (Roth tasks).
   - `GET /api/life-insurance?client_id=...` — policy (ILIT / estate-liquidity tasks).
   - `GET /api/trust-candidates?client_id=...` — GRAT/CRAT parameters (trust / estate-liquidity tasks).
   - `GET /api/policies/tax` and `GET /api/rmd-factors` — constants.
3. Resolve source precedence and record the controlling sources.
4. Apply the per-family formulas in `references/formulas.md`. Verify intermediate numbers.
5. Apply the enum decision rules in `references/decision_rules.md`.
6. Emit JSON exactly matching the template.

## Source-precedence resolution (applies to every task)

Source documents are imported from different systems on different dates and **disagree on purpose**.
For household/profile/goal facts (age, income, marginal_tax_rate, beneficiary_count, filing/marital
status, philanthropic_intent, family_transfer_priority, estate_value, liquid_assets), precedence is:

```
SIGNED_PROFILE  >  ATTORNEY_MEMO  >  CRM_NOTE  >  STALE_MARKETING_INTAKE
(newest, signed, most complete)        (oldest, least trusted)
```

The **SIGNED_PROFILE** (the newest, signed, most complete document) controls. Do not let an older
CRM_NOTE override it just because it has a field — e.g. if CRM says `beneficiary_count=3` but the
SIGNED_PROFILE says `4`, use `4`. The client header (`/api/clients`) agrees with the SIGNED_PROFILE.

Controlling-source enum values to report:
- `controlling_profile_source` / `controlling_goal_source` / `controlling_beneficiary_source` → **`SIGNED_PROFILE`**.
- `controlling_account_source` → **`CUSTODIAN_EXPORT`** (IRA facts come only from the retirement export, whose `source_type` is `CUSTODIAN_EXPORT`).
- `controlling_policy_source` → **`SIGNED_PROFILE`** (the controlling household document governs policy/ILIT context, even though the dollar policy facts are read from the life-insurance record).
- `controlling_asset_source` → **`ATTORNEY_MEMO`** (trust/estate asset planning facts are governed by the attorney memo).

> Pitfall corrected from blind attempts: `controlling_policy_source` is **SIGNED_PROFILE**, not
> `CUSTODIAN_EXPORT`. The life-insurance and trust-candidate records have no `source_type` field — do
> not invent `CUSTODIAN_EXPORT` for them. The controlling *source* is the household document, by the
> precedence above.

## Conventions that bit the prior solver (apply everywhere)

- **Married couples get a doubled estate-tax exemption** (portability): `exemption_used = 2 ×
  estate_tax_exemption[planning_year]` when `marital_status == "married"` (filing MFJ); single filers
  use `1 ×`. Using the single exemption for a married client is the single biggest error to avoid.
- **`premium_gap` is floored at zero**: `premium_gap = max(0, annual_premium − annual_exclusion_capacity)`.
  Never report a negative gap; surplus capacity means the gap is `0.0`.
- **GRAT/CRAT annuity payments are NOT reinvested.** Remainder = `FV_of_assets − (annuity_payment ×
  term_years)`, i.e. grow the corpus at the growth rate and subtract the *plain sum* of payments made.
  Do not use a future-value-of-annuity (reinvested) formula.
- **Crummey window math** uses a 7-day notice lag then a 30-day withdrawal window (see formulas).
- **`conversion_years_positive`** is the count of years with a positive conversion amount, which equals
  `conversion_years` (conversions continue through the window even after RMDs start). It is **not** the
  count of years before RMD onset.
- **`tax_liquidity_support`** (ILIT task) is the household's `liquid_assets`, not `min(death_benefit,
  estate_tax_exposure)`.

## Reference files

- `references/formulas.md` — exact per-family formulas, the year-by-year RMD simulation order of
  operations, Crummey date arithmetic, GRAT/CRAT remainder formula, estate math. **Read this before
  computing any number.**
- `references/decision_rules.md` — every enum's decision rule and the `action_set` membership rules.
- `scripts/advisory.py` — reusable Python: API fetchers, controlling-fact resolver, the RMD simulator,
  GRAT/CRAT remainder, Crummey dates, estate math, and rounding helper. Import or adapt it.

## Final check before you answer

- Every key in the template's `required_top_level_keys` and `fields` is present, with the correct enum
  spelling and type.
- All USD values rounded to 2 decimals; all dates ISO; `action_set` (if present) sorted alphabetically.
- Married → doubled exemption applied; `premium_gap` floored at 0; trust remainder uses
  non-reinvested payments; `conversion_years_positive == conversion_years`.
- Output is the bare JSON object only.
