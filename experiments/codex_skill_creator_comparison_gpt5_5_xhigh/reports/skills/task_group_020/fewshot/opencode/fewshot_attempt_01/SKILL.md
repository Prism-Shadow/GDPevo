---
name: deal-workbench-ma-json
description: Solve M&A deal workbench tasks that require a strict JSON answer from a live task environment. Use when the prompt asks counsel to review a deal, APA/SPA terms, closing readiness, committee escalations, transition issues, consents, regulatory status, employee matters, or playbook/policy deviations using TASK_ENV_BASE_URL and an answer_template.json.
---

# Deal Workbench M&A JSON Solver

Use this skill to produce strict JSON answers for legal deal-workbench tasks. The task normally provides a prompt, an `input/payloads/answer_template.json`, and a `<TASK_ENV_BASE_URL>` placeholder for a running M&A workbench.

## Core Workflow

1. Read the user prompt and the answer template before calling the workbench.
2. Identify the deal ID, client side, transaction type, required playbook or policy, requested scope, units, rounding rules, ordering rules, and enum values.
3. Replace `<TASK_ENV_BASE_URL>` with the environment base URL from the task. If the prompt does not give it directly, use the staged environment access file for the base URL.
4. Fetch the complete deal record and all relevant endpoint families. Use `scripts/fetch_workbench.py` when useful.
5. Build a source map keyed by stable IDs: terms, playbook rules, policy thresholds, risk estimates, consents, employees, material contracts, regulatory records, diligence findings, benchmarks, documents, notes, and cap table entries.
6. Compare current draft terms against the applicable buyer, seller, or committee position. Treat missing affirmative protections as issues when the playbook, policy, or surrounding deal facts show they are needed.
7. Populate the answer template exactly. Preserve top-level keys, nested structures, enum spelling, stable IDs, ordering requirements, numeric units, and `null` where a field is not applicable or not supported.
8. Validate that the final response is valid JSON only. Use `scripts/check_answer.py` for a quick structural check against the template.

## Workbench Collection

Fetch broadly, then reason narrowly. The repeated endpoint families are:

- `/api/deals/<deal_id>`
- `/api/deals/<deal_id>/terms`
- `/api/deals/<deal_id>/documents`
- `/api/deals/<deal_id>/benchmarks`
- `/api/deals/<deal_id>/risk-estimates`
- `/api/deals/<deal_id>/cap-table`
- `/api/deals/<deal_id>/consents`
- `/api/deals/<deal_id>/employees`
- `/api/deals/<deal_id>/material-contracts`
- `/api/deals/<deal_id>/regulatory`
- `/api/deals/<deal_id>/diligence-findings`
- `/api/deals/<deal_id>/notes`
- `/api/playbooks/<playbook_id>/rules`
- `/api/policies/<policy_id>/thresholds`

If read-only SQL is available, use `POST /api/query` with token `deal-workbench-readonly` for cross-table checks and to confirm counts, totals, or missing records. Do not use SQL as a substitute for reading the named API records.

## Issue Selection

Only include issues requested by the prompt and template.

- For playbook matrices, include in-policy positions only when the template or prompt asks for a complete matrix; otherwise focus on out-of-policy, draft-below-playbook, draft-exceeds-playbook, and missing-required-term items.
- For committee escalations, include only current draft terms that breach policy or are restricted for committee approval. Exclude stale terms, in-policy terms, and non-committee distractors, but list excluded IDs if the template asks.
- For transition or separation reviews, treat draft silence as an issue when the seller position requires affirmative terms for IP transition, domain redirects, TSA scope/fees, Section 1060 allocation, transfer tax, employees, outside date, or governing law/forum.
- For closing readiness, distinguish blockers from tradeable issues. Required consents, HSR clearance, specific material-contract conditions, unresolved indemnity/escrow mechanics, and employee transition failures are usually blockers when the playbook makes them closing conditions.

Use stable source IDs from the workbench. For missing draft terms, set `source_term_ids` to an empty array and cite relevant non-term records when the schema has a separate source-record field.

## Calculations

Use the basis stated in the prompt, template, draft term, playbook, or policy. If no different basis is stated, calculate percentages from the headline purchase price or equity value in the deal record.

- Currency: integer dollars.
- Percentages: decimal percent points rounded exactly as the prompt or template says.
- Months, days, years, counts: integers.
- Holder percentages: use the precision requested by the prompt, commonly four decimal places.
- Percent amount: `round(basis_amount * percent_points / 100)`.
- Shortfall to fallback for buyer protections: `fallback_amount - draft_amount` when draft is below fallback.
- Delta to fallback for seller protections: excess above fallback or required fee shortfall, depending on the field label.
- Holder allocation: allocate each value component by fully diluted percentage or as-converted share percentage, then make totals reconcile to the stated cash, stock, and aggregate consideration.
- Exposure totals: include only quantified components the prompt asks to include. Keep not-quantified or explicitly excluded components out of aggregate exposure totals, but list them where the template asks.

When a field name says `preferred`, `fallback`, `draft`, `required`, `shortfall`, or `delta`, calculate from the matching source position rather than reusing another field.

## Legal Classification Patterns

Classify from the client perspective:

- Buyer-side: a draft cap, escrow, survival period, materiality scrape, consent condition, HSR condition, or material-contract condition below buyer fallback is usually `draft_below_playbook` with `revise` or `add`.
- Seller-side: a buyer-friendly burden above seller fallback, broad termination right, excessive escrow, long survival, financing condition, cherry-pick employee right, uncapped TSA, or missing seller protection is usually `draft_exceeds_playbook`, `out_of_policy`, or `missing_required_term`.
- Committee policy: use the policy threshold as the boundary. Draft values above the approved cap, restricted fiduciary changes, overlong survival, or unapproved MAE carveouts are `out_of_policy`.
- Missing affirmative protections use `missing_required_term`, empty term IDs, and `add`.
- Accept only when the current draft is in policy for the requested matrix and the template expects an included row.

Risk rating should reflect legal significance, closing impact, quantified exposure, and whether the item blocks signing or closing. Prioritize closing certainty, regulatory and consent blockers, major economics, indemnity leakage, employee transition, and operational continuity ahead of lower-risk housekeeping items unless the template provides an explicit sort order.

## Output Discipline

Return exactly one JSON object and no prose. Do not include comments, Markdown fences, citations outside fields, or explanatory text.

Before finalizing:

1. Confirm every template-required top-level key is present.
2. Confirm arrays use the requested order: explicit template order first, otherwise priority order for `priority_order` fields, otherwise stable ID or issue order if instructed.
3. Confirm enum strings match the template exactly.
4. Confirm amounts, percentages, month/day counts, and totals reconcile.
5. Confirm stable IDs come from the workbench or are synthetic only when the template allows them.
6. Confirm no values are copied from unrelated projects or similarly named deals.

## Bundled Helpers

- Use [scripts/fetch_workbench.py](scripts/fetch_workbench.py) to collect a deal snapshot from the live API into one JSON file.
- Use [scripts/check_answer.py](scripts/check_answer.py) to verify the final JSON parses and roughly matches the provided answer template top-level shape.
