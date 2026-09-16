# Partial-R2 Mediation Sensitivity

## Baseline Quantities

From the primary mediation models:
- a = path-a coefficient (exposure-to-mediator)
- b = path-b coefficient (mediator-to-outcome, from the direct model)
- SE_b = standard error of b
- total = total-effect coefficient (exposure-to-outcome without mediator)
- df = residual degrees of freedom from the direct model

## Sensitivity Magnitude

For declared R2 values rM (confounder-mediator) and rY (confounder-outcome):
- magnitude = SE_b * sqrt(df * rY * rM / (1 - rM))

## Adjusted Estimates

For each combination of (rM, rY) and direction in declared order:
- If direction is NEGATIVE: adjusted_b = b + magnitude
- If direction is POSITIVE: adjusted_b = b - magnitude
- adjusted_indirect = a * adjusted_b
- adjusted_direct = total - adjusted_indirect
- proportion = adjusted_indirect / total (mediated proportion)

## Surface Enumeration

Enumerate in declared order: r2_mediator ascending, r2_outcome ascending, then NEGATIVE before POSITIVE.
Report all combinations as the full surface array.

## Tipping Point

The equal-strength tipping R2 is the value of r2 (= rM = rY) such that the POSITIVE adjusted_indirect crosses zero (changes sign from the baseline):
- Solve for r2 where b - SE_b * sqrt(df * r2 * r2 / (1 - r2)) = 0
- i.e. SE_b * sqrt(df * r2^2 / (1 - r2)) = b
- Numerically find the root in [0, 1) or report if no root exists
- If the baseline indirect effect is negative, the tipping point is where the NEGATIVE adjusted indirect crosses zero.

## Decision Predicates

Typical gate: "Every POSITIVE row with both R2 values at most 0.08 preserves the nonzero baseline indirect-effect sign."
- Check all rows with direction = POSITIVE, rM <= 0.08, rY <= 0.08.
- The predicate passes if every such row's adjusted_indirect has the same sign as the baseline indirect effect (a * b).
