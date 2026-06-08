---
name: asteria-portfolio-workflow
description: Solve Asteria Investment Office task_group_010 portfolio-risk JSON tasks using the public Asteria API. Use when a prompt references the shared Asteria environment, portfolios such as PF-EN, PF-FI, PF-INT, or PF-MA, energy-credit trade packages, fixed-income risk rotations, international equity correlation reviews, active allocation views, macro-signal mapping, or committee decision JSON outputs.
---

# Asteria Portfolio Workflow

## Core Workflow

1. Read only the task prompt, local request payloads, and answer template. Treat local payload snapshots, stale notes, and prior-week shortlists as context, not final marks.
2. Use the public API at `http://127.0.0.1:8036` as the current book of record. If filesystem access to environment docs is restricted, use `GET /` and `GET /api/catalog` for route discovery.
3. Fetch only the records needed for the requested portfolio, universe, quarter, and template fields.
4. Build the JSON exactly to the template: required keys, enum values, ordering rules, and declared rounding precision.
5. Prefer policy pass and committee intent over raw yield maximization. Current environment data always overrides stale local payloads.

## Public API Routes

Use these routes as the normal data surface:

- `GET /api/catalog` for available portfolio, policy, bond, issuer, index, and opportunity-set ids.
- `GET /api/policies` for top-level policy set id, credit limits, correlation thresholds, and allocation mapping thresholds.
- `GET /api/portfolios` and `GET /api/portfolios/<portfolio_id>` for current holdings, constraints, market value, and as-of date.
- `GET /api/instruments/bonds` for security master fields: candidate flag, energy linkage, rating bucket, duration, yield, subsector, issuer, and theme tags.
- `GET /api/issuers` for watchlist status and issuer research tags.
- `GET /api/market/energy` for energy pitch themes and current commodity signals.
- `GET /api/indices`, `GET /api/index-levels`, and `GET /api/index-levels/<index_id>` for index metadata and monthly levels.
- `GET /api/allocation/opportunity-sets`, `GET /api/allocation/prior-views`, and `GET /api/macro-signals` for allocation taxonomy, prior view comparison, and current signal scores.

## Credit And Bond Calculations

Treat `quantity_usd_m` and `notional_usd_m` as market value in USD millions.

- Total market value: current holdings plus BUY quantities minus SELL quantities.
- HY allocation percent: `100 * sum(quantity for bonds with rating_bucket == "HY") / total_market_value`.
- Weighted modified duration: `sum(quantity * modified_duration_years) / total_market_value`.
- Weighted YTM: `sum(quantity * yield_to_maturity_pct) / total_market_value`.
- Watchlist exposure: sum quantities whose bond issuer has `watchlist: true`.
- HY reduction percentage points: current HY allocation percent minus post-trade HY allocation percent.
- Duration and HY caps are inclusive. Use portfolio constraints when present; otherwise use the relevant policy object from `/api/policies`.
- Round only final numeric output fields to the template precision.

### Energy-Credit BUY Packages

For income-oriented energy sleeves, screen BUY candidates with:

- `candidate: true`
- `energy_linked: true`
- issuer not on watchlist
- current API record, not stale worksheet marks
- post-trade HY allocation and duration inside policy limits
- selected buy issuers distinct
- selected buy subsectors meeting the policy minimum, usually at least two

For two equal BUY tickets, size each ticket as `total_notional_usd_m / ticket_count`. Prefer a package that combines the strongest current theme with risk diversification. In the learned pattern, LNG/gas demand from a BlueGas-style bond plus a separate non-watchlist carry/diversifier beat long-dated oil/LNG worksheet ideas and watchlist yield traps. Use `sales_positioning.target_segment = "multi_asset_income"` when the local request names a multi-asset income client context, and use `theme = "lng_export_tailwind"` when LNG export/gas-demand signals drive the package.

### Fixed-Income Risk Rotations

For risk-reduction portfolios:

- Sell current watchlist holdings first.
- Sell enough additional HY pressure points to pass the HY cap and meet the target HY reduction, but do not liquidate all HY if a smaller rotation preserves carry and passes policy.
- Exclude watchlist BUY candidates even if they offer the highest carry.
- When a meeting memo provides a shortlist with several current eligible IG, non-watchlist candidates, prefer breadth across the eligible shortlist rather than concentrating only in the two highest-yield names. Allocate buys to fully fund sells and keep duration inside band.
- In the Lumen-style pattern, the standard rotation kept the non-watchlist consumer HY carry, sold the watchlist telecom bond plus the chemicals HY pressure point, and funded all three eligible IG diversifiers from the shortlist while excluding the watchlist telecom candidate.
- Use `risk_note_code = "watchlist_concentration"` when clearing watchlist exposure is a central reason for the trade, even if HY cap pressure is also present.

Follow the template's trade ordering exactly. If it says SELL before BUY, list all SELL trades first and sort instrument ids ascending within each action group.

## Equity Correlation Reviews

Use monthly simple returns from consecutive index levels:

```text
return_t = level_t / level_(t-1) - 1
```

Then calculate Pearson correlation on the return vectors. With 12 monthly levels, `return_observations` is 11. Filter the level window inclusively by the requested start and end dates, sort by date, and round correlations to three decimals.

Ordering rules:

- Sort `index_set` and pair ids with raw lexicographic id ordering. In this dataset, `IDX_ACWI_IMI` sorts before `IDX_AC_ASIA_PAC_EX_JP`.
- `highest_positive` is the pair with the maximum correlation.
- `lowest` or `best_diversifier` is the pair with the minimum correlation, including negative values.

Concentration and diversifier rules:

- Set `high_threshold_breached` when any relevant pair correlation exceeds `/api/policies.correlation.correlation_high_threshold`, usually `0.8`.
- Use `CHINA_ASIA_DEPENDENCE` when the breached relationship involves China, EM, or Asia Pacific ex Japan and the memo mentions China/Asia concentration.
- Include `IDX_LATAM` as a diversifier when it has the most negative or lowest correlations versus China/EM/Asia.
- Include `IDX_EM_EX_CHINA` as a structural de-China diversification candidate even when its raw correlations remain above the high threshold; this was an easy blind-pass miss.
- Do not include `IDX_INDIA` as a low-correlation diversifier when its China or Asia correlations breach the high threshold, even if India has a positive allocation signal.
- For a compact two-action sleeve plan with dedicated China and LatAm available, use `trim` on the China sleeve and `add` on Latin America, sorted by sleeve name. Keep EM ex-China in candidates unless the template or prompt asks for an EM rotation action.

## Allocation View Mapping

Use `/api/policies.allocation_mapping`:

- Current view: score `>= OW_min` maps to `OW`; score `<= UW_max` maps to `UW`; otherwise `N`.
- Conviction: absolute score `>= HIGH_abs_min` maps to `HIGH`; absolute score `>= MEDIUM_abs_min` maps to `MEDIUM`; otherwise `LOW`.
- Rationale code: copy from the matching `/api/macro-signals` record.
- Asset class: copy from `/api/allocation/opportunity-sets`.
- Prior view: use `/api/allocation/prior-views` where `quarter == target_quarter` and `opportunity_set` matches. The row's `view` is the prior-quarter view for change comparison.
- Change: compare current and prior view ranks from policy (`UW = -1`, `N = 0`, `OW = 1`): higher is `UP`, lower is `DOWN`, equal is `UNCHANGED`.
- Policy lineage: use the top-level `/api/policies.policy_id` such as `POLICY_SET_2026_05` when the output has a general `policy_id` lineage field. Use a subpolicy id only when the template explicitly asks for that subpolicy.

Risk overlay judgment:

- Choose `DURATION_QUALITY_TILT` with `tilt_to_duration_quality` when U.S. Treasuries or duration support is positive and Corporate HY is underweight on valuation risk.
- Include material supporting rationale codes in business priority order. For the learned Q2 allocation pattern, the overlay rationale included `DURATION_SUPPORT`, `HY_VALUATION_RISK`, and the material equity concentration code `CHINA_DEPENDENCE`.
- Choose `CREDIT_RISK_REDUCTION` only when the task is primarily a credit beta reduction overlay rather than a duration-quality tilt.

## Committee JSON Rules

For multi-asset committee tasks that combine correlation and allocation:

- Use the requested index subset for `correlation_summary`; do not search the full universe unless the prompt asks.
- `highest_concentration` is the highest positive pair in the subset. `best_diversifier` is the lowest pair in the subset.
- Set `rebalance_trigger = "correlation_cap_breach"` and `portfolio_risk_concentration_flag = true` when the concentration pair breaches the high threshold.
- Map target actions from active views and committee context: EM with `UW` and China-dependence rationale trims; India `OW` adds; Latin America `OW` adds.
- For a USD sleeve, use `hedge` when the request or stale note frames USD as a defensive offset and the current view falls to neutral, even though the allocation view is `N`. Do not default this case to `hold`.
- Use `next_step = "approve_with_monitoring"` when a correlation cap breach remains a live concentration flag but the proposed trim/add/hedge plan is acceptable for committee action.

## Common Pitfalls

- Do not read restricted environment folders when the public API provides the same records.
- Do not use stale local market values, stale quantities, or stale exception-board labels as the official book of record.
- Do not maximize bond yield by buying watchlist issuers or same-subsector pairs that fail the selected diversification checks.
- Do not omit `IDX_EM_EX_CHINA` from diversification candidates in China/EM concentration reviews.
- Do not output `POL_ALLOCATION_MAPPING` for a general lineage `policy_id`; use the top-level policy set id.
- Do not omit `CHINA_DEPENDENCE` from a broad Q2 risk overlay rationale when EM/China risk is one of the focus rows.
- Do not collapse a risk-reduction IG buy program to only two names when the memo's eligible shortlist contains three diversifying, non-watchlist IG candidates.
- Do not set the USD committee action to `hold` when the prompt frames the USD sleeve as a defensive hedge decision.
