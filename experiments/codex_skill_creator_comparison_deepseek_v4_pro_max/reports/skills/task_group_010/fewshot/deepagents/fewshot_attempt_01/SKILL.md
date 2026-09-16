---
name: asteria-portfolio-risk
description: Institutional portfolio risk analysis for the Asteria Investment Office. Covers energy-credit trade strategy, international equity correlation review, active allocation view refresh, fixed-income risk rebalance, and multi-asset committee decision linkage. Use when the task references Asteria portfolios, the Asteria Investment Office, or any portfolio ID starting with PF-EN-, PF-INT-, PF-FI-, or PF-MA-. Also use when the task provides an answer_template.json and a local request payload and expects JSON output computed from a shared Asteria API environment at http://task-env:9010/.
license: MIT
compatibility: designed for codex-cli
---

# Asteria Portfolio Risk

## Environment

The Asteria Investment Office API is available at:

    http://task-env:9010/

No authentication is required. All endpoints return JSON. Read
[references/api_reference.md](references/api_reference.md) for endpoint schemas
and field descriptions.

## Core Principle: Environment Precedence

Local request payloads may contain stale marks, outdated worksheets, or
preferences from earlier analysis. The API is the current book of record.
Always fetch current data from the API and treat it as authoritative over any
locally-provided snapshot. When the answer template includes a data_precedence
field, set it to "current_environment_over_stale_payload" unless the local
payload contains information not available from the API.

## API Inventory

Before starting any task, run:

    curl -s http://task-env:9010/api/catalog | python3 -m json.tool

This returns all available IDs: portfolios, policies, indices, bonds, issuers,
and opportunity sets.

After reading the catalog, fetch the specific data the task requires. Always
fetch the full bond universe (/api/instruments/bonds) and full issuer set
(/api/issuers) for any credit or portfolio task. Constraint checks depend on
watchlist status, rating buckets, and subsector classification from those lists.

For policy thresholds and constraint rules, read
[references/policy_reference.md](references/policy_reference.md).

## Computation Script

scripts/compute_metrics.py provides deterministic calculations:

**Pearson correlation from index levels:**
Pipe two JSON arrays of [date, level] pairs on stdin:

    echo JSON_ARRAYS | python3 scripts/compute_metrics.py pearson

Output: {"correlation": 0.915} rounded to 3 decimals.

**Post-trade portfolio statistics:**
Pipe a JSON object with holdings, bonds, issuers, and optional trades:

    python3 scripts/compute_metrics.py portfolio_stats < input.json

Output includes total_market_value_usd_m, hy_allocation_pct,
weighted_modified_duration_years, weighted_yield_to_maturity_pct, and
watchlist_exposure_usd_m.

## Task Workflows

### 1. Energy-Credit Trade Strategy

For PF-EN-* portfolios. The task provides a desk request with stale holdings
and preferences.

Steps:

1. Fetch portfolio holdings from /api/portfolios/{id}/holdings
2. Fetch all bonds from /api/instruments/bonds
3. Fetch all issuers from /api/issuers
4. Fetch energy market signals from /api/market/energy
5. Fetch policies from /api/policies
6. Filter candidate bonds: candidate=true, energy_linked=true,
   issuer watchlist=false
7. Select bonds aligned with desk preferences (LNG exporters, gas demand, etc.)
   that improve carry while staying inside constraints
8. Compute pre-trade then post-trade metrics with the script
9. Run constraint checks against the portfolio policy
10. Choose sales positioning segment and theme matching bond selections
11. Fill the answer template, rounding to template precision

### 2. International Equity Correlation Review

For PF-INT-* portfolios. The task provides a review window and index universe.

Steps:

1. Fetch portfolio holdings from /api/portfolios/{id}/holdings
2. Fetch all indices from /api/indices
3. Fetch index levels for every index in the universe from
   /api/index-levels/{index_id}
4. Filter levels to the requested window
5. For every pair of indices, compute Pearson correlation using the script
6. Identify the highest-positive and lowest correlation pairs
7. Assess concentration: check if any correlation exceeds 0.8 threshold
8. Identify diversification candidates with low correlation to concentrated
   sleeves
9. Propose exactly 2 sleeve actions (trim a concentrated sleeve, add a
   diversifier)
10. Fill the answer template; return_observations = number of monthly return
    data points (level count minus 1)

### 3. Active Allocation View Refresh

For CIO desk allocation tasks with target_quarter and prior_quarter.

Steps:

1. Fetch opportunity sets from /api/allocation/opportunity-sets
2. Fetch prior views from /api/allocation/prior-views, filtering for
   previous_quarter={prior_quarter} and quarter={target_quarter}
3. Fetch macro signals from /api/macro-signals for quarter={target_quarter}
4. Fetch policies from /api/policies
5. For each opportunity set in the focus list, look up its signal score
6. Map score to view using policy thresholds:
   score >= 0.35 -> OW, score <= -0.35 -> UW, otherwise -> N
7. Map abs(score) to conviction:
   >= 0.7 -> HIGH, >= 0.35 -> MEDIUM, < 0.35 -> LOW
8. Compare to prior view to determine change: UP/DOWN/UNCHANGED
9. Use rationale_code directly from the signal data
10. Determine risk overlay by scanning all signal scores for the dominant theme
11. Fill the answer template in request payload focus order

### 4. Fixed-Income Risk Rebalance

For PF-FI-* portfolios. The task provides a meeting memo with preferences and
a stale exception board.

Steps:

1. Fetch portfolio holdings from /api/portfolios/{id}/holdings
2. Fetch all bonds from /api/instruments/bonds
3. Fetch all issuers from /api/issuers
4. Fetch policies from /api/policies
5. Identify HY and watchlist positions to sell
6. Select eligible buys: candidate=true, issuer watchlist=false, appropriate
   rating and sector diversification
7. Build trades: SELL first, BUY second; sort by instrument_id within each
8. Compute post-trade metrics with the script
9. Check exception flags against the portfolio policy
10. Record watchlist handling
11. Choose the risk_note_code that characterizes the primary risk pressure

### 5. Multi-Asset Committee Decision

For PF-MA-* portfolios. Links correlation to allocation views.

Steps:

1. Fetch portfolio holdings from /api/portfolios/{id}/holdings
2. Fetch index levels for committee-specified index IDs
3. Compute correlations for the focused pairs
4. Fetch opportunity sets, prior views, macro signals, and policies
5. Produce allocation views for the requested opportunity sets
6. Determine sleeve actions from correlation and view synthesis
7. Set rebalance_trigger, portfolio_risk_concentration_flag, and next_step

## Precision and Rounding

Match the precision declared in each answer template. The script rounds to
2 decimals for percentages and durations, 1 decimal for USD millions, and
3 decimals for correlations. Adjust inline when the template differs.

## Constraint Check Rules

Apply these from the portfolio policy (credit_default or credit_risk_reduction):

- HY cap: hy_allocation_pct <= max_hy_allocation_pct (default 20%)
- Duration band: weighted duration within band min/max (default 3.0-5.0)
- Issuer diversification: no single issuer > 12% of post-trade MV
- Subsector diversification: at least 2 distinct subsectors among new buys
- Watchlist avoidance: no BUY ticket references a watchlisted issuer

For credit_risk_reduction: also verify HY reduction meets target_hy_reduction_pct.

See [references/policy_reference.md](references/policy_reference.md) for full
policy structure.
