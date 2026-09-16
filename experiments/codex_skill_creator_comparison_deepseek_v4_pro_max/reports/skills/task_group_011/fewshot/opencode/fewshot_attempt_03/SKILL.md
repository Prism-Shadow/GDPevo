---
name: credit-risk-committee
description: Prepare credit-risk committee packets from the shared credit office API. Use this skill whenever the user asks for a committee review, branch portfolio analysis, lending allocation package, credit union segment posture, watch-list stress test, competing CRE decision, rating migration review, or any credit-risk report that references branch IDs, application IDs, segment IDs, FDIC/NCUA benchmarks, risk ratings, CDFI scores, DSCR stress, concentration limits, or the shared credit office API. Triggers on any mention of credit committee, lending committee, loan review, portfolio regrade, adverse-rated loans, nonperforming loans, NPA benchmarks, sector exposure limits, or credit union segment posture.
---

# Credit Risk Committee Packet Preparation

Prepare committee-ready JSON answers using the shared credit office public API. Every task requires fetching live data, applying policy rules for derivations, and returning JSON that exactly matches the provided answer template.

## API Primer

The base URL is supplied as `<TASK_ENV_BASE_URL>`. No credentials are needed. Use these public endpoints:

| Endpoint | What it returns |
|---|---|
| `GET /api/manifest` | Benchmark versions, record counts, policy version |
| `GET /api/policies` | Risk-rating rules, CDFI factor scores, CRE weighted-score weights, stress formulas, capacity/concentration rules |
| `GET /api/branches` | All branches: ids, lending capacity, sector ceilings, CRE limits, institution type, state, total assets |
| `GET /api/branches/{id}` | Single branch detail |
| `GET /api/branches/{id}/metrics` | Branch metrics: total loans, deposits, NPA, delinquency, allowance, charge-offs (by quarter) |
| `GET /api/branches/{id}/loans` | Loan portfolio: ratings, balances, DSCR, LTV, collateral, FICO, debt-to-asset, liquidity, payment status, sector, loan type |
| `GET /api/branches/{id}/sector-exposures` | Per-sector exposure, limit, grandfathered flag |
| `GET /api/branches/{id}/applications` | Pending applications with applicant/business details, financials, loan type, purpose, sector |
| `GET /api/benchmarks/fdic/q4-2024` | FDIC Q4 2024: five benchmark ratios |
| `GET /api/benchmarks/ncua/q1-2025` | NCUA Q1 2025: state-level rows with delinquency, loan-to-share, ROAA, net income; includes "US" national row |
| `GET /api/credit-union-segments/{segment_id}` | Segment metadata: member profile, peer states, quarterly capacity, minimum checklist, internal context, risk tolerance |

**Fetch all needed data first.** Start with policies and the manifest, then the target entity's endpoints. Do not guess at policy values — always read `/api/policies` and apply the rules from it exactly.

## Risk Rating Derivation (Dominant Factor)

Applied whenever the task asks to re-derive or compute risk ratings. The policy rule is: **final rating = worst (highest numeric) rating from available DSCR, LTV, and delinquency factors.**

### DSCR-to-rating

| DSCR | Rating |
|---|---|
| >= 1.50 | 3 |
| >= 1.25 | 4 |
| >= 1.05 | 5 |
| >= 1.00 | 6 |
| < 1.00 | 7 |

If a loan has no DSCR, skip this factor.

### LTV-to-rating

| LTV | Rating |
|---|---|
| <= 0.65 | 3 |
| <= 0.75 | 4 |
| <= 0.85 | 5 |
| <= 1.00 | 6 |
| > 1.00 | 7 |

If a loan has no LTV and no collateral_value, skip this factor. When LTV is null but collateral_value exists, compute `ltv = outstanding_balance / collateral_value`.

### Delinquency floor

| Payment Status | Minimum Rating |
|---|---|
| Current | (no floor) |
| 30 Days Past Due | 4 |
| 60 Days Past Due | 5 |
| 90+ Days Past Due | 7 |
| Nonaccrual | 8 |

### Material downgrade threshold

A downgrade of **2 or more notches** is material. Count notches as `final_rating - current_rating`.

### NPA identification

Loans on **Nonaccrual** status are nonperforming. The branch NPA exposure is the sum of outstanding_balance for all Nonaccrual loans. For NPA ratio: `npa_exposure / branch_total_loans_outstanding`.

### Watch-list action assignment

After regrade, assign each loan to the most severe action appropriate for its final rating and payment status:

| Final Rating | Minimum Action |
|---|---|
| 3-4 | monitor |
| 5-6 | watchlist |
| 7 | special_assets |
| 8 | partial_chargeoff_review |

Escalation guidance: Nonaccrual loans at rating 8 → `partial_chargeoff_review`. 90+ Days Past Due → at least `special_assets`. A loan with projected loss (LTV > 1.0 and score >=19) → `partial_chargeoff_review`. Only include loans requiring action (rating >=5 for watch-list coverage), not monitor-only loans unless the task explicitly includes them.

## CDFI Factor Scoring

Used for risk-class assignment and CRE weighted scoring. Score each factor by looking up its value in the `/api/policies` `cdfi_factor_scores` tables, then sum. The four factors are: **fico**, **ltv**, **debt_to_asset**, **liquidity_months**.

Mapping `factor_score` (sum of the four sub-scores) to `risk_class`:

| Score Range | Risk Class |
|---|---|
| 0-5 | Prime |
| 6-9 | Desirable |
| 10-13 | Satisfactory |
| 14-18 | Watch |
| >=19 | Doubtful |
| LTV > 1.0 (any score) | Projected Loss |

If any factor value is null, score it as **0** for that factor. If LTV is null but collateral_value exists, compute LTV as `outstanding_balance / collateral_value` before scoring. LTV > 1.0 forces `Projected Loss` regardless of total factor score.

## CRE Weighted Scoring

Used for comparing CRE applications. The five dimensions and their weights are in `/api/policies` `cre_weighted_score.weights`. Compute sub-scores for each available dimension, then compute the weighted sum. Score classes from total weighted score:

| Weighted Score | Class |
|---|---|
| <= 2.0 | approve_quality |
| <= 3.0 | conditional |
| > 3.0 | weak |

**Lower weighted score is better.** For qualitative dimensions without explicit numeric value (capacity, capital, character, conditions), use reasonable judgment anchored in the application data and branch context. For collateral_exposure, use the CDFI factor score or LTV/concentration-based proxies.

## Stress Formulas

From `/api/policies` `stress`:

**Watch-list +200bp parallel shock:**
```
stressed_dscr = dscr / (1 + 0.18)
```

**CRE dual stress (tenant roll + rate shock):**
```
stressed_dscr = dscr * 0.85 / (1 + 0.18)
```

**Breach threshold:** 1.0 in both formulas. A loan breaches when `stressed_dscr < 1.0`. When DSCR is unavailable for a loan, omit it from stress results.

## Benchmarks

### FDIC Q4 2024

Five metrics. Common selections:

| Metric | Use case |
|---|---|
| `total_loans_noncurrent_pct` | NPA comparison |
| `total_real_estate_noncurrent_pct` | CRE NPA |
| `total_real_estate_30_89_pct` | CRE delinquency |
| `construction_development_noncurrent_pct` | C&D NPA |

Compute branch ratio as: `branch_value / branch_total_loans_outstanding`. Then `variance_ratio = branch_ratio - benchmark_ratio`. `variance_bps = variance_ratio * 10000`.

Always use the **latest** quarter from branch metrics (first item in the array) for current-period ratios.

### NCUA Q1 2025

State-level rows plus a "US" national row. When the task specifies a state, find its row. The US row is the national comparison. Peer states and the state code come from the credit-union segment data.

For peer median: sort the metric values for all peer state rows, pick the middle value. If even number of peers, average the two middle values — but the answer values imply the simple median.

Direction comparisons: compare NC value to US value and to peer median. "higher", "lower", or "equal" (use "equal" only when values match exactly).

## Allocation and Capacity

From `/api/policies` `capacity_concentration`:
- `lending_capacity_q1` is on the branch object
- `sector_ceiling_pct` is the default single-sector limit; sector-specific limits from `/api/branches/{id}/sector-exposures` override it
- CRE has its own `cre_policy_limit_pct` on the branch
- Existing over-ceiling exposure may be grandfathered, but new approvals may not worsen that sector without mitigation

**Capacity consumed:** For a standard approval, `bank_capacity_used = approved_amount`. For participation: only the bank's retained portion counts. The template specifies the exact field.

**Concentration check:** `post_approval_pct = (existing_sector_exposure + approved_amount) / branch_total_loans_outstanding`. Flag as over-limit when this exceeds the sector's `limit_pct`.

**Priority ranking:** Order approved and conditionally approved applications by priority (highest first). Factors: score class, DSCR strength, relationship depth, sector alignment, and whether conditions are needed.

## Decision Logic for Applications

Evaluate each application against these gates:

1. **Policy floors**: Check DSCR, LTV, FICO against minimum acceptable thresholds. Identify weak financials.
2. **Sector limits**: Would approval breach the sector concentration limit?
3. **Capacity**: Is there remaining Q1 lending capacity for the bank's retained portion?
4. **Benchmark variance**: Does the branch have adverse FDIC variance for this loan type?
5. **Qualitative**: Years in business, prior delinquencies, guarantor strength, relationship.

**Decision outputs:**
- `approve` — passes all gates, no conditions needed
- `conditional_approve` — passes with mitigation (participation, SBA guaranty, board exception, reduced amount, startup monitoring)
- `decline` — fails one or more gates with no viable mitigation
- `defer` — needs more information or conditions not currently met
- `participation_required` — risk must be shared to be acceptable

Match decline reason codes to the specific gate that failed, exactly from the template's enum.

## Output Rules

1. Return **only** valid JSON — no narrative, no markdown fences, no commentary outside the JSON object.
2. Match every key, type, enum, ordering, and precision rule from `answer_template.json`.
3. Sort lists exactly as the template specifies (ascending/descending by the named field).
4. Round numeric fields to the precision specified in the template.
5. Use exactly the enum values listed in the template — never invent new ones.
6. Include all required keys even when the value is zero, empty, or "none".


## Helper Script

A deterministic Python script for policy computations is at [scripts/compute.py](scripts/compute.py). Use it to eliminate arithmetic errors on risk ratings, CDFI factor scores, stress DSCR, and FDIC benchmarks:

```
python3 scripts/compute.py rating loans.json policies.json     # re-derive ratings
python3 scripts/compute.py cdfi loans.json policies.json       # CDFI factor scores + risk class
python3 scripts/compute.py stress loans.json watchlist         # watch-list +200bp shock
python3 scripts/compute.py stress apps.json cre                # CRE dual stress
python3 scripts/compute.py benchmark-fdic metrics.json fdic.json  # FDIC variance
python3 scripts/compute.py ncua-median ncua.json SC,TN,VA      # peer median
```

The script writes enriched JSON to stdout. Pipe it to a temp file and use the computed fields (computed_final_rating, computed_cdfi_score, computed_risk_class) in the final answer.
## Task-Type Workflows

Detailed step-by-step workflows for each task type are in [references/task-patterns.md](references/task-patterns.md). Read that file when you need the exact sequence for a portfolio regrade, lending allocation, CU segment posture, watch-list stress, or competing CRE decision.
