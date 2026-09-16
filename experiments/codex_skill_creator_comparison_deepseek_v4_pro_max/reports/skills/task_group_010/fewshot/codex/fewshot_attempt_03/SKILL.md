---
name: asteria-portfolio
description: Institutional portfolio analytics for the Asteria Investment Office shared environment. Supports energy credit trade construction, international equity correlation review, active allocation view derivation, fixed-income risk rebalancing, and multi-asset committee decisions. Use when the task references Asteria portfolios (PF-EN-*, PF-INT-*, PF-FI-*, PF-MA-*), the Asteria API at http://task-env:9010/, institutional credit/equity/allocation workflows, or when a local payload contains a request_id and a stale worksheet that must be reconciled against the current API environment.
---

# Asteria Portfolio Analytics

Support institutional portfolio workflows using the Asteria Investment Office shared API environment. Always treat the API as the current book of record; local payloads may contain stale marks.

## Core Rules

### Data Precedence

The shared Asteria API (`http://task-env:9010/`) is always the authoritative source. When a local payload date is earlier than the API `as_of_date` (2026-05-29), prefer API values. Report this in any `data_precedence` field as `"current_environment_over_stale_payload"`. When dates match or no conflict exists, use `"no_conflict_found"`.

### Template Conformance

Every task provides an `answer_template.json` in `input/payloads/`. Read it first — it defines the exact output shape, required keys, allowed enum values, numeric precision, and sort orders. Produce only the JSON object that conforms; no narrative outside it unless the prompt explicitly calls for it.

### Numeric Precision

Round every numeric field to the precision declared in the template (e.g., 1 decimal for USD millions, 2 decimals for percentages and duration, 3 decimals for correlations). Use standard `round()` semantics.

### Sorting Conventions

- Trade lists: sort by `action` (SELL before BUY), then `instrument_id` ascending within each action group. For BUY-only lists, sort ascending by `instrument_id`.
- Index pairs: sort alphabetically within each pair.
- Allocation view rows: follow the order in the request payload's `focus_opportunity_sets`.
- Diversification candidates and index sets: ascending alphabetical.

## API Endpoints

Full catalog: [references/api_reference.md](references/api_reference.md).

Key endpoints for the five standard workflow surfaces:

| Workflow | Primary Endpoints |
|---|---|
| Energy credit trade | `/api/portfolios/{id}/holdings`, `/api/instruments/bonds`, `/api/issuers`, `/api/market/energy`, `/api/policies` |
| Equity correlation review | `/api/indices`, `/api/index-levels`, `/api/index-levels/{id}`, `/api/policies` |
| Allocation view refresh | `/api/allocation/opportunity-sets`, `/api/allocation/prior-views`, `/api/macro-signals`, `/api/policies` |
| FI risk rebalance | `/api/portfolios/{id}/holdings`, `/api/instruments/bonds`, `/api/issuers`, `/api/policies` |
| Multi-asset committee | `/api/portfolios/{id}/holdings`, `/api/indices`, `/api/index-levels/{id}`, `/api/allocation/prior-views`, `/api/macro-signals`, `/api/policies` |

Always start by fetching the relevant policies (`/api/policies`) to know constraint thresholds, correlation windows, and allocation mapping rules.

## Deterministic Scripts

Use these bundled scripts when the task requires computed values. They produce JSON you can read programmatically.

### `scripts/compute_correlations.py`

Computes Pearson correlations from index-level JSON.

```bash
python3 scripts/compute_correlations.py <levels.json> <index_ids.txt>
```

`levels.json` is a JSON array of `{"index_id": "...", "levels": [{"date": "...", "level": number}]}` — fetch one `/api/index-levels/{id}` per index and combine. `index_ids.txt` lists index IDs, one per line. Outputs `return_observations` and all pair correlations rounded to 3 decimals, sorted alphabetically.

### `scripts/compute_portfolio_metrics.py`

Computes portfolio-level metrics from holdings + bond master.

```bash
python3 scripts/compute_portfolio_metrics.py <holdings.json> <bonds.json> [<issuers.json>]
```

Outputs `total_market_value_usd_m`, `hy_allocation_pct`, `weighted_modified_duration_years`, `weighted_yield_to_maturity_pct`, `watchlist_exposure_usd_m`, issuer and subsector exposure maps. Run once on the pre-trade holdings and once on the simulated post-trade holdings to compute deltas.

## Computation Methods

Details: [references/formulas.md](references/formulas.md).

### Pearson Correlation

Monthly simple returns: `r_t = level_t / level_{t-1} - 1`. Standard Pearson formula over the return series. 3-decimal rounding. The review window uses 12 monthly levels yielding 11 return observations.

### Post-Trade Portfolio Metrics

Simulate post-trade holdings: start from current portfolio, add BUY quantities, subtract SELL quantities. Weight metrics by notional. Use the bond master for rating, duration, and yield data per instrument.

### Allocation View Derivation

From the macro signal `score` in `/api/macro-signals` for the target quarter:

- `score ≥ 0.35` → `OW`, `score ≤ -0.35` → `UW`, otherwise `N`
- `|score| ≥ 0.7` → `HIGH` conviction, `0.35 ≤ |score| < 0.7` → `MEDIUM`, `< 0.35` → `LOW`
- Compare to prior quarter's view (from `/api/allocation/prior-views`) to set `change`: rank(OW)=1, rank(N)=0, rank(UW)=-1. Current > prior → `UP`, current < prior → `DOWN`, equal → `UNCHANGED`

### Constraint Checks

Read constraint thresholds from `/api/policies` (key varies by portfolio's `constraint_policy_id`):

- **HY cap**: post-trade HY allocation ≤ `max_hy_allocation_pct` (default 20%)
- **Duration band**: post-trade duration inside `duration_band_years` (default 3.0–5.0)
- **Issuer concentration**: no single issuer > `issuer_concentration_limit_pct` (default 12%)
- **Subsector diversification**: at least `subsector_min_count_for_diversified` distinct subsectors (default 2) among the selected instruments
- **Watchlist avoidance**: BUY trades must not target watchlisted issuers

### Correlation Concentration

- `china_asia_dependence_flag`: IDX_CHINA vs IDX_AC_ASIA_PAC_EX_JP correlation > 0.8
- `high_threshold_breached`: any pair correlation > `correlation_high_threshold` (0.8)
- `primary_code`: `CHINA_ASIA_DEPENDENCE` if china flag true, `GLOBAL_DEVELOPED_OVERLAP` if EM-WORLD > 0.8 without china dependence, `NO_MATERIAL_CONCENTRATION` otherwise

## Workflow Patterns

### Energy Credit Trade Construction

1. Fetch portfolio holdings, bond universe, issuers, energy market signals, and applicable credit policy
2. Filter to `energy_linked: true` and `candidate: true` bonds
3. Exclude watchlisted issuers
4. Rank candidates by yield-to-maturity within the desk's preferred exposures (e.g., LNG exporters, gas demand)
5. Select the required ticket count and total notional, ensure post-trade metrics satisfy all constraints
6. Position the trade thematically using the `sales_positioning` segment and theme enums from the template

### Equity Correlation Review

1. Fetch the index set's levels from `/api/index-levels/{id}` for each ID in the template's `allowed_values`
2. Compute all pairwise Pearson correlations using the script or equivalent manual computation
3. Identify `highest_positive` and `lowest` correlation pairs
4. Run the concentration check (china dependence, threshold breach)
5. Select diversification candidates (indices with low or negative correlations to the concentrated region)
6. Propose two sleeve actions (one trim, one add) targeting only the allowed `target_index_id` values

### Allocation View Refresh

1. Fetch opportunity-set taxonomy, prior-quarter views, and macro signals for the target quarter
2. For each opportunity set in the request's `focus_opportunity_sets`, derive `view`, `conviction`, and `change` from scores
3. Use the signal's `rationale_code` directly as each row's rationale
4. Derive the risk overlay by combining the most material risk signals across the book:
   - If duration-support signals are strong and HY/credit signals are negative → `DURATION_QUALITY_TILT`
   - If HY valuation risk dominates → `CREDIT_RISK_REDUCTION`
   - If equity growth signals are strong → `EQUITY_BETA_EXTENSION`
   - If dollar weakness signals dominate → `CURRENCY_DEFENSIVE_HEDGE`
   - Order rationale codes by business priority (highest priority first)

### Fixed-Income Risk Rebalance

1. Fetch portfolio holdings, bond universe, issuers, and credit risk reduction policy
2. Identify SELL candidates: HY-rated holdings (prioritize watchlisted), targeting sufficient notional to meet `target_hy_reduction_pct`
3. Identify BUY candidates: `candidate: true` bonds, IG-rated, non-watchlisted, with duration complementary to the portfolio
4. Simulate post-trade holdings and verify HY cap, duration band, and watchlist clearance
5. Set `risk_note_code` to the primary pressure addressed (`watchlist_concentration`, `hy_cap_pressure`, `duration_preservation`, `carry_tradeoff`, or `no_action`)

### Multi-Asset Committee Decision

1. Fetch indices and index levels for correlation, plus allocation prior views and macro signals
2. Compute correlations for the committee's focus indices (typically EM, China, India, LatAm)
3. Derive allocation views as in the allocation workflow for the committee's opportunity sets
4. Set `rebalance_trigger` based on the primary finding: `correlation_cap_breach` when high correlation is the issue, `hy_cap_pressure` for credit stress, `committee_review` for scheduled review
5. Set `portfolio_risk_concentration_flag` to `true` when correlation or credit flags fire
6. Set `next_step` based on constraint status: `approve_rotation` if clean, `approve_with_monitoring` if flagged but within limits, `defer_pending_risk_review` if borderline, `reject_constraint_breach` if constraints fail
