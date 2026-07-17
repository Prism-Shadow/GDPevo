---
name: asteria-investment-office-json
description: >-
  Produce the Asteria Investment Office portfolio JSON deliverables (energy-credit
  trade packages, international equity correlation reviews, active allocation refreshes,
  fixed-income risk rebalances, and multi-asset committee decisions). Treat the shared
  Asteria HTTP environment as the authoritative book of record over any local payload,
  apply the documented policy thresholds, and emit answers that exactly match each
  task's answer_template (field names, enum value sets, rounding, id ordering).
  Use this whenever a prompt references Asteria portfolios (PF-*), bonds (BND_*),
  issuers (ISS_*), indices (IDX_*), opportunity sets, macro signals, or allocation policy.
---

# Asteria Investment Office — Portfolio JSON Deliverables

You build compact JSON decision files for the Asteria Investment Office. Five archetypes
share one environment and one policy set. This skill gives the exact endpoints,
computation recipes, schema conventions, and policy rules that produce correct output.

## 0. Universal SOPs (apply to every task)

1. **Environment is the book of record.** Pull every current fact (holdings, market
   values, ratings, watchlist flags, index levels, prior views, macro scores, policy
   thresholds) from the HTTP API. Local payloads (`desk_request`, `review_request`,
   `risk_meeting_memo`, `committee_request`, stale snapshots, "prior-week shortlists",
   "exception boards") are **intake context only and frequently stale**. When they
   disagree with the environment, the environment wins. If the schema has a
   `data_precedence` field, set it to `current_environment_over_stale_payload` whenever
   the local payload's marks/preferences differ from current records (they usually do).
2. **as_of_date** = the environment's current `as_of_date` (read it from the policies or
   portfolio response; do not copy the local memo date). All four portfolios and the
   policy set share one as-of date.
3. **Read the answer_template literally.** Emit exactly the required keys, in the required
   order where ordering is specified, using only enum values from `allowed_values`, and
   round every numeric to its declared precision. Do not add commentary keys.
4. **Booleans are computed, not assumed.** Every `*_pass` / `*_flag` boolean must reflect
   the real post-trade/post-review computation, even if you also report the metric.
5. **Rounding:** round only at the end, to the declared decimals. Percentages are in
   percent units (e.g. 14.10, not 0.141). Notionals/quantities in USD millions.
6. **id ordering:** wherever ids appear in a list or a pair, sort ascending alphabetically
   unless the template names a different order (e.g. "follow request payload order",
   "SELL before BUY", or a fixed item_order list).
7. Use `python` (Anaconda) for math; `curl` for HTTP. Save fetched JSON only inside your
   own working directory.

### Endpoints
```
GET /api/catalog                         ids available
GET /api/policies                        all thresholds (see §6)
GET /api/portfolios/<id>                 objective, constraints, holdings, market_value, as_of_date
GET /api/instruments/bonds               bond master: rating_bucket, modified_duration_years,
                                         yield_to_maturity_pct, spread_bps, energy_linked,
                                         candidate, subsector, issuer_id
GET /api/issuers                         sector/subsector/rating_bucket/watchlist/outlook
GET /api/market/energy                   commodity signal scores + pitch themes
GET /api/indices                         index metadata
GET /api/index-levels  (or /<id>)        monthly index levels
GET /api/allocation/opportunity-sets     asset_class taxonomy per opportunity_set
GET /api/allocation/prior-views          standing views by (opportunity_set, quarter)
GET /api/macro-signals                   per (opportunity_set, quarter): score, rationale_code, drivers
```

## 1. Pearson correlation recipe (used by archetypes b and e)

The single most reused, fully deterministic computation. Get it byte-exact:

1. Window = the policy / request `review_window` (e.g. `level_start_date` ..
   `level_end_date`). The default correlation window is on `/api/policies` under
   `correlation` (`review_window_start`, `review_window_end`). A "12-month monthly-level
   window" = 12 monthly levels.
2. For each index, take its monthly levels **inside the window inclusive**, sorted by
   date. **N levels → N-1 returns.** Report `return_observations` = N-1 (12 levels → 11).
3. **Monthly simple returns:** `r[i] = level[i]/level[i-1] - 1`. (Not log returns.)
4. **Pearson** correlation of the two return series; **round to 3 decimals**.
5. Pair id = the two index ids sorted **alphabetically**.
6. Highest-correlation pair = max over all unordered pairs; lowest = min (can be negative).
7. Concentration / "highest_concentration" pair = the max-positive pair; "best diversifier"
   / "lowest" pair = the min (most negative) pair.

```python
def returns(levels, start, end):
    rows = sorted((d for d in levels if start <= d["date"] <= end), key=lambda x: x["date"])
    lv = [d["level"] for d in rows]
    return [lv[i]/lv[i-1]-1 for i in range(1, len(lv))]

def pearson(x, y):
    n=len(x); mx=sum(x)/n; my=sum(y)/n
    cov=sum((a-mx)*(b-my) for a,b in zip(x,y))
    sx=sum((a-mx)**2 for a in x)**0.5; sy=sum((b-my)**2 for b in y)**0.5
    return cov/(sx*sy)
```

## 2. Allocation-view mapping recipe (archetypes c and e)

Fully deterministic from `POL_ALLOCATION_MAPPING` (under `/api/policies` →
`allocation_mapping`). For each opportunity_set, for the **target quarter**:

- `signal_score` = the macro-signals `score` for that (opportunity_set, target_quarter).
  Round to 3 decimals where the schema asks for `signal_score`.
- `view`: `OW` if score ≥ `OW_min` (0.35); `UW` if score ≤ `UW_max` (-0.35); else `N`.
  (neutral band is the open-ish interval (-0.35, 0.35).)
- `conviction`: `HIGH` if |score| ≥ 0.7; `MEDIUM` if |score| ≥ 0.35; else `LOW`.
- `change`: compare the new `view` rank (UW=-1, N=0, OW=1) to the **prior view**. The prior
  view is the `/api/allocation/prior-views` row whose `quarter` == target_quarter and
  `previous_quarter` == prior_quarter (i.e. the standing view going into this refresh).
  rank diff > 0 → `UP`; < 0 → `DOWN`; 0 → `UNCHANGED`.
- `rationale_code`: copy directly from the macro-signal row's `rationale_code` for that
  (opportunity_set, target_quarter). Do not re-derive it.
- `asset_class`: from `/api/allocation/opportunity-sets`
  (Equities / Duration / Credit / Currency).
- **Row order:** follow the request payload's `focus_opportunity_sets` /
  `opportunity_sets` order, NOT alphabetical.

Worked enum example (target Q2_2026, do recompute live): a strongly positive domestic-growth
score → OW / HIGH / INDIA_OFFSET; a mildly negative dollar score (~-0.22) → N (it is inside
the neutral band) / LOW / NEUTRAL_BALANCE with `change=DOWN` if the prior view was OW. Always
honor the neutral band: a score between -0.35 and 0.35 is `N` even if it is clearly signed.

### Portfolio risk overlay (archetype c)
For a balanced multi-asset model, read the duration and credit signals: a positive
duration/Treasury signal plus a negative high-yield signal → `overlay_code`
`DURATION_QUALITY_TILT` with `primary_action` `tilt_to_duration_quality`. If credit
de-risking dominates instead, use `CREDIT_RISK_REDUCTION` / `trim_credit_beta`. Populate
`rationale_codes` from the most material drivers ordered by |score| descending (highest
priority first), e.g. duration support before HY valuation risk before regional themes.

## 3. Archetype (a) — Energy-credit trade package

Goal: a small BUY package (e.g. 2 tickets, even split of a fixed total notional) that
improves carry and stays inside credit constraints, suitable for an income pitch.

- **Eligible universe:** bond is `candidate == true` **AND** `energy_linked == true`
  **AND** its issuer's `watchlist == false`. (Watchlist/refining names are the "yield
  trap" to avoid; never buy them even though they have the fattest coupons.)
- Each ticket notional = total / ticket_count (even split). Sort `trade_package` ascending
  by `instrument_id`.
- **post_trade_metrics** on the post-trade book (current holdings + new buys; new MV =
  current MV + total bought):
  - `total_market_value_usd_m` (2dp).
  - `hy_allocation_pct` = HY market value / total MV × 100 (2dp). HY = `rating_bucket=="HY"`.
  - `weighted_modified_duration_years` = Σ(qty × modified_duration)/MV (2dp).
  - `weighted_yield_to_maturity_pct` = Σ(qty × ytm)/MV (2dp).
- **constraint_checks** (booleans):
  - `hy_cap_pass`: post-trade hy_allocation_pct ≤ `max_hy_allocation_pct` (20.0).
  - `duration_band_pass`: post-trade WMD within `duration_band_years` [3.0, 5.0] inclusive.
  - `selected_issuer_diversification_pass`: the selected buys are different issuers.
  - `selected_subsector_diversification_pass`: the selected buys span ≥ 2 distinct
    subsectors (so two same-subsector LNG names fail this — pair one LNG name with a
    different subsector).
  - `watchlist_avoidance_pass`: no selected bond's issuer is on the watchlist (true if you
    obeyed the eligibility filter).
- **sales_positioning:** pick `target_segment` and `theme` from the enum to match the
  dominant energy signal and the client context. A multi-asset income client + a dominant
  positive LNG export signal → `target_segment` `multi_asset_income`, `theme`
  `lng_export_tailwind`. If refining/oversupply dominates, use the matching caution theme;
  if the package's whole point is dodging watchlist names, `avoid_watchlist_yield_trap`.
- **data_precedence:** `current_environment_over_stale_payload` (the desk worksheet marks
  are stale vs the portfolio service).
- Selection principle: maximize carry **subject to** all constraints, but keep the package
  defensible for an income pitch — favor the desk's stated preferred exposures (e.g. LNG /
  gas demand) and do not stack the absolute-highest-yield long-dated HY names if a cleaner,
  thematically-aligned package also clears the constraints.

## 4. Archetype (b) — International equity correlation review

- `index_set`: the request's index universe, sorted ascending alphabetically.
- `review_window`: echo `level_start_date` / `level_end_date`; `return_observations` =
  (levels in window) - 1.
- `extreme_pairs.highest_positive` = max-correlation pair; `extreme_pairs.lowest` =
  min-correlation pair (correlation 3dp, pair_id alphabetical).
- `concentration`:
  - `china_asia_dependence_flag`: true if the China / Asia-Pacific complex is highly
    correlated with the broad sleeve (multiple China/Asia pairs ≥ `correlation_high_threshold`).
  - `primary_code`: `CHINA_ASIA_DEPENDENCE` when China/Asia drives the concentration;
    `GLOBAL_DEVELOPED_OVERLAP` if developed-market overlap dominates; else
    `NO_MATERIAL_CONCENTRATION`.
  - `high_threshold_breached`: true if any pair correlation ≥ `correlation_high_threshold`
    (0.8). The top global/EM pair (~0.97) breaches it.
- `diversification_candidates` (from the allowed set, alphabetical): the indices that are
  **genuinely low-correlated to the concentrated bloc**, i.e. correlation to China/Asia/EM
  **below `correlation_low_threshold` (0.2)**. A negatively-correlated regional sleeve
  (e.g. Latin America) qualifies decisively; sleeves still ≥ 0.8 correlated to the bloc do
  not. Apply the threshold rule rather than guessing the whole allowed set.
- `sleeve_actions` (length 2, ascending by sleeve; `sleeve` = the portfolio holding's
  sleeve name string): **trim the concentrated sleeve** (action `trim`, `target_index_id`
  = that bloc's index, e.g. IDX_CHINA) and **add the low-correlation diversifier** (action
  `add`, `target_index_id` = the diversifier index, e.g. IDX_LATAM). Do NOT "rotate" the
  concentrated sleeve into another still-correlated bloc — a plain trim + add scores higher
  than a rotate.

## 5. Archetype (d) — Fixed-income risk rebalance

Goal: reduce HY and remove avoidable watchlist risk while keeping duration in the CIO band
and preserving carry. Governing policy is `POL_CREDIT_RISK_REDUCTION`
(`target_hy_reduction_pct` 4.0, `max_hy_allocation_pct` 20.0, `duration_band_years`
[3.0, 5.0]).

- The rebalance is **market-value-neutral**: SELL proceeds fund the BUYs, total MV
  unchanged.
- **Mandatory sell:** the held HY bond whose issuer is on the watchlist. Put it in
  `watchlist_handling.watchlist_sell_ids` (ascending) and set `buys_avoid_watchlist=true`.
- **Be targeted, not maximal.** Do NOT dump every HY position to 0% — over-reducing HY is
  penalized because it destroys carry. Sell the watchlist name plus only the additional HY
  needed to bring `hy_allocation_pct` under the cap (20%) while meeting the ≥4.0pp reduction
  target; preserve the highest-carry HY names where possible.
- **Buys:** investment-grade, non-watchlist `candidate==true` bonds (e.g. data-center,
  materials, LNG IG names). Size them MV-neutral so post-trade duration stays inside
  [3.0, 5.0] and near the prior duration. Never buy a watchlist candidate even if it has
  the highest carry.
- `rotation.trades` ordering: **SELL before BUY, then instrument_id ascending within each
  action.** `quantity_usd_m` to 1dp.
- `risk_metrics`: `post_trade_hy_allocation_pct` (2dp), `post_trade_duration_years` (2dp),
  `hy_reduction_pct_points` = current HY% − post HY% (2dp),
  `post_trade_watchlist_exposure_usd_m` (1dp, → 0 once the watchlist name is sold).
- `exception_flags`: `hy_cap_pass` (post HY% ≤ 20), `duration_band_pass` (in band),
  `target_hy_reduction_met` (reduction ≥ 4.0pp), `watchlist_exposure_cleared`
  (post watchlist exposure == 0).
- `risk_note_code`: when the headline action is removing watchlist names, use
  `watchlist_concentration` (this is the right note even though the HY cap was also
  breached — the watchlist clean-up is the story). Use `hy_cap_pressure` only when the cap
  is the sole driver and no watchlist name is involved.

## 6. Archetype (e) — Multi-asset committee decision

Combines §1 (correlation) and §2 (allocation views) into one committee file.

- `correlation_summary` (length 2, fixed item_order `[highest_concentration,
  best_diversifier]`): over the committee's small index set, on the current 12-month
  monthly-level window. `highest_concentration` = the max-correlation pair;
  `best_diversifier` = the min (most negative) pair. Each item: `pair_role`, `pair`
  (alphabetical), `correlation` (3dp).
- `allocation_views` (item_order from the request, e.g. EM, India, LATAM, USD): full §2
  recipe — `prior_view`, `signal_score` (3dp), `view`, `change`, `conviction`,
  `rationale_code`. USD/currency sets follow the same thresholds (a mildly negative USD
  score lands in the neutral band → `N`, typically `DOWN` from a prior OW, `LOW`).
- `target_sleeve_actions` (same item_order): map view → action — `UW`→`trim`, `OW`→`add`
  (or `hold` if the OW is unchanged), `N`→`hold`/`monitor`; a currency that has lost its
  defensive overweight → `hedge`/`monitor`. (Action wording is the most lenient field;
  keep it consistent with the view direction.)
- `portfolio_risk_concentration_flag`: true if any committee-set pair correlation breaches
  `correlation_high_threshold` (0.8).
- `rebalance_trigger`: when a correlation pair breaches the high threshold, the natural
  trigger is `correlation_cap_breach`; otherwise `committee_review`.
- `next_step`: gate on the multi-asset-risk escalation rule
  (`committee_escalation_threshold` = "two_or_more_material_exceptions"). With a single
  material exception (e.g. one correlation breach), `approve_with_monitoring`; with two or
  more material exceptions, escalate (`defer_pending_risk_review`); use `reject_constraint_breach`
  only for an outright hard-constraint violation and `approve_rotation` when nothing is flagged.

## 7. Policy constants (verify live each run — values seen in the policy set)

- Credit (`credit_default` / `credit_risk_reduction`): `max_hy_allocation_pct` 20.0;
  `duration_band_years` [3.0, 5.0]; `issuer_concentration_limit_pct` 12.0;
  `subsector_min_count_for_diversified` 2; `target_hy_reduction_pct` 0.0 (default) / 4.0
  (risk-reduction).
- Correlation (`correlation`): `correlation_high_threshold` 0.8; `correlation_low_threshold`
  0.2; default window 2025-05-30 .. 2026-04-30.
- Allocation mapping (`allocation_mapping`): view thresholds OW_min 0.35 / UW_max -0.35;
  conviction HIGH ≥ 0.7, MEDIUM ≥ 0.35, else LOW; view_rank UW -1 / N 0 / OW 1.
- Multi-asset risk: escalate at two_or_more_material_exceptions.

Always re-read `/api/policies` rather than hard-coding; thresholds are authoritative there.

## 8. Pre-submit checklist

- [ ] Every value pulled from the environment, not the stale local payload.
- [ ] as_of_date = environment current date.
- [ ] All enums are from the template's `allowed_values`; no invented strings.
- [ ] Numerics rounded to declared precision; percents in percent units.
- [ ] Lists/pairs ordered exactly as specified (alphabetical id, request order, or
      SELL-before-BUY).
- [ ] Correlations: monthly **simple** returns, N-1 observations, 3dp, alphabetical pairs.
- [ ] Views: neutral band respected; change measured vs the standing prior view;
      rationale_code copied from the macro row.
- [ ] Constraint/exception booleans recomputed from the post-trade book.
- [ ] Watchlist names excluded from buys; required watchlist names sold; rebalance MV-neutral
      and not over-reduced.
- [ ] data_precedence set to current_environment_over_stale_payload when payload conflicts.
- [ ] Output is a single JSON object with exactly the required keys, no extra commentary.
