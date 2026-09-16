# Computation Rules

Deterministic formulas for every numeric output in Asteria tasks.

---

## Post-Trade Portfolio Metrics (Family A)

Given:
- Current holdings from `/api/portfolios/{id}/holdings` (each has `instrument_id`, `quantity_usd_m`)
- Bond attributes from `/api/instruments/bonds` (keyed by `instrument_id`; each has `rating_bucket`, `modified_duration_years`, `yield_to_maturity_pct`, `issuer_id`, `subsector`)
- Proposed trades (each has `action`, `instrument_id`, `notional_usd_m` or `quantity_usd_m`)

### Step 1: Build the post-trade holdings list

Start with current holdings. For each SELL trade, subtract quantity from the
matching holding (if the holding is fully removed, drop it). For each BUY trade,
add a new holding entry at the given quantity.

### Step 2: Compute total market value

```
total_market_value_usd_m = sum(quantity_usd_m for each post-trade holding)
```

Round to 2 decimals.

### Step 3: Compute HY allocation %

```
hy_market_value = sum(quantity_usd_m for holdings whose bond rating_bucket == "HY")
hy_allocation_pct = (hy_market_value / total_market_value_usd_m) * 100
```

Round to 2 decimals.

### Step 4: Compute weighted modified duration

```
weighted_duration = sum(quantity_usd_m * bond.modified_duration_years for each holding) / total_market_value_usd_m
```

Round to 2 decimals.

### Step 5: Compute weighted YTM

```
weighted_ytm = sum(quantity_usd_m * bond.yield_to_maturity_pct for each holding) / total_market_value_usd_m
```

Round to 2 decimals.

### Step 6: Compute HY reduction

```
hy_reduction_pct_points = pre_trade_hy_pct - post_trade_hy_pct
```

Round to 2 decimals.

### Step 7: Compute watchlist exposure

```
watchlist_exposure = sum(quantity_usd_m for holdings whose issuer is watchlisted)
```

Round to 1 decimal.

---

## Pearson Correlation (Family B)

Given two index level series from the review window.

### Monthly simple return

For each pair of consecutive dates in the window:

```
return_i = (level_i - level_{i-1}) / level_{i-1}
```

Do this for both index series, producing two equal-length arrays of returns.

### Pearson formula

```
r = sum((x_i - x_mean) * (y_i - y_mean)) / sqrt(sum((x_i - x_mean)^2) * sum((y_i - y_mean)^2))
```

Where x and y are the return arrays.

Round to 3 decimals.

### Observation count

```
return_observations = len(levels) - 1
```

Only count pairs where both indices have levels for consecutive dates.

### Pair ordering

Within each pair_id array, sort index ids alphabetically. For example,
`["IDX_CHINA", "IDX_EM"]` not `["IDX_EM", "IDX_CHINA"]`.

---

## Active View Derivation (Family C)

### View from signal score

Using thresholds from `allocation_mapping.view_score_thresholds`:

```
if score >= OW_min: view = "OW"
elif score <= UW_max: view = "UW"
else: view = "N"
```

### Change from prior view

Using ranks from `allocation_mapping.view_rank` (OW=1, N=0, UW=-1):

```
if rank(current_view) > rank(prior_view): change = "UP"
elif rank(current_view) < rank(prior_view): change = "DOWN"
else: change = "UNCHANGED"
```

### Conviction from score magnitude

Using thresholds from `allocation_mapping.conviction_thresholds`:

```
if abs(score) >= HIGH_abs_min: conviction = "HIGH"
elif abs(score) >= MEDIUM_abs_min: conviction = "MEDIUM"
else: conviction = "LOW"
```

Note: conviction is derived from the current quarter's signal score, not from
the prior-views conviction field. The prior-views conviction field is the
previously published conviction and should not be copied forward.

### Rationale code

Use the `rationale_code` field from the macro-signal record for the matching
opportunity_set and quarter. Do not invent codes or use codes from different
opportunity sets.

---

## Constraint Checks (Family A)

### HY cap pass

```
hy_cap_pass = (post_trade_hy_allocation_pct <= max_hy_allocation_pct)
```

### Duration band pass

```
duration_band_pass = (duration_band_years[0] <= weighted_duration <= duration_band_years[1])
```

### Issuer diversification pass

For each issuer represented in the selected (buy) instruments:
```
issuer_share = sum(quantity of holdings from that issuer) / total_market_value * 100
```
If any issuer_share > issuer_concentration_limit_pct, fail.

### Subsector diversification pass

Count distinct subsectors among the selected trade instruments. Must be >=
subsector_min_count_for_diversified.

### Watchlist avoidance pass

For every BUY ticket, check the issuer's `watchlist` field from `/api/issuers`.
If any is `true`, fail.
