---
name: ma-deal-workbench
description: Use this skill for M&A deal workbench tasks that ask counsel to prepare structured JSON issue registers, closing or economics packages, committee escalation memos, transition reviews, SPA or APA deviation matrices, or playbook/policy comparisons from deal APIs. Trigger whenever the prompt mentions a deal ID, buyer-side or seller-side counsel, APA, SPA, M&A Committee, consents, HSR, cap tables, material contracts, risk estimates, benchmarks, or an answer_template JSON.
compatibility: Python 3 standard library only. Optional helper script in scripts/collect_workbench.py.
---

# M&A Deal Workbench Structured JSON

Use this skill when the user asks for a legal deal-workbench analysis and final output must be strict JSON. The recurring task is to gather workbench records for one deal, compare current draft terms against the applicable playbook or policy, compute derived economics, and emit exactly the schema in the provided answer template.

## Operating Rules

- Stay on the deal ID named in the prompt. Do not use records from similarly named projects or unrelated deals.
- Read `input/payloads/answer_template.json` before drafting the answer. Treat it as the output contract: field names, nesting, enums, ordering instructions, rounding, and nullability come from the template.
- Use current workbench records as source of truth. Notes, benchmarks, risk estimates, diligence findings, consents, and material contracts can explain or quantify an issue, but source term IDs should come from current draft terms unless the template asks for other IDs.
- Treat missing draft language as an issue when the applicable playbook, policy, prompt, or template requires an affirmative provision.
- Return only valid JSON. Do not include markdown, citations outside JSON, or explanatory prose.

## Collect Sources

First identify from the prompt:

- `deal_id`
- client side: buyer, seller, committee, or deal-team package
- agreement/work product: APA, SPA, committee memo, transition review, deviation matrix, closing package
- playbook or policy ID if named
- required endpoints and output template path

Fetch the deal-specific API records named in the prompt. If a base URL placeholder is used and `environment_access.md` is available in the task workspace, read it to obtain the base URL and allowed endpoints.

You may use the helper script:

```bash
python skill/scripts/collect_workbench.py --base-url "$TASK_ENV_BASE_URL" --deal-id "$DEAL_ID" --playbook-id "$PLAYBOOK_ID" --policy-id "$POLICY_ID" --out workbench_sources.json
```

Omit `--playbook-id` or `--policy-id` when not applicable or unknown. The script uses only standard-library HTTP calls, fetches deal-scoped endpoints, and records missing endpoints without discarding successful responses. If the prompt gives a read-only SQL endpoint and token, use SQL only for cross-checks such as totals, current-vs-stale filters, or source ID reconciliation; do not rely on SQL to bypass the public API record model.

## Source Map

Build a compact source map before writing JSON:

- Deal economics: headline value, equity value, upfront cash, stock value, milestone value, signing and meeting dates.
- Current draft terms: term ID, category, clause reference, metric values, draft silence, status/currentness.
- Playbook or policy rules: preferred position, fallback/threshold position, required terms, required conditions, restricted changes.
- Consents and material contracts: condition type, notice-only status, amount at risk, annual revenue, counterparty, linked contract IDs.
- Regulatory: HSR requirement, approval status, closing-condition requirement, covenant standard.
- Employees: continuing or affected employee count, service-credit population, PTO liability, WARN/retention risk.
- Diligence, risk estimates, benchmarks, documents, and notes: use for quantified exposure, rationale, and exclusions.

Filter aggressively. For committee escalations, include only current draft terms that are out of policy or restricted for approval; list excluded in-policy categories only when the template asks. For deviation matrices and issue registers, include in-policy rows only when the prompt or template clearly requires full coverage.

## Compare Draft To Rules

Classify each position from the client perspective:

- `missing_required_term`: the draft is silent but the rule requires an affirmative provision, closing condition, allocation method, forum, escrow, covenant, or protection.
- `draft_below_playbook`: the draft gives the client less protection or economics than the fallback/threshold position, such as a buyer indemnity cap below buyer fallback or a required closing condition omitted from a broad consent clause.
- `draft_exceeds_playbook`: the draft imposes more burden or leakage on the client than the rule permits, such as seller escrow/cap/survival exposure above fallback or overbroad buyer termination rights.
- `out_of_policy`: use when the policy framework or template describes the item as a restricted or committee-level deviation.
- `in_policy`: use only when the task asks for full coverage and the current draft matches an accepted fallback or approved position.

For recommendation fields, choose the action that matches the required legal move: add absent protection, revise an overbroad or under-protective clause, delete an unacceptable condition, accept in-policy fallback, reject restricted changes that cannot be approved, or approve with stated conditions.

## Calculations

Use the basis specified by the prompt, template, or source record. If no different basis is stated, percentage-dollar calculations normally use the deal headline purchase price or equity value. Keep percentages as percent points, not fractions.

Common formulas:

- amount from percent: `round(base_dollars * percent_points / 100)` as an integer dollar amount.
- buyer shortfall to fallback: `fallback_amount - draft_amount` when the draft is below buyer fallback.
- seller delta to fallback: `draft_amount - fallback_amount` when the draft exceeds seller fallback.
- reverse break fee shortfall: `required_fee_amount - draft_fee_amount`.
- month delta: draft months minus fallback months when the draft is longer than allowed, or preferred/fallback months minus draft months when the client needs longer protection.
- holder allocation: allocate each consideration component by fully diluted percentage or as-converted shares, then sum cash plus stock plus other consideration required by the template.
- consent total: sum only required closing consents, not notice-only or post-closing covenants, unless the template requests those separately.
- material-contract revenue: sum annual revenue only for contracts requiring pre-closing consent or specific closing conditions.
- exposure summary: include only risk estimates that correspond to included issues; keep excluded components in the requested exclusion fields when present.

Respect the requested rounding precision: integer dollars, integer months, and percentage decimals exactly as the prompt/template states. Reconcile counts against the arrays you output.

## Populate JSON

Start from the template shape and fill every required field:

- Preserve enum strings exactly.
- Use `null` for unknown or not applicable nullable values, not empty strings or invented placeholders.
- Use booleans for yes/no fields when the template expects booleans; use the template's `"yes" | "no"` strings only when it explicitly does.
- Use stable workbench IDs for `source_term_ids`, consent IDs, contract IDs, employee IDs, finding IDs, risk estimate IDs, and synthetic regulatory blockers where the template permits them.
- Keep arrays ordered as instructed. If no explicit ordering is given, use a defensible workflow order: closing blockers and regulatory issues first, then high-risk economics, then employee/transition/tax/forum cleanup.
- For redline or must-have-term objects, express the required position as normalized machine-readable fields rather than prose.

## Final Validation

Before final output:

1. Parse the JSON with a real parser.
2. Compare top-level keys and required nested keys to `answer_template.json`.
3. Check enum values, booleans, nulls, and number types.
4. Recompute all totals, counts, deltas, and priority ranks from the output arrays.
5. Confirm every included source ID belongs to the requested deal.
6. Confirm no training-example project IDs, holder names, dollar values, or answer records have been reused.

If a fact is absent from the workbench after checking the relevant endpoints, use the template's null or not-found status rather than guessing.
