# Asteria Portfolio JSON Generation Skill

## Purpose
Generate structured portfolio-management JSON outputs by querying the Asteria Investment Office shared environment API and applying financial calculation rules. Each task provides a request payload and an answer-template schema; the solver must fetch live data, perform calculations, and emit valid JSON conforming to the template.

## API Base URL
`http://34.46.77.124:8010` (from `environment_access.md`; always use this, never localhost).

## Step-by-Step SOP

### 1. Read Inputs
- Read `input/prompt.txt` for narrative context.
- Read `input/payloads/answer_template.json` for the exact output schema, required fields, enum values, ordering rules, and precision requirements.
- Read the request JSON in `input/payloads/` (e.g., `desk_request.json`, `review_request.json`, etc.) for portfolio-specific parameters, stale snapshots, and desk preferences.

### 2. Discover Available Data
Call `GET /api/catalog` to see the universe of portfolio IDs, policy IDs, index IDs, issuer IDs, bond IDs, and opportunity-set IDs.

### 3. Fetch Core Records
Always fetch the portfolio record and its linked policy:
- `GET /api/portfolios/<portfolio_id>` → current holdings, market value, constraints, as-of date.
- `GET /api/policies` → constraint thresholds (HY caps, duration bands, issuer limits, correlation thresholds, allocation mapping thresholds, etc.).

**Data-precedence rule:** If the request payload contains a "stale" snapshot (e.g., old holding data, old index levels, old as-of date), always treat the live API records as authoritative. Set `data_precedence` to `current_environment_over_stale_payload` when a conflict exists.

### 4. Fetch Domain-Specific Data Based on Task Type

| Task Domain | Required Endpoints |
|-------------|-------------------|
| **Energy credit trade** | `/api/instruments/bonds`, `/api/issuers`, `/api/market/energy` |
| **Correlation review** | `/api/indices`, `/api/index-levels`, `/api/index-levels/<index_id>` |
| **Allocation views (CIO/quarterly)** | `/api/allocation/opportunity-sets`, `/api/allocation/prior-views`, `/api/macro-signals` |
| **Credit rebalance / risk reduction** | `/api/instruments/bonds`, `/api/issuers`, portfolio holdings |
| **Multi-asset committee** | All of the above as needed for the specific portfolio |

### 5. Perform Calculations

#### 5a. Pearson Correlation from Monthly Index Levels
- Fetch levels for each relevant index via `/api/index-levels/<index_id>`.
- Compute **monthly simple returns**: `r_t = (level_t - level_{t-1}) / level_{t-1}` for each consecutive pair.
- Compute Pearson correlation across the common return observation window.
- Round to the precision specified in the template (usually 3 decimals).
- Sort index IDs alphabetically within each pair.

#### 5b. Allocation View Mapping (Signal Score → View / Conviction)
Use the policy thresholds from `/api/policies` → `allocation_mapping`:
- **View:**
  - `signal_score >= 0.35` → `OW`
  - `signal_score <= -0.35` → `UW`
  - Otherwise → `N`
- **Conviction:**
  - `|signal_score| >= 0.7` → `HIGH`
  - `|signal_score| >= 0.35` → `MEDIUM`
  - Otherwise → `LOW`
- **Change:** Compare current `view` to `prior_view` (from `/api/allocation/prior-views`):
  - If view rank increases (e.g., N→OW, UW→N) → `UP`
  - If view rank decreases → `DOWN`
  - If unchanged → `UNCHANGED`
- **Rationale code:** Use the `rationale_code` from the matching macro signal record.

#### 5c. Post-Trade / Portfolio Metrics
- **Weighted modified duration:** `Σ (holding_mv * duration) / total_mv`
- **Weighted yield to maturity:** `Σ (holding_mv * ytm) / total_mv`
- **HY allocation pct:** `Σ (HY holding market values) / total_market_value * 100`
- **Issuer concentration:** Check that no single issuer exceeds the policy limit (default 12%).
- **Subsector diversification:** Count distinct subsectors; must be ≥ policy minimum (default 2).
- **Watchlist avoidance:** Verify no holding whose issuer has `watchlist: true` is being bought or retained in excess.

#### 5d. Trade Sizing
- Use the desk request’s `total_notional_usd_m` and `ticket_count` to derive per-trade notionals.
- Match candidate instruments to portfolio preferences (e.g., LNG exporters, non-watchlist carry).
- When rebalancing, sell existing pressure points first (SELL before BUY), then fund eligible candidates.
- Sort trades by action (SELL before BUY) then by `instrument_id` ascending.

### 6. Apply Constraint Checks
Evaluate each boolean flag using live data against the active policy:
- `hy_cap_pass`: post-trade HY % ≤ `max_hy_allocation_pct`
- `duration_band_pass`: post-trade duration inside `duration_band_years` [min, max]
- `selected_issuer_diversification_pass`: no issuer > `issuer_concentration_limit_pct`
- `selected_subsector_diversification_pass`: distinct subsector count ≥ `subsector_min_count_for_diversified`
- `watchlist_avoidance_pass`: no new watchlist exposure added
- `target_hy_reduction_met`: reduction ≥ `target_hy_reduction_pct` (for risk-reduction policies)

### 7. Assemble the Output JSON
- Include **only** the JSON object—no markdown fences, no narrative commentary.
- Use exact enum values from the template; never invent new values.
- Respect all ordering rules:
  - Lists sorted alphabetically by ID unless template specifies another order (e.g., request payload’s `focus_opportunity_sets` order).
  - Pairs sorted alphabetically.
  - Trades: SELL before BUY, then `instrument_id` ascending.
- Round numbers to the template-specified precision (usually 1, 2, or 3 decimal places).
- Populate `as_of_date` from the live portfolio record, not from stale payload snapshots.

### 8. Validate Before Returning
- Verify every `required` top-level key and nested key is present.
- Confirm list lengths match exact requirements (e.g., `length: 2`, `required_length: 8`).
- Double-check that enum values match the template’s `allowed_values` exactly.
- Ensure boolean flags are actual JSON booleans (`true`/`false`), not strings.

## Common Pitfalls to Avoid
1. **Using stale payload data as primary source** — always refresh from the API.
2. **Wrong correlation window** — use the policy’s `review_window_start` and `review_window_end`, not the request payload dates.
3. **Incorrect trade ordering** — SELL before BUY, then alphabetical by `instrument_id`.
4. **Precision errors** — round exactly to the decimals specified (1, 2, or 3).
5. **Missing `data_precedence` field** — include it and set it correctly when stale vs. current conflicts exist.
6. ** Inventing enum values** — only use values explicitly listed in the template.
7. **Forgetting to sort pairs alphabetically** — both correlation pairs and index sets must be alphabetically ordered.

## Quick Reference: Key API Endpoints
```
GET /api/catalog
GET /api/policies
GET /api/portfolios
GET /api/portfolios/<portfolio_id>
GET /api/instruments/bonds
GET /api/issuers
GET /api/market/energy
GET /api/indices
GET /api/index-levels
GET /api/index-levels/<index_id>
GET /api/allocation/opportunity-sets
GET /api/allocation/prior-views
GET /api/macro-signals
```

## Example Policy Thresholds (from `/api/policies`)
- HY cap: `max_hy_allocation_pct` = 20.0
- Duration band: `[3.0, 5.0]` years
- Issuer concentration limit: 12.0%
- Correlation high threshold: 0.8
- Correlation low threshold: 0.2
- Allocation OW threshold: ≥ 0.35
- Allocation UW threshold: ≤ -0.35
- HIGH conviction: |score| ≥ 0.7
- MEDIUM conviction: |score| ≥ 0.35
