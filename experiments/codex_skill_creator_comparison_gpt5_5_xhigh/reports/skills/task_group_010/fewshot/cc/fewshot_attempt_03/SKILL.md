---
name: asteria-portfolio-decision-json
description: Build Asteria Investment Office portfolio decision JSON from the shared task environment. Use when the user asks for energy-credit trade packages, regional correlation reviews, allocation-view refreshes, fixed-income rebalances, or committee packets for PF-* portfolios, especially when the prompt mentions stale worksheets, live portfolio records, policies, prior views, macro signals, bonds, issuers, or index levels.
---

# Asteria Portfolio Decision JSON

Use this skill to turn an Asteria request into a schema-perfect JSON object from live portfolio data.

## Source of truth

Treat the shared environment as authoritative. Use the local payload only for:
- the requested portfolio id
- the requested universe or candidate set
- the output template
- any narrative context the prompt adds

If the local payload or memo conflicts with the live environment, prefer the live environment and set the precedence field accordingly.

If the prompt mentions a stale worksheet, stale snapshot, earlier desk note, or similar, do not use those values for final numbers.

## Read first

1. Read `input/payloads/answer_template.json`.
2. Read the local request payload.
3. Query the live environment only for the data the schema needs.

Common endpoints:
- `/api/portfolios`
- `/api/portfolios/{portfolio_id}/holdings`
- `/api/policies`
- `/api/instruments/bonds`
- `/api/issuers`
- `/api/indices`
- `/api/index-levels`
- `/api/allocation/opportunity-sets`
- `/api/allocation/prior-views`
- `/api/macro-signals`
- `/api/market/energy`

Use the portfolio record to confirm `as_of_date`, `constraint_policy_id`, and the current market value. Map `constraint_policy_id` to the matching block inside `/api/policies` instead of assuming every portfolio uses the same limits.

## Pick the workflow from the template

Let the schema tell you which task you are in:

- Trade package or rotation:
  - Use portfolio holdings, bonds, issuers, market signals, and the relevant credit policy.
  - Pick only eligible buy candidates for new buys.
  - Use current holdings for sells.
- Correlation review:
  - Use index metadata and monthly index levels.
  - Compute correlations from monthly simple returns.
  - Use the exact index universe named in the template.
- Allocation views:
  - Use opportunity-set taxonomy, prior views, macro signals, and allocation policy.
  - Filter to the quarter named in the prompt.
- Committee packet:
  - Combine the correlation logic and the allocation-view logic.
  - Keep the correlation summary and sleeve actions aligned with the final view set.

## Live policy defaults in this environment

Confirm these against `/api/policies` before using them:
- Allocation mapping: `OW` if score >= 0.35, `UW` if score <= -0.35, otherwise `N`.
- Conviction: `HIGH` if absolute score >= 0.70, `LOW` if absolute score < 0.35, otherwise `MEDIUM`.
- Credit: max HY allocation 20.0%, duration band 3.0 to 5.0 years, issuer concentration limit 12.0%.
- Credit risk reduction: target HY reduction 4.0 percentage points.
- Correlation: high threshold 0.8, low threshold 0.2.

## Calculation rules

### Correlations

For monthly levels, compute simple monthly returns:

`return_t = level_t / level_(t-1) - 1`

Then compute Pearson correlation on the return series over the full requested window.

Rules:
- Sort index ids alphabetically inside each pair.
- For a global extreme-pair field, search only the indices in the template's requested set and pick the max or min correlation as named.
- For a named concentration/diversifier field, compute only within the focus list named by the prompt, then pick the strongest positive pair for concentration and the most negative pair for diversification unless the template says otherwise.
- `return_observations` is the number of monthly returns, usually `len(levels) - 1`.

### Allocation views

Derive each view from the live macro signal score and the allocation policy:
- score >= 0.35 -> `OW`
- score <= -0.35 -> `UW`
- otherwise -> `N`

Derive conviction from absolute score:
- abs(score) >= 0.70 -> `HIGH`
- abs(score) < 0.35 -> `LOW`
- otherwise -> `MEDIUM`

Derive change by comparing the new view to the prior-quarter view:
- stronger than prior -> `UP`
- weaker than prior -> `DOWN`
- same -> `UNCHANGED`

Filter prior views and macro signals to the quarter named in the prompt. Do not accidentally use a later quarter if the API returns more than one.

### Trade packages and rotations

For credit trades:
- Use current holdings for sells and live buy candidates for purchases.
- For new buys, start from the live candidate universe; do not use `candidate:false` instruments unless the task is explicitly about existing positions.
- Prefer eligible instruments that improve carry without breaking the live credit policy.
- Keep issuer and subsector diversification in mind.
- Avoid watchlisted names when the prompt or policy warns about them.
- Preserve the requested notional split exactly, then round to the template precision.

For post-trade metrics:
- `total_market_value_usd_m = current market value + buys - sells`
- `hy_allocation_pct = HY notional / post-trade market value`
- `weighted_modified_duration_years = sum(notional * duration) / post-trade market value`
- `weighted_yield_to_maturity_pct = sum(notional * ytm) / post-trade market value`

For fixed-income rebalance tasks, count only sold watchlisted instruments in `watchlist_sell_ids`.

### Committee packets

When the output combines correlation and allocation:
- Use the concentration pair and diversifier pair that best match the prompt's focus.
- Set the trigger to the dominant issue: correlation breach, HY pressure, watchlist concentration, or committee review.
- Set the next step to the action that matches the final risk posture after the sleeve actions.

## Ordering and formatting

Follow the template's order exactly.

Common ordering rules:
- trade tickets: sort by instrument id unless the template says action order first
- SELL before BUY when the template asks for action grouping
- allocation rows: follow the request payload's opportunity-set order
- pair ids: sort alphabetically inside each pair
- candidate lists: sort alphabetically unless the template says otherwise

Round numeric values only to the precision the template asks for:
- 1 decimal for trade notionals
- 2 decimals for portfolio metrics
- 3 decimals for correlations and signal scores

## Final sanity check

Before answering, verify:
- required keys are present
- the portfolio id matches the request
- the live `as_of_date` is used
- the output is valid JSON only
- no stale payload value leaked into a final numeric field
- the computed metrics and flags are internally consistent
