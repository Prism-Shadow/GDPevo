# Asteria Portfolio Policy Reference

All policy thresholds come from GET /api/policies. The response is the
composite policy object with policy_id "POLICY_SET_2026_05".

## Policy Selection by Portfolio

Each portfolio constraint_policy_id determines which sub-policy applies:

| Portfolio prefix | Typical policy |
|-----------------|----------------|
| PF-EN-* | POL_CREDIT_DEFAULT |
| PF-FI-* (risk) | POL_CREDIT_RISK_REDUCTION |
| PF-FI-* (defensive) | POL_CREDIT_DEFAULT |
| PF-INT-* | POL_CORRELATION_DEFAULT |
| PF-MA-* (default) | POL_MULTI_ASSET_DEFAULT |
| PF-MA-* (risk) | POL_MULTI_ASSET_RISK |

Always verify by reading the portfolio summary and checking constraint_policy_id.

## Credit Policies

### POL_CREDIT_DEFAULT

- max_hy_allocation_pct: 20.0
- duration_band_years: [3.0, 5.0]
- issuer_concentration_limit_pct: 12.0
- subsector_min_count_for_diversified: 2
- target_hy_reduction_pct: 0.0

### POL_CREDIT_RISK_REDUCTION

- max_hy_allocation_pct: 20.0
- duration_band_years: [3.0, 5.0]
- issuer_concentration_limit_pct: 12.0
- subsector_min_count_for_diversified: 2
- target_hy_reduction_pct: 4.0  (must reduce HY by at least 4 pct points)

## Correlation Policy

### POL_CORRELATION_DEFAULT

- correlation_high_threshold: 0.8
- correlation_low_threshold: 0.2
- review_window_start: "2025-05-30"
- review_window_end: "2026-04-30"

## Allocation Policy

### POL_ALLOCATION_MAPPING

View-to-score mapping:
- OW: score >= 0.35
- N: -0.35 < score < 0.35
- UW: score <= -0.35

Conviction thresholds:
- HIGH: abs(score) >= 0.7
- MEDIUM: abs(score) >= 0.35
- LOW: abs(score) < 0.35

Change determination:
- Compare target quarter view vs prior quarter view
- view_rank: UW=-1, N=0, OW=1
- view > prior => UP, view < prior => DOWN, equal => UNCHANGED

## Multi-Asset Policies

### POL_MULTI_ASSET_DEFAULT

Uses allocation_mapping + correlation_default + credit_default.

### POL_MULTI_ASSET_RISK

Uses correlation_default + credit_risk_reduction.
committee_escalation_threshold: "two_or_more_material_exceptions"
