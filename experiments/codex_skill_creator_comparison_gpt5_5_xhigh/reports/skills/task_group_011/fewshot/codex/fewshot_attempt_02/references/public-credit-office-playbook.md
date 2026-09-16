# Public Credit Office Playbook

## Contents
- Common sources
- Policy constants
- Task recipes
- Sort rules

## Common sources
- `GET /api/manifest` for version strings and the endpoint list.
- `GET /api/policies` for scoring, stress, and concentration rules.
- `GET /api/branches/{branch_id}` for branch profile data.
- `GET /api/branches/{branch_id}/metrics` for quarter metrics.
- `GET /api/branches/{branch_id}/loans` for existing portfolio loans.
- `GET /api/branches/{branch_id}/sector-exposures` for concentration by sector.
- `GET /api/branches/{branch_id}/applications` for pending applications.
- `GET /api/credit-union-segments/{segment_id}` for segment posture reviews.
- `GET /api/benchmarks/fdic/q4-2024` and `GET /api/benchmarks/ncua/q1-2025` for benchmark comparisons.

## Policy constants
### Risk rating
- DSCR thresholds: 1.5 -> 3, 1.25 -> 4, 1.05 -> 5, 1.0 -> 6, below 1.0 -> 7.
- LTV thresholds: 0.65 -> 3, 0.75 -> 4, 0.85 -> 5, 1.0 -> 6, above 1.0 -> 7.
- Delinquency minimums: Current -> none, 30 DPD -> 4, 60 DPD -> 5, 90+ DPD -> 7, Nonaccrual -> 8.
- Dominant factor rule: final re-derived rating is the worst numeric rating from the available factors.
- Material downgrade threshold: 2 notches.

### CDFI factor score map
- Debt-to-asset: <0.40 = 0, 0.40-0.60 = 2, 0.60-0.80 = 4, >0.80 = 6.
- FICO: >720 = 0, 680-720 = 1, 580-679 = 3, <580 = 5.
- Liquidity months: >12 = 0, 6-12 = 1, 3-6 = 3, <3 = 5.
- LTV: <0.40 = 0, 0.40-0.60 = 2, 0.60-0.80 = 4, >0.80 = 6.
- Class map: Prime 0-5, Desirable 6-9, Satisfactory 10-13, Watch 14-18, Doubtful >=19, Projected Loss >=19 with LTV > 1.0.

### CRE weighted score
- Weights: capacity 0.45, capital 0.03, character 0.05, collateral_exposure 0.36, conditions 0.11.
- Class map: approve_quality <= 2.0, conditional <= 3.0, weak > 3.0.
- Lower weighted score is better.

### Concentration
- Allowed mitigations: participation_required, reduced_amount, board_exception.
- Use `branches.lending_capacity_q1` as the lending capacity field.
- Use `branches.sector_ceiling_pct` as the single-sector default field.
- Use the `sector_exposures` table for branch-sector overrides.
- Existing over-ceiling exposure may be grandfathered, but new approvals may not worsen that sector without mitigation.

### Stress formulas
- CRE dual stress: `stressed_dscr = dscr * 0.85 / (1 + 0.18)`.
- Watch-list stress: `stressed_dscr = dscr / (1 + 0.18)`.
- Parallel shock label: `+200bp`.

## Task recipes
### Branch regrade
- Start from the prompt's current-rating floor.
- Recompute each loan using the policy thresholds and dominant factor rule.
- Record all loans whose final rating differs materially from current rating.
- Group follow-up actions by action type for the watch-list coverage section.

### Lending allocation
- Score each application with the CRE weights.
- Use branch capacity, requested amount, sector exposure, and concentration limits together.
- Approve or conditionally approve only the credits that fit the committee path.
- Sort `decline_reasons` values alphabetically for every declined application.

### Segment posture
- Compare the state row to the US row and the named peers on delinquency, loan-to-share, ROAA, and positive net income.
- Use tighter conditions when the state is weaker than the benchmark set but still operable.
- Tie checklist gates to funding documents and collateral perfection.

### Watch-list stress
- Identify loans with `current_rating >= 6`.
- Use all available objective factors to build the CDFI-style risk score.
- Stress only the loans with DSCR values.
- Queue the highest-exposure credits first, then break ties by loan ID.

### CRE comparison
- Compare the two applications on weighted score, stressed coverage, and concentration impact.
- Favor the stronger application only if the path remains policy-consistent.
- If the weaker credit is not selected, explain it only through the controlled reason codes.

## Sort rules
- Follow every template-specific ordering rule exactly.
- For unordered sets, emit a stable operational order.
- Use 2-decimal currency rounding, 4-decimal ratio rounding, and exact integers for benchmark values.
