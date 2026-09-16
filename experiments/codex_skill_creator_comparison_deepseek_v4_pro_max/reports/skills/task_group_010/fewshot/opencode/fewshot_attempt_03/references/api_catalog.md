# Asteria Environment API Catalog

Base URL: `http://task-env:9010/`

No authentication required. All endpoints are GET.

---

## Portfolios

### GET /api/portfolios

Returns all portfolio summaries.

Fields per portfolio:
- `portfolio_id` (string) — e.g. `"PF-EN-ALTA"`
- `as_of_date` (string, `YYYY-MM-DD`)
- `name` (string)
- `strategy` (string)
- `objective` (string)
- `base_currency` (string, always `"USD"`)
- `market_value_usd_m` (number)
- `holding_count` (integer)
- `constraint_policy_id` (string) — the policy to use for constraint checks

### GET /api/portfolios/{portfolio_id}/holdings

Returns a portfolio's current holdings.

Fields:
- `portfolio_id` (string)
- `as_of_date` (string)
- `base_currency` (string)
- `holdings` (array of objects):
  - `instrument_id` (string) — e.g. `"BND_AURORA_2029"`
  - `quantity_usd_m` (number)
  - `asset_class` (string)
  - `sleeve` (string)
  - `notes` (string)

---

## Bonds & Issuers

### GET /api/instruments/bonds

Returns the full bond universe.

Fields per bond:
- `instrument_id` (string) — primary key
- `issuer_id` (string) — FK to `/api/issuers`
- `issuer_name` (string)
- `candidate` (boolean) — true if eligible for new purchase
- `rating` (string) — e.g. `"BBB-"`, `"B+"`
- `rating_bucket` (string) — `"IG"` or `"HY"`
- `coupon_pct` (number)
- `yield_to_maturity_pct` (number)
- `modified_duration_years` (number)
- `spread_bps` (number)
- `maturity` (string, `YYYY-MM-DD`)
- `sector` (string)
- `subsector` (string)
- `energy_linked` (boolean)
- `recommended_theme_tags` (array of strings)

### GET /api/issuers

Returns all issuer research records.

Fields per issuer:
- `issuer_id` (string) — primary key
- `issuer_name` (string)
- `rating_bucket` (string) — `"IG"` or `"HY"`
- `sector` (string)
- `subsector` (string)
- `credit_outlook` (string) — `"positive"`, `"stable"`, `"negative"`
- `watchlist` (boolean)
- `research_tags` (array of strings)

---

## Equity Indices

### GET /api/indices

Returns index metadata for all indices.

Fields per index:
- `index_id` (string) — e.g. `"IDX_EM"`
- `display_name` (string)
- `region` (string)
- `currency` (string, always `"USD"`)
- `frequency` (string, always `"monthly"`)
- `level_start_date` (string, `YYYY-MM-DD`)
- `level_end_date` (string, `YYYY-MM-DD`)

### GET /api/index-levels

Returns level arrays for all indices in a single response. Each element is the
same shape as the per-index endpoint.

### GET /api/index-levels/{index_id}

Returns levels for a single index.

Fields:
- `index_id` (string)
- `levels` (array of `{date, level}`):
  - `date` (string, `YYYY-MM-DD`)
  - `level` (number)

---

## Allocation Framework

### GET /api/allocation/opportunity-sets

Returns the taxonomy of opportunity sets.

Fields per set:
- `opportunity_set` (string) — e.g. `"Emerging Markets"`, `"EUR"`
- `asset_class` (string) — `"Equities"`, `"Duration"`, `"Credit"`, `"Currency"`
- `display_order` (integer)
- `sub_asset_class` (string)

### GET /api/allocation/prior-views

Returns published views across quarters.

Fields per record:
- `quarter` (string) — the quarter the view belongs to, e.g. `"Q2_2026"`
- `previous_quarter` (string) — the prior quarter it was derived from, e.g. `"Q1_2026"`
- `opportunity_set` (string)
- `view` (string) — `"OW"`, `"N"`, `"UW"`
- `conviction` (string) — `"LOW"`, `"MEDIUM"`, `"HIGH"`

**Important filtering**: To find the prior views to compare against, query rows
where `quarter` equals the target quarter AND `previous_quarter` equals the
prior quarter. For example, for Q2_2026 deriving from Q1_2026, filter
`quarter == "Q2_2026" AND previous_quarter == "Q1_2026"`.

### GET /api/macro-signals

Returns signal scores and rationale codes.

Fields per record:
- `quarter` (string)
- `opportunity_set` (string)
- `score` (number, can be negative)
- `rationale_code` (string)
- `drivers` (array of strings)

---

## Energy Market

### GET /api/market/energy

Returns current energy market signals.

Fields:
- `as_of_date` (string)
- `source` (string)
- `stale_data_warning` (string)
- `pitch_themes` (array of strings)
- `signals` (array):
  - `signal_id` (string)
  - `commodity` (string)
  - `direction` (string)
  - `score` (number)
  - `summary` (string)

---

## Policies

### GET /api/policies

Returns a single JSON object with all policies and fragments.

Top-level fields:
- `policy_id` (string) — the current policy set identifier, e.g. `"POLICY_SET_2026_05"`
- `as_of_date` (string)

Sub-objects keyed by policy_id (or by function):
- `allocation_mapping` — view derivation thresholds
- `correlation` — correlation thresholds and review window
- `credit_default` — credit constraint thresholds
- `credit_risk_reduction` — credit constraint thresholds with HY reduction target
- `multi_asset` / `multi_asset_risk` — composite policy references

See [policy_thresholds.md](policy_thresholds.md) for the detailed field layout.
