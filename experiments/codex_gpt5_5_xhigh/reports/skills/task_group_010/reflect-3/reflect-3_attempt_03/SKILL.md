# Reflect-3 Institutional Portfolio Workflow

Use this skill for Asteria-style portfolio tasks that combine current environment records, local task payloads, portfolio constraints, correlations, allocation views, and strict JSON answer templates.

## Source Precedence

- Treat the shared environment service as the current book of record for portfolios, policies, instruments, issuers, index levels, opportunity sets, prior views, and macro signals.
- Treat local task payloads as request context. If local payload values conflict with current environment records, use the current environment record and set any requested precedence/data-lineage field accordingly.
- Use the portfolio `as_of_date` or policy/signal `as_of_date` that matches the records actually used.
- Do not infer missing securities, issuers, thresholds, or enum labels. Query the relevant endpoint and copy identifiers exactly.

## Environment API Habits

- Start with the catalog when the available ids are unclear, then query only the endpoints needed for the requested output.
- Useful current-record endpoints are:
  - `/api/policies`
  - `/api/portfolios` and `/api/portfolios/<portfolio_id>`
  - `/api/instruments/bonds`
  - `/api/issuers`
  - `/api/market/energy`
  - `/api/indices`
  - `/api/index-levels`
  - `/api/allocation/opportunity-sets`
  - `/api/allocation/prior-views`
  - `/api/macro-signals`
- Equality filters may be available, but verify that filtered records still contain every field needed for calculations.
- Build JSON requests programmatically or validate them before submitting anywhere; malformed JSON can masquerade as scoring or data-quality trouble.

## Credit Trade And Rebalance SOP

1. Pull the current portfolio, current bond master, issuer watchlist records, and the applicable credit policy.
2. Join holdings and proposed trade candidates to bond metadata by `instrument_id`, then join issuer metadata by `issuer_id`.
3. For BUY eligibility, apply all request-specific filters such as `candidate: true`, sector or `energy_linked`, rating bucket, theme tags, and watchlist exclusion.
4. For SELL eligibility, use only current portfolio holdings unless the request explicitly allows external shorts or hedges.
5. Separate "new allocation" from "rotation":
   - New allocation increases post-trade market value by net buys.
   - Rotation usually keeps market value unchanged because sells fund buys.
6. Compute metrics from current environment quantities, not stale local snapshots:
   - `post_total_market_value = current_market_value + buys - sells`
   - `post_hy_allocation_pct = post_hy_notional / post_total_market_value * 100`
   - `weighted_modified_duration = sum(post_notional_i * duration_i) / post_total_market_value`
   - `weighted_yield_to_maturity = sum(post_notional_i * ytm_i) / post_total_market_value`
   - `hy_reduction_pct_points = current_hy_pct - post_hy_pct`
   - `post_watchlist_exposure = sum(post_notional_i where issuer.watchlist is true)`
7. Constraint booleans must report the calculated result, not the intended result. If a proposal leaves a cap breached, the pass flag is `false`.
8. For watchlist handling, exclude watchlist issuers from new buys when the request says to avoid them, and include all watchlist sell ids in ascending instrument order.
9. Prefer the lowest-turnover proposal that satisfies all hard constraints. If several proposals pass, use request language to choose between carry maximization, duration preservation, watchlist cleanup, and client-facing quality.

## Correlation SOP

1. Use the requested index ids and date window from the task payload or policy.
2. Use monthly simple returns from consecutive index levels:
   - `return_t = level_t / level_(t-1) - 1`
   - `return_observations = number_of_levels - 1`
3. Compute Pearson correlations on the return series, not on raw index levels.
4. Round correlations to the precision in the template, usually three decimals.
5. Sort ids inside every pair alphabetically by index id.
6. For "highest positive" and "lowest" pairs, evaluate all requested-pair combinations unless the prompt narrows the universe.
7. Use the policy high-correlation threshold for concentration flags and the low-correlation threshold for diversification labels when provided.
8. Diversification candidate lists should include both true low-correlation diversifiers and explicitly requested de-concentration tools when the allowed enum set includes both; keep the list sorted by index id.

## Allocation View Mapping

1. Use `/api/allocation/opportunity-sets` for the official `asset_class` of each opportunity set.
2. Use `/api/macro-signals` for the target quarter's `score` and `rationale_code`.
3. Use `/api/allocation/prior-views` for the prior view that corresponds to the target/prior-quarter lineage in the request.
4. Map signal score to active view using the allocation policy thresholds:
   - `OW` when score is greater than or equal to the OW threshold.
   - `UW` when score is less than or equal to the UW threshold.
   - `N` when score is between the thresholds.
5. Map conviction from absolute signal score:
   - `HIGH` at or above the high threshold.
   - `MEDIUM` at or above the medium threshold.
   - `LOW` below the medium threshold.
6. Compute `change` by comparing view ranks, usually `UW=-1`, `N=0`, `OW=1`:
   - rank increases -> `UP`
   - rank decreases -> `DOWN`
   - rank unchanged -> `UNCHANGED`
7. Preserve the request's opportunity-set order unless the template explicitly asks for another order.
8. For overlay fields, choose the enum that matches the dominant portfolio-level action, not merely the first positive signal. Duration support plus HY valuation pressure generally indicates a quality/duration tilt or credit-risk reduction; choose based on the requested action enum and rationale priority.

## Committee JSON SOP

- When a task combines correlation and allocation views, calculate the correlation section first, then let those results inform sleeve actions.
- Use `correlation_cap_breach` when the policy high-correlation threshold is breached and the template asks for a rebalance trigger.
- Set concentration flags from policy thresholds, not from qualitative concern text alone.
- Link sleeve actions to both the active view and the correlation role:
  - UW or concentration exposure often maps to `trim` or `rotate`.
  - OW with a diversifying role often maps to `add`.
  - unchanged OW can map to `hold` when the task asks for target actions rather than new trades.
  - Currency sleeves can use `hedge` when the current signal weakens a stale overweight or defensive note.
- Choose next-step enums according to constraint severity: use approval/monitoring when actions address the issue, and rejection/deferral only when constraints remain unresolved or required inputs are missing.

## Output Hygiene

- Return only the JSON object when the prompt says JSON only.
- Use exact enum strings from the answer template; do not invent synonyms.
- Include every required key, even when a flag is false or a list has one item.
- Apply the template's rounding precision after calculations.
- Keep booleans as JSON booleans, not strings.
- Sort arrays exactly as specified: request order, alphabetical id order, or action-specific order.
- For trade arrays that specify action ordering, follow the template even when normal alphabetical order would differ.
- Do not include narrative explanations, citations, comments, or calculation scratchwork in the answer JSON.

## Pitfalls To Avoid

- Do not use stale local snapshots for current market value, holdings, policy thresholds, or index windows.
- Do not buy a watchlist issuer when the request says to avoid watchlist risk, even if its yield is attractive.
- Do not assume the highest-yielding candidate is preferred; client-facing and risk-reduction requests may favor cleaner issuer status, diversification, and policy fit.
- Do not calculate correlations from index levels directly.
- Do not include all allowed enum values just because they are allowed; include only values supported by current records and the prompt.
- Do not silently force pass flags to `true`; flags are calculated outputs.
- Do not carry train-time feedback mechanisms into normal task solving. Use the environment data endpoints and the task's input/template only.
