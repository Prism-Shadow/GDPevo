# Asteria Environment API Reference

This document describes the Asteria Investment Office shared environment
service endpoints. The base URL is provided in the task's environment
context (typically `http://task-env:9010/`). All endpoints return JSON.

## Quick-reference table

| Method | Path | Purpose |
|--------|------|---------|
| GET | / | Service root; returns as-of date and health |
| GET | /api/portfolios | List all available portfolios |
| GET | /api/portfolios/{id}/holdings | Holdings for a portfolio |
| GET | /api/instruments/bonds | Full bond catalog |
| GET | /api/issuers | All issuer records |
| GET | /api/market/energy | Energy-market data |
| GET | /api/indices | All index metadata |
| GET | /api/index-levels | All index level time series |
| GET | /api/index-levels/{index_id} | Level series for one index |
| GET | /api/allocation/opportunity-sets | Opportunity-set taxonomy |
| GET | /api/allocation/prior-views | Prior-quarter allocation views |
| GET | /api/macro-signals | Current macro signal scores |

---

## GET /

Service root. Returns the environment's current as-of date.

### Expected response shape

```json
{
  "service": "Asteria Investment Office",
  "as_of_date": "2026-05-29",
  "status": "ok"
}
```

The `as_of_date` field should be used as the `as_of_date` throughout
the answer JSON unless the answer template specifies a different date.

---

## GET /api/portfolios

Returns a list of all available portfolio records.

### Expected response shape

```json
[
  {
    "portfolio_id": "PF-EXAMPLE",
    "name": "Example Portfolio",
    "currency": "USD",
    "benchmark": "...",
    "hy_cap_pct": 20.0,
    "duration_min_years": 2.5,
    "duration_max_years": 4.5,
    "as_of_date": "2026-05-29"
  }
]
```

### Key fields

- `portfolio_id` — String, matches the request's portfolio identifier.
- `hy_cap_pct` — Number, the maximum high-yield allocation as a percent.
  Used for `hy_cap_pass` constraint checks.
- `duration_min_years` / `duration_max_years` — Numbers, the CIO-approved
  modified-duration band. Used for `duration_band_pass` checks.
- `as_of_date` — String, the record date.

---

## GET /api/portfolios/{portfolio_id}/holdings

Returns the current holdings for a specific portfolio.

### Expected response shape

```json
[
  {
    "instrument_id": "BND_EXAMPLE_2030",
    "market_value_usd_m": 5.2,
    "quantity": 5000000,
    "as_of_date": "2026-05-29"
  }
]
```

### Key fields

- `instrument_id` — String, cross-reference with `/api/instruments/bonds`.
- `market_value_usd_m` — Number (USD millions), used for weighted
  metric calculations and post-trade simulation.
- `quantity` — Number, par or face amount held.

---

## GET /api/instruments/bonds

Returns the full bond catalog. Every bond in the environment appears here.

### Expected response shape

```json
[
  {
    "instrument_id": "BND_EXAMPLE_2030",
    "issuer_id": "ISSUER_EXAMPLE",
    "coupon_pct": 4.75,
    "maturity_date": "2030-06-15",
    "rating": "BBB+",
    "sector": "Energy",
    "subsector": "LNG Midstream",
    "ytm_pct": 5.2,
    "modified_duration_years": 3.6,
    "market_value_usd_m": 125.0
  }
]
```

### Key fields

- `instrument_id` — String, bond identifier used in trade packages.
- `issuer_id` — String, cross-reference with `/api/issuers`.
- `rating` — String, credit rating (IG if BBB-/Baa3 or above).
- `sector` / `subsector` — Used for subsector diversification checks.
- `ytm_pct` — Number (percent), used for carry ranking.
- `modified_duration_years` — Number, used for weighted duration.
- `market_value_usd_m` — Number, total market value outstanding.

---

## GET /api/issuers

Returns all issuer records including watchlist status.

### Expected response shape

```json
[
  {
    "issuer_id": "ISSUER_EXAMPLE",
    "issuer_name": "Example Energy Corp",
    "sector": "Energy",
    "rating": "BBB+",
    "watchlist": false
  }
]
```

### Key fields

- `issuer_id` — String, cross-reference with bond instruments.
- `watchlist` — Boolean, true if the issuer is flagged for elevated
  credit risk. Used for watchlist avoidance and sell-candidate selection.

---

## GET /api/market/energy

Returns energy-market data used for thematic context in energy-credit
trade recommendations.

### Expected response shape

```json
{
  "as_of_date": "2026-05-29",
  "lng_spot_price": 12.4,
  "oil_spot_price": 72.5,
  "gas_demand_forecast": "rising",
  "commentary": "..."
}
```

---

## GET /api/indices

Returns metadata for all equity indices.

### Expected response shape

```json
[
  {
    "index_id": "IDX_EM",
    "name": "MSCI Emerging Markets",
    "region": "Global EM",
    "currency": "USD"
  }
]
```

### Key fields

- `index_id` — String, used throughout correlation reviews.

---

## GET /api/index-levels

Returns all monthly index-level time series for all indices.

### Expected response shape

```json
[
  {
    "index_id": "IDX_EM",
    "levels": [
      {"date": "2025-05-30", "value": 1102.3},
      {"date": "2025-06-30", "value": 1098.7}
    ]
  }
]
```

Each index object contains a `levels` array of `{date, value}` pairs
sorted chronologically.

---

## GET /api/index-levels/{index_id}

Returns the monthly level series for a single index.

### Expected response shape

```json
{
  "index_id": "IDX_EM",
  "levels": [
    {"date": "2025-05-30", "value": 1102.3},
    {"date": "2025-06-30", "value": 1098.7}
  ]
}
```

Same shape as a single element from `/api/index-levels`. Use this
endpoint when only a subset of indices is needed.

---

## GET /api/allocation/opportunity-sets

Returns the taxonomy of all opportunity sets used in allocation views.

### Expected response shape

```json
[
  {
    "opportunity_set": "Emerging Markets",
    "asset_class": "Equities",
    "policy_weight_pct": 12.5
  }
]
```

### Key fields

- `opportunity_set` — String, matches the set names in allocation
  request payloads ("Europe", "Japan", "Emerging Markets", "India",
  "Latin America", "U.S. Treasuries", "Corporate High Yield", "EUR", "USD").
- `asset_class` — One of "Equities", "Duration", "Credit", "Currency".
  Use this exact value in the `asset_class` field of allocation view rows.

---

## GET /api/allocation/prior-views

Returns the allocation views from the prior quarter.

### Expected response shape

```json
[
  {
    "opportunity_set": "Emerging Markets",
    "quarter": "Q4_2025",
    "view": "N",
    "conviction": "MEDIUM"
  }
]
```

### Key fields

- `opportunity_set` — String, the opportunity set.
- `quarter` — String, the quarter this view applies to (used to
  confirm the baseline is the correct prior quarter).
- `view` — "UW", "N", or "OW". The baseline for computing `change`.
- `conviction` — String, prior conviction level.

---

## GET /api/macro-signals

Returns current macro signal scores for each opportunity set.

### Expected response shape

```json
[
  {
    "opportunity_set": "Emerging Markets",
    "signal_score": 0.250,
    "as_of_date": "2026-05-29"
  }
]
```

### Key fields

- `opportunity_set` — String, the opportunity set.
- `signal_score` — Number, signed score where positive values support
  an overweight stance and negative values support underweight. Used
  alongside prior views to determine the current view and change.

---

## General usage notes

- Query endpoints in parallel where possible (e.g., fetch holdings,
  bonds, and issuers simultaneously for credit tasks).
- The `as_of_date` from the root or portfolio endpoint is the
  authoritative date for the answer.
- Every endpoint returns JSON arrays/objects. Use a JSON parser; do
  not hand-parse strings.
- Response field names are consistent across endpoints: `instrument_id`,
  `issuer_id`, `opportunity_set`, `index_id` always use
  the same key.
