## Formulas & Computation Methods

### Pearson Correlation (Monthly Simple Returns)

1. For each index `i` with levels `L_0, L_1, ..., L_T` at consecutive month-ends:
   - Simple return: `r_t = (L_t / L_{t-1}) - 1.0` for `t = 1..T`
   - Gives `T` observations (typically 11 for a 12-month window)

2. Pearson correlation between two index return series `X` and `Y` of length `n`:
   ```
   mx = Σx / n,  my = Σy / n
   cov = Σ(x_i - mx)(y_i - my)
   sx = √Σ(x_i - mx)²,  sy = √Σ(y_i - my)²
   r = cov / (sx * sy)
   ```

3. Round to three decimal places. Return `NaN` if standard deviation is zero.

### Post-Trade Portfolio Metrics

Start with current holdings from `/api/portfolios/{id}/holdings`. Apply proposed trades (add BUY quantities, subtract SELL quantities). Use bond master from `/api/instruments/bonds` for rating, duration, and yield data.

- **total_market_value_usd_m**: Sum of all holding quantities after trades
- **hy_allocation_pct**: (Sum of HY-rated quantities / total_mv) × 100
- **weighted_modified_duration_years**: Σ(qty_i × dur_i) / total_mv
- **weighted_yield_to_maturity_pct**: Σ(qty_i × ytm_i) / total_mv
- **hy_reduction_pct_points**: pre_trade_hy_pct - post_trade_hy_pct
- **watchlist_exposure_usd_m**: Sum of quantities whose issuer is on watchlist

### Allocation View Derivation

Use the macro signal `score` and the allocation mapping policy:

- **score ≥ 0.35** → `OW` (Overweight)
- **score ≤ -0.35** → `UW` (Underweight)
- **-0.35 < score < 0.35** → `N` (Neutral)

Conviction from score magnitude:
- **|score| ≥ 0.7** → `HIGH`
- **0.35 ≤ |score| < 0.7** → `MEDIUM`
- **|score| < 0.35** → `LOW`

View change vs prior quarter:
- Compare current derived view to prior quarter's view from `/api/allocation/prior-views`
- If current > prior rank → `UP`; if current < prior rank → `DOWN`; else `UNCHANGED`

### Constraint Checks (Credit Portfolios)

- **hy_cap_pass**: post_trade `hy_allocation_pct` ≤ `max_hy_allocation_pct` (20%)
- **duration_band_pass**: post_trade duration within `[min, max]` (default 3.0–5.0 years)
- **issuer_diversification_pass**: No single issuer > 12% of post-trade market value
- **subsector_diversification_pass**: At least 2 distinct subsectors represented among the traded instruments
- **watchlist_avoidance_pass**: No BUY trades on watchlisted issuers; SELL trades on watchlisted issuers are permitted

### Correlation Concentration Check

- **china_asia_dependence_flag**: True when IDX_CHINA vs IDX_AC_ASIA_PAC_EX_JP correlation > 0.8
- **high_threshold_breached**: True when any pair correlation exceeds `correlation_high_threshold` (0.8)
- **primary_code**: `CHINA_ASIA_DEPENDENCE` when china_asia flag is true, `GLOBAL_DEVELOPED_OVERLAP` when EM-WORLD correlation > 0.8 but china dependence is false, `NO_MATERIAL_CONCENTRATION` otherwise

### Trade Package Sorting

- **trade_package**: Sort ascending by `instrument_id`
- **rotation trades**: Sort SELL before BUY, then ascending by `instrument_id` within each action
- **index_id pairs**: Sort alphabetically within each pair
