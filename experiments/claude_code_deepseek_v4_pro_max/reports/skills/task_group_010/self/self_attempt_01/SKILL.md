# Asteria Investment Office — Reusable Task-Solving Procedure

## 1. Workflow Rules

### 1.1 Always start from the API, not the local payload
Local payloads (desk requests, meeting memos, committee packets) provide **task context only** — the opportunity-set names requested, the portfolio id, the quarter, the trade size. Stale snapshots, stale marks, and stale local notes must be **overridden** with current API data.

### 1.2 Data-precedence baseline
Unless the local payload has a date *newer* than the API `as_of_date` (which it never will in this environment), the API is authoritative. Use `"data_precedence": "current_environment_over_stale_payload"` as the default answer.

### 1.3 Standard call sequence
1. `GET /api/policies` — policy thresholds, constraint bands, correlation thresholds, conviction/view-score mapping.
2. `GET /api/portfolios/<portfolio_id>` — current holdings, total market value, constraint policy id.
3. Domain-specific endpoints:
   - **Credit / fixed-income:** `/api/instruments/bonds`, `/api/issuers`, `/api/market/energy`
   - **Equity / correlation:** `/api/indices`, `/api/index-levels`
   - **Allocation:** `/api/allocation/opportunity-sets`, `/api/allocation/prior-views`, `/api/macro-signals`
4. `/api/catalog` is only needed to confirm available IDs.

### 1.4 Task-type dispatch
- **Credit trade strategy** (portfolio with `POL_CREDIT_DEFAULT`): bonds + issuers + energy market + portfolio holdings → select BUY tickets, compute post-trade metrics, check constraints.
- **Correlation review** (portfolio with `POL_CORRELATION_DEFAULT`): index levels → Pearson correlations → extreme pairs, concentration, diversification candidates.
- **Allocation view refresh** (CIO desk, no single portfolio): opportunity-set taxonomy + macro signals + prior views + policy → view/change/conviction/rationale rows + risk overlay.
- **FI risk rebalance** (portfolio with `POL_CREDIT_RISK_REDUCTION`): portfolio + bonds + issuers → SELL/BUY trades reducing HY + watchlist while keeping duration in band.
- **Multi-asset committee** (portfolio with `POL_MULTI_ASSET_DEFAULT` or `POL_MULTI_ASSET_RISK`): correlation review (subset of indices) + allocation views (subset of opportunity sets) → linked output.

---

## 2. API/Data Usage Habits

### 2.1 Key entity relationships
- `bond.instrument_id` → `bond.issuer_id` → `issuer.issuer_id`
- `portfolio.holdings[].instrument_id` → `bond.instrument_id` (or `index_id` for equity sleeves)
- `bond.rating_bucket` ∈ {`IG`, `HY`}. `issuer.rating_bucket` matches but may differ in nuance — use **bond-level** `rating_bucket` for HY/IG classification.
- `issuer.watchlist` (boolean) is the authoritative watchlist flag. Bonds tagged `WATCHLIST_RISK` in `recommended_theme_tags` are a secondary signal.
- `bond.candidate` (boolean) — `false` means the bond is already held and should not be double-counted as a new buy unless explicitly instructed.

### 2.2 Policy constraints lookup
Read `/api/policies` once. The response is keyed by policy category:
- `allocation_mapping` — view-score thresholds and conviction thresholds.
- `credit_default` — `max_hy_allocation_pct`, `duration_band_years`, `issuer_concentration_limit_pct`, `subsector_min_count_for_diversified`.
- `credit_risk_reduction` — same fields + `target_hy_reduction_pct`.
- `correlation` — `correlation_high_threshold` (0.8), `correlation_low_threshold` (0.2).
- `multi_asset` / `multi_asset_risk` — composite policies that reference the above.

The portfolio object's `constraint_policy_id` (or `constraints.policy_id`) tells you which policy to apply.

### 2.3 Index-levels endpoint
`GET /api/index-levels` returns all indices. Each index has 12 monthly levels from 2025-05-30 through 2026-04-30 inclusive. Levels are already sorted chronologically. The `indices` endpoint gives metadata: `level_start_date`, `level_end_date`, `currency`, `frequency`.

### 2.4 Macro-signals and prior-views quarter filtering
Both return **all quarters**. Filter:
- **Macro signals:** `quarter == "<target_quarter>"` (e.g., `"Q2_2026"`)
- **Prior views:** `quarter == "<target_quarter>"` AND `previous_quarter == "<prior_quarter>"` (e.g., `Q2_2026` with `Q1_2026` as previous). These prior-view records tell you what the Q1→Q2 view WAS.

### 2.5 Energy market signals
Each signal has `signal_id`, `score` (float, signed), `direction` (descriptive), `commodity`, `summary`. Use these to theme the trade selection. Positive scores on LNG (0.72) and gas (0.46) support gas/LNG-linked bonds. Negative on refining (-0.41) warns away from refiners.

---

## 3. Calculation Procedures

### 3.1 Pearson correlation of monthly simple returns

Given index levels `L_0, L_1, ..., L_n` (n+1 levels → n returns):

```
r_t = (L_t - L_{t-1}) / L_{t-1}    for t = 1..n
```

Then Pearson:

```
ρ = Σ(r_i - r̄)(s_i - s̄) / sqrt(Σ(r_i - r̄)² × Σ(s_i - s̄)²)
```

- Use **all levels** within the window (start_date through end_date, both inclusive).
- `return_observations` = number of levels − 1 = 11 for a full 12-month window.
- Round correlations to **3 decimal places**.
- Do NOT use log returns. Do NOT annualize.

### 3.2 Portfolio-level weighted metrics

**Pre-trade (current):**
```
hy_allocation_pct = Σ(mv of HY-rated holdings) / total_mv × 100
weighted_modified_duration = Σ(holding_mv × instrument_duration) / total_mv
weighted_yield_to_maturity = Σ(holding_mv × instrument_ytm) / total_mv
```

**Post-trade:**
Start with current holdings. Add BUY ticket notional amounts; remove SELL ticket amounts from both the numerator and denominator. Recompute.

**HY reduction (risk rebalance):**
```
hy_reduction_pct_points = pre_trade_hy_pct − post_trade_hy_pct
```

**Watchlist exposure:**
Sum market values of holdings whose **issuer** has `watchlist == true`.

### 3.3 Active allocation view from macro signal score

From policy `allocation_mapping`:
- `OW` if score ≥ 0.35
- `UW` if score ≤ −0.35
- `N` otherwise (i.e., −0.35 < score < 0.35)

**Conviction:**
- `HIGH` if |score| ≥ 0.70
- `MEDIUM` if 0.35 ≤ |score| < 0.70
- `LOW` if |score| < 0.35

**Change vs prior quarter:**
Compare the current view (derived from signal score) against the prior view from the prior-views API (Q1_2026 records with `quarter: "Q2_2026"`):
- `UP` — view moved in the positive direction (N→OW, UW→N, UW→OW)
- `DOWN` — view moved in the negative direction (N→UW, OW→N, OW→UW)
- `UNCHANGED` — view stayed the same

**Rationale code:** Taken directly from the macro-signal record's `rationale_code` field. Do not invent rationale codes.

### 3.4 Constraint checks

**HY cap:** `post_trade_hy_allocation_pct ≤ max_hy_allocation_pct` (20%).

**Duration band:** `duration_band_years[0] ≤ weighted_modified_duration ≤ duration_band_years[1]` (3.0–5.0).

**Issuer diversification (selected):** The newly selected BUY tickets have distinct issuers. In the credit trade context (`selected_issuer_diversification_pass`), check that the two selected bonds are from different issuers.

**Subsector diversification (selected):** The newly selected BUY tickets belong to different subsectors. `subsector_min_count_for_diversified` = 2, so the two selected bonds must map to ≥ 2 distinct subsectors.

**Watchlist avoidance:** No BUY ticket's issuer has `watchlist == true`. Also exclude bonds whose `recommended_theme_tags` include `"WATCHLIST_RISK"`.

**Target HY reduction met (risk rebalance):** `hy_reduction_pct_points ≥ target_hy_reduction_pct` (4.0 pp for `POL_CREDIT_RISK_REDUCTION`).

### 3.5 Correlation concentration analysis

- **Concentration (china_asia_dependence):** If the China–Asia Pacific ex Japan correlation exceeds the `correlation_high_threshold` (0.8) and China is in the portfolio as a dedicated sleeve, flag `china_asia_dependence_flag: true` with `primary_code: "CHINA_ASIA_DEPENDENCE"` and `high_threshold_breached: true`.

- **Extreme pairs:** `highest_positive` = the pair with the maximum Pearson correlation. `lowest` = the pair with the minimum Pearson correlation (most negative). Break ties by alphabetical order of the pair_id list.

- **Diversification candidates:** Among `IDX_EM_EX_CHINA`, `IDX_INDIA`, `IDX_LATAM`, select those with **below-average** correlation to the portfolio's concentration-risk indices. In practice, identify indices with low or negative correlations vs China/EM.

---

## 4. Output-Field Conventions

### 4.1 Dates
- Use `YYYY-MM-DD` format.
- `as_of_date`: use the API portfolio's `as_of_date` (or the policies `as_of_date` if no portfolio). This is consistently `2026-05-29` in the current environment.
- Review windows: use the `review_window` from the correlation policy or the local request's window boundaries.

### 4.2 Sort orders
- **Trade tickets:** Sort by `action` (SELL before BUY), then by `instrument_id` ascending within each action group.
- **Trade package (BUY only):** Sort ascending by `instrument_id`.
- **Index/pair lists:** Sort alphabetically by index id.
- **Pair identifiers within a pair:** Always sort alphabetically.
- **Allocation view rows:** Follow the order in the request payload's `focus_opportunity_sets` list.
- **Sleeve actions:** Sort ascending by sleeve/opportunity_set name.
- **Diversification candidates list:** Sort ascending alphabetically.
- **Watchlist sell IDs:** Sort ascending by instrument_id.

### 4.3 Numeric precision
Match the precision declared in each answer template:
- `notional_usd_m` / `quantity_usd_m`: **1 decimal**
- `total_market_value_usd_m`: **2 decimals**
- `hy_allocation_pct`: **2 decimals**
- `weighted_modified_duration_years`: **2 decimals**
- `weighted_yield_to_maturity_pct`: **2 decimals**
- `post_trade_hy_allocation_pct`: **2 decimals**
- `post_trade_duration_years`: **2 decimals**
- `hy_reduction_pct_points`: **2 decimals**
- `post_trade_watchlist_exposure_usd_m`: **1 decimal**
- `correlation`: **3 decimals**
- `signal_score`: **3 decimals**

### 4.4 Enum values
Use EXACT string values from the answer template's `allowed_values` lists. Common enums:
- Views: `"UW"`, `"N"`, `"OW"`
- Change: `"UP"`, `"DOWN"`, `"UNCHANGED"`
- Conviction: `"LOW"`, `"MEDIUM"`, `"HIGH"`
- Actions: `"BUY"`, `"SELL"`, `"trim"`, `"add"`, `"hold"`, `"hedge"`, `"monitor"`, `"rotate"`
- Booleans are JSON `true`/`false`, not strings.

### 4.5 Envelope
Return **only JSON**. No markdown fences, no narrative. The JSON must contain every required key from the answer template.

---

## 5. Common Pitfalls

1. **Using stale local data instead of API.** The local payload's holding snapshot, stale marks, or prior-week shortlists are intake context — the API is the current book of record.

2. **Confusing `rating_bucket` between bond and issuer levels.** Use the bond's `rating_bucket` for HY/IG classification in portfolio metrics. The issuer-level `rating_bucket` may differ.

3. **Watchlist check on bond tags, not issuer.** Always cross-reference `issuer.watchlist`. A bond may not have `WATCHLIST_RISK` in tags even if the issuer is watchlisted (though in this environment they are consistent, the issuer is authoritative).

4. **Using log returns for correlation.** The task spec says Pearson on **simple** monthly returns. Log returns produce slightly different correlations.

5. **Miscounting return observations.** 12 monthly levels → 11 return observations (consecutive pairs). Don't report 12.

6. **Wrong prior quarter for view changes.** For Q2_2026 target, the prior is Q1_2026. The `/api/allocation/prior-views` records with `quarter: "Q2_2026"` and `previous_quarter: "Q1_2026"` give the prior view. Don't look at Q1_2026 quarter records directly.

7. **Forgetting the correlation policy thresholds.** The `high_threshold` (0.8) and `low_threshold` (0.2) are in `/api/policies` under `correlation`. Use them for concentration/diversification flags — don't hardcode.

8. **Not checking BUY candidates against the constraint policy.** Every BUY must be: `candidate == true`, issuer `watchlist == false`, and (for energy tasks) `energy_linked == true` unless the task explicitly widens the universe.

9. **Duration band misapplication.** The band `[3.0, 5.0]` means 3.0 ≤ duration ≤ 5.0. Both endpoints are inclusive.

10. **Pair-id alphabetization inside pairs.** `["IDX_CHINA", "IDX_EM"]` not `["IDX_EM", "IDX_CHINA"]` even if EM is mentioned first in the task.

11. **Risk overlay ordering.** The `rationale_codes` list in the risk overlay must be in **business priority order, highest priority first**. Derive priority from signal score magnitude and policy impact.

12. **Trade sizing mismatch.** For train_001-style tasks: the total and per-ticket notional must sum exactly to the requested amounts (e.g., $8.0M total, $4.0M each). For train_004-style rotations: sell and buy amounts need not match — the goal is meeting the risk constraints, not preserving MV.

13. **Conviction vs view confusion.** Conviction is about the *strength* of the signal (|score| magnitude). View is about the *direction* (sign of score vs thresholds). A HIGH-conviction OW is possible (score ≥ 0.70); a LOW-conviction OW is also possible (0.35 ≤ score < 0.70 but not HIGH).

14. **Risk overlay vs allocation views.** The risk overlay (`overlay_code` + `primary_action`) is a portfolio-level recommendation separate from the individual allocation rows. Its rationale_codes should be the highest-priority rationale codes from the most material allocation views.
