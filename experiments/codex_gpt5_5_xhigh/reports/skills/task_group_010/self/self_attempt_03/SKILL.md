# Asteria Portfolio Risk Skill

Use this skill for Asteria Investment Office tasks that ask for JSON decisions on credit trades, fixed-income rotations, international equity correlations, active allocation views, or multi-asset committee files. The common pattern is: read the local task input for scope and schema, use the shared Asteria API as the current book of record, compute with unrounded source values, then emit only the requested JSON shape.

## Source Discipline

1. Read the task prompt and `input/payloads/*` files first. Treat local memos, stale snapshots, and preference packets as context, not authoritative holdings or marks.
2. Use the environment access file for the API base URL. Quote URLs that contain query strings, for example `curl -s '.../api/instruments/bonds?candidate=true'`.
3. Prefer current API records over local payload records whenever they conflict. If the schema has a `data_precedence` field, use the enum that states the current environment overrode stale local payload data.
4. Never use output files, answer files, judge feedback, or generated answers from other runs. The answer must be derived from the task inputs plus the public API only.
5. Emit exactly the JSON object requested by `answer_template.json`. Do not add narrative text around it.

Useful endpoints:

- `/api/catalog`
- `/api/policies`
- `/api/portfolios`
- `/api/portfolios/<portfolio_id>`
- `/api/instruments/bonds`
- `/api/issuers`
- `/api/market/energy`
- `/api/indices`
- `/api/index-levels`
- `/api/index-levels/<index_id>`
- `/api/allocation/opportunity-sets`
- `/api/allocation/prior-views`
- `/api/macro-signals`

Most list endpoints support equality filters matching field names, such as `?candidate=true`, `?quarter=Q2_2026`, or `?rating_bucket=HY`. Fetch all records and filter locally if a filter is awkward.

## JSON Contract Habits

- Follow required top-level keys, enum values, list lengths, and ordering rules from the template literally.
- Round only at the final field level and to the precision in the template. Do not round intermediate returns, weights, or post-trade quantities.
- Preserve task/request-specific ordering when the template says so. Otherwise sort as instructed:
  - trade packages often sort by `instrument_id`;
  - rotations often sort `SELL` before `BUY`, then `instrument_id`;
  - pair IDs sort alphabetically inside the pair;
  - index sets and watchlist sell IDs often sort alphabetically;
  - allocation rows usually follow the request payload's opportunity-set order.
- Use the environment `as_of_date` relevant to the data used: portfolio `as_of_date` for portfolio trade/risk outputs, policy or API set `as_of_date` for allocation/correlation lineage when the task asks for policy lineage. If they agree, use that shared current date.

## Credit And Bond Trade SOP

Use this for energy-credit buy packages and fixed-income risk-reduction rotations.

### Required joins

1. Fetch the target portfolio with `/api/portfolios/<portfolio_id>`.
2. Fetch bonds with `/api/instruments/bonds`; use `candidate=true` only for possible buys when the task asks for eligible candidates.
3. Fetch issuers with `/api/issuers`; issuer `watchlist` status is authoritative.
4. Fetch `/api/policies` and use the portfolio's `constraint_policy_id` or embedded constraints.
5. For energy-income tasks, fetch `/api/market/energy` for pitch themes and stale-data warnings.

### Eligibility and exclusions

- Current holdings can be sold even if their bond record has `candidate=false`.
- New buys should normally require `candidate=true`; if the prompt narrows the universe, also filter by fields such as `energy_linked=true`, sector, rating bucket, or requested theme.
- Exclude watchlist issuers from buys whenever the task asks for watchlist avoidance or client-suitable income. High yield is not automatically prohibited, but watchlisted high carry is a common trap.
- For energy buy packages, prefer non-watchlist bonds with the requested themes, then check whether the pair uses distinct issuers and distinct subsectors when diversification checks exist.
- For credit-risk reduction, sell current HY/watchlist pressure points first and buy current eligible non-watchlist candidates, often IG or duration-preserving bonds. Do not buy a high-yield or watchlist candidate just because it has high yield.

### Portfolio math

Treat quantities/notionals as USD millions unless the template says otherwise.

For each post-trade holding:

```text
post_quantity = current_quantity + buy_quantity - sell_quantity
```

For funded new-buy packages, total market value increases by the buy notional. For rotations, sell proceeds and buy quantities should usually net to zero unless the prompt says otherwise.

Compute:

```text
total_market_value = sum(post_quantity)
hy_allocation_pct = 100 * sum(post_quantity where instrument.rating_bucket == "HY") / total_market_value
weighted_duration = sum(post_quantity * instrument.modified_duration_years) / total_market_value
weighted_ytm = sum(post_quantity * instrument.yield_to_maturity_pct) / total_market_value
watchlist_exposure = sum(post_quantity where issuer.watchlist == true)
issuer_concentration_pct = 100 * sum(post_quantity for issuer) / total_market_value
hy_reduction_pct_points = pre_trade_hy_allocation_pct - post_trade_hy_allocation_pct
```

Use `yield_to_maturity_pct` for carry/yield fields, not coupon or spread. Use `modified_duration_years` for duration. Use instrument `rating_bucket` for HY/IG classification.

### Constraint checks

Read thresholds from policy records every time. Common defaults in this environment include a 20% HY cap, duration band of 3.0 to 5.0 years, 12% issuer concentration limit, and 4 percentage point HY-reduction target for risk-reduction portfolios, but verify from `/api/policies`.

Set booleans directly from post-trade results:

- `hy_cap_pass`: post-trade HY allocation is at or below max.
- `duration_band_pass`: post-trade duration is inside the inclusive policy band.
- `target_hy_reduction_met`: HY reduction is at least the policy/request target.
- `watchlist_exposure_cleared`: post-trade watchlist exposure is zero, when the task asks to clear it.
- `buys_avoid_watchlist`: no buy uses an issuer with `watchlist=true`.
- `selected_issuer_diversification_pass`: selected buys use distinct issuers and, if the policy/schema implies concentration, do not create issuer concentration above the limit.
- `selected_subsector_diversification_pass`: selected buys span at least the requested or policy minimum number of subsectors.

### Trade selection priorities

1. Satisfy hard constraints and exact ticket/count/notional requirements first.
2. Avoid watchlist buys and stale memo quantities.
3. Improve the requested metric: carry for income packages, HY/watchlist reduction for risk rotations, duration preservation when the CIO band matters.
4. Use themes only after the risk math passes. For energy, LNG/gas demand and midstream defensive carry are generally more client-suitable than watchlist/refining yield traps.
5. If two packages both pass, prefer the one with clearer issuer/subsector diversification and simpler client rationale.

## Equity Correlation SOP

Use this for international equity concentration reviews and multi-asset correlation summaries.

### Data and window

1. Read requested index IDs and date window from the payload. If the task says "current 12-month monthly-level window", use the correlation policy or index metadata window.
2. Fetch each index through `/api/index-levels/<index_id>` or fetch `/api/index-levels` and filter.
3. Use levels from `level_start_date` through `level_end_date`, inclusive.
4. Compute monthly simple returns from consecutive levels:

```text
return_t = level_t / level_(t-1) - 1
return_observations = number_of_levels - 1
```

Do not use log returns. Align series by common dates if needed. With 12 monthly levels, expect 11 return observations.

### Pearson correlation

For each unique unordered pair of requested index IDs:

```text
corr(x,y) = sum((x_i - mean_x) * (y_i - mean_y)) /
            sqrt(sum((x_i - mean_x)^2) * sum((y_i - mean_y)^2))
```

The sample/population covariance convention cancels as long as numerator and denominator are consistent. Round final correlations to three decimals.

### Pair roles and flags

- Sort the two index IDs alphabetically within every `pair` or `pair_id`.
- `highest_positive` or `highest_concentration` is the pair with the highest correlation among the requested universe.
- `lowest` or `best_diversifier` is the pair with the lowest correlation among the requested universe, even if it is still positive.
- Use policy thresholds for flags. Common defaults are high correlation at 0.8 and low correlation at 0.2, but verify from `/api/policies`.
- `high_threshold_breached` or concentration flag is true if the highest relevant correlation is at or above the high threshold.
- Use concentration codes by cause:
  - China plus Asia/EM overlap: `CHINA_ASIA_DEPENDENCE`.
  - Developed/global beta overlap: `GLOBAL_DEVELOPED_OVERLAP`.
  - No threshold-level issue: `NO_MATERIAL_CONCENTRATION`.
- Diversification candidates should come from the template's allowed values, chosen for lower correlations to the concentration source, then sorted as required.

### Sleeve actions

Map actions to the facts, not to stale memo wording:

- `trim`: reduce a sleeve that is the source of concentration.
- `add`: increase a low-correlation diversifier or high-conviction diversifying sleeve.
- `rotate`: move exposure from concentrated beta into a diversifier.
- `hedge`: currency or beta hedge when the task asks for hedge framing.
- `monitor`: risk exists but does not require immediate trade.
- `hold`: no material concentration or no clear action.

## Active Allocation View SOP

Use this for CIO allocation refreshes and allocation sections inside committee files.

### Required joins

1. Read `target_quarter`, `prior_quarter`, and requested opportunity sets from the payload.
2. Fetch `/api/allocation/opportunity-sets` for asset class and taxonomy.
3. Fetch `/api/allocation/prior-views`, filtering to rows whose `quarter` equals the target quarter. These rows provide the prior baseline view for comparison to the target-quarter signal.
4. Fetch `/api/macro-signals`, filtering to `quarter == target_quarter`.
5. Fetch `/api/policies` for allocation mapping thresholds and `view_rank`.

### Derive fresh view from signal

Do not treat `prior-views` as the final current view. It is the comparison baseline.

Using the macro `score` and policy thresholds:

```text
if score >= OW_min: view = "OW"
else if score <= UW_max: view = "UW"
else: view = "N"

if abs(score) >= HIGH_abs_min: conviction = "HIGH"
else if abs(score) >= MEDIUM_abs_min: conviction = "MEDIUM"
else: conviction = "LOW"
```

Common thresholds are `OW_min = 0.35`, `UW_max = -0.35`, `MEDIUM_abs_min = 0.35`, and `HIGH_abs_min = 0.7`, but always read the policy.

Use `macro_signal.rationale_code` for the row rationale. Use the opportunity-set taxonomy for `asset_class`. If the schema asks for `signal_score`, round the raw score to the required precision.

### Derive change

Compare the derived view to the prior baseline using policy `view_rank`:

```text
rank_delta = view_rank[new_view] - view_rank[prior_view]
if rank_delta > 0: change = "UP"
else if rank_delta < 0: change = "DOWN"
else: change = "UNCHANGED"
```

Keep allocation rows in the request's opportunity-set order unless the template specifies another order.

### Risk overlay selection

Choose one overlay that best captures the highest-priority portfolio risk among the requested rows:

- `CREDIT_RISK_REDUCTION` / `trim_credit_beta`: HY valuation risk, credit spread risk, or an underweight HY/credit signal dominates.
- `DURATION_QUALITY_TILT` / `tilt_to_duration_quality`: duration support and quality carry dominate, especially when paired with credit caution.
- `EQUITY_BETA_EXTENSION` / `add_cyclical_equity_beta`: broad positive equity growth signals dominate without material concentration risk.
- `CURRENCY_DEFENSIVE_HEDGE` / `add_currency_hedge`: defensive dollar/currency risk dominates.
- `NO_OVERLAY` / `hold_policy_weights`: no material active signal.

For overlay `rationale_codes`, deduplicate and order by business priority, not alphabetically. Put hard risk-control rationales before return-seeking rationales when both are present.

## Multi-Asset Committee SOP

These tasks combine the correlation and allocation procedures.

1. Fetch the current portfolio for the requested `portfolio_id` for `as_of_date` and holdings context.
2. Compute correlation summary only on the requested index IDs and requested/current window.
3. Produce exactly the required role order, commonly `highest_concentration` then `best_diversifier`.
4. Derive allocation views for the requested opportunity sets using the allocation SOP. Include `prior_view` and `signal_score` only when the schema asks for them.
5. Map target sleeve actions from the combined evidence:
   - reduce or monitor the concentrated sleeve;
   - add or rotate toward the diversifier;
   - hedge currency if currency views and the schema call for it;
   - hold where signal and concentration evidence are neutral.
6. Set `rebalance_trigger` to the dominant issue: `correlation_cap_breach`, `hy_cap_pressure`, `duration_drift`, `watchlist_concentration`, or `committee_review`.
7. Set `portfolio_risk_concentration_flag` true when the correlation high threshold is breached for the relevant review universe.
8. Use `approve_with_monitoring` for actionable but constraint-compliant committee recommendations, `approve_rotation` for a clean proposed trade rotation, `defer_pending_risk_review` if current data is insufficient or the committee must review unresolved risk, and `reject_constraint_breach` if a proposed action fails hard constraints.

## Final Validation Checklist

Before returning JSON:

- Required keys all present, no extra prose.
- Enum strings match the template exactly.
- Quantities and notionals match exact ticket/count/funding instructions.
- Post-trade math uses API current holdings, not stale payload snapshots.
- Buys are eligible candidates and satisfy task-specific filters.
- Watchlist status comes from `/api/issuers`.
- Weighted metrics use post-trade quantities and total market value.
- Correlations use simple monthly returns from consecutive levels.
- Pair IDs are alphabetically sorted inside pairs.
- Allocation views are derived from macro scores; prior views are only the baseline for `change`.
- Rounding is final-field rounding only.
