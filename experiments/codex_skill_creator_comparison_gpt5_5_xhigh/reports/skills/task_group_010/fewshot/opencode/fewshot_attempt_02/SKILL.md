---
name: asteria-portfolio-json
description: Solve Asteria Investment Office portfolio prompts that require a compact JSON answer from live environment data. Use whenever the prompt mentions Asteria, a portfolio id, a schema/template payload, stale worksheet notes, credit rotations, correlation reviews, allocation views, or a committee memo that must reconcile local context with current API records.
---

# Asteria Portfolio JSON

Use the live Asteria API as the book of record. Treat local payloads as the request contract and any stale worksheet notes as hints only.

## First pass

1. Read the prompt and `input/payloads/answer_template.json`.
2. Read every local payload under `input/payloads/`.
3. Read `environment_access.md` if it is present. Use its `base_url` and only call endpoints that appear in its `allowed_endpoints`.
4. Use [scripts/asteria_toolkit.py](scripts/asteria_toolkit.py) when you need repeatable fetches or calculations.

## Output contract

- Match the template exactly.
- Preserve field order and list ordering from the template.
- Round numeric fields to the precision requested by the template.
- Return JSON only. No markdown, prose, or code fences.
- If the template asks for lineage fields like `policy_id`, take them from the current records or the task payload; do not invent them.
- Do not invent identifiers. If a required id is not in the live API, use the task payload or stop and inspect the current data again.

## Task patterns

See [references/asteria_rules.md](references/asteria_rules.md) for the reusable rules for:

- fixed-income trade packages and post-trade risk metrics
- correlation reviews and concentration flags
- allocation-view rows and conviction scoring
- committee memos that combine correlation and allocation outputs

## Common workflow

- Start from the current API snapshot, not the stale worksheet.
- Use the template to decide the output shape before you decide the answer.
- When a task asks for a portfolio action, filter first for explicit constraints, then rank the remaining candidates by current carry, diversification, and fit with the memo.
- When a task asks for correlations, compute them from monthly simple returns on the requested level window.
- When a task asks for allocation views, derive the row order from the request payload and join prior views with current macro signals.

## Helper script

Use [scripts/asteria_toolkit.py](scripts/asteria_toolkit.py) to:

- discover the base URL from `environment_access.md` or `ASTERIA_BASE_URL`
- fetch Asteria JSON endpoints
- compute pairwise correlations
- rank eligible bond candidates
- apply trades and recompute post-trade metrics
