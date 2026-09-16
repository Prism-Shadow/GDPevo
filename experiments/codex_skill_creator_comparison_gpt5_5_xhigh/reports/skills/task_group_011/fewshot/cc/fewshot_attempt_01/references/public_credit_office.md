# Public Credit Office Reference

This reference captures the shared API and policy rules used by the staged committee-packet tasks.

## API Map
- `/api/manifest` - confirm benchmark versions, policy version, endpoint list, and record counts.
- `/api/policies` - shared scoring, threshold, mitigation, and stress rules.
- `/api/branches` - list branch metadata.
- `/api/branches/{branch_id}` - branch profile with policy limit, lending capacity, sector ceiling, state, and assets.
- `/api/branches/{branch_id}/metrics` - branch financial and delinquency metrics by quarter.
- `/api/branches/{branch_id}/loans` - loan-level review data.
- `/api/branches/{branch_id}/sector-exposures` - current sector concentrations and grandfathering.
- `/api/branches/{branch_id}/applications` - pending applications.
- `/api/credit-union-segments/{segment_id}` - segment posture inputs.
- `/api/benchmarks/fdic/q4-2024` - FDIC benchmark table.
- `/api/benchmarks/ncua/q1-2025` - NCUA benchmark table.

## Shared Policy Rules

### Capacity and concentration
- Allowed mitigation values for capacity concentration problems: `participation_required`, `reduced_amount`, `board_exception`.
- Lending capacity comes from `branches.lending_capacity_q1`.
- Single-sector default ceiling comes from `branches.sector_ceiling_pct`.
- Existing over-ceiling exposure may be grandfathered, but new approvals may not worsen that sector without mitigation.

### CDFI factor scoring
- Factor scoring is driven by the policy table for debt-to-asset, FICO, liquidity months, and LTV.
- Risk class bands:
  - Prime: 0-5
  - Desirable: 6-9
  - Satisfactory: 10-13
  - Watch: 14-18
  - Doubtful: 19+
  - Projected Loss: 19+ and `ltv > 1.0`

### CRE weighted score
- Weights: capacity 0.45, capital 0.03, character 0.05, collateral_exposure 0.36, conditions 0.11.
- Classes:
  - approve_quality: score <= 2.0
  - conditional: score <= 3.0
  - weak: score > 3.0

### Risk rating thresholds
- Delinquency minimums: Current -> null, 30 Days Past Due -> 4, 60 Days Past Due -> 5, 90+ Days Past Due -> 7, Nonaccrual -> 8.
- Dominant factor rule: the final re-derived rating is the worst numeric rating from available DSCR, LTV or collateral, and delinquency factors.
- DSCR thresholds: >= 1.5 -> 3, >= 1.25 -> 4, >= 1.05 -> 5, >= 1.0 -> 6, < 1.0 -> 7.
- LTV thresholds: <= 0.65 -> 3, <= 0.75 -> 4, <= 0.85 -> 5, <= 1.0 -> 6, > 1.0 -> 7.
- Material downgrade notch threshold: 2.

### Stress formulas
- Watch-list +200bp stress: `stressed_dscr = dscr / (1 + 0.18)`.
- CRE dual stress: `stressed_dscr = dscr * 0.85 / (1 + 0.18)`.
- Coverage breach threshold: 1.0.

## Output Discipline
- Mirror the template's top-level keys exactly.
- Sort lists exactly as requested by the template.
- Use enum values verbatim.
- Keep currency fields to 2 decimals and ratio fields to 4 decimals when those precisions are requested.
- Return raw JSON only.
