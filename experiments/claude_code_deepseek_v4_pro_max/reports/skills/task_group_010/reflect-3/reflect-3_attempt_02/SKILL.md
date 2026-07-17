# Asteria Investment Office — Reflect Skill

## Overview

This skill covers the Asteria Investment Office workflow: energy credit trade construction, international equity correlation review, active allocation views, fixed-income risk rebalancing, and multi-asset committee decision files. All tasks share a remote HTTP API (`GDPEVO_ENV_BASE_URL`) as the authoritative book of record; local payloads are intake context only and may contain stale marks.

## Environment and Data Precedence

- The remote API at `GDPEVO_ENV_BASE_URL` is the sole current book of record. Never use localhost, `env/README.md`, or filesystem paths.
- Local payload files (desk requests, meeting memos, review packets) provide task framing but may contain stale marks. The prompt text or `environment_access.md` takes precedence over local URL references.
- **Data precedence rule**: when the API and a local payload disagree on values (quantities, dates, market values), use the API. Output `data_precedence` as `"current_environment_over_stale_payload"` whenever a stale-data warning or reconciliation note appears in the local payload. If no conflict exists, use `"no_conflict_found"`.
- The API `as_of_date` (available in `/api/policies` and each portfolio response) is the as-of date for all outputs unless a task-specific window overrides it.

## Key API Endpoints and Their Data

| Endpoint | Key fields returned |
|---|---|
| `GET /api/catalog` | All IDs: `portfolio_ids`, `bond_instrument_ids`, `index_ids`, `issuer_ids`, `policy_ids`, `opportunity_sets` |
| `GET /api/portfolios/<id>` | `holdings[]` (instrument_id, quantity_usd_m, sleeve, asset_class, notes), `market_value_usd_m`, `constraints`, `as_of_date` |
| `GET /api/instruments/bonds` | `instrument_id`, `issuer_id`, `rating_bucket` (IG/HY), `modified_duration_years`, `yield_to_maturity_pct`, `subsector`, `sector`, `candidate`, `energy_linked`, `recommended_theme_tags` |
| `GET /api/issuers` | `issuer_id`, `watchlist` (boolean), `credit_outlook`, `rating_bucket`, `subsector`, `research_tags` |
| `GET /api/indices` + `/api/index-levels` | Index metadata (`region`, `frequency`, `level_start_date`, `level_end_date`) and monthly level time series per index_id |
| `GET /api/market/energy` | Energy commodity `signals[]` (score, direction, signal_id), `pitch_themes[]`, `stale_data_warning` |
| `GET /api/allocation/opportunity-sets` | `opportunity_set`, `asset_class` (Equities/Duration/Credit/Currency), `display_order` |
| `GET /api/allocation/prior-views` | `opportunity_set`, `quarter`, `previous_quarter`, `view` (UW/N/OW), `conviction` (LOW/MEDIUM/HIGH). Filter to entries where `quarter` matches the target quarter. |
| `GET /api/macro-signals` | `opportunity_set`, `quarter`, `score` (float), `rationale_code`, `drivers[]` |
| `GET /api/policies` | Aggregated policy set: `allocation_mapping` (view_score_thresholds, conviction_thresholds), `credit_default`, `credit_risk_reduction`, `correlation` (high/low thresholds), `multi_asset`, `multi_asset_risk` |

## Bond Selection and Trade Construction

### Eligibility Filtering

When selecting bonds for a trade strategy or rotation:

1. Filter bonds to `candidate: true` (unless the portfolio already holds a non-candidate bond for selling).
2. For energy-credit tasks, further filter to `energy_linked: true`.
3. Cross-reference each bond's `issuer_id` with `/api/issuers` to obtain `watchlist` status. Exclude watchlisted issuers from BUY tickets.
4. When a bond's `recommended_theme_tags` include `WATCHLIST_RISK`, verify issuer watchlist status explicitly — do not rely on tags alone.

### Constraint Checks for Credit Portfolios

Credit portfolios are governed by a constraint policy (found in the portfolio's `constraints` field or `constraint_policy_id`). Standard constraints:

- **HY cap**: `max_hy_allocation_pct` (typically 20.0). Post-trade HY allocation = sum of all HY-rated position quantities / post-trade total market value × 100.
- **Duration band**: `duration_band_years` (typically `[3.0, 5.0]`). Weighted modified duration must fall inside this inclusive range.
- **Issuer concentration**: `issuer_concentration_limit_pct` (typically 12.0). No single issuer's total position should exceed this percentage of post-trade market value.
- **Subsector diversification**: `subsector_min_count_for_diversified` (typically 2). The selected new BUY tickets must span at least this many distinct subsectors.
- **Watchlist avoidance**: BUY tickets must not involve watchlisted issuers.
- **HY reduction target** (credit risk reduction policy): `target_hy_reduction_pct` (typically 4.0 percentage points). The rotation must reduce HY allocation by at least this amount.

Each constraint maps to a boolean `*_pass` field in the output.

### Trade List Ordering Rules

- **train_001 style** (single-direction package): Sort by `instrument_id` ascending.
- **train_004 style** (rotation with SELL + BUY): SELL trades before BUY trades; within each action group, sort by `instrument_id` ascending.
- Quantities use precision 1 (USD millions), e.g., `4.0`, `12.0`.
- Total sell notional must equal total buy notional to preserve market value.

### Weighted Portfolio Metric Formulas

```
post_trade_mv = pre_trade_mv  (when total_buys == total_sells)

weighted_duration = Σ(position_qty × modified_duration_years) / total_mv
weighted_ytm      = Σ(position_qty × yield_to_maturity_pct) / total_mv
hy_allocation_pct = Σ(HY-rated position quantities) / total_mv × 100
hy_reduction_pp   = pre_trade_hy_pct − post_trade_hy_pct
watchlist_exposure = Σ(positions where issuer.watchlist == true)
```

Round weighted duration to 2 decimals, YTM to 2 decimals, HY % to 2 decimals, HY reduction to 2 decimals, and watchlist exposure to 1 decimal (USD millions).

### Sales Positioning Convention

- `target_segment`: map from `client_context` in the desk request. "multi-asset income update" → `"multi_asset_income"`. Other valid values: `insurance_general_account`, `pension_liability_matching`, `private_bank_income`, `endowment_opportunistic`.
- `theme`: align with the strongest positive energy signal or the desk's preferred exposures. Valid values: `lng_export_tailwind`, `oil_oversupply_caution`, `midstream_stability`, `transition_bond_selectivity`, `avoid_watchlist_yield_trap`.
- When the energy market `/api/market/energy` shows `LNG_EXPORT_PULL` with the highest positive score, prefer `lng_export_tailwind` if LNG/gas demand is in the desk's preferred exposures.

## Pearson Correlation from Index Levels

### Monthly Simple Returns

For indices with 12 consecutive end-of-month levels, compute 11 monthly simple returns:

```
return_t = (level_t − level_{t−1}) / level_{t−1}
```

### Pearson Correlation Formula

```
r = Σ((x_i − x̄)(y_i − ȳ)) / √(Σ(x_i − x̄)² × Σ(y_i − ȳ)²)
```

Compute in full floating-point precision, then round to 3 decimal places.

### Review Window and Return Observations

- `level_start_date` and `level_end_date` determine the window. From the index levels endpoint, use all dates within `[start, end]` inclusive.
- `return_observations` = number of level observations − 1.
- For a 12-month window with monthly data, this is 11.

### Extreme Pair Identification

- **highest_positive**: the pair with the largest positive Pearson correlation.
- **lowest**: the pair with the most negative (lowest numerical value) Pearson correlation.
- In pair objects, `pair_id` is a two-element string array sorted alphabetically by index ID.

### Concentration Analysis

- `china_asia_dependence_flag`: true when `IDX_CHINA` vs `IDX_AC_ASIA_PAC_EX_JP` correlation exceeds the `correlation_high_threshold` (0.8).
- `high_threshold_breached`: true when any index pair's correlation exceeds the high threshold.
- `primary_code`: `"CHINA_ASIA_DEPENDENCE"` when the China-Asia pair breaches the threshold; `"GLOBAL_DEVELOPED_OVERLAP"` for developed-market overlap; `"NO_MATERIAL_CONCENTRATION"` otherwise.

### Diversification Candidates

Candidates are drawn from `{IDX_EM_EX_CHINA, IDX_INDIA, IDX_LATAM}`. Include indices that provide low or negative correlation to the primary concentration pair. List them sorted alphabetically by index ID.

### Sleeve Actions

- Sleeve names must match the portfolio's `holdings[].sleeve` field exactly.
- Two actions per review, sorted ascending by sleeve name.
- Available actions: `trim`, `add`, `hold`, `hedge`, `monitor`, `rotate`.
- Available `target_index_id` values: `IDX_CHINA`, `IDX_EM_EX_CHINA`, `IDX_LATAM`.

## Active Allocation Views

### Computing Views from Macro Signal Scores

Use the policy at `allocation_mapping.view_score_thresholds`:

| Condition | View |
|---|---|
| `score ≥ OW_min` (0.35) | `OW` |
| `score ≤ UW_max` (−0.35) | `UW` |
| otherwise (in `neutral_between`) | `N` |

The neutral range `[−0.35, 0.35]` is inclusive of both endpoints.

### Computing Conviction from Absolute Score

Use `allocation_mapping.conviction_thresholds`:

| Condition | Conviction |
|---|---|
| `|score| ≥ HIGH_abs_min` (0.7) | `HIGH` |
| `|score| ≥ MEDIUM_abs_min` (0.35) | `MEDIUM` |
| `|score| < LOW_abs_below` (0.35) | `LOW` |

### Determining Change vs Prior Quarter

Look up the prior quarter's view from `/api/allocation/prior-views` where `quarter` matches the target quarter and `previous_quarter` matches the prior quarter. Compare:

- View moves from N to OW, UW to N, or UW to OW → `UP`
- View moves from OW to N, N to UW, or OW to UW → `DOWN`
- Same view → `UNCHANGED`

### Asset Class and Rationale Code

- `asset_class`: from `/api/allocation/opportunity-sets` for the matching `opportunity_set`.
- `rationale_code`: from `/api/macro-signals` for the matching `opportunity_set` and `quarter`.
- The `policy_id` in the output should be `POL_ALLOCATION_MAPPING`.

### Risk Overlay

The overlay synthesizes the dominant risk theme across all requested views:

- `overlay_code`: pick from the set in the request payload's `overlay_code_choices`.
- `primary_action`: the matching action from `primary_action_choices`.
- `rationale_codes`: a list ordered by business priority (highest priority first). Include the rationale codes for the views that most strongly support the overlay choice.

Common overlay patterns:
- Multiple OW on duration/quality + UW on credit risk → `DURATION_QUALITY_TILT` with `tilt_to_duration_quality`
- Multiple UW on credit + EM → `CREDIT_RISK_REDUCTION` with `trim_credit_beta`
- Adding to equities across regions → `EQUITY_BETA_EXTENSION` with `add_cyclical_equity_beta`

### Output Ordering for Allocation Views

Rows must follow the exact order of `focus_opportunity_sets` from the request payload — do not sort alphabetically.

## Fixed-Income Risk Rebalancing (Rotation)

### Identifying Sells

1. All bonds whose issuers are on watchlist (`/api/issuers` → `watchlist: true`).
2. Additional HY bonds needed to meet the `target_hy_reduction_pct` (typically 4.0 pp) while bringing post-trade HY below `max_hy_allocation_pct`.
3. Quantities to sell: use the **current API portfolio quantities**, not stale payload quantities, unless the stale data provides the specific bonds to sell as a shortlist.

### Identifying Buys

1. Candidates from the request payload's `candidate_shortlist` that are IG-rated and whose issuers are not on watchlist.
2. Buy quantities should sum to total sell quantities to preserve market value.
3. Avoid any candidate whose `recommended_theme_tags` include `WATCHLIST_RISK` (cross-verify with issuer data).

### Watchlist Handling

- `watchlist_sell_ids`: list of instrument_ids sold whose issuers are on watchlist, sorted ascending.
- `buys_avoid_watchlist`: `true` if all BUY tickets involve non-watchlisted issuers.

### Risk Note Code

Select the code that best describes the primary risk trade-off:

| Code | When to use |
|---|---|
| `watchlist_concentration` | Watchlist exposure was the main driver of the rotation |
| `hy_cap_pressure` | HY allocation was near or above the cap |
| `duration_preservation` | Duration constraint was binding |
| `carry_tradeoff` | The rotation sacrifices yield/carry for risk reduction |
| `no_action` | No trades recommended |

## Multi-Asset Committee Files (Cross-Task Integration)

When a task links correlation findings with allocation views (e.g., PF-MA-HELIO):

- **correlation_summary**: exactly 2 entries — `highest_concentration` (pair with max positive correlation) and `best_diversifier` (pair with most negative correlation involving the concentration indices). Within each pair, index IDs sorted alphabetically. Correlation to 3 decimals.
- **target_sleeve_actions**: one entry per requested opportunity set, in the order specified by the request. Action derived from the view: UW/negative → `trim` or `hedge`; OW/positive → `add` or `hold` (if unchanged); N with prior OW → `trim` or `hedge`.
- **allocation_views**: includes `prior_view` (from `/api/allocation/prior-views`), `signal_score` (from `/api/macro-signals`, to 3 decimals), plus the standard view/change/conviction/rationale_code fields computed per the allocation-view rules above.
- **rebalance_trigger**: `correlation_cap_breach` when any concentration pair exceeds `correlation_high_threshold`; `committee_review` for scheduled reviews without a specific breach.
- **portfolio_risk_concentration_flag**: `true` when the highest-concentration pair's correlation exceeds `correlation_high_threshold`.
- **next_step**: `defer_pending_risk_review` when concentration is flagged and views are shifting; `approve_with_monitoring` for actionable views with moderate risk; `approve_rotation` for clean passes; `reject_constraint_breach` for hard failures.

## Common Pitfalls

1. **Stale payload quantities**: Always use current API portfolio quantities, not `stale_holding_snapshot` or `stale_exception_board` quantities. The API is the authoritative book of record; stale payloads are intake context only.
2. **Watchlist cross-referencing**: A bond's tags may mention watchlist risk, but only `/api/issuers` watchlist boolean is authoritative. Always cross-reference.
3. **Return observation count**: 12 monthly levels → 11 simple returns, not 12. The return_observations field is an integer count of return observations, not a count of levels.
4. **Rounding before final computation**: Compute weighted metrics in full precision, then round to the declared precision. Avoid intermediate rounding.
5. **Pair ID ordering**: Index IDs within pair objects must be sorted alphabetically. For example, `["IDX_CHINA", "IDX_EM"]` not `["IDX_EM", "IDX_CHINA"]`.
6. **"Lowest" correlation means most negative**: In extreme-pair contexts, "lowest" refers to the minimum numerical value (most negative), not the smallest absolute value.
7. **View change direction**: UP means the view became more positive (N→OW, UW→N, UW→OW). DOWN means more negative (OW→N, N→UW, OW→UW).
8. **Asset class from taxonomy**: Always fetch asset_class from `/api/allocation/opportunity-sets`, do not guess from the opportunity set name. For example, "EUR" is Currency, not Equities.
9. **Policy ID for allocation**: Use `POL_ALLOCATION_MAPPING` for view/conviction threshold calculations, not the composite multi-asset policy ID.
10. **Trade ordering**: SELL always before BUY in rotation tasks. Within each action group, sort by instrument_id ascending.
11. **Duration band is inclusive**: `[3.0, 5.0]` means both endpoints are acceptable. A weighted duration of exactly 3.00 or 5.00 passes.
12. **Neutral score range includes boundaries**: `[-0.35, 0.35]` is inclusive — a score of exactly −0.35 maps to N, and exactly 0.35 maps to N (but OW_min 0.35 may create an edge case — treat ≥ OW_min as OW, ≤ UW_max as UW).
