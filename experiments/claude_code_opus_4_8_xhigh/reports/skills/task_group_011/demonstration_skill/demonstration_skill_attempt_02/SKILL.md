---
name: credit-committee-packets
description: >
  Produce committee-ready JSON answers for the shared Credit Office / lending-committee
  task family backed by the HTTP API at http://127.0.0.1:8003. Use this skill WHENEVER a
  prompt asks you to prepare a credit-risk, lending-committee, or credit-union-segment
  packet against that environment — including branch loan-rating migration / regrade reviews,
  watch-list stress and workout queues, pending-application capacity & concentration
  allocations, competing CRE underwriting decisions, and credit-union segment posture pages.
  Trigger on cues like "rating migration", "regrade", "watch-list stress", "+200bp DSCR
  stress", "lending-committee allocation", "concentration flags", "decline reason codes",
  "weighted CRE / CDFI score", "segment posture", "branch_id", "segment_id", "answer_template.json",
  or any request that says to follow input/payloads/answer_template.json and return only JSON.
  Always read the live /api/policies endpoint for authoritative thresholds rather than
  guessing numbers.
---

# Credit Committee Packets

You produce a single JSON object that conforms to the task's `answer_template.json`. The
underlying data lives behind a read-only HTTP API; the **policy endpoint is the single
source of truth** for every threshold and formula. Never hardcode thresholds from memory or
from a worked example — re-read them from the API each run, because branch limits and policy
bands vary per task.

## Golden rules (apply to every task)

1. **Output is JSON only.** No prose, no markdown fences, nothing outside the object. Emit
   exactly the keys the template lists, in the template's structure. Extra keys are risk;
   missing required keys fail.
2. **The API is the only data source.** Use `curl`/`urllib` against `http://127.0.0.1:8003`.
   Ignore any mention of `env/setup.sh`, local DBs, or files — the service is already up.
   Treat every number as authoritative; do not re-estimate it.
3. **Re-read `/api/policies` every run** and drive all bands/weights/formulas from it. Branch
   objects carry their own `cre_policy_limit_pct`, `sector_ceiling_pct`, and
   `lending_capacity_q1`; sector rows carry their own `limit_pct`. Use the per-entity value,
   not a global default.
4. **Use only enum values the template allows.** Reason codes, decisions, actions, postures,
   risk classes, conditions, owners — all are closed vocabularies. Never invent a value.
5. **Respect rounding and ordering exactly** (see "Precision & ordering" below). The grader
   compares numbers and list order literally.
6. **Compute the helper script once.** `scripts/credit_office.py` wraps the API and the
   policy math (risk re-derivation, CDFI scoring, stress, ratios). Read it and reuse it
   instead of re-deriving formulas by hand.

## How to approach any task in this family

1. Read the prompt and the staged `input/payloads/answer_template.json`. The template's
   `required_top_level_keys`, `item_required_keys`, `allowed_values`/`choices`, `ordering`,
   and `precision`/`numeric_precision` notes ARE the spec. Build your output shape from it.
2. Identify the variant from the requested keys and verbs (see `references/playbooks.md`):
   - **regrade / rating migration** → portfolio_regrade + npa_benchmark + material_downgrades + top_problem_credit
   - **watch-list stress / workout** → watch_list_summary + stress_results + workout_queue + severe_bucket_counts
   - **allocation / pending applications** → allocation + decisions + concentration_flags + decline_reasons + post_approval_concentrations
   - **competing CRE decision** → applications_compared + recommended_path + stress + concentration + conditions
   - **credit-union segment posture** → posture + state_metrics + peer_comparison + controls + escalation_triggers + interpretation
3. Pull `/api/policies` and the entity data the prompt names (`branch_id` or `segment_id`).
   Fetch exactly the surfaces the prompt lists; extra fetches are fine but do not invent data.
4. Apply the playbook for that variant (`references/playbooks.md`) using policy thresholds.
5. Assemble JSON, apply precision/ordering, validate enums, print only the JSON.

## Core business rules (driven by `/api/policies`, schema in `references/policy.md`)

These are stable across tasks; the exact numbers come from the live policy each run.

**Risk-rating re-derivation (dominant-factor rule).** For a loan, compute a candidate rating
from each *available* objective factor and take the **worst (highest) numeric rating**:
- DSCR → `risk_rating.dscr_thresholds` (first band whose `min` is met, descending; if DSCR <
  the lowest `min`, use the `max_below` band, i.e. rating 7).
- LTV → `risk_rating.ltv_thresholds` (first band whose `max` is satisfied, ascending; if LTV
  exceeds the top `max`, use the `min_above` band, rating 7).
- Delinquency → `risk_rating.delinquency_minimums[payment_status]` is a *floor* (e.g.
  Nonaccrual ≥ 8, 90+ ≥ 7, 60 ≥ 5, 30 ≥ 4; "Current" is null = no floor).
- Final rating = max of the available candidates. **If no factor is available (no DSCR, no
  LTV, payment_status Current → null floor), keep the loan's existing `current_rating`.**
- A downgrade is **material** when `final_rating − current_rating ≥ risk_rating.material_downgrade_notches`.

**CDFI factor scoring (additive, lower is better).** Sum the four factor scores from
`cdfi_factor_scores` for FICO, LTV, debt_to_asset, liquidity_months. A factor that is missing
contributes 0 (it cannot be scored). Map the total to a class via the score bands
(Prime 0-5, Desirable 6-9, Satisfactory 10-13, Watch 14-18, Doubtful ≥19). **Projected Loss
override:** a credit already in the Watch band or worse whose **LTV > 1.0** (underwater
collateral) is reported as `Projected Loss` rather than its score-band class.

**CRE weighted score (lower is better).** `cre_weighted_score.weights` (capacity 0.45,
collateral_exposure 0.36, conditions 0.11, character 0.05, capital 0.03) weight CDFI-style
factor scores. Class from `cre_weighted_score.classes`: `approve_quality` ≤ 2.0,
`conditional` ≤ 3.0, `weak` > 3.0. The class and the resulting decision are the gradeable
outputs; weight the per-C factor scores as described in `references/playbooks.md`.

**Stress formulas** (from `stress`):
- Watch-list +200bp parallel shock: `stressed_dscr = dscr / (1 + 0.18)`.
- CRE dual stress: `stressed_dscr = dscr * 0.85 / (1 + 0.18)`.
- Breach when `stressed_dscr < coverage_breach_threshold` (1.0). Only loans/apps **with a
  DSCR** appear in stress results; skip rows where DSCR is null.

**Recommended-action / workout mapping** keyed off the effective severity rating
(re-derived final rating, or current_rating where the variant specifies):
rating 8 / Nonaccrual / Projected Loss → `partial_chargeoff_review`; rating 7 →
`special_assets`; rating 6 → `watchlist`. Lower/healthier → `monitor`. Reserve
`legal_referral`/`workout` for cases the prompt explicitly calls out.

**Capacity & concentration.**
- `lending_capacity_q1` is the branch quarterly capacity. `bank_capacity_used` for an approved
  app = approved amount, **reduced** by participation (bank retains a portion) and by SBA
  guaranty (`approved × (1 − sba_guaranty_pct)`).
- `committed_capacity_amount` = Σ `bank_capacity_used`; `remaining_capacity` =
  `lending_capacity_q1 − committed_capacity_amount`; `gross_approved_amount` = Σ approved
  amounts (full, before participation/SBA reduction) for approved + conditional apps.
- Concentration % = sector exposure ÷ **post-approval total portfolio** (Σ all sector
  current_exposures + all approved additions), rounded to 4 decimals. Compare to the sector's
  `limit_pct` (or branch `sector_ceiling_pct`). Existing over-ceiling exposure may be
  grandfathered, but a new approval may not worsen a breached sector without a mitigation
  (`participation_required`, `reduced_amount`, `board_exception`).

**Benchmark variance.** Branch ratio − benchmark ratio. **`variance_bps` is computed from the
UNROUNDED ratios** `(branch_ratio − benchmark_ratio) × 10000` then rounded to 2 dp — do NOT
multiply the already-rounded 4-dp `variance_ratio`, which loses precision. Pick the benchmark
metric the template's enum specifies (e.g. `total_loans_noncurrent_pct` for NPA,
`total_real_estate_30_89_pct` for CRE real-estate delinquency).

## Precision & ordering (grader compares literally)

- Currency (USD) fields → 2 decimals. Ratios/percentages-as-ratios → 4 decimals. bps → 2
  decimals (from unrounded inputs, per above). CRE weighted score → 1 decimal. DSCR base/
  stressed → 2 decimals. Counts/ratings → integers.
- Emit ratios as decimals (0.1897), never as "18.97%".
- Apply each list's stated `ordering` exactly. Common ones: ascending `loan_id` /
  `application_id` (string sort), ascending `final_rating`, reason codes ascending
  alphabetically, sectors ascending, peer states ascending, workout queue **descending
  exposure then ascending loan_id**, severe buckets ascending current_rating then ascending
  payment_status (plain string sort, so "90+ Days Past Due" sorts before "Current").
- NCUA state-benchmark integers (delinquency_bps, loan_to_share_pct, roaa_bps,
  positive_net_income_pct) are reported **exactly as the table gives them** — no recomputation.

## Common misjudgments to avoid

- **Don't drop the no-factor loans.** A loan with no DSCR/LTV and a Current status stays at
  its `current_rating` and still counts in totals — it does not vanish or become rating 0.
- **Population filters are inclusive and literal.** "rated 3 or worse" = `current_rating ≥ 3`;
  "current_rating 6 or worse" = `≥ 6`; "adversely rated" uses the rating the prompt names.
- **Stress only covers DSCR-available rows.** Missing-DSCR loans are excluded from
  `stress_results`/`results` but may still appear in other sections.
- **bps from unrounded ratios** (see above) — the single most common numeric error.
- **Concentration denominator is the portfolio post-approval total, not metrics
  `total_loans_outstanding` and not the lending capacity.**
- **SBA guaranty and participation reduce capacity used, not the approved/gross amount.**
- **Enums only.** A plausible-sounding label that isn't in the template's list is wrong.
- **score_class/decision, not the raw weighted score, are usually graded** — when a weighted
  decomposition is ambiguous, get the class band and the decision right and keep the score
  consistent with the band.
- **NPA/CRE benchmark metric must match the template enum**, not whatever metric seems closest.

## References

- `references/policy.md` — annotated structure of `/api/policies` and every band/weight, plus
  the exact endpoint list and the fields that matter on each surface.
- `references/playbooks.md` — step-by-step SOP for each of the five known variants, including
  field-by-field derivation and the data surfaces each variant needs.
- `scripts/credit_office.py` — runnable helper: API client + policy-driven functions for risk
  re-derivation, CDFI scoring, stress, ratios, and rounding/ordering. Import or copy it.
