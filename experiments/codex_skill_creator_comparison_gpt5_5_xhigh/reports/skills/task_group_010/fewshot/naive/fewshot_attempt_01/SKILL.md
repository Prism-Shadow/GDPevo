---
name: asteria-investment-json-solver
description: Solve Asteria Investment Office JSON tasks that require using the shared read-only environment plus local prompt payloads for portfolio credit trades, fixed-income risk rotations, equity index correlations, active allocation views, and multi-asset committee decision files.
---

# Asteria Investment JSON Solver

Use this skill when a task asks for an Asteria Investment Office answer as a single JSON object.

## Workflow

1. Read the task prompt, every file under `input/payloads/`, and the local answer template before calling the environment.
2. Read the environment access file for the base URL and allowed endpoints. Use only read-only business endpoints; never call a judge or write endpoint.
3. Treat the shared Asteria environment as the book of record for current dates, portfolios, holdings, policy thresholds, security master data, index levels, prior views, and macro signals.
4. Treat local payloads as request scope, stale desk context, output contract, and ordering instructions. If a local value conflicts with current environment records, use the environment unless the prompt explicitly says otherwise.
5. Build the answer from the template schema. Preserve required keys, enum values, exact list lengths, and declared ordering. Round numeric fields only at output precision.
6. Return only valid JSON. Do not include calculations, commentary, markdown fences, or source notes unless the answer template requires them.

The helper script at `scripts/asteria_calcs.py` can compute common correlations, allocation rows, and post-trade credit metrics from the live environment:

```bash
python path/to/skill/scripts/asteria_calcs.py correlations --base-url "$BASE_URL" --index IDX_A IDX_B IDX_C --start YYYY-MM-DD --end YYYY-MM-DD
python path/to/skill/scripts/asteria_calcs.py allocation --base-url "$BASE_URL" --quarter QX_YYYY --opportunity-set "Opportunity Set"
python path/to/skill/scripts/asteria_calcs.py credit-metrics --base-url "$BASE_URL" --portfolio-id PF-ID --trades-file trades.json
```

Use the script as a calculator, not as a full answer generator.

## Source Joins

Use these environment records as needed:

- `/api/policies`: policy set as-of date, credit limits, correlation thresholds, allocation score thresholds, view ranks.
- `/api/portfolios` and `/api/portfolios/{portfolio_id}`: current portfolio summary, constraints, holdings, sleeves, market value.
- `/api/instruments/bonds`: bond attributes keyed by `instrument_id`, including candidate flag, energy linkage, duration, yield, rating bucket, sector, subsector, issuer.
- `/api/issuers`: issuer watchlist and research records keyed by `issuer_id`.
- `/api/market/energy`: current energy macro and pitch themes.
- `/api/indices` and `/api/index-levels`: monthly index metadata and levels keyed by `index_id`.
- `/api/allocation/opportunity-sets`: taxonomy and asset class for opportunity-set rows.
- `/api/allocation/prior-views` and `/api/macro-signals`: prior active views and current-quarter signal scores/rationale codes.

## Credit And Bond Tasks

Join portfolio holdings to bonds and issuers before selecting or validating trades.

For a proposed trade list:

- BUY increases the instrument quantity and total market value unless funded by simultaneous SELLs.
- SELL decreases an existing quantity and should not exceed the current holding unless the prompt explicitly allows short sales.
- Post-trade total market value is current market value plus buys minus sells.
- Weighted duration and weighted yield are `sum(quantity_usd_m * field) / post_total_market_value`.
- HY allocation percent is `100 * post_trade_quantity where rating_bucket == "HY" / post_total_market_value`.
- Watchlist exposure is the post-trade quantity whose joined issuer has `watchlist: true`.
- HY reduction percentage points are pre-trade HY allocation percent minus post-trade HY allocation percent.

Use the relevant portfolio constraints or policy fields:

- `hy_cap_pass`: post-trade HY allocation is less than or equal to `max_hy_allocation_pct`.
- `duration_band_pass`: post-trade duration is within the inclusive duration band.
- `target_hy_reduction_met`: HY reduction is at least the requested or policy target.
- `watchlist_exposure_cleared`: post-trade watchlist exposure is zero when the task asks to clear it.
- `watchlist_avoidance_pass` or `buys_avoid_watchlist`: no selected BUY has a watchlisted issuer.
- Issuer diversification: selected BUY issuers are distinct and any selected issuer remains within the issuer concentration limit if one is provided.
- Subsector diversification: selected BUYs span at least the policy minimum number of subsectors when the template asks for it.

For income-oriented BUY packages, filter to current eligible candidates from the environment, apply request scope such as energy-linked bonds and ticket count/notional, avoid watchlisted issuers, and choose the highest carry package that still passes HY, duration, issuer, and subsector constraints. Prefer candidates aligned with current market themes when the answer template asks for sales positioning.

For risk-reduction rotations, sell current watchlist holdings first. If the HY cap or target HY reduction still fails, sell the smallest additional full HY pressure positions needed to pass, using local risk memos only to prioritize the pressure set. Buy current non-watchlist candidates, usually IG when the task asks to reduce risk, and size replacements so sale proceeds are used, duration remains inside band, and no new watchlist exposure is added.

## Correlation Tasks

Use monthly simple returns from consecutive index levels:

```text
return[t] = level[t] / level[t-1] - 1
```

Filter levels to the requested inclusive level window. The return observation count is one less than the number of filtered levels. Compute Pearson correlations over the aligned return vectors, round correlations to the requested precision, and sort index ids alphabetically inside every pair id.

For an `extreme_pairs` object:

- `highest_positive`: pair with the largest correlation.
- `lowest` or `best_diversifier`: pair with the smallest correlation.

Set concentration flags from the policy high threshold. Use concentration codes such as `CHINA_ASIA_DEPENDENCE` when China, EM, or Asia-Pacific pairs breach the high threshold and the request memo names China/Asia dependence. Diversification candidates and sleeve actions should follow the template's allowed values: trim the concentrated sleeve, add the lowest-correlation diversifier or a structurally ex-China alternative, and keep rows in the requested order.

## Allocation View Tasks

For each requested opportunity set and quarter:

1. Read the opportunity-set taxonomy for `asset_class`.
2. Read the current macro signal record for the requested quarter.
3. Read the prior-view record whose `quarter` equals the requested target quarter; its `view` is the prior quarter's view for comparison.
4. Map score to view using policy thresholds: `score >= OW_min` is `OW`, `score <= UW_max` is `UW`, otherwise `N`.
5. Map conviction from absolute score using policy thresholds: `HIGH` at or above `HIGH_abs_min`, `MEDIUM` at or above `MEDIUM_abs_min`, otherwise `LOW`.
6. Compare policy view ranks to set `change`: higher rank is `UP`, lower rank is `DOWN`, equal rank is `UNCHANGED`.
7. Use the macro signal's `rationale_code` and score, rounding only if the template asks for `signal_score`.

The policy set's top-level `policy_id` and `as_of_date` are lineage fields unless a more specific template field names another source.

For portfolio-level overlays, use the dominant active risks from the requested set. Typical mappings are:

- duration support plus HY or China weakness: `DURATION_QUALITY_TILT` and `tilt_to_duration_quality`.
- broad credit weakness or required HY reduction: `CREDIT_RISK_REDUCTION` and `trim_credit_beta`.
- broad positive equity signals: `EQUITY_BETA_EXTENSION` and `add_cyclical_equity_beta`.
- currency defensiveness or explicit currency hedge need: `CURRENCY_DEFENSIVE_HEDGE` and `add_currency_hedge`.
- no material signal: `NO_OVERLAY` and `hold_policy_weights`.

List overlay rationale codes in business priority order, led by the risks or supports that drive the chosen overlay.

## Multi-Asset Committee Tasks

These tasks usually combine correlation and allocation outputs:

- Build the correlation summary from the request's index universe, using highest positive correlation as concentration and lowest correlation as diversifier.
- Build allocation rows from macro signals and prior views for the requested opportunity sets.
- Translate sleeve actions from both views and correlations: trim concentrated or UW sleeves, add OW diversifiers, hedge currencies when the current view no longer supports a prior overweight or the request asks for a hedge, and otherwise hold or monitor.
- Use `correlation_cap_breach` when the concentration pair exceeds the policy high threshold. Set the portfolio concentration flag consistently with that threshold.
- Use `approve_with_monitoring` when constraints are addressed but a concentration flag remains; use a stricter next step only when the computed checks fail or the template/prompt demands escalation.

## Output Discipline

- Match template order when stated; otherwise use stable logical order from the request payload.
- Sort pair ids and instrument ids exactly as the template specifies.
- Preserve action ordering such as SELL before BUY when required.
- Do not copy stale local snapshots into metrics.
- Do not include training answer values, hidden assumptions, or final-answer examples in the skill output.
