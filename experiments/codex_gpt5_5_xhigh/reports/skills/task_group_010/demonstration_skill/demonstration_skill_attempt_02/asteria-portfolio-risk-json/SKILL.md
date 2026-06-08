---
name: asteria-portfolio-risk-json
description: Generate JSON answers for Asteria Investment Office portfolio-risk tasks using the public Asteria API. Use when prompts ask for credit trade or rebalance packages, equity correlation reviews, active allocation views, or committee decision JSON based on portfolios, bonds, issuers, policies, index levels, prior views, and macro signals.
---

# Asteria Portfolio Risk JSON

## Core Workflow

1. Read the local prompt, request payload, and `answer_template.json` first. Treat the template as the output contract for required fields, ordering, allowed enum values, and numeric precision.
2. Use only the public API at `http://127.0.0.1:8036` as the current book of record. Local payloads often include stale snapshots or preference memos; use them for requested IDs, ticket counts, windows, focus lists, and committee context, not for current marks when API data conflicts.
3. Query the API root or `/api/catalog` if endpoint names or IDs are unclear. API list responses often contain a `value` array and `Count`.
4. Return only the JSON object requested by the prompt. Do not include narrative outside JSON.

Useful public endpoints:

- `/api/catalog`: available portfolio, policy, index, issuer, bond, and opportunity-set IDs.
- `/api/portfolios` and `/api/portfolios/<portfolio_id>`: current portfolio summaries, holdings, constraints, and as-of dates.
- `/api/instruments/bonds`: held and candidate bond security master with `candidate`, `energy_linked`, `rating_bucket`, `modified_duration_years`, `yield_to_maturity_pct`, issuer, sector, subsector, and theme tags.
- `/api/issuers`: issuer research and `watchlist` flags.
- `/api/policies`: current policy set, credit constraints, correlation thresholds, and allocation mapping rules.
- `/api/market/energy`: current energy signals and pitch themes.
- `/api/indices`, `/api/index-levels`, `/api/index-levels/<index_id>`: monthly equity index metadata and levels.
- `/api/allocation/opportunity-sets`, `/api/allocation/prior-views`, `/api/macro-signals`: allocation taxonomy, prior views, and current signal scores.

## Output Discipline

- Preserve exact enum spelling and case from the template: examples include `BUY`, `SELL`, `UW`, `N`, `OW`, `UP`, `DOWN`, `UNCHANGED`, `LOW`, `MEDIUM`, `HIGH`.
- Sort arrays exactly as the template says. Common rules: instrument IDs ascending, pair IDs alphabetical within each pair, requested focus-list order for allocation rows, and `SELL` rows before `BUY` rows for rotations.
- Round only final numeric fields to the template precision. Use JSON numbers, not strings.
- Use `as_of_date` from the current API record used for the calculation, usually the portfolio or policy date. For allocation lineage, `policy_id` is the top-level `/api/policies.policy_id` when the template asks for the policy set.
- Set data precedence to `current_environment_over_stale_payload` when local snapshots, stale notes, or prior worksheets conflict with API records. Use `no_conflict_found` only when the local payload has no conflicting current-data claims.

## Credit Trade And Rebalance Rules

Build all credit calculations from current portfolio holdings joined to `/api/instruments/bonds` and `/api/issuers`.

- Current notional is `quantity_usd_m`; for this data set it is also the market-value weight basis.
- Post-trade market value increases by new-money buys and remains unchanged for funded rotations where sells fund buys.
- High-yield allocation percent is `100 * sum(post_notional where rating_bucket == "HY") / post_total_market_value`.
- Weighted duration is `sum(post_notional * modified_duration_years) / post_total_market_value`.
- Weighted yield is `sum(post_notional * yield_to_maturity_pct) / post_total_market_value`.
- HY reduction in percentage points is `pre_trade_hy_allocation_pct - post_trade_hy_allocation_pct`.
- Watchlist exposure is post-trade notional of instruments whose issuer has `watchlist: true`.

Candidate selection patterns:

- For energy income packages, restrict to current API bond candidates that are `candidate: true`, `energy_linked: true` when the prompt requires energy-linked exposure, and non-watchlist when client-facing or risk language warns against watchlist yield traps.
- Apply portfolio constraints after the hypothetical trade: HY cap, duration band, issuer concentration limit, and subsector diversification when present. Issuer concentration is post issuer notional divided by post total market value.
- Select trades that satisfy the requested ticket count and notional split. If several packages pass, prefer the package that best matches current market themes and memo preferences, not just the highest headline yield. LNG/gas strength supports `lng_export_tailwind`; midstream supports `midstream_stability`; watchlist avoidance supports `avoid_watchlist_yield_trap`.
- For risk-reduction rotations, sell current holdings that create the pressure named in the memo, especially watchlist issuers and HY positions. Buy current non-watchlist candidates, usually IG candidates, that keep duration inside the CIO band while preserving reasonable carry.

Credit flags and notes:

- `hy_cap_pass`: post HY allocation is at or below the policy cap.
- `duration_band_pass`: post weighted duration is inside the inclusive policy band.
- `target_hy_reduction_met`: HY reduction meets or exceeds the policy or memo target.
- `watchlist_exposure_cleared`: post watchlist exposure is zero.
- `watchlist_sell_ids`: sorted sold instrument IDs whose issuers are watchlisted; do not include non-watchlist HY sells.
- `buys_avoid_watchlist`: true only if every buy issuer is non-watchlist.
- Choose `risk_note_code` for the dominant reason: watchlist cleanup over generic HY pressure when both are present; duration preservation when the key trade-off is staying in range; carry tradeoff when accepting lower yield to satisfy risk.

## Allocation View Rules

Use `/api/allocation/opportunity-sets` for the `asset_class` of each requested opportunity set. Use `/api/macro-signals` for the target-quarter `score` and `rationale_code`. Use `/api/allocation/prior-views` rows for the target quarter as the prior view to compare against.

Map scores to current views using `/api/policies.allocation_mapping`:

- `score >= 0.35` -> `OW`
- `score <= -0.35` -> `UW`
- otherwise -> `N`

Map conviction by absolute score:

- `abs(score) >= 0.70` -> `HIGH`
- `abs(score) >= 0.35` -> `MEDIUM`
- `abs(score) < 0.35` -> `LOW`

Map `change` by comparing view ranks (`UW=-1`, `N=0`, `OW=1`) between current view and prior view: higher rank is `UP`, lower rank is `DOWN`, equal rank is `UNCHANGED`.

For portfolio-level risk overlays, prefer `DURATION_QUALITY_TILT` / `tilt_to_duration_quality` when duration support is positive while HY valuation or China-dependence risks argue against adding credit or broad EM beta. Order overlay rationale codes by business priority, not alphabetically.

## Correlation Review Rules

Use monthly levels from `/api/index-levels` for the requested index IDs and date window.

1. Sort or align levels by date within the requested level window.
2. Compute monthly simple returns from consecutive levels: `level_t / level_(t-1) - 1`.
3. `return_observations` equals the number of returns, usually one fewer than the number of monthly levels.
4. Compute Pearson correlations on the return vectors without rounding intermediate values.
5. Round reported correlations to three decimals.
6. Keep each `pair_id` or `pair` sorted alphabetically by index ID.

For `highest_positive`, choose the maximum positive correlation, not the largest absolute value. For `lowest` or `best_diversifier`, choose the minimum correlation, which may be negative. For committee summaries over a smaller index set, `highest_concentration` is the highest positive pair in that set and `best_diversifier` is the lowest pair.

Use policy correlation thresholds from `/api/policies.correlation`. Set concentration flags when relevant portfolio sleeves and memo concerns show China/Asia/EM overlap and at least one relevant correlation breaches the high threshold. Common action logic: trim China or broad EM concentration, add Latin America for negative/low correlation diversification, consider EM ex China when the objective is to retain EM beta with less China exposure, and add India when allocation signals support it as an offset.

## Multi-Asset Committee Rules

Committee JSONs often combine correlation and allocation logic:

- Build `correlation_summary` from the requested index subset and current monthly levels.
- Build `allocation_views` with the score-to-view mapping above, including `prior_view` and exact `signal_score`.
- Translate views and correlations into sleeve actions using the template order: trim high-concentration EM/China beta, add supported diversifiers, hedge currency exposure when the currency view is no longer a confident overweight, otherwise hold or monitor.
- Use `correlation_cap_breach` as the rebalance trigger when a relevant pair exceeds the high-correlation policy threshold. Set the portfolio concentration flag true in that case.
- Use `approve_with_monitoring` when actions address the risk without violating policy; reserve rejection for a hard constraint breach.

## Common Pitfalls

- Do not read hidden environment files; the public API is sufficient.
- Do not trust local stale quantities, dates, watchlist boards, or old desk notes over the API.
- Do not compute correlations from levels directly; compute monthly returns first.
- Do not compare allocation `change` to the prior conviction. Compare current view to prior view.
- Do not select watchlist buys just because they have high yield.
- Do not forget that rotations can sell multiple HY bonds while `watchlist_sell_ids` includes only watchlisted sold IDs.
- Do not reorder output rows by your preference when the template gives a request-order or enum-order convention.
