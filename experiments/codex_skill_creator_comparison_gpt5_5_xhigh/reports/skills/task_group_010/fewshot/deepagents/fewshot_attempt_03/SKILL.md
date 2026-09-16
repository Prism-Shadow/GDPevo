---
name: asteria-investment-office
description: Solve Asteria Investment Office JSON tasks that require using the shared environment as the current book of record for portfolio holdings, fixed-income trades, equity-index correlations, active allocation views, macro signals, policies, and committee/risk outputs. Use when prompts mention Asteria portfolios, PF-* ids, energy credit, fixed-income risk rebalance, international equity correlation, allocation view refreshes, or committee decision JSON.
---

# Asteria Investment Office

## Core Workflow

1. Read the user prompt, every local payload JSON, and the answer template before calculating. Treat the template as the output contract: required keys, enum values, ordering rules, and rounding precision all come from it.
2. Read `environment_access.md` in the task workspace and use only the listed Asteria environment endpoints. Current environment records override local worksheet, memo, or stale payload values whenever the prompt says to use the shared environment as the book of record.
3. Run the helper at [scripts/asteria_env_helper.py](scripts/asteria_env_helper.py) when useful:

```bash
python scripts/asteria_env_helper.py analyze input
```

Pass the task input directory, task directory, or current directory. The helper prints a JSON fact pack with fetched portfolio data, enriched holdings, fixed-income metrics, pairwise correlations, allocation signal rows, and candidate bond facts. Use it as calculation support, not as the final answer.
4. Build the final JSON manually against the template. Return only JSON when requested; do not include commentary.

## Environment Use

Fetch the current portfolio summary, holdings, bond master, issuer master, market/energy signals, index metadata, index levels, opportunity-set taxonomy, prior views, and macro signals as needed. If the prompt or access file exposes a policy endpoint, fetch it for thresholds and policy ids. Otherwise use thresholds stated in the payload/template and the portfolio `constraint_policy_id` as lineage when no better policy record is available.

Join fixed-income holdings to bond records by `instrument_id` and issuer records by `issuer_id`. Join equity holdings to index records by `index_id`. Use holding `quantity_usd_m` as market value/notional unless a task explicitly provides a different price convention.

## Fixed-Income Tasks

For energy-credit BUY packages:

- Restrict to current `candidate` bonds that match the requested sector/theme, such as `energy_linked` bonds for energy sleeves.
- Exclude issuers whose current issuer record is watchlisted when the output checks watchlist avoidance or the prompt warns about watchlist yield traps.
- Respect exact ticket count, action type, total notional, equal split, and sort order from the payload/template.
- Prefer positive-current-theme candidates that improve carry while keeping post-trade HY allocation and duration inside constraints. When diversification checks are required, avoid selecting duplicate issuers and duplicate subsectors inside the selected package.
- Compute post-trade market value as current market value plus buys minus sells. Compute HY allocation, modified duration, and yield to maturity as notional-weighted values using current holdings plus proposed trades.
- Set sales positioning from the local client context and the dominant current theme. Use `current_environment_over_stale_payload` when local marks or worksheets conflict with environment records.

For fixed-income risk-reduction rotations:

- Sell current watchlist holdings first. Then sell additional HY pressure names only as needed to meet HY cap/reduction targets, preferring to retain the better non-watchlist carry when constraints still pass.
- Buy only current eligible non-watchlist candidates, favoring IG quality, current memo shortlists, diversification, and enough duration to keep the post-trade portfolio inside the CIO range.
- Fund buys with sells unless the request explicitly says new allocation. Verify post-trade HY allocation, duration, HY reduction in percentage points, and residual watchlist exposure.
- Sort trades exactly as the template specifies, commonly SELL before BUY and then `instrument_id` ascending.

## Correlation Tasks

Use monthly simple returns from consecutive index levels over the requested level window:

```text
return_t = level_t / level_(t-1) - 1
```

Calculate Pearson correlations on aligned monthly return vectors. The number of return observations is one less than the number of monthly levels in the inclusive window. Sort each pair id alphabetically.

For extreme-pair outputs, evaluate all requested index pairs. `highest_positive` or `highest_concentration` is the largest correlation unless the prompt narrows the concentration pair set. `lowest` or `best_diversifier` is the smallest correlation. For China/Asia concentration flags, use the policy threshold when available; if no threshold is exposed, treat correlations at or above 0.90 as high only when the prompt asks for a policy-style breach flag.

Diversification candidates should come from the template/payload allowed set. Prefer candidates with the lowest correlation to the concentration driver, especially China or broad EM dependence, and preserve required ordering.

## Allocation View Tasks

Use the opportunity-set taxonomy for `asset_class`. Use prior views matching the requested target and prior quarter as the prior state. Use macro signals matching the requested quarter for current signal score and rationale code.

Derive current active views from signal score:

- `OW` for score >= 0.30
- `UW` for score <= -0.30
- `N` otherwise

Derive conviction from absolute score:

- `HIGH` for abs(score) >= 0.70
- `MEDIUM` for abs(score) >= 0.30
- `LOW` otherwise

Compare current view to prior view with `UW < N < OW`: higher is `UP`, lower is `DOWN`, equal is `UNCHANGED`. Round signal scores to the template precision.

For risk overlays, connect the strongest requested signals to the portfolio objective. Prefer duration/quality overlays when duration support is positive and credit/China risk is negative, credit-risk reduction when HY or watchlist pressure dominates, currency hedges when USD/dollar defensive risk is central, equity beta extension when growth signals are broadly positive without concentration breach, and no overlay when signals are balanced. Order rationale codes by business priority from the prompt and constraints.

## Committee Outputs

When a committee task links correlation findings to allocation views:

- Use the requested correlation index ids, not every available index, unless the template asks for a broader universe.
- Map `OW` equity views to `add`, `UW` to `trim`, and `N` to `hold` unless the prompt asks for a hedge/monitor/rotate interpretation. For USD or defensive currency sleeves, a downgrade from `OW` toward `N` commonly maps to `hedge` when the committee request is about risk concentration.
- Set the portfolio concentration flag from the correlation breach/concentration finding.
- Choose `approve_with_monitoring` when proposed actions address a concentration finding and all computed constraints pass; choose a stricter next step only when required checks fail or the prompt asks for deferral.

## Output Discipline

Use environment dates for `as_of_date`. Preserve template ordering rules. Round only at the final field precision. Do not include fields not requested by the template. Do not reuse stale local quantities or marks when current environment records are available.
