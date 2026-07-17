# Asteria Investment Office — Operational Skill

## Core principle: Environment is the book of record

The shared Asteria API is the **current, authoritative source**. Local payloads (desk requests, meeting memos, committee packets) are **intake context only** — they may contain stale marks, outdated worksheets, or pre-reconciled snapshots. When a local payload conflicts with the API, the API wins.

**Data-precedence value:** `"current_environment_over_stale_payload"` — use this whenever the task template includes a `data_precedence` field and the local payload carries snapshot data that the API supersedes.

## API inventory (all `GET`, no auth)

| Endpoint | Returns |
|---|---|
| `/api/catalog` | All IDs (bonds, indices, issuers, portfolios, policies, opportunity sets) |
| `/api/policies` | Constraint thresholds, allocation mapping, correlation policy, as-of date |
| `/api/portfolios/<id>` | Holdings (instrument_id, quantity_usd_m, sleeve, asset_class), market_value_usd_m, constraints, as_of_date |
| `/api/instruments/bonds` | Full bond universe: rating_bucket (IG/HY), ytm, modified_duration_years, subsector, issuer_id, energy_linked, candidate, recommended_theme_tags, maturity, spread_bps |
| `/api/issuers` | Issuer research: watchlist (bool), rating_bucket, sector, subsector, credit_outlook |
| `/api/index-levels/<id>` or `/api/index-levels` | Monthly index levels with dates and level values |
| `/api/allocation/opportunity-sets` | Taxonomy: opportunity_set → asset_class mapping |
| `/api/allocation/prior-views` | Prior-quarter views per opportunity_set; keyed by `quarter` and `previous_quarter` |
| `/api/macro-signals` | Current-quarter signal scores, rationale_code, and drivers per opportunity_set |
| `/api/market/energy` | Energy commodity signals and pitch themes |

## Universal conventions

### Dates
- The environment `as_of_date` lives in `/api/policies[].as_of_date` and in every portfolio response. Use it as the output `as_of_date`; do not carry forward a date from a local payload.
- Index level windows are given as `level_start_date` / `level_end_date` in the request. The number of monthly observations = count of levels − 1.

### Numeric precision (follow the answer template exactly)
| Field type | Precision | Example |
|---|---|---|
| USD millions (notional, quantity, market value) | 1 decimal | `4.0`, `12.0` |
| Portfolio market value, HY %, duration, YTM | 2 decimals | `68.00`, `13.24`, `3.28` |
| Correlations | 3 decimals | `0.974`, `-0.825` |
| Signal scores | 3 decimals | `-0.373`, `0.732` |
| Percentage-point reductions | 2 decimals | `25.64` |

### Sorting
- **Instrument IDs in lists:** ascending alphabetical (e.g. `"BND_BLUEGAS_2030"` < `"BND_RIVER_2029"`).
- **Index IDs in pair arrays:** ascending alphabetical (e.g. `["IDX_CHINA","IDX_EM"]`).
- **Trade tickets:** by action group (SELL before BUY), then ascending instrument_id within each group.
- **Allocation/opportunity-set rows:** preserve the order given in the request payload's focus list.
- **Sleeve-action rows:** follow the template's prescribed item order (usually the request's opportunity-set list order).

### Watchlist
- Check `/api/issuers` → `watchlist` boolean. Bonds whose issuer is watchlisted carry `WATCHLIST_RISK` in their `recommended_theme_tags`.
- A buy that goes to a watchlisted issuer fails `watchlist_avoidance_pass` / `buys_avoid_watchlist`.
- Watchlist sell IDs are the instrument_ids of sold holdings whose issuer is on the watchlist.

## Task-type workflows

### A. Credit desk / bond selection (e.g. PF-EN-ALTA, PF-FI-LUMEN)

**Step 1 — Load current state**
- `GET /api/portfolios/<id>` → holdings, current market_value_usd_m, constraints policy_id.
- `GET /api/policies` → extract the relevant credit policy (POL_CREDIT_DEFAULT or POL_CREDIT_RISK_REDUCTION). Key thresholds:
  - `max_hy_allocation_pct`: 20.0
  - `duration_band_years`: [3.0, 5.0]
  - `issuer_concentration_limit_pct`: 12.0
  - `subsector_min_count_for_diversified`: 2
  - `target_hy_reduction_pct` (risk-reduction policy only): 4.0

**Step 2 — Load bond & issuer universe**
- `GET /api/instruments/bonds` → filter for `candidate: true` (unless an existing holding is a sell target, which may be `candidate: false`).
- `GET /api/issuers` → join on `issuer_id` for watchlist status.

**Step 3 — Select trades**
- For buys: pick candidate bonds that are energy-linked (if the portfolio is energy-focused), IG-rated, non-watchlist, with attractive carry (YTM) while keeping duration inside the band.
- For sells: target HY positions and watchlisted positions.
- Each trade has `action`, `instrument_id`, and quantity (USD millions, 1 decimal).
- Two BUY tickets usually means exactly two buy instruments, evenly split.

**Step 4 — Compute post-trade metrics**
```
post_market_value = pre_market_value + sum(buy quantities)   [sells change composition, not MV, when proceeds are reinvested]

For funded buys (new money): post_mv = pre_mv + sum(buys)
For rotation (sell to fund buys): post_mv = pre_mv (net zero), buys funded by sell proceeds

hy_pct = sum(quantities of HY-rated holdings) / post_market_value * 100

weighted_duration = sum(qty_i × duration_i) / sum(qty_i)     [over all post-trade holdings]

weighted_ytm = sum(qty_i × ytm_i) / sum(qty_i)               [over all post-trade holdings]

hy_reduction_pts = pre_trade_hy_pct - post_trade_hy_pct
```

**Step 5 — Constraint checks** (all boolean)
- `hy_cap_pass`: post_trade HY % ≤ max_hy_allocation_pct
- `duration_band_pass`: duration_band_years[0] ≤ weighted_duration ≤ duration_band_years[1]
- `selected_issuer_diversification_pass`: no single issuer's total post-trade quantity exceeds issuer_concentration_limit_pct of post_market_value
- `selected_subsector_diversification_pass`: at least subsector_min_count_for_diversified distinct subsectors among selected (bought) instruments
- `watchlist_avoidance_pass`: no buy goes to a watchlisted issuer
- `target_hy_reduction_met`: hy_reduction_pts ≥ target_hy_reduction_pct (risk-reduction policy)

**Step 6 — Watchlist handling**
- `watchlist_sell_ids`: list of sold instrument_ids whose issuer `watchlist` is true, sorted ascending.
- `buys_avoid_watchlist`: true if no buy-side instrument has a watchlisted issuer.

### B. Equity correlation review (e.g. PF-INT-NEXVEN, PF-MA-HELIO correlation portion)

**Step 1 — Fetch index levels**
- `GET /api/index-levels` → filter to the requested index IDs and the date window [level_start_date, level_end_date] inclusive.

**Step 2 — Compute monthly simple returns**
```
For each index, for each consecutive pair of monthly levels:
  return_t = (level_t / level_{t-1}) - 1

return_observations = count of levels - 1   (e.g. 12 monthly levels → 11 return observations)
```

**Step 3 — Compute Pearson correlation for every index pair**
- Standard Pearson r on the paired monthly return series.
- Correlation values rounded to **3 decimal places**.
- Pair identifiers: array of two index IDs, **sorted alphabetically**.

**Step 4 — Identify extreme pairs**
- `highest_positive`: the pair with the largest positive correlation (closest to +1.0).
- `lowest`: the pair with the most negative correlation (closest to −1.0). This is labeled `lowest` in the template, not "most negative".

**Step 5 — Concentration analysis**
- Thresholds from `POL_CORRELATION_DEFAULT` in `/api/policies`:
  - `correlation_high_threshold`: 0.8
  - `correlation_low_threshold`: 0.2
- If China↔Asia Pacific ex-Japan correlation exceeds the high threshold → `china_asia_dependence_flag: true`, `primary_code: "CHINA_ASIA_DEPENDENCE"`, `high_threshold_breached: true`.
- Otherwise `primary_code: "NO_MATERIAL_CONCENTRATION"`.

**Step 6 — Diversification candidates**
- From the subset `["IDX_EM_EX_CHINA", "IDX_INDIA", "IDX_LATAM"]`, include any index whose pairwise correlations against the concentration pair members are **below** the high threshold. Sorted alphabetically.

**Step 7 — Sleeve actions**
- Sleeves with high concentration → `"trim"`.
- Diversifying sleeves with low/negative correlation → `"add"`.
- Match sleeve names to index IDs using the portfolio's holding sleeve labels.
- Sort by sleeve name alphabetically (template says "ascending by sleeve").

### C. Allocation view refresh (e.g. train_003, train_005 allocation portion)

**Step 1 — Load taxonomy and signals**
- `GET /api/allocation/opportunity-sets` → maps each opportunity_set to its `asset_class`.
- `GET /api/macro-signals` → filter to the target quarter (e.g. `Q2_2026`). Each entry has: `opportunity_set`, `score`, `rationale_code`.
- `GET /api/allocation/prior-views` → filter to rows where `quarter` = target quarter (these rows carry `previous_quarter` = prior quarter's view in `view`). **Important:** the prior-views endpoint returns rows keyed by `quarter` (the target quarter), with `previous_quarter` naming the comparison quarter and `view` giving that prior quarter's view. Each row's `view` field IS the prior view for the target quarter.

**Step 2 — Determine current view from signal score**
Using policy thresholds from `/api/policies` → `allocation_mapping.view_score_thresholds`:
```
score ≥ OW_min (0.35)       → "OW"
score ≤ UW_max (-0.35)      → "UW"
-0.35 < score < 0.35        → "N"
```

**Step 3 — Determine conviction from |score|**
Using `allocation_mapping.conviction_thresholds`:
```
|score| ≥ HIGH_abs_min (0.7)     → "HIGH"
|score| ≥ MEDIUM_abs_min (0.35)  → "MEDIUM"
|score| < LOW_abs_below (0.35)   → "LOW"
```

**Step 4 — Determine change vs prior quarter**
Using `allocation_mapping.view_rank`: OW=1, N=0, UW=-1.
```
new_rank > prior_rank  → "UP"
new_rank < prior_rank  → "DOWN"
new_rank == prior_rank → "UNCHANGED"
```

**Step 5 — Rationale code**
- Use the `rationale_code` from the macro-signal entry for that opportunity_set and quarter. Do not invent or reassign.

**Step 6 — Risk overlay**
- Synthesize an overlay from the pattern of views. Common overlay choices map to:
  - `DURATION_QUALITY_TILT` / `tilt_to_duration_quality`: when OW duration, UW HY, concerns about credit/EM
  - `CREDIT_RISK_REDUCTION` / `trim_credit_beta`: when HY is UW with high conviction
  - `CURRENCY_DEFENSIVE_HEDGE` / `add_currency_hedge`: when USD signal is negative and EUR/JPY diverge
  - `NO_OVERLAY` / `hold_policy_weights`: when no strong tilt exists
- `rationale_codes` list: the rationale codes that support the overlay choice, ordered by business priority (most important first).

**Step 7 — Policy ID**
- From the portfolio's constraints or `/api/policies` top-level `policy_id`.

### D. Multi-asset committee (combines B + C, e.g. train_005)

- Run the correlation review on the requested index subset (Step B) and the allocation refresh on the requested opportunity sets (Step C) within the same answer.
- `target_sleeve_actions`: map each opportunity_set to an action (`trim`/`add`/`hold`/`hedge`/`monitor`/`rotate`) informed by both correlation signals and allocation views. For currency sleeves (e.g. USD), `hedge` is valid.
- `rebalance_trigger`: pick from the enum — `correlation_cap_breach` when a correlation threshold is crossed; otherwise match the dominant risk theme.
- `portfolio_risk_concentration_flag`: true when a high-correlation pair involving a held sleeve breaches the threshold.
- `next_step`: `approve_with_monitoring` when all checks pass but a flag is raised; `approve_rotation` when clean; `defer_pending_risk_review` when uncertain.

## Common pitfalls

1. **Using stale local dates instead of the environment as_of_date.** Always read `/api/policies` or the portfolio endpoint and use that date.
2. **Computing returns from raw levels without de-synchronizing dates.** All index level arrays share the same monthly date grid — verify that every pair uses the same set of observation dates.
3. **Sorting pair IDs incorrectly.** Always alphabetical within a pair: `["IDX_CHINA","IDX_EM"]` not `["IDX_EM","IDX_CHINA"]`.
4. **Confusing `lowest` with "lowest positive".** `lowest` means the most negative (or least positive) correlation value — the minimum, not the smallest absolute value.
5. **Mixing up prior vs current quarter in allocation views.** The `prior-views` endpoint returns rows where `quarter` = target quarter and `previous_quarter` = comparison quarter; the `view` field in each row is the **prior** view (from `previous_quarter`), not the current one.
6. **Not filtering bonds by `candidate` status.** Holdings in a portfolio may have `candidate: false` — they can be sold but should not be bought.
7. **Forgetting to join issuers for watchlist checks.** A bond's own tags may hint at watchlist risk, but the definitive source is `issuers[issuer_id].watchlist`.
8. **Duration band is inclusive.** `duration_band_years: [3.0, 5.0]` means duration must be ≥ 3.0 AND ≤ 5.0.
9. **Rounding before all calculations are complete.** Compute with full precision, round only the final output values to the template's declared precision.
10. **Using the wrong policy.** Check the portfolio's `constraints.policy_id` — it may be `POL_CREDIT_DEFAULT`, `POL_CREDIT_RISK_REDUCTION` (adds a target HY reduction), `POL_CORRELATION_DEFAULT`, `POL_MULTI_ASSET_DEFAULT`, or `POL_MULTI_ASSET_RISK`.

## Quick-reference: key thresholds

| Parameter | Value | Source |
|---|---|---|
| HY cap | 20.0% | credit policy |
| Duration band | [3.0, 5.0] years | credit policy |
| Issuer concentration limit | 12.0% | credit policy |
| Subsector min count | 2 | credit policy |
| Correlation high threshold | 0.8 | correlation policy |
| Correlation low threshold | 0.2 | correlation policy |
| OW signal threshold | ≥ 0.35 | allocation mapping |
| UW signal threshold | ≤ −0.35 | allocation mapping |
| HIGH conviction | ≥ 0.7 | allocation mapping |
| MEDIUM conviction | ≥ 0.35 | allocation mapping |

## Task-agnostic output rules

- Always match the answer template's `required` keys exactly — no extra keys, no missing keys.
- Enum fields: use only the `allowed_values` from the template.
- List fields: match the declared length and ordering.
- `task_id` field (when present): use the exact value declared in the template's `required_value`.
- Return **only** the JSON object — no markdown fences, no narrative.
