# Asteria Investment Office — Portfolio Analytics Skill

## Overview

This skill provides reusable patterns for working with the Asteria Investment Office shared environment to produce institutional portfolio analytics: credit trade strategies, equity correlation reviews, active allocation view refreshes, fixed-income risk rebalances, and multi-asset committee decision files.

## General Workflow

### 1. Read Task Inputs

Each task provides three input files:
- **`prompt.txt`** — the assignment statement, portfolio id, and what to produce
- **`payloads/answer_template.json`** — the required JSON output shape with field types, allowed values, precision rules, and sort orders
- **`payloads/*.json`** (desk request, review request, memo, etc.) — intake context that may contain stale marks, preferences, or candidate shortlists from an earlier worksheet

### 2. Query the Environment

The Asteria shared environment is the current book of record. Call its public read-only endpoints with HTTP GET to obtain current portfolio compositions, bond universes, issuer research, index levels, allocation taxonomy, prior views, macro signals, and policies.

- Portfolio summaries and holdings are at the portfolio-family endpoints.
- Bond candidate universes include `candidate` flags, energy-linked tags, credit ratings, sector/subsector classifications, duration, and yield-to-maturity.
- Issuer records carry watchlist status, credit outlook, and research tags.
- Index levels are monthly time series with a consistent date range.
- Prior views carry the last official quarter's allocation stance.
- Macro signals for each quarter include a numeric score, rationale code, and conviction drivers.
- Policy endpoints carry constraint thresholds: HY caps, duration bands, issuer concentration limits, correlation thresholds, view-score mapping rules, and conviction cutoffs.

### 3. Reconcile Data Precedence

Always treat the current environment service as authoritative over stale payload data. If a local payload provides a different portfolio market value, holding snapshot, or date than the environment, prefer the environment values. Record your data-precedence decision explicitly when the template requires it.

### 4. Select Bonds or Indices

When selecting candidates from the bond universe:
- Filter by the task's sector/theme requirements (e.g., `energy_linked: true`).
- Prefer `candidate: true` bonds that are not already held, unless the task explicitly permits adding to existing positions.
- Avoid issuers flagged as `watchlist: true` in issuer records when the task requires watchlist avoidance.
- Ensure issuer diversification (selected picks should have different issuers).
- Ensure subsector diversification (selected picks should belong to different subsectors).
- Compute post-trade weighted metrics: total market value, HY allocation percentage, weighted modified duration, and weighted yield to maturity.

### 5. Compute Weighted Portfolio Metrics

For a portfolio with holdings each having quantity `q_i`, duration `d_i`, and yield `y_i`:

- **Total market value** = sum of all `q_i` (including new trades)
- **Weighted duration** = `sum(q_i × d_i) / total_mv`
- **Weighted YTM** = `sum(q_i × y_i) / total_mv`
- **HY allocation** = `sum(q_i for HY-rated holdings) / total_mv × 100`

Round all outputs to the precision declared in the answer template.

### 6. Compute Pearson Correlations

For index correlation tasks:
- Retrieve the full monthly level series for each index in the review universe.
- Compute monthly simple returns: `(level_t − level_{t−1}) / level_{t−1}`.
- Compute Pearson correlation between each pair of return series.
- Identify the pair with the highest positive correlation (concentration risk) and the pair with the lowest/most-negative correlation (diversification).
- Sort pair identifiers alphabetically within each pair.
- Round correlation values to three decimal places.
- Count the number of return observations (one less than the number of levels).

### 7. Determine Active Allocation Views

For each opportunity set in the focus list:

1. **Obtain the prior view** from the prior-views endpoint for the target quarter.
2. **Obtain the macro signal score and rationale code** for the same quarter.
3. **Map score to view** using the policy's view-score thresholds (default: OW if score ≥ 0.35, UW if score ≤ −0.35, N otherwise).
4. **Determine change** by comparing the new view to the prior view:
   - UP if OW > N or N > UW (rank order: OW=1, N=0, UW=−1)
   - DOWN if the rank decreased
   - UNCHANGED if the rank is the same
5. **Determine conviction** from the absolute signal score using policy conviction thresholds (default: HIGH if |score| ≥ 0.7, MEDIUM if 0.35 ≤ |score| < 0.7, LOW otherwise).
6. **Use the rationale code** from the macro-signals endpoint for that opportunity set and quarter.
7. **Look up the asset class** from the opportunity-set taxonomy endpoint.

### 8. Design Rotation Trades

For fixed-income risk-rebalance tasks:
- Sell holdings that create watchlist risk or excessive HY concentration.
- Buy IG-rated candidates that preserve or extend duration within the CIO band.
- Compute post-trade HY%, duration, HY reduction in percentage points, and remaining watchlist exposure.
- Verify all exception flags pass: HY cap, duration band, target HY reduction met, watchlist cleared.
- Sort trades: SELL before BUY, then alphabetically by instrument_id within each action group.

### 9. Formulate Risk Overlays and Committee Decisions

For allocation or multi-asset tasks:
- Choose a risk overlay code that reflects the dominant theme across multiple views (e.g., credit risk reduction when HY signals are strongly negative, duration-quality tilt when duration views are positive while credit views are negative).
- Provide rationale codes in business priority order.
- For committee JSONs, link correlation findings to allocation views: high-correlation pairs suggest trimming, low/negative-correlation pairs suggest adding diversifiers.
- Set the portfolio risk concentration flag to `true` when any pairwise correlation exceeds the policy's high threshold.
- Choose a rebalance trigger that best describes the primary driver (correlation cap breach, HY cap pressure, duration drift, watchlist concentration, or committee review).
- Select a next-step action consistent with the overall risk picture.

### 10. Assembly Rules

- Follow the answer template exactly: required keys, allowed values, precision, sort order, and list lengths.
- Return only the JSON object; do not include narrative commentary outside it.
- Sort list items as directed by the template (alphabetically by id, by template-defined order, or by action group then id).
- Always use the environment's `as_of_date` for the `as_of_date` field.
- Use the policy identifier from the active policy record when the template requires a `policy_id`.

## Common Pitfalls

- **Stale payloads**: Local request files may contain older snapshots. Always cross-check against current environment data and prefer the environment.
- **Watchlist checks**: Verify watchlist status from issuer records, not from bond tags alone. A bond may carry a `WATCHLIST_RISK` theme tag even if its issuer research confirms watchlist status.
- **Rounding**: Compute with full precision, then round only the final value to the template's declared precision. Use standard rounding (round half to even, or as Python's `round()` does).
- **Sort order**: Alphabetical sorting of index/candidate ids is case-sensitive ASCII order. Apply sorting exactly as the template requires.
- **Constraint thresholds**: Policy thresholds (HY caps, duration bands, correlation highs/lows, view-score cutoffs) come from the policies endpoint and may differ between portfolios.

## Dependencies

- HTTP access to the Asteria Investment Office shared environment.
- Python with `json` and `math` modules for calculations (or equivalent).
- `curl` for API queries.
