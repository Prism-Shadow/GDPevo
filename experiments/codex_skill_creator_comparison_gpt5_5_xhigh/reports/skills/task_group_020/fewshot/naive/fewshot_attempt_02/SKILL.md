---
name: ma-deal-workbench-json
description: Solve M&A deal workbench tasks that require schema-exact JSON outputs from deal APIs, playbooks, policies, diligence, consents, regulatory, employee, benchmark, risk, and draft-term records.
---

# M&A Deal Workbench JSON Solver

Use this skill when the user asks for an M&A legal or deal-team package based on a running deal workbench and an `answer_template.json`.

## Core workflow

1. Read the prompt and `input/payloads/answer_template.json` first.
2. Extract the deal ID, client side, requested package type, playbook or policy ID, required endpoints, units, rounding rules, allowed enums, stable IDs, and ordering instructions from the prompt/template.
3. Fetch only records for the requested deal. Do not assume similarly named projects apply.
4. Build the answer from current workbench records, not from memory. Return only valid JSON conforming to the template.

Useful endpoint patterns are:

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

If the prompt permits read-only SQL, use `POST /api/query` only for cross-checks. Keep queries read-only and filtered to the requested deal ID.

## Record extraction checklist

For every task, gather:

- Deal economics: headline value, equity value, purchase price, upfront cash, stock value, milestones, signing/meeting dates, parties, project and target names.
- Current draft terms: term IDs, clause refs, category, current metric, basis, status, and whether any record is stale or superseded.
- Playbook or policy rules: preferred positions, fallback positions, thresholds, required affirmative terms, restricted terms, and approval conditions.
- Risk estimates: low/high exposure ranges and source IDs, keeping only components requested by the template.
- Benchmarks: sample size, median, upper quartile, and metric basis when the template asks for market support.
- Consents and material contracts: required vs notice-only vs post-closing items, amount at risk, annual revenue, counterparty, contract IDs, and condition type.
- Regulatory records: HSR requirement, clearance status, industry review, effort covenant, hell-or-high-water position, outside-date implications, and closing condition need.
- Employee records: continuing or affected employees, service-credit requirement, PTO liability, WARN risk, retention groups, and restrictive-covenant coverage.
- Diligence/documents/notes: missing provisions, unresolved findings, transaction expenses, D&O tail, TSA scope, IP/domain transition, tax allocation, transfer tax, governing law/forum, and closing-readiness notes.

## Issue selection

Use the template's issue IDs and enums. Do not invent IDs when the template supplies stable values.

- Include only the subject areas requested by the prompt.
- Use `source_term_ids: []` for missing required terms.
- Treat draft silence as an issue only when the playbook, policy, prompt, or surrounding deal facts require an affirmative provision.
- Exclude stale, superseded, non-current, in-policy, or non-scope records unless the template explicitly asks to list excluded items.
- For committee escalation tasks, include only current draft terms that are out of policy or restricted for committee approval; summarize excluded in-policy terms separately only if requested.

Status classification:

- `missing_required_term`: no current draft term covers a required affirmative position.
- `draft_exceeds_playbook`: the draft is more burdensome than the client-side seller/playbook fallback permits, or otherwise exceeds an allowed limit.
- `draft_below_playbook`: the draft gives the client less protection than the buyer/playbook fallback requires, or omits part of a required protective package.
- `out_of_policy`: a current draft term breaches a policy threshold or restricted-term rule.
- `in_policy`: the draft satisfies the applicable rule and the output schema asks for in-policy items.

Recommended actions should match the legal move: `delete` for prohibited terms, `revise` for terms needing narrowing or stronger protection, `add` for missing provisions, `accept` for in-policy terms, and committee approval enums only where escalation is requested.

## Common M&A analyses

Indemnity, survival, basket, scrape, escrow:

- Compare draft percentages/months/type against preferred and fallback rules.
- For seller-side review, quantify excess over fallback when the draft is too high or too long.
- For buyer-side review, quantify shortfall to fallback and preferred when the draft is too low or incomplete.
- Check basket type, knowledge qualifiers, materiality scrape scope, escrow agent, release trigger, and survival linkage.

Closing consents and material contracts:

- Required closing consents become blockers when unresolved or when the draft condition excludes them.
- Notice-only and post-closing covenants are not blockers unless the template separately asks for tradeable or non-blocking items.
- Material-contract conditions should use stable contract IDs and sum only the contracts requiring consent/condition treatment.

Regulatory:

- If HSR or another clearance is required and the draft lacks a closing condition, classify it as missing or below playbook for buyer-side tasks.
- For seller-side tasks, flag overbroad buyer termination rights or regulatory effort gaps according to the seller playbook.
- Record hell-or-high-water only from the draft, playbook, or regulatory rule; do not infer it from deal size alone.

Employees and restrictive covenants:

- Total continuing or affected employees from employee records, not from narrative estimates.
- Sum PTO liabilities for the covered employee group.
- Require service credit, comparable terms, PTO allocation, retention, WARN treatment, or restrictive covenants only when requested by the playbook/prompt or triggered by deal facts.

Transition and carveout terms:

- Check TSA scope, duration, fee model, stranded overhead recovery, clean termination rights, IP/trademark licenses, domain redirects, Section 1060 allocation, transfer tax split, outside-date extensions, and governing law/forum.
- For required redlines, mirror the template's stable redline IDs and include must-have terms as normalized objects.

Committee packages:

- Compare each current draft term to policy thresholds.
- Calculate threshold amounts and deltas from the stated value basis.
- Use benchmarks only when a benchmark record matches the term metric and basis; otherwise mark benchmark support as not applicable if the schema permits.
- Recommendations should distinguish non-approvable legal deviations from economics that can be approved with caps or conditions.

## Calculations

Use the basis stated by the source record or prompt. If no different basis is stated, use the deal's headline purchase price or equity value as directed by the task.

- Percent amount: `integer_dollars = round(base_dollars * percent_points / 100)`.
- Holder allocation: allocate each component using fully diluted percentage or as-converted shares as the cap table directs; verify totals reconcile to the component totals.
- Seller excess delta: `draft_amount - fallback_amount` when the draft is above the seller fallback.
- Buyer shortfall delta: `fallback_amount - draft_amount` when the draft is below the buyer fallback.
- Required fee shortfall: required fee amount minus the draft/current fee amount.
- Month deltas: excess or shortfall versus fallback, in integer months, using the direction implied by client side.
- Count summaries from the final included arrays, not from all raw records.
- Sum closing consent amount at risk only for required closing consents.
- Sum material-contract revenue only for contracts requiring closing-condition treatment.
- Sum risk exposure only for components the template asks to include; exclude not-quantified, notice-only, or tradeable components unless requested.

Follow prompt units exactly: integer dollars, percent points rounded to the specified decimals, integer months, holder percentages to the requested precision, and dates as `YYYY-MM-DD`.

## Output discipline

- Fill the exact template shape. Do not add prose outside JSON.
- Use allowed enums exactly as written.
- Use stable source IDs from workbench records or the template.
- Use `null` for unavailable scalar values and `[]` for empty arrays unless the template states otherwise.
- Preserve required ordering: template ordering first, then negotiation priority, then stable ID order if no other instruction exists.
- Before final answer, validate JSON syntax, required top-level keys, allowed enums, counts, sums, rounding, blocker lists, and absence of placeholders.
