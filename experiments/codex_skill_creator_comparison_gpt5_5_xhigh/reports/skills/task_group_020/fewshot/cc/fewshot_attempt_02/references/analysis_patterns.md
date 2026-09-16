# Analysis Patterns

Use these patterns after fetching the deal data and reading the task template. They are deliberately reusable: rely on live workbench values for every deal-specific ID, amount, date, term, threshold, and recommendation.

## Evidence Handling

- Treat the prompt and `answer_template.json` as the required output contract.
- Treat workbench records as authoritative evidence; prefer direct endpoint records over UI text.
- Filter every array by the exact `deal_id` if a response includes deal IDs.
- Exclude stale draft terms, stale notes, duplicate rows, and similarly named projects unless the prompt expressly asks for historical comparison.
- Preserve source IDs exactly: term IDs, consent IDs, contract IDs, employee IDs, finding IDs, estimate IDs, benchmark IDs, document IDs, and synthetic IDs requested by the template.
- For missing required provisions, use an empty `source_term_ids` array and cite supporting non-term records in fields such as `source_record_ids` when the template provides them.

## Comparing Draft Terms To Rules

Playbook tasks compare current draft terms to the applicable playbook rules:

- Use the playbook named in the prompt, or the `playbook_id` on the deal record if the prompt does not override it.
- Match draft terms and rules by normalized category first, then by basis, unit, and nearby wording in `draft_value`, `preferred_position`, `fallback_position`, `required_action`, notes, and documents.
- Seller-side review generally flags buyer-favorable terms that exceed seller tolerance, omit seller protections, or shift transition/economic burden to the seller.
- Buyer-side review generally flags draft terms that provide less protection than the buyer playbook requires, omit buyer closing conditions, or leave material diligence risk unsupported.
- Policy tasks compare current draft terms to policy thresholds. Include only current out-of-policy or restricted terms requiring the named approval body when the prompt asks for an escalation package.
- A term can be `in_policy` only when the draft satisfies the required fallback or accepted position. If the task asks only for deviations, exclude in-policy terms and list them only in the requested exclusion summary.

Status selection:

- `missing_required_term`: the draft is silent or no current term covers a required protection.
- `draft_exceeds_playbook`: the draft value is more burdensome than the client's limit, such as too large a seller escrow, too long a seller survival period, or too broad a buyer termination right.
- `draft_below_playbook`: the draft value is weaker than the client's required protection, such as too low a buyer indemnity cap or missing closing-condition coverage.
- `out_of_policy`: a current draft term exceeds or violates a policy threshold or restricted standard.
- `in_policy`: the current draft is acceptable under the relevant playbook or policy and the template asks to include accepted items.

Risk and recommendation:

- Use source risk ratings when records provide them; otherwise start from the playbook or policy default and adjust upward for closing blockers, quantified high exposure, regulatory closing conditions, or unresolved material contracts.
- Use `add` for missing provisions, `revise` for provisions that exist but need narrowing or strengthening, `delete` for prohibited terms, `accept` for in-policy terms, and `escalate` or approval actions only when the template asks for governance routing.
- Priority should reflect business impact first: closing certainty and regulatory blockers, material customer or contract consents, major economic deltas, employee or transition disruption, then cleanup legal terms.

## Arithmetic

Use the basis stated by the source record or prompt. If no different basis is stated, use the deal's headline value.

- Percent amount: `basis_amount * percent_points / 100`, rounded to an integer dollar.
- Buyer-side shortfall: required or fallback amount minus draft amount when draft protection is too low.
- Seller-side excess delta: draft amount minus fallback amount when draft burden is too high.
- Reverse fee shortfall: required fee amount minus draft fee amount.
- Month delta: compare draft months to fallback or policy months in the direction that makes the draft noncompliant.
- Holder allocation: multiply cash and stock consideration by the holder's fully diluted percentage; compute total consideration as cash plus stock, and use cap table share counts unchanged.
- Closing consent total: sum `amount_at_risk` only for consents required before closing.
- Material contract revenue total: sum annual revenue only for material contracts that require consent or are requested as closing conditions.
- Employee totals: use employee record counts for affected groups and sum PTO liability for groups that require assumption, credit, or allocation.
- Risk estimate totals: include each requested exposure category once. Do not double-count a consent amount, contract revenue, or diligence finding merely because it supports more than one issue.
- If a workbench risk estimate has low/high exposure fields, use those fields for modeled exposure unless the template asks for a specific independently calculated delta.

## Common Record Uses

- Deal record: client, counterparty, target, project name, signing and meeting dates, transaction type, currency, headline value, upfront cash, stock value, milestone value, playbook ID, policy ID.
- Draft terms: category, term ID, clause reference, draft value, numeric value, unit, basis, staleness flag, and rationale.
- Playbook rules: category, preferred position, fallback position, limit value, limit unit, basis, required action, risk default.
- Policy thresholds: category, policy standard, threshold value, threshold unit, basis, restricted flag, approval body.
- Benchmarks: match by category or metric; report sample size, median, upper quartile, and whether the draft is at/below median, between median and upper quartile, at upper quartile, or above upper quartile.
- Risk estimates: use estimate IDs and low/high exposures for quantified exposure fields.
- Consents: distinguish closing consents from notice-only or post-closing obligations; carry contract names, counterparties, risk ratings, and amount at risk.
- Material contracts: include only contracts whose consent requirement or change-of-control/anti-assignment status matters to the requested closing condition.
- Employees: identify affected groups, counts, service credit requirements, PTO liability, draft treatment, and WARN risk.
- Regulatory: determine whether HSR or another approval is required, whether clearance must be a closing condition, and whether a hell-or-high-water covenant is required or rejected.
- Diligence findings: use finding IDs and amounts for specific indemnities, NWC mechanics, privacy/security exposure, or other special risk support.
- Documents and notes: use them to prove draft silence, current version, ancillary-document requirements, transition/separation facts, or negotiation context.

## Template-Specific Strategy

- Issue registers and deviation matrices: enumerate every issue requested by the template, including missing required protections. Fill non-applicable fields with `null`, empty arrays, or enum statuses exactly as the schema instructs.
- Closing/economics packages: reconcile economics, holder allocation, indemnity package, escrow, NWC, consents, employee covenants, D&O tail, expenses, regulatory conditions, and final readiness in one pass. Classify blockers separately from tradeable issues.
- Committee escalation packages: include only current terms that are out of policy or restricted for committee approval. Provide policy comparison, benchmark support where applicable, quantified exposure where available, recommendation, required conditions, and an aggregate summary.
- Carveout transition reviews: look for transition services scope/duration/fees, IP and domain transition, tax allocation, transfer taxes, employee continuity and PTO, outside date extensions, customer consent termination rights, and governing law/forum. Treat draft silence as an issue when the seller or buyer required position needs an affirmative clause.

## Final Checks

- Every output issue must be traceable to a current source term, a missing required term supported by playbook/policy, or a deal-scoped non-term record.
- Counts must equal the arrays actually returned in the answer.
- Risk counts must match the issue objects, not the source records.
- Totals must match the included components and avoid double-counting.
- IDs must be stable source IDs or template-requested synthetic IDs, never invented prose labels unless the template expressly calls for a stable synthetic ID.
- The final answer must parse as JSON and contain no text outside the object.
