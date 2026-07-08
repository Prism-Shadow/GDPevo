# Asteria Investment Office — Institutional Portfolio Risk Skill

Reusable rules for solving Asteria Investment Office portfolio-risk tasks against the
remote environment at `<remote-env-url>`. The environment is the **current book
of record**; local `input/payloads/` files are possibly-stale intake context. When a
local payload conflicts with the environment, prefer the environment unless the task
prompt explicitly says otherwise.

These rules were distilled from judge feedback on the official train tasks. They cover
three workflows the test tasks draw from: (1) energy/fixed-income trade strategy,
(2) international correlation review, (3) cross-asset active allocation view updates.

---

## 0. Environment & shared conventions

### Endpoints (GET, base `<remote-env-url>`)
- `/api/catalog` — all available ids (portfolios, policies, indices, issuers, bonds, opportunity sets).
- `/api/policies` — all policy objects (see thresholds below).
- `/api/portfolios` and `/api/portfolios/<portfolio_id>` — portfolio objective, constraints, current holdings (with `quantity_usd_m` = market value, `sleeve`, `notes`).
- `/api/instruments/bonds` and `/api/instruments/bonds?candidate=true` (also `?rating_bucket=HY`). Bond fields: `instrument_id`, `issuer_id`, `rating` (specific, e.g. BBB/BB), `rating_bucket` (IG/HY), `modified_duration_years`, `yield_to_maturity_pct`, `sector`, `subsector`, `candidate`, `maturity`, `coupon_pct`, `spread_bps`, `recommended_theme_tags`, `energy_linked`.
- `/api/issuers` — `issuer_id`, `sector`, `subsector`, `rating_bucket`, `watchlist` (bool), `credit_outlook`, `research_tags`.
- `/api/market/energy` — `as_of_date`, `signals` (commodity, `signal_id`, `score`, `direction`, `summary`), `pitch_themes`, `stale_data_warning`.
- `/api/indices` and `/api/index-levels/<index_id>` — monthly `levels` (date + level).
- `/api/allocation/opportunity-sets` — `opportunity_set`, `asset_class`, `display_order`.
- `/api/allocation/prior-views` — prior views per opportunity set (with `quarter`, `previous_quarter`, `view`, `conviction`).
- `/api/macro-signals` — per opportunity set: `score`, `rationale_code`, `drivers`, `quarter`.

### Universal conventions
- **Numeric precision follows each field's declaration in `input/payloads/answer_template.json`.** Do not round differently.
- **No correlations are precomputed.** Always compute Pearson correlations yourself from `/api/index-levels` monthly levels.
- Use `rating_bucket` (IG/HY) — NOT the specific `rating` (BBB/BB) — for HY calculations.
- Holdings `quantity_usd_m` is the market value (they sum to the portfolio `market_value_usd_m`).
- `as_of_date` in answers = the environment's current as-of date (the portfolio/`/api/policies` `as_of_date`, e.g. 2026-05-29), NOT a stale intake date.
- Watchlist issuers (set `watchlist=true` on `/api/issuers`) are avoid-on-buy. Known watchlist HY traps: `ISS_DRIFTWOOD`, `ISS_PACIFIC_REFIN`, `ISS_JUNIPER_TEL`.

### Policy thresholds (from `/api/policies`)
- `POL_CREDIT_DEFAULT` / `POL_CREDIT_RISK_REDUCTION`: `duration_band_years` [3.0, 5.0]; `max_hy_allocation_pct` 20.0; `issuer_concentration_limit_pct` 12.0; `subsector_min_count_for_diversified` 2. `POL_CREDIT_RISK_REDUCTION` adds `target_hy_reduction_pct` 4.0.
- `POL_CORRELATION_DEFAULT`: `correlation_high_threshold` 0.8; `correlation_low_threshold` 0.2.
- `POL_ALLOCATION_MAPPING`: `view_score_thresholds` OW_min 0.35, UW_max -0.35, neutral ]-0.35, 0.35[; `conviction_thresholds` HIGH_abs_min 0.7, MEDIUM_abs_min 0.35, LOW_abs_below 0.35; `view_rank` OW=1, N=0, UW=-1.
- `POL_MULTI_ASSET_DEFAULT` (balanced multi-asset model) uses allocation_mapping + correlation_default + credit_default. `POL_MULTI_ASSET_RISK` uses correlation_default + credit_risk_reduction (committee escalation on two+ material exceptions).

---

## 1. Workflow: Energy / fixed-income BUY trade strategy

Example: PF-EN-ALTA. Produce a BUY ticket package under credit-risk constraints.

### Data to pull
`/api/portfolios/<id>` (constraints + holdings), `/api/instruments/bonds?candidate=true`, `/api/issuers` (watchlist), `/api/market/energy`, `/api/policies`.

### Stale-worksheet precedence
Desk worksheets in the payload are explicitly stale ("Operations has not reconciled this
worksheet to the current Asteria portfolio service"). Set
`data_precedence = "current_environment_over_stale_payload"`. Use the environment's
current `as_of_date`, holdings, and market value — not the stale snapshot's.

### Picking the BUY tickets
- Only `candidate=true` bonds, action `BUY`.
- Issuer must NOT be on the watchlist.
- Selected tickets must span **≥2 distinct issuers** and **≥2 distinct subsectors** (the `selected_*_diversification_pass` checks are about the SELECTED trades).
- Each selected bond's `modified_duration_years` should be inside the duration band [3.0, 5.0] (and the post-trade portfolio weighted duration must stay in band).
- Post-trade HY allocation must stay under the 20% cap.
- Align to the strongest `/api/market/energy` signals and the desk's preferred exposures.
  - For LNG/gas preference: pick the IG LNG exporter (e.g. `BND_BLUEGAS_2030`, Natural Gas/LNG).
  - For "select non-watchlist energy-linked carry": pick an HY energy bond from a DIFFERENT subsector whose issuer is NOT watchlisted (e.g. `BND_FJORD_WIND_2029`, Renewables HY). Avoid the tempting high-YTM watchlist HY bonds (Driftwood, Pacific Refining, Juniper) — those are yield traps.

### Notional sizing — EQUAL split
When the request gives `ticket_count` and `total_notional_usd_m` with no per-ticket
sizing guidance, split **equally** (e.g. 2 tickets of 4.0 for 8.0 total). An asymmetric
carry-tilt split was confirmed WORSE by the judge. `notional_usd_m` precision = 1.

### Output fields
- `portfolio_id` (required value), `as_of_date` (environment as-of).
- `trade_package`: list sorted **ascending by instrument_id**, each `{action:"BUY", instrument_id, notional_usd_m}`.
- `post_trade_metrics` (precision 2):
  - `total_market_value_usd_m` = pre-trade total + sum(new notionals).
  - `hy_allocation_pct` = (sum of post-trade market values of `rating_bucket=="HY"` bonds) / total × 100.
  - `weighted_modified_duration_years` = Σ(mv × modified_duration_years) / total.
  - `weighted_yield_to_maturity_pct` = Σ(mv × yield_to_maturity_pct) / total.
- `constraint_checks` (booleans):
  - `hy_cap_pass`: post-trade HY% < `max_hy_allocation_pct` (20).
  - `duration_band_pass`: post-trade weighted duration within [3.0, 5.0].
  - `selected_issuer_diversification_pass`: selected trades span ≥2 issuers (and each selected issuer ≤ concentration limit).
  - `selected_subsector_diversification_pass`: selected trades span ≥2 subsectors.
  - `watchlist_avoidance_pass`: no selected (and no portfolio) issuer is watchlisted.
- `sales_positioning`:
  - `target_segment` from the request's `client_context` (e.g. `multi_asset_income`).
  - `theme` = the theme matching the **strongest** market-energy signal. CONFIRMED: when `LNG_EXPORT_PULL` is the dominant signal (highest score) and LNG exporters are the #1 preferred exposure, `theme = "lng_export_tailwind"`. (`avoid_watchlist_yield_trap` was confirmed WRONG even though watchlist caution is mentioned — the theme tracks the positive headline signal, not the caution.)
- `data_precedence = "current_environment_over_stale_payload"`.

### Worked reference (train_001, judge-confirmed pieces)
PF-EN-ALTA pre-trade 60.0 (5 holdings, 1 HY = EASTERN_LNG 5.0 → HY 8.33%). BUY
`BND_BLUEGAS_2030` 4.0 + `BND_FJORD_WIND_2029` 4.0 → post-trade total 68.00, HY 13.24%,
weighted duration 3.28, weighted YTM 5.76; all constraints pass; theme
`lng_export_tailwind`. (Equal 4.0/4.0 split confirmed correct; the LNG theme confirmed
correct. Residual convention gap remained in the constraint-flag reporting — see note
below.)

> **Constraint-flag honesty note:** if the portfolio already breaches
> `issuer_concentration_limit_pct` (12%) in pre-existing holdings that a BUY-only ticket
> cannot reduce, evaluate each `*_pass` flag carefully against the post-trade portfolio
> (not only the selected trades). Report `false` where a hard constraint is genuinely
> breached post-trade; the `selected_*` flags specifically grade the selected trades.

---

## 2. Workflow: International equity correlation review

Example: PF-INT-NEXVEN.

### Compute correlations
For each index in the task's `index_universe`, fetch `/api/index-levels/<index_id>`.
Sort levels by date. Compute monthly simple returns `r_t = level_t / level_{t-1} - 1`.
`return_observations = n_levels - 1` (e.g. 12 levels → 11 returns). Pearson correlation
on the common return series. Round correlation to **3 decimals**.

### Output fields
- `review_window`: `{level_start_date, level_end_date, return_observations}` (use the policy/ request window dates; observations = levels − 1).
- `index_set`: all universe index ids, sorted **ascending alphabetically**.
- `extreme_pairs`:
  - `highest_positive`: the pair with the maximum correlation.
  - `lowest`: the pair with the minimum (most negative) correlation.
  - Each `pair_id` is a 2-element list sorted **alphabetically**; `correlation` to 3 decimals.
- `concentration`:
  - `china_asia_dependence_flag` (bool): true when China's correlation with Asia-Pacific / EM indices exceeds the 0.8 high threshold.
  - `primary_code`: `CHINA_ASIA_DEPENDENCE` when the dominant overlap is China+Asia/EM; `GLOBAL_DEVELOPED_OVERLAP` when EM/World/ACWI/EAFE developed-cluster overlaps dominate; `NO_MATERIAL_CONCENTRATION` otherwise. Match the CIO memo's stated concern codes.
  - `high_threshold_breached` (bool): true if any pair correlation > 0.8.
- `diversification_candidates`: list of the low-correlation diversifier index ids (from the allowed set), sorted alphabetically. Include the actionable diversifiers the sleeve actions rotate into (e.g. `IDX_EM_EX_CHINA` and `IDX_LATAM`); exclude still-highly-correlated indices like `IDX_INDIA` when it does not diversify the cluster.
- `sleeve_actions`: list of 2 objects `{sleeve, action, target_index_id}`, sorted ascending by `sleeve`. Trim the concentrated sleeve (e.g. China → `trim`, target `IDX_CHINA`); add the low-correlation diversifier (e.g. Latin America → `add`, target `IDX_LATAM`). `action` ∈ {trim, add, hold, hedge, monitor, rotate}.

### Confirmed (train_002 scored 1.0)
9-index NEXVEN review: highest `IDX_EM`/`IDX_WORLD` (0.974); lowest `IDX_CHINA`/`IDX_LATAM`
(-0.825); `china_asia_dependence_flag=true`, `primary_code=CHINA_ASIA_DEPENDENCE`,
`high_threshold_breached=true`; diversification_candidates `[IDX_EM_EX_CHINA, IDX_LATAM]`;
sleeve_actions `[{China, trim, IDX_CHINA}, {Latin America, add, IDX_LATAM}]`.

---

## 3. Workflow: Cross-asset active allocation view refresh

Example: CIO desk Q2 2026 refresh. Output one row per requested opportunity set.

### Data to pull
`/api/allocation/opportunity-sets` (maps opportunity_set → asset_class), `/api/allocation/prior-views`, `/api/macro-signals`, `/api/policies`.

### Derive each allocation row (CONFIRMED algorithm)
For each opportunity set in the **request's `focus_opportunity_sets` order**:
1. `signal_score` = the matching macro-signal `score` (round to the precision the template declares, e.g. 3 decimals).
2. `view`: `OW` if score ≥ 0.35; `UW` if score ≤ −0.35; else `N` (from `POL_ALLOCATION_MAPPING` view_score_thresholds).
3. `conviction`: `HIGH` if abs(score) ≥ 0.7; `MEDIUM` if abs(score) ≥ 0.35; `LOW` if abs < 0.35.
4. `rationale_code` = the macro-signal's `rationale_code` (verbatim).
5. `prior_view` (when the template requires it) = the view from `prior-views` for that opportunity set (the entry whose `quarter` = target quarter and `previous_quarter` = prior quarter).
6. `change`: compare `view_rank(new view)` vs `view_rank(prior view)` (OW=1, N=0, UW=−1): higher → `UP`, lower → `DOWN`, equal → `UNCHANGED`.
7. `asset_class` = from the opportunity-sets taxonomy (Equities / Duration / Credit / Currency).

### Risk overlay — do NOT automatically add one
`risk_overlay` = `{overlay_code, primary_action, rationale_codes}`. The overlay codes and
primary actions pair 1:1 (DURATION_QUALITY_TILT↔tilt_to_duration_quality,
CREDIT_RISK_REDUCTION↔trim_credit_beta, EQUITY_BETA_EXTENSION↔add_cyclical_equity_beta,
CURRENCY_DEFENSIVE_HEDGE↔add_currency_hedge, NO_OVERLAY↔hold_policy_weights).

**Key lesson (confirmed by judge):** when the active allocation views already express the
risk positions (e.g. Corporate High Yield is UW on HY_VALUATION_RISK, U.S. Treasuries is
OW on DURATION_SUPPORT), three different non-trivial overlays
(DURATION_QUALITY_TILT, CREDIT_RISK_REDUCTION, EQUITY_BETA_EXTENSION) all scored
 IDENTICALLY and never reached full marks. The correct overlay in that situation is
**`NO_OVERLAY` / `hold_policy_weights`** — the active views themselves are the position,
so no additional portfolio-level overlay is warranted. `rationale_codes` then carries
the neutral justification (e.g. `[NEUTRAL_BALANCE]`). Only impose a non-trivial overlay
when a portfolio-level risk is NOT already captured by the per-opportunity-set views.

`rationale_codes` is ordered **business-priority, highest first**.

### Lineage
`task_id` (required value), `as_of_date` (environment as-of), `target_quarter`/`prior_quarter` (required values), `policy_id` = `POL_MULTI_ASSET_DEFAULT` for a balanced multi-asset reference model.

### Confirmed (train_003 rows all correct)
Europe OW/UP/MEDIUM/EUROPE_RECOVERY; Japan UW/DOWN/MEDIUM/JAPAN_POLICY_RISK; Emerging
Markets UW/DOWN/MEDIUM/CHINA_DEPENDENCE; India OW/UNCHANGED/HIGH/INDIA_OFFSET; Latin
America OW/UP/MEDIUM/LATAM_DIVERSIFIER; U.S. Treasuries OW/UP/MEDIUM/DURATION_SUPPORT;
Corporate High Yield UW/DOWN/MEDIUM/HY_VALUATION_RISK; EUR OW/UP/MEDIUM/EUROPE_RECOVERY.
(Asset classes: the 5 regional equities = Equities; U.S. Treasuries = Duration;
Corporate High Yield = Credit; EUR = Currency.)

---

## 4. Workflow: Committee JSON — correlation + allocation combined

Example: PF-MA-HELIO. Combines a 4-index correlation review with allocation views and
sleeve actions for a multi-asset sleeve.

### correlation_summary (length 2, ordered [highest_concentration, best_diversifier])
Compute Pearson correlations among the requested `index_ids` (same method as workflow 2).
- `highest_concentration` = the pair with the **maximum** correlation (the concentration-risk pair).
- `best_diversifier` = the pair with the **minimum** (most negative) correlation (the diversification pair).
- Each item: `{pair_role, pair (2 index ids sorted alphabetically), correlation (3 decimals)}`.

### target_sleeve_actions
Ordered exactly as the request lists the opportunity sets. For each `{opportunity_set, action}`:
- Map the concentrated sleeve to `trim`.
- Map overwatch-offset / diversifier sleeves to `add`.
- For a **defensive currency sleeve** (e.g. USD described as a "defensive offset"), use `hedge` (CONFIRMED: `hold` was wrong; the stale note calling it a "defensive offset" signals `hedge`).

### allocation_views
Same algorithm as workflow 3, but each row also includes `prior_view` (from prior-views)
and `signal_score` (3 decimals). Ordered as the request lists the opportunity sets.

### rebalance_trigger
Use `correlation_cap_breach` when the correlation high threshold (0.8) is breached by any
reviewed pair (CONFIRMED: `correlation_cap_breach` is correct; `committee_review` was
confirmed WRONG and dropped the score). The cap-breach finding is the substantive trigger;
do not use procedural `committee_review`.

### portfolio_risk_concentration_flag
`true` when the portfolio actually holds concentrated, highly-correlated sleeves (check
`/api/portfolios/<id>` holdings — e.g. EM + China sleeves that are 0.9+ correlated and
together a large share of the book).

### next_step
`approve_rotation` when a clear rotation plan (trim concentrated sleeve, add diversifier)
addresses the identified concentration (CONFIRMED: `approve_rotation` correct;
`approve_with_monitoring` was wrong).

### Stale local note
Refresh before submitting: ignore stale dated desk notes (e.g. "kept USD overweight…
did not include the final April index levels") and use the current environment index
levels and as-of date.

### Confirmed (train_005, 12/13)
correlation_summary highest `[IDX_CHINA, IDX_EM]` 0.915 / best `[IDX_CHINA, IDX_LATAM]`
−0.825; sleeve actions EM=trim, India=add, Latin America=add, USD=hedge; allocation views
EM UW/DOWN, India OW/UNCHANGED, LATAM OW/UP, USD N/DOWN; `rebalance_trigger=correlation_cap_breach`;
`portfolio_risk_concentration_flag=true`; `next_step=approve_rotation`.
(A residual convention gap remained in one sleeve-action mapping — when an overwatch
"offset" sleeve is OW but highly correlated with the concentrated sleeve, consider whether
`add` vs `rotate` is intended; `add` follows the OW view and is the default.)

---

## 5. Workflow: Fixed-income risk rebalance (SELL + BUY rotation)

Example: PF-FI-LUMEN (policy `POL_CREDIT_RISK_REDUCTION`).

### Data to pull
`/api/portfolios/<id>` (constraints: duration band, HY cap 20%, target_hy_reduction 4.0),
`/api/instruments/bonds`, `/api/issuers` (watchlist), `/api/policies`.

### Rotation design (confirmed direction via judge)
1. **Clear watchlist exposure**: SELL every watchlist HY bond (e.g. `BND_JUNIPER_2028`). `watchlist_exposure_cleared` requires post-trade watchlist market value = 0.
2. **Get HY under the 20% cap**: sell enough HY so post-trade HY% < 20%. Selling only the watchlist bond (leaving HY still over the cap) scored WORST — a rebalance must clear the cap.
3. **Preserve carry**: do NOT sell all HY. KEEP the highest-carry non-watchlist HY bond (highest `yield_to_maturity_pct` among non-watchlist HY) and sell the lower-carry HY to get under the cap. Selling ALL HY (HY→0) scored worse than keeping the best HY carry bond.
4. **Fund eligible IG candidates**: BUY non-watchlist IG candidates from the shortlist (exclude any watchlist HY candidate, e.g. `BND_JUNIPER_2030`). Prefer IG candidates that add duration ballast / diversification (e.g. `BND_QUARTZ_2031` data-center IG, `BND_IRONORE_2030` materials IG, `BND_BLUEGAS_2030` LNG IG).
5. **Avoid a duration shortfall**: selling low-duration HY and buying higher-duration IG raises portfolio duration (no shortfall); keep post-trade weighted duration inside [3.0, 5.0].

### Stale exception-board quantities
The local "stale_exception_board" quantities may differ from the current portfolio; use
the **current** environment holdings quantities.

### Output fields
- `task_id`, `portfolio_id`, `as_of_date` (environment as-of).
- `rotation.trades`: list sorted **SELL before BUY, then by instrument_id ascending within each action**. Each `{action ("BUY"/"SELL"), instrument_id, quantity_usd_m (precision 1)}`.
- `risk_metrics`:
  - `post_trade_hy_allocation_pct` (precision 2) = post-trade HY market value / total × 100.
  - `post_trade_duration_years` (precision 2) = Σ(mv × modified_duration) / total.
  - `hy_reduction_pct_points` (precision 2) = pre-trade HY% − post-trade HY%.
  - `post_trade_watchlist_exposure_usd_m` (precision 1) = 0.0 after clearing watchlist.
- `exception_flags` (booleans): `hy_cap_pass` (post HY < 20), `duration_band_pass` (post duration in [3,5]), `target_hy_reduction_met` (reduction ≥ target_hy_reduction_pct), `watchlist_exposure_cleared` (watchlist mv = 0).
- `watchlist_handling`: `watchlist_sell_ids` (ascending instrument_id — only the watchlist bonds sold; non-watchlist HY sold for cap reduction are NOT listed here), `buys_avoid_watchlist` (true).
- `risk_note_code` ∈ {hy_cap_pressure, watchlist_concentration, duration_preservation, carry_tradeoff, no_action}: pick the code matching the rotation's salient risk theme (e.g. the dominant pre-trade issue is HY-cap pressure when HY is far over the cap; watchlist_concentration when the watchlist issuer is the headline; carry_tradeoff when the rotation deliberately retains carry).

### Confirmed direction (train_004)
Pre-trade LUMEN: HY 31/78 = 39.74% (far over 20% cap), watchlist = JUNIPER 12.0.
Best-scoring rotation shape: SELL JUNIPER (watchlist) + SELL one lower-carry HY (NOVA),
KEEP LUMEN (highest-carry HY), BUY non-watchlist IG; result HY ≈ 14%, under cap,
watchlist 0, duration in band. (Exact buy sizing/note code still had residual convention
gap — the structural rules above are the transferable lesson.)

---

## 6. Quick precision/ordering checklist
- Correlations: 3 decimals. pair ids sorted alphabetically. observations = levels − 1.
- Trade/rotation lists: respect each template's stated ordering (ascending instrument_id; or SELL-before-BUY then instrument_id).
- Money precisions: `notional_usd_m` / `quantity_usd_m` / `post_trade_watchlist_exposure_usd_m` = 1 decimal; `total_market_value_usd_m`, `hy_allocation_pct`, weighted duration/YTM, `post_trade_duration_years`, `hy_reduction_pct_points` = 2 decimals; `signal_score` = 3 decimals.
- Always derive the answer from the **current environment** data, never from a stale local worksheet; only prefer a local payload when the prompt explicitly instructs it.
- Enum values must match the template's allowed values exactly (case and underscores).
