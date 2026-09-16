# Asteria Method

## Data Precedence

Use the local payloads to identify the requested portfolio, review window, opportunity sets, index universe, trade sizing, and required JSON shape. Use the live Asteria environment for current records. If the payload has stale worksheets, stale snapshots, or prior notes that conflict with the environment, prefer the environment and set any requested data-precedence field accordingly.

Useful endpoints are usually:

- `/api/portfolios`
- `/api/portfolios/{portfolio_id}/holdings`
- `/api/instruments/bonds`
- `/api/issuers`
- `/api/market/energy`
- `/api/indices`
- `/api/index-levels`
- `/api/index-levels/{index_id}`
- `/api/allocation/opportunity-sets`
- `/api/allocation/prior-views`
- `/api/macro-signals`
- `/api/policies` when available or named by the task

## Correlation Reviews

1. Use the requested level window from the payload or the policy record.
2. Sort each index level series by date and keep levels in the inclusive window.
3. Convert levels to monthly simple returns: `level[t] / level[t-1] - 1`.
4. Compute ordinary Pearson correlation for each requested index pair.
5. Report `return_observations` as the number of returns, not the number of levels.
6. Sort index IDs alphabetically inside pair fields. Sort requested index sets as directed by the template.
7. Use the policy correlation high threshold when deciding concentration flags. If unavailable, infer cautiously from the policy-like defaults in the environment rather than inventing a new threshold.

For concentration review fields, a high correlation involving China and broad EM or Asia exposure supports a China/Asia dependence flag. The lowest or most negative pair is the best diversification evidence. Structural candidates such as EM ex China can be useful even when their numeric correlation is not the absolute minimum.

## Allocation Views

Use macro signal scores and the allocation mapping policy:

- Score at or above the overweight threshold maps to `OW`.
- Score at or below the underweight threshold maps to `UW`.
- Scores inside the neutral band map to `N`.
- Absolute score above the high-conviction threshold maps to `HIGH`; inside the medium band maps to `MEDIUM`; below the medium threshold maps to `LOW`.

Compare the current view to the prior view using the policy rank mapping (`UW < N < OW`):

- Higher rank: `UP`
- Lower rank: `DOWN`
- Same rank: `UNCHANGED`

Use the macro signal's `rationale_code` directly. Use the opportunity-set taxonomy for `asset_class`. When a risk overlay is requested, prioritize duration support, high-yield valuation risk, and China-dependence rationales when they are present in the focused rows.

## Credit Trades and Rotations

Join holdings to bond instruments by `instrument_id`, then join bonds to issuers by `issuer_id`. Quantity fields are USD millions and can be treated as market value weights.

Post-trade calculations:

- Total market value: current holding quantity plus buys minus sells.
- High-yield allocation: post-trade quantity in bonds with `rating_bucket == "HY"` divided by total market value.
- Weighted duration: sum of post-trade quantity times modified duration divided by total market value.
- Weighted yield: sum of post-trade quantity times yield to maturity divided by total market value.
- Watchlist exposure: post-trade quantity whose issuer has `watchlist: true`.

For energy-credit buy packages, filter to current candidate bonds, avoid watchlist issuers, respect the requested ticket count and total notional, and test each candidate package against the credit policy. Prefer packages that improve carry while preserving duration, issuer diversity, subsector diversity, and client-suitable exposure. Strong LNG or gas themes are usually preferred when the energy market endpoint shows positive LNG or gas signals; avoid high-yield watchlist yield traps even when carry is high.

For fixed-income risk reductions, sell watchlist holdings first. If the request asks for high-yield reduction, sell additional lower-carry high-yield holdings only as needed to meet the reduction objective or fund eligible replacement buys. Replacement buys should be current candidates, avoid watchlist issuers, favor investment-grade quality, and keep duration inside policy.

## Committee Packages

Committee files often combine the correlation and allocation workflows:

- Use the requested index IDs to identify the highest concentration pair and best diversifier pair.
- Use the requested opportunity sets to build current allocation views with prior view, score, change, conviction, and rationale when required.
- Map underweight/concentration sleeves to `trim`, overweight/diversifier sleeves to `add`, neutral sleeves to `hold` or `monitor`, and defensive currency exposure to `hedge` when the committee is explicitly focused on hedging or prior defensive exposure has been reduced.
- Use a correlation-cap trigger when high-correlation concentration breaches the policy threshold; otherwise use the template's closest committee-review or monitoring code.
