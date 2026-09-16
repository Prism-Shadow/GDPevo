# Asteria Workflow Reference

## Data Precedence

Current environment data wins over stale local payloads or memo notes. If a prompt says the worksheet may be stale, do not trust the local snapshot for final holdings, marks, or scores.

## Live Endpoints

- `GET /api/portfolios`
- `GET /api/portfolios/{portfolio_id}/holdings`
- `GET /api/instruments/bonds`
- `GET /api/issuers`
- `GET /api/market/energy`
- `GET /api/indices`
- `GET /api/index-levels/{index_id}`
- `GET /api/allocation/opportunity-sets`
- `GET /api/allocation/prior-views`
- `GET /api/macro-signals`
- `GET /api/policies`

## Policy Thresholds

- Allocation mapping: `OW` if score is at least `0.35`, `UW` if score is at most `-0.35`, otherwise `N`.
- Conviction: `LOW` if `abs(score) < 0.35`, `MEDIUM` if `0.35 <= abs(score) < 0.70`, `HIGH` if `abs(score) >= 0.70`.
- View rank: `UW = -1`, `N = 0`, `OW = 1`.
- Correlation review window: `2025-05-30` to `2026-04-30`.
- Correlation thresholds: high threshold `0.8`, low threshold `0.2`.
- Credit default and risk reduction: duration band `3.0` to `5.0` years, issuer concentration limit `12.0%`, max HY allocation `20.0%`, minimum diversified subsectors `2`, HY reduction target `4.0` percentage points for the risk-reduction policy.

## Core Calculations

- Monthly simple return: `(level_t / level_{t-1}) - 1`.
- Pearson correlation: use aligned monthly return series, not raw levels.
- Return observations: the count of monthly return periods, which is one less than the number of level points in the window.
- Pair ids: always sort the two ids alphabetically before writing them.
- Highest concentration pair: the highest positive correlation in the requested universe.
- Best diversifier pair: the lowest correlation in the requested universe.

## Output Patterns

- Allocation rows: keep the request order, pull `prior_view` from the prior-view feed, map `view` from the signal score thresholds, compute `change` from the view-rank delta, and copy the current-quarter `rationale_code` from the matching macro signal.
- `policy_id`: use the top-level policy bundle id from `/api/policies`, not the nested credit or correlation sub-policy ids.
- Credit trades: prefer current eligible candidates, current holdings, issuer watchlist status, rating bucket, and duration band. Sort `SELL` before `BUY`, then by `instrument_id`.
- Energy trades: prefer live energy-linked candidates with strong carry or defensive carry themes; avoid stale worksheet marks when current records disagree.
- Committee outputs: use the correlation result to judge concentration, then choose sleeve actions that match the requested role (`trim` for risk reduction, `add` for positive sleeves, `hedge` for a defensive offset).
