# Asteria Investment Office — Operational Skill

## 1. Environment & Data Sources

**Base URL:** `GDPEVO_ENV_BASE_URL` (from environment_access.md). All data comes from the remote HTTP API at this URL. Never read local env source files or use localhost.

**Key endpoints:**
| Endpoint | Returns |
|---|---|
| `GET /api/catalog` | Directory of all available data |
| `GET /api/policies` | Policy thresholds (HY caps, duration bands, concentration limits) |
| `GET /api/portfolios` | List of all portfolios |
| `GET /api/portfolios/<id>` | Single portfolio: holdings, market values, current metrics |
| `GET /api/instruments/bonds` | Bond security master: YTM, modified duration, rating (IG/HY), issuer, sector/subsector, watchlist flag |
| `GET /api/issuers` | Issuer records: credit quality, watchlist status, sector |
| `GET /api/market/energy` | Energy-linked bond data (LNG, midstream, etc.) |
| `GET /api/indices` | Index metadata (name, region, asset class) |
| `GET /api/index-levels` | Monthly index levels (all indices) |
| `GET /api/index-levels/<id>` | Monthly levels for one index |
| `GET /api/allocation/opportunity-sets` | Taxonomy: opportunity set → asset class mapping |
| `GET /api/allocation/prior-views` | Prior-quarter allocation views per opportunity set |
| `GET /api/macro-signals` | Current macro signal scores per opportunity set |

**Workflow rule:** Always start by fetching the relevant endpoints to establish the current book of record. Use `requests` (Python) or `curl` — prefer Python for any calculation-heavy work.

## 2. Data Precedence Rule

**The live API always beats local payloads.** Every task provides a local request payload (`.json` in `input/payloads/`) that may contain stale marks, outdated holdings, or old preference lists. The local payload tells you *what* to compute, but current API data tells you *the values to use*.

- Portfolio holdings → use `GET /api/portfolios/<id>`, not stale snapshots
- Bond attributes (YTM, duration, rating, watchlist) → use `GET /api/instruments/bonds`, not desk labels
- Issuer status → use `GET /api/issuers`
- Prior views → use `GET /api/allocation/prior-views`
- Signal scores → use `GET /api/macro-signals`
- Policy thresholds → use `GET /api/policies`

When the API has fresher/different data than a local payload, set `"data_precedence": "current_environment_over_stale_payload"` in the output.

## 3. Correlation Calculations (Pearson, Monthly Simple Returns)

Used in equity correlation reviews and multi-asset committee tasks.

**Procedure:**
1. Fetch monthly index levels for the review window from `GET /api/index-levels`. The window is defined by `level_start_date` and `level_end_date`.
2. Compute monthly simple returns: `r_t = (level_t − level_{t−1}) / level_{t−1}`
3. If you have N level observations, you get N−1 return observations.
4. For each pair of indices, compute the **Pearson correlation coefficient** over the overlapping return series.
5. Round to **3 decimal places**.

**Pearson formula:**
```
r = Σ((x_i − x̄)(y_i − ȳ)) / sqrt(Σ(x_i − x̄)² × Σ(y_i − ȳ)²)
```

**Best diversifier** = the pair with the **lowest** (most negative) correlation.
**Highest concentration** = the pair with the **highest positive** correlation.

## 4. Portfolio Metrics — How to Compute

### Post-trade HY allocation (%)
```
HY_pct = (Σ MV of HY-rated holdings after trades) / (total portfolio MV after trades) × 100
```
Round to precision declared in the answer template (typically 2 decimal places).

### Weighted modified duration (years)
```
Wtd_Dur = Σ (MV_i / total_MV) × mod_duration_i
```
Each bond's modified duration comes from `GET /api/instruments/bonds`. Round to 2 decimals.

### Weighted yield to maturity (%)
```
Wtd_YTM = Σ (MV_i / total_MV) × YTM_i
```
Each bond's YTM comes from `GET /api/instruments/bonds`. Round to 2 decimals.

### Total market value (USD millions)
```
Total_MV = Σ market_value_i   (after applying all trades)
```
Round to template precision.

### HY reduction (percentage points)
```
HY_reduction = pre_trade_HY_pct − post_trade_HY_pct
```

### Watchlist exposure
Sum the market values (post-trade) of any holdings whose issuer is on the watchlist (from `GET /api/issuers`). Target: zero.

## 5. Allocation Views — View, Change, Conviction

### Signal score → View (UW / N / OW)
Derive from macro signal scores at `GET /api/macro-signals`:

| Signal score range | View |
|---|---|
| score ≥ +0.25 | OW (Overweight) |
| score ≤ −0.25 | UW (Underweight) |
| −0.25 < score < +0.25 | N (Neutral) |

The exact boundary may vary slightly; the principle is: strongly positive → OW, strongly negative → UW, near zero → N.

### View → Conviction (LOW / MEDIUM / HIGH)
Based on the **absolute value** of the signal score:

| \|Signal score\| | Conviction |
|---|---|
| ≥ 0.5 | HIGH |
| 0.25 to <0.5 | MEDIUM |
| < 0.25 | LOW |

### Change vs prior quarter (UP / DOWN / UNCHANGED)
Compare the **current view** to the **prior quarter's view** from `GET /api/allocation/prior-views`:

| Prior → Current | Change |
|---|---|
| N/OW → OW or UW → OW | UP (more bullish/overweight vs prior) |
| OW → UW or N → UW or UW → N | DOWN (less bullish / more bearish) |
| Same view | UNCHANGED |

**Important nuance:** The `change` field reflects directional momentum, not just a diff. If prior was N and current is OW, that's UP. If prior was OW and current is N, that's DOWN. If prior was N and current is UW, that's DOWN. UW → N is UP (less bearish).

### Rationale codes
Choose from the enum allowed in the answer template. Match the rationale to the signal direction and macro context:
- Positive equity signals → `GROWTH_IMPROVES`, `EUROPE_RECOVERY`, `INDIA_OFFSET`, `LATAM_DIVERSIFIER`
- Negative equity signals → `CHINA_DEPENDENCE`, `JAPAN_POLICY_RISK`
- Duration positive → `DURATION_SUPPORT`, `RATE_CUT_SUPPORT`
- Credit negative → `HY_VALUATION_RISK`, `CREDIT_SPREAD_RISK`
- Currency → `DOLLAR_DEFENSIVE`, `NEUTRAL_BALANCE`

### Risk overlay
Synthesize from the dominant themes across all allocation views:
- If OW duration + UW HY → `DURATION_QUALITY_TILT`
- If UW credit broadly → `CREDIT_RISK_REDUCTION`
- If broad equity OW → `EQUITY_BETA_EXTENSION`
- If defensive currency views → `CURRENCY_DEFENSIVE_HEDGE`
- If all neutral → `NO_OVERLAY`

The `rationale_codes` list should include the rationale codes that drove the overlay decision, ordered by business priority (highest priority first).

## 6. Trade Selection & Constraint Checks

### Bond eligibility for BUY
- Bonds must be **current** (not matured) as of the as_of_date
- Issuer must **not** be on the watchlist (check `GET /api/issuers`)
- Bond rating comes from `GET /api/instruments/bonds`
- For energy-linked tasks, bonds must appear in `GET /api/market/energy`
- Prefer bonds with higher YTM (carry) subject to constraints
- Diversify across issuers and subsectors

### Constraint checks (boolean flags)
- **HY cap:** Post-trade HY allocation % ≤ policy HY cap (from `GET /api/policies`)
- **Duration band:** Post-trade weighted modified duration within CIO min/max range (from policies)
- **Issuer diversification:** Selected BUY bonds must not share the same issuer
- **Subsector diversification:** Selected BUY bonds must be from different subsectors
- **Watchlist avoidance:** No BUY on any watchlisted issuer or bond

### Trade sorting
- **BUY-only packages:** Sort ascending by `instrument_id`
- **Mixed SELL/BUY rotations:** SELL entries first, then BUY entries; within each action group, sort ascending by `instrument_id`

## 7. Output Formatting Conventions

### Numeric precision — follow the template
Each answer template declares precision per field. Common defaults:
- `notional_usd_m` / `quantity_usd_m`: **1 decimal place**
- Percentages (`_pct`, `_pct_points`): **2 decimal places**
- Duration in years: **2 decimal places**
- Pearson correlation: **3 decimal places**
- Signal scores: **3 decimal places**
- Total market value: **2 decimal places**

### String ordering
- **Index IDs in pairs:** Alphabetically ascending (e.g., `["IDX_CHINA", "IDX_LATAM"]`)
- **Index sets:** Alphabetically ascending
- **Trade lists:** By action group then instrument_id ascending
- **Allocation views:** In the order specified by the request payload's `focus_opportunity_sets` array
- **Sleeve actions:** By the order specified in the template's `item_order`
- **Watchlist sell IDs:** Ascending instrument_id order

### Date format
All dates: `YYYY-MM-DD` string format. The `as_of_date` should be the date of the current environment data, not the request date.

### Task ID
When a template requires `task_id`, use the value from the template's `required_value` field.

### Return format
Return **only the JSON object**. No markdown fences, no commentary. The answer must validate against the answer template's schema.

## 8. Workflow Checklist

For any Asteria task, follow this sequence:

1. **Read the local payload** to understand the request (portfolio ID, window, focus sets, preferences).
2. **Read the answer template** to know the exact output shape, field names, and allowed enum values.
3. **Fetch current data from the API** — portfolio, bonds, issuers, policies, indices, signals, prior views, etc. — whatever the task needs.
4. **Compute** — correlations, portfolio metrics, views from signals, constraint checks.
5. **Assemble output** — fill every required field, order lists correctly, apply precision rules.
6. **Validate** — check that every enum value matches the template's allowed values, every boolean is `true`/`false` (not strings), and numeric precision matches the template.

## 9. Common Pitfalls

- **Using stale local data instead of API data.** Always refresh from the API. If the local payload says a bond has 10.0M and the portfolio API says 12.0M, use 12.0M and flag the precedence.
- **Wrong correlation direction for diversifier.** "Best diversifier" means LOWEST correlation, not highest negative absolute value. A correlation of −0.825 is a better diversifier than +0.100, but between −0.825 and +0.050, −0.825 is the best diversifier.
- **Including a pair against itself** in the correlation matrix. Exclude self-correlations (always 1.0) from the extreme-pair scan.
- **Reversing change direction.** When prior=N and current=UW, change is DOWN (became more bearish). When prior=UW and current=N, change is UP (became less bearish).
- **Forgetting to recompute post-trade metrics** — total MV must reflect trades: BUYs add to MV, SELLs subtract.
- **Exceeding template enum values.** Only use values listed in the answer template's `allowed_values` arrays — don't invent new ones.
- **Wrong ordering of trade lists.** SELL-before-BUY grouping only applies when the template explicitly says so; otherwise sort by instrument_id.
- **Misidentifying IG vs HY.** Check the bond's actual rating from the API, not the desk label in the local payload.
- **Forgetting that notional/quantity must match trade constraints.** If the desk says "exactly two BUY tickets totaling $8M split evenly," each must be exactly $4.0M.
- **Correlation rounding.** Always round to 3 decimal places for correlation values; 2 for most percentages and ratios.
