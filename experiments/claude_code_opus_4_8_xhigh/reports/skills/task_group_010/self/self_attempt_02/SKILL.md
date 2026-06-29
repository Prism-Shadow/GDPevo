---
name: asteria-investment-office-json-desk
description: >
  Repeatable workflow for the Asteria Investment Office desk JSON tasks. Covers five
  archetypes: (a) energy-credit trade-package selection, (b) international equity
  correlation review, (c) active allocation view refresh, (d) fixed-income risk
  rebalance, (e) multi-asset committee decision. Explains which HTTP endpoints to
  call, the exact computation recipes (Pearson correlation from monthly simple
  returns, weighted modified duration, HY allocation %, weighted YTM, issuer
  concentration %), the policy thresholds to apply, and the precise output-schema
  conventions (field names, enum value sets, rounding precision, id ordering).
  Treats the shared environment as the book of record and reconciles stale local
  payloads against it.
---

# Asteria Investment Office — Desk JSON Workflow

You produce a single JSON object that conforms to the task's
`input/payloads/answer_template.json`. The shared **Asteria** environment is a
read-only HTTP API and the **current book of record**. Local payloads (desk
requests, memos, snapshots, "stale notes") are intake context only and may be
stale — **when they disagree with the environment, the environment always wins.**

## 0. Universal SOPs (apply to every task)

1. **Environment is authoritative.** Re-pull every number you use from the API.
   Never trust a quantity, rating, watchlist flag, duration, view, or score that
   only appears in the local payload. If a payload field conflicts with the env,
   use the env value and (where the schema asks) flag the precedence as
   "current_environment_over_stale_payload". If nothing conflicts, "no_conflict_found".
2. **Read the answer_template first and obey it literally.** It declares the
   exact top-level keys, required values (e.g. `portfolio_id`), enum value sets,
   numeric `precision` (decimal places), units, list `length`/`required_length`,
   and **ordering rules**. Mismatched enum spelling, wrong rounding, or wrong sort
   order are failures even when the analysis is right.
3. **as_of_date / lineage.** Use the environment's current as-of date for output
   `as_of_date` fields (do not copy the payload's stale date). At the time this
   skill was written the env-wide as-of date was the value returned by
   `/api/policies` (`as_of_date`) and matched each portfolio's `as_of_date`. Pull
   it live; do not hard-code.
4. **Rounding.** Round only at the end, to the precision the template states
   (e.g. correlations to 3 decimals, %/years to 2, notional to 1). Carry full
   precision through intermediate math.
5. **id ordering.** Where the template says "alphabetical", sort index/instrument
   ids as plain ascending strings. For index *pairs*, sort the two ids inside the
   pair alphabetically too. Trade lists usually sort by action then instrument_id;
   read the exact rule each time.
6. **Use `python` (not `python3`) and `curl`.** Save responses inside your own
   working directory. Compute correlations and weighted aggregates in python.
7. **Candidate vs held filter.** Bonds carry `candidate` (true = buyable new
   ticket) and you can see which ids are already in the portfolio's `holdings`.
   New BUY tickets normally come from `candidate==true` instruments not already
   held. Holdings you keep are not "trades".
8. **Watchlist / eligibility exclusions are the most common trap.** A high-yield
   "distractor" candidate is often on the issuer watchlist or duration-ineligible.
   Read the issuer's `watchlist` flag (`/api/issuers`) and the instrument's
   `modified_duration_years`/`rating_bucket`; exclude per the task's policy.

## Endpoint map

| Need | Endpoint |
|------|----------|
| Available ids + opportunity sets | `GET /api/catalog` |
| All policy thresholds | `GET /api/policies` |
| Portfolio objective/constraints/holdings | `GET /api/portfolios/<id>` |
| Bond security master (held + candidates) | `GET /api/instruments/bonds` |
| Issuer sector/subsector/rating/watchlist/outlook | `GET /api/issuers` |
| Energy commodity signals + pitch themes | `GET /api/market/energy` |
| Index metadata (window dates, region) | `GET /api/indices` |
| Monthly index levels | `GET /api/index-levels` or `/api/index-levels/<id>` |
| Opportunity-set taxonomy (asset_class, display_order) | `GET /api/allocation/opportunity-sets` |
| Prior active allocation views | `GET /api/allocation/prior-views` |
| Current macro/asset signal scores + rationale codes | `GET /api/macro-signals` |

Most list endpoints accept equality filters by field name (e.g.
`?rating_bucket=HY`, `?candidate=true`, `?quarter=Q3_2026`).

## Policy thresholds (always re-pull `/api/policies`; do not hard-code values)

`/api/policies` returns nested blocks. Key sub-policies and the fields you use:

- **allocation_mapping** (`POL_ALLOCATION_MAPPING`):
  - `view_score_thresholds`: `OW_min` (e.g. 0.35), `UW_max` (e.g. -0.35),
    neutral band in between. Map a signal `score` → view:
    `score >= OW_min → OW`; `score <= UW_max → UW`; else `N`.
  - `conviction_thresholds`: by **absolute** score — `HIGH_abs_min` (e.g. 0.7),
    `MEDIUM_abs_min` (e.g. 0.35), below that → `LOW`.
  - `view_rank`: `{UW:-1, N:0, OW:1}`. Use it for the `change` field:
    new_rank > prior_rank → `UP`; < → `DOWN`; equal → `UNCHANGED`. (UP means
    *more bullish*, i.e. toward OW.)
- **correlation** (`POL_CORRELATION_DEFAULT`): `correlation_high_threshold`
  (e.g. 0.8), `correlation_low_threshold` (e.g. 0.2), and the official
  `review_window_start` / `review_window_end`.
- **credit_default** (`POL_CREDIT_DEFAULT`): `duration_band_years` (e.g. [3.0,5.0]),
  `max_hy_allocation_pct` (e.g. 20.0), `issuer_concentration_limit_pct` (e.g. 12.0),
  `subsector_min_count_for_diversified` (e.g. 2), `target_hy_reduction_pct` (0.0).
- **credit_risk_reduction** (`POL_CREDIT_RISK_REDUCTION`): same bands/caps but
  `target_hy_reduction_pct` is a positive number (e.g. 4.0) — used by the FI
  rebalance task.
- **multi_asset** / **multi_asset_risk**: composition policies that say which of
  the above they reuse (`uses_allocation_mapping`, `uses_correlation_default`,
  `uses_credit_default` / `uses_credit_risk_reduction`) and the committee
  escalation rule (`committee_escalation_threshold`, e.g.
  "two_or_more_material_exceptions").

A portfolio's own `constraints.policy_id` tells you which credit policy governs it
(`/api/portfolios/<id>`). For `policy_id` output fields, prefer the policy id the
portfolio/answer is governed by (e.g. the allocation-mapping policy id for an
allocation refresh, or the portfolio's `constraints.policy_id` for a credit task).
The top-level `/api/policies` `policy_id` (e.g. a "POLICY_SET_..." id) is the
versioned bundle; use it only if the schema clearly wants the set id.

## Core computations

### Pearson correlation from monthly simple returns
1. Pull monthly `level` series for each index over the **requested window**
   (inclusive of both endpoints). N monthly levels → N-1 returns.
2. Simple return for month i: `r_i = level_i / level_{i-1} - 1`.
3. Pearson correlation of two return vectors x,y:
   `corr = Σ(x-mean_x)(y-mean_y) / ( sqrt(Σ(x-mean_x)^2) * sqrt(Σ(y-mean_y)^2) )`.
4. `return_observations` in the output = number of returns = N-1 (NOT N levels).
5. Round correlation to the template's precision (typically 3 decimals).
6. "Highest positive" pair = max corr; "lowest" / "best diversifier" = min corr
   (most negative). Within each pair, sort the two ids alphabetically.

```python
def simple_returns(levels):           # levels: [{"date","level"}, ...] in date order
    return [levels[i]['level']/levels[i-1]['level']-1 for i in range(1,len(levels))]
def pearson(x,y):
    import math; n=len(x); mx=sum(x)/n; my=sum(y)/n
    cov=sum((a-mx)*(b-my) for a,b in zip(x,y))
    sx=math.sqrt(sum((a-mx)**2 for a in x)); sy=math.sqrt(sum((b-my)**2 for b in y))
    return cov/(sx*sy)
```

### Portfolio credit aggregates (notional/market-value weighted)
For holdings list of `(instrument_id, quantity_usd_m)`, joined to bond master:
- `total_market_value = Σ quantity`.
- `hy_allocation_pct = 100 * Σ(quantity where rating_bucket=="HY") / total`.
- `weighted_modified_duration = Σ(quantity * modified_duration_years) / total`.
- `weighted_ytm = Σ(quantity * yield_to_maturity_pct) / total`.
- `issuer_concentration_pct(issuer) = 100 * Σ(quantity for that issuer) / total`;
  compare the max to `issuer_concentration_limit_pct`.
- `watchlist_exposure_usd_m = Σ(quantity where issuer.watchlist == true)`.
Recompute these on the **post-trade** book (apply SELLs/BUYs to the live holdings).

---

## Archetype (a) — Energy-credit recommendation / trade-package selection

**Example:** "Prepare the proposed energy-credit trade strategy for PF-EN-ALTA …
two BUY tickets totaling USD 8.0m split evenly … improve carry while staying inside
credit constraints … suitable for a client income pitch."

**Endpoints:** `/api/portfolios/<id>`, `/api/instruments/bonds`, `/api/issuers`,
`/api/market/energy`, `/api/policies` (credit_default for this portfolio).

**Selection recipe:**
1. Build the eligible BUY universe: bonds with `candidate==true`,
   `energy_linked==true` (for an energy sleeve), issuer **not** on watchlist,
   and **not already held**.
2. Honour the ticket structure exactly (e.g. 2 tickets, USD 8.0m total split
   evenly → 4.0m each). Action enum is `BUY`/`SELL`/`HOLD`/`NO_TRADE`.
3. **Post-trade constraint checks** (apply the buys to live holdings, recompute):
   - `hy_cap_pass`: post-trade `hy_allocation_pct <= max_hy_allocation_pct`.
   - `duration_band_pass`: post-trade weighted modified duration within
     `duration_band_years`.
   - `selected_issuer_diversification_pass`: the **selected tickets** are from
     **different issuers** (i.e. don't double up one issuer within the package).
   - `selected_subsector_diversification_pass`: the selected tickets span
     `>= subsector_min_count_for_diversified` **distinct subsectors**.
   - `watchlist_avoidance_pass`: no selected ticket's issuer is on the watchlist.
   NOTE the word "selected": issuer/subsector diversification checks are about the
   chosen package, not the whole portfolio. A pre-existing large legacy holding may
   already exceed the portfolio-wide issuer-concentration limit; that is a
   pre-existing condition and is not what `selected_issuer_diversification_pass`
   measures.
4. **Choosing among feasible packages:** prefer the package that improves expected
   carry (higher post-trade weighted YTM / spread) **and** is defensible for a
   client income pitch. Use `/api/market/energy` signals: the strongest positive
   commodity signal and `pitch_themes` should steer theme/segment. Watch the
   tension: HY-heavy packages push carry up but bump against the HY cap and the
   committee's stated sensitivity to "headline carry from watchlisted issuers";
   IG LNG/midstream names give a cleaner, lower-HY income story. Pick the package
   that maximises carry **subject to** all constraints and the client/theme
   guidance rather than raw yield alone.

**Output schema conventions:**
- `trade_package`: list of length 2, **sorted ascending by instrument_id**, each
  `{action, instrument_id, notional_usd_m}`; `notional_usd_m` precision 1.
- `post_trade_metrics`: `total_market_value_usd_m`, `hy_allocation_pct`,
  `weighted_modified_duration_years`, `weighted_yield_to_maturity_pct` — all
  precision 2.
- `constraint_checks`: the five booleans above.
- `sales_positioning`: `target_segment` ∈ {insurance_general_account,
  pension_liability_matching, multi_asset_income, private_bank_income,
  endowment_opportunistic}; `theme` ∈ {lng_export_tailwind, oil_oversupply_caution,
  midstream_stability, transition_bond_selectivity, avoid_watchlist_yield_trap}.
  Pick the theme that matches the dominant energy signal and the client context
  in the request (e.g. a multi-asset income client + strong LNG signal →
  `multi_asset_income` + `lng_export_tailwind`).
- `data_precedence`: ∈ {current_environment_over_stale_payload,
  local_payload_over_current_environment, no_conflict_found}. If the stale
  snapshot's MV/HY/duration differ from the live portfolio (they usually do),
  use `current_environment_over_stale_payload`.

---

## Archetype (b) — International equity correlation review

**Example:** PF-INT-NEXVEN correlation review over a stated monthly-level window
for a 9-index universe.

**Endpoints:** `/api/portfolios/<id>` (sleeves/holdings), `/api/policies`
(correlation thresholds + official window), `/api/indices` (window dates),
`/api/index-levels` (levels).

**Recipe:**
1. Window: use the request's `review_window` (reconcile against the policy's
   `review_window_start/end` and the indices' `level_start_date/level_end_date`;
   they should agree — env wins if not). Compute monthly simple returns →
   `return_observations = N_levels - 1`.
2. Compute the full pairwise Pearson correlation matrix over the requested
   `index_universe`. Identify `highest_positive` (max) and `lowest` (min, most
   negative) pairs.
3. **Concentration logic:** if the highly-correlated cluster is the China + Asia
   sleeves (China, Asia-Pac, EM are mutually >`high_threshold`), set
   `china_asia_dependence_flag = true` and `primary_code = CHINA_ASIA_DEPENDENCE`.
   `high_threshold_breached = true` if any relevant pair exceeds
   `correlation_high_threshold`. (Other codes: GLOBAL_DEVELOPED_OVERLAP if the
   dominant overlap is developed-world betas; NO_MATERIAL_CONCENTRATION if nothing
   breaches.)
4. **Diversification candidates:** from the allowed set (e.g. EM_EX_CHINA, INDIA,
   LATAM), the genuine diversifiers are those with **low/negative** correlation to
   the concentrated cluster. LATAM-type indices that are negatively correlated to
   the China/Asia cluster are the real diversifiers; EM-ex-China and India often
   remain >0.8 correlated to the core and are weaker diversifiers. Sort the chosen
   candidate ids alphabetically.
5. **Sleeve actions:** typically two — trim/hedge the concentrated sleeve
   (target the China index) and add the best diversifier (target the LATAM index).
   `action` ∈ {trim, add, hold, hedge, monitor, rotate}; `target_index_id`
   restricted to the template's allowed set.

**Output schema conventions:**
- `index_set`: alphabetical list of the universe ids.
- `review_window`: `{level_start_date, level_end_date, return_observations}`.
- `extreme_pairs`: `{highest_positive:{pair_id:[a,b],correlation}, lowest:{...}}`,
  pair ids alphabetical within the pair, correlation to 3 decimals.
- `concentration`: `{china_asia_dependence_flag(bool), primary_code(enum),
  high_threshold_breached(bool)}`.
- `diversification_candidates`: alphabetical subset of the allowed ids.
- `sleeve_actions`: list (length per template, e.g. 2), sorted by sleeve, each
  `{sleeve, action, target_index_id}`.

---

## Archetype (c) — Active allocation view refresh

**Example:** Q2 2026 CIO active allocation refresh for a focus list of
opportunity sets; output view / change / conviction / rationale per set plus a
portfolio-level risk overlay.

**Endpoints:** `/api/allocation/opportunity-sets` (asset_class + display_order),
`/api/allocation/prior-views`, `/api/macro-signals`, `/api/policies`
(allocation_mapping).

**Recipe (per opportunity set, for the target quarter):**
1. Pull the macro signal for that `opportunity_set` and `quarter==target_quarter`:
   gives `score`, `rationale_code`, `drivers`.
2. `view` = map `score` through `view_score_thresholds` (OW/UW/N).
3. `conviction` = map `abs(score)` through `conviction_thresholds`
   (HIGH/MEDIUM/LOW).
4. `prior_view` = the standing view from `/api/allocation/prior-views` for that
   opportunity set whose `quarter == target_quarter` (its `previous_quarter`
   equals the prior quarter). That recorded view is the baseline you refresh from.
5. `change` = compare new view rank vs prior view rank using `view_rank`
   (UP/DOWN/UNCHANGED).
6. `rationale_code` = the macro signal's `rationale_code` (already from the allowed
   enum, e.g. EUROPE_RECOVERY, JAPAN_POLICY_RISK, CHINA_DEPENDENCE, INDIA_OFFSET,
   LATAM_DIVERSIFIER, DURATION_SUPPORT, HY_VALUATION_RISK, NEUTRAL_BALANCE, …).
7. `asset_class` = from the opportunity-set taxonomy (Equities/Duration/Credit/
   Currency).

**Risk overlay:** synthesize from the dominant theme across the focus set:
- `overlay_code` ∈ {DURATION_QUALITY_TILT, CREDIT_RISK_REDUCTION,
  EQUITY_BETA_EXTENSION, CURRENCY_DEFENSIVE_HEDGE, NO_OVERLAY}.
- `primary_action` ∈ {tilt_to_duration_quality, trim_credit_beta,
  add_cyclical_equity_beta, add_currency_hedge, hold_policy_weights}.
- Choose the overlay that matches the strongest cross-set message: e.g. if
  duration/treasuries score strongly positive while HY scores strongly negative,
  that is a duration-quality tilt away from credit beta
  (DURATION_QUALITY_TILT + tilt_to_duration_quality). If HY risk dominates, it's
  CREDIT_RISK_REDUCTION + trim_credit_beta.
- `rationale_codes`: ordered list, **highest business priority first**, drawn from
  the rationale codes of the most decisive sets (e.g. DURATION_SUPPORT,
  HY_VALUATION_RISK, then supporting codes).

**Output schema conventions:**
- `allocation_views`: list ordered by the **request's `focus_opportunity_sets`
  order** (NOT alphabetical, NOT display_order — follow the payload), required
  length = number of focus sets. Each row: `{opportunity_set, asset_class, view,
  change, conviction, rationale_code}`, all enums exactly as allowed.
- Lineage: `task_id` (required_value from template), `as_of_date` (env current),
  `target_quarter`, `prior_quarter`, `policy_id`.
- `risk_overlay`: `{overlay_code, primary_action, rationale_codes[]}`.

---

## Archetype (d) — Fixed-income risk rebalance

**Example:** PF-FI-LUMEN rotation that reduces HY and watchlist pressure while
keeping duration in the CIO band; sell pressure points, fund eligible candidates.

**Endpoints:** `/api/portfolios/<id>`, `/api/instruments/bonds`, `/api/issuers`,
`/api/policies` (the portfolio's `constraints.policy_id`, typically
credit_risk_reduction with a positive `target_hy_reduction_pct`).

**Recipe:**
1. Compute pre-trade `hy_allocation_pct`, weighted duration, and
   `watchlist_exposure_usd_m` from live holdings.
2. **SELLs:** prioritise (i) watchlist HY holdings (these are the "avoidable
   watchlist risk" to remove), then (ii) additional non-watchlist HY as needed.
   You usually must sell **more than just the watchlist name** — removing one
   watchlist HY often still leaves HY above the cap, so keep selling HY until both
   the `target_hy_reduction_pct` reduction AND the `max_hy_allocation_pct` cap are
   satisfied.
3. **BUYs:** fund from `candidate==true`, **non-watchlist**, **IG** names not
   already held (e.g. data-center / materials / LNG IG). Keep the rotation roughly
   notional-neutral (Σ buys ≈ Σ sells) unless told otherwise, and choose buy
   durations that keep post-trade weighted duration inside `duration_band_years`.
4. **Reject the watchlist HY distractor candidate.** A shortlisted candidate that
   is HY *and* watchlist (e.g. a higher-coupon name flagged "issuer status
   concern") must NOT be bought when the memo says avoid new watchlist buys —
   `buys_avoid_watchlist` must stay true.
5. Recompute post-trade metrics and the boolean exception flags.

**Output schema conventions:**
- `rotation.trades`: sorted **SELL before BUY**, then ascending instrument_id
  within each action; each `{action(BUY|SELL), instrument_id, quantity_usd_m}`,
  quantity precision 1.
- `risk_metrics`: `post_trade_hy_allocation_pct` (prec 2),
  `post_trade_duration_years` (prec 2),
  `hy_reduction_pct_points` = pre_HY% − post_HY% (prec 2),
  `post_trade_watchlist_exposure_usd_m` (prec 1).
- `exception_flags`: `hy_cap_pass`, `duration_band_pass`,
  `target_hy_reduction_met` (reduction ≥ `target_hy_reduction_pct`),
  `watchlist_exposure_cleared` (post-trade watchlist exposure == 0).
- `watchlist_handling`: `watchlist_sell_ids` (ascending instrument_id list of the
  watchlist names you sold), `buys_avoid_watchlist` (bool).
- `risk_note_code` ∈ {hy_cap_pressure, watchlist_concentration,
  duration_preservation, carry_tradeoff, no_action} — pick the dominant theme of
  the rebalance (e.g. clearing HY over the cap → hy_cap_pressure, or removing a
  watchlist concentration → watchlist_concentration).

---

## Archetype (e) — Multi-asset committee decision

**Example:** PF-MA-HELIO committee JSON linking non-US equity correlation findings
to active allocation views for EM, India, Latin America, and USD.

This archetype **combines (b) and (c)** for one compact file.

**Endpoints:** `/api/portfolios/<id>`, `/api/index-levels`, `/api/policies`
(multi_asset / multi_asset_risk → which reuses correlation_default and the
allocation mapping), `/api/allocation/prior-views`, `/api/macro-signals`.

**Recipe:**
1. **Correlation summary** over the requested equity index ids and window
   (same Pearson-from-monthly-simple-returns recipe). Produce exactly two items in
   the fixed order `[highest_concentration, best_diversifier]`:
   - `highest_concentration` = the max-correlation pair (the concentration risk).
   - `best_diversifier` = the min-correlation (most negative) pair.
   Each item `{pair_role, pair:[a,b] alphabetical, correlation (prec 3)}`.
2. **Allocation views** for the requested opportunity sets (EM, India, Latin
   America, USD) using archetype (c)'s mapping. Output rows in the template's
   fixed `item_order` (e.g. Emerging Markets, India, Latin America, USD). Each row
   needs `{opportunity_set, prior_view, signal_score (prec 3), view, change,
   conviction, rationale_code}`. The **stale local note often keeps USD overweight
   "as a defensive offset"** — refresh it: if the current USD signal is in the
   neutral band, USD becomes `N` with `change=DOWN` from a prior `OW`. This is the
   canonical "environment overrides stale local note" case.
3. **target_sleeve_actions** for the same sets (same fixed order), `action` ∈
   {trim, add, hold, hedge, monitor, rotate}. Tie actions to the views/correlation:
   trim the concentrated EM/China-driven sleeve, add the diversifier (LatAm),
   hold/monitor India if already OW, hedge/hold USD per its refreshed view.
4. **rebalance_trigger** ∈ {correlation_cap_breach, hy_cap_pressure,
   duration_drift, watchlist_concentration, committee_review}: if a correlation
   pair breaches `correlation_high_threshold`, `correlation_cap_breach` is apt;
   otherwise `committee_review`.
5. **portfolio_risk_concentration_flag** (bool): true if the equity book shows a
   material concentration (high-corr cluster breaching the threshold).
6. **next_step** ∈ {approve_rotation, defer_pending_risk_review,
   approve_with_monitoring, reject_constraint_breach}. Use the multi_asset_risk
   escalation rule: e.g. two or more material exceptions → escalate
   (defer/approve_with_monitoring) rather than approve outright.

**Output schema conventions:** top-level keys `portfolio_id` (required_value),
`as_of_date` (env current), `review_quarter` (required_value),
`correlation_summary` (len 2, fixed role order), `target_sleeve_actions`
(fixed set order), `allocation_views` (fixed set order),
`rebalance_trigger`, `portfolio_risk_concentration_flag`, `next_step`. No prose
outside the JSON.

---

## Common misjudgments to avoid (checklist)

- Using stale payload marks (MV, HY%, duration, prior view, USD overweight)
  instead of live env values. **Always re-pull.**
- Counting **levels** instead of **returns** for `return_observations` (it is
  N_levels − 1).
- Forgetting to sort pair ids / index sets / trade lists per the template's
  ordering rule, or sorting allocation rows alphabetically when the template says
  follow the request's focus order.
- Treating EM-ex-China or India as a strong diversifier when they remain
  >0.8 correlated to the China/Asia core; the negatively-correlated index
  (LatAm-type) is the real diversifier.
- Buying a watchlist or already-held or non-candidate or duration-ineligible
  instrument as a "new ticket."
- Selling only the single watchlist name and assuming the HY cap is cleared — it
  often is not; sell enough HY to satisfy both the reduction target and the cap.
- Mis-mapping `change`: remember `view_rank` UW(-1) < N(0) < OW(1); UP = toward OW.
- Wrong rounding precision or emitting an enum value not in the template's
  `allowed_values` (exact spelling, case, and punctuation matter).
- Confusing the "selected" diversification checks (within the chosen package) with
  the portfolio-wide issuer-concentration limit.

## Self-consistency cross-checks before emitting

- Re-add post-trade notional: Σ holdings ± trades should reconcile to the MV you
  report.
- Confirm every enum value you output appears verbatim in the template's allowed
  set; confirm every required top-level key is present.
- Confirm correlations are within [-1, 1] and that highest_positive ≥ every other
  pair and lowest ≤ every other pair.
- Confirm boolean flags actually match your computed numbers (e.g.
  `hy_cap_pass` ⇔ post-trade HY% ≤ cap; `duration_band_pass` ⇔ duration in band;
  `watchlist_exposure_cleared` ⇔ post-trade watchlist exposure == 0).
- Confirm list lengths and ordering match the template exactly.
