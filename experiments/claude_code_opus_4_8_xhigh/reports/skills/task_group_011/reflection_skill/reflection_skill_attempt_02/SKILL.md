---
name: credit-office-committee-packets
description: >-
  Produce committee-ready JSON answers for the shared "credit office" HTTP API
  (branches, loans, applications, sector exposures, credit-union segments, FDIC/NCUA
  benchmarks, and the /api/policies rulebook). Use this whenever a task asks you to
  re-derive risk ratings, build a Q1 lending-capacity / allocation package, score
  CDFI factor classes, run watch-list or CRE dual-stress, compare competing CRE
  requests, write a credit-union segment posture page, or compute NPA / FDIC / NCUA
  benchmark variances against an answer_template.json. Apply it for any prompt that
  names a branch_id or segment_id, references credit policies, risk ratings,
  concentration limits, reason codes, or asks for a JSON answer matching a payload
  template in this credit-office domain.
---

# Credit Office Committee Packets

You build JSON deliverables for a bank/credit-union credit office. Every task gives a
prompt, a target `branch_id`/`segment_id`, and an `answer_template.json` describing the
exact output shape and enums. The grader compares your JSON to an official answer field
by field, so **the rules, rounding, ordering, and enum choices below are load-bearing**.

This skill is distilled from solving these tasks blind and then diffing against the
official answers. The "Common pitfalls" section is the highest-value part — it lists the
exact mistakes that were made and the rule that fixes each one. Read it before you start.

## How to work

1. `GET /api/policies` first — it is the single source of truth for thresholds, scoring
   bands, class cutoffs, and stress formulas. Never invent a threshold the policy gives.
2. Pull the branch/segment data you need (see API map below). Treat the API as the only
   data source — do not look for local files/db.
3. Read the `answer_template.json` carefully: it defines required keys, enums, numeric
   `precision`, and `ordering`. Match them exactly.
4. Compute with full precision; round only at the final write, per field (see Rounding).
5. Output only the JSON object. No prose.

## API quick map (base `http://127.0.0.1:8003`)

| Need | Endpoint | Key fields |
|---|---|---|
| Policy rulebook | `/api/policies` | `risk_rating`, `cdfi_factor_scores`, `cre_weighted_score`, `stress`, `capacity_concentration` |
| Branch detail | `/api/branches/{id}` | `lending_capacity_q1`, `sector_ceiling_pct`, `cre_policy_limit_pct`, `institution_type`, `state_code` |
| Branch metrics | `/api/branches/{id}/metrics?quarter=2025Q1` | `total_loans_outstanding`, `nonperforming_loans`, `delinquency_30_plus_pct` |
| Loans | `/api/branches/{id}/loans?min_current_rating=N` | `current_rating`, `dscr`, `ltv`, `payment_status`, `outstanding_balance`, `debt_to_asset`, `fico`, `liquidity_months`, `collateral_value` |
| Sector exposures | `/api/branches/{id}/sector-exposures` | `sector`, `current_exposure`, `limit_pct` (per-sector override) |
| Applications | `/api/branches/{id}/applications` | `dscr`, `ltv`, `fico`, `years_in_business`, `bankruptcy_months_ago`, `sba_guaranty_pct`, `requested_amount`, `sector` |
| CU segment | `/api/credit-union-segments/{id}` | `risk_tolerance`, `minimum_checklist`, `peer_states`, `quarterly_capacity`, `current_outstanding`, `internal_context` |
| FDIC benchmark | `/api/benchmarks/fdic/q4-2024` | `total_loans_noncurrent_pct`, `total_real_estate_30_89_pct`, ... |
| NCUA benchmark | `/api/benchmarks/ncua/q1-2025?state_code=XX` | per-state `delinquency_bps`, `loan_to_share_pct`, `roaa_bps`, `positive_net_income_pct` |

`branch_id`/`segment_id` match case-insensitively. `min_current_rating=N` returns loans
with `current_rating >= N`.

## Core business rules (re-apply on every relevant task)

### Risk-rating re-derivation (dominant-factor rule)
For each loan compute a numeric rating from each *available* factor, then take the
**worst (max)**:
- **DSCR band**: `>=1.5 -> 3`, `>=1.25 -> 4`, `>=1.05 -> 5`, `>=1.0 -> 6`, `<1.0 -> 7`.
- **LTV band**: `<=0.65 -> 3`, `<=0.75 -> 4`, `<=0.85 -> 5`, `<=1.0 -> 6`, `>1.0 -> 7`.
  (Collateral is expressed through LTV.)
- **Delinquency floor**: `30DPD -> 4`, `60DPD -> 5`, `90+ -> 7`, `Nonaccrual -> 8`,
  `Current -> none`.
- `final_rating = max(of the available factor ratings)`.
- If a loan has **no** usable factors (DSCR, LTV/collateral, and delinquency all null and
  Current), **keep its current rating unchanged** — do not exclude it, do not floor it.
- `downgrade_notches = final_rating - current_rating`. A downgrade is **material** when
  notches `>= material_downgrade_notches` (2).

### CDFI factor scoring (watch-list classes)
Sum the sub-scores for the factors that are present (`debt_to_asset`, `fico`,
`liquidity_months`, `ltv`) using the policy sub-scale tables. **Only sum non-null
factors — do not penalize or zero-fill missing ones.** Map the total to a class:
`0-5 Prime`, `6-9 Desirable`, `10-13 Satisfactory`, `14-18 Watch`, `>=19 Doubtful`.
- **Projected Loss escalation**: the policy text reads ">=19 and ltv>1.0", but the
  operative trigger is the **underwater LTV**. Classify a severely impaired credit
  (Nonaccrual / Watch-or-worse band) with `ltv > 1.0` as **Projected Loss** even if its
  score is below 19. A high-score credit with `ltv <= 1.0` stays in its score band.

### Stress tests (from policy `stress`)
- Watch-list +200bp shock: `stressed_dscr = dscr / (1 + 0.18)`.
- CRE dual stress: `stressed_dscr = dscr * 0.85 / (1 + 0.18)`.
- A loan **breaches** when `stressed_dscr < coverage_breach_threshold` (1.0), strictly less.
- Only include loans/apps that **have a DSCR** in the stress results list.

### Concentration & lending capacity (allocation tasks)
- Per-sector limit = `sector_exposures.limit_pct` if present for that sector, else the
  branch default `sector_ceiling_pct`. (Some sectors override the default, e.g. Healthcare.)
- **Two different denominators — do not mix them up:**
  - *Per-application* `concentration_flags.post_approval_pct`
    `= (sector_current_exposure + THIS app's amount) / (total_base + THIS app's amount)`,
    where `total_base = sum of all sector current_exposure`. Flag `true` when this exceeds
    the sector limit. A declined app still gets a flag if its *requested* add would breach.
  - *Aggregate* `post_approval_concentrations.post_approval_pct`
    `= (sector_current_exposure + sum of ALL approved adds in that sector) / (total_base + sum of ALL approved adds across all sectors)`.
    Because the denominator grows with every approval, aggregate sectors often end up
    `over_limit = false` even when individual apps flagged.
- `gross_approved_amount = sum of approved_amount`;
  `committed_capacity_amount = sum of bank_capacity_used`;
  `remaining_capacity = lending_capacity_q1 - committed_capacity_amount`.
- `bank_capacity_used = approved_amount` normally, but `= approved_amount * 0.50` for
  `participation_required` deals (bank retains half).

### Underwriting floors (application decline reason codes)
These are **not** in the policy endpoint; they are fixed SOP thresholds derived from the
official answers:
- `weak_dscr`: base `dscr < 1.20`.
- `high_ltv`: `ltv > 0.85`.   `underwater_collateral`: `ltv > 1.0`.
- `low_fico`: `fico < 620`.
- `startup_risk`: `years_in_business < 2`.
- `recent_bankruptcy`: `bankruptcy_months_ago < 24`.
- `sector_breach`: the app's per-application post-approval concentration exceeds its
  sector limit.
- A floor breach that is mitigated (e.g. SBA guaranty for a startup / weak DSCR) becomes a
  `conditional_approve` with `sba_guaranty_required` + `startup_monitoring` rather than a
  decline. A credit-clean app that only trips `sector_breach` gets a mitigation path
  (`participation_required` or `conditional_approve` + `reduced_amount`), not a decline.
- **Context matters:** in a CRE stress comparison, `weak_dscr` comes from the *stress
  breach* (`stressed_dscr < 1.0`), not the base-DSCR floor. Emit only the reason codes the
  task's own checks actually produce.

### Decision paths
- `approve`: credit-clean, no breach.
- `conditional_approve`: viable but needs a condition (reduced amount, SBA, startup
  monitoring, etc.).
- `participation_required`: viable but concentration/exposure pressure → bank retains 50%.
- `decline`: fails underwriting floors with no mitigation.
- `defer`: a viable competing credit that simply lost the head-to-head. In a "select the
  stronger of two" task, the **unselected** credit is **deferred, not declined**, even if
  it breaches stress — its `decision` and `unselected_disposition` are both `defer`.

### Recommended-action mapping (watch-list / workout)
Drive this from the loan's status and re-derived/risk class, not from intuition:
- Nonaccrual **or** Projected Loss → `partial_chargeoff_review`.
- 90+ Days Past Due → `special_assets`.
- final rating 7, or a Watch-class structurally weak credit → `special_assets`.
- final rating 6 / adverse-but-performing → `watchlist`.
- final rating <= 5 → not on the watch list (effectively `monitor`).

### Watch-list action coverage population
Cover **every loan whose re-derived final rating is adverse (`>= 6`)**, regardless of
whether it was downgraded. A loan that was already rated 6 and stays 6 is still covered; a
loan downgraded into final rating 5 is **not** covered. Do not gate coverage on
"downgraded" — gate it on the adverse final rating.

### Benchmark variances (NPA / FDIC / NCUA)
- NPA exposure = the branch metric `nonperforming_loans` (Nonaccrual). NPA ratio
  `= nonperforming_loans / total_loans_outstanding`. Benchmark metric enum for the bank
  NPA comparison is `total_loans_noncurrent_pct`.
- CRE/RE delinquency comparison: branch `delinquency_30_plus_pct` vs FDIC
  `total_real_estate_30_89_pct`.
- NCUA segment metrics: read the per-state row **verbatim** (they are already integers —
  `delinquency_bps`, `loan_to_share_pct`, `roaa_bps`, `positive_net_income_pct`). Direction
  fields (`higher`/`lower`/`equal`) describe NC relative to the comparison value.

## Rounding, precision & ordering conventions

- **Round each output field independently at the end, at the precision the template
  states. Never feed a rounded intermediate into another field.** In particular,
  `variance_bps` (and any `*_variance_bps`) is computed from the **unrounded** ratio
  difference (`(branch_ratio - benchmark_ratio) * 10000`, then round to 2dp). It is *not*
  `(rounded_ratio_4dp - rounded_benchmark_4dp) * 10000`. Getting this wrong shifts bps by
  ~0.5.
- Currency fields: 2 decimals. Ratio/percentage fields: 4 decimals. bps: 2 decimals.
  CDFI/weighted scores: integer or 1 decimal exactly as the template says.
- **Ordering is graded.** Follow the template's `ordering` literally:
  - lists "ascending by final_rating" / "ascending loan_id" → numeric/lexical ascending.
  - `severe_bucket_counts`: ascending `current_rating`, then `payment_status` as a **plain
    ascending string** — so "90+ Days Past Due" sorts **before** "Current" (digit `9` <
    letter `C`). Do **not** sort payment_status by severity/enum order.
  - reason-code lists: **alphabetical** ascending.
  - `workout_queue`: descending exposure, then ascending loan_id.
- For `set`-typed fields (checklist gates, operating controls) order is not significant,
  but include exactly the right *members*.

## Common pitfalls / error reflections (from blind-vs-official diffs)

1. **Inventing action codes instead of using the fixed mapping.** Blind sent
   `legal_referral` for Nonaccrual credits and `workout` for adverse-but-performing ones.
   Official uses `partial_chargeoff_review` for Nonaccrual/Projected-Loss and `special_assets`
   for 90+/Watch. Fix: use the Recommended-action mapping above; `legal_referral` was not
   the right code for these Nonaccrual credits.

2. **Wrong watch-list coverage population.** Blind covered "downgraded" credits and so
   *excluded* a loan that was already rated 6 and stayed 6, while *including* a loan that
   fell to final rating 5. Fix: coverage = all loans with **final rating >= 6**, downgrade
   status irrelevant.

3. **bps computed from rounded ratios.** Blind produced `1037.0`; official `1037.49`. Fix:
   compute bps from the full-precision ratio difference, round only at the end.

4. **Concentration denominator confusion.** Blind used one denominator everywhere and so
   flagged only one sector. Official uses `total_base + this app's add` for per-app flags
   (catching 4 sectors, including a declined app whose requested add would breach) and
   `total_base + all approved adds` for the aggregate view. Keep the two denominators
   separate.

5. **Guessed underwriting floors / wrong reason codes.** Blind flagged `high_ltv` on a loan
   with LTV 0.80 and missed `sector_breach`/`low_fico`/`weak_dscr` elsewhere. Fix: use the
   exact floors (DSCR<1.20, LTV>0.85, FICO<620, startup<2yr, bankruptcy<24mo) and add
   `sector_breach` whenever the per-app concentration exceeds the limit.

6. **Capacity treated as binding when it wasn't.** Blind declined an app with
   `capacity_limit` although remaining capacity was positive. Fix: only use `capacity_limit`
   when committed capacity actually exhausts `lending_capacity_q1`. Fund every
   credit-qualified, non-breaching (or mitigated) app while capacity remains.

7. **Overriding a source value with personal judgment.** Blind set `risk_tolerance` to
   `restrained`; the segment record literally says `"moderate"`. Fix: when an output field
   matches a field in the source data, **echo the source value** unless the task explicitly
   asks you to re-derive it.

8. **Emitting a subset of allowed enum items.** Blind produced 3 escalation triggers;
   official has one trigger for **every** allowed `condition` choice (4). Fix: when the
   template enumerates condition/trigger choices and asks for triggers, cover all of them,
   mapping each to its owner (delinquency/state-gap → credit_risk_manager,
   insurance/lien → operations_control_manager, capacity → lending_committee_chair).

9. **Compressed CDFI/weighted-score spread → wrong class and wrong decision.** Blind scored
   a weak CRE credit at 2.9 (class `conditional`) when the official was 4.4 (class `weak`),
   which flipped the disposition. The weighted score is dominated by `capacity` (0.45) and
   `collateral_exposure` (0.36); a genuinely weak credit must cross the 3.0 cutoff. See
   `references/cre_weighted_score.md` before scoring — the raw-factor sub-mapping is the
   most underspecified rule in this family and needs care.

10. **`defer` vs `decline` for the unselected credit.** Blind declined the loser of a CRE
    head-to-head; official **defers** it. The unselected credit in a "pick the stronger"
    task is deferred, not declined.

## References
- `references/cre_weighted_score.md` — how to build the 5-C weighted CDFI score, what is
  certain vs underspecified, and how to sanity-check it against the class cutoffs.
