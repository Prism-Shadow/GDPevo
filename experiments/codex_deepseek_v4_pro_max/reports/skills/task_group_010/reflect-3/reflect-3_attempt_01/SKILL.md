## When to use this skill

Use this skill when the task involves preparing institutional portfolio analytics or recommendation JSON files for the Asteria Investment Office. The skill covers energy-credit trade strategy, international equity correlation review, active allocation view refresh, fixed-income risk rebalance, and multi-asset committee decision support.

## Core workflow

### 1. Read the environment first

Always query the shared environment API before computing any answer. The environment is the current book of record; local payloads (desk requests, meeting memos, committee packets) provide context, preferences, and the answer template but may contain stale marks or outdated snapshots.

Start by reading these endpoints to understand available data:
- `GET /api/catalog` — lists all valid IDs for portfolios, bonds, issuers, indices, policies, and opportunity sets.
- `GET /api/policies` — constraint thresholds (HY cap, duration band, correlation high/low, issuer concentration limits, view-score thresholds, conviction thresholds) and the as-of date.
- `GET /api/portfolios` — summary of all portfolios including their constraint policy assignments.

### 2. Gather task-specific data

For **credit/fixed-income tasks**:
- `GET /api/portfolios/{id}/holdings` — current holdings with quantities and sleeves.
- `GET /api/instruments/bonds` — full bond universe: rating bucket (IG/HY), modified duration, YTM, subsector, issuer, energy-linked flag, candidate flag, watchlist-related theme tags.
- `GET /api/issuers` — watchlist status, credit outlook, research tags, sector, subsector.
- `GET /api/market/energy` — current commodity signals and pitch themes (for energy-credit tasks).

For **equity correlation tasks**:
- `GET /api/indices` — index metadata (region, frequency, level date range).
- `GET /api/index-levels/{index_id}` — monthly index levels for return calculations.
- `GET /api/portfolios/{id}/holdings` — current sleeve allocations to indices.

For **allocation view tasks**:
- `GET /api/allocation/opportunity-sets` — taxonomy mapping opportunity sets to asset classes.
- `GET /api/allocation/prior-views` — previously established views per quarter (use entries where `quarter` matches the target quarter).
- `GET /api/macro-signals` — signal scores, rationale codes, and conviction drivers for the target quarter.

### 3. Apply policy thresholds

Always look up the relevant policy for the portfolio (found in the portfolio summary's `constraint_policy_id` field) from `GET /api/policies`. Apply these rules:

**Credit policy** (`POL_CREDIT_DEFAULT` or `POL_CREDIT_RISK_REDUCTION`):
- `max_hy_allocation_pct` — high-yield cap (typically 20%).
- `duration_band_years` — acceptable duration range (typically [3.0, 5.0]).
- `issuer_concentration_limit_pct` — max per issuer (typically 12%).
- `subsector_min_count_for_diversified` — minimum distinct subsectors.

**Allocation mapping** (`POL_ALLOCATION_MAPPING`):
- `view_score_thresholds.OW_min` — scores at or above this → Overweight.
- `view_score_thresholds.UW_max` — scores at or below this → Underweight.
- `view_score_thresholds.neutral_between` — scores in this range → Neutral.
- `conviction_thresholds.HIGH_abs_min` — absolute score at or above this → HIGH conviction.
- `conviction_thresholds.LOW_abs_below` — absolute score below this → LOW conviction.
- Everything else → MEDIUM conviction.

**Correlation policy** (`POL_CORRELATION_DEFAULT`):
- `correlation_high_threshold` — pairs above this indicate concentration risk.
- `correlation_low_threshold` — pairs below this indicate diversification potential.

### 4. Compute numeric values correctly

**Weighted averages** (for portfolio duration, YTM, HY allocation):
```
weighted_metric = sum(quantity_i × metric_i for each holding) / total_market_value
```
Use exact API values; only round at the final step to the precision declared in the answer template.

**Pearson correlation** from monthly index levels:
```
monthly_simple_return_i = level_i / level_{i-1} - 1
```
Compute Pearson correlation over the resulting return series. The number of return observations equals (number of level dates − 1).

**HY allocation percentage**:
```
hy_pct = (sum of market values for all HY-rated holdings) / total_market_value × 100
```

### 5. Determine views from macro signals

For each opportunity set:
1. Look up the Q2_2026 (or appropriate quarter) signal score from `/api/macro-signals`.
2. Compare to allocation-mapping thresholds to determine `view` (OW / N / UW).
3. Compare to the prior quarter's view from `/api/allocation/prior-views` to determine `change` (UP / DOWN / UNCHANGED). Use the entry for the target quarter (e.g., entries with `quarter: "Q2_2026"`) as the prior established view.
4. Use the absolute signal score against conviction thresholds to determine `conviction` (LOW / MEDIUM / HIGH).
5. Use the `rationale_code` directly from the macro signal entry.

A view change of UNCHANGED is possible when the new signal-derived view matches the prior established view, even if the prior view was not Neutral.

### 6. Observe sort orders and precision

Answer templates specify ordering rules and numeric precision. Follow them exactly:
- Sort trade lists: SELL before BUY, then by `instrument_id` ascending within each action.
- Sort index lists alphabetically by ID.
- Sort index pairs alphabetically within each pair.
- Round numbers to the decimal places declared in the template (e.g., precision 2 for percentages, precision 3 for correlations).

### 7. Constraint checks and flags

After proposing trades or views, verify each constraint and set boolean flags accordingly:
- `hy_cap_pass` — post-trade HY% ≤ policy max.
- `duration_band_pass` — post-trade weighted duration within [min, max].
- `selected_issuer_diversification_pass` — selected (new) instruments are from different issuers.
- `selected_subsector_diversification_pass` — selected instruments are from different subsectors.
- `watchlist_avoidance_pass` / `watchlist_exposure_cleared` — no watchlist instruments in the final portfolio or new buys.
- `target_hy_reduction_met` — HY reduction in percentage points meets or exceeds the policy target.

### 8. Align qualitative fields with data

**Sales positioning**: Match `target_segment` to the client context in the task payload. Match `theme` to the strongest directional signal from the relevant market endpoint (e.g., for energy-credit tasks, use the commodity with the highest absolute score from `/api/market/energy`).

**Data precedence**: When local payload data conflicts with current API data, always choose `current_environment_over_stale_payload`. Use `no_conflict_found` only when all payload values agree with current API records.

**Risk overlay**: For allocation-view tasks, select the overlay code that best captures the dominant shift in views (e.g., credit-risk reduction when HY goes to UW and duration goes to OW). List rationale codes in descending order of signal magnitude (most extreme signals first).

**Risk note codes**: Choose the code that describes the primary pressure being addressed (e.g., `watchlist_concentration` when the main action is removing watchlisted instruments, `hy_cap_pressure` when HY% substantially exceeds the cap).

### 9. Watchlist handling

Always cross-reference bond instrument IDs with issuer watchlist status from `GET /api/issuers`. Watchlisted issuers have `watchlist: true`. Never propose buying a watchlisted instrument. When reducing watchlist exposure, list all watchlisted instrument IDs being sold in `watchlist_sell_ids`, sorted ascending.

### 10. Energy-credit trade selection

When selecting energy-credit trades:
- Prefer bonds where `energy_linked: true` and `candidate: true`.
- Align selections with desk-stated preferred exposures (e.g., LNG exporters, gas demand).
- Balance IG and HY to improve expected carry while staying within the HY cap.
- Ensure the two selected instruments have different issuers and different subsectors.
- Verify both selected instruments are non-watchlist (cross-reference issuers).

## Important constraints

- Never use data from stale local payloads when current API data is available. The prompt will explicitly state when the environment is the book of record.
- Do not add commentary outside the required JSON output unless the task explicitly permits it.
- All IDs (portfolio, instrument, issuer, index, policy) must exactly match values from the `/api/catalog` or relevant detail endpoints.
- When computing returns from index levels, use monthly simple returns (ratio method), not log returns.
