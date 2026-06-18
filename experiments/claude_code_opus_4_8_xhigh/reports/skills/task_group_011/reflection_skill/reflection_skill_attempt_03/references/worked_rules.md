# Derivation notes for the non-obvious rules

These show *how* each rule was confirmed against the official keys so a future solver can re-verify
on new branches/segments rather than trusting a remembered constant. Do not copy any single
example's output; re-pull the live data and re-derive.

## Action map keyed on final rating
Reconstructed by grouping the official watch-list coverage by action and intersecting with the
re-derived final ratings of the loans in each group: every loan in the `watchlist` group had final
6, every `special_assets` loan had final 7, the lone `partial_chargeoff_review` loan had final 8
(Nonaccrual). Coverage population = final ≥ 6. The map is deterministic on final_rating, so it
generalizes to any branch.

## Projected Loss override (ltv > 1.0)
Two watch-list loans had identical CDFI factor_score = 17 (Watch band, 14–18). The official answer
classed the one with ltv 1.18 as `Projected Loss` and the one with ltv 0.93 as `Watch`. The only
discriminator is ltv > 1.0. Interpretation: underwater collateral forces Projected Loss
irrespective of the numeric band; pair it with `recommended_action: partial_chargeoff_review` and
`projected_loss: true`.

## Participation sell-down to ceiling
Let `base = total_loans_outstanding`, `other_bank_used` = Σ bank_capacity_used of the other funded
apps, `existing_sector` = the breaching sector's current exposure, `limit` = sector limit_pct. The
retained amount r satisfies the bank-side ceiling exactly:

    existing_sector + r = limit * (base + other_bank_used + r)
  ⇒ r = (limit*(base + other_bank_used) - existing_sector) / (1 - limit)

Plugging the live Lakeview numbers (limit 0.19 Healthcare; base 14,334,094.87; other_bank_used =
sum of the consumer-equipment-SBA approvals) reproduces the official `bank_capacity_used` to the
cent. `committed_capacity_amount` is then Σ bank_capacity_used and `remaining_capacity =
lending_capacity_q1 − committed_capacity_amount` — both matched.

## SBA guaranty haircut
`bank_capacity_used = approved_amount * (1 - sba_guaranty_pct)`. A 0.75 guaranty on the SBA app
gave bank_used = approved × 0.25, matching the official figure. `approved_amount` stayed gross.

## Concentration denominator grows by gross approvals
post_approval Construction exposure = existing + the equipment app's full approved amount; dividing
by `(total_loans_outstanding + Σ gross approved amounts)` reproduced the official post_approval_pct
for every listed sector. Using a participation-haircut numerator/denominator did NOT match — gross
is correct. Only sectors that received a new approval appear in post_approval_concentrations.

## CRE weighted score factor mapping
weights: capacity 0.45, collateral_exposure 0.36, conditions 0.11, character 0.05, capital 0.03.
The two competing apps shared dscr_rating and ltv_sub but differed in debt_to_asset
(=total_debt/total_assets) sub-score (2 vs 6). The official score gap was exactly
0.45 × (6 − 2) = 1.8, proving **capacity sub-score = debt_to_asset sub-score**. The 0.36 term
matches the LTV CDFI sub-score (both apps ltv_sub 4 → 1.44). After capacity+collateral, each app
needed an identical +0.26 residual from conditions/character/capital (0.11/0.05/0.03). With two
data points the residual split is underdetermined; a consistent assignment is conditions ≈ 1,
character from the FICO sub-score (0 when fico is null), capital small. Because these carry tiny
weight, get capacity and collateral right first — they decide score_class
(approve_quality ≤2.0, conditional ≤3.0, weak >3.0). On a new task, re-derive the residual from
any app whose minor factors are populated rather than assuming.

## Benchmark ratios are metric fields where available
`branch_delinquency_ratio` for the RE 30-89 comparison = the branch `delinquency_30_plus_pct`
metric for the as-of quarter (matched the official 0.2853), not a reconstructed RE-only ratio.
`branch_npa_ratio` = branch noncurrent (e.g. `nonperforming_loans` metric or the Nonaccrual loan
balance) / `total_loans_outstanding`. variance_bps is computed from the unrounded ratio difference
× 10000, then rounded to 2dp.

## Segment posture sourcing
`required_checklist_gates` = segment `minimum_checklist` verbatim, source order preserved.
`peer_states` from the segment; compare NC to the US NCUA row and to the median of the peer states.
Escalation triggers: keep only those backed by a concrete segment condition (recent_delinquency_bps
near the 90bps line, the named insurance/lien control_issue, quarterly_capacity); the generic
state-gap trigger was excluded. Trigger ids `ET001..ET00n`, ascending.
