# Asteria Environment API Reference

Base URL: read from the task's `environment_access.md`. The default is `http://task-env:9010/`.

No authentication required.

## Endpoint catalog

### GET /

HTML landing page listing all endpoints. Use for discovery.

### GET /api/catalog

Returns ids for all available portfolios, policies, indices, issuers, bonds, and opportunity sets.

```json
{
  "portfolio_ids": ["PF-EN-ALTA", ...],
  "policy_ids": ["POL_ALLOCATION_MAPPING", "POL_CORRELATION_DEFAULT", ...],
  "index_ids": ["IDX_ACWI_IMI", ...],
  "issuer_ids": ["ISS_AURORA_EN", ...],
  "bond_instrument_ids": ["BND_AURORA_2029", ...],
  "opportunity_sets": ["U.S. Large Cap", ...]
}
```

### GET /api/portfolios

List all portfolios with summary metadata. Each entry:

| Field | Type | Description |
|-------|------|-------------|
| portfolio_id | string | Primary key |
| name | string | Display name |
| market_value_usd_m | number | Current total market value in USD millions |
| base_currency | string | Always "USD" |
| holding_count | integer | Number of holdings |
| strategy | string | Investment strategy description |
| objective | string | Objective statement |
| constraint_policy_id | string | Linked constraint policy |
| as_of_date | string | YYYY-MM-DD date of portfolio snapshot |

### GET /api/portfolios/{portfolio_id}

Same as above plus full holdings list and constraint details.

Each holding:

| Field | Type | Description |
|-------|------|-------------|
| instrument_id | string | Index or bond identifier |
| asset_class | string | "Fixed Income" or "Equity" |
| sleeve | string | Descriptive sleeve name |
| quantity_usd_m | number | Market value in USD millions |
| notes | string | Comment |

Constraint block includes:
- `max_hy_allocation_pct` (number, percent)
- `duration_band_years` ([min, max], years)
- `correlation_high_threshold` (number, for correlation reviews)
- `correlation_low_threshold` (number)
- `policy_id` (string)
- `target_hy_reduction_pct` (number, for risk-reduction policies)

### GET /api/portfolios/{portfolio_id}/holdings

Same holdings/constraints block as above, returned directly.

### GET /api/instruments/bonds

Full bond universe (held and candidate). Each bond:

| Field | Type | Description |
|-------|------|-------------|
| instrument_id | string | BND_{ISSUER}_{MATURITY} |
| issuer_id | string | ISS_{ISSUER} |
| issuer_name | string | Display name |
| coupon_pct | number | Coupon rate in percent |
| yield_to_maturity_pct | number | Current YTM in percent |
| spread_bps | number | Spread over benchmark in basis points |
| rating | string | S&P-style rating (e.g., BBB-, B+) |
| rating_bucket | string | "IG" or "HY" |
| sector | string | Broad sector |
| subsector | string | Sub-sector |
| maturity | string | YYYY-MM-DD |
| modified_duration_years | number | Modified duration in years |
| energy_linked | boolean | Whether energy exposed |
| candidate | boolean | Whether eligible for new trades |
| recommended_theme_tags | list[string] | Desk tags |

### GET /api/issuers

Issuer-level records. Each issuer:

| Field | Type | Description |
|-------|------|-------------|
| issuer_id | string | ISS_{NAME} |
| issuer_name | string | Display name |
| rating_bucket | string | "IG" or "HY" |
| sector | string | Sector |
| subsector | string | Sub-sector |
| credit_outlook | string | "stable", "positive", "negative" |
| watchlist | boolean | Whether on risk watchlist |
| research_tags | list[string] | Research descriptor tags |

### GET /api/market/energy

Current energy market signals.

| Field | Type | Description |
|-------|------|-------------|
| as_of_date | string | YYYY-MM-DD |
| pitch_themes | list[string] | Marketing themes |
| signals | list[object] | Commodity signal list |
| signals[].commodity | string | Commodity name |
| signals[].direction | string | "positive", "negative", "neutral_to_positive" |
| signals[].score | number | -1 to +1 signal score |
| signals[].signal_id | string | Signal identifier |
| signals[].summary | string | One-line summary |
| stale_data_warning | string | Cutoff reminder |

### GET /api/indices

Index metadata list. Each index:

| Field | Type | Description |
|-------|------|-------------|
| index_id | string | IDX_{NAME} |
| display_name | string | Display name |
| currency | string | Always "USD" |
| frequency | string | "monthly" |
| region | string | Region |
| level_start_date | string | Earliest available date |
| level_end_date | string | Latest available date |

### GET /api/index-levels

All index levels for all indices, keyed by index_id. Each index entry is a list of date/level objects.

| Field | Type | Description |
|-------|------|-------------|
| date | string | YYYY-MM-DD month-end date |
| level | number | Index level |

### GET /api/index-levels/{index_id}

Levels for a single index, same format wrapped as `{"index_id": "...", "levels": [...]}`.

### GET /api/allocation/opportunity-sets

Full opportunity set taxonomy.

| Field | Type | Description |
|-------|------|-------------|
| opportunity_set | string | Name |
| asset_class | string | "Equities", "Duration", "Credit", "Currency" |
| sub_asset_class | string | Same or narrower |
| display_order | integer | Sort order |

### GET /api/allocation/prior-views

Prior-quarter views for all opportunity sets, including future quarters. Each record:

| Field | Type | Description |
|-------|------|-------------|
| opportunity_set | string | Name |
| quarter | string | "QN_YYYY" |
| previous_quarter | string | Prior quarter |
| view | string | "UW", "N", "OW" |
| conviction | string | "LOW", "MEDIUM", "HIGH" |

Filter to rows where `quarter` matches the target and `previous_quarter` matches the prior quarter.

### GET /api/macro-signals

Current-quarter signal scores for all opportunity sets. Each record:

| Field | Type | Description |
|-------|------|-------------|
| opportunity_set | string | Name |
| quarter | string | Target quarter |
| rationale_code | string | Signal rationale |
| score | number | -1 to +1 signal score |
| drivers | list[string] | Factor driver labels |

### GET /api/policies

Complete policy bundle keyed by component policy IDs plus a `policy_id` field for the overall policy set. Contains:

- `allocation_mapping`: view score thresholds (`OW_min`, `UW_max`, neutral band), conviction thresholds (`HIGH_abs_min`, `MEDIUM_abs_min`, `LOW_abs_below`), view rank mapping.
- `correlation`: correlation thresholds, review window dates.
- `credit_default`: HY cap, duration band, issuer concentration limit, subsector diversification minimum.
- `credit_risk_reduction`: same plus target HY reduction.
- `multi_asset`: references which sub-policies are inherited.
- `multi_asset_risk`: same plus committee escalation threshold.
