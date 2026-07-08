---
name: asteria-investment-office-json
description: >
  Produce committee-grade JSON answers for the Asteria Investment Office across
  five portfolio archetypes — (a) energy-credit trade packages, (b) international
  equity correlation reviews, (c) active allocation-view refreshes, (d)
  fixed-income risk rebalances, and (e) multi-asset committee decisions. Covers
  the exact endpoints to pull, the deterministic computation recipes (Pearson
  correlation on monthly simple returns, notional-weighted modified duration and
  YTM, HY allocation %, carry, concentration), the policy thresholds that drive
  views/conviction/constraint checks, and the output-schema conventions (field
  names, enum sets, rounding, id ordering) that the desk's answer templates
  require. Use whenever a task references an Asteria portfolio (PF-*), index
  (IDX_*), bond (BND_*), issuer (ISS_*), policy (POL_*), or an answer_template.json.
---

# Asteria Investment Office — committee JSON solver

## 0. Golden rules (apply to every archetype)

1. **The HTTP environment is the book of record.** Local payloads
   (desk_request, review_request, memo, committee_request, "stale" snapshots,
   exception boards, prior-week shortlists) are *intake context only*. Whenever a
   local number disagrees with the environment (holding quantities, marks, HY %,
   duration, currency views, index levels), USE THE ENVIRONMENT VALUE. A common
   trap: a memo lists a stale holding quantity (e.g. 10.0) while the live
   portfolio shows 12.0 — compute with 12.0. When the schema has a
   `data_precedence` field, the value is `current_environment_over_stale_payload`
   in essentially every refresh/rebalance case.
2. **`as_of_date`** = the environment's current as-of date (the `as_of_date`
   returned by `/api/policies`, `/api/portfolios/<id>`, `/api/market/energy`,
   etc.), NOT any date written in the local payload.
3. **Follow the answer_template exactly**: required keys, enum value sets
   (verbatim casing), rounding precision, list lengths, and ordering rules.
   Echo `required_value` fields literally (portfolio_id, task_id, quarters).
4. **Rounding**: round only at the end, to the precision the template declares
   per field. Trailing-zero forms are fine (5.8 == 5.80). Compute with full
   precision; never round intermediate weighted sums.
5. **Ordering**: respect each field's stated order — "ascending by instrument_id",
   "alphabetical by index id", "SELL before BUY then id ascending", or "in the
   request payload's focus order / item_order". Within a correlation pair, sort
   the two ids alphabetically.
6. **Use `python` (not python3) and `curl`.** Save fetched JSON locally and
   compute deterministically; do not eyeball.

## 1. Endpoints

Base: `GET` on the Asteria HTTP service.

- `/api/catalog` — id inventory (portfolios, policies, indices, issuers, bonds, opportunity sets).
- `/api/policies` — **all thresholds** (see §2). Also gives the current `as_of_date`.
- `/api/portfolios/<id>` — objective, constraints (incl. `policy_id`), holdings (instrument_id, quantity_usd_m, sleeve), `market_value_usd_m`.
- `/api/instruments/bonds` — bond master: `rating_bucket` (IG/HY), `modified_duration_years`, `yield_to_maturity_pct`, `coupon_pct`, `spread_bps`, `sector`, `subsector`, `energy_linked`, `candidate` (eligible for purchase), `issuer_id`, `recommended_theme_tags`.
- `/api/issuers` — `watchlist` (bool), `credit_outlook`, `rating_bucket`, `sector`, `subsector`, `research_tags`.
- `/api/market/energy` — commodity `signals` with `score`/`direction` (oil, gas, LNG, refining, renewables) + `pitch_themes`.
- `/api/indices` and `/api/index-levels[/<id>]` — monthly index level series.
- `/api/allocation/opportunity-sets` — opportunity_set → asset_class (Equities/Duration/Credit/Currency) + display_order.
- `/api/allocation/prior-views` — prior active views per opportunity_set & quarter (view, conviction, previous_quarter).
- `/api/macro-signals` — per opportunity_set & quarter: `score` (signed) and `rationale_code` and `drivers`.

Most list endpoints accept equality filters (`?rating_bucket=HY`, `?candidate=true`, `?quarter=Q2_2026`).

## 2. Policy thresholds (from `/api/policies` — read them, don't hardcode blindly)

- **Allocation mapping** (`POL_ALLOCATION_MAPPING`):
  - View from signal score: `OW` if score ≥ `OW_min` (0.35); `UW` if score ≤ `UW_max` (-0.35); else `N`. Boundaries are inclusive of OW/UW.
  - Conviction from |score|: `HIGH` if |score| ≥ 0.70; `LOW` if |score| < 0.35; else `MEDIUM`.
  - view_rank: UW=-1, N=0, OW=+1 (used to derive `change`).
- **Correlation** (`POL_CORRELATION_DEFAULT`): `correlation_high_threshold` = 0.8, `correlation_low_threshold` = 0.2. Review window dates are given by the policy/request (e.g. 2025-05-30 → 2026-04-30).
- **Credit default** (`POL_CREDIT_DEFAULT`): `duration_band_years` [3.0, 5.0]; `max_hy_allocation_pct` 20.0; `issuer_concentration_limit_pct` 12.0; `subsector_min_count_for_diversified` 2; `target_hy_reduction_pct` 0.0.
- **Credit risk reduction** (`POL_CREDIT_RISK_REDUCTION`): same band/cap but `target_hy_reduction_pct` = 4.0.
- **Multi-asset** sets compose the above; `POL_MULTI_ASSET_RISK` escalates to committee on "two_or_more_material_exceptions".

Always take the policy_id from the portfolio's own `constraints.policy_id` and use that policy's numbers.

## 3. Core computation recipes

### 3a. Pearson correlation (archetypes b, e)
1. For each index pull its monthly level series for the window; sort by date.
2. Compute **simple returns** between consecutive levels: r_t = level_t/level_{t-1} − 1.
   A 12-month window of levels yields **11 returns** → `return_observations` = 11.
3. Pearson r over the paired return vectors. Round to **3 decimals**.
4. `highest_positive` / `highest_concentration` = pair with the **max** correlation.
   `lowest` / `best_diversifier` = pair with the **minimum (most negative)** correlation.
5. Each `pair_id`/`pair` is the two index ids sorted **alphabetically**.

### 3b. Notional-weighted portfolio metrics (archetypes a, d)
Build the post-trade position list (current holdings ± trades), then weight by
`quantity_usd_m`:
- `total_market_value_usd_m` = Σ quantity (BUY-only packages add to MV; sell-and-fund rebalances keep MV constant when sells == buys).
- `weighted_modified_duration_years` = Σ(dur·qty)/Σqty.
- `weighted_yield_to_maturity_pct` = Σ(ytm·qty)/Σqty.
- `hy_allocation_pct` = (Σ qty where rating_bucket==HY) / total · 100, on **post-trade** MV.
- `hy_reduction_pct_points` = pre-trade HY% − post-trade HY%.
- watchlist exposure = Σ qty of held instruments whose issuer.watchlist is true.
Note HY% and HY-reduction depend only on which HY notional is added/removed —
they are invariant to *which* IG bond you buy; only duration/YTM depend on buy identity.

### 3c. Signal → view mapping (archetypes c, e)
For each requested opportunity_set, take the **current** macro `score` for the
target quarter, map to view/conviction via §2, set `rationale_code` to the macro
signal's own `rationale_code`, set `asset_class` from the opportunity-set
taxonomy, and set `change` = sign of (new view_rank − prior view_rank) →
UP/DOWN/UNCHANGED. The prior view comes from `/api/allocation/prior-views`
(the row whose quarter == target quarter; its recorded `view` is the standing
prior). Always **recompute** the view from the live score — do not copy the
recorded prior view as the new view.

## 4. Archetype playbooks

### (a) Energy-credit trade package (e.g. PF-EN-ALTA)
Goal: N BUY tickets of equal notional that raise carry while staying inside
credit constraints and suitable for an income pitch.

Eligibility filter for a candidate bond (ALL must hold):
- `candidate == true` AND `energy_linked == true`
- issuer `watchlist == false`
- not already a current holding (new sleeve money)
- **single-bond `modified_duration_years` within the duration band [3.0, 5.0]**
  — this per-bond duration gate is decisive. A long-dated bond (e.g. dur 5.9)
  is ineligible even though the *portfolio average* might still land in band.

Selection among eligible bonds:
- Anchor on the **strongest energy signal** (typically LNG/gas — check
  `/api/market/energy`; LNG export pull is usually the top score). Pick the
  IG LNG/gas name (theme tags like LNG_EXPORTS / GAS_DEMAND).
- Pair it with the **highest-YTM** diversifier that has a **different issuer AND
  different subsector**, to maximize carry while passing diversification.
- Verify post-trade: HY% ≤ cap, weighted duration in band, both
  `selected_issuer_diversification` and `selected_subsector_diversification`
  true, `watchlist_avoidance` true. Set those constraint booleans honestly.

Schema conventions: `trade_package` length 2, sorted ascending by
`instrument_id`, each {action:"BUY", instrument_id, notional_usd_m (1 dp)}.
`post_trade_metrics` (MV 2dp, hy% 2dp, dur 2dp, ytm 2dp). `sales_positioning`:
target_segment from the client context (e.g. `multi_asset_income`), theme from
the dominant signal (e.g. `lng_export_tailwind`). `data_precedence` =
`current_environment_over_stale_payload`.

### (b) International equity correlation review (e.g. PF-INT-NEXVEN)
1. Compute the full correlation matrix over the requested index universe (§3a).
2. `extreme_pairs.highest_positive` and `.lowest` per §3a; `return_observations`
   from the window (11 for a 12-level year).
3. `index_set` = the universe sorted alphabetically.
4. `concentration`:
   - `high_threshold_breached` = any pair correlation ≥ 0.8 (true when the cluster
     is tightly correlated).
   - `china_asia_dependence_flag` = true when China/Asia/EM sleeves are mutually
     ≥ 0.8 (a dedicated-China + Asia-beta overlap exists).
   - `primary_code` = the dominant concentration label. Choose
     `CHINA_ASIA_DEPENDENCE` when the China/Asia block drives it, else
     `GLOBAL_DEVELOPED_OVERLAP` when the top pair is a broad developed/global
     overlap (e.g. EM↔World), else `NO_MATERIAL_CONCENTRATION`. (Keep
     china_asia_dependence_flag and primary_code logically consistent with which
     pair is actually the maximum.)
5. `diversification_candidates` = the low-correlation diversifier sleeve(s) from
   the allowed set (the index whose correlations are negative / well below the
   0.2 low threshold is the clearest — a LatAm-type sleeve; include an India-type
   only if it is a genuine relative diversifier, exclude broad EM-ex-China which
   stays ≥0.8).
6. `sleeve_actions` (ordered ascending by sleeve): **trim** the concentrated
   sleeve (the dedicated China/over-weighted one) and **add** the low-correlation
   diversifier. Prefer decisive `trim`/`add` over `monitor`/`hold` for a flagged
   concentration.

### (c) Active allocation refresh (balanced multi-asset, e.g. Q2 focus list)
For each focus opportunity_set, emit a row {opportunity_set, asset_class, view,
change, conviction, rationale_code} using §3c. Order rows by the request payload's
focus order. Lineage: `policy_id` = `POL_ALLOCATION_MAPPING`; quarters echoed
from the request; `as_of_date` = env as-of.

`risk_overlay`:
- Pick `overlay_code`/`primary_action` from the dominant cross-asset tilt implied
  by the views: duration support + IG quality with HY underweight →
  `DURATION_QUALITY_TILT` / `tilt_to_duration_quality`; a credit-led de-risk →
  `CREDIT_RISK_REDUCTION` / `trim_credit_beta`; strong cyclical equity →
  `EQUITY_BETA_EXTENSION`; defensive FX → `CURRENCY_DEFENSIVE_HEDGE`; else
  `NO_OVERLAY`.
- `rationale_codes` = the supporting macro rationale codes in business-priority
  order (duration/quality support first, then the credit-risk code), highest
  priority first.
(The allocation rows are the heavily weighted, deterministic part — get the
score-mapping, conviction boundaries, and `change` exactly right.)

### (d) Fixed-income risk rebalance (sell-and-fund, e.g. PF-FI-LUMEN)
Use `POL_CREDIT_RISK_REDUCTION` (target HY reduction 4.0pp, cap 20%, band [3,5]).
Recipe:
1. Identify held HY (rating_bucket==HY) and held watchlist names (issuer.watchlist).
2. **Sells**: always sell the held **watchlist** name(s) to clear watchlist
   exposure to 0. Add the **minimum** additional HY needed to bring post-trade
   HY% under the 20% cap (and to meet the ≥4pp reduction). When choosing which
   extra HY to sell, prefer the **lowest-carry (lowest YTM)** HY name so carry is
   preserved — do not dump the highest-yielding HY.
3. **Buys**: fund with **non-watchlist IG `candidate` bonds named in the desk
   shortlist**, keeping total buys == total sells so MV/duration are preserved
   and no duration shortfall is created. **Exclude** any shortlist name whose
   issuer is on the watchlist (a tempting high-carry watchlist candidate must be
   dropped). Favor the cross-desk LNG IG name and a sector diversifier over a
   pure long-duration ballast when both are offered.
4. `risk_metrics` per §3b. `exception_flags`: hy_cap_pass (≤20%),
   duration_band_pass (in [3,5]), target_hy_reduction_met (≥4pp),
   watchlist_exposure_cleared (==0) — all true for a clean rotation.
5. `watchlist_handling.watchlist_sell_ids` = held watchlist ids you sold
   (ascending). `buys_avoid_watchlist` = true. `risk_note_code` = the dominant
   pressure (`hy_cap_pressure` when starting HY% far exceeds the cap).
6. `rotation.trades` ordered SELL before BUY, then instrument_id ascending within
   each action; quantities 1 dp.

### (e) Multi-asset committee decision (e.g. PF-MA-HELIO)
Combines (b) + (c) on a small index/opportunity subset.
1. `correlation_summary` (length 2, item order [highest_concentration,
   best_diversifier]): highest_concentration = max-correlation pair;
   best_diversifier = min (most negative) pair; pairs alphabetical, corr 3dp.
2. `allocation_views` per §3c, including `prior_view` (from prior-views) and
   `signal_score` (the macro score, 3dp). Refresh stale currency views: a stale
   note keeping USD overweight is superseded — recompute from the live score
   (often lands at N), with `change` DOWN from the prior OW.
3. `target_sleeve_actions` (item order matches the request): map view direction
   to action — UW→`trim`, OW→`add` (high-conviction OW may `hold`), and for a
   currency sleeve being de-risked use `hedge` rather than `hold`.
4. `portfolio_risk_concentration_flag` = true when a pair ≥ the 0.8 high
   threshold (e.g. China↔EM concentration).
5. `rebalance_trigger` = `committee_review` for a committee decision file
   (prefer this over the more specific `correlation_cap_breach` in committee
   framing). `next_step` = `approve_with_monitoring` when a concentration flag is
   true but the rotation is actionable (escalate/defer only on ≥2 material
   exceptions).

## 5. Pre-submission checklist
- [ ] Pulled live env data; reconciled every stale local number to it.
- [ ] `as_of_date` and `policy_id` taken from the environment, not the payload.
- [ ] All enum values match the template's allowed sets verbatim.
- [ ] Correlations: 3dp, alphabetical pairs, correct obs count, max/min picked correctly.
- [ ] Weighted metrics weighted by notional; HY%, duration, YTM rounded per template.
- [ ] Constraint/exception booleans computed from the actual post-trade book.
- [ ] Eligibility gates applied (per-bond duration band; candidate; non-watchlist; not already held).
- [ ] Lists in the exact required order and length.
- [ ] Required_value fields echoed literally; no extra keys, no narrative outside JSON.
