# Asteria Investment Office — Operational Skill

## Environment

All tasks use the shared Asteria API at `http://34.46.77.124:8010`. Treat the API as the **current book of record**. Local payload files (in `input/payloads/`) are intake context — they may contain **stale marks, outdated worksheets, or pre-refresh preferences**. When the API and a local payload disagree, the API wins.

The current environment `as_of_date` is **2026-05-29**. Always set `as_of_date` to this value in outputs. Set `data_precedence` to `"current_environment_over_stale_payload"` whenever the local payload contains stale/older data that the API supersedes.

### Key endpoints

| Endpoint | Use |
|---|---|
| `GET /api/catalog` | Inventory of all IDs (bonds, indices, issuers, portfolios, policies, opportunity sets) |
| `GET /api/portfolios` | List all portfolios with metadata, constraint policy, and current MV |
| `GET /api/portfolios/<id>` | Full portfolio detail including holdings (instrument_id, quantity_usd_m, sleeve, asset_class, notes) |
| `GET /api/instruments/bonds` | Bond master: instrument_id, issuer_id, rating, rating_bucket (IG/HY), modified_duration_years, yield_to_maturity_pct, coupon_pct, maturity, sector, subsector, spread_bps, candidate flag, energy_linked flag, recommended_theme_tags |
| `GET /api/issuers` | Issuer master: issuer_id, issuer_name, sector, subsector, rating_bucket, credit_outlook, watchlist flag, research_tags |
| `GET /api/indices` | Index metadata: index_id, display_name, region, currency, frequency, level date range |
| `GET /api/index-levels` | All index monthly levels (12 points: 2025-05-30 through 2026-04-30) |
| `GET /api/index-levels/<id>` | Single index levels |
| `GET /api/policies` | All policy thresholds including allocation mapping, correlation defaults, credit defaults, credit risk reduction, multi-asset defaults |
| `GET /api/allocation/opportunity-sets` | Opportunity-set taxonomy (opportunity_set, asset_class, sub_asset_class, display_order) |
| `GET /api/allocation/prior-views` | Prior-quarter views (opportunity_set, quarter, previous_quarter, view, conviction) — key for computing `change` |
| `GET /api/macro-signals` | Q2/Q3 2026 signal scores per opportunity_set (score, rationale_code, drivers, quarter) |
| `GET /api/market/energy` | Energy commodity signals and pitch themes |

---

## Workflow: Always start by reading the API

1. **Fetch `/api/catalog`** to orient on available IDs.
2. **Read the answer template** (`input/payloads/answer_template.json`) for the required output shape, key names, enum values, ordering rules, and numeric precision.
3. **Read the payload** (desk request, review request, allocation request, risk memo, committee request) for the task's scope — which portfolio, which instruments/indices/opportunity-sets are in play, and any stale data warnings.
4. **Fetch the portfolio** (`/api/portfolios/<id>`) for current holdings and constraint policy.
5. **Fetch the relevant policy** (`/api/policies`) — the portfolio's `constraint_policy_id` tells you which thresholds apply.
6. **Fetch supporting data** (bonds, issuers, indices, index-levels, macro-signals, prior-views, opportunity-sets) relevant to the task.

---

## Task archetypes and computation rules

### A. Credit trade / rebalance (bond portfolios)

**Selecting bonds:**
- Prefer bonds where `candidate: true`.
- For energy-linked mandates, prefer `energy_linked: true`.
- Avoid issuers where `watchlist: true` (from `/api/issuers`). If the task requires avoiding watchlist buys, never propose a BUY for a watchlisted issuer's bonds.
- If the task requires selling watchlist positions, identify holdings whose issuer has `watchlist: true`.
- For income/carry objectives, prefer higher `yield_to_maturity_pct` while respecting constraint policy.

**Post-trade metrics — key formulas:**

**total_market_value_usd_m** (precision 1 or 2, follow template):
```
= sum of all holding market values after proposed trades
= current portfolio MV + net new buy notional (for buy-only)
= current portfolio MV (for rotation/rebalance — MV is preserved unless funded)
```
For a rotation (sell to fund buy), total MV stays at the pre-trade level. For a buy package funded from new sleeve allocation, total MV = pre-trade MV + total buy notional.

**HY allocation pct** (precision 2):
```
hy_allocation_pct = (sum of HY-bucket holding quantities) / total MV * 100
```
Where HY bucket = bonds whose `rating_bucket` is `"HY"` in the bond master.

**weighted_modified_duration_years** (precision 2):
```
weighted_duration = sum(quantity_i / total_MV * duration_i) for all holdings
```

**weighted_yield_to_maturity_pct** (precision 2):
```
weighted_YTM = sum(quantity_i / total_MV * YTM_i) for all holdings
```

**hy_reduction_pct_points** (precision 2):
```
hy_reduction = pre_trade_hy_pct - post_trade_hy_pct
```

**post_trade_watchlist_exposure_usd_m** (precision 1):
```
= sum of quantities of all holdings whose issuer has watchlist: true after trades
```

**Constraint checks (booleans):**
- **hy_cap_pass**: `post_trade_hy_allocation_pct <= max_hy_allocation_pct` (from policy)
- **duration_band_pass**: `duration_band_years[0] <= post_trade_duration <= duration_band_years[1]`
- **selected_issuer_diversification_pass**: no single issuer among the BUY selections exceeds `issuer_concentration_limit_pct` of total MV (check if any issuer appears on more than one selected ticket)
- **selected_subsector_diversification_pass**: at least `subsector_min_count_for_diversified` distinct subsectors among BUY selections
- **watchlist_avoidance_pass**: no BUY ticket is for a watchlisted issuer
- **target_hy_reduction_met**: `hy_reduction_pct_points >= target_hy_reduction_pct` from policy
- **watchlist_exposure_cleared**: `post_trade_watchlist_exposure == 0`

**Trade ordering in output:**
- Template specifies the rule. Common patterns: SELL before BUY, then alphabetical by `instrument_id` within each action group. Or: sort ascending by `instrument_id`.

---

### B. Equity correlation review

**Computing Pearson correlation from index levels:**

1. Filter index levels to the review window (from `level_start_date` through `level_end_date`). Both endpoints are included — the first date is the base for the first return.
2. Compute **monthly simple returns** for each index:
   ```
   r_t = (level_t / level_{t-1}) - 1
   ```
   where `t` and `t-1` are consecutive monthly observation dates.
3. The number of return observations = number of level dates minus 1.
4. Compute **Pearson correlation** between each pair of return series. Round to **3 decimal places**.
5. Include all requested indices in `index_set`, sorted alphabetically.

**Extreme pairs:**
- **highest_positive**: the pair with the largest positive correlation (closest to +1.0). If ties, pick alphabetically.
- **lowest**: the pair with the most negative correlation (closest to -1.0). This is the *lowest* numeric value, not the lowest absolute value.
- Each pair's index IDs must be sorted alphabetically within the pair.

**Concentration / dependence check:**
- Compare the highest correlation against `correlation_high_threshold` (default 0.8 from `POL_CORRELATION_DEFAULT`).
- `china_asia_dependence_flag`: true if the China-related pair exceeds the high threshold AND involves IDX_CHINA + an Asia/Emerging index.
- `high_threshold_breached`: true if any pair exceeds `correlation_high_threshold`.
- `primary_code`: `"CHINA_ASIA_DEPENDENCE"` if China concentration is the primary concern, `"GLOBAL_DEVELOPED_OVERLAP"` for developed-market overlaps, `"NO_MATERIAL_CONCENTRATION"` if no threshold breached.

**Diversification candidates:**
- Indices that appear in the lowest-correlation pair (the best diversifier) OR that have pairwise correlations below `correlation_low_threshold` (default 0.2). Sorted alphabetically.

**Sleeve actions:**
- For concentrated sleeves: `"trim"`.
- For diversification candidates: `"add"`.
- Sorted alphabetically by `sleeve` name (or by the order in the template).

---

### C. Allocation view refresh

**Determining active view (`UW` / `N` / `OW`):**

From `/api/policies` → `allocation_mapping.view_score_thresholds`:
- `score >= OW_min` (0.35) → `"OW"`
- `score <= UW_max` (-0.35) → `"UW"`
- Otherwise → `"N"`

**Determining conviction (`LOW` / `MEDIUM` / `HIGH`):**

From `/api/policies` → `allocation_mapping.conviction_thresholds`:
- `|score| >= HIGH_abs_min` (0.7) → `"HIGH"`
- `|score| >= MEDIUM_abs_min` (0.35) → `"MEDIUM"`
- Otherwise → `"LOW"`

**Determining change (`UP` / `DOWN` / `UNCHANGED`):**

Compare current view to prior-quarter view (from `/api/allocation/prior-views`):
- Map views to ranks: UW = -1, N = 0, OW = +1 (from `view_rank` in policy).
- If current rank > prior rank → `"UP"`
- If current rank < prior rank → `"DOWN"`
- If equal → `"UNCHANGED"`

**Rationale code:**
- Use the `rationale_code` from `/api/macro-signals` for the given opportunity_set and target quarter.
- The signal score column is also the `signal_score` field (precision 3).

**Prior view:**
- From `/api/allocation/prior-views`: look up the `view` for the opportunity_set where `previous_quarter` matches the task's prior quarter.
- **Important**: The prior-views endpoint returns entries where `quarter` is the target quarter and `previous_quarter` is the prior quarter. Match on both `opportunity_set` and `previous_quarter`.

**Risk overlay:**
- Select the overlay whose `primary_action` best matches the dominant tilt across views:
  - `"DURATION_QUALITY_TILT"` / `"tilt_to_duration_quality"` — when OW duration/IG, UW HY
  - `"CREDIT_RISK_REDUCTION"` / `"trim_credit_beta"` — when reducing credit risk
  - `"EQUITY_BETA_EXTENSION"` / `"add_cyclical_equity_beta"` — when adding equity exposure
  - `"CURRENCY_DEFENSIVE_HEDGE"` / `"add_currency_hedge"` — when hedging currency
  - `"NO_OVERLAY"` / `"hold_policy_weights"` — when no significant tilt
- `rationale_codes`: List the rationale codes of the views that drive the overlay decision, in business priority order (strongest/clearest signal first).

**Ordering:**
- `allocation_views` list: follow the order of `focus_opportunity_sets` from the request payload (not alphabetical).
- `rationale_codes` list: business priority order, highest priority first.

---

### D. Multi-asset committee (hybrid: correlation + allocation)

This archetype combines correlation review and allocation views into a single JSON.

**Correlation summary:**
- Compute Pearson correlations on the subset of indices named in the request.
- `highest_concentration`: the pair with the highest positive correlation.
- `best_diversifier`: the pair with the lowest (most negative) correlation.
- Pairs sorted alphabetically within each `pair` list.

**Target sleeve actions:**
- Based on correlation findings and allocation views: `"trim"` concentrated sleeves, `"add"` diversifying sleeves, `"hedge"` currency sleeves with negative signals.

**Allocation views for each opportunity set:**
- Include `prior_view` (from `/api/allocation/prior-views`), `signal_score` (from `/api/macro-signals`), `view` (derived from score), `change` (vs prior), `conviction` (from score magnitude), `rationale_code` (from macro-signals).
- Round `signal_score` to 3 decimal places.

**Rebalance trigger:**
- `"correlation_cap_breach"` — when a correlation pair exceeds the high threshold.
- `"hy_cap_pressure"` — when HY allocation is near/above cap.
- `"duration_drift"` — when duration is outside the band.
- `"watchlist_concentration"` — when watchlist exposure is material.
- `"committee_review"` — when escalated for general review.

**portfolio_risk_concentration_flag:** `true` when any material concentration or threshold breach is identified.

**next_step:** `"approve_with_monitoring"` when there are actions but no hard constraint breach; `"approve_rotation"` for clean rotations; `"defer_pending_risk_review"` when material risks need further review; `"reject_constraint_breach"` for hard breaches.

---

## Precision rules (by field type)

| Data type | Precision | Example |
|---|---|---|
| `notional_usd_m` / `quantity_usd_m` | 1 decimal | `4.0`, `12.0` |
| `total_market_value_usd_m` | Check template: 1 or 2 decimals | `68.0` or `78.00` |
| `hy_allocation_pct` | 2 decimals | `13.24` |
| `weighted_modified_duration_years` | 2 decimals | `3.28` |
| `weighted_yield_to_maturity_pct` | 2 decimals | `5.80` → `5.8` (trailing zeros omitted per template; follow template's actual output format) |
| `hy_reduction_pct_points` | 2 decimals | `25.64` |
| `post_trade_watchlist_exposure_usd_m` | 1 decimal | `0.0` |
| `correlation` | 3 decimals | `0.974`, `-0.825` |
| `signal_score` | 3 decimals | `-0.373`, `0.732` |
| `return_observations` | integer | `11` |

**Critical**: Match the precision declared in the template's `properties` for each field. If the template says `precision: 2` for a field and the answer for train_001 shows `5.8` not `5.80`, the format strips trailing zeros — match the number of significant decimal places shown in the template specification but don't pad trailing zeros unless the template explicitly formats them.

---

## Ordering rules

1. **Trade lists**: SELL before BUY, then alphabetical by `instrument_id` within each action group. If the template says "sort ascending by instrument_id" without action grouping, sort globally.
2. **Index lists**: Always alphabetical ascending by index ID (`IDX_...`).
3. **Pair IDs**: Both IDs within a pair sorted alphabetically.
4. **Allocation views**: Follow the order in the request payload's `focus_opportunity_sets` or the template's `item_order`.
5. **Sleeve actions**: Alphabetically by `sleeve` name, or by template's `item_order`.
6. **Diversification candidates**: Alphabetically by index ID.
7. **Watchlist sell IDs**: Alphabetically by instrument ID.
8. **Rationale codes in risk_overlay**: Business priority order, highest/c strongest signal first.

---

## Enumeration conventions

- **Actions**: `BUY`, `SELL`, `HOLD`, `NO_TRADE`
- **Sleeve actions**: `trim`, `add`, `hold`, `hedge`, `monitor`, `rotate`
- **Views**: `UW` (underweight), `N` (neutral), `OW` (overweight)
- **Change**: `UP`, `DOWN`, `UNCHANGED`
- **Conviction**: `LOW`, `MEDIUM`, `HIGH`
- **Rating buckets**: `IG` (investment grade: AAA through BBB-), `HY` (high yield: BB+ and below)
- **Data precedence**: `current_environment_over_stale_payload`, `local_payload_over_current_environment`, `no_conflict_found`
- **Sales target segments**: `insurance_general_account`, `pension_liability_matching`, `multi_asset_income`, `private_bank_income`, `endowment_opportunistic`
- **Themes**: `lng_export_tailwind`, `oil_oversupply_caution`, `midstream_stability`, `transition_bond_selectivity`, `avoid_watchlist_yield_trap`
- **Risk note codes**: `hy_cap_pressure`, `watchlist_concentration`, `duration_preservation`, `carry_tradeoff`, `no_action`
- **Rebalance triggers**: `correlation_cap_breach`, `hy_cap_pressure`, `duration_drift`, `watchlist_concentration`, `committee_review`
- **Next steps**: `approve_rotation`, `defer_pending_risk_review`, `approve_with_monitoring`, `reject_constraint_breach`
- **Correlation concentration codes**: `CHINA_ASIA_DEPENDENCE`, `GLOBAL_DEVELOPED_OVERLAP`, `NO_MATERIAL_CONCENTRATION`
- **Overlay codes**: `DURATION_QUALITY_TILT`, `CREDIT_RISK_REDUCTION`, `EQUITY_BETA_EXTENSION`, `CURRENCY_DEFENSIVE_HEDGE`, `NO_OVERLAY`
- **Primary actions**: `tilt_to_duration_quality`, `trim_credit_beta`, `add_cyclical_equity_beta`, `add_currency_hedge`, `hold_policy_weights`

---

## Common pitfalls

1. **Stale payload data**: The local payload may have stale marks, old quantities, or outdated worksheet snapshots. Always reconcile against the API's current portfolio and instrument records. The stale snapshot is intake context — not the source of truth.

2. **Wrong policy**: Each portfolio has a `constraint_policy_id`. Credit default (`POL_CREDIT_DEFAULT`) and credit risk reduction (`POL_CREDIT_RISK_REDUCTION`) have different `target_hy_reduction_pct` values (0.0 vs 4.0). Multi-asset policies (`POL_MULTI_ASSET_DEFAULT`, `POL_MULTI_ASSET_RISK`) stack sub-policies. Always check which policy applies.

3. **Correlation window**: The window is `level_start_date` through `level_end_date` inclusive at both ends. The number of return observations = (number of levels) - 1. A 12-date window yields 11 return observations. Use only the dates within the window — do not include earlier or later observations.

4. **Simple returns, not log returns**: The formula is `(L_t / L_{t-1}) - 1`, not `ln(L_t / L_{t-1})`.

5. **HY classification**: HY is determined by `rating_bucket`, not by the spread or yield. A BB bond is HY even if its spread is modest.

6. **Weighted metrics are market-value-weighted**: Each holding's contribution to portfolio duration or YTM is proportional to its quantity divided by total portfolio market value.

7. **Change direction**: Compare current view rank minus prior view rank. If prior was N (0) and current is OW (+1), that's UP. If prior was OW (+1) and current is N (0), that's DOWN.

8. **Signal score vs conviction**: Signal score determines the view AND conviction independently. View uses the signal score threshold (±0.35). Conviction uses the absolute signal score magnitude (≥0.7 = HIGH, ≥0.35 = MEDIUM, else LOW).

9. **Post-trade MV for rotation**: In a rotation (sell to fund buy), total MV does NOT change — you are swapping one set of holdings for another. In a new-money buy, total MV = current MV + new buy notional.

10. **Watchlist avoidance is per issuer**: The `/api/issuers` endpoint has the `watchlist` boolean. If any issuer is watchlisted, all its bonds are off-limits for BUY actions when watchlist avoidance is required.

11. **Output template is authoritative**: Always read the template JSON for exact key names, required fields, enum values, and ordering rules. Templates differ between tasks even within the same archetype.

12. **Trailing zeros in JSON numbers**: Python's `json.dumps` may output `5.8` for a float `5.80`. If the template requires exactly 2 decimal places (precision: 2), you may need to format the number as `5.8` (minimal representation) or `5.80` (padded). Follow the convention shown in the template's answer examples — train outputs show minimal decimal representation (e.g., `5.8` not `5.80`).
