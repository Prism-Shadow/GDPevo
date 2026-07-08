# Asteria Investment Office Portfolio Task Skill

## Purpose
Solve institutional portfolio management tasks that require querying the Asteria shared environment API and producing strict JSON output matching a provided schema template.

## Prerequisites
- The task provides `input/prompt.txt`, `input/payloads/<request>.json`, and `input/payloads/answer_template.json`
- Environment URL is fixed: `GDPEVO_ENV_BASE_URL=http://34.46.77.124:8010` (or as specified in `environment_access.md`)
- Do not read `env/`, `test/`, or `eval/` directories

## Step-by-Step Procedure

### 1. Parse the Request
Read `input/prompt.txt` and `input/payloads/*.json` to identify:
- **Target portfolio ID** (e.g., `PF-EN-ALTA`, `PF-FI-LUMEN`, `PF-MA-HELIO`)
- **Task type**: trade strategy, rebalance/rotation, allocation review, correlation analysis, committee decision file
- **Stale data warnings** in the payload — these are critical; always prefer current API data
- **Required output keys** from `answer_template.json`

### 2. Query the Shared Environment API
Use the API in this order to gather current data. Always prefer current API records over any stale payload data.

**Discovery:**
```bash
curl -s http://34.46.77.124:8010/api/catalog
```
Returns all valid `portfolio_ids`, `policy_ids`, `index_ids`, `bond_instrument_ids`, `issuer_ids`, and `opportunity_sets`.

**Portfolio-specific:**
```bash
curl -s http://34.46.77.124:8010/api/portfolios/<portfolio_id>
```
Returns `as_of_date`, `holdings` (with `instrument_id`, `quantity_usd_m`, `sleeve`, `notes`), `constraints`, `market_value_usd_m`.

**Constraints & Policies:**
```bash
curl -s http://34.46.77.124:8010/api/policies
```
Fetch the portfolio's `constraint_policy_id` to get `duration_band_years`, `max_hy_allocation_pct`, `target_hy_reduction_pct`, `correlation_high_threshold`, etc.

**Bond Universe:**
```bash
curl -s http://34.46.77.124:8010/api/instruments/bonds
```
Returns all bonds with `rating_bucket` (IG/HY), `modified_duration_years`, `yield_to_maturity_pct`, `sector`, `subsector`, `energy_linked`, `candidate` (true/false), `recommended_theme_tags`, `issuer_id`.

**Issuers / Watchlist:**
```bash
curl -s http://34.46.77.124:8010/api/issuers
```
Returns watchlist flags and issuer research. Use this to identify `WATCHLIST_RISK` instruments.

**Energy Market Signals** (for energy portfolios):`
```bash
curl -s http://34.46.77.124:8010/api/market/energy
```
Returns `pitch_themes`, commodity signals, and a `stale_data_warning` date threshold.

**Equity Index Data** (for correlation/allocation tasks):`
```bash
curl -s http://34.46.77.124:8010/api/indices
curl -s http://34.46.77.124:8010/api/index-levels/<index_id>
```
Index levels are monthly. Compute simple returns as `(level_t / level_{t-1}) - 1`, then Pearson correlation.

**Allocation Views & Macro Signals:**
```bash
curl -s http://34.46.77.124:8010/api/allocation/opportunity-sets
curl -s http://34.46.77.124:8010/api/allocation/prior-views
curl -s http://34.46.77.124:8010/api/macro-signals
```
Prior views show `view` (OW/N/UW), `conviction`, and `previous_quarter`. Macro signals show `score` and `rationale_code`.

### 3. Resolve Data Precedence
If the payload contains a `stale_local_note` or `stale_data_warning`, **always refresh from the API** before computing:
- Use the portfolio's current `as_of_date` from `/api/portfolios/<id>` as the `as_of_date` in the answer.
- Use current holdings quantities, not payload quantities.
- Use current bond ratings, durations, and yields from `/api/instruments/bonds`.
- Use current macro signals and prior views from `/api/allocation/*` and `/api/macro-signals`.

### 4. Perform Calculations

**Correlation (for equity tasks):**
1. Fetch 12 monthly levels for each requested `index_id`.
2. Compute simple monthly returns: `r_t = (level_t / level_{t-1}) - 1`.
3. Compute Pearson correlation across the return series.
4. Round to 3 decimal places.
5. Sort index IDs alphabetically within each pair.
6. Identify:
   - `highest_concentration`: pair with highest correlation
   - `best_diversifier`: pair with lowest correlation

**Post-Trade Metrics (for credit tasks):**
1. Start with current holdings from `/api/portfolios/<id>`.
2. Apply requested trades (SELL reduces quantity, BUY adds).
3. Compute new `market_value_usd_m` using bond prices (treat `quantity_usd_m` as market value).
4. Compute `hy_allocation_pct` = sum of HY holdings / total market value * 100.
5. Compute weighted duration and weighted YTM:
   - `weighted_dur = sum(holding_qty * bond_duration) / total_mv`
   - `weighted_ytm = sum(holding_qty * bond_ytm) / total_mv`
6. Round to 2 decimal places unless template specifies otherwise.

**HY Reduction:**
- `hy_reduction_pct_points = pre_trade_hy_pct - post_trade_hy_pct`
- Compare against policy `target_hy_reduction_pct` or payload `minimum_preferred_hy_reduction_pct_points`.

**Watchlist Handling:**
- Query `/api/issuers` or check bond `recommended_theme_tags` for `WATCHLIST_RISK`.
- Sell all watchlist holdings if the task requires clearing watchlist exposure.
- Never buy a `candidate` bond whose issuer or tags indicate watchlist risk if `avoid_new_watchlist_buy: true`.

**Allocation Views (for multi-asset/policy tasks):**
- Map each `opportunity_set` to its `asset_class` using `/api/allocation/opportunity-sets`.
- Get `prior_view` from `/api/allocation/prior-views`.
- Get `signal_score` from `/api/macro-signals`.
- Derive `view` and `change` (UP/DOWN/UNCHANGED) by comparing current macro signal direction vs. prior view.
- Select `rationale_code` from the allowed enum matching the macro signal's `rationale_code`.
- Set `conviction` based on signal magnitude (e.g., |score| > 0.4 → HIGH, 0.2–0.4 → MEDIUM, < 0.2 → LOW).

### 5. Populate the Answer Template
- Include **all required top-level keys** exactly as listed in `answer_template.json`.
- Respect **enum allowed_values** exactly; do not invent values.
- Respect **ordering rules** (e.g., SELL before BUY, then alphabetical; or specific opportunity_set order).
- Use correct **precision** (decimal places) for each numeric field.
- Set `data_precedence` to `current_environment_over_stale_payload` whenever stale notes exist.

### 6. Validate Before Returning
- Verify JSON is parseable and contains no markdown fences or narrative text.
- Check that all `required` / `required_top_level_keys` are present.
- Check enum values against allowed lists.
- Check numeric precision matches template.
- Verify ordering rules (alphabetical, SELL-before-BUY, or payload-defined sequence).
- Confirm `as_of_date` matches the current API portfolio record, not the payload date.

## Common Pitfalls
- **Using stale payload data**: If the payload has `stale_local_note`, override with API data.
- **Wrong as_of_date**: Use the API portfolio `as_of_date`, not the request's memo date.
- **Missing required keys**: The template explicitly lists required keys; verify every one.
- **Incorrect enum values**: Rationale codes, action types, and view codes must match exactly (e.g., `GROWTH_IMPROVES`, not `growth_improves`).
- **Precision errors**: Round exactly as specified (usually 1, 2, or 3 decimal places).
- **Watchlist oversight**: Always cross-check `/api/issuers` and bond `recommended_theme_tags` for `WATCHLIST_RISK`.
- **Correlation pair ordering**: Index IDs within each pair must be sorted alphabetically.

## Example API Session
```bash
BASE="http://34.46.77.124:8010"
PORTFOLIO="PF-FI-LUMEN"

# 1. Catalog
curl -s "$BASE/api/catalog" | jq .

# 2. Portfolio holdings & constraints
curl -s "$BASE/api/portfolios/$PORTFOLIO" | jq .

# 3. Bond universe for candidate selection
curl -s "$BASE/api/instruments/bonds" | jq '.[] | select(.candidate==true)'

# 4. Issuer watchlist status
curl -s "$BASE/api/issuers" | jq '.[] | select(.watchlist==true)'

# 5. Index levels for correlation
curl -s "$BASE/api/index-levels/IDX_EM" | jq '.levels'
```
