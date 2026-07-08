---
name: private-wealth-advisory-structured-planning
description: >
  Solve private-wealth advisory structured-JSON planning tasks served by the
  prismshadow advisory API: (a) Roth conversion / RMD tax summaries
  (analysis_type roth_conversion_rmd), (b) ILIT Crummey funding cycles
  (ilit_crummey_implementation), (c) GRAT vs CRAT comparisons (trust_comparison),
  and (d) integrated estate-liquidity action plans (estate_liquidity_action_plan).
  Use when a task asks for one structured JSON object conforming to an
  answer_template.json for a client CLT-xxxx, sourcing all data from the read-only
  HTTP advisory API. Contains the verified formulas, conflict-resolution priority,
  exact output schema/enums, rounding/date conventions, and pitfalls.
---

# Private Wealth Advisory — Structured Planning SOP

You produce ONE JSON object per task, conforming exactly to that task's
`input/payloads/answer_template.json`. All input data comes from a read-only HTTP
advisory API. Output JSON only — no prose, no markdown fences.

## 0. Environment / API

Base URL is given by the harness (often `API_BASE`); in this environment it is
`<remote-env-url>`. Fetch with `curl -s` (Bash). If you run helper
scripts use `python` (NOT `python3`). Endpoints (all GET):

- `GET /api/health` — liveness.
- `GET /api/clients/<client_id>` — base client record (age, filing_status, planning_year, estate_value, liquid_assets, marital_status).
- `GET /api/source-documents?client_id=<id>` — conflicting imported docs; each has `source_type`, `effective_date`, `facts{}`.
- `GET /api/retirement-accounts?client_id=<id>` — IRA export (traditional_balance, roth_balance, expected_return, rmd_start_age, recommended_conversion_years). `source_type` = CUSTODIAN_EXPORT.
- `GET /api/life-insurance?client_id=<id>` — policy (proposed_owner, death_benefit, annual_premium, planned_contribution_date, is_existing_policy_transfer).
- `GET /api/trust-candidates?client_id=<id>` — trust params (asset_value, expected_growth_rate, grat_term_years, grat_annuity_rate, crat_term_years, crat_payout_rate).
- `GET /api/policies/tax` — constants (see below).
- `GET /api/rmd-factors` — `{age: factor}` map for ages 73..99.

Always fetch the client record, source-documents, `/api/policies/tax`, and the
domain-specific export(s) you need before computing.

### Tax policy constants (shape)
```
annual_gift_exclusion: {"2025":19000, "2026":20000}      # per-year, per beneficiary
estate_tax_exemption:  {"2025":13990000, "2026":13610000}
estate_tax_rate: 0.40
conversion_bracket_targets: {"MFJ":394600, "SINGLE":197300, "HOH":263500}
max_crat_term_years: 20
charitable_deduction_rate: 0.35
```
Always index `annual_gift_exclusion` and `estate_tax_exemption` by the client's
`planning_year` (string key), not a hardcoded year.

## 1. Conflict resolution (source priority) — VERIFIED

Source documents disagree (CRM import is stale). Resolve fields by WHICH attribute
you need, not by one global winner:

- **Profile / personal facts** (age, filing_status, marital_status, planning_year,
  annual_non_ira_income, marginal_tax_rate, beneficiary_count, philanthropic_intent,
  family_transfer_priority, liquid_assets): use the **SIGNED_PROFILE** document.
  It is the newest (effective_date ~2026-02-06) and most complete. This is the
  `controlling_profile_source` / `controlling_goal_source` / `controlling_beneficiary_source`.
- **Account / retirement facts** (balances, returns, rmd_start_age,
  recommended_conversion_years): use the **CUSTODIAN_EXPORT** (the
  retirement-accounts endpoint). This is `controlling_account_source`.
- **Policy facts** (death_benefit, annual_premium, contribution date): come from
  the life-insurance endpoint; report `controlling_policy_source = CUSTODIAN_EXPORT`.
- **Asset / trust valuation facts** (the trust `asset_value`, estate value used for
  trust sizing): report `controlling_asset_source = ATTORNEY_MEMO`.
  IMPORTANT and counter-intuitive: asset source resolves to ATTORNEY_MEMO, NOT
  SIGNED_PROFILE. (Confirmed: the asset/trust valuation source resolves to ATTORNEY_MEMO.)

General priority when a needed field exists in several docs and the above does not
apply: SIGNED_PROFILE > ATTORNEY_MEMO > CUSTODIAN_EXPORT > CRM_NOTE >
STALE_MARKETING_INTAKE (newer effective_date and signed/legal docs win; CRM is stale).

Source enum values: SIGNED_PROFILE, ATTORNEY_MEMO, CUSTODIAN_EXPORT, CRM_NOTE,
STALE_MARKETING_INTAKE.

## 2. Rounding / dates / output

- All USD amounts are JSON numbers rounded to cents (2 decimals). Never strings.
- Integer-year fields are integers (e.g. 2026, 2046).
- Dates are ISO `YYYY-MM-DD` strings.
- `action_set` (estate plan) is a list sorted ALPHABETICALLY.
- Always echo `task_id` (e.g. "test_001") and `client_id` exactly, and set
  `analysis_type` to the task's enum.
- Emit only the keys the template lists; numbers as JSON numbers.

---

## 3. analysis_type = roth_conversion_rmd  (FULLY VERIFIED)

Inputs: client (age, filing_status, planning_year), SIGNED_PROFILE
(annual_non_ira_income, marginal_tax_rate), retirement-accounts
(traditional_balance, roth_balance, expected_return, rmd_start_age,
recommended_conversion_years), tax policy (conversion_bracket_targets), rmd-factors.
Horizon year is given in the request memo (e.g. 2046, 2042).

### Conversion plan
- `first_conversion_year` = planning_year.
- `conversion_years` = `recommended_conversion_years` from the custodian export.
  `conversion_years_positive` = same value (max(conversion_years, 0)).
- `annual_conversion_amount` = `conversion_bracket_targets[filing_status]
  − annual_non_ira_income`  (fill the bracket headroom).
  DO NOT use traditional_balance / conversion_years (even-split is WRONG).
- `total_converted` = annual_conversion_amount × conversion_years.
- `total_conversion_tax` = total_converted × marginal_tax_rate.

### RMD projection (year-by-year simulation)
- `first_rmd_year` = planning_year + (rmd_start_age − age). (Holds even when the
  conversion window overlaps RMD years.)
- `horizon_year` = the memo's planning horizon.
- Simulate each year from planning_year through horizon_year inclusive, tracking a
  traditional balance and a roth balance (roth starts at the export's roth_balance).
  Per year, IN THIS ORDER:
  1. **Convert**: if `first_conversion_year ≤ year < first_conversion_year +
     conversion_years`, move `c = min(annual_conversion_amount, trad_balance)` from
     traditional to roth.
  2. **RMD**: if `age ≥ rmd_start_age`, `rmd = trad_balance / rmd_factor[age]`;
     add `rmd × marginal_tax_rate` to that scenario's RMD-tax accumulator; subtract
     rmd from trad_balance.
  3. **Grow**: multiply BOTH balances by `(1 + expected_return)`.
  Advance age and year by 1.
- Run the simulation twice:
  - baseline (do_conversion = False) → `baseline_rmd_tax_through_horizon`.
  - conversion (do_conversion = True) → `conversion_rmd_tax_through_horizon` and the
    horizon balances.
- `rmd_tax_savings_through_horizon` = baseline − conversion.

### Legacy projection
- `projected_roth_balance_horizon` = roth balance at end of the CONVERSION
  simulation.
- `projected_traditional_balance_horizon` = traditional balance at end of the
  CONVERSION simulation.
- `heir_tax_profile` by roth share = roth / (roth + trad):
  - MOSTLY_TAX_FREE if share ≳ 0.7
  - MIXED_TAXABLE_AND_TAX_FREE if roughly 0.3 ≤ share ≤ 0.7 (verified at shares
    0.455 and 0.613)
  - MOSTLY_TAXABLE if share ≲ 0.3

### Recommendation enums (verified)
- `primary_action` = STAGED_ROTH_CONVERSION when staged conversion reduces RMD tax
  (savings > 0). (Other enums: DEFER, NO_CONVERSION — use only if conversion is not
  beneficial / blocked.)
- `suitability` = SUITABLE when conversion saves tax — even if the client is one
  year from RMD. (BORDERLINE / DEFER are wrong here; verified SUITABLE.)
- `risk_flag`:
  - RMD_NEAR_TERM when the client is at/near RMD age (e.g. age == rmd_start_age − 1,
    so RMD begins next year). (Verified for age 72, rmd_start_age 73.)
  - TAX_BRACKET_MANAGEMENT when RMD is years away and the plan is about filling
    bracket headroom over a multi-year window. (Verified for age 66.)
  - LIQUIDITY_CONSTRAINT if conversion taxes strain liquid_assets.

### Source resolution
`controlling_profile_source` = SIGNED_PROFILE; `controlling_account_source` =
CUSTODIAN_EXPORT.

---

## 4. analysis_type = ilit_crummey_implementation  (mostly verified)

Inputs: client, SIGNED_PROFILE (beneficiary_count), life-insurance policy
(death_benefit, annual_premium, planned_contribution_date,
is_existing_policy_transfer), tax policy (annual_gift_exclusion, estate_tax_*).

### Gift plan (VERIFIED)
- `planning_year` = client planning_year.
- `annual_exclusion_per_beneficiary` = `annual_gift_exclusion[planning_year]`
  (= 20000 for 2026).
- `beneficiary_count` = SIGNED_PROFILE beneficiary_count.
- `annual_exclusion_capacity` = per_beneficiary × beneficiary_count.
- `annual_premium` = policy annual_premium.
- `premium_gap` = **max(0, annual_premium − annual_exclusion_capacity)**.
  (Verified: when capacity ≥ premium the gap is 0.00, NOT the negative difference.)

### Administration
- `notices_required` = beneficiary_count (one Crummey notice per beneficiary). VERIFIED.
- `contribution_date` = policy `planned_contribution_date` (ISO). VERIFIED.
- `dedicated_bank_account_required` = true (ILIT best practice). [best-effort]
- `notice_due_date`, `withdrawal_window_end`, `earliest_premium_payment_date`:
  Crummey timing relative to the contribution date. Verified anchor:
  `earliest_premium_payment_date` = contribution_date + 31 days (i.e. the day AFTER a
  30-day withdrawal window). So model a 30-day withdrawal window:
  `withdrawal_window_end` = contribution_date + 30 days,
  `earliest_premium_payment_date` = window_end + 1 day = contribution_date + 31 days.
  `notice_due_date` = contribution_date (notices issued at/with the contribution).
  [The 31-day earliest-payment offset is verified; notice_due_date and the exact
  window_end day are best-effort — keep the 30-day window unless task text says otherwise.]

### Estate result
- `death_benefit` = policy death_benefit. VERIFIED.
- `estate_inclusion_risk` = same enum as risk_flag (see below). VERIFIED.
- `projected_outside_estate_if_implemented` = death_benefit (the full benefit sits
  outside the taxable estate once the ILIT owns the policy and formalities are met).
  [best-effort]
- `tax_liquidity_support` = the policy's contribution to estate-tax liquidity.
  Candidate = min(death_benefit, estate_tax_exposure) where estate_tax_exposure =
  (estate_value − estate_tax_exemption[planning_year]) × estate_tax_rate. [UNCONFIRMED
  — neither full death_benefit nor min(db, estate_tax) verified; compute the estate
  tax and use min(death_benefit, estate_tax) as the best estimate.]

### Recommendation / risk_flag logic
Determine two conditions:
- exclusion_shortfall = premium_gap > 0 (premium exceeds annual exclusion capacity).
- three_year_lookback = `is_existing_policy_transfer == true` (transferring an
  EXISTING policy triggers the 3-year estate-inclusion lookback; a brand-new policy
  does not).
Then:
- Neither → primary_action FUND_WITH_CRUMMEY_NOTICES, suitability
  SUITABLE_WITH_ADMINISTRATION, risk_flag LOW_IF_FORMALITIES_MET. VERIFIED.
- Only shortfall → primary_action USE_LIFETIME_EXEMPTION_FOR_SHORTFALL,
  risk_flag EXCLUSION_SHORTFALL.
- Only lookback → primary_action USE_NEW_POLICY_OR_ACCEPT_LOOKBACK,
  risk_flag THREE_YEAR_LOOKBACK.
- Both → primary_action DISCLOSE_LOOKBACK_AND_USE_EXEMPTION,
  risk_flag THREE_YEAR_LOOKBACK_AND_EXCLUSION_SHORTFALL.
suitability is SUITABLE_WITH_ADMINISTRATION when formalities can be met (default);
BORDERLINE / NOT_SUITABLE only for severe shortfall/lookback problems.
`estate_inclusion_risk` mirrors `risk_flag`.

### Source resolution
`controlling_beneficiary_source` = SIGNED_PROFILE;
`controlling_policy_source` = CUSTODIAN_EXPORT.

---

## 5. Estate context block (taxable estate / exposure / liquidity gap) — VERIFIED

Used by both `trust_comparison` and `estate_liquidity_action_plan`. Confirmed correct
on the estate-liquidity analysis:
- `taxable_estate` = estate_value − estate_tax_exemption[planning_year].
- `estate_tax_exposure` = taxable_estate × estate_tax_rate (0.40).
- `liquidity_gap_before_planning` = estate_tax_exposure − liquid_assets.
Use the SIGNED_PROFILE / client estate_value and liquid_assets. (If estate_value <
exemption, taxable_estate and exposure floor at 0; gap may then be negative or 0 —
follow the same arithmetic.)

---

## 6. analysis_type = trust_comparison (GRAT vs CRAT)

Inputs: client, SIGNED_PROFILE (philanthropic_intent, family_transfer_priority),
trust-candidates (asset_value, expected_growth_rate, grat_term_years,
grat_annuity_rate, crat_term_years, crat_payout_rate), tax policy.

### Estate context
As in section 5. (taxable_estate, estate_tax_exposure, liquidity_gap_before_planning.)

### Recommendation (goal-driven)
Read goals from SIGNED_PROFILE:
- family_transfer_priority = high and philanthropic_intent low/moderate →
  `preferred_strategy` = GRAT, `rationale_code` = CHILDREN_TRANSFER_PRIORITY,
  `alternate_role` = SECONDARY_CHARITABLE_TOOL.
- philanthropic_intent = high (and/or dominant over family transfer) →
  `preferred_strategy` = CRAT, `rationale_code` = PHILANTHROPIC_PRIORITY,
  `alternate_role` = SECONDARY_FAMILY_TRANSFER_TOOL.
- `crat.family_transfer_fit` = LOW when GRAT is preferred / family transfer is the
  goal (a CRAT serves charity, not heirs); HIGH/MODERATE only if the CRAT structure
  is being used partly for family. Default LOW for a charity-only CRAT.
- `grat.term_years` = grat_term_years; `crat.term_years` = crat_term_years
  (both straight from trust-candidates). VERIFIED.
- `grat.mortality_inclusion_risk` = TERM_SURVIVAL_REQUIRED (only enum). VERIFIED.

### GRAT / CRAT projection numbers  [UNCONFIRMED — best effort]
The exact projection formula remains UNCONFIRMED; a simple
annuity simulation (grow-then-pay or pay-then-grow) did NOT match. Implement the
best-effort model below, but treat these four numbers as the uncertain part:
- GRAT annuity = asset_value × grat_annuity_rate.
  `grat.projected_remainder_to_heirs`: simulate term years; each year grow corpus by
  expected_growth_rate then subtract the GRAT annuity; remainder = ending corpus.
  (Closed form: asset×(1+g)^n − annuity×[((1+g)^n − 1)/g].)
- `grat.estimated_estate_tax_reduction`: assets/appreciation removed from the estate
  × estate_tax_rate. Candidates tried (both unverified): remainder×0.40 and
  asset_value×0.40. Prefer modeling the APPRECIATION transferred:
  (projected_remainder_to_heirs − asset_value) × estate_tax_rate may be the intended
  "value removed from estate" — test alternatives if possible.
- CRAT annual payout = asset_value × crat_payout_rate (crat_term_years capped by
  max_crat_term_years = 20).
  `crat.projected_charitable_remainder`: same simulation over crat_term_years.
- `crat.estimated_income_tax_deduction`: charitable deduction. Candidates:
  charitable_deduction_rate(0.35) × asset_value, or × projected charitable remainder.
  Unverified — pick the present-value-of-remainder interpretation if you can derive it.

### Source resolution
`controlling_goal_source` = SIGNED_PROFILE; `controlling_asset_source` =
ATTORNEY_MEMO (verified — see §1).

---

## 7. analysis_type = estate_liquidity_action_plan (integrated) — largely verified

Combines estate context (§5), ILIT (§4 gift/estate logic), and a trust transfer
(§6). Inputs: client, SIGNED_PROFILE, life-insurance, trust-candidates, tax policy.

### Estate context — VERIFIED (§5 formulas).

### ILIT sub-block — VERIFIED
- `annual_exclusion_capacity` = annual_gift_exclusion[planning_year] ×
  beneficiary_count.
- `premium_gap` = max(0, annual_premium − annual_exclusion_capacity).
- `estate_inclusion_risk` = risk enum from the ILIT shortfall/lookback logic (§4);
  LOW_IF_FORMALITIES_MET for a new policy with capacity ≥ premium.
- `projected_outside_estate_if_implemented` = policy death_benefit.

### Trust transfer sub-block
- `preferred_strategy` = GRAT or CRAT by the §6 goal logic (GRAT when
  family_transfer_priority high & philanthropic low). VERIFIED (GRAT chosen).
- `projected_remainder_to_heirs`, `estimated_estate_tax_reduction`,
  `projected_charitable_remainder`: SAME unconfirmed projection math as §6 — these
  three numbers are the unresolved part; everything else in this analysis verified.

### Recommendation (VERIFIED enums for the combined ILIT+GRAT, no shortfall/lookback case)
- `primary_action` = COMBINE_ILIT_AND_GRAT (when both an ILIT and a GRAT are
  warranted). Other options: CRAT_WITH_LIQUIDITY_REVIEW (charitable focus),
  ILIT_WITH_EXEMPTION_REVIEW (premium > exclusion capacity).
- `sequencing` = ILIT_FIRST_THEN_GRAT. Others: TRUST_DECISION_FIRST,
  ILIT_FIRST_THEN_ATTORNEY_REVIEW.
- `risk_flag` = LOW_IF_FORMALITIES_MET (new policy, capacity ≥ premium). Use the same
  shortfall/lookback escalation as §4 otherwise.

### action_set — VERIFIED (alphabetically sorted list)
Pick the applicable items from this fixed vocabulary, then SORT alphabetically:
- ATTORNEY_DRAFT_REVIEW — always include (attorney coordination).
- ILIT_CRUMMEY_NOTICE_CYCLE — include when an ILIT/policy is in play.
- LIFETIME_EXEMPTION_ALLOCATION — include when estate exposure / exemption use applies.
- GRAT_FOR_APPRECIATING_SHARES — include when preferred_strategy = GRAT.
- CRAT_FOR_CHARITABLE_REMAINDER — include when preferred_strategy = CRAT /
  philanthropic_intent is high. EXCLUDE when GRAT is preferred and philanthropic
  intent is low.
Verified example (GRAT chosen, philanthropic low): exactly
["ATTORNEY_DRAFT_REVIEW","GRAT_FOR_APPRECIATING_SHARES","ILIT_CRUMMEY_NOTICE_CYCLE","LIFETIME_EXEMPTION_ALLOCATION"].

### Source resolution
`controlling_goal_source` = SIGNED_PROFILE; `controlling_policy_source` =
CUSTODIAN_EXPORT.

---

## 8. Pitfalls & checklist

- Roth conversion amount fills BRACKET HEADROOM (bracket_target − non_ira_income),
  never traditional_balance / years.
- Simulation order each year: convert → RMD → grow. Grow BOTH traditional and roth.
  Include the starting roth_balance.
- first_rmd_year = planning_year + (rmd_start_age − age); the conversion window can
  legitimately overlap RMD years.
- premium_gap and any "gap" that represents a shortfall are floored at 0 (max(0, …)),
  not signed negatives.
- Index exemptions and gift exclusions by the client's planning_year string key.
- Asset/trust valuation source = ATTORNEY_MEMO; everything personal = SIGNED_PROFILE;
  accounts & policies = CUSTODIAN_EXPORT.
- Crummey earliest premium payment = contribution_date + 31 days (30-day window + 1).
- action_set MUST be alphabetically sorted; exclude CRAT items when GRAT is chosen
  and philanthropic intent is low.
- Round every USD field to cents; emit numbers (not strings); ISO dates only.
- Echo task_id, client_id, analysis_type exactly. Output the JSON object only.
- The GRAT/CRAT projection dollar figures (remainder to heirs, estate-tax reduction,
  charitable remainder, income-tax deduction) are the least certain — compute them
  with the documented annuity simulation but double-check the intended ordering /
  PV vs FV interpretation; all other fields above are confirmed reliable.
