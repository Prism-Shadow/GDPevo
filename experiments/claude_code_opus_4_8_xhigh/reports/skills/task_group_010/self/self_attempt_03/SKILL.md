---
name: asteria-investment-office-json
description: >
  Executable workflow for the Asteria Investment Office task family. Covers five
  archetypes (energy-credit trade package, international equity correlation review,
  active allocation view refresh, fixed-income risk rebalance, multi-asset committee
  decision). Documents which HTTP endpoints supply which fields, the exact
  computation recipes (Pearson correlation, weighted modified duration, HY %, carry/
  YTM, issuer & subsector diversification), the policy thresholds in /api/policies,
  and the output-schema conventions (field names, enum value sets, rounding,
  id ordering). The remote environment is always the book of record.
---

# Asteria Investment Office — JSON answer workflow

You produce a single JSON object that conforms to the task's
`input/payloads/answer_template.json`. The shared environment is a read-only HTTP
API and the **current book of record**. Local payloads are intake context only and
may be stale; when they disagree with the environment, **the environment wins**.

Base URL: `<remote-env-url>` (see `environment_access.md`). Use
`curl` for HTTP and `python` (NOT `python3`) for math. Save fetched JSON inside your
own working directory.

## 0. Universal SOP (do this for every task)

1. **Read the prompt + every payload + the answer_template first.** The template is
   the contract: it dictates required keys, enum value sets, rounding precision,
   list lengths, and ordering. Mirror it exactly. Extra or missing top-level keys,
   wrong enum spelling, or wrong ordering are failures.
2. **Pull the live data** you need from the endpoints below — never trust a stale
   mark, weight, watchlist flag, view, or duration from the local payload. Recompute
   everything from the environment.
3. **Identify the governing policy.** Each portfolio summary / detail carries a
   `constraint_policy_id`. Resolve thresholds from `/api/policies` (see §1). Do not
   hardcode numbers from memory; read them.
4. **Compute, then cross-check internal consistency** (e.g. sum of holding
   quantities equals stated market value; HY% is HY market value / total market
   value; correlation observation count = number of monthly levels − 1).
5. **Emit JSON only** (no prose) when the prompt says so. Round each numeric field
   to the precision the template declares. Apply the exact ordering rules.
6. **Set any data-precedence / lineage field** to reflect that the current
   environment overrode the stale payload when (and only when) a real conflict
   exists; otherwise use the "no conflict" value.

### Key endpoints and what they authoritatively provide
- `GET /api/catalog` — valid ids for portfolios, policies, indices, issuers, bonds,
  opportunity sets. Use to sanity-check id spelling.
- `GET /api/policies` — all thresholds (correlation, allocation mapping, credit
  bands, HY caps, issuer concentration, target HY reduction) plus `as_of_date`.
- `GET /api/portfolios` and `/api/portfolios/<id>` — `as_of_date`,
  `market_value_usd_m`, `constraint_policy_id`, and `holdings` (instrument_id,
  quantity_usd_m, sleeve, asset_class). Holding quantities are USD millions and (in
  this dataset) sum to the portfolio market value, so quantity = market-value weight.
- `GET /api/instruments/bonds` — per-bond security master: `candidate` (true =
  buyable candidate, false = currently-held/not-offered), `energy_linked`,
  `rating_bucket` (IG/HY), `modified_duration_years`, `yield_to_maturity_pct`,
  `coupon_pct`, `spread_bps`, `subsector`, `issuer_id`, `recommended_theme_tags`.
- `GET /api/issuers` — `watchlist` (bool), `rating_bucket`, `sector`, `subsector`,
  `credit_outlook`, `research_tags`. The **issuer** `watchlist` flag is the source of
  truth for watchlist avoidance (bond theme tags like `WATCHLIST_RISK` corroborate
  but rely on the issuer flag).
- `GET /api/indices` and `/api/index-levels` (or `/api/index-levels/<id>`) — index
  metadata and monthly `{date, level}` arrays per index id.
- `GET /api/allocation/opportunity-sets` — `opportunity_set` → `asset_class`
  (Equities / Duration / Credit / Currency) and `display_order`.
- `GET /api/allocation/prior-views` — rows keyed by `quarter` + `previous_quarter`,
  each with `view` (UW/N/OW) and `conviction`. The prior view for a target quarter Q
  is the row whose `quarter == Q` (its `previous_quarter` is the quarter before).
- `GET /api/macro-signals` — per `opportunity_set` per `quarter`: numeric `score`,
  `rationale_code`, `drivers`. This is the signal that maps to a view.
- `GET /api/market/energy` — current commodity signals + `pitch_themes` for energy
  trade positioning.

List endpoints accept simple equality filters, e.g. `?rating_bucket=HY`,
`?candidate=true`, `?quarter=Q2_2026`.

## 1. Policy thresholds (read live from /api/policies)

The current set (`POLICY_SET_2026_05`, `as_of_date` 2026-05-29) exposes:

- **allocation_mapping** (`POL_ALLOCATION_MAPPING`):
  - `view_score_thresholds`: `OW_min` = +0.35, `UW_max` = −0.35, neutral band
    (−0.35, +0.35). Score ≥ OW_min → **OW**; ≤ UW_max → **UW**; else **N**.
  - `conviction_thresholds` on **absolute** score: `HIGH_abs_min` = 0.70,
    `MEDIUM_abs_min` = 0.35, `LOW_abs_below` = 0.35. |score| ≥ 0.70 → HIGH;
    0.35 ≤ |score| < 0.70 → MEDIUM; |score| < 0.35 → LOW.
  - `view_rank`: UW = −1, N = 0, OW = +1. Use for change direction.
- **correlation** (`POL_CORRELATION_DEFAULT`): `correlation_high_threshold` = 0.80,
  `correlation_low_threshold` = 0.20, review window `2025-05-30` … `2026-04-30`.
- **credit_default** (`POL_CREDIT_DEFAULT`): `duration_band_years` [3.0, 5.0],
  `max_hy_allocation_pct` 20.0, `issuer_concentration_limit_pct` 12.0,
  `subsector_min_count_for_diversified` 2, `target_hy_reduction_pct` 0.0.
- **credit_risk_reduction** (`POL_CREDIT_RISK_REDUCTION`): same bands/caps but
  `target_hy_reduction_pct` = 4.0 (used by risk-reduction rebalances).
- **multi_asset** (`POL_MULTI_ASSET_DEFAULT`): composes allocation_mapping +
  correlation_default + credit_default.
- **multi_asset_risk** (`POL_MULTI_ASSET_RISK`): composes correlation_default +
  credit_risk_reduction; `committee_escalation_threshold` =
  "two_or_more_material_exceptions".

Always re-read these; do not assume they are unchanged between runs.

## 2. Core computation recipes

### Pearson correlation from monthly simple returns
1. For each index, fetch `/api/index-levels/<id>`; keep rows with
   `level_start_date <= date <= level_end_date` (the window from the request /
   policy). Sort ascending by date.
2. The standard window has **12 monthly levels → 11 monthly returns**
   (`return_observations` = levels − 1). Verify all indices share the same dates.
3. Simple return r_t = level_t / level_{t-1} − 1.
4. Pearson r over the aligned return vectors. Round to **3 decimals** unless the
   template says otherwise.
5. Compare against `correlation_high_threshold` (0.80) and
   `correlation_low_threshold` (0.20). "Highest positive" = max r; "lowest" = min r
   (can be strongly negative).

### Weighted modified duration / weighted YTM
Quantity-weighted (= market-value-weighted, since qty sums to MV):
`Σ(qty_i × metric_i) / Σ qty_i`. Use post-trade quantities for post-trade metrics.

### HY allocation %
`100 × (HY market value) / (total post-trade market value)`. HY = bonds whose
`rating_bucket == "HY"`. Denominator is the portfolio market value AFTER the trades
(for BUY-only sleeves, MV increases by the bought notional; for self-funded
rotations, MV is unchanged).

### Issuer / subsector concentration & "selected" diversification
- Portfolio issuer concentration = max issuer MV / total MV vs
  `issuer_concentration_limit_pct` (12%). NOTE: a held position can already breach
  this; a pure-BUY task's `selected_*_diversification_pass` flags refer to the
  **selected trade package**, i.e. the chosen tickets use ≥2 distinct issuers and
  ≥2 distinct subsectors (`subsector_min_count_for_diversified` = 2) — not a
  portfolio-wide recomputation. Read the template field name to decide which.

### Carry / YTM improvement
"Improve carry" = raise portfolio weighted `yield_to_maturity_pct` (and/or
`coupon_pct`) versus the current weighted YTM. Compute current weighted YTM first
as the baseline to beat.

## 3. View / conviction / change mapping (allocation archetypes)

For each opportunity set, for the target quarter:
1. `signal_score` = `score` from `/api/macro-signals` (that opportunity_set, that
   quarter). Round to 3 decimals where the template exposes it.
2. `view` from `view_score_thresholds` (§1).
3. `conviction` from |score| (§1).
4. `prior_view` = `/api/allocation/prior-views` row where `quarter == target`.
5. `change` by comparing `view_rank(new view)` vs `view_rank(prior view)`:
   greater → `UP`, less → `DOWN`, equal → `UNCHANGED`.
6. `rationale_code` = the macro signal's `rationale_code` for that set (it already
   uses the allowed enum). `asset_class` from `/api/allocation/opportunity-sets`.

Watch for stale-payload traps: a local note may assert an old view (e.g. "kept USD
overweight"); if the current score maps elsewhere (e.g. USD score in the neutral
band → N with change DOWN), the environment value wins.

## 4. Archetype playbooks

### (a) Energy-credit recommendation / trade-package selection
Endpoints: portfolio detail, `/api/instruments/bonds`, `/api/issuers`,
`/api/market/energy`, `/api/policies`.
- Eligible BUY universe = `candidate == true` AND `energy_linked == true` AND issuer
  `watchlist == false` (committee is sensitive to watchlist yield traps; the energy
  desk theme is `AVOID_REFINING_WATCHLIST`). Exclude already-held when the task asks
  for *new* tickets.
- Honour the ticket spec literally (e.g. "exactly two BUY tickets totalling USD 8.0m
  split evenly" → two BUYs of 4.0 each).
- Choose tickets that (i) raise weighted YTM above the current baseline, (ii) keep
  post-trade weighted duration inside [3.0, 5.0], (iii) keep post-trade HY ≤ 20%,
  (iv) use ≥2 issuers and ≥2 subsectors (selected diversification), and (v) fit the
  income/theme story. For an LNG/gas income pitch, favour Natural Gas/LNG and
  midstream/oil names (the top energy signal is LNG export pull); set
  `sales_positioning.target_segment` = `multi_asset_income` and
  `sales_positioning.theme` = `lng_export_tailwind`. Use `avoid_watchlist_yield_trap`
  only if the story is explicitly about dodging watchlist carry.
- Output: `trade_package` sorted **ascending by instrument_id**; numeric precision
  per template (notional 1 dp; metrics 2 dp). `post_trade_metrics` recomputed on the
  full post-trade book. `constraint_checks` booleans: hy_cap_pass,
  duration_band_pass, selected_issuer_diversification_pass,
  selected_subsector_diversification_pass, watchlist_avoidance_pass.
  `data_precedence` = `current_environment_over_stale_payload` when the live
  portfolio (MV, HY, duration) differs from the stale snapshot.
- `as_of_date` = the portfolio/environment `as_of_date`.

### (b) International equity correlation review
Endpoints: portfolio detail, `/api/policies`, `/api/indices`, `/api/index-levels`.
- Build the correlation matrix over the requested index universe and window (§2).
  `review_window.return_observations` = levels − 1.
- `extreme_pairs.highest_positive` = max-correlation pair; `.lowest` =
  min-correlation pair. Each `pair_id` is the two index ids **sorted ascending
  alphabetically**; `correlation` to 3 decimals.
- `index_set` = the universe sorted ascending alphabetically.
- `concentration`: set `high_threshold_breached` = (max pair r ≥ 0.80);
  `china_asia_dependence_flag` = true when the dominant high-correlation cluster is
  China/Asia regional overlap; `primary_code` ∈
  {CHINA_ASIA_DEPENDENCE, GLOBAL_DEVELOPED_OVERLAP, NO_MATERIAL_CONCENTRATION} —
  pick CHINA_ASIA_DEPENDENCE when China/Asia drive the concentration, else the
  global-developed overlap or none.
- `diversification_candidates` ⊆ {IDX_EM_EX_CHINA, IDX_INDIA, IDX_LATAM} — the
  low/negative-correlation diversifiers (LatAm is the classic strong diversifier when
  it shows negative correlations); sorted ascending alphabetically.
- `sleeve_actions`: length 2, ordered ascending by sleeve; `action` ∈
  {trim, add, hold, hedge, monitor, rotate}; `target_index_id` ∈
  {IDX_CHINA, IDX_EM_EX_CHINA, IDX_LATAM}. Typical pattern: trim the
  concentrated/over-overlapping sleeve, add the diversifier.

### (c) Active allocation view refresh
Endpoints: `/api/allocation/opportunity-sets`, `/api/allocation/prior-views`,
`/api/macro-signals`, `/api/policies`.
- One row per requested opportunity set, rows ordered by the **request payload's
  focus_opportunity_sets order** (NOT alphabetical) unless template says otherwise.
- Each row: opportunity_set, asset_class, view, change, conviction, rationale_code
  per §3.
- `risk_overlay`: pick `overlay_code` + `primary_action` from the dominant signal
  cluster across the requested sets. When duration/quality signals dominate
  (Treasuries/Bunds/IG positive) →
  `DURATION_QUALITY_TILT` / `tilt_to_duration_quality`. When HY risk dominates
  (Corporate High Yield strongly negative) →
  `CREDIT_RISK_REDUCTION` / `trim_credit_beta`. When cyclical equity is broadly
  positive → `EQUITY_BETA_EXTENSION` / `add_cyclical_equity_beta`. When a defensive
  currency hedge is warranted → `CURRENCY_DEFENSIVE_HEDGE` / `add_currency_hedge`.
  Otherwise `NO_OVERLAY` / `hold_policy_weights`. `rationale_codes` is a list ordered
  by business priority (strongest driver first), drawn from the enum.
- `policy_id` = the allocation/policy id (`POL_ALLOCATION_MAPPING` or the composing
  policy set id, per template). `as_of_date`, `target_quarter`, `prior_quarter`, and
  any fixed `task_id`/`required_value` come straight from the template/payload.

### (d) Fixed-income risk rebalance
Endpoints: portfolio detail, `/api/instruments/bonds`, `/api/issuers`,
`/api/policies` (governing policy is usually `POL_CREDIT_RISK_REDUCTION`).
- Baseline: compute current HY%, weighted duration, watchlist exposure (Σ qty of
  holdings whose issuer `watchlist == true`).
- SELL pressure points: watchlist HY first (to clear watchlist exposure), then
  enough additional HY so post-trade HY ≤ 20% (max_hy_allocation_pct) AND HY
  reduction ≥ `target_hy_reduction_pct` (4.0 pp). Selling only the single watchlist
  bond is usually NOT enough to satisfy the 20% cap — verify the arithmetic and sell
  a second HY line if needed.
- BUY current eligible candidates (`candidate == true`, issuer `watchlist == false`)
  to fund the sells and preserve duration inside [3.0, 5.0] (IG ballast like data
  centers / mining / utilities). NEVER buy a watchlist candidate even if it is on the
  desk shortlist (e.g. a high-carry watchlist HY name is a deliberate distractor) →
  `buys_avoid_watchlist` = true.
- Keep the rotation self-funded (Σ SELL notional = Σ BUY notional) unless the task
  says otherwise.
- Output: `trades` sorted by action with **SELL before BUY**, then ascending
  instrument_id within each action; quantity 1 dp. `risk_metrics` (post_trade_hy %
  2dp, post_trade_duration 2dp, hy_reduction_pct_points 2dp, watchlist_exposure 1dp).
  `exception_flags` booleans (hy_cap_pass, duration_band_pass,
  target_hy_reduction_met, watchlist_exposure_cleared). `watchlist_sell_ids`
  ascending. `risk_note_code` = dominant driver (`watchlist_concentration` or
  `hy_cap_pressure`; `duration_preservation` / `carry_tradeoff` / `no_action`
  otherwise). `as_of_date` = portfolio as_of_date.

### (e) Multi-asset committee decision
Endpoints: portfolio detail, index levels, `/api/policies`, prior-views,
macro-signals (it links a correlation finding to allocation views).
- `correlation_summary`: length 2 in fixed order
  [highest_concentration, best_diversifier] over the requested equity index subset
  (window = current 12-month monthly window = policy window). Each item: pair_role
  enum, `pair` (two ids sorted alphabetically), `correlation` 3dp. Highest
  concentration = max-correlation pair; best diversifier = min-correlation pair.
- `target_sleeve_actions` and `allocation_views`: one row per opportunity set in the
  payload's `item_order` (NOT alphabetical). allocation_views expose prior_view,
  signal_score (3dp), view, change, conviction, rationale_code per §3. sleeve actions
  use {trim, add, hold, hedge, monitor, rotate} — typically trim the concentration
  driver, add/hold the diversifier, hedge/monitor a defensive currency.
- `rebalance_trigger` ∈ {correlation_cap_breach, hy_cap_pressure, duration_drift,
  watchlist_concentration, committee_review}: use `correlation_cap_breach` when the
  top equity pair ≥ 0.80, else `committee_review`.
- `portfolio_risk_concentration_flag` = true when a material concentration exists
  (e.g. China/Asia equity pair ≥ high threshold).
- `next_step` ∈ {approve_rotation, defer_pending_risk_review,
  approve_with_monitoring, reject_constraint_breach}: choose
  `approve_with_monitoring` for a sound but concentration-flagged plan,
  `reject_constraint_breach` only on a hard breach, `defer_pending_risk_review` when
  data/escalation is incomplete. Honour the multi_asset_risk escalation rule (two or
  more material exceptions → committee escalation).
- Refresh against the stale local note (e.g. don't carry a stale USD overweight if
  the current USD score is neutral). `as_of_date` = environment as_of_date.

## 5. Common misjudgments to avoid

- Trusting stale local marks/weights/views/watchlist flags instead of the live API.
- Forgetting the off-by-one: N monthly levels give N−1 returns; observation count and
  correlation both use returns, not levels.
- Using log returns or pairwise-dropped data — use **simple** returns over the
  common, fully-aligned window.
- Mis-ordering output: pair ids alphabetical within a pair; lists sometimes
  alphabetical (correlation review), sometimes payload-defined order (allocation
  rows), sometimes action-then-id (rotations). Read each ordering rule.
- Buying or holding a watchlist name because it has the highest carry — it is a
  yield-trap distractor; watchlist avoidance overrides carry.
- Selling only the watchlist bond and assuming the HY cap is satisfied — verify HY%
  ≤ 20 explicitly and sell more HY if needed.
- Confusing candidate-vs-held: `candidate == false` bonds are existing/un-offered;
  only `candidate == true` are buyable.
- Confusing "selected diversification" (within the chosen trade package) with
  portfolio-wide issuer concentration.
- Rounding at the wrong precision, or returning narrative text when JSON-only is
  required.
- Never call any scoring/judge endpoint; only the read-only data endpoints above.
