## Asteria Investment Office API Reference

Base URL: declared in the environment access file provided with each task.
All endpoints return JSON. No authentication required.

### Portfolio Endpoints

**GET /api/portfolios** — List all portfolios with summary fields:
`portfolio_id`, `name`, `as_of_date`, `market_value_usd_m`, `holding_count`,
`constraint_policy_id`, `objective`, `strategy`, `base_currency`.

**GET /api/portfolios/{portfolio_id}/holdings** — Current holdings for one portfolio:

```json
{
  "portfolio_id": "PF-EN-ALTA",
  "as_of_date": "2026-05-29",
  "base_currency": "USD",
  "holdings": [
    {
      "asset_class": "Fixed Income",
      "instrument_id": "BND_AURORA_2029",
      "quantity_usd_m": 18.0,
      "sleeve": "Energy Credit",
      "notes": "Core IG oil exposure"
    }
  ]
}
```

### Bond Instrument Endpoints

**GET /api/instruments/bonds** — Full bond universe (held and candidate). Each bond:

| Field | Description |
|---|---|
| `instrument_id` | e.g. `BND_BLUEGAS_2030` |
| `candidate` | `true` if available for new trades |
| `coupon_pct` | Coupon rate as percent |
| `energy_linked` | `true` for energy-sector bonds |
| `issuer_id` / `issuer_name` | Issuer reference |
| `maturity` | `YYYY-MM-DD` |
| `modified_duration_years` | Modified duration |
| `rating` | `AAA` … `CCC` |
| `rating_bucket` | `IG` (BBB- and above) or `HY` (BB+ and below) |
| `recommended_theme_tags` | Thematic tags for sales pitches |
| `sector` | `Energy`, `Materials`, `Financials`, etc. |
| `subsector` | `Natural Gas/LNG`, `Midstream`, `Integrated Oil`, etc. |
| `spread_bps` | Spread over benchmark in basis points |
| `yield_to_maturity_pct` | YTW as percent |

### Issuer Endpoints

**GET /api/issuers** — Issuer research records:

| Field | Description |
|---|---|
| `issuer_id` | e.g. `ISS_BLUEGAS` |
| `issuer_name` | Legal name |
| `rating_bucket` | `IG` or `HY` |
| `credit_outlook` | `positive`, `stable`, `negative` |
| `watchlist` | `true` = issuer is on credit watchlist |
| `research_tags` | Analysts' risk/opportunity tags |
| `sector` / `subsector` | Classification |

### Index Endpoints

**GET /api/indices** — List all indices with `index_id`, `display_name`, `region`,
`level_start_date`, `level_end_date`, `frequency`.

**GET /api/index-levels** — All index level data at once (one entry per index).

**GET /api/index-levels/{index_id}** — Single index levels:

```json
{
  "index_id": "IDX_EM",
  "levels": [
    {"date": "2025-05-30", "level": 994.8355},
    {"date": "2025-06-30", "level": 1007.0331}
  ]
}
```

Monthly frequency, month-end dates. Levels represent total-return index values in
USD terms. Use consecutive pairs for monthly simple returns:
`(level_t - level_{t-1}) / level_{t-1}`.

### Policy Endpoints

**GET /api/policies** — All policy records in one response. Key sub-objects:

- `policy_id` — Top-level policy set identifier (e.g. `POLICY_SET_2026_05`)
- `credit_default` / `credit_risk_reduction` — Credit constraint policies with:
  `policy_id`, `max_hy_allocation_pct`, `duration_band_years` [min, max],
  `issuer_concentration_limit_pct`, `subsector_min_count_for_diversified`,
  `target_hy_reduction_pct`
- `correlation` — `policy_id`, `correlation_high_threshold`, `correlation_low_threshold`,
  `review_window_start`, `review_window_end`
- `allocation_mapping` — `view_score_thresholds` (`OW_min`, `UW_max`, `neutral_between`),
  `conviction_thresholds` (`HIGH_abs_min`, `MEDIUM_abs_min`, `LOW_abs_below`),
  `view_rank` mapping
- `multi_asset` / `multi_asset_risk` — Composite policy references

A portfolio's `constraint_policy_id` links it to the relevant credit or correlation
policy sub-object.

### Allocation Endpoints

**GET /api/allocation/opportunity-sets** — Ordered taxonomy:
`opportunity_set`, `asset_class` (`Equities` / `Duration` / `Credit` / `Currency`),
`sub_asset_class`, `display_order`.

**GET /api/allocation/prior-views** — Prior-quarter views:
`opportunity_set`, `quarter`, `previous_quarter`, `view` (`UW` / `N` / `OW`),
`conviction` (`LOW` / `MEDIUM` / `HIGH`). Multiple quarters returned; filter to the
`prior_quarter` declared in the task request.

**GET /api/macro-signals** — Current-quarter signal scores:
`opportunity_set`, `quarter`, `score` (float), `rationale_code`, `drivers`.
Filter to the `target_quarter` declared in the task request.

### Market Endpoints

**GET /api/market/energy** — Energy market signals: `as_of_date`, `pitch_themes`,
`signals` (array of `{signal_id, commodity, direction, score, summary}`).

### Catalog

**GET /api/catalog** — Lists all available `bond_instrument_ids`, `index_ids`,
`issuer_ids`, `opportunity_sets`, `policy_ids`, `portfolio_ids`.

### Data Precedence Rule

The environment service is the authoritative book of record. Local payloads
(desk_request, review_request, etc.) are intake context only and may contain
stale marks, worksheet snapshots, or preferences from earlier dates. Always
reconcile local payload data against the current API responses. When local
payload values conflict with current API data, prefer the API.

The current `as_of_date` for portfolio, bond, issuer, policy, market, and
allocation data is visible in every API response.

### Common IDs Across Tasks

**Portfolio IDs and their default policies:**
- `PF-EN-ALTA` → `POL_CREDIT_DEFAULT` (energy credit carry)
- `PF-INT-NEXVEN` → `POL_CORRELATION_DEFAULT` (non-US equity correlation)
- `PF-FI-LUMEN` → `POL_CREDIT_RISK_REDUCTION` (credit risk rebalance)
- `PF-MA-HELIO` → `POL_MULTI_ASSET_DEFAULT` (multi-asset committee)

**Watchlisted issuers:** `ISS_DRIFTWOOD`, `ISS_JUNIPER_TEL`, `ISS_PACIFIC_REFIN`
