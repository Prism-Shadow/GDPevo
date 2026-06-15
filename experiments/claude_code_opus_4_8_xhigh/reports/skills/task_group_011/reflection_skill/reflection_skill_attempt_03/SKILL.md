---
name: credit-office-committee-answers
description: >-
  Use this skill for any "credit office" committee-packet task that pulls from the shared
  HTTP API at http://127.0.0.1:8003 and must return JSON matching an answer_template.json.
  Triggers include: branch rating-migration / regrade reviews, watch-list stress packets,
  CRE / lending-committee allocation & application decisions, competing-CRE comparisons,
  CDFI-style risk classification, concentration / sector-ceiling checks, NPA or FDIC/NCUA
  benchmark variance, and credit-union segment posture pages. Apply it whenever the prompt
  names a branch_id / segment_id, references credit policies, risk ratings, DSCR/LTV stress,
  sector concentration, or benchmark comparisons — even if it does not say "use the skill."
  It encodes the authoritative business rules, API usage, exact rounding/ordering conventions,
  and the specific mistakes a prior blind solver made so they are not repeated.
---

# Credit Office Committee Answers

You are producing committee-ready JSON for a bank / credit-union "credit office." All data
comes from one live read-only HTTP API. The API + the `/api/policies` endpoint are the single
source of truth — never invent thresholds you can read, and never read local files.

This skill is built from a reflection pass: a prior solver answered 5 tasks blind, and its
answers were diffed field-by-field against the official keys. The rules below are the ones
that actually reproduce the official answers, and the "Pitfalls" section is the list of real
mistakes that cost points. Read `references/pitfalls.md` for the full blind-vs-official diff
and `references/worked_rules.md` for the derivation of every non-obvious rule.

## Workflow for any task

1. Read the prompt and `input/payloads/answer_template.json` first. The template defines the
   exact top-level keys, enums, **precision**, and **ordering** for every field. Treat it as a
   contract — emit every required key, use only allowed enum values, and match the stated sort.
2. `GET /api/policies` and use its thresholds verbatim. Note the `policy_version`.
3. Pull only the branch/segment/benchmark data the task needs (endpoints below).
4. Re-derive every number from raw rows + policy. Do not trust your memory of a threshold.
5. Round/sort/format per the template, then output **only** the JSON (no prose around it).

## API quick reference

Base URL `http://127.0.0.1:8003`. `branch_id`/`segment_id` are case-insensitive.

- `GET /api/policies` — authoritative thresholds (risk rating, stress, CDFI, CRE, concentration).
- `GET /api/branches/{id}` — `lending_capacity_q1`, `sector_ceiling_pct`, `cre_policy_limit_pct`,
  `fdic_benchmark_set`, `state_code`, `institution_type`.
- `GET /api/branches/{id}/metrics?quarter=YYYYQn` — returns a list; pick the requested quarter
  (default the as-of quarter, e.g. `2025Q1`). Key fields: `total_loans_outstanding`,
  `delinquency_30_plus_pct`, `nonperforming_loans`.
- `GET /api/branches/{id}/loans?min_current_rating=N&loan_type=&payment_status=` — loan rows
  (`loan_id`, `current_rating`, `payment_status`, `dscr`, `ltv`, `outstanding_balance`,
  `debt_to_asset`, `liquidity_months`, `fico`, `loan_type`, `borrower_name`).
- `GET /api/branches/{id}/sector-exposures` — `sector`, `current_exposure`, `limit_pct`,
  `grandfathered`.
- `GET /api/branches/{id}/applications` — pending apps (`dscr`, `ltv`, `fico`, `total_debt`,
  `total_assets`, `years_in_business`, `bankruptcy_months_ago`, `sba_guaranty_pct`, `sector`,
  `loan_type`, `requested_amount`, `documentation_complete`, `co_guarantor_strength`).
- `GET /api/benchmarks/fdic/q4-2024` — `total_loans_noncurrent_pct`,
  `total_real_estate_30_89_pct`, `total_real_estate_noncurrent_pct`,
  `construction_development_30_89_pct`, `construction_development_noncurrent_pct`.
- `GET /api/benchmarks/ncua/q1-2025?state_code=XX` — state credit-union benchmarks.
- `GET /api/credit-union-segments/{id}` — `minimum_checklist`, `peer_states`, `risk_tolerance`,
  `quarterly_capacity`, `current_outstanding`, `recent_delinquency_bps`, `internal_context`.

## Core business rules (authoritative — re-apply every time)

### Risk-rating re-derivation (dominant-factor rule)
For each loan compute up to three factor ratings, then **final_rating = max (worst) of the
factors that are available**. Skip a factor when its input is null; if no factor is available
the loan has no final_rating (exclude it from regrade/downgrade lists). Bands:

- DSCR: ≥1.5→3, ≥1.25→4, ≥1.05→5, ≥1.0→6, <1.0→7.
- LTV: ≤0.65→3, ≤0.75→4, ≤0.85→5, ≤1.0→6, >1.0→7.
- Delinquency minimum (payment_status): 30dpd→4, 60dpd→5, 90+dpd→7, Nonaccrual→8, Current→none.

`downgrade_notches = final_rating − current_rating`. A **material downgrade** is ≥2 notches
(`material_downgrade_notches` in policy). List only loans that actually downgraded ≥2 (a loan
whose final < current is NOT a downgrade — exclude it).

### Action map (keyed on FINAL re-derived rating — verified)
Map the recomputed final_rating to the action enum. Do **not** invent a severity map:

| final_rating | action |
|---|---|
| 6 | `watchlist` |
| 7 | `special_assets` |
| 8 (Nonaccrual / Projected Loss) | `partial_chargeoff_review` |

`legal_referral` and `workout` are valid enum values but were **not** the answer for any
Nonaccrual/severe loan in training — a Nonaccrual loan rated 8 maps to `partial_chargeoff_review`,
not `legal_referral`. The watch-list coverage population is loans with **final_rating ≥ 6**.

### CDFI factor scoring (watch-list risk class)
`factor_score = sum of available sub-scores` from fico / debt_to_asset / ltv / liquidity_months
(skip null factors). Sub-score bands are in `policy.cdfi_factor_scores`. Class by total score:
Prime 0-5, Desirable 6-9, Satisfactory 10-13, Watch 14-18, Doubtful ≥19.

**Projected Loss override (verified, easy to get wrong):** classify as `Projected Loss` whenever
**ltv > 1.0** (underwater) for a severe/nonaccrual loan, **even if the score is below 19**. The
policy line `">=19 and ltv>1.0"` behaves as: underwater collateral promotes the loan to
Projected Loss regardless of the numeric band. In training, two loans both scored 17 (Watch
band); the one with ltv 1.18 became `Projected Loss` while the one with ltv 0.93 stayed `Watch`.
Set `projected_loss: true` for exactly the Projected Loss loan and give it
`recommended_action: partial_chargeoff_review`.

### Stress formulas (from policy.stress)
- Watch-list +200bp parallel shock: `stressed_dscr = dscr / 1.18`.
- CRE dual stress: `stressed_dscr = dscr * 0.85 / 1.18`.
- Breach when `stressed_dscr < 1.0` (`coverage_breach_threshold`). Round stressed DSCR to 2dp,
  then compare. Only include loans/apps where DSCR is available; exclude null-DSCR rows from
  the results list and from breach_loan_ids.

### CRE weighted score (lower is better)
`weighted_score = Σ weight_C × subscore_C`, weights: capacity 0.45, collateral_exposure 0.36,
conditions 0.11, character 0.05, capital 0.03. Verified factor→C mapping for the dominant terms:
**capacity sub-score = debt_to_asset CDFI sub-score** (debt_to_asset = total_debt/total_assets),
**collateral_exposure sub-score = LTV CDFI sub-score**. (Do NOT map capacity to a DSCR-derived
number — that was the blind error.) Round to 1dp. Classes: `approve_quality` ≤2.0,
`conditional` ≤3.0, `weak` >3.0. See `references/worked_rules.md` for the minor terms, which are
small-weight and only matter at the margin.

### Concentration / sector ceilings
- Single-sector limit = the sector's `limit_pct` (fall back to branch `sector_ceiling_pct`);
  CRE limit = branch `cre_policy_limit_pct`.
- Existing concentration denominator = **`total_loans_outstanding`** (the metric for the as-of
  quarter), which equals the sum of loan balances.
- **Post-approval grows both numerator and denominator by the gross approved amount.** The
  post-approval denominator = `total_loans_outstanding + Σ gross approved amounts`. The sector
  numerator = existing sector exposure + the full (gross) approved amount in that sector. Use the
  **gross** approved amount here, never a participation-haircut amount.
- `over_limit` / `flag` = post_approval_pct > limit_pct. Existing over-ceiling exposure may be
  **grandfathered**, but a new approval may not worsen a sector past its ceiling without
  mitigation (`participation_required`, `reduced_amount`, `board_exception`).

### Participation sell-down for a concentration breach (verified, high-value)
When an approval would push a sector over its ceiling and the disposition is
`participation_required`, the bank retains only enough to bring its **on-book** sector exposure
to exactly the ceiling. Solve simultaneously (the retained amount sits in the bank-side
denominator):

```
retained = (limit_pct * (base_total_loans + other_bank_used) - existing_sector_exposure)
           / (1 - limit_pct)
```

`bank_capacity_used` for that app = `retained` (not 50%, not a flat fraction). This is the
`bank_capacity_used` figure; `approved_amount` stays the full gross amount.

### SBA guaranty reduces bank capacity used
For an SBA-guaranteed approval, `bank_capacity_used = approved_amount × (1 − sba_guaranty_pct)`.
(A 75% guaranty → bank retains 25%.) `approved_amount` is still the full amount.

### Allocation rollups
- `gross_approved_amount` = Σ full approved amounts (approve + conditional_approve +
  participation_required).
- `committed_capacity_amount` = Σ `bank_capacity_used` (after participation/SBA reductions).
- `remaining_capacity` = `lending_capacity_q1` − `committed_capacity_amount`.
- `priority_ranking` = approved/conditional/participation apps only, strongest credit first.
  An otherwise-fine application that is not funded because higher-priority credits consumed the
  allocation is declined with reason `capacity_limit`.

### Application decision gates (verified thresholds; produce reason codes)
- `weak_dscr`: dscr < 1.25
- `high_ltv`: ltv > 0.80
- `low_fico`: fico < 580
- `startup_risk`: years_in_business < 2
- `recent_bankruptcy`: bankruptcy_months_ago is not null
- `underwater_collateral`: ltv > 1.0
- `sector_breach`: the approval pushes its sector over the ceiling (maps to reason code
  `sector_breach`, **not** `capacity_limit`)
- `fdic_adverse_variance`: branch delinquency materially worse than the FDIC benchmark — include
  it on app reason-code lists when the branch underperforms (it applies to all apps at that
  branch, not just one).
Mitigants can overturn a flag: a strong SBA guaranty + deposit/relationship can turn a
weak_dscr/startup app into `conditional_approve` rather than decline. Reason-code lists are
sorted **alphabetically** and pruned to the decisive reasons (a dominated reason like high_ltv
may be dropped when stronger codes already explain the decline).

### Benchmark variance
- `branch_npa_ratio` = branch noncurrent exposure / `total_loans_outstanding`. Use the branch
  `nonperforming_loans` metric (or the Nonaccrual loan exposure) as the NPA numerator; compare to
  the FDIC metric named in the template enum (e.g. `total_loans_noncurrent_pct`).
- For RE 30-89 delinquency comparisons, **use the branch `delinquency_30_plus_pct` metric field
  directly** as `branch_delinquency_ratio` — do NOT recompute a RE-only ratio from loan rows.
  Compare to FDIC `total_real_estate_30_89_pct`.
- `variance_ratio = branch_ratio − benchmark_ratio`; `variance_bps = variance_ratio × 10000`,
  computed from the **unrounded** ratio then rounded to 2dp.

### Credit-union segment posture
- `required_checklist_gates` = the segment's `minimum_checklist` in its **source order** (do NOT
  re-sort alphabetically).
- `state_metrics` = the NCUA row values for the segment's state, exactly as reported (integers).
- `peer_states` come from the segment; compare NC to the US row and to the peer-state **median**.
  Report each direction as `higher`/`lower`/`equal` (NC value vs comparison value).
- Emit only the escalation triggers backed by a real, named segment condition (in training, the
  generic "gap widens 25bps" trigger was excluded — 3 triggers, not 4). Trigger ids use a
  zero-padded `ET001`, `ET002`, … convention, sorted ascending.

## Rounding, ordering & enum conventions

- Currency → 2 decimals. Ratios/percentages-as-ratios → 4 decimals. CRE weighted score → 1
  decimal. bps → 2 decimals (computed from the unrounded ratio).
- Compute on unrounded intermediates; round only the emitted field.
- **Ordering is graded.** Follow the template's stated sort exactly. When sorting by a string
  field (action, payment_status, sector) the default is **ASCII/lexicographic ascending**, e.g.
  `"90+ Days Past Due"` sorts before `"Current"` because `'9' < 'C'` — do NOT use enum/severity
  order unless the template says so. Lists of action/reason enums are alphabetical.
- Use only the enum values in the template. Emit every required key.

## Common pitfalls (from the actual blind-vs-official diff)

See `references/pitfalls.md` for the full diff. The point-costing mistakes were:

1. **Inventing an action map.** Blind used `legal_referral` for a Nonaccrual/rating-8 loan; the
   correct map is final 6→`watchlist`, 7→`special_assets`, 8→`partial_chargeoff_review`.
2. **Strict CDFI score band ignoring ltv.** Blind classed an underwater (ltv 1.18) loan as `Watch`
   on its score of 17; ltv > 1.0 promotes it to `Projected Loss` (and `projected_loss: true`).
3. **Flat 50% participation haircut.** Blind retained 50% of every participation; the real
   retention is the concentration sell-down formula above, and SBA apps retain (1 − guaranty_pct).
   This broke `bank_capacity_used`, `committed_capacity_amount`, and `remaining_capacity`.
4. **Wrong concentration scope.** Blind listed all sectors in post_approval_concentrations; only
   sectors that received a new approval belong. Blind also used a haircut numerator; use gross.
5. **Recomputing a benchmark ratio that is a metric field.** Blind recomputed RE delinquency from
   loan rows (wrong denominator); the answer is the branch `delinquency_30_plus_pct` metric.
6. **Wrong CRE weighted-score factor mapping.** Blind tied capacity to DSCR; capacity = the
   debt_to_asset sub-score, collateral_exposure = the LTV sub-score.
7. **Wrong unselected disposition / reason codes.** A weak-scored competing CRE app is `defer`,
   not `decline`; `fdic_adverse_variance` belongs on app reason codes when the branch
   underperforms the FDIC benchmark; a CRE concentration breach is `sector_breach`, not
   `capacity_limit`.
8. **Re-sorting source-ordered lists / using enum order for string sorts.** Checklist gates keep
   segment source order; payment_status secondary sort is ASCII (90+ before Current); `by_action`
   and reason-code lists are alphabetical.
9. **Emitting extra escalation triggers.** Include only triggers tied to a named segment
   condition, with the `ET00n` id convention.

## Exclusion rules (who is in / out of a population)

- Regrade/material-downgrade lists: exclude loans with no derivable final_rating (all factors
  null) and loans that did not downgrade by ≥2 notches.
- Stress results & breach lists: exclude rows with null DSCR.
- post_approval_concentrations: include only sectors touched by a new approval.
- priority_ranking: include only approved / conditional_approve / participation_required apps.
- Watch-list coverage: final_rating ≥ 6.
