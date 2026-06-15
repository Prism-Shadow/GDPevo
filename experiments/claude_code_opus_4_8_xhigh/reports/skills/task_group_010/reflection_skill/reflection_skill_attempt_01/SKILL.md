---
name: asteria-investment-office-desk
description: >
  Solve Asteria Investment Office CIO / credit-desk JSON tasks (energy-credit BUY packages,
  fixed-income risk-reduction rotations, equity-correlation reviews, quarterly active-allocation
  refreshes, and multi-asset committee files). Use when a prompt references the Asteria shared
  environment (http://127.0.0.1:8036), a PF-* portfolio, opportunity-set allocation views, index
  correlation reviews, HY/duration/watchlist credit constraints, or an answer_template.json that
  must be filled from environment data. Encodes the exact formulas, enum mappings, selection logic,
  and business-judgment rules required, and the specific pitfalls that cause wrong answers.
---

# Asteria Investment Office — CIO / Credit Desk SOP

You produce ONE JSON object per task that conforms exactly to the task's
`input/payloads/answer_template.json`. The shared HTTP API is the book of record; local payloads
are intake context that may be STALE. Output only JSON (no prose) unless asked otherwise.

## 0. Environment access (always do this first)

All data is read-only GET JSON at base `http://127.0.0.1:8036`. Key endpoints:
`/api/catalog`, `/api/policies`, `/api/portfolios`, `/api/portfolios/<id>`,
`/api/instruments/bonds` (filter `?candidate=true`), `/api/issuers`, `/api/market/energy`,
`/api/indices`, `/api/index-levels`, `/api/index-levels/<id>`,
`/api/allocation/opportunity-sets`, `/api/allocation/prior-views`, `/api/macro-signals`.

Universal rules:
- **`as_of_date` = the environment `as_of_date`** (read it from `/api/policies` or any
  `/api/portfolios/<id>`), NOT the date on a local payload/memo. (It has been 2026-05-29, but
  always read it live.)
- **Environment overrides stale local payloads** for marks, ratings, holdings, quantities,
  watchlist, index levels, macro scores, policy numbers. When a payload disagrees, the environment
  wins. For the conflict-disclosure enum use `current_environment_over_stale_payload` whenever the
  live portfolio differs from the snapshot in the payload (it almost always does — e.g. payload MV
  vs live MV). Compute every metric from LIVE holdings/quantities, never from the stale snapshot.
- Round every numeric field to the precision the template declares. Keep trailing-zero values as
  numbers (e.g. `0.0`, `14.10`); do not drop precision.
- Apply every ordering rule literally (e.g. "ascending by instrument_id", "SELL before BUY then
  id ascending", "by the payload's focus order", pair ids "alphabetical").

## 1. Policy numbers (read from `/api/policies`, do not hardcode)

- Credit constraints (`credit_default` / `credit_risk_reduction`): `max_hy_allocation_pct` (20.0),
  `duration_band_years` ([3.0, 5.0]), `issuer_concentration_limit_pct` (12.0),
  `subsector_min_count_for_diversified` (2). `credit_risk_reduction` adds
  `target_hy_reduction_pct` (4.0); `credit_default` has it = 0.0.
- Allocation mapping (`allocation_mapping`): view thresholds `OW_min=0.35`, `UW_max=-0.35`,
  neutral in (-0.35, 0.35); conviction `HIGH if |score|>=0.7`, `MEDIUM if |score|>=0.35`, else
  `LOW`. View rank {UW:-1, N:0, OW:1}.
- Correlation (`correlation`): `high_threshold=0.8`, `low_threshold=0.2`, review window
  `2025-05-30 .. 2026-04-30`.

### PITFALL — lineage `policy_id`
For a `policy_id` LINEAGE / "policy version" field, use the **top-level `policy_id` of the
`/api/policies` document** (the policy-set stamp, e.g. `POLICY_SET_2026_05`). Do NOT substitute a
bundle id like `POL_MULTI_ASSET_DEFAULT` or the mapping policy `POL_ALLOCATION_MAPPING`. (A
portfolio's own `constraints.policy_id` is a different field — use that only when the template asks
for the policy actually governing that one portfolio.)

## 2. Weighted portfolio metrics (quantity-weighted)

All portfolio-level metrics are weighted by `quantity_usd_m` (market value in USD millions):
- `total_market_value_usd_m` = sum of all post-trade quantities.
- `hy_allocation_pct` = (sum quantity where `rating_bucket=="HY"`) / total * 100.
- `weighted_modified_duration_years` = sum(qty * `modified_duration_years`) / total.
- `weighted_yield_to_maturity_pct` = sum(qty * `yield_to_maturity_pct`) / total.
- `hy_reduction_pct_points` = base HY% (pre-trade) − post-trade HY%.

Join each holding/candidate `instrument_id` to `/api/instruments/bonds` for
`rating_bucket`, `modified_duration_years`, `yield_to_maturity_pct`, `subsector`, `issuer_id`.
Join `issuer_id` to `/api/issuers` for `watchlist`. Watchlist is at the ISSUER level — every bond
of a watchlisted issuer is watchlist-tainted.

## 3. Bond SELECTION logic (BUY packages and rotations)

This is the highest-risk area. The desk does **not** simply maximize carry to the cap.

### 3a. Eligibility filters (apply ALL, then select among survivors)
1. Right universe: `candidate=true`; for energy tasks also `energy_linked=true`.
2. **Exclude any bond whose issuer is on the watchlist** (`/api/issuers` `watchlist=true`).
3. **Per-instrument duration screen**: each selected bond's OWN `modified_duration_years` must lie
   inside the duration band [3.0, 5.0]. This excludes long-dated names (e.g. dur 5.4, 5.9, 6.7)
   even when their carry is highest. (Blind error: picking a high-YTM bond with individual
   duration > 5.0.)
4. Diversification: the selected set must span ≥2 distinct `issuer_id` and ≥2 distinct
   `subsector` (`subsector_min_count_for_diversified`).
5. Post-trade portfolio constraints must hold: `hy_allocation_pct <= max_hy_allocation_pct`,
   weighted duration inside band.

### 3b. Choosing among eligible sets — moderate risk, not max carry
The objective is "improve expected carry while staying inside constraints" AND being suitable for
the stated client/committee context (income pitch, watchlist-sensitive committee). The correct
package is the **best-carry MODERATE-risk package, not the carry-maximizing one that pushes HY to
the cap.**

For a 2-ticket energy income BUY package (split evenly):
- Prefer **one IG anchor + one HY carry leg** (keeps post-trade HY at the moderate tier with a
  comfortable buffer below the 20% cap) over two HY legs (which jam HY against the cap).
- **Anchor the IG leg on the strongest current energy signal.** Read `/api/market/energy`
  `signals[].score`; the highest-score theme (e.g. LNG) dictates the anchor. Pick the IG bond
  whose `recommended_theme_tags` match that theme (e.g. `LNG_EXPORTS`) — this also sets the
  `sales_positioning.theme` enum (e.g. `lng_export_tailwind`).
- For the HY leg, take the **highest-carry non-watchlist HY bond that passes the per-instrument
  duration screen and sits in a distinct subsector** from the anchor.
- Among near-ties, prefer the bond matching the dominant theme/highest signal.
- Pitfall: do NOT chase the single highest post-trade weighted YTM if it requires two HY legs or
  an out-of-band-duration bond. Negative/negative-signal subsectors (e.g. refining when its signal
  is negative) are exactly the watchlisted names to avoid.

### 3c. Fixed-income risk-reduction rotation (notional-neutral)
Style = "sell existing pressure points and fund current eligible candidates," keeping total
notional constant (sum SELL = sum BUY).
- **SELL** the binding-risk holdings: every watchlisted holding (mandatory) plus enough HY
  holdings to meet `target_hy_reduction_pct` and the HY cap. Keep a HY carry name if HY can still
  satisfy the cap/target without it (do not zero out carry unnecessarily).
- **BUY**: fund from the candidate shortlist, using **ALL eligible (non-watchlist) shortlisted
  candidates**, not a subset. (Blind error: funding only 2 of 3 eligible candidates.) Exclude the
  watchlisted shortlist name even if it has the highest carry.
- Split the buy notional across the eligible candidates so post-trade weighted duration lands
  comfortably inside [3.0, 5.0] (weight more to the longer-duration IG names for duration
  ballast/preservation). The exact split is judgment; verify the post-trade duration is in band
  and recompute metrics from it.
- `watchlist_sell_ids` = sold watchlisted ids (ascending). `buys_avoid_watchlist=true` when no buy
  is watchlisted. `post_trade_watchlist_exposure_usd_m` = remaining watchlisted notional (0.0 if
  cleared). Exception flags are booleans on the post-trade state vs the policy thresholds.

### PITFALL — `risk_note_code` / primary-driver enums
Pick the enum that names the **binding driver actually resolved**, not a generic one. When the
rotation's defining action was clearing watchlisted exposure, use `watchlist_concentration` rather
than `hy_cap_pressure`. Read the memo: which constraint was the explicit reason for the trade?
Map to the closest enum describing that driver.

## 4. Index correlation reviews

- Returns: monthly **simple returns** `r_t = L_t / L_{t-1} − 1` from `/api/index-levels`.
- The review window has **12 monthly levels → 11 return observations** (`return_observations=11`).
  Use the window in the request payload / `/api/policies` correlation window.
- Correlation = **Pearson** over those 11 returns, rounded to 3 decimals.
- Pair ids inside every pair are sorted **alphabetically**; index_set is ascending alphabetical.
- `highest_positive` / `highest_concentration` = max correlation pair; `lowest` /
  `best_diversifier` = min (most negative) correlation pair, over the requested sub-universe.
- Concentration flag: a China/Asia bloc with intra-bloc correlations above `high_threshold` (0.8)
  → `china_asia_dependence_flag=true`, `primary_code=CHINA_ASIA_DEPENDENCE`,
  `high_threshold_breached=true`. For the committee `rebalance_trigger`, a breach of the
  correlation high threshold = `correlation_cap_breach`;
  `portfolio_risk_concentration_flag=true`.

### PITFALL — diversification candidates are GENUINE diversifiers only
When choosing `diversification_candidates` from an allowed list, include only indices that
**actually reduce** the flagged dependence — i.e. low or negative correlation to the concentration
driver. **Exclude an index that is itself part of the high-correlation bloc**, even if it is a
distinct growth story. (Blind error: including IDX_INDIA, which has the HIGHEST correlation to the
China/Asia bloc, as a "diversifier." India is a growth OFFSET in the macro view but is NOT a
correlation diversifier.) Map each memo concern code to its true structural fix:
- "reduce broad Asia/China beta overlap" → the ex-China breadth index (IDX_EM_EX_CHINA).
- "low-correlation diversifier" → the genuinely low/negative-correlation index (IDX_LATAM).
- A "dedicated China sleeve" concern is about trimming China itself, not adding a new sleeve.

For `sleeve_actions`: `sleeve` = the portfolio holding's `sleeve` string (e.g. "China",
"Latin America"); `target_index_id` = that holding's `instrument_id`. Trim the over-concentrated
sleeve (China/IDX_CHINA), add the best diversifier (Latin America/IDX_LATAM). Order ascending by
`sleeve`.

## 5. Active-allocation view derivation (per opportunity set)

For each requested opportunity set and target quarter:
1. **score**: `/api/macro-signals` row matching `opportunity_set` AND `quarter` → its `score`
   (a.k.a. `signal_score`, report at the template precision).
2. **view**: map score via allocation thresholds — `OW` if score >= 0.35, `UW` if score <= -0.35,
   else `N`.
3. **conviction**: `HIGH` if |score| >= 0.7, `MEDIUM` if |score| >= 0.35, else `LOW`.
4. **rationale_code**: the `rationale_code` on that same macro-signal row.
5. **prior_view**: `/api/allocation/prior-views` row with `opportunity_set` and
   `quarter == target_quarter` (this row carries the stance brought in from the prior quarter; its
   `previous_quarter` = the prior quarter). Use its `view` as `prior_view`.
6. **change**: compare derived view rank to prior_view rank {UW:-1, N:0, OW:1} → `UP` / `DOWN` /
   `UNCHANGED`.
7. **asset_class**: from `/api/allocation/opportunity-sets` (`Equities` / `Duration` / `Credit` /
   `Currency`).

This derivation was verified correct end-to-end; reproduce it exactly. Currencies (USD/EUR) follow
the same score→view mapping.

### Sleeve action from the resulting view (committee files)
Map the **RESULTING view** (not the change direction) to a sleeve action:
- Equity `OW` → `add` (even if change is UNCHANGED — e.g. a sustained OW conviction still says add).
- Equity `UW` → `trim`. Equity `N` → `hold`.
- **Currency** that lands `N` after being `OW` (defensive overweight neutralized) → `hedge`
  (keep it as a hedge, do not `trim` it like an equity). (Blind errors: India OW/UNCHANGED → `hold`
  should be `add`; USD OW→N → `trim` should be `hedge`.)

### PITFALL — risk-overlay rationale codes come from the FOCUS rows
The portfolio `risk_overlay` (overlay_code + primary_action + rationale_codes):
- Choose the overlay theme implied by the cross-set views. When duration/Treasuries are OW and
  HY/EM are UW, that is a duration/quality tilt away from credit & risk beta →
  `DURATION_QUALITY_TILT` / `tilt_to_duration_quality`.
- **`rationale_codes` MUST be drawn only from the rationale codes that actually appear in the
  derived focus rows** — never invent a code that is not among the focus set's own rows. (Blind
  error: adding `RATE_CUT_SUPPORT`, which appears only on non-focus sets like German Bunds/IG.)
- Pick the codes that thematically support the chosen overlay, ordered by business priority
  (the duration-add driver first, then the risk-reduction UW drivers, e.g. DURATION_SUPPORT →
  HY_VALUATION_RISK → CHINA_DEPENDENCE).

### Committee decision enums
`next_step`: when constraints are not breached but a concentration warrants oversight, use
`approve_with_monitoring`; `reject_constraint_breach` only on a hard breach;
`defer_pending_risk_review` when more analysis is required.

## 6. Pre-submission checklist
- [ ] `as_of_date` taken from the live environment, not a payload date.
- [ ] All metrics computed from LIVE holdings/quantities; `data_precedence` set correctly.
- [ ] Every numeric rounded to template precision (trailing zeros preserved).
- [ ] All orderings applied (id ascending / SELL-before-BUY / payload focus order / alphabetical
      pairs / ascending sleeve).
- [ ] Bond picks pass per-instrument duration screen + watchlist exclusion + 2-issuer/2-subsector
      diversification; package is best-carry MODERATE risk, not carry-maxed to the HY cap; all
      eligible shortlist candidates funded.
- [ ] Correlations from 11 monthly simple returns, Pearson, 3 decimals; diversification candidates
      are genuine (low/negative-corr) diversifiers only.
- [ ] Views/conviction/change/rationale derived from the matching macro-signal + prior-view rows;
      sleeve actions keyed off the resulting view (currency-N → hedge).
- [ ] `policy_id` lineage = top-level `/api/policies` policy-set id.
- [ ] Overlay rationale_codes are a subset of the derived focus rows' rationale codes.
- [ ] Enum driver fields (`risk_note_code`, `theme`, `rebalance_trigger`, `next_step`) name the
      actual binding driver.
- [ ] Output is exactly the template shape — no extra keys, no narrative.
