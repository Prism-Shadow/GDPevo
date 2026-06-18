---
name: asteria-cio-credit-desk
description: >-
  Produce JSON deliverables for the Asteria Investment Office CIO / credit-desk
  task family: energy-credit trade packages, fixed-income risk-reduction
  rotations, international-equity correlation reviews, active allocation-view
  refreshes, and multi-asset committee decision files. Use whenever a task names
  an Asteria portfolio (PF-EN-*, PF-FI-*, PF-INT-*, PF-MA-*), references the
  shared Asteria environment (http://127.0.0.1:8036) as book of record, supplies
  a desk_request / review_request / allocation_request / risk_meeting_memo /
  committee_request payload, and asks for a JSON answer conforming to an
  answer_template.json. Covers correlation, view-mapping, HY/duration/watchlist
  constraints, enum selection, rounding, and ordering rules.
---

# Asteria Investment Office — CIO / Credit Desk SOP

This skill encodes the corrected, verified rules for the Asteria task family. It
exists to prevent the specific mistakes that occur when these tasks are solved
quickly from intuition. Read the "Pitfalls" section before answering — most
errors are not arithmetic; they are wrong source fields, wrong enum choices, and
**over-trading**.

## 0. Golden rules (cause of most failures)

1. **Environment is the only book of record.** Always pull current data from the
   HTTP API. Local payloads (desk_request, memo, snapshot, "stale_*" blocks) are
   intake context and are frequently stale (wrong notionals, marks, ratings,
   watchlist status, dates). When they disagree, the environment wins, and set
   any `data_precedence` field to `current_environment_over_stale_payload`.
2. **`as_of_date` = the environment's current date**, not any date in the
   payload. It is identical across endpoints: read it from
   `/api/policies` (top-level `as_of_date`) or any `/api/portfolios/<id>`
   (`as_of_date`). For this distribution it is the same value everywhere.
3. **`policy_id` (lineage) = the TOP-LEVEL policy-set id from `/api/policies`**
   (the `policy_id` at the root of the policies object, e.g. a `POLICY_SET_*`
   value). Do NOT use a sub-policy id (`POL_ALLOCATION_MAPPING`,
   `POL_CREDIT_DEFAULT`, etc.) for a lineage/`policy_id` field. Sub-policy ids
   only appear inside a specific portfolio's `constraints` block.
4. **Do not over-trade.** The rebalance/trade tasks reward the *minimum*
   proportionate action that satisfies the constraints with margin — not the
   maximal one. Driving HY to 0%, selling every flagged position, or buying the
   full requested notional when smaller works are classic over-trading errors.
5. **Pick enums from the data, never invent.** Every enum value you emit
   (rationale_code, theme, view, action, risk_note_code, primary_code, …) must
   be (a) in the template's allowed_values AND (b) justified by an actual signal,
   holding, or threshold you read. Never insert a plausible-sounding code (e.g.
   `RATE_CUT_SUPPORT`) that is not present in the relevant rows you used.
6. **Honor the template literally**: required keys, enum `allowed_values`, list
   lengths, item ordering, `required_value` constants, and per-field `precision`.
   Round each numeric to the declared precision. Output only the JSON object.

## 1. Environment API (read-only GET, base http://127.0.0.1:8036)

- `/api/catalog` — ids for portfolios, policies, indices, issuers, bonds, opportunity_sets.
- `/api/policies` — **top-level `policy_id` and `as_of_date`**; sub-objects:
  `allocation_mapping`, `correlation`, `credit_default`, `credit_risk_reduction`,
  `multi_asset`, `multi_asset_risk`.
- `/api/portfolios/<id>` — `objective`, `constraints` (with its own `policy_id`),
  `holdings` (`instrument_id`, `quantity_usd_m`, `sleeve`), `market_value_usd_m`,
  `as_of_date`.
- `/api/instruments/bonds` — `rating_bucket` (IG/HY), `modified_duration_years`,
  `yield_to_maturity_pct`, `subsector`, `issuer_id`, `energy_linked`, `candidate`,
  `recommended_theme_tags`, `spread_bps`.
- `/api/issuers` — `watchlist` (bool), `credit_outlook`, `sector`, `subsector`,
  `rating_bucket`. **Watchlist status lives on the ISSUER, not the bond.**
- `/api/market/energy` — `signals` (per-commodity score/direction), `pitch_themes`.
- `/api/indices`, `/api/index-levels`, `/api/index-levels/<id>` — monthly levels.
- `/api/allocation/opportunity-sets` — `asset_class`, `sub_asset_class`, `display_order`.
- `/api/allocation/prior-views` — rows keyed by `quarter` + `previous_quarter`.
- `/api/macro-signals` — rows keyed by `quarter`: `score`, `rationale_code`, `drivers`.

Filters: most list endpoints accept equality filters (`?candidate=true`,
`?rating_bucket=HY`, `?quarter=Q2_2026`, …). Verify by re-querying.

## 2. Canonical formulas (verified against official answers)

**Portfolio metrics** — quantities (`quantity_usd_m`) are used as market-value
weights; total market value = sum of post-trade quantities (a notional-neutral
swap keeps total MV unchanged).
- `total_market_value = Σ quantity_usd_m` over post-trade positions.
- `hy_allocation_pct = 100 * (Σ quantity over positions with rating_bucket=="HY") / total_market_value`.
- `weighted_modified_duration = Σ(quantity * modified_duration_years) / total_market_value`.
- `weighted_yield_to_maturity_pct = Σ(quantity * yield_to_maturity_pct) / total_market_value`.
- `watchlist_exposure_usd_m = Σ quantity over positions whose ISSUER has watchlist==true`.
- `hy_reduction_pct_points = pre_trade_hy_pct - post_trade_hy_pct`.
Round each to the template's precision (typically 2 for percents/years, 1 for notionals).

**Correlations** (correlation-review / committee tasks):
- Use monthly **simple** returns `r_t = level_t / level_{t-1} - 1` over the
  requested level window (inclusive of both endpoints). With 12 monthly levels you
  get **11 return observations** → `return_observations = 11`.
- Use the policy correlation window (`/api/policies.correlation`:
  `review_window_start`/`review_window_end`) when the task says "current 12-month
  window" and gives no explicit dates.
- `correlation` = Pearson on the return series, rounded to **3 decimals**.
- Pair ids are sorted **alphabetically** within each pair.
- `highest_positive` / `highest_concentration` = the max-correlation pair;
  `lowest` / `best_diversifier` = the min-correlation pair (most negative).
- `high_threshold_breached` / `correlation_cap_breach`: true when the max pair
  correlation ≥ `correlation_high_threshold` (0.8). Low threshold (0.2) flags
  diversifiers. (Thresholds come from `/api/policies.correlation`.)

**Active view mapping** (allocation-refresh / committee tasks) — driven by
`/api/policies.allocation_mapping`:
- `signal_score` = the `score` from `/api/macro-signals` for that
  `opportunity_set` and the **target** `quarter`.
- `view`: OW if `score ≥ OW_min` (0.35); UW if `score ≤ UW_max` (-0.35); else N.
- `conviction`: HIGH if `|score| ≥ HIGH_abs_min` (0.7); MEDIUM if `|score| ≥ 0.35`; else LOW.
- `rationale_code`: take the `rationale_code` field straight from that macro-signal row.
- `prior_view`: from `/api/allocation/prior-views`, the row whose
  `quarter == target_quarter` (its `previous_quarter` equals the prior quarter).
  The `view` stored on that row is the PRIOR view entering the refresh.
  (Sanity check: the next quarter's prior-views rows equal your computed views.)
- `change`: rank(view) vs rank(prior_view) using `view_rank` (UW=-1, N=0, OW=1) →
  UP / DOWN / UNCHANGED.
- `asset_class` (when required): from `/api/allocation/opportunity-sets`.

## 3. Task-type playbooks

### A. Energy / credit BUY package (e.g. PF-EN-*)
1. Build eligible candidate set: `candidate==true`; match requested exposure
   (e.g. `energy_linked==true`); exclude bonds whose issuer is `watchlist==true`.
2. Honor ticket count and total notional and the split rule (e.g. "two tickets,
   evenly split" → each = total/2).
3. Lead with the dominant macro theme (read `/api/market/energy`: highest-score
   signal, e.g. LNG → theme `lng_export_tailwind`). The package must remain
   suitable for the stated client pitch.
4. Enforce post-trade: HY% ≤ `max_hy_allocation_pct` (20), duration inside
   `duration_band_years` ([3,5]); the selected picks must satisfy
   issuer-diversification (distinct issuers) and subsector-diversification
   (≥ `subsector_min_count_for_diversified`, i.e. distinct subsectors) and
   watchlist avoidance. Prefer headroom under the HY cap and a clean income
   pitch over squeezing out maximum raw carry.
5. Set constraint_checks booleans honestly; `data_precedence` per Golden rule 1;
   sort trade_package by `instrument_id` ascending.

### B. Fixed-income risk-reduction rotation (e.g. PF-FI-*)
Objective is "reduce HY and watchlist pressure WITHOUT a duration shortfall and
WITHOUT destroying carry." This is the task most prone to over-trading.
1. **Sell side — be surgical, not maximal:**
   - You MUST sell every holding whose issuer is on the watchlist (to drive
     `watchlist_exposure` to 0 / `watchlist_exposure_cleared`).
   - Then sell *just enough additional HY* to (a) bring HY% under the cap with
     margin and (b) meet/exceed the memo's `minimum_preferred_hy_reduction_pct_points`
     and the policy `target_hy_reduction_pct`. **Do not sell all HY / do not
     drive HY to 0%** — retain HY carry where the cap and target already pass.
   - Prefer selling the *lower-duration* HY names so the remaining/post-trade
     duration stays inside the band (selling short-duration raises avg duration).
   - Use CURRENT holdings/quantities from the portfolio endpoint, not the memo's
     stale exception-board quantities.
2. **Buy side:** only `candidate==true`, IG (`rating_bucket=="IG"`), non-watchlist
   bonds; `buys_avoid_watchlist` must be true. Exclude any candidate whose issuer
   is watchlisted even if the memo shortlisted it.
3. **Sizing:** fund from the sale proceeds (typically MV-neutral). Size buys so
   the weighted duration lands comfortably inside [3,5]; tilting more notional to
   longer-duration IG offsets duration lost from the sales. Do not blindly
   replace the full sold notional 1:1 across all candidates if a smaller, in-band
   package satisfies all constraints.
4. **risk_note_code:** choose the code naming the PRIMARY risk actually resolved.
   If the rotation's defining action is clearing watchlist names, use
   `watchlist_concentration`; use `hy_cap_pressure` only when the cap breach (not
   watchlist) is the singular driver. Match the note to the dominant story.
5. **Ordering:** trades sorted SELL before BUY, then `instrument_id` ascending
   within each action. `watchlist_sell_ids` ascending. Recompute all
   `risk_metrics` and `exception_flags` from the actual post-trade book.

### C. International-equity correlation review (e.g. PF-INT-*)
1. `return_observations`, correlations, extreme pairs per Section 2.
2. `concentration.primary_code`: `CHINA_ASIA_DEPENDENCE` when the China/Asia/EM
   cluster pairs exceed the high threshold; else `GLOBAL_DEVELOPED_OVERLAP` or
   `NO_MATERIAL_CONCENTRATION`. `china_asia_dependence_flag` and
   `high_threshold_breached` set from the actual max-correlation pair vs 0.8.
3. **`diversification_candidates` — pick by diversification ROLE, not raw
   correlation alone.** From the template's allowed pool, include a candidate
   only if it genuinely reduces the identified concentration:
   - the structural ex-concentration sleeve (e.g. **EM ex-China** directly
     addresses a dedicated-China concentration), AND
   - any sleeve with low/negative correlation to the concentration anchor
     (e.g. **Latin America**).
   - **Exclude** a candidate that is itself inside the high-correlation cluster
     (correlation to the concentration anchor ≥ high threshold 0.8) — e.g. India
     correlating ~0.85 to China is part of the problem, not a diversifier, even
     though it is a separate sleeve.
   Map the memo's concern_codes to candidates (a "dedicated China sleeve" concern
   → the ex-China structural candidate; a "low correlation diversifier" concern →
   the low-correlation candidate). Return the list alphabetically; it can have
   more than one entry. (A common error is returning only the single lowest-
   correlation name and dropping the structural ex-China candidate.)
4. `sleeve_actions`: trim the concentration source sleeve; add the diversifier
   sleeve. Use the allowed action and target_index enums; order ascending by sleeve.

### D. Active allocation-view refresh (CIO desk, multiple opportunity sets)
1. One row per focus opportunity_set, in the payload's `focus_opportunity_sets`
   order. Derive view/change/conviction/rationale_code per Section 2; pull
   `asset_class` from the opportunity-set taxonomy.
2. `policy_id` = top-level policy-set id (Golden rule 3). `as_of_date`,
   `target_quarter`, `prior_quarter`, `task_id` per template constants.
3. **`risk_overlay`:**
   - Choose `overlay_code` + matching `primary_action` from the net tilt the
     rows imply. A strong duration OW (e.g. US Treasuries positive) plus an HY UW
     points to `DURATION_QUALITY_TILT` / `tilt_to_duration_quality`. A dominant
     credit-risk story → `CREDIT_RISK_REDUCTION` / `trim_credit_beta`. Risk-on
     equity breadth → `EQUITY_BETA_EXTENSION`. Currency defense →
     `CURRENCY_DEFENSIVE_HEDGE`. Otherwise `NO_OVERLAY` / `hold_policy_weights`.
   - **`rationale_codes` must be the codes that JUSTIFY the chosen overlay**,
     drawn from the actual focus-set macro-signal rows, ordered by business
     priority. For a duration-quality tilt the order is: duration support first
     (`DURATION_SUPPORT`), then the credit-de-risking driver
     (`HY_VALUATION_RISK`), then the dominant equity risk (e.g.
     `CHINA_DEPENDENCE`). **Do NOT** include risk-ON rationales
     (`INDIA_OFFSET`, `LATAM_DIVERSIFIER`, `EUROPE_RECOVERY`) — they do not
     support a defensive overlay even if their |score| is high. **Do NOT**
     invent a code (e.g. `RATE_CUT_SUPPORT`) that is not present among the
     focus-set rows you used.

### E. Multi-asset committee file (e.g. PF-MA-*)
Combines C (correlation summary on the requested index subset) and D (allocation
views on the requested opportunity sets, including currency like USD).
1. `correlation_summary`: highest_concentration + best_diversifier pairs (Section 2),
   3 decimals, pairs alphabetical, item order per template
   (`highest_concentration` then `best_diversifier`).
2. `allocation_views`: full mapping per Section 2 (prior_view, signal_score, view,
   change, conviction, rationale_code) for each opportunity set in the template's
   item order. For a currency like USD, `rationale_code` is whatever the macro row
   says (e.g. `NEUTRAL_BALANCE` when that is the row's code — do not force
   `DOLLAR_DEFENSIVE`).
3. **`target_sleeve_actions` must FOLLOW the derived views**, not default to
   `hold`:
   - view OW → `add`; view UW → `trim`.
   - For an equity sleeve at N → `hold`/`monitor`.
   - For a defensive currency sleeve being reduced from OW (USD moving down) →
     `hedge`, not `hold`.
   (Blind error: emitting `hold` for an OW sleeve, or `hold` instead of `hedge`
   for a de-risked currency sleeve.)
4. `rebalance_trigger` = `correlation_cap_breach` when the top pair ≥ high
   threshold; `portfolio_risk_concentration_flag` = that breach boolean.
   `next_step` = `approve_with_monitoring` when there is a flagged concentration
   but the proposed views/actions are coherent (not a hard breach requiring
   rejection or deferral).

## 4. Pitfalls checklist (each maps to a real blind-solve error)

- [ ] Used the **top-level** `policy_id` from `/api/policies` for lineage — not a
      sub-policy id like `POL_ALLOCATION_MAPPING`.
- [ ] Did **not** over-trade: kept residual HY carry (did not zero HY), sold only
      watchlist + the minimum extra HY, sized buys for an in-band package.
- [ ] `risk_note_code` / triggers / enums reflect the PRIMARY risk addressed
      (e.g. `watchlist_concentration` when clearing watchlist names dominates).
- [ ] `diversification_candidates` includes the structural ex-China candidate AND
      the low-correlation candidate; excluded high-correlated sleeves (India);
      returned all qualifying names, not just one.
- [ ] `risk_overlay.rationale_codes` are the overlay-justifying codes from real
      focus rows, in business-priority order; no invented codes; no risk-on codes.
- [ ] `target_sleeve_actions` follow the views (OW→add, UW→trim, defensive
      currency→hedge), not blanket `hold`.
- [ ] Currency `rationale_code` taken from the actual macro row.
- [ ] Watchlist read from issuer endpoint; current holdings/quantities from the
      portfolio endpoint (ignored stale memo notionals/snapshots).
- [ ] Correlations: 11 obs, simple returns, Pearson, 3 decimals, alphabetical pairs.
- [ ] `as_of_date` = environment current date; `data_precedence` reflects the
      stale-vs-current conflict.
- [ ] All numerics rounded to template precision; lists ordered as specified;
      output is exactly the required JSON shape and nothing else.

## 5. Always verify by recomputation

Before emitting: re-pull the portfolio, recompute post-trade HY%, duration, YTM,
watchlist exposure, and reduction from the actual post-trade book; recompute every
correlation/view from the raw endpoint data. Confirm each enum value exists in the
template's allowed_values and is supported by a value you actually read. Confirm
list lengths, ordering, and constant `required_value` fields.
