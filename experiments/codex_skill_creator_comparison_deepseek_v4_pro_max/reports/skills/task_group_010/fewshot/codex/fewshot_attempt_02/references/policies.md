# Policy Reference

The `/api/policies` endpoint returns a composite policy document keyed by component policy IDs. This reference documents the fixed threshold values and mapping rules. However, always fetch `/api/policies` at run time since policy values may be environment-specific.

## Allocation mapping (POL_ALLOCATION_MAPPING)

| Parameter | Value |
|-----------|-------|
| OW threshold (view_score_thresholds.OW_min) | 0.35 |
| UW threshold (view_score_thresholds.UW_max) | -0.35 |
| Neutral band (view_score_thresholds.neutral_between) | [-0.35, 0.35] |
| HIGH conviction (conviction_thresholds.HIGH_abs_min) | 0.7 |
| MEDIUM conviction (conviction_thresholds.MEDIUM_abs_min) | 0.35 |
| LOW conviction (conviction_thresholds.LOW_abs_below) | 0.35 |

## View rank (for change determination)

| View | Rank |
|------|------|
| UW | -1 |
| N | 0 |
| OW | 1 |

## Correlation defaults (POL_CORRELATION_DEFAULT)

| Parameter | Value |
|-----------|-------|
| correlation_high_threshold | 0.8 |
| correlation_low_threshold | 0.2 |
| review_window_start | 2025-05-30 |
| review_window_end | 2026-04-30 |

## Credit default (POL_CREDIT_DEFAULT)

| Parameter | Value |
|-----------|-------|
| max_hy_allocation_pct | 20.0 |
| duration_band_years | [3.0, 5.0] |
| issuer_concentration_limit_pct | 12.0 |
| subsector_min_count_for_diversified | 2 |
| target_hy_reduction_pct | 0.0 |

## Credit risk reduction (POL_CREDIT_RISK_REDUCTION)

| Parameter | Value |
|-----------|-------|
| max_hy_allocation_pct | 20.0 |
| duration_band_years | [3.0, 5.0] |
| issuer_concentration_limit_pct | 12.0 |
| subsector_min_count_for_diversified | 2 |
| target_hy_reduction_pct | 4.0 |

## Multi-asset default (POL_MULTI_ASSET_DEFAULT)

Inherits: `uses_allocation_mapping`, `uses_correlation_default`, `uses_credit_default`.

## Multi-asset risk (POL_MULTI_ASSET_RISK)

Inherits: `uses_correlation_default`, `uses_credit_risk_reduction`. Escalation threshold: `two_or_more_material_exceptions`.

## Overlay selection guidance

1. Count which rationale codes are driving views across requested opportunity sets.
2. When DURATION_SUPPORT and HY_VALUATION_RISK are both prominent: choose `DURATION_QUALITY_TILT` with action `tilt_to_duration_quality`.
3. When CREDIT_SPREAD_RISK dominates: choose `CREDIT_RISK_REDUCTION`.
4. When GROWTH_IMPROVES / EUROPE_RECOVERY dominate: choose `EQUITY_BETA_EXTENSION`.
5. When DOLLAR_DEFENSIVE dominates: choose `CURRENCY_DEFENSIVE_HEDGE`.
6. Otherwise: `NO_OVERLAY`.

## Conviction mapping from absolute signal score

| Condition | Conviction |
|-----------|------------|
| abs(score) >= 0.7 | HIGH |
| abs(score) >= 0.35 | MEDIUM |
| abs(score) < 0.35 | LOW |
