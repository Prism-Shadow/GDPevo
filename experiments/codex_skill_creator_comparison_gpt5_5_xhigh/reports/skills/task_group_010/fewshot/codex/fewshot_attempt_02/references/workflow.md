# Workflow Notes

## Source Priority

1. Use current Asteria environment records first.
2. Use the request payload for scope, ordering, and required fields.
3. Treat local notes, stale snapshots, and memo commentary as context only.

## Common Endpoints

- `GET /api/portfolios` for portfolio metadata, as-of date, constraint policy, and current book value.
- `GET /api/portfolios/{portfolio_id}/holdings` for current positions and sleeve mapping.
- `GET /api/instruments/bonds` for bond candidates, rating bucket, duration, YTM, spread, energy linkage, and watchlist indicators.
- `GET /api/issuers` for issuer watchlist status, outlook, sector, and subsector.
- `GET /api/indices` and `GET /api/index-levels` for index universe and monthly level series.
- `GET /api/allocation/opportunity-sets`, `GET /api/allocation/prior-views`, and `GET /api/macro-signals` for allocation-view tasks.

## Correlation Tasks

- Compute monthly simple returns from consecutive index levels.
- Use Pearson correlation on the return vectors.
- Round correlations to three decimals.
- Sort pair ids alphabetically.
- For review windows, report the number of return observations, not the number of levels.

## Trade and Rotation Tasks

- Anchor the trade list to current holdings and live bond metadata.
- Prefer current eligible names over stale desk candidates when they conflict.
- Avoid watchlist exposure unless the prompt explicitly allows it.
- Keep trade ordering exactly as the template specifies, usually SELL before BUY and then by `instrument_id`.
- Recompute post-trade metrics from the current book plus the proposed trades.

## Allocation Tasks

- Join the requested opportunity sets to current prior views and macro signals for the target quarter.
- Carry forward the current signal score when the template asks for it.
- Derive `view`, `change`, `conviction`, and `rationale_code` from the live records, not from the local memo.
- Preserve the request order for the output rows.

## Committee Tasks

- Combine the correlation finding with the allocation outputs.
- Use the concentration pair to justify the rebalance trigger.
- Keep the next-step label consistent with the risk flag and monitoring posture.
