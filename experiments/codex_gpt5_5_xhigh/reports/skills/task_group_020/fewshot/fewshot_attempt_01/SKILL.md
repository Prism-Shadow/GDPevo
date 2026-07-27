---
name: ma-deal-workbench
description: Prepare schema-exact JSON work products from an M&A deal workbench. Use when Codex is asked to review APA/SPA terms, seller or buyer playbooks, committee policy thresholds, closing conditions, economics, transition packages, consents, regulatory facts, diligence findings, benchmarks, risks, notes, or related deal records and return only JSON conforming to a provided answer_template.json.
---

# M&A Deal Workbench JSON

## Core Workflow

1. Read the user prompt and the provided `input/payloads/answer_template.json` before querying data. Extract:
   - deal ID, project name, client side, counterparty, work product type, and applicable playbook or policy ID;
   - required units, rounding, enum values, stable issue IDs, ordering rules, and required top-level fields;
   - whether the task asks for all issues, only escalations, only transition issues, closing readiness, economics, or a deviation matrix.

2. Reach the running workbench only through the base URL supplied by the task or environment access file. Prefer the documented JSON APIs over the UI. Query all relevant records for the requested work product, commonly:
   - `GET /api/deals/<deal_id>`
   - `GET /api/deals/<deal_id>/terms`
   - `GET /api/playbooks/<playbook_id>/rules` or `GET /api/policies/<policy_id>/thresholds`
   - `GET /api/deals/<deal_id>/risk-estimates`
   - `GET /api/deals/<deal_id>/benchmarks`
   - `GET /api/deals/<deal_id>/consents`
   - `GET /api/deals/<deal_id>/employees`
   - `GET /api/deals/<deal_id>/material-contracts`
   - `GET /api/deals/<deal_id>/regulatory`
   - `GET /api/deals/<deal_id>/diligence-findings`
   - `GET /api/deals/<deal_id>/cap-table`
   - `GET /api/deals/<deal_id>/documents`
   - `GET /api/deals/<deal_id>/notes`

3. Use read-only SQL only for cross-table checks or to find records not exposed cleanly by a listed endpoint. Use the provided query token and keep queries scoped to the requested deal ID.

4. Build a source map before drafting the JSON:
   - draft terms by term ID, category, clause reference, status/currentness, metric, basis, and text;
   - playbook or policy rules by issue/category, preferred position, fallback, threshold, required conditions, and action;
   - factual support by stable source IDs from consents, contracts, employees, regulatory records, diligence findings, risk estimates, benchmarks, documents, and notes.

## Legal Analysis Pattern

Compare the current draft against the client-side rule set. Treat draft silence as a missing issue when the playbook or policy requires an affirmative term and deal facts show the term is relevant. Use an empty `source_term_ids` array for missing draft terms, and include non-term source IDs where the template supports them.

Classify status from the client's perspective:

- `in_policy`: draft matches an acceptable position or fallback.
- `out_of_policy`: draft conflicts with a policy threshold or restricted position.
- `missing_required_term`: required protection is absent.
- `draft_below_playbook`: draft gives the client less protection or economics than the applicable fallback.
- `draft_exceeds_playbook`: draft imposes more burden, cost, exposure, duration, scope, or conditionality on the client than allowed.

Use the template's enum values exactly. If the template gives stable issue IDs, final positions, redline IDs, blocker types, or condition IDs, choose from those values rather than inventing new labels.

Common buyer-side protections to test include: higher indemnity cap and basket support, longer survival, materiality scrape, escrow or holdback, working-capital adjustment, required consents, material-contract closing conditions, HSR clearance, limited regulatory efforts, service credit and PTO treatment, founder or executive restrictive covenants, D&O tail, and seller expense allocation.

Common seller-side protections to test include: no buyer financing condition, reverse break fee when buyer financing or regulatory closing risk remains, lower escrow and indemnity cap, shorter survival, deductible basket, narrow restrictive covenants, all-employee transition process with service credit and PTO allocation, transition services limits and cost recovery, IP/trademark/domain transition protections, Section 1060 allocation, transfer-tax split, outside-date extension where regulatory approval is required, and the seller-preferred governing law and forum.

For committee or escalation packages, include only current draft terms that are out of policy, restricted, or otherwise routed for approval. Exclude stale terms, in-policy terms, and non-committee distractors, but list excluded terms or categories if the template asks for them.

## Calculations

Use the value basis specified by the prompt, template, deal record, rule, or source record. If no alternate basis is stated, calculate percentages from the deal headline value or purchase price requested by the prompt. Keep these conventions:

- currency amounts: integer dollars;
- percent fields: percent points, rounded exactly as the template instructs;
- months, days, counts, and years: integers;
- holder allocation: apply fully diluted or as-converted percentages to each consideration component, then reconcile totals to the stated economics;
- shortfall to fallback: fallback amount minus draft amount when the client needs more protection, or draft amount minus fallback when the client needs less burden;
- negotiation delta: only count quantified deltas requested by the template, and avoid double-counting the same exposure through both a term and a summary;
- exposure totals: sum only included risk-estimate components and document excluded components when the template asks.

When a source provides a specific quantified finding, consent amount at risk, annual revenue, PTO liability, stranded cost, privacy exposure, or risk range, use that source value instead of recomputing from purchase price.

## Closing And Operational Review

For consents and material contracts, distinguish required closing consents from notices and post-closing covenants. Include notice-only records only in non-blocking or excluded fields. Use stable consent and contract IDs, not paraphrases.

For regulatory records, determine whether HSR or another approval is required, whether clearance should be a closing condition, and whether hell-or-high-water or a limited efforts covenant is required by the relevant client position.

For employee records, aggregate only the employee groups relevant to the requested issue. Capture continuing employee count, field or operations groups, service credit, PTO liability, WARN risk, retention, cherry-picking rights, and comparable terms only when supported by source records or rules.

For transition and carveout issues, test TSA duration, scope, fee model, stranded overhead recovery, clean termination rights, IP/trademark licenses, domain redirects, tax allocation, transfer taxes, customer consent termination rights, outside dates, and forum provisions.

## JSON Assembly

Populate the answer directly in the shape of `answer_template.json`. Preserve all required keys, use `null` where the schema calls for a nullable value, and omit narrative outside the JSON. Sort arrays by the template's explicit ordering rule; otherwise use priority order for negotiation work products and stable ID order for issue registers or redline lists.

Before finalizing:

1. Recheck every non-null value against a source record, rule, calculation, or template instruction.
2. Recompute all counts from the arrays actually emitted.
3. Confirm high, medium, low, missing-term, draft-below, draft-exceeds, blocker, exposure, and issue totals.
4. Validate that enum strings and stable IDs exactly match the template or workbench records.
5. Return valid JSON only.
