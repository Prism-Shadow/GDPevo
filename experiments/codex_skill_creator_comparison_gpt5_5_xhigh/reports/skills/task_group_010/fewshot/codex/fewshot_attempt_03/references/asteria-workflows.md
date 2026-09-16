# Asteria Workflows

## Source Precedence

Use current environment data for records that can change: portfolio market value and holdings, as-of dates, policy thresholds, policy ids, instrument eligibility, issuer watchlist status, index levels, prior views, and macro signal scores. Use local payloads for request intent and output requirements. Treat stale snapshots, shortlists, and desk notes as hints until verified against the environment.

If the prompt and template disagree, satisfy the business objective from the prompt while preserving the template's JSON shape and allowed values. If a field asks for an as-of date, use the current environment date for the records used in the calculation.

## Endpoint Map

Read the task's `environment_access.md` for the base URL and credentials. Common Asteria endpoints are:

- `GET /api/portfolios`: portfolio summaries, market value, strategy, current as-of date, and constraint policy id.
- `GET /api/portfolios/{portfolio_id}/holdings`: current holdings and quantities for one portfolio.
- `GET /api/policies`: current policy set, allocation mapping, correlation thresholds, credit limits, and policy id.
- `GET /api/instruments/bonds`: bond security master, candidate flag, sector/subsector, rating bucket, duration, yield, and theme tags.
- `GET /api/issuers`: issuer watchlist status, credit outlook, sector, and research tags.
- `GET /api/market/energy`: energy-market context for energy-credit decisions when requested.
- `GET /api/indices`: index metadata and available level windows.
- `GET /api/index-levels/{index_id}`: monthly level series for one index.
- `GET /api/allocation/opportunity-sets`: official opportunity-set taxonomy and asset classes.
- `GET /api/allocation/prior-views`: prior active views and convictions by quarter and opportunity set.
- `GET /api/macro-signals`: signal scores, drivers, and rationale codes by quarter and opportunity set.

Prefer narrow portfolio or index-specific endpoint calls once the request identifies the required ids.

## Correlation Calculations

1. Restrict each index level series to the requested start and end dates, inclusive.
2. Compute monthly simple returns from consecutive levels: `return_t = level_t / level_t_minus_1 - 1`.
3. Align return observations by date across indexes. The return observation count is the number of aligned monthly return rows.
4. Compute Pearson correlation for every requested pair using unrounded returns. Round correlation fields only when writing the final JSON.
5. Sort ids inside each pair alphabetically. Sort pair lists according to the answer template, not by calculation order.
6. Select the highest-concentration pair as the largest positive correlation unless the template names a narrower universe. Select a diversifier or lowest pair as the smallest correlation among eligible pairs. Use current policy thresholds for concentration flags.

## Allocation View Mapping

Join opportunity sets, prior views, macro signals, and policy mapping by requested quarter and opportunity set.

- `asset_class`: take from the opportunity-set taxonomy.
- `view`: map the macro signal score using the current policy's positive, negative, and neutral score thresholds.
- `conviction`: map the absolute signal score using the current policy's conviction thresholds.
- `rationale_code`: take from the macro signal row unless the prompt provides a stricter enum mapping.
- `change`: compare current and prior views with the policy view rank. Positive rank movement is `UP`, negative is `DOWN`, zero is `UNCHANGED`.
- `prior_view`: include the prior view if the template asks for it.
- `signal_score`: round to the template precision after using the raw score for view and conviction mapping.

Preserve the opportunity-set order specified by the request payload or template. Use the current policy-set id when a policy id field is required.

## Credit Trade And Rotation Calculations

Build a joined security table from portfolio holdings, bond instruments, and issuers. Classify each position by rating bucket, issuer watchlist status, sector, subsector, duration, yield, and candidate eligibility.

For BUY packages:

- Respect requested action type, ticket count, total notional, split rule, and funding source.
- Filter to current candidates that match the requested sector or theme. Verify candidate status and watchlist status from the environment, not the local shortlist.
- Prefer higher carry only after hard constraints pass. For client-facing income requests, avoid watchlist yield traps and choose themes supported by the selected bonds' current tags.

For rotations:

- Identify current holdings that create high-yield, watchlist, duration, or concentration pressure.
- Sell enough current pressure exposure to satisfy the target reduction and clear avoidable watchlist exposure.
- Buy eligible replacement candidates that preserve the requested duration band, avoid watchlist issuers, and keep net notional consistent with the funding instruction.

Compute post-trade positions by adding buys and subtracting sells from current holdings. Do not allow negative quantities. Treat quantities in USD millions as the weighting base unless the prompt provides a separate market value field.

Common metrics:

- Total market value: sum post-trade quantities, adjusted for new funding or self-funded rotation.
- High-yield allocation percent: post-trade quantity in high-yield instruments divided by total post-trade market value, times 100.
- Weighted duration and yield: quantity-weighted averages from current instrument fields.
- High-yield reduction: pre-trade high-yield allocation minus post-trade high-yield allocation.
- Watchlist exposure: post-trade quantity for issuers with current watchlist status.
- Issuer concentration: issuer post-trade quantity divided by total post-trade market value, times 100.

Set pass/fail flags from the current policy thresholds. Evaluate selected-issuer and selected-subsector diversification with the template wording and the active credit policy.

## Committee Decisions

When a committee output links multiple signals, compute each component independently before assigning summary fields.

- Correlation-driven concentration flags come from the live index-level correlation workflow and current thresholds.
- Target sleeve actions should follow the computed risk result and active view: trim concentrated or deteriorating sleeves, add diversifying or positive-view sleeves, hedge or neutralize currencies when the current view weakens but risk context still matters, and monitor when neither an add nor trim is justified.
- Rebalance trigger should name the dominant computed exception. Next step should reflect whether the proposed action passes constraints, requires monitoring, or should be deferred.

## Final JSON Check

Before returning:

1. Compare every top-level and nested key against `answer_template.json`.
2. Confirm required list lengths and item order.
3. Confirm enum values are copied exactly from the template.
4. Confirm pair ids, trade lists, and opportunity-set rows follow the stated ordering rule.
5. Confirm numeric precision and that numbers remain JSON numbers.
6. Confirm no explanatory text surrounds the JSON.
