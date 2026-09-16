# Asteria API Reference

Base URL: `http://task-env:9010/`
No authentication required.

Always use the live API as the official book of record. Local payload files
may contain stale marks or intake preferences that need reconciliation.

## Endpoints

### GET /

HTML landing page with endpoint listing and descriptions.

### GET /api/portfolios

Returns a JSON array of all portfolio summaries. Each entry:

```
{
  "portfolio_id": "string",
  "name": "string",
  "as_of_date": "YYYY-MM-DD",
  "base_currency": "USD",
  "market_value_usd_m": number,
  "holding_count": integer,
  "constraint_policy_id": "string",
  "strategy": "string",
  "objective": "string"
}
```

### GET /api/portfolios/{portfolio_id}

Returns one portfolio object with full holdings:

```
{
  "portfolio_id": "string",
  "name": "string",
  "as_of_date": "YYYY-MM-DD",
  "base_currency": "USD",
  "market_value_usd_m": number,
  "constraints": {
    "policy_id": "string",
    "max_hy_allocation_pct": number,
    "duration_band_years": [number, number],
    "target_hy_reduction_pct": number   (only for POL_CREDIT_RISK_REDUCTION)
  },
  "holdings": [
    {
      "instrument_id": "string",
      "asset_class": "string",
      "quantity_usd_m": number,
      "sleeve": "string",
      "notes": "string"
    }
  ],
  "strategy": "string",
  "objective": "string"
}
```

### GET /api/portfolios/{portfolio_id}/holdings

Lightweight version returning only the holdings array and `as_of_date`.

### GET /api/instruments/bonds

Returns a JSON array of all bonds in the universe (held and candidate). Each entry:

```
{
  "instrument_id": "string",
  "issuer_id": "string",
  "issuer_name": "string",
  "sector": "string",
  "subsector": "string",
  "coupon_pct": number,
  "maturity": "YYYY-MM-DD",
  "modified_duration_years": number,
  "rating": "string",
  "rating_bucket": "IG" | "HY",
  "spread_bps": integer,
  "yield_to_maturity_pct": number,
  "energy_linked": boolean,
  "candidate": boolean,
  "recommended_theme_tags": ["string"]
}
```

### GET /api/issuers

Returns a JSON array of all issuer records. Each entry:

```
{
  "issuer_id": "string",
  "issuer_name": "string",
  "rating_bucket": "IG" | "HY",
  "sector": "string",
  "subsector": "string",
  "credit_outlook": "stable" | "positive" | "negative",
  "watchlist": boolean,
  "research_tags": ["string"]
}
```

### GET /api/market/energy

Returns energy market signals:

```
{
  "as_of_date": "YYYY-MM-DD",
  "source": "string",
  "pitch_themes": ["string"],
  "signals": [
    {
      "signal_id": "string",
      "commodity": "string",
      "direction": "positive" | "neutral_to_positive" | "negative",
      "score": number (range ~[-1, 1]),
      "summary": "string"
    }
  ],
  "stale_data_warning": "string"
}
```

### GET /api/indices

Returns a JSON array of all equity index metadata. Each entry:

```
{
  "index_id": "string",
  "display_name": "string",
  "region": "string",
  "currency": "USD",
  "frequency": "monthly",
  "level_start_date": "YYYY-MM-DD",
  "level_end_date": "YYYY-MM-DD"
}
```

### GET /api/index-levels

Returns a JSON array of all index-level objects (one per index with full level
history). Same shape as `GET /api/index-levels/{index_id}` but for all indices.

### GET /api/index-levels/{index_id}

Returns one index with its monthly level history:

```
{
  "index_id": "string",
  "levels": [
    {"date": "YYYY-MM-DD", "level": number}
  ]
}
```

Levels are end-of-month values. To compute monthly simple returns:
`return_t = (level_t / level_{t-1}) - 1`

For a 12-month window with levels from date D[0] through D[11], there are 11
return observations (D[0] is the anchor level, D[1]/D[0] gives the first
return).

### GET /api/allocation/opportunity-sets

Returns all allocation taxonomy entries:

```
{
  "opportunity_set": "string",
  "asset_class": "Equities" | "Duration" | "Credit" | "Currency",
  "sub_asset_class": "string",
  "display_order": integer
}
```

### GET /api/allocation/prior-views

Returns prior-quarter views for all opportunity sets. Each entry:

```
{
  "opportunity_set": "string",
  "quarter": "Q?_2026",
  "previous_quarter": "Q?_2026",
  "view": "OW" | "N" | "UW",
  "conviction": "HIGH" | "MEDIUM" | "LOW"
}
```

Filter by `quarter` to get only the current quarter's prior-quarter records.
The `view` field on a Q2_2026 / previous_quarter Q1_2026 row is the Q1 view.

### GET /api/macro-signals

Returns current-quarter signal scores and rationale codes:

```
{
  "opportunity_set": "string",
  "quarter": "Q?_2026",
  "score": number (range ~[-1, 1]),
  "rationale_code": "string",
  "drivers": ["string"]
}
```

### GET /api/policies

Returns the full policy set with all sub-policies:

```
{
  "policy_id": "POLICY_SET_2026_05",
  "as_of_date": "YYYY-MM-DD",
  "allocation_mapping": {
    "policy_id": "POL_ALLOCATION_MAPPING",
    "view_score_thresholds": {
      "OW_min": 0.35,
      "UW_max": -0.35,
      "neutral_between": [-0.35, 0.35]
    },
    "conviction_thresholds": {
      "HIGH_abs_min": 0.70,
      "MEDIUM_abs_min": 0.35,
      "LOW_abs_below": 0.35
    },
    "view_rank": {"N": 0, "OW": 1, "UW": -1}
  },
  "correlation": {
    "policy_id": "POL_CORRELATION_DEFAULT",
    "correlation_high_threshold": 0.80,
    "correlation_low_threshold": 0.20,
    "review_window_start": "YYYY-MM-DD",
    "review_window_end": "YYYY-MM-DD"
  },
  "credit_default": {
    "policy_id": "POL_CREDIT_DEFAULT",
    "max_hy_allocation_pct": 20.0,
    "duration_band_years": [3.0, 5.0],
    "issuer_concentration_limit_pct": 12.0,
    "subsector_min_count_for_diversified": 2
  },
  "credit_risk_reduction": {
    "policy_id": "POL_CREDIT_RISK_REDUCTION",
    "max_hy_allocation_pct": 20.0,
    "duration_band_years": [3.0, 5.0],
    "target_hy_reduction_pct": 4.0,
    "issuer_concentration_limit_pct": 12.0,
    "subsector_min_count_for_diversified": 2
  },
  "multi_asset": {
    "policy_id": "POL_MULTI_ASSET_DEFAULT",
    "uses_allocation_mapping": true,
    "uses_correlation_default": true,
    "uses_credit_default": true
  },
  "multi_asset_risk": {
    "policy_id": "POL_MULTI_ASSET_RISK",
    "uses_correlation_default": true,
    "uses_credit_risk_reduction": true,
    "committee_escalation_threshold": "two_or_more_material_exceptions"
  }
}
```

Always read `/api/policies` to get the active `policy_id` and constraint
thresholds. The `as_of_date` on the policies response is the same canonical
date used throughout.

## Standard Enumeration Values

### Rebalance trigger codes
- `correlation_cap_breach`
- `hy_cap_pressure`
- `duration_drift`
- `watchlist_concentration`
- `committee_review`

### Sleeve action codes
- `trim`, `add`, `hold`, `hedge`, `monitor`, `rotate`

### Next step codes
- `approve_rotation`
- `defer_pending_risk_review`
- `approve_with_monitoring`
- `reject_constraint_breach`

### Sales positioning target segments
- `insurance_general_account`
- `pension_liability_matching`
- `multi_asset_income`
- `private_bank_income`
- `endowment_opportunistic`

### Sales positioning themes
- `lng_export_tailwind`
- `oil_oversupply_caution`
- `midstream_stability`
- `transition_bond_selectivity`
- `avoid_watchlist_yield_trap`

### Risk overlay codes
- `DURATION_QUALITY_TILT`
- `CREDIT_RISK_REDUCTION`
- `EQUITY_BETA_EXTENSION`
- `CURRENCY_DEFENSIVE_HEDGE`
- `NO_OVERLAY`

### Primary action codes
- `tilt_to_duration_quality`
- `trim_credit_beta`
- `add_cyclical_equity_beta`
- `add_currency_hedge`
- `hold_policy_weights`

### Risk note codes
- `hy_cap_pressure`
- `watchlist_concentration`
- `duration_preservation`
- `carry_tradeoff`
- `no_action`

### Allocation rationale codes
- `GROWTH_IMPROVES`
- `RATE_CUT_SUPPORT`
- `CREDIT_SPREAD_RISK`
- `DOLLAR_DEFENSIVE`
- `CHINA_DEPENDENCE`
- `LATAM_DIVERSIFIER`
- `INDIA_OFFSET`
- `DURATION_SUPPORT`
- `HY_VALUATION_RISK`
- `EUROPE_RECOVERY`
- `JAPAN_POLICY_RISK`
- `NEUTRAL_BALANCE`

### Concentration primary codes
- `CHINA_ASIA_DEPENDENCE`
- `GLOBAL_DEVELOPED_OVERLAP`
- `NO_MATERIAL_CONCENTRATION`

### Data precedence values
- `current_environment_over_stale_payload`
- `local_payload_over_current_environment`
- `no_conflict_found`
