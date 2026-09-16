---
name: asteria-investment-office-json
description: Generate strict JSON answers for Asteria Investment Office portfolio tasks by reconciling the local memo with the live shared environment. Use this whenever the prompt asks for credit trade packages, fixed-income rotations, correlation reviews, allocation views, committee memos, or any response built from current Asteria portfolio, holdings, bond, index, macro, or policy records, especially when the prompt mentions stale worksheets or a current book of record.
---

# Asteria Investment Office JSON

Use this skill for Asteria tasks that require a schema-locked JSON object built from live portfolio data. The local payloads are context, not the source of truth.

## Operating rules

- Read the prompt, all payload files, and the answer template first.
- Treat any stale snapshot or memo in the payload as advisory only.
- Use the live Asteria service as the book of record.
- If payload data and live data conflict, follow the live data and reflect that in any precedence field the template asks for.
- Return only the JSON object requested by the template. No prose, no markdown, no code fences.
- Match every required key, list order, and numeric precision exactly.

## Live data map

See `references/environment.md` for the endpoint list and request notes.

Use the live service this way:

- Portfolio and credit tasks: read portfolios, holdings, bond universe, issuers, energy market notes, and policies.
- Correlation tasks: read index metadata, index level history, and policies.
- Allocation and committee tasks: read opportunity-set taxonomy, prior views, macro signals, and policies.

## Decision workflow

1. Identify the portfolio id, task family, required fields, and ordering rules from the template.
2. Pull the live records needed for that task family.
3. Reconcile the local memo against live data.
4. Compute the requested output from the live records.
5. Draft the JSON to the exact schema.
6. Validate structure, ordering, and rounding before answering.

## Credit and rotation tasks

When the task asks for a trade package, rotation, or candidate selection:

- Use current holdings, the live bond universe, issuer status, and the policy thresholds.
- Prefer candidates marked eligible in the live universe.
- Avoid watchlisted or otherwise flagged issuers unless the prompt explicitly asks for them or the policy allows them for the objective.
- Preserve the requested constraint envelope rather than chasing headline carry.
- Recompute any post-trade totals, HY share, duration, and exposure fields from the proposed trades plus current holdings.
- If the prompt asks for a client-facing pitch angle, align the theme to the dominant live macro signal, not the stale worksheet.

## Correlation tasks

When the task asks for index correlations or diversification actions:

- Use the requested index ids from the prompt.
- Pull the full monthly level series for each index.
- Convert levels to monthly simple returns before computing correlations.
- Use Pearson correlation over the requested window.
- Sort pair ids alphabetically.
- Use the live correlation policy thresholds when flagging concentration and diversification candidates.

## Allocation and committee tasks

When the task asks for active views or committee decisions:

- Pull the opportunity-set taxonomy, prior views, macro signals, and allocation policy.
- Keep the output rows in the order required by the request payload or template.
- Map signal scores to views with the live policy thresholds.
- Use the absolute signal score to set conviction.
- Set change relative to the prior quarter or prior view record.
- Choose rationale codes that match the dominant live driver, not a generic label.
- Keep any overlay or next-step field consistent with the same signal story.

## Calculations

- Simple return = `level_t / level_(t-1) - 1`
- Correlation = Pearson correlation of overlapping monthly simple returns
- Round only after the final calculation so intermediate values stay accurate

## Policy use

If `/api/policies` is available, use it before finalizing:

- Credit policies give the live HY cap, duration band, issuer concentration limit, and required reduction target.
- Correlation policy gives the window and the concentration thresholds.
- Allocation policy gives the view and conviction score cutoffs.

Do not hard-code those numbers unless the task itself supplies them as authoritative.

## Final check

Before responding, verify:

- The JSON matches the template exactly.
- No extra keys are present.
- Lists are sorted as required.
- Dates use the requested format.
- Numeric fields use the requested precision.
- The response contains only JSON.
