---
name: asteria-cio-credit-desk
description: >-
  Use this skill for any Asteria Investment Office CIO-desk or credit-desk task that returns a
  structured JSON answer built from the shared read-only HTTP API at http://127.0.0.1:8036.
  Triggers include: energy-credit BUY/trade packages for a portfolio, fixed-income risk-reduction
  rotations, equity index correlation reviews / diversification screens, quarterly active allocation
  view refreshes (UW/N/OW, conviction, change vs prior), multi-asset investment-committee decision
  files, and any prompt that references PF-* portfolios, IDX_* indices, BND_* bonds, ISS_* issuers,
  opportunity sets, macro signals, prior views, or POLICY_SET_2026_05 / POL_* policies. Apply it
  whenever the work involves Pearson correlations of index returns, MV-weighted credit metrics,
  HY caps / duration bands / watchlist rules, or mapping macro scores to allocation views.
---

# Asteria Investment Office — CIO / Credit Desk SOP

You produce JSON answers for the Asteria Investment Office against a read-only HTTP/JSON API
(base URL `http://127.0.0.1:8036`, all `GET`). The environment is the **current book of record**.
Local payloads in `input/payloads/` are *intake context* and are frequently stale (old marks,
quantities, dates, preferences). Always pull live data and prefer it over the payload; set any
`data_precedence`-style field to `current_environment_over_stale_payload` when they conflict.

This skill is reflection-hardened: the pitfalls below are the exact mistakes a careful first pass
makes. Read the pitfalls before answering, not after.

## 0. Universal setup (do this first, every task)

1. `GET /api/policies` → read `as_of_date` (use it verbatim for every `as_of_date` field; do **not**
   use the payload's `memo_as_of_date` / `committee_date` / `stale_local_note.as_of_date`), plus all
   thresholds (correlation high/low, HY cap, duration band, view/conviction thresholds, view_rank).
2. `GET /api/catalog` to confirm available ids if anything is ambiguous.
3. Read the answer_template.json carefully: it dictates **key order is irrelevant but list ORDER,
   list LENGTH, enum spelling, and numeric PRECISION are graded**. Round every numeric to the exact
   declared precision (e.g. precision 2 → `13.24`; precision 3 → `0.974`; precision 1 → `4.0`).
   Keep trailing-zero-free numbers as JSON numbers (e.g. `5.8`, not `"5.80"`).
4. Respect every `ordering` instruction literally (alphabetical by id, SELL-before-BUY, payload
   focus order, fixed item_order list, etc.).

## 1. Endpoints

`/api/catalog`, `/api/policies`, `/api/portfolios`, `/api/portfolios/<id>`,
`/api/instruments/bonds`, `/api/issuers`, `/api/market/energy`, `/api/indices`,
`/api/index-levels`, `/api/index-levels/<index_id>`, `/api/allocation/opportunity-sets`,
`/api/allocation/prior-views`, `/api/macro-signals`. Most list endpoints accept equality filters
(`?rating_bucket=HY`, `?candidate=true`, `?quarter=Q2_2026`, ...).

## 2. Correlation math (correlation reviews & committee files)

- Window comes from the payload `review_window` (and matches `policies.correlation` window).
- For each index, `GET /api/index-levels/<index_id>`, keep level rows with
  `level_start_date <= date <= level_end_date`, sort by date.
- **Returns = monthly simple returns** `r_t = L_t / L_{t-1} - 1`. With 12 monthly levels you get
  **11 return observations** (`return_observations` = #levels − 1).
- Correlation = **Pearson** on those simple-return vectors, rounded to **3 decimals**.
- Every `pair_id` / `pair` lists the two index ids in **ascending alphabetical order**.
- `highest_positive` / `highest_concentration` = the max correlation pair; `lowest` /
  `best_diversifier` = the min (most negative) correlation pair.
- `high_threshold_breached` is true if any pair ≥ `correlation_high_threshold` (0.8).

### Pitfall 2a — `diversification_candidates` is NOT just "all correlations below the low threshold"

A first pass that selects only indices whose every distinct correlation to the held sleeves is
below the low threshold (0.2) **under-selects**. The corrected rule: from the template's allowed
candidate set, include an index if it materially relieves the *flagged* concentration, by either
route:

- **(a) Genuine low-correlation diversifier** — broadly negative / sub-low-threshold correlations
  to the held cluster (this is the obvious one, e.g. a Latin America sleeve).
- **(b) Structural de-concentrator tied to the named concern code, not already held** — an index
  whose construction directly removes the flagged exposure (e.g. an "EM ex China" sleeve directly
  cuts China beta when the concern is China/Asia dependence), even though its *overall* correlation
  to the cluster is still high.

Exclude a candidate that is **already a held sleeve and highly correlated** to the concentration
cluster — it adds no incremental diversification (e.g. an India sleeve already in the book and
~+0.8 to China/Asia is not a diversifier). Net: the answer can legitimately contain a high-beta
"ex-the-risk" sleeve alongside the obvious negative-correlation sleeve.

### Pitfall 2b — `primary_code` follows the memo's stated concern, not the single top pair

Pick the concentration `primary_code` that matches the CIO concern memo / concern_codes (e.g.
`CHINA_ASIA_DEPENDENCE` when the memo flags a dedicated China sleeve + Asia beta overlap), even if
the single highest-correlation pair happens to be a global-beta pair. The memo defines the lens.

### Sleeve actions (correlation review)

`sleeve_actions` map the concentration finding to trades, not the allocation views: **trim** the
concentrated/overlapping sleeve, **add** the diversifier. Order ascending by the `sleeve` field
(sleeve display name).

## 3. Allocation views (quarterly refresh & committee files)

Inputs: `GET /api/macro-signals` (filter `quarter=<target_quarter>`),
`GET /api/allocation/prior-views`, `GET /api/allocation/opportunity-sets`, `GET /api/policies`
(`allocation_mapping`).

**Per requested opportunity_set:**
- `signal_score` = the macro-signal `score` for that opportunity_set in the target quarter, at the
  declared precision (precision 3 → report `-0.373`, `0.48`, etc.).
- `rationale_code` = the macro-signal `rationale_code` for that opportunity_set (use it verbatim).
- `asset_class` = from `/api/allocation/opportunity-sets`.
- **New `view` from score** via `view_score_thresholds`: `score ≥ 0.35` → `OW`; `score ≤ -0.35`
  → `UW`; strictly between → `N`.
- **`conviction` from |score|** via `conviction_thresholds`: `|score| ≥ 0.7` → `HIGH`;
  `0.35 ≤ |score| < 0.7` → `MEDIUM`; `|score| < 0.35` → `LOW`.
- **`prior_view`** = the prior-views record whose `quarter == target_quarter` (equivalently
  `previous_quarter == prior_quarter`). That record is the view *carried into* the target quarter,
  i.e. the prior-quarter stance. (Confirmed correct: do not instead read the record whose
  `quarter == prior_quarter`.)
- **`change`** = sign of `view_rank(new) − view_rank(prior)` using `view_rank` (UW=−1, N=0, OW=1):
  positive → `UP`, negative → `DOWN`, zero → `UNCHANGED`.
- Ignore stale payload notes about old stances (e.g. "kept USD overweight"); recompute from live
  scores + prior-views.

Order allocation rows by the payload's `focus_opportunity_sets` / template `item_order`.

### Pitfall 3a — lineage `policy_id` is the umbrella policy set, not the mechanism sub-policy

For a lineage / "which policy governs this" field, use the **top-level policy set id**
(`policies.policy_id`, e.g. `POLICY_SET_2026_05`), **not** the narrow sub-policy that happens to
describe the mapping mechanics (`POL_ALLOCATION_MAPPING`) and not `POL_MULTI_ASSET_DEFAULT`. The
sub-policies are the calculators; the lineage field wants the governing policy set in effect. When
unsure which level a `policy_id` field wants, prefer the umbrella set for *lineage/provenance*
fields and the specific sub-policy only when the field is explicitly about a constraint calculation
the portfolio runs under (e.g. a portfolio's own `constraints.policy_id`).

### Pitfall 3b — `risk_overlay.rationale_codes` = the views that JUSTIFY the overlay direction

Do not just dump the top-N views by |score|, and do not invent supporting macro themes that are
not the `rationale_code` of any requested view (e.g. don't add `RATE_CUT_SUPPORT` when it isn't a
rationale code on any of the requested opportunity sets). For a defensive **duration/quality tilt**
(`DURATION_QUALITY_TILT` / `tilt_to_duration_quality`), the rationale codes are exactly the
*risk-reducing* theses, ordered by business priority:
1. the duration-support thesis (the OW-duration view → e.g. `DURATION_SUPPORT`),
2. the credit-caution thesis (the UW-HY view → e.g. `HY_VALUATION_RISK`),
3. the dominant equity-risk thesis being de-risked (the UW-EM view → e.g. `CHINA_DEPENDENCE`).
Pro-cyclical / risk-ON OW theses (e.g. `INDIA_OFFSET`, `LATAM_DIVERSIFIER`, `EUROPE_RECOVERY`) do
**not** belong in a de-risking overlay's rationale even when their |score| is large. Choose the
`overlay_code` / `primary_action` from the same logic: strong duration support + HY caution ⇒
duration/quality tilt.

### Pitfall 3c — committee `target_sleeve_actions` follow the VIEW stance, not the `change`

Map the **new view**, not the change flag, to the action: `OW → add`, `UW → trim`, `N → hold`.
An OW view whose `change` is `UNCHANGED` is still **add**, not hold (a common slip: treating
"unchanged" as "hold"). **Currency special case:** a currency-overlay opportunity set (e.g. USD)
that lands at `N` after dropping from a defensive overweight maps to **hedge** (you actively manage
the currency exposure), not `hold`. Use the action enum the template allows
(`trim/add/hold/hedge/monitor/rotate`).

## 4. Credit metrics & bond selection (energy packages and FI rotations)

Data: `GET /api/portfolios/<id>` (holdings, `market_value_usd_m`, `constraints`),
`GET /api/instruments/bonds` (universe; fields `rating_bucket` IG/HY, `modified_duration_years`,
`yield_to_maturity_pct`, `candidate`, `energy_linked`, `subsector`, `issuer_id`,
`recommended_theme_tags`), `GET /api/issuers` (`watchlist` flag per `issuer_id`).

**Formulas (all MV-weighted on notional in USD-millions):**
- `total_market_value` = sum of all post-trade notionals.
- `hy_allocation_pct` = (sum of HY notional) / total MV × 100. Note this is invariant to *which*
  IG bonds you buy when total MV is held constant — so HY% alone does not pin the trade list.
- `weighted_modified_duration_years` = Σ(notional × modified_duration_years) / total MV.
- `weighted_yield_to_maturity_pct` = Σ(notional × yield_to_maturity_pct) / total MV.
- `hy_reduction_pct_points` = pre-trade HY% − post-trade HY%.

**Constraints (from `policies`/portfolio `constraints`):** HY ≤ `max_hy_allocation_pct` (20%);
duration within `duration_band_years` ([3,5]) **post-trade**; issuer concentration ≤ 12%;
"diversified" needs ≥ `subsector_min_count_for_diversified` (2) distinct subsectors; never BUY a
watchlist-issuer bond. For a two-pick package, "issuer diversification" and "subsector
diversification" mean the two picks differ from **each other** in issuer and subsector.

**Eligibility filters:**
- Energy package: `candidate == true` AND `energy_linked == true` AND issuer **not** on watchlist.
- FI rotation buys: current `candidate == true`, correct rating bucket (IG for de-risking), issuer
  **not** on watchlist.
- Resolve watchlist via the bond's `issuer_id` → `/api/issuers[...].watchlist`.

### Energy-credit package SOP

Split the stated total notional evenly across the exact number of tickets requested (e.g. 8.0M over
2 BUYs → 4.0 each). Choose eligible bonds that **improve carry** (higher YTM) while keeping all
post-trade constraints satisfied, are **diversified** (different issuer AND different subsector —
two LNG/Natural-Gas names fail subsector diversification even if both look thematic), and suit a
**client income pitch**. For sales positioning, anchor `theme` to the strongest *relevant* energy
signal in `/api/market/energy` and the bond's `recommended_theme_tags` (e.g. LNG flagship →
`lng_export_tailwind`); set `target_segment` to the income-oriented client segment implied by the
desk context. Sort `trade_package` ascending by `instrument_id`.

### Pitfall 4a — fund a rotation across ALL eligible shortlist candidates, not a minimal subset

When a desk memo gives a `candidate_shortlist`, **buy every eligible (non-watchlist, correct-bucket)
candidate on it**, distributing the buy notional across all of them — do not collapse to the two
"best" names. Excluding only the watchlist candidate and spreading the remainder across the rest is
the intended rebalance style ("fund current eligible candidates"). This changes both the buy list
and `weighted_modified_duration_years`, so it is graded. (HY% and hy_reduction are unaffected, which
is why a minimal-subset pass can look "passing" yet still be wrong.)

### FI risk-reduction rotation SOP

1. Pre-trade: compute HY%, duration, watchlist exposure from live holdings.
2. **Sell pressure points:** always sell the watchlist HY name(s) in full (record them in
   `watchlist_sell_ids`, ascending), and sell enough additional HY (start with the lowest-carry HY)
   to clear the HY cap and meet `target_hy_reduction_pct`. Keep total notional constant unless told
   otherwise (sell N, buy N).
3. **Buy** the eligible IG shortlist candidates per Pitfall 4a, distributing the funded notional;
   keep post-trade duration inside the band (use a longer-duration IG name as ballast if needed).
4. `exception_flags`: hy_cap_pass, duration_band_pass, target_hy_reduction_met,
   watchlist_exposure_cleared — all should be true in a good rotation; `buys_avoid_watchlist` true.
5. Order trades **SELL before BUY, then instrument_id ascending** within each action.

### Pitfall 4b — `risk_note_code` / `rebalance_trigger`: pick the most specific remediated risk

When several risk codes are simultaneously true pre-trade (e.g. both HY-cap breach and watchlist
exposure), choose the **most specific, distinctive risk the rotation is built to remediate**, not
the largest-magnitude generic one. A rotation whose headline action is selling a watchlist issuer
to remove "avoidable watchlist risk" should code `watchlist_concentration` rather than the generic
`hy_cap_pressure`. Likewise prefer a concrete structural trigger (e.g. `correlation_cap_breach`
when a correlation exceeds the high threshold) over a procedural one like `committee_review`, even
when the packet is literally a committee request. General rule: match the code to the *specific
condition being fixed*, favoring the named/avoidable structural risk over a broad magnitude label.

## 5. Decision / status fields

For `next_step`-style enums on an actionable but still-watch-worthy proposal (a clean rotation that
nonetheless leaves a live concentration breach to monitor), prefer `approve_with_monitoring` over
either a blanket `approve_rotation` or a `defer_pending_risk_review`. Set boolean concentration
flags (e.g. `portfolio_risk_concentration_flag`) true whenever a correlation crosses the high
threshold.

## 6. Output discipline checklist (run before returning)

- [ ] `as_of_date` = environment `as_of_date`, not any payload date.
- [ ] Every numeric rounded to the template's declared precision; numbers are JSON numbers.
- [ ] Every list in the required order and exact required length.
- [ ] Every enum value spelled exactly as in `allowed_values`.
- [ ] `policy_id` lineage = umbrella `POLICY_SET_2026_05` unless the field is a portfolio
      constraint reference.
- [ ] Correlations: simple returns, Pearson, 3 dp, pairs alphabetical, obs = levels − 1.
- [ ] View ← score thresholds; conviction ← |score|; change ← rank vs `quarter==target` prior view.
- [ ] Diversification candidates include structural de-concentrators, not only sub-0.2 names.
- [ ] Sleeve/target actions follow the VIEW (OW→add, UW→trim, N→hold; currency N→hedge).
- [ ] Rotation buys span all eligible shortlist candidates; trades SELL-before-BUY then id-asc.
- [ ] Risk/trigger code = the most specific remediated risk.
- [ ] Output is ONLY the JSON object (no prose), matching the template's required keys.
