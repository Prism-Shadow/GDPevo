---
name: task-group-010-fewshot-attempt-03
description: Solve PanofyBench task_group_010 Asteria Investment Office input-output tasks. Use when producing JSON answers from local request payloads and the public Asteria API at http://127.0.0.1:8036 for credit trade packages, fixed-income risk rotations, equity index correlations, allocation views, and multi-asset committee files.
---

# Task Group 010 SOP

Use only the local task input files and the public API at `http://127.0.0.1:8036`. Treat the API as the current book of record; local payload snapshots, desk notes, and stale shortlists are request context only unless the template explicitly makes them authoritative.

## API Workflow

Start with:

- `GET /api/catalog` for valid ids.
- `GET /api/policies` for `as_of_date`, policy ids, thresholds, and view-mapping rules.
- `GET /api/portfolios` and `/api/portfolios/<portfolio_id>` for current holdings and constraints.
- `GET /api/instruments/bonds`, `/api/issuers`, `/api/market/energy` for credit tasks.
- `GET /api/indices`, `/api/index-levels`, `/api/index-levels/<index_id>` for correlation tasks.
- `GET /api/allocation/opportunity-sets`, `/api/allocation/prior-views`, `/api/macro-signals` for active allocation tasks.

Always read the answer template before calculating. Match required keys, enum case, list ordering, and decimal precision exactly. Return only the JSON object when the prompt asks for JSON only.

## Credit Trade And Rotation Rules

Build post-trade holdings from current API holdings plus proposed trades:

- `BUY` adds quantity; `SELL` subtracts current holding quantity.
- New-funded packages increase total market value by net buys.
- Rotation packages usually keep total market value unchanged because sells fund buys.
- Ignore stale local quantities when API holdings differ.

Compute credit metrics by USD million quantity:

- `HY allocation % = sum(quantity where bond.rating_bucket == "HY") / total_market_value * 100`.
- Weighted duration and yield use `sum(quantity * instrument_metric) / total_market_value`.
- Watchlist exposure uses issuer records from `/api/issuers`; do not rely only on bond tags.
- HY reduction is pre-trade HY allocation minus post-trade HY allocation, in percentage points.

Check constraints from portfolio/policies:

- HY cap passes when post-trade HY allocation is at or below `max_hy_allocation_pct`.
- Duration band passes when weighted duration is inside `duration_band_years`.
- Target HY reduction passes when the reduction meets the stricter of policy and request target.
- Watchlist avoidance/clearance requires no bought watchlist issuers and no remaining avoidable watchlist exposure.
- Selected issuer/subsector diversification usually requires distinct issuers and at least the policy minimum subsector count among selected buys.

For energy income packages, prefer current `candidate: true`, energy-linked instruments that improve carry, fit the requested theme, avoid watchlist issuers, preserve issuer/subsector diversification, and keep HY/duration inside constraints. Do not simply maximize yield if that creates headline HY, watchlist, long-duration, or concentration problems. Use `/api/market/energy` to map client themes such as LNG/gas, midstream stability, oil caution, renewables, and watchlist avoidance.

For risk-reduction rotations, sell existing watchlist pressure first, then sell enough HY pressure points to meet the target reduction. Fund current eligible non-watchlist buys, usually IG candidates, that restore duration/carry without reintroducing HY or watchlist risk. `watchlist_sell_ids` contains sold instruments whose issuers are watchlisted.

Common `risk_note_code` intent:

- `watchlist_concentration`: watchlist cleanup is the central reason.
- `hy_cap_pressure`: HY cap or HY reduction dominates.
- `duration_preservation`: duration band is the main binding constraint.
- `carry_tradeoff`: safer replacement lowers carry materially.
- `no_action`: no rotation needed.

## Equity Correlation Rules

Use the requested or policy level window, inclusive of start and end dates. Convert monthly levels to monthly simple returns:

```text
return_t = level_t / level_(t-1) - 1
```

`return_observations` is the number of returns, not the number of level rows. Compute Pearson correlations on the return vectors and round final correlations to three decimals.

Evaluate pairs across the request's index universe unless the template narrows the pair set. Sort the two ids inside every `pair_id` or `pair` alphabetically. For extreme pairs:

- `highest_positive` or `highest_concentration` is the maximum positive correlation.
- `lowest` or `best_diversifier` is the minimum correlation, often negative.

Use the policy high threshold, commonly `0.8`, for concentration flags. A China/Asia/EM overlap above the high threshold maps to `CHINA_ASIA_DEPENDENCE`; developed-world overlap maps to `GLOBAL_DEVELOPED_OVERLAP`; otherwise use `NO_MATERIAL_CONCENTRATION`. Diversification candidates should come from allowed values and have low or negative correlation to the concentration sleeve; sort them as the template requires.

## Allocation View Rules

For each requested opportunity set:

1. Get `asset_class` from `/api/allocation/opportunity-sets`.
2. Get the macro signal for the requested quarter from `/api/macro-signals`.
3. Get the prior view from `/api/allocation/prior-views` where `quarter` equals the target quarter and `previous_quarter` equals the prior quarter.
4. Map signal score to view using `/api/policies.allocation_mapping.view_score_thresholds`:
   - `score >= OW_min` -> `OW`
   - `score <= UW_max` -> `UW`
   - otherwise `N`
5. Map conviction by absolute score:
   - `abs(score) >= HIGH_abs_min` -> `HIGH`
   - `abs(score) >= MEDIUM_abs_min` -> `MEDIUM`
   - below `LOW_abs_below` -> `LOW`
6. Use the signal's `rationale_code`.
7. Compare view ranks `UW=-1`, `N=0`, `OW=1`: higher is `UP`, lower is `DOWN`, same is `UNCHANGED`.

Round `signal_score` only to the template precision, normally three decimals.

Risk overlays are selected from the dominant allocation risks and supports:

- `DURATION_QUALITY_TILT` / `tilt_to_duration_quality`: duration support plus credit/equity risk reduction.
- `CREDIT_RISK_REDUCTION` / `trim_credit_beta`: HY or credit-spread risk dominates.
- `EQUITY_BETA_EXTENSION` / `add_cyclical_equity_beta`: constructive growth/region scores dominate.
- `CURRENCY_DEFENSIVE_HEDGE` / `add_currency_hedge`: currency defensiveness dominates.
- `NO_OVERLAY` / `hold_policy_weights`: no material signal.

Order overlay `rationale_codes` by business priority, not alphabetically.

## Multi-Asset Committee Rules

Combine correlation and allocation outputs rather than recomputing separate narratives. Typical sleeve actions:

- `trim`: a sleeve is part of a high-correlation concentration and has `UW` or a downgrade.
- `add`: a sleeve is an allowed diversifier and has `OW` or an upgrade.
- `hedge`: a currency sleeve is used defensively or reduced from `OW` while risk remains.
- `hold` or `monitor`: no decisive trade signal.
- `rotate`: move exposure from a concentrated sleeve to diversifiers.

Use `correlation_cap_breach` when a material pair exceeds the high threshold, `watchlist_concentration` for unresolved credit watchlist risk, `hy_cap_pressure` for HY pressure, `duration_drift` for duration exceptions, and `committee_review` when no hard breach drives action. Set `portfolio_risk_concentration_flag` true only when the relevant high-correlation threshold is breached among material sleeves. Use `approve_with_monitoring` when actions are acceptable but still require committee oversight; reserve rejection for unresolved constraint breaches.

## Ordering And Formatting

- Preserve request order for focused opportunity sets and target sleeve actions when the template says so.
- Sort `trade_package` by `instrument_id` when requested.
- Sort rotations as `SELL` before `BUY`, then `instrument_id` ascending within each action.
- Sort candidate id lists alphabetically unless the template defines business priority order.
- Use exact enum spellings: `UW`, `N`, `OW`, `UP`, `DOWN`, `UNCHANGED`, `LOW`, `MEDIUM`, `HIGH`, and action enums in the template's case.
- Round final numeric fields to the declared precision. Do not round intermediate values before weighted sums or correlations.
- Use JSON booleans `true` and `false`; include no comments or extra prose in final JSON.

## Pitfalls

- Do not read environment files; use the public API.
- Do not trust stale local snapshots for current holdings, marks, policy ids, watchlist state, or as-of dates.
- Do not compute correlations from raw levels; compute consecutive simple returns first.
- Do not choose watchlist buys just because they offer high carry.
- Do not omit required lineage fields such as `as_of_date`, `target_quarter`, `prior_quarter`, or `policy_id`.
- Do not add fields outside the template unless the template permits them.
