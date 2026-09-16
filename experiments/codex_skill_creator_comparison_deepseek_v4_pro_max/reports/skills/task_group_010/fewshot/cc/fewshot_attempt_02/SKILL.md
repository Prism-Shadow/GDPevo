---
name: asteria-investment-office
description: Run institutional portfolio workflows for the Asteria Investment Office shared environment. Use this skill whenever the user mentions Asteria, the Investment Office, a portfolio identified by a PF- prefix (e.g., PF-EN-ALTA, PF-INT-NEXVEN, PF-FI-LUMEN, PF-MA-HELIO), credit trading, energy-linked bonds, index correlation reviews, active allocation views, risk rebalancing, multi-asset committee decisions, or any task that references a shared Asteria API. Also use this skill when the user provides an answer template JSON, a desk/committee request payload, or asks for institutional fixed-income or equity portfolio analytics.
---

# Asteria Investment Office

Institutional portfolio workflows for the Asteria Investment Office shared environment. This
skill covers credit trading, index correlation, active allocation, risk rebalancing, and
multi-asset committee tasks.

## Environment

The Asteria Investment Office exposes a shared public-data API. The solver reads current
portfolio records, bond universes, issuer research, policies, indices, index levels,
market signals, allocation taxonomy, macro signals, and prior views from this service.

### Base URL

```
http://task-env:9010
```

### API Endpoints

| Endpoint | Purpose |
|---|---|
| `GET /api/portfolios` | All portfolio summaries (id, name, strategy, as_of_date, market_value, constraint_policy_id) |
| `GET /api/portfolios/{portfolio_id}/holdings` | Current holdings for a single portfolio (instrument_id, quantity, market_value, weight) |
| `GET /api/instruments/bonds` | Full bond universe (id, issuer, coupon, maturity, rating, rating_bucket, yield, duration, sector, subsector, spread, candidate, energy_linked, theme_tags) |
| `GET /api/issuers` | Issuer credit research (issuer_id, name, sector, subsector, rating_bucket, credit_outlook, watchlist, research_tags) |
| `GET /api/market/energy` | Current energy market signals (commodity scores, direction, pitch_themes, stale_data_warning) |
| `GET /api/indices` | Index metadata (id, display_name, region, currency, frequency, level_start/end dates) |
| `GET /api/index-levels` | Monthly index levels for all indices over the current window |
| `GET /api/index-levels/{index_id}` | Monthly level series for a single index |
| `GET /api/allocation/opportunity-sets` | Allocation taxonomy (opportunity_set, asset_class, sub_asset_class, display_order) |
| `GET /api/allocation/prior-views` | Previous quarter active views (opportunity_set, view, conviction, quarter) |
| `GET /api/macro-signals` | Current quarter macro signal scores (opportunity_set, score, rationale_code, drivers, quarter) |
| `GET /api/policies` | All policy objects (credit_default, credit_risk_reduction, correlation, multi_asset, multi_asset_risk, allocation_mapping) |

Read every endpoint the task needs. Do not assume stale local payload data
matches the current API.

### Start Every Task Here

1. Read `GET /api/portfolios` to confirm the portfolio_id, constraint_policy_id, and
   as_of_date.
2. Read `GET /api/policies` for the constraint thresholds and mapping rules the task
   uses.
3. Read every additional endpoint implied by the task domain (bonds, issuers, indices,
   index levels, energy, allocation, signals).

## Data Precedence

**The current API is the book of record.** Local JSON payloads (desk requests, meeting
memos, committee packets) are intake context that may contain stale marks, old
worksheets, earlier estimates, or unreconciled desk notes. Always resolve conflicts in
favor of the current API.

When a local payload includes a snapshot date, holdings table, or mark that disagrees
with the API, use the API values. If there is no conflict, still validate key figures
against the API. The `data_precedence` field in some answer templates explicitly captures
this choice — set it to `current_environment_over_stale_payload` when the API is
authoritative.

The energy market endpoint (`/api/market/energy`) carries a `stale_data_warning` field.
Read it and apply its date guidance: worksheets dated before the warning threshold are
stale.

## Working with Answer Templates

Every local payload directory includes an `answer_template.json` that defines the exact
output JSON shape. The solver produces a single JSON object conforming to that schema.

Follow the template precisely:

- **Required keys**: Every key listed under `required`, `required_top_level_keys`,
  `required_keys`, or `required_item_keys` must appear in the output.
- **Fixed values**: Fields with `required_value` or a declared constant must carry
  exactly that value.
- **Enums**: Fields with `allowed_values` must use only those values. The template
  enumerates allowed rationale codes, segment names, action verbs, view codes, and risk
  codes.
- **Numeric precision**: Fields declaring `precision` (e.g. `precision: 2`) must be
  rounded to that many decimal places. Do not carry extra digits.
- **Ordering**: Lists with an `ordering` rule must respect it — alphabetical by id,
  SELL before BUY, by display_order or request order.
- **List lengths**: Check explicit `length` constraints and do not produce extra or
  missing entries.
- **Units**: Respect declared units (USD millions, percent, years, percentage points).
  The template may mix `quantity_usd_m`, `notional_usd_m`, percentage fields, and
  decimal fractions.

When the template expects a task_id or portfolio_id, read the prompt and payloads for
the correct value, then validate against the API.

Output only the JSON object. Do not wrap it in markdown fences unless the prompt
explicitly permits wrapping.

## Correlation Computation

When a task asks for Pearson correlations from monthly index levels, follow this
procedure exactly:

1. Read the index metadata from `GET /api/indices`. Note the `level_start_date` and
   `level_end_date` — these define the available window.
2. If the task provides a specific review window (e.g., in a review_request payload),
   use those dates. Otherwise use the full available window.
3. For each index in the task's universe, fetch its monthly level series from
   `GET /api/index-levels/{index_id}`.
4. Align all series by date. Every index in the Asteria environment uses the same
   monthly observation dates.
5. Compute monthly simple returns: `(level_t / level_{t-1}) - 1.0`.
6. For each pair of indices, compute the Pearson correlation coefficient from the
   paired return arrays:
   - Subtract the mean from each series.
   - Sum the products of the centered series.
   - Divide by sqrt(sum of squared centered series_i) times
     sqrt(sum of squared centered series_j).
7. Round results to three decimal places unless the template specifies a different
   precision.
8. Sort index ids alphabetically within each pair.

The number of return observations is `len(levels) - 1`, which typically matches the
`return_observations` field in the answer template.

## Policy Interpretation

The `/api/policies` response is a compound object containing several named policy
sub-objects. Each portfolio's `constraint_policy_id` maps to the sub-object to use.

### Credit Policies (POL_CREDIT_DEFAULT, POL_CREDIT_RISK_REDUCTION)

| Field | Meaning |
|---|---|
| `max_hy_allocation_pct` | HY market value must not exceed this percentage of total portfolio market value |
| `duration_band_years` | Portfolio weighted modified duration must stay within [min, max] |
| `issuer_concentration_limit_pct` | No single issuer holdings may exceed this percentage |
| `subsector_min_count_for_diversified` | A diversified portfolio holds at least this many distinct subsectors |
| `target_hy_reduction_pct` | (POL_CREDIT_RISK_REDUCTION only) Desired HY reduction in percentage points |

### Correlation Policy (POL_CORRELATION_DEFAULT)

| Field | Meaning |
|---|---|
| `correlation_high_threshold` | Above this absolute value signals material concentration |
| `correlation_low_threshold` | Below this absolute value signals potential diversification |
| `review_window_start` | Default review window start date |
| `review_window_end` | Default review window end date |

### Allocation Mapping (POL_ALLOCATION_MAPPING)

Maps macro signal scores to active views:

- `score >= OW_min` → OW (typically 0.35)
- `score <= UW_max` → UW (typically -0.35)
- `score` strictly between neutral bounds → N

Conviction levels from `conviction_thresholds`:

- `abs(score) >= HIGH_abs_min` → HIGH (typically 0.70)
- `abs(score) >= MEDIUM_abs_min` → MEDIUM (typically 0.35)
- `abs(score) < LOW_abs_below` → LOW (typically 0.35)

### Multi-Asset Policies

These reference other policies:

- `POL_MULTI_ASSET_DEFAULT` uses allocation_mapping, correlation_default, and
  credit_default.
- `POL_MULTI_ASSET_RISK` uses correlation_default and credit_risk_reduction, plus a
  `committee_escalation_threshold`.

When a multi-asset task spans both correlation and allocation, apply each referenced
policy independently to its domain, then integrate findings.

## Bond Selection

When a task requires selecting bonds from the current universe (credit trading or
risk rebalancing):

1. Read `GET /api/instruments/bonds` for the full instrument universe.
2. Read `GET /api/issuers` for watchlist status and credit research on every issuer.
3. Read `GET /api/portfolios/{portfolio_id}/holdings` for current positions.

### Selection Filters

Apply these filters in the order that matches the task objective:

- **Candidate eligibility**: Only instruments with `candidate: true` are eligible for
  buy recommendations. Instruments with `candidate: false` are held-only (sell or keep
  but do not add).
- **Watchlist avoidance**: Unless the task explicitly requires selling a watchlisted
  holding, do not buy any bond whose issuer has `watchlist: true`. Check `/api/issuers`
  — some bonds carry `WATCHLIST_RISK` theme tags but their issuer record controls the
  actual status.
- **Energy linkage**: For energy-credit tasks, prefer `energy_linked: true`. Non-energy
  bonds may be used for diversification or duration ballast when the task calls for it.
- **Rating bucket**: IG brings lower carry but lower constraint risk. HY brings carry
  but counts against the HY cap. Balance based on the policy's `max_hy_allocation_pct`.
- **Yield carry**: Higher `yield_to_maturity_pct` improves portfolio income. For income
  pitches, prefer bonds with yields above the current portfolio weighted average.
- **Duration**: Keep the post-trade weighted modified duration inside the policy's
  `duration_band_years`. Long-duration bonds add interest-rate sensitivity; short
  bonds reduce it.

### Portfolio Metric Calculations

When computing post-trade metrics:

- **Total market value**: Sum of all position market values after the trades.
- **HY allocation %**: (Sum of HY-rated position values / total market value) * 100.
- **Weighted modified duration**: Weighted average of `modified_duration_years` by
  market-value weight across all positions.
- **Weighted YTM**: Weighted average of `yield_to_maturity_pct` by market-value weight.
- **Issuer concentration**: For each issuer, (total market value held / total portfolio
  value) * 100. Compare to `issuer_concentration_limit_pct`.
- **Subsector count**: Number of distinct `subsector` values across holdings. Compare to
  `subsector_min_count_for_diversified`.
- **HY reduction**: Pre-trade HY% minus post-trade HY% in percentage points.

### Constraint Checks

After constructing a trade package, verify every constraint from the relevant policy:

1. `hy_cap_pass`: post_trade_hy_pct <= max_hy_allocation_pct
2. `duration_band_pass`: duration_band[0] <= post_trade_duration <= duration_band[1]
3. Issuer diversification: no single issuer exceeds the concentration limit
4. Subsector diversification: distinct subsector count meets the minimum
5. Watchlist avoidance: no buy-side ticket touches a watchlisted issuer

If the task defines additional checks (target HY reduction met, watchlist exposure
cleared), verify those as well.

## Allocation View Construction

When a task asks for active allocation views:

1. Read `GET /api/allocation/opportunity-sets` for the full taxonomy.
2. Read `GET /api/allocation/prior-views` for the previous quarter's views.
3. Read `GET /api/macro-signals` for current quarter signal scores and rationale codes.
4. Read `GET /api/policies` for the `allocation_mapping` thresholds.

For each opportunity set in the task's focus list:

- Look up the current macro signal `score` in `/api/macro-signals`.
- Map score to view using `view_score_thresholds` from `allocation_mapping`.
- Map `abs(score)` to conviction using `conviction_thresholds`.
- Compare new view to the prior quarter's view from `/api/allocation/prior-views` to
  determine `change`: UP (rank increased), DOWN (rank decreased), UNCHANGED (same rank).
  Use the `view_rank` mapping: OW=1, N=0, UW=-1.
- Assign the `rationale_code` from the macro signal record.
- Assign `asset_class` from the opportunity-set taxonomy.

When constructing a risk overlay, pick the `overlay_code` and `primary_action` that best
represent the dominant tilt across all views. List `rationale_codes` in business
priority order (most impactful first).

## Multi-Asset Committee Tasks

These tasks integrate correlation findings with allocation views:

1. Compute correlations for the requested index subset using the procedure above.
2. Identify the highest-concentration pair (highest positive correlation involving a
   China or EM index) and the best-diversifier pair (lowest or most negative correlation
   involving a diversifying index like Latin America).
3. Build allocation views for the requested opportunity sets.
4. Cross-reference: if a region shows both high correlation concentration and an
   unfavorable macro signal, recommend trimming. If a region shows low correlation and a
   favorable signal, recommend adding.
5. Set `portfolio_risk_concentration_flag` to true when any correlation exceeds the
   `correlation_high_threshold` from the correlation policy.
6. Set `rebalance_trigger` based on what's driving the action (correlation_cap_breach,
   hy_cap_pressure, etc.).
7. Set `next_step` to `approve_with_monitoring` when all constraints pass but a
   concentration flag is raised.

## Task-Type Recognition

The solver identifies the workflow from the portfolio_id, payloads, and prompt language:

| Signal | Likely workflow |
|---|---|
| Energy-linked bond trade, BUY tickets, income pitch | Credit trading (energy) |
| Correlation, Pearson, monthly returns, index pair extremes | Index correlation review |
| Allocation, views, OW/UW/N, macro signals, prior quarter | Active allocation refresh |
| Risk rebalance, HY reduction, watchlist removal, rotation | Credit risk rebalancing |
| Committee, multi-asset, correlation + allocation, sleeve actions | Multi-asset committee |

When a task bridges multiple domains (e.g., combining correlation and allocation), apply
every relevant section of this skill.

## Rounding and Output Discipline

Every numeric field in the answer template declares a precision. Before emitting the
final JSON:

- Round to the declared number of decimal places using standard half-up rounding.
- Express percentages as the template expects — some templates use percent values
  (e.g., 13.24 for 13.24%), others expect decimal fractions. Read the `unit` or
  description field to disambiguate.
- For correlation values, use three decimal places unless overridden.
- For USD million fields, use the precision declared in the template (typically 1 or 2).

## Self-Check Before Finalizing

Before emitting the answer JSON, verify:

1. Every required key from the template is present.
2. All enum values are from the declared allowed sets.
3. All numeric fields are rounded to declared precision.
4. All lists respect declared ordering.
5. All constraint booleans are computed from policy thresholds against actual
   post-trade numbers, not assumed.
6. The `as_of_date` matches the API's date, not a stale payload date.
7. Trade instruments exist in the current bond universe with `candidate: true` (for
   buys).
8. No watchlisted issuer appears in buy tickets.
