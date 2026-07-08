# Asteria Investment Office — Institutional Portfolio-Risk Solver Skill

Reusable execution knowledge for the Asteria Investment Office remote
environment. Test tasks draw from three workflows: (A) energy / fixed-income
trade strategy, (B) international correlation review, (C) cross-asset active
allocation view updates (sometimes combined in one committee JSON). Re-derive
every value from the live environment per task — do NOT memorize specific
answers.

---

## 0. Data-precedence rule (applies to every task)

The remote environment at `<remote-env-url>` is the **current book of
record**. Files in `input/payloads/` are intake context and MAY BE STALE:
they often carry an earlier snapshot date, stale holding quantities/exception
boards, or stale prior preferences. When a local payload conflicts with the
environment, **prefer the environment** unless the task prompt explicitly
instructs otherwise.

Staleness signals to ignore in favor of the environment:
- `stale_holding_snapshot`, `stale_exception_board`, `stale_local_note`,
  `candidate_shortlist_from_prior_week`, `snapshot_date` keys.
- Any payload date earlier than the environment `as_of_date` (currently
  `2026-05-29`).
- A stale note saying "USD overweight as a defensive offset" or "old worksheet
  highlighted…" — these are prior preferences, not current views; refresh from
  macro signals / index levels.

The `as_of_date` you put in every answer = the environment's `as_of_date`
(`2026-05-29`), NOT the payload's request/memo date.

---

## 1. Environment endpoints & field shapes

Base URL: `<remote-env-url>`. Call with `curl` or `python urllib`.

- `GET /api/catalog` — available portfolio ids, policy ids, index ids, issuer
  ids, bond ids, opportunity sets. Good first call to confirm IDs.
- `GET /api/policies` — all policy thresholds (see §2).
- `GET /api/portfolios` — portfolio summaries.
- `GET /api/portfolios/<id>` — `{portfolio_id, name, objective, strategy,
  base_currency, as_of_date, market_value_usd_m, constraints{policy_id,
  duration_band_years, max_hy_allocation_pct, ...}, holdings[{instrument_id,
  quantity_usd_m, asset_class, sleeve, notes}]}`. The `constraints.policy_id`
  tells you which credit policy applies (and thus the target HY reduction).
- `GET /api/instruments/bonds` — supports filters `?candidate=true`,
  `?rating_bucket=HY`. Each bond: `{instrument_id, issuer_id, issuer_name,
  candidate, energy_linked, coupon_pct, maturity, modified_duration_years,
  rating, rating_bucket (IG|HY), sector, subsector, spread_bps,
  yield_to_maturity_pct, recommended_theme_tags}`.
- `GET /api/issuers` — `{issuer_id, issuer_name, sector, subsector,
  rating_bucket, watchlist (bool), credit_outlook, research_tags}`. Key the
  watchlist check by `issuer_id`.
- `GET /api/market/energy` — oil/gas/LNG/refining/renewables signals (theme
  context for §A; not directly required for the arithmetic).
- `GET /api/indices` — index metadata.
- `GET /api/index-levels` — a **dict** mapping each `index_id` to a list of
  `{date, level}` monthly observations for ALL indices.
  `GET /api/index-levels/<id>` returns one index. No correlations are
  precomputed — compute them yourself (§5).
- `GET /api/allocation/opportunity-sets` — 25 sets, each
  `{opportunity_set, asset_class (Equities|Duration|Credit|Currency),
  sub_asset_class, display_order}`. Use this to map an opportunity-set name to
  its `asset_class`.
- `GET /api/allocation/prior-views` — list of records for **multiple quarters**;
  each `{opportunity_set, quarter, previous_quarter, view (UW|N|OW),
  conviction}`. **You must filter `quarter == target_quarter`**; the `view` on
  that record is the prior view held entering the target quarter.
- `GET /api/macro-signals` — list of `{opportunity_set, quarter, score,
  rationale_code, drivers}`. Filter `quarter == target_quarter`.

Roster of list endpoints also accept simple equality filters matching field
names, e.g. `?rating_bucket=HY`, `?candidate=true`, `?quarter=Q2_2026`.

---

## 2. Policy conventions (`GET /api/policies`)

Top-level: `policy_id: POLICY_SET_2026_05`, `as_of_date: 2026-05-29`.

- `credit_default` (policy_id `POL_CREDIT_DEFAULT`): `duration_band_years`
  `[3.0, 5.0]`, `max_hy_allocation_pct` 20.0, `issuer_concentration_limit_pct`
  12.0, `subsector_min_count_for_diversified` 2, `target_hy_reduction_pct` 0.0.
- `credit_risk_reduction` (`POL_CREDIT_RISK_REDUCTION`): same as above but
  `target_hy_reduction_pct` **4.0**. Used by risk-rebalance portfolios
  (rotation tasks). The per-portfolio `constraints` names which one applies.
- `correlation` (`POL_CORRELATION_DEFAULT`): `correlation_high_threshold` 0.8,
  `correlation_low_threshold` 0.2, `review_window_start` 2025-05-30,
  `review_window_end` 2026-04-30.
- `allocation_mapping` (`POL_ALLOCATION_MAPPING`):
  - `view_score_thresholds`: `OW_min` 0.35, `UW_max` −0.35, `neutral`
    `[−0.35, 0.35]`.
  - `conviction_thresholds`: `HIGH_abs_min` 0.7, `MEDIUM_abs_min` 0.35,
    `LOW_abs_below` 0.35.
  - `view_rank`: `{UW: −1, N: 0, OW: 1}`.
- `multi_asset` uses allocation_mapping + correlation_default + credit_default.
- `multi_asset_risk` uses credit_risk_reduction + correlation_default;
  `committee_escalation_threshold`: "two_or_more_material_exceptions".

For credit tasks, read the portfolio's `constraints` to pick
`target_hy_reduction_pct` (0 vs 4) and the duration band.

---

## 3. Precision & ordering conventions (always honor the template)

Always follow the per-field precision declared in
`input/payloads/answer_template.json`. Verified defaults:

- `trade_package`/rotation `notional_usd_m` and `quantity_usd_m`: **1 decimal**.
- `post_trade_metrics`: `total_market_value_usd_m` 2 dp;
  `hy_allocation_pct` 2 dp; `weighted_modified_duration_years` 2 dp;
  `weighted_yield_to_maturity_pct` 2 dp.
- `correlation`: **3 decimals**.
- `signal_score`: **3 decimals**.
- `hy_reduction_pct_points`: 2 dp; `post_trade_watchlist_exposure_usd_m`: 1 dp.

Ordering rules (verified):
- Energy BUY-only `trade_package`: **sort ascending by `instrument_id`**.
- Rotation `.trades`: **SELL before BUY, then `instrument_id` ascending within
  each action**.
- `index_set`, `diversification_candidates`, `pair` ids within a pair:
  **ascending alphabetical**.
- `allocation_views` / committee lists: follow the **request payload's
  focus/opportunity_sets order** (NOT alphabetical) unless the template says
  otherwise — read the template's `ordering` field.
- `rationale_codes` (overlay): **business priority order, highest first**.
- `watchlist_sell_ids`: ascending `instrument_id`.

---

## 4. Post-trade metric recipe (all credit workflows)

Given current holdings (env `quantity_usd_m`) + trades (BUY adds, SELL
subtracts), build the post-trade holdings map, then:

1. `total_market_value_usd_m` = Σ post-trade quantities (round 2 dp). For a
   funded rotation (Σ sells = Σ buys) this equals the current portfolio MV.
2. `hy_allocation_pct` = (Σ q where bond `rating_bucket`=='HY') / total × 100.
3. `weighted_modified_duration_years` = Σ(q × `modified_duration_years`) / total.
4. `weighted_yield_to_maturity_pct` = Σ(q × `yield_to_maturity_pct`) / total.
5. `hy_reduction_pct_points` = `pre_trade_hy_pct` − `post_trade_hy_pct`, where
   `pre_trade_hy_pct` = (current HY MV) / (current total MV) × 100.
6. `post_trade_watchlist_exposure_usd_m` = Σ post-trade q where the bond's
   issuer (via `issuer_id` → `/api/issuers`) has `watchlist == true`.

Get `rating_bucket`, `modified_duration_years`, `yield_to_maturity_pct` from
`/api/instruments/bonds`; get the watchlist flag from `/api/issuers` keyed by
`issuer_id`. Round each metric per §3. This recipe reproduces the env-verified
metric set exactly (market-value-weighted).

### Constraint booleans

- `hy_cap_pass`: `post_trade_hy_allocation_pct <= max_hy_allocation_pct` (20.0).
- `duration_band_pass`: `post_trade weighted_modified_duration_years` within
  `[band[0], band[1]]` inclusive (default [3.0, 5.0]).
- `target_hy_reduction_met`: `hy_reduction_pct_points >= target_hy_reduction_pct`
  (0 for `credit_default`, 4.0 for `credit_risk_reduction`).
- `watchlist_exposure_cleared`: `post_trade_watchlist_exposure_usd_m == 0`
  (and `buys_avoid_watchlist == true`).
- `selected_issuer_diversification_pass`: selected buys come from distinct
  issuers (and no issuer exceeds `issuer_concentration_limit_pct`).
- `selected_subsector_diversification_pass`: selected buys span ≥
  `subsector_min_count_for_diversified` (2) distinct subsectors.
- `watchlist_avoidance_pass`: no bought bond's issuer is on the watchlist.

---

## 5. Workflow A — Energy / fixed-income trade strategy (BUY tickets)

**Inputs**: portfolio_id, ticket count, total notional (+ split rule, e.g.
evenly), allowed actions (usually BUY), income period, preferred exposures
(e.g. "LNG exporters", "gas demand", "non-watchlist carry"), client segment,
watchlist-yield sensitivity.

**SOP**:
1. `GET /api/portfolios/<id>` → `as_of_date`, `market_value_usd_m`,
   `holdings`, `constraints` (policy_id, duration band, HY cap).
2. `GET /api/instruments/bonds?candidate=true` → candidate universe. Filter to
   `energy_linked==true` (or per preferred exposures). Build a lookup of bond
   → `{rating_bucket, modified_duration_years, yield_to_maturity_pct,
   issuer_id, subsector}`.
3. `GET /api/issuers` → mark watchlist issuers. **Exclude every candidate whose
   issuer `watchlist==true`** (watchlist_avoidance).
4. Select exactly the requested ticket count, summing to the total notional
   with the required split. Prefer bonds that:
   (a) improve carry (higher YTM) while keeping post-trade HY % ≤ cap and
       post-trade duration within the band;
   (b) diversify — ≥ 2 distinct subsectors among selected buys and distinct
       issuers;
   (c) match the desk's preferred exposures/themes / `recommended_theme_tags`.
5. Compute post-trade metrics (§4) on env holdings + selected buys.
6. Derive constraint booleans (§4).
7. `sales_positioning.target_segment` + `theme`: pick from the template's
   enums driven by desk context (e.g. `multi_asset_income` +
   `lng_export_tailwind` when LNG exporters are selected; use
   `avoid_watchlist_yield_trap` when a watchlisted high-carry bond was the
   near-miss that you correctly excluded).
8. `data_precedence = current_environment_over_stale_payload` whenever the
   payload snapshot differs from the env (the usual case). Only use
   `no_conflict_found` if values truly match.
9. Sort `trade_package` ascending by `instrument_id`; round `notional_usd_m`
   to 1 dp.

**Rotation variant (sell existing pressure, fund IG buys)**:
- SELL in full every **watchlisted** holding (clear avoidable watchlist risk).
- SELL additional **HY** holdings as needed to (i) fund the IG buys and (ii)
  meet/exceed `target_hy_reduction_pct`. Size so Σ sells ≈ Σ buys (funded
  rotation → total MV preserved). Use env quantities, NOT the
  `stale_exception_board` quantities (they differ).
- BUY only **IG, non-watchlist** candidates whose durations, blended in, keep
  portfolio duration inside the band. Avoid any desk-shortlisted candidate
  flagged for issuer-status concern.
- `watchlist_sell_ids` = watchlisted holdings sold (ascending instrument_id);
  `buys_avoid_watchlist = true`.
- `risk_note_code` enum: `watchlist_concentration` when watchlist clearing
  dominated; `hy_cap_pressure` when capping HY was the lever;
  `duration_preservation` when duration ballast drove buys; `carry_tradeoff`;
  `no_action`.

---

## 6. Workflow B — International correlation review

**Inputs**: portfolio_id, as_of, `review_window{level_start_date,
level_end_date}`, `index_universe[]`, CIO concern codes.

**SOP**:
1. `GET /api/index-levels`. For each index in `index_universe`, filter
   observations to `[level_start_date, level_end_date]` **inclusive** and sort
   ascending by date.
2. Compute monthly simple returns per index:
   `r[i] = level[i+1] / level[i] − 1`. `return_observations = #levels − 1`
   (e.g. 12 monthly levels → 11 returns).
3. For every unordered pair, compute **Pearson correlation** of the two
   return series (equal length, aligned by date). Round to **3 decimals**.
4. `extreme_pairs.highest_positive` = max-corr pair; `lowest` = min-corr pair.
   Each `pair_id` sorted **alphabetical**; `correlation` to 3 dp.
5. `index_set` = `index_universe` sorted **ascending alphabetical**.
6. `concentration`:
   - `high_threshold_breached` = any pair corr ≥ `correlation_high_threshold`
     (0.8).
   - `china_asia_dependence_flag` = true if any pair ≥ 0.8 involves a
     China/Asia-related index (`IDX_CHINA`, `IDX_AC_ASIA_PAC_EX_JP`, `IDX_EM`,
     `IDX_EM_EX_CHINA`, `IDX_INDIA`).
   - `primary_code` = `CHINA_ASIA_DEPENDENCE` if that flag is true; else
     `GLOBAL_DEVELOPED_OVERLAP` if the high cluster is only among
     developed/global indices (`IDX_WORLD`, `IDX_EAFE`, `IDX_ACWI_IMI`); else
     `NO_MATERIAL_CONCENTRATION`. The memo's concern codes
     (ASIA_BETA_OVERLAP, CHINA_DEDICATED_SLEEVE) hint toward
     `CHINA_ASIA_DEPENDENCE`.
7. `diversification_candidates`: indices with the lowest (most negative /
   lowest-abs) correlation to the concentration cluster — typically
   `IDX_EM_EX_CHINA` and `IDX_LATAM`. Sort ascending alphabetical; restrict to
   the template's `allowed_values`.
8. `sleeve_actions`: trim the concentration-driving sleeve (e.g. China →
   `trim`, `IDX_CHINA`) and add a diversifier (e.g. Latin America → `add`,
   `IDX_LATAM`). Respect the template's length/ordering and
   `target_index_id` allowed values; `action` ∈ {trim, add, hold, hedge,
   monitor, rotate}.

---

## 7. Workflow C — Cross-asset active allocation view updates

For **each requested opportunity_set** (in the request's focus order):

1. `asset_class` = `opportunity-sets[os]['asset_class']`
   (Equities / Duration / Credit / Currency). Note mappings: `U.S. Treasuries`
   → Duration; `Corporate High Yield` → Credit; `EUR`/`USD`/currency names →
   Currency.
2. `prior_view` = `prior-views` filtered to `quarter == target_quarter` AND
   `opportunity_set == os` → `view`. (**Filter by quarter — the endpoint holds
   multiple quarters; the wrong record gives the next quarter's view.**)
3. `macro` = `macro-signals` filtered to `quarter == target_quarter` AND
   `opportunity_set == os` → `score`, `rationale_code`.
4. `signal_score` = round(`score`, 3).
5. `view`: `OW` if score ≥ 0.35; `UW` if score ≤ −0.35; else `N`.
6. `change`: compare `view_rank[new]` vs `view_rank[prior_view]`:
   `UP` if new>prior, `DOWN` if <, `UNCHANGED` if ==. Rank `{UW:−1, N:0,
   OW:1}`. (A score moving 0.6→0.4 is still OW→OW = UNCHANGED.)
7. `conviction`: `HIGH` if |score| ≥ 0.7; `MEDIUM` if 0.35 ≤ |score| < 0.7;
   `LOW` if |score| < 0.35.
8. `rationale_code` = `macro['rationale_code']` (the enum from the signal
   record — GROWTH_IMPROVES, RATE_CUT_SUPPORT, CREDIT_SPREAD_RISK,
   DOLLAR_DEFENSIVE, CHINA_DEPENDENCE, LATAM_DIVERSIFIER, INDIA_OFFSET,
   DURATION_SUPPORT, HY_VALUATION_RISK, EUROPE_RECOVERY, JAPAN_POLICY_RISK,
   NEUTRAL_BALANCE).
9. Order rows per the template (usually the request payload's focus order).
10. `policy_id` (top-level, when required) = `POLICY_SET_2026_05`.
    `as_of_date` = env as_of (`2026-05-29`); `target_quarter`/`prior_quarter`
    from the request (e.g. `Q2_2026` / `Q1_2026`).

### Risk overlay (standalone allocation memo)
- `overlay_code` + `primary_action`: pick the dominant theme from the derived
  views:
  - Duration OW + HY UW → `DURATION_QUALITY_TILT` / `tilt_to_duration_quality`.
  - Credit/HY stress dominant → `CREDIT_RISK_REDUCTION` / `trim_credit_beta`.
  - Equity growth tilt → `EQUITY_BETA_EXTENSION` / `add_cyclical_equity_beta`.
  - Currency defensive → `CURRENCY_DEFENSIVE_HEDGE` / `add_currency_hedge`.
  - No strong tilt → `NO_OVERLAY` / `hold_policy_weights`.
- `rationale_codes`: the rationale codes of the most consequential views, in
  business priority order (highest priority first).

### Combined committee JSON (correlation + allocation, e.g. multi-asset sleeve)
- `correlation_summary`: 2 items — `highest_concentration` (max-corr pair) and
  `best_diversifier` (min-corr / most-negative pair). Each `pair` sorted
  alphabetical; `correlation` to 3 dp (Pearson of monthly simple returns from
  `/api/index-levels` over the window).
- `target_sleeve_actions`: per sleeve, action ∈ {trim, add, hold, hedge,
  monitor, rotate} (e.g. trim the concentration sleeve, add the diversifier,
  hedge a defensive currency).
- `allocation_views`: per opportunity_set include `prior_view`,
  `signal_score`, `view`, `change`, `conviction`, `rationale_code` (all
  derived per §7 steps 2–8). Use the prior from `/api/allocation/prior-views`
  (filtered to target quarter), **not** the `stale_local_note`.
- `rebalance_trigger` enum: `correlation_cap_breach` if any relevant pair ≥
  0.8; else `hy_cap_pressure` / `duration_drift` / `watchlist_concentration` /
  `committee_review` per the dominant risk.
- `portfolio_risk_concentration_flag` (bool): true when the correlation
  high-threshold (0.8) is breached.
- `next_step` enum: `approve_rotation` / `defer_pending_risk_review` /
  `approve_with_monitoring` (typical when concentration flagged but overlay
  addresses it) / `reject_constraint_breach`.

---

## 8. Common misjudgments & exclusion rules

1. **Stale-payload values**: don't use `stale_holding_snapshot` MV/HY%/
   quantity or `stale_exception_board` quantities — they differ from the env
   (e.g. payload 58.5 MV vs env 60.0; payload 10.0 held vs env 12.0). Always
   recompute from `/api/portfolios/<id>`.
2. **Watchlist yield trap**: before selecting any candidate, check its
   `issuer_id` in `/api/issuers` and exclude if `watchlist==true`. A high-carry
   watchlisted bond is the classic distractor.
3. **Duration-ineligible distractor**: a long-dated or HY bond whose inclusion
   would push post-trade duration outside [3.0, 5.0] or breach the HY cap.
   Always compute post-trade metrics before finalizing.
4. **Wrong prior view**: `/api/allocation/prior-views` holds multiple quarters.
   Filter `quarter == target_quarter`. Taking the first/last record without
   filtering yields the next quarter's view and corrupts `change`.
5. **Mis-deriving `change`**: it is `new view` vs `prior view` by `view_rank`,
   NOT score direction or conviction change. Equal views ⇒ UNCHANGED.
6. **Correlation on levels**: must be Pearson of monthly **simple returns**
   (`level[i+1]/level[i] − 1`), not of price levels.
7. **Window/observation count**: filter levels to `[start, end]` inclusive;
   `return_observations = #levels − 1` (12 levels → 11 returns).
8. **Trade ordering**: energy BUY-only ⇒ ascending `instrument_id`; rotation ⇒
   SELL-before-BUY then `instrument_id` ascending. Swapping these fails the
   sort check.
9. **Funded-rotation base**: Σ sells = Σ buys so total MV is preserved; compute
   HY reduction against the env pre-trade HY MV / env total MV, not the stale
   board.
10. **Stale desk preference override**: ignore old "USD overweight as defensive
    offset" notes when refreshing — re-derive `view`/`change` from current
    `macro-signals` + April index levels.
11. **Missing `data_precedence`**: when a payload snapshot conflicts with env,
    set `current_environment_over_stale_payload`. It is almost always set (the
    payloads are deliberately stale).
12. **Ignoring the answer template's exact field set / enums**: re-read
    `answer_template.json` each task — required keys, allowed enum values,
    ordering instructions, and precision per field vary slightly across tasks.
    Return only the JSON object, no narrative.

---

## 9. End-to-end checklist (every task)

1. Read `prompt.txt` + every `input/payloads/*.json` (request + answer
   template). Identify the workflow(s) and the required top-level keys.
2. Confirm IDs via `/api/catalog` if unsure; then pull the per-task endpoints.
3. Use env `as_of_date` as the answer's `as_of_date`.
4. Compute from the environment (holdings/bonds/issuers/index-levels/prior-
   views/macro-signals/policies) — never trust stale payload snapshots.
5. Round per the template; sort per the template; use only allowed enum values.
6. Verify pass/fail booleans against §4 thresholds.
7. Return **only** the JSON object.
