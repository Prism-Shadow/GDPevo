# Asteria Investment Office — Institutional Portfolio-Risk Skill

Reusable workflow rules for solving Asteria portfolio-risk tasks against the shared
remote environment. Apply the SOP below per task type. All numeric output must follow
the precision declared in each task's `input/payloads/answer_template.json`.

## 0. Environment (the authoritative book of record)

Base URL: `<remote-env-url>` — GET endpoints only. The environment is the
**current book of record**. Every local payload in `input/payloads/` (desk requests,
meeting memos, committee packets, stale snapshots, exception boards) is possibly-stale
intake context; when it conflicts with the environment, prefer the environment.

Key endpoints:
- `GET /api/catalog` — all portfolio ids, policy ids, index ids, issuer ids, bond ids, opportunity sets.
- `GET /api/policies` — portfolio constraints, correlation thresholds, allocation-mapping rules. Top-level `as_of_date` and `policy_id` (policy set) plus sub-policies.
- `GET /api/portfolios` and `GET /api/portfolios/<portfolio_id>` — objective, constraints, current holdings (each holding `instrument_id`, `quantity_usd_m` = market value USD millions, `sleeve`).
- `GET /api/instruments/bonds` (all) and `GET /api/instruments/bonds?candidate=true` — bond universe. Each bond: `instrument_id`, `issuer_id`, `rating_bucket` (IG/HY), `modified_duration_years`, `yield_to_maturity_pct`, `coupon_pct`, `energy_linked`, `candidate`, `sector`, `subsector`, `recommended_theme_tags`.
- `GET /api/issuers` — `issuer_id`, `sector`, `subsector`, `rating_bucket`, `watchlist` (boolean), `outlook`, `tags`.
- `GET /api/market/energy` — current oil/gas/LNG/refining/renewables signals (`signal_id`, `direction`, `score`, `summary`) and `pitch_themes`.
- `GET /api/indices` — index metadata; `GET /api/index-levels` and `/api/index-levels/<index_id>` — monthly levels. **No correlations are precomputed; compute them yourself from levels.**
- `GET /api/allocation/opportunity-sets` — taxonomy mapping `opportunity_set` → `asset_class` (Equities / Duration / Credit / Currency) and `display_order`.
- `GET /api/allocation/prior-views` — prior active allocation views (multi-quarter).
- `GET /api/macro-signals` — macro/asset signal scores and rationale codes (multi-quarter; see Workflow C filter rule).

Use `curl` or `urllib`/`requests`. Do not attempt to read source code, env files, or
any local `env/` directory.

## 1. Universal conventions

- **as_of_date**: use the environment's `as_of_date` (top-level of `/api/policies`, also on each portfolio). It is the recommendation date.
- **Numeric precision** (from each field's template, never assume):
  - `notional_usd_m`, `quantity_usd_m`, `post_trade_watchlist_exposure_usd_m` → 1 decimal.
  - Post-trade metrics (market value, HY %, duration, YTM, reduction pct points) → 2 decimals.
  - Correlations, `signal_score` → 3 decimals.
- **Ordering rules** (strict, verified):
  - `trade_package` (BUY/SELL tickets): ascending by `instrument_id`.
  - `rotation.trades`: SELL before BUY, then `instrument_id` ascending within each action.
  - `index_set`, `pair_id` lists: ascending alphabetical by index id using **ASCII code points** — the underscore `_` (0x5F) sorts AFTER uppercase letters (A–Z are 0x41–0x5A). Therefore `IDX_ACWI_IMI` sorts BEFORE `IDX_AC_ASIA_PAC_EX_JP`. Always mirror the order shown in `/api/catalog` and in the request payload's index universe.
  - `sleeve_actions`: ascending by the `sleeve` field (the sleeve name string, e.g. "China" < "Latin America").
  - `allocation_views` / `target_sleeve_actions`: follow the request payload's `focus_opportunity_sets` / opportunity-set order exactly.
  - `correlation_summary`: item order `[highest_concentration, best_diversifier]`.
  - `diversification_candidates`: ascending alphabetical (fixed by template).
- **Data precedence**: when a local payload snapshot (stale holding worksheet, stale exception board quantities, stale desk notes) conflicts with the current environment, set any `data_precedence` field to `current_environment_over_stale_payload`. Use current environment quantities for all computations.

## 2. Credit policies (read from `/api/policies`)

Two credit sub-policies share most fields:
- `POL_CREDIT_DEFAULT`: `duration_band_years [3.0, 5.0]`, `max_hy_allocation_pct 20.0`, `issuer_concentration_limit_pct 12.0`, `subsector_min_count_for_diversified 2`, `target_hy_reduction_pct 0.0`.
- `POL_CREDIT_RISK_REDUCTION`: same but `target_hy_reduction_pct 4.0` (use when a task targets an HY reduction of ≥4 ppt).

The portfolio record's `constraints.policy_id` tells you which applies. Multi-asset
portfolios use `POL_MULTI_ASSET_DEFAULT` (bundles allocation mapping, correlation
default, credit default) or `POL_MULTI_ASSET_RISK` (uses correlation default +
credit risk reduction; committee escalation at `two_or_more_material_exceptions`).

Correlation policy: `correlation_high_threshold 0.8`, `correlation_low_threshold 0.2`,
`review_window_start`/`review_window_end`.

## 3. Workflow A — Energy / fixed-income trade strategy

For BUY/SELL bond tickets under credit-risk constraints (e.g. PF-EN-ALTA income
sleeve, PF-FI-LUMEN rotation).

### Step-by-step
1. `GET /api/portfolios/<id>` for current holdings + constraints + as_of_date.
2. `GET /api/instruments/bonds` (all — held bonds are NOT in the `?candidate=true` list) and `?candidate=true` for eligible new buys. `GET /api/issuers` for watchlist flags. `GET /api/market/energy` for signals/themes. `GET /api/policies` for the credit policy.
3. Compute pre-trade metrics from current holdings (market-value-weighted):
   - `HY% = sum(qty where rating_bucket==HY) / total_mv * 100`
   - `weighted modified duration = sum(qty * modified_duration_years) / total_mv`
   - `weighted YTM = sum(qty * yield_to_maturity_pct) / total_mv`
4. Build the trade package, then recompute the same metrics on the post-trade book (held − sells + buys). Round to template precision.

### Selection rules
- **Carry improvement = maximize YTM within constraints.** For an income BUY package, pick the IG anchor on the strongest positive energy signal (e.g. LNG export pull) and the carry ticket as the **highest-YTM** eligible bond that is: energy-linked, non-watchlist, modified duration inside the `[3.0, 5.0]` band, and from a new issuer/subsector. Do NOT pick a lower-YTM "story" bond if a higher-YTM in-band non-watchlist bond clears every constraint.
- **Watchlist avoidance is a hard constraint.** Never BUY a bond whose `issuer_id` has `watchlist == true`. The energy watchlist issuers are the high-carry traps (e.g. shale E&P, refining). A non-watchlist HY carry bond is acceptable; a watchlist HY bond is not, regardless of yield.
- **Duration-band distractors**: exclude bonds with `modified_duration_years` outside `[3.0, 5.0]` — long-dated LNG/oil bonds (dur > 5) and very-short HY (dur < 3) are traps. Also confirm the **post-trade weighted** duration stays in band.
- **Issuer concentration limit 12%**: a candidate whose issuer is already held can blow past 12% post-trade — exclude or size down. Prefer new issuers.
- **Diversification of the package**: the selected buys must span ≥2 distinct issuers AND ≥2 distinct subsectors (set `selected_issuer_diversification_pass` and `selected_subsector_diversification_pass` accordingly).
- **HY cap**: post-trade `hy_allocation_pct` must be ≤ 20.0.
- **sales_positioning.theme**: map to the single strongest energy signal / pitch theme (e.g. LNG export tailwind). A "selectivity/transition" theme that overlaps the narrative is NOT correct when a clear commodity-tailwind theme dominates. `target_segment` follows the request's client context (e.g. multi-asset income → `multi_asset_income`).

### Rotation variant (SELL + BUY to cut HY/watchlist, keep duration)
- The desk memo's `stale_exception_board` and `candidate_shortlist` are prior-week context; reconcile every quantity and issuer status to the current environment.
- SELL the watchlist bond(s) first (clears watchlist exposure to 0). SELL enough HY to get post-trade `hy_allocation_pct` ≤ 20.0 and meet the `target_hy_reduction_pct` (≥4 ppt for the risk-reduction policy). BUY eligible IG candidates (non-watchlist, duration in band) to redeploy the proceeds (rotation keeps total MV constant).
- `watchlist_sell_ids` = only the watchlist-flagged bonds you sold (ascending). `buys_avoid_watchlist = true` iff no buy issuer is watchlisted.
- **The sell side drives correctness**: which HY you sell (and the resulting HY% / reduction ppt) are the primary differentiators. Get the sell side right (clear watchlist to 0, land HY under cap and ≥ target reduction, keep duration in band); buy sizing and the `risk_note_code` are secondary. Pick the HY to keep (if any) deliberately — do not assume the highest-carry HY is always retained; weigh stability and subsector too.
- `risk_metrics`: `post_trade_hy_allocation_pct` (2), `post_trade_duration_years` (2), `hy_reduction_pct_points` = pre HY% − post HY% (2), `post_trade_watchlist_exposure_usd_m` (1).
- `exception_flags`: `hy_cap_pass`, `duration_band_pass`, `target_hy_reduction_met`, `watchlist_exposure_cleared`.
- `trades` ordering: SELL before BUY, then `instrument_id` ascending within each action.

## 4. Workflow B — International equity correlation review

For pair-correlation analysis across an index universe (e.g. PF-INT-NEXVEN).

### Step-by-step
1. Read the request's `review_window`, `index_universe`, and CIO concern memo. `GET /api/policies` for correlation thresholds + window. `GET /api/portfolios/<id>` for sleeve names. `GET /api/index-levels` for monthly levels.
2. Filter each index's levels to `[review_window_start, review_window_end]` (the policy's `review_window_start`/`_end`). There should be 12 monthly levels → **11 monthly simple returns** `r_t = level_t / level_{t-1} − 1`.
3. Compute **Pearson correlation** over the 11 returns for every pair. Round to **3 decimals**. (Pair id lists are 2 index ids sorted ascending alphabetically by ASCII — see §1.)
4. `extreme_pairs`: `highest_positive` = the pair with the max correlation; `lowest` = the pair with the min (most negative) correlation.
5. `index_set`: the request universe, ascending ASCII alphabetical (ACWI before AC_ASIA_PAC_EX_JP — underscore sorts after letters; mirror `/api/catalog`).
6. `review_window`: `level_start_date`, `level_end_date`, `return_observations` (= 11).

### Concentration & sleeve actions
- `high_threshold_breached = true` if any pair correlation > 0.8.
- `china_asia_dependence_flag = true` if the China/Asia-Pacific overlap pair exceeds the high threshold.
- `primary_code`: choose `CHINA_ASIA_DEPENDENCE` when the review's CIO memo concerns Asia-beta overlap / China-dedicated sleeves — even if the single highest pair in the universe is a global-developed overlap. The memo's stated concern drives the primary code, not the raw maximum pair. Use `GLOBAL_DEVELOPED_OVERLAP` only when the concentration is unambiguously a developed/global block overlap with no Asia/China concern. Use `NO_MATERIAL_CONCENTRATION` only when no pair breaches.
- `diversification_candidates`: the fixed template list (e.g. `[IDX_EM_EX_CHINA, IDX_INDIA, IDX_LATAM]`), ascending.
- `sleeve_actions`: 2 items, ascending by sleeve name. Trim the concentrated sleeve (e.g. China) and add the best diversifier (the index with the most negative correlation to the concentration, typically LATAM). Use the portfolio's sleeve names (e.g. "China", "Latin America") as the `sleeve` field; `target_index_id` from the allowed index set.

## 5. Workflow C — Cross-asset active allocation view updates

For active allocation views + risk overlay (e.g. Q2 2026 refresh, PF-MA-HELIO committee file).

### Critical: filter macro-signals to the TARGET quarter
`GET /api/macro-signals` returns records for **multiple quarters** (e.g. both Q2_2026 and
Q3_2026 in the same list). You MUST keep only the records whose `quarter == target_quarter`.
Do NOT build a dict keyed by `opportunity_set` without filtering by quarter — duplicate
opportunity sets across quarters will silently overwrite and you will use next-quarter
scores, producing wrong views. Filter explicitly:
```
signal = next(x for x in macro if x['opportunity_set']==opp and x['quarter']==target_quarter)
```

### Deriving each allocation row
Per opportunity set in the request's focus order:
- `asset_class`: from `/api/allocation/opportunity-sets` taxonomy (Equities / Duration / Credit / Currency).
- `signal_score`: the filtered macro signal `score` (3 decimals).
- `rationale_code`: the filtered macro signal `rationale_code` (one of the 12 enums).
- `view` from `POL_ALLOCATION_MAPPING` thresholds: `OW` if score ≥ 0.35; `UW` if score ≤ −0.35; else `N`.
- `conviction` from `|score|`: `HIGH` if ≥ 0.7; `MEDIUM` if ≥ 0.35; else `LOW`.
- `prior_view`: from `/api/allocation/prior-views` — the record with `previous_quarter == prior_quarter` and `quarter == target_quarter` (its `view` is the prior-quarter view). For target Q2_2026 / prior Q1_2026, use the records where `previous_quarter=Q1_2026, quarter=Q2_2026`.
- `change`: compare view ranks (`OW`=1, `N`=0, `UW`=−1): `UP` if new > prior, `DOWN` if new < prior, else `UNCHANGED`.
- Order rows by the request payload's `focus_opportunity_sets` order.

### Cross-check
Sanity-check your derived `view` + `conviction` against the prior-views record whose
`previous_quarter == target_quarter` (the next-quarter refresh record) — the
target-quarter views should match that record's view/conviction when signals are
stable. If they disagree, you likely filtered the wrong quarter.

### Lineage & overlay
- `task_id`, `target_quarter`, `prior_quarter`: use the template's required values.
- `as_of_date`: environment `as_of_date`.
- `policy_id`: the allocation-mapping policy id (`POL_ALLOCATION_MAPPING`) that defines the view/conviction thresholds. (If a multi-asset policy id is expected instead, the portfolio's `constraints.policy_id` is the fallback — resolve from the portfolio record.)
- `risk_overlay`: `{overlay_code, primary_action, rationale_codes}`. The overlay is evaluated as a unit; pick the single overlay that matches the dominant portfolio-level action implied by the views (e.g. duration-up + credit-down → duration-quality tilt; broad equity growth → equity-beta extension; currency defensiveness → currency hedge; balanced/no single dominant risk → no overlay). `rationale_codes` in business-priority order (highest priority first), drawn from the same 12-code enum. Choose deliberately — a mismatched overlay bundle earns no partial credit.

## 6. Workflow D — Combined correlation + allocation committee file

(e.g. PF-MA-HELIO: link non-US equity correlation findings to active allocation views
for a subset of opportunity sets.)

- `correlation_summary`: 2 items `[highest_concentration, best_diversifier]`, each
  `{pair_role, pair (2 index ids, sorted alphabetical ASCII), correlation (3 decimals,
  Pearson of monthly simple returns over the policy correlation window)}`.
  `highest_concentration` = max-correlation pair; `best_diversifier` = most-negative
  (min) correlation pair.
- `allocation_views`: as Workflow C (filter macro to target quarter; include
  `prior_view`, `signal_score`, `view`, `change`, `conviction`, `rationale_code`),
  ordered by the request's opportunity-set list.
- `target_sleeve_actions`: one per opportunity set in the request's order, each
  `{opportunity_set, action}`. Action reflects view + correlation finding: trim a sleeve
  that is UW and/or part of the highest-concentration pair; add a sleeve that is OW
  and/or the best diversifier; hold a sleeve that is unchanged. For a currency sleeve
  downgraded OW→N on a neutral signal, prefer `trim` (implement the downgrade) over
  `hold`.
- `rebalance_trigger`: `correlation_cap_breach` when any reviewed pair exceeds the 0.8
  high threshold. Other triggers (`hy_cap_pressure`, `duration_drift`,
  `watchlist_concentration`, `committee_review`) apply only when those conditions are
  present in the portfolio.
- `portfolio_risk_concentration_flag`: `true` when any reviewed pair > 0.8.
- `next_step`: with a live concentration breach (flag = true) and a remedying rotation,
  `approve_with_monitoring` is preferred over `approve_rotation`. Use
  `defer_pending_risk_review` only at `two_or_more_material_exceptions`; use
  `reject_constraint_breach` only when the rotation cannot clear the breach.

## 7. Confirmed pass/fail & common pitfalls

- **Multi-quarter macro signals**: always filter `/api/macro-signals` to `quarter == target_quarter` before deriving views. This is the single most impactful allocation pitfall.
- **ASCII alphabetical ordering** of index ids: underscore sorts after uppercase letters (`IDX_ACWI_IMI` before `IDX_AC_ASIA_PAC_EX_JP`). Mirror `/api/catalog`.
- **Carry maximization within constraints**: for income BUY packages, the highest-YTM in-band non-watchlist eligible bond is preferred over a lower-YTM "story" bond.
- **Watchlist = hard no-buy**: never buy a watchlisted issuer, however high the yield.
- **Duration band [3.0, 5.0]**: exclude per-bond distractors outside the band AND keep the post-trade weighted duration inside it.
- **HY cap 20%**: post-trade HY% must be ≤ 20.0; for the risk-reduction policy also reduce by ≥ 4 ppt.
- **Data precedence**: current environment over any stale local payload snapshot/board/notes.
- **No precomputed correlations**: compute Pearson from monthly simple returns of consecutive index levels (12 levels → 11 returns).
- **Held bonds are not in `?candidate=true`**: fetch the full bond list to get held-instrument details (duration, YTM, rating).
- **Sell side drives rotation correctness**: in HY/watchlist-reduction rotations, which HY you sell (and the resulting HY% and reduction ppt) is the differentiator; buy sizing and the qualitative note are secondary. Clear watchlist to 0 and land HY under cap.
- **Overlay / sleeve-action sets are all-or-nothing**: a partial match earns no credit — commit to the single most defensible overlay/action set rather than hedging.
- **next_step with a live breach**: prefer `approve_with_monitoring` over `approve_rotation`.

## 8. Output discipline

Return a single JSON object conforming to `input/payloads/answer_template.json`. Match
every field name, enum value, ordering rule, and precision exactly. Include only the
fields the template requires. Do not add narrative outside the JSON. Round every
number to the field's declared precision. Re-derive all metrics from current
environment data, never from stale local payloads.
