---
name: asteria-investment-office-json
description: Build Asteria Investment Office portfolio decision JSON from the shared Asteria environment and local answer templates. Use when Codex is asked to prepare Asteria PF-* outputs such as energy-credit trade packages, international equity correlation reviews, active allocation view refreshes, fixed-income risk rotations, or committee decision files that require current portfolio records, policy thresholds, index levels, macro signals, instruments, issuers, and strict JSON schemas.
---

# Asteria Investment Office JSON

## Core Workflow

1. Read the prompt, `input/payloads/answer_template.json`, and every local request payload. Treat the template as the output contract for required keys, enums, precision, list length, and ordering.
2. Read `environment_access.md` if present for the base URL and credentials, then fetch the current environment records. Use the environment as the book of record for portfolios, holdings, policies, market data, security master data, index levels, prior views, and macro signals.
3. Use local payloads for request scope only: target portfolio, requested universe, ticket counts, funding style, review windows, allowed output choices, and desk or committee context. If local notes conflict with the environment or call themselves stale, prefer the environment. When the template includes a precedence field, select the enum that represents current environment over stale local data.
4. For endpoint selection, calculations, and task-family rules, read [Asteria workflows](references/asteria-workflows.md).
5. Return only the requested JSON object. Do not include narrative text, markdown fences, extra keys, or values carried over from examples or prior runs.

## Task Families

### Credit Trade Packages

For BUY-only packages, apply the requested ticket count, notional total, split rule, and funding treatment exactly. Filter candidates by the request scope, current security-master fields, issuer watchlist status, and active credit policy. Choose instruments that improve the requested carry or income objective while passing high-yield, duration, issuer, subsector, and watchlist constraints.

For risk rotations, sell current pressure holdings first when they are high-yield, watchlisted, or otherwise named as risk exceptions. Fund buys from current eligible candidates, avoid new watchlist exposure unless explicitly requested, and keep net notional consistent with the memo.

### Correlation Reviews

Fetch monthly levels for the requested index ids and window. Convert consecutive levels to monthly simple returns, compute Pearson correlations, and round only at output time. Sort ids inside each pair alphabetically. Use the template and policy thresholds to identify concentration pairs, diversifier pairs, flags, and sleeve actions.

### Allocation View Refreshes

Join the opportunity-set taxonomy, prior views, macro signals, and current policy mapping for the requested quarter. Map signal scores to active views and convictions from the policy thresholds, derive `change` by comparing current and prior view ranks, and use the macro signal rationale code. Preserve the opportunity-set order requested by the local payload or template.

### Committee Decision Files

Compose the relevant sub-workflows rather than shortcutting: compute correlation findings from live index levels, compute allocation views from current signals and prior views, then derive target actions, rebalance triggers, concentration flags, and next steps from the policy result and committee objective.

## Output Discipline

Use the template's exact field names and allowed enum values. Apply all specified sorting rules before returning JSON. Format numeric literals to the declared precision where the output text can preserve it, but keep them as JSON numbers, not strings.

Never hard-code dates, portfolio metrics, instrument ids, policy ids, correlations, views, actions, or rationale codes from examples. Recompute them from the live environment and the current task payload.
