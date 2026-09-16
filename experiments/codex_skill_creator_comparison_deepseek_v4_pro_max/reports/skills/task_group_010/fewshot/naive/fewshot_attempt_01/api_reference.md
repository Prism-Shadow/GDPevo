## API Reference

All endpoints at `http://task-env:9010/` are read-only GETs with no authentication.

### GET /api/health

Returns `{"status": "ok"}`. Use to confirm the environment is running.

### GET /api/portfolios

Returns an array of portfolio summary objects. Fields per portfolio:

| Field | Type | Description |
|---|---|---|
| `portfolio_id` | string | Portfolio identifier (e.g. `PF-EN-ALTA`) |
| `name` | string | Display name |
| `as_of_date` | string | Current environment date (YYYY-MM-DD) |
| `base_currency` | string | Always `USD` |
| `market_value_usd_m` | number | Total portfolio market value in USD millions |
| `holding_count` | integer | Number of holdings |
| `constraint_policy_id` | string | Policy ID linking to constraint rules |
| `objective` | string | Portfolio objective description |
| `strategy` | string | Strategy description |

### GET /api/portfolios/{portfolio_id}/holdings

Returns an object with `portfolio_id`, `as_of_date`, `base_currency`, and a `holdings` array:

| Field | Type | Description |
|---|---|---|
| `instrument_id` | string | Bond or index identifier |
| `asset_class` | string | `Fixed Income` or `Equity` |
| `quantity_usd_m` | number | Market value in USD millions |
| `sleeve` | string | Allocation sleeve name |
| `notes` | string | Short descriptor |

### GET /api/instruments/bonds

Returns an array of all bond instruments. Each bond:

| Field | Type | Description |
|---|---|---|
| `instrument_id` | string | Unique bond identifier |
| `issuer_id` | string | Links to `/api/issuers` |
| `issuer_name` | string | Issuer display name |
| `candidate` | boolean | Whether bond is eligible for purchase |
| `coupon_pct` | number | Coupon rate |
| `yield_to_maturity_pct` | number | Yield to maturity |
| `modified_duration_years` | number | Modified duration |
| `rating` | string | Credit rating (e.g. BBB, BB-, B+) |
| `rating_bucket` | string | `IG` or `HY` |
| `sector` | string | High-level sector |
| `subsector` | string | Detailed subsector |
| `spread_bps` | number | Spread in basis points |
| `energy_linked` | boolean | Whether bond is energy-linked |
| `recommended_theme_tags` | array of strings | Investment theme tags |
| `maturity` | string | Maturity date (YYYY-MM-DD) |

### GET /api/issuers

Returns an array of all issuers. Each issuer:

| Field | Type | Description |
|---|---|---|
| `issuer_id` | string | Unique issuer identifier |
| `issuer_name` | string | Display name |
| `credit_outlook` | string | `positive`, `stable`, or `negative` |
| `rating_bucket` | string | `IG` or `HY` |
| `watchlist` | boolean | Whether issuer is on the credit watchlist |
| `sector` | string | High-level sector |
| `subsector` | string | Detailed subsector |
| `research_tags` | array of strings | Credit research tags |

### GET /api/market/energy

Returns an object with energy market context:

| Field | Type | Description |
|---|---|---|
| `as_of_date` | string | Current environment date |
| `source` | string | Data source attribution |
| `stale_data_warning` | string | Warning about stale desk worksheets |
| `pitch_themes` | array of strings | Current pitch theme labels |
| `signals` | array of objects | Energy commodity signals. Each signal: `signal_id`, `commodity`, `direction`, `score`, `summary` |

### GET /api/indices

Returns an array of all equity indices. Each index:

| Field | Type | Description |
|---|---|---|
| `index_id` | string | Unique index identifier (e.g. `IDX_CHINA`) |
| `display_name` | string | Display name |
| `region` | string | Geographic region |
| `currency` | string | Always `USD` |
| `frequency` | string | `monthly` |
| `level_start_date` | string | Earliest available level date |
| `level_end_date` | string | Latest available level date |

### GET /api/index-levels/{index_id}

Returns an object with `index_id` and a `levels` array of `{date, level}` objects. Dates are month-end (YYYY-MM-DD). Levels are index point values.

### GET /api/allocation/opportunity-sets

Returns an array of all opportunity sets. Each:

| Field | Type | Description |
|---|---|---|
| `opportunity_set` | string | Set name (e.g. `Europe`, `Emerging Markets`) |
| `asset_class` | string | `Equities`, `Duration`, `Credit`, or `Currency` |
| `sub_asset_class` | string | Same as opportunity_set for equity sets |
| `display_order` | integer | Display sort order |

### GET /api/allocation/prior-views

Returns an array of prior-quarter views. Each:

| Field | Type | Description |
|---|---|---|
| `opportunity_set` | string | Set name |
| `quarter` | string | Target quarter (e.g. `Q2_2026`) |
| `previous_quarter` | string | Prior quarter (e.g. `Q1_2026`) |
| `view` | string | `OW`, `N`, or `UW` |
| `conviction` | string | `LOW`, `MEDIUM`, or `HIGH` |

Filter by the quarter pair matching your request. The environment may return views for multiple quarters.

### GET /api/macro-signals

Returns an array of macro signals. Each:

| Field | Type | Description |
|---|---|---|
| `opportunity_set` | string | Set name |
| `quarter` | string | Target quarter (e.g. `Q2_2026`) |
| `score` | number | Signal score, typically in [-1.0, 1.0] |
| `rationale_code` | string | Predefined rationale code |
| `drivers` | array of strings | Key drivers |

Filter by the quarter specified in the request. Use `rationale_code` directly in output.
