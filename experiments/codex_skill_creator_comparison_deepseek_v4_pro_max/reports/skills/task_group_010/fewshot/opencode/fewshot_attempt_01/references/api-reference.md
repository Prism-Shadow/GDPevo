# Asteria API Reference

All endpoints return JSON. Base URL is given in `environment_access.md` (typically `http://task-env:9010/`). No authentication required.

## GET /api/catalog

Returns all valid ids across every domain. Read this first to confirm which ids exist.

```json
{
  "bond_instrument_ids": ["BND_..."],
  "index_ids": ["IDX_..."],
  "issuer_ids": ["ISS_..."],
  "opportunity_sets": ["..."],
  "policy_ids": ["POL_..."],
  "portfolio_ids": ["PF-..."]
}
```

## GET /api/portfolios

Returns all portfolios with current summaries.

Each portfolio object:
```json
{
  "portfolio_id": "PF-EN-ALTA",
  "name": "Alta Energy Income Sleeve",
  "as_of_date": "2026-05-29",
  "base_currency": "USD",
  "market_value_usd_m": 60.0,
  "holding_count": 5,
  "constraint_policy_id": "POL_CREDIT_DEFAULT",
  "strategy": "...",
  "objective": "..."
}
```

Key fields for every task:
- `market_value_usd_m`: current total market value (use this, not payload snapshots).
- `constraint_policy_id`: which sub-policy inside `/api/policies` applies.
- `as_of_date`: the environment snapshot date to use as your `as_of_date` in the answer.

## GET /api/portfolios/{portfolio_id}/holdings

Returns the current holdings for one portfolio. Every holding has:

```json
{
  "instrument_id": "BND_AURORA_2029",
  "quantity_usd_m": 18.0,
  "asset_class": "Fixed Income",
  "sleeve": "Energy Credit",
  "notes": "Core IG oil exposure"
}
```

For equity portfolios, `instrument_id` is an index id (e.g., `IDX_EM`). For credit portfolios, it is a bond id (e.g., `BND_AURORA_2029`).

**Important:** Holdings may include bonds that are `candidate: false` in the bond universe (meaning they are existing positions, not available for new buys). Check `candidate` status when selecting new purchases.

## GET /api/instruments/bonds

Full bond universe. Every bond has:

```json
{
  "instrument_id": "BND_BLUEGAS_2030",
  "issuer_id": "ISS_BLUEGAS",
  "issuer_name": "BlueGas LNG Holdings",
  "coupon_pct": 5.1,
  "maturity": "2030-02-20",
  "modified_duration_years": 4.0,
  "yield_to_maturity_pct": 5.95,
  "spread_bps": 168,
  "rating": "BBB-",
  "rating_bucket": "IG",
  "sector": "Energy",
  "subsector": "Natural Gas/LNG",
  "energy_linked": true,
  "candidate": true,
  "recommended_theme_tags": ["LNG_EXPORTS", "GAS_DEMAND"]
}
```

Key selection criteria:
- `candidate: true` = available for new purchases. `candidate: false` means existing-only.
- `rating_bucket`: "IG" (investment grade: BBB- and above) or "HY" (high yield: BB+ and below).
- `energy_linked`: whether the bond has energy exposure (relevant for energy-desk tasks).
- `modified_duration_years`: always use this for duration calculations, not time-to-maturity.
- `yield_to_maturity_pct`: YTW for yield calculations.
- Cross-reference `issuer_id` with `/api/issuers` to determine watchlist status.

## GET /api/issuers

Issuer research records. Every issuer has:

```json
{
  "issuer_id": "ISS_BLUEGAS",
  "issuer_name": "BlueGas LNG Holdings",
  "sector": "Energy",
  "subsector": "Natural Gas/LNG",
  "rating_bucket": "IG",
  "credit_outlook": "positive",
  "watchlist": false,
  "research_tags": ["LNG_CONTRACTS", "EXPORT_CAPACITY"]
}
```

Key field: `watchlist` (boolean). Bonds from watchlisted issuers should be avoided for BUY actions. Watchlist bonds that are already held should be considered for SELL in rebalance tasks.

## GET /api/market/energy

Energy market signals. Returns:

```json
{
  "as_of_date": "2026-05-29",
  "source": "Asteria macro and commodities desk",
  "pitch_themes": ["LNG_EXPORT_GROWTH", "MIDSTREAM_DEFENSIVE_CARRY", ...],
  "signals": [
    {
      "signal_id": "LNG_EXPORT_PULL",
      "commodity": "Global LNG",
      "direction": "positive",
      "score": 0.72,
      "summary": "..."
    }
  ],
  "stale_data_warning": "..."
}
```

Use this for energy-credit desk tasks to align bond selection with current commodity themes. The `pitch_themes` array suggests client-facing themes for `sales_positioning`.

## GET /api/indices

Index metadata. Each index:

```json
{
  "index_id": "IDX_EM",
  "display_name": "Asteria EM Equity",
  "region": "Emerging Markets",
  "currency": "USD",
  "frequency": "monthly",
  "level_start_date": "2025-05-30",
  "level_end_date": "2026-04-30"
}
```

The date range shows the full window available. Filter to the payload's review window when computing correlations.

## GET /api/index-levels

Returns level history for all indices as a JSON object keyed by index_id:

```json
{
  "IDX_EM": [
    {"date": "2025-05-30", "level": 994.8355},
    {"date": "2025-06-30", "level": 1007.0331},
    ...
  ],
  ...
}
```

Each index has 12 monthly levels spanning May 2025 through April 2026 (11 return observations). Levels are end-of-month.

## GET /api/index-levels/{index_id}

Same structure but for a single index. Use when you only need a subset.

## GET /api/allocation/opportunity-sets

Taxonomy mapping opportunity set names to asset classes:

```json
{
  "opportunity_set": "Emerging Markets",
  "asset_class": "Equities",
  "sub_asset_class": "Emerging Markets",
  "display_order": 9
}
```

Use this to fill `asset_class` in allocation view rows. The four asset classes are: Equities, Duration, Credit, Currency.

## GET /api/allocation/prior-views

Prior-quarter allocation views. Each record:

```json
{
  "opportunity_set": "Emerging Markets",
  "quarter": "Q2_2026",
  "previous_quarter": "Q1_2026",
  "view": "N",
  "conviction": "LOW"
}
```

The endpoint returns records for multiple quarters. To get Q2_2026 prior views, filter to records where `previous_quarter` is `"Q1_2026"`. Do not confuse `quarter` (the target quarter, Q2_2026) with `previous_quarter` (the prior quarter, Q1_2026).

The `view` field in prior-views uses the same mapping as current views: "OW", "N", or "UW". This is the prior view used for `change` computation.

**Important:** The prior-views endpoint gives the view from the *prior quarter's perspective* about the current quarter. So for a Q2_2026 refresh, the record with `previous_quarter: "Q1_2026"` and `quarter: "Q2_2026"` is the prior view you compare against.

## GET /api/macro-signals

Current-quarter signal scores. Each record:

```json
{
  "opportunity_set": "Emerging Markets",
  "quarter": "Q2_2026",
  "score": -0.373,
  "rationale_code": "CHINA_DEPENDENCE",
  "drivers": ["china_drag", "dollar_sensitivity"]
}
```

The `score` is the primary input for view mapping. The `rationale_code` is the justification to use in the output. The `drivers` array provides context but is not directly used in the answer.

Filter to the target quarter (`quarter` field matches the payload's target quarter). The endpoint returns records for multiple quarters.

## GET /api/policies

Returns a wrapper object containing all sub-policies, plus a top-level `policy_id` and `as_of_date`:

```json
{
  "policy_id": "POLICY_SET_2026_05",
  "as_of_date": "2026-05-29",
  "allocation_mapping": { ... },
  "correlation": { ... },
  "credit_default": { ... },
  "credit_risk_reduction": { ... },
  "multi_asset": { ... },
  "multi_asset_risk": { ... }
}
```

Extract the sub-policy matching the portfolio's `constraint_policy_id`. See `references/policy-reference.md` for the meaning of each sub-policy's fields.
