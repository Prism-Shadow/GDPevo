---
name: asteria-investment-office-json-desk
description: >-
  Produce committee-grade JSON for the Asteria Investment Office across five task
  archetypes: (a) energy-credit trade packages, (b) international equity correlation
  reviews, (c) active allocation view refreshes, (d) fixed-income risk rebalances,
  and (e) multi-asset committee decisions. Pulls every fact from the shared Asteria
  HTTP environment (the book of record), runs the exact quantitative recipes
  (Pearson correlation, weighted duration/YTM, HY %, view mapping), applies the
  policy thresholds and exclusion rules, and emits output that conforms exactly to
  the task's answer_template (field names, enum value sets, rounding, id ordering).
---

# Asteria Investment Office — JSON desk SOP

You answer Asteria desk requests by producing a single JSON object that conforms
to the task's `answer_template.json`. Local payloads (desk requests, memos,
worksheets, exception boards, shortlists) are **intake context only** and are
frequently stale. The shared Asteria HTTP environment is the **book of record**:
when a local number disagrees with the environment, the environment wins, and
your `data_precedence`/lineage fields should say so.

Use `python` (not `python3`) for all math. Fetch all data over HTTP and save
responses inside your own working directory.

## 0. Universal rules (apply to every archetype)

1. **Environment over payload.** Re-pull portfolio holdings, quantities, bond
   security-master, issuer flags, index levels, prior views, macro signals, and
   policy thresholds from the environment. Do not trust payload marks, stale
   quantities, or "kept X overweight" notes. (E.g. a memo HY position of 10 may
   actually be 12 in the portfolio service; a worksheet that "kept USD OW" may be
   neutral once the current signal is read.)
2. **Conform to the template literally.** Match required key names, the exact enum
   value sets, the declared rounding precision per field, list lengths, and the
   declared ordering rule. A wrong enum spelling, an extra/missing key, or wrong
   sort order each costs points.
3. **Rounding.** Round only at the end, to the precision the field declares
   (correlations 3 dp; pct/years metrics usually 2 dp; not/quantity usually 1 dp;
   signal scores 3 dp). Carry full precision through intermediate math.
4. **`as_of_date`** is the environment's current as-of date (read it from the
   portfolio record or `/api/policies`, e.g. the policy set's `as_of_date`), not
   the payload's memo date.
5. **Endpoints** (base `<remote-env-url>`):
   `/api/catalog`, `/api/policies`, `/api/portfolios/<id>`,
   `/api/instruments/bonds`, `/api/issuers`, `/api/market/energy`,
   `/api/indices`, `/api/index-levels` (or `/<id>`),
   `/api/allocation/opportunity-sets`, `/api/allocation/prior-views`,
   `/api/macro-signals`. List endpoints accept equality filters
   (`?rating_bucket=HY`, `?candidate=true`, `?quarter=Q2_2026`).

## 1. Policy thresholds (read from `/api/policies`; values below are the defaults)

- **Allocation mapping** (`POL_ALLOCATION_MAPPING`):
  - view from signal score: `OW` if score ≥ **+0.35**, `UW` if score ≤ **−0.35**,
    else `N` (neutral band is the closed interval [−0.35, +0.35]).
  - conviction from |score|: `HIGH` if ≥ **0.7**, `MEDIUM` if ≥ **0.35**,
    else `LOW`.
  - view_rank for change comparison: `UW = −1`, `N = 0`, `OW = +1`.
- **Correlation** (`POL_CORRELATION_DEFAULT`): high threshold **0.8**, low
  threshold **0.2**; default review window 2025-05-30 → 2026-04-30.
- **Credit default** (`POL_CREDIT_DEFAULT`): duration band **[3.0, 5.0]** years,
  issuer concentration limit **12%**, max HY **20%**, subsector min count for
  "diversified" = **2**, target HY reduction **0.0** pp.
- **Credit risk reduction** (`POL_CREDIT_RISK_REDUCTION`): same as above but
  target HY reduction **4.0** pp. (Risk-reduction portfolios carry this policy_id
  in their own constraints block.)
- **Multi-asset risk** (`POL_MULTI_ASSET_RISK`): committee escalation =
  "two_or_more_material_exceptions"; uses correlation-default + credit-risk-
  reduction.

Always prefer the threshold values returned by the live `/api/policies` and by the
portfolio's own `constraints` block over any memorized constant.

## 2. Core computation recipes

### Pearson correlation on monthly simple returns
- Pull `/api/index-levels/<id>` (a list of `{date, level}` sorted monthly).
- Simple return for month i: `r_i = (level[i+1] - level[i]) / level[i]`.
- With 12 monthly levels you get **11 returns** → `return_observations = 11`.
- Pearson r between two return series; round to **3 decimals**.
- "Highest positive" = max r; "lowest" = min r (can be negative).
- Every `pair_id`/`pair` lists the two index ids in **ascending alphabetical**
  order; pair lists across the answer are ordered as the template dictates.

### Weighted modified duration / weighted YTM
- Weight each holding's `modified_duration_years` (or `yield_to_maturity_pct`) by
  its `quantity_usd_m`, divide by total market value. Round to 2 dp.

### HY allocation %
- `HY% = (sum of quantity_usd_m where rating_bucket == "HY") / total_MV * 100`.
- `hy_reduction_pct_points = pre_HY% − post_HY%` (round 2 dp).

### View / change / conviction mapping (allocation tasks)
- New view = map current-quarter signal score through the OW/UW/N thresholds.
- Conviction = map |signal score| through HIGH/MEDIUM/LOW thresholds.
- `change` = compare new view rank vs the **prior view** rank
  (UP if higher, DOWN if lower, UNCHANGED if equal).
- `rationale_code` comes straight from the macro signal row's `rationale_code`
  (do not invent one); it already matches the allowed enum set.

## 3. The quarter-filtering trap (allocation & committee tasks)

Both `/api/macro-signals` and `/api/allocation/prior-views` contain **multiple
quarters** (e.g. Q2_2026 and Q3_2026 rows for the same opportunity set). This is
the single biggest silent-error source.
- Filter macro signals to `quarter == target_quarter` (the request's quarter).
- The **prior view** to compare against is the prior-views row whose
  `previous_quarter == prior_quarter` (its `view` is the view going into the
  target quarter). Equivalently, the row whose `quarter == target_quarter` and
  `previous_quarter == prior_quarter`.
- Using the wrong-quarter row flips both the view and the rationale_code (e.g. a
  currency that is Neutral/NEUTRAL_BALANCE this quarter looks UW/DOLLAR_DEFENSIVE
  next quarter). Always pin the quarter first.

## 4. Archetype playbooks

### (a) Energy-credit trade package
Inputs: `/api/portfolios/<id>`, `/api/instruments/bonds`, `/api/issuers`,
`/api/market/energy`, `/api/policies`.
- **Eligible buy universe** = bonds with `candidate == true` **and**
  `energy_linked == true` **and** whose issuer is **not** on the watchlist
  (`/api/issuers` → `watchlist == true` is excluded). Watchlisted energy issuers
  are typically the E&P, refining, and one telecom name — never buy them.
- Honor the requested ticket count and total notional, split as instructed
  (e.g. two tickets, 8.0 USD m total → 4.0 each). Use different issuers
  (issuer diversification) and prefer different subsectors (subsector
  diversification; "diversified" needs ≥ 2 subsectors).
- Compute post-trade `total_market_value_usd_m`, `hy_allocation_pct`,
  `weighted_modified_duration_years`, `weighted_yield_to_maturity_pct` by adding
  the buys to current holdings (MV = current MV + new notional).
- **Constraint checks** must all hold: HY ≤ 20%, duration inside [3.0, 5.0],
  selected issuers distinct, selected subsectors distinct, no watchlist issuer.
- **Selection bias that matters:** for an income/client-facing package, favor a
  **quality tilt** — keep HY comfortably below the cap rather than maxing carry by
  stacking HY to ~19%. Pair the dominant macro theme (the energy desk's strongest
  positive signal, typically LNG export, score ≈ 0.7) with a defensive
  diversifier (IG midstream/"natural gas") so carry improves versus the current
  book while staying diversified. Theme/segment enums: pick the theme matching the
  strongest signal (e.g. `lng_export_tailwind`) and segment `multi_asset_income`
  for an income pitch.
- `data_precedence`: if env MV/HY/duration differ from the stale snapshot, set
  `current_environment_over_stale_payload`.

### (b) International equity correlation review
Inputs: `/api/index-levels`, `/api/policies` (correlation thresholds), request's
index universe + window.
- Confirm the level series matches the requested window; compute the 11-return
  Pearson matrix over the universe.
- `extreme_pairs.highest_positive` / `.lowest` = max/min r, pair ids alphabetical,
  3 dp; `return_observations` = number of returns (11 for a 12-point window).
- `concentration`:
  - `high_threshold_breached` = any pair |r| (positive cluster) ≥ 0.8.
  - `china_asia_dependence_flag` = the dedicated China sleeve is highly correlated
    (≥ 0.8) with the broad Asia/EM indices.
  - `primary_code` = `CHINA_ASIA_DEPENDENCE` when that cluster is the dominant
    concentration; otherwise `GLOBAL_DEVELOPED_OVERLAP` or
    `NO_MATERIAL_CONCENTRATION`.
- `diversification_candidates` = **only** indices whose correlation to the
  concentrated core is **below the low threshold (0.2)** — in practice the
  Latin-America index (strongly negative). Do **not** list India or EM-ex-China as
  diversifiers when they sit > 0.8 against the core; they are not diversifiers.
- `sleeve_actions`: use the **geographic sleeve name** as the `sleeve` value
  (e.g. "China", "Latin America"), not generic labels like "Diversifier" — generic
  labels lose credit. Typical pair: trim the concentrated China sleeve, add the
  low-correlation diversifier; order ascending by sleeve; `target_index_id` from
  the allowed set.

### (c) Active allocation view refresh
Inputs: `/api/allocation/opportunity-sets`, `/api/allocation/prior-views`,
`/api/macro-signals`, `/api/policies`.
- One row per requested opportunity set, **ordered exactly as the request's
  focus list** (not alphabetical).
- `asset_class` = the opportunity set's `asset_class` from
  `/api/allocation/opportunity-sets` (Equities / Duration / Credit / Currency).
- Apply the quarter filter (Section 3), then the view/change/conviction mapping
  and the macro-provided `rationale_code` (Section 2).
- `policy_id` = the allocation mapping policy id (`POL_ALLOCATION_MAPPING`).
- `risk_overlay`: read the tilt from the new view set. When duration (Treasuries)
  is OW and credit (HY) is UW, overlay_code `DURATION_QUALITY_TILT` with
  primary_action `tilt_to_duration_quality`; `rationale_codes` in business-priority
  order (duration support first, HY valuation risk next). Choose
  `CREDIT_RISK_REDUCTION`/`trim_credit_beta`, `EQUITY_BETA_EXTENSION`/
  `add_cyclical_equity_beta`, `CURRENCY_DEFENSIVE_HEDGE`/`add_currency_hedge`, or
  `NO_OVERLAY`/`hold_policy_weights` when the view set points there instead.

### (d) Fixed-income risk rebalance
Inputs: `/api/portfolios/<id>` (use **current** quantities, not the stale
exception board), `/api/instruments/bonds`, `/api/issuers`, `/api/policies`
(`POL_CREDIT_RISK_REDUCTION`).
- The portfolio may already breach the HY cap (HY can be ~40% in a mixed-credit
  book). The rotation must end with HY ≤ 20% **and** achieve at least the target
  HY reduction (4.0 pp), keep duration inside [3.0, 5.0], and clear watchlist
  pressure.
- **Sell side:** sell the watchlist issuer's bond(s) (mandatory to clear watchlist)
  plus the minimum extra HY needed to drop under the cap and meet the reduction
  target — do not zero out HY (preserve carry/mandate).
- **Buy side:** fund with current **eligible IG candidates** (`candidate == true`,
  `rating_bucket == IG`, issuer not on watchlist); **never buy a watchlist name**
  even if it has high carry. Prefer the desk's named IG shortlist (data-center,
  materials, LNG IG). Keep buys ≈ sells so MV is roughly preserved and duration
  stays in band; the exact notional split per buy is secondary to the right
  instrument set.
- Trade list ordering: **SELL before BUY**, then `instrument_id` ascending within
  each action; quantities to 1 dp.
- `risk_metrics`: post-trade HY %, post-trade weighted duration, HY reduction pp,
  post-trade watchlist exposure (USD m).
- `exception_flags`: hy_cap_pass (≤20), duration_band_pass (in [3,5]),
  target_hy_reduction_met (≥ target pp), watchlist_exposure_cleared (== 0).
- `watchlist_handling`: `watchlist_sell_ids` = sold watchlist instruments
  (ascending); `buys_avoid_watchlist` = true.
- `risk_note_code`: when a watchlist name is the headline issue being cleared,
  prefer **`watchlist_concentration`** over `hy_cap_pressure`, even if the HY cap
  is also pressured. Use `duration_preservation`, `carry_tradeoff`, or `no_action`
  only when those are genuinely the dominant story.

### (e) Multi-asset committee decision
Inputs: combine (b) correlation on the requested small index set with (c)
allocation views on the requested opportunity sets, plus `/api/policies`.
- `correlation_summary` (length 2, order [highest_concentration, best_diversifier]):
  highest_concentration = max-r pair (e.g. the China/EM pair ≈ 0.92);
  best_diversifier = min-r pair (e.g. China/LatAm ≈ −0.83); pair ids alphabetical,
  correlation 3 dp.
- `allocation_views` (ordered as the request lists the sets): include `prior_view`,
  `signal_score` (3 dp, from the **target-quarter** macro row), `view`, `change`,
  `conviction`, `rationale_code` — all via Sections 2–3. Reconcile any stale local
  stance here (e.g. a "USD overweight" worksheet becomes Neutral if the current
  signal is in the neutral band).
- `target_sleeve_actions` (same order): trim the set you downgraded / that drives
  concentration (EM), hold an unchanged OW (India), add the diversifier you
  upgraded (LatAm), monitor/hedge/trim the currency you reduced (USD).
- `rebalance_trigger`: when the top correlation exceeds the high threshold (0.8),
  use `correlation_cap_breach`.
- `portfolio_risk_concentration_flag`: true when the China/EM concentration breaches
  the high threshold.
- `next_step`: with one material exception flagged (concentration breach) but a
  coherent rotation in hand, prefer **`approve_with_monitoring`**. Use
  `defer_pending_risk_review` only when escalation is genuinely triggered
  (two or more material exceptions), `reject_constraint_breach` for a hard breach,
  and `approve_rotation` only when there is no concentration flag at all.

## 5. Pre-submit checklist

- Every required top-level key present; no extra keys.
- Enums spelled exactly from the allowed set; booleans are real booleans.
- All numbers rounded to the field's declared precision (correlations 3 dp,
  signal scores 3 dp, pct/years 2 dp, notional/quantity 1 dp).
- Lists in the declared order (focus-list order, alphabetical ids, SELL-before-BUY,
  pair role order); pair member ids alphabetical.
- Metrics computed from current environment holdings, not from stale payload marks;
  data_precedence / lineage reflects the reconciliation.
- Constraint/exception flags computed from the actual post-trade numbers and the
  live policy thresholds, not asserted.
