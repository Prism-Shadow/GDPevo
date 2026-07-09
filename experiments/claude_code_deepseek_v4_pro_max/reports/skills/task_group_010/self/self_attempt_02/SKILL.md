# Asteria Investment Office — Reusable Task-Solving Procedure

This skill covers institutional portfolio risk tasks in the Asteria Investment Office domain: credit trade construction, equity correlation reviews, active allocation view refreshes, fixed-income risk rebalancing, and multi-asset committee decision files.

---

## 1. Environment & Data Precedence

**API base URL** as provided by the task environment. All data comes from these HTTP GET endpoints:

| Endpoint | What it returns |
|---|---|
| `/api/catalog` | All valid IDs: portfolios, instruments, issuers, indices, policies, opportunity sets |
| `/api/policies` | Constraint thresholds, allocation mapping rules, correlation thresholds, all policy detail |
| `/api/portfolios` | Portfolio summaries (market value, policy link, strategy) |
| `/api/portfolios/<id>` | Full holdings with instrument_id, quantity_usd_m, asset_class, sleeve |
| `/api/instruments/bonds` | Bond universe: YTM, duration, rating_bucket (IG/HY), subsector, issuer, energy_linked, candidate, watchlist tags in recommended_theme_tags |
| `/api/issuers` | Issuer research: watchlist (bool), rating_bucket, credit_outlook, sector, subsector, research_tags |
| `/api/market/energy` | Energy market signals, pitch themes, stale-data warning |
| `/api/indices` | Index metadata: region, currency, frequency, level date range |
| `/api/index-levels` | Monthly index levels keyed by index_id; each entry has date and level |
| `/api/allocation/opportunity-sets` | Taxonomy: opportunity_set → asset_class, sub_asset_class, display_order |
| `/api/allocation/prior-views` | Prior-quarter views per opportunity_set: view (UW/N/OW), conviction, quarter |
| `/api/macro-signals` | Current-quarter signal scores, rationale codes, drivers per opportunity_set |

**Hard data-precedence rule**: The current environment API is authoritative. Local payload data (request JSONs, memos, stale snapshots) may contain outdated marks. When current API data conflicts with a local payload, prefer the API. Capture this in any `data_precedence` output field as `"current_environment_over_stale_payload"`.

**Global as-of date**: All API responses share the same `as_of_date` (verify by checking `/api/portfolios`, `/api/policies`, `/api/market/energy`). Use this date in every output that requires `as_of_date`. The stale-data cutoff printed in `/api/market/energy` tells you which local dates to distrust.

---

## 2. Policy Lookup Chain

Every portfolio links to a constraint policy via `constraint_policy_id` in its summary. Look up that policy in the `/api/policies` response — it is a flat object with keys matching each `policy_id`. The policy provides:

- `max_hy_allocation_pct` — hard cap on high-yield exposure
- `duration_band_years` — `[min, max]` allowed weighted modified duration
- `issuer_concentration_limit_pct` — single-issuer cap (typically 12%)
- `subsector_min_count_for_diversified` — minimum distinct subsectors across selected holdings
- `target_hy_reduction_pct` — for risk-reduction policies, the minimum percentage-point reduction required
- `correlation_high_threshold` / `correlation_low_threshold` — for correlation policies
- `conviction_thresholds` / `view_score_thresholds` — for allocation-mapping policies

The allocation mapping policy (POL_ALLOCATION_MAPPING) defines:
- **View thresholds**: `score ≥ 0.35 → OW`, `score ≤ -0.35 → UW`, otherwise `N`
- **Conviction thresholds**: `abs(score) ≥ 0.70 → HIGH`, `0.35 ≤ abs(score) < 0.70 → MEDIUM`, `abs(score) < 0.35 → LOW`
- **View rank**: `OW = 1`, `N = 0`, `UW = -1`

Multi-asset policies compose from the single-asset policies (e.g., POL_MULTI_ASSET_DEFAULT uses POL_ALLOCATION_MAPPING + POL_CORRELATION_DEFAULT + POL_CREDIT_DEFAULT).

---

## 3. Task-Type Procedures

### 3A. Credit Trade Construction (e.g., PF-EN-ALTA)

**Goal**: Select eligible bonds for BUY/SELL orders that improve carry while respecting constraints.

**Procedure**:

1. **Fetch current portfolio** from `/api/portfolios/<id>`. Record each holding: instrument_id, quantity_usd_m, sleeve.
2. **Enrich each holding** by matching `instrument_id` to the bond universe (`/api/instruments/bonds`). Pull: rating_bucket, modified_duration_years, yield_to_maturity_pct, subsector, issuer_id, energy_linked.
3. **Enrich issuers** from `/api/issuers` — pull `watchlist` flag per issuer_id.
4. **Compute current portfolio metrics**:
   - `total_market_value_usd_m` = sum of all quantity_usd_m
   - `hy_allocation_pct` = 100 × (sum of HY-rated quantity_usd_m) / total_market_value_usd_m
   - `weighted_modified_duration_years` = Σ(qty_i × dur_i) / Σ(qty_i)
   - `weighted_yield_to_maturity_pct` = Σ(qty_i × ytm_i) / Σ(qty_i)
5. **Filter candidate bonds**: from the bond universe, select bonds where:
   - `candidate` is true (or is an existing holding)
   - The issuer is not on the watchlist (if watchlist avoidance is required)
   - Matches any sector/theme preferences from the request
6. **Select trades**: choose the required number of BUY/SELL tickets at the required sizes.
7. **Recompute post-trade metrics** by adding new holdings to the portfolio and re-running the weighted-average formulas.
8. **Check each constraint**:
   - `hy_cap_pass`: post-trade HY% ≤ max_hy_allocation_pct
   - `duration_band_pass`: post-trade duration ∈ [band_min, band_max]
   - `issuer_diversification_pass`: no single issuer > issuer_concentration_limit_pct of post-trade MV
   - `subsector_diversification_pass`: ≥ subsector_min_count distinct subsectors among the selected (new) positions
   - `watchlist_avoidance_pass`: none of the BUY tickets are watchlisted issuers

**Rounding**: notional_usd_m to 1 decimal; post_trade_metrics to 2 decimals.

**Ordering**: trade_package sorted ascending by instrument_id.

### 3B. Equity Correlation Review (e.g., PF-INT-NEXVEN)

**Goal**: Compute Pearson correlation matrix from monthly index levels and identify concentration/diversification pairs.

**Procedure**:

1. **Determine the review window** from the request payload (`level_start_date`, `level_end_date`). Also available from the policy's correlation section.
2. **Fetch index levels** from `/api/index-levels` for each index in the universe. Each index returns an array of `{date, level}` objects.
3. **Filter levels** to the review window dates (inclusive of both start and end).
4. **Compute monthly simple returns** for each index:
   - `r_t = (level_t / level_{t-1}) - 1`
   - Result: N levels → N-1 returns. Count = `return_observations`.
   - Do NOT use log returns; use simple (discrete) returns.
5. **Compute the Pearson correlation** for every unordered pair of indices:
   - `ρ(X,Y) = Σ((x_i - x̄)(y_i - ȳ)) / √(Σ(x_i - x̄)² × Σ(y_i - ȳ)²)`
   - Round to **3 decimal places**.
6. **Identify extreme pairs**:
   - `highest_positive`: the pair with the largest correlation value
   - `lowest`: the pair with the smallest (most negative) correlation value
7. **Concentration analysis**: check whether IDX_CHINA and the Asia-Pacific index (IDX_AC_ASIA_PAC_EX_JP) correlation exceeds the high threshold (0.8). If so, `china_asia_dependence_flag = true` and `primary_code = "CHINA_ASIA_DEPENDENCE"`. Also set `high_threshold_breached = true`.
8. **Diversification candidates**: from {IDX_EM_EX_CHINA, IDX_INDIA, IDX_LATAM}, select indices whose pairwise correlations are lowest (best diversifiers). List in alphabetical order.
9. **Sleeve actions**: suggest trim/add/rotate based on concentration and diversification findings.

**Pair formatting**: each pair_id is a 2-element list of index IDs sorted alphabetically.

**Return observations**: equals the number of monthly return data points (levels - 1).

### 3C. Active Allocation View Refresh (e.g., Q2 2026 CIO desk)

**Goal**: Produce active views (UW/N/OW), change vs prior quarter, conviction, and rationale for each requested opportunity set.

**Procedure**:

1. **Read the allocation policy** from `/api/policies` (section `allocation_mapping`). Extract score thresholds and conviction thresholds.
2. **Read prior views** from `/api/allocation/prior-views`. Filter to `quarter == target_quarter` and `previous_quarter == prior_quarter` (the prior-views endpoint stores the *current* assigned view carried forward from the previous quarter). **Important**: the prior-views endpoint gives you the Q2_2026 assigned views that were determined in Q1_2026 — these ARE the prior views for the current refresh.
3. **Read macro signals** from `/api/macro-signals`. Filter to `quarter == target_quarter`. Each entry gives: `opportunity_set`, `score`, `rationale_code`, `drivers`.
4. **For each requested opportunity set**:
   - Look up the macro signal score
   - **Determine view**: score ≥ OW_min → `OW`; score ≤ UW_max → `UW`; else `N`
   - **Determine conviction**: |score| ≥ HIGH_abs_min → `HIGH`; |score| ≥ MEDIUM_abs_min → `MEDIUM`; else `LOW`
   - **Determine change**: compare the current view to the prior view from step 2:
     - Prior `N` → Current `OW`: `UP`
     - Prior `UW` → Current `N`: `UP`
     - Prior `OW` → Current `N`: `DOWN`
     - Prior `N` → Current `UW`: `DOWN`
     - Same view: `UNCHANGED`
   - **Rationale_code**: use the `rationale_code` directly from the macro signal
   - **Asset_class**: from `/api/allocation/opportunity-sets`
5. **Select risk overlay** based on the aggregate direction of views:
   - If HY is UW and duration is OW → `DURATION_QUALITY_TILT` / `tilt_to_duration_quality`
   - If HY is severely UW (|score| large) → `CREDIT_RISK_REDUCTION` / `trim_credit_beta`
   - If equities are broadly OW → `EQUITY_BETA_EXTENSION` / `add_cyclical_equity_beta`
   - If currency signals diverge defensively → `CURRENCY_DEFENSIVE_HEDGE` / `add_currency_hedge`
   - If no clear tilt → `NO_OVERLAY` / `hold_policy_weights`
   - Rationale_codes: list the most relevant codes in business priority order.

**Ordering**: allocation_views rows in the order listed by the request payload's `focus_opportunity_sets`. Risk overlay rationale_codes in business priority order.

**Policy ID**: use the allocation-mapping policy_id from the policies response (`POL_ALLOCATION_MAPPING`).

### 3D. Fixed-Income Risk Rebalance (e.g., PF-FI-LUMEN)

**Goal**: Propose SELL/BUY rotation that reduces HY and watchlist exposure while keeping duration in band.

**Procedure**:

1. **Fetch current portfolio** and enrich with bond/issuer data (same as 3A steps 1-3).
2. **Identify watchlist bonds** in the portfolio — cross-reference each holding's issuer_id against `/api/issuers` watchlist flag.
3. **Identify HY bonds** in the portfolio — bonds with `rating_bucket == "HY"`.
4. **Compute pre-trade metrics** (same formulas as 3A step 4).
5. **Construct rotation**:
   - **SELL side**: prioritize watchlisted HY bonds first, then non-watchlist HY as needed to meet the HY reduction target. Use quantities from the current portfolio, or scale to meet the reduction requirement.
   - **BUY side**: select candidate IG bonds (not watchlisted, not already held in large concentration) to replace the sold bonds. Match total proceeds approximately (dollar-neutral rotation).
6. **Recompute post-trade metrics**:
   - `post_trade_hy_allocation_pct` = 100 × (post-trade HY qty) / total MV
   - `post_trade_duration_years` = weighted average of post-trade holdings
   - `hy_reduction_pct_points` = pre_trade HY% − post_trade HY%
   - `post_trade_watchlist_exposure_usd_m` = sum of remaining watchlist-issuer quantities
7. **Check exception flags**:
   - `hy_cap_pass`: post_trade HY% ≤ max_hy_allocation_pct
   - `duration_band_pass`: post_trade duration ∈ [band_min, band_max]
   - `target_hy_reduction_met`: hy_reduction_pct_points ≥ target_hy_reduction_pct (from policy)
   - `watchlist_exposure_cleared`: post_trade_watchlist_exposure_usd_m == 0

**Rounding**: quantity_usd_m to 1 decimal; risk_metrics percentages and duration to 2 decimals; watchlist exposure to 1 decimal.

**Ordering**: trades sorted by action (SELL before BUY), then by instrument_id ascending within each action. watchlist_sell_ids sorted ascending.

**Risk note code**: choose based on the dominant concern addressed:
- `hy_cap_pressure` if HY was near/above cap
- `watchlist_concentration` if watchlist positions were material
- `duration_preservation` if duration was maintained through the rotation
- `carry_tradeoff` if carry was sacrificed for risk reduction
- `no_action` if no material risk

### 3E. Multi-Asset Committee File (e.g., PF-MA-HELIO)

**Goal**: Combine correlation findings with active allocation views into a single committee decision file.

**Procedure**:

1. **Correlation sub-task**: Run the correlation procedure (3B) on the subset of indices specified in the request. Use the "current 12-month monthly-level window" from the policy (`review_window_start` to `review_window_end` from POL_CORRELATION_DEFAULT).
2. **Identify concentration and diversifier pairs** from the correlation matrix:
   - `highest_concentration`: the pair with the highest correlation
   - `best_diversifier`: the pair with the lowest correlation
3. **Allocation sub-task**: Run the allocation view procedure (3C) on the requested opportunity sets. Include prior_view (from prior quarter), signal_score (from macro signals), view, change, conviction, and rationale_code.
4. **Sleeve actions**: For each sleeve/opportunity set, combine the correlation insight with the allocation view:
   - High correlation + UW view → `trim` or `hedge`
   - High correlation + OW view → `monitor` (concentration concern despite positive view)
   - Low correlation + OW view → `add`
   - Low correlation + N view → `hold`
5. **Determine rebalance trigger**: `correlation_cap_breach` if any pair exceeds the high threshold; `committee_review` for scheduled review; `hy_cap_pressure` or `watchlist_concentration` if credit risk is the primary concern.
6. **Set portfolio_risk_concentration_flag**: `true` if any material concentration exists (e.g., a correlation pair above the high threshold, or a severely UW allocation signal).
7. **Set next_step**: `approve_rotation` if clear actions emerge; `approve_with_monitoring` if views are mixed; `defer_pending_risk_review` if concerns unresolved; `reject_constraint_breach` if a hard constraint fails.

**Ordering**: correlation_summary items by pair_role (highest_concentration first, then best_diversifier). target_sleeve_actions and allocation_views rows in request payload order. Index IDs within each pair sorted alphabetically.

---

## 4. Common Formulas

### Weighted Average

```
weighted_avg = Σ(quantity_i × metric_i) / Σ(quantity_i)
```

Used for: portfolio duration, portfolio YTM. Quantities in USD millions.

### High-Yield Allocation Percentage

```
hy_pct = 100 × Σ(quantity of HY-rated holdings) / Σ(all quantities)
```

HY-rated means `rating_bucket == "HY"` from the bond universe.

### Issuer Concentration

```
concentration_pct = 100 × max_issuer_exposure / total_market_value
```

Where `max_issuer_exposure` is the largest sum of quantities for a single `issuer_id`. Check that this ≤ `issuer_concentration_limit_pct`.

### Monthly Simple Return

```
r_t = (level_t / level_{t-1}) - 1
```

For t from 1 to N-1 where N is the number of monthly level observations in the window.

### Pearson Correlation

```
ρ = Σ((x_i - x̄)(y_i - ȳ)) / sqrt(Σ(x_i - x̄)² × Σ(y_i - ȳ)²)
```

Where x_i and y_i are the monthly simple return series for two indices. Round to 3 decimal places. Number of observations = number of return pairs.

### Signal Score to View

```
if score >= 0.35 → "OW"
elif score <= -0.35 → "UW"
else → "N"
```

### Signal Score to Conviction

```
if abs(score) >= 0.70 → "HIGH"
elif abs(score) >= 0.35 → "MEDIUM"
else → "LOW"
```

### View Change Detection

Compare current view to prior-quarter view:
- `N → OW` or `UW → N` or `UW → OW` (improving direction) → `"UP"`
- `OW → N` or `N → UW` or `OW → UW` (deteriorating direction) → `"DOWN"`
- Same view → `"UNCHANGED"`

---

## 5. Output Conventions

### Precision (decimal places)

| Field category | Precision | Example |
|---|---|---|
| Notional / quantity (USD M) | 1 | `4.0` |
| Market value (USD M) | 2 | `68.00` |
| HY allocation / reduction (pct) | 2 | `7.35` |
| Duration (years) | 2 | `3.28` |
| Yield to maturity (pct) | 2 | `5.80` |
| Correlation | 3 | `0.872` |
| Signal score | 3 | `0.732` |

### Ordering Rules

| Context | Order |
|---|---|
| Trade lists | SELL before BUY; within each action, instrument_id ascending |
| Index IDs in a pair | Alphabetical ascending |
| Index sets (lists) | Alphabetical ascending |
| Allocation view rows | Same order as the request payload's focus_opportunity_sets |
| Sleeve action rows | Ascending by sleeve/opportunity_set name |
| Correlation summary | `highest_concentration` first, then `best_diversifier` |
| Watchlist sell IDs | Ascending instrument_id |
| Rationale codes (list) | Business priority order (most important first) |

### Boolean Flags

Use JSON `true` / `false` (not strings). All constraint check flags are boolean.

### Dates

Format as `YYYY-MM-DD`. Use the API's `as_of_date` (not the local request date) when the output asks for the current environment date.

---

## 6. Common Pitfalls

1. **Stale vs current data**: Local payloads (desk requests, memos, "stale" snapshots) may have dates or marks that conflict with the live API. Always prefer the API. The `/api/market/energy` endpoint includes a `stale_data_warning` field with the cutoff date.

2. **Rating bucket, not rating letter**: Use `rating_bucket` (IG/HY) for HY allocation calculations, not the individual `rating` letter grade. IG = investment grade, HY = high yield.

3. **Watchlist is on the issuer, not the bond**: Check `watchlist` via `/api/issuers` by matching `issuer_id`. A bond's `recommended_theme_tags` may hint at watchlist risk (e.g., "WATCHLIST_RISK") but the authoritative field is the issuer record.

4. **Duration band is inclusive**: `[min, max]` from policy means post-trade duration must be ≥ min AND ≤ max.

5. **Return observations count**: For N monthly index levels, there are N-1 monthly returns. The review window's `return_observations` is N-1, not N.

6. **Simple returns, not log returns**: Always use `(P_t / P_{t-1}) - 1`, never `ln(P_t / P_{t-1})`.

7. **Prior views look-up**: The `/api/allocation/prior-views` endpoint returns entries keyed by `quarter` (the target quarter) and `previous_quarter`. For a Q2_2026 refresh, filter to `quarter == "Q2_2026"` and `previous_quarter == "Q1_2026"`. These entries represent the views assigned in Q1_2026 that are the "prior" for the Q2 refresh.

8. **View change direction**: `UP` means the view became more favorable (UW→N→OW direction), `DOWN` means less favorable. Check the view_rank from the policy: OW=1, N=0, UW=-1. Compare ranks numerically when in doubt.

9. **Energy-linked filter**: The `energy_linked` boolean on bonds determines eligibility for energy-credit portfolios. A bond can be in the Utilities or Materials sector but still be `energy_linked: true`.

10. **Subsector vs sector**: For diversification checks, use `subsector` (more granular), not `sector`. The constraint `subsector_min_count_for_diversified` counts distinct subsectors.

11. **Multi-asset policy composition**: POL_MULTI_ASSET_DEFAULT and POL_MULTI_ASSET_RISK compose from sub-policies. Their fields `uses_allocation_mapping`, `uses_correlation_default`, `uses_credit_default`, `uses_credit_risk_reduction` tell you which sub-policy thresholds to apply. Always check these flags.

12. **Risk overlay selection is holistic**: Don't pick the overlay from just one signal. Consider the overall pattern: if duration signals are OW while credit/HY signals are UW, the overlay should address credit risk (CREDIT_RISK_REDUCTION) rather than duration (DURATION_QUALITY_TILT). If equity signals dominate, consider EQUITY_BETA_EXTENSION. If no clear tilt, NO_OVERLAY.

13. **Candidate flag**: Bonds with `candidate: false` are existing holdings that should not be considered for new purchases (they may be legacy positions). Bonds with `candidate: true` are available for selection.

14. **Correlation pair_id ordering**: Always sort the two index IDs alphabetically within a pair. The answer template requires ascending alphabetical order.

15. **Even split for ticket packages**: When the desk specifies "exactly N tickets totaling $X million, split evenly," each ticket is $X/N million.
