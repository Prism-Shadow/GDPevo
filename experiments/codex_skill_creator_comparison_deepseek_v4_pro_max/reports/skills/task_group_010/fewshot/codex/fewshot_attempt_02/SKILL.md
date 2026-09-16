---
name: asteria-portfolio
description: Institutional portfolio workflows for the Asteria Investment Office shared environment. Use when preparing JSON answer files for Asteria credit trade strategies, international equity correlation reviews, CIO allocation view refreshes, fixed-income risk rebalances, or multi-asset committee decisions. Covers API-driven data fetching from the task environment, Pearson correlation computations, signal-to-view mapping, constraint checks, and strict JSON output contracts. Do not use for generic portfolio work or non-Asteria domains.
---

# Asteria Portfolio

## Core rules

Apply these on every Asteria task, regardless of task type.

### Environment-first precedence

Always fetch current records from the task-environment API before making decisions. Local payloads (desk requests, meeting memos, committee packets) are intake context and may contain stale marks, preferences, or pre-reconciled snapshots. When a local value conflicts with the current environment, default to the environment value and set `data_precedence` to `current_environment_over_stale_payload` where the output contract requires it.

### JSON output contract

Every task provides an `input/payloads/answer_template.json` that declares the required output shape: top-level keys, field types, enum allowed values, numeric precisions, list lengths, and sort orders. Read the template first and conform to it exactly. Do not add extra fields, skip required fields, or change precision.

### Rounding by template precision

The answer template declares precision per numeric field. Use the declared precision digits; round with Python `round(value, ndigits)` or equivalent. Do not hard-code a single precision across fields.

### Sorting conventions

When the answer template declares an ordering, follow it:
- Sort instrument IDs and index IDs in **ascending alphabetical order**.
- Sort trades with **SELL before BUY**, then ascending by instrument_id within each action.
- Sort list items by the explicit order declared in the template (e.g., the request payload's `focus_opportunity_sets` order).
- Sort pair ids inside correlation pair objects alphabetically.

### Watchlist rule

Always cross-reference every BUY candidate against the issuer watchlist (`/api/issuers` : `watchlist` field). Never propose buying a watchlisted issuer. When the task requires sells, include watchlisted holdings in the sell list.

## Workflow

For any Asteria task, read these in order before computing output:

1. **Read the prompt** — identify the task type and portfolio ID.
2. **Read `input/payloads/answer_template.json`** — memorize the output contract, enums, precisions, and sort orders.
3. **Read any intake payloads** (desk request, review request, allocation request, meeting memo, committee request) — extract the request-specific parameters (portfolio ID, date windows, focus sets, preferences). Note stale values to discard.
4. **Fetch current environment data** from the API endpoints needed for the task type.
5. **Apply computations and constraints** (see references).
6. **Write the JSON answer** conforming to the template exactly.

### Task-type specific steps

**Credit trade strategy** (train_001 pattern): fetch portfolio holdings, bond universe, issuers, energy market signals. Select eligible BUY candidates (energy-linked, non-watchlist, within HY and duration constraints), compute post-trade metrics, fill constraint checks and sales positioning. See [api.md](references/api.md) and [computation.md](references/computation.md).

**International equity correlation review** (train_002 pattern): fetch portfolio holdings, indices, index levels from `/api/index-levels`, and policies. Compute Pearson correlations of monthly simple returns over the review window. Identify extreme pairs, check China-Asia concentration, propose diversification candidates and sleeve actions. See [computation.md](references/computation.md).

**CIO allocation view refresh** (train_003 pattern): fetch opportunity sets, prior views, macro signals from `/api/macro-signals`, and policies. Map signal scores to views using policy thresholds, determine view changes vs prior quarter, map conviction from absolute scores, choose risk overlay. See [api.md](references/api.md) and [computation.md](references/computation.md).

**Fixed-income risk rebalance** (train_004 pattern): fetch portfolio holdings, bond universe, issuers, policies. Prioritize selling HY and watchlist holdings; fund purchases with IG non-watchlist candidates meeting duration targets. Compute post-trade metrics and check all constraint flags. See [api.md](references/api.md) and [computation.md](references/computation.md).

**Multi-asset committee** (train_005 pattern): combine correlation analysis on specified index pairs with allocation view signals. Build correlation summary, target sleeve actions, and allocation views table. Set rebalance trigger, concentration flag, and next step. See [computation.md](references/computation.md).

## API reference

See [api.md](references/api.md) for the complete endpoint catalog with response field definitions.

## Enum reference

See [enums.md](references/enums.md) for all allowed values across answer templates and API responses.

## Computation reference

See [computation.md](references/computation.md) for Pearson correlation, signal-to-view mapping, constraint checks, and rounding.

## Policy reference

See [policies.md](references/policies.md) for constraint thresholds, signal mapping rules, and overlay selection guidance.
