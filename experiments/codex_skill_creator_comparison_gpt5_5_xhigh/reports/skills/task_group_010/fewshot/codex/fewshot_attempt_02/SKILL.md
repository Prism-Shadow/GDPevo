---
name: skill
description: Produce strict JSON answers for Asteria Investment Office portfolio tasks using the live portfolio, bond, index, allocation, prior-view, and macro-signal records. Use when solving staged requests for energy-credit trades, fixed-income rotations, correlation reviews, allocation views, or committee decision files that may include stale local notes.
---

# Asteria Portfolio JSON

## Workflow

1. Read the request payload and answer template first.
2. Treat current Asteria environment records as the source of truth. Use local payloads and memos only as task framing when they conflict with live records.
3. Read only the needed endpoint families. See [workflow notes](references/workflow.md) for the endpoint map and calculation rules.
4. Match the template exactly. Keep required keys, enum values, ordering, and numeric precision unchanged.
5. Use the current environment `as_of_date` and policy identifiers, not request dates, memo dates, or stale worksheet snapshots.
6. Return only the JSON object.

## Output Checks

- Preserve the requested order for rows, pairs, trades, and sleeves.
- Round numeric fields to the precision declared by the template.
- Keep ids alphabetized when the template asks for alphabetical ordering.
- Do not add commentary, markdown, or extra keys.
- Do not copy stale sample values into the answer.

## Task Families

- Credit trade packages and rotations: use current holdings, bond metadata, issuer watchlist status, and portfolio constraints to select eligible names and size trades.
- Correlation reviews: compute Pearson correlations from monthly simple returns over the requested window, then identify the strongest positive pair and the weakest pair in the stated universe.
- Allocation views: combine current macro signal scores with prior views to set `view`, `change`, `conviction`, and `rationale_code`, plus any required overlay fields.
- Committee summaries: combine the correlation and allocation outputs, then choose the trigger and next step that match the concentration story.
