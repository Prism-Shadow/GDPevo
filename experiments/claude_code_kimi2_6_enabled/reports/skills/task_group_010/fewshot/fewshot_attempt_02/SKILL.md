# Skill: Asteria Investment Office Portfolio Risk Solver

## Purpose
Solve `task_group_010` institutional portfolio risk tasks that require querying a shared Asteria Investment Office environment, reading local request payloads, and producing a structured JSON answer that conforms to a provided template.

## Environment Rules
- Use **only** the remote environment base URL declared in `environment_access.md` (e.g., `GDPEVO_ENV_BASE_URL`).
- **Do not** start local env servers, run `env/setup.sh`, or read files under `env/`.
- **Do not** return narrative commentary outside the JSON object unless the prompt explicitly asks for it.

## Step 1: Identify the Task Type and Portfolio
From the prompt, extract:
- **Portfolio ID** (e.g., `PF-EN-ALTA`, `PF-INT-NEXVEN`, `PF-FI-LUMEN`, `PF-MA-HELIO`).
- **Task category**: credit trade, correlation review, allocation view refresh, fixed-income rebalance, or multi-asset committee memo.

## Step 2: Read Local Payloads and Answer Template
List and read every JSON file in `input/payloads/`:
- `answer_template.json` — defines the exact output schema, field names, nesting, and rounding rules.
- Request-specific payloads (e.g., `committee_request.json`, `review_request.json`, `desk_request.json`) — provide constraints such as review windows, index universes, trade sizes, target opportunity sets, or CIO memos.

## Step 3: Query the Shared Environment
Use `curl` or an HTTP tool against the remote base URL. Start with `GET /api/catalog` to discover valid IDs.

**Common endpoints**
| Endpoint | Purpose |
|---|---|
| `GET /api/portfolios` | List all portfolios |
| `GET /api/portfolios/<portfolio_id>` | Holdings, market value, and constraint policy |
| `GET /api/instruments/bonds` | Bond universe with coupon, maturity, rating bucket, duration, YTM, spread, energy-linked flag, candidate flag, and issuer ID |
| `GET /api/issuers` | Issuer metadata including `watchlist`, `rating_bucket`, `sector`, and `subsector` |
| `GET /api/indices` | Index metadata (frequency, region, etc.) |
| `GET /api/index-levels/<index_id>` | Monthly level time-series for correlation calculations |
| `GET /api/allocation/opportunity-sets` | Taxonomy of opportunity sets |
| `GET /api/allocation/prior-views` | Prior-quarter views and convictions |
| `GET /api/macro-signals` | Quarterly signal scores and rationale codes per opportunity set |
| `GET /api/policies` | Policy thresholds: duration bands, HY caps, correlation thresholds, view-score thresholds, and conviction thresholds |
| `GET /api/market/energy` | Energy market signals and client pitch themes |

## Step 4: Compute and Derive Values

### Credit Trade Strategy
1. Compute current portfolio metrics from the portfolio’s holdings: total market value, HY allocation %, weighted modified duration, and weighted YTM.
2. Filter the bond universe using criteria from the prompt/payload:
   - `energy_linked == true` (if required)
   - `candidate == true` (if "eligible" is specified)
   - Issuer `watchlist == false`
   - Rating bucket and duration band aligned with the portfolio’s active policy.
3. Select the required number of bonds and notional amounts (respect even splits if the prompt specifies them).
4. Compute post-trade metrics:
   - `hy_allocation_pct` = (current HY market value) / (new total market value) × 100
   - `weighted_modified_duration_years` = Σ(quantity × duration) / new total
   - `weighted_yield_to_maturity_pct` = Σ(quantity × YTM) / new total
   - Issuer concentration for each selected issuer = (existing quantity + new quantity) / new total
   - Subsector count (must be ≥ `subsector_min_count_for_diversified` from the active policy).
5. Choose a `client_pitch_theme` that aligns with the selected bonds and has a positive market signal from `/api/market/energy`.

### Correlation Review
1. Fetch monthly index levels for each index in the requested universe over the review window.
2. Compute simple monthly returns: `(level_t − level_{t−1}) / level_{t−1}`.
3. Compute the **sample Pearson correlation** for every pair. Round to the precision declared in the template (typically three decimals). Pair identifiers should be listed in alphabetical order.
4. Identify:
   - **Highest concentration pair** — the pair with the maximum correlation.
   - **Best diversifier pair** — the pair with the minimum correlation (ideally negative).
5. Map findings to sleeve actions per the template instructions (e.g., trim, add, hold, reduce).

### Allocation View Refresh
1. For each requested opportunity set, fetch the macro signal record for the correct quarter from `/api/macro-signals`.
2. Map `signal_score` to the active view using the policy’s `view_score_thresholds`:
   - `score > OW_min` → `OW`
   - `score < UW_max` → `UW`
   - otherwise → `N`
3. Map the absolute score to conviction using the policy’s `conviction_thresholds`:
   - `|score| ≥ HIGH_abs_min` → `HIGH`
   - `|score| ≥ MEDIUM_abs_min` → `MEDIUM`
   - otherwise → `LOW`
4. Determine `change` by comparing the new view to the `prior_view` from `/api/allocation/prior-views`:
   - Use the implicit rank: `OW (1) > N (0) > UW (−1)`.
   - `UP` if rank increases, `DOWN` if rank decreases, `UNCHANGED` if the same.
5. Carry over the `rationale_code` from the macro signal record.

### Fixed-Income Rebalance
1. Calculate current HY % and weighted duration from the portfolio’s holdings.
2. Identify watchlist and HY holdings to sell.
3. Select IG, non-watchlist buys that keep:
   - `post_trade_hy_allocation_pct ≤ max_hy_allocation_pct`
   - `post_trade_duration_years` inside `duration_band_years`
   - `post_trade_watchlist_exposure_usd_m == 0` (if the policy requires clearing watchlist exposure).
4. Ensure the rotation meets the policy’s `target_hy_reduction_pct` (interpret as percentage points or relative reduction per the template).
5. Populate exception flags (`hy_cap_pass`, `duration_band_pass`, `watchlist_exposure_cleared`, etc.) based on post-trade metrics.

### Multi-Asset Committee Memo
1. Run the **correlation analysis** on the portfolio’s non-US equity holdings (or the index universe specified in the payload).
2. Run the **allocation view refresh** for the requested opportunity sets.
3. Set `rebalance_trigger` if the highest concentration correlation exceeds `correlation_high_threshold` from the policy (e.g., `correlation_cap_breach`).
4. Set `portfolio_risk_concentration_flag` accordingly.
5. Derive `target_sleeve_actions` from the allocation views:
   - `UW` → `trim`
   - `OW` → `add`
   - `N` → `hedge` or `hold` per the template instructions.
6. Choose `next_step` based on exceptions and triggers (e.g., `approve_with_monitoring` when triggers exist but are manageable).

## Step 5: Populate the Answer Template
- Transfer every required field from `answer_template.json`.
- Use exact key names, array structures, and nesting.
- Apply rounding rules precisely (e.g., correlations to three decimals, percentages to two decimals, durations to two or three decimals as specified).
- Return **only** the JSON object. Do not wrap it in markdown code fences or add explanatory text.

## Step 6: Validate
- Verify the JSON is well-formed (`python3 -m json.tool`).
- Cross-check every numeric bound against the active policy from `/api/policies`.
- Confirm all template fields are present and populated.
- Ensure no extra keys or commentary are included.
