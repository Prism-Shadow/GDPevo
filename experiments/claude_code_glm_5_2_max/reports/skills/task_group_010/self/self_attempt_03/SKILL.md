# Asteria Investment Office — Institutional Portfolio-Risk Solver Skill

A transferable SOP for solving Asteria Investment Office portfolio-risk tasks. Three workflows feed
the test set: (A) energy/fixed-income credit trade strategy, (B) international equity correlation
review, (C) cross-asset active allocation view updates. Some test tasks combine B+C.

## 0. Golden rules (read first)

1. **The remote environment is the book of record.** Base URL `<remote-env-url>`. Every
   `input/payloads/*.json` is intake context and may be stale (old worksheet marks, stale quantity
   boards, prior-week shortlists, old desk notes). When a payload conflicts with the environment,
   prefer the environment. The answer field `data_precedence` / your reasoning must reflect this.
2. **Fetch fresh.** Do not trust locally-cached payload numbers for holdings, quantities, or marks.
   Always pull `/api/portfolios/<id>` for current holdings and `/api/instruments/bonds`,
   `/api/issuers` for security master. Stale-quantity boards in particular disagree with the
   portfolio service; use the portfolio service quantities.
3. **No correlations are stored.** Compute every correlation yourself from `/api/index-levels`
   (monthly simple returns, Pearson). Never invent or reuse a correlation.
4. **Precision is declared per-field in `answer_template.json`.** Respect it exactly:
   - `notional_usd_m` / `quantity_usd_m` / `post_trade_watchlist_exposure_usd_m` → 1 decimal.
   - All `post_trade_metrics`, `risk_metrics` percents/years → 2 decimals.
   - `correlation` and allocation `signal_score` → 3 decimals.
   - Round half-up at the end; do not round intermediate inputs.
5. **Output exactly one JSON object** matching the template's required keys, enums, and ordering.
   Sort trade lists as the template dictates (ascending `instrument_id`; SELL-before-BUY then
   `instrument_id`). Pair index ids alphabetically inside each pair.
6. **No judge, no hidden gold.** Derive every value from environment + template. Do not assume a
   "correct" pre-decided answer; the environment + policy thresholds define correctness.

## 1. Endpoints that matter

All GET, all on `<remote-env-url>`:

- `/api/catalog` — every portfolio/bond/issuer/index/policy/opportunity-set id. Start here to confirm ids.
- `/api/portfolios` — summaries (id, objective, strategy, `constraint_policy_id`, MV, holding count, **`as_of_date`**).
- `/api/portfolios/<id>` — objective, **constraints**, **current holdings** (instrument_id, quantity_usd_m, sleeve, notes), MV. This is authoritative for holdings & quantities.
- `/api/instruments/bonds` (filters: `?candidate=true`, `?rating_bucket=HY`) — bond universe. Per bond: `candidate`, `energy_linked`, `rating`, `rating_bucket` (IG/HY), `modified_duration_years`, `yield_to_maturity_pct`, `coupon_pct`, `spread_bps`, `sector`, `subsector`, `issuer_id`, `maturity`, `recommended_theme_tags`.
- `/api/issuers` — per issuer: `sector`, `subsector`, `rating_bucket`, **`watchlist`** (bool), `credit_outlook`, `research_tags`. Join to bonds via `issuer_id`.
- `/api/policies` — one object with sub-policies: `credit_default`, `credit_risk_reduction`, `correlation`, `allocation_mapping`, `multi_asset`, `multi_asset_risk`. Each portfolio's `constraint_policy_id` names which applies.
- `/api/market/energy` — commodity signals (oil/gas/LNG/refining/renewables) with `score`, `direction`, `signal_id`, `pitch_themes`, `stale_data_warning`. Use for energy-desk theme/sales positioning.
- `/api/indices` — index metadata (region, frequency, level window).
- `/api/index-levels` — `{index_id: [{date, level}, ...]}` monthly. Source for all correlations.
- `/api/allocation/opportunity-sets` — taxonomy mapping `opportunity_set` → `asset_class` (Equities/Duration/Credit/Currency) + `display_order`.
- `/api/allocation/prior-views` — records `{quarter, previous_quarter, opportunity_set, view, conviction}`. **Holds the PRIOR-period view** (see §6 for the exact selection rule).
- `/api/macro-signals` — `{quarter, opportunity_set, score, rationale_code, drivers}`. Source for new allocation views.

## 2. Policy reference (environment facts, re-fetch to confirm)

- `credit_default` / `credit_risk_reduction` (POL_CREDIT_DEFAULT / POL_CREDIT_RISK_REDUCTION):
  `duration_band_years: [3.0, 5.0]`, `max_hy_allocation_pct: 20.0`,
  `issuer_concentration_limit_pct: 12.0`, `subsector_min_count_for_diversified: 2`,
  `target_hy_reduction_pct` (0 for credit_default; 4.0 for credit_risk_reduction — a required
  percentage-point reduction).
- `correlation` (POL_CORRELATION_DEFAULT): `correlation_high_threshold: 0.8`,
  `correlation_low_threshold: 0.2`, window start/end align with index level window.
- `allocation_mapping` (POL_ALLOCATION_MAPPING):
  - `view_score_thresholds`: `OW_min: 0.35`, `UW_max: -0.35`, neutral between `[-0.35, 0.35]`.
  - `conviction_thresholds`: `HIGH_abs_min: 0.7`, `MEDIUM_abs_min: 0.35`, `LOW_abs_below: 0.35`.
  - `view_rank`: `UW=-1, N=0, OW=1`.
- `multi_asset` (POL_MULTI_ASSET_DEFAULT) `uses_allocation_mapping/uses_correlation_default/uses_credit_default: true`.
- `multi_asset_risk` (POL_MULTI_ASSET_RISK) `uses_correlation_default/uses_credit_risk_reduction: true`, escalates on `two_or_more_material_exceptions`.

## 3. Precision & ordering conventions (universal)

- Trade lists: sort as template states. Energy trade package = ascending `instrument_id`. Lumen
  rotation trades = SELL before BUY, then ascending `instrument_id` within each action.
- `notional_usd_m` / `quantity_usd_m`: 1 decimal (e.g. `4.0`, not `4`).
- `total_market_value_usd_m`, `hy_allocation_pct`, `weighted_modified_duration_years`,
  `weighted_yield_to_maturity_pct`, `post_trade_hy_allocation_pct`, `post_trade_duration_years`,
  `hy_reduction_pct_points`: 2 decimals.
- `post_trade_watchlist_exposure_usd_m`: 1 decimal.
- Correlation, `signal_score`: 3 decimals.
- `as_of_date`: use the portfolio summary `as_of_date` (currently `2026-05-29`) unless the task says otherwise.
- Pair ids: alphabetical within the pair; sleeve/lists ordered ascending unless an `item_order` is given.

---

## WORKFLOW A — Energy / fixed-income credit trade strategy

Covers: BUY/SELL bond tickets under credit constraints; post-trade metrics; sales positioning;
data-precedence (train_001 BUY-only energy income; train_004 HY/watchlist risk-reduction rotation).

### A1. Load current state (order matters)
1. `GET /api/portfolios/<portfolio_id>` → holdings (instrument_id → quantity_usd_m), MV, constraints.
2. `GET /api/instruments/bonds` → join each holding to its bond master (rating_bucket, modified_duration_years, yield_to_maturity_pct, subsector, issuer_id, energy_linked).
3. `GET /api/issuers` → join `issuer_id` → `watchlist`, `credit_outlook`.
4. `GET /api/market/energy` → signal scores + pitch themes (for energy-desk tasks).
5. `GET /api/policies` → the portfolio's `constraint_policy_id` sub-policy.

Re-read holdings from the portfolio service even if a stale snapshot / exception board is in the
payload — those boards routinely disagree by a few $m (e.g. a watchlist HY bond shown as 10.0 on
the stale board is 12.0 in the service). The service wins.

### A2. Post-trade metric formulas (market-value-weighted)
For the post-trade book (existing holdings ± trades):

- `total_market_value_usd_m = Σ quantity_usd_m` (after trades).
- `hy_allocation_pct = (Σ quantity where rating_bucket=="HY") / total_market_value_usd_m * 100`.
- `weighted_modified_duration_years = Σ(quantity * modified_duration_years) / total_market_value_usd_m`.
- `weighted_yield_to_maturity_pct   = Σ(quantity * yield_to_maturity_pct)  / total_market_value_usd_m`.

Weight by quantity (=$m par/market value here; the service gives one figure). Round outputs to 2 dp.
For rotation tasks: `hy_reduction_pct_points = pre_trade_hy_pct − post_trade_hy_pct` (2 dp);
`post_trade_watchlist_exposure_usd_m = Σ quantity of holdings whose issuer is watchlist` (1 dp).

### A3. Constraint pass/fail
- `hy_cap_pass`: post-trade `hy_allocation_pct <= max_hy_allocation_pct` (20.0).
- `duration_band_pass`: `duration_band_years[0] <= weighted_modified_duration_years <= [1]` (3.0–5.0).
- `selected_issuer_diversification_pass`: the SELECTED (new) tickets' issuers are distinct. (Issuer
  concentration limit 12% also exists; check a selected buy isn't an existing-issuer overload.)
- `selected_subsector_diversification_pass`: the selected tickets span `>= subsector_min_count_for_diversified` (2) distinct subsectors.
- `watchlist_avoidance_pass`: no selected BUY whose issuer `watchlist==true`. For rotation tasks
  also report `watchlist_exposure_cleared` (post-trade watchlist $m == 0) and `buys_avoid_watchlist`.
- `target_hy_reduction_met` (risk-reduction policy only): `hy_reduction_pct_points >= target_hy_reduction_pct` (4.0).

### A4. BUY-only energy selection (train_001-style)
Inputs: exactly N BUY tickets (usually 2) for a fixed total notional, split evenly; energy-linked;
improve carry; keep inside constraints; client-facing income pitch.

Selection filter for candidates:
1. `candidate==true` AND `energy_linked==true` AND not already a holding.
2. **Watchlist filter:** issuer `watchlist==false` (credit committee is sensitive to headline
   watchlist carry — drop Driftwood/Pacific Refining/Juniper even though their YTM is highest).
3. **Duration-band filter on the post-trade book, but a good heuristic is to drop candidates whose
   own `modified_duration_years` is outside `[3.0, 5.0]`** — long-dated LNG/oil (dur ~5.8–6.7) and
   very short HY (dur <3.0) are duration-ineligible distractors; including them risks breaching the
   band. Prefer candidates whose own duration sits inside the band.
4. Prefer the desk's preferred themes (LNG exporters / gas demand): match `recommended_theme_tags`
   (`LNG_EXPORTS`, `GAS_DEMAND`) and the strongest `market/energy` signal (LNG export pull is the
   most positive energy signal).
5. Improve carry: among eligible, prefer higher YTM. One IG anchor (LNG/gas, IG) + one non-watchlist
   HY carry bond is the canonical "improve carry while staying diversified" pair; verify the HY
   addition keeps `hy_allocation_pct` well under the 20% cap and that the two picks are distinct
   issuers and distinct subsectors.

Output `sales_positioning`: `target_segment` from the request's `client_context`
(`multi_asset_income` etc.); `theme` from the energy pitch themes — pick the one matching the
anchor (e.g. `lng_export_tailwind` when the IG anchor is an LNG exporter). `data_precedence` =
`current_environment_over_stale_payload` whenever a stale worksheet mark differs from the service
(MV, HY%, duration, or quantity) — which is the normal case.

### A5. HY/watchlist risk-reduction rotation (train_004-style)
Goal: lower HY, remove avoidable watchlist risk, keep duration in the CIO band, fund IG candidates.

1. Identify watchlist holdings (issuer `watchlist==true`) — sell them (fully) to clear watchlist.
2. The portfolio is usually far over the 20% HY cap. Compute pre-trade HY%. To clear the cap with MV
   held roughly constant, sell at least `(pre_hy_pct − 20)% * total_mv` of HY. Selling only the
   watchlist bond may not reach the cap — sell additional non-watchlist HY "pressure points" too.
3. Keep at least the higher-rated HY for carry if "preserve carry" is an objective; don't strip all
   HY unless the desk asks.
4. Fund IG candidates from the desk shortlist / `?candidate=true` IG universe. Exclude any candidate
   whose issuer is watchlist (`avoid_new_watchlist_buy`). Verify each buy's own duration sits inside
   `[3.0, 5.0]`; spread buys across distinct issuers (issuer conc 12%).
5. Preserve duration: selling short-duration HY (dur ~2.8–3.4) raises portfolio duration; buying
   longer IG (dur ~4.0–4.8) raises it further. Re-check `weighted_modified_duration_years <= 5.0`.
   If it would breach 5.0, tilt buys toward shorter IG / sell some longer IG.
6. `risk_note_code`: pick the dominant story — `watchlist_concentration` (watchlist was the issue),
   `hy_cap_pressure` (HY still over cap after rotation), `duration_preservation` (rotation held
   duration), `carry_tradeoff` (gave up carry to reduce risk), `no_action`.

Pitfalls: the stale exception board's quantities are NOT the service quantities — re-fetch. The
desk shortlist often includes a watchlist HY bond (high carry, "risk team concerned about issuer
status") as a trap; exclude it. Duration-ineligible IG candidates (dur >5.0) appear in shortlists
as "duration ballast" but breach the band — check, don't trust the label.

---

## WORKFLOW B — International equity correlation review

Covers: pair correlations across an index universe, highest/lowest pairs, China/Asia dependence
flags, diversification candidates, sleeve actions (train_002; also the correlation half of train_005).

### B1. Compute correlations
1. `GET /api/index-levels` (and/or `/api/index-levels/<id>`). Each index has monthly `{date, level}`.
2. For each index, sort by date, compute **simple monthly returns** `r_t = level_t / level_{t-1} − 1`
   across the review window (level_start_date … level_end_date). 12 monthly levels ⇒ 11 returns.
3. Pearson correlation per pair: `cov(r_i, r_j) / (std(r_i)*std(r_j))` over the shared return dates.
4. Round to 3 decimals. `return_observations` = number of returns (e.g. 11).

Use the window declared in the request payload's `review_window` (start/end dates) — these match the
index metadata `level_start_date`/`level_end_date`.

### B2. Extremes & pairs
- `highest_positive`: the pair with the maximum correlation. `lowest`: the pair with the minimum
  correlation (can be negative). `pair_id` / `pair` = the two index ids sorted alphabetically.
- For combined B+C tasks (train_005): `correlation_summary` has exactly two items in order
  [`highest_concentration`, `best_diversifier`]. `highest_concentration` = the **highest** absolute
  correlation pair (the pair that moves together most = concentration risk). `best_diversifier` =
  the **lowest** (most negative) correlation pair (best diversification). Both pairs sorted
  alphabetically internally.

### B3. Concentration flags (POL_CORRELATION_DEFAULT)
- `high_threshold_breached`: any pair correlation `>= correlation_high_threshold` (0.8). Usually true
  for regional equity universes — many pairs exceed 0.8.
- `china_asia_dependence_flag`: set when the dedicated China sleeve and the Asia-Pacific-ex-Japan
  sleeve are both highly correlated with EM/World (Asia beta overlap). Check IDX_CHINA and
  IDX_AC_ASIA_PAC_EX_JP correlations against IDX_EM / IDX_WORLD — if multiple exceed 0.8, flag true.
- `primary_code`:
  - `CHINA_ASIA_DEPENDENCE` when China/AsiaPac/EM inter-correlations dominate the high pairs.
  - `GLOBAL_DEVELOPED_OVERLAP` when EAFE/World/ACWI developed-overlap pairs dominate instead.
  - `NO_MATERIAL_CONCENTRATION` only when no pair breaches 0.8.

### B4. Diversification candidates & sleeve actions
- `diversification_candidates`: indices with low (ideally negative) correlation to the concentrated
  China/Asia cluster. Typical allowed set: `IDX_EM_EX_CHINA`, `IDX_INDIA`, `IDX_LATAM` — list all
  that qualify, ascending alphabetical. LatAm's negative correlation to China/Asia makes it the
  strongest diversifier.
- `sleeve_actions` (length per template, ascending by sleeve): the two most actionable moves.
  Typical pattern: **trim/rotate the concentrated China sleeve** toward `IDX_EM_EX_CHINA` (keep EM
  beta, drop single-country concentration), and **add the best diversifier** (`IDX_LATAM`).
  `action` ∈ {trim, add, hold, hedge, monitor, rotate}; `target_index_id` ∈ the sleeve's allowed set.
- For combined B+C tasks: `target_sleeve_actions` lists one action per requested sleeve (e.g. EM,
  India, LatAm, USD) in the template's `item_order`. Map each sleeve's allocation view to an action:
  UW+DOWN → `trim`; OW+UP → `add`; OW+UNCHANGED-high-conviction → `add` or `hold`; N → `hold`/`monitor`;
  a currency sleeve used as defensive offset → `hedge`.

### B5. Correlation pitfalls
- Use **simple** returns (level ratio − 1), NOT log returns, unless the template says otherwise.
- Ensure both indices share the same monthly dates; align by date before correlating.
- Don't round returns before correlating — round only the final correlation.
- A negative "lowest" pair is normal; don't force it positive.

---

## WORKFLOW C — Cross-asset active allocation view updates

Covers: active allocation views (view/change/conviction/rationale_code) per opportunity set, risk
overlay, lineage, concentration flag, rebalance trigger, next-step enums (train_003; the allocation
half of train_005).

### C1. The view-derivation pipeline (this is the core algorithm)
For a refresh with `target_quarter` T and `prior_quarter` P (e.g. T=Q2_2026, P=Q1_2026):

1. **New view** from `/api/macro-signals` where `quarter==T`, using `allocation_mapping` thresholds:
   - `score >= 0.35` → `OW`; `score <= -0.35` → `UW`; else `N`.
2. **Conviction** from `|score|`:
   - `|score| >= 0.7` → `HIGH`; `>= 0.35` → `MEDIUM`; `< 0.35` → `LOW`.
3. **rationale_code** = the macro signal's own `rationale_code` (e.g. `EUROPE_RECOVERY`,
   `JAPAN_POLICY_RISK`, `CHINA_DEPENDENCE`, `INDIA_OFFSET`, `LATAM_DIVERSIFIER`,
   `DURATION_SUPPORT`, `HY_VALUATION_RISK`, `DOLLAR_DEFENSIVE`, `CREDIT_SPREAD_RISK`,
   `GROWTH_IMPROVES`, `RATE_CUT_SUPPORT`, `NEUTRAL_BALANCE`).
4. **prior_view** from `/api/allocation/prior-views`. **Selection rule (critical):** pick the
   records where `quarter == T` (these carry `previous_quarter == P`); their `view` (and
   `conviction`) IS the prior-period (P) view. Do NOT look for a `quarter == P` batch — it does not
   exist. Do NOT treat the prior-views `view` as the new/target view; the new view always comes from
   the macro signal via step 1.
5. **change** = compare `view_rank` of new vs prior: `UP` if new>old, `DOWN` if new<old, else
   `UNCHANGED`. (`view_rank`: UW=-1, N=0, OW=1.)
6. **asset_class** from `/api/allocation/opportunity-sets` (Europe→Equities, U.S. Treasuries→Duration,
   Corporate High Yield→Credit, USD→Currency, etc.).

Sanity check: the prior-views batch where `quarter == T` reflects the incoming (P) view; a later
batch where `quarter == T+1` would reflect the just-derived (T) view and should match your
signal-derived T views for most (not all) opportunity sets — committee judgment can override an
occasional name, so trust your signal derivation for the T view, and trust prior-views for the P view.

### C2. Output ordering & required rows
- `allocation_views` ordered by the request payload's `focus_opportunity_sets` order (NOT alphabetical,
  NOT display_order). Include exactly the requested opportunity sets (train_003 = 8; train_005 = 4).
- Each row: `opportunity_set`, `asset_class`, `view`, `change`, `conviction`, `rationale_code`.
- train_005 also wants `prior_view` and `signal_score` (raw macro score, 3 dp) per row.

### C3. Risk overlay (train_003)
`risk_overlay`: `overlay_code`, `primary_action`, `rationale_codes` (list, **business-priority order,
highest priority first**).
- Decide from the dominant risk in the view set. When HY is UW on `HY_VALUATION_RISK` and duration
  (U.S. Treasuries) is OW on `DURATION_SUPPORT`, the overlay is `DURATION_QUALITY_TILT` with
  `primary_action: tilt_to_duration_quality` — rotate out of credit beta into duration/quality.
  When credit spread risk dominates with no duration offset, use `CREDIT_RISK_REDUCTION` /
  `trim_credit_beta`. When currency defensiveness dominates (USD/CHF defensive), use
  `CURRENCY_DEFENSIVE_HEDGE` / `add_currency_hedge`. If views net to neutral, `NO_OVERLAY` /
  `hold_policy_weights`.
- `rationale_codes` priority order: lead with the most actionable risk-reduction code (the one
  driving the overlay), then supporting codes. Deduplicate.

`policy_id` (train_003) = `POL_ALLOCATION_MAPPING` (the policy whose thresholds produce the views).
`task_id` = the template's `required_value` (e.g. `train_003`). `as_of_date` = portfolio/env as_of.
`target_quarter`/`prior_quarter` = the request's quarters (template holds `required_value`).

### C4. Combined correlation+allocation committee JSON (train_005-style)
Top-level: `portfolio_id`, `as_of_date`, `review_quarter` (the allocation quarter, e.g. Q2_2026),
`correlation_summary` (§B2), `target_sleeve_actions` (§B4, in `item_order`), `allocation_views`
(§C1, with `prior_view`+`signal_score`), `rebalance_trigger`, `portfolio_risk_concentration_flag`,
`next_step`.

- `rebalance_trigger`: choose from {`correlation_cap_breach`, `hy_cap_pressure`, `duration_drift`,
  `watchlist_concentration`, `committee_review`}. When the concentration pair breaches the 0.8
  correlation cap and drives the review, use `correlation_cap_breach`. When it's a routine committee
  refresh with no hard breach, `committee_review`.
- `portfolio_risk_concentration_flag`: true when the highest-concentration pair breaches the 0.8
  threshold OR a dedicated China sleeve creates single-country beta — generally true for these sleeves.
- `next_step`: `approve_rotation` when a clear risk-reducing rotation is proposed and no hard
  constraint is breached; `approve_with_monitoring` when concentration is flagged but managed;
  `defer_pending_risk_review` when signals conflict materially; `reject_constraint_breach` only when
  a hard policy cap is violated by the proposal.

### C5. Allocation pitfalls
- **The prior-view selection rule (§C1.4) is the #1 error source.** Re-read it. The `view` field in
  prior-views is the PRIOR (incoming) view for the refresh tagged by `quarter==T`, not the new T view.
- Don't copy conviction from prior-views — derive the NEW conviction from `|score|`.
- `change` is about view RANK (UW<N<OW), not score magnitude. OW→OW is `UNCHANGED` even if conviction rises.
- `rationale_code` must come from the macro signal, never invented. If two opportunity sets share a
  rationale code (e.g. Europe and EUR both `EUROPE_RECOVERY`), that's fine.
- `signal_score` in output = the raw macro score (3 dp), not the derived view.
- A stale local note (e.g. "USD overweight as defensive offset") describes a PRIOR posture, not the
  current view — refresh from signals; the USD score is often negative (defensive bid fading).

---

## 4. Reusable computation snippets

Pearson over monthly levels (Python):
```python
def returns(levels):  # levels: list of (date, level) sorted by date
    r = []
    for i in range(1, len(levels)):
        r.append(levels[i][1] / levels[i-1][1] - 1.0)
    return r
def pearson(x, y):
    n = len(x); mx = sum(x)/n; my = sum(y)/n
    cov = sum((x[i]-mx)*(y[i]-my) for i in range(n))
    return cov / ((sum((xi-mx)**2 for xi in x)**0.5) * (sum((yi-my)**2 for yi in y)**0.5))
```

View derivation:
```python
def view_of(s):  return "OW" if s>=0.35 else ("UW" if s<=-0.35 else "N")
def conv_of(s):
    a=abs(s); return "HIGH" if a>=0.7 else ("MEDIUM" if a>=0.35 else "LOW")
RANK={"UW":-1,"N":0,"OW":1}
def change_of(new,old):
    return "UP" if RANK[new]>RANK[old] else ("DOWN" if RANK[new]<RANK[old] else "UNCHANGED")
# prior_view: prior_views record where record["quarter"]==target_quarter (previous_quarter==prior)
```

Post-trade metrics:
```python
tot = sum(q for q in holdings.values())
hy  = sum(q for id,q in holdings.items() if bond[id]["rating_bucket"]=="HY")
wdur= sum(q*bond[id]["modified_duration_years"] for id,q in holdings.items())/tot
wytm= sum(q*bond[id]["yield_to_maturity_pct"]  for id,q in holdings.items())/tot
hy_pct = hy/tot*100
```

## 5. Distillation checklist (run before emitting JSON)
- [ ] Did I fetch holdings from `/api/portfolios/<id>` (not the stale payload board)?
- [ ] Are watchlist issuers excluded from BUYS (and sold in rotations)?
- [ ] Are duration-ineligible candidates (own mod_dur outside [3,5]) excluded?
- [ ] Post-trade HY%, duration, YTM computed market-value-weighted and rounded to 2 dp?
- [ ] Correlations computed from monthly simple returns, Pearson, 3 dp, pairs alphabetical?
- [ ] Allocation views derived from macro signals via the 0.35 / 0.7 thresholds; prior_view from
      prior-views where `quarter==target`; change from view rank?
- [ ] Trade/list ordering matches the template (ascending instrument_id; SELL-before-BUY)?
- [ ] `data_precedence` reflects env-over-stale when any payload figure disagreed with the service?
- [ ] All enums pulled from the template's allowed_values, no typos?
- [ ] One JSON object only, no narrative outside it (unless the prompt asks otherwise)?
