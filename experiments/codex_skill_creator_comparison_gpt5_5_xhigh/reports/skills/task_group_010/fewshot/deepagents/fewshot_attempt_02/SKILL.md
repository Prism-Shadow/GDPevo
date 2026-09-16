---
name: asteria-investment-office
description: Solve Asteria Investment Office JSON tasks that require the shared environment as the current book of record for portfolios, holdings, bonds, issuers, energy signals, index correlations, active allocation views, fixed-income risk rotations, and multi-asset committee decisions. Use when prompts mention Asteria portfolios, payload answer templates, stale local worksheets, CIO/risk/committee reviews, or environment-backed investment records.
---

# Asteria Investment Office

Use the shared Asteria environment as the book of record. Treat local payloads as request context and output contracts; do not trust local marks, quantities, dates, policy values, or stale notes when the environment has current records.

## Standard Workflow

1. Read the prompt, `input/payloads/answer_template.json`, and every local payload.
2. Fetch current records from the environment. Default base URL: `http://task-env:9010/`.
3. Build the answer from environment records, then shape it exactly to the template: required keys only when implied, allowed enum values, declared ordering, and declared rounding.
4. Return only the JSON object unless the prompt explicitly asks for something else.

Use `scripts/asteria_tools.py` for repeatable calculations. From the skill directory:

```bash
python scripts/asteria_tools.py correlations --indices IDX_A IDX_B IDX_C --start YYYY-MM-DD --end YYYY-MM-DD
python scripts/asteria_tools.py allocation --quarter Q2_2026 --sets "Emerging Markets" India USD
python scripts/asteria_tools.py fi-metrics --portfolio PORTFOLIO_ID --trades trades.json
```

## Environment Data

Fetch only public GET endpoints exposed by the task environment or prompt:

- `/api/portfolios` and `/api/portfolios/{portfolio_id}/holdings`
- `/api/instruments/bonds` and `/api/issuers`
- `/api/market/energy`
- `/api/indices`, `/api/index-levels`, and `/api/index-levels/{index_id}`
- `/api/allocation/opportunity-sets`, `/api/allocation/prior-views`, and `/api/macro-signals`
- `/api/policies` only when the task prompt or environment access file exposes it

Join holdings to bonds by `instrument_id`, and bonds to issuers by `issuer_id`. Use portfolio and holdings `as_of_date` for lineage fields. Use policy ids and thresholds from current environment policy records when available; otherwise use explicit policy fields in the portfolio header, prompt, template, or payload.

## Fixed-Income Trades

For energy-credit buy packages:

- Apply the requested ticket count, action set, total notional, and split exactly.
- Select from current candidate bonds matching the requested sector/theme, usually `candidate: true` and `energy_linked: true` for energy tasks.
- Avoid issuer watchlist exposure for buys unless the prompt explicitly permits it.
- Prefer current positive energy themes, higher yield/carry, acceptable duration, and issuer/subsector diversification.
- Use IG or shorter-duration ballast when HY caps, watchlist rules, or duration bands would be stressed.

For risk-reduction rotations:

- Sell watchlist holdings first when the request asks to clear avoidable watchlist risk.
- Continue selling HY or other pressure holdings until HY cap, target reduction, and watchlist goals are met.
- Prefer keeping stronger carry when multiple non-watchlist HY holdings are otherwise similar.
- Fund buys with sale proceeds unless the request says new cash is available.
- Buy current candidate, non-watchlist, higher-quality bonds that preserve or improve duration fit and diversify issuer/sector risk.

Recompute post-trade metrics from final holdings:

- `total_market_value` = sum post-trade quantities.
- `hy_allocation_pct` = HY post-trade quantity / total market value * 100.
- Weighted duration or yield = sum(quantity * instrument metric) / total market value.
- Watchlist exposure = sum post-trade quantities whose issuer has `watchlist: true`.
- HY reduction in percentage points = pre-trade HY allocation minus post-trade HY allocation.

Sort trades exactly as the template states. Common fixed-income ordering is SELL before BUY, then `instrument_id` ascending within action; buy packages often require `instrument_id` ascending.

## Correlation Reviews

Use index ids from the request payload, holdings, or template universe. Use the requested level window, or the index metadata window when the prompt asks for the current monthly-level window.

Calculate monthly simple returns from consecutive levels:

```text
return[t] = level[t] / level[t-1] - 1
```

Then compute Pearson correlations on aligned return vectors. The return observation count is one less than the number of included monthly levels. Sort each `pair_id` alphabetically. Round correlations to the template precision, usually three decimals.

Use the highest positive correlation as the concentration pair and the lowest correlation as the diversifier pair. For concentration flags, compare against policy thresholds when available. If no threshold is exposed, treat clearly high regional overlap around the upper-0.8 range or higher as a concentration breach and negative correlations as diversifiers.

Map actions from the correlation finding and allowed enums:

- Trim or monitor the sleeve represented by the concentrated risk pair.
- Add diversifying sleeves with low/negative correlation, especially when their active allocation view is neutral-to-positive.
- Hedge currency sleeves when currency risk is part of the request and the current view weakens.

## Active Allocation Views

For each requested opportunity set:

1. Get its `asset_class` from `/api/allocation/opportunity-sets`.
2. Get the prior view from `/api/allocation/prior-views` for the requested target quarter and matching previous/prior quarter.
3. Get the current signal from `/api/macro-signals` for the target quarter.
4. Derive the current view from the signal score unless an official current-view field is exposed:
   - `score >= 0.35` -> `OW`
   - `score <= -0.35` -> `UW`
   - otherwise -> `N`
5. Derive conviction from absolute score:
   - `abs(score) >= 0.70` -> `HIGH`
   - `abs(score) >= 0.35` -> `MEDIUM`
   - otherwise -> `LOW`
6. Use the signal `rationale_code`.
7. Compare prior and current views on `UW < N < OW`: upward movement is `UP`, downward is `DOWN`, no movement is `UNCHANGED`.

Preserve the request's opportunity-set order unless the template declares a different order.

For portfolio-level overlays, choose the allowed code/action whose rationale best matches the dominant risks:

- Duration support plus credit/HY or China/EM pressure -> `DURATION_QUALITY_TILT` / `tilt_to_duration_quality`.
- Credit or HY spread risk without a duration-quality offset -> `CREDIT_RISK_REDUCTION` / `trim_credit_beta`.
- Broad positive growth/equity signals without material risk flags -> `EQUITY_BETA_EXTENSION` / `add_cyclical_equity_beta`.
- Dominant currency defensiveness or hedge need -> `CURRENCY_DEFENSIVE_HEDGE` / `add_currency_hedge`.
- No material active risk -> `NO_OVERLAY` / `hold_policy_weights`.

Order overlay rationale codes by business priority: duration/rate support, HY or credit-spread risk, China/EM dependence, diversifier support, then currency defense, unless the prompt specifies another priority.

## Multi-Asset Committee Files

Combine the relevant building blocks rather than inventing new logic:

- Use correlation rules for `correlation_summary`, concentration flags, and correlation-driven triggers.
- Use allocation-view rules for target opportunity sets, including prior view, signal score, view, change, conviction, and rationale.
- Set target sleeve actions from both signals: trim concentrated/risk-off sleeves, add diversifying OW sleeves, hedge currency sleeves when requested, and hold otherwise.
- Choose `correlation_cap_breach`, `hy_cap_pressure`, `duration_drift`, `watchlist_concentration`, or `committee_review` based on the active exception that best matches the computed metrics and prompt.
- Use `approve_with_monitoring` when the recommendation is actionable and constraints pass but a risk flag remains; use `reject_constraint_breach` only when proposed actions still fail required constraints.
