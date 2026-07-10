# Asteria Investment Office — Operational Skill

## Data Precedence Rule
**Current environment always overrides stale local payloads.**
- The remote API (`/api/portfolios`, `/api/instruments/bonds`, `/api/issuers`, `/api/policies`, `/api/index-levels`, `/api/macro-signals`, `/api/allocation/prior-views`) is the book of record.
- Local request payloads contain intake context (requested ticket sizes, focus sets, review windows) but their stale snapshots, stale marks, and stale exception-board quantities must be reconciled to current API records.
- When a local payload's date or quantity conflicts with the API, use the API value.
- Set `data_precedence` fields to `"current_environment_over_stale_payload"` or equivalent.

## Key Endpoints and What They Carry
| Endpoint | Key Fields |
|---|---|
| `GET /api/catalog` | All valid IDs: bonds, indices, issuers, opportunity sets, policies, portfolios |
| `GET /api/policies` | Thresholds: `max_hy_allocation_pct` (20%), `duration_band_years` ([3.0, 5.0]), `correlation_high_threshold` (0.8), `correlation_low_threshold` (0.2), `view_score_thresholds` (OW ≥ 0.35, UW ≤ −0.35), `conviction_thresholds` (HIGH ≥ 0.7, MEDIUM ≥ 0.35, LOW < 0.35), `issuer_concentration_limit_pct` (12%), `subsector_min_count_for_diversified` (2) |
| `GET /api/portfolios/<id>` | Current holdings with `instrument_id`, `quantity_usd_m`, `sleeve`, `market_value_usd_m`, `as_of_date`, `constraint_policy_id` |
| `GET /api/instruments/bonds` | `rating_bucket` (IG/HY), `modified_duration_years`, `yield_to_maturity_pct`, `energy_linked`, `subsector`, `issuer_id`, `candidate`, `recommended_theme_tags` |
| `GET /api/issuers` | `watchlist` (boolean), `credit_outlook`, `rating_bucket`, `subsector` |
| `GET /api/index-levels` and `/<index_id>` | Monthly levels with dates, 12 rows per index spanning ~1 year |
| `GET /api/macro-signals` | Per-opportunity-set `score` (float), `rationale_code`, `drivers`, `quarter` |
| `GET /api/allocation/prior-views` | `view` (UW/N/OW), `conviction`, `previous_quarter`, target `quarter` |
| `GET /api/allocation/opportunity-sets` | `asset_class`, `sub_asset_class`, `display_order` |
| `GET /api/market/energy` | Commodity direction signals and pitch themes |

## Policy Identification
- Use the top-level policy-set ID from `/api/policies` (e.g., `"POLICY_SET_2026_05"`) when an answer template asks for `policy_id` in an allocation or committee context.
- For portfolio-specific constraint checks, use the `constraint_policy_id` from the portfolio record (e.g., `POL_CREDIT_DEFAULT`, `POL_CREDIT_RISK_REDUCTION`, `POL_CORRELATION_DEFAULT`, `POL_MULTI_ASSET_DEFAULT`).

## Weighted Portfolio Metrics (Credit Tasks)
For a portfolio with holdings `(qty_i, dur_i, ytm_i, rating_bucket_i)`:

```
MV = Σ qty_i
HY_pct = Σ(qty_i for HY bonds) / MV × 100
Wtd_dur = Σ(qty_i × dur_i) / MV
Wtd_ytm = Σ(qty_i × ytm_i) / MV
```

Post-trade: remove sold bonds' contributions, add bought bonds' contributions, recompute MV, HY_pct, wtd_dur, wtd_ytm. Round to declared precision (typically 2 decimal places for percentages and duration, 1 decimal place for notional in USD millions).

## Pearson Correlation from Index Levels (Correlation Tasks)
1. Extract 12 monthly levels per index (start-date through end-date).
2. Compute 11 monthly simple returns: `r_t = (L_t − L_{t−1}) / L_{t−1}`.
3. Compute Pearson: `r = Σ(x_i−x̄)(y_i−ȳ) / √(Σ(x_i−x̄)² · Σ(y_i−ȳ)²)`.
4. Round to 3 decimal places.
5. `return_observations` = 11 (one less than the number of level dates).
6. Within each pair, index IDs are sorted alphabetically ascending.
7. `index_set` lists all universe indices in ascending alphabetical order.

## View Mapping from Macro Signals (Allocation Tasks)
For each opportunity set, read `score` from `/api/macro-signals` for the target quarter:

| Condition | View | Conviction | 
|---|---|---|
| score ≥ 0.35 | OW | abs(score) ≥ 0.7 → HIGH, ≥ 0.35 → MEDIUM |
| score ≤ −0.35 | UW | abs(score) ≥ 0.7 → HIGH, ≥ 0.35 → MEDIUM |
| −0.35 < score < 0.35 | N | abs(score) < 0.35 → LOW |

**Change versus prior quarter**: Compare the new view to the prior quarter's view from `/api/allocation/prior-views`. Use rank order UW = −1, N = 0, OW = 1. If current rank > prior rank → `"UP"`, if < → `"DOWN"`, else `"UNCHANGED"`.

## Constraint Checks

### Credit Constraints
- **HY cap**: `hy_allocation_pct ≤ max_hy_allocation_pct` (typically 20%). Use post-trade HY.
- **Duration band**: `weighted_modified_duration_years ∈ [3.0, 5.0]`.
- **Issuer diversification (selected pair)**: The two selected bonds must have different `issuer_id`s.
- **Subsector diversification (selected pair)**: At least `subsector_min_count_for_diversified` (2) distinct subsectors among the selected bonds.
- **Watchlist avoidance**: No selected bond's issuer may be on the watchlist (`watchlist: true` in `/api/issuers`).

### Watchlist Issuers
The following issuers are on the watchlist:
- ISS_DRIFTWOOD (Driftwood Shale Finance) — bonds: BND_DRIFTWOOD_2028, BND_DRIFTWOOD_2031
- ISS_JUNIPER_TEL (Juniper Telecom) — bonds: BND_JUNIPER_2028, BND_JUNIPER_2030
- ISS_PACIFIC_REFIN (Pacific Refining) — bonds: BND_PACREF_2028, BND_PACREF_2030

### Correlation Constraints
- **High threshold** (0.8): Pairs with correlation > 0.8 represent concentration risk.
- **Low threshold** (0.2): Pairs with correlation < 0.2 (or negative) represent diversification.
- **China-Asia dependence**: Check `IDX_CHINA` vs `IDX_AC_ASIA_PAC_EX_JP`. If correlation > 0.8, set `china_asia_dependence_flag = true` and `primary_code = "CHINA_ASIA_DEPENDENCE"`.

## Output Ordering Conventions
- **Trades (credit tasks)**: SELL before BUY, then ascending by `instrument_id` within each action.
- **Allocation rows**: Follow the order in the request payload's `focus_opportunity_sets` list.
- **Index lists and pair IDs**: Ascending alphabetical by index ID.
- **Sleeve actions**: Ascending by `sleeve` name or in the order specified by the template.
- **Correlation summary pairs**: `highest_concentration` first, `best_diversifier` second.

## Risk Overlay Selection (Allocation Tasks)
Choose the overlay that matches the dominant signal pattern across opportunity sets:
- **CREDIT_RISK_REDUCTION** / `trim_credit_beta`: When HY is UW and U.S. Treasuries/IG is OW — signals rotation from credit risk to quality.
- **DURATION_QUALITY_TILT** / `tilt_to_duration_quality`: When duration assets (UST, Bunds) are broadly OW and credit/equity is mixed.
- **EQUITY_BETA_EXTENSION** / `add_cyclical_equity_beta`: When equity OW signals dominate.
- **CURRENCY_DEFENSIVE_HEDGE** / `add_currency_hedge`: When USD is UW and defensive currencies are OW.
- **NO_OVERLAY** / `hold_policy_weights`: When signals are balanced/neutral across asset classes.

Rationale codes in the overlay should be listed in business-priority order (most impactful first).

## Precision Rules (by Field)
- Correlation values: **3 decimal places** (e.g., 0.915, −0.825).
- Portfolio weights/percentages (HY%, YTM%, duration): **2 decimal places** (e.g., 13.24, 5.76, 3.28).
- Notional/quantity (USD millions): **1 decimal place** (e.g., 4.0, 12.0).
- Signal scores: **3 decimal places** (e.g., 0.732, −0.373).
- Return observations: **integer** (11 for a 12-month window).
- Dates: **YYYY-MM-DD** format.

## Common Pitfalls
1. **Stale local data**: Never use local payload marks, quantities, or dates that conflict with the current API. The stale exception board or desk worksheet may show different quantities than the current portfolio — always use current API data.
2. **HY identification**: HY = `rating_bucket == "HY"` (BB+ and below). BBB− and above is IG.
3. **Watchlist from issuers endpoint, not bonds**: Check `/api/issuers` for the `watchlist` field — the bond record alone may not carry it.
4. **Same-issuer concentration**: A bond from an issuer already in the portfolio may still pass the selected-issuer diversification check (it only checks the two new bonds against each other), but be aware of overall issuer concentration limits.
5. **Duration push**: When replacing short-duration HY bonds with longer-duration IG bonds, duration drifts up — verify it stays within [3.0, 5.0].
6. **Correlation sign**: The "lowest" correlation is the most negative (not the closest to zero). The pair with the most negative correlation is the best diversifier.
7. **View change direction**: Changing from OW to UW is DOWN (not UP), even though UW is "underweight." Use the numeric rank order.
8. **Energy-linked filter**: For energy credit tasks, filter bonds to `energy_linked == true` and `candidate == true`. Verify the issuer is not on the watchlist.
9. **Policy ID contexts**: Portfolio-level constraint checks reference the portfolio's `constraint_policy_id`; allocation-view tasks use the top-level `policy_id` from `/api/policies`.
10. **Trade sizing**: Total sells must equal total buys (rotation, not net inflow/outflow) unless the request explicitly describes new funding.
