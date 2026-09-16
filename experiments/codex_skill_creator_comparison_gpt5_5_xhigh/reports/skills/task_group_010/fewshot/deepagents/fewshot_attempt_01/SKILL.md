---
name: asteria-investment-office-json
description: Solve Asteria Investment Office JSON tasks that combine current portfolio records, holdings, bonds, issuers, index levels, policy thresholds, prior views, and macro signals. Use for strict JSON outputs such as credit trade packages, fixed-income rotations, correlation reviews, allocation view refreshes, or committee summaries.
---

# Asteria Investment Office JSON

## Workflow

1. Read the prompt, local payload, and answer template together. Identify the task family from the required output keys.
2. Use the shared Asteria environment as the source of truth. Treat local worksheet notes as stale unless the prompt explicitly elevates them.
3. Resolve the current portfolio from `/api/portfolios` and load current holdings from `/api/portfolios/{portfolio_id}/holdings`.
4. Pull task-specific data:
   - Credit trade or rotation tasks: `/api/instruments/bonds`, `/api/issuers`, `/api/policies`
   - Correlation tasks: `/api/indices`, `/api/index-levels`, `/api/policies`
   - Allocation view tasks: `/api/allocation/opportunity-sets`, `/api/allocation/prior-views`, `/api/macro-signals`, `/api/policies`
5. Follow the template exactly. Preserve required key order, list order, enums, and numeric precision.
6. Return only a JSON object.

## Task Patterns

- `trade_package` / `rotation`: honor fixed ticket counts, split notionals, sell-before-buy ordering, and any watchlist-avoidance rule in the prompt.
- `correlation_summary` / `extreme_pairs`: compute Pearson correlation from monthly simple returns over the requested level window. Sort pair ids alphabetically.
- `allocation_views`: align rows to the requested opportunity-set order. Derive `view`, `change`, and `conviction` from the active policy and the current macro signal score.
- Committee summaries that combine correlation and allocation logic: use the same current environment pass for both halves and keep the outputs consistent.

## Calculation Rules

- Read the active policy record and apply its thresholds rather than hard-coding numeric cutoffs.
- Compute `return_observations` as the number of monthly levels minus one.
- Prefer current environment data over stale payload values when they conflict.
- Sort any output lists exactly as the schema says, not by convenience.

## Credit Discipline

- Prefer eligible candidates with better carry, lower watchlist pressure, and acceptable duration.
- Keep the portfolio inside the policy's HY cap, duration band, issuer limit, and subsector diversification rules.
- Avoid watchlist buys unless the prompt explicitly allows them.
- For risk-reduction tasks, sell the most problematic current exposure first and fund the cleanest eligible replacements.
