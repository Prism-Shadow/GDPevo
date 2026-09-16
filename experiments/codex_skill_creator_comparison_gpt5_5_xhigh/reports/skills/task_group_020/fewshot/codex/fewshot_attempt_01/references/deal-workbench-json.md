# Deal Workbench JSON Reference

## Fetching Context

Use the prompt and environment note to identify the base URL and one `deal_id`. Prefer the explicit API endpoints named in the prompt, then add standard deal endpoints as needed:

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

Common response wrappers are `deal`, `draft_terms`, `rules`, `thresholds`, `benchmarks`, `risk_estimates`, `cap_table`, `consents`, `employees`, `material_contracts`, `regulatory`, `diligence_findings`, `documents`, and `deal_notes`.

Use SQL only if the prompt permits it and GET responses leave a real cross-table ambiguity. Never query broad or unrelated matters while preparing one deal answer.

## Evidence Map

Create a compact map before filling JSON:

- Deal: client, counterparty, target, transaction type, signing or meeting dates, currency, headline value, upfront cash, stock value, milestone value, playbook id, policy id.
- Terms: current draft only unless the task asks to discuss stale records. Track `term_id`, category, clause reference, numeric value, unit, basis, draft value text, source document, and staleness flag.
- Rules or thresholds: category, preferred and fallback positions, limit value, limit unit, basis, required action, risk default, approval requirement, restricted flag, and policy standard.
- Consents and material contracts: closing-required flags, notice-only status, anti-assignment or change-of-control flags, amount at risk, annual revenue, risk rating, and source ids.
- Regulatory: HSR requirement, threshold basis, approval type, closing condition need, hell-or-high-water or remedy covenant.
- Employees: group counts, PTO liability, service-credit requirement, WARN risk, and draft treatment.
- Economics: cap table percentages and shares; diligence amounts; risk estimate low/high ranges; benchmark median and upper quartile.

## Issue Classification

Use the client's side to decide direction:

- Buyer-side protection below buyer playbook fallback is usually `draft_below_playbook`.
- Seller-side exposure above seller fallback is usually `draft_exceeds_playbook`.
- A required protective provision absent from current draft terms is `missing_required_term`.
- A current term outside a committee threshold or restricted by policy is `out_of_policy`.
- A term at or better than the fallback position is `in_policy` unless the prompt asks to escalate preferred-only gaps.

For committee escalation tasks, include only current draft terms requiring committee action. Exclude stale terms, in-policy terms, and non-committee distractors, but list exclusions if the template asks.

For missing terms, set `source_term_ids` to `[]` and use supporting record ids from documents, regulatory records, consents, material contracts, employees, findings, or risk estimates when the template has a field for them.

## Common M&A Issue Mapping

- Indemnity cap and basket: compare draft cap percent to preferred and fallback rules; note missing deductible or tipping basket if the template asks.
- Survival and knowledge qualifiers: compare months to rule thresholds and record missing knowledge qualifiers only if the template treats them as required.
- Materiality scrape: classify full, breach-only, damages-only, or absent according to the buyer or seller rule.
- Escrow or holdback: calculate percent and amount from the stated basis; record agent, release timing, and unresolved findings if required.
- Financing condition and reverse break fee: seller-side drafts with buyer financing outs usually require deletion or a fee; calculate fee shortfall from the stated basis.
- Consents and material contracts: required-for-closing consents and material contract consents are blockers; notice-only records are nonblocking or tradeable unless the prompt says otherwise.
- HSR and regulatory: if HSR is required, add a clearance condition when missing. Use the regulatory record for hell-or-high-water or limited-efforts language.
- Employee transition: sum affected employee counts and PTO liabilities; require service credit, comparable terms, PTO allocation, and all-employee or defined-process treatment when the playbook requires it.
- Restrictive covenants: include only groups and scope supported by holder, employee, or playbook records.
- Transition services and carveouts: compare services, duration, stranded-cost recovery, clean termination rights, IP/trademark/domain transition, tax allocation, transfer tax split, outside date extensions, and governing law/forum to seller rules.
- Committee policies: compare threshold values, restricted flags, and benchmarks. Attach benchmark position only when the matching benchmark category exists.

## Calculations

- Percent amount: `round(value_basis * percent / 100)` and output as an integer dollar amount.
- Seller delta where draft is too high: `draft_amount - fallback_amount`.
- Buyer shortfall where draft is too low: `fallback_amount - draft_amount`, and preferred shortfall if the template asks.
- Reverse break fee shortfall: required fee amount minus drafted fee amount.
- Holder allocation: multiply each consideration component by fully diluted percentage; keep holder percentages at the precision requested by the prompt.
- Consent amount at risk: sum closing-required consent `amount_at_risk` values included as blockers.
- Material contract revenue conditioned: sum annual revenue for contracts requiring closing consent or listed as material-contract blockers.
- Employee PTO liability: sum PTO liabilities for affected or continuing employee groups included by the task.
- Exposure totals: use risk estimate low/high values for included categories only. Do not add non-quantified categories unless the template defines a value.

Respect the prompt's rounding precision. If no precision is stated, use integer dollars, percent points as numeric values, and integer months.

## Ordering And Final Checks

Follow explicit template ordering first. If no order is specified, prioritize closing certainty and regulatory blockers, then core economics and indemnity, then employee or transition operations, then tax and forum issues.

Before final output:

- Confirm every required top-level field is present.
- Confirm every issue object has all required fields, using `null`, `[]`, or `{}` only where the template allows.
- Confirm stable IDs match source records or template enumerations exactly.
- Confirm all current required blockers appear in both issue summaries and blocker arrays when the template separates them.
- Confirm no stale, unrelated, or similarly named project records influenced the answer.
- Run a JSON parser and remove all explanatory prose.
