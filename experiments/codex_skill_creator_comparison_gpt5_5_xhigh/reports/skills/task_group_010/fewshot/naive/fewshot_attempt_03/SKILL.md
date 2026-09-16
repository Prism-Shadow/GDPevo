---
name: asteria-investment-office-solver
description: Solve Asteria Investment Office JSON tasks by combining local payload contracts with the live read-only Asteria environment.
---

# Asteria Investment Office Solver

Use this skill for tasks that ask for Asteria Investment Office portfolio, credit-risk, correlation, allocation-view, or committee JSON answers. The local task files define the requested shape and focus; the shared environment is the current book of record.

## Workflow

1. Read `prompt.txt`, every JSON file in `input/payloads/`, and especially `answer_template.json`.
2. Fetch current data from `http://task-env:9010/` unless the task gives another base URL. Use only read-only endpoints. Never call a judge or write endpoint.
3. Treat the environment as authoritative for portfolio holdings, marks, policy thresholds, security master data, issuer watchlist status, macro signals, and index levels. Use local payloads for requested portfolio ids, windows, focus sets, ticket counts, ordering, and schema constraints. If a local payload says it is stale or has an older as-of date, the correct precedence is current environment over stale payload.
4. Build the answer exactly to `answer_template.json`: no extra prose, no missing required fields, declared ordering, and numeric rounding at the requested precision.
5. Prefer deterministic calculation over narrative inference. When the template is one of the common Asteria patterns, run the helper:

```bash
python3 skill/asteria_helper.py /path/to/task/input
```

The helper prints a JSON draft to stdout. Inspect it against the template and the prompt before final submission.

## Environment Endpoints

The recurring endpoints are:

- `/api/policies`
- `/api/portfolios` and `/api/portfolios/{portfolio_id}`
- `/api/portfolios/{portfolio_id}/holdings`
- `/api/instruments/bonds`
- `/api/issuers`
- `/api/market/energy`
- `/api/indices`
- `/api/index-levels` or `/api/index-levels/{index_id}`
- `/api/allocation/opportunity-sets`
- `/api/allocation/prior-views`
- `/api/macro-signals`

## Core Calculations

Credit metrics:

- Apply trades to current environment holdings, not stale local snapshots.
- Treat USD-million quantities as market-value weights unless a task states otherwise.
- High-yield allocation is `post_trade_hy_market_value / post_trade_total_market_value * 100`.
- Weighted duration and yield use post-trade bond notionals and the instrument fields `modified_duration_years` and `yield_to_maturity_pct`.
- Watchlist exposure is post-trade notional whose issuer has `watchlist: true`.
- Constraint flags come from the portfolio constraint object or `/api/policies`: HY cap, duration band, issuer concentration, subsector diversification, target HY reduction, and watchlist clearance.

Correlation metrics:

- Use the requested monthly index-level window, inclusive of start and end dates. If the payload names a "current" window without dates, use the correlation policy dates.
- Convert levels to monthly simple returns: `level[t] / level[t-1] - 1`.
- Pearson correlations use all consecutive return observations in the window.
- Select pair ids as unordered pairs, sort ids alphabetically inside each pair, and round correlations only after choosing extremes.
- `highest_positive` or `highest_concentration` is the maximum correlation; `lowest` or `best_diversifier` is the minimum correlation.
- A high-threshold breach is any relevant pair at or above the policy high threshold. China/Asia/EM overlap should be classified as China dependence when the requested universe contains dedicated China plus EM or Asia exposure and their correlation breaches the high threshold.

Allocation views:

- Join `/api/allocation/opportunity-sets`, `/api/allocation/prior-views`, `/api/macro-signals`, and `/api/policies`.
- Map macro signal score to view with policy thresholds: OW at or above the OW threshold, UW at or below the UW threshold, otherwise N.
- Map absolute score to conviction with policy conviction thresholds.
- Compute change by comparing rank `UW=-1`, `N=0`, `OW=1` against the prior view for the same requested quarter.
- Keep allocation rows in the payload-requested order unless the template declares another order.

Decision heuristics:

- Energy-credit buy packages should use current candidate bonds, avoid watchlisted issuers, respect issuer/subsector diversification, keep HY and duration constraints, and balance carry with the client theme in the request. LNG/gas and midstream themes are preferred only when current market signals and payload preferences support them.
- Risk-reduction rotations should sell watchlisted holdings first, then the smallest additional HY pressure positions needed to meet HY and target-reduction rules. Replacement buys should avoid watchlist issuers, prefer current eligible IG candidates, and preserve duration inside the policy band.
- Committee tasks generally combine the correlation breach signal with allocation views: trim UW concentration sleeves, add OW diversifiers, hedge currency sleeves when the current view has deteriorated or is defensive, and use monitoring when constraints are met but correlation risk remains elevated.

## Helper

See [`asteria_helper.py`](asteria_helper.py). It is a portable, standard-library-only assistant for the recurring Asteria schemas. It does not contain stored example answers; it recomputes from the current task input and live environment.
