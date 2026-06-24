---
name: asteria-investment-office-json
description: >
  Repeatable workflow for answering Asteria Investment Office (PF-*) portfolio
  tasks against the shared HTTP environment (<remote-env-url>).
  Covers five archetypes: (a) energy-credit trade-package selection,
  (b) international equity correlation review, (c) active allocation view refresh,
  (d) fixed-income risk rebalance, (e) multi-asset committee decision. Tells you
  which endpoints to call, the exact math, the policy thresholds, and the output
  schema conventions (field names, enum sets, rounding, id ordering). Use whenever
  the prompt names an Asteria portfolio id, an allocation/correlation/credit memo,
  or asks for JSON matching an answer_template.
---

# Asteria Investment Office — task workflow

The Asteria environment is a **read-only HTTP API and the current book of record**.
Local payloads in `input/payloads/` are intake context only and may be stale.
**When local disagrees with the environment, the environment always wins.**

Base URL: `<remote-env-url>`. Use `curl` for HTTP and `python`
(NOT `python3`) for math. Save fetched JSON only inside your own working dir.

## Golden rules (apply to every task)

1. **Environment is the source of truth.** Re-fetch every number from the API.
   Treat market values, holdings, quantities, ratings, durations, yields,
   watchlist flags, signal scores, prior views, and index levels as authoritative
   even if the local payload quotes a different "stale" value. The `as_of_date` in
   your answer = the environment `as_of_date` (e.g. from `/api/policies` or the
   portfolio record), NOT any date in the local memo.
2. **Read the answer_template like a contract.** Honor exactly: required keys,
   the `required_value` constants (portfolio_id, task_id, quarter, etc.), enum
   `allowed_values` (use the literal strings/casing shown — note some enums are
   lowercase like `trim`/`add`/`hold`, others UPPER like `UW`/`OW`/`BUY`),
   numeric `precision` (round to that many decimals), list `length`/`required_length`,
   and the **ordering rule** for every list.
3. **Ordering conventions seen:** sort trade lists ascending by `instrument_id`;
   for SELL/BUY lists "SELL before BUY, then instrument_id ascending"; index
   `pair_id` / `pair` = the two ids in **alphabetical order**; `index_set` /
   candidate lists = alphabetical; allocation rows = the payload's
   `focus_opportunity_sets` order (or the template's explicit `item_order`).
4. **Output only the JSON object** (no prose) when the prompt says so.
5. **Never call any scoring/judge endpoint.** Only the data endpoints below exist.
6. Bootstrap every task by fetching `/api/catalog` (valid ids) and `/api/policies`
   (all thresholds). Then fetch the archetype-specific endpoints.

## Policy reference (`GET /api/policies`)

Read these live each run; values below are the structure to expect.

- `allocation_mapping`:
  - `view_score_thresholds`: `OW_min` (e.g. 0.35), `UW_max` (e.g. -0.35),
    neutral band between. Map a signal `score` → view:
    `OW if score >= OW_min; UW if score <= UW_max; else N`.
  - `conviction_thresholds`: `HIGH_abs_min` (e.g. 0.7), `MEDIUM_abs_min`
    (e.g. 0.35), `LOW_abs_below` (e.g. 0.35). Map on **abs(score)**:
    `HIGH if |s|>=HIGH_abs_min; MEDIUM if |s|>=MEDIUM_abs_min; else LOW`.
  - `view_rank`: `{UW:-1, N:0, OW:1}` → `change` = compare new vs prior rank:
    higher=`UP`, lower=`DOWN`, equal=`UNCHANGED`.
- `correlation`: `correlation_high_threshold` (e.g. 0.8),
  `correlation_low_threshold` (e.g. 0.2), and the official review window
  (`review_window_start`/`_end`).
- `credit_default` / `credit_risk_reduction`: `duration_band_years` (e.g. [3.0,5.0]),
  `max_hy_allocation_pct` (e.g. 20.0), `issuer_concentration_limit_pct` (e.g. 12.0),
  `subsector_min_count_for_diversified` (e.g. 2), `target_hy_reduction_pct`
  (0.0 for default, 4.0 for risk-reduction). A portfolio's own
  `constraints.policy_id` tells you which credit policy applies.
- `multi_asset_risk.committee_escalation_threshold`:
  `two_or_more_material_exceptions` (drives committee `next_step`).

---

## Archetype (a) — Energy-credit trade-package selection

Example prompt: "Prepare the proposed energy-credit trade strategy / BUY package
for PF-EN-ALTA." Template keys: `portfolio_id`, `as_of_date`, `trade_package`
(list of {action, instrument_id, notional_usd_m}), `post_trade_metrics`,
`constraint_checks`, `sales_positioning`, `data_precedence`.

**Endpoints:** `/api/portfolios/<id>` (holdings, market_value, constraints),
`/api/instruments/bonds` (universe), `/api/issuers` (watchlist/outlook),
`/api/market/energy` (signals + pitch themes), `/api/policies` (credit policy).

**Candidate eligibility filter (intersect all):**
- `candidate == true` (only buy candidates, not already-held core lines),
- `energy_linked == true` (for the energy sleeve),
- issuer `watchlist == false` (watchlist avoidance — exclude DRIFTWOOD, JUNIPER,
  PACIFIC_REFIN, etc.; their bonds are deliberate yield-trap distractors),
- the resulting **post-trade** portfolio must stay inside the credit constraints.

**Sizing:** honor the request (e.g. "two BUY tickets totaling 8.0m split evenly"
= two 4.0m BUYs). `notional_usd_m` precision per template (often 1 dp).

**Post-trade metric recipe** (notional-weighted over held + bought positions):
- `total_market_value_usd_m` = current MV + total new notional (precision 2).
- `hy_allocation_pct` = (sum HY notional / total) * 100 (rating_bucket=="HY").
- `weighted_modified_duration_years` = Σ(md_i * q_i)/Σq_i over all positions.
- `weighted_yield_to_maturity_pct` = Σ(ytm_i * q_i)/Σq_i. "Improve carry" means
  post-trade weighted YTM > pre-trade weighted YTM.

**constraint_checks (booleans):**
- `hy_cap_pass`: post-trade HY% <= `max_hy_allocation_pct`.
- `duration_band_pass`: post-trade weighted MD within `duration_band_years`.
- `selected_issuer_diversification_pass`: the two **selected buys** are from
  two **distinct issuers** (this is a check on the SELECTED names, not the whole
  book — the existing portfolio may already exceed the 12% issuer-concentration
  guideline, which is unavoidable and not what this flag measures).
- `selected_subsector_diversification_pass`: the selected buys span
  >= `subsector_min_count_for_diversified` distinct subsectors.
- `watchlist_avoidance_pass`: neither selected name's issuer is watchlisted.

**Selection judgment:** among eligible pairs that pass all constraints and improve
carry, prefer the package that matches the desk preference and the strongest
current market signal. The energy signal scores (`/api/market/energy`) rank
themes — e.g. LNG export pull is typically the strongest positive, refining is
negative ("avoid refining watchlist"). For a **client-facing income pitch** /
committee that is "sensitive to headline carry from watchlist issuers," do NOT
max raw yield by loading HY to just under the cap; favor IG LNG/gas-demand carry
(e.g. BlueGas/Eastern-LNG family) plus a diversifying second subsector.

**Enums:** `action` ∈ {BUY,SELL,HOLD,NO_TRADE}; `sales_positioning.target_segment`
typically `multi_asset_income` (or `private_bank_income`) for an income pitch;
`theme` = `lng_export_tailwind` when LNG is the lead signal (or
`midstream_stability` / `avoid_watchlist_yield_trap` as the data dictates);
`data_precedence` = `current_environment_over_stale_payload` whenever the live
record differs from the stale snapshot (it usually does — e.g. MV/HY/duration
move vs the worksheet).

---

## Archetype (b) — International equity correlation review

Example prompt: "international equity correlation review for PF-INT-NEXVEN."
Template keys: `portfolio_id`, `review_window`, `index_set`, `extreme_pairs`
(highest_positive / lowest), `concentration`, `diversification_candidates`,
`sleeve_actions`.

**Endpoints:** `/api/portfolios/<id>`, `/api/indices` (metadata, window dates),
`/api/index-levels` or `/api/index-levels/<id>` (monthly levels), `/api/policies`
(correlation thresholds). Use the index universe + window from the request payload
(cross-check against the policy review window — they match, e.g.
2025-05-30 → 2026-04-30).

**Correlation recipe (do this in python):**
1. For each index, take monthly **levels** within `[level_start_date,
   level_end_date]`, sorted by date. A 12-level window → **11 monthly returns**.
2. Convert to **simple returns**: `r_t = level_t/level_{t-1} - 1`.
3. `return_observations` = number of returns = (#levels - 1) = 11 (report the
   return count, not the level count).
4. Pearson correlation between each pair's return series:
   `r = Σ(a-ā)(b-b̄) / sqrt(Σ(a-ā)² · Σ(b-b̄)²)`. Round to **3 decimals**.
5. Over all C(n,2) pairs: `highest_positive` = max correlation pair,
   `lowest` = min (most negative) correlation pair.
6. **`pair_id` = the two index ids sorted alphabetically**, length 2.

**concentration block:**
- `china_asia_dependence_flag` (bool): true when China / EM / Asia-Pacific indices
  are highly correlated (China–EM pair near/above the high threshold).
- `high_threshold_breached` (bool): the highest pairwise correlation
  >= `correlation_high_threshold` (0.8). With a global benchmark in the set the
  top pair (e.g. EM–WORLD ~0.97) breaches.
- `primary_code` enum: `CHINA_ASIA_DEPENDENCE` when the China/Asia cluster drives
  concentration; else `GLOBAL_DEVELOPED_OVERLAP` or `NO_MATERIAL_CONCENTRATION`.

**diversification_candidates:** from the template's allowed set
({IDX_EM_EX_CHINA, IDX_INDIA, IDX_LATAM}), the indices that are the lowest-
correlated diversifiers vs the concentrated cluster (LatAm and India typically
show negative correlation to China). Alphabetical order.

**sleeve_actions:** two rows, ascending by sleeve. `action` ∈
{trim,add,hold,hedge,monitor,rotate}; `target_index_id` ∈
{IDX_CHINA, IDX_EM_EX_CHINA, IDX_LATAM}. Logic: trim/hedge the concentrated
China/EM exposure, add the diversifier (e.g. LatAm / EM-ex-China).

---

## Archetype (c) — Active allocation view refresh

Example prompt: "Q2 active allocation view refresh." Template keys: `task_id`,
`as_of_date`, `target_quarter`, `prior_quarter`, `policy_id`, `allocation_views`
(one row per focus opportunity set), `risk_overlay`.

**Endpoints:** `/api/allocation/opportunity-sets` (asset_class mapping +
display_order), `/api/allocation/prior-views`, `/api/macro-signals`,
`/api/policies`.

**Per-row recipe** for each requested opportunity_set, at the **target quarter**:
- `score` = `/api/macro-signals` row for (opportunity_set, target_quarter).
- `rationale_code` = that row's `rationale_code` (use it verbatim; it is already
  one of the template enum values, e.g. INDIA_OFFSET, CHINA_DEPENDENCE,
  LATAM_DIVERSIFIER, DURATION_SUPPORT, HY_VALUATION_RISK, EUROPE_RECOVERY,
  JAPAN_POLICY_RISK, NEUTRAL_BALANCE, etc.).
- `view` = map score via `view_score_thresholds` (OW/N/UW).
- `conviction` = map |score| via `conviction_thresholds` (HIGH/MEDIUM/LOW).
- `change` = compare new `view` rank vs the **prior view**. The prior view is the
  `/api/allocation/prior-views` row whose `quarter == target_quarter` (i.e. the
  standing/published view for that quarter, whose `previous_quarter` ==
  `prior_quarter`). Compute UP/DOWN/UNCHANGED from view_rank.
- `asset_class` = from `/api/allocation/opportunity-sets` (Equities/Duration/
  Credit/Currency).
- `policy_id` (lineage) = `allocation_mapping.policy_id` (or the policy-set id as
  the template implies); `as_of_date` = environment as_of_date;
  `target_quarter`/`prior_quarter` echo the request.
- Row ordering = the payload's `focus_opportunity_sets` order.

**risk_overlay:** pick the `overlay_code` + `primary_action` that summarize the
dominant tilt across the rows, and list contributing `rationale_codes` in
business-priority order. Heuristics from the data:
- Strong duration-quality signals (Treasuries/Bunds OW, HY UW) →
  `DURATION_QUALITY_TILT` / `tilt_to_duration_quality`, leading rationale
  DURATION_SUPPORT (+ RATE_CUT_SUPPORT, HY_VALUATION_RISK).
- Dominant HY/credit-spread risk → `CREDIT_RISK_REDUCTION` / `trim_credit_beta`
  (CREDIT_SPREAD_RISK / HY_VALUATION_RISK first).
- Broad equity OW → `EQUITY_BETA_EXTENSION` / `add_cyclical_equity_beta`.
- USD/defensive currency tilt → `CURRENCY_DEFENSIVE_HEDGE` / `add_currency_hedge`.
- Otherwise `NO_OVERLAY` / `hold_policy_weights`.

---

## Archetype (d) — Fixed-income risk rebalance

Example prompt: "fixed-income risk rebalance / rotation for PF-FI-LUMEN — reduce
HY and watchlist pressure, keep duration in range." Template keys: `task_id`,
`portfolio_id`, `as_of_date`, `rotation.trades`, `risk_metrics`,
`exception_flags`, `watchlist_handling`, `risk_note_code`.

**Endpoints:** `/api/portfolios/<id>`, `/api/instruments/bonds`, `/api/issuers`,
`/api/policies` (this portfolio uses `POL_CREDIT_RISK_REDUCTION`, so
`target_hy_reduction_pct` = 4.0).

**Setup:** compute current weighted MD, current HY% (HY notional / MV * 100),
current watchlist exposure (Σ notional of held bonds whose issuer
`watchlist == true`). Identify held watchlist names (sell candidates) and held HY.

**Build a MV-neutral rotation** (Σ sells == Σ buys, so total MV is unchanged):
- **SELL** the held watchlist name(s) in full (clear watchlist) plus enough other
  held HY to satisfy the HY cap. **Caution:** selling only the single watchlist
  line often leaves HY still above the 20% cap — you usually need a **second HY
  sell** (e.g. another chemicals/consumer HY line) so `hy_cap_pass` is true.
- **BUY** only **eligible candidates**: `candidate == true` AND issuer
  `watchlist == false` (avoid_new_watchlist_buy). A watchlisted candidate
  (e.g. JUNIPER_2030) is a distractor — never buy it even though it has high
  carry. Prefer IG names that keep weighted MD inside the band and span
  >= 2 subsectors. Split buys to fund the sells (e.g. two equal IG buys).

**risk_metrics (recompute post-trade):** `post_trade_hy_allocation_pct` (2dp),
`post_trade_duration_years` (2dp), `hy_reduction_pct_points` =
current_HY% - post_HY% (2dp), `post_trade_watchlist_exposure_usd_m` (1dp, = 0
after clearing).

**exception_flags (booleans):** `hy_cap_pass` (post HY% <= cap),
`duration_band_pass` (post MD in band), `target_hy_reduction_met`
(hy_reduction >= `target_hy_reduction_pct`), `watchlist_exposure_cleared`
(post watchlist exposure == 0).

**watchlist_handling:** `watchlist_sell_ids` = sold watchlist instrument_ids,
ascending; `buys_avoid_watchlist` = true (always, by construction).

**trades ordering:** SELL rows before BUY rows, instrument_id ascending within
each action. `quantity_usd_m` precision 1. `action` ∈ {BUY,SELL}.

**risk_note_code** enum: choose the dominant theme — `hy_cap_pressure`
(HY over cap was the binding issue), `watchlist_concentration`,
`duration_preservation`, `carry_tradeoff`, or `no_action`.

---

## Archetype (e) — Multi-asset committee decision

Example prompt: "committee JSON for PF-MA-HELIO linking correlation findings to
allocation views." Template keys: `portfolio_id`, `as_of_date`, `review_quarter`,
`correlation_summary`, `target_sleeve_actions`, `allocation_views`,
`rebalance_trigger`, `portfolio_risk_concentration_flag`, `next_step`.

This archetype **composes (b) + (c)** for a small focused set, then makes a
governance decision.

**Endpoints:** all of (b) and (c): `/api/portfolios/<id>`, `/api/index-levels`,
`/api/policies`, `/api/allocation/prior-views`, `/api/macro-signals`.

**correlation_summary:** length 2 in fixed order
[`highest_concentration`, `best_diversifier`]. Compute Pearson correlations
(monthly simple returns, 3dp) over the requested 4-index window; the highest
positive pair = `highest_concentration`, the most negative pair =
`best_diversifier`. Each `pair` is alphabetically sorted, length 2. (For an
EM/China/India/LatAm set: highest ≈ China–EM; lowest ≈ China–LatAm.)

**allocation_views:** for each requested opportunity set, output `prior_view`,
`signal_score` (3dp, from macro-signals), `view`, `change`, `conviction`,
`rationale_code` — same mapping recipe as archetype (c), at the review quarter.
Watch the **stale-note trap**: e.g. a desk note may keep USD overweight, but if
the current USD score sits in the neutral band it maps to `N` (change DOWN). The
environment wins.

**target_sleeve_actions:** one action per opportunity set (same item_order),
`action` ∈ {trim,add,hold,hedge,monitor,rotate}. Tie to the views/correlation:
trim/hedge the concentrated leg, add the diversifier (e.g. add LatAm, hold/trim
EM, hold India OW, trim/hedge USD).

**Governance fields:**
- `portfolio_risk_concentration_flag` (bool): true when the top equity pair
  correlation >= `correlation_high_threshold` (0.8) — i.e. a real concentration
  exception exists.
- `rebalance_trigger` enum: `correlation_cap_breach` when the high-correlation
  threshold is breached; else `hy_cap_pressure`/`duration_drift`/
  `watchlist_concentration`/`committee_review` as the dominant cause.
- `next_step` enum: under `multi_asset_risk` escalation
  (`two_or_more_material_exceptions`), if there are >=2 material exceptions
  (e.g. correlation breach + a view downgrade) lean to
  `defer_pending_risk_review`; a single, manageable exception →
  `approve_with_monitoring`; a clean book → `approve_rotation`; a hard constraint
  breach you cannot cure → `reject_constraint_breach`. Decide from the computed
  exceptions, not the stale note.

---

## Common misjudgments to avoid

- Using stale payload numbers (MV, HY%, duration, quantities, USD-OW) instead of
  re-fetching — the worksheet is intentionally out of date.
- Counting **levels** instead of **returns** for `return_observations`
  (12 levels → 11 returns).
- Using log returns — the spec is **simple** returns.
- Not alphabetizing the two ids inside a pair, or not sorting the list itself.
- Buying a watchlisted candidate for its high carry (distractor), or buying an
  already-held core line instead of a `candidate==true` name.
- Treating `selected_issuer_diversification_pass` as a whole-portfolio
  concentration test — it is about the two **selected** buys.
- Clearing the watchlist name but forgetting that HY% can still exceed the cap,
  so a second HY sell is required.
- Maxing raw carry to just under the HY cap when the brief is a conservative,
  client/committee income pitch.
- Wrong enum casing (`BUY` vs `buy`, `trim` vs `TRIM`, `OW` vs `ow`) or wrong
  rounding precision — copy them verbatim from the template.
- Echoing a date from the local memo as `as_of_date` instead of the environment
  as_of_date.
