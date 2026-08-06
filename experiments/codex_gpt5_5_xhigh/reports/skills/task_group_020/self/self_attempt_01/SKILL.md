---
name: ma-deal-workbench-json
description: Prepare M&A deal-workbench legal and business analysis packages as strict JSON. Use when a task asks counsel to review buyer or seller M&A deal terms, playbooks, policies, consents, regulatory status, cap tables, employees, material contracts, risk estimates, benchmarks, notes, or diligence findings and return a structured issue register, deviation matrix, closing package, committee escalation, or transition review conforming to a provided JSON template.
---

# M&A Deal Workbench JSON

## Core Workflow

1. Read the user prompt, every file under the task's `input/payloads/`, and any environment access file supplied with the task before querying data or drafting an answer.
2. Use only the workbench base URL, query token, and endpoints authorized by the environment access file. Prefer the exact API routes named in the prompt, then use listed collection endpoints or read-only SQL only for cross-table checks and reconciliation.
3. Identify the deal ID, client side, transaction type, applicable playbook or policy, requested output package, units, rounding rules, allowed enums, required field names, ordering rules, and stable IDs from the prompt and payload templates.
4. Gather the complete evidence set needed for the requested package: deal record, current draft terms, playbook rules, policy thresholds, benchmarks, risk estimates, consents, employees, material contracts, regulatory records, diligence findings, cap table, documents, and notes as applicable.
5. Build an evidence map before writing JSON. Track stable source IDs for draft terms, consents, contracts, employees, holders, findings, benchmarks, estimates, notes, and policy or playbook rules. Use empty source arrays only when the issue is a genuinely missing required draft term.
6. Compare the current draft against the client's playbook or policy from the client's perspective. Treat missing affirmative protections as issues when the playbook, policy, or deal facts require them.
7. Include only the issue universe requested by the prompt and template. Exclude stale records, similarly named deals, in-policy distractors, and non-requested categories unless the template specifically asks to list excluded items.
8. Populate the exact JSON shape requested by the payload template. Use template keys, enums, stable issue IDs, redline IDs, final-position IDs, and ordering instructions exactly. Return valid JSON only, with no prose outside the object.

## Comparison Rules

- Classify draft terms against preferred, fallback, required, restricted, and approval-threshold positions from the applicable playbook or policy.
- Use `in_policy` only when the current draft satisfies the client-side requirement for the requested issue.
- Use `out_of_policy` when a present draft term violates an approval threshold or restricted policy.
- Use `missing_required_term` when the current draft is silent but the client-side position requires an affirmative provision.
- Use `draft_below_playbook` when the draft gives less protection or economics than the client's fallback or minimum position.
- Use `draft_exceeds_playbook` when the draft creates more burden or exposure than the client position allows.
- Choose recommendations from the template enums by remedy: add missing protection, revise inadequate or excessive terms, delete unacceptable buyer or seller asks, accept compliant terms, or escalate/approve/reject when a committee or business decision is required.
- Assign risk ratings based on closing impact, quantified exposure, regulatory need, customer or contract termination risk, employee disruption, and deviation from non-discretionary policy.

## Quantification Rules

- Use the purchase-price base stated in the prompt, template, source record, playbook, or policy. If no different basis is stated, use the deal's headline purchase price.
- Keep integer dollars as integers. Round percentage points to the precision required by the prompt or template. Keep month values as integers and dates in `YYYY-MM-DD` format.
- Convert percentages to dollars as `base_amount * percent / 100`, then round to whole dollars when the field requires integer dollars.
- Calculate shortfalls and deltas against the specified preferred, fallback, required, or threshold position. Do not mix preferred and fallback bases in one field.
- For cap-table allocations, use the workbench holder percentages or calculate from as-converted or fully diluted shares as directed. Reconcile allocations to the applicable cash, stock, milestone, upfront, or headline value fields.
- Sum only comparable quantified exposures. Avoid double-counting the same risk estimate across issue rows and aggregate summaries. Preserve the source estimate ID where the template asks for it.
- Count blockers, high/medium/low risks, missing terms, required consents, conditioned contract revenue, PTO liability, and employee populations directly from the evidence set, not from narrative impressions.

## Package Patterns

- For seller issue registers, focus on buyer draft deviations from seller playbook positions, absent seller-protective APA terms, closing certainty, escrow and indemnity economics, covenants, employees, taxes, governing law/forum, consents, materiality scrape, and regulatory effort.
- For buyer closing and economics packages, cover consideration allocation, indemnity, escrow or holdback, survival, working-capital mechanics, closing consents, material contracts, regulatory clearance, employee treatment, restrictive covenants, D&O tail, transaction expenses, readiness, and blockers.
- For committee escalation packages, include only current draft terms that are out of policy, restricted, or otherwise require approval. Provide policy comparison, quantified delta, benchmark support when available, exposure, recommendation, conditions, and aggregate routing fields.
- For carveout transition reviews, focus on separation and transition protections: IP transition, trademark and domain redirects, transition services scope, duration and fees, purchase-price allocation mechanics, transfer taxes, employee continuity, outside date protection, governing law/forum, and customer or contract consent risk.
- For buyer deviation matrices, cover the requested buyer positions such as indemnity cap and basket, survival and knowledge qualifiers, materiality scrape, escrow or holdback, consent closing conditions, HSR or other regulatory clearance, material-contract blockers, and risk totals.

## Output Discipline

- Preserve English-only output when required.
- Do not add fields absent from a strict template unless the template permits open objects.
- Use `null`, empty arrays, or empty objects exactly as the template semantics require; do not invent values to avoid nulls.
- Prefer stable workbench IDs over descriptive labels in ID fields. Use human-readable names only where the template asks for names.
- Validate that every enum value is copied exactly from the template, every required top-level field is present, numeric fields use the required units, and the final answer parses as JSON.
