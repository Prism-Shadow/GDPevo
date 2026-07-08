# Asteria Investment Office — Portfolio-Risk Task Skill

Operating SOP for solving Asteria portfolio-risk evaluation tasks. The test
solver receives only a task `input/` (prompt + payloads/answer_template.json +
a request payload) plus this skill and the remote environment. Three workflow
families appear; a task may involve one or combine two.

Base URL: `<remote-env-url>` (GET only). Use `curl` or `python3`+`urllib`.

---

## 0. Golden rules (apply to every task)

1. **Environment = book of record.** Every `input/payloads/*.json` is *intake
   context* and may be stale (old marks, old quantities, old desk notes).
   Always reconcile to the environment. When a local payload conflicts with the
   environment, prefer the environment. The `data_precedence` answer field is
   `current_environment_over_stale_payload` whenever any conflict exists (e.g.
   stale snapshot MV/quantity differs from `/api/portfolios/<id>`).
2. **`as_of_date`** in your answer = the environment's current as-of date. Read
   it from `/api/portfolios/<id>` (`as_of_date`) or `/api/policies`
   (`as_of_date`). Do **not** copy a date stamped on a local request payload or
   a stale worksheet unless the prompt explicitly overrides.
3. **No precomputed correlations.** The environment stores index *levels*, never
   correlations. Compute Pearson correlations yourself from monthly simple
   returns (see Workflow B).
4. **Precision follows each field in `answer_template.json`.** Round the final
   value to the declared decimals. JSON numerics like `5.8` and `5.80` are equal,
   but always round to the specified precision (2/3/1 decimals) before emitting.
5. **Read the answer template first.** It declares required keys, enums,
   ordering, and precision per field. Conform exactly: missing keys, wrong
   enum values, wrong sort order, or wrong precision all fail.
6. **Output is a single JSON object** matching the template — no narrative
   outside JSON unless the prompt asks for it.

---

## 1. Environment endpoints (what each is for)

| Endpoint | Use |
|---|---|
| `GET /api/policies` | All constraint/threshold/mapping policies + `as_of_date`. |
| `GET /api/portfolios` | List of portfolio summaries. |
| `GET /api/portfolios/<id>` | Objective, constraints, **current holdings** (instrument_id, quantity_usd_m, sleeve), MV, as_of. |
| `GET /api/instruments/bonds` | Bond universe. Filters: `?candidate=true`, `?rating_bucket=HY`. Fields: instrument_id, issuer_id, rating_bucket(IG/HY), rating, modified_duration_years, yield_to_maturity_pct, coupon_pct, spread_bps, sector, subsector, energy_linked, candidate, recommended_theme_tags. |
| `GET /api/issuers` | issuer_id, sector, subsector, rating_bucket, **watchlist(bool)**, credit_outlook, research_tags. |
| `GET /api/market/energy` | Oil/gas/LNG/refining/renewables signal scores + pitch_themes. |
| `GET /api/indices` | Index metadata (region, level window). |
| `GET /api/index-levels` | All monthly index levels: dict index_id -> [{date, level}]. |
| `GET /api/index-levels/<index_id>` | One index's monthly levels. |
| `GET /api/allocation/opportunity-sets` | Cross-asset taxonomy: opportunity_set -> asset_class (Equities/Duration/Credit/Currency). |
| `GET /api/allocation/prior-views` | Prior-quarter active views (see Workflow C). |
| `GET /api/macro-signals` | Current signal scores + rationale_code per opportunity_set/quarter. |

`GET /api/catalog` may return empty; ignore it and use the typed endpoints above.

**Reuse fetches.** `/api/instruments/bonds`, `/api/issuers`, `/api/index-levels`,
`/api/allocation/prior-views`, `/api/macro-signals` are small and shared across
tasks — fetch once, cache to `/tmp/*.json`, reuse.

---

## 2. Policy reference (`/api/policies`)

- `credit_default` (POL_CREDIT_DEFAULT): `max_hy_allocation_pct`=20.0,
  `duration_band_years`=[3.0, 5.0], `issuer_concentration_limit_pct`=12.0,
  `subsector_min_count_for_diversified`=2, `target_hy_reduction_pct`=0.0.
- `credit_risk_reduction` (POL_CREDIT_RISK_REDUCTION): same as above but
  `target_hy_reduction_pct`=4.0 (used by risk-reduction rotations).
- `correlation` (POL_CORRELATION_DEFAULT):
  `correlation_high_threshold`=0.8, `correlation_low_threshold`=0.2,
  review window (e.g. 2025-05-30 → 2026-04-30).
- `allocation_mapping` (POL_ALLOCATION_MAPPING):
  - `view_score_thresholds`: OW if score ≥ 0.35; UW if score ≤ -0.35; N in (-0.35, 0.35).
  - `conviction_thresholds`: HIGH if |score| ≥ 0.70; MEDIUM if |score| ≥ 0.35; LOW if |score| < 0.35.
  - `view_rank`: OW=1, N=0, UW=-1 (for computing change vs prior).
- `multi_asset` (POL_MULTI_ASSET_DEFAULT): uses allocation_mapping +
  correlation_default + credit_default. Used by multi-asset sleeves.
- `multi_asset_risk` (POL_MULTI_ASSET_RISK): uses correlation_default +
  credit_risk_reduction; `committee_escalation_threshold`=
  "two_or_more_material_exceptions" → next_step logic in Workflow C.

The portfolio's `constraints.policy_id` tells you which policy set governs it.

---

## 3. Workflow A — Energy / fixed-income credit trade strategy

Tasks: build a BUY package (income sleeve) **or** a SELL+BUY rotation
(risk-reduction). Answer fields: trade_package/rotation.trades,
post_trade_metrics / risk_metrics, constraint_checks / exception_flags,
sales_positioning or watchlist_handling, risk_note_code, data_precedence.

### 3.1 Gather state
1. `GET /api/portfolios/<id>` → holdings (instrument_id, quantity_usd_m),
   MV, constraints.policy_id.
2. `GET /api/instruments/bonds` → bond metrics (rating_bucket, modified_duration,
   YTM, spread, energy_linked, subsector, issuer_id).
3. `GET /api/issuers` → cross-reference **watchlist** flag per issuer_id and
   subsector/sector/rating.
4. `GET /api/market/energy` → signal scores + pitch_themes (energy tasks).

### 3.2 Pre-trade metrics (market-value-weighted)
Using `quantity_usd_m` as the market-value weight:
- `HY allocation %` = Σ(HY quantity) / Σ(all quantity) × 100.
- `weighted modified duration` = Σ(qty × modified_duration_years) / Σ(qty).
- `weighted YTM` = Σ(qty × yield_to_maturity_pct) / Σ(qty).

Same weighting applies post-trade after applying buys/sells (post MV = pre MV
+ buys − sells; for a "new sleeve allocation" MV grows by the buy notional; for
a "fund from proceeds" rotation MV stays ~constant, i.e. Σbuys = Σsells).

### 3.3 Eligibility & exclusion rules (critical)
- **Watchlist avoidance**: never BUY a bond whose issuer `watchlist` is true.
  Cross-check the issuer_id from `/api/issuers`. Watchlist flags are on the
  *issuer*, not the bond — a non-watchlist-looking bond whose issuer is
  watchlisted is still forbidden.
- **Duration-ineligible distractors**: bonds with `modified_duration_years`
  outside [3.0, 5.0] are ineligible as BUY candidates (the duration band is
  enforced on both the portfolio and effectively on eligible candidates; long
  2033/2034 paper at dur 5.4–6.7 and short paper at dur 2.3–2.9 are
  distractors). Always prefer candidates with duration inside the band.
- **HY cap**: post-trade HY % must be ≤ 20.0 (`hy_cap_pass`). If the book is
  already over cap, the rotation must sell enough HY to get under.
- **Duration band**: post-trade weighted modified duration must be in [3.0, 5.0]
  (`duration_band_pass`). For rotations, keep duration roughly flat ("without
  creating a duration shortfall").
- **Diversification** (`selected_*_diversification_pass`): the *selected* BUY
  package must span ≥2 distinct issuers AND ≥2 distinct subsectors
  (`subsector_min_count_for_diversified`=2). This is a check on the **selected
  trades**, not the whole book. Do not pair two bonds from the same issuer or
  same subsector.
- Avoid doubling up on already-overweight issuers where it would push a single
  issuer over 12% concentration, but the hard "selected" check is the 2-buy
  diversification rule above.

### 3.4 Selection SOP — income BUY package (2 tickets, even split)
1. Compute the package notional from the desk request (e.g. 8.0m total → 4.0
   each, 1-decimal precision).
2. Among `candidate=true` bonds that are `energy_linked=true` (for energy
   sleeves), non-watchlist, duration-in-band, pick an **anchor** matching the
   desk's top preference and the strongest `/api/market/energy` signal. The LNG
   export signal is typically strongest; an IG LNG exporter bond (IG, dur ~4,
   themes LNG_EXPORTS/GAS_DEMAND) is the usual anchor.
3. Pick the **second** bond from a *different issuer and different subsector*,
   also energy-linked, non-watchlist, duration-in-band, that improves carry
   (YTM above the pre-trade weighted YTM). If HY budget allows (post HY ≤ 20%),
   a non-watchlist HY carry bond maximizes carry improvement; choose the
   highest-YTM eligible HY diversifier. Renewables / merchant-power HY are
   typical carry diversifiers.
4. Verify all five constraint_checks; compute post_trade_metrics (2 decimals);
   `notional_usd_m` to 1 decimal; sort `trade_package` ascending by
   instrument_id.
5. `sales_positioning.target_segment`: take from the request's client_context
   (e.g. "multi-asset income" → `multi_asset_income`).
6. `sales_positioning.theme`: pick the enum matching the dominant
   `pitch_themes`/signal (LNG-led → `lng_export_tailwind`; renewables+LNG →
   `transition_bond_selectivity`; avoiding watchlist HY carry →
   `avoid_watchlist_yield_trap`; midstream → `midstream_stability`).
7. `data_precedence`: `current_environment_over_stale_payload` if the stale
   snapshot/MV/quantity differs from the environment, else `no_conflict_found`.

### 3.5 Selection SOP — risk-reduction rotation (SELL+BUY)
1. Identify **pressure points** to sell: watchlist holdings (issuer
   `watchlist`=true) first, then HY holdings, prioritizing the lowest-carry HY
   for sale while keeping the highest-carry non-watchlist HY to preserve carry.
2. Sell enough HY to (a) clear watchlist exposure to 0 and (b) get post-trade
   HY % ≤ 20 (and meet the `target_hy_reduction_pct` ≥ 4 pp where the policy is
   POL_CREDIT_RISK_REDUCTION — getting under the 20% cap always satisfies 4 pp).
3. Buy IG `candidate=true` bonds from the candidate shortlist that are
   non-watchlist, duration-in-band. Fund the buys with the sell proceeds
   (Σbuys = Σsells, MV constant). Pick the highest-YTM IG candidates across
   different sectors for carry + diversification.
4. Trivially **never** buy a watchlist HY candidate even if it appears on the
   desk's shortlist with a "high carry" comment (`buys_avoid_watchlist`=true).
5. Sort `rotation.trades` **SELL before BUY**, then instrument_id ascending
   within each action. `quantity_usd_m` to 1 decimal.
6. `risk_metrics`: `post_trade_hy_allocation_pct` (2), `post_trade_duration_years`
   (2), `hy_reduction_pct_points` (2) = pre_HY% − post_HY%,
   `post_trade_watchlist_exposure_usd_m` (1).
7. `watchlist_handling.watchlist_sell_ids`: all sold watchlist instrument_ids,
   ascending.
8. `risk_note_code`: the dominant theme — `watchlist_concentration` if a
   watchlist name was the acute risk removed; `hy_cap_pressure` if the HY-over-
   cap was the driver; `duration_preservation` if keeping duration in-band was
   the binding constraint; `carry_tradeoff` if high-carry HY was sacrificed for
   IG quality. `no_action` only if no trades.

---

## 4. Workflow B — International equity correlation review

Tasks: pair correlations across an index universe from monthly levels;
highest/lowest pairs; China/Asia dependence concentration; diversification
candidate set; sleeve actions.

### 4.1 Compute correlations (yourself)
1. `GET /api/index-levels` → levels per index. Use the window from the request's
   `review_window` (level_start_date, level_end_date) — which equals the policy
   `correlation.review_window_start/end` and the index metadata window.
2. For each index, take levels with `start_date <= date <= end_date`, sorted by
   date. **Monthly simple return** r_t = (level_t − level_{t-1}) / level_{t-1}.
3. `return_observations` = number of returns = (number of levels in window) − 1
   (12 monthly levels → 11 returns).
4. **Pearson correlation** between two return series:
   r = Σ((xᵢ−x̄)(yᵢ−ȳ)) / sqrt(Σ(xᵢ−x̄)² · Σ(yᵢ−ȳ)²).
5. Round correlations to **3 decimals**.
6. `pair_id` / `pair` = the two index ids in **ascending alphabetical order**.

### 4.2 Extreme pairs
- `highest_positive` = the pair with the maximum correlation.
- `lowest` = the pair with the **minimum** correlation (most negative).
Both report `pair_id` (sorted) and `correlation` (3 decimals).

### 4.3 Concentration flags
- `china_asia_dependence_flag` = true when the China index and the Asia-Pacific-
  ex-Japan index (and/or EM) are correlated above the high threshold (0.8),
  i.e. the dedicated China + Asia sleeves carry overlapping beta.
- `high_threshold_breached` = true when the relevant concentration pair crosses
  `correlation_high_threshold` (0.8).
- `primary_code`: `CHINA_ASIA_DEPENDENCE` if the China/Asia/EM overlap is the
  dominant concentration (matches the CIO concern codes
  ASIA_BETA_OVERLAP / CHINA_DEDICATED_SLEEVE); `GLOBAL_DEVELOPED_OVERLAP` if the
  dominant high correlations are developed-world (EAFE/WORLD/ACWI); 
  `NO_MATERIAL_CONCENTRATION` if nothing breaches.

### 4.4 Diversification candidates & sleeve actions
- `diversification_candidates`: the ex-China EM diversifier pool (e.g.
  IDX_EM_EX_CHINA, IDX_INDIA, IDX_LATAM), ascending alphabetical — the sleeves
  the committee evaluates for diversification. (The genuinely low/negatively-
  correlated one — typically LatAm vs China — is the one to *add*.)
- `sleeve_actions` (length per template, ordered ascending by `sleeve` name):
  trim the concentrated sleeve (the high-beta China/Asia sleeve → action
  `trim`, target that index) and add the low-correlation diversifier sleeve
  (→ action `add`, target the diversifying index). Use `monitor`/`hold`/`rotate`
  sparingly only when no size change is warranted. `target_index_id` must be
  from the template's allowed set.

---

## 5. Workflow C — Cross-asset active allocation view updates

Tasks: produce per-opportunity-set active views (view, change, conviction,
rationale_code) from prior views + macro signals; choose a risk overlay;
and (combined variant) link correlations to sleeve actions + rebalance trigger
+ next step.

### 5.1 Source the inputs
- **Prior (prior-quarter) views**: `GET /api/allocation/prior-views`. Each
  record has `quarter`, `previous_quarter`, `opportunity_set`, `view`, `conviction`.
  For a target quarter Q with prior quarter P, the **prior view** = the record
  where `quarter`=Q and `previous_quarter`=P. (Its `view`/`conviction` fields
  ARE the prior-quarter view you compare against — do not treat them as the new
  view.) The new view is derived from signals below.
- **Current signals**: `GET /api/macro-signals`, filter `quarter`=Q. Each gives
  `score` (signal_score) and `rationale_code`.
- **Mapping policy**: `POL_ALLOCATION_MAPPING` (§2).
- **Asset class**: from `/api/allocation/opportunity-sets` (opportunity_set →
  asset_class: Equities / Duration / Credit / Currency).

### 5.2 Derive each allocation row
For each opportunity_set in the request's focus list (in that order):
1. `asset_class` from the opportunity-sets taxonomy.
2. `signal_score` = macro-signal score, **3 decimals**.
3. `view` (new) from score via mapping: OW if ≥0.35, UW if ≤−0.35, else N.
4. `conviction` from |score|: HIGH ≥0.70, MEDIUM ≥0.35, LOW <0.35.
5. `rationale_code` = macro-signal `rationale_code` (must be one of the enum).
6. `prior_view` (combined-variant template) = the prior-views record's `view`.
7. `change` = compare new view rank vs prior view rank (OW=1,N=0,UW=−1):
   `UP` if new>prior, `DOWN` if new<prior, `UNCHANGED` if equal.
8. Order rows exactly as the request's focus_opportunity_sets list (or the
   template's `item_order`).

### 5.3 Choose the risk overlay
Pick the single overlay that captures the dominant cross-asset rotation:
- If credit (Corporate High Yield) is UW and/or duration (U.S. Treasuries) is OW
  → rotate credit→duration: `DURATION_QUALITY_TILT` / `tilt_to_duration_quality`.
- If HY UW is the single clearest risk with no duration bid →
  `CREDIT_RISK_REDUCTION` / `trim_credit_beta`.
- If cyclical equities (Europe/LatAm) are the leading OWs with no defensive
  rotation → `EQUITY_BETA_EXTENSION` / `add_cyclical_equity_beta`.
- If USD/defensive currency view is the headline →
  `CURRENCY_DEFENSIVE_HEDGE` / `add_currency_hedge`.
- Only `NO_OVERLAY` / `hold_policy_weights` when no view departs materially from
  neutral.
`rationale_codes`: the 1–3 enum codes driving the overlay, **business priority
order** (largest |signal| / most material risk first). For a duration-quality
tilt use the duration-support and credit-risk codes; for credit-risk reduction
use the negative credit/equity-risk codes ordered by severity.

`policy_id` (where the template requires it) = `POL_ALLOCATION_MAPPING`.

### 5.4 Combined correlation + allocation variant (multi-asset committee JSON)
This variant (e.g. PF-MA-HELIO) asks for both a `correlation_summary` and
`allocation_views` plus `target_sleeve_actions`, `rebalance_trigger`,
`portfolio_risk_concentration_flag`, `next_step`.
1. `correlation_summary` (length 2, order `[highest_concentration,
   best_diversifier]`): from the named index subset, the highest-correlation
   pair = concentration risk; the most-negative pair = best diversifier. Pair
   ids sorted alphabetically; correlation 3 decimals; compute as in §4.
2. `allocation_views`: as §5.2 for the named opportunity sets (typically
   Emerging Markets, India, Latin America, USD), in the template's `item_order`.
3. `target_sleeve_actions`: one per opportunity set in `item_order`. Map the
   view+correlation to an action: trim sleeves whose index is in the
   high-concentration pair and whose view is UW; `add` sleeves that are the
   low-correlation diversifier / OW offset; `hold` for sleeves whose view moved
   to neutral (revert to policy weights); `monitor`/`hedge` only when clearly
   warranted.
4. `rebalance_trigger`: `correlation_cap_breach` if a pair exceeds the 0.8 high
   threshold (the usual trigger for these reviews); else `hy_cap_pressure` /
   `duration_drift` / `watchlist_concentration` if a credit exception dominates;
   `committee_review` as the catch-all.
5. `portfolio_risk_concentration_flag`: true if any concentration pair breaches
   the high threshold (0.8).
6. `next_step`: count material exceptions (correlation breach + any credit
   exception). Under `POL_MULTI_ASSET_RISK`, two-or-more →
   `defer_pending_risk_review`; one addressable exception →
   `approve_with_monitoring`; clean rotation that resolves the breach →
   `approve_rotation`; unresolvable breach → `reject_constraint_breach`.
   Under `POL_MULTI_ASSET_DEFAULT` a single correlation breach that the
   rotation addresses typically → `approve_with_monitoring`.

---

## 6. Precision & ordering conventions (all workflows)

| Field | Precision | Notes |
|---|---|---|
| `notional_usd_m`, `quantity_usd_m` | 1 decimal | USD millions. |
| `total_market_value_usd_m` | 2 decimals | |
| `hy_allocation_pct`, `weighted_modified_duration_years`, `weighted_yield_to_maturity_pct` | 2 decimals | market-value-weighted. |
| `post_trade_hy_allocation_pct`, `post_trade_duration_years`, `hy_reduction_pct_points` | 2 decimals | |
| `post_trade_watchlist_exposure_usd_m` | 1 decimal | |
| correlation values | 3 decimals | Pearson of monthly simple returns. |
| `signal_score` | 3 decimals | from macro-signals. |
| `return_observations` | integer | = levels_in_window − 1. |
| booleans | true/false | lower-case JSON. |

**Ordering rules (strict):**
- `trade_package`: ascending by `instrument_id`.
- `rotation.trades`: SELL before BUY, then `instrument_id` ascending within each action.
- `index_set`, `diversification_candidates`, `pair`/`pair_id`: ascending alphabetical by index id.
- `sleeve_actions`: ascending by `sleeve`.
- `allocation_views`/`target_sleeve_actions`: the request's focus_opportunity_sets order (or template `item_order`).
- `watchlist_sell_ids`: ascending instrument_id.
- `rationale_codes`: business priority, highest priority first.

---

## 7. Common pitfalls & exclusion rules

- **Stale worksheet trap**: a desk payload may state MV, HY%, duration, or
  holding quantities that differ from the environment. Always recompute from
  `/api/portfolios/<id>` holdings + `/api/instruments/bonds`. Set
  `data_precedence` = `current_environment_over_stale_payload`.
- **Watchlist is on the issuer, not the bond**: a bond's `rating`/`sector` can
  look fine while its `issuer_id` is `watchlist=true`. Always join to
  `/api/issuers`. Watchlist HY "high carry" candidates on a desk shortlist are
  deliberate traps — never buy them.
- **Duration-ineligible distractors**: long-dated 2032–2034 paper (dur 5.4–6.7)
  and very short 2028 paper (dur 2.3–2.9) sit outside [3,5]; exclude as buys.
- **HY cap math**: HY % is of post-trade MV (after buys/sells), not pre-trade.
  For a rotation that keeps MV constant, the denominator is unchanged; for a
  new-sleeve BUY package, MV grows by the buy notional.
- **Diversification is on the selected package**: do not reject a pair just
  because the broader book is concentrated; the `selected_*_diversification_pass`
  checks the 2 chosen buys span ≥2 issuers and ≥2 subsectors.
- **Correlations are not stored**: never look for a "correlation" field in the
  environment; compute from `index-levels`. Use simple (not log) returns.
- **Prior view vs new view**: in `/api/allocation/prior-views`, the record
  `quarter=Q, previous_quarter=P` holds the **prior (P)** view for a Q target.
  The new Q view comes from Q's `macro-signals` + the mapping policy. Getting
  this backwards inverts every `change`.
- **Conviction uses |score|**: a UW view at score −0.373 has MEDIUM conviction
  (|0.373|≥0.35), not LOW. A score of exactly ±0.35 is MEDIUM (≥ threshold).
- **change direction**: UP/DOWN by view rank, not by score magnitude. OW(1)→N(0)
  is DOWN; N(0)→UW(−1) is DOWN; N→OW is UP.
- **Enum casing & values**: match the template's allowed_values exactly (e.g.
  `multi_asset_income` not `multi-asset-income`; `Q2_2026` not `Q2-2026`).
- **Trailing zeros**: JSON numerics `5.8` and `5.80` are equal, but always round
  to the template's declared decimals before emitting.

---

## 8. End-to-end solving checklist

1. Read `prompt.txt`, `payloads/answer_template.json`, and the request payload.
   Note required keys, enums, ordering, precision, and which workflow(s) apply.
2. Fetch the portfolio (`/api/portfolios/<id>`) and the relevant universe
   endpoints; cache large ones to `/tmp`.
3. Identify the governing `policy_id` from the portfolio constraints and read
   the matching policy thresholds from `/api/policies`.
4. Apply the workflow SOP (§3 / §4 / §5).
5. Recompute every numeric field from environment data; round to template
   precision; apply the template's sort order.
6. Re-check every enum value against `allowed_values`; re-check every boolean
   (constraint pass/fail) against the policy thresholds.
7. Emit a single JSON object conforming to the template — no extra keys, no
   narrative.

### Reusable correlation snippet (python3)
```python
import json, itertools
from statistics import mean
lv = json.load(open('/tmp/index_levels_all.json'))
START='2025-05-30'; END='2026-04-30'
def rets(idx):
    rows=sorted([r for r in lv[idx] if START<=r['date']<=END],key=lambda r:r['date'])
    L=[r['level'] for r in rows]
    return [(L[i]-L[i-1])/L[i-1] for i in range(1,len(L))]
def pearson(x,y):
    n=len(x); mx=mean(x); my=mean(y)
    sxy=sum((x[i]-mx)*(y[i]-my) for i in range(n))
    return sxy/((sum((a-mx)**2 for a in x)**0.5)*(sum((b-my)**2 for b in y)**0.5))
R={i:rets(i) for i in UNIVERSE}
pairs=sorted(((a,b,pearson(R[a],R[b])) for a,b in itertools.combinations(sorted(UNIVERSE),2)),key=lambda t:t[2])
highest=max(pairs,key=lambda t:t[2]); lowest=pairs[0]  # pairs[0] is min
```

### Reusable weighted-metric snippet
```python
bonds={b['instrument_id']:b for b in json.load(open('/tmp/bonds_all.json'))}
# port = {instrument_id: market_value_usd_m}
mv=sum(port.values())
hy=sum(q for iid,q in port.items() if bonds[iid]['rating_bucket']=='HY')/mv*100
dur=sum(q*bonds[iid]['modified_duration_years'] for iid,q in port.items())/mv
ytm=sum(q*bonds[iid]['yield_to_maturity_pct'] for iid,q in port.items())/mv
print(round(mv,2),round(hy,2),round(dur,2),round(ytm,2))
```
