---
name: ma-deal-workbench-json
description: Use when solving M&A deal workbench tasks that require fetching deal records, comparing APA or SPA draft terms to buyer or seller playbooks or committee policy, calculating deal economics, and returning strict JSON issue registers, deviation matrices, closing packages, or committee escalations.
---

# M&A Deal Workbench JSON

Use this skill for M&A workbench tasks where the prompt provides a deal ID, a task environment base URL, an answer template, and asks for JSON only.

## Core Rules

- The prompt and the task's answer template are the output contract. Match field names, nesting, enum strings, nullability, ordering instructions, units, and rounding exactly.
- Treat the deal ID, client side, applicable playbook or policy, and endpoint list in the prompt as authoritative. Do not use records from similarly named projects.
- Fetch source records before reasoning. Do not invent source IDs, amounts, dates, holder names, or policy thresholds.
- Use stable IDs from the workbench in all source fields. For a required term missing from the draft, use an empty `source_term_ids` array unless the template asks for document, regulatory, consent, or other record IDs.
- Return only valid JSON. No narrative, Markdown, citations, or comments outside the JSON object.

## One-Pass Workflow

1. Read the prompt and the answer template.
2. Identify the deal ID, client side, governing playbook or committee policy, requested output type, required units, and ordering rules.
3. Fetch every endpoint named in the prompt. Also fetch relevant standard deal routes when the prompt asks for those record types: `deal`, `terms`, `playbook` or `policy` rules, `risk-estimates`, `employees`, `consents`, `regulatory`, `benchmarks`, `notes`, `cap-table`, `material-contracts`, `diligence-findings`, and `documents`.
4. If read-only SQL is offered, use it only to cross-check joins, record completeness, or unclear field names. Prefer API records as the primary source for stable IDs and business facts.
5. Build a working table of draft terms, controlling rule thresholds, required missing provisions, deal economics, consents, material contracts, regulatory status, employee facts, diligence findings, risk estimates, benchmarks, notes, and document metadata.
6. Compare each required issue against the controlling playbook or policy, calculate all requested metrics, then assemble JSON directly in the template shape.
7. Validate the JSON locally before final output.

Useful command pattern:

```bash
BASE="$TASK_ENV_BASE_URL"
DEAL_ID="the_deal_id_from_the_prompt"
curl -sS "$BASE/api/deals/$DEAL_ID" > /tmp/deal.json
curl -sS "$BASE/api/deals/$DEAL_ID/terms" > /tmp/terms.json
```

For SQL cross-checks, post to `/api/query` with the read-only token only when the prompt says that endpoint is available.

## Playbook And Policy Comparison

Classify from the client perspective:

- `missing_required_term`: the draft is silent and the playbook, policy, regulatory facts, consents, employee facts, or diligence record shows an affirmative provision is needed.
- `draft_below_playbook`: the draft gives the client less protection or economics than the client fallback or required position.
- `draft_exceeds_playbook`: the draft imposes more burden, duration, exposure, buyer discretion, or closing optionality than the client fallback allows.
- `out_of_policy`: a current draft term violates a committee threshold, restricted provision, or template-specific policy rule.
- `in_policy`: the draft satisfies the applicable fallback or accepted position.

Recommended actions usually follow the classification:

- Delete buyer financing conditions or other terms the client playbook prohibits.
- Revise terms that can be brought to fallback or preferred positions.
- Add missing required provisions, closing conditions, redlines, escrow mechanics, tax allocations, governing law/forum, HSR conditions, employee protections, or transition covenants.
- Accept only when the draft is in policy or at an expressly acceptable fallback.
- Escalate, approve with conditions, or reject when the task is a committee package or the template uses approval enums.

For committee escalation tasks, include only current draft terms that are out of policy or restricted. Exclude stale, in-policy, non-committee, or distractor terms, and populate any template fields that ask for excluded terms or categories.

## Calculations

- Use the purchase price, equity value, upfront cash, or other basis specified by the source rule. If no special basis is stated, use the deal headline value requested by the prompt.
- Percentage amounts: `integer dollars = round(basis_dollars * percent_points / 100)`.
- Percentage fields are percent points, not fractions, unless the template explicitly says holder percentages or another field should be fractional.
- Dollar fields are integer USD. Month fields are integers. Dates use the format required by the prompt or template.
- For seller-side burdens, dollar or month deltas usually measure draft burden minus fallback allowance. For buyer-side protections, shortfalls usually measure fallback or preferred protection minus the draft.
- For holder allocations, multiply cash, stock, and total consideration by each holder's fully diluted percentage or share ratio, then ensure the allocation totals reconcile to the source economics.
- For escrow, holdback, cap, fee, collar, special indemnity, PTO, consent risk, and material-contract revenue fields, use the explicit source basis where available and avoid mixing bases.
- Aggregate exposures from the selected risk estimates or quantified impacts requested by the template. Do not double count the same risk under multiple labels. Exclude components the task identifies as not applicable, stale, in-policy, or outside the requested package.
- Summary counts should be derived from the final arrays: issue counts, risk counts, blocker counts, missing term counts, business outcome counts, and status counts.

## Record Mapping

Use these recurring workbench records:

- Deal record: client, project, target, counterparty, transaction type, signing or meeting dates, currency, value basis, headline value, upfront cash, stock value, and milestone value.
- Terms: `term_id`, category, clause reference, draft percentages, months, baskets, caps, escrow, survival, materiality scrape, financing condition, consent condition, governing law, tax, TSA, employee, and restrictive covenant language.
- Playbook or policy rules: preferred position, fallback, thresholds, required actions, required conditions, and coded positions.
- Consents: stable consent ID, counterparty, contract name, condition type, risk rating, amount at risk, notice-only status, and closing condition status.
- Material contracts: contract ID, contract name, annual revenue, consent requirement, and whether it should be a closing blocker or non-blocking notice.
- Regulatory: HSR requirement, threshold basis, approval scope, covenant standard, remedy cap, hell-or-high-water requirement, and whether clearance must be a closing condition.
- Employees: continuing or affected employee counts, service-credit employee IDs, PTO liabilities, WARN risk employee IDs, field-selection or cherry-pick rights, retention requirements, and comparable terms.
- Diligence findings and risk estimates: source finding or estimate IDs, quantified low/high exposure, special indemnities, privacy or customer concentration findings, NWC adjustments, transition disruption, and stranded cost gaps.
- Benchmarks and notes: sample size, median, upper quartile, benchmark position, negotiation notes, business rationales, and stale or distractor markers.
- Documents: stable document IDs for missing provisions that are apparent from draft silence.

## Output Patterns

- Issue registers and deviation matrices should cover every issue the prompt requires, including missing protective terms when the surrounding workbench data makes them necessary.
- Transition and carveout reviews often need a paired issue list and redline list. Put the issue facts in the issue entry and the required drafting positions in the redline `must_have_terms`.
- Closing packages should separate true blockers from tradeable issues. Required consents, HSR clearance, and material-contract consents are blockers when the template asks for closing readiness.
- Committee packages should preserve policy comparison fields: draft metric, policy metric, delta, benchmark support, exposure, recommendation, and required conditions.
- Sort arrays exactly as instructed by the template. If the template gives no ordering rule, use negotiation priority for priority lists and a stable deterministic order for issue arrays.

## Validation Checklist

Before returning:

- Parse the final object with `python -m json.tool`.
- Check every enum value against the template.
- Check every required field exists, including fields whose value is `null`, `[]`, or `{}`.
- Check all source IDs came from fetched records.
- Check missing draft terms use empty term ID arrays unless another source record is required.
- Check calculations, rounding, bases, and signs for deltas and shortfalls.
- Check summary totals against the final arrays and selected source records.
- Confirm the final response is JSON only.
