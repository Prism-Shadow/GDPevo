# Asteria Data And Workflow Guide

Read this guide when solving Asteria Investment Office JSON tasks that require current portfolio, instrument, index, macro, or allocation data.

## Source Precedence

- Treat the current environment as authoritative for portfolio holdings, instrument metadata, issuer watchlist status, index levels, macro signals, prior views, policy identifiers, and as-of dates.
- Treat local payloads as request context: portfolio id, review window, requested opportunity sets, ticket counts, notional budgets, enum choices, stale desk notes, and audience preferences.
- If a local payload contains a stale snapshot or prior worksheet and the environment differs, use the current environment and set any requested data-precedence field accordingly.
- Do not hardcode values from examples. Recompute from the current task payload and current environment records.

## Environment Endpoint Map

Use the base URL and allowed paths from the task's environment access file. In the staged Asteria environment, the useful endpoints are:

- `GET /api/portfolios`: current portfolio summaries, including `portfolio_id`, `as_of_date`, `market_value_usd_m`, `constraint_policy_id`, objective, and strategy.
- `GET /api/portfolios/{portfolio_id}/holdings`: current holdings for a portfolio, including `instrument_id`, `quantity_usd_m`, `asset_class`, `sleeve`, and notes.
- `GET /api/instruments/bonds`: bond master with `candidate`, `energy_linked`, `issuer_id`, `issuer_name`, `rating_bucket`, `modified_duration_years`, `yield_to_maturity_pct`, sector, subsector, spread, and theme tags.
- `GET /api/issuers`: issuer master with `issuer_id`, rating bucket, sector/subsector, credit outlook, research tags, and `watchlist`.
- `GET /api/market/energy`: current energy signals and pitch themes for energy-credit positioning.
- `GET /api/indices`: index metadata, level start/end dates, display names, regions, and monthly frequency.
- `GET /api/index-levels` or `GET /api/index-levels/{index_id}`: monthly index levels by index id.
- `GET /api/allocation/opportunity-sets`: opportunity-set taxonomy and asset classes.
- `GET /api/allocation/prior-views`: prior active views by opportunity set and quarter.
- `GET /api/macro-signals`: current signal score, drivers, and rationale code by opportunity set and quarter.

If a prompt names an endpoint that is not documented in the current access file, first look for the needed value in documented records, especially portfolio `constraint_policy_id`. Do not invent inaccessible policy data.

## Portfolio And Credit Math

Join holdings to the bond master by `instrument_id` and to the issuer master by `issuer_id`.

For current metrics:

- `total_market_value_usd_m = sum(quantity_usd_m)`
- `hy_allocation_pct = sum(quantity where bond.rating_bucket == "HY") / total_market_value * 100`
- `weighted_modified_duration_years = sum(quantity * modified_duration_years) / total_market_value`
- `weighted_yield_to_maturity_pct = sum(quantity * yield_to_maturity_pct) / total_market_value`
- `watchlist_exposure_usd_m = sum(quantity where issuer.watchlist is true)`

For post-trade metrics, apply sells as negative quantities and buys as positive quantities before recomputing. `hy_reduction_pct_points` is current HY allocation minus post-trade HY allocation.

For energy-credit BUY packages:

- Start from current holdings, not stale desk worksheets.
- Obey requested ticket count, total notional, action list, and split instructions.
- Restrict to current eligible bonds. The bond master `candidate` flag is the primary eligibility cue.
- Use issuer `watchlist` to avoid watchlist yield traps when the prompt or template asks for watchlist avoidance.
- Prefer bonds that improve carry while keeping HY allocation and duration inside constraints.
- Use issuer and subsector diversification checks on the selected tickets when requested.
- Use energy market signals and bond theme tags to choose a client-facing pitch theme.

For fixed-income risk rebalances:

- Sell current holdings that create watchlist, HY, or duration pressure before adding new risk.
- Prioritize clearing watchlisted issuer exposure when the template asks for it.
- Fund sells with current eligible candidates that avoid watchlist issuers and preserve duration.
- Sort trade rows exactly as the template says, commonly SELL rows before BUY rows, then `instrument_id` ascending within each action.
- Compute exception flags from post-trade metrics, not from local meeting labels.

## Correlation Math

Use index levels over the requested level window. For each index:

1. Sort levels by date.
2. Keep only dates inside the requested start/end window.
3. Calculate monthly simple returns from consecutive levels:
   `return_t = level_t / level_(t-1) - 1`
4. Use the aligned return vectors to calculate Pearson correlation for every requested pair.
5. Round correlations only after ranking pairs.

Role selection:

- `highest_positive`, `highest_concentration`, or concentration-risk roles use the largest positive correlation among eligible pairs.
- `lowest` or `best_diversifier` uses the lowest correlation among eligible pairs.
- Sort ids inside every pair alphabetically. If the template orders roles, preserve that role order even if the pair ids are sorted internally.
- Set concentration flags when the highest positive correlation is materially high and matches the portfolio's stated concentration concern.

## Active Allocation Views

For each requested opportunity set:

1. Get its asset class from `/api/allocation/opportunity-sets`.
2. Get the prior view from `/api/allocation/prior-views` where `quarter` matches the target quarter and `previous_quarter` matches the requested prior quarter.
3. Get the current macro signal from `/api/macro-signals` for the target quarter.
4. Use the signal's `rationale_code` unless the view is neutral and the signal is near zero; then use the template's neutral-balance option if available.

Use this score mapping unless the task provides a different policy scale:

- `score >= 0.30`: current view `OW`, conviction `MEDIUM`.
- `score <= -0.30`: current view `UW`, conviction `MEDIUM`.
- `-0.30 < score < 0.30`: current view `N`, conviction `LOW`.
- If `abs(score) >= 0.70`, conviction is `HIGH`.

Derive `change` by comparing current view to prior view using `UW < N < OW`: higher is `UP`, lower is `DOWN`, equal is `UNCHANGED`.

Risk overlay selection should reflect the dominant actionable risks:

- Duration support plus credit/HY risk favors a duration-quality tilt.
- Credit spread or HY valuation risk favors trimming credit beta.
- Broad positive equity signals favor adding cyclical equity beta.
- Defensive currency signals favor adding a currency hedge.
- No dominant signal favors holding policy weights.

## Combined Committee Files

When a committee request links correlation findings with active allocation views:

- Compute the requested correlation summary first.
- Derive allocation views for the requested opportunity sets next.
- Let high concentration and negative active views drive trim or hedge actions.
- Let diversifying pairs and positive active views drive add actions.
- Use a correlation-cap or concentration trigger when a high positive pair is the central risk.
- Choose a next step that is consistent with all flags: approve with monitoring when actions improve the issue without breaching constraints; reject or defer only when unresolved constraints remain.
