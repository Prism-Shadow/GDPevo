# Asteria Policy Definitions

## Policy lookup by portfolio

Each portfolio's `constraint_policy_id` from `/api/portfolios` maps to a section in the `/api/policies` response:

| constraint_policy_id | Policy section | Key thresholds |
|---|---|---|
| `POL_CREDIT_DEFAULT` | `credit_default` | HY cap 20%, duration 3.0–5.0 yr, issuer conc. 12%, subsector min 2, target HY reduction 0% |
| `POL_CREDIT_RISK_REDUCTION` | `credit_risk_reduction` | Same as credit_default, but target HY reduction ≥ 4.0 pp |
| `POL_CORRELATION_DEFAULT` | `correlation` | High threshold 0.8, low threshold 0.2 |
| `POL_MULTI_ASSET_DEFAULT` | `multi_asset` | Uses credit_default + correlation + allocation_mapping |
| `POL_MULTI_ASSET_RISK` | `multi_asset_risk` | Uses credit_risk_reduction + correlation |

## Credit constraints (POL_CREDIT_DEFAULT and POL_CREDIT_RISK_REDUCTION)

- **HY cap**: Post-trade HY allocation must not exceed `max_hy_allocation_pct` (20%).
- **Duration band**: Post-trade weighted modified duration must fall within `duration_band_years` [min, max].
- **Issuer concentration**: No single issuer > `issuer_concentration_limit_pct` of post-trade market value.
- **Subsector diversification**: At least `subsector_min_count_for_diversified` distinct subsectors among the selected trade instruments.
- **Target HY reduction** (POL_CREDIT_RISK_REDUCTION only): HY allocation must drop by at least `target_hy_reduction_pct` percentage points.

## Correlation thresholds (POL_CORRELATION_DEFAULT)

- **High threshold**: Pairs with correlation ≥ `correlation_high_threshold` (0.8) flag concentration risk.
- **Low threshold**: Pairs with correlation ≤ `correlation_low_threshold` (0.2) are diversification candidates.
- **Window**: Review period from `review_window_start` to `review_window_end`.

## Allocation mapping

From `/api/policies` → `allocation_mapping`:

### View from signal score

- Score ≥ `OW_min` (0.35) → `OW`
- Score ≤ `UW_max` (-0.35) → `UW`
- Between → `N`

### Conviction from signal score absolute value

- `|score|` ≥ `HIGH_abs_min` (0.70) → `HIGH`
- `|score|` ≥ `MEDIUM_abs_min` (0.35) → `MEDIUM`
- Else → `LOW`

### Change from prior view

View rank: OW=1, N=0, UW=-1.
- Current rank > prior rank → `UP`
- Current rank < prior rank → `DOWN`
- Equal → `UNCHANGED`
