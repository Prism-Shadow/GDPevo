---
name: asteria-investment-office-tasks
description: >-
  Solve Asteria Investment Office (CIO / credit desk) JSON tasks: energy/fixed-income
  credit trade packages, international equity correlation reviews, cross-asset active
  allocation view refreshes, fixed-income risk rebalances, and combined committee
  decision files. Use when a prompt references the Asteria shared environment, a
  PF-* portfolio, an answer_template.json output contract, opportunity-set allocation
  views (UW/N/OW), index correlation reviews, or energy-credit trade strategy. Covers
  which HTTP API endpoints to call, exact computation formulas and rounding, controlled
  enum mapping, current-environment-over-stale-payload precedence, and constraint checks.
---

# Asteria Investment Office Task Family

You produce a single strict JSON object that conforms to the task's `answer_template.json`.
The Asteria environment is a read-only HTTP/JSON API and is the **current book of record**.
Local payloads (`*_request.json`, `*_memo.json`, snapshots) are intake context and may be
stale — when they conflict with the environment, the environment wins.

## 0. Universal operating rules (apply to every task)

1. **Read the contract first.** Open `input/payloads/answer_template.json`. It declares the
   exact required keys, value types, enum allowed-values, list lengths, ordering rules,
   per-field rounding precision, and any `required_value` constants. Mirror it exactly:
   include every required key, use only allowed enum values, respect list lengths and the
   stated item ordering, and round each numeric field to its declared precision.
2. **Read the local payload** for IDs, the review window, focus sets, requested outputs,
   preferences and thresholds — but treat its marks/holdings/ratings/watchlist/dates as
   possibly stale.
3. **Pull current truth from the API.** Base URL `http://127.0.0.1:8036`. All endpoints are
   `GET` returning JSON. Endpoints:
   - `GET /api/catalog` — valid portfolio/policy/index/issuer/bond/opportunity-set ids.
   - `GET /api/policies` — all constraint thresholds and the allocation mapping policy.
   - `GET /api/portfolios` and `GET /api/portfolios/<id>` — objective, constraints, holdings.
   - `GET /api/instruments/bonds` — held + candidate bond universe (filter `?candidate=true`).
   - `GET /api/issuers` — sector, subsector, rating bucket, **watchlist**, outlook, tags.
   - `GET /api/market/energy` — oil/gas/LNG/refining/renewables signals + pitch themes.
   - `GET /api/indices`, `GET /api/index-levels`, `GET /api/index-levels/<index_id>` — monthly levels.
   - `GET /api/allocation/opportunity-sets` — taxonomy (asset_class, display_order).
   - `GET /api/allocation/prior-views` — prior active views (keyed by quarter).
   - `GET /api/macro-signals` — current macro/asset signal scores + rationale codes (keyed by quarter).
   - Filters supported on list endpoints by field name, e.g. `?rating_bucket=HY`, `?candidate=true`,
     `?quarter=Q3_2026`, `?issuer_id=...`, `?region=...`.
4. **as_of_date** = the environment's current as-of date. Read it from `GET /api/policies`
   (`as_of_date`) or from `GET /api/portfolios/<id>` (`as_of_date`). Do NOT use the local
   payload's request/memo/snapshot date for `as_of_date`. (In the observed environment this
   is `2026-05-29`; always re-read it rather than hard-coding.)
5. **data_precedence / refresh:** If the local payload disagrees with the environment on any
   mark, holding, rating, watchlist status, MV, or date, the conflict resolves in favor of the
   environment. For a `data_precedence` field, emit `current_environment_over_stale_payload`
   when such a conflict exists (it usually does — payloads deliberately carry stale snapshots);
   use `no_conflict_found` only if everything matches.
6. **Constants:** Copy `required_value` fields verbatim (e.g. `task_id`, `portfolio_id`,
   `target_quarter`). Read `policy_id` from the environment (`POL...`/`POLICY_SET_...`), not invented.
7. Output **only** the JSON object — no prose, no markdown fences.

## 1. Reference data model (observed)

- **Policies** (`/api/policies`): `correlation` thresholds `high=0.80`, `low=0.20`;
  `credit_default` and `credit_risk_reduction`: `duration_band_years=[3.0,5.0]`,
  `max_hy_allocation_pct=20.0`, `issuer_concentration_limit_pct=12.0`,
  `subsector_min_count_for_diversified=2`; `target_hy_reduction_pct` = 0.0 (default) or
  4.0 (risk-reduction). `allocation_mapping`: `view_score_thresholds` OW_min=0.35,
  UW_max=−0.35, neutral in (−0.35, 0.35); `conviction_thresholds` HIGH |s|≥0.7,
  MEDIUM |s|≥0.35, LOW |s|<0.35; `view_rank` {UW:−1, N:0, OW:+1}. The top-level
  `policy_id` (e.g. `POLICY_SET_2026_05`) is the lineage id for allocation memos.
  Always re-read these — do not hard-code numbers if a new task uses a different policy.
- **Bonds:** each has `rating_bucket` (IG/HY), `modified_duration_years`,
  `yield_to_maturity_pct`, `issuer_id`, `subsector`, `sector`, `energy_linked` (bool),
  `candidate` (bool), `recommended_theme_tags`, `spread_bps`, `coupon_pct`, `maturity`.
- **Issuers:** carry the authoritative `watchlist` boolean, `credit_outlook`,
  `rating_bucket`, `sector`/`subsector`, `research_tags`. Watchlist is determined at the
  **issuer** level (a bond inherits its issuer's watchlist status). A bond may also tag
  `WATCHLIST_RISK` in `recommended_theme_tags`, but trust the issuer record.
- **Quantities** are in USD millions. Treat `quantity_usd_m` as the position market value
  for all weight/allocation/duration/yield calculations (par ≈ MV, 1:1). Portfolio MV =
  sum of holding `quantity_usd_m`.
- **Index levels** are monthly. The standard review window has 12 monthly levels →
  **11 monthly returns**.

## 2. Core calculations and rounding

### 2.1 Portfolio credit metrics (market-value weighted by quantity_usd_m)
Let `q_i` = post-trade quantity (USD m) of instrument i, `MV = Σ q_i`.
- `total_market_value_usd_m = MV` (round 2 dp).
- `hy_allocation_pct = 100 * (Σ q_i over HY bucket) / MV` (round 2 dp).
- `weighted_modified_duration_years = (Σ q_i * modified_duration_years_i) / MV`
  (round to template precision — 2 dp for metrics objects).
- `weighted_yield_to_maturity_pct = (Σ q_i * ytm_i) / MV` (round 2 dp).
- `issuer_concentration_pct(issuer) = 100 * (Σ q_i for that issuer) / MV`; must be
  ≤ `issuer_concentration_limit_pct` (12%).
- `hy_reduction_pct_points = pre_trade_hy_pct − post_trade_hy_pct` (percentage points, 2 dp),
  where pre/post HY% use their respective MV denominators.
- `watchlist_exposure_usd_m = Σ q_i over holdings whose issuer is on watchlist` (round to
  the field's precision, often 1 dp).

Always compute pre-trade metrics from current environment holdings, apply the trades, then
compute post-trade metrics. Round only the final reported number, not intermediates.

### 2.2 Pearson correlation from monthly index levels
1. For each index, fetch `/api/index-levels/<index_id>` and keep only levels with
   `level_start_date ≤ date ≤ level_end_date` (the requested/policy window). Sort ascending by date.
2. Monthly **simple returns**: `r_t = level_t / level_{t-1} − 1` for consecutive months.
   12 levels → 11 returns; report `return_observations` = number of returns.
3. Pearson correlation between two return series a, b:
   `corr = Σ(a−ā)(b−b̄) / sqrt(Σ(a−ā)² · Σ(b−b̄)²)`.
4. **Round correlations to 3 decimals.**
5. Compute over the pairwise combinations of the requested index universe only.

### 2.3 Active allocation view derivation (from macro score + prior view)
For each opportunity set, read its **current-quarter macro signal** from `/api/macro-signals`
filtered to the task's `target_quarter` (the row matching `opportunity_set` + `quarter`):
- `signal_score` = that row's `score` (report at template precision, e.g. 3 dp).
- `view`: OW if score ≥ 0.35; UW if score ≤ −0.35; else N. (Use policy thresholds, not hard 0.35.)
- `conviction`: HIGH if |score| ≥ 0.7; MEDIUM if 0.35 ≤ |score| < 0.7; LOW if |score| < 0.35.
- `prior_view`: from `/api/allocation/prior-views`, the row whose **`quarter` equals the
  target quarter** (its `previous_quarter` is the prior quarter; that row carries the prior
  view/conviction the desk is updating from). For Q2_2026, use prior-views rows with
  `quarter == Q2_2026`.
- `change`: compare new view to prior_view via `view_rank` {UW:−1,N:0,OW:+1}:
  rank(new) > rank(prior) → `UP`; < → `DOWN`; equal → `UNCHANGED`.
- `rationale_code`: use the macro-signal row's `rationale_code` directly. **Exception:** when
  the resolved view is `N` (neutral), use `NEUTRAL_BALANCE`. (When the macro rationale is
  already NEUTRAL_BALANCE this is moot; the safe rule for any N view is NEUTRAL_BALANCE.)
- `asset_class`: from `/api/allocation/opportunity-sets` (Equities / Duration / Credit / Currency).

## 3. SOPs by task type

Identify the task type from the prompt + which template keys exist:

### SOP A — Energy / fixed-income credit trade package (BUY tickets)
Template signature: `trade_package`, `post_trade_metrics`, `constraint_checks`,
`sales_positioning`, `data_precedence`.

1. Read the portfolio (`/api/portfolios/<id>`) for current holdings, MV, constraints,
   policy_id. Read `/api/instruments/bonds`, `/api/issuers`, `/api/market/energy`.
2. Determine the desk mandate from the payload: ticket count, total notional, even split,
   allowed actions (e.g. exactly 2 BUYs, $8.0m total → $4.0m each).
3. **Eligible candidate filter** (intersection of all):
   - `candidate == true` (only buy from the candidate universe; held-only bonds are not buys);
   - matches the desk's exposure theme (e.g. `energy_linked == true` for an energy sleeve);
   - issuer **not on watchlist** (drop any bond whose issuer.watchlist is true — e.g. the
     refining/E&P/telecom names) — this is the "avoid watchlist yield trap" rule;
   - align with current energy signals: favor positive signals (LNG, gas, power, midstream,
     contracted renewables); avoid negative ones (refining). Refining names are also watchlisted.
4. **Selection** to maximize carry while passing constraints and suiting an income pitch:
   - Build a package of distinct issuers (issuer diversification) **and** ≥2 distinct
     subsectors (`subsector_min_count_for_diversified`).
   - Keep post-trade `hy_allocation_pct` ≤ `max_hy_allocation_pct` (20%) and post-trade
     `weighted_modified_duration_years` inside `duration_band_years` (3.0–5.0).
   - Prefer a quality/carry balance (e.g. one IG carry name + one HY carry name) rather than
     stacking the lowest-quality highest-yield names — better income pitch and keeps HY low.
   - Tie-break toward the strongest current energy theme (e.g. LNG when LNG signal is highest).
5. Compute `post_trade_metrics` per §2.1 (apply buys to current holdings).
6. `constraint_checks` (all booleans): `hy_cap_pass` (post HY% ≤ cap),
   `duration_band_pass` (post WMD within band), `selected_issuer_diversification_pass`
   (selected buys are distinct issuers and each issuer post-trade ≤ 12% concentration),
   `selected_subsector_diversification_pass` (≥2 distinct subsectors among selected),
   `watchlist_avoidance_pass` (no selected issuer on watchlist).
7. `sales_positioning.target_segment`: map from the payload's client context
   (e.g. "multi-asset income update" → `multi_asset_income`; private-bank income →
   `private_bank_income`; insurance GA, pension LDI, endowment opportunistic likewise).
   `theme`: map to the dominant energy signal (LNG strongest → `lng_export_tailwind`;
   midstream defensive → `midstream_stability`; oil oversupply → `oil_oversupply_caution`;
   transition/renewables selectivity → `transition_bond_selectivity`; if the headline risk is
   avoiding watchlisted high-yield refiners → `avoid_watchlist_yield_trap`).
8. `data_precedence`: compare payload snapshot vs environment (MV, HY%, duration, holdings).
   Stale snapshot present → `current_environment_over_stale_payload`.
9. `trade_package` ordering: **ascending by instrument_id**; each item
   `{action:"BUY", instrument_id, notional_usd_m}` with notional at 1 dp.

### SOP B — International equity correlation review
Template signature: `review_window`, `index_set`, `extreme_pairs`, `concentration`,
`diversification_candidates`, `sleeve_actions`.

1. Read the requested `index_universe` and window from the payload; cross-check the window
   against `/api/policies.correlation` (`review_window_start/end`) and `/api/indices`.
2. Compute monthly simple returns and the full pairwise Pearson matrix over the universe
   (§2.2). Set `review_window` = {level_start_date, level_end_date, return_observations(=11)}.
   `index_set` = the universe sorted ascending alphabetically by index id.
3. `extreme_pairs.highest_positive` = pair with max correlation; `extreme_pairs.lowest` =
   pair with min correlation. Each `pair_id` is the two ids **sorted alphabetically**;
   `correlation` rounded to 3 dp.
4. `concentration`:
   - `high_threshold_breached` = (max correlation across the matrix ≥ `correlation_high_threshold`
     0.80).
   - `china_asia_dependence_flag` = true when the China / Asia-Pacific complex is highly
     correlated with the broad/EM sleeves (e.g. China–AsiaPac and China–EM correlations ≥ 0.80),
     i.e. the sleeve's risk is concentrated in China/Asia beta.
   - `primary_code`: `CHINA_ASIA_DEPENDENCE` if the china_asia flag is set;
     else `GLOBAL_DEVELOPED_OVERLAP` if the dominant high pair is among developed/global indices
     (World/EAFE/ACWI overlap); else `NO_MATERIAL_CONCENTRATION` if nothing breaches the high threshold.
5. `diversification_candidates` (allowed subset, e.g. EM_EX_CHINA / INDIA / LATAM): pick the
   candidates with the **lowest correlation to the concentration anchor** (China/Asia complex)
   — typically the negative/near-zero ones plus the structural China-removal sleeve. Exclude
   any candidate that is itself highly correlated to the anchor. Sort ascending alphabetically.
6. `sleeve_actions` (length 2, ascending by sleeve name): **trim** the concentrated sleeve
   (e.g. China) and **add** the best diversifier sleeve (e.g. Latin America). Use
   `target_index_id` from the allowed list; `action` from {trim, add, hold, hedge, monitor, rotate}.

### SOP C — Active allocation view refresh
Template signature: `allocation_views` (list), `risk_overlay`, plus lineage
(`as_of_date, target_quarter, prior_quarter, policy_id, task_id`).

1. Lineage: copy `task_id`/`target_quarter`/`prior_quarter` constants from the template/payload;
   `policy_id` from `/api/policies` top-level (`POLICY_SET_...`); `as_of_date` from environment.
2. `allocation_views`: one row per `focus_opportunity_sets` entry, **in the payload's focus
   order** (not display_order). For each set derive view/change/conviction/rationale_code and
   `asset_class` per §2.3. Verify the row count matches `required_length`.
3. `risk_overlay`: synthesize the portfolio-level tilt from the views:
   - Duration strongly OW + High Yield strongly UW → `DURATION_QUALITY_TILT` /
     `tilt_to_duration_quality`.
   - Credit (HY/IG) the dominant risk to cut → `CREDIT_RISK_REDUCTION` / `trim_credit_beta`.
   - Cyclical equities the dominant positive theme → `EQUITY_BETA_EXTENSION` /
     `add_cyclical_equity_beta`.
   - Currency defensiveness the headline → `CURRENCY_DEFENSIVE_HEDGE` / `add_currency_hedge`.
   - Nothing material → `NO_OVERLAY` / `hold_policy_weights`.
   `rationale_codes`: the strongest risk-relevant drivers in business-priority order
   (highest priority first) — typically the overlay's own theme first (e.g. DURATION_SUPPORT),
   then the credit-risk theme (HY_VALUATION_RISK), then the dominant equity risk
   (CHINA_DEPENDENCE). Take these from the macro `rationale_code`s of the most extreme
   |score| sets that justify the overlay.

### SOP D — Fixed-income risk rebalance (rotation)
Template signature: `rotation.trades`, `risk_metrics`, `exception_flags`,
`watchlist_handling`, `risk_note_code`.

1. Read current holdings, constraints, `target_hy_reduction_pct` (policy
   `POL_CREDIT_RISK_REDUCTION` → 4.0), and the memo's preferences (min HY reduction,
   keep duration in CIO band, avoid new watchlist buys). Read bonds + issuers for current
   ratings/watchlist; the memo's "stale exception board"/"shortlist" are hints, not truth.
2. **Sells:** sell the pressure points. Any **watchlist** holding must be sold (mandatory).
   Also sell enough additional HY to bring post-trade HY% under the cap and to meet/exceed the
   target HY reduction, but **do not over-sell** — keep non-watchlist HY carry where the cap and
   reduction targets are already satisfied (the goal is reduction, not elimination). Sell the
   **entire** position of each instrument you choose to sell (full current `quantity_usd_m`).
3. **Buys (funding):** the rotation is **self-funded** — total BUY notional = total SELL
   notional, so portfolio MV is unchanged. Fund from current eligible candidates
   (`candidate==true`), **never buy a watchlist issuer**. Prefer IG names that keep duration
   inside the band and avoid a duration shortfall (longer-dated IG raises duration toward the
   band's upper half without breaching 5.0). Reject any shortlisted name whose issuer is on the
   watchlist (rejection reason = watchlist).
4. `risk_metrics`: `post_trade_hy_allocation_pct` (2 dp), `post_trade_duration_years` (2 dp),
   `hy_reduction_pct_points` = pre HY% − post HY% (2 dp), `post_trade_watchlist_exposure_usd_m`
   (1 dp; should be 0.0 once all watchlist holdings are sold).
5. `exception_flags`: `hy_cap_pass` (post ≤ 20%), `duration_band_pass` (post within 3–5),
   `target_hy_reduction_met` (reduction ≥ target), `watchlist_exposure_cleared` (post WL exp = 0).
6. `watchlist_handling`: `watchlist_sell_ids` = ascending instrument_ids of the watchlist
   holdings sold (only issuers actually on watchlist; non-watchlist HY sells are NOT listed);
   `buys_avoid_watchlist` = true if no buy is a watchlist issuer.
7. `risk_note_code`: the headline binding issue — `watchlist_concentration` if clearing
   watchlist was the driver; `hy_cap_pressure` if HY cap was the driver; `duration_preservation`
   if duration was the constraint; `carry_tradeoff` if carry give-up was the theme; `no_action`
   if no trade.
8. `trades` ordering: **SELL before BUY**, then ascending instrument_id within each action.
   Each trade `{action, instrument_id, quantity_usd_m}` at 1 dp.

### SOP E — Combined committee decision file
Template signature: `correlation_summary`, `target_sleeve_actions`, `allocation_views`,
`rebalance_trigger`, `portfolio_risk_concentration_flag`, `next_step`.

1. `correlation_summary` (length 2, order [highest_concentration, best_diversifier]): run §2.2
   over the requested equity index ids. `highest_concentration` = max-correlation pair;
   `best_diversifier` = min-correlation pair. `pair` ids sorted alphabetically; correlation 3 dp.
2. `allocation_views` (fixed item_order from template, e.g. EM, India, LatAm, USD): derive
   per §2.3, including `prior_view`, `signal_score` (3 dp), `view`, `change`, `conviction`,
   `rationale_code`.
3. `target_sleeve_actions` (same item_order): map each view to an action — UW → `trim`,
   OW → `add`, equity N → `hold`/`monitor`; a currency sleeve flagged for defensiveness →
   `hedge` (e.g. USD). Honor the committee's stated focus when it dictates a defensive hedge.
4. `portfolio_risk_concentration_flag` = true if the highest equity correlation ≥
   `correlation_high_threshold` (0.80).
5. `rebalance_trigger`: `correlation_cap_breach` if the concentration breaches the correlation
   cap; else `hy_cap_pressure` / `duration_drift` / `watchlist_concentration` if those are
   binding; else `committee_review`.
6. `next_step`: `approve_with_monitoring` when a concentration is flagged but the rotation is
   acceptable; `approve_rotation` if clean; `defer_pending_risk_review` if unresolved exceptions;
   `reject_constraint_breach` if a hard limit is breached and cannot be cleared.
7. Honor the stale-note instruction to refresh (e.g. a payload that "kept USD overweight"
   must be re-derived from current macro signals — likely no longer OW).

## 4. Enum mapping quick reference

- View: score ≥ +0.35 → `OW`; ≤ −0.35 → `UW`; else `N`.
- Conviction: |score| ≥ 0.7 → `HIGH`; ≥ 0.35 → `MEDIUM`; else `LOW`.
- Change: rank(new) vs rank(prior) using {UW:−1,N:0,OW:+1} → `UP`/`DOWN`/`UNCHANGED`.
- Rationale: macro row's `rationale_code`; if view is `N` use `NEUTRAL_BALANCE`. Codes commonly
  seen: GROWTH_IMPROVES, RATE_CUT_SUPPORT, CREDIT_SPREAD_RISK, DOLLAR_DEFENSIVE,
  CHINA_DEPENDENCE, LATAM_DIVERSIFIER, INDIA_OFFSET, DURATION_SUPPORT, HY_VALUATION_RISK,
  EUROPE_RECOVERY, JAPAN_POLICY_RISK, NEUTRAL_BALANCE.
- Sleeve action: UW→trim, OW→add, N→hold/monitor, currency-defensive→hedge.
- Energy theme: LNG dominant→lng_export_tailwind; midstream→midstream_stability;
  oil oversupply→oil_oversupply_caution; transition/renewables→transition_bond_selectivity;
  watchlist HY avoidance→avoid_watchlist_yield_trap.

## 5. Common pitfalls / exclusions

- **Do not use the local payload's date** for `as_of_date`; use the environment as-of date.
- **Do not buy held-only or watchlist-issuer bonds.** Buys come from `candidate==true` and
  non-watchlist issuers only.
- **Watchlist is an issuer attribute** — resolve every bond's watchlist status via its issuer.
- **11 returns from 12 levels.** Filter levels strictly to the requested window before
  computing returns; report `return_observations` accordingly.
- **Pair ids and index_set must be alphabetically sorted;** trade/rotation lists have their own
  ordering rules (instrument_id ascending; SELL-before-BUY) — read the template's ordering note
  per field, they differ.
- **Self-funded rotations:** total BUY notional must equal total SELL notional (MV unchanged)
  unless the payload says otherwise. Even-split BUY packages must split the total evenly.
- **Round only the final reported value** to the template precision; compute on unrounded values.
- **prior_view comes from the prior-views row whose `quarter` == target quarter** (its
  `previous_quarter` is the quarter before). Do not pick the wrong quarter's row.
- **Risk-overlay `rationale_codes` are ordered by business priority** (overlay theme first),
  not by raw score magnitude.
- Emit only the JSON object; include every required key; never invent enum values or ids.

## 6. Verification checklist before returning

- Validate against `answer_template.json`: all required keys present, enums valid, list lengths
  and orderings correct, required_value constants exact.
- Re-confirm each numeric field's rounding precision.
- Re-derive views/correlations from the **current** environment (not the stale payload).
- Confirm constraint booleans are consistent with the computed metrics (HY cap, duration band,
  issuer concentration, watchlist, target reduction).
