# Asteria Environment API Reference

Base URL: `http://task-env:9010/`

All endpoints return JSON. No authentication required.

---

## Endpoint details

### `GET /api/health`

Returns `{"status": "ok"}` when the service is running. Always call this first.

### `GET /api/portfolios`

Returns a list of portfolio objects. Each has at minimum:
- `portfolio_id` (string) — the identifier used throughout tasks (e.g., `PF-EN-ALTA`, `PF-FI-LUMEN`, `PF-INT-NEXVEN`, `PF-MA-HELIO`)
- `name` (string) — display name

### `GET /api/portfolios/{portfolio_id}/holdings`

Returns holdings for the given portfolio. The response typically includes:
- `as_of_date` (string, YYYY-MM-DD) — the current book-of-record date
- `holdings` (array) — each holding with:
  - `instrument_id` (string)
  - `market_value` / `market_value_usd` (number)
  - `quantity` / `notional_usd_m` (number)
  - `weight` (number, fraction of portfolio)
  - Classification fields such as `rating`, `subsector`, `issuer_id`, `duration`, `yield_to_maturity`, `watchlist`

### `GET /api/instruments/bonds`

Returns the bond security master. Each bond has:
- `instrument_id` (string) — e.g., `BND_BLUEGAS_2030`
- `issuer_id` (string)
- `subsector` (string) — e.g., `LNG`, `midstream`, `telecom`, `materials`, `chemicals`, `data_center`
- `rating` (string) — credit rating grade
- `watchlist` (boolean) — whether the instrument is under watch
- `coupon` (number, percent)
- `maturity` (string, YYYY-MM-DD)
- `modified_duration` (number, years)
- `yield_to_maturity` (number, percent)

### `GET /api/issuers`

Returns issuer records. Each issuer has:
- `issuer_id` (string)
- `name` (string)
- `domicile` (string)
- `credit_rating` (string)
- `watchlist` (boolean)

### `GET /api/market/energy`

Returns energy market data including benchmark prices, spreads, and forward curves.

### `GET /api/indices`

Returns index metadata. Each index has:
- `index_id` (string) — e.g., `IDX_EM`, `IDX_CHINA`, `IDX_LATAM`
- `name` (string)
- `region` (string)
- `asset_class` (string)

### `GET /api/index-levels`

Returns monthly index levels for all indices. Response structure:
- `levels` (object keyed by `index_id`) — each value is an array of `{date, level}` objects

### `GET /api/index-levels/{index_id}`

Returns monthly levels for a single index, same `{date, level}` array format.

### `GET /api/allocation/opportunity-sets`

Returns the opportunity-set taxonomy. Each entry has:
- `opportunity_set` (string) — e.g., `Emerging Markets`, `India`, `U.S. Treasuries`
- `asset_class` (string) — `Equities`, `Duration`, `Credit`, `Currency`

### `GET /api/allocation/prior-views`

Returns the prior-quarter views. Each entry has:
- `opportunity_set` (string)
- `quarter` (string) — e.g., `Q1_2026`
- `view` (string) — `UW`, `N`, or `OW`

### `GET /api/macro-signals`

Returns current macro signal scores. Each entry has:
- `opportunity_set` (string)
- `signal_score` (number) — positive = favorable, negative = unfavorable
- `quarter` (string) — the target quarter

### `GET /api/policies`

Returns policy records. Each policy has:
- `policy_id` (string) — e.g., `POLICY_SET_2026_05`
- `hy_cap_pct` (number) — maximum high-yield allocation allowed
- `duration_min_years` / `duration_max_years` (number) — CIO duration band
- Other constraint thresholds

---

## Common patterns

### Fetch and extract with Python

```bash
curl -s http://task-env:9010/api/portfolios/PF-EN-ALTA/holdings | python3 -c "
import sys, json
data = json.load(sys.stdin)
print(json.dumps(data, indent=2))
"
```

### Pipe into jq for field extraction

```bash
curl -s http://task-env:9010/api/instruments/bonds | python3 -c "
import sys, json
bonds = json.load(sys.stdin)
for b in bonds:
    print(b['instrument_id'], b['subsector'], b['rating'], b['yield_to_maturity'])
"
```

---

## Rating classification

Investment grade (IG) is typically BBB- and above. High yield (HY) is BB+ and below. When the environment data uses explicit `is_hy` or `rating_class` fields, prefer those. Otherwise derive from the rating string.

## Watchlist handling

Both instruments (`/api/instruments/bonds`) and issuers (`/api/issuers`) may carry a `watchlist` boolean. An instrument is watchlisted if either its own flag or its issuer's flag is true. For risk rebalance tasks, the goal is to sell watchlisted holdings and avoid buying any watchlisted instruments.
