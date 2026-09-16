# Asteria Scoring Rules

## View Mapping (Signal Score to View)

Apply the thresholds from `/api/policies` → `allocation_mapping` → `view_score_thresholds`:

| Condition              | View |
|------------------------|------|
| score ≥ OW_min         | OW   |
| score ≤ UW_max         | UW   |
| UW_max < score < OW_min | N   |

Default thresholds: OW_min = 0.35, UW_max = -0.35, neutral_between = (-0.35, 0.35).

## Conviction Mapping (Signal Score to Conviction)

Apply the thresholds from `/api/policies` → `allocation_mapping` → `conviction_thresholds`:

| Condition          | Conviction |
|--------------------|------------|
| abs(score) ≥ 0.70  | HIGH       |
| abs(score) ≥ 0.35  | MEDIUM     |
| abs(score) < 0.35  | LOW        |

Check HIGH first, then MEDIUM, then LOW. Default thresholds: HIGH_abs_min = 0.70, MEDIUM_abs_min = 0.35.

## Change Detection (View → Change vs Prior Quarter)

Compare the current mapped view to the prior-quarter view from `/api/allocation/prior-views`.
Use the policy `view_rank` mapping: N = 0, OW = 1, UW = -1.

| Condition                    | Change    |
|------------------------------|-----------|
| current_rank > prior_rank    | UP        |
| current_rank < prior_rank    | DOWN      |
| current_rank == prior_rank   | UNCHANGED |

When the prior view is N (rank 0) and the new view is OW (rank 1), the change is UP.
When the prior view is N and the new view is UW (rank -1), the change is DOWN.
When both views are the same, the change is UNCHANGED regardless of conviction.

## Pearson Correlation

Formula for two aligned series of monthly simple returns:

```
r = covariance(X, Y) / (std(X) * std(Y))
```

Where covariance and standard deviation are sample statistics (divide by n-1).

Monthly simple return: `return_t = (level_t / level_{t-1}) - 1`

For a 12-month level window (e.g. 2025-05-30 through 2026-04-30), there are 12
level dates and 11 return observations. The first date provides the denominator
for the first return.

Correlation values are rounded to 3 decimal places.

## Portfolio Metrics

### HY Allocation Percentage

```
hy_pct = (sum of HY-rated holding quantities / total portfolio market value) * 100
```

Rating bucket "HY" includes all bonds where `rating_bucket` is "HY".
Total market value is the sum of all holding quantities plus any new BUY
notional, minus any SELL notional.

### Weighted Modified Duration

```
wtd_duration = sum(holding_qty * bond_duration) / total_market_value
```

### Weighted Yield to Maturity

```
wtd_ytm = sum(holding_qty * bond_ytm) / total_market_value
```

### HY Reduction in Percentage Points

```
hy_reduction_pts = pre_trade_hy_pct - post_trade_hy_pct
```

## Constraint Checks

### HY Cap Pass

```
hy_cap_pass = post_trade_hy_allocation_pct <= policy.max_hy_allocation_pct
```

### Duration Band Pass

```
duration_band_pass = policy.duration_band_years[0] <= post_trade_duration_years <= policy.duration_band_years[1]
```

### Issuer Diversification Pass

No single issuer's total holding exceeds the policy `issuer_concentration_limit_pct`
of total market value (typically 12%). Check the selected instruments (new buys
plus retained holdings) do not concentrate a single issuer above the limit.

### Subsector Diversification Pass

The selected instruments span at least `subsector_min_count_for_diversified`
distinct subsectors (typically 2).

### Watchlist Avoidance Pass

None of the instruments selected for BUY have a watchlisted issuer. Check
`/api/issuers` for `watchlist: true`.

## Correlation Concentration Rules

- **High threshold**: correlation ≥ policy `correlation_high_threshold` (default 0.80) flags
  concentration risk.
- **Low threshold**: correlation ≤ policy `correlation_low_threshold` (default 0.20) flags
  a diversification candidate.

When the China index correlates ≥ 0.80 with EM or AC Asia Pacific ex Japan,
flag `china_asia_dependence_flag = true` and set `primary_code = "CHINA_ASIA_DEPENDENCE"`.

## Risk Overlay Selection

Choose the single overlay code that best describes the aggregate signal pattern:

- `DURATION_QUALITY_TILT` when duration signals (U.S. Treasuries, Bunds) are
  positive and credit/equity signals are negative/mixed.
- `CREDIT_RISK_REDUCTION` when HY valuation risk dominates and duration
  signals are neutral/positive.
- `EQUITY_BETA_EXTENSION` when equity signals are broadly positive and credit
  spreads are benign.
- `CURRENCY_DEFENSIVE_HEDGE` when dollar defensive signals dominate and
  equity/credit carry signals are mixed.
- `NO_OVERLAY` when signals are mostly neutral.

The primary_action must match the overlay_code according to these pairings:

| overlay_code              | primary_action           |
|---------------------------|--------------------------|
| DURATION_QUALITY_TILT     | tilt_to_duration_quality |
| CREDIT_RISK_REDUCTION     | trim_credit_beta         |
| EQUITY_BETA_EXTENSION     | add_cyclical_equity_beta |
| CURRENCY_DEFENSIVE_HEDGE  | add_currency_hedge       |
| NO_OVERLAY                | hold_policy_weights      |

Rationale codes for the risk overlay are selected from the same rationale code
enumeration (e.g. `DURATION_SUPPORT`, `HY_VALUATION_RISK`, `CHINA_DEPENDENCE`) and
ordered by business priority (most important first).
