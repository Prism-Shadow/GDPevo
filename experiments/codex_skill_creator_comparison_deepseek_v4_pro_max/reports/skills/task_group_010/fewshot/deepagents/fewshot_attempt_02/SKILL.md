---
name: asteria-portfolio-risk
description: "Institutional portfolio risk, credit strategy, equity correlation, and asset-allocation workflows for the Asteria Investment Office shared API environment. Use when the task involves Asteria portfolios, credit desk decisions, equity correlation reviews, fixed-income rebalance rotations, CIO allocation views, or investment-committee decision files. The environment exposes current portfolio holdings, bond and issuer records, monthly index levels, allocation opportunity sets, prior views, macro signals, and policy thresholds. Trigger on prompts that reference Asteria, PF-..., BND_... or IDX_... identifiers, credit/correlation/allocation/committee/rebalance workflows, or any structured JSON output template matching Asteria schema conventions."
license: MIT
compatibility: designed for deepagents-code
---

# Asteria Portfolio Risk

## Core workflow

1. **Read the task prompt and local payloads** — identify the portfolio, template, and decision context.
2. **Fetch current state from the Asteria API** — always use the live environment over stale local data.
3. **Reconcile conflicting records** — when a local payload disagrees with the API, the API wins unless the task explicitly says otherwise.
4. **Compute required metrics** using the bundled scripts where applicable.
5. **Apply policy thresholds** from `/api/policies` to evaluate constraint passes.
6. **Fill the JSON template exactly** — keep numeric precision, field ordering, and enum values as declared.

## API base

```
http://task-env:9010
```

See [references/api_endpoints.md](references/api_endpoints.md) for the full endpoint catalog and data shapes. See [references/policies.md](references/policies.md) for threshold definitions and allocation mapping rules.

## Data precedence

When a local payload contains stale marks (older date, worksheet snapshot, desk note about unreconciled data), **always prefer the current API responses**. The `data_precedence` field in some templates captures this choice as `current_environment_over_stale_payload`. Only use `local_payload_over_current_environment` when the task explicitly instructs it.

## Scripts

### Correlation computation

Use `scripts/compute_correlation.py` to compute Pearson correlations from monthly index-level time series. The script accepts two columns of levels and returns a single correlation rounded to 3 decimals.

```bash
python3 scripts/compute_correlation.py --levels-a "100,101,102,..." --levels-b "200,201,203,..."
```

### Portfolio fixed-income metrics

Use `scripts/compute_portfolio_metrics.py` to compute weighted YTM, weighted duration, HY allocation percentage, and total market value from holdings and bond universe data.

```bash
python3 scripts/compute_portfolio_metrics.py \
  --holdings-json '<holdings array>' \
  --bonds-json '<bonds array>' \
  --issuers-json '<issuers array>'
```

The script reads JSON arrays from arguments, combines them, and outputs post-trade metrics.

### Allocation view resolution

Use `scripts/resolve_allocation_view.py` to determine the active view (OW/N/UW), view change versus prior quarter, conviction level, and rationale code from signal scores and policy thresholds.

```bash
python3 scripts/resolve_allocation_view.py \
  --signal-score 0.48 \
  --prior-view N \
  --policy-json '<allocation mapping policy>'
```

## Constraint checking

After computing post-trade metrics, compare against the relevant policy from `/api/policies`. Each portfolio's `constraint_policy_id` determines which policy section applies:

- `POL_CREDIT_DEFAULT` — standard credit constraints (HY cap 20%, duration band 3.0–5.0, issuer concentration 12%)
- `POL_CREDIT_RISK_REDUCTION` — same constraints plus a target HY reduction (≥4.0 pp reduction)
- `POL_CORRELATION_DEFAULT` — correlation high threshold 0.8, low threshold 0.2
- `POL_MULTI_ASSET_DEFAULT` — composites credit, correlation, and allocation mapping
- `POL_MULTI_ASSET_RISK` — composites credit risk reduction and correlation; escalation at two or more material exceptions

## Allocation mapping

Signal scores from `/api/macro-signals` map to views through the thresholds in `/api/policies` → `allocation_mapping`:

- Score ≥ 0.35 → `OW`
- Score ≤ -0.35 → `UW`
- Between → `N`

Conviction is determined from signal score absolute value:
- `|score|` ≥ 0.70 → `HIGH`
- 0.35 ≤ `|score|` < 0.70 → `MEDIUM`
- `|score|` < 0.35 → `LOW`

Change versus prior quarter: compare the current quarter's view to the prior quarter's view from `/api/allocation/prior-views`. If view rank (OW=1, N=0, UW=-1) increases → `UP`, decreases → `DOWN`, unchanged → `UNCHANGED`.

## Index correlation reviews

When computing pairwise correlations from monthly index levels:

1. Fetch levels for each index in the universe from `/api/index-levels/{index_id}`.
2. For each pair, extract the overlapping date range, compute monthly simple returns: `(level_t / level_{t-1}) - 1`.
3. Compute Pearson correlation from the two return series.
4. Identify highest-positive and lowest correlations among all pairs.
5. The number of return observations is one fewer than the number of level observations (because the first level produces no return).

## Common enum values

See [references/enum_values.md](references/enum_values.md) for the full set of allowed values used across Asteria JSON templates.
