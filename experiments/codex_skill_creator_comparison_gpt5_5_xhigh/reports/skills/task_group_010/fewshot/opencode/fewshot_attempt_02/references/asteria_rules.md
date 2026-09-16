# Asteria Rules

These rules are the reusable core of the Asteria portfolio workflows.

## Source of truth

- Prefer the current API over stale worksheet notes.
- Use the local payload for request intent, output shape, and any explicit constraints.
- If the template asks for a lineage field such as `policy_id`, take it from the current records or the request payload; do not infer it from older worksheets.
- Do not guess ids, policy names, or thresholds when the live data or prompt does not supply them.

## Correlation reviews

- Use monthly simple returns: `return_t = level_t / level_(t-1) - 1`.
- Compute Pearson correlation on aligned return series.
- Sort every pair id alphabetically.
- For a summary object, use the highest positive correlation as the concentration pair and the lowest correlation as the diversifier or lowest pair.
- If the prompt asks for a concentration flag and no numeric threshold is stated, treat a clearly strong same-family overlap as a breach and document the basis in the answer fields.

## Allocation views

- Join the requested opportunity sets to the current-quarter prior-view table and the current macro-signal table.
- Keep rows in the exact request order.
- Map signal score to view with a simple three-band rule:
  - `score >= 0.35` -> `OW`
  - `score <= -0.35` -> `UW`
  - otherwise `N`
- Map signal score to conviction:
  - `abs(score) >= 0.65` -> `HIGH`
  - `abs(score) >= 0.35` -> `MEDIUM`
  - otherwise `LOW`
- Compare prior view to current view with the ordinal `UW < N < OW` to get `DOWN`, `UNCHANGED`, or `UP`.
- Copy the rationale code from the macro signal that matches the opportunity set and quarter.

## Credit trade packages

- Holdings quantities are USD millions and can be treated as current market value.
- Start with the current holdings, then apply sells and buys to get the post-trade book.
- Filter candidate bonds by the explicit prompt first: allowed actions, candidate eligibility, energy linkage if requested, rating bucket, watchlist avoidance, issuer diversification, subsector diversification, and duration or HY limits.
- Favor current environment records over stale candidate notes.
- Keep buy legs diversified across issuer and subsector when the prompt asks for two buys or similar small baskets.
- Recompute post-trade metrics from the updated book:
  - total market value = sum of position values
  - weighted metric = sum(position value * metric) / total market value
  - HY allocation = HY value / total value
  - watchlist exposure = sum of watchlisted positions
- For pass/fail booleans, use the live current constraints when available; otherwise check the prompt's explicit limits and stay conservative.

## Committee memos

- Use the strongest concentration pair from the requested correlation universe.
- Use the allocation views to show how the same macro signal maps into sleeve actions.
- Keep the output compact and aligned to the template. Do not add commentary outside the JSON object.
