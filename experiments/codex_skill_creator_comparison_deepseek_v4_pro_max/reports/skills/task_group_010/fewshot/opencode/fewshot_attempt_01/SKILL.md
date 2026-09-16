---
name: asteria-investment-office
description: Complete institutional portfolio tasks for the Asteria Investment Office. Use this skill whenever the user mentions Asteria, a portfolio id like PF-EN-ALTA, PF-INT-NEXVEN, PF-FI-LUMEN, or PF-MA-HELIO, a CIO allocation view refresh, credit trade strategy, fixed-income rebalance, equity correlation review, multi-asset committee JSON, or any task that references a shared Asteria environment or API. Do not skip this skill even when the task seems straightforward — the Asteria API is the authoritative book of record and stale local payloads must always be reconciled against it.
---

# Asteria Investment Office Portfolio Work

Use the Asteria shared environment API as the authoritative book of record. Local payloads (desk requests, meeting memos, committee packets) are intake context that may contain stale marks, preferences from earlier worksheets, or unreconciled snapshots. Always read current records from the API before making decisions.

## Core Principle: Current Environment Over Stale Payload

Every task follows a single overriding rule: the API returns the current state, and local payloads may be stale. When the two conflict, prefer the API. This is captured in the `data_precedence` field on credit tasks as `current_environment_over_stale_payload`, but it applies equally to all task types.

Concretely:
- Portfolio holdings from the API are the current book; stale snapshots in payloads are not.
- Bond data, issuer/watchlist status, index levels, prior views, macro signals — all come from the API, not from payload notes.
- Payload preferences (e.g., "the desk wants LNG exposure") guide candidate selection but do not override API facts about watchlist status, rating buckets, or eligibility.
- Never copy holding quantities, market values, HY percentages, or index levels from a payload snapshot when the API provides current values.

## Environment API

The API is served at the base URL given in `environment_access.md` (typically `http://task-env:9010/`). No credentials are required. Start every task by reading the API landing page to confirm available endpoints.

### Endpoint Summary

| Method | Path | Purpose |
|--------|------|---------|
| GET | `/api/catalog` | All valid ids: portfolios, bonds, issuers, indices, opportunity sets, policies |
| GET | `/api/portfolios` | All portfolio summaries (market value, constraint policy, objective) |
| GET | `/api/portfolios/{id}/holdings` | Current holdings for a portfolio |
| GET | `/api/instruments/bonds` | Full bond universe with ratings, sectors, subsectors, duration, YTW, spreads |
| GET | `/api/issuers` | Issuer research records: credit outlook, rating bucket, watchlist status, research tags |
| GET | `/api/market/energy` | Energy market signals: commodity direction, scores, pitch themes |
| GET | `/api/indices` | Index metadata: region, currency, frequency, date range |
| GET | `/api/index-levels` | All index levels for the current review window |
| GET | `/api/index-levels/{id}` | Single-index level history |
| GET | `/api/allocation/opportunity-sets` | Allocation taxonomy: asset class, sub-asset-class, display order |
| GET | `/api/allocation/prior-views` | Prior-quarter views per opportunity set (view, conviction, quarter) |
| GET | `/api/macro-signals` | Current-quarter signal scores, rationale codes, drivers per opportunity set |
| GET | `/api/policies` | Policy thresholds: HY caps, duration bands, correlation thresholds, allocation mapping |

### Reading Strategy

1. Hit `/api/catalog` early to orient yourself on available ids.
2. Read endpoints in parallel where possible (portfolios, bonds, issuers, indices, policies — all independent).
3. For credit tasks: read portfolio holdings, the full bond universe, all issuers (for watchlist), and the relevant policy.
4. For correlation tasks: read the index metadata, then `/api/index-levels` for the relevant ids.
5. For allocation tasks: read opportunity sets, prior views, macro signals, and the allocation mapping policy.
6. Always read `/api/policies` — the top-level object wraps sub-policies; extract the one named in the portfolio's `constraint_policy_id`.

## Task Types and Workflows

### Credit Trade Strategy (e.g., energy-credit desk tickets)

This is a bond selection task with two or more BUY tickets. The desk request payload describes preferences, but actual bond eligibility, ratings, and watchlist status come from the API.

**Workflow:**

1. Read the portfolio's current holdings from `/api/portfolios/{id}/holdings`.
2. Read the full bond universe from `/api/instruments/bonds`.
3. Read all issuers from `/api/issuers` — cross-reference with bond `issuer_id` to determine which bonds are on watchlist.
4. Read `/api/market/energy` if energy-linked bonds are in scope (to understand commodity themes).
5. Read the constraint policy from `/api/policies` — extract the sub-policy named in the portfolio's `constraint_policy_id`.
6. Compute current portfolio metrics (market value, HY%, duration, YTW) from holdings + bond data.
7. Select eligible bonds:
   - Must be `candidate: true` in the bond universe.
   - Must not be from a watchlisted issuer (cross-reference bonds with issuers).
   - For energy tasks: prefer `energy_linked: true` bonds matching desk-preferred exposures.
   - For HY cap compliance: sum current HY holdings + new HY buys, check against `max_hy_allocation_pct`.
   - For duration band: compute weighted modified duration post-trade, check against `duration_band_years`.
   - For issuer diversification: no single issuer's post-trade exposure should exceed `issuer_concentration_limit_pct`.
   - For subsector diversification: at least `subsector_min_count_for_diversified` distinct subsectors in portfolio.
8. Fill the trade package: action=BUY, instrument_id, notional_usd_m rounded to 1 decimal.
9. Compute post-trade metrics using the weightings and rounded to 2 decimal places:
   - `total_market_value_usd_m` = current MV + sum of BUY notionals
   - `hy_allocation_pct` = (sum of post-trade HY quantities / total MV) x 100
   - `weighted_modified_duration_years` = weighted average of individual bond durations by post-trade quantity
   - `weighted_yield_to_maturity_pct` = weighted average of individual bond YTW by post-trade quantity
10. Set constraint_checks booleans and sales_positioning enums from the template's allowed values.
11. Set `data_precedence` to `current_environment_over_stale_payload` unless the payload genuinely adds information the API lacks.

### Fixed Income Risk Rebalance (rotation trades)

This is a rotation: sell pressure points, buy eligible candidates, while meeting HY reduction and duration targets.

**Workflow:**

1. Read current holdings, bonds, issuers, and the portfolio's constraint policy (often `POL_CREDIT_RISK_REDUCTION`).
2. Identify sell candidates: holdings that are HY, watchlisted, or named in the stale exception board as pressure points. Cross-reference with API data — the stale exception board may list bonds that no longer exist or have changed status. Only sell what the portfolio actually holds.
3. Compute current metrics (HY%, duration, watchlist exposure).
4. Identify buy candidates from `candidate: true`, non-watchlist bonds that improve the portfolio. Prefer those that add duration, are IG, and diversify issuer/subsector exposure.
5. Size the trades: total sells should fund total buys. The combined effect must reduce HY by at least the policy's `target_hy_reduction_pct` (in percentage points) and keep duration inside `duration_band_years`.
6. Format trades with action SELL before BUY, then instrument_id ascending within each action. Notional rounded to 1 decimal.
7. Compute post-trade `hy_reduction_pct_points` = pre-trade HY% minus post-trade HY%.
8. Set exception flags: `hy_cap_pass`, `duration_band_pass`, `target_hy_reduction_met`, `watchlist_exposure_cleared`.
9. Watchlist handling: list watchlist sell ids ascending, set `buys_avoid_watchlist` true.

See `references/computation-guide.md` for post-trade metric formulas.

### International Equity Correlation Review

Compute Pearson correlations from monthly index levels and identify concentration and diversification signals.

**Workflow:**

1. Read `/api/indices` and `/api/index-levels` for the indices in the review universe.
2. The review window is specified in the payload (start/end dates). Use level records within that range only.
3. Compute monthly simple returns for each index:
   - For each pair of consecutive months: `return = (level_current / level_prior) - 1`
   - The number of return observations = number of level pairs = (number of level records - 1).
4. For each pair of indices, compute the Pearson correlation of their return series. Round to 3 decimal places.
5. Identify extreme pairs:
   - `highest_positive`: the pair with the highest correlation value.
   - `lowest`: the pair with the lowest correlation value.
   - When computing pairwise correlations, sort each pair's index ids alphabetically.
6. Concentration analysis:
   - Check if the China-to-Asia relationship is a concern: compute the correlation between IDX_CHINA and IDX_EM (or IDX_AC_ASIA_PAC_EX_JP). If it exceeds the policy's `correlation_high_threshold` (0.8), flag `china_asia_dependence_flag: true`.
   - Select the `primary_code` from the template's allowed values.
   - Set `high_threshold_breached` based on whether any relevant pair exceeds the threshold.
7. Diversification candidates: from the allowed set, list index ids sorted alphabetically that have low or negative correlation with the concentrated regions.
8. Sleeve actions: two entries sorted by sleeve name, with action from allowed enum and target_index_id from allowed enum.

See `references/computation-guide.md` for the correlation formula details.

### Allocation View Refresh (CIO quarterly views)

Determine active allocation views (UW/N/OW) for specified opportunity sets.

**Workflow:**

1. Read `/api/allocation/opportunity-sets` to confirm the asset class of each set.
2. Read `/api/allocation/prior-views` filtered to the prior quarter (Q1_2026 for Q2_2026 refresh). The prior-views endpoint returns records keyed by `previous_quarter`; find rows where `previous_quarter` matches the prior quarter from the payload.
3. Read `/api/macro-signals` filtered to the target quarter. Each signal record has `quarter`, `opportunity_set`, `score`, `rationale_code`, `drivers`.
4. Read `/api/policies` to get the `allocation_mapping` sub-policy.
5. For each requested opportunity set:
   - Map `view` from the signal score using the allocation mapping thresholds:
     - `score >= OW_min (0.35)` -> `OW`
     - `score <= UW_max (-0.35)` -> `UW`
     - Otherwise -> `N`
   - Map `conviction` from the absolute signal score:
     - `abs(score) >= HIGH_abs_min (0.7)` -> `HIGH`
     - `abs(score) >= MEDIUM_abs_min (0.35)` -> `MEDIUM`
     - Otherwise -> `LOW`
   - `change`: compare the new view to the prior view. If they differ and the new view is "higher" (N->OW, UW->N, UW->OW), change is `UP`. If "lower" (OW->N, N->UW, OW->UW), change is `DOWN`. If same, `UNCHANGED`.
   - `rationale_code`: from the macro signal record.
   - `asset_class`: from the opportunity-sets taxonomy.
6. Risk overlay selection: combine signals across the portfolio to pick the dominant risk theme. The overlay_code and primary_action come from the template's allowed values. The rationale_codes list should be in business-priority order (highest priority first), drawn from the set of relevant signal rationale codes.
7. Sort allocation views in the request payload's focus order, not alphabetically.

See `references/computation-guide.md` for the view-mapping logic and policy thresholds.

### Multi-Asset Committee JSON

This links correlation findings with allocation views for a portfolio that holds both equity index sleeves and bond positions.

**Workflow:**

1. Read the portfolio's holdings — these may contain both equity index positions and bond positions. Treat each holding type separately.
2. For correlation: read the relevant index levels and compute pairwise Pearson correlations for the committee's focus indices (typically 4 indices: EM, China, India, Latin America). Identify highest-concentration pair (highest correlation) and best-diversifier pair (lowest correlation). Each pair's ids must be sorted alphabetically. Round to 3 decimals.
3. For allocation: read prior views and macro signals for the committee's focus opportunity sets. Apply the allocation mapping policy thresholds to determine view, change, conviction, and rationale_code.
4. For target sleeve actions: recommend actions (trim/add/hold/hedge) per opportunity set, driven by correlation signals and allocation views.
5. Set `rebalance_trigger` from the template's enum based on the most material risk driver.
6. Set `portfolio_risk_concentration_flag` to true if any correlation exceeds the policy threshold or if a material risk exception exists.
7. Set `next_step` from the template's enum.

## Output Conventions

### JSON Precision
- Notional/quantity values (USD millions): round to **1 decimal place**.
- Percentages, durations, yields: round to **2 decimal places**.
- Correlation values: round to **3 decimal places**.
- Signal scores: round to **3 decimal places** (as returned by the API).

### Sorting
- Trade lists: SELL before BUY, then instrument_id ascending within each action group.
- Index id lists within pairs: sort alphabetically.
- Allocation view lists: follow the request payload's order (not alphabetical).
- Sleeve action lists: sort by sleeve name ascending.

### Enum-Only Fields
When the answer template declares an `allowed_values` list for a field, use only those exact strings. Do not invent new values. The same enum values recur across tasks: the view/conviction/change/rationale_code sets, the action sets, the sales positioning sets, etc.

### Dates
- `as_of_date` must match the date of the API records used (usually `2026-05-29` for this environment snapshot).
- Window dates (level_start_date, level_end_date) come from the payload's review window and the API index metadata.

## Reference Files

- `references/computation-guide.md` — Formulas for post-trade metrics, correlations, view mapping, and policy threshold lookups.
- `references/api-reference.md` — Detailed field schemas for each API endpoint and how to use them.
- `references/policy-reference.md` — Policy sub-objects, threshold values, and how constraint checks map to portfolio policy ids.
