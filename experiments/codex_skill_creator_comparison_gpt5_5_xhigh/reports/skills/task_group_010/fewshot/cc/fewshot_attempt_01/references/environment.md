# Asteria live environment

Base URL: `http://task-env:9010`

No auth is required.
Use `GET` only.

## Endpoints

- `/api/portfolios`
- `/api/portfolios/{portfolio_id}/holdings`
- `/api/instruments/bonds`
- `/api/issuers`
- `/api/market/energy`
- `/api/indices`
- `/api/index-levels/{index_id}`
- `/api/allocation/opportunity-sets`
- `/api/allocation/prior-views`
- `/api/macro-signals`
- `/api/policies`

## Notes

- `/api/portfolios` includes the live `as_of_date`, current market value, holding count, and `constraint_policy_id`.
- `/api/portfolios/{portfolio_id}/holdings` is the current book of record for the portfolio sleeve.
- `/api/instruments/bonds` includes candidate flags, ratings, watchlist tags, subsectors, and yield/duration data.
- `/api/issuers` shows issuer watchlist status and credit outlook.
- `/api/market/energy` provides live macro theme and signal context for energy-credit tasks.
- `/api/index-levels/{index_id}` returns a monthly level series. Convert levels to simple returns before computing Pearson correlations.
- `/api/allocation/prior-views` and `/api/macro-signals` drive the allocation-view tasks.
- `/api/policies` returns the live thresholds and policy ids. Use it instead of hard-coding cutoffs.
- When live data disagrees with the local memo, treat the live data as authoritative.
