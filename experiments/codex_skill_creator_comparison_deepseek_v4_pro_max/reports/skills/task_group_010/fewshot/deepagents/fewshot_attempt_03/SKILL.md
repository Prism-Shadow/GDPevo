---
name: asteria-investment-office
description: "Institutional portfolio risk and allocation workflows for the Asteria Investment Office shared environment. Use for fixed-income credit trades, international equity correlation reviews, active allocation view refreshes, credit risk rebalances, and multi-asset committee decisions. The environment exposes REST endpoints for portfolios, bonds, issuers, indices, index levels, policies, allocation taxonomy, prior views, macro signals, and energy markets. Task prompts reference client desks (energy credit, CIO, risk, investment committee) and provide structured answer templates. Do not use for general portfolio analytics or other investment data providers."
license: MIT
compatibility: designed for deepagents-code
---

# Asteria Investment Office

Work with the shared Asteria Investment Office environment to produce
portfolio-risk and allocation outputs. Every task provides an answer template
JSON — conform to its exact structure, key ordering, allowed values, and
precision.

## Core Principle: API Over Local Payloads

Local task payloads (desk_request, review_request, risk_meeting_memo, etc.)
are intake context only. They may carry stale marks, worksheet snapshots, or
preferences from earlier dates. The current environment API is the book of
record. When values differ, prefer the API and set the `data_precedence` field
to `current_environment_over_stale_payload` when the template includes it.

## Environment Setup

Read the `environment_access.md` file provided with each task for the base URL.
All endpoints are GET with no authentication. Start every task by reading the
API landing page (`GET /`) for endpoint discovery.

API reference: [references/api.md](references/api.md). Load it when endpoint
details or field schemas are needed beyond what the task payload describes.

## Scripts

### Correlation Computation

[scripts/correlation.py](scripts/correlation.py) — Computes Pearson correlation
of monthly simple returns from two index-level series.

Usage: pipe a JSON object with `levels_a` and `levels_b` (each an array of
`{date, level}` objects) to stdin. Outputs `{correlation, return_observations}`.

Use this script for all pairwise index correlations. Do not implement correlation
manually. The script guarantees 3-decimal rounding consistent with the policy
thresholds.

### Portfolio Weighted-Average Metrics

[scripts/weighted_metrics.py](scripts/weighted_metrics.py) — Computes
post-trade / post-rotation portfolio metrics from enriched holding-level data.

Usage: pipe a JSON object with `holdings` (array of `{quantity_usd_m, instrument}`
where `instrument` is the full bond object from `/api/instruments/bonds`) to
stdin. Outputs `total_market_value_usd_m`, `hy_allocation_pct`,
`weighted_modified_duration_years`, `weighted_yield_to_maturity_pct`. All
values rounded to 2 decimal places.

Build the input by merging current portfolio holdings with proposed trades
(adding BUY quantities, removing SELL quantities) and attaching the full bond
record to each holding.

## Workflows

### Energy Credit Trade Strategy

When the prompt requests a trade package for an energy credit portfolio:

1. Read the answer template for required structure, precision, and allowed values.
2. Fetch `/api/portfolios/{portfolio_id}/holdings` for current positions.
3. Fetch `/api/instruments/bonds` for the full bond universe.
4. Fetch `/api/issuers` for watchlist status and credit outlook.
5. Fetch `/api/policies` for the portfolio's constraint policy (match via
   the portfolio's `constraint_policy_id`). Read `max_hy_allocation_pct`,
   `duration_band_years`, `issuer_concentration_limit_pct`,
   `subsector_min_count_for_diversified`.
6. Fetch `/api/market/energy` for energy market signals and pitch themes.
7. Filter candidates: `candidate: true`, `energy_linked: true`, issuer not on
   watchlist, rating and duration consistent with the constraint policy.
8. Select the required number of BUYs with the prescribed total notional. Prefer
   candidates aligned with positive energy signals (LNG, gas demand) and avoid
   watchlisted issuers or subsectors.
9. Build post-trade holdings by merging current holdings with proposed buys,
   then run [scripts/weighted_metrics.py](scripts/weighted_metrics.py).
10. Check constraints: HY cap, duration band, issuer diversification (no issuer
    exceeds the concentration limit), subsector diversification (at least the
    minimum distinct subsectors among selections), watchlist avoidance.
11. Set `sales_positioning` from the template's allowed values, choosing a
    segment and theme that match the desk's client context and the selected
    bonds' theme tags.
12. Set `data_precedence` to `current_environment_over_stale_payload` when the
    local payload carries stale data.

### International Equity Correlation Review

When the prompt requests a correlation review for an international equity
portfolio:

1. Read the answer template and the review request payload for the review window
   (`level_start_date`, `level_end_date`) and index universe.
2. Fetch `/api/index-levels` (bulk) or individual `/api/index-levels/{id}` for
   each index in the universe.
3. Fetch `/api/policies` for correlation thresholds (`correlation_high_threshold`,
   `correlation_low_threshold`).
4. Compute pairwise Pearson correlations across all index pairs using
   [scripts/correlation.py](scripts/correlation.py). Extract the highest
   positive and lowest correlation pairs.
5. Identify concentration: check if the highest correlation exceeds the high
   threshold. Look for China-Asia dependence patterns (IDX_CHINA paired with
   regional indices). Set `china_asia_dependence_flag`, `primary_code`, and
   `high_threshold_breached` from the template's allowed values.
6. Identify diversification candidates: indices with low correlations to the
   dominant concentrated indices.
7. Propose sleeve actions from the template's allowed action set (`trim`, `add`,
   `hold`, `hedge`, `monitor`, `rotate`). Match actions to the concentration
   and diversification findings. Sort sleeves alphabetically.

### Active Allocation View Refresh

When the prompt requests an allocation view refresh for a target quarter:

1. Read the answer template and the allocation request for `focus_opportunity_sets`,
   `target_quarter`, `prior_quarter`.
2. Fetch `/api/allocation/opportunity-sets` for the asset class mapping of each
   opportunity set.
3. Fetch `/api/allocation/prior-views` and filter to records where
   `quarter` equals the `target_quarter` and `previous_quarter` equals
   `prior_quarter`. These give the Q1→Q2 view and conviction for each
   opportunity set.
4. Fetch `/api/macro-signals` and filter to `target_quarter`. These give the
   current `score` and `rationale_code` for each opportunity set.
5. Fetch `/api/policies` for the `allocation_mapping` policy: use
   `view_score_thresholds` to map signal scores to views (score ≥ OW_min → OW,
   score ≤ UW_max → UW, else N). Use `conviction_thresholds` to map absolute
   scores to conviction levels.
6. For each focused opportunity set, determine the new view from the signal
   score. Compare to the prior-quarter view to compute `change` (`UP`, `DOWN`,
   `UNCHANGED`). Use the `rationale_code` from the macro signal record.
7. Select a risk overlay: review overall signal direction across all
   opportunity sets. Choose from the template's overlay options. Provide
   rationale codes in business-priority order (highest priority first).
8. Use the top-level `policy_id` from `/api/policies` as the `policy_id` field.

### Fixed-Income Risk Rebalance

When the prompt requests a credit-risk rotation for a fixed-income portfolio:

1. Read the answer template and meeting memo for the portfolio, rebalance
   preferences, and target reductions.
2. Fetch `/api/portfolios/{portfolio_id}/holdings` for current positions.
3. Fetch `/api/instruments/bonds` for the full bond universe.
4. Fetch `/api/issuers` for watchlist status and credit outlook.
5. Fetch `/api/policies` for the portfolio's constraint policy. Read
   `max_hy_allocation_pct`, `duration_band_years`, `target_hy_reduction_pct`,
   `issuer_concentration_limit_pct`.
6. Identify SELL candidates: holdings that are HY, on watchlist, or identified
   in the meeting memo as pressure points. Sell enough to meet the target HY
   reduction.
7. Identify BUY candidates: `candidate: true`, IG-rated, issuer not on
   watchlist, duration consistent with keeping the portfolio inside the
   duration band. Use candidates from the memo's shortlist when they pass
   constraint checks, but reject any where the issuer is watchlisted.
8. Build post-trade holdings, compute metrics with
   [scripts/weighted_metrics.py](scripts/weighted_metrics.py).
9. Check constraints: HY cap, duration band, target HY reduction met,
   watchlist exposure cleared.
10. Fill `watchlist_handling`: identify which sold instruments are on the
    watchlist, confirm buys avoid watchlisted issuers.
11. Set `risk_note_code` from the template's allowed values based on the most
    material risk concern addressed.

### Multi-Asset Committee Decision

When the prompt requests a committee JSON linking correlation findings to
allocation views:

1. Read the answer template and committee request for the focused opportunity
   sets, index IDs, and review quarter.
2. Run both the correlation review and allocation view refresh workflows for
   the specified subsets (indices and opportunity sets).
3. Fetch `/api/index-levels` for the specified index IDs and compute the
   highest-concentration and best-diversifier pairs using
   [scripts/correlation.py](scripts/correlation.py).
4. Fetch `/api/allocation/prior-views` and `/api/macro-signals` for the
   specified opportunity sets. Compute signal-based views and changes.
5. Determine `rebalance_trigger`: if the highest correlation exceeds the policy
   threshold, use `correlation_cap_breach`. Match other trigger options to the
   dominant risk finding.
6. Set `portfolio_risk_concentration_flag` to `true` when the concentration
   pair breaches the correlation threshold.
7. Set `next_step` based on whether constraints are breached and the severity
   of findings.
8. Sort all list items per the template's ordering rules.

## Rounding and Precision

Every template declares precision explicitly per field. Follow these rules:

- Correlation values: round to 3 decimal places. Use
  [scripts/correlation.py](scripts/correlation.py) which guarantees this.
- Portfolio metrics (market_value, HY%, duration, YTW): round to 2 decimal
  places. Use [scripts/weighted_metrics.py](scripts/weighted_metrics.py).
- Notional values (quantity_usd_m): round to 1 decimal place.
- Signal scores: round to 3 decimal places as declared in the template.
- All list items must follow the template's declared sort order.
