---
name: ma-deal-workbench-json
description: Solve M&A deal workbench tasks that require strict JSON outputs for APA, SPA, merger, carveout, closing-readiness, issue-register, deviation-matrix, committee-escalation, consent, employee, indemnity, escrow, tax, regulatory, and transition-review analyses. Use when a prompt references an M&A deal workbench, deal APIs, playbooks, policies, draft terms, benchmarks, risk estimates, or an answer_template.json schema.
---

# M&A Deal Workbench JSON

Use this skill to turn a deal-workbench prompt and answer template into one valid JSON answer. Work from the live deal records and the prompt's schema; do not rely on memorized example outputs.

## Start

1. Read the user prompt and `input/payloads/answer_template.json` before fetching data.
2. Extract the `deal_id`, client side, transaction type, named playbook or policy, requested categories, required ordering, units, precision, and enum spellings.
3. Resolve `<TASK_ENV_BASE_URL>` from the prompt or environment. If it is not explicit, try `TASK_ENV_BASE_URL`, then `http://task-env:9020/`.
4. Fetch the deal bundle. From this skill directory, run:

```bash
python scripts/fetch_workbench.py DEAL_ID --base-url "$TASK_ENV_BASE_URL" --output /tmp/deal_bundle.json
```

If your current directory is not the skill directory, use the absolute path to `scripts/fetch_workbench.py`.

If the script is unavailable, manually GET the deal, terms, documents, benchmarks, risk estimates, cap table, consents, employees, material contracts, regulatory facts, diligence findings, notes, and the deal's playbook rules or policy thresholds.

Use `POST /api/query` with the read-only token only for cross-table checks that the REST records do not make clear. Filter SQL by the active `deal_id`; do not run broad discovery queries.

## Records To Use

Treat the workbench as the source of truth:

- `deal`: parties, client side, transaction type, value fields, dates, playbook ID, policy ID, and project metadata.
- `draft_terms`: current paper by `category`, `term_id`, `clause_ref`, `basis`, `numeric_value`, `unit`, and `draft_value`. Use current terms unless the prompt asks for stale history.
- `playbook.rules`: client preferred and fallback positions, limit units and values, required actions, basis, and risk defaults.
- `policy.thresholds`: committee approval requirements, restricted flags, threshold values, threshold units, and policy standards.
- `consents`: required-for-closing flags, risk ratings, counterparties, contracts, and amount at risk.
- `material_contracts`: consent requirement, annual revenue, anti-assignment, change-of-control, and contract IDs.
- `employees`: employee groups, counts, PTO liabilities, service-credit requirements, WARN risk, and draft treatment.
- `regulatory`: HSR requirement, approval type, threshold basis, and hell-or-high-water position.
- `benchmarks`: category or metric support, median, upper quartile, sample size, and notable precedent.
- `risk_estimates`: low/high modeled exposure by category and source estimate ID.
- `diligence_findings`, `notes`, and `documents`: support for missing mechanics, special indemnities, expense allocation, D&O tail, tax, forum, transition, and other terms not captured as draft-term rows.

Always preserve stable source IDs from these records in the output. For a missing required term, use an empty `source_term_ids` array and cite the relevant non-term records if the template provides a place for them.

## Build The Issue Set

Let the prompt and template decide what rows belong in the answer.

- If the prompt says to identify only out-of-policy, restricted, or current draft terms needing committee approval, exclude stale, in-policy, and non-committee distractors. Populate any template fields that ask for excluded term IDs or categories.
- If the prompt says to cover a set of buyer or seller positions, include every requested category even when one row is in policy.
- If the prompt asks for transition, carveout, closing-readiness, or issue-register coverage, treat draft silence as an issue whenever the playbook, policy, prompt, regulatory facts, consents, employee records, material contracts, documents, diligence findings, or notes show an affirmative provision is needed.
- Do not invent issue IDs. Use the stable IDs and enum values supplied by the answer template.

Common missing-term triggers include HSR clearance conditions, material consent closing conditions, material-contract consent conditions, escrow or holdback support, reverse break or financing-risk protection, employee continuity, service credit and PTO allocation, D&O tail and expense allocation, transition services limits and cost recovery, IP or domain transition terms, tax allocation, transfer-tax split, outside-date extension, and governing law/forum.

## Compare Positions

Use the client side to interpret direction:

- Seller-side reviews usually mark a buyer draft as `draft_exceeds_playbook` when it is higher, longer, broader, or more conditional than the seller fallback allows. Mark `draft_below_playbook` when a seller protection, fee, cost recovery, or closing-certainty protection is absent or too low.
- Buyer-side reviews usually mark a seller draft as `draft_below_playbook` when indemnity, survival, escrow, consent, material-contract, regulatory, employee, or other buyer protections are below fallback or missing. Mark `in_policy` only when the draft satisfies the requested fallback or accepted position.
- Committee-policy reviews include terms that breach numeric thresholds or restricted policy standards. Restricted changes can be non-numeric, such as removing a fiduciary trigger or adding unapproved carveouts.
- Use exact template statuses: `missing_required_term` for absent needed terms, `out_of_policy` for policy breaches, `draft_exceeds_playbook` or `draft_below_playbook` for playbook comparisons, and `in_policy` only when the row should remain in the matrix.

When preferred and fallback values are embedded in prose rather than numeric fields, parse the relevant number from the playbook or policy text and keep the basis from that rule.

## Calculate

Follow the prompt's unit instructions exactly.

- Percent-derived dollars: `basis_amount * percent_points / 100`, rounded to integer dollars. Use the rule's basis where stated; otherwise use the deal headline value unless the prompt specifies purchase price, equity value, enterprise value, upfront cash, identified findings, or another basis.
- Holder allocation: multiply upfront cash, stock value, and total consideration by each holder's fully diluted percentage. Keep cap-table percentages in the precision requested by the prompt; these are often decimals rather than percent points.
- Seller delta to fallback: for caps, escrows, survival, TSA duration, or similar overreaches, subtract fallback from draft. For missing or below-playbook seller protections such as a fee, calculate the required shortfall from zero or the draft value when the template asks for a shortfall.
- Buyer shortfall: subtract draft from fallback or preferred as requested. For missing escrow or holdback, the shortfall is the required escrow amount if the template treats the draft as absent.
- Consent amount at risk: sum records required for closing. Keep notice-only and post-closing covenant records separate when the template asks.
- Material-contract revenue conditioned: sum annual revenue for material contracts whose consent is required as a closing condition. Exclude notice-only contracts unless requested.
- Employee metrics: sum employee counts and PTO liabilities only for the groups requested by the prompt or template.
- Risk exposures: sum only the modeled risk-estimate categories that the output asks to include. List excluded exposure categories when the template asks for them.
- Counts: compute counts from the rows you output. If a template uses an "out of policy" total for a matrix, count all non-`in_policy` position rows unless the prompt defines it more narrowly.

Use `null` for unavailable scalar values, empty arrays for no IDs, and empty objects only when the template expects an object.

## Risk, Recommendations, And Readiness

Start from workbench risk ratings, playbook risk defaults, and policy approval requirements, then adjust based on the requested business task.

- Closing certainty, HSR, required consents, material-contract blockers, financing conditions, reverse-break protection gaps, broad consent termination rights, and major indemnity or escrow deltas usually deserve the highest priority.
- Employee continuity, PTO, service-credit, WARN, TSA duration, transition-cost recovery, and IP/domain transition issues are high when they affect post-closing operations or carveout separation.
- Tax allocation, transfer-tax split, governing law/forum, and narrow drafting gaps are often medium unless the workbench assigns a higher risk.
- Closing readiness is `NOT_READY` when required consents, HSR clearance, material-contract conditions, or core economics/indemnity mechanics remain blockers. Use `READY_WITH_CONDITIONS` for non-blocking open items and `READY` only when no required blocker remains.

For priority arrays, order by negotiation importance, not by JSON row order, unless the template gives a specific ordering rule. Put closing/regulatory blockers and high quantified exposure before tradeable drafting cleanups.

## Output Discipline

1. Fill the template shape exactly. Do not add fields, comments, Markdown, or explanatory prose.
2. Use exact enum spellings from the template. Normalize source data spelling only when the template requires an enum.
3. Keep stable IDs from the workbench, not generated labels, for terms, consents, contracts, employees, findings, risks, documents, policies, and playbooks.
4. Re-check arithmetic, counts, nulls, arrays, and precision against the prompt.
5. Validate the final JSON before answering:

```bash
python -m json.tool /tmp/answer.json >/tmp/answer.validated.json
```

Return only the JSON object.
