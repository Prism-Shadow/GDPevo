---
name: asteria-portfolio-risk
description: Solve Asteria Investment Office finance tasks that require portfolio, credit-risk, equity-correlation, active-allocation, or committee JSON outputs from the shared Asteria API. Use when prompts mention Asteria portfolios, energy-credit tickets, fixed-income rebalance rotations, international equity correlation reviews, macro allocation views, or multi-asset committee files.
---

# Asteria Portfolio Risk

Use this skill to produce schema-exact JSON for Asteria portfolio/risk tasks. Treat the local prompt and payloads as the assignment scope and output contract; treat the shared Asteria API as the current book of record.

## Source Discipline

1. Read only the prompt, payloads under `input/`, and the environment access file supplied with the task.
2. Use the API base URL from the access file. Start with:
   - `/api/catalog`
   - `/api/policies`
   - `/api/portfolios`
   - `/api/portfolios/<portfolio_id>`
3. Pull the specific domain records needed:
   - Credit: `/api/instruments/bonds`, `/api/issuers`, and `/api/market/energy` for energy themes.
   - Correlation: `/api/indices` and `/api/index-levels/<index_id>`.
   - Allocation: `/api/allocation/opportunity-sets`, `/api/allocation/prior-views`, `/api/macro-signals`, and `/api/policies`.
4. If a local payload has stale snapshots, prior-week shortlists, old marks, or dated notes, use them only as context. Current API portfolio, security master, issuer, policy, index, and signal records override them.
5. If an answer field asks for data precedence and the payload conflicts with current API records, use `current_environment_over_stale_payload`.

## JSON Contract

1. Follow `answer_template.json` exactly: required keys, enum values, precision, item count, and ordering.
2. Return only the JSON object when the prompt requests JSON only.
3. Preserve requested portfolio IDs, task IDs, quarter labels, dates, and opportunity-set names exactly.
4. Round final numeric fields to the precision in the template. Keep booleans as booleans.
5. Honor ordering rules from the template over any natural sorting instinct. Common patterns:
   - Trade package: ascending `instrument_id` when requested.
   - Rotation trades: `SELL` before `BUY`, then ascending `instrument_id` within action.
   - Correlation pairs: index IDs inside each pair in alphabetical order.
   - Allocation rows: request payload order unless the template says alphabetical.

## Credit Trades And Rebalances

Load the portfolio detail, policies, bonds, and issuers. Join bonds to issuers on `issuer_id`; watchlist status comes from the issuer table, not from yield or theme tags alone.

For each holding or proposed trade, use `quantity_usd_m` or trade notional in USD millions as the weight.

Formulas:

```text
post_quantity = current_quantity + buys - sells
post_market_value = current_market_value + unfunded_buys - unfunded_sells
HY allocation % = 100 * sum(post_quantity where rating_bucket == "HY") / post_market_value
weighted duration = sum(post_quantity * modified_duration_years) / post_market_value
weighted YTM % = sum(post_quantity * yield_to_maturity_pct) / post_market_value
HY reduction pct points = current_HY_allocation_pct - post_HY_allocation_pct
watchlist exposure = sum(post_quantity where issuer.watchlist == true)
issuer concentration % = 100 * sum(post_quantity by issuer_id) / post_market_value
```

Use the portfolio's `constraints` first; if a needed field is absent there, use the matching policy block from `/api/policies`.

Selection rules:

1. For BUY candidates, require `candidate: true` unless the prompt explicitly permits non-candidates.
2. For energy-credit tasks, require `energy_linked: true` when the request is for energy-linked bonds.
3. Avoid watchlist issuers for new buys whenever the prompt or risk context says to avoid watchlist risk, even if the bond has high carry.
4. For risk-reduction rotations, sell current pressure points from the live portfolio, not stale memo quantities. Prioritize watchlist holdings, then high-yield holdings needed to meet the HY cap or target reduction.
5. Fund sells with current eligible non-watchlist candidates that preserve the duration band and improve the requested risk profile. Prefer investment-grade candidates for HY reduction tasks.
6. For income/carry tasks, among packages that pass hard constraints, prefer higher YTM and request-aligned themes. Use `/api/market/energy` to choose client-facing themes such as LNG export support, midstream stability, renewables rate relief, or avoiding refining/watchlist traps.
7. Check all relevant constraints after the full package, not trade by trade:
   - `hy_cap_pass`: post HY allocation is at or below `max_hy_allocation_pct`.
   - `duration_band_pass`: post weighted duration is inside `[min, max]`.
   - issuer diversification: issuer concentration is within the policy limit; if the field refers to selected issuers, avoid concentrating selected buys in one issuer.
   - subsector diversification: distinct selected subsectors meet `subsector_min_count_for_diversified`.
   - watchlist avoidance/clearing: no watchlist buys; if asked to clear watchlist exposure, sell watchlist holdings down to zero.

## Equity Correlation Reviews

Use the index universe and dates from the request/template, then load index levels for each `index_id`.

Calculation:

```text
monthly simple return_t = level_t / level_(t-1) - 1
return_observations = number_of_level_points - 1
correlation = Pearson correlation over aligned monthly simple returns
```

Rules:

1. Use consecutive monthly levels, inclusive of the requested level start and end dates.
2. Do not correlate raw levels. Do not use log returns unless the prompt says so.
3. Align by date across indices before calculating.
4. Round correlations to three decimals when requested.
5. `highest_positive` or concentration pair means the maximum Pearson correlation among eligible pairs.
6. `lowest` or best diversifier means the minimum Pearson correlation among eligible pairs, including negative correlations.
7. Apply policy thresholds from `/api/policies`:
   - high correlation breach if correlation is greater than or equal to `correlation_high_threshold`.
   - low/diversifying relationship if correlation is at or below `correlation_low_threshold`, or choose the lowest available pair when the template asks for a best diversifier.
8. For concentration codes, use China/Asia dependence when a China, EM, or Asia-Pacific relationship breaches the high threshold; use global/developed overlap for broad developed/global pairs; otherwise use no material concentration.
9. Sleeve actions should follow the finding: trim/monitor the concentrated sleeve, add/rotate toward diversifiers with supportive views, and hold where no action is justified.

## Active Allocation Views

Load opportunity-set taxonomy, policy mapping, prior views, and macro signals.

For each requested opportunity set:

1. Get `asset_class` from `/api/allocation/opportunity-sets`.
2. Get the macro signal for the target quarter and opportunity set.
3. Convert signal score to current view using `allocation_mapping.view_score_thresholds`:
   - score `>= OW_min` -> `OW`
   - score `<= UW_max` -> `UW`
   - otherwise -> `N`
4. Convert absolute score to conviction using `allocation_mapping.conviction_thresholds`:
   - `abs(score) >= HIGH_abs_min` -> `HIGH`
   - `abs(score) >= MEDIUM_abs_min` -> `MEDIUM`
   - below `LOW_abs_below` -> `LOW`
5. Use the macro signal's `rationale_code`.
6. Use `/api/allocation/prior-views` as the baseline prior view for the target/prior-quarter relationship.
7. Compute `change` with `allocation_mapping.view_rank`:
   - current rank > prior rank -> `UP`
   - current rank < prior rank -> `DOWN`
   - otherwise -> `UNCHANGED`
8. Include `signal_score` only when the template requests it, rounded to the specified precision.

Risk overlay selection:

1. Choose `DURATION_QUALITY_TILT` / `tilt_to_duration_quality` when duration support and credit-quality preference are both material, especially with HY underweight or HY valuation risk.
2. Choose `CREDIT_RISK_REDUCTION` / `trim_credit_beta` when credit-spread or HY risk dominates the request.
3. Choose `EQUITY_BETA_EXTENSION` / `add_cyclical_equity_beta` when broad equity growth signals dominate without offsetting risk flags.
4. Choose `CURRENCY_DEFENSIVE_HEDGE` / `add_currency_hedge` when currency defensive rationale dominates.
5. Choose `NO_OVERLAY` / `hold_policy_weights` only when signals are neutral or mixed without a material portfolio action.
6. Order overlay rationale codes by business priority: hard risk reduction first, then concentration/correlation risks, then duration/currency support, then growth/diversifier rationales.

## Multi-Asset Committee Files

When a task combines correlation and allocation:

1. Run the correlation workflow for the requested index set.
2. Run the allocation workflow for the requested opportunity sets and quarter.
3. Use the portfolio/API as-of date, not a stale local note date.
4. Set concentration flags from correlation-policy breaches.
5. Map target sleeve actions from both signals:
   - high concentration plus unfavorable/neutral view -> trim, monitor, or rotate.
   - low/negative correlation plus favorable view -> add.
   - currency sleeves -> hedge or hold according to the current view and committee context.
6. Use `correlation_cap_breach` as the rebalance trigger when the main issue is a high-correlation breach; use credit triggers only for credit-risk tasks; otherwise use `committee_review`.
7. Choose the next step from the template based on whether the proposed actions resolve or monitor the material flags without breaking policy.

## Common Pitfalls

- Do not use `output/answer.json`, run outputs, judge files, or any non-input artifacts.
- Do not trust stale local quantities, dates, HY percentages, or shortlists over API portfolio detail.
- Do not miss the issuer join for watchlist status.
- Do not let a high-yield or watchlist bond win solely because it has the highest yield.
- Do not calculate HY allocation from coupon, spread, or sector; use `rating_bucket == "HY"`.
- Do not use level count as return observations; returns are one fewer than levels.
- Do not forget alphabetical pair IDs even when the economic relationship is directional.
- Do not round intermediate calculations before deriving pass/fail flags.
- Do not invent enum strings. If the exact value is absent from the template, choose the closest allowed value rather than creating a new one.
