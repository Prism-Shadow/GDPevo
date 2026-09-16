---
name: asteria-json-workflows
description: Solve Asteria Investment Office portfolio JSON tasks by using the shared task environment as the source of truth, computing credit trade packages, fixed-income risk rotations, international equity correlation reviews, allocation views, and committee summaries, and returning only exact JSON that matches the provided answer template. Use when the user mentions Asteria, a PF- portfolio request, a current portfolio record, energy-credit trades, credit-risk rebalances, correlation reviews, allocation memos, committee packets, or any compact JSON answer built from the Asteria task environment, even if the prompt does not say Asteria explicitly.
---

# Asteria JSON Workflows

Use this skill for Asteria portfolio tasks that end in strict JSON.

## Workflow

1. Read the task prompt, local payloads, and `answer_template.json` together.
2. Treat the shared Asteria API as the book of record.
3. Ignore stale snapshots or worksheet notes when they conflict with current API data.
4. Match the task to one of the common Asteria patterns below.
5. Fill only the fields required by the template.
6. Preserve required key order, list order, and numeric precision.
7. Return JSON only.

## Shared data rules

- Use current API data for holdings, bonds, issuers, market signals, index levels, opportunity sets, prior views, and macro signals.
- Do not invent policy IDs, thresholds, or classifications when the task or environment exposes them.
- When local payload notes conflict with the live service, trust the live service.
- Round values exactly to the template precision.

## Fixed-income and energy-credit tasks

- Start from current holdings.
- Prefer eligible current candidates with clean issuer and watchlist status.
- Avoid watchlisted issuers unless the prompt explicitly allows them.
- Keep selected buys diversified across issuer and subsector unless the task says otherwise.
- For exact-ticket packages, split notional exactly as requested.
- For rotations, sell the pressure points first, then fund replacements that keep the book inside the requested risk band.
- Check the final package with the bundled helper before writing the answer.

Use [scripts/asteria_tools.py](scripts/asteria_tools.py) to:

- enumerate equal-size energy-credit buy pairs
- compute post-trade market value, HY share, duration, yield, and watchlist exposure

## Correlation review tasks

- Compute Pearson correlations from monthly simple returns over the requested level window.
- Sort pair identifiers alphabetically.
- Report the strongest positive pair and the weakest pair exactly as the template asks.
- When the memo asks for concentration or diversification interpretation, follow the concern codes and portfolio context, not only the raw max pair.

Use the helper script to calculate the pairwise correlation matrix from `/api/index-levels`.

## Allocation-view tasks

- Pull the requested opportunity sets in the order given by the prompt.
- Pull prior-quarter views and macro signals from the live service.
- Map signal score to view with the default thresholds unless the prompt gives a different rule:
  - `score >= 0.300` -> `OW`
  - `score <= -0.300` -> `UW`
  - otherwise `N`
- Map conviction with the same score:
  - `abs(score) >= 0.650` -> `HIGH`
  - `abs(score) >= 0.300` -> `MEDIUM`
  - otherwise `LOW`
- Set `change` by comparing the derived view to the prior view with the order `UW < N < OW`.
- Use the rationale code that matches the active macro driver.

## Output discipline

- Emit only the requested JSON object.
- Do not add commentary, markdown, or code fences.
- Do not add extra keys.
- Keep arrays in the order the template requires.
- Recheck the final object against the template before returning it.
