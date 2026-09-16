---
name: asteria-portfolio-analyst
description: Solve Asteria Investment Office portfolio tasks using the shared environment API. Handles credit trade selection, equity correlation reviews, allocation views, fixed-income risk rebalancing, and multi-asset committee memos. Follow strict JSON output templates and always prefer current environment data over stale local payloads.
---

# Asteria Portfolio Analyst

Use the shared Asteria Investment Office environment service at the base URL
provided in the task description or `environment_access.md`. All portfolio,
instrument, issuer, index, and policy records come from that live service.
Local payloads provide intake context (request parameters, template shapes,
and stale worksheet notes) but must not be treated as the current book of
record. Always prefer the current environment response over any stale local
snapshot when the two conflict.

## Environment

Base URL is read from the task-supplied `environment_access.md` or the task
prompt itself. The service uses no authentication. Allowed endpoints:

| Method | Path | Purpose |
|--------|------|---------|
| GET | `/` | Service root / health ping |
| GET | `/api/health` | Health check |
| GET | `/api/portfolios` | List all portfolios |
| GET | `/api/portfolios/{portfolio_id}/holdings` | Current holdings for a portfolio |
| GET | `/api/instruments/bonds` | Bond instrument master |
| GET | `/api/issuers` | Issuer metadata (sector, subsector, ratings, watchlist status) |
| GET | `/api/market/energy` | Energy market data linked to bonds |
| GET | `/api/indices` | Index metadata and identifiers |
| GET | `/api/index-levels` | Monthly index levels across all indices |
| GET | `/api/index-levels/{index_id}` | Monthly index levels for one index |
| GET | `/api/allocation/opportunity-sets` | Opportunity set taxonomy |
| GET | `/api/allocation/prior-views` | Prior-quarter allocation views |
| GET | `/api/macro-signals` | Macro signal scores for the current quarter |

## Core Principles

### Data Precedence

The environment service is the authoritative source. When a local payload
contains stale marks, snapshot dates, or unreconciled worksheets, discard
those values in favor of the current environment response. Set the answer
field `data_precedence` (or equivalent) to `current_environment_over_stale_payload`
whenever the template includes it.

Use local payloads only for: the request structure, the output template
contract, the list of instruments or opportunity sets to examine, and any
qualitative meeting context. Any quantitative field (market values, yields,
ratings, durations, allocation percentages, signal scores) must come from
the environment.

### Template Compliance

Every task includes an `answer_template.json` in its `input/payloads/`
directory. Read it before writing output. Follow it exactly:

- **Required keys**: Every key listed as required must appear. Top-level
  required keys are non-negotiable.
- **Enum values**: Use only the `allowed_values` listed. Never invent a
  value not present in the enum set.
- **Numeric precision**: Match the declared `precision` for every number.
  Values in the train answers use the declared precision exactly, e.g. 2
  decimals for percentages, 3 decimals for Pearson correlations, 1 decimal
  for USD millions.
- **Ordering**: Follow the ordering rules declared in the template (e.g.
  ascending by `instrument_id`, SELL before BUY, the order of the
  `focus_opportunity_sets` list from the payload).
- **Required values**: When a field has `required_value`, output that exact
  value (e.g. the `portfolio_id` field must match its `required_value` exactly).

### API Query Strategy

Query the environment in parallel whenever the endpoints are independent:

1. Portfolio holdings: `GET /api/portfolios/{id}/holdings` returns the
   current portfolio with each holding's `instrument_id`, `market_value_usd`,
   `quantity_usd_m`, `weight`, and `modified_duration_years`.

2. Bond instruments: `GET /api/instruments/bonds` returns all bonds with
   `instrument_id`, `issuer_id`, `coupon_rate_pct`, `maturity_date`,
   `yield_to_maturity_pct`, `modified_duration_years`, `rating`, `hy_flag`,
   `subsector`, and `watchlist_flag`.

3. Issuers: `GET /api/issuers` returns issuer-level metadata: `issuer_id`,
   `issuer_name`, `sector`, `subsector`, `rating`, `watchlist_flag`,
   `country`.

4. Index levels: `GET /api/index-levels/{index_id}` or the bulk
   `GET /api/index-levels` returns a list of objects with `index_id`,
   `level_date`, and `index_level`.

5. Macro signals: `GET /api/macro-signals` returns signal scores per
   opportunity set and per quarter. Each entry has `opportunity_set`,
   `quarter`, `signal_score`, and a `rationale_code` (or similar
   recommendation field).

6. Prior views: `GET /api/allocation/prior-views` returns the previous
   quarter's views (`UW`, `N`, `OW`) per opportunity set.

7. Opportunity sets: `GET /api/allocation/opportunity-sets` returns the
   taxonomy mapping `opportunity_set` to `asset_class` and other metadata.

8. Energy market: `GET /api/market/energy` returns energy-market context
   per instrument (used for credit desk energy-linked bond selection).

### Post-Trade Portfolio Math

When constructing buy/sell trade packages, compute post-trade metrics using
market-value-weighted formulas:

**Post-trade market value**:

```
post_mv = current_total_mv + sum(buys notional) - sum(sells notional)
```

Note: sells remove holdings. When selling an existing holding, the quantity
sold cannot exceed its current `market_value_usd` or `quantity_usd_m` in the
portfolio. The answer should reflect the actual quantity removed.

**Post-trade HY allocation percentage**:

```
post_hy_pct = 100 * (sum of post-trade market values of all HY-flagged holdings) / post_mv
```

Recompute by: take the current HY holdings, remove any HY holdings that are
sold (fully or partially), add any new HY buys, then divide by post_mv.

**HY reduction in percentage points**:

```
hy_reduction_ppt = current_hy_pct - post_hy_pct
```

**Post-trade weighted modified duration**:

```
post_dur = sum(holding_mv_i * holding_dur_i) / post_mv
```

for all holdings after trades. Use each bond's `modified_duration_years`
from the bond instrument master.

**Post-trade weighted YTM**:

```
post_ytm = sum(holding_mv_i * holding_ytm_i) / post_mv
```

### Constraint Checks

Every trade recommendation must pass or explicitly flag these constraints:

**HY cap**: The portfolio's post-trade HY allocation percentage must not
exceed the policy cap. Check the policy endpoint or infer from context
(train answers suggest a cap around 20-25%). Set `hy_cap_pass` to `true`
if post_trade_hy <= cap, `false` otherwise.

**Duration band**: The post-trade weighted modified duration must fall
within the CIO-approved band. When the task mentions a CIO range, check
that `post_trade_duration_years` is inside it. Set `duration_band_pass`
accordingly.

**Issuer diversification**: The selected instruments (buys) must not all
belong to the same issuer. At least two distinct issuers among the buys.
Set `selected_issuer_diversification_pass` accordingly.

**Subsector diversification**: The selected instruments must span at least
two different subsectors. Set `selected_subsector_diversification_pass`
accordingly.

**Watchlist avoidance**: No buy ticket may involve an instrument whose
issuer is on the watchlist. All sells of watchlisted instruments should be
flagged. Set `watchlist_avoidance_pass` to `true` only if zero buys touch
watchlisted issuers.

### Pearson Correlation from Monthly Index Levels

When a task requires Pearson correlation between two equity indices:

1. Query `GET /api/index-levels/{index_id}` for each index in the universe.
2. Filter to monthly level records whose `level_date` falls within the
   specified review window (inclusive of start and end).
3. Sort by `level_date` ascending.
4. Calculate simple monthly returns: `r_t = (level_t - level_{t-1}) / level_{t-1}`.
5. Compute the Pearson correlation coefficient from the paired return series:

```
r = sum((x_i - mean_x) * (y_i - mean_y)) / sqrt(sum((x_i - mean_x)^2) * sum((y_i - mean_y)^2))
```

6. Round to 3 decimal places.
7. The number of return observations is `(number of level records used) - 1`.

**Extreme pair identification** (for concentration/diversification tasks):

- `highest_positive`: Find the pair with the largest positive correlation.
  Break ties by alphabetical order of the pair id.
- `lowest`: Find the pair with the most negative (or smallest) correlation.
  Break ties by alphabetical order.
- When the task asks for `highest_concentration` and `best_diversifier`:
  highest concentration is the most positive correlation; best diversifier
  is the most negative (lowest) correlation.

**Concentration detection**:

- Flag `china_asia_dependence_flag` as `true` when the correlation between
  `IDX_CHINA` and `IDX_AC_ASIA_PAC_EX_JP` exceeds a high threshold (around
  0.85-0.90 based on train evidence).
- Set `primary_code` to `CHINA_ASIA_DEPENDENCE` when that pair dominates.
- Set `high_threshold_breached` to `true` when the relevant pair correlation
  exceeds the threshold.

### Allocation View Derivation

For each requested opportunity set:

1. Look up its `asset_class` from `/api/allocation/opportunity-sets`.
2. Look up the prior view from `/api/allocation/prior-views` for the prior
   quarter.
3. Look up the current macro signal score from `/api/macro-signals` for the
   target quarter and opportunity set.
4. Determine the view:
   - `signal_score > 0.3` suggests `OW` (overweight)
   - `signal_score < -0.3` suggests `UW` (underweight)
   - `-0.3 <= signal_score <= 0.3` suggests `N` (neutral)
   These thresholds are guidelines; the environment signal scores and
   rationale codes are the definitive source. When the environment provides
   explicit `rationale_code` values per opportunity set, use them directly.
5. Determine change versus prior:
   - If prior view is `N` and new view is `OW` -> `UP`
   - If prior view is `N` and new view is `UW` -> `DOWN`
   - If prior view is `OW` and new view is `UW` -> `DOWN`
   - If prior view is `UW` and new view is `OW` -> `UP`
   - If prior equals new -> `UNCHANGED`
6. Assign conviction:
   - `HIGH` when the absolute signal score is well above threshold and the
     direction is unambiguous.
   - `MEDIUM` when the signal is directional but moderate.
   - `LOW` when the signal is near zero or mixed.
7. Assign `rationale_code` from the environment's macro signals for that
   opportunity set; if not directly available, derive from the
   allowed_values list using the pattern of the signal direction.

### Risk Overlay Selection

When the task requires a portfolio-level risk overlay, select from the
template's `overlay_code_choices`. Derive by counting the dominant themes
across the allocation views:

- If multiple duration-support / rate-cut-support / quality-tilt signals
  dominate: `DURATION_QUALITY_TILT`
- If credit HY valuation risk signals dominate: `CREDIT_RISK_REDUCTION`
- If equity cyclical signals dominate: `EQUITY_BETA_EXTENSION`
- If dollar defensive / currency hedge signals dominate: `CURRENCY_DEFENSIVE_HEDGE`
- If no clear tilt: `NO_OVERLAY`

The `rationale_codes` list for the overlay should be the top rationale codes
from the allocation views that align with the overlay direction, ordered by
business priority (highest priority first).

### Combined Correlation and Allocation Integration
When a task combines correlation analysis and allocation views (committee pattern):

1. Compute the full pairwise correlation matrix for the requested index set
   using the 12-month monthly-level window.
2. Identify the highest-concentration pair and best-diversifier pair.
3. Derive sleeve actions (`trim`, `add`, `hold`, `hedge`) based on combined
   correlation + allocation view signals:
   - `trim` for opportunity sets with negative/bearish views and high
     concentration correlations.
   - `add` for opportunity sets with positive/bullish views and favorable
     diversification characteristics.
   - `hedge` for currency sleeves when the signal is defensive.
   - `hold` for neutral views with no concentration pressure.
4. Select `rebalance_trigger` from the template's enum:
   - `correlation_cap_breach` when a concentration pair exceeds the threshold
   - `committee_review` when this is a scheduled review with no breach
   - Other codes when those conditions are the primary driver.
5. Set `portfolio_risk_concentration_flag` to `true` when any concentration
   threshold is breached.
6. Set `next_step` based on the overall risk picture:
   - `approve_with_monitoring` when recommendations are moderate and
     constraints are satisfied.
   - `approve_rotation` when a clear rotation is warranted and passes checks.
   - `defer_pending_risk_review` when there is unresolved risk data.
   - `reject_constraint_breach` when a constraint is violated.

## Bond Selection for Credit Trade Packages
For credit trade packages that require buy tickets with income focus:
1. Query `/api/instruments/bonds` and `/api/issuers` and
   `/api/market/energy` to build the eligible bond universe.
2. Filter to energy-linked bonds (energy sector, LNG, gas, or relevant
   subsectors).
3. Exclude bonds whose issuer is on the watchlist.
4. Among remaining candidates, prefer bonds with higher YTM (better carry),
   IG rating (safer credit), and moderate duration.
5. Ensure issuer and subsector diversification among the selected buys.
6. Each BUY ticket notional must match the split requested in the desk
   request (total notional divided equally across the ticket count).
7. The `sales_positioning` fields:
   - `target_segment`: match the client context from the desk request
     (e.g. `multi_asset_income` for income-pitch tasks, `insurance_general_account` for liability-matching).
   - `theme`: select the best-fitting theme from the template enum. For
     LNG/gas-focused selections, `lng_export_tailwind`; for midstream
     bonds, `midstream_stability`; for cautionary contexts,
     `oil_oversupply_caution`; etc.

## Sleeve Action Derivation
For tasks that derive sleeve actions from correlation analysis:

1. Map each requested opportunity set or index to its sleeve name.
2. Determine action:
   - `trim` when the opportunity set/index has high concentration correlation
     with a dominant sleeve AND the allocation signal is bearish or the CIO
     concern memo flags concentration.
   - `add` when the opportunity set/index is a diversification candidate
     (low or negative correlation with the concentration pair) AND the
     allocation signal is supportive.
   - `hedge` for currency sleeves when the dollar is defensive.
   - `hold` or `monitor` when signals are neutral.
3. `target_index_id` must be one of the allowed values from the template.
4. Order sleeve actions as specified by the template.

## Exception Flags for FI Risk Rebalances
For fixed-income risk rebalance rotations:

1. Compute all post-trade risk metrics as described in "Post-Trade Portfolio
   Math" above.
2. Set exception flags:
   - `hy_cap_pass`: post-trade HY% <= policy cap
   - `duration_band_pass`: post-trade duration within CIO range
   - `target_hy_reduction_met`: hy_reduction_ppt >= the minimum requested
     in the meeting memo
   - `watchlist_exposure_cleared`: post-trade watchlist exposure in USD m
     is zero or minimal
3. `watchlist_handling`:
   - `watchlist_sell_ids`: list of instrument_ids sold that were on the
     watchlist, in ascending alphabetical order.
   - `buys_avoid_watchlist`: `true` if no buy ticket involves a watchlisted
     issuer.
4. `risk_note_code`: Select the code that best characterizes the dominant
   risk factor addressed by the rotation:
   - `watchlist_concentration` when watchlist exposure was the primary driver
   - `hy_cap_pressure` when HY cap was the binding constraint
   - `duration_preservation` when duration maintenance shaped the picks
   - `carry_tradeoff` when carry sacrifice was noted
   - `no_action` when no material change was needed (rare in rebalance tasks)

## Common Output Conventions

- **Dates**: Always use `YYYY-MM-DD` format. The `as_of_date` should reflect
  the date of the current environment data used, not the stale local payload
  date.
- **JSON only**: Do not wrap the output in markdown code fences, commentary,
  or extra text unless the task explicitly asks for a narrative section.
- **Field ordering in lists**: Follow the template's declared ordering.
  When the template says "Sort ascending by instrument_id", do exactly that.
  When it says "SELL before BUY", group sells first.
- **Strings vs numbers**: Never quote numeric values. Booleans are
  unquoted `true`/`false`. All string fields use double quotes.
- **Empty or null**: The train answers never use `null`. If a field is
  required, it must be present with a valid value. Lists must not be empty
  unless the template allows it.

## Quick-Start Workflow

1. Read the task `prompt.txt` to understand the assignment and portfolio id.
2. Read every file under `input/payloads/` — especially
   `answer_template.json` for the output contract and the request/memo
   JSON for intake parameters.
3. If an `environment_access.md` (or similar) is provided, note the base URL.
4. Query all relevant environment endpoints in parallel:
   - Holdings for the target portfolio
   - Bond instrument master (if bond tasks)
   - Issuer master (if bond or credit tasks)
   - Index levels for all requested indices (if correlation tasks)
   - Macro signals and prior views (if allocation tasks)
   - Opportunity sets (if allocation tasks)
5. Compute derived values (correlations, post-trade metrics, signal-derived
   views).
6. Construct the output JSON conforming to every rule in the template.
7. Verify every required key, enum value, precision, and ordering rule
   before returning.
