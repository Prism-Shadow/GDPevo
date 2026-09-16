## Asteria Investment Office API Reference

Base URL: `http://task-env:9010/`

No authentication required. All endpoints return JSON.

### Discovery

- `GET /` — HTML landing page listing available endpoints
- `GET /api/catalog` — IDs for portfolios, policies, indices, issuers, bonds, opportunity sets

### Portfolio & Holdings

- `GET /api/portfolios` — All portfolio summaries with `as_of_date`, `constraint_policy_id`, `market_value_usd_m`
- `GET /api/portfolios/{portfolio_id}/holdings` — Holdings array: `instrument_id`, `quantity_usd_m`

### Instruments

- `GET /api/instruments/bonds` — Full bond universe: `instrument_id`, `issuer_id`, `rating_bucket` (IG/HY), `modified_duration_years`, `yield_to_maturity_pct`, `coupon_pct`, `spread_bps`, `maturity`, `sector`, `subsector`, `energy_linked` (boolean), `candidate` (boolean), `recommended_theme_tags`

### Issuers

- `GET /api/issuers` — Issuer research: `issuer_id`, `issuer_name`, `rating_bucket`, `credit_outlook`, `sector`, `subsector`, `watchlist` (boolean), `research_tags`

### Market Signals

- `GET /api/market/energy` — Energy commodity signals with `signal_id`, `score`, `direction`, `pitch_themes`

### Indices & Levels

- `GET /api/indices` — Index metadata: `index_id`, `display_name`, `region`, `level_start_date`, `level_end_date`
- `GET /api/index-levels` — All index levels (date-ordered arrays)
- `GET /api/index-levels/{index_id}` — Single-index levels

Level objects: `{ "date": "YYYY-MM-DD", "level": number }` covering 12 monthly observations (2025-05-30 through 2026-04-30).

### Allocation

- `GET /api/allocation/opportunity-sets` — Taxonomy with `opportunity_set`, `asset_class`, `display_order`
- `GET /api/allocation/prior-views` — Prior-quarter views (`view`, `conviction`, `previous_quarter`)
- `GET /api/macro-signals` — Signal scores per opportunity-set per quarter: `score`, `rationale_code`, `drivers`

### Policies

- `GET /api/policies` — All constraint policies in one document keyed by policy type:
  - `POL_ALLOCATION_MAPPING` — View-to-score mapping thresholds
  - `POL_CORRELATION_DEFAULT` — Correlation thresholds, review window dates
  - `POL_CREDIT_DEFAULT` — Credit constraints (HY cap 20%, duration 3-5 yr band, issuer limit 12%, subsector min 2)
  - `POL_CREDIT_RISK_REDUCTION` — Same as CREDIT_DEFAULT but with `target_hy_reduction_pct: 4.0`
  - `POL_MULTI_ASSET_DEFAULT` — Composes allocation_mapping + correlation_default + credit_default
  - `POL_MULTI_ASSET_RISK` — Composes correlation_default + credit_risk_reduction

### Data Precedence

The API (`current_environment`) always takes precedence over stale local payloads. When the API `as_of_date` is later than a local payload date, use API values. Report `data_precedence` as `"current_environment_over_stale_payload"` when they conflict.
