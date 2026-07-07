# Asteria Investment Office JSON Task Solver

## Purpose
Generate precise JSON decision files for portfolio management tasks against the Asteria shared environment. Tasks cover energy-credit trades, international equity correlation reviews, allocation desk responses, fixed-income risk rotations, and multi-asset committee packs.

## Prerequisites
- Environment base URL: `http://34.46.77.124:8010`
- Data is read-only via REST endpoints; no local env directories are used

## Step-by-Step Procedure

### 1. Read All Input Files
Read the task's `input/prompt.txt`, `input/payloads/*.json` (request packet and answer template).

**Critical:** The request packet (e.g., `desk_request.json`, `review_request.json`, `committee_request.json`) contains **specific numeric constraints** that override the general prompt:
- exact ticket counts and notionals
- allowed actions (e.g., `["BUY"]` only)
- target quarters and prior quarters
- specific index IDs or opportunity sets to include
- stale data warnings (flag these for `data_precedence`)

### 2. Fetch Live Data from the Shared Environment
Query these endpoints and cache results:

| Endpoint | Purpose |
|----------|---------|
| `/api/catalog` | Lists all portfolio, bond, index, issuer, policy IDs |
| `/api/portfolios/<portfolio_id>` | Current holdings, MV, constraints |
| `/api/instruments/bonds` | Bond universe with coupon, duration, YTM, rating bucket, sector, subsector, energy flag |
| `/api/issuers` | Issuer credit outlook, watchlist flag, sector/subsector |
| `/api/policies` | Constraint thresholds (HY cap, duration band, issuer concentration, allocation mapping thresholds) |
| `/api/indices` | Index metadata (frequency, date range) |
| `/api/index-levels/<index_id>` | Monthly levels for correlation calculations |
| `/api/allocation/prior-views` | Prior quarter views and convictions |
| `/api/allocation/opportunity-sets` | Valid opportunity set names |
| `/api/macro-signals` | Signal scores and rationale codes by quarter |
| `/api/market/energy` | Energy market signals (for energy-credit tasks) |

**Rule:** Always use the **current environment as-of date** from portfolio/policy records, not stale dates in request packets.

### 3. Perform Calculations

#### 3.1 Correlation (Equity Review Tasks)
- Use the **monthly simple return** series from consecutive index levels:
  ```
  return_t = (level_t - level_{t-1}) / level_{t-1}
  ```
- Compute **Pearson correlation** between return series.
- The standard 12-month window produces **11 return observations**.
- Sort index IDs alphabetically within each pair.
- Identify highest (concentration) and lowest (diversifier) correlation pairs.
- Compare against the `correlation_high_threshold` (typically 0.8) from policies.

#### 3.2 Portfolio Metrics (Fixed-Income / Energy-Credit Tasks)
For post-trade holdings, calculate:
- **Market value:** sum of all holding quantities
- **HY allocation %:** `sum(HY quantities) / MV * 100`
- **Weighted duration:** `sum(qty * modified_duration) / MV`
- **Weighted YTM:** `sum(qty * yield_to_maturity) / MV`
- **Issuer concentration:** group by `issuer_id`, check `max(qty) / MV * 100` against policy limit
- **Subsector diversification:** count distinct issuers per subsector, check against `subsector_min_count_for_diversified`
- **Watchlist exposure:** sum quantities for bonds whose issuer has `watchlist: true`

#### 3.3 Allocation Views (Multi-Asset / Desk Response Tasks)
Use the `allocation_mapping` policy thresholds:
- **View mapping:**
  - `score >= OW_min` → `OW`
  - `score <= UW_max` → `UW`
  - else → `N`
- **Conviction mapping:**
  - `|score| >= HIGH_abs_min` → `HIGH`
  - `|score| >= MEDIUM_abs_min` → `MEDIUM`
  - else → `LOW`
- **Change:** compare current mapped view against the **prior quarter view** from `/api/allocation/prior-views`.
  - Use the endpoint entries whose `quarter` equals the **task's target quarter**; these represent the prior quarter's views.
  - Rank: `UW=-1, N=0, OW=1`. Increase = `UP`, decrease = `DOWN`, same = `UNCHANGED`.
- **Rationale code:** use the `rationale_code` from the macro signal for the matching opportunity set and quarter.

### 4. Construct the Answer JSON
Follow the answer template schema **exactly**:

- **Required top-level keys:** include every key listed in `required` or `required_top_level_keys`.
- **Enum values:** use only the allowed values listed in the template.
- **Precision:** round numbers to the exact decimal places specified (e.g., `precision: 2` means exactly 2 decimal places).
- **Ordering rules:**
  - Instrument IDs: ascending alphabetical
  - Opportunity sets: ascending alphabetical or the explicit `item_order` in the template
  - Trades: SELL before BUY, then ascending by instrument_id
  - Watchlist sell IDs: ascending alphabetical
- **Pair ordering:** sort both index IDs alphabetically inside each pair list.
- **Booleans:** use JSON `true`/`false`, not strings.

### 5. Derive Policy-Driven Fields
- **Constraint flags:** compute from post-trade metrics against policy thresholds (HY cap, duration band, issuer limit, watchlist avoidance).
- **Rebalance trigger / risk note code:** choose the enum that best matches the primary risk identified (e.g., `correlation_cap_breach` when a pair exceeds the high threshold; `hy_cap_pressure` when HY exceeds cap; `watchlist_concentration` when watchlist exposure is present).
- **Data precedence:** when the request packet contains a stale snapshot that conflicts with live API data, set `data_precedence` to `current_environment_over_stale_payload`.
- **Sales positioning / overlay:** align with the dominant theme from macro signals or energy market signals (e.g., LNG tailwind, duration/quality tilt, credit risk reduction).

### 6. Validation Checklist
Before finalizing:
- [ ] Every required key is present at every nesting level
- [ ] All enum values match the template exactly
- [ ] Numbers are rounded to the specified precision
- [ ] Lists follow the required ordering rules
- [ ] Pairs/sets are sorted alphabetically where required
- [ ] `as_of_date` matches the current environment date, not stale request dates
- [ ] `portfolio_id` matches the template's `required_value`
- [ ] Trade counts and notionals match explicit request packet constraints

## Common Pitfalls
- **Ignoring request packet specifics:** A prompt may say "raise by ~10m" while the desk request specifies exactly 2 BUY tickets totaling 8.0m.
- **Wrong prior view source:** Do not search for a non-existent prior quarter in the API. The `prior-views` endpoint entries for the target quarter already encode the previous quarter's views.
- **Stale date usage:** Use the live portfolio `as_of_date` (typically `2026-05-29`) for the answer, not dates inside stale request packets.
- **Correlation using levels directly:** Always compute returns first, then correlate the return series.
- **Forgetting to sort:** Unsorted pairs, trades, or instrument lists often cause partial credit loss.
