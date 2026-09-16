# Credit Office Policy Reference

All policy rules are served live by `GET /api/policies`. This reference documents the stable computation and classification rules derived from that endpoint.

## Risk Rating Derivation

The final risk rating for a loan is derived from the **dominant factor rule**: take the worst (highest numeric) rating from available DSCR, LTV/collateral, and delinquency minimum factors. Ratings are 1 (best) to 8 (worst).

### DSCR Thresholds

| DSCR         | Rating |
|--------------|--------|
| >= 1.50      | 3      |
| >= 1.25      | 4      |
| >= 1.05      | 5      |
| >= 1.00      | 6      |
| < 1.00       | 7      |

Absent DSCR data, the DSCR factor is omitted.

### LTV Thresholds

| LTV           | Rating |
|---------------|--------|
| <= 0.65       | 3      |
| <= 0.75       | 4      |
| <= 0.85       | 5      |
| <= 1.00       | 6      |
| > 1.00        | 7      |

Absent LTV or collateral_value, the LTV factor is omitted. If either `ltv` or `collateral_value` is null, skip the LTV factor for that loan.

### Delinquency Minimums

| Payment Status        | Minimum Rating |
|-----------------------|----------------|
| Current               | (no floor)     |
| 30 Days Past Due      | 4              |
| 60 Days Past Due      | 5              |
| 90+ Days Past Due     | 7              |
| Nonaccrual            | 8              |

### Derivation Procedure

1. Collect the numeric ratings from each available factor (DSCR, LTV, delinquency).
2. The final rating is the maximum of those values.
3. If no factors are available, preserve the `current_rating`.
4. If the delinquency minimum is higher than any derived rating, it dominates.

### Material Downgrades

A loan is a **material downgrade** when `final_rating - current_rating >= 2`.

## CDFI Factor Scores

Sum scores across four factors (omit any where the input field is null), then map the total to a risk class.

### Factor Tables

**FICO Score**
| FICO      | Score |
|-----------|-------|
| > 720     | 0     |
| 680-720   | 1     |
| 580-679   | 3     |
| < 580     | 5     |

**LTV**
| LTV       | Score |
|-----------|-------|
| < 0.40    | 0     |
| 0.40-0.60 | 2     |
| 0.60-0.80 | 4     |
| > 0.80    | 6     |

**Liquidity Months**
| Liquidity | Score |
|-----------|-------|
| > 12      | 0     |
| 6-12      | 1     |
| 3-6       | 3     |
| < 3       | 5     |

**Debt to Asset**
| D/A       | Score |
|-----------|-------|
| < 0.40    | 0     |
| 0.40-0.60 | 2     |
| 0.60-0.80 | 4     |
| > 0.80    | 6     |

### Risk Class Mapping

| Total Score | Class           |
|-------------|-----------------|
| 0-5         | Prime           |
| 6-9         | Desirable       |
| 10-13       | Satisfactory    |
| 14-18       | Watch           |
| >= 19       | Doubtful        |
| >= 19 AND LTV > 1.00 | Projected Loss |

## CRE Weighted Scoring (Five Cs)

Weights:
| Component           | Weight |
|---------------------|--------|
| Capacity            | 0.45   |
| Capital             | 0.03   |
| Character           | 0.05   |
| Collateral/Exposure | 0.36   |
| Conditions          | 0.11   |

Map application fields to CDFI factor scoring:

- **Capacity score**: use the application's DSCR mapped to an LTV-like scale: DSCR >= 1.50 -> score 0; DSCR 1.25-1.50 -> score 2; DSCR 1.05-1.25 -> score 4; DSCR < 1.05 -> score 6.
- **Collateral/Exposure score**: use the application's LTV to score via the CDFI LTV table.
- **Capital score**: use `debt_to_asset` from the application mapped to the CDFI D/A table. If `total_debt` and `total_assets` are available but `debt_to_asset` is null, compute `debt_to_asset = total_debt / total_assets`.
- **Character score**: use `fico` mapped to the CDFI FICO table.
- **Conditions score**: use `liquidity_months` mapped to the CDFI liquidity table. Note: applications may not have `liquidity_months`; if null, substitute score 0.

If any factor's input is null and cannot be computed, substitute score 0 for that component.

Weighted score = sum(weight_i * score_i). Lower is better.

### Score Class
| Weighted Score | Class            |
|----------------|------------------|
| <= 2.0         | approve_quality  |
| <= 3.0         | conditional      |
| > 3.0          | weak             |

## Stress Formulas

### Watch-List Stress (+200bp)

```
stressed_dscr = dscr / (1 + 0.18)
```
Breach threshold: stressed_dscr < 1.00.

### CRE Dual Stress

```
stressed_dscr = dscr * 0.85 / (1 + 0.18)
```
Breach threshold: stressed_dscr < 1.00.

## Capacity and Concentration

- **Bank capacity**: `branches.lending_capacity_q1` is the Q1 lending budget across all applications.
- **Committed capacity**: for `participation_required` approvals, committed = `approved_amount * (1 - sba_guaranty_pct)`. Otherwise committed = `approved_amount`.
- **Remaining capacity**: `lending_capacity_q1 - sum(committed_capacity_amount)`.
- **Sector ceiling**: `branches.sector_ceiling_pct` is the default single-sector limit. Individual sectors may have lower `limit_pct` per `sector_exposures`.
- **CRE limit**: `branches.cre_policy_limit_pct` for CRE-specific concentration.
- **Grandfathering**: existing over-ceiling exposure may be grandfathered (`grandfathered` field in sector_exposures), but new approvals may not worsen an over-limit sector without mitigation.
- **Allowed mitigations**: `participation_required`, `reduced_amount`, `board_exception`.
- **Post-approval concentration**: `(existing_sector_exposure + approved_amount) / total_loans_outstanding` from the most recent branch metrics quarter. Compare to `limit_pct`.

## Benchmark Data

### FDIC Q4 2024

`GET /api/benchmarks/fdic/q4-2024` returns a single object with national aggregate ratios:
- `total_loans_noncurrent_pct`
- `total_real_estate_noncurrent_pct`
- `construction_development_noncurrent_pct`
- `total_real_estate_30_89_pct`
- `construction_development_30_89_pct`

### NCUA Q1 2025

`GET /api/benchmarks/ncua/q1-2025` returns a `rows` array with per-state metrics plus a US row (`state_code: "US"`):
- `delinquency_bps`, `loan_to_share_pct`, `roaa_bps`, `positive_net_income_pct`

**Peer median**: compute the median of peer state values (exclude NC and US rows from the median set).

### Benchmark Variance

For FDIC: `variance_ratio = branch_ratio - benchmark_ratio`, `variance_bps = variance_ratio * 10000`.

For NCUA direction: compare NC value to US or peer median; report `"higher"`, `"lower"`, or `"equal"`.

## Task-Specific Procedures

### Portfolio Regrade (Rating Migration Review)

1. Fetch branch loans; filter to `current_rating >= target_current_rating_min`.
2. Re-derive final rating for each target loan using the dominant factor rule.
3. Group by final_rating for `final_rating_exposure_totals`.
4. Track migration: for loans with `current_rating == 3`, report their final_rating destinations.
5. Watch-list actions: assign `recommended_action` per final_rating band:
   - Rating 6 -> `"watchlist"`
   - Rating 7 -> `"special_assets"`
   - Rating 8 -> `"partial_chargeoff_review"`
   - Ratings 1-5 -> no watch-list coverage
6. Loans with `current_rating < target_current_rating_min` are excluded from the regrade population (their existing rating is not re-derived).

### NPA Benchmark

- `branch_npa_exposure` = sum of `outstanding_balance` for loans with `payment_status == "Nonaccrual"` (or `final_rating == 8` after regrade).
- `branch_total_loans` = `total_loans_outstanding` from the most recent branch metrics quarter.
- `branch_npa_ratio` = `branch_npa_exposure / branch_total_loans`.

### Application Decisions (Lending Allocation)

1. Score each application with policy flags. Decline applications meeting any automatic decline criteria:
   - DSCR < 1.00 -> `weak_dscr`
   - LTV > 1.00 -> `high_ltv` (also `underwater_collateral` if LTV > 1.00)
   - FICO < 580 -> `low_fico`
   - `bankruptcy_months_ago` not null and <= 24 -> `recent_bankruptcy`
   - `years_in_business` < 2 and no SBA guaranty (`sba_guaranty_pct` null or 0) -> `startup_risk`
   - `documentation_complete == 0` -> `documentation_gap`
2. Rank surviving applications by priority (relationship strength, DSCR, risk factors).
3. Allocate capacity in priority order. Check sector concentration before each approval.
4. For concentration breaches, apply mitigation (`participation_required`, `reduced_amount`) or decline with `sector_breach`.
5. Applications that cannot fit in remaining capacity get `capacity_limit` decline.

### Credit Union Segment Posture

1. Fetch segment: `GET /api/credit-union-segments/{segment_id}`.
2. Fetch NCUA benchmarks; extract NC row, US row, and peer state rows.
3. Compute peer median for each of the four metrics.
4. Compare NC vs US and NC vs peer median (direction only).
5. Posture based on capacity and external risk signals.

### Watch-List Stress (Adverse-Rated Loans)

1. Fetch branch loans; filter to `current_rating >= 6`.
2. Assign CDFI risk class to each adverse loan.
3. For loans with DSCR available, compute +200bp stressed_dscr.
4. Build workout queue: sort by descending `outstanding_balance`, then ascending `loan_id`.
5. Count severe buckets: group by `current_rating` and `payment_status`.

### Competing CRE Decision

1. Score both CRE applications using the weighted 5-Cs formula.
2. Run dual-stress on both.
3. Compute concentration: existing CRE exposure + selected application vs `cre_policy_limit_pct`.
4. Compare branch delinquency to FDIC benchmark (`total_real_estate_30_89_pct`).
5. Recommend the stronger credit; flag the unselected credit with reason codes.
