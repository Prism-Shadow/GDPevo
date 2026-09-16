---
name: asteria-portfolio-json
description: Use this skill for Asteria Investment Office tasks that require strict JSON portfolio, credit, correlation, allocation, rebalance, or committee decisions from the shared Asteria environment. Trigger when prompts mention Asteria, PF-* portfolio ids, answer_template.json, current environment records, energy-credit trades, fixed-income rotations, HY/watchlist constraints, non-US equity correlations, index levels, macro signals, active allocation views, or committee decision files.
---

# Asteria Portfolio JSON

Use this skill to produce schema-conforming JSON decisions for Asteria Investment Office tasks. These tasks are data exercises, not writing exercises: the correct answer comes from combining the local request/template with current environment records and deterministic calculations.

## Required Workflow

1. Read the user prompt, every local payload, and the answer template before calculating. Treat the template as the output contract: required keys, enum values, field order, item order, and rounding precision all come from it.
2. Read [references/asteria-workflow.md](references/asteria-workflow.md) before using environment data, computing portfolio metrics, calculating correlations, or deriving allocation views.
3. Use the shared Asteria environment as the current book of record. Local payloads often contain stale snapshots, prior-week shortlists, or desk notes; use them for scope and preferences only unless the template explicitly says otherwise.
4. Fetch current data only from endpoints documented by the task or environment access file. Do not inspect test answers, evaluator code, hidden tasks, or unrelated paths.
5. Build the answer from current records, then validate it against the template:
   - Include exactly the requested JSON object and no narrative text.
   - Preserve requested top-level key order and row order.
   - Sort pairs, instruments, sleeves, or actions exactly as the template says.
   - Round numeric fields to the declared precision after all calculations.
   - Use only enum values allowed by the template.

## Decision Discipline

For credit recommendations, compute current and post-trade market value, HY allocation, weighted duration, weighted yield, watchlist exposure, and requested pass/fail flags from holdings plus the bond and issuer masters. Prefer current eligible candidates over stale local shortlists, avoid watchlisted issuers when the request is risk-sensitive, and choose trades that satisfy the numeric constraints before optimizing carry or pitch appeal.

For correlation reviews, compute monthly simple returns from consecutive index levels over the requested level window, then calculate Pearson correlations across every requested pair. Sort index ids inside each pair alphabetically and select the requested extreme roles from the computed matrix.

For allocation views, combine current macro signals with the matching prior-view row. Derive view, conviction, rationale code, prior/current change, and risk overlay from the signal score, prior view, asset class, and request focus list.

For combined committee files, reconcile the correlation conclusion with the active allocation views. The resulting sleeve actions, rebalance trigger, concentration flag, and next step should tell the same story as the data.
