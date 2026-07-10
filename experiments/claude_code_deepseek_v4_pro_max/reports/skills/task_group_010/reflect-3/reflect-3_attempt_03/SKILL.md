# Asteria Investment Office — Operational Skill

## Core principle
Always use the **current shared Asteria environment** (remote HTTP API) as the authoritative book of record. Local payloads may carry stale marks, worksheet snapshots, or pre-reconciliation estimates. When a local payload disagrees with the API, the API wins. Express this precedence explicitly in any output field that asks for it (use `"current_environment_over_stale_payload"`).

---

## API data sources and endpoints

| Resource | Endpoint | Key fields returned |
|---|---|---|
| Catalog | `GET /api/catalog` | All ids: portfolios, bonds, indices, issuers, policies, opportunity-sets |
| Policies | `GET /api/policies` | Top-level `policy_id` (e.g., `POLICY_SET_2026_05`), allocation-mapping thresholds, credit constraints, correlation thresholds |
| Portfolios | `GET /api/portfolios/<id>` | Holdings (instrument_id, quantity_usd_m, sleeve), as_of_date, constraint_policy_id, market_value_usd_m |
| Bonds | `GET /api/instruments/bonds` | instrument_id, issuer_id, rating_bucket (IG/HY), modified_duration_years, yield_to_maturity_pct, energy_linked, candidate, subsector, recommended_theme_tags |
| Issuers | `GET /api/issuers` | issuer_id, watchlist (bool), subsector, rating_bucket, research_tags |
| Energy signals | `GET /api/market/energy` | Commodity scores/direction, pitch themes |
| Indices | `GET /api/indices` | index_id, level_start_date, level_end_date, frequency |
| Index levels | `GET /api/index-levels` | Monthly level per index_id (dates YYYY-MM-DD, float levels) |
| Opportunity sets | `GET /api/allocation/opportunity-sets` | opportunity_set, asset_class, display_order |
| Prior views | `GET /api/allocation/prior-views` | opportunity_set, quarter, previous_quarter, view (UW/N/OW), conviction |
| Macro signals | `GET /api/macro-signals` | opportunity_set, quarter, score, rationale_code, drivers |

**Always use the `as_of_date` from the portfolio or policies endpoint** (typically `"2026-05-29"`) as the answer's `as_of_date`.

---

## Portfolio-metric calculations

### Weighted modified duration
For each holding: weight × modified_duration_years. Sum products, divide by total market value. Round to **2 decimal places**.

### Weighted yield to maturity (YTM)
For each holding: weight × yield_to_maturity_pct. Sum products, divide by total market value. Round to **2 decimal places**.

### HY allocation percentage
Sum of all HY-rated holdings (rating_bucket == "HY") divided by total market value × 100. Round to **2 decimal places**.

### HY reduction (percentage points)
Pre-trade HY% minus post-trade HY%. Round to **2 decimal places**.

### Post-trade metrics
Compute over the **full resulting portfolio** (existing holdings minus sells plus buys). Each metric uses its own weighted-average formula. Re-verify that post-trade values sit inside the constraint band declared by the policy.

---

## Policy thresholds

### Allocation view mapping (`POL_ALLOCATION_MAPPING`)
From signal `score`:
- **score > +0.35 → OW**
- **score < −0.35 → UW**
- **−0.35 ≤ score ≤ +0.35 → N**

### Conviction
From absolute signal score:
- **\|score\| ≥ 0.70 → HIGH**
- **0.35 ≤ \|score\| < 0.70 → MEDIUM**
- **\|score\| < 0.35 → LOW**

### View change
Compare the new view (from current signal score) to the prior quarter's view from `/api/allocation/prior-views`:
- Prior OW → new UW → `DOWN`
- Prior OW → new OW → `UNCHANGED`
- Prior N → new OW → `UP`
- Prior N → new UW → `DOWN`
- Prior UW → new N → `UP`
- etc.

Always use the **Q2_2026 signal scores** with the **Q1_2026→Q2_2026 prior views** (the row where `previous_quarter` matches the prior quarter and `quarter` matches the target quarter).

### Rationale code
Use the **exact rationale_code from the macro-signal** for that opportunity_set/quarter. Do not substitute even if another allowed code seems plausible.

### Credit constraints (`POL_CREDIT_DEFAULT` / `POL_CREDIT_RISK_REDUCTION`)
- `max_hy_allocation_pct`: 20.0 (HY cap)
- `duration_band_years`: [3.0, 5.0]
- `issuer_concentration_limit_pct`: 12.0
- `target_hy_reduction_pct`: 4.0 (only when policy is `POL_CREDIT_RISK_REDUCTION`)

### Correlation thresholds (`POL_CORRELATION_DEFAULT`)
- `correlation_high_threshold`: 0.80 (breach = concentration risk)
- `correlation_low_threshold`: 0.20 (below = diversifier)

---

## Pearson correlation of monthly simple returns

1. Extract levels for each index_id from `/api/index-levels` over the requested date window.
2. Number of levels = N, number of return observations = **N − 1**.
3. Monthly simple return: `(level_t − level_{t−1}) / level_{t−1}`.
4. Compute standard Pearson correlation on the paired return vectors.
5. Round to **3 decimal places**.
6. Within each pair, list the two index ids in **ascending alphabetical order**.
7. For the `index_set` output field, list all universe indices in ascending alphabetical order.

---

## Bond selection rules

### Energy-credit (e.g., PF-EN-ALTA)
1. Filter to `energy_linked: true` bonds.
2. Exclude **watchlisted** issuers (cross-reference `/api/issuers` — `watchlist: true`).
3. Prefer bonds that improve the portfolio's weighted YTM over the current level.
4. Both selected bonds must have **different issuers** and **different subsectors**.
5. Post-trade HY must stay ≤ `max_hy_allocation_pct` (20%).
6. Post-trade weighted duration must stay inside `duration_band_years` [3.0, 5.0].
7. Sort trade_package entries **ascending by instrument_id**.
8. Each notional is in USD millions, precision 1 decimal.

### Fixed-income risk rebalance (e.g., PF-FI-LUMEN)
1. Identify all watchlisted holdings → must SELL fully.
2. Sell HY pressure points until post-trade HY% ≤ 20% and HY reduction ≥ 4.0 ppt.
3. Buy only IG, non-watchlist candidates from the shortlist.
4. Post-trade weighted duration must stay in [3.0, 5.0].
5. Trades list: SELL entries before BUY entries; within each action, ascending by instrument_id.
6. `watchlist_sell_ids`: ascending instrument_id order, listing every sold watchlisted bond.
7. `buys_avoid_watchlist`: must be `true` (hard constraint from meeting preferences).

---

## Output conventions

### Ordering rules
- **Index ids in lists**: ascending alphabetical (e.g., `["IDX_CHINA", "IDX_EM"]`).
- **Trade entries**: SELL before BUY; within each action, ascending by instrument_id.
- **Allocation view rows**: follow the request payload's `focus_opportunity_sets` order exactly.
- **Sleeve actions**: follow the template's declared item order.
- **Rationale codes in risk overlay**: business priority order (highest priority first).

### Numeric precision
- Portfolio market value, HY%, duration, YTM: **2 decimal places**.
- Trade notionals, watchlist exposure: **1 decimal place**.
- Correlations: **3 decimal places**.
- Signal scores: **3 decimal places**.

### Boolean flags
- All constraint-check booleans must reflect the **post-trade state**.
- `hy_cap_pass`: post-trade HY% ≤ max cap.
- `duration_band_pass`: post-trade duration inside [min, max].
- `selected_issuer_diversification_pass`: the chosen bonds have different issuer_ids.
- `selected_subsector_diversification_pass`: the chosen bonds have different subsectors.
- `watchlist_avoidance_pass`: no selected bond's issuer is on the watchlist.
- `target_hy_reduction_met`: HY reduction ppt ≥ target_hy_reduction_pct.
- `watchlist_exposure_cleared`: post-trade watchlist exposure = 0.

### Policy ID in lineage
Use the **top-level policy set id** (e.g., `"POLICY_SET_2026_05"`) from the policies endpoint, not a sub-policy id like `"POL_ALLOCATION_MAPPING"`.

### Data precedence
When the answer template includes a `data_precedence` field: choose `"current_environment_over_stale_payload"` whenever the local payload contains a snapshot date or worksheet that predates the API's `as_of_date`.

---

## Common pitfalls

1. **Using stale payload quantities instead of current portfolio holdings.** The API portfolio endpoint is the book of record. The local payload may have different quantities due to unreconciled worksheets.

2. **Wrong policy_id in lineage.** Use the top-level `policy_id` from `GET /api/policies` (e.g., `"POLICY_SET_2026_05"`), not a child policy's `policy_id`.

3. **Mixing up prior-view quarter semantics.** The prior-views API returns rows where `previous_quarter` names the quarter in which the view was set and `quarter` names the target quarter. For a Q2_2026 target, look up the row with `previous_quarter: "Q1_2026"` and `quarter: "Q2_2026"`.

4. **Substituting rationale codes.** Always take the rationale_code verbatim from the macro-signal record, even if another allowed enum value seems to fit better.

5. **Incorrect return-observation count.** With N monthly index levels, there are N−1 monthly return observations, not N.

6. **Rounding before final calculation.** Carry full precision through intermediate steps; round only the final answer fields to the declared precision.

7. **Ignoring issuer concentration on new buys.** Even when the selected bonds have different issuers and different subsectors, check that no single issuer's post-trade weight exceeds the concentration limit if the constraint applies.

8. **Using the wrong correlation pair for "highest".** The "highest_positive" pair is the one with the numerically largest Pearson correlation within the index universe — not the pair most relevant to a stated concern.

9. **Mismatched sleeve names.** In sleeve_actions and similar fields, use the exact sleeve name as it appears in the portfolio holdings.

10. **Forgetting to sort pairs.** Every pair_id output must list its two index ids in ascending alphabetical order.
