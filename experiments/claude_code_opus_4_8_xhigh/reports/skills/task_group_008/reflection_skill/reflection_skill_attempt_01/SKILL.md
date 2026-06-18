---
name: private-wealth-advisory-planning
description: >-
  Produce the structured JSON planning outputs for the Private Wealth Advisory
  benchmark, covering Roth-conversion/RMD tax summaries, ILIT Crummey funding
  cycles, GRAT-vs-CRAT trust comparisons, and integrated estate-liquidity action
  plans. Use this whenever a task references the advisory API (base like
  http://127.0.0.1:8066 / API_BASE), a client like CLT-XXXX, a request_memo plus
  answer_template, or asks for any of: Roth conversion / RMD projection, ILIT /
  Crummey notices / gift-tax exclusion, GRAT or CRAT remainder comparison, estate
  tax exposure / liquidity gap, or an estate-liquidity action plan. It encodes the
  verified formulas, source-precedence rules, RMD simulation order of operations,
  Crummey date arithmetic, enum decision rules, and rounding/date conventions so
  the numbers and enums match the gold answers to the cent.
---

# Private Wealth Advisory Planning

Generate the exact structured JSON output for a private-wealth advisory task. Tasks
come in four families and are scored field-by-field against a gold answer, so every
number, enum, and date must be produced by the precise rule — not estimated.

## Workflow

1. **Read the task inputs.** Open `input/prompt.txt`, `input/payloads/request_memo.md`,
   and `input/payloads/answer_template.json`. The memo gives the client ID, the
   engagement type, and sometimes a planning **horizon year**. The template lists the
   exact required keys, enums, and field semantics for THIS task — always follow it,
   because field names differ across families.

2. **Identify the family** from `analysis_type` in the template:
   - `roth_conversion_rmd` — staged Roth conversion + RMD tax summary.
   - `ilit_crummey_implementation` — ILIT first-premium Crummey cycle.
   - `trust_comparison` — GRAT vs CRAT recommendation.
   - `estate_liquidity_action_plan` — integrated ILIT + trust + liquidity plan.

3. **Pull client data from the advisory API** (base URL from the harness, often
   `API_BASE`, commonly `http://127.0.0.1:8066`; GET-only). Use ONLY the API — never
   local files or your own tax-table knowledge. Policy constants come from
   `/api/policies/tax` and RMD divisors from `/api/rmd-factors`, keyed by year/age.

4. **Resolve conflicting sources** (`/api/source-documents` returns multiple, possibly
   disagreeing). Precedence: **SIGNED_PROFILE** (newest, signed, most complete) controls
   all profile / goal / beneficiary / policy facts; **CUSTODIAN_EXPORT** controls
   retirement-account facts; **ATTORNEY_MEMO** controls estate/asset valuation. A stale
   `CRM_NOTE` never overrides a fact present in the signed profile.

5. **Compute with the verified solver.** Use `scripts/advisory_solver.py` — it
   implements every formula below and reproduces the gold answers exactly. Import its
   functions, build the answer dict per the template, round USD to cents, and emit JSON
   only (no prose). For anything subtle, consult `references/business_rules.md`.

6. **Self-check before emitting:** every required key present, USD numbers are JSON
   numbers rounded to 2 decimals, dates are ISO `YYYY-MM-DD`, any "sorted" list is
   alphabetically sorted, and `task_id`/`client_id` echo the prompt exactly.

## Using the solver

```python
import sys; sys.path.insert(0, "scripts")
import advisory_solver as S
api = S.API(BASE_URL)                       # BASE_URL from the harness
cid = "CLT-XXXX"                            # from the memo
src = S.controlling_facts(api, cid)         # resolved facts + controlling-source enums

# pick the blocks the template needs:
plan = S.roth_rmd(api, cid, horizon_year)   # roth_conversion_rmd
rec  = S.roth_recommendation(plan)
est  = S.estate_context(api, cid)           # estate exposure / liquidity
gc   = S.grat_crat(api, cid)                # GRAT + CRAT remainders, reductions
trec = S.trust_recommendation(api, cid)     # GRAT vs CRAT enums
ilit = S.ilit_cycle(api, cid)               # Crummey dates, capacity, liquidity support
```

Map these outputs onto the template's field names (they vary per family — e.g. the
trust block exposes `grat_remainder`/`grat_estate_tax_reduction`, which become
`grat.projected_remainder_to_heirs`/`grat.estimated_estate_tax_reduction`).

## The formulas that must be exact (full detail in references/business_rules.md)

- **Roth sizing:** `annual = conversion_bracket_targets[filing_status] − annual_non_ira_income`;
  `total_tax = annual × years × marginal_tax_rate`. `first_rmd_year = planning_year + (rmd_start_age − age)`.
- **RMD simulation, per year, in this order:** convert (conversion scenario only) →
  take RMD `balance/rmd_factor[age]` and tax it BEFORE growth → grow both balances.
  Reported horizon balances are the **conversion** scenario; baseline scenario disables conversions.
- **Estate:** `exemption_used = exemption[year] × (2 if married else 1)`;
  `taxable = max(0, estate_value − exemption_used)`; `exposure = taxable × estate_tax_rate`;
  `liquidity_gap = max(0, exposure − liquid_assets)`.
- **GRAT/CRAT remainder:** `asset×(1+growth)^term − (asset × rate × term)`. The annuity/
  payout stream is a **simple sum (payment × term)** — do NOT compound it. Estate-tax
  reduction = GRAT remainder × estate_tax_rate; income-tax deduction = CRAT remainder ×
  charitable_deduction_rate.
- **Crummey dates:** notice_due = contribution + 7d; withdrawal_window_end = notice_due
  + 30d; earliest_premium = window_end + 1d. `tax_liquidity_support = death_benefit ×
  estate_tax_rate`. `capacity = gift_exclusion[year] × beneficiary_count`.

## Pitfalls that previously caused wrong answers

These are the exact mistakes that made a blind solver diverge from gold — guard against each:

- **Marital exemption.** Married = DOUBLE estate exemption; single = 1×. Forgetting this
  leaves `taxable_estate` = full estate value (way too high) and corrupts every downstream
  trust number. Always net the marital-aware exemption first.
- **GRAT/CRAT compounding.** The payout stream is a plain `payment × term`, not a
  future-valued annuity. Compounding it understates the remainder and breaks the deduction.
- **heir_tax_profile.** A roth majority is not enough for `MOSTLY_TAX_FREE`. Use the bands
  (≥0.70 tax-free, ≤0.30 taxable, else MIXED). A ~0.61 roth fraction is `MIXED_TAXABLE_AND_TAX_FREE`.
- **Near-RMD ≠ unsuitable.** A conversion with bracket headroom and positive savings is
  `SUITABLE` / `TAX_BRACKET_MANAGEMENT` even when the client is one year from RMDs. Don't
  reflexively pick `BORDERLINE`/`RMD_NEAR_TERM`.
- **Crummey timing.** Notice is due 7 days AFTER the contribution, and the 30-day window
  runs from the NOTICE DUE DATE (not the contribution). Off-by-7 errors cascade through all four dates.
- **tax_liquidity_support.** It is `death_benefit × estate_tax_rate`, not the full death benefit.
- **controlling_policy_source = SIGNED_PROFILE.** The signed profile governs the engagement
  even though the death-benefit number is read from the life-insurance record. Don't answer CUSTODIAN_EXPORT.
- **action_set exclusions.** Omit `CRAT_FOR_CHARITABLE_REMAINDER` when philanthropic intent
  is low; omit `LIFETIME_EXEMPTION_ALLOCATION` when premium_gap is 0. Sort the list alphabetically.

## Reference files

- `scripts/advisory_solver.py` — verified, importable formula library (use this).
- `references/business_rules.md` — full formula derivations, source-precedence table,
  enum decision rules, and output conventions. Read it when a field is ambiguous or a
  new variation appears that the solver doesn't already cover.
