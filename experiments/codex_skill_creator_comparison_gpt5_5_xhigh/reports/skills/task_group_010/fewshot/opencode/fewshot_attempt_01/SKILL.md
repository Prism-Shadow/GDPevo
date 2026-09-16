---
name: asteria-portfolio-json
description: Solve Asteria Investment Office tasks that require portfolio, credit-risk, correlation, allocation-view, or committee JSON answers from the shared Asteria environment. Use this skill whenever the prompt mentions Asteria, portfolio IDs, answer_template.json, energy-credit trades, fixed-income rotations, watchlist or high-yield limits, Pearson index correlations, macro signals, active allocation views, CIO refreshes, or committee decision files.
---

# Asteria Portfolio JSON

Use this skill to prepare compact JSON answers for Asteria Investment Office tasks. The key pattern is that local payload files define the assignment and output contract, while the shared Asteria environment is the current book of record.

## Workflow

1. Read the task prompt, every JSON payload under `input/payloads/`, and especially `input/payloads/answer_template.json`.
2. Read `environment_access.md` to get the base URL and available endpoints. Use the environment for current portfolios, holdings, instruments, issuers, index levels, policies, prior views, and macro signals.
3. Treat local payloads as request context. When a payload says a snapshot, note, worksheet, memo, or shortlist is stale, reconcile it to the environment before deciding.
4. Build the answer from the template, not from memory. Match required keys, enum values, list lengths, ordering rules, and numeric precision.
5. Return only the JSON object when the task asks for JSON only.

## Helper

Use the bundled helper when the task matches one of the observed Asteria workflows:

```bash
python <skill>/scripts/asteria_helper.py solve --task-dir input --env environment_access.md
```

The helper dynamically fetches current environment records and can draft answers for:

- Energy-linked credit buy packages.
- Fixed-income risk-reduction rotations.
- International equity correlation reviews.
- Active allocation view refreshes.
- Committee packages combining correlation findings and allocation views.

Use its output as a computed draft, then check it against the prompt and template before final response. For methods, formulas, and manual fallback rules, read [references/asteria-method.md](references/asteria-method.md).

## Validation Checklist

- Use environment `as_of_date` for current records.
- Calculate fixed-income weighted metrics from post-trade notionals: market value, high-yield percent, duration, yield, and watchlist exposure.
- Calculate correlations from monthly simple returns, not from raw index levels.
- Sort pair IDs alphabetically inside each pair.
- Preserve template-required row ordering, such as request order for allocation rows or action/instrument order for trades.
- Round only at the final field precision requested by the template.
- Do not include explanation outside JSON unless the user explicitly asks for it.
