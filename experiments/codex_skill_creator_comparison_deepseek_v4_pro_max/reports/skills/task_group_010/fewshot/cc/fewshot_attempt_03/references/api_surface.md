# Asteria Investment Office API Reference

Base URL: `http://task-env:9010/` (no authentication required)

All endpoints return JSON arrays or objects. All timestamps and dates use UTC.

---

## GET /

HTML catalogue page. Lists all available endpoints. Use this to confirm the API
is running and discover new endpoints.

---

## GET /api/catalog

Returns a single JSON object listing every known identifier in the system:

| Field | Type | Description |
|-------|------|-------------|
| `portfolio_ids` | string[] | All portfolio IDs (e.g., `PF-EN-ALTA`, `PF-FI-LUMEN`) |
| `bond_instrument_ids` | string[] | All bond instrument IDs |
| `index_ids` | string[] | All equity index IDs |
| `issuer_ids` | string[] | All issuer IDs |
| `opportunity_sets` | string[] | All allocation opportunity-set names |
| `policy_ids` | string[] | All policy identifiers |

---

## GET /api/portfolios

Returns an array of portfolio summary objects:

| Field | Type | Description |
|-------|------|-------------|
| `portfolio_id` | string | Unique identifier |
| `name` | string | Human-readable name |
| `as_of_date` | string | Current data date (YYYY-MM-DD) |
| `base_currency` | string | Always `"USD"` |
| `market_value_usd_m` | number | Total market value in USD millions |
| `holding_count` | integer | Number of holdings |
| `constraint_policy_id` | string | Which policy this portfolio uses |
| `strategy` | string | Strategy description |
| `objective` | string | Portfolio objective |

---

## GET /api/portfolios/{portfolio_id}/holdings

Returns a single object with `portfolio_id`, `as_of_date`, `base_currency`, and
a `holdings` array. Each holding:

| Field | Type | Description |
|-------|------|-------------|
| `instrument_id` | string | Bond ID (`BND_*`) or index ID (`IDX_*`) |
| `quantity_usd_m` | number | Notional in USD millions |
| `sleeve` | string | Portfolio sleeve label |
| `notes` | string | Desk comment |
| `asset_class` | string | `"Fixed Income"` or `"Equity"` |

---

## GET /api/instruments/bonds

Returns an array of all bond instruments. Each bond:

| Field | Type | Description |
|-------|------|-------------|
| `instrument_id` | string | e.g., `BND_BLUEGAS_2030` |
| `issuer_id` | string | Links to `/api/issuers` |
| `issuer_name` | string | Human-readable issuer name |
| `candidate` | boolean | Whether this bond is eligible for new buys |
| `maturity` | string | Maturity date (YYYY-MM-DD) |
| `coupon_pct` | number | Coupon rate in percent |
| `yield_to_maturity_pct` | number | YTM in percent |
| `modified_duration_years` | number | Modified duration |
| `rating` | string | e.g., `BBB-`, `BB`, `A-` |
| `rating_bucket` | string | `"IG"` or `"HY"` |
| `spread_bps` | number | Spread in basis points |
| `sector` | string | GICS-like sector |
| `subsector` | string | Finer classification |
| `energy_linked` | boolean | Whether bond is energy-sector |
| `recommended_theme_tags` | string[] | Desk-recommended tags |

---

## GET /api/issuers

Returns an array of all issuer records. Each issuer:

| Field | Type | Description |
|-------|------|-------------|
| `issuer_id` | string | Links to bonds |
| `issuer_name` | string | Human-readable name |
| `watchlist` | boolean | **Critical**: true means avoid |
| `credit_outlook` | string | `"positive"`, `"stable"`, `"negative"` |
| `rating_bucket` | string | `"IG"` or `"HY"` |
| `sector` | string | Primary sector |
| `subsector` | string | Finer classification |
| `research_tags` | string[] | Analyst tags |

---

## GET /api/indices

Returns an array of all equity indices. Each index:

| Field | Type | Description |
|-------|------|-------------|
| `index_id` | string | e.g., `IDX_EM`, `IDX_CHINA` |
| `display_name` | string | Human-readable name |
| `level_start_date` | string | Earliest available level date |
| `level_end_date` | string | Latest available level date |
| `frequency` | string | `"monthly"` |
| `currency` | string | `"USD"` |
| `region` | string | Regional label |

---

## GET /api/index-levels/{index_id}

Returns the level array for a single index. An array of monthly level observations:

| Field | Type | Description |
|-------|------|-------------|
| `date` | string | Month-end date (YYYY-MM-DD) |
| `level` | number | Index level (float) |

Levels are month-end and span approximately 12 months (12 observations).

---

## GET /api/allocation/opportunity-sets

Returns the full taxonomy of allocation opportunity sets. Each entry:

| Field | Type | Description |
|-------|------|-------------|
| `opportunity_set` | string | e.g., `"Emerging Markets"`, `"U.S. Treasuries"` |
| `asset_class` | string | `"Equities"`, `"Duration"`, `"Credit"`, `"Currency"` |
| `sub_asset_class` | string | Usually same as opportunity_set |
| `display_order` | integer | Sort order |

---

## GET /api/allocation/prior-views

Returns an array of prior-quarter views across multiple quarters. Filter by
`previous_quarter` matching the prior quarter and by `opportunity_set` matching
focus sets. Each entry:

| Field | Type | Description |
|-------|------|-------------|
| `opportunity_set` | string | Matches opportunity-set taxonomy |
| `previous_quarter` | string | The prior quarter, e.g., `"Q1_2026"` |
| `quarter` | string | The target quarter, e.g., `"Q2_2026"` |
| `view` | string | `"OW"`, `"N"`, or `"UW"` |
| `conviction` | string | `"LOW"`, `"MEDIUM"`, or `"HIGH"` |

**Important**: the array contains entries for multiple quarters. When the task
targets Q2_2026 with prior Q1_2026, filter to entries where `quarter` is
`"Q2_2026"` and `previous_quarter` is `"Q1_2026"`.

---

## GET /api/macro-signals

Returns an array of signal records. Each entry:

| Field | Type | Description |
|-------|------|-------------|
| `opportunity_set` | string | Matches opportunity-set taxonomy |
| `quarter` | string | The target quarter, e.g., `"Q2_2026"` |
| `score` | number | Signal score (typically -1.0 to +1.0) |
| `rationale_code` | string | Pre-computed rationale code |
| `drivers` | string[] | Factor drivers |

**Rationale codes** (from the task environment):

| Code | Typical Score Direction | Meaning |
|------|------------------------|---------|
| `GROWTH_IMPROVES` | positive | Improving growth outlook |
| `RATE_CUT_SUPPORT` | positive | Rate cuts support the asset |
| `CREDIT_SPREAD_RISK` | negative | Credit spread widening risk |
| `DOLLAR_DEFENSIVE` | varies | USD as defensive currency |
| `CHINA_DEPENDENCE` | negative | China slowdown spillover |
| `LATAM_DIVERSIFIER` | positive | Latin America diversification |
| `INDIA_OFFSET` | positive | India domestic growth offset |
| `DURATION_SUPPORT` | positive | Duration benefits from rate cuts |
| `HY_VALUATION_RISK` | negative | High-yield valuations stretched |
| `EUROPE_RECOVERY` | positive | European recovery tailwind |
| `JAPAN_POLICY_RISK` | negative | BOJ normalization pressure |
| `NEUTRAL_BALANCE` | near-zero | Balanced risk/reward |

---

## GET /api/market/energy

Returns a single object with energy market context:

| Field | Type | Description |
|-------|------|-------------|
| `as_of_date` | string | Current data date |
| `source` | string | Sources attribution |
| `pitch_themes` | string[] | Current pitch themes (check for alignment) |
| `signals` | array | Per-commodity signal objects |
| `stale_data_warning` | string | Warning about stale worksheet data |

Each signal in the `signals` array:

| Field | Type | Description |
|-------|------|-------------|
| `signal_id` | string | Signal identifier |
| `commodity` | string | e.g., `"Global LNG"`, `"Brent crude"` |
| `direction` | string | e.g., `"positive"`, `"negative"` |
| `score` | number | Signal strength |
| `summary` | string | One-line narrative |

---

## GET /api/policies

Returns a single composite JSON object. The structure:

```json
{
  "as_of_date": "2026-05-29",
  "policy_id": "POLICY_SET_2026_05",
  "credit_default": { ... },
  "credit_risk_reduction": { ... },
  "correlation": { ... },
  "allocation_mapping": { ... },
  "multi_asset": { ... },
  "multi_asset_risk": { ... }
}
```

The top-level `policy_id` is the current policy-set identifier for lineage
fields.

### Credit Policies (`credit_default` and `credit_risk_reduction`)

| Field | Type | Description |
|-------|------|-------------|
| `policy_id` | string | e.g., `POL_CREDIT_DEFAULT` |
| `max_hy_allocation_pct` | number | HY cap (percent) |
| `duration_band_years` | number[2] | [min, max] duration band |
| `issuer_concentration_limit_pct` | number | Max single issuer % |
| `subsector_min_count_for_diversified` | integer | Min distinct subsectors |
| `target_hy_reduction_pct` | number | Desired HY reduction for risk-reduction policy |

### Correlation Policy (`correlation`)

| Field | Type | Description |
|-------|------|-------------|
| `policy_id` | string | `POL_CORRELATION_DEFAULT` |
| `correlation_high_threshold` | number | Pairs above this are concentration risk |
| `correlation_low_threshold` | number | Pairs below this are diversifiers |
| `review_window_start` | string | Level window start date |
| `review_window_end` | string | Level window end date |

### Allocation Mapping Policy (`allocation_mapping`)

| Field | Type | Description |
|-------|------|-------------|
| `policy_id` | string | `POL_ALLOCATION_MAPPING` |
| `view_score_thresholds.OW_min` | number | Score >= this -> OW |
| `view_score_thresholds.UW_max` | number | Score <= this -> UW |
| `view_score_thresholds.neutral_between` | number[2] | Range for N |
| `conviction_thresholds.HIGH_abs_min` | number | abs(score) >= this -> HIGH |
| `conviction_thresholds.LOW_abs_below` | number | abs(score) < this -> LOW |
| `conviction_thresholds.MEDIUM_abs_min` | number | In between -> MEDIUM |

### Multi-Asset Policies

`multi_asset` and `multi_asset_risk` are composites that reference which
sub-policies apply. The `multi_asset` policy uses `credit_default` + the
correlation policy + allocation mapping. The `multi_asset_risk` policy uses
`credit_risk_reduction` + the correlation policy.
