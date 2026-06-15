---
name: asteria-investment-office
description: >-
  Produce strict-JSON deliverables for the Asteria Investment Office (CIO / credit
  desk) task family: energy/fixed-income credit trade packages, international equity
  correlation reviews, cross-asset active-allocation view refreshes, fixed-income
  risk rebalances, multi-asset risk-board reconciliations, and committee combined-decision
  files. Use whenever a task references the Asteria shared environment / book-of-record,
  a PF-* portfolio, an answer_template.json output contract, allocation views, index
  correlations, energy-credit trades, watchlist/HY constraints, or active-allocation
  rationale codes. The environment is a read-only HTTP/JSON API; outputs must follow
  the provided answer_template exactly (enums, ordering, rounding).
---

# Asteria Investment Office — CIO / Credit Desk Skill

This skill solves tasks that return a single strict JSON object describing an
investment decision for an Asteria portfolio. The shared environment is the
authoritative book of record, exposed as a read-only HTTP/JSON API. Each task
ships an `answer_template.json` (in `input/payloads/`) that defines the exact
output schema: required keys, controlled enums, list ordering, and numeric
precision. **Always conform to that template; it overrides any default below.**

## 0. Universal workflow (do this every time)

1. **Read the prompt and every file in `input/payloads/`.** The payload is
   *intake context only* — it may carry stale marks, holdings, watchlist flags,
   or preferences. Note the `portfolio_id`, the requested universe/quarter/window,
   and the exact output contract in `answer_template.json`.
2. **Pull live data from the API** (base `http://127.0.0.1:8036`, all `GET`):
   start with `/api/policies` (thresholds), `/api/catalog` (valid ids), and the
   portfolio/data endpoints relevant to the task type (see §1).
3. **Apply source precedence:** when the payload disagrees with the environment
   on marks, ratings, holdings, watchlist status, quantities, or policy data,
   **use the environment.** The payload's `*_as_of_date`/`snapshot_date` is
   usually older than the environment `as_of_date` (currently `2026-05-29`).
4. **Use the environment `as_of_date` for every `as_of_date` output field**
   (read it from `/api/policies` or any portfolio record — they agree). Do NOT
   echo the payload's request/memo date.
5. **Compute deterministically** using the formulas in §3, then map to enums
   (§4). Round each field to its template precision *(2 dp → e.g. `5.80` is
   `5.8` numerically; emit the number, JSON drops trailing zeros)*.
6. **Honor ordering rules** in the template (sort lists exactly as specified).
7. Return **only** the JSON object — no prose, no markdown fences.

## 1. API endpoints and what to call them for

| Endpoint | Use it for |
|---|---|
| `GET /api/catalog` | Valid portfolio_ids, policy_ids, index_ids, issuer_ids, bond instrument_ids, opportunity_sets. |
| `GET /api/policies` | All thresholds: HY cap, duration band, issuer concentration, correlation high/low, allocation view/conviction thresholds, target HY reduction, top-level `policy_id` and `as_of_date`. |
| `GET /api/portfolios` | Portfolio summaries incl. `constraint_policy_id`, MV, holding_count. |
| `GET /api/portfolios/<id>` | One portfolio's objective, constraints, and **current holdings** (`instrument_id`, `quantity_usd_m`, sleeve). Authoritative for positions/sizes. |
| `GET /api/instruments/bonds` | Bond master: `rating_bucket` (IG/HY), `modified_duration_years`, `yield_to_maturity_pct`, `spread_bps`, `coupon_pct`, `sector`, `subsector`, `issuer_id`, `energy_linked`, `candidate` (buyable), `recommended_theme_tags`. Filter e.g. `?candidate=true`, `?rating_bucket=HY`. |
| `GET /api/issuers` | `rating_bucket`, sector/subsector, `watchlist` (bool — authoritative), `credit_outlook`, tags. Join bonds→issuer via `issuer_id` to get watchlist. |
| `GET /api/market/energy` | Energy `signals` (commodity, direction, score), `pitch_themes`, stale-data warning. Drives energy trade themes. |
| `GET /api/indices` | Index metadata, `level_start_date`/`level_end_date`, region, currency. |
| `GET /api/index-levels` or `/api/index-levels/<index_id>` | Monthly `levels` (date, level). Use for correlations. |
| `GET /api/allocation/opportunity-sets` | `opportunity_set` → `asset_class` (Equities/Duration/Credit/Currency) and `display_order`. Source of the `asset_class` field. |
| `GET /api/allocation/prior-views` | Standing views by `opportunity_set` and `quarter` (with `view`, `conviction`, `previous_quarter`). Source of `prior_view`. Filter `?quarter=Q2_2026`. |
| `GET /api/macro-signals` | Per opportunity_set + quarter: `score` (float), `rationale_code`, `drivers`. Source of `signal_score` and `rationale_code`. Filter `?quarter=Q2_2026`. |

Most list endpoints accept simple equality filters on field names
(`?rating_bucket=HY`, `?candidate=true`, `?quarter=Q3_2026`, `?issuer_id=...`).

## 2. Key policy constants (read live; values as of POLICY_SET_2026_05)

From `/api/policies`:

- **credit_default / credit_risk_reduction**: `max_hy_allocation_pct = 20.0`,
  `duration_band_years = [3.0, 5.0]`, `issuer_concentration_limit_pct = 12.0`,
  `subsector_min_count_for_diversified = 2`. `target_hy_reduction_pct = 0.0`
  for `credit_default`, **`4.0` for `credit_risk_reduction`** (the risk-reduction
  policy used by rebalance portfolios such as PF-FI-LUMEN).
- **correlation**: `correlation_high_threshold = 0.8`,
  `correlation_low_threshold = 0.2`, window `2025-05-30`..`2026-04-30`.
- **allocation_mapping**:
  - `view_score_thresholds`: `OW_min = 0.35`, `UW_max = -0.35`, neutral in
    `(-0.35, 0.35)`.
  - `conviction_thresholds`: `HIGH_abs_min = 0.7`, `MEDIUM_abs_min = 0.35`,
    `LOW_abs_below = 0.35` (i.e. |score| ≥0.7 HIGH; ≥0.35 MEDIUM; else LOW).
  - `view_rank`: `UW=-1, N=0, OW=1`.
- **multi_asset_risk**: `committee_escalation_threshold = two_or_more_material_exceptions`.
- Top-level **`policy_id = POLICY_SET_2026_05`** and **`as_of_date = 2026-05-29`**.

Always re-read these — never hardcode if the live values differ. A portfolio's
own `constraint_policy_id` (from `/api/portfolios`) tells you which constraint
block applies (e.g. PF-FI-LUMEN → `POL_CREDIT_RISK_REDUCTION`).

## 3. Calculation formulas and rounding

### 3.1 Portfolio metrics (credit tasks)
Let post-trade positions be `{instrument_id: quantity_usd_m}` (apply BUY +qty,
SELL −qty to current holdings; drop zero/negatives).

- `total_market_value_usd_m` = Σ quantity. For a **cash-neutral rotation**
  (sells = buys) MV is unchanged; for a **new-sleeve BUY package** MV =
  current MV + Σ buys. (Precision 2.)
- `hy_allocation_pct` = 100 × (Σ qty where `rating_bucket=="HY"`) / MV. (Prec 2.)
- `weighted_modified_duration_years` = Σ(qty × `modified_duration_years`) / MV.
  (Prec 2.)
- `weighted_yield_to_maturity_pct` = Σ(qty × `yield_to_maturity_pct`) / MV.
  (Prec 2.)
- `hy_reduction_pct_points` = pre-trade HY% − post-trade HY%. (Prec 2.)
- `post_trade_watchlist_exposure_usd_m` = Σ qty where the holding's issuer has
  `watchlist == true`. (Prec 1.)
- Issuer concentration (per issuer) = 100 × (Σ qty for that issuer) / MV;
  compare to `issuer_concentration_limit_pct`.

**Rounding:** round each reported field independently to its declared precision
(standard half-up rounding). Trade notionals are in USD millions at precision 1.

### 3.2 Correlations (equity review / committee)
For each index, fetch monthly `levels` over the requested window
(inclusive of `level_start_date`..`level_end_date`).

- **Monthly simple returns:** `r_t = level_t / level_{t-1} − 1`.
  N monthly levels ⇒ **N−1 return observations** (12 levels ⇒ 11).
  `return_observations` = N−1.
- **Pearson correlation** between two return series x, y:
  `corr = Σ(x−x̄)(y−ȳ) / sqrt(Σ(x−x̄)² · Σ(y−ȳ)²)`. (Population vs sample
  std is irrelevant — it cancels.) **Round to 3 decimals.**
- `highest_positive` (a.k.a. `highest_concentration`) = the pair with the
  **maximum** correlation; `lowest` / `best_diversifier` = the pair with the
  **minimum** (most negative) correlation, over all pairs in the requested
  index set.
- **Pair ids must be sorted alphabetically within each pair**, and pair lists
  sorted as the template says.

## 4. Mapping decisions to enums (allocation engine)

This logic drives allocation views in tasks 003 and 005 and the sleeve actions.

For each requested `opportunity_set` at the target quarter:

1. **signal_score** = `macro-signals` `score` for that opportunity_set+quarter
   (report at precision 3 when the template asks for it).
2. **view** from score via `view_score_thresholds`:
   `score ≥ OW_min → OW`; `score ≤ UW_max → UW`; else `N`.
3. **prior_view** = `prior-views` record where `quarter == target_quarter`
   (its `previous_quarter` is the prior quarter; this record is the *standing
   view going into the target quarter*). Use its `view` (and its `conviction`
   if you need the prior conviction).
4. **change** = compare new `view` rank vs `prior_view` rank
   (`UW=-1,N=0,OW=1`): higher → `UP`, lower → `DOWN`, equal → `UNCHANGED`.
5. **conviction** from `|score|` via `conviction_thresholds`:
   `≥0.7 → HIGH`, `≥0.35 → MEDIUM`, else `LOW`.
6. **rationale_code** = the `rationale_code` field on the macro-signal record
   for that opportunity_set+quarter (do NOT invent one). Common values:
   `EUROPE_RECOVERY, JAPAN_POLICY_RISK, CHINA_DEPENDENCE, INDIA_OFFSET,
   LATAM_DIVERSIFIER, DURATION_SUPPORT, HY_VALUATION_RISK, DOLLAR_DEFENSIVE,
   RATE_CUT_SUPPORT, CREDIT_SPREAD_RISK, GROWTH_IMPROVES, NEUTRAL_BALANCE`.
7. **asset_class** (when required) = from `/api/allocation/opportunity-sets`
   (Equities / Duration / Credit / Currency).

This rule set reproduces every allocation row deterministically — trust it.

### 4.1 Risk overlay (allocation-refresh task)
Choose `overlay_code` + `primary_action` from the dominant cross-asset tilt in
the computed views, and `rationale_codes` as the priority-ordered drivers:

- **OW Duration (e.g. U.S. Treasuries OW) + UW Credit (HY UW)** →
  `DURATION_QUALITY_TILT` / `tilt_to_duration_quality`. rationale_codes
  (highest priority first): the supportive duration driver (`DURATION_SUPPORT`),
  then the credit-risk driver (`HY_VALUATION_RISK`), then the next strongest
  negative-risk driver (e.g. `CHINA_DEPENDENCE`).
- Predominantly **UW credit / spread risk** → `CREDIT_RISK_REDUCTION` /
  `trim_credit_beta`.
- Predominantly **OW cyclical equities, risk-on** → `EQUITY_BETA_EXTENSION` /
  `add_cyclical_equity_beta`.
- **Defensive currency tilt dominant** → `CURRENCY_DEFENSIVE_HEDGE` /
  `add_currency_hedge`.
- No material tilt → `NO_OVERLAY` / `hold_policy_weights`.
Order `rationale_codes` by business priority (strongest-conviction / largest
|score| risk driver first).

### 4.2 Sleeve actions (correlation review & committee)
Map each sleeve/opportunity_set to an action enum
(`trim, add, hold, hedge, monitor, rotate`):

- The sleeve driving the **highest correlation / concentration** (e.g. the
  China/EM core) and/or carrying a **UW** view → **`trim`**.
- A **low/negatively-correlated diversifier** with an **OW** view (e.g.
  Latin America, EM-ex-China) → **`add`**.
- A high-conviction **OW** offset (e.g. India) → **`add`**.
- A **currency** sleeve used as a defensive offset (e.g. USD) → **`hedge`**.
- Neutral/no-change → `hold` or `monitor`.

## 5. Per-task SOPs

### Task A — Energy-credit trade package (e.g. PF-EN-ALTA)
Template keys: `trade_package` (2 items, BUY), `post_trade_metrics`,
`constraint_checks`, `sales_positioning`, `data_precedence`.

1. Read the desk request (ticket_count, total notional, allowed actions). Split
   the total notional evenly across the tickets (e.g. 2 × USD 4.0m for an 8.0m
   package).
2. Build the **eligible buy universe**: bonds with `candidate == true` and
   (for energy mandates) `energy_linked == true`, whose **issuer is NOT
   watchlisted** (`/api/issuers` watchlist==false). This enforces
   `watchlist_avoidance_pass`.
3. Select two bonds that **(a)** are **different issuers** and **different
   subsectors** (satisfies `selected_issuer_diversification_pass` and
   `selected_subsector_diversification_pass`), **(b)** keep post-trade
   `hy_allocation_pct ≤ max_hy_allocation_pct` and post-trade
   `weighted_modified_duration_years` inside `duration_band_years`, and
   **(c)** improve carry while fitting the **dominant energy theme and client
   pitch** (do not blindly max carry — favor the theme with the highest energy
   `signal` score, typically LNG/gas, and avoid stretching HY to the cap).
   A robust, suitable package pairs an IG thematic anchor (e.g. LNG exporter)
   with one non-watchlist HY carry name in a different subsector.
4. Compute `post_trade_metrics` per §3.1 (MV = current MV + buys).
5. `constraint_checks`: each boolean is the pass/fail of its rule on the chosen
   package (HY cap, duration band, selected-issuer diversification, selected-
   subsector diversification, watchlist avoidance).
6. `sales_positioning`:
   - `target_segment` from the payload's `client_context` →
     `multi_asset_income` ("multi-asset income"), `private_bank_income`,
     `insurance_general_account`, `pension_liability_matching`,
     `endowment_opportunistic`.
   - `theme` from the dominant energy `signal`: high LNG signal →
     `lng_export_tailwind`; oil oversupply/negative → `oil_oversupply_caution`;
     midstream defensive → `midstream_stability`; renewables selective →
     `transition_bond_selectivity`; refining/watchlist caution →
     `avoid_watchlist_yield_trap`.
7. `data_precedence`: if the stale snapshot conflicts with the environment
   (MV, HY%, duration, holdings, ratings) → `current_environment_over_stale_payload`;
   if no conflict → `no_conflict_found`.
8. **Order `trade_package` ascending by `instrument_id`.**

### Task B — International equity correlation review (e.g. PF-INT-NEXVEN)
Template keys: `review_window`, `index_set`, `extreme_pairs`, `concentration`,
`diversification_candidates`, `sleeve_actions`.

1. Use the payload's `review_window` (level_start/end) and `index_universe`.
   Fetch levels for each index in the window; compute returns and
   `return_observations = N−1`.
2. Compute Pearson correlations for **all index pairs** (§3.2). Report
   `extreme_pairs.highest_positive` (max) and `.lowest` (min), pair ids sorted
   alphabetically, correlation to 3 dp.
3. `index_set` = the requested universe, sorted ascending alphabetically.
4. `concentration`:
   - `high_threshold_breached` = (max correlation ≥ `correlation_high_threshold`,
     i.e. ≥0.8).
   - `china_asia_dependence_flag` = true when the concentration is driven by
     China/EM/Asia overlap (the highest pairs are global-developed or
     EM/Asia/China names and the memo flags China/Asia dependence).
   - `primary_code`: `CHINA_ASIA_DEPENDENCE` when China/Asia/EM overlap drives
     it; `GLOBAL_DEVELOPED_OVERLAP` when developed-world indices dominate;
     `NO_MATERIAL_CONCENTRATION` when nothing breaches the high threshold.
5. `diversification_candidates` (from the allowed set, ascending): pick the
   indices that **structurally reduce the identified concentration** — for a
   China/Asia dependence, `IDX_EM_EX_CHINA` (de-China EM) and `IDX_LATAM`
   (lowest, often negative, correlation to China). Exclude an index that is
   itself part of the concentrated Asia/EM beta (e.g. `IDX_INDIA` is highly
   correlated to China, so it is usually NOT a China-dependence diversifier).
6. `sleeve_actions` (length 2, ordered by sleeve): `trim` the concentrated
   sleeve (e.g. China → `IDX_CHINA`) and `add` the best diversifier
   (e.g. Latin America → `IDX_LATAM`). `target_index_id` from the allowed set.

### Task C — Active allocation view refresh (CIO desk)
Template keys: `task_id`, `as_of_date`, `target_quarter`, `prior_quarter`,
`policy_id`, `allocation_views`, `risk_overlay`.

1. `task_id` = template `required_value` (e.g. `train_003`); `target_quarter`/
   `prior_quarter` from payload; `as_of_date` = env date; `policy_id` =
   top-level `policy_id` from `/api/policies` (e.g. `POLICY_SET_2026_05`).
2. `allocation_views`: one row per opportunity_set in the payload's
   `focus_opportunity_sets`, **in that exact order**. For each row compute
   `asset_class` (opportunity-sets), `view`, `change`, `conviction`,
   `rationale_code` per §4.
3. `risk_overlay` per §4.1 (overlay_code, primary_action, priority-ordered
   rationale_codes).

### Task D — Fixed-income risk rebalance (e.g. PF-FI-LUMEN)
Template keys: `rotation.trades`, `risk_metrics`, `exception_flags`,
`watchlist_handling`, `risk_note_code`.

1. Goal: reduce HY and clear watchlist exposure while keeping duration in band;
   prefer a **cash-neutral rotation** (Σ SELL notional = Σ BUY notional, MV
   unchanged). Use the portfolio's `POL_CREDIT_RISK_REDUCTION` block —
   `target_hy_reduction_pct = 4.0`.
2. **SELLs:** sell **every watchlisted holding in full** (clears
   `watchlist_exposure`), then sell additional HY holdings as needed to hit the
   HY-reduction target while keeping post-trade duration in `[3.0, 5.0]`.
   Use **current** quantities from the API (override stale memo quantities).
3. **BUYs:** only `candidate == true`, **non-watchlist**, typically **IG**
   bonds from the memo shortlist / eligible universe (enforces
   `buys_avoid_watchlist == true`). Size buys so total buys = total sells and
   post-trade duration stays in band (longer-duration IG buys offset the
   duration lost by selling).
4. Compute `risk_metrics` per §3.1: `post_trade_hy_allocation_pct`,
   `post_trade_duration_years`, `hy_reduction_pct_points`,
   `post_trade_watchlist_exposure_usd_m` (target 0.0).
5. `exception_flags`: `hy_cap_pass` (post HY ≤ cap), `duration_band_pass`
   (post dur in band), `target_hy_reduction_met` (reduction ≥
   `target_hy_reduction_pct`), `watchlist_exposure_cleared` (post watchlist
   exposure == 0).
6. `watchlist_handling`: `watchlist_sell_ids` = sold watchlist instruments
   (ascending), `buys_avoid_watchlist` = true if no buy is watchlisted.
7. `risk_note_code`: `watchlist_concentration` when the driving issue was
   watchlist exposure; `hy_cap_pressure` when HY cap was the binding concern;
   `duration_preservation` when duration was the key trade-off;
   `carry_tradeoff` when carry was sacrificed; `no_action` if no trade.
8. **Order `trades`: all SELL before all BUY, then ascending `instrument_id`
   within each action.**

### Task E — Multi-asset risk-board reconciliation (e.g. PF-MA-CYGNUS)
Mixed credit + equity sleeves under `POL_MULTI_ASSET_RISK`. Identify and rank
**material exceptions**: HY over/near cap, duration out of band, watchlist
concentration, and equity correlation ≥ `correlation_high_threshold`. Escalate
to committee when **two or more** material exceptions exist
(`committee_escalation_threshold`). Follow the specific answer_template's enums
and ordering; reuse §3 (credit metrics + correlations) and §4 (mappings).

### Task F — Committee combined decision (e.g. PF-MA-HELIO / PF-MA-VEGA)
Template keys (HELIO example): `correlation_summary`, `target_sleeve_actions`,
`allocation_views`, `rebalance_trigger`, `portfolio_risk_concentration_flag`,
`next_step`.

1. `correlation_summary` (order: `highest_concentration`, then
   `best_diversifier`): from the requested equity index set compute max and min
   Pearson correlation (§3.2); pair ids sorted alphabetically, corr 3 dp.
2. `target_sleeve_actions` (fixed item order per template) per §4.2.
3. `allocation_views` (fixed item order per template): one row per
   opportunity_set with `prior_view`, `signal_score` (3 dp), `view`, `change`,
   `conviction`, `rationale_code` per §4.
4. `rebalance_trigger`: `correlation_cap_breach` when max equity correlation ≥
   high threshold; else `hy_cap_pressure` / `duration_drift` /
   `watchlist_concentration` per the binding credit issue; `committee_review`
   if none binding but committee is reviewing.
5. `portfolio_risk_concentration_flag` = true when a high-threshold
   concentration (correlation or otherwise) is breached.
6. `next_step`: `approve_with_monitoring` when actionable but with a flagged
   risk; `approve_rotation` when clean; `defer_pending_risk_review` when
   exceptions need escalation; `reject_constraint_breach` when a hard constraint
   is violated.

## 6. Common pitfalls and exclusion rules

- **Source precedence:** always recompute from live API positions/marks; never
  trust stale payload quantities, watchlist flags, or HY% (e.g. a memo's
  `stale_quantity_usd_m` may differ from the current holding).
- **as_of_date** = environment date (`2026-05-29`), not the payload date.
- **Watchlist** comes from `/api/issuers` (`watchlist` bool) joined via
  `issuer_id`; never buy a watchlisted issuer; sell all watchlisted holdings in
  risk-reduction tasks.
- **`candidate == false` bonds are not buyable** — they are existing-holding or
  off-the-run instruments. Only buy `candidate == true`.
- **HY cap is a ceiling (≤20%), not a target.** Do not stretch HY to the cap
  for carry; suitable income packages stay comfortably inside it.
- **Issuer & subsector diversification** in trade packages is checked on the
  *selected* bonds (different issuers, different subsectors), not the whole
  portfolio (the existing book may already exceed the issuer-concentration
  limit on a legacy line, which is not your responsibility to fix in a 2-ticket
  add).
- **Return observations = levels − 1.** Off-by-one here breaks correlations.
- **Pair ordering:** index ids alphabetical *within* each pair; then order the
  pair list per the template.
- **Allocation `change`** is measured against the standing prior view for the
  target quarter (the `prior-views` record whose `quarter == target_quarter`),
  not against a different quarter.
- **rationale_code and signal_score are read from `macro-signals`** — do not
  derive a rationale from your own narrative.
- **Rounding precision is per field** (notionals 1 dp; %, duration, YTM, MV 2 dp;
  correlations & signal scores 3 dp). Round at the end, each field independently.
- **Emit only the JSON object**, with every required key present and only the
  allowed enum values.

## 7. Quick reference: enum cheat-sheet

- View: `UW / N / OW` from score thresholds (−0.35 / +0.35).
- Change: `UP / DOWN / UNCHANGED` (new view rank vs prior view rank).
- Conviction: `LOW / MEDIUM / HIGH` from |score| (0.35 / 0.7).
- Trade actions: `BUY / SELL / HOLD / NO_TRADE` (credit package);
  `BUY / SELL` (rotation).
- Sleeve actions: `trim / add / hold / hedge / monitor / rotate`.
- data_precedence: `current_environment_over_stale_payload /
  local_payload_over_current_environment / no_conflict_found`.
- Concentration primary_code: `CHINA_ASIA_DEPENDENCE /
  GLOBAL_DEVELOPED_OVERLAP / NO_MATERIAL_CONCENTRATION`.
- Overlay: `DURATION_QUALITY_TILT / CREDIT_RISK_REDUCTION /
  EQUITY_BETA_EXTENSION / CURRENCY_DEFENSIVE_HEDGE / NO_OVERLAY` paired with
  `tilt_to_duration_quality / trim_credit_beta / add_cyclical_equity_beta /
  add_currency_hedge / hold_policy_weights`.
- Committee next_step: `approve_rotation / approve_with_monitoring /
  defer_pending_risk_review / reject_constraint_breach`.
