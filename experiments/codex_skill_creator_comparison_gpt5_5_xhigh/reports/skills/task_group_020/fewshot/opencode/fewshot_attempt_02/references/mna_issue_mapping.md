# M&A Issue Mapping Reference

Use this reference after reading the task prompt and answer template. It captures reusable patterns for deal-workbench JSON tasks without embedding values from any particular deal.

## Source Records To Check

- Deal record: project name, parties, client side, transaction type, value basis, headline value, signing or meeting dates, currency, applicable playbook or policy IDs.
- Terms: current draft provisions, term IDs, clause references, status flags, percentages, months, baskets, escrow/holdback mechanics, closing conditions, covenants, tax, governing law, and remedies.
- Playbook rules or policy thresholds: preferred and fallback positions, restricted provisions, approval thresholds, required conditions, and issue-specific enum language.
- Benchmarks: market median, quartiles, sample size, and whether the draft is above, at, or below market support.
- Risk estimates: low/high exposure values, source estimate IDs, categories, and assumptions.
- Consents: required closing consents versus notices or post-closing covenants, amount at risk, counterparty, contract references, and risk rating.
- Material contracts: annual revenue, consent requirement, customer or supplier relationship, and whether it should be a closing condition.
- Regulatory: HSR requirement, filing/clearance status, industry review, effort covenant, outside date needs, and hell-or-high-water limits.
- Employees: continuing employee counts, employee IDs, service-credit requirements, PTO liability, WARN or retention issues, and group labels.
- Cap table: holder names, security classes, fully diluted percentages, as-converted shares, and consideration allocation basis.
- Diligence findings, documents, and notes: unresolved risks, missing terms, stale/distractor flags, client instructions, and negotiated concessions.

## Client-Side Posture

Buyer-side tasks usually favor stronger closing and post-closing protection:

- Higher indemnity cap or special indemnity where risk findings support it.
- Deductible or basket mechanics if required by the playbook.
- Longer survival period or escrow release tied to survival.
- Full or fallback materiality scrape according to playbook.
- Escrow/holdback when unresolved findings, agent, release, or survival issues exist.
- All material consents and specified material contracts as closing conditions.
- HSR clearance as a closing condition when required; avoid hell-or-high-water unless the playbook requires it.
- Founder/executive restrictive covenants, service credit, PTO allocation, D&O tail, and seller expense responsibility when applicable.

Seller-side tasks usually favor narrower exposure and clearer transition/separation protections:

- Delete buyer financing conditions or require an adequate reverse break fee if financing risk remains.
- Reduce indemnity cap, escrow amount, escrow duration, and survival period to fallback limits.
- Add missing deductible baskets, tax allocation, transfer-tax split, governing law/forum, and restrictive covenant limits.
- Limit consents to required closing consents; exclude notice-only items and add material-adverse-impact standards where relevant.
- Require cost recovery, clean termination rights, and limited duration for transition services.
- Add IP, trademark, domain redirect, outside-date extension, employee continuity, service-credit, and PTO allocation protections when the records show transition risk.

Committee escalation tasks are narrower:

- Include only current draft terms that are out of policy, restricted, or require committee approval.
- Exclude stale terms, in-policy terms, and non-committee distractors even if they are interesting negotiation points.
- Provide the draft metric, policy threshold, delta, benchmark support, exposure, recommendation, and required approval conditions for each escalated term.

## Issue Classification

Use the task template's issue IDs and enums first. Map the evidence to the nearest template-approved issue, not to your own taxonomy.

- Indemnity cap and basket: compare draft cap, special indemnities, basket type, scrape, knowledge qualifiers, and risk findings against buyer or seller fallback.
- Survival: compare general and fundamental representation survival periods against thresholds. Separate month deltas when the template has distinct fields.
- Escrow or holdback: check percentage, amount, release timing, agent status, investment control, and whether unresolved findings support the escrow.
- Closing consents: classify required consents separately from notice-only or post-closing covenants. Required consents can be blockers.
- Material contracts: include specific contracts only when the source records require consent or the prompt asks for material-contract conditions.
- Regulatory and HSR: add a clearance condition when HSR is required and no adequate condition exists. Distinguish effort covenant from closing condition.
- Financing condition and reverse break fee: seller-side issue when buyer financing risk affects closing certainty.
- Employee continuity: check all continuing employee process terms, service credit, comparable terms, PTO liability, WARN, retention, and cherry-pick rights.
- Transition services: compare scope, duration, fee model, stranded overhead recovery, and clean termination rights.
- IP/domain/trademark transition: treat absence of required transition license, redirect, domain maintenance, or subdomain/page coverage as a missing required term.
- Tax allocation and transfer taxes: check mutual Section 1060 allocation, Form 8594 consistency, timing, and split of transfer taxes or bulk-sale costs.
- Governing law/forum: add missing preferred law/forum and extend to ancillary documents when required.
- Fiduciary out, reverse termination fee, and MAE carveouts: for committee tasks, compare restricted public-company merger terms against policy thresholds and required triggers/carveout groups.

## Output Construction Checks

- Use `null` for not-applicable scalar fields, `[]` for empty arrays, and `{}` only where the template expects an object.
- Keep exact enum case and spelling from the template.
- Sort issue arrays by template instruction. If the prompt asks for priority order, put closing certainty and largest quantified exposure first unless a policy says otherwise.
- Do not copy values from prior examples or similarly named projects. Recompute every number from the current deal and current sources.
- Do not fill a field just because the template mentions it. Fill it only when the current workbench evidence supports it; otherwise use the template's null/empty convention.
- Document mental arithmetic in scratch work, not in the final answer.
