# Credit Office Rules

Use the API policy payload first. The formulas below summarize the reusable rules observed in the staged examples and should be checked against `/api/policies` during each task.

## Risk Rating Regrade

Include loans whose `current_rating` is at least the prompt's adverse or target minimum. Higher numeric ratings are worse.

Derive factor ratings from available fields and ignore null factors:

| Factor | Rule |
| --- | --- |
| DSCR | `>=1.50 -> 3`, `>=1.25 -> 4`, `>=1.05 -> 5`, `>=1.00 -> 6`, `<1.00 -> 7` |
| LTV | `<=0.65 -> 3`, `<=0.75 -> 4`, `<=0.85 -> 5`, `<=1.00 -> 6`, `>1.00 -> 7` |
| Delinquency | use `policies.risk_rating.delinquency_minimums`: `30 Days Past Due -> 4`, `60 Days Past Due -> 5`, `90+ Days Past Due -> 7`, `Nonaccrual -> 8`; current payments add no minimum |

Final re-derived rating is the worst numeric rating among available DSCR, LTV, and delinquency factors. If all factors are missing, retain `current_rating`.

Material downgrade means `final_rating - current_rating >= policies.risk_rating.material_downgrade_notches`.

Typical follow-up action mapping:

| Signal | Recommended action |
| --- | --- |
| Final rating 6 | `watchlist` |
| Final rating 7 or 90+ past due | `special_assets` |
| Final rating 8, nonaccrual, or projected loss | `partial_chargeoff_review` |
| Final rating 5 when follow-up is explicitly requested | `monitor` |

For a top problem credit, choose the highest final rating first, then the most severe payment status, then largest exposure.

## CDFI Factor Scores

Use available objective factors; do not penalize a missing nullable field unless the prompt or template says to.

| Factor | Score |
| --- | --- |
| LTV `<0.40`, `0.40-0.60`, `0.60-0.80`, `>0.80` | `0`, `2`, `4`, `6` |
| Debt-to-asset `<0.40`, `0.40-0.60`, `0.60-0.80`, `>0.80` | `0`, `2`, `4`, `6` |
| Liquidity months `>12`, `6-12`, `3-6`, `<3` | `0`, `1`, `3`, `5` |
| FICO `>720`, `680-720`, `580-679`, `<580` | `0`, `1`, `3`, `5` |

Sum factor scores. Classify as:

| Score | Class |
| --- | --- |
| `0-5` | `Prime` |
| `6-9` | `Desirable` |
| `10-13` | `Satisfactory` |
| `14-18` | `Watch` |
| `>=19` | `Doubtful` |

Use `Projected Loss` when collateral is underwater and the record also shows a loss severity signal such as nonaccrual status, explicit projected-loss notes, or an otherwise doubtful score.

## Stress Calculations

Use the formulas from `/api/policies.stress`:

- Watch-list stress: `stressed_dscr = dscr / (1 + 0.18)`.
- CRE dual stress: `stressed_dscr = dscr * 0.85 / (1 + 0.18)`.
- Breach threshold is normally `1.00`; a result breaches when stressed DSCR is below the threshold.

Only include stress rows for records with DSCR available. Round base and stressed DSCR to 2 decimals in final output.

## Benchmark Variance

Use the benchmark version string returned by the API.

- NPA/noncurrent benchmark: `branch_npa_ratio = nonperforming_loans / total_loans_outstanding`; compare with the requested FDIC noncurrent metric.
- Delinquency benchmark: use the branch metric ratio requested by the template or prompt, commonly `delinquency_30_plus_pct`, and compare with the matching FDIC `30_89` metric.
- `variance_ratio = branch_ratio - benchmark_ratio`.
- `variance_bps = variance_ratio * 10000`.

For NCUA posture tasks, compare the target state's NCUA metrics with `US` and with the median of the peer states listed by the segment endpoint. For each metric, output `higher`, `lower`, or `equal`.

## Concentration and Capacity

Current sector exposure comes from `/api/branches/{branch_id}/sector-exposures`. If a sector is absent, current exposure is zero and the branch's default sector ceiling may apply unless a sector-specific row is present.

Post-approval concentration is:

```text
sector_exposure_after_approval / total_exposure_after_approval
```

For gross concentration views, add full approved amounts to sector exposure and to the denominator. For committed capacity, use the bank-retained amount:

- Ordinary approval: retained amount equals approved amount.
- SBA guaranty: retained amount is `approved_amount * (1 - sba_guaranty_pct)`.
- Participation-required approval: solve the retained amount that keeps the sector at or below its limit after already selected commitments:

```text
x = (limit_pct * (current_total + prior_committed) - current_sector_exposure) / (1 - limit_pct)
```

Cap `x` between zero and the requested amount. Use a small cushion only if needed to avoid rounding over the limit.

Flag a concentration when an approval breaches a limit, materially worsens an already-over-limit sector, or sits close enough to the limit that the decision requires mitigation such as `participation_required`, `reduced_amount`, or `board_exception`.

## Application Decisions and Reason Codes

The template controls allowed decision and reason-code enums. Apply policy-style reasons consistently:

| Condition | Reason or condition |
| --- | --- |
| DSCR below the applicable floor, or stressed DSCR below threshold | `weak_dscr` |
| LTV above normal tolerance or collateral is underwater | `high_ltv` or `underwater_collateral` |
| FICO below normal tolerance | `low_fico` |
| Recent bankruptcy | `recent_bankruptcy` |
| Very young operating history | `startup_risk` |
| Missing required documentation or policy floor | `documentation_gap` or `policy_floor_missing` |
| Lending capacity is exhausted by stronger approved requests | `capacity_limit` |
| New money would breach or worsen a sector or CRE limit | `sector_breach` |
| Branch materially underperforms FDIC benchmark | `fdic_adverse_variance` |
| State/peer credit-union benchmarks are adverse | `ncua_peer_weakness` |

Approve the strongest credits first. Use `conditional_approve` for credits that are fundamentally acceptable but need SBA guaranty, startup monitoring, reduced amount, participation, or extra controls. Use `participation_required` when the credit is selected but bank-retained exposure must be capped for capacity or concentration.

For competing CRE decisions, calculate the CRE dual stress for each candidate, compare weighted credit quality, test existing and post-approval CRE concentration against branch policy, then select the stronger credit. The unselected credit is usually `defer` when it is weaker but not clearly unbankable; use `decline` when hard policy failures dominate.

## Validation Checklist

Before final response:

- Recompute totals from row-level records after sorting.
- Confirm every listed ID belongs to the target branch or segment.
- Confirm final totals equal grouped rows within rounding tolerance.
- Confirm basis points are ratio differences times 10000, not percentage points times 100.
- Confirm arrays follow template ordering, especially IDs, actions, sectors, ratings, and payment-status groupings.
- Confirm final output parses as JSON and has no extra text.
