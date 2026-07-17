# Asteria Investment Office — Risk Evaluation Skill

Transferable execution knowledge for the Asteria institutional portfolio-risk
tasks. The test task will give you one portfolio, a local request payload
(`input/payloads/`), an `answer_template.json` output contract, and access to
the same remote Asteria environment described below. You have NOT seen the
train tasks; this file is your playbook.

The tasks draw from three workflows:
- **A. Energy / fixed-income trade strategy** (bond ticket selection + post-trade metrics).
- **B. International equity correlation review** (compute correlations from index levels).
- **C. Cross-asset active allocation view updates** (map macro signals to views).
- A fourth shape **D** blends B + C into one committee JSON.

---

## 1. Environment access (the book of record)

Base URL: `<remote-env-url>`

The remote environment is the **current book of record**. Local payloads in
`input/payloads/` are intake context and are frequently **stale** (old worksheet
dates, stale marks, stale quantities). When a local payload conflicts with the
environment, prefer the environment unless the task prompt explicitly says
otherwise.

Call with `curl` (Bash) or Python `urllib`/`requests`. Always re-fetch live data
per task — do not assume cached shapes.

### Endpoints that matter

| Endpoint | Use |
|---|---|
| `GET /api/catalog` | All portfolio ids, policy ids, index ids, issuer ids, bond ids, opportunity sets. |
| `GET /api/policies` | Constraints: HY cap, duration band, diversification rules, correlation thresholds, allocation-mapping thresholds. |
| `GET /api/portfolios` | Portfolio summaries. |
| `GET /api/portfolios/<id>` | Objective, constraints (incl. `policy_id`, `max_hy_allocation_pct`, `duration_band_years`, optional `target_hy_reduction_pct`), current holdings, `market_value_usd_m`, `as_of_date`. |
| `GET /api/instruments/bonds` | Held + candidate bond universe. Filters: `?candidate=true`, `?rating_bucket=HY`. |
| `GET /api/issuers` | Issuer `sector`, `subsector`, `rating_bucket`, `watchlist` (bool), `credit_outlook`, `research_tags`. **Authoritative watchlist source.** |
| `GET /api/market/energy` | Energy commodity signals (scores, directions) and `pitch_themes` for sale positioning. |
| `GET /api/indices` | Index metadata (region, currency, `level_start_date`, `level_end_date`, frequency). |
| `GET /api/index-levels` / `GET /api/index-levels/<id>` | Monthly index levels `{date, level}`. **No correlations are precomputed — compute them yourself.** |
| `GET /api/allocation/opportunity-sets` | Cross-asset taxonomy: `opportunity_set`, `asset_class`, `display_order`. |
| `GET /api/allocation/prior-views` | Prior-quarter active views (`view`, `conviction`, `quarter`, `previous_quarter`). |
| `GET /api/macro-signals` | Per opportunity-set `score`, `rationale_code`, `drivers`, `quarter`. Drives view/conviction/rationale. |

Most list endpoints accept simple equality filters matching field names
(`?rating_bucket=HY`, `?candidate=true`, `?quarter=Q3_2026`).

### Environment rules
- Use only the listed endpoints. Do not read source/data files or any local `env/` directory.
- Numeric precision in the final answer must follow `input/payloads/answer_template.json` per field.
- The environment `as_of_date` (e.g. `2026-05-29`) is the as-of date for answers unless the task gives another.

---

## 2. Data-precedence rule (applies to every workflow)

1. Read the local request payload to learn the *ask* (which portfolio, which
   window, which opportunity sets, ticket count, totals, preferences).
2. Read the **environment** for the actual current values used in computation.
3. If a stale local snapshot (worksheet date, stale marks, stale quantities,
   `stale_exception_board`, `stale_local_note`) conflicts with the environment,
   compute from the environment and emit `data_precedence =
   current_environment_over_stale_payload`.
4. If no stale-conflict exists, emit `no_conflict_found`.
5. `local_payload_over_current_environment` is essentially never correct unless
   the task prompt explicitly overrides.

Where the answer schema has a `data_precedence` field, set it accordingly.
Where it does not (e.g. workflow B/C/D), still apply the rule silently in your
computations.

---

## 3. Workflow A — Energy / fixed-income trade strategy

Tasks ask for a proposed set of BUY (and in rotation variants SELL+BUY) bond
tickets that improve carry while keeping the portfolio inside credit-risk
constraints, plus post-trade metrics, constraint booleans, sales positioning,
and a data-precedence declaration. Output shape follows the task's own
`answer_template.json`; two variants were seen:

- **BUY-only variant:** `trade_package` (list of `{action,instrument_id,notional_usd_m}`),
  `post_trade_metrics`, `constraint_checks`, `sales_positioning`, `data_precedence`.
- **Rotation variant:** `rotation.trades` (list of `{action,instrument_id,quantity_usd_m}`),
  `risk_metrics`, `exception_flags`, `watchlist_handling`, `risk_note_code`.

### SOP
1. `GET /api/portfolios/<id>` — read `constraints`, `holdings`, `market_value_usd_m`.
2. `GET /api/instruments/bonds?candidate=true` — candidate universe.
3. `GET /api/issuers` — join each candidate's `issuer_id` to get `watchlist`,
   `sector`, `subsector`, `rating_bucket`. (The bonds endpoint `watchlist` field
   is unreliable/None — use issuers.)
4. `GET /api/market/energy` — for energy tasks, read signals + `pitch_themes`.
5. `GET /api/policies` — confirm HY cap, duration band, diversification, and
   any `target_hy_reduction_pct`.

### Candidate selection rules
- Only buy bonds with `candidate=true`.
- For an **energy** desk task, require `energy_linked=true` and match desk
  preferences (e.g. LNG exporters / gas demand). For a general credit rotation,
  non-energy IG candidates (data centers, mining, REIT, banking, utility) are
  eligible.
- **Exclude watchlist issuers** (`watchlist=true`) from BUYs. Identify them via
  `/api/issuers`, not the bond record.
- Exclude duration-ineligible distractors: a single bond whose
  `modified_duration_years` is far outside the band is a distractor even if
  attractive on yield; the *portfolio-weighted* duration must stay in band, but
  avoid buying bonds that would push it out.
- Honor the ticket count, total notional, and split rules from the request
  payload exactly (e.g. "exactly two BUY tickets totaling USD 8.0M split evenly"
  → two tickets of 4.0M each).
- Prefer candidates that **improve carry** (higher `yield_to_maturity_pct`)
  while keeping HY% under the cap and duration in band.
- BUYs must be **diversified**: distinct issuers and distinct subsectors among
  the selected tickets (this drives `selected_issuer_diversification_pass` and
  `selected_subsector_diversification_pass`; policy `subsector_min_count_for_diversified`
  is typically 2 distinct subsectors among what you add).

### Rotation (SELL+BUY) rules
- Identify current holdings on watchlist issuers and SELL them first
  (`watchlist_sell_ids`).
- SELL enough HY to meet the portfolio's `target_hy_reduction_pct` (percentage
  points) — you may overshoot the target when also clearing watchlist risk.
- BUY IG (or otherwise eligible) candidates that fund the SELL notional, keep
  weighted duration inside the band, and avoid watchlist issuers.
- Use **environment** holding quantities for SELL sizes, not stale local
  `stale_exception_board` quantities.

### Post-trade metric computation (market-value-weighted)
Treat each holding's `quantity_usd_m` as its market value (par approximation;
no separate clean-price field is provided). After applying trades:

- `total_market_value_usd_m` = sum of all post-trade holding quantities (for
  BUY-only funded by new allocation, add the bought notionals to the starting
  `market_value_usd_m`; for a balanced rotation, total MV is unchanged).
- `hy_allocation_pct` = (sum of post-trade HY holding market values) / total MV × 100.
- `weighted_modified_duration_years` = Σ(qty_i × `modified_duration_years_i`) / total MV.
- `weighted_yield_to_maturity_pct` = Σ(qty_i × `yield_to_maturity_pct_i`) / total MV.
- A holding is HY iff its issuer/bond `rating_bucket == "HY"` (or `rating` startswith HY).

Verify each bond's `modified_duration_years` and `yield_to_maturity_pct` from
`/api/instruments/bonds` (match by `instrument_id`).

### Constraint checks (booleans)
Read thresholds from `/api/policies` (policy_id from portfolio constraints):
- `hy_cap_pass`: post-trade `hy_allocation_pct` <= `max_hy_allocation_pct` (e.g. 20.0).
- `duration_band_pass`: post-trade weighted duration within `duration_band_years` (e.g. [3.0, 5.0]) inclusive.
- `selected_issuer_diversification_pass`: selected BUY tickets have >=2 distinct issuers.
- `selected_subsector_diversification_pass`: selected BUY tickets have >=2 distinct subsectors.
- `watchlist_avoidance_pass`: none of the BUYs is a watchlist issuer (`watchlist_avoidance_pass`); for rotation also `watchlist_exposure_cleared` (post-trade watchlist MV == 0) and `buys_avoid_watchlist`.
- Rotation adds `target_hy_reduction_met`: actual HY reduction (ppt) >= `target_hy_reduction_pct`.

### Sales positioning (energy BUY-only variant)
- `target_segment`: derive from the request's client context (e.g.
  "multi-asset income update" → `multi_asset_income`). Allowed values are in
  the template.
- `theme`: pick the `pitch_theme` from `/api/market/energy` that matches the
  dominant positive energy signal backing the trade (e.g. LNG export growth →
  `lng_export_tailwind`). Map energy `pitch_themes` to the template's theme
  enum (LNG_EXPORT_GROWTH→`lng_export_tailwind`, MIDSTREAM_DEFENSIVE_CARRY→`midstream_stability`,
  OIL_DISCIPLINE→`oil_oversupply_caution`, RENEWABLES_RATE_RELIEF→`transition_bond_selectivity`,
  AVOID_REFINING_WATCHLIST→`avoid_watchlist_yield_trap`).

### Output precision & ordering
- `notional_usd_m` / `quantity_usd_m`: 1 decimal.
- All `post_trade_metrics` and `risk_metrics` percentages/durations: 2 decimals
  (except `post_trade_watchlist_exposure_usd_m`: 1 decimal).
- BUY-only `trade_package`: sort **ascending by `instrument_id`**.
- Rotation `rotation.trades`: sort **SELL before BUY, then `instrument_id`
  ascending within each action**.
- `watchlist_sell_ids`: ascending `instrument_id` order.
- Use only enum values from the template. Always emit the `data_precedence`
  value when the schema requires it.

---

## 4. Workflow B — International equity correlation review

Compute pair correlations across an index universe from monthly index levels,
find extreme pairs, flag concentration, and propose sleeve actions.

### SOP
1. Read the request payload for `review_window` (`level_start_date`,
   `level_end_date`) and `index_universe` (list of index ids).
2. For each index id, `GET /api/index-levels/<id>` → `levels` list of
   `{date, level}` (monthly).
3. Build **monthly simple returns**: r_t = (level_t − level_{t−1}) / level_{t−1}
   for consecutive levels. Number of return observations = (number of levels) − 1.
4. Compute **Pearson correlation** over the common return series for every pair.

```
pearson(a,b) = Σ((a_k−mean_a)(b_k−mean_b)) / sqrt(Σ(a_k−mean_a)² × Σ(b_k−mean_b)²)
```

5. `extreme_pairs`:
   - `highest_positive`: the pair with the maximum correlation.
   - `lowest`: the pair with the minimum correlation (most negative).
   - Each `pair_id` is a 2-element list **sorted alphabetically** by index id.
   - `correlation` rounded to **3 decimals**.
6. `review_window`: echo `level_start_date`, `level_end_date`, and
   `return_observations` (integer = levels − 1).
7. `index_set`: the universe ids, **ascending alphabetical**.

### Concentration flags (thresholds from `/api/policies` → `correlation`)
- `correlation_high_threshold` (e.g. 0.8), `correlation_low_threshold` (e.g. 0.2).
- `high_threshold_breached`: true if any pair correlation >= high threshold.
- `china_asia_dependence_flag`: true when China/Asia-Pacific pairs breach the
  high threshold (CHINA vs EM, CHINA vs AC_ASIA_PAC_EX_JP, etc.). 
- `primary_code`: `CHINA_ASIA_DEPENDENCE` when China/Asia concentration fires;
  `GLOBAL_DEVELOPED_OVERLAP` when the breach is among developed/global indices
  (WORLD/EAFE/etc.); `NO_MATERIAL_CONCENTRATION` when nothing breaches.
- `diversification_candidates`: indices with the lowest (ideally negative)
  correlation to the concentration source, restricted to the template's
  allowed set (typically `IDX_EM_EX_CHINA`, `IDX_INDIA`, `IDX_LATAM`),
  **ascending alphabetical**.

### Sleeve actions
- Exactly the number required by the template (often 2), **ordered ascending by
  `sleeve`**.
- Each item: `{sleeve, action, target_index_id}`.
- `action` from `{trim, add, hold, hedge, monitor, rotate}`: `trim` the
  concentrated sleeve (e.g. China), `add` the best diversifier sleeve.
- `target_index_id` from the template's allowed set.

### Precision
- All correlations: **3 decimals**. No rounding of level inputs.

---

## 5. Workflow C — Cross-asset active allocation view updates

Map macro signals + prior views into a refreshed set of active allocation views
plus a portfolio-level risk overlay.

### SOP
1. Read the request payload: `target_quarter`, `prior_quarter`, and the
   focus `opportunity_sets` list (output row order = this list's order).
2. `GET /api/allocation/opportunity-sets` — map each opportunity set to its
   `asset_class` (Equities / Duration / Credit / Currency).
3. `GET /api/allocation/prior-views` — find the prior-quarter view and
   conviction for each focus opportunity set (match `quarter` ==
   `prior_quarter`, or use the row whose `previous_quarter` precedes the target).
4. `GET /api/macro-signals` — for the target quarter, get each focus set's
   `score`, `rationale_code`, `drivers`.
5. `GET /api/policies` → `allocation_mapping` for thresholds (and `policy_id`
   = top-level `policy_id` e.g. `POLICY_SET_2026_05`).

### Deriving each view row (deterministic from the policy)
Using `allocation_mapping`:
- `view_score_thresholds`: `OW_min` (e.g. 0.35), `UW_max` (e.g. −0.35),
  neutral in between.
  - score >= OW_min → `OW`
  - score <= UW_max → `UW`
  - else → `N`
- `conviction` from `|score|`:
  - |score| >= `HIGH_abs_min` (0.7) → `HIGH`
  - |score| >= `MEDIUM_abs_min` (0.35) → `MEDIUM`
  - |score| < `LOW_abs_below` (0.35) → `LOW`
- `change` = compare new view vs prior view using `view_rank`
  (OW=+1, N=0, UW=−1):
  - new rank > prior rank → `UP`
  - new rank < prior rank → `DOWN`
  - equal → `UNCHANGED`
- `rationale_code`: copy directly from the macro-signal's `rationale_code`.
- `asset_class`: from the opportunity-sets taxonomy.

Row order = the request payload's `focus_opportunity_sets` order (NOT alphabetised).

### Risk overlay
- `overlay_code` / `primary_action`: choose the pairing that matches the
  dominant directional tilt of the views. Pairings:
  - `DURATION_QUALITY_TILT` ↔ `tilt_to_duration_quality` (duration OW + HY/credit risk).
  - `CREDIT_RISK_REDUCTION` ↔ `trim_credit_beta` (credit-spread / HY stress).
  - `EQUITY_BETA_EXTENSION` ↔ `add_cyclical_equity_beta` (broad equity OW).
  - `CURRENCY_DEFENSIVE_HEDGE` ↔ `add_currency_hedge` (defensive currency tilt).
  - `NO_OVERLAY` ↔ `hold_policy_weights` (no material tilt).
- `rationale_codes`: the 2–4 most material risk rationale codes from the view
  rows, in **business-priority order (highest priority first)** — typically
  duration/credit/China-dependence drivers ahead of growth/balance ones.

### Precision
- No numeric precision needed for views (all enums/strings). `policy_id`,
  `as_of_date`, `target_quarter`, `prior_quarter` echo the environment/payload.

---

## 6. Workflow D — Combined correlation + allocation committee JSON

Blends B and C: link non-US equity correlation findings to active allocation
views for a focused set of opportunity sets (e.g. Emerging Markets, India,
Latin America, USD).

### SOP
1. Compute correlations exactly as in Workflow B over the requested index set
   (often a 4-index subset, e.g. EM/China/India/LatAm).
2. `correlation_summary`: exactly 2 items in this order:
   - `pair_role: highest_concentration` = the highest-positive-correlation pair.
   - `pair_role: best_diversifier` = the lowest (most negative) correlation pair.
   - Each `pair` is 2 ids **sorted alphabetically**; `correlation` to 3 decimals.
3. `target_sleeve_actions`: one per requested opportunity set, in the
   request's order. Derive `action` from the resulting view:
   `UW`→`trim`, `OW`→`add`, neutral currency (e.g. USD→`N`)→`hedge` when the
   sleeve is a defensive currency. Actions from `{trim, add, hold, hedge, monitor, rotate}`.
4. `allocation_views`: one per requested opportunity set in request order.
   Each row carries **both** lineage and derived fields:
   - `prior_view` (from prior-views), `signal_score` (macro score, **3 decimals**),
     `view`, `change`, `conviction`, `rationale_code` (derived per Workflow C).
5. `rebalance_trigger`: choose the trigger that matches the dominant breach —
   `correlation_cap_breach` when a pair exceeds the correlation high threshold
   (0.8); `hy_cap_pressure`, `duration_drift`, `watchlist_concentration`, or
   `committee_review` otherwise.
6. `portfolio_risk_concentration_flag`: true when a material concentration/
   exception exists (e.g. correlation cap breach or two-or-more material
   exceptions).
7. `next_step`: choose by severity per the multi-asset risk policy
   (`committee_escalation_threshold` = "two_or_more_material_exceptions"):
   - single material exception, otherwise clean → `approve_with_monitoring`.
   - clean rotation ready → `approve_rotation`.
   - two+ material exceptions or unresolved breach → `defer_pending_risk_review`
     (or `reject_constraint_breach` for a hard constraint breach).

---

## 7. Common precision & ordering conventions (quick reference)

| Field | Precision | Ordering |
|---|---|---|
| `trade_package` `notional_usd_m` | 1 dec | asc by `instrument_id` |
| `rotation.trades` `quantity_usd_m` | 1 dec | SELL before BUY, then `instrument_id` asc |
| `post_trade_metrics` (MV, HY%, dur, YTM) | 2 dec | — |
| `risk_metrics` pct/duration | 2 dec | — |
| `post_trade_watchlist_exposure_usd_m` | 1 dec | — |
| correlations (all workflows) | 3 dec | pair ids alphabetical |
| `signal_score` | 3 dec | — |
| `index_set`, `diversification_candidates` | — | asc alphabetical |
| `sleeve_actions` | — | asc by `sleeve` |
| `allocation_views` (workflow C) | — | request payload `focus_opportunity_sets` order |
| `allocation_views` (workflow D) | — | request payload opportunity-set order |
| `watchlist_sell_ids` | — | asc `instrument_id` |
| `return_observations` | integer | — |

Round only at output. Carry full precision through intermediate steps.

---

## 8. Common misjudgments to avoid

- **Trusting the bond record's `watchlist` field.** It is often `None`. JOIN to
  `/api/issuers` and use the issuer `watchlist` boolean. Watchlist issuers seen
  include E&P, telecom, and refining names.
- **Buying a watchlist issuer for carry.** High-YTM candidates tagged
  `WATCHLIST_RISK` / `HIGH_CARRY` are traps — exclude them.
- **Using stale local quantity/marks.** `stale_holding_snapshot`,
  `stale_exception_board`, `stale_local_note` are deliberately stale; use
  environment holdings and mark `data_precedence` accordingly.
- **Duration-ineligible distractors.** A long-dated IG bond with duration > band
  upper bound (e.g. 6.7y) looks safe (IG, good ytm) but breaks the band; the
  portfolio *weighted* duration must stay in band, so avoid tickets that push it out.
- **Ignoring the HY cap.** Adding HY carry can breach `max_hy_allocation_pct`.
  Recompute HY% post-trade (sum HY MV / total MV).
- **Alphabetising allocation rows.** Workflow C/D rows keep the request payload's
  opportunity-set order, not alphabetical.
- **Pair id order.** Always sort the two index ids alphabetically inside a pair.
- **Correlation source.** Use monthly **simple returns** of consecutive levels,
  not levels themselves, not log returns unless told. return_observations =
  levels − 1.
- **Conviction vs view thresholds differ.** View uses signed thresholds
  (±0.35); conviction uses absolute thresholds (0.35 / 0.7). A score of 0.34 is
  `N` view but `LOW` conviction; 0.36 is `OW` view, `MEDIUM` conviction.
- **`change` is view-vs-prior, not score-vs-prior.** Compare the new view rank
  to the prior view rank (OW/N/UW), not the numeric score.
- **Forgetting `target_hy_reduction_pct`.** Risk-reduction portfolios carry a
  policy `target_hy_reduction_pct` (e.g. 4.0); meet or exceed it (in pct points)
  and set `target_hy_reduction_met`.
- **Output contract drift.** Always conform to the specific task's
  `answer_template.json` — schema, required keys, enum values, and ordering vary
  between BUY-only and rotation variants and between correlation variants.

---

## 9. Policy conventions (from `/api/policies`)

- `POL_CREDIT_DEFAULT`: HY cap (e.g. 20%), duration band [3.0, 5.0], issuer
  concentration limit (e.g. 12%), `subsector_min_count_for_diversified` 2,
  `target_hy_reduction_pct` 0.
- `POL_CREDIT_RISK_REDUCTION`: same but `target_hy_reduction_pct` 4.0 — used by
  risk-reduction rotation portfolios.
- `POL_CORRELATION_DEFAULT`: `correlation_high_threshold` 0.8,
  `correlation_low_threshold` 0.2, review window start/end dates.
- `POL_ALLOCATION_MAPPING`: view-score thresholds (OW>=0.35, UW<=−0.35, neutral
  between), conviction thresholds (HIGH>=0.7, MEDIUM>=0.35, LOW<0.35),
  `view_rank` (OW=1, N=0, UW=−1).
- `POL_MULTI_ASSET_DEFAULT` / `POL_MULTI_ASSET_RISK`: composition policies; the
  risk variant uses `committee_escalation_threshold = "two_or_more_material_exceptions"`.
- Top-level `policy_id` (e.g. `POLICY_SET_2026_05`) is the value to echo in
  allocation answers' `policy_id` field.

A pass/fail boolean is `true` iff the post-trade (or post-review) state satisfies
the corresponding policy threshold with the environment's authoritative data.

---

## 10. Final checks before submitting

1. Did I fetch every needed endpoint live (portfolio, bonds, issuers, market/energy
   or index-levels, macro-signals, prior-views, policies, opportunity-sets)?
2. Did I use environment values over stale local payloads, and set
   `data_precedence` when the schema asks?
3. Are all numeric fields rounded to the template-declared precision?
4. Are all lists ordered per the template (instrument_id asc; SELL-before-BUY;
   alphabetical index ids/pairs; request-payload order for allocation rows)?
5. Are all enum values from the template's allowed sets?
6. Does the JSON conform exactly to `answer_template.json` required keys and
   top-level shape? Return only the JSON object unless told otherwise.
