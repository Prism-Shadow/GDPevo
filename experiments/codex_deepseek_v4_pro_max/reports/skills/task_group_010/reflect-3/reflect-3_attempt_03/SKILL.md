## When to Use

Use this skill when solving institutional-portfolio decision tasks backed by a shared read-only API environment. These tasks require you to fetch current portfolio, instrument, issuer, index, policy, and signal records over HTTP GET, reconcile them against local task-specific payloads (which may be stale), compute quantitative outputs, and return a single JSON answer matching a provided template schema.

## Core Principle: Current Environment Over Stale Payloads

Local task input payloads are intake context. They may contain outdated positions, stale marks, or worksheet snapshots that have not been reconciled. The shared API is the official book of record. Always:
- Read the API first for portfolio holdings, bond master data, issuer research, policy thresholds, index levels, and signal scores.
- Use current API values for all quantitative computations.
- Only fall back to local payload values when the API lacks a field and the template requires it.

## Workflow Template

1. Fetch the catalog (`GET /api/catalog`) to learn available portfolio ids, instrument ids, issuer ids, index ids, policy ids, and opportunity-set names.
2. Fetch the target portfolio holdings and note its constraint policy id.
3. Fetch the policy details to extract thresholds (duration bands, HY caps, issuer concentration limits, correlation thresholds, signal-score mapping rules).
4. Fetch instrument master data (bonds) for yield, duration, rating bucket, sector, subsector, energy-linked flag, and candidate flag.
5. Fetch issuer records for watchlist status, rating bucket, and research tags.
6. For equity-index tasks, fetch index metadata and monthly index levels. Compute Pearson correlations from consecutive monthly simple returns: (level_t - level_{t-1}) / level_{t-1}.
7. For allocation-view tasks, fetch the opportunity-set taxonomy, prior-quarter views, and macro-signal scores.
8. Build the candidate JSON answer by applying numeric logic and policy thresholds to the fetched data, never by guessing.

## Metric and Constraint Conventions

### Duration and Yield (Fixed-Income Portfolios)

- **Weighted modified duration**: sum(quantity × modified_duration) / total_market_value.
- **Weighted YTM**: sum(quantity × yield_to_maturity_pct) / total_market_value.
- **HY allocation pct**: sum of quantities where rating_bucket = "HY" divided by total market value, times 100.
- **Post-trade total**: pre-trade market value plus net new buys. Sells and buys that are equal in total notional leave the denominator unchanged.

### Credit Constraints

- **HY cap**: post-trade HY allocation must not exceed the policy `max_hy_allocation_pct`.
- **Duration band**: post-trade weighted modified duration must fall inside the policy `duration_band_years` range (inclusive).
- **Selected issuer diversification**: the proposed buy tickets must be from different issuers.
- **Selected subsector diversification**: the proposed buy tickets must include at least the policy `subsector_min_count_for_diversified` distinct subsectors.
- **Watchlist avoidance**: no proposed buy may involve an issuer flagged `watchlist: true` in the issuer endpoint.
- Do not re-flag pre-existing concentration breaches unless the task explicitly asks for a full-portfolio assessment. The `selected_*` constraint checks apply only to the new proposed trades.

### Correlation Review (Equity Indices)

- Use monthly index levels over the review window specified in the task payload.
- Compute Pearson correlation of the 11 monthly simple returns derived from 12 consecutive monthly level observations.
- Return correlation values rounded to three decimal places.
- The `highest_positive` extreme pair is the pair with the largest positive correlation value.
- The `lowest` extreme pair is the pair with the smallest (most negative) correlation value.
- `china_asia_dependence_flag`: true when the China–Asia-Pacific-ex-Japan correlation exceeds the policy `correlation_high_threshold` (typically 0.8).
- `high_threshold_breached`: true when the flagged correlation exceeds the policy high threshold.
- `primary_code`: "CHINA_ASIA_DEPENDENCE" when the China-Asia overlap dominates; "GLOBAL_DEVELOPED_OVERLAP" for developed-market concentration; "NO_MATERIAL_CONCENTRATION" otherwise.

### Allocation Views from Macro Signals

- Use the policy `view_score_thresholds` to map signal scores to views:
  - `OW` when score ≥ `OW_min` (typically 0.35).
  - `UW` when score ≤ `UW_max` (typically -0.35).
  - `N` when score is in the neutral band between the two thresholds.
- Use `conviction_thresholds` for conviction:
  - `HIGH` when |score| ≥ `HIGH_abs_min` (typically 0.70).
  - `MEDIUM` when |score| ≥ `MEDIUM_abs_min` (typically 0.35) but less than HIGH.
  - `LOW` when |score| < `MEDIUM_abs_min`.
- `change` compares the computed view against the prior-quarter view from the `/api/allocation/prior-views` endpoint:
  - `UP` when the rank moves higher (UW→N, UW→OW, N→OW).
  - `DOWN` when the rank moves lower (OW→N, OW→UW, N→UW).
  - `UNCHANGED` otherwise.
- The `rationale_code` comes directly from the macro-signal record for that opportunity set and quarter.
- `prior_view` comes from the prior-views record for the target quarter (the record with `quarter` equal to the target quarter and `previous_quarter` equal to the prior quarter).

### Signal Scores for Currency Opportunity Sets

- Currency opportunity sets (e.g., USD, EUR) appear in the macro-signals endpoint alongside equity and duration sets. Apply the same view-score and conviction thresholds. The asset class for currency sets is "Currency".

## Ordering and Sorting Rules

Every list field in the answer template declares an ordering rule. Follow it exactly:
- **Instrument ids in pair lists**: sort alphabetically within the pair before writing the pair array.
- **Index sets**: ascending alphabetical by index id.
- **Trade lists**: sort by action with SELL before BUY, then by instrument_id ascending within each action group.
- **Allocation-view rows**: in the order given by the request payload's `focus_opportunity_sets` list; do not re-sort alphabetically.
- **Diversification-candidate lists**: ascending alphabetical by index id.
- **Sleeve-action lists**: ascending alphabetical by sleeve name.

## Numeric Precision

- Every numeric field in the answer template declares a precision (e.g., `precision: 2` for percentages, `precision: 3` for correlations, `precision: 1` for USD millions). Round all computed values to exactly that many decimal places before writing them into the JSON. Do not carry extra digits.
- Use standard half-up rounding.

## Energy-Linked Bond Selection

When a task asks for energy-linked bonds:
- Filter the bond universe to instruments where `energy_linked: true` and `candidate: true`.
- Exclude bonds from issuers where `watchlist: true`.
- Prefer bonds whose `recommended_theme_tags` align with the desk preferences or energy-market signal direction (e.g., LNG_EXPORTS, GAS_DEMAND when the LNG signal score is strongly positive).
- Ensure the selected bonds' modified durations fall within the policy duration band after the proposed additions.
- The desk preferences in the local payload describe thematic tilts (e.g., "LNG exporters", "gas demand") but the final selection must satisfy all hard constraints from the policy.

## Rotation and Rebalance Tasks

- Sell positions from issuers flagged on the watchlist first.
- Fund buys by selling existing pressure points; the total buy notional should equal the total sell notional to leave post-trade market value unchanged (unless the task specifies new funding).
- Meet the minimum HY reduction target (in percentage points) stated in the meeting preferences, even if the policy threshold is looser.
- After the rotation, check that the post-trade duration stays inside the CIO duration band.
- `watchlist_sell_ids` lists every instrument_id sold that belongs to a watchlisted issuer, sorted ascending.
- `buys_avoid_watchlist` must be true when every proposed buy avoids watchlisted issuers.

## Committee Decision Tasks (Multi-Asset)

When a committee task links correlation findings with allocation views:
- Compute the correlation summary using only the index subset named in the committee request, not the full index universe.
- The `highest_concentration` pair is the pair with the largest positive correlation among that subset.
- The `best_diversifier` pair is the pair with the smallest (most negative) correlation among that subset.
- `target_sleeve_actions` follow the opportunity-set order declared in the answer template (which matches the committee request order).
- `rebalance_trigger` is "correlation_cap_breach" when any correlation in the summary exceeds the policy correlation high threshold; otherwise pick the most salient risk code.
- `portfolio_risk_concentration_flag` is true when a material concentration (correlation above the high threshold) exists.

## Data Precedence

When the task answer template includes a `data_precedence` field:
- Use "current_environment_over_stale_payload" when the API returns values that differ from the local payload and the API is the authoritative source.
- Use "local_payload_over_current_environment" only when the task explicitly instructs that the local payload overrides the API.
- Use "no_conflict_found" when both sources agree.

## What Not to Do

- Do not copy stale quantities, views, or dates from local payloads into quantitative outputs without cross-checking the API.
- Do not include bonds from watchlisted issuers as buys.
- Do not select bonds whose modified duration pushes the post-trade weighted duration outside the policy band.
- Do not exceed the HY cap, even if a bond's carry looks attractive.
- Do not guess signal scores, prior views, or policy thresholds; always fetch them from the API.
- Do not use the `/api/judge` endpoint; it is not available at test time.

## Typical Endpoint Usage Sequence

Portfolio tasks: catalog → portfolios → portfolio holdings → policies → instruments/bonds → issuers → market/energy (if energy-linked).
Correlation tasks: catalog → indices → index-levels → policies → portfolio holdings.
Allocation tasks: catalog → allocation/opportunity-sets → allocation/prior-views → macro-signals → policies.
Committee tasks: combine correlation and allocation sequences, then cross-reference with portfolio holdings.
