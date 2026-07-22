---
name: deal-workbench-ma-review
description: Prepare structured M&A deal-workbench JSON deliverables from a task prompt and answer template, including buyer or seller APA/SPA issue registers, closing and economics packages, committee escalation memoranda, carveout transition reviews, and deviation matrices. Use when Codex must gather deal records, draft terms, playbook or policy rules, consents, regulatory facts, employees, material contracts, benchmarks, risk estimates, diligence records, notes, and then return schema-conforming JSON with calculated amounts, priorities, blockers, and stable source IDs.
---

# Deal Workbench M&A Review

## Core Workflow

1. Read the user prompt and the provided answer template before drafting anything.
2. Treat the answer template as controlling. Preserve required top-level fields, enum spellings, stable issue/redline IDs, nullability, array names, and ordering instructions.
3. Gather only records for the target deal ID. Use the workbench UI, APIs, or allowed read-only query access named in the task prompt. Do not import facts from similarly named or adjacent projects.
4. Build a compact source map: deal economics, current draft terms, playbook or policy thresholds, consents, regulatory records, employees, material contracts, diligence findings, benchmarks, risk estimates, notes, and documents.
5. Compare current draft terms to the applicable playbook or policy. Exclude stale terms unless the template explicitly asks to list excluded distractors.
6. Add missing-required-term issues only when the prompt, template stable IDs, playbook/policy, or surrounding deal records show that an affirmative provision is needed.
7. Return only valid JSON. Do not include narrative outside the JSON.

## Template Fidelity

- If the template is an example object with placeholders, fill that object shape directly.
- If the template describes `required_top_level_fields` or `required_output_shape`, output that described shape unless the prompt expressly asks to retain schema metadata.
- Use exactly the template enums for statuses, risk ratings, actions, blocker types, final positions, posture, and recommendation fields.
- Use stable IDs from the template when supplied. Use source IDs from workbench records for terms, consents, material contracts, employees, findings, benchmarks, risk estimates, notes, and documents.
- Keep arrays in the template-requested order. If no order is stated, prefer deterministic ordering: priority fields for priority lists, stable ID order for issue/redline lists, and source-record order for factual lists.
- Use `null` for unavailable scalar values and `[]` for unavailable list values when the template permits them. Do not invent values for fields marked as not found in current records.

## Deal Analysis

- Seller-side APA review: flag buyer financing conditions, missing or inadequate reverse break fees, excessive escrow or indemnity exposure, long survival, broad consent termination rights, TSA duration/fee gaps, employee cherry-picking or PTO shifts, missing IP/domain transition, tax allocation, transfer-tax, outside-date, governing-law, and forum protections.
- Buyer-side SPA review: flag indemnity cap and basket shortfalls, short survival or unsupported fallback survival, missing knowledge-qualifier treatment, no or fallback-only materiality scrape, missing escrow/holdback mechanics, consent and material-contract condition gaps, HSR condition gaps, employee service-credit/PTO issues, founder/executive restrictive covenants, D&O tail, and expense allocation.
- Committee escalation: include only current draft terms that are out of policy or restricted for committee approval. Exclude stale, in-policy, or non-committee distractors, but list them only if the template has fields for excluded items.
- Carveout transition review: treat transition services, stranded-cost reimbursement, shared IP/systems, trademarks, domains, customer consents, employee continuity, Section 1060 allocation, transfer taxes, outside date, and governing-law/forum as separate issues when the template provides stable IDs for them.

## Calculations

- Use the deal's headline value or purchase price as the default dollar basis unless a source record states a different basis.
- Keep currency as integer dollars. Round percentages to the precision requested by the prompt/template. Keep month values as integers.
- Compute draft, preferred, fallback, delta, and shortfall amounts from the stated percentage and basis.
- For buyer positions, a seller draft below buyer fallback is usually `draft_below_playbook`; for seller positions, a buyer draft above seller fallback is usually `draft_exceeds_playbook`.
- For cap tables, allocate cash, stock, and total consideration from the template-requested holder percentage or as-converted share basis; ensure allocations reconcile to the deal economics.
- For consents, distinguish required closing consents from notice-only or post-closing items. Sum required closing consent exposure only from records marked required for closing unless the template asks for all notices.
- For material contracts, separate consent-required contracts from notice-only contracts. Sum conditioned revenue from the contracts that must be satisfied before closing.
- For risk totals, include only the risk estimate categories requested by the template. Avoid double-counting the same estimate when multiple issues point to one exposure category.

## Final QA

Before responding, verify:

- The output parses as JSON and has no prose wrapper.
- Every template-required key is present.
- Enum values match the template exactly.
- Stable issue, redline, blocker, source, and record IDs are copied exactly.
- Stale records and similarly named deals are not used.
- Dollar, percent, month, date, count, and holder-allocation values follow the requested precision.
- Summary counts equal the included issue/blocker arrays.
