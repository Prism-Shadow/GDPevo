# Computation Reference

All computations use the current environment records as the authoritative data
source. Payload values are intake context only and must be validated against the
environment before use.

## Portfolio-level weighted metrics

After proposing trades, recompute the following from the post-trade holdings.

**Notation:**
- q_i = quantity (USD millions) of holding i
- y_i = yield_to_maturity_pct of instrument i (from /api/instruments/bonds)
- d_i = modified_duration_years of instrument i
- r_i = "HY" if instrument i has rating_bucket == "HY", else "IG"

### Weighted yield to maturity
```
weighted_ytm = sum(q_i * y_i) / sum(q_i)
```
Round to the precision declared in the answer template.

### Weighted modified duration
```
weighted_duration = sum(q_i * d_i) / sum(q_i)
```
Round to the precision declared in the answer template.

### HY allocation percentage
```
hy_pct = (sum of q_i where r_i == "HY") / sum(q_i) * 100
```
Round to the precision declared in the answer template.

### HY reduction in percentage points
```
hy_reduction_ppt = pre_trade_hy_pct - post_trade_hy_pct
```
Round to two decimal places.

### Total market value
```
total_mv = sum(q_i)
```
This equals the sum of all post-trade holding quantities. Add the new buy
notionals to the pre-trade total if the template asks for post_trade metrics
with buys appended.

### Issuer concentration
For each issuer, sum the quantities of all holdings mapped to that issuer
(via instrument → issuer_id lookup). Divide by total market value and multiply
by 100. Check that no issuer exceeds the policy's issuer_concentration_limit_pct.

### Subsector diversification
Count distinct subsectors across all post-trade holdings. Check against the
policy's subsector_min_count_for_diversified.

## Pearson correlation from index levels

Compute Pearson correlation from two series of monthly simple returns derived
from consecutive index levels.

**Step 1:** For a given index, collect the level array for the requested date
window. Let L[t] be the level at observation t (t = 0, 1, ..., N-1, where N is
the number of observations in the window).

**Step 2:** Compute monthly simple returns:
```
R[t] = (L[t] / L[t-1]) - 1,   for t = 1 to N-1
```
This yields N-1 return observations.

**Step 3:** For two indices A and B with return series R_a and R_b (both of
length n = N-1):
```
mean_a = sum(R_a) / n
mean_b = sum(R_b) / n
cov = sum((R_a[i] - mean_a) * (R_b[i] - mean_b)) / (n - 1)
std_a = sqrt(sum((R_a[i] - mean_a)^2) / (n - 1))
std_b = sqrt(sum((R_b[i] - mean_b)^2) / (n - 1))
r = cov / (std_a * std_b)
```
Round the result to three decimal places as required by the answer templates.

**Using the script:** The bundled script `scripts/pearson_corr.py` implements
this computation. Pipe two JSON arrays of levels (numbers only, in chronological
order) to stdin:
```
echo '[1032.9333, 1054.2742, ...]' $'\n' '[1005.12, 1010.34, ...]' | python3 scripts/pearson_corr.py
```
It outputs the Pearson r rounded to three decimals. Use this instead of
hand-rolling the computation to avoid rounding and floating-point errors.

### Finding extreme pairs
When the task asks for highest_positive and lowest correlation pairs across an
index universe:
1. Fetch all required index levels from the environment.
2. Compute the Pearson correlation for every unordered pair of distinct indices.
3. The highest_positive pair is the one with the largest r value.
4. The lowest pair is the one with the smallest (most negative) r value.
5. Within each pair, sort the index ids alphabetically.
6. Use the bundled script to compute each pair's correlation deterministically.

### Return observations count
`return_observations` = number of levels minus 1. For 12 month-end levels,
there are 11 return observations.

## Signal-to-view mapping

Use the `allocation_mapping` policy from `/api/policies`:

**View thresholds:** OW_min = 0.35, UW_max = -0.35
```
view = "OW"  if signal_score >= 0.35
view = "UW"  if signal_score <= -0.35
view = "N"   otherwise (between -0.35 and 0.35, exclusive)
```

**Conviction thresholds:** HIGH_abs_min = 0.7, MEDIUM_abs_min = 0.35
```
conviction = "HIGH"   if abs(signal_score) >= 0.7
conviction = "MEDIUM" if abs(signal_score) >= 0.35
conviction = "LOW"    otherwise
```

**View change vs prior quarter:**
Compare the current view (computed from signal_score using the thresholds above)
with the prior-quarter view from `/api/allocation/prior-views`:

| Prior → Current | Change     |
|-----------------|------------|
| N → OW          | UP         |
| UW → N          | UP         |
| UW → OW         | UP         |
| OW → N          | DOWN       |
| N → UW          | DOWN       |
| OW → UW         | DOWN       |
| same            | UNCHANGED  |

**Rationale code:** Use the `rationale_code` from `/api/macro-signals` for the
matching opportunity set and quarter. The signal score, rationale code, and
drivers are correlated — the rationale code encodes the macro narrative that
explains the signal direction. When the signal score is in the neutral band,
prefer `NEUTRAL_BALANCE` as the rationale code.

## Constraint checks

All thresholds come from `/api/policies` under the policy_id that matches the
portfolio's `constraint_policy_id`.

### Credit constraints (POL_CREDIT_DEFAULT, POL_CREDIT_RISK_REDUCTION)
- `hy_cap_pass`: post_trade_hy_allocation_pct ≤ max_hy_allocation_pct (20%)
- `duration_band_pass`: post_trade_duration_years within [3.0, 5.0]
- `selected_issuer_diversification_pass`: no issuer > 12% of portfolio
- `selected_subsector_diversification_pass`: ≥ 2 distinct subsectors
- `watchlist_avoidance_pass`: all BUY instruments from non-watchlist issuers
- `target_hy_reduction_met`: hy_reduction_pct_points ≥ target_hy_reduction_pct

### Correlation constraints (POL_CORRELATION_DEFAULT)
- `high_threshold_breached`: any pair correlation ≥ 0.8
- `china_asia_dependence_flag`: true if IDX_CHINA:IDX_AC_ASIA_PAC_EX_JP
  correlation exceeds high_threshold

### Concentration assessment
- `primary_code = "CHINA_ASIA_DEPENDENCE"` when the China-Asia Pacific pair
  breaches the high threshold
- `primary_code = "GLOBAL_DEVELOPED_OVERLAP"` when World-ACWI IMI or
  World-EAFE pairs breach the high threshold
- `primary_code = "NO_MATERIAL_CONCENTRATION"` otherwise

## Watchlist handling

The authoritative watchlist record is `issuer.watchlist` from `/api/issuers`.
The bond-level `recommended_theme_tags` may include `WATCHLIST_RISK` as a desk
tag, but this is an advisory signal, not the official status.

When watchlist avoidance is required:
- For sell tickets: sell all holdings whose issuer is on the watchlist.
- For buy tickets: only buy instruments from issuers with `watchlist: false`.
- Check every candidate's issuer against `/api/issuers` before committing to a
  buy.
