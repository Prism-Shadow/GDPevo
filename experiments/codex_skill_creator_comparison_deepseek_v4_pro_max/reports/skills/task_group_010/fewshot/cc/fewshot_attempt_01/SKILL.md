---
name: asteria-portfolio-analytics
description: Use this skill when the task involves the Asteria Investment Office environment, references portfolio ids starting with PF-, bond ids like BND_*, index ids like IDX_*, the task-env HTTP service, or asks for institutional portfolio trade strategies, correlation reviews, allocation view refreshes, or risk rebalance proposals that require a structured JSON answer conforming to a provided template.
---

# Asteria Portfolio Analytics

Use this skill when preparing institutional portfolio analytics answers using the
shared Asteria Investment Office HTTP environment. The environment is always at
`http://task-env:9010/` and requires no credentials.

Every Asteria task follows a common structure: a local request payload provides
context and preferences (some of which may be stale), the environment exposes
current portfolio, instrument, issuer, index, policy, signal, and allocation
records, and the answer must conform to a JSON template supplied in the payload.

## Workflow

Follow these steps in order. Do not skip the environment queries.

### 1. Read the local inputs

Read every file under `input/payloads/` and the task prompt. Identify:

- The portfolio id (e.g., `PF-EN-ALTA`, `PF-FI-LUMEN`) and which desk/committee
  is requesting the work.
- Any stale marks, preferences, or candidate lists in the payload — treat these
  as intake context only. The environment is the authoritative book of record.
- The answer template. Its `required` keys, enum constraints, numeric precision
  declarations, ordering rules, and allowed values are non-negotiable. The
  output must satisfy every constraint the template declares.

### 2. Query the environment

Read [references/api_endpoints.md](references/api_endpoints.md) for the full
catalog. The essential calls for most tasks are:

- `/api/portfolios` — confirm portfolio ids and constraint policy assignments.
- `/api/portfolios/{id}` — current holdings, market value, and constraints.
- `/api/instruments/bonds` — the bond universe (candidate flags, ratings,
  yields, durations, sectors, subsectors, energy-linked flags, watchlist tags).
- `/api/issuers` — issuer research, credit outlooks, and the authoritative
  watchlist field.
- `/api/policies` — constraint thresholds (HY caps, duration bands, issuer
  concentration limits, correlation thresholds, allocation mapping rules).

Depending on the task, also query:

- `/api/market/energy` — energy market signals for credit strategies.
- `/api/indices` and `/api/index-levels` — index metadata and monthly levels
  for correlation computations.
- `/api/index-levels/{index_id}` — fetch individual index level series if
  you need them one at a time.
- `/api/allocation/opportunity-sets` — taxonomy for allocation views.
- `/api/allocation/prior-views` — prior-quarter allocation views for computing
  view changes.
- `/api/macro-signals` — current macro signal scores, rationale codes, and
  drivers per opportunity set.

Always confirm the environment's `as_of_date` from any endpoint response; use
this date in the answer.

### 3. Reconcile payload with environment

The environment record is the current truth. When the payload contains stale
holdings, candidate lists, or marks that conflict with the environment:

- Prefer the environment's portfolio holdings, instrument attributes (rating,
  yield, duration, watchlist status), issuer status, index levels, signal
  scores, and policy thresholds.
- Use the payload's preferences (e.g., ticket count, notional budget, preferred
  exposures, review window dates, focus opportunity-set lists) to guide
  selection, but validate every instrument, issuer, and metric against the
  environment before committing.
- The field that encodes this reconciliation (e.g., `data_precedence`) should
  be set to `current_environment_over_stale_payload` when a conflict exists.

### 4. Perform the required computations

Read [references/computations.md](references/computations.md) for the detailed
formulas. The three families of computations are:

**Portfolio-level weighted metrics** — after any proposed trades, recompute:
- Weighted yield to maturity: Σ(quantity × YTM) / Σ(quantity)
- Weighted modified duration: Σ(quantity × duration) / Σ(quantity)
- HY allocation %: (Σ HY quantities / Σ all quantities) × 100
- Total market value: sum of all post-trade quantities

**Pearson correlation** — from monthly index levels over the requested date
window. Use the bundled script `scripts/pearson_corr.py` instead of hand-rolling
the computation. The script reads level arrays from stdin (one JSON array per
line) and outputs the Pearson r rounded to three decimals.

**Signal-to-view mapping** — using the allocation mapping policy thresholds from
`/api/policies`:
- View: OW if signal_score ≥ OW_min, UW if signal_score ≤ UW_max, N otherwise.
- Conviction: HIGH if abs(score) ≥ HIGH_abs_min, MEDIUM if ≥ MEDIUM_abs_min,
  LOW otherwise.
- Change vs prior: compare current view with prior-quarter view from
  `/api/allocation/prior-views`; if different, direction is UP (N→OW, UW→N,
  UW→OW) or DOWN (OW→N, N→UW, OW→UW). If same view, UNCHANGED.

### 5. Run constraint and policy checks

After computing post-trade or post-rebalance metrics, verify every constraint
against the applicable policy from `/api/policies`:

- **HY cap**: post_trade_hy_allocation_pct ≤ max_hy_allocation_pct
- **Duration band**: post_trade_duration_years within [low, high]
- **Issuer diversification**: no single issuer exceeds issuer_concentration_limit_pct
- **Subsector diversification**: at least subsector_min_count_for_diversified distinct subsectors
- **Watchlist avoidance**: buy-side instruments must have `watchlist: false` in
  the issuer record (check `/api/issuers`, not bond-level tags)
- **Correlation thresholds**: check high_threshold and low_threshold from policy
- **Target HY reduction**: post-trade reduction ≥ target_hy_reduction_pct points

Set boolean flags in the constraint_checks / exception_flags section of the
answer accordingly.

### 6. Fill the answer template

Produce exactly the JSON object the template requires:

- Every top-level key declared in `required` or `required_top_level_keys` must
  be present.
- Every field must use the declared type, enum, precision, ordering, and length.
- Numeric values must be rounded to the precision declared in the template
  (e.g., `"precision": 2` means two decimal places).
- Lists must be sorted per the template's ordering rule.
- String enum values must be chosen from the declared `allowed_values`.
- The portfolio id must match the one in the request.

Return only the JSON object with no narrative outside it.

### 7. Quality checks before finalizing

Before returning the answer, verify:

- The `as_of_date` matches the environment's date.
- Every bond or index id in the answer is present in the environment records.
- All constraint boolean flags are consistent with the computed metrics.
- The answer has no fields beyond what the template declares.
- Enum selections fit the task's actual situation (e.g., the `sales_positioning`
  segment and theme match the selected instruments and client context).
- The `data_precedence` or equivalent field correctly declares whether the
  environment overrode the payload.
