# Asteria Investment Office API Reference

Base URL: http://task-env:9010/

No authentication required. All endpoints return JSON arrays or objects.

## Endpoints

### GET /api/catalog
Returns a master listing of all available identifiers:
- bond_instrument_ids: all bond instrument IDs
- index_ids: all equity index IDs
- issuer_ids: all issuer IDs
- opportunity_sets: all allocation opportunity set names
- policy_ids: all policy IDs
- portfolio_ids: all portfolio IDs

### GET /api/portfolios
Returns an array of portfolio summary objects. Each object has:
- portfolio_id, name, strategy, objective
- as_of_date: current record date (YYYY-MM-DD)
- base_currency: "USD"
- market_value_usd_m: total market value in USD millions
- holding_count: number of holdings
- constraint_policy_id: the policy governing this portfolio

### GET /api/portfolios/{portfolio_id}/holdings
Returns the current holdings for one portfolio:
- as_of_date, base_currency, portfolio_id
- holdings: array of {asset_class, instrument_id, notes, quantity_usd_m, sleeve}

### GET /api/instruments/bonds
Returns all 27 bonds in the universe (held and candidate):
- instrument_id, issuer_id, issuer_name
- coupon_pct, maturity, modified_duration_years
- rating (e.g. "A-", "BBB", "BB-", "B+"), rating_bucket ("IG" or "HY")
- yield_to_maturity_pct, spread_bps
- sector, subsector
- energy_linked: boolean
- candidate: boolean (true means available for new buys)
- recommended_theme_tags: array of theme strings

### GET /api/issuers
Returns all 18 issuers:
- issuer_id, issuer_name
- rating_bucket ("IG" or "HY")
- sector, subsector
- credit_outlook: "stable", "positive", or "negative"
- watchlist: boolean
- research_tags: array of strings

### GET /api/market/energy
Returns current energy market signals:
- as_of_date
- pitch_themes: array of theme strings
- signals: array of {commodity, direction, score, signal_id, summary}
- stale_data_warning: timestamp threshold

### GET /api/indices
Returns all 14 equity indices:
- index_id, display_name, region, currency
- frequency: "monthly"
- level_start_date, level_end_date

### GET /api/index-levels
Returns levels for all indices. Each entry: {index_id, levels: [{date, level}]}

### GET /api/index-levels/{index_id}
Returns levels for one index: {index_id, levels: [{date, level}]}

### GET /api/policies
Returns the composite policy object:
- policy_id: "POLICY_SET_2026_05"
- as_of_date: "2026-05-29"
- allocation_mapping: {policy_id, view_rank, view_score_thresholds, conviction_thresholds}
- correlation: {policy_id, review_window_start, review_window_end, correlation_high_threshold, correlation_low_threshold}
- credit_default: {policy_id, max_hy_allocation_pct, duration_band_years, issuer_concentration_limit_pct, subsector_min_count_for_diversified, target_hy_reduction_pct}
- credit_risk_reduction: same shape as credit_default but with target_hy_reduction_pct=4.0
- multi_asset: {policy_id, uses_allocation_mapping, uses_correlation_default, uses_credit_default}
- multi_asset_risk: {policy_id, uses_correlation_default, uses_credit_risk_reduction, committee_escalation_threshold}

### GET /api/allocation/opportunity-sets
Returns 25 opportunity sets:
- opportunity_set, asset_class, sub_asset_class, display_order

### GET /api/allocation/prior-views
Returns prior-quarter and target-quarter views:
- opportunity_set, quarter, previous_quarter, view, conviction

Filter by quarter and previous_quarter to find Q1_2026 prior views for Q2_2026.

### GET /api/macro-signals
Returns current-quarter signal scores:
- opportunity_set, quarter, score, rationale_code, drivers

Filter by quarter to get the target quarter's signals.
