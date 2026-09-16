# Policy Thresholds Reference

The `/api/policies` endpoint returns a single JSON object. Here is the full
structure with field meanings.

---

## Policy Selection

Every portfolio's `/api/portfolios` record includes a `constraint_policy_id`:

| constraint_policy_id | Policy sub-object | Purpose |
|---|---|---|
| `POL_CREDIT_DEFAULT` | `credit_default` | Standard credit portfolio constraints |
| `POL_CREDIT_RISK_REDUCTION` | `credit_risk_reduction` | Credit portfolio with HY reduction target |
| `POL_CORRELATION_DEFAULT` | `correlation` | International equity correlation thresholds |
| `POL_MULTI_ASSET_DEFAULT` | `multi_asset` | Multi-asset composite (references credit_default + correlation + allocation_mapping) |
| `POL_MULTI_ASSET_RISK` | `multi_asset_risk` | Multi-asset with risk escalation (references credit_risk_reduction + correlation) |

Multi-asset policies reference the sub-policies they use via boolean flags:
- `uses_allocation_mapping` — true means use `allocation_mapping`
- `uses_correlation_default` — true means use `correlation`
- `uses_credit_default` — true means use `credit_default`
- `uses_credit_risk_reduction` — true means use `credit_risk_reduction`

When a portfolio uses a multi-asset policy, first read the multi_asset or
multi_asset_risk sub-object to determine which sub-policies apply, then read
those sub-policies for actual thresholds.

---

## Credit Policy Fields (credit_default / credit_risk_reduction)

| Field | Type | Meaning |
|---|---|---|
| `policy_id` | string | `"POL_CREDIT_DEFAULT"` or `"POL_CREDIT_RISK_REDUCTION"` |
| `max_hy_allocation_pct` | number | Maximum HY % of portfolio market value (e.g. 20.0) |
| `duration_band_years` | [number, number] | Allowed weighted duration range (e.g. [3.0, 5.0]) |
| `issuer_concentration_limit_pct` | number | Max single-issuer share of market value (e.g. 12.0) |
| `subsector_min_count_for_diversified` | integer | Minimum distinct subsectors required (e.g. 2) |
| `target_hy_reduction_pct` | number | Target HY reduction in percentage points (0.0 for credit_default, 4.0 for credit_risk_reduction) |

---

## Correlation Policy Fields

| Field | Type | Meaning |
|---|---|---|
| `policy_id` | string | `"POL_CORRELATION_DEFAULT"` |
| `correlation_high_threshold` | number | Above this is considered high concentration (e.g. 0.8) |
| `correlation_low_threshold` | number | Below this is considered a diversifier (e.g. 0.2) |
| `review_window_start` | string | Default start date for the correlation window |
| `review_window_end` | string | Default end date for the correlation window |

---

## Allocation Mapping Fields

| Field | Type | Meaning |
|---|---|---|
| `policy_id` | string | `"POL_ALLOCATION_MAPPING"` |
| `view_score_thresholds.OW_min` | number | Score ≥ this → OW (e.g. 0.35) |
| `view_score_thresholds.UW_max` | number | Score ≤ this → UW (e.g. -0.35) |
| `view_score_thresholds.neutral_between` | [number, number] | Range for N (e.g. [-0.35, 0.35]) |
| `view_rank.OW` | number | 1 |
| `view_rank.N` | number | 0 |
| `view_rank.UW` | number | -1 |
| `conviction_thresholds.HIGH_abs_min` | number | \|score\| ≥ this → HIGH (e.g. 0.7) |
| `conviction_thresholds.MEDIUM_abs_min` | number | \|score\| ≥ this AND < HIGH_abs_min → MEDIUM (e.g. 0.35) |
| `conviction_thresholds.LOW_abs_below` | number | \|score\| < this → LOW (e.g. 0.35) |

---

## Top-Level Fields

| Field | Type | Meaning |
|---|---|---|
| `policy_id` | string | Current policy set version, e.g. `"POLICY_SET_2026_05"` |
| `as_of_date` | string | Date of the policy set |

This `policy_id` is the one to use for the `policy_id` field in allocation
view tasks.
