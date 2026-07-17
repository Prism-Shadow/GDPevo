# Asteria Investment Office — Task-Solving Skill

## Environment & Data Precedence

**Single source of truth**: The remote Asteria API at `GDPEVO_ENV_BASE_URL` (set per session). All portfolio, bond, issuer, index, policy, allocation, and signal data lives there. The root `GET /` enumerates available endpoints.

**Stale-data rule**: Every local payload (desk requests, memos, committee packets, stale snapshots) may contain outdated marks, quantities, or preferences. The API environment is the current book of record. When local data conflicts with API data, the API wins. The `data_precedence` field in relevant templates should be `"current_environment_over_stale_payload"` whenever the API is used to resolve or override local numbers.

**as_of_date**: Always pulled from the current portfolio record on the API (`/api/portfolios/<id>` → `as_of_date`). Across the 2026-05 environment this is `"2026-05-29"`. Use it for every output's `as_of_date` field.

---

## API Data Model Quick Reference

| Endpoint | Key fields | Used by tasks |
|---|---|---|
| `GET /api/catalog` | All IDs (portfolios, bonds, indices, issuers, policies, opportunity sets) | Orientation |
| `GET /api/policies` | Credit constraints (HY cap, duration band, issuer limit, subsector min), correlation thresholds (high 0.8, low 0.2), allocation mapping (view/conviction thresholds), policy IDs | All |
| `GET /api/portfolios/<id>` | Holdings (instrument_id, quantity_usd_m, sleeve), market_value_usd_m, constraint_policy_id, as_of_date | 1,2,4,5 |
| `GET /api/instruments/bonds` | instrument_id, issuer_id, rating_bucket (IG/HY), yield_to_maturity_pct, modified_duration_years, energy_linked (bool), candidate (bool), sector, subsector, recommended_theme_tags | 1,4,5 |
| `GET /api/issuers` | issuer_id, watchlist (bool), rating_bucket, sector, subsector, credit_outlook | 1,4 |
| `GET /api/indices` | index_id, display_name, region, frequency, level_start_date, level_end_date | 2,5 |
| `GET /api/index-levels` | Per-index array of {date, level} ordered chronologically, 12 monthly points from 2025-05-30 to 2026-04-30 | 2,5 |
| `GET /api/market/energy` | Commodity signals with score, direction, signal_id | 1 |
| `GET /api/allocation/opportunity-sets` | opportunity_set, asset_class, sub_asset_class, display_order | 3,5 |
| `GET /api/allocation/prior-views` | opportunity_set, quarter, previous_quarter, view, conviction | 3,5 |
| `GET /api/macro-signals` | opportunity_set, quarter, score, rationale_code, drivers | 3,5 |

---

## Task-Type Workflows

### Type 1: Credit Trade Strategy (train_001 — PF-EN-ALTA)

**Goal**: Select N BUY/SELL tickets meeting notional, eligibility, and constraint requirements while improving carry.

**Step-by-step**:
1. `GET /api/portfolios/<id>` → current holdings, MV, constraint_policy_id, as_of_date
2. `GET /api/policies` → read the constraint block matching the portfolio's `constraint_policy_id` for HY cap, duration band, issuer limit, subsector min
3. `GET /api/instruments/bonds` → filter to eligible candidates (`candidate: true`, plus any sector/theme filters from the request)
4. `GET /api/issuers` → cross-reference `watchlist` status; never BUY a watchlisted issuer's bonds
5. `GET /api/market/energy` (if energy-linked) → thematic support for sales positioning
6. Select bonds, compute post-trade metrics, run constraint checks, fill template

**Post-trade metric formulas** (all market-value-weighted):
- `total_market_value_usd_m` = current MV + sum(new notionals), rounded to 2 decimals
- `hy_allocation_pct` = (sum of HY-rated holdings post-trade) / post_trade_MV × 100, rounded to 2 decimals
- `weighted_modified_duration_years` = Σ(holding_qty × bond_duration) / post_trade_MV, rounded to 2 decimals
- `weighted_yield_to_maturity_pct` = Σ(holding_qty × bond_ytm) / post_trade_MV, rounded to 2 decimals

**Constraint checks** (all boolean):
- `hy_cap_pass`: post_trade_hy_pct ≤ max_hy_allocation_pct (20%)
- `duration_band_pass`: post_trade_duration ∈ [duration_band_years[0], duration_band_years[1]] ([3.0, 5.0])
- `selected_issuer_diversification_pass`: the selected bonds are from at least 2 distinct issuers, AND no single issuer's post-trade total exceeds `issuer_concentration_limit_pct` (12%) of post-trade MV
- `selected_subsector_diversification_pass`: the selected bonds span at least `subsector_min_count_for_diversified` (2) distinct subsectors
- `watchlist_avoidance_pass`: none of the selected BUY bonds belong to a watchlisted issuer

**Sales positioning**: Match to template enum. For energy-income pitches, `"multi_asset_income"` + theme from market signals (e.g., `"lng_export_tailwind"` if LNG scores highest).

**Trade ordering**: Sort by `instrument_id` ascending within each action group, or as specified by the template.

---

### Type 2: Equity Correlation Review (train_002 — PF-INT-NEXVEN)

**Goal**: Compute Pearson correlations across an index universe and identify concentration/diversification signals.

**Step-by-step**:
1. `GET /api/portfolios/<id>` → holdings, constraint_policy_id
2. `GET /api/policies` → correlation thresholds (`correlation_high_threshold: 0.8`, `correlation_low_threshold: 0.2`)
3. `GET /api/index-levels` → for each index in the review universe, extract the 12 monthly level values
4. Compute monthly simple returns, then all pairwise Pearson correlations

**Return calculation** (CRITICAL — use simple returns, NOT log returns):
```
For each index, for t = 1..11:
    r_t = (level_t - level_{t-1}) / level_{t-1}
```
This yields 11 return observations per index (12 levels → 11 returns).

**Pearson correlation**:
```
r_xy = Σ((x_i - x̄)(y_i - ȳ)) / sqrt(Σ(x_i - x̄)² × Σ(y_i - ȳ)²)
```
Round to **3 decimal places** for all correlation outputs.

**Extreme pairs**:
- `highest_positive`: the pair with the largest (most positive) correlation value
- `lowest`: the pair with the smallest (most negative) correlation value
- For each, output `pair_id` (list of 2 index IDs, alphabetically sorted) and `correlation`

**Concentration analysis**:
- `china_asia_dependence_flag`: true if China / AC Asia Pac ex JP correlation exceeds `correlation_high_threshold` (0.8)
- `primary_code`: `"CHINA_ASIA_DEPENDENCE"` if flag is true and this is the primary concern; `"GLOBAL_DEVELOPED_OVERLAP"` if developed-market pairs dominate; `"NO_MATERIAL_CONCENTRATION"` otherwise
- `high_threshold_breached`: true if ANY pair exceeds 0.8

**Diversification candidates**: Among the allowed candidate set, select indices whose pairwise correlations are ≤ `correlation_low_threshold` (0.2) with the concentration source. Sort alphabetically.

**Index/pair ordering**: Always sort index IDs alphabetically within pairs and lists.

---

### Type 3: Allocation View Refresh (train_003 — CIO Q2 2026)

**Goal**: Derive active allocation views from macro signal scores using policy thresholds.

**Step-by-step**:
1. `GET /api/allocation/opportunity-sets` → asset_class for each opportunity set
2. `GET /api/macro-signals` → filter to `quarter: "Q2_2026"` entries; extract `score` and `rationale_code` for each requested opportunity set
3. `GET /api/allocation/prior-views` → filter to `quarter: <target_quarter>` entries (these are the views set in the prior quarter for the target quarter); extract `view` as the prior view
4. `GET /api/policies` → allocation_mapping thresholds

**View derivation from signal score** (use `allocation_mapping.view_score_thresholds`):
| Condition | View |
|---|---|
| score ≥ OW_min (0.35) | `"OW"` |
| score ≤ UW_max (-0.35) | `"UW"` |
| -0.35 < score < 0.35 | `"N"` |

**Change vs. prior quarter** (use `allocation_mapping.view_rank`: OW=1, N=0, UW=-1):
| Condition | Change |
|---|---|
| current_rank > prior_rank | `"UP"` |
| current_rank < prior_rank | `"DOWN"` |
| current_rank == prior_rank | `"UNCHANGED"` |

**Conviction from abs(score)** (use `allocation_mapping.conviction_thresholds`):
| abs(score) | Conviction |
|---|---|
| ≥ HIGH_abs_min (0.7) | `"HIGH"` |
| ≥ MEDIUM_abs_min (0.35) | `"MEDIUM"` |
| < LOW_abs_below (0.35) | `"LOW"` |

**Rationale code**: Copy the `rationale_code` from the macro-signal record for that opportunity set. This is a direct lookup, not derived.

**Risk overlay**: Select `overlay_code` and `primary_action` based on the aggregate pattern of views. Common patterns:
- Many UW credit views + OW duration views → `"CREDIT_RISK_REDUCTION"` / `"trim_credit_beta"`
- OW on duration, mixed equities → `"DURATION_QUALITY_TILT"` / `"tilt_to_duration_quality"`
- No strong tilt → `"NO_OVERLAY"` / `"hold_policy_weights"`

`rationale_codes` for the overlay: list the most relevant rationale codes from the macro signals that support the overlay choice, in business priority order (highest priority first).

**Row ordering**: Follow the request payload's `focus_opportunity_sets` order exactly.

**Policy ID**: Use the `policy_id` from the `allocation_mapping` block in `/api/policies`.

---

### Type 4: Fixed-Income Risk Rebalance (train_004 — PF-FI-LUMEN)

**Goal**: Rotate out of HY/watchlist positions and into eligible IG candidates while meeting reduction targets and duration constraints.

**Step-by-step**:
1. `GET /api/portfolios/<id>` → current holdings, MV, constraint_policy_id
2. `GET /api/policies` → read the matching constraint block for HY cap, duration band, target HY reduction
3. `GET /api/instruments/bonds` → current holdings' details + candidate pool
4. `GET /api/issuers` → watchlist cross-reference
5. Design SELL/BUY rotation, compute post-trade metrics, fill template

**Rotation design rules**:
- SELL: target HY-rated holdings and/or watchlisted-issuer bonds. Use the portfolio's actual current quantities (from API), not stale payload quantities.
- BUY: select from `candidate: true` bonds that are IG-rated and NOT from watchlisted issuers. Match the portfolio's sector/style.
- SELL and BUY notional amounts should balance (or be sized to meet the HY reduction target).
- `hy_reduction_pct_points` = pre_trade_hy_pct − post_trade_hy_pct, rounded to 2 decimals.

**Post-trade watchlist exposure**: Sum of all post-trade holdings from watchlisted issuers. If all watchlisted bonds are sold, this is 0.0.

**Trade ordering**: SELL before BUY, then by `instrument_id` ascending within each action group.

**Constraint flags**:
- `hy_cap_pass`: post_trade_hy_pct ≤ max_hy_allocation_pct
- `duration_band_pass`: post_trade_duration ∈ [band_low, band_high]
- `target_hy_reduction_met`: hy_reduction_pct_points ≥ target_hy_reduction_pct (4.0 for risk-reduction policy)
- `watchlist_exposure_cleared`: post_trade_watchlist_exposure_usd_m == 0.0 (or negligible)

**Watchlist handling output**:
- `watchlist_sell_ids`: instrument_ids of sold watchlisted bonds, sorted ascending
- `buys_avoid_watchlist`: true if all BUY tickets are from non-watchlisted issuers

**risk_note_code**: Pick the enum value that best describes the primary risk trade-off in the rotation.

---

### Type 5: Multi-Asset Committee JSON (train_005 — PF-MA-HELIO)

**Goal**: Combine equity correlation findings with active allocation views into a single committee decision file.

**Step-by-step**:
1. `GET /api/portfolios/<id>` → holdings, policy_id
2. `GET /api/index-levels` → for the 4-index subset (EM, China, India, LatAm), compute Pearson correlations (same Type 2 method)
3. `GET /api/macro-signals` → for the requested opportunity sets (Emerging Markets, India, Latin America, USD), get scores and rationale codes
4. `GET /api/allocation/prior-views` → prior views for the requested sets
5. `GET /api/policies` → thresholds

**Correlation summary** (2 items, in order):
1. `highest_concentration`: the pair with the highest positive correlation among the 4-index subset → indicates concentration risk
2. `best_diversifier`: the pair with the lowest (most negative) correlation → indicates diversification benefit

**Target sleeve actions** (ordered by opportunity_set as specified):
- Derive from both correlation signals AND allocation views
- `"trim"` for concentrated/overweight positions; `"add"` for diversifying/underweight positions; `"hold"` for neutral; `"hedge"` for high-concentration positions needing offset; `"monitor"` for borderline cases; `"rotate"` for replacing one exposure with another

**Allocation views**: Same Type 3 derivation but includes `signal_score` (raw score, rounded to 3 decimals) and `prior_view` (from prior-views endpoint).

**rebalance_trigger**: The primary reason for action — pick the enum that matches the dominant signal.

**portfolio_risk_concentration_flag**: true if any correlation in the subset exceeds the high threshold (0.8).

**next_step**: The committee's decision based on constraint checks and risk flags.

---

## Precision & Rounding Rules

All numeric output fields must match the precision declared in the answer template:

| Field type | Typical precision | Example |
|---|---|---|
| Market values, notionals | 1 decimal (USD M) | `4.0`, `68.0` |
| Portfolio MV | 2 decimals (USD M) | `68.00` |
| HY allocation % | 2 decimals | `13.24` |
| Duration (years) | 2 decimals | `3.28` |
| YTM % | 2 decimals | `5.80` |
| Correlation | 3 decimals | `0.974` |
| Signal score | 3 decimals | `0.732` |
| HY reduction (pp) | 2 decimals | `4.00` |

Use standard rounding (round half to even, or `round(value, N)` in Python). Do not truncate.

---

## Sorting & Ordering Conventions

1. **Index IDs in pairs**: Always alphabetical ascending (e.g., `["IDX_CHINA", "IDX_LATAM"]`)
2. **Index lists**: Alphabetical ascending by index_id
3. **Trade lists**: When template says "SELL before BUY, then instrument_id ascending within each action" — follow that exactly
4. **Allocation rows**: Follow the request payload's `focus_opportunity_sets` order — preserve the input sequence, do not re-sort
5. **Correlation summary items**: Follow the template's `item_order` array
6. **Watchlist sell IDs**: Ascending instrument_id order
7. **Overlay rationale codes**: Business priority order (highest priority first)

---

## Common Pitfalls

1. **Using stale payload quantities as current holdings**. Always fetch current quantities from `/api/portfolios/<id>`. Local payloads often contain stale snapshots.
2. **Log returns instead of simple returns**. The spec says "monthly simple returns" — use `(P₁-P₀)/P₀`, never `ln(P₁/P₀)`.
3. **Confusing signal score sign with view direction**. A negative score below -0.35 maps to UW; a positive score above 0.35 maps to OW. The sign of the score IS the direction signal.
4. **Watchlist check via bond tags only**. Always cross-reference `/api/issuers` → `watchlist: true`. The `WATCHLIST_RISK` theme tag on a bond is a hint, but the issuer record is authoritative.
5. **Filtering out non-energy-linked bonds for non-energy portfolios**. Only apply `energy_linked: true` filter when the task explicitly requires energy-linked bonds (train_001). Other credit tasks use the full bond universe.
6. **Wrong policy block**. Match the portfolio's `constraint_policy_id` to the correct block in `/api/policies`. Different portfolios use different policies with different thresholds.
7. **Incorrect observation count**. With 12 monthly index levels, there are 11 simple returns. Report `return_observations: 11`.
8. **Missing the `candidate` filter**. Only bonds with `candidate: true` can be selected for BUY trades. Held bonds may have `candidate: false`.
9. **Overlooking issuer concentration from existing holdings**. When checking `selected_issuer_diversification_pass`, account for the TOTAL post-trade exposure per issuer (existing + new), not just the new tickets.
10. **Using the wrong quarter's prior views**. Filter prior-views by `quarter: <target_quarter>` to get the views that were set in the prior quarter for the current target quarter.
11. **Rounding before all calculations are done**. Keep full precision through intermediate steps; only round final output values.
12. **Not using the answer_template.json structure**. Every task provides an `answer_template.json` — match its exact key names, types, enums, and nesting.

---

## Output Conventions

- Return **only** the JSON object (unless the task explicitly allows narrative). No markdown wrapping, no commentary outside the JSON.
- All `required` keys in the template must be present, even if their value is an empty list.
- Boolean fields use JSON `true`/`false` (not strings).
- String enum values must match the allowed values exactly, including case and underscores.
- The `portfolio_id` field is always a required string matching the portfolio being analyzed.
