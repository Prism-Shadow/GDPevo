---
name: task-group-010-asteria-risk
description: Workflow SOP for Asteria Investment Office task_group_010 portfolio-risk and allocation JSON tasks. Use when solving PanofyBench task_group_010 style tasks that require the public Asteria API for energy-credit trade packages, fixed-income HY/watchlist rebalances, international equity correlations, active allocation views, or multi-asset committee decision files.
---

# Asteria Portfolio Risk Workflow

## Guardrails

Use only the public Asteria API and the task's allowed input files. Do not use stale local payload values as book-of-record data when the API has current portfolio, policy, security-master, issuer, index, prior-view, or macro-signal records.

Read the task prompt and `answer_template.json` first. Preserve required key names, item ordering, enum values, and numeric precision exactly. Return JSON only for task answers.

## Public API

Use `http://127.0.0.1:8036` as the base URL.

Core endpoints:

- `GET /api/catalog`: ids for portfolios, policies, indices, issuers, bonds, and opportunity sets.
- `GET /api/policies`: global policy set plus nested credit, correlation, multi-asset, and allocation-mapping thresholds.
- `GET /api/portfolios` and `GET /api/portfolios/<portfolio_id>`: current portfolio summary, as-of date, constraints, and holdings.
- `GET /api/instruments/bonds`: bond security master, candidate flag, energy linkage, rating bucket, duration, yield, sector/subsector, and theme tags.
- `GET /api/issuers`: issuer watchlist and outlook records.
- `GET /api/market/energy`: energy market signals and pitch themes.
- `GET /api/indices`, `GET /api/index-levels`, `GET /api/index-levels/<index_id>`: monthly regional equity levels.
- `GET /api/allocation/opportunity-sets`: opportunity set to asset-class mapping.
- `GET /api/allocation/prior-views`: prior-quarter active views.
- `GET /api/macro-signals`: current-quarter signal scores and rationale codes.

## Current-Record Precedence

Set `as_of_date` from the current API record being used, normally the portfolio record or `/api/policies`.

If local request payloads contain stale snapshots, old worksheet notes, or prior-week shortlists, treat them as intent only. Use current API holdings, instrument data, issuer watchlist status, index levels, policies, prior views, and macro signals for calculations. Use `"current_environment_over_stale_payload"` when the answer asks for data precedence.

For allocation answers, use the top-level `/api/policies.policy_id` as the answer `policy_id` unless the template explicitly asks for a nested policy id. Do not substitute `POL_ALLOCATION_MAPPING` for the full policy set id.

## Credit Calculations

Treat `quantity_usd_m`, `notional_usd_m`, and buy/sell trade sizes as USD millions of market value. Unless the task supplies prices, do not convert through par or price.

Compute post-trade quantities by adding BUY quantities and subtracting SELL quantities from current API holdings.

Compute:

- `total_market_value_usd_m`: sum of positive post-trade quantities.
- `hy_allocation_pct`: `100 * sum(quantity for bonds with rating_bucket == "HY") / total_market_value`.
- `weighted_modified_duration_years`: `sum(quantity * modified_duration_years) / total_market_value`.
- `weighted_yield_to_maturity_pct`: `sum(quantity * yield_to_maturity_pct) / total_market_value`.
- `post_trade_watchlist_exposure_usd_m`: sum of quantities whose issuer has `watchlist: true`.
- `hy_reduction_pct_points`: current HY allocation percent minus post-trade HY allocation percent.

Round only at final output precision. Check duration against the policy band, HY against `max_hy_allocation_pct`, and HY-reduction against any target reduction.

## Energy-Credit Buy Packages

Filter eligible buys through current API records:

1. `candidate: true`.
2. `energy_linked: true`.
3. issuer is not watchlisted.
4. trade action is allowed by the request.
5. post-trade HY and duration constraints pass.

For two-ticket energy income packages, use equal ticket sizes if the request says the package is evenly split. Sort selected trades ascending by `instrument_id`.

Prefer the client-facing theme before chasing the absolute highest HY yield. For LNG/gas income requests, a strong pattern is to combine an LNG/gas-linked, non-watchlist issuer with a separate non-watchlist carry issuer in another subsector so both issuer and subsector diversification pass. In learned training cases, this meant preferring the current LNG/gas demand ticket over long-dated or watchlist-yield alternatives, then pairing it with a distinct higher-carry energy-linked issuer.

Set:

- `selected_issuer_diversification_pass`: true when selected tickets use distinct issuers and do not introduce a watchlist issuer.
- `selected_subsector_diversification_pass`: true when the selected tickets span at least two subsectors.
- `watchlist_avoidance_pass`: true only when all selected issuers are non-watchlist.
- `sales_positioning.target_segment`: usually from local client context, e.g. multi-asset income.
- `sales_positioning.theme`: map the best supported market/theme signal, e.g. LNG export tailwind for LNG/gas demand packages.

Pitfall: do not use stale desk marks for current market value, HY allocation, or duration. Recompute from `/api/portfolios/<id>` and `/api/instruments/bonds`.

## Fixed-Income Risk Rebalances

Use current holdings and issuer watchlist data first. Sell current held watchlist HY pressure before selling non-watchlist HY. Then sell only enough additional HY pressure to pass the HY cap, meet the requested HY-reduction target, clear watchlist exposure, and preserve carry.

Use the current eligible buy shortlist from the payload as intent, but revalidate every candidate through `/api/instruments/bonds` and `/api/issuers`. Exclude watchlist buys even when their yield is high.

For mixed-credit risk rotations, prefer diversified IG replacement buys across all eligible non-watchlist candidates rather than concentrating all proceeds into the highest-yield IG names. Size the buys to preserve duration inside the CIO band and total proceeds. A learned Lumen pattern was: sell the watchlist HY bond plus the lower-carry HY pressure point needed to pass the cap; fund all eligible IG candidates with more weight to duration ballast and diversifiers.

Sort `rotation.trades` with all `SELL` rows before `BUY` rows, then by `instrument_id` ascending within each action.

Set:

- `watchlist_sell_ids`: only sold instruments whose issuer is currently watchlisted, sorted ascending.
- `buys_avoid_watchlist`: true only if every buy issuer is non-watchlist.
- `risk_note_code`: use `watchlist_concentration` when the central action clears held watchlist exposure; use `duration_preservation` when duration is the binding design objective; use `carry_tradeoff` when the main issue is reduced yield from derisking.

Pitfall: a buy split that produces the same rounded risk metrics can still be wrong if it ignores an eligible diversifier from the sanctioned shortlist.

## Correlation Reviews

Use monthly simple returns from consecutive index levels in the requested level window:

```text
return_t = level_t / level_(t-1) - 1
```

With 12 monthly levels, report `return_observations: 11`. Compute Pearson correlation over the return series:

```text
corr(x,y) = sum((x-mean_x)*(y-mean_y)) / sqrt(sum((x-mean_x)^2) * sum((y-mean_y)^2))
```

Round correlations to three decimals at output. Sort the two ids inside every pair alphabetically. For `extreme_pairs`, use the maximum positive correlation for `highest_positive` and the minimum correlation, including negative values, for `lowest`.

Use `/api/policies.correlation` thresholds:

- Set concentration high-threshold flags when a relevant pair exceeds `correlation_high_threshold`.
- Use `CHINA_ASIA_DEPENDENCE` when China, Asia, or EM sleeves show high overlap.
- Include low/negative-correlation diversifiers such as LatAm.
- Also include EM ex China as a diversification candidate when China dependence is the problem, even if LatAm is the single lowest-correlation pair.

Common sleeve-action pattern: trim the China sleeve when China dependence is flagged and add Latin America when it is the best diversifier. Keep actions sorted by requested sleeve ordering or template rule.

Pitfall: do not limit diversification candidates to only the lowest pair. The committee logic can also value a structural de-China replacement such as EM ex China.

## Allocation Views

Join three API sources:

1. `/api/allocation/opportunity-sets` for `asset_class`.
2. `/api/macro-signals` for the requested target quarter's `score` and `rationale_code`.
3. `/api/allocation/prior-views` for the row whose `quarter` equals the target quarter and whose `previous_quarter` equals the prior quarter.

Use `/api/policies.allocation_mapping` thresholds:

- `view = "OW"` when `score >= OW_min`.
- `view = "UW"` when `score <= UW_max`.
- `view = "N"` between those thresholds.
- `conviction = "HIGH"` when `abs(score) >= HIGH_abs_min`.
- `conviction = "MEDIUM"` when `abs(score) >= MEDIUM_abs_min`.
- `conviction = "LOW"` when `abs(score) < LOW_abs_below`.

Compute `change` by ranking `UW=-1`, `N=0`, `OW=1` and comparing current view to the prior view:

- higher rank: `UP`
- lower rank: `DOWN`
- same rank: `UNCHANGED`

Preserve the request payload's opportunity-set order for allocation rows unless the template says otherwise.

Risk overlay guidance:

- Use `DURATION_QUALITY_TILT` and `tilt_to_duration_quality` when duration support is positive and HY valuation risk is negative.
- Include `DURATION_SUPPORT`, `HY_VALUATION_RISK`, and `CHINA_DEPENDENCE` together when those rationale codes are present in the focused rows. The China code remains relevant to portfolio risk even when the overlay action is duration-quality.
- Use `CREDIT_RISK_REDUCTION` only when the task's primary instruction is reducing credit beta and no stronger duration-quality overlay is requested by signals.

Pitfall: do not omit a focused equity risk rationale from `risk_overlay.rationale_codes` just because the overlay action is fixed-income oriented.

## Multi-Asset Committee Files

Combine correlation and allocation workflows.

For `correlation_summary`, compute only over the requested index subset:

- `highest_concentration`: highest positive pair in that subset.
- `best_diversifier`: lowest pair in that subset.

For target sleeve actions, map current views and correlation roles:

- Emerging Markets with China-dependence UW: `trim`.
- India with high-conviction OW: `add`.
- Latin America with OW and low/negative correlation: `add`.
- USD with prior OW but current neutral/down and a stale local note preserving the old overweight: `hedge`, not hold.

Use `rebalance_trigger: "correlation_cap_breach"` when the concentration pair breaches the high-correlation threshold. Set `portfolio_risk_concentration_flag: true` in that case and usually `next_step: "approve_with_monitoring"` when proposed actions satisfy policy but still require committee oversight.

## Output Hygiene

Build the final object directly against the template. Check:

- all required top-level keys are present;
- numbers are rounded to the declared precision;
- no narrative is included outside JSON;
- arrays follow the specified order;
- trade pair ids and watchlist id lists are sorted as requested;
- booleans reflect recalculated current API constraints, not stale memo labels.
