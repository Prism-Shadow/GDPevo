# Computation Reference

## Pearson correlation of monthly simple returns

Used by international equity correlation reviews (train_002, train_005).

**Steps:**

1. For each index in the set, collect its level series from `/api/index-levels` for dates >= `level_start_date` and <= `level_end_date`.
2. Compute simple monthly returns for each index: `return = (level_t - level_{t-1}) / level_{t-1}` where `level_{t-1}` is the prior period's level. This yields `N-1` return observations from `N` level points.
3. For each pair (i, j), compute the Pearson correlation coefficient on the aligned return vectors:

   r = covariance(returns_i, returns_j) / (std(returns_i) * std(returns_j))

   Use the population standard deviation (n divisor, not n-1) for both covariance and standard deviation. This computes `sum((x - mean(x)) * (y - mean(y))) / n` divided by `sqrt(sum((x - mean(x))^2) / n) * sqrt(sum((y - mean(y))^2) / n)`.

4. Round each correlation to 3 decimal places.

5. The `return_observations` count equals `N-1`.

**Code pattern (Python):**

```python
def pearson_r(x, y):
    n = len(x)
    mx = sum(x) / n
    my = sum(y) / n
    cov = sum((x[i] - mx) * (y[i] - my) for i in range(n)) / n
    sx = (sum((xi - mx)**2 for xi in x) / n) ** 0.5
    sy = (sum((yi - my)**2 for yi in y) / n) ** 0.5
    return cov / (sx * sy)
```

## Finding extreme correlation pairs

- `highest_positive`: the pair with the maximum correlation value. If ties, prefer the pair with alphabetically first pair_id.
- `lowest`: the pair with the minimum correlation value. If ties, prefer the pair with alphabetically first pair_id.

## China-Asia dependence check

From the correlation matrix, check the pair `(IDX_CHINA, IDX_AC_ASIA_PAC_EX_JP)`. If this correlation exceeds the policy's `correlation_high_threshold`, set `china_asia_dependence_flag: true`, `primary_code: "CHINA_ASIA_DEPENDENCE"`, and `high_threshold_breached: true`.

## Diversification candidate selection

After computing all correlations involving `IDX_CHINA`:

- If `IDX_EM_EX_CHINA` has correlation < `correlation_low_threshold` with `IDX_CHINA`, include it.
- If `IDX_LATAM` has correlation < `correlation_low_threshold` with `IDX_CHINA`, include it.
- If `IDX_INDIA` has correlation < `correlation_low_threshold` with `IDX_CHINA`, include it.

Select candidates with China correlation below the low threshold. Sort results alphabetically.

## Sleeve actions (correlation review)

Based on correlation findings:
- If China concentration is flagged and `IDX_CHINA` shows high correlation with other sleeves: action `"trim"` on `IDX_CHINA`.
- If `IDX_LATAM` is a low-correlation diversifier: action `"add"` on `IDX_LATAM`.
- Sort sleeve actions ascending by sleeve name.

## Signal-to-view mapping

Used by allocation view tasks (train_003, train_005).

1. Fetch signal scores from `/api/macro-signals` for the target quarter and requested opportunity sets.
2. Fetch policy thresholds from `/api/policies` → `allocation_mapping.view_score_thresholds`:
   - score > `OW_min` → `OW`
   - score < `UW_max` → `UW`
   - else → `N`
3. Fetch prior views from `/api/allocation/prior-views` filtered to target quarter (rows where `previous_quarter` matches the prior quarter).
4. Determine view change: compare new view to prior view.
   - `OW` > `N` → `UP`
   - `N` > `OW` → `UP`
   - `N` > `UW` → `DOWN`
   - `UW` > `N` → `DOWN`
   - `UW` < `N` → `UP`
   - `N` < `UW` → `DOWN`
   - Same view → `UNCHANGED`
5. Map conviction from absolute score using `allocation_mapping.conviction_thresholds`:
   - abs(score) >= `HIGH_abs_min` → `HIGH`
   - abs(score) >= `MEDIUM_abs_min` → `MEDIUM`
   - abs(score) < `LOW_abs_below` → `LOW`
6. Use the `rationale_code` from the macro signal record for each opportunity set.

## Risk overlay selection

Based on the overall signal pattern across all allocated opportunity sets:

1. Count the dominant rationale codes across views.
2. If `DURATION_SUPPORT` is prominent and `HY_VALUATION_RISK` is present among reasons for UW views: `overlay_code = "DURATION_QUALITY_TILT"`, `primary_action = "tilt_to_duration_quality"`.
3. Include the most prominent rationale codes (business priority, highest priority first) that support the overlay choice. Priority order: DURATION_SUPPORT, HY_VALUATION_RISK, CHINA_DEPENDENCE, RATE_CUT_SUPPORT, and others.
4. Sort rationale_codes by this business priority.

## Post-trade metric calculations (credit tasks)

For credit trade strategies and risk rebalances:

### HY allocation pct

1. After proposed trades, sum market values of HY-rated holdings.
2. Divide by total portfolio market value.
3. Round to 2 decimal places as percent.

### Weighted modified duration

1. For each post-trade holding, multiply `quantity_usd_m` by `modified_duration_years`.
2. Sum these products.
3. Divide by total market value.
4. Round to 2 decimal places.

### Weighted yield to maturity

1. For each post-trade holding, multiply `quantity_usd_m` by `yield_to_maturity_pct`.
2. Sum these products.
3. Divide by total market value.
4. Round to 2 decimal places.

### Total market value

Sum all holding quantities. Round to template precision.

### HY reduction pct points

pre_trade_hy_pct - post_trade_hy_pct. Round to 2 decimal places.

### Watchlist exposure

Sum market values of watchlisted issuers in the post-trade portfolio. Round to 1 decimal.

## Constraint checks (credit tasks)

- `hy_cap_pass`: post_trade HY allocation pct <= policy max_hy_allocation_pct.
- `duration_band_pass`: post_trade weighted modified duration within policy duration_band_years [min, max] inclusive.
- `selected_issuer_diversification_pass`: no single issuer exceeds the policy issuer_concentration_limit_pct after trades. Compute per-issuer market value / total portfolio market value.
- `selected_subsector_diversification_pass`: at least `subsector_min_count_for_diversified` distinct subsectors among post-trade holdings.
- `watchlist_avoidance_pass`: no BUY candidate is from a watchlisted issuer.

## Bond selection logic (energy-credit BUY strategy)

For energy credit tasks like train_001:

1. From `/api/instruments/bonds`, filter to bonds where `candidate: true` AND `energy_linked: true`.
2. Exclude watchlisted issuers (cross-reference `/api/issuers`).
3. Prefer bonds with higher `yield_to_maturity_pct` while keeping post-trade HY allocation <= 20% and duration within [3.0, 5.0].
4. Ensure at least 2 distinct issuers and 2 distinct subsectors after the buys.
5. Select exactly 2 bonds, each with `notional_usd_m: 4.0` (split evenly).
6. Sort by instrument_id ascending in the trade_package.

## Bond selection logic (fixed-income risk rebalance)

For risk rebalance tasks like train_004:

1. Identify holdings that are HY and/or watchlisted for SELL.
2. Sell enough to meet the target HY reduction (priority: watchlisted first, then by highest HY percentage contribution).
3. Buy IG non-watchlist candidates with `candidate: true` to replace the sold amount while keeping duration in band.
4. Sort trades: SELL before BUY, then ascending instrument_id within each action.

## Rebalance trigger and next step (committee tasks)

For multi-asset committee tasks like train_005:

- If correlation exceeds threshold and concentration flagged: `rebalance_trigger = "correlation_cap_breach"`.
- `portfolio_risk_concentration_flag` matches the flag from correlation analysis.
- `next_step = "approve_with_monitoring"` when constraint violations are present but manageable.
