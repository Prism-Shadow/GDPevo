# API Reference

## Contents

- [Endpoints](#endpoints)
- [Policy Rules](#policy-rules)
- [Packet Patterns](#packet-patterns)
- [Output Checks](#output-checks)

## Endpoints

- `/api/manifest`: confirm `policy_version`, benchmark versions, record counts, and available public endpoints.
- `/api/policies`: source for scoring, rating, concentration, and stress rules.
- `/api/benchmarks/fdic/q4-2024`: FDIC ratios used by branch and CRE packets.
- `/api/benchmarks/ncua/q1-2025`: state benchmark rows keyed by `state_code`.
- `/api/branches/{branch_id}`: branch facts.
- `/api/branches/{branch_id}/metrics`: branch metrics used for regrade, allocation, and CRE concentration tasks.
- `/api/branches/{branch_id}/loans`: loan portfolio for branch review and watch-list tasks.
- `/api/branches/{branch_id}/sector-exposures`: sector concentration data.
- `/api/branches/{branch_id}/applications`: pending applications and credit decisions.
- `/api/credit-union-segments/{segment_id}`: segment posture data.

## Policy Rules

### Capacity and concentration

- Allowed mitigations: `participation_required`, `reduced_amount`, `board_exception`.
- Lending capacity field: `branches.lending_capacity_q1`.
- Single-sector ceiling field: `branches.sector_ceiling_pct`.
- Existing over-ceiling exposure may be grandfathered; do not worsen that sector without mitigation.

### CDFI factor scores

- Classes:
  - `Prime`: 0-5
  - `Desirable`: 6-9
  - `Satisfactory`: 10-13
  - `Watch`: 14-18
  - `Doubtful`: >=19
  - `Projected Loss`: >=19 and ltv > 1.0
- Factor scores:
  - `debt_to_asset`: `<0.40=0`, `0.40-0.60=2`, `0.60-0.80=4`, `>0.80=6`
  - `fico`: `>720=0`, `680-720=1`, `580-679=3`, `<580=5`
  - `liquidity_months`: `>12=0`, `6-12=1`, `3-6=3`, `<3=5`
  - `ltv`: `<0.40=0`, `0.40-0.60=2`, `0.60-0.80=4`, `>0.80=6`

### CRE weighted score

- Weights: `capacity=0.45`, `capital=0.03`, `character=0.05`, `collateral_exposure=0.36`, `conditions=0.11`.
- Class cutoffs: `approve_quality<=2.0`, `conditional<=3.0`, `weak>3.0`.

### Risk rating

- Delinquency minimums: `Current=null`, `30 Days Past Due=4`, `60 Days Past Due=5`, `90+ Days Past Due=7`, `Nonaccrual=8`.
- DSCR thresholds: `>=1.5 -> 3`, `>=1.25 -> 4`, `>=1.05 -> 5`, `>=1.0 -> 6`, `<1.0 -> 7`.
- LTV thresholds: `<=0.65 -> 3`, `<=0.75 -> 4`, `<=0.85 -> 5`, `<=1.0 -> 6`, `>1.0 -> 7`.
- Dominant factor rule: final re-derived rating is the worst numeric rating from the applicable DSCR, LTV, collateral, and delinquency factors.
- Material downgrade threshold: 2 notches.

### Stress

- CRE dual stress formula: `stressed_dscr = dscr * 0.85 / (1 + 0.18)`.
- Watch-list formula: `stressed_dscr = dscr / (1 + 0.18)`.
- Coverage breach threshold: `1.0`.

## Packet Patterns

### Branch regrade

- Filter loans by the prompt's current-rating floor.
- Re-derive final ratings with the risk-rating rules above.
- Aggregate final-rating totals, migration from current rating 3, material downgrades, watch-list coverage, and the top problem credit.
- Use the requested FDIC benchmark metric and compute variance against the branch ratio.

### Lending allocation

- Use branch capacity and sector exposure to size approvals, conditional approvals, and declines.
- Keep priority ranking to approved and conditionally approved applications only.
- Build concentration flags from post-approval percentages versus the branch sector ceiling.
- Return decline reasons only from the controlled enum.

### Segment posture

- Compare the target state to the U.S. and the prompt's peer states using the NCUA table.
- Keep `peer_states` sorted by state code.
- Use the allowed controls, triggers, owners, and interpretation enums only.

### Watch-list stress

- Treat current rating 6 or worse as adverse unless the prompt says otherwise.
- Score each loan with the CDFI factor rules.
- Apply the watch-list or CRE shock to DSCR where available.
- Sort workout queues by the prompt's exposure rule and summarize severe buckets by rating and payment status.

### Competing CRE

- Use the weighted CRE score to compare the two applications.
- Pair the score with stressed DSCR, concentration, and FDIC variance.
- Choose the stronger path for the selected application and carry the unselected reason codes through unchanged.

## Output Checks

- Verify the JSON parses.
- Verify every key is from the template.
- Verify every enum value is allowed.
- Verify sort order, rounding, and numeric precision.
- Return no commentary outside the JSON object.
