# Skill: Asteria Investment Office Portfolio Risk JSON Tasks

## Overview

This skill covers solving tasks against the Asteria Investment Office shared environment, which exposes a REST API at a remote base URL. Tasks fall into several categories: energy-credit trade recommendations, issuer watchlist/correlation reviews, allocation view refreshes, fixed-income risk rebalances, and multi-asset committee packs.

## Environment Setup

1. **Base URL**: Use only the provided environment base URL (e.g., `http://34.46.77.124:8010`). Do not use localhost or 127.0.0.1.
2. **Key endpoints** (discoverable from `GET /` and `GET /api/catalog`):
   - `/api/catalog` — lists available portfolio, policy, index, issuer, bond, and opportunity-set IDs.
   - `/api/portfolios/<portfolio_id>` — current holdings, constraints, market value.
   - `/api/policies` — policy thresholds (HY caps, duration bands, correlation thresholds, allocation mapping).
   - `/api/instruments/bonds` — full bond universe with `candidate`, `energy_linked`, `rating_bucket`, `modified_duration_years`, `spread_bps`, `yield_to_maturity_pct`, `recommended_theme_tags`.
   - `/api/issuers` — issuer records with `watchlist`, `rating_bucket`, `sector`, `subsector`, `research_tags`.
   - `/api/index-levels/<index_id>` — monthly index levels for correlation calculations.
   - `/api/market/energy` — energy market signals and pitch themes.
   - `/api/allocation/opportunity-sets`, `/api/allocation/prior-views`, `/api/macro-signals` — allocation taxonomy, prior-quarter views, and current macro signal scores/rationale codes.

## General Workflow

1. **Read the task prompt** to identify the portfolio ID, task type, and required output schema.
2. **Read the local payload** (`desk_request.json`, `review_request.json`, `allocation_request.json`, `committee_request.json`, `risk_meeting_memo.json`, etc.) for context, but treat it as potentially stale.
3. **Fetch current environment data** for the portfolio, bonds, issuers, policies, and any relevant market signals.
4. **Compute derived values** (correlations, post-trade metrics, allocation views) using the current environment as the book of record.
5. **Produce JSON** matching the `answer_template.json` exactly, including key ordering, precision, and enum values.

## Task Type Patterns

### 1. Energy-Credit Trade Recommendations (e.g., PF-EN-ALTA)

- **Goal**: Select exactly N BUY tickets (usually 2) totaling a specific notional (e.g., USD 8.0M split evenly).
- **Constraints**:
  - `max_hy_allocation_pct` from portfolio policy (e.g., 20%).
  - `duration_band_years` (e.g., 3.0–5.0 years).
  - Avoid watchlisted issuers.
  - Prefer `energy_linked=true` bonds aligned with current energy signals.
  - Ensure issuer and subsector diversification.
- **Post-trade metrics to compute**:
  - `total_market_value_usd_m` = current MV + new notional.
  - `hy_allocation_pct` = sum of HY holdings / total MV × 100.
  - `weighted_modified_duration_years` = weighted average duration.
  - `weighted_yield_to_maturity_pct` = weighted average YTM.
- **Sales positioning**: Match the `target_segment` and `theme` enums from the template to the portfolio strategy (e.g., `multi_asset_income` + `lng_export_tailwind` for LNG-focused trades).
- **Data precedence**: Always set `current_environment_over_stale_payload` when the local request contains stale marks.

### 2. International Equity Correlation Reviews (e.g., PF-INT-NEXVEN)

- **Goal**: Compute Pearson correlations from monthly simple returns over the requested window.
- **Method**:
  - Fetch `/api/index-levels/<index_id>` for each index in the universe.
  - Compute simple returns: `(level_t - level_{t-1}) / level_{t-1}`.
  - Compute Pearson correlation between each pair.
  - Round to 3 decimals.
- **Outputs**:
  - `review_window` with `level_start_date`, `level_end_date`, `return_observations` (N-1 months).
  - `index_set` sorted ascending alphabetically.
  - `extreme_pairs`: `highest_positive` and `lowest` pair, with `pair_id` sorted alphabetically.
  - `concentration`: Check if `china_asia_dependence_flag` is true (correlation between China and Asia Pac ex-JP ≥ threshold), set `high_threshold_breached` if any pair ≥ 0.8.
  - `diversification_candidates`: From allowed values, select those with low correlation to the rest of the portfolio.
  - `sleeve_actions`: Two actions sorted ascending by sleeve name, chosen from allowed actions/target indices.

### 3. Allocation View Refresh (e.g., Q2_2026 CIO Desk)

- **Goal**: Produce active views (UW/N/OW) for a focused set of opportunity sets.
- **Inputs**:
  - `/api/macro-signals` for the target quarter — provides `score` and `rationale_code`.
  - `/api/allocation/prior-views` for prior and current quarter — provides prior `view` and `conviction`.
  - `/api/policies` → `allocation_mapping` — defines score thresholds:
    - `OW` if score ≥ 0.35
    - `UW` if score ≤ -0.35
    - `N` otherwise
    - `HIGH` conviction if |score| ≥ 0.7, `MEDIUM` if ≥ 0.35, else `LOW`.
- **Change determination**: Compare current computed view to prior quarter view:
  - `UP` if view improves (e.g., N→OW or UW→N)
  - `DOWN` if view worsens (e.g., OW→N or N→UW)
  - `UNCHANGED` if same.
- **Risk overlay**: Choose from allowed overlay codes. Rationale codes should be ordered by business priority (highest first). Common choice: `CREDIT_RISK_REDUCTION` with `trim_credit_beta` when HY signals are negative.
- **Lineage**: Include `as_of_date` (environment date), `target_quarter`, `prior_quarter`, and `policy_id` (e.g., `POL_ALLOCATION_MAPPING`).

### 4. Fixed-Income Risk Rebalance (e.g., PF-FI-LUMEN)

- **Goal**: Reduce HY exposure and remove watchlist risk while keeping duration in band.
- **Inputs**:
  - Current portfolio holdings from `/api/portfolios/<id>`.
  - Bond details from `/api/instruments/bonds`.
  - Issuer watchlist status from `/api/issuers`.
  - Policy constraints (e.g., `POL_CREDIT_RISK_REDUCTION` with `target_hy_reduction_pct`, `duration_band_years`, `max_hy_allocation_pct`).
- **Approach**:
  - Sell HY bonds from the stale exception board, especially watchlisted ones.
  - Buy IG candidate bonds that are not watchlisted and fit the duration band.
  - Ensure `hy_reduction_pct_points` meets the minimum target.
  - Keep `post_trade_duration_years` within the CIO band.
- **Outputs**:
  - `rotation.trades`: SELLs first sorted by instrument_id, then BUYs sorted by instrument_id.
  - `risk_metrics`: `post_trade_hy_allocation_pct`, `post_trade_duration_years`, `hy_reduction_pct_points`, `post_trade_watchlist_exposure_usd_m`.
  - `exception_flags`: All booleans reflecting constraint passes.
  - `watchlist_handling`: List of sold watchlist IDs, and `buys_avoid_watchlist=true`.
  - `risk_note_code`: Choose from allowed enum (e.g., `watchlist_concentration`, `hy_cap_pressure`, `duration_preservation`).

### 5. Multi-Asset Committee Pack (e.g., PF-MA-HELIO)

- **Goal**: Link non-US equity correlation findings to active allocation views.
- **Correlation summary**: Exactly 2 items ordered `[highest_concentration, best_diversifier]`. Pairs sorted alphabetically. Correlation rounded to 3 decimals.
- **Target sleeve actions**: Ordered by opportunity set (Emerging Markets, India, Latin America, USD). Action from allowed enum.
- **Allocation views**: Ordered by opportunity set. Include `prior_view` from `/api/allocation/prior-views`, `signal_score` from `/api/macro-signals`, computed `view`/`change`/`conviction`/`rationale_code`.
- **Rebalance trigger**: Choose from allowed enum based on findings (e.g., `correlation_cap_breach` if high correlation exceeds threshold).
- **Portfolio risk concentration flag**: Boolean based on whether concentration risk is material.
- **Next step**: Choose from allowed enum (e.g., `approve_with_monitoring` when there is concentration but no hard constraint breach).

## Critical Precision Rules

- Always round to the precision declared in the answer template.
- Sort lists as specified in the template (alphabetical, ascending by instrument_id, SELL before BUY then by instrument_id, etc.).
- Use only allowed enum values; any other string will fail validation.
- Include all required keys; missing keys will fail validation.

## Common Pitfalls

- **Stale data**: The local payload may contain stale marks or outdated holdings. Always use the current environment API as the book of record.
- **Portfolio not found**: Some portfolio IDs in prompts may not exist in the catalog. Use the portfolio ID explicitly named in the prompt/template, but fetch its data from the environment.
- **Correlation window**: Use the exact level dates from the request payload. Return observations = number of levels - 1.
- **Duration/YTM weighting**: Weight by market value (quantity_usd_m), not equal weighting.
- **HY allocation**: Compute as percentage of post-trade total market value, not pre-trade.
