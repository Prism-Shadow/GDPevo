# Asteria Investment Office — Portfolio-Risk Evaluation Skill

This skill distills reusable execution knowledge for solving Asteria Investment
Office portfolio-risk tasks. The test task gives you a prompt, an
`input/payloads/answer_template.json`, and one or more request payloads. You
also have the remote Asteria environment (the current book of record) and this
skill. Use the environment as the source of truth and follow the SOPs below.

The tasks draw on three workflows that may also be combined:

- **Workflow A — Energy / fixed-income credit trade strategy.** Build a BUY/SELL
  bond package under credit-risk constraints, then report post-trade metrics,
  constraint booleans, and sales positioning.
- **Workflow B — International equity correlation review.** Compute pair
  correlations from monthly index levels, flag concentration, and propose sleeve
  actions.
- **Workflow C — Cross-asset active allocation view refresh.** Translate macro
  signal scores into active views (UW/N/OW) with conviction, change vs prior
  quarter, rationale, plus risk overlay and committee fields.

---

## 0. Golden rules (read first)

1. **Environment is the current book of record.** The remote service at
   `<remote-env-url>` is authoritative for current holdings, holding
   quantities, issuer status, market signals, index levels, policies, prior
   views, and macro signals. Local `input/payloads/*.json` files are **intake
   context** that may be stale (old worksheet dates, stale marks, stale
   quantities, old shortlists). When a local payload conflicts with the
   environment, **prefer the environment** unless the task prompt explicitly
   overrides. Set `data_precedence` accordingly
   (`current_environment_over_stale_payload` when a conflict exists;
   `no_conflict_found` only when nothing stale is present). Watch for explicit
   "stale" markers in payloads (`snapshot_date`, `stale_*`, `memo_as_of_date`,
   `stale_local_note`, "Operations has not reconciled..." comments) — these
   signal you must refresh from the environment.
2. **Always read `answer_template.json` first.** It defines required keys,
   allowed enum values, field precision, ordering rules, and list lengths.
   Conform exactly: a field declared `precision: 1` must be rounded to 1
   decimal; a list declared `length: 2` must have exactly 2 items; an enum must
   use one of the allowed values verbatim.
3. **`as_of_date` is the environment's current date**, NOT the payload's request
   date or memo date. Read it from `GET /api/policies` (top-level `as_of_date`)
   or any `GET /api/portfolios/<id>` (`as_of_date`). All train examples use the
   environment as_of_date (e.g. `2026-05-29`), not the older memo/snapshot dates.
4. **Correlations are never precomputed.** Compute them yourself from
   `GET /api/index-levels` (monthly simple returns, see Workflow B).
5. **Be precise about ordering.** Lists are sorted as the template declares:
   trade packages by `instrument_id` ascending (or SELL-before-BUY then
   instrument_id), index sets/pair_ids alphabetically, allocation rows in the
   request payload's focus order, sleeve_actions by sleeve name ascending.

---

## 1. Environment endpoints (GET only)

Base URL: `<remote-env-url>`. Call with `curl` or Python `urllib`.

| Endpoint | Use |
|---|---|
| `GET /api/catalog` | All available portfolio ids, policy ids, index ids, issuer ids, bond ids, opportunity sets. |
| `GET /api/policies` | **Constraints + thresholds.** Returns top-level `policy_id` (e.g. `POLICY_SET_2026_05`), `as_of_date`, and sub-policies `credit_default`, `credit_risk_reduction`, `correlation`, `allocation_mapping`, `multi_asset`, `multi_asset_risk`. |
| `GET /api/portfolios` | Portfolio summaries. |
| `GET /api/portfolios/<id>` | One portfolio: objective, `constraints`, current `holdings` (each with `instrument_id`, `quantity_usd_m`, sleeve, notes), `market_value_usd_m`, `as_of_date`. |
| `GET /api/instruments/bonds` | Full bond universe. Filter with `?candidate=true`, `?rating_bucket=HY`, etc. Each bond has `instrument_id`, `issuer_id`, `sector`, `subsector`, `rating`, `rating_bucket` (IG/HY), `modified_duration_years`, `yield_to_maturity_pct`, `coupon_pct`, `maturity`, `energy_linked` (bool), `candidate` (bool), `recommended_theme_tags`. |
| `GET /api/issuers` | Issuer master: `issuer_id`, `sector`, `subsector`, `rating_bucket`, **`watchlist` (bool)**, `outlook`, `issuer_name`. |
| `GET /api/market/energy` | Energy market signals + `pitch_themes`. Used for sales positioning in energy trade tasks. |
| `GET /api/indices` | Index metadata (`level_start_date`, `level_end_date`, region, currency). |
| `GET /api/index-levels` | Object keyed by `index_id`, each a list of `{date, level}` monthly observations. |
| `GET /api/index-levels/<id>` | Monthly levels for one index. |
| `GET /api/allocation/opportunity-sets` | Opportunity-set taxonomy: `opportunity_set`, `asset_class` (Equities/Duration/Credit/Currency), `display_order`. |
| `GET /api/allocation/prior-views` | List of prior active views. Each entry has `opportunity_set`, `quarter` (the effective quarter), `previous_quarter` (when set), `view`, `conviction`. Two cohorts exist: a Q_{n-1}→Q_n cohort (the prior standing view) and a Q_n→Q_{n+1} cohort. |
| `GET /api/macro-signals` | List of macro signal scores. Each has `opportunity_set`, `quarter`, `score` (signed float), `rationale_code`, `drivers`. |

---

## 2. Cross-cutting conventions

### Precision (follow `answer_template.json` declarations)
- `notional_usd_m` / `quantity_usd_m` → **1 decimal**.
- `post_trade_metrics` numeric fields (`*_usd_m` with precision 2, `hy_allocation_pct`, `weighted_modified_duration_years`, `weighted_yield_to_maturity_pct`) → **2 decimals**.
- `correlation` → **3 decimals**.
- `signal_score` → **3 decimals**.
- `total_market_value_usd_m` → **2 decimals** (per template).
- Booleans are `true`/`false`. Round half-up to the declared precision; JSON drops
  trailing zeros naturally (e.g. `5.80` renders as `5.8`).

### Policy snapshot (`GET /api/policies`)
Key fields the SOPs reference (concrete values observed; re-read at test time in
case the environment changed):
- `policy_id` (top-level): the policy-set id used as the allocation `policy_id`
  field (e.g. `POLICY_SET_2026_05`).
- `credit_default` / `credit_risk_reduction`: `duration_band_years: [3.0, 5.0]`,
  `max_hy_allocation_pct: 20.0`, `issuer_concentration_limit_pct: 12.0`,
  `subsector_min_count_for_diversified: 2`. `credit_risk_reduction` adds
  `target_hy_reduction_pct: 4.0` (the minimum HY reduction a rebalance must
  achieve). Portfolios opt into one of these via `constraints.policy_id`.
- `correlation`: `correlation_high_threshold: 0.8`, `correlation_low_threshold:
  0.2`, `review_window_start`, `review_window_end`.
- `allocation_mapping`: `view_score_thresholds` (`OW_min: 0.35`, `UW_max: -0.35`,
  `neutral_between: [-0.35, 0.35]`), `conviction_thresholds` (`HIGH_abs_min: 0.7`,
  `MEDIUM_abs_min: 0.35`, `LOW_abs_below: 0.35`), `view_rank` (`UW=-1, N=0, OW=1`).

### Which policy a portfolio uses
Read `GET /api/portfolios/<id>` → `constraints.policy_id`. A pure credit sleeve
uses `POL_CREDIT_DEFAULT`; a risk-reduction rotation uses
`POL_CREDIT_RISK_REDUCTION` (which adds the `target_hy_reduction_pct` floor).
Multi-asset sleeves compose: `POL_MULTI_ASSET_DEFAULT` references credit +
correlation + allocation; `POL_MULTI_ASSET_RISK` references correlation +
credit-risk-reduction.

---

## 3. Workflow A — Energy / fixed-income credit trade strategy

Applies to: standalone energy sleeve trades and fixed-income risk-reduction
rotations. Two sub-shapes exist:

- **Income-add shape (two BUY tickets):** `trade_package` (BUY list),
  `post_trade_metrics`, `constraint_checks`, `sales_positioning`,
  `data_precedence`.
- **Rotation shape (SELL+BUY):** `rotation.trades` (SELL before BUY),
  `risk_metrics`, `exception_flags`, `watchlist_handling`, `risk_note_code`.

### Step-by-step SOP

1. **Read the portfolio** `GET /api/portfolios/<portfolio_id>`. Capture current
   holdings (`instrument_id`, `quantity_usd_m`), `market_value_usd_m`,
   `as_of_date`, and `constraints` (duration band, HY cap, target HY reduction).
   **Use these environment quantities, not any stale quantities in the local
   memo.** (Example pattern: a local memo may show a holding at 10.0 while the
   environment shows 12.0 — trade off the 12.0.)
2. **Read all bonds** `GET /api/instruments/bonds` (and `?candidate=true` for the
   buy universe). **Read all issuers** `GET /api/issuers` to get the
   `watchlist` flag per issuer (join on `issuer_id`).
3. **Apply exclusion filters to candidate buys:**
   - **Watchlist avoidance:** drop any bond whose issuer `watchlist == true`.
     This is a hard exclusion (the desk is "sensitive to headline carry from
     watchlisted issuers"). Candidates flagged with theme tags like
     `WATCHLIST_RISK` / `REFINANCING_RISK` or refining issuers (negative
     refining signal) are exclude-by-default.
   - **Duration-band eligibility:** keep only bonds whose
     `modified_duration_years` is within the policy band **[3.0, 5.0]**
     (inclusive). Long-dated distractors (dur 5.8, 6.7, 5.9) and very short
     ones (dur 2.3) are excluded. For an income-add where the *package* must
     keep the *portfolio* weighted duration in band, individual buy durations
     should sit inside the band.
   - **HY capacity:** HY buys are allowed only if post-trade HY % stays under
     the cap (20%). Do not blind-buy the highest-YTM HY name if it breaches the
     cap or concentrates a watchlisted issuer.
   - **Sector/energy linkage:** for an *energy* sleeve task, buy bonds with
     `energy_linked == true`. (`energy_linked` is a bond-level field, not the
     issuer `sector`; e.g. a utilities-issuer power bond can be energy-linked.)
   - **Issuer concentration:** no single issuer should exceed
     `issuer_concentration_limit_pct` (12%) of post-trade market value.
4. **Select the package** honoring the desk's stated preferences (e.g. LNG
   exporters / gas demand / non-watchlist carry) and the "improve carry" goal
   (higher YTM helps). A robust pattern for a two-ticket income add:
   - Pick one IG bond that matches the preferred theme (LNG/gas) for ballast +
     client pitch suitability.
   - Pick one higher-carry non-watchlist energy-linked bond (often HY) that
     lifts portfolio YTM while keeping HY % well under cap and adding issuer +
     subsector diversification.
   - Verify post-trade weighted duration stays inside the band and that new
     issuers/subsectors increase diversification.
   For a **rotation (risk-reduction)** task:
   - Sell watchlist holdings first (entire positions); the watchlist sells are
     reported in `watchlist_sell_ids`.
   - Sell additional HY as needed to bring post-trade HY % under cap and meet
     `target_hy_reduction_pct`. Prefer keeping higher-carry non-watchlist HY and
     trimming lower-carry HY when both are eligible, so carry is preserved.
   - Fund duration ballast by buying IG candidates from the shortlist that are
     non-watchlist and inside the duration band; weight notionals toward longer
     duration to replace duration lost when selling short-duration HY.
   - Keep the package roughly self-funding (total sell notional ≈ total buy
     notional) so total market value is preserved.
5. **Order the trades** as the template declares. Income-add: ascending by
   `instrument_id`. Rotation: **SELL before BUY**, then `instrument_id`
   ascending within each action. Notional field name follows the template
   (`notional_usd_m` for income-add; `quantity_usd_m` for rotation).

### Post-trade metrics computation (mechanical, market-value-weighted)

Build the post-trade book = current holdings adjusted by trades (SELL subtracts,
BUY adds; use environment quantities). Then:

- `total_market_value_usd_m` = sum of post-trade `quantity_usd_m`.
- `hy_allocation_pct` = (sum of HY `quantity_usd_m`) / total_market_value × 100,
  rounded to 2 decimals. (HY defined by bond `rating_bucket == "HY"`.)
- `weighted_modified_duration_years` = Σ(quantity · modified_duration_years) /
  total_market_value, rounded to 2.
- `weighted_yield_to_maturity_pct` = Σ(quantity · yield_to_maturity_pct) /
  total_market_value, rounded to 2.

For rotation outputs:
- `post_trade_hy_allocation_pct` = post-trade HY % (2 decimals).
- `post_trade_duration_years` = post-trade weighted modified duration (2 dp).
- `hy_reduction_pct_points` = pre_trade_HY% − post_trade_HY% (2 dp, can be
  large when a watchlist HY block is removed).
- `post_trade_watchlist_exposure_usd_m` = sum of post-trade quantities whose
  issuer `watchlist == true` (1 decimal; should be 0.0 if all watchlist names
  were sold).
- Pre-trade HY % is computed the same way on the un-adjusted holdings.

**Verify every metric by recomputing; do not trust stale worksheet snapshots.**

### Constraint-check derivation (booleans)

- `hy_cap_pass` = post-trade HY % ≤ `max_hy_allocation_pct` (20.0).
- `duration_band_pass` = post-trade weighted duration within
  `duration_band_years` (inclusive [3.0, 5.0]).
- `issuer_diversification_pass` / `selected_issuer_diversification_pass` = no
  single issuer exceeds `issuer_concentration_limit_pct` (12%) of post-trade
  MV (and, for "selected" variants, the newly selected issuers are distinct from
  each other / add diversification).
- `subsector_diversification_pass` / `selected_subsector_diversification_pass` =
  the holding set (or selected buys) spans at least
  `subsector_min_count_for_diversified` (2) subsectors.
- `watchlist_avoidance_pass` = no bought bond has a watchlisted issuer (and for
  rotation, `watchlist_exposure_cleared` = post-trade watchlist exposure == 0).
- `target_hy_reduction_met` (rotation only) = `hy_reduction_pct_points` ≥
  `target_hy_reduction_pct` (4.0 for credit_risk_reduction policy).

### Sales positioning (energy income-add)

Read `GET /api/market/energy`. Pick the strongest positive signal that matches
your selected bonds' theme tags:
- LNG export pull (highest positive score) → `theme: lng_export_tailwind`.
- Midstream defensive carry → `midstream_stability`.
- Oil discipline / oversupply caution → `oil_oversupply_caution`.
- Watchlist yield avoidance → `avoid_watchlist_yield_trap`.
- Selective transition/renewables → `transition_bond_selectivity`.

`target_segment` follows the client context in the desk request (e.g.
"multi-asset income update" → `multi_asset_income`; insurance / pension /
private-bank / endowment contexts map to their respective enum). When
refining/refiner signals are negative and watchlisted, do NOT pick a refining
theme; the refining signal being negative + AVOID_REFINING_WATCHLIST pitch theme
reinforces watchlist avoidance.

### `risk_note_code` (rotation)

Pick the dominant driver of the rotation:
`watchlist_concentration` (when the main issue was a watchlisted holding),
`hy_cap_pressure` (when HY cap drove sells), `duration_preservation` (when the
rotation's point was keeping duration in band), `carry_tradeoff` (when selling
carry to reduce risk), `no_action` (when nothing needed fixing). If watchlist
exposure was the trigger, `watchlist_concentration` is correct.

---

## 4. Workflow B — International equity correlation review

No correlations are precomputed. Compute from `GET /api/index-levels`.

### Correlation method (confirmed deterministic)

1. Take the review window from the request payload
   (`review_window.level_start_date` / `level_end_date`) — these match the
   policy `correlation.review_window_start/end` for the default window. For each
   index in the requested `index_universe`, extract the monthly levels in date
   order across the window.
2. Compute **monthly simple returns**: `r[t] = level[t] / level[t-1] − 1` for
   consecutive observations. A window with 12 month-end levels yields **11
   return observations** (`review_window.return_observations` = 11).
3. For each unordered pair of indices, compute the **Pearson correlation** of
   their return series:
   `corr = cov(r_x, r_y) / (σ_x · σ_y)` (population, dividing by n).
4. `extreme_pairs.highest_positive` = the pair with max correlation;
   `extreme_pairs.lowest` = the pair with min correlation (most negative).
   `pair_id` lists the two index ids **sorted alphabetically**. Round correlation
   to **3 decimals**.
5. `index_set` = the requested universe, sorted ascending alphabetically.

### Concentration flags

Using the policy thresholds `correlation_high_threshold (0.8)` and
`correlation_low_threshold (0.2)`:
- `high_threshold_breached` = **any** pair correlation ≥ 0.8.
- `china_asia_dependence_flag` = true when `IDX_CHINA` correlation with the
  Asia/EM/developed block (IDX_EM, IDX_AC_ASIA_PAC_EX_JP, IDX_ACWI_IMI,
  IDX_WORLD, IDX_EAFE, IDX_EM_EX_CHINA, IDX_INDIA) is ≥ 0.8 — i.e. China is
  tightly coupled to the regional/global complex.
- `primary_code`:
  - `CHINA_ASIA_DEPENDENCE` when China↔Asia/EM pairs drive the concentration
    (CIO memos flag ASIA_BETA_OVERLAP / CHINA_DEDICATED_SLEEVE).
  - `GLOBAL_DEVELOPED_OVERLAP` when the dominant high-correlation cluster is
    developed/global (IDX_WORLD, IDX_EAFE, IDX_ACWI_IMI) rather than China.
  - `NO_MATERIAL_CONCENTRATION` when no pair breaches the high threshold.

### Diversification candidates

From the template's allowed candidate set, select indices that **diversify the
concentration center** (typically China). Rank allowed candidates by their
correlation with the concentration center ascending (most negative / lowest
first). Include those that meaningfully diversify:
- Indices with **negative** correlation to the center (e.g. IDX_LATAM, which is
  negatively correlated to everything) always qualify.
- Indices that structurally remove the concentration (e.g. IDX_EM_EX_CHINA)
  qualify as the "ex-China" diversifier.
- **Exclude** an allowed candidate whose correlation with the concentration
  center breaches the high threshold in a way that adds to (not relieves) the
  concentration (e.g. IDX_INDIA when it is ≥0.8 with China does not diversify
  China risk). Sort the resulting list ascending alphabetically.

### Sleeve actions

Produce the number of sleeve-action objects the template requires, ordered
**ascending by sleeve name**. Map from the review's conclusions:
- `trim` the concentrated sleeve (the source of concentration, e.g. the China
  dedicated sleeve).
- `add` the best diversifier sleeve (e.g. Latin America).
- `hold` / `monitor` / `hedge` / `rotate` for other sleeves as appropriate.
`target_index_id` and `action` must use the template's allowed enums.

---

## 5. Workflow C — Cross-asset active allocation view refresh

This is **largely deterministic** — derive views mechanically from macro signal
scores and the `allocation_mapping` policy. Do not editorialize.

### Per opportunity set (one allocation_views row)

1. **prior_view** = the view from `GET /api/allocation/prior-views` for the entry
   where `quarter == target_quarter` AND `previous_quarter == prior_quarter`.
   (This is the standing view set last quarter for the current quarter.)
2. **signal_score** = `GET /api/macro-signals` score for
   `(opportunity_set, quarter == target_quarter)` (round to 3 decimals if the
   template exposes it).
3. **rationale_code** = that macro-signal entry's `rationale_code` (verbatim
   from the environment — e.g. CHINA_DEPENDENCE, INDIA_OFFSET,
   LATAM_DIVERSIFIER, DURATION_SUPPORT, HY_VALUATION_RISK, EUROPE_RECOVERY,
   JAPAN_POLICY_RISK, DOLLAR_DEFENSIVE, NEUTRAL_BALANCE, RATE_CUT_SUPPORT,
   CREDIT_SPREAD_RISK, GROWTH_IMPROVES).
4. **view** from `signal_score` via `allocation_mapping.view_score_thresholds`:
   - score ≥ `OW_min` (0.35) → `OW`
   - score ≤ `UW_max` (−0.35) → `UW`
   - otherwise → `N`
5. **conviction** from `|signal_score|` via `conviction_thresholds`:
   - |score| ≥ `HIGH_abs_min` (0.7) → `HIGH`
   - `MEDIUM_abs_min` (0.35) ≤ |score| < 0.7 → `MEDIUM`
   - |score| < `LOW_abs_below` (0.35) → `LOW`
6. **change** from `view_rank` (UW=−1, N=0, OW=1): compare `rank(new_view)` vs
   `rank(prior_view)`:
   - new > prior → `UP`
   - new < prior → `DOWN`
   - equal → `UNCHANGED`
7. **asset_class** = the `asset_class` from
   `GET /api/allocation/opportunity-sets` for that opportunity set (Equities /
   Duration / Credit / Currency).
8. **Row order** = the request payload's `focus_opportunity_sets` order (not
   alphabetical). `required_length` matches the focus list size.
9. **policy_id** = the top-level `policy_id` from `GET /api/policies`
   (e.g. `POLICY_SET_2026_05`). `target_quarter` / `prior_quarter` = the request
   values. `as_of_date` = environment as_of_date.

### Risk overlay (judgment, but patterned)

Choose `overlay_code` / `primary_action` from the macro picture formed by the
rows (paired enums: DURATION_QUALITY_TILT↔tilt_to_duration_quality,
CREDIT_RISK_REDUCTION↔trim_credit_beta, EQUITY_BETA_EXTENSION↔add_cyclical_equity_beta,
CURRENCY_DEFENSIVE_HEDGE↔add_currency_hedge, NO_OVERLAY↔hold_policy_weights):
- If duration/quality is supported (U.S. Treasuries OW, DURATION_SUPPORT) **and**
  HY is a risk (Corporate HY UW, HY_VALUATION_RISK) →
  `DURATION_QUALITY_TILT` / `tilt_to_duration_quality`.
- If HY/credit spread risk dominates → `CREDIT_RISK_REDUCTION` /
  `trim_credit_beta`.
- If defensive currency is the theme → `CURRENCY_DEFENSIVE_HEDGE` /
  `add_currency_hedge`.
- If cyclical growth recovery dominates with no risk offset →
  `EQUITY_BETA_EXTENSION` / `add_cyclical_equity_beta`.
- If views net to roughly neutral with no material risk → `NO_OVERLAY` /
  `hold_policy_weights`.

`rationale_codes` = the rationale codes driving the overlay choice, ordered by
**business priority** (highest priority first). Favor the risk-reduction and
duration-support rationales first (e.g. DURATION_SUPPORT, HY_VALUATION_RISK,
CHINA_DEPENDENCE), then growth/diversifier codes. Keep the list to the 2–4 most
material drivers.

---

## 6. Combined workflow — correlation + allocation (committee JSON)

Some tasks (multi-asset committee files) combine B and C: a small index
sub-universe correlation summary plus allocation views for the matching sleeves.

- `correlation_summary` (length 2, ordered `[highest_concentration,
  best_diversifier]`): compute Pearson over the requested index subset;
  `highest_concentration` = the **max**-correlation pair; `best_diversifier` =
  the **min** (most negative) pair. Each `pair` sorted alphabetically;
  correlation rounded to 3 decimals.
- `target_sleeve_actions`: one row per requested opportunity set, in the
  template's `item_order`. Map view → action: OW → `add`, UW → `trim`. For a
  currency sleeve (USD) that is downgraded from OW toward neutral, use `hedge`
  (reduce the defensive long). Stable OW → `add`/`hold`; stable N → `hold`/
  `monitor`.
- `allocation_views`: same deterministic computation as Workflow C (prior_view,
  signal_score, view, change, conviction, rationale_code), in the template's
  `item_order`.
- `rebalance_trigger`:
  - `correlation_cap_breach` when a high-threshold pair breach drove the review
    (most common when the correlation summary shows a pair ≥ 0.8).
  - `hy_cap_pressure` / `duration_drift` / `watchlist_concentration` for those
    drivers; `committee_review` as the generic catch-all.
- `portfolio_risk_concentration_flag`: true when the correlation summary or
  constraint picture shows material concentration (a pair ≥ high threshold, or a
  China/Asia dependence flag).
- `next_step`:
  - `approve_with_monitoring` when actions reduce concentration but residual
    monitoring is warranted (common when the package trims the concentrated
    sleeve and adds diversifiers without a hard breach remaining).
  - `approve_rotation` when the proposed rotation fully resolves the issue.
  - `defer_pending_risk_review` when material exceptions remain unresolved.
  - `reject_constraint_breach` when a constraint breach cannot be fixed.

---

## 7. Common misjudgments to avoid

- **Trusting stale holding quantities / marks.** The local memo is intake
  context. A "stale_exception_board" with `stale_quantity_usd_m` or a
  "stale_holding_snapshot" is explicitly unreliable — recompute off the
  environment portfolio. Sell quantities must equal the environment's current
  holding quantity when exiting a position.
- **Buying a watchlisted issuer.** Always join bonds → issuers and check
  `watchlist`. High-carry HY names (yield 9–11%) are often traps: a watchlisted
  refiner or E&P issuer with a HIGH_CARRY/WATCHLIST_RISK tag should be excluded
  even if it maximizes YTM.
- **Duration-ineligible distractors.** Long-dated IG names (dur 5.8–6.7) and
  very short HY names (dur 2.3) sit outside the [3.0, 5.0] band. Do not pick
  them as buys; flag the band as the reason.
- **Misreading `energy_linked`.** It is a bond-level boolean, not the issuer's
  sector label. Filter buys for the task's sector requirement using this flag.
- **Forgetting the HY cap after adds.** A high-YTM HY buy can push post-trade HY
  % over 20%; recompute and choose a smaller notional or an IG alternative.
- **Computing correlations wrong.** Use **simple monthly returns**
  (level[t]/level[t-1]−1), not log returns or level changes; use **Pearson**
  (cov/σσ); the number of return observations is one fewer than the number of
  levels. Round to 3 decimals; sort pair ids alphabetically.
- **Inventing allocation views.** Views/conviction/rationale are *computed* from
  macro-signals + the allocation_mapping thresholds + prior-views — not
  judgment. A score of 0.732 is OW/HIGH/INDIA_OFFSET, not a subjective call.
- **Wrong `change`.** `change` compares the new view rank to the **prior standing
  view** (from prior-views for the target quarter), not to a guessed baseline.
  OW(1)→UW(−1) is DOWN; N(0)→OW(1) is UP; OW→OW is UNCHANGED.
- **Wrong as_of_date.** Use the environment's current as_of_date, not the
  request_date / memo_as_of_date / snapshot_date in the local payload.
- **Wrong trade ordering.** Income-add packages sort by instrument_id ascending;
  rotation packages put SELL before BUY then instrument_id ascending within each
  action.
- **Including rationale_code not in the enum.** Only use rationale codes that
  appear in the template's `allowed_values` and are returned by the macro-signals
  endpoint verbatim.
- **Over- or under-rounding.** Match each field's declared precision exactly.

---

## 8. Final output checklist

Before emitting the JSON:

- [ ] Every required top-level key present; no extra narrative outside the JSON
      (unless the prompt allows it — most say "Return only JSON").
- [ ] `as_of_date` = environment as_of_date; `portfolio_id` / `task_id` /
      `target_quarter` / `prior_quarter` / `review_quarter` match the template's
      `required_value`.
- [ ] All enums use allowed values verbatim; all booleans are real booleans.
- [ ] Every numeric field rounded to its declared precision.
- [ ] Lists sorted and sized per template (`ordering`, `length`,
      `required_length`, `item_order`).
- [ ] `trade_package` / `rotation.trades` ordering correct (instrument_id asc;
      SELL-before-BUY where applicable).
- [ ] Post-trade metrics recomputed from environment holdings + trades (not the
      stale snapshot); constraint booleans derived from recomputed metrics vs
      policy thresholds.
- [ ] Watchlist joins performed; no watchlisted issuer bought; watchlist sells
      reported correctly.
- [ ] Correlations computed from monthly simple returns (Pearson, 3 decimals).
- [ ] Allocation views computed from macro-signals + allocation_mapping policy +
      prior-views; `change` vs the matching prior-views cohort.
- [ ] `data_precedence` reflects whether a local payload was stale vs the
      environment.
- [ ] Validate the final object against `answer_template.json` field-by-field.
