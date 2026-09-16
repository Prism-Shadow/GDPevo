## Credit Policy Rules & Scoring Systems

Version: `credit_policy_v2025Q1`. All rules below come from `GET /api/policies`.

### Risk Rating Derivation

**Dominant-factor rule:** The final re-derived rating is the worst (highest numeric) rating from the available factors: DSCR, LTV (or collateral), and delinquency. For each factor, match the value against its threshold table; if a factor is unavailable (null), skip it.

#### Delinquency Minimums

| Payment Status | Minimum Rating |
|---|---|
| `Current` | no floor |
| `30 Days Past Due` | 4 |
| `60 Days Past Due` | 5 |
| `90+ Days Past Due` | 7 |
| `Nonaccrual` | 8 |

#### DSCR Thresholds

| Condition | Rating |
|---|---|
| DSCR >= 1.50 | 3 |
| DSCR >= 1.25 | 4 |
| DSCR >= 1.05 | 5 |
| DSCR >= 1.00 | 6 |
| DSCR < 1.00 | 7 |

#### LTV Thresholds

| Condition | Rating |
|---|---|
| LTV <= 0.65 | 3 |
| LTV <= 0.75 | 4 |
| LTV <= 0.85 | 5 |
| LTV <= 1.00 | 6 |
| LTV > 1.00  | 7 |

**Collateral fallback:** When `collateral_value` is non-null and `ltv` is null, compute LTV as `outstanding_balance / collateral_value` then apply LTV thresholds. When both are null, skip the LTV/collateral factor.

#### Material Downgrade Threshold

A downgrade is material when `final_rating - current_rating >= 2` notches (from policy: `material_downgrade_notches: 2`).

### CDFI Factor Scores (for risk-class assignment)

Sum scores across all four available factor dimensions (skip nulls). Map total to a risk class:

| Class | Score Range |
|---|---|
| Prime | 0-5 |
| Desirable | 6-9 |
| Satisfactory | 10-13 |
| Watch | 14-18 |
| Doubtful | >= 19 |
| Projected Loss | >= 19 **and** LTV > 1.0 |

#### FICO Score

| Range | Score |
|---|---|
| > 720 | 0 |
| 680-720 | 1 |
| 580-679 | 3 |
| < 580 | 5 |

#### LTV Score

| Range | Score |
|---|---|
| < 0.40 | 0 |
| 0.40-0.60 | 2 |
| 0.60-0.80 | 4 |
| > 0.80 | 6 |

#### Debt-to-Asset Score

| Range | Score |
|---|---|
| < 0.40 | 0 |
| 0.40-0.60 | 2 |
| 0.60-0.80 | 4 |
| > 0.80 | 6 |

#### Liquidity Months Score

| Range | Score |
|---|---|
| > 12 | 0 |
| 6-12 | 1 |
| 3-6 | 3 |
| < 3 | 5 |

### CRE Weighted Score

For CRE applications, compute: `score = sum(weight_i * factor_score_i)` where `factor_score_i` is the raw CDFI score (not the sum) for the factor mapped to a 0-5 scale normalized against max per dimension (6), with capacity using `requested_amount / lending_capacity_q1` as a 0-5 ratio.

Weights:

| Factor | Weight |
|---|---|
| capacity | 0.45 |
| collateral_exposure | 0.36 |
| conditions | 0.11 |
| capital | 0.03 |
| character | 0.05 |

Score classes (lower is better):

| Class | Threshold |
|---|---|
| approve_quality | <= 2.0 |
| conditional | 2.0 < score <= 3.0 |
| weak | > 3.0 |

**Factor mapping for weighted CRE score:** Use application fields. For each factor, derive a 0-5 score:

- **capacity**: `capacity_score = min(5, round((requested_amount / lending_capacity_q1) * 5))` — capped at 5 for amounts exceeding capacity.
- **collateral_exposure**: Use the LTV CDFI score (0-6) divided by 6 and multiplied by 5: `collateral_exposure_score = (cdfi_ltv_score / 6) * 5`.
- **conditions**: `conditions_score = 0` if `documentation_complete == 1` else `3`. Add `1` if `years_in_business < 3`, add `1` if `prior_delinquencies_12m > 0`.
- **capital**: `capital_score = 0` if `net_income > 0` else `3`; add `2` if `debt_to_asset > 0.60`.
- **character**: `character_score = 0` if `fico >= 680` else `2` if `fico < 680`; add `3` if `bankruptcy_months_ago` not null.

### Stress Formulas

| Context | Formula | Label |
|---|---|---|
| Watch-list (adverse loans) | `stressed_dscr = base_dscr / (1 + 0.18)` | `+200bp` |
| CRE competing (dual stress) | `stressed_dscr = base_dscr * 0.85 / (1 + 0.18)` | `dscr * 0.85 / 1.18` |

Breach threshold for both: `stressed_dscr < 1.0`.

Only apply stress to loans/applications where `dscr` is non-null.

### Capacity & Concentration

- **Lending capacity:** From `branch.lending_capacity_q1`. Compare against gross approved amounts.
- **Sector ceiling:** From `branch.sector_ceiling_pct` or per-sector `limit_pct` from sector-exposure endpoint. Use per-sector `limit_pct` from `/branches/{id}/sector-exposures` as the authoritative limit per sector.
- **CRE limit:** From `branch.cre_policy_limit_pct`. Sum all CRE-type loans for concentration checks.
- **Allowed mitigations:** `participation_required`, `reduced_amount`, `board_exception`.
- **Grandfathering:** Existing over-ceiling exposure is grandfathered but new approvals must not worsen the sector.
- **Concentration post-approval pct:** `(current_exposure_in_sector + approved_amount_in_sector) / (total_loans_outstanding + gross_approved_amount)` — compute per sector.

### Watch-List Action Mapping

Derive recommended actions from the final rating and DSCR stress breach:

| Final Rating | DSCR Stress Breach | Recommended Action |
|---|---|---|
| 6 | — | `watchlist` |
| 7 | — | `special_assets` |
| 8 | — | `partial_chargeoff_review` |
| Any | Stress breach + 90+ DPD | `special_assets` |
| Any | Nonaccrual | `partial_chargeoff_review` |
| Any (rating 6+) | No stress breach, Current | `watchlist` |

For loans without DSCR (null), default to rating-based action: 6 -> `watchlist`, 7 -> `special_assets`, 8 -> `partial_chargeoff_review`.

### Decline Reason Codes

| Code | Meaning |
|---|---|
| `capacity_limit` | Exceeds remaining lending capacity |
| `sector_breach` | Sector concentration limit exceeded |
| `weak_dscr` | DSCR below policy floor |
| `high_ltv` | LTV too high |
| `low_fico` | FICO below acceptable threshold |
| `recent_bankruptcy` | Bankruptcy within lookback window |
| `startup_risk` | Limited operating history |
| `underwater_collateral` | Collateral value below outstanding balance |
| `policy_floor_missing` | Required policy floor not met |
| `documentation_gap` | Application documentation incomplete |
| `fdic_adverse_variance` | FDIC benchmark adverse variance |
| `ncua_peer_weakness` | NCUA peer-state weakness |

### Application Decision Logic

Rank eligible applications by a composite score (higher is better priority):
1. Exclude auto-decline applications (see conditions below).
2. Sort remaining by: `dscr * (1 / requested_amount) * (fico_frac)` where fico_frac = `fico / 850` if non-null else 0.5. Give a slight weight to `years_in_business` and `existing_relationship_years`.
3. Approve in priority order until capacity is exhausted or sector limits bind.
4. Flag concentration breaches using per-sector limits from the sector-exposure endpoint.
5. Map each declined application to the appropriate reason codes.

**Auto-decline conditions:**
- `ltv > 0.85` → decline, reason `high_ltv`
- `dscr < 1.05` → decline, reason `weak_dscr` (combined with others if present)
- `fico < 580` → decline, reason `low_fico`
- `years_in_business < 2` and not SBA → decline, reason `startup_risk`
- `bankruptcy_months_ago` non-null → decline, reason `recent_bankruptcy`
- `documentation_complete == 0` → decline, reason `documentation_gap`

**Conditional approval:**
- SBA applications with `years_in_business < 2`: condition `startup_monitoring`
- Sector near limit (< 0.5% headroom below): condition `participation_required` or `reduced_amount`
- SBA loan type: condition `sba_guaranty_required`

### NPA Benchmark Comparison

1. Fetch FDIC benchmark: `total_loans_noncurrent_pct` from `/api/benchmarks/fdic/q4-2024`.
2. Compute branch NPA ratio: `nonperforming_loans / total_loans_outstanding` from `/branches/{id}/metrics` (first quarter entry).
3. Variance: `branch_npa_ratio - fdic_benchmark_ratio` (ratio) and `variance_ratio * 10000` (bps).
4. For CRE delinquency comparison: use `total_real_estate_30_89_pct` from FDIC vs branch `delinquency_30_plus_pct` from metrics.

### Credit Union Segment Posture

1. Fetch segment data from `/api/credit-union-segments/{segment_id}`.
2. Fetch NCUA benchmark from `/api/benchmarks/ncua/q1-2025`.
3. For each peer state in `segment.peer_states`, compute median across the four metrics.
4. Compare the target state (from `segment.state_code`) vs US row and vs peer median on each metric.
5. Determine posture:
   - `continue_approving`: state stronger than or equal to both US and peers on most metrics.
   - `continue_with_tighter_conditions`: mixed picture — capacity available but external risk weaker on several dimensions.
   - `temporarily_pause`: state materially weaker than both US and peers across most metrics, or recent delinquency >= 90 bps.
6. Escalation triggers: derive from segment internal context and benchmark gap.
7. Operating controls: add controls informed by segment's `control_issue` and `staffing_constraint`.
8. Interpretation fields: derive from posture, capacity, and risk tolerance.

### Competing CRE Decision

1. Fetch both applications and branch data.
2. Compute weighted CDFI scores for both.
3. Apply dual stress (`dscr * 0.85 / 1.18`) to both.
4. Compute CRE concentration: existing CRE exposure across all loans with `loan_type == \"CRE\"` divided by `total_loans_outstanding`, then add selected application to compute post-approval concentration.
5. Compare vs `cre_policy_limit_pct` and FDIC real estate delinquency benchmark.
6. Select the stronger application (lower weighted score, better stress result).
7. For the unselected: map to `decline` or `defer` with reason codes.
8. Conditions for the selected application mirror concentration and stress concerns.
