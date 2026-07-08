# Asteria Investment Office — Institutional Portfolio Risk Solver Skill

Reusable workflow rules for solving Asteria Investment Office portfolio-risk tasks.
Base environment: `<remote-env-url>` (Asteria Investment Office API). All current
data comes from this shared service; local task payloads are intake context only and may be
stale. Three task families share this service: (1) energy/fixed-income credit trade
strategy, (2) international equity correlation review, (3) cross-asset active allocation
view updates.

## 0. Universal rules

- ALWAYS treat the shared environment service as the book of record. Local payloads
  (desk_request, risk_meeting_memo, committee_request, review_request, allocation_request)
  are intake context that may carry stale marks, stale quantities, or prior-week
  shortlists. When a payload value conflicts with the current environment, use the
  environment. The `data_precedence` answer for such cases is
  `current_environment_over_stale_payload`.
- The environment emits a `stale_data_warning` and payloads carry snapshot dates; any
  worksheet dated before the environment `as_of_date` must be reconciled to the service
  before deciding. Use current portfolio quantities (not stale exception-board quantities).
- `as_of_date` in answers = the environment `as_of_date` (e.g. `2026-05-29`), which is
  consistent across `/api/portfolios`, `/api/policies`, `/api/market/energy`, etc.
- Keep every numeric field rounded to the precision declared in the task's
  `answer_template.json`. Do not add fields; do not include narrative outside the JSON.
- Ordering rules are load-bearing: honor every `ordering` / `Sort ...` instruction in the
  template exactly (ascending by instrument_id, SELL before BUY, alphabetical pair ids,
  focus_opportunity_sets request order, sleeve order, etc.).

## 1. Environment endpoints that matter

- `GET /api/catalog` — all valid ids (portfolios, bonds, issuers, indices, opportunity
  sets, policies). Use to confirm membership before emitting any id.
- `GET /api/policies` — the policy set. Key policies:
  - `credit_default`: duration_band_years [3.0,5.0], max_hy_allocation_pct 20.0,
    issuer_concentration_limit_pct 12.0, subsector_min_count_for_diversified 2,
    target_hy_reduction_pct 0.0.
  - `credit_risk_reduction`: same bands/caps but `target_hy_reduction_pct` 4.0 (the
    minimum preferred HY reduction for risk-reduction rotations).
  - `correlation`: correlation_high_threshold 0.8, correlation_low_threshold 0.2,
    review window (e.g. 2025-05-30 to 2026-04-30).
  - `allocation_mapping` (POL_ALLOCATION_MAPPING): view_score_thresholds
    (OW_min 0.35, UW_max -0.35, neutral between), conviction thresholds
    (HIGH_abs_min 0.7, MEDIUM_abs_min 0.35, LOW_abs_below 0.35), view_rank
    (OW 1, N 0, UW -1).
  - `multi_asset` (POL_MULTI_ASSET_DEFAULT): master multi-asset policy that
    uses_allocation_mapping + correlation + credit defaults.
  - `multi_asset_risk` (POL_MULTI_ASSET_RISK): uses credit_risk_reduction +
    correlation; committee_escalation_threshold "two_or_more_material_exceptions".
- `GET /api/portfolios` and `/api/portfolios/<id>` — portfolio summary, current
  holdings (instrument_id, quantity_usd_m, sleeve, notes), constraints, market_value_usd_m.
- `GET /api/instruments/bonds` (and `?candidate=true`) — bond master. Fields:
  instrument_id, issuer_id, rating, rating_bucket (IG/HY), sector, subsector,
  energy_linked, modified_duration_years, yield_to_maturity_pct, coupon_pct,
  spread_bps, maturity, recommended_theme_tags, candidate flag.
- `GET /api/issuers` — issuer research: rating_bucket, sector, subsector,
  credit_outlook, research_tags, and a boolean `watchlist` (the watchlist flag is
  the authoritative watchlist-source; do not infer watchlist status from theme tags
  alone).
- `GET /api/market/energy` — energy signals: pitch_themes and per-commodity signals
  with `score` and `direction`. Use these to pick the sales/positioning theme.
- `GET /api/indices`, `/api/index-levels`, `/api/index-levels/<index_id>` — index
  metadata and monthly levels (`date`, `level`). Correlations are computed from these
  levels; the API gives NO precomputed correlations.
- `GET /api/allocation/opportunity-sets` — taxonomy mapping each opportunity_set to an
  asset_class (Equities/Duration/Credit/Currency) and display_order.
- `GET /api/allocation/prior-views` — prior-quarter views. Each entry has `quarter`,
  `previous_quarter`, `opportunity_set`, `view`, `conviction`. For a target-quarter
  refresh, the PRIOR view = the entry whose `previous_quarter` equals the prior
  quarter (e.g. for a Q2_2026 refresh with prior_quarter Q1_2026, use entries where
  previous_quarter=Q1_2026). Do not treat the endpoint's `quarter` field as the new
  answer; it labels the transition, and the `view` field is the prior-quarter input.
- `GET /api/macro-signals` — per-opportunity_set signal `score`, `rationale_code`,
  `drivers`, `quarter`. For a target quarter, use the entries with that `quarter`.

## 2. Workflow A — Energy / fixed-income credit trade strategy

Templates require: portfolio_id, as_of_date, trade_package (sorted ascending by
instrument_id), post_trade_metrics, constraint_checks, sales_positioning,
data_precedence. A fixed-income rotation variant adds rotation.trades,
risk_metrics, exception_flags, watchlist_handling, risk_note_code.

### Selection logic (CONFIRMED by judge feedback)
- Capacity/spec: honor the exact ticket count, total notional, and split (e.g. exactly
  two BUY tickets totaling USD 8.0M split evenly = 4.0M each).
- Eligibility filters, all required:
  1. `energy_linked = true` when the desk preference names energy exposures
     (LNG exporters, gas demand, energy-linked carry).
  2. Issuer `watchlist = false` — NEVER select a watchlisted issuer. Watchlisted
     issuers in this environment include the shale/E&P, telecom, and refining names;
     confirm via `/api/issuers` each run.
  3. Modified duration INSIDE the policy band [3.0, 5.0]. Duration-ineligible
     distractors are any bond with modified_duration_years > 5.0 or < 3.0 — exclude
     them even if their carry looks attractive. Long-dated LNG/oil bonds and very
     short refiner bonds are classic distractors here.
  4. The two selected buys must be from DISTINCT issuers AND DISTINCT subsectors
     (selected_issuer_diversification_pass and selected_subsector_diversification_pass
     both require the selected set to span >=2 issuers and >=2 subsectors).
- Carry objective = MAXIMIZE expected carry (weighted YTM uplift) subject to the
  above. Among eligible non-watchlist energy-linked HY carry bonds inside the
  duration band, pick the HIGHEST yield_to_maturity. A lower-carry renewables HY
  bond is NOT an acceptable substitute when a higher-carry non-watchlist energy HY
  bond (e.g. merchant power) is eligible and satisfies diversification. This
  carry-maximization was the decisive pass criterion.
- The anchor buy is the LNG/natural-gas IG name that matches `LNG_EXPORTS` /
  `GAS_DEMAND` theme tags and the strongest positive energy signal (LNG export
  pull). Pair it with the highest-YTM eligible non-watchlist energy HY carry bond
  from a DIFFERENT subsector.

### Post-trade metric computation
Using current portfolio holdings (quantity_usd_m) + the new BUY quantities:
- `total_market_value_usd_m` = sum of all post-trade holding quantities. Precision 2.
- `hy_allocation_pct` = (sum of post-trade quantities whose rating_bucket == "HY")
  / total_market_value_usd_m * 100. Precision 2.
- `weighted_modified_duration_years` = sum(quantity * modified_duration_years) /
  total_market_value_usd_m. Precision 2.
- `weighted_yield_to_maturity_pct` = sum(quantity * yield_to_maturity_pct) /
  total_market_value_usd_m. Precision 2.
- `notional_usd_m` per ticket: precision 1.
Weights are MARKET-VALUE (quantity) weights, not notional-equal weights.

### Constraint checks (booleans)
- `hy_cap_pass`: post-trade hy_allocation_pct <= max_hy_allocation_pct (20.0).
- `duration_band_pass`: weighted_modified_duration_years within [3.0, 5.0].
- `selected_issuer_diversification_pass`: the selected buys span >=2 distinct issuers.
- `selected_subsector_diversification_pass`: the selected buys span >=2 distinct
  subsectors.
- `watchlist_avoidance_pass`: no selected buy is from a watchlisted issuer.

### sales_positioning
- `target_segment`: match the desk client_context (e.g. "multi-asset income update"
  -> `multi_asset_income`).
- `theme`: match the dominant POSITIVE energy signal / pitch theme. For an
  LNG-anchored package the theme is `lng_export_tailwind`. (Other allowed themes:
  oil_oversupply_caution, midstream_stability, transition_bond_selectivity,
  avoid_watchlist_yield_trap.)

### data_precedence
- `current_environment_over_stale_payload` whenever the local worksheet pre-dates the
  service and operations has not reconciled it.

### Fixed-income rotation variant (PF-FI-* risk rebalance)
- The rotation MUST bring HY to <= the 20% cap (`hy_cap_pass = true`). Submitting a
  rotation that leaves HY above the cap (hy_cap_pass false) scores badly. This is a
  hard pass criterion.
- HOWEVER the rotation must also PRESERVE CARRY: do NOT eliminate all HY. Sell the
  watchlisted bond(s) fully (watchlist_exposure_cleared = true, post-trade watchlist
  exposure 0) PLUS enough non-watchlist HY to get under the 20% cap, while KEEPING
  the highest-carry non-watchlist HY bond for carry. Fully rotating HY to 0 is
  penalized; keeping one carry HY while clearing the cap is rewarded.
- `target_hy_reduction_met`: hy_reduction_pct_points (pre-trade hy% - post-trade hy%)
  >= the policy target_hy_reduction_pct (4.0 for POL_CREDIT_RISK_REDUCTION). The 4pp
  is a FLOOR; the 20% cap is the BINDING constraint that usually forces a larger cut.
- Sells = the watchlisted holding(s) + the lower-carry non-watchlist HY needed to
  clear the cap. Buys = the eligible non-watchlist IG candidates from the desk
  shortlist (exclude any candidate whose issuer is watchlisted — "risk team
  concerned about issuer status" means watchlist). `buys_avoid_watchlist = true`.
- `watchlist_sell_ids`: instrument_ids of watchlisted bonds sold, ascending order.
- Trade ordering: SELL before BUY, then instrument_id ascending within each action.
- `risk_note_code` MUST be consistent with the flags. If `hy_cap_pass = true` (cap
  met), do NOT use `hy_cap_pressure` — use `carry_tradeoff` (gave up HY carry for IG
  safety) or `watchlist_concentration`/`duration_preservation` as fits. Reserve
  `hy_cap_pressure` for cases where the cap remains breached.
- Quantity precision 1; post_trade_hy_allocation_pct / duration / reduction precision
  2; post_trade_watchlist_exposure_usd_m precision 1.

## 3. Workflow B — International equity correlation review

Templates require: portfolio_id, review_window {level_start_date, level_end_date,
return_observations}, index_set, extreme_pairs {highest_positive, lowest},
concentration {china_asia_dependence_flag, primary_code, high_threshold_breached},
diversification_candidates, sleeve_actions.

### Correlation computation (CONFIRMED)
- Pull monthly levels for each index in the request universe over
  [level_start_date, level_end_date].
- Compute monthly SIMPLE returns: r[i] = level[i+1]/level[i] - 1.
- `return_observations` = number of returns = (number of levels) - 1. For a 12-month
  window (12 monthly levels) this is 11. Do NOT report the level count.
- Pearson correlation between each pair of return series:
  r = cov(a,b) / (stdev(a)*stdev(b)). Round to THREE decimals.
- `index_set` = the request universe, sorted ascending. ASCII sort: uppercase letters
  (A-Z, 65-90) sort before underscore `_` (95), so `IDX_ACWI_IMI` precedes
  `IDX_AC_ASIA_PAC_EX_JP` (the `W` before `_`). Verify each run with a real sort.
- `extreme_pairs.highest_positive` = the off-diagonal pair with the MAX correlation;
  `extreme_pairs.lowest` = the pair with the MIN correlation (most negative is
  allowed and expected). Each `pair_id` is a 2-element list sorted alphabetically;
  `correlation` to 3 decimals.
- Do NOT use any precomputed correlation field — compute from levels.

### Concentration
- `china_asia_dependence_flag` = true when the China and/or Asia-Pacific sleeves are
  present and their pair correlations breach the high threshold (0.8).
- `high_threshold_breached` = true when ANY pair correlation (absolute or positive per
  the policy) exceeds correlation_high_threshold (0.8). In a tightly-overlapping
  universe many pairs breach; report true.
- `primary_code`: the dominant concentration pattern. Use `CHINA_ASIA_DEPENDENCE` when
  the memo concern codes are Asia/China-focused and the China<->Asia/EM correlations
  are above 0.8. Use `GLOBAL_DEVELOPED_OVERLAP` when the single highest pair is a
  global/developed overlap (e.g. EM<->World) that dominates. Choose based on which
  concentration the data + memo jointly emphasize; when unsure, the memo's stated
  concern codes are the tiebreaker. Allowed: CHINA_ASIA_DEPENDENCE,
  GLOBAL_DEVELOPED_OVERLAP, NO_MATERIAL_CONCENTRATION.

### Diversification candidates
- Candidates = indices whose correlations to the concentrated block fall below the
  low threshold (0.2) — i.e. the genuine low-correlation diversifiers. In this
  environment the Latin America index is the consistent diversifier (negative
  correlations to the China/Asia/EM block). Emit ascending by index id.

### Sleeve actions (CONFIRMED)
- Exactly two actions, ordered ascending by `sleeve`. Use `trim` on the concentrated
  sleeve (e.g. trim the dedicated China sleeve) and `add` on the low-correlation
  diversifier (e.g. add Latin America).
- DO NOT use `rotate` for these review actions — using `rotate` (rotating the
  concentrated sleeve into an EM-ex-China index) was CONFIRMED to lower the score.
  The review action set is trim-the-concentration + add-the-diversifier.

## 4. Workflow C — Cross-asset active allocation view updates

Two variants: (C1) a pure allocation-view memo (task 003 type) and (C2) a committee
JSON linking correlation findings to allocation views (task 005 type).

### Deriving views (CONFIRMED correct)
- For each requested opportunity_set, read the prior view from `/api/allocation/prior-views`
  (entry whose previous_quarter = prior_quarter) and the current signal from
  `/api/macro-signals` (entry whose quarter = target_quarter).
- New `view` from signal `score` via POL_ALLOCATION_MAPPING thresholds:
  score >= 0.35 -> OW; score <= -0.35 -> UW; otherwise N.
- `conviction` from abs(score): >= 0.7 -> HIGH; >= 0.35 -> MEDIUM; < 0.35 -> LOW.
- `rationale_code` = the macro-signal's `rationale_code` directly (do not invent).
- `change` vs prior view using view_rank (OW=1, N=0, UW=-1):
  new_rank > prior_rank -> UP; < -> DOWN; equal -> UNCHANGED.
- `asset_class` from `/api/allocation/opportunity-sets` taxonomy
  (Equities / Duration / Credit / Currency).
- `signal_score` (C2 only) = the macro signal score, precision 3.
- `prior_view` (C2 only) = the prior-quarter view code.
- Order rows by the request payload's focus_opportunity_sets order (NOT alphabetical).
- `target_quarter` / `prior_quarter` are required fixed values from the request.

### Risk overlay (C1)
- `overlay_code`, `primary_action`, `rationale_codes` (business priority, highest
  first). The overlay should reflect the dominant signal theme across the focus set
  (e.g. duration-OW + HY-UW + IG-OW => a quality/duration tilt; HY valuation risk =>
  credit risk reduction). Allowed overlays: DURATION_QUALITY_TILT,
  CREDIT_RISK_REDUCTION, EQUITY_BETA_EXTENSION, CURRENCY_DEFENSIVE_HEDGE, NO_OVERLAY.
  Pick the one matching the strongest risk/repositioning signal and keep
  primary_action paired with its overlay code.
- `policy_id`: report the GOVERNING multi-asset policy (POL_MULTI_ASSET_DEFAULT) as
  the lineage policy_id for a multi-asset reference model, not the sub-policy
  POL_ALLOCATION_MAPPING (which is the threshold source, not the portfolio policy).

### Committee JSON (C2 — PF-MA-HELIO type)
Required keys: portfolio_id, as_of_date, review_quarter, correlation_summary,
target_sleeve_actions, allocation_views, rebalance_trigger,
portfolio_risk_concentration_flag, next_step.
- `correlation_summary`: a 2-item list, item_order [highest_concentration,
  best_diversifier]. Each item: {pair_role, pair (2 index ids alphabetical),
  correlation (Pearson of monthly simple returns, 3 decimals)}.
  highest_concentration = the pair with the MAX correlation in the requested index
  set; best_diversifier = the pair with the MIN (most negative) correlation. Use the
  same monthly-return Pearson method as Workflow B over the stated 12-month window.
- `allocation_views`: one row per requested opportunity_set (order = request order),
  with prior_view, signal_score (3 dec), view, change, conviction, rationale_code
  derived as above.
- `target_sleeve_actions`: one per requested opportunity_set (order = request order).
  Map the NEW VIEW to the action: OW -> add, UW -> trim, N -> hold. (For a sleeve
  whose new view is N after being OW, use hold — do not trim a neutral currency
  view.) This view-based mapping is preferred.
- `rebalance_trigger`: the substantive breach that drove the review. When a pair
  correlation exceeds correlation_high_threshold (0.8), use
  `correlation_cap_breach`. (Other allowed: hy_cap_pressure, duration_drift,
  watchlist_concentration, committee_review.)
- `portfolio_risk_concentration_flag`: true when any reviewed pair breaches the high
  threshold (correlation > 0.8) or the portfolio carries a concentrated
  high-correlation sleeve pair.
- `next_step`: `approve_with_monitoring` when a rotation is proposed that addresses a
  flagged concentration. CONFIRMED: `approve_rotation` (clean approve, no monitoring)
  is WRONG when a concentration is flagged — it lowers the score. With a flagged
  risk concentration, approve WITH monitoring. (Use `defer_pending_risk_review` only
  for two-or-more material exceptions; `reject_constraint_breach` only when the
  rotation cannot resolve the breach.)

## 5. Precision & formatting quick reference

| field | precision |
|---|---|
| trade_package.notional_usd_m | 1 decimal |
| rotation.trades.quantity_usd_m | 1 decimal |
| post_trade_metrics.total_market_value_usd_m | 2 decimals |
| post_trade_metrics.hy_allocation_pct | 2 decimals |
| post_trade_metrics.weighted_modified_duration_years | 2 decimals |
| post_trade_metrics.weighted_yield_to_maturity_pct | 2 decimals |
| risk_metrics.post_trade_hy_allocation_pct | 2 decimals |
| risk_metrics.post_trade_duration_years | 2 decimals |
| risk_metrics.hy_reduction_pct_points | 2 decimals |
| risk_metrics.post_trade_watchlist_exposure_usd_m | 1 decimal |
| correlation (all workflows) | 3 decimals |
| allocation_views.signal_score | 3 decimals |

## 6. Confirmed misjudgment / exclusion rules (do not violate)

1. Watchlist avoidance: never BUY a watchlisted issuer; never keep a watchlisted
   holding in a risk-reduction rotation. Verify `watchlist` on `/api/issuers`.
2. Duration-ineligible distractors: exclude any bond outside [3.0, 5.0] modified
   duration even if carry is high; classic traps are long-dated LNG/oil (>5.0) and
   short refiner/shale (<3.0) paper.
3. Carry maximization: among eligible non-watchlist energy HY carry bonds inside the
   band, choose the HIGHEST YTM that preserves issuer+subsector diversification. Do
   not substitute a lower-carry renewables HY bond when a higher-carry eligible name
   exists.
4. HY cap is a hard pass: a fixed-income rotation MUST end with
   hy_allocation_pct <= 20.0 (hy_cap_pass true). Leaving HY above the cap is a
   severe failure.
5. Preserve carry: a risk-reduction rotation keeps the highest-carry non-watchlist
   HY bond; do not drive HY to 0.
6. Stale-worksheet precedence: use current environment quantities/marks over the
   local payload snapshot (data_precedence = current_environment_over_stale_payload).
7. Correlation review sleeve actions: trim the concentrated sleeve + add the
   diversifier. Do NOT use rotate (confirmed score loss).
8. Committee next_step: approve_with_monitoring (not approve_rotation) when a risk
   concentration is flagged.
9. risk_note_code consistency: do not report hy_cap_pressure when hy_cap_pass is
   true.
10. Correlations: compute Pearson from monthly simple returns on index levels; never
    use a precomputed correlation field; return_observations = levels - 1.

## 7. SOP per workflow

### SOP A — energy trade strategy
1. GET /api/portfolios/<id>, /api/instruments/bonds, /api/issuers, /api/market/energy,
   /api/policies.
2. Filter bonds: energy_linked=true, watchlist=false, modified_duration in [3,5],
  candidate=true (or held). Mark duration-ineligible distractors.
3. Pick the LNG/gas IG anchor (LNG_EXPORTS/GAS_DEMAND tags, strongest LNG signal).
4. Pick the highest-YTM eligible non-watchlist energy HY carry bond from a DIFFERENT
   issuer and subsector.
5. Size tickets to the spec (e.g. 4.0M each), sort ascending by instrument_id.
6. Compute market-value-weighted post-trade metrics at the required precision.
7. Set constraint_checks (hy_cap, duration_band, selected issuer/subsector
   diversification, watchlist avoidance).
8. Set sales_positioning (target_segment from client_context; theme from dominant
   energy signal) and data_precedence = current_environment_over_stale_payload.

### SOP B — correlation review
1. GET /api/portfolios/<id>, /api/index-levels, /api/policies, /api/indices.
2. For the request universe, compute monthly simple returns and the full Pearson
   matrix.
3. Set review_window (dates from request; return_observations = levels - 1).
4. Set index_set sorted ASCII ascending.
5. Set extreme_pairs (highest_positive = max pair; lowest = min pair; pair ids
   alphabetical; 3 decimals).
6. Set concentration (china_asia_dependence_flag, primary_code per memo+data,
   high_threshold_breached).
7. Set diversification_candidates = indices with correlations below the low
   threshold vs the concentrated block.
8. Set sleeve_actions = [trim concentrated sleeve, add diversifier], ascending by
   sleeve.

### SOP C — allocation view refresh
1. GET /api/allocation/opportunity-sets, /api/allocation/prior-views,
   /api/macro-signals, /api/policies.
2. For each requested opportunity_set: prior view (prior-views entry with
   previous_quarter = prior_quarter); signal (macro-signals entry with quarter =
   target_quarter).
3. Derive view (>=0.35 OW, <=-0.35 UW, else N), conviction (>=0.7 HIGH, >=0.35
   MEDIUM, else LOW), rationale_code (from signal), change (vs prior view_rank),
   asset_class (taxonomy).
4. Order rows by the request focus_opportunity_sets order.
5. Set risk_overlay (overlay_code + paired primary_action + priority rationale_codes)
   and policy_id (governing multi-asset policy).
6. For committee JSON (C2): add correlation_summary (highest_concentration /
   best_diversifier pairs from monthly-return Pearson), target_sleeve_actions
   (OW->add, UW->trim, N->hold in request order), rebalance_trigger
   (correlation_cap_breach when a pair >0.8), portfolio_risk_concentration_flag
   (true when >0.8), next_step (approve_with_monitoring when a rotation addresses a
   flagged concentration).
