---
name: private-wealth-advisory-planning
description: >-
  Produce the exact structured-JSON planning output for the private-wealth
  advisory benchmark (base API http://127.0.0.1:8066). Use this whenever a task
  asks you to prepare a planning output for an advisory client (IDs like
  CLT-1001) and the answer must conform to an answer_template.json, especially
  for any of these four engagement families: (1) Roth conversion / RMD tax
  summaries (analysis_type roth_conversion_rmd), (2) ILIT Crummey funding cycles
  (ilit_crummey_implementation), (3) GRAT-vs-CRAT trust comparisons
  (trust_comparison), and (4) integrated estate-liquidity action plans
  (estate_liquidity_action_plan). Triggers on mentions of Roth conversions, RMDs,
  required minimum distributions, ILIT/Crummey notices, GRAT, CRAT, charitable
  remainder trusts, estate-tax liquidity, lifetime exemption, conflicting source
  documents (CRM_NOTE / ATTORNEY_MEMO / SIGNED_PROFILE), or "controlling source"
  resolution. Use it even when the prompt only gives a client ID and a request
  memo and says to return JSON.
---

# Private-Wealth Advisory Planning

You are producing one JSON object that exactly matches a provided
`answer_template.json` for a single advisory client. The math is fully
deterministic — there is one right number for every field. Your job is to pull
the right facts from the API, apply the verified formulas, and emit clean JSON.

The detailed, cent-accurate specification lives in
**`references/formulas_and_rules.md`** — open it whenever you need a precise
formula, field definition, enum decision rule, or source-precedence table. This
file is the high-level workflow plus the traps that are easy to get wrong.

A ready-made, verified calculator is in **`scripts/advisory_calcs.py`**. Prefer
importing its functions (the simulation order of operations and the
GRAT/CRAT/Crummey conventions are baked in and self-tested) over re-deriving the
math by hand. Run `python scripts/advisory_calcs.py` to confirm it still
reproduces the documented sanity checks against the live API.

## Workflow

1. **Read the task inputs.** Note the `client_id`, the engagement type, and any
   `Planning horizon year` in the request memo. Open `answer_template.json` and
   list every required top-level key and field — that is your output contract.

2. **Identify the analysis_type** and the field shape, then jump to the matching
   section of `references/formulas_and_rules.md`:
   - `roth_conversion_rmd` → §3
   - `ilit_crummey_implementation` → §4
   - `trust_comparison` → §5
   - `estate_liquidity_action_plan` → §6

3. **Pull data from the API** (`http://127.0.0.1:8066`, GET only). At minimum get
   `/api/clients/{id}`, `/api/source-documents?client_id=`, `/api/policies/tax`,
   plus whichever of `/api/retirement-accounts`, `/api/life-insurance`,
   `/api/trust-candidates`, `/api/rmd-factors` the engagement needs. Always take
   tax constants and RMD factors from the API, never from memory.

4. **Resolve conflicting sources** (§2). Each client has CRM_NOTE (oldest, a
   stale import to distrust), ATTORNEY_MEMO, and SIGNED_PROFILE (newest, signed).
   Profile/goal/beneficiary facts come from SIGNED_PROFILE; IRA and policy facts
   come from the CUSTODIAN_EXPORT records; trust asset source is ATTORNEY_MEMO.

5. **Compute** using `scripts/advisory_calcs.py` (or the §3–§6 formulas). Do not
   round mid-calculation; round only the final outputs to cents.

6. **Emit JSON only.** Every required key present, numbers as JSON numbers
   rounded to 2 decimals, dates ISO `YYYY-MM-DD`, no prose, no code fences. Echo
   `task_id`, `client_id`, and `analysis_type` exactly.

## The traps that actually cost points

These are real errors a prior blind solver made; each one maps to a verified
gold rule. Internalize them before you start.

- **Conversions are NOT truncated at RMD age.** Roth conversions run the full
  `recommended_conversion_years` window even after RMDs begin. And the per-year
  order is **CONVERT → RMD → GROW** (convert first, so that year's RMD is on the
  reduced traditional balance). Getting either wrong throws off every downstream
  dollar. (§3)

- **"Near-RMD" framing is a distractor.** If a staged conversion produces
  positive RMD-tax savings, recommend `STAGED_ROTH_CONVERSION` / `SUITABLE` /
  `TAX_BRACKET_MANAGEMENT` — even if the client is one year from RMDs. Don't
  default to DEFER just because the memo says "near-RMD." (§3)

- **`controlling_policy_source` is `CUSTODIAN_EXPORT`, not SIGNED_PROFILE.**
  Policy facts come from the life-insurance export. "Newest household doc wins"
  applies to profile/goal facts, not to account or policy data. (§2)

- **GRAT/CRAT remainder subtracts the annuity at its NOMINAL sum.**
  `remainder = asset*(1+g)^term − asset*rate*term`. The asset compounds for the
  full term; the annuity/payout is `asset*rate*term` (not future-valued, not a
  loop that compounds each payment). (§5)

- **CRAT income-tax deduction is on the CRAT REMAINDER, not the raw asset.**
  `deduction = crat_remainder * charitable_deduction_rate`. (§5)

- **ILIT `tax_liquidity_support = min(death_benefit, estate-tax exposure)`**,
  where exposure uses the **single** exemption even for married clients. It is
  not the client's liquid assets. (§4)

- **Estate-context exemption is DOUBLED for married, single for single.** This
  is for `taxable_estate`/`estate_tax_exposure` in the trust and
  estate-liquidity tasks. (Note the deliberate asymmetry: the ILIT
  `tax_liquidity_support` calc above uses the single exemption regardless of
  marital status.) (§5, §6)

- **`LIFETIME_EXEMPTION_ALLOCATION` is gated on premium_gap > 0**, i.e. a
  Crummey exclusion shortfall — NOT on the estate liquidity gap. Don't add it
  just because the estate can't cover its tax bill. And exclude
  `CRAT_FOR_CHARITABLE_REMAINDER` when philanthropy is low. Sort `action_set`
  alphabetically. (§6)

- **Crummey dates:** `notice_due_date = contribution_date` (same day),
  `withdrawal_window_end = contribution + 30 days`,
  `earliest_premium_payment_date = window_end + 1 day`. `premium_gap` is floored
  at 0. (§4)

## Self-check before you submit

- Did you use SIGNED_PROFILE values (income, marginal rate, beneficiary_count,
  intents), not the stale CRM_NOTE?
- Are all required template keys present, numbers rounded to cents, dates ISO?
- For Roth tasks: convert-before-RMD ordering, full conversion window, savings
  computed as baseline − conversion?
- For trust tasks: nominal-annuity remainder formula, deduction on the remainder,
  exemption doubled iff married?
- Did you run / mirror `scripts/advisory_calcs.py` rather than hand-rolling the
  arithmetic?
