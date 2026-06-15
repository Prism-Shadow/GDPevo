---
name: asteria-investment-office-json
description: >-
  Produce strict-JSON deliverables for the Asteria Investment Office (CIO / credit
  desk) task family: energy/fixed-income credit trade packages, international equity
  correlation reviews, cross-asset active-allocation view refreshes, fixed-income
  risk-rebalance rotations, and combined committee decision files. Use this whenever
  a prompt references an Asteria portfolio (PF-*), the shared Asteria HTTP/JSON
  environment, an answer_template.json output contract, and asks for trade packages,
  correlation/concentration findings, allocation views (UW/N/OW), or rotation/rebalance
  JSON. Covers which API endpoints to call, exact formulas/rounding, controlled-enum
  mapping, and current-environment-over-stale-payload precedence.
---

# Asteria Investment Office — Strict-JSON Task Solver

You answer institutional investment-office tasks that each return ONE strict JSON
object matching a provided `answer_template.json`. The shared **Asteria environment**
is a read-only HTTP/JSON API and is the **single source of truth (book of record)**.
A local payload (desk_request / review_request / allocation_request / risk memo /
committee packet) provides intake context that is often **stale**; whenever it
disagrees with the environment on marks, ratings, holdings, quantities, watchlist
status, dates, prior views, or policy values, **use the environment**.

## 0. Golden rules (apply to every task)

1. **Read the `answer_template.json` first.** It defines the exact required keys,
   list lengths, item ordering, enum allowed-values, and per-field numeric precision.
   Emit exactly those keys with values in the declared enums. Return **only** the JSON
   object — no prose, no markdown fences, no extra keys.
2. **Environment overrides stale payload.** Pull current holdings, quantities,
   ratings, watchlist flags, prior views, signal scores, policy thresholds, and the
   `as_of_date` from the API — never from the local payload.
3. **`as_of_date` (and `policy_id`, target/prior quarter) come from the environment.**
   The current env `as_of_date` is the value returned by `/api/policies`,
   `/api/portfolios/<id>`, and most endpoints (they agree). Use that date, not the
   payload's request_date / memo_as_of_date / committee_date.
4. **Round per field.** Apply the precision the template states for each field
   (`precision: N` = N decimals). Round at the end, after computing in full precision.
   Notionals are usually 1 decimal; percentages and durations 2 decimals; correlations
   and signal scores 3 decimals. A whole number stays valid at its precision (e.g. 4.0,
   68.0, 5.8).
5. **Honor ordering rules.** "Sort ascending by instrument_id", "SELL before BUY then
   instrument_id ascending", "item_order: [...]" (fixed business order), "ascending
   alphabetical by index id", "rows in payload focus order". Follow the template's
   exact instruction; do not re-sort against it.
6. **Pairs/lists of index ids are sorted alphabetically inside each pair.**

## 1. Environment API quick reference (base `http://127.0.0.1:8036`, all GET/JSON)

| Endpoint | Use it for |
|---|---|
| `/api/catalog` | All valid ids (portfolio, policy, index, issuer, bond, opportunity_set). |
| `/api/policies` | Constraint thresholds, correlation thresholds, allocation-mapping thresholds, current `as_of_date`, and the global `policy_id` (e.g. `POLICY_SET_2026_05`). |
| `/api/portfolios` | All portfolio summaries (name, market_value, holding_count, `constraint_policy_id`). |
| `/api/portfolios/<id>` | One portfolio: objective, constraints (with its policy_id), and current holdings (`instrument_id`, `quantity_usd_m`, sleeve). |
| `/api/instruments/bonds` | Bond master: `rating_bucket` (IG/HY), `modified_duration_years`, `yield_to_maturity_pct`, `coupon_pct`, `spread_bps`, `subsector`, `sector`, `issuer_id`, `energy_linked`, `candidate`, `recommended_theme_tags`. Filters: `?candidate=true`, `?rating_bucket=HY`, `?issuer_id=...`. |
| `/api/issuers` | Issuer `watchlist` (bool), `credit_outlook`, `rating_bucket`, sector/subsector, research_tags. **Watchlist lives on the ISSUER, not the bond.** |
| `/api/market/energy` | Current energy signals (each with `score` and `direction`), `pitch_themes`. Drives credit theme selection. |
| `/api/indices` | Index metadata, `level_start_date`/`level_end_date`, region. |
| `/api/index-levels` / `/api/index-levels/<id>` | Monthly index levels (`date`, `level`) for correlations. |
| `/api/allocation/opportunity-sets` | Taxonomy: `opportunity_set` -> `asset_class` (Equities/Duration/Credit/Currency), `display_order`. |
| `/api/allocation/prior-views` | Standing prior views per opportunity_set per quarter (`view`, `conviction`, `quarter`, `previous_quarter`). |
| `/api/macro-signals` | Per opportunity_set per quarter: `score` (float), `rationale_code`, `drivers`. |

Always resolve the bond -> issuer chain: `bond.issuer_id` -> issuers entry ->
`watchlist`. A bond is "watchlist" iff its issuer's `watchlist` is true.

## 2. Core formulas (verified against the data model)

**Notional weighting.** All portfolio metrics weight by `quantity_usd_m` (notional /
market value in USD millions). Treat `quantity_usd_m` as the market value.

- `total_market_value_usd_m = Σ quantity_usd_m` over the post-trade book.
- `hy_allocation_pct = 100 * (Σ quantity of bonds with rating_bucket=="HY") / total`.
- `weighted_modified_duration_years = Σ(modified_duration_years_i * q_i) / Σ q_i`.
- `weighted_yield_to_maturity_pct = Σ(yield_to_maturity_pct_i * q_i) / Σ q_i`.
- `watchlist_exposure_usd_m = Σ quantity of bonds whose issuer.watchlist is true`.
- `hy_reduction_pct_points = pre_trade_hy_pct − post_trade_hy_pct` (positive = reduced).
- `issuer_concentration_pct (one issuer) = 100 * Σ quantity for that issuer / total`.

**Post-trade book construction.** Start from the current env holdings.
SELL subtracts `quantity_usd_m`; BUY adds it. Drop positions that reach ~0. Pre-trade
metrics use env holdings as-is.

**Correlations (Pearson on monthly simple returns).**
1. Take each index's monthly levels within `[level_start_date, level_end_date]`
   inclusive (sorted by date). With 12 monthly levels you get **11 returns**;
   `return_observations` = (#levels in window − 1).
2. Simple return `r_t = level_t / level_{t-1} − 1`.
3. Pearson `corr(X,Y) = cov(X,Y) / (std(X)*std(Y))` (population or sample — they cancel).
4. Round correlation to **3 decimals**.
5. Compute correlations only across the **requested index universe/subset**.

**Allocation view mapping** (thresholds from `/api/policies.allocation_mapping`):
- Inputs per opportunity_set: macro `score` (for target quarter) and prior `view`.
- `view`: `score >= OW_min(0.35)` -> `OW`; `score <= UW_max(-0.35)` -> `UW`; else `N`.
- `conviction` (by `abs(score)`): `>= HIGH_abs_min(0.7)` -> `HIGH`;
  `>= MEDIUM_abs_min(0.35)` -> `MEDIUM`; `< LOW_abs_below(0.35)` -> `LOW`.
- `change` vs prior using `view_rank {UW:-1, N:0, OW:1}`: new rank > prior -> `UP`;
  new < prior -> `DOWN`; equal -> `UNCHANGED`.
- `rationale_code` = the macro signal's `rationale_code` for that opportunity_set/quarter
  (use it verbatim from the API; do not invent).
- `signal_score` field (when required) = the raw macro `score` (3 decimals; trailing
  zeros may drop, e.g. 0.48).

> Read these thresholds from `/api/policies` each run rather than hardcoding; the
> values above are the current defaults but the policy object is authoritative.

## 3. Quarter / prior-view lookup (critical, easy to get wrong)

For a **target quarter** (e.g. `Q2_2026`):
- **macro signal**: row where `opportunity_set` matches AND `quarter == target_quarter`.
- **prior view**: row in `/api/allocation/prior-views` where `opportunity_set` matches
  AND **`quarter == target_quarter`** (that row's `view`/`conviction` is the standing
  prior view; its `previous_quarter` equals the prior quarter). Do NOT filter prior-views
  by `quarter == prior_quarter`.

## 4. SOPs by task type

Identify the task from the prompt + which payload + which template keys are present.

### 4A. Credit trade package — BUY tickets ("trade strategy", `trade_package`)
Template signals: `trade_package`, `post_trade_metrics`, `constraint_checks`,
`sales_positioning`, `data_precedence`.

1. `GET /api/portfolios/<id>` (current holdings + constraints), `/api/instruments/bonds`,
   `/api/issuers`, `/api/market/energy`, `/api/policies`.
2. Read the ticket constraints from the prompt/payload: ticket_count, total notional,
   even split per ticket (e.g. 2 tickets / USD 8.0m -> 4.0 each), allowed actions (BUY).
3. **Eligible universe**: `candidate == true`, matching the requested sleeve/theme
   (e.g. `energy_linked == true` for an energy sleeve), not already held.
4. **Hard filters (must all hold for selected buys):**
   - Watchlist avoidance: exclude any bond whose **issuer** `watchlist == true`.
   - Post-trade `hy_allocation_pct <= max_hy_allocation_pct` (cap, default 20).
   - Post-trade `weighted_modified_duration_years` within `duration_band_years` [3.0,5.0].
   - Selected-ticket diversification: the chosen buys span **>=2 distinct issuers** and
     **>= subsector_min_count_for_diversified (2) distinct subsectors**.
5. **Selection priority among constraint-passing pairs** (this is NOT pure carry-max):
   (a) thematic fit to the **dominant current energy signal** (the highest-`score`
   signal — currently LNG/`LNG_EXPORT_PULL` ~0.72) and the desk's stated
   `preferred_exposures`; (b) **quality for a client income pitch** — prefer at least one
   IG anchor and keep HY comfortably under the cap; (c) then **maximize carry** (YTM).
   A higher-carry pair that is lower quality / off-theme loses to an on-theme IG-anchored
   pair that still adds carry.
6. `trade_package`: list of the selected BUYs, `notional_usd_m` per ticket, **sorted
   ascending by instrument_id**.
7. `post_trade_metrics`: compute on env holdings + buys (Section 2 formulas; precision
   per template — typically total/HY/duration/YTM at 2 decimals, but follow the field).
8. `constraint_checks` (booleans): `hy_cap_pass`, `duration_band_pass`,
   `selected_issuer_diversification_pass` (buys from distinct issuers),
   `selected_subsector_diversification_pass` (buys span >=2 subsectors),
   `watchlist_avoidance_pass` (no selected buy issuer is watchlisted). Note the
   "selected_*" checks judge the **selected tickets**, not the whole legacy book (the
   book may already exceed issuer concentration and that does not fail these flags).
9. `sales_positioning.target_segment`: map the client context — "multi-asset income" ->
   `multi_asset_income`; private-bank income -> `private_bank_income`;
   insurance general account -> `insurance_general_account`; pension/LDI ->
   `pension_liability_matching`; endowment/opportunistic -> `endowment_opportunistic`.
10. `sales_positioning.theme`: map the dominant energy signal / chosen exposure —
    LNG-export tilt -> `lng_export_tailwind`; defensive midstream -> `midstream_stability`;
    oil oversupply/discipline caution -> `oil_oversupply_caution`; transition/renewables
    selectivity -> `transition_bond_selectivity`; deliberately steering off watchlist
    yield -> `avoid_watchlist_yield_trap`.
11. `data_precedence`: if the stale snapshot disagrees with the env on MV/HY/duration/
    ratings -> `current_environment_over_stale_payload`; if no conflict ->
    `no_conflict_found` (rarely `local_payload_over_current_environment` — only if the
    prompt explicitly tells you to trust the payload).

### 4B. Fixed-income risk rebalance — rotation ("reduce HY / watchlist", `rotation`)
Template signals: `rotation.trades`, `risk_metrics`, `exception_flags`,
`watchlist_handling`, `risk_note_code`.

1. `GET /api/portfolios/<id>`, `/api/instruments/bonds`, `/api/issuers`, `/api/policies`.
   Use the portfolio's `constraint_policy_id` (e.g. `POL_CREDIT_RISK_REDUCTION`, which
   carries `target_hy_reduction_pct`, default 4.0).
2. **SELL side**: target the HY and watchlist pressure points among current holdings.
   - Sell ALL of every **watchlisted** holding (clears watchlist exposure to 0).
   - Sell additional non-watchlist **HY** holdings as needed to meet the target HY
     reduction (>= `target_hy_reduction_pct` and any payload `minimum_preferred_hy_reduction`)
     while keeping duration in band — prefer selling shorter-duration HY so post-trade
     duration stays inside [3.0,5.0] and does not undershoot.
3. **BUY side**: only from eligible candidates (`candidate == true`) that are
   **NOT watchlisted** (reject any watchlist candidate, e.g. a high-carry but watchlisted
   name — record it as avoided). Prefer IG names that preserve/lift duration and carry.
4. **Cash-neutral**: total BUY notional == total SELL notional (keeps total MV constant)
   unless the prompt says otherwise.
5. `rotation.trades`: **SELL rows before BUY rows; within each action sort instrument_id
   ascending**; `quantity_usd_m` at 1 decimal.
6. `risk_metrics`: `post_trade_hy_allocation_pct` (2dp), `post_trade_duration_years`
   (2dp), `hy_reduction_pct_points = pre − post` (2dp),
   `post_trade_watchlist_exposure_usd_m` (1dp, normally 0.0).
7. `exception_flags` (bool): `hy_cap_pass` (post HY <= cap), `duration_band_pass`
   (post duration in band), `target_hy_reduction_met` (reduction >= target),
   `watchlist_exposure_cleared` (post watchlist exposure == 0).
8. `watchlist_handling`: `watchlist_sell_ids` = sold instruments whose issuer is
   watchlisted (ascending); `buys_avoid_watchlist` = true if no bought issuer is watchlisted.
9. `risk_note_code`: choose the dominant resolved risk — a watchlisted-issuer
   concentration that the rotation clears -> `watchlist_concentration`; HY cap being the
   binding pressure -> `hy_cap_pressure`; duration kept/preserved as the headline ->
   `duration_preservation`; a carry-vs-risk tradeoff -> `carry_tradeoff`; no trade ->
   `no_action`.

### 4C. International equity correlation review (`extreme_pairs` / `concentration`)
Template signals: `review_window`, `index_set`, `extreme_pairs`, `concentration`,
`diversification_candidates`, `sleeve_actions`.

1. `GET /api/portfolios/<id>` (held sleeves), `/api/policies` (correlation thresholds:
   high 0.8, low 0.2), `/api/indices`, `/api/index-levels`.
2. `review_window`: use the payload's `level_start_date`/`level_end_date`;
   `return_observations` = (#monthly levels in window − 1).
3. `index_set`: the requested universe, **ascending alphabetical**.
4. Compute the pairwise Pearson correlation matrix over the universe (Section 2).
5. `extreme_pairs.highest_positive` = max-correlation pair; `extreme_pairs.lowest` =
   minimum (most negative) pair. Each `pair_id` is the two ids alphabetically; correlation
   to 3 decimals.
6. `concentration`:
   - `high_threshold_breached` = any pair correlation > `correlation_high_threshold` (0.8).
   - `china_asia_dependence_flag` = true when the China/Asia cluster is highly
     intercorrelated and the portfolio leans on it (China + EM/Asia sleeves with high
     mutual correlation, reinforced by memo concern codes like `CHINA_DEDICATED_SLEEVE` /
     `ASIA_BETA_OVERLAP`).
   - `primary_code`: `CHINA_ASIA_DEPENDENCE` when the China/Asia overlap is the binding
     concentration; `GLOBAL_DEVELOPED_OVERLAP` when developed-world (World/EAFE/ACWI)
     overlap dominates; `NO_MATERIAL_CONCENTRATION` when nothing breaches the high
     threshold.
7. `diversification_candidates` (from the allowed set, ascending): pick the indices that
   genuinely **reduce the concentration anchor** — i.e. NOT highly correlated to the
   anchor (China). A candidate whose correlation to the anchor exceeds the high threshold
   (0.8) does NOT diversify and is excluded (e.g. India ~0.85 vs China is excluded), while
   a strongly negative one (LatAm) and a structural de-China index (EM-ex-China) are
   included.
8. `sleeve_actions` (ascending by sleeve, length per template): **trim** the
   concentration-anchor sleeve toward its index, and **add** the best diversifier sleeve
   toward its index. Use the portfolio's sleeve names and the `target_index_allowed_values`.

### 4D. Active allocation view refresh (`allocation_views` + `risk_overlay`)
Template signals: `allocation_views` (8 rows), `risk_overlay`, lineage keys.

1. `GET /api/allocation/opportunity-sets`, `/api/allocation/prior-views`,
   `/api/macro-signals`, `/api/policies`.
2. Lineage: `as_of_date` (env), `target_quarter`/`prior_quarter` (payload), `policy_id`
   (env global, e.g. `POLICY_SET_2026_05`), `task_id` (template `required_value`).
3. For each opportunity_set in the payload's **focus order** (preserve order):
   `asset_class` from opportunity-sets taxonomy; `view`/`conviction`/`change`/
   `rationale_code` via Section 2 mapping using the target-quarter macro score and the
   target-quarter prior view (Section 3).
4. `risk_overlay`:
   - `overlay_code` + `primary_action` from the view pattern:
     duration OW & HY/credit UW -> `DURATION_QUALITY_TILT` / `tilt_to_duration_quality`;
     credit/HY risk the dominant cut -> `CREDIT_RISK_REDUCTION` / `trim_credit_beta`;
     broad cyclical-equity OW -> `EQUITY_BETA_EXTENSION` / `add_cyclical_equity_beta`;
     currency-defensive dominant -> `CURRENCY_DEFENSIVE_HEDGE` / `add_currency_hedge`;
     nothing material -> `NO_OVERLAY` / `hold_policy_weights`.
   - `rationale_codes`: the top supporting drivers, **highest business priority first**
     (the tilt's primary driver first, then the risk being reduced) — typically ordered
     by the strength (|score|) / centrality of the views that justify the overlay.

### 4E. Combined committee decision file (`correlation_summary` + `allocation_views` + decision enums)
Template signals: `correlation_summary`, `target_sleeve_actions`, `allocation_views`
(with `prior_view`/`signal_score`), `rebalance_trigger`,
`portfolio_risk_concentration_flag`, `next_step`.

1. Do the correlation review (4C) on the requested **subset** and the allocation views
   (4D) on the requested opportunity sets, then combine.
2. `correlation_summary` (item_order [highest_concentration, best_diversifier]):
   highest_concentration = max-correlation pair in the subset; best_diversifier =
   minimum (most negative) pair. Pairs alphabetical, correlation 3dp.
3. `allocation_views`: include `prior_view` (target-quarter prior view), `signal_score`
   (raw macro score, 3dp), plus `view`/`change`/`conviction`/`rationale_code`. Keep the
   requested `item_order`.
4. `target_sleeve_actions` (same item_order): map each set's resolved view to an action —
   `OW` -> `add`; `UW` -> `trim`; `N`/`hold` -> `hold`; a currency set used as a defensive
   offset -> `hedge`; rebalance/rotate context -> `rotate`/`monitor` as the template's
   allowed values fit.
5. `rebalance_trigger`: if any subset pair correlation exceeds the high threshold ->
   `correlation_cap_breach`; otherwise pick the binding pressure
   (`hy_cap_pressure` / `duration_drift` / `watchlist_concentration`) or `committee_review`.
6. `portfolio_risk_concentration_flag`: true when a concentration/correlation breach is
   present.
7. `next_step`: a breach with a viable rotation that still needs oversight ->
   `approve_with_monitoring`; clean rotation -> `approve_rotation`; unresolved/ambiguous
   risk -> `defer_pending_risk_review`; a hard constraint still violated post-trade ->
   `reject_constraint_breach`.

## 5. Common pitfalls & exclusions

- **Watchlist is on the issuer.** Always join bond -> issuer; never read a bond field
  for watchlist. Watchlisted names are excluded from BUYs and are first to be SOLD.
- **Stale payload values are traps.** Stale snapshots/exception boards may show wrong
  quantities, HY%, marks, "kept USD overweight", or omit the latest index levels — always
  recompute from the env. Set `data_precedence` to `current_environment_over_stale_payload`
  when they conflict.
- **`return_observations` = levels − 1**, not the number of levels.
- **Prior-view row keying**: filter prior-views by `quarter == target_quarter`
  (Section 3). Using the `prior_quarter` row is wrong.
- **`rationale_code` and `signal_score` are taken from the macro-signals API verbatim**
  (rationale by code, score by raw value); do not derive your own.
- **Selection is not naive carry-max** (4A) and not naive lowest-correlation (4C):
  apply theme/quality (credit) and anchor-reduction (correlation) logic above.
- **"selected_*" diversification flags** judge only the chosen tickets, not the
  pre-existing book; the legacy book may already breach issuer concentration without
  failing these flags.
- **Cash-neutral rotations**: BUY notional == SELL notional unless told otherwise; total
  MV should be unchanged.
- **Enum discipline**: every enum field must be one of the template's allowed_values
  exactly (case/spelling). Opportunity-set strings (e.g. "U.S. Treasuries", "Corporate
  High Yield", "Latin America", "USD"/"EUR") must match the taxonomy exactly.
- **Ordering & lengths**: respect `required_length`, `length`, and `item_order`/`ordering`
  precisely; emit lists in the stated order.
- **Numbers**: compute in full precision, round once at the end to the field's declared
  precision; do not pad or truncate beyond the stated decimals.

## 6. Workflow checklist

1. Read the prompt + payload; open `answer_template.json`; note keys, enums, lengths,
   ordering, precisions, and any `required_value` fields.
2. Pull the env: `/api/policies` (thresholds + as_of_date + policy_id),
   `/api/portfolios/<id>`, and the task-specific endpoints (bonds/issuers/energy, or
   indices/index-levels, or opportunity-sets/prior-views/macro-signals).
3. Reconcile payload vs env; decide precedence.
4. Compute (Section 2 formulas) and select per the relevant SOP (Section 4).
5. Map decisions to controlled enums (Section 4).
6. Assemble JSON in exact template shape, apply ordering, round per field.
7. Validate: all required keys present, enums valid, list lengths/orders correct, numbers
   at declared precision, and the output is the JSON object only.
