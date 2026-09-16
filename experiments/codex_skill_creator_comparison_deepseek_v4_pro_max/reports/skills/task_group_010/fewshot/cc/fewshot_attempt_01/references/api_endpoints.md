# Asteria Investment Office API Catalog

Base URL: `http://task-env:9010/`

No authentication required. All responses are JSON.

## Portfolio endpoints

### GET /api/portfolios
Returns a list of all portfolios. Each entry includes:
- `portfolio_id`, `name`, `strategy`, `objective`
- `as_of_date` — current environment date; use this in answers
- `market_value_usd_m`, `holding_count`, `constraint_policy_id`

### GET /api/portfolios/{portfolio_id}
Returns the portfolio summary plus current holdings. Each holding has:
- `instrument_id`, `quantity_usd_m`, `asset_class`, `sleeve`, `notes`

The response also includes `constraints` with `policy_id`, `max_hy_allocation_pct`,
and `duration_band_years`.

### GET /api/portfolios/{portfolio_id}/holdings
Returns just the holdings array. Useful for post-trade metric recomputation.

## Instrument endpoints

### GET /api/instruments/bonds
The full bond universe (both held and candidate-only). Each bond has:
- `instrument_id`, `issuer_id`, `issuer_name`
- `rating`, `rating_bucket` (`IG` or `HY`)
- `candidate` — true if available for new positions
- `modified_duration_years`, `yield_to_maturity_pct`, `coupon_pct`
- `sector`, `subsector`
- `energy_linked` — true if the bond is energy-linked
- `recommended_theme_tags` — desk tags (e.g., `WATCHLIST_RISK`, `LNG_EXPORTS`)
- `maturity`, `spread_bps`

Important: the `recommended_theme_tags` on bonds may include `WATCHLIST_RISK`
as a desk tag, but the authoritative watchlist record is the `watchlist` boolean
on the issuer in `/api/issuers`. Always cross-check both when watchlist avoidance
is required.

## Issuer endpoints

### GET /api/issuers
Issuer research records. Each issuer has:
- `issuer_id`, `issuer_name`
- `rating_bucket`, `sector`, `subsector`
- `credit_outlook` — `stable`, `positive`, or `negative`
- `research_tags` — analyst tags (e.g., `DOWNGRADE_RISK`, `LNG_CONTRACTS`)
- `watchlist` — boolean; this is the authoritative field for watchlist status

## Index endpoints

### GET /api/indices
List of all indices with metadata: `index_id`, `display_name`, `region`,
`frequency`, `level_start_date`, `level_end_date`.

### GET /api/index-levels
All index levels for all indices in one response. Each key is an index_id;
each value is an array of `{date, level}` objects covering
2025-05-30 through 2026-04-30, all at month-end.

### GET /api/index-levels/{index_id}
Levels for a single index. Use when you only need a subset of the index universe.

## Policy endpoints

### GET /api/policies
The full policy document. Key sub-objects:

- `credit_default` — `POL_CREDIT_DEFAULT`: HY cap 20%, duration band [3.0, 5.0],
  issuer limit 12%, subsector min 2, target HY reduction 0%.
- `credit_risk_reduction` — `POL_CREDIT_RISK_REDUCTION`: same thresholds except
  target HY reduction is 4.0 pct points.
- `correlation` — `POL_CORRELATION_DEFAULT`: high_threshold 0.8,
  low_threshold 0.2.
- `allocation_mapping` — `POL_ALLOCATION_MAPPING`: view thresholds (OW ≥ 0.35,
  UW ≤ -0.35, neutral between), conviction thresholds (HIGH ≥ 0.7, MEDIUM ≥ 0.35).
- `multi_asset` — references `allocation_mapping`, `correlation_default`, and
  `credit_default`.
- `multi_asset_risk` — references `correlation_default` and `credit_risk_reduction`.

The top-level `as_of_date` is the current policy date. The top-level `policy_id`
(e.g., `POLICY_SET_2026_05`) is the policy set identifier for lineage fields.

## Market endpoints

### GET /api/market/energy
Current energy market signals. Returns `as_of_date`, `signals` (array with
`signal_id`, `commodity`, `direction`, `score`, `summary`), and `pitch_themes`.

### GET /api/macro-signals
Quarterly macro signal scores per opportunity set. Each entry has:
- `opportunity_set`, `quarter`, `score`, `rationale_code`, `drivers`

## Allocation endpoints

### GET /api/allocation/opportunity-sets
The full opportunity-set taxonomy. Each entry has:
- `opportunity_set`, `asset_class`, `sub_asset_class`, `display_order`

### GET /api/allocation/prior-views
Prior-quarter allocation views. Each entry has:
- `opportunity_set`, `quarter`, `previous_quarter`, `view`, `conviction`

## Catalog

### GET /api/catalog
Aggregate listing of all IDs: `portfolio_ids`, `bond_instrument_ids`,
`index_ids`, `issuer_ids`, `opportunity_sets`, `policy_ids`.
