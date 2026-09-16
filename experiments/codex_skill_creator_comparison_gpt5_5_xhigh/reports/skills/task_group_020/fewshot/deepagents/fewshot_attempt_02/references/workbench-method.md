# Workbench Method

## Evidence Collection

Fetch only records for the requested deal ID. Useful API families are:

- Deal overview: `/api/deals/<deal_id>`
- Current draft terms: `/api/deals/<deal_id>/terms`
- Documents and notes: `/api/deals/<deal_id>/documents`, `/api/deals/<deal_id>/notes`
- Rules: `/api/playbooks/<playbook_id>/rules` or `/api/policies/<policy_id>/thresholds`
- Financial and risk support: `/api/deals/<deal_id>/benchmarks`, `/api/deals/<deal_id>/risk-estimates`, `/api/deals/<deal_id>/diligence-findings`
- Closing support: `/api/deals/<deal_id>/consents`, `/api/deals/<deal_id>/material-contracts`, `/api/deals/<deal_id>/regulatory`
- People and economics: `/api/deals/<deal_id>/employees`, `/api/deals/<deal_id>/cap-table`

Use read-only SQL only for cross-table checks and only with the token provided in the task prompt. Do not use admin or reseed endpoints while solving.

## Issue Selection

Start from the requested work product, not from every record in the database.

- Seller APA or carveout transition review: look for buyer terms that exceed seller limits, missing seller protections, financing or consent termination rights, escrow and indemnity overreach, TSA duration and fee gaps, employee transition burden, restrictive covenant scope, IP/domain transition gaps, tax allocation, transfer tax split, outside date, and governing law/forum.
- Buyer SPA or deviation matrix: look for buyer protections that are below playbook, missing escrow or holdback mechanics, inadequate cap/basket/survival/materiality scrape terms, missing required consents, HSR closing condition, material contract blockers, employee service-credit/PTO issues, D&O tail, transaction expense allocation, and holder-level consideration allocation.
- Committee escalation: include only current draft terms that breach policy thresholds or are restricted for committee approval. Exclude stale records, in-policy terms, and issues outside the committee policy scope even if they are business-relevant.

Treat a term as missing when the required protection is absent from current draft terms and a rule, policy, or deal fact makes it necessary. Use an empty `source_term_ids` array for missing terms and use supporting record IDs in the template's other source fields when available.

## Classification

Use the template enums. Common patterns:

- `in_policy`: the current draft satisfies the governing rule and the template asks to include accepted positions.
- `out_of_policy`: the term violates a policy or rule without a more specific directional enum.
- `draft_exceeds_playbook`: the draft gives the counterparty more than the client-side playbook allows, common for seller-side review of buyer overreach.
- `draft_below_playbook`: the draft gives the client less protection than the client-side playbook requires, common for buyer-side review.
- `missing_required_term`: no current term provides a required protection.

Recommended actions should match the fix: `delete` for prohibited conditions, `revise` for terms needing changed numbers or scope, `add` for missing protections, `accept` for in-policy positions, and `approve_with_conditions` or `reject` for committee decisions.

Risk is usually `HIGH` for closing blockers, financing uncertainty, regulatory clearance, fiduciary restrictions, essential customer or material-contract consents, large quantified deltas, and employee or transition disruption. Use `MEDIUM` for material legal cleanup or moderate economic deviations, and `LOW` for notice-only or low-dollar items when the template includes them.

## Calculations

Use the source-specified value basis. If none is specified, use the deal headline purchase price or equity value named in the deal record.

- Percentages in legal terms are percent points. Convert to dollars as `basis * percent / 100` and round to integer dollars.
- Holder percentages may be fractions or percent points depending on the template. Follow the template precision exactly.
- Months are integers. Deltas are positive excesses or shortfalls relative to the fallback or threshold requested by the field name.
- Consent amount at risk is the sum of required closing consent amounts, excluding notice-only records unless the template asks for them.
- Material-contract revenue conditioned is the sum of annual revenue for contracts that require closing consent or are closing blockers.
- Issue counts, risk counts, and missing/out-of-policy counts should be computed from the final arrays, not separately estimated.
- Aggregate exposure should sum the risk-estimate components the prompt asks to include. Do not double-count the same exposure under both an issue and a blocker unless the template explicitly separates them.
- Priority order should follow explicit prompt/template ordering. Otherwise rank by closing certainty and regulatory blockers first, then high-dollar economic issues, then employee/transition continuity, then legal cleanup.

## Output Discipline

- Preserve every required key from the template, even when the value is `null`, `[]`, or `{}`.
- Use source IDs exactly as stored in the workbench.
- Keep array ordering from the template instructions. If no ordering rule exists, use priority order for issue matrices and stable ascending IDs for redlines.
- Do not include explanatory prose, Markdown fences, comments, or trailing commas in the final answer.
