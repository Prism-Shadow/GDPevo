# Reflect-3 Asteria JSON Workflow

Use this skill for Asteria Investment Office tasks that ask for compact JSON decisions using the shared environment API plus a local request/template packet.

## Source Precedence

- Treat the local prompt and payload as the contract: requested portfolio, task window, field names, enum choices, item order, and rounding precision.
- Treat the shared environment as the book of record for current portfolios, holdings, policies, instruments, issuers, index levels, opportunity sets, prior views, and macro signals.
- If a local memo contains stale snapshots, quantities, marks, or preferences, use it only as context. Current environment records override stale local values for calculations and eligibility.
- Use the environment `as_of_date` from the current record that drives the answer. For allocation lineage, prefer the top-level policy-set id when the template asks generically for `policy_id`; use a nested policy id only when the task/template specifically identifies that policy.

## API Habits

- Start with `/api/policies` to get dates, thresholds, score mappings, duration bands, HY caps, and policy identifiers.
- Fetch the specific portfolio detail with `/api/portfolios/<portfolio_id>` instead of relying on portfolio list summaries.
- For credit tasks, join portfolio holdings to `/api/instruments/bonds` and `/api/issuers` by `instrument_id` and `issuer_id`.
- For correlation tasks, use `/api/indices` for the official level window and `/api/index-levels` or `/api/index-levels/<index_id>` for monthly levels.
- For allocation tasks, combine `/api/allocation/opportunity-sets`, `/api/allocation/prior-views`, and `/api/macro-signals`; filter by the requested quarter and opportunity sets.
- Equality filters are useful, but verify the shape returned by the API before assuming a filtered endpoint returns only one object.

## JSON Contract Discipline

- Build the answer from the template, not from memory. Include required keys only unless the prompt asks for extras.
- Use exact enum strings from the template. Do not invent synonyms.
- Preserve the template's item order when it gives one: request order, explicit `item_order`, action ordering, or allowed-value order. For ambiguous "alphabetical" instructions, prefer the template/request ordering when it is explicit, and always sort pair ids within each pair as requested.
- Sort trade lists exactly as specified, commonly `SELL` rows before `BUY` rows and then ascending `instrument_id` within each action.
- Round only at the final output step, using the precision declared in the template. Keep internal calculations unrounded.

## Credit And Bond Calculations

- Adjust current holdings by proposed trades, then calculate post-trade metrics from the adjusted book.
- Post-trade market value is current market value plus buys minus sells. For fully funded rotations, it should remain unchanged.
- HY allocation percent: `100 * sum(quantity_usd_m where rating_bucket == "HY") / post_trade_market_value`.
- Weighted duration: `sum(quantity_usd_m * modified_duration_years) / post_trade_market_value`.
- Weighted yield: `sum(quantity_usd_m * yield_to_maturity_pct) / post_trade_market_value`.
- HY reduction in percentage points: pre-trade HY allocation percent minus post-trade HY allocation percent.
- Watchlist exposure: sum adjusted quantities for instruments whose issuer has `watchlist: true`.
- For BUY packages, honor all filters in the prompt: `candidate`, sector or energy linkage, allowed action, watchlist avoidance, issuer/subsector diversification, ticket count, and exact total notional split.
- For rebalance packages, sell current holdings rather than stale memo quantities, clear any required watchlist exposure, and fund buys with current eligible non-watchlist candidates when requested.
- High yield alone should not dominate selection. A client-facing carry package still needs to pass HY caps, duration bands, issuer/subsector diversification, and watchlist rules.

## Correlation Calculations

- Use monthly simple returns from consecutive levels: `return_t = level_t / level_(t-1) - 1`.
- `return_observations` equals the number of level observations minus one.
- Compute Pearson correlation on the aligned simple-return arrays for each requested pair.
- `highest_positive` is the maximum correlation in the requested universe; `lowest` or best diversifier is the minimum correlation unless the prompt narrows the candidate universe.
- Pair ids inside each pair must be sorted by index id before output.
- Use the policy high-correlation threshold for concentration flags and the low-correlation threshold only when the task asks for threshold-qualified diversifiers.

## Allocation View Mapping

- Pull the target-quarter macro signal for each requested opportunity set.
- Map signal score to view using the allocation policy thresholds: `OW` at or above the OW threshold, `UW` at or below the UW threshold, otherwise `N`.
- Map conviction from absolute signal score using the policy's LOW/MEDIUM/HIGH thresholds.
- Use the prior-view record for the requested target quarter as the prior state, then compare ranks (`UW < N < OW`) to emit `UP`, `DOWN`, or `UNCHANGED`.
- Use the opportunity-set taxonomy for `asset_class` and the macro signal's `rationale_code` for rationale fields.
- For overlays, choose the enum/action that matches the dominant active risk signal, and order rationale codes by business priority rather than alphabetically when the template says so.

## Action Enum Conventions

- For sleeve actions, let the active view drive the direct action: `UW` usually maps to `trim`, `OW` to `add`, and `N` to `hold` or `monitor`.
- Reserve `rotate` for an explicit replacement from one sleeve or target to another; do not use it merely because a correlation finding is present.
- Use `hedge` for currency sleeves when the current view or memo specifically frames the position as a defensive currency offset.
- Use `approve_with_monitoring` when the package addresses the signal but a concentration/risk flag remains important for committee oversight; use rejection only when constraints remain breached.

## Common Pitfalls

- Do not use stale local snapshots for current quantities, market value, HY allocation, or duration.
- Do not buy watchlist issuers to chase yield when the prompt asks for client-safe income or watchlist avoidance.
- Do not broaden diversification candidates beyond the requested universe or policy-qualified candidates.
- Do not round component inputs before computing weighted metrics or correlations.
- Do not output narrative text around the JSON when the prompt asks for JSON only.
- Do not include training answers, gold outputs, evaluation notes, or run artifacts in the working context or final response.
