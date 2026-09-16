# Asteria API Endpoints

Base URL: `http://task-env:9010`

## Portfolio endpoints

### GET /api/portfolios

Returns a list of all portfolio summaries. Each summary includes:
- `portfolio_id`, `name`, `as_of_date`
- `base_currency`, `market_value_usd_m`, `holding_count`
- `constraint_policy_id` — links to the `/api/policies` section that governs this portfolio
- `objective`, `strategy`

### GET /api/portfolios/{portfolio_id}/holdings

Returns the current holdings for one portfolio:
- `portfolio_id`, `as_of_date`, `base_currency`
- `holdings` array: each item has `instrument_id`, `quantity_usd_m`, `sleeve`, `asset_class`, `notes`

Holdings may be equity index positions (`IDX_...`) or fixed-income bond positions (`BND_...`).

## Bond and issuer endpoints

### GET /api/instruments/bonds

Returns the full bond universe (held and candidate). Each bond:
- `instrument_id`, `issuer_id`, `issuer_name`
- `coupon_pct`, `yield_to_maturity_pct`, `spread_bps`
- `modified_duration_years`, `maturity`
- `rating`, `rating_bucket` (`"IG"` or `"HY"`)
- `sector`, `subsector`
- `candidate` (boolean — `true` if eligible for new purchases)
- `energy_linked` (boolean)
- `recommended_theme_tags` (array of strings)

### GET /api/issuers

Returns all issuer records:
- `issuer_id`, `issuer_name`
- `sector`, `subsector`, `rating_bucket`
- `credit_outlook` (`"positive"`, `"stable"`, `"negative"`)
- `watchlist` (boolean)
- `research_tags` (array)

## Index endpoints

### GET /api/indices

Returns metadata for all available indices:
- `index_id`, `display_name`, `region`, `currency`
- `frequency` (always `"monthly"`)
- `level_start_date`, `level_end_date`

### GET /api/index-levels

Returns all monthly levels for all indices in a single response. The response is a map keyed by `index_id`, each value an array of `{date, level}` objects.

### GET /api/index-levels/{index_id}

Returns monthly levels for a single index as an array of `{date, level}` objects.

## Market signals endpoint

### GET /api/market/energy

Returns current energy market signals:
- `as_of_date`, `source`
- `pitch_themes` (array)
- `signals` array: each has `signal_id`, `commodity`, `direction`, `score`, `summary`
- `stale_data_warning`

## Allocation endpoints

### GET /api/allocation/opportunity-sets

Returns the taxonomy of all opportunity sets:
- `opportunity_set`, `asset_class`, `sub_asset_class`, `display_order`

### GET /api/allocation/prior-views

Returns prior-quarter allocation views. Each record:
- `quarter`, `previous_quarter`
- `opportunity_set`, `view`, `conviction`

Filter to `quarter` = target quarter and `previous_quarter` = prior quarter.

### GET /api/macro-signals

Returns current macro signal scores. Each record:
- `quarter`, `opportunity_set`  
- `score` (float, signed)
- `rationale_code`, `drivers` (array)

Filter to `quarter` = target quarter.

## Policy endpoint

### GET /api/policies

Returns the combined policy document. Key sections:

- `policy_id` — top-level identifier (e.g. `"POLICY_SET_2026_05"`)
- `as_of_date`
- `credit_default` — for `POL_CREDIT_DEFAULT`:
  - `max_hy_allocation_pct`, `duration_band_years`, `issuer_concentration_limit_pct`, `subsector_min_count_for_diversified`, `target_hy_reduction_pct`
- `credit_risk_reduction` — for `POL_CREDIT_RISK_REDUCTION`:
  - Same fields as credit_default, with `target_hy_reduction_pct` ≥ 4.0
- `correlation` — for `POL_CORRELATION_DEFAULT`:
  - `correlation_high_threshold`, `correlation_low_threshold`, `review_window_start`, `review_window_end`
- `allocation_mapping` — for view derivation:
  - `view_score_thresholds`, `conviction_thresholds`, `view_rank`
- `multi_asset` — composite policy referencing credit_default + correlation + allocation_mapping
- `multi_asset_risk` — composite policy referencing credit_risk_reduction + correlation
