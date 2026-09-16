---
name: asteria-investment-office
description: Solve Asteria Investment Office institutional portfolio tasks by querying the shared environment API, reconciling stale local payloads against current records, computing standard risk and correlation metrics, and producing strictly schema-conformant JSON answers.
---

# Asteria Investment Office Portfolio Tasks

This skill covers institutional portfolio workflows for the Asteria Investment Office: credit trade strategy, equity correlation review, active allocation views, fixed-income risk rebalancing, and multi-asset committee decisions.

## Environment

The shared Asteria Investment Office service is at `http://task-env:9010/`. All endpoints are read-only GETs with no authentication. The service acts as the current book of record for portfolios, instruments, indices, issuers, allocation views, signals, and market data. Always treat the environment as authoritative.

## Data Precedence

Local payloads (desk requests, meeting memos, committee packets) may contain stale snapshots, desk worksheets from prior weeks, or unreconciled marks. **The environment API is always the current book of record.** When the environment and a local payload disagree on a fact (holdings, dates, ratings, watchlist status, yield, duration), use the environment value. The answer template typically includes a `data_precedence` or similarly purposed field; set it to `current_environment_over_stale_payload` whenever the environment corrects a local payload claim.

Signs that a payload is stale: a `stale_data_warning` in any environment response, a `snapshot_date` or `memo_as_of_date` predating the environment's `as_of_date`, or explicit desk notes saying records must be checked.

## Standard Workflow

For any task anchored to a portfolio_id, follow this sequence:

1. **Fetch the portfolio record** from `GET /api/portfolios` and note `as_of_date`, `constraint_policy_id`, `market_value_usd_m`, and `objective`.
2. **Fetch current holdings** from `GET /api/portfolios/{portfolio_id}/holdings`.
3. **Read the input payload** for the request intent, template schema, and any stale-context flags.
4. **Fetch environment reference data** as needed (see [api_reference.md](api_reference.md)):
   - For credit tasks: `/api/instruments/bonds`, `/api/issuers`, `/api/market/energy`
   - For equity/correlation tasks: `/api/indices`, `/api/index-levels/{index_id}` (one per index)
   - For allocation tasks: `/api/allocation/opportunity-sets`, `/api/allocation/prior-views`, `/api/macro-signals`
5. **Reconcile**: replace any stale payload values with current environment data.
6. **Compute** the required metrics (see Computation Patterns below).
7. **Validate** the output against the answer template's schema, allowed enums, precision, sort order, and required keys.

## API Reference

Full endpoint schemas and field descriptions are in [api_reference.md](api_reference.md). Key points:

- The current environment as-of date appears in portfolio records and market data. Use it for all `as_of_date` fields.
- Bond instruments carry `candidate`, `rating_bucket` (IG/HY), `energy_linked`, `recommended_theme_tags`, `yield_to_maturity_pct`, `modified_duration_years`, `sector`, and `subsector`.
- Issuers carry `watchlist`, `credit_outlook`, `rating_bucket`, and `research_tags`. For watchlist avoidance, check the issuer object, not just bond theme tags.
- Portfolio `constraint_policy_id` links to the relevant constraint policy.
- Index levels are monthly. Each `/api/index-levels/{id}` returns a `levels` array of `{date, level}` objects.
- Macro signals have a `quarter` field and contain `score`, `rationale_code`, and `drivers`. Filter by the quarter specified in the request.
- Prior views have `quarter` and `previous_quarter`. Use the pair matching the request's target and prior quarters.
- Energy market signals include `signal_id`, `direction`, `score`, `commodity`, and `summary`.

## Computation Patterns

### Post-Trade Portfolio Metrics (Credit Tasks)

When the trade package only adds positions (BUY-only) with no SELLs:

- **Post-trade market value** = current `market_value_usd_m` + sum of BUY notional amounts.
- **Post-trade HY allocation pct** = (existing HY holdings MV + new HY buy notionals) / post-trade MV * 100.
- **Post-trade weighted modified duration** = sum(quantity * modified_duration) / sum(quantity) across all post-trade holdings.
- **Post-trade weighted YTM** = sum(quantity * yield_to_maturity_pct) / sum(quantity) across all post-trade holdings.

When the trade package includes SELLs: subtract sold quantities from both numerator and denominator before computing percentages.

### Pearson Correlation (Equity Index Tasks)

For N monthly index levels from `level_start_date` to `level_end_date` inclusive:

1. Compute N-1 monthly simple returns: return_i = (level_{i+1} - level_i) / level_i.
2. For each pair of indices, compute Pearson correlation of their paired return vectors.
3. Round to 3 decimal places.
4. Identify extreme pairs by scanning all pairwise correlations.

The number of return observations is N-1. For a 12-month window starting 2025-05-30 ending 2026-04-30, you get 12 levels and 11 return observations.

### HY Reduction (Risk Rebalance Tasks)

- **Pre-trade HY allocation pct** = sum of HY-rated holding MVs / total portfolio MV * 100.
- **Post-trade HY allocation pct** = similar calculation after removing sold HY positions and adding any new HY buys.
- **HY reduction pct points** = pre-trade HY pct - post-trade HY pct.

## Decision Rules

### Watchlist Avoidance

An issuer on the environment's `/api/issuers` watchlist (`"watchlist": true`) must never be purchased. If the portfolio already holds a watchlisted instrument, prefer to sell it. Use the issuer endpoint to determine watchlist status; do not rely solely on bond-level theme tags like `WATCHLIST_RISK`.

In rotation-style tasks: sell watchlisted holdings first, then fund eligible non-watchlist candidates. The `buys_avoid_watchlist` flag should be `true` when every BUY targets a non-watchlist issuer.

### HY Cap and Duration Bands

Every credit portfolio has a HY allocation cap. Post-trade HY allocation must stay at or below this cap. Duration must stay within the CIO range. When a task requests HY reduction of at least N percentage points, verify the reduction meets or exceeds N.

Do not fabricate the exact cap or band numbers. The environment records (constraint policies, portfolio objectives) supply the boundaries. If the request itself names specific targets (e.g., "minimum 4.0 pct points HY reduction"), use those as the test thresholds.

### Issuer and Subsector Diversification

When selecting bonds for a trade package:

- Do not pick two bonds from the same issuer (`issuer_id` must be distinct across selections).
- Prefer bonds from different subsectors to spread exposure.
- Within a 2-ticket package, having different issuer_ids and different subsectors passes both checks.

### Energy-Linked Bond Selection

For energy-credit tasks, filter bonds to `"energy_linked": true`. Prefer bonds whose `recommended_theme_tags` align with the portfolio's `preferred_exposures` (e.g., LNG_EXPORTS, GAS_DEMAND). Cross-reference with energy market signals: a positive LNG signal favors LNG-linked bonds. Avoid bonds from watchlisted issuers even if energy-linked.

### Allocation View Derivation

To determine the active view (UW, N, OW) for an opportunity set:

1. Fetch the prior view from `/api/allocation/prior-views` for the matching `previous_quarter` to `quarter` pair.
2. Fetch the current macro signal score and rationale_code from `/api/macro-signals` for the same `quarter`.
3. Determine the view:
   - Strong positive score (>0.3): OW
   - Strong negative score (<-0.3): UW
   - Moderate score between -0.3 and 0.3: N
4. Determine change: compare the new view to the prior view. If the direction changes (N to OW, UW to N, etc.), it is UP or DOWN accordingly. If the same, it is UNCHANGED.
5. Assign conviction: |score| >= 0.5 to HIGH; |score| >= 0.3 to MEDIUM; otherwise LOW.
6. Use the `rationale_code` from the macro signal directly.

### Risk Overlay Selection

Look at the dominant macro signal direction across the requested opportunity sets. The overlay code and primary action form a linked pair:

- `DURATION_QUALITY_TILT` + `tilt_to_duration_quality` (when duration/rate-cut signals dominate)
- `CREDIT_RISK_REDUCTION` + `trim_credit_beta` (when HY or credit-spread risk signals dominate)
- `EQUITY_BETA_EXTENSION` + `add_cyclical_equity_beta` (when growth-improvement signals dominate)
- `CURRENCY_DEFENSIVE_HEDGE` + `add_currency_hedge` (when dollar-defensive or currency-risk signals dominate)
- `NO_OVERLAY` + `hold_policy_weights` (when signals are broadly neutral)

The `rationale_codes` list should include the top priority codes from the dominant signals, ordered by business priority (highest first).

## Output Formatting Rules

### Precision

Round numeric outputs to the precision declared in the answer template:
- Notional amounts (USD millions): 1 decimal place.
- Percentages, duration: 2 decimal places.
- Correlations, signal_scores: 3 decimal places.

### Sort Order

- Trade lists: BUY tickets after SELL tickets when both exist; then sort ascending by `instrument_id` within each action group.
- Index lists and pair_ids: ascending alphabetical order.
- Allocation views: preserve the order specified in the request's focus_opportunity_sets list.
- Rationale codes in risk overlay: business priority order, highest priority first.

### Enum Strictness

Every enumerated field has a fixed set of allowed values declared in the answer template. Never fabricate a value outside the allowed set. Always use values exactly as spelled in the template or in the environment data. When mapping environment-derived concepts (theme tags, rationale codes) to template enums, use the exact string match found in the environment.

### Schema Fidelity

Match every required key, every array length, every ordering rule, and every field type in the answer template. If the template says `"required_value": "PF-EN-ALTA"`, output that exact string. If it says `"length": 2`, output exactly 2 items. Omit no required keys.
