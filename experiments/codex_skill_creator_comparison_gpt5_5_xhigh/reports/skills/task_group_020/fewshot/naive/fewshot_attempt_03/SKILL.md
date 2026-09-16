---
name: ma-deal-workbench-review
description: Use this skill for M&A deal-workbench legal review tasks that require gathering deal, draft term, playbook, policy, diligence, consent, employee, regulatory, benchmark, or risk records and returning strict JSON issue registers, SPA or APA deviation matrices, closing/economics packages, committee escalations, or transition reviews.
---

# M&A Deal Workbench Review

## Core Rule

Solve from the current task's prompt, answer template, and live deal-workbench records. Do not reuse values from prior examples. Filter every record by the exact `deal_id` in the prompt or template, and treat similarly named projects as unrelated.

Return only valid JSON conforming to the provided `input/payloads/answer_template.json`. Preserve the template's field names, stable IDs, enum values, ordering instructions, units, and rounding rules.

## One-Pass Workflow

1. Read the prompt and answer template first.
2. Identify the exact deal ID, client side, transaction form, requested output sections, applicable playbook or policy, and unit rules.
3. Gather all relevant workbench records before drafting the answer:
   - deal summary: value basis, purchase price/equity value, dates, parties, project and target names, currency, playbook or policy ID
   - current draft terms: include active/current terms only; ignore stale or wrong-project terms
   - playbook rules or policy thresholds: preferred, fallback, required, prohibited, restricted, and escalation positions
   - risk estimates: modeled exposure ranges, categories, source IDs, and whether a component should be included
   - consents and material contracts: required closing conditions, notices, post-closing items, amounts at risk, revenue, and source IDs
   - regulatory records: HSR status, required approvals, efforts covenant, outside date needs, and closing-condition requirements
   - employees: continuing populations, service credit, PTO liability, WARN or continuity risks
   - cap table: holder names, security classes, fully diluted percentages, and share counts
   - benchmarks, diligence findings, documents, and notes: use for benchmark support, missing-term evidence, and special issues
4. Compare draft terms and draft silence against the governing playbook or policy.
5. Build a source-backed issue matrix, closing package, transition review, or committee escalation using only issues requested by the prompt and template.
6. Validate calculations, IDs, enums, nulls, arrays, and JSON syntax before final output.

## API Use

Use the base URL supplied by the task environment. Common routes include:

- `GET /api/deals/<deal_id>`
- `GET /api/deals/<deal_id>/terms`
- `GET /api/deals/<deal_id>/documents`
- `GET /api/deals/<deal_id>/benchmarks`
- `GET /api/deals/<deal_id>/risk-estimates`
- `GET /api/deals/<deal_id>/cap-table`
- `GET /api/deals/<deal_id>/consents`
- `GET /api/deals/<deal_id>/employees`
- `GET /api/deals/<deal_id>/material-contracts`
- `GET /api/deals/<deal_id>/regulatory`
- `GET /api/deals/<deal_id>/diligence-findings`
- `GET /api/deals/<deal_id>/notes`
- `GET /api/playbooks/<playbook_id>/rules`
- `GET /api/policies/<policy_id>/thresholds`

If cross-table checks are helpful, use the read-only SQL endpoint only when the task permits it. Keep SQL scoped to the exact deal ID.

## Issue Selection

Follow the prompt's inclusion rules:

- For committee escalation tasks, include only current draft terms that are out of policy, restricted, or require committee approval. Exclude stale, in-policy, non-committee, and distractor terms unless the template asks for an exclusion list.
- For seller-side reviews, flag buyer draft provisions that exceed seller playbook limits, reduce seller protections, create unwanted closing optionality, or omit seller-required terms.
- For buyer-side reviews, flag draft provisions below buyer playbook requirements, missing buyer protections, consent or regulatory blockers, and economics or indemnity gaps.
- Include an absent term as `missing_required_term` when the prompt, template, playbook, policy, diligence record, document record, or deal facts show an affirmative term is required.
- Include `in_policy` issues only when the prompt or template asks for a complete position matrix that covers both deviations and acceptable fallback positions.
- Use empty `source_term_ids` for missing terms. Use stable record IDs from documents, diligence, regulatory, consent, employee, contract, benchmark, note, risk, playbook, or policy records to support missing-term findings when the template has source-record fields.

## Status, Risk, and Action

Use template enums exactly.

- `draft_exceeds_playbook`: a draft term is worse for the represented side because it is above an allowed cap, longer than allowed, broader than allowed, or gives the counterparty more leverage than the playbook permits.
- `draft_below_playbook`: a draft term is weaker than the represented side's required, fallback, or preferred buyer position.
- `out_of_policy`: a policy threshold, required trigger, restricted carveout, or committee rule is violated.
- `missing_required_term`: the current draft lacks a required protective provision.
- `in_policy`: the current draft fits the applicable rule and the output asks to report it.

Recommended action is usually `delete` for prohibited terms, `revise` for existing terms that need narrowing or improvement, `add` for missing required terms, and `accept` for requested in-policy items. Use explicit risk ratings from records when available; otherwise rank closing blockers, major economics gaps, regulatory conditions, financing optionality, customer consent failures, and employee continuity failures above lower-impact documentation gaps.

## Calculations

Use the basis specified by the prompt, deal record, policy, playbook, or template. If no other basis is stated, percentages for economics and indemnity are usually calculated from headline purchase price or equity value.

- Dollar amount: `round(percent / 100 * basis)` and output as an integer.
- Draft excess or shortfall: compare the draft to the relevant fallback threshold unless the template asks for both preferred and fallback deltas.
- Reverse or termination fee: multiply the required or draft fee percent by the value basis, then report excess or shortfall as directed by the represented side.
- Escrow or holdback: multiply the required percentage by the correct basis and tie release months to the playbook fallback, survival period, or unresolved finding requirement.
- Holder allocation: allocate each consideration component by fully diluted percentage; total consideration is the sum of allocated cash, stock, and other included components. Follow the prompt's holder percentage precision.
- Consent totals: sum only required closing consents for closing-condition amounts at risk. Exclude notice-only and post-closing covenant records unless the template asks for non-blocking lists.
- Material contract totals: sum annual revenue only for material contracts that require pre-closing consent or must be closing conditions.
- Employee totals: use employee records for continuing employee counts, service-credit IDs, PTO liability, and WARN-risk IDs.
- Risk totals: sum modeled exposure lows and highs only for components the template requests. Do not double-count a negotiation delta as modeled exposure unless the records classify it that way.
- Benchmarks: report the benchmark metric, sample size, median, upper quartile, and position using workbench benchmark records; use `not_applicable` or the template's null convention when no benchmark applies.

## Common Output Patterns

For APA seller issue registers, compare the buyer draft to seller playbook positions on financing conditions, reverse break fees, escrow, indemnity cap and basket, survival, restrictive covenants, employee continuity, transition services, tax allocation, governing law/forum, consent conditions, materiality scrape, and HSR covenants when requested. Prioritize closing certainty and high-dollar economics before medium-risk documentation points unless the template specifies a sort order.

For SPA closing and economics packages, cover purchase-price components, cap-table allocation, indemnity, escrow, survival, materiality scrape, working-capital adjustment, consents, material contracts, employment covenants, restrictive covenants, D&O tail, expenses, regulatory conditions, closing blockers, tradeable issues, and readiness status.

For committee escalation packages, compare current draft terms to policy thresholds and committee restrictions. Provide draft metrics, policy metrics, deltas, benchmark support, exposure, recommendation, required conditions, excluded in-policy terms or categories when requested, aggregate risk counts, quantified exposure, and negotiation priority.

For carveout transition reviews, focus on transition services scope, duration and fees, IP/trademark/domain transition, employee continuity, required consent conditions, outside date or regulatory extensions, Section 1060 allocation, transfer taxes, governing law/forum, redline requirements, operational risk, quantified exposures, and protected business outcomes.

For buyer-side deviation matrices, cover indemnity cap and basket, survival and knowledge qualifiers, materiality scrape, escrow/holdback release, consent closing conditions, HSR, and material contracts when requested. Use priority ranks that put closing blockers and required regulatory or consent conditions before lower-risk economics and acceptable in-policy items.

## JSON Assembly Checks

- Keep all required top-level fields from the template.
- Use `null`, empty arrays, or empty objects only where the template allows them.
- Use stable IDs from the workbench and stable issue or redline IDs from the template.
- Sort arrays according to template instructions; otherwise sort by requested priority or stable issue ID.
- Dates must be `YYYY-MM-DD`.
- Currency must be integer dollars.
- Percent points and holder percentages must follow the prompt's precision.
- Do not include markdown, citations, comments, or explanatory prose outside the JSON.
