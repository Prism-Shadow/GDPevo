---
name: ma-deal-workbench-json
description: Analyze M&A deal workbench records and draft transaction terms to produce structured JSON outputs such as seller issue registers, buyer SPA deviation matrices, committee escalation packages, closing readiness packages, transition reviews, consent/blocker schedules, cap-table economics allocations, and playbook or policy comparison summaries. Use when the task provides a deal workbench, a deal ID, and an answer template requiring precise legal/business issue classification, quantified deal metrics, stable source IDs, and JSON-only output.
---

# M&A Deal Workbench JSON

## Workflow

1. Read the prompt and answer template before fetching data. Identify the deal ID, client side, transaction type, requested work product, required ordering, enums, units, rounding rules, and required fields.
2. Gather the complete workbench record set made available for the deal: deal summary, current draft terms, playbook rules or policy thresholds, risk estimates, employees, consents, material contracts, regulatory records, diligence findings, benchmarks, notes, documents, and cap table when economics or holder allocation is requested.
3. Do not assume that similarly named projects or generic records apply. Use only records tied to the requested deal ID.
4. Use read-only cross-table querying only when the prompt makes it available and only to verify source records, joins, or completeness.
5. Build the output directly from the template. Keep enum strings exact, preserve required object nesting, include every required field, and return valid JSON only.

## Issue Selection

- Use only current draft terms unless the prompt asks for historical context. Exclude stale terms, in-policy distractors, and categories with no current draft term unless the prompt or client position requires a missing affirmative provision.
- Include missing required terms when the surrounding records show a protection is needed, such as regulatory clearance, required consents, employee service credit/PTO, escrow support, transition services, tax allocation, transfer taxes, governing law/forum, IP/domain transition, or outside-date protection.
- For committee escalation tasks, include current terms that exceed policy thresholds or are marked restricted for committee approval. Exclude stale rows and non-committee approval rows unless the template asks to list them as exclusions.
- For transition/carveout reviews, keep each stable issue ID separate when the template provides them. Do not merge TSA economics, employee continuity, customer-consent rights, tax, IP/domain, outside-date, and forum issues unless the template requires aggregation.

## Classification

- `draft_exceeds_playbook`: a draft numeric value is above the client-side maximum or gives the counterparty broader rights than allowed.
- `draft_below_playbook`: a draft numeric value is below the client-side minimum or omits part of a fallback protection.
- `missing_required_term`: no current draft term addresses a protection required by the prompt, playbook, policy, or deal facts.
- `out_of_policy`: a current term violates a policy threshold or restricted approval rule.
- `in_policy`: the draft satisfies the preferred or acceptable fallback position.

For buyer-side outputs, buyer-favorable positions commonly include higher indemnity caps, longer survival, full or fallback materiality scrape, escrow/holdback support, required material consents, HSR clearance conditions, service credit, and PTO protection.

For seller-side outputs, seller-favorable positions commonly include no financing condition, adequate reverse fee if financing risk remains, lower escrow/caps/survival, limited TSA duration with stranded-cost recovery, narrow consent termination rights, defined employee transfer/PTO mechanics, tax allocation, transfer-tax allocation, governing law/forum, and IP/domain transition limits.

## Calculations

- Calculate percentage amounts as `basis_amount * percent / 100`. Use the prompt's required basis; otherwise use the deal headline value unless a source record states a different basis such as upfront cash, equity value, stock value, or identified findings.
- Round currency to integer dollars. Round percentage-point fields exactly as the prompt requires. Keep month values as integers.
- For cap tables, allocate each consideration component by fully diluted percentage, then verify holder totals sum to the deal-level cash, stock, milestone, and headline values.
- For indemnity caps, compute draft, preferred, fallback, shortfall to fallback, and shortfall to preferred. Treat a separate special indemnity or identified finding as distinct from the general cap unless the template asks to combine them.
- For employees, sum counts and PTO liability from the relevant employee groups. Include service-credit requirements and medium/high WARN or retention risks when requested.
- For consents and contracts, treat `required_for_closing` consents and material contracts requiring consent as blockers. Keep notice-only records non-blocking unless the prompt specifically asks to challenge an exclusion.
- For risk totals, include only exposure components relevant to the requested issues. Avoid double-counting the same risk estimate in aggregate totals when it supports multiple issues; list the component once unless the template clearly asks for per-issue summation.
- For benchmarks, compare the draft metric to median and upper quartile: equal to upper quartile is `at_upper_quartile`; greater than upper quartile is `above_upper_quartile`.

## Output Discipline

- Use stable source IDs exactly as shown in the workbench. Use an empty array for missing draft-term source IDs when the template says to do so.
- Use `null` for fields that are genuinely not applicable unless the template uses zero-valued metrics for not-applicable numeric fields.
- Keep arrays sorted by the template's ordering instructions. If no explicit sort is given, use counsel workflow priority for priority arrays and stable IDs or template order for issue arrays.
- Make summary counts and totals reconcile to the emitted arrays. Recompute counts after any issue-set change.
- Classify closing readiness as `NOT_READY` when required consents, regulatory clearance, or material contract conditions remain unsatisfied. Use conditional/readiness statuses only when the template distinguishes tradeable issues from true blockers.
- Before final output, validate that the JSON parses, contains no prose outside the object, uses the required language and units, and does not include unsupported enum values.
