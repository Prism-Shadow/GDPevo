---
name: ma-deal-workbench-json
description: Analyze M&A deal workbench records and draft APA, SPA, merger, carveout, or committee terms against buyer, seller, or committee playbooks/policies, then return schema-conforming JSON issue registers, closing packages, transition reviews, escalation memos, or deviation matrices. Use when a task mentions TASK_ENV_BASE_URL, deal workbench APIs, deal IDs, playbook or policy thresholds, indemnity, escrow, survival, consents, HSR, employees, material contracts, or M&A legal JSON outputs.
---

# M&A Deal Workbench JSON

Use this skill to solve M&A workbench tasks that require a structured legal/commercial JSON deliverable. Treat the user's `input/payloads/answer_template.json` as the output contract.

## Core Workflow

1. Read the prompt and the answer template before fetching data.
2. Extract the deal ID, client side, deal type, required playbook or committee policy, output units, enum values, required ordering, and any explicit exclusions.
3. Replace `<TASK_ENV_BASE_URL>` with the task environment base URL and fetch all records needed for the requested sections.
4. Build a source map keyed by stable IDs from every record: draft terms, playbook or policy rules, deal economics, consents, regulatory records, employees, cap table, material contracts, diligence findings, risk estimates, benchmarks, documents, and notes.
5. Compare only current draft terms and required missing provisions against the applicable client playbook or committee policy.
6. Fill the exact JSON template. Use stable workbench IDs, required enums, integer dollar amounts, requested percent precision, integer month values, `null` for not applicable scalar fields, and empty arrays for no applicable list items.
7. Validate the final response as parseable JSON with no prose outside the JSON object.

## Data Collection

Prefer direct API records over the web UI when endpoints are documented in the prompt. The usual GET routes are:

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

Use read-only SQL only as a cross-check or to join unclear records:

```bash
curl -sS -X POST "$TASK_ENV_BASE_URL/api/query" \
  -H 'content-type: application/json' \
  -d '{"token":"deal-workbench-readonly","query":"select ..."}'
```

The optional helper [scripts/fetch_workbench.py](scripts/fetch_workbench.py) can collect common endpoint JSON into a directory:

```bash
python skill/scripts/fetch_workbench.py --base-url "$TASK_ENV_BASE_URL" --deal-id "$DEAL_ID" --out /tmp/deal-records
```

Do not assume records from similarly named projects apply. If a template asks for missing draft terms, use empty `source_term_ids` and anchor the issue to documents, regulatory records, playbook rules, or other stable source IDs when the schema has a place for them.

## Comparison Rules

Use the client posture to interpret "better" and "worse":

- For buyer-side tasks, draft terms are below playbook when they give the buyer less protection than the buyer fallback or required position, such as a low indemnity cap, missing escrow, narrow consent closing conditions, absent HSR clearance condition, or missing material-contract blockers.
- For seller-side tasks, draft terms exceed or violate playbook when they impose more seller burden, exposure, delay, or closing optionality than the seller fallback, such as excessive escrow, excessive indemnity cap or survival, broad buyer termination rights, financing conditions, field employee cherry-picking, or long/underpriced transition services.
- For committee tasks, include only current draft terms that the policy flags as restricted, approval-required, or out of threshold. Exclude stale, in-policy, and non-committee terms unless the template asks for excluded term IDs or categories.
- Treat a missing affirmative protection as an issue only when the playbook/policy requires it or deal facts make it necessary, such as required consents, HSR, service credit/PTO, tax allocation, transfer-tax allocation, governing law/forum, D&O tail, outside-date extensions, restrictive covenants, or IP/domain transition protections.

Classify status with the template's enum vocabulary:

- `missing_required_term`: no current draft term covers a required protection.
- `draft_below_playbook`: the draft gives the client less than the required fallback or required condition.
- `draft_exceeds_playbook`: the draft goes beyond what the client should accept or imposes excess burden on the client.
- `out_of_policy`: the draft violates a committee threshold, restricted-change rule, or non-numeric policy.
- `in_policy`: use only when the requested matrix expects accepted positions to remain in the output.

## Common Issue Areas

Check all areas requested by the prompt and template:

- Economics: headline value, upfront cash, stock value, milestone value, working-capital or NWC adjustment, holder allocation.
- Indemnity: cap, basket, survival, materiality scrape, escrow or holdback, special indemnities, privacy/cyber or diligence-driven findings.
- Closing certainty: financing condition, reverse termination fee, required consents, material-contract consents, customer termination rights, outside date, HSR, regulatory approvals, efforts covenant, hell-or-high-water covenant.
- Employees: continuing employee count, offer process, service credit, PTO allocation, WARN/termination risk, retention, founder/executive restrictive covenants.
- Transition/separation: TSA scope, duration, fee model, stranded cost recovery, clean termination rights, IP transition, trademark license, domain redirects, tax allocation, transfer-tax split.
- Governance and expenses: governing law/forum, D&O tail, seller and buyer transaction-expense allocation.

## Quantification

Use the basis stated in the prompt, template, playbook, policy, or term. If no source states a different basis, use the headline purchase price or equity value from the deal record.

- Percent amount: `round(basis * percent / 100)` as integer dollars.
- Buyer shortfall: required fallback or preferred amount minus draft amount, never a negative number unless the template explicitly wants a signed delta.
- Seller excess delta: draft amount or months minus seller fallback amount or months when the draft exceeds the seller fallback.
- Reverse fee shortfall: required fee amount minus draft fee amount.
- Holder allocation: use cap-table percentages if provided; otherwise compute as converted shares divided by total as-converted shares, then allocate each consideration component separately.
- NWC collars, privacy findings, consent amounts at risk, stranded costs, transition disruption, and indemnity leakage should come from diligence findings or risk-estimate records, not from invented assumptions.
- Aggregate exposure only from components the prompt asks to include. Keep unquantified, not-applicable, or expressly excluded components out of exposure sums, while preserving their IDs in excluded lists if requested.
- Counts must be computed from the final filtered output, not from all records fetched.

Honor precision exactly: integer dollars, integer months, dates as `YYYY-MM-DD`, and percent points rounded to the number of decimals specified by the prompt or template.

## Output Construction

Start from the provided answer template and remove placeholder examples by replacing them with actual arrays or values. Do not add fields that are absent from the template.

For each output row or issue:

- Use stable source IDs from the workbench. Use synthetic IDs only when the template explicitly allows them for regulatory or issue-level blockers.
- Include all template fields even when their value is `null`, unless the template clearly shows an optional shape.
- Use `null` for scalar values that do not apply, and `[]` for empty list fields.
- Preserve exact enum spelling from the template.
- Put issue-specific details in normalized objects only when the template provides such fields.
- For blocker lists, include only items that must be satisfied before closing or that the template identifies as blockers.

Ordering should follow the template. If no ordering is specified, use the requested priority order for priority arrays and a stable logical order for matrices: closing blockers and regulatory issues first, then economics/indemnity, employee and transition issues, then cleanup terms.

## Final Verification

Before answering:

1. Parse the JSON locally if possible.
2. Confirm every required top-level key and nested key from the template is present.
3. Confirm enum values match exactly.
4. Recalculate all percentages, dollar amounts, month deltas, holder allocations, counts, and aggregate sums.
5. Confirm every non-empty source ID appears in the fetched workbench records or is an allowed synthetic ID.
6. Confirm excluded or in-policy records were handled according to the prompt.
7. Return only the JSON object.
