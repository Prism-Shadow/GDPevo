---
name: deal-workbench-ma-json
description: Produce schema-conformant JSON for M&A deal workbench review tasks. Use when a prompt provides a deal_id and answer_template.json and asks for APA/SPA issue registers, closing and economics packages, committee policy escalation packages, transition reviews, deviation matrices, or similar legal/commercial analyses using deal APIs, playbooks, policies, terms, benchmarks, risk estimates, cap tables, consents, employees, material contracts, regulatory records, diligence findings, documents, and notes.
---

# Deal Workbench M&A JSON

## Core Workflow

1. Read the user prompt and `input/payloads/answer_template.json` before querying data. Extract the deal ID, client side, transaction type, requested work product, applicable playbook or policy ID, required rounding, required ordering, allowed enums, and every required output field.
2. Read `environment_access.md` for the base URL, query token, and allowed endpoints. Use only that workbench environment for network access.
3. Fetch records for the exact deal ID. Do not use records from similarly named projects.
4. Compare current draft terms against the applicable playbook rules or policy thresholds. Treat absent protective terms as issues when the prompt, playbook, policy, or surrounding deal data makes the term required.
5. Build the answer directly against the template. Preserve required keys, enum spellings, nulls, empty arrays, source ID fields, and requested ordering.
6. Validate that the final response is valid JSON and contains no narrative outside the JSON object.

## Data Collection

Use the helper when available:

```bash
python3 <path-to-this-skill>/scripts/fetch_deal_workbench.py <DEAL_ID> --env-file environment_access.md
```

Fetch these API resources as relevant:

- `/api/deals/<deal_id>` for deal economics, parties, dates, playbook ID, policy ID, transaction type, and value basis.
- `/api/deals/<deal_id>/terms` for current draft terms. Use stable `term_id` values; skip stale terms unless the prompt asks to discuss stale records.
- `/api/playbooks/<playbook_id>/rules` for buyer or seller fallback/preferred positions.
- `/api/policies/<policy_id>/thresholds` for committee approval thresholds and restricted categories.
- `/api/deals/<deal_id>/benchmarks` for sample size, median, upper quartile, and market-position support.
- `/api/deals/<deal_id>/risk-estimates` for quantified exposure ranges and source estimate IDs.
- `/api/deals/<deal_id>/cap-table` for holder allocation by fully diluted percentage or as-converted shares.
- `/api/deals/<deal_id>/consents` for required closing consents, notice-only items, counterparties, risk ratings, and amounts at risk.
- `/api/deals/<deal_id>/material-contracts` for material contract consent conditions and revenue at risk.
- `/api/deals/<deal_id>/employees` for continuing employee counts, service credit, PTO liability, WARN risk, and affected groups.
- `/api/deals/<deal_id>/regulatory` for HSR, industry review, closing condition, and effort covenant facts.
- `/api/deals/<deal_id>/diligence-findings`, `/documents`, and `/notes` for support on missing terms, special indemnities, NWC mechanics, transition needs, expense allocation, and distractor handling.

Use `POST /api/query` only for cross-table checks or to confirm records when API lists are ambiguous. Send the token from `environment_access.md`, constrain queries by the exact `deal_id`, and avoid mutating statements.

## Comparison Rules

- **Playbook matters:** map draft term categories to playbook rule categories. For buyer-side work, weaker buyer protection is usually `draft_below_playbook` or `missing_required_term`; for seller-side work, buyer overreach is usually `draft_exceeds_playbook` and absent seller protections are `missing_required_term`.
- **Policy matters:** include only current draft terms that are outside the specified committee policy, require the requested approval body, or are marked restricted. Exclude stale, in-policy, and non-committee distractor terms; populate exclusion lists when the template requests them.
- **Missing terms:** use an empty `source_term_ids` array and cite stable supporting records elsewhere when possible, such as documents, regulatory records, consents, material contracts, employee records, risk estimates, findings, or notes.
- **Closing blockers:** include required closing consents, required regulatory clearances, and material contract consents that must be satisfied before closing. Keep notice-only and post-closing covenant items separate when the template provides fields for them.
- **Risk ratings and recommendations:** start from source record risk ratings and playbook/policy defaults, then elevate when a missing or noncompliant term affects closing certainty, regulatory clearance, employee continuity, consent economics, or quantified exposure.

## Calculations

- Use the basis specified by the prompt, term, playbook, policy, or deal record. If no different basis is stated, use the deal's headline purchase price or equity value as directed by the task.
- Convert percentage points to dollars as `basis * percent / 100`, rounded to integer dollars. Keep percent-point fields as numbers, not fractions. Keep holder percentage fields as fractions only when the template or cap table uses fractional fully diluted percentages.
- For holder allocations, multiply each holder's fully diluted percentage by each consideration component requested by the template, then sum to total consideration. Preserve the template's requested decimal precision.
- For cap, basket, escrow, reverse-fee, survival, outside-date, TSA-duration, and policy-threshold deltas, calculate draft minus fallback or threshold in the direction described by the template.
- Sum quantified exposure fields only from components included in the requested analysis. Do not add non-quantified exposures to dollar totals.
- For consent totals, sum `amount_at_risk` only for required closing consents. For material contract totals, sum annual revenue only for contracts requiring consent or express closing-condition treatment.
- For employee totals, sum counts and PTO liabilities for the affected continuing or transferring employee groups requested by the task.

## Output Checks

- Return one JSON object only.
- Match every template key and allowed enum exactly.
- Use integer dollars, requested percent precision, integer month values, and `YYYY-MM-DD` dates.
- Use stable IDs from workbench records for terms, consents, contracts, employees, findings, risks, documents, notes, blockers, and redlines. Use synthetic IDs only when the template expressly permits them.
- Preserve the template's ordering instructions. If no explicit order is given, order by negotiation priority for priority fields and by stable ID for register or matrix rows.
- Re-run a JSON parser on the final object before responding.
