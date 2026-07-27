---
name: ma-deal-workbench-review
description: Analyze M&A deal-workbench records and produce strict JSON issue registers, deviation matrices, closing packages, committee escalations, or transition reviews for APA, SPA, merger, and carveout deal tasks. Use when a prompt asks Codex to compare draft transaction terms against buyer/seller playbooks or committee policies, quantify purchase-price-based positions, classify consents/regulatory/employee/material-contract blockers, allocate consideration, or summarize deal risk using a provided answer template.
---

# M&A Deal Workbench Review

## Core Workflow

1. Read the user prompt and answer template before querying data. Treat the template as the controlling schema for keys, enums, units, ordering, stable issue IDs, and whether to include metadata fields.
2. Gather every deal record relevant to the prompt: deal summary, draft terms, playbook rules or policy thresholds, risk estimates, employees, consents, material contracts, regulatory facts, diligence findings, cap table, benchmarks, documents, and notes.
3. Use stable IDs exactly as supplied by records or the template. Use empty arrays for missing draft terms when the template asks for source term IDs.
4. Compare only current draft terms unless the task explicitly asks for stale or historical terms. Exclude stale, in-policy, non-committee, or non-task distractors.
5. Treat a missing draft term as an issue when the playbook, policy, prompt, or surrounding deal facts require an affirmative provision.
6. Return only valid JSON matching the answer template. Do not include narrative outside the JSON.

## Comparisons

- For buyer-side positions, classify seller drafts below buyer fallback as `draft_below_playbook`; classify absent required protections as `missing_required_term`; classify accepted fallback terms as `in_policy`.
- For seller-side positions, classify buyer drafts above seller caps, longer than seller fallback periods, or broader than seller closing conditions as `draft_exceeds_playbook` or `out_of_policy` according to template wording.
- For committee escalations, include only current terms that exceed a restricted threshold or otherwise require the specified approval body. Exclude stale, below-threshold, and non-committee terms even if they are related.
- Preserve template order when given. Otherwise order issue rows by stable issue ID, source term ID, or explicit priority, whichever the template requests.

## Calculations

- Use the deal field that matches the stated basis. Use `headline_value` for purchase price, headline purchase price, enterprise value, or equity value unless the prompt or record states a different base such as upfront cash, stock value, or identified findings.
- Calculate percent amounts as `round(base * percent / 100)` and output integer dollars.
- Output percentages in the template's unit: percent points for legal thresholds; holder percentages to the precision requested by the prompt.
- For cap shortfalls, calculate buyer shortfall as required amount minus draft amount. For seller excess, calculate draft amount minus fallback amount.
- Sum employee counts and PTO liabilities from employee records when totals are requested; use subgroup totals when a field names a specific employee group.
- For holder allocation, allocate each consideration component separately using cap-table percentages or as-converted shares as the template directs, then verify totals tie back to deal economics.

## Deal Record Mapping

- Consents with `required_for_closing: yes` are closing blockers unless the prompt directs a broader buyer condition. If the draft excludes a named agreement group that the buyer prompt treats as material, include those excluded source IDs and update blocker totals.
- Material contracts with consent-required or change-of-control constraints support material-contract closing conditions. Notice-only records are non-blocking unless the prompt identifies them as excluded required contracts.
- Regulatory records control HSR fields. If HSR is required and the draft has no clearance condition, include the missing condition using the template's stable ID or a clear synthetic ID only when the template permits one.
- Risk estimates map by category: closing certainty for consent, regulatory, financing, and deadline risk; indemnity leakage for cap, survival, basket, scrape, and special indemnity risk; transition disruption for TSA, carveout separation, IP/domain transition, and employee transition risk.
- Avoid double-counting the same risk-estimate component across multiple issue rows. For aggregate modeled exposure, sum the distinct risk categories included by the task scope.
- Benchmarks support only categories with a matching benchmark metric. Use `not_applicable` or null-style values when no benchmark supports the issue and the template permits that.

## Output Discipline

- Use exact enum strings from the template, including casing.
- Use `null` for unavailable scalar values and `[]` for unavailable arrays unless the template says otherwise.
- Prefer stable record IDs over invented descriptions in ID fields. Keep invented IDs short and deterministic only when the template requires an ID and no source ID exists.
- Keep normalized or free-form objects conservative: use source field names, template vocabulary, and numeric facts rather than long prose.
- Before finalizing, check that counts equal the arrays and classifications in the JSON, dollar totals reconcile, and all required template fields are present.
