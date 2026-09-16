# Reasoning Guide

This guide captures reusable derivation patterns for credit-office public API tasks. It intentionally contains no solved task records.

## Source Priority

1. Prompt and answer template define the required scope and output shape.
2. `/api/policies` defines thresholds, formulas, weights, classes, and mitigation vocabulary.
3. Target API records define values.
4. Benchmarks define comparator metrics and versions.

When these appear to conflict, follow the prompt/template first, then the policy endpoint.

## Common Data Joins

Bank branch tasks usually need:

- `/api/branches/{branch_id}` for capacity, state, CRE limit, default sector ceiling, benchmark set.
- `/api/branches/{branch_id}/metrics` for total loans, delinquency, nonperforming loans, deposits, and current/prior quarter.
- `/api/branches/{branch_id}/loans` for portfolio, rating migration, watch-list, borrower, payment, DSCR, LTV, and balances.
- `/api/branches/{branch_id}/sector-exposures` for current sector exposure and sector limits.
- `/api/branches/{branch_id}/applications` for pending application scoring and allocation.

Credit-union segment tasks usually need:

- `/api/credit-union-segments/{segment_id}` for state, peer states, checklist gates, context, capacity, and risk tolerance.
- `/api/benchmarks/ncua/q1-2025` for state, US, and peer-state metrics.

## Risk Rating

Compute separate ratings from each available factor, then choose the worst numeric rating.

DSCR:

- `dscr >= 1.50` maps to rating 3.
- `1.25 <= dscr < 1.50` maps to rating 4.
- `1.05 <= dscr < 1.25` maps to rating 5.
- `1.00 <= dscr < 1.05` maps to rating 6.
- `dscr < 1.00` maps to rating 7.

LTV:

- `ltv <= 0.65` maps to rating 3.
- `0.65 < ltv <= 0.75` maps to rating 4.
- `0.75 < ltv <= 0.85` maps to rating 5.
- `0.85 < ltv <= 1.00` maps to rating 6.
- `ltv > 1.00` maps to rating 7.

Payment status minimums:

- Current has no automatic minimum.
- 30 days past due maps to at least rating 4.
- 60 days past due maps to at least rating 5.
- 90+ days past due maps to at least rating 7.
- Nonaccrual maps to at least rating 8.

Use the policy endpoint for the authoritative thresholds in case the environment changes.

## Watch-List Actions

Map the severity of the re-derived risk to a controlled action when the template asks for action coverage or workout queues:

- Rating 5 or lower: monitor, unless prompt asks only follow-up exceptions.
- Rating 6: watchlist.
- Rating 7: special_assets, or workout when the template/prompt emphasizes workout handling.
- Rating 8 or projected loss: partial_chargeoff_review unless legal referral is specifically supported by facts.

Do not invent an action outside the template enum.

## CDFI Factor Scores

Use policy factor-score bands, summing only available fields:

- LTV and debt-to-asset: lower leverage scores better; above 0.80 is the weakest ordinary band.
- FICO: higher scores better; below 580 is the weakest band.
- Liquidity months: more liquidity scores better; below 3 months is the weakest band.

Class the total score by policy class ranges. If a credit is both nonaccrual and collateral is underwater, classify as projected-loss when that enum is available.

## CRE Weighted Score

When the template asks for `weighted_cdfi_score`, use `/api/policies` weights for capacity, capital, character, collateral/exposure, and conditions. Build a transparent component table:

- Capacity: repayment coverage quality, including base and stressed DSCR.
- Capital: debt-to-asset or similar leverage measure.
- Character: delinquencies, bankruptcy, relationship depth, guarantor quality, and documentation.
- Collateral/exposure: LTV, collateral strength, and sector/CRE concentration.
- Conditions: benchmark underperformance, branch capacity, and policy exceptions.

Lower weighted scores are better. Use the policy score-class thresholds for `approve_quality`, `conditional`, and `weak`.

## Concentration

Use a consistent denominator:

```text
post_total_exposure = current_total_loans_or_sector_total + sum(approved_gross_amounts)
post_sector_exposure = current_sector_exposure + sum(approved_gross_amounts_in_sector)
post_approval_pct = post_sector_exposure / post_total_exposure
```

For retained-capacity fields, use bank-retained amounts after participation or guaranty mitigation:

```text
remaining_capacity = lending_capacity - sum(bank_capacity_used)
```

When a sector is already grandfathered over limit, do not treat grandfathering as permission to add exposure without mitigation.

## Benchmark Comparisons

FDIC benchmark rows are single objects with named ratio fields. Use the benchmark metric named by the template. Compare branch ratios from branch metrics:

- Nonperforming/noncurrent comparisons usually use `nonperforming_loans / total_loans_outstanding`.
- 30-89 delinquency comparisons use the branch `delinquency_30_plus_pct` when the prompt/template asks for delinquency.

NCUA benchmark rows include state and US records. For peer comparisons:

- Select the target state row from the segment `state_code`.
- Select peer rows from `peer_states`.
- Use the median of peer rows for each metric.
- Direction is from the target state's value relative to the comparator.
- For delinquency and loan-to-share, higher generally means more external risk.
- For ROAA and positive-net-income percentage, lower generally means more external risk.

## JSON Assembly

Populate exactly what the template asks for. Avoid extra keys unless clearly harmless and useful; most tasks expect only the requested shape.

For list ordering, honor the template text literally:

- Ascending IDs sort lexicographically.
- Descending exposure sorts numeric exposure descending, with ID as tie-breaker if requested.
- Reason codes and conditions sort alphabetically when requested.
- Peer state codes sort alphabetically.

Use `null` only when the template allows missing data. Otherwise omit optional records or choose the controlled enum supported by facts.
