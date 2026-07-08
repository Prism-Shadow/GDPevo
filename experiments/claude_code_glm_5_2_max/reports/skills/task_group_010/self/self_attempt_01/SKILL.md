# Asteria Investment Office — Institutional Portfolio-Risk Solver Skill

This skill helps solve portfolio-risk JSON tasks against the shared Asteria Investment
Office environment. The environment is the **current book of record**; local
`input/payloads/` files are intake context that may be stale. Always reconcile to the
environment before answering. Return ONLY a JSON object matching the task's
`answer_template.json` (no narrative outside the JSON).

There are three recurring workflows. Identify yours from the prompt/portfolio id, then
follow the matching SOP. Cross-cutting conventions (precision, ordering, enums,
precedence) apply to all of them.

---

## 0. Environment access

Base URL: `<remote-env-url>` (GET only). Call with `curl` or `python3 urllib`.

Key endpoints and what they return:

| Endpoint | Use |
|---|---|
| `GET /api/catalog` | All ids: portfolios, policies, indices, issuers, bonds, opportunity_sets |
| `GET /api/policies` | ALL policy blocks in one object: `credit_default`, `credit_risk_reduction`, `correlation`, `allocation_mapping`, `multi_asset`, `multi_asset_risk`. Also top-level `as_of_date`. |
| `GET /api/portfolios` | Portfolio summaries |
| `GET /api/portfolios/<portfolio_id>` | Objective, constraints (policy_id), `holdings[]` with `quantity_usd_m`/`instrument_id`/`sleeve`, `market_value_usd_m`, `as_of_date` |
| `GET /api/instruments/bonds` | Full bond universe. Filter `?candidate=true`, `?rating_bucket=HY` |
| `GET /api/issuers` | `sector`, `subsector`, `rating_bucket`, `watchlist` (bool), `credit_outlook`, `research_tags` |
| `GET /api/market/energy` | Energy commodity `signals[]` (score, direction, signal_id) and `pitch_themes` |
| `GET /api/indices` | Index metadata + `level_start_date`/`level_end_date` |
| `GET /api/index-levels` | Dict: `index_id -> [ {date, level}, ... ]` monthly. **No precomputed correlations** — compute yourself. |
| `GET /api/allocation/opportunity-sets` | Taxonomy: `opportunity_set` -> `asset_class` (Equities/Duration/Credit/Currency) + `display_order` |
| `GET /api/allocation/prior-views` | List of prior-quarter view records (see §2C) |
| `GET /api/macro-signals` | List of signal records: `opportunity_set`, `quarter`, `score`, `rationale_code`, `drivers` |

Filter style: append `?<field>=<value>` matching the record field name
(e.g. `?quarter=Q2_2026`, `?candidate=true`, `?rating_bucket=HY`).

### Data-precedence rule (universal)

The environment is authoritative. When a local payload conflicts with the environment,
prefer the environment and set any precedence enum to `current_environment_over_stale_payload`.
Only choose `no_conflict_found` when the payload and environment genuinely agree; never
choose `local_payload_over_current_environment` for live portfolio/mark records. Common
conflicts to check: stale `market_value_usd_m`, stale HY %, stale holding quantities
(worksheet quantities often lag the reconciled service), stale as-of dates, and stale
local "desk notes" that pre-date the latest index levels.

### as_of_date

Use the environment's current `as_of_date` (top of `/api/policies`, also on each
portfolio). It is the portfolio book-of-record date. Do not copy the local packet's
older `request_date`/`memo_as_of_date`/`snapshot_date` into the answer's `as_of_date`.

---

## 1. Workflow A — Energy / fixed-income trade strategy

Tasks: build a bond trade package under credit-risk constraints, then report post-trade
metrics, constraint checks, sales positioning, and a data-precedence verdict. Variants:
(1a) a BUY-only income package funded by a new sleeve allocation; (1b) a SELL+BUY
rotation that reduces HY / watchlist pressure while preserving duration.

### A1. Inputs to fetch

- `GET /api/portfolios/<id>` — holdings (instrument_id, quantity_usd_m), market_value_usd_m, constraints.policy_id.
- `GET /api/policies` — the policy block matching the portfolio's `constraints.policy_id`
  (e.g. `POL_CREDIT_DEFAULT` or `POL_CREDIT_RISK_REDUCTION`).
- `GET /api/instruments/bonds` (+ `?candidate=true`) — bond master: `rating_bucket`
  (IG/HY), `modified_duration_years`, `yield_to_maturity_pct`, `energy_linked`,
  `candidate`, `sector`, `subsector`, `issuer_id`, `recommended_theme_tags`.
- `GET /api/issuers` — `watchlist` bool per issuer (join on `issuer_id`).
- `GET /api/market/energy` (energy tasks) — directional signals + pitch themes.
- The local payload (`desk_request.json` / `risk_meeting_memo.json`) — ticket count,
  notional, allowed actions, candidate shortlist, stale snapshot, preferences. Reconcile
  every quantity/mark to the environment.

### A2. Policy constraints (from `/api/policies` credit blocks)

Both `credit_default` and `credit_risk_reduction` carry: `duration_band_years:[3.0,5.0]`,
`max_hy_allocation_pct:20.0`, `issuer_concentration_limit_pct:12.0`,
`subsector_min_count_for_diversified:2`. `credit_risk_reduction` additionally has
`target_hy_reduction_pct:4.0` (minimum HY reduction in percentage points). Read the
exact numbers from the policy file in the test environment — do not hard-code.

### A3. Candidate filtering (apply in this order)

1. `candidate == true` (the bond is in the opportunity set).
2. `energy_linked == true` for energy-credit tasks (the prompt says "energy-linked").
3. Issuer `watchlist == false` — **drop every watchlist issuer**. Watchlist issuers are
   the ones with `watchlist:true` in `/api/issuers` (typically the refiners, shale/E&P,
   and telecom names flagged with downgrade/refinancing/margin risk).
4. Modified duration within the policy band (e.g. 3.0–5.0). Drop duration-ineligible
   distractors (very short <3.0 or long >5.0) — these are traps, not picks.
5. Honor the desk's stated exposures/preferences and the `recommended_theme_tags`, and
   cross-check with `/api/market/energy` signals: pick bonds whose themes align with
   positive commodity signals (e.g. LNG-export pull, gas-demand, renewables rate-relief),
   avoid bonds whose commodity signal is negative (e.g. watchlisted refiners).

### A4. Diversification checks on the SELECTED package

The `*_diversification_pass` checks apply to the **selected trade package**, not the whole
book (a 2-ticket package cannot repair a whole portfolio's concentration):
- `selected_issuer_diversification_pass`: the selected buys are from >=2 distinct issuers.
- `selected_subsector_diversification_pass`: the selected buys span >=2 distinct
  subsectors (the policy's `subsector_min_count_for_diversified`, normally 2).
So do NOT pick two bonds from the same subsector (e.g. two Natural Gas/LNG names) — pair
complementary subsectors (e.g. LNG + Midstream, or LNG + Renewables).

### A5. Post-trade metric formulas (market-value-weighted)

Let `q_i` = holding quantity (USD m), `dur_i` = modified duration, `ytm_i` = YTM, and
`hy_i` = 1 if bond rating_bucket == HY else 0. After applying the trade package (adds for
BUY, removes for SELL), with post-trade total market value `MV = Σ q_i`:

- `total_market_value_usd_m = MV` (precision 2)
- `hy_allocation_pct = 100 * Σ(q_i * hy_i) / MV` (precision 2)
- `weighted_modified_duration_years = Σ(q_i * dur_i) / MV` (precision 2)
- `weighted_yield_to_maturity_pct = Σ(q_i * ytm_i) / MV` (precision 2)

For a BUY-funded (new allocation) package, post-trade MV = pre-trade MV + sum of BUY
notionals. For a rotation (SELL then reinvest into BUY), post-trade MV = pre-trade MV
(SELL proceeds fund the BUYs). Use the environment's bond master for `dur`/`ytm`/`rating`
(noting duration is "modified duration" in years and YTM is in percent).

### A6. Constraint pass/fail booleans

- `hy_cap_pass`: post-trade `hy_allocation_pct <= max_hy_allocation_pct`.
- `duration_band_pass`: post-trade weighted duration within `[3.0, 5.0]` (inclusive).
- `watchlist_avoidance_pass`: no selected BUY's issuer is on the watchlist (AND, for
  rotation tasks, all watchlist holdings were sold).
- Diversification passes as in A4.
For rotation tasks, the additional booleans are: `target_hy_reduction_met` =
(pre-trade HY% − post-trade HY%) >= `target_hy_reduction_pct`; `watchlist_exposure_cleared`
= post-trade watchlist exposure == 0.

### A7. Sales positioning (BUY-package tasks)

- `target_segment`: pick from the enum to match the client context
  (`multi_asset_income` for a "multi-asset income update"; `insurance_general_account`/
  `pension_liability_matching` for long-duration IG ballast; `endowment_opportunistic`
  for HY carry; `private_bank_income` for carry). The prompt's `client_context` is the
  cue.
- `theme`: pick the enum that best matches the headline selection AND the energy pitch
  theme: `lng_export_tailwind` (LNG exporter headline, LNG-export pull signal),
  `midstream_stability` (midstream fee-based), `transition_bond_selectivity` (renewables
  with rate-relief), `oil_oversupply_caution`, `avoid_watchlist_yield_trap` (the desk
  explicitly flags watchlist sensitivity / stale worksheet highlighted watchlist yield).

### A8. Rotation-specific fields (SELL+BUY tasks)

- `rotation.trades`: list with `action` BUY/SELL, `instrument_id`, `quantity_usd_m`
  (precision 1). **Ordering: SELL before BUY, then instrument_id ascending within each
  action** (note: not the same ordering as the BUY-only package).
- `risk_metrics`: `post_trade_hy_allocation_pct`, `post_trade_duration_years`,
  `hy_reduction_pct_points` (= pre-trade HY% − post-trade HY%, precision 2),
  `post_trade_watchlist_exposure_usd_m` (precision 1).
- `watchlist_handling.watchlist_sell_ids`: instrument ids sold that were watchlisted,
  ascending instrument_id. `buys_avoid_watchlist`: bool (true iff no buy is watchlisted).
- `risk_note_code`: pick the dominant risk theme: `watchlist_concentration` if clearing a
  watchlist name was the driver; `hy_cap_pressure` if HY cap was the binding constraint;
  `duration_preservation` if the package's main job was keeping duration inside the band;
  `carry_tradeoff` if HY carry was sacrificed for IG quality; `no_action` only if no trade.

### A9. Rotation sizing logic

The rotation must satisfy ALL of: clear watchlist (sell every watchlist holding), get
post-trade HY% <= cap, achieve the >= target HY pp reduction, keep duration in band, and
avoid buying watchlist. Because HY pp reduction and the HY cap are both binding, compute
the minimum HY notional to sell = max(0, pre_HY_mv − cap*MV_target, and ensure the pp
reduction threshold). With discrete holdings, sell whole watchlist + enough HY to get
under the cap, then reinvest the proceeds into duration-band-eligible IG candidates from
the shortlist (excluding any watchlisted shortlist name — check the issuer). Favor buys
that preserve carry (acceptable YTM) and keep the blended duration mid-band.

### A10. Common pitfalls (Workflow A)

- Stale worksheet quantities (e.g. a holding shown as 10.0 locally but 12.0 in the
  environment) — always use the environment quantity.
- Picking a high-YTM watchlist bond because it "improves carry" — watchlist avoidance
  overrides carry.
- Two buys from the same subsector (fails subsector diversification) even if both fit
  the desk's LNG preference.
- A duration-ineligible distractor (dur 2.3 or 6.7) that looks attractive on yield.
- Treating a HY cap of 20% as a target rather than a ceiling; or forgetting that the HY
  reduction target is in *percentage points*, not percent of HY.
- Using `notional_usd_m` (precision 1) where the task wants `quantity_usd_m`, or
  forgetting the SELL-before-BUY ordering on rotation trades.

---

## 2. Workflow B — International equity correlation review

Tasks: given an index universe and a level window, compute pairwise Pearson correlations
of monthly simple returns, identify extreme pairs, flag China/Asia concentration, name
diversification candidates, and propose sleeve actions.

### B1. Inputs to fetch

- `GET /api/index-levels` — the dict of monthly levels per index_id.
- `GET /api/policies` -> `correlation` block: `correlation_high_threshold` (0.8),
  `correlation_low_threshold` (0.2), `review_window_start`, `review_window_end`.
- `GET /api/portfolios/<id>` — the sleeve holdings (which sleeves/indices the book holds).
- The local `review_request.json` — `review_window` (level_start_date/level_end_date),
  `index_universe`, and the CIO `memo.concern_codes`.

The policy window and the request window normally coincide
(`2025-05-30` .. `2026-04-30`). Use the request window if it is given; fall back to the
policy window.

### B2. Correlation computation

For each index in the universe:
1. Take the monthly levels with `date` in `[level_start_date, level_end_date]` inclusive,
   sorted ascending. There are normally **12 levels** (one per month-end) yielding **11
   monthly simple returns** `r_t = level_t / level_{t-1} − 1`.
2. Compute **Pearson correlation** of the return series for each unordered pair.
   Use sample statistics (n−1) — but with n identical across series the choice of n vs
   n−1 cancels in the Pearson ratio; just be consistent. `cov/(sx*sy)`.
3. Round each reported correlation to **3 decimals**.

`return_observations` (integer) in the `review_window` object = the number of return
observations (11 for a 12-level window). `level_start_date`/`level_end_date` echo the
window bounds.

### B3. Extreme pairs

- `highest_positive`: the pair with the maximum correlation.
- `lowest`: the pair with the minimum correlation (often negative).
Each `pair_id` is a **list of exactly 2 index ids sorted ascending alphabetically**.
`correlation` rounded to 3 decimals.

### B4. Concentration flags

- `high_threshold_breached`: true if ANY pair correlation >= `correlation_high_threshold`
  (0.8).
- `china_asia_dependence_flag`: true if the China index and/or the Asia-Pacific-ex-Japan
  index correlate >= high threshold with the broad complex (EM, World, ACWI, EAFE) — i.e.
  the portfolio's risk is concentrated in a China/Asia beta cluster.
- `primary_code`:
  - `CHINA_ASIA_DEPENDENCE` when China/Asia high-correlation cluster dominates (concern
    codes like `CHINA_DEDICATED_SLEEVE`, `ASIA_BETA_OVERLAP`).
  - `GLOBAL_DEVELOPED_OVERLAP` when the dominant high-correlation cluster is EAFE/World/
    ACWI (developed overlap) without China/Asia being the headline.
  - `NO_MATERIAL_CONCENTRATION` only if no pair breaches the high threshold.
- The low-correlation diversifier (concern code `LOW_CORRELATION_DIVERSIFIER`) is the
  index whose correlations with the rest are all below the low threshold (often strongly
  negative); Latam typically plays this role.

### B5. Diversification candidates

`diversification_candidates`: list of index ids that reduce concentration, from the
template's allowed values, **sorted ascending alphabetically**. Typically the
EM-ex-China, India, and Latam ids (the non-China EM set that breaks the China/Asia
cluster).

### B6. Sleeve actions

`list[object]` length per template, **ordered ascending by `sleeve` name**. Each row:
`sleeve`, `action` ∈ {trim, add, hold, hedge, monitor, rotate}, `target_index_id`.
Map from the concentration verdict: trim the concentrated sleeve (e.g. China),
add/rotate into the diversifier(s) (e.g. Latam, EM-ex-China). Typical 2-row set:
trim China (target IDX_CHINA) + add the low-correlation diversifier (target IDX_LATAM).

### B7. Pitfalls (Workflow B)

- Using price *levels* instead of *returns* for correlation.
- Forgetting to sort pair ids alphabetically.
- Reporting `return_observations` as the number of levels (12) instead of returns (11).
- Pre-computing correlations from a stale local worksheet that "did not include the final
  month's level" — recompute from `/api/index-levels`.
- Mis-reading the high threshold as 0.9 or low as 0.0 — read them from the policy block.

---

## 3. Workflow C — Cross-asset active allocation view updates

Tasks: produce per-opportunity-set active views (UW/N/OW) with change vs prior,
conviction, rationale code; plus a portfolio-level risk overlay and lineage. A combined
variant (PF-MA-HELIO) also bundles a small correlation summary + sleeve actions +
rebalance trigger + concentration flag + next step.

### C1. Inputs to fetch

- `GET /api/allocation/opportunity-sets` — maps each `opportunity_set` to an
  `asset_class` (Equities / Duration / Credit / Currency) and `display_order`.
- `GET /api/allocation/prior-views` — the prior-quarter view records.
- `GET /api/macro-signals` — current signal `score` + `rationale_code` per
  opportunity_set, per `quarter`.
- `GET /api/policies` -> `allocation_mapping` block (view + conviction thresholds), and
  the governing multi-asset policy block.
- The local `allocation_request.json` / `committee_request.json` — `focus_opportunity_sets`
  (the rows requested, **in the order rows must be emitted**), `target_quarter`,
  `prior_quarter`, `policy_id` hints.

### C2. Selecting the right records

- **Macro signals**: filter `/api/macro-signals` to records whose `quarter` ==
  `target_quarter`. Use that quarter's `score` and `rationale_code` for each requested
  opportunity set.
- **Prior view**: from `/api/allocation/prior-views`, pick the records whose
  `previous_quarter` == the task's `prior_quarter`. (Each prior-views record carries both
  `quarter` (the target it was the prior for) and `previous_quarter` (the stance's
  quarter); match on `previous_quarter` == `prior_quarter`. The record's `view`
  (UW/N/OW) is the prior view.) The prior `conviction` is NOT reused — only the prior
  view, to compute change.
- Sanity check: the prior views should NOT already equal what the current-quarter macro
  signals imply (if they did, you'd be transcribing not refreshing). If they match, you
  likely selected the wrong quarter's signals.

### C3. View, conviction, change from the allocation-mapping policy

From `/api/policies` `allocation_mapping`:
- `view_score_thresholds`: `OW_min` (0.35), `UW_max` (−0.35), `neutral_between`
  [−0.35, 0.35].
- `conviction_thresholds`: `HIGH_abs_min` (0.7), `MEDIUM_abs_min` (0.35),
  `LOW_abs_below` (0.35).
- `view_rank`: OW=1, N=0, UW=−1.

Derivation (use the macro signal `score` `s`):
- `view`: `OW` if `s >= OW_min`; `UW` if `s <= UW_max`; else `N`.
- `conviction`: `HIGH` if `|s| >= HIGH_abs_min`; `MEDIUM` if `MEDIUM_abs_min <= |s| <
  HIGH_abs_min`; `LOW` if `|s| < LOW_abs_below`.
- `rationale_code`: copy the macro-signal record's `rationale_code` (must be one of the
  template's allowed enum values).
- `change` vs prior view (compare **view ranks**, not scores):
  `UP` if `rank(new) > rank(prior)`; `DOWN` if `rank(new) < rank(prior)`;
  `UNCHANGED` if equal.
- `asset_class`: from `/api/allocation/opportunity-sets` for that opportunity_set
  (Equities / Duration / Credit / Currency).

Boundary rule: at exactly ±0.35 the view flips to OW/UW and conviction is MEDIUM (not
LOW). Read the exact thresholds from the policy file in the test environment.

### C4. Row ordering

- Allocation-views list: **sort rows in the request payload's `focus_opportunity_sets`
  order** (the order the CIO listed them), not alphabetical and not display_order.
- Output exactly the requested number of rows (e.g. 8). One row per requested
  opportunity set.
- For the combined committee variant: `target_sleeve_actions` and `allocation_views` are
  emitted in the template's stated `item_order` (e.g. Emerging Markets, India, Latin
  America, USD).

### C5. Risk overlay

`risk_overlay` (allocation-only tasks): `overlay_code`, `primary_action`,
`rationale_codes[]`.
- Derive `overlay_code` from the cluster of view directions + rationale codes:
  - `CREDIT_RISK_REDUCTION` / `trim_credit_beta` when Corporate HY is UW on
    `HY_VALUATION_RISK` (credit beta to cut).
  - `DURATION_QUALITY_TILT` / `tilt_to_duration_quality` when U.S. Treasuries (or core
    duration) is OW on `DURATION_SUPPORT` / `RATE_CUT_SUPPORT` (rotate into duration
    quality).
  - `CURRENCY_DEFENSIVE_HEDGE` / `add_currency_hedge` when a safe-haven currency is OW
    / risk currency UW on `DOLLAR_DEFENSIVE`.
  - `EQUITY_BETA_EXTENSION` / `add_cyclical_equity_beta` when cyclical equities are OW on
    `GROWTH_IMPROVES`/`EUROPE_RECOVERY`.
  - `NO_OVERLAY` / `hold_policy_weights` only if views are broadly neutral.
- `rationale_codes[]`: the rationale codes driving the overlay, in **business-priority
  order, highest priority first** (strongest signal / most actionable risk first; e.g.
  lead with the binding risk like `HY_VALUATION_RISK`, then `DURATION_SUPPORT`,
  `RATE_CUT_SUPPORT`). Each must be from the allowed enum; do not duplicate.

### C6. Combined committee variant fields (PF-MA-HELIO style)

- `policy_id`: the governing multi-asset policy id (e.g. `POL_MULTI_ASSET_DEFAULT` for a
  balanced multi-asset model; `POL_MULTI_ASSET_RISK` if the prompt stresses risk-overlay/
  escalation). The portfolio's `constraints.policy_id` is the source of truth.
- `correlation_summary`: length-2 list `[highest_concentration, best_diversifier]`. Each
  item: `pair_role`, `pair` (2 index ids **sorted alphabetically**), `correlation`
  (Pearson of monthly simple returns over the level window, **3 decimals**) — compute
  exactly as in Workflow B but for the request's `correlation_review.index_ids` subset.
- `target_sleeve_actions`: one row per item in the template's `item_order`, each with
  `opportunity_set` + `action`. Map from the new views + correlation verdict:
  UW/trim the concentrated sleeve, OW/add the diversifier, unchanged-OW/hold the
  strong offset, downgrade/trim or hedge the stale-defensive currency.
- `allocation_views`: one row per item in `item_order`, each with `opportunity_set`,
  `prior_view` (from prior-views), `signal_score` (the macro signal score, **3
  decimals**), `view`, `change`, `conviction`, `rationale_code` — derived as in C3.
- `rebalance_trigger`: `correlation_cap_breach` if any reviewed pair >= the correlation
  high threshold; else `hy_cap_pressure` / `duration_drift` / `watchlist_concentration`
  if those pressures are present in the book; else `committee_review`.
- `portfolio_risk_concentration_flag`: true if a correlation cap is breached OR a China/
  Asia dependence concentration is present.
- `next_step`: pick from `approve_rotation`, `approve_with_monitoring`,
  `defer_pending_risk_review`, `reject_constraint_breach`. The
  `multi_asset_risk.committee_escalation_threshold` ("two_or_more_material_exceptions")
  governs: with two or more material exceptions (e.g. correlation breach + a constraint
  breach) -> `defer_pending_risk_review`; a single contained exception with a clear
  remediation -> `approve_with_monitoring`; a clean rotation plan -> `approve_rotation`;
  an unfixable breach -> `reject_constraint_breach`.

### C7. Lineage fields

- `as_of_date`: environment `as_of_date`.
- `target_quarter` / `prior_quarter`: from the request (required values in the template).
- `policy_id`: the governing policy id (see C6).
- `task_id`: the template's required value (e.g. `train_003`) — echo it verbatim.

### C8. Pitfalls (Workflow C)

- Using the wrong quarter's macro signals (Q3 signals for a Q2 target). Match `quarter`
  == `target_quarter` exactly.
- Matching prior-views on `quarter` instead of `previous_quarter` — that gives the
  already-decided view and makes `change` meaningless.
- Computing `change` from score deltas instead of view-rank deltas (a score that moves
  within the same band is UNCHANGED).
- Emitting rows alphabetically instead of in the request's `focus_opportunity_sets`
  order.
- Leaving `signal_score` unrounded (3 decimals) or rounding it to 2.
- Forgetting `prior_view` in the combined-variant rows, or reusing the prior conviction
  as the new conviction (conviction comes from the current signal score).
- Trusting a stale local "desk note" that keeps an old overweight (e.g. USD OW) — refresh
  from current signals; the downgrade is the point of the refresh.

---

## 4. Cross-cutting output conventions

- **Precision**: obey each field's `precision` in `answer_template.json`. Common values:
  `notional_usd_m` / `quantity_usd_m` = 1 decimal; `post_trade_metrics` /
  `risk_metrics` percentages/durations = 2 decimals; correlations = 3 decimals;
  `signal_score` = 3 decimals. Round (not truncate) at the end.
- **Ordering**: `trade_package` (BUY-only) sorted **ascending by instrument_id**;
  `rotation.trades` sorted **SELL before BUY, then instrument_id ascending** within each
  action; pair ids and index lists **ascending alphabetical**; sleeve_actions **ascending
  by sleeve**; allocation rows in **request payload order**; rationale_codes in
  **business-priority order**.
- **Enums**: every enum field MUST be exactly one of the template's `allowed_values`
  (case-sensitive). Do not invent values.
- **Required values**: fields with `required_value` (portfolio_id, task_id,
  target_quarter, review_quarter, policy_id-where-fixed) must echo exactly.
- **Booleans**: pass/fail and flag fields are real JSON booleans, not strings.
- **JSON only**: emit a single JSON object. No prose, no markdown fences, no trailing
  commas, no comments.

---

## 5. Universal execution checklist

1. Read `prompt.txt`, `answer_template.json`, and the local payload fully; note the
   required top-level keys, required values, enums, precision, and ordering rules.
2. Identify the workflow (A trade strategy / B correlation review / C allocation views,
   possibly the combined C+B committee variant).
3. Fetch `/api/policies` first (gives as_of_date + all thresholds), then the portfolio,
   then the workflow-specific endpoints. Cache responses to reuse across calculations.
4. Reconcile every local quantity/mark/window to the environment; record the precedence
   verdict where required.
5. Compute with the environment's numbers; round only when emitting.
6. Validate: every required key present, every enum legal, every ordering satisfied,
   every boolean reflecting the actual computed constraint, precision correct.
7. Emit only the JSON object.
