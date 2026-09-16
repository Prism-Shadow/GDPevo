---
name: asteria-portfolio
description: Use the Asteria Investment Office API to produce credit trade strategies, equity correlation reviews, allocation view refreshes, and fixed-income risk rebalance proposals for institutional portfolios. Use when working with Asteria portfolio tasks that require querying the shared environment API, computing portfolio metrics, correlating index returns, mapping macro signals to allocation views, reconciling stale local payloads against live records, and outputting structured JSON responses.
---

# Asteria Portfolio

Work with the Asteria Investment Office shared environment to produce
institutional portfolio analysis outputs: credit trade packages, equity
correlation reviews, active allocation views, fixed-income rebalance
proposals, and multi-asset committee decision files.

## Environment

The Asteria API runs at `http://task-env:9010/` with no authentication.
Always query the live API for current data. Local payload files may contain
stale snapshots or preferences from earlier worksheets. When field values
conflict, the live API wins unless the payload schema explicitly marks a field
as intake-only (e.g. `requested_package`, `focus_opportunity_sets`).

**Policy set**: Query `/api/policies` once per task to read the active
`policy_id`, constraint thresholds, and allocation mapping rules.

## Core workflow

1. Read the local intake payload and the answer template to understand the
   required output shape, field enumerations, ordering rules, and numeric
   precisions.
2. Call the relevant API endpoints for current portfolio, bond, issuer, index,
   index-level, allocation, macro-signal, and policy records.
3. Reconcile stale payload values against live API data. Set the
   `as_of_date` field to the API's `as_of_date`. Flag data precedence
   when the template requires it (values: `current_environment_over_stale_payload`,
   `local_payload_over_current_environment`, `no_conflict_found`).
4. Apply computations (see [references/scoring_rules.md](references/scoring_rules.md)):
   - Monthly simple returns and Pearson correlation for index pairs.
   - Portfolio-level HY allocation, weighted duration, weighted YTM.
   - Signal-score to view, conviction, and change mappings.
5. Run constraint checks against the active policy (HY cap, duration band,
   issuer/subsector diversification, watchlist avoidance).
6. Produce the JSON output exactly matching the answer template's structure,
   field ordering, enum values, and numeric precision.

## Task patterns

### Credit trade construction

Used for energy-credit desks (PF-EN-ALTA, PF-EN-BOREAL) and credit risk
rebalance meetings (PF-FI-LUMEN).

- Query `/api/portfolios/{id}` for holdings and constraints.
- Query `/api/instruments/bonds` for the full bond universe.
- Query `/api/issuers` for watchlist status and credit outlook.
- For energy tasks also query `/api/market/energy` for commodity signals.
- Filter bonds by eligibility (energy-linked, candidate, watchlist avoidance,
  rating bucket preference). Select bonds that improve carry while staying
  inside HY cap and duration band.
- Compute post-trade portfolio metrics with
  `scripts/compute_portfolio_metrics.py`.

### Equity correlation review

Used for international equity correlation desks (PF-INT-NEXVEN, PF-INT-ORION).

- Query `/api/indices` and `/api/index-levels/{id}` for each index in the
  universe.
- Compute monthly simple returns: `(level_t / level_{t-1}) - 1` across the
  requested window. For a 12-month level window, there are 11 return
  observations (the first level date starts the window).
- Compute all pairwise Pearson correlations with
  `scripts/compute_correlation.py`.
- Identify extreme pairs (highest positive, lowest correlation).
- Flag concentration (e.g. China-Asia dependence when China correlates
  highly with broad EM or Asia Pacific indices).

### Allocation view refresh

Used for CIO allocation memos (Q2/Q3 2026 views).

- Query `/api/allocation/opportunity-sets` for the taxonomy.
- Query `/api/allocation/prior-views` for the prior-quarter views.
- Query `/api/macro-signals` for current signal scores and rationale codes.
- Apply [references/scoring_rules.md](references/scoring_rules.md) to map
  each signal score to a view (UW / N / OW), conviction (LOW / MEDIUM / HIGH),
  and change (UP / DOWN / UNCHANGED) versus the prior quarter.
- Select a risk overlay code and rationale codes based on the aggregate
  signal pattern.

### Multi-asset committee review

Combines correlation findings and allocation views for a single portfolio
(PF-MA-HELIO, PF-MA-CYGNUS, PF-MA-VEGA).

- Run both the correlation and allocation workflows for the named indices
  and opportunity sets.
- Produce sleeve actions (trim/add/hold/hedge/monitor/rotate) grounded in
  correlation evidence and allocation views.
- Set rebalance trigger, concentration flag, and next-step fields.

## Resources

### references/

- [api_reference.md](references/api_reference.md) -- All API endpoints with
  field schemas and example responses. Load when you need endpoint-specific
  details.
- [scoring_rules.md](references/scoring_rules.md) -- View mapping, conviction
  thresholds, change rules, and correlation formula. Load for any allocation
  or correlation task.

### scripts/

- `scripts/compute_correlation.py` -- Pearson correlation from two series of
  index levels. Pass two JSON arrays of `{date, level}` objects. Outputs a
  JSON object with correlation and observation count.
- `scripts/compute_portfolio_metrics.py` -- Portfolio-level HY allocation %,
  weighted modified duration, and weighted YTM. Pass a JSON array of holding
  objects (each with `instrument_id`, `quantity_usd_m`) and a JSON array of
  bond objects (each with `instrument_id`, `rating_bucket`, `modified_duration_years`,
  `yield_to_maturity_pct`). Outputs a JSON object with all three metrics.
