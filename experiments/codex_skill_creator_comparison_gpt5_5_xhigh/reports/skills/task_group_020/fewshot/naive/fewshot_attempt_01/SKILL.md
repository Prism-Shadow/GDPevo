---
name: ma-deal-workbench-json
description: Solve M&A deal workbench tasks that require strict JSON outputs from deal API records, playbook or policy comparisons, source IDs, and legal/economic calculations.
---

# M&A Deal Workbench JSON

Use this skill when a prompt asks you to prepare an M&A issue register, deviation matrix, committee escalation package, closing package, transition review, or similar structured JSON output from a running deal workbench.

## Core Workflow

1. Read the user prompt and `input/payloads/answer_template.json` before querying data.
2. Extract the deal ID, client side, transaction type, requested package, applicable playbook or policy ID if named, required units, rounding rules, enum values, sorting rules, and required output shape.
3. Gather records from the workbench for only the requested deal. Start with the deal record, then fetch the endpoints the prompt names or implies: terms, playbook or policy rules, risk estimates, employees, consents, material contracts, regulatory, benchmarks, notes, diligence findings, cap table, documents, and deal-specific metadata.
4. If the prompt permits read-only SQL, use `POST /api/query` with token `deal-workbench-readonly` only for cross-table checks or to locate records that are not obvious from the REST endpoints. Do not use SQL to infer evaluator internals.
5. Build an evidence table keyed by stable source IDs: draft term IDs, consent IDs, material contract IDs, employee IDs, risk estimate IDs, benchmark IDs, document IDs, and regulatory IDs.
6. Compare current draft positions against the client playbook or committee policy. Treat absent required protections as issues when the playbook, policy, or surrounding deal facts show the provision is needed.
7. Construct the answer from the template, using exact field names and enum strings. Return valid JSON only, with no explanatory prose.

Do not assume records from similarly named projects apply to the requested deal. Exclude stale drafts, superseded notes, distractor terms, and in-policy items when the prompt asks only for escalations or deviations.

## Data Gathering Checklist

Use these endpoint patterns when available, substituting the actual base URL and deal or playbook IDs from the task:

- `GET /api/deals/{deal_id}`
- `GET /api/deals/{deal_id}/terms`
- `GET /api/playbooks/{playbook_id}/rules`
- `GET /api/deals/{deal_id}/risk-estimates`
- `GET /api/deals/{deal_id}/employees`
- `GET /api/deals/{deal_id}/consents`
- `GET /api/deals/{deal_id}/material-contracts`
- `GET /api/deals/{deal_id}/regulatory`
- `GET /api/deals/{deal_id}/benchmarks`
- `GET /api/deals/{deal_id}/diligence-findings`
- `GET /api/deals/{deal_id}/cap-table`
- `GET /api/deals/{deal_id}/documents`
- `GET /api/deals/{deal_id}/notes`

After fetching, normalize records into:

- Deal economics: headline value, purchase price, equity value, upfront cash, stock value, milestone value, value basis, signing and meeting dates.
- Draft terms: term ID, category, clause reference, metric values, current/stale status, and whether the term is silent on a required point.
- Playbook or policy rules: preferred position, fallback position, hard cap, required triggers, approved carveouts, closing condition requirements, required redlines, and escalation thresholds.
- Deal facts: required consents, notice-only consents, material contracts and revenue, employee groups and PTO liability, HSR or other regulatory status, diligence findings, benchmarks, and risk estimate ranges.

## Comparison Rules

Use the client side to interpret whether a draft is too weak or too burdensome:

- Buyer-side tasks: a lower-than-required indemnity cap, missing escrow, missing material consents, missing HSR condition, insufficient survival, missing service-credit protection, or weak closing condition is usually `draft_below_playbook` or `missing_required_term`.
- Seller-side tasks: buyer-favorable financing conditions, excessive escrow, excessive indemnity cap or survival, broad consent termination rights, uncapped transition obligations, buyer employee cherry-picking, missing seller tax/forum protections, or missing transition limits are usually `draft_exceeds_playbook`, `out_of_policy`, or `missing_required_term`.
- Committee packages: include only current terms that breach policy thresholds or require committee approval. Exclude stale, in-policy, or non-committee distractors, but list excluded items if the template asks for them.
- If a term exists but omits a required mechanism, use the status that best matches the template: `missing_required_term` for total silence, `draft_below_playbook` when the client needs more protection, `draft_exceeds_playbook` when the draft imposes more exposure than the client accepts, and `out_of_policy` for policy-restricted deviations.
- Preserve stable source IDs. Use an empty `source_term_ids` array only when the issue is genuinely missing from current draft terms.

## Common Issue Handling

Indemnity:

- Calculate cap, basket, escrow, fee, and shortfall amounts from the source-specified basis. If no special basis is stated, use the deal value basis requested in the prompt or template.
- Compare draft percentages and months to preferred and fallback levels. Buyer-side shortfall is fallback/preferred amount minus draft amount. Seller-side excess is draft amount or months minus fallback.
- Track basket type, knowledge qualifiers, materiality scrape type, special indemnities, privacy or diligence findings, escrow agent status, release trigger, and survival linkage when requested.

Closing certainty:

- Required consents are blockers when records mark them as required for closing, assignment, change-of-control, or material customer/vendor continuity.
- Notice-only records are nonblocking unless the prompt or source explicitly elevates them.
- Material contract closing conditions usually include only contracts with consent rights, termination rights, or other closing-risk flags. Exclude ordinary or notice-only contracts when the template has an exclusion field.
- HSR or industry approvals require a closing condition when regulatory records say required or pending. Record whether hell-or-high-water obligations are required, barred, or limited by the playbook.

Employees and covenants:

- Use employee records to count continuing or affected employees, identify service-credit populations, WARN-risk employees, and sum PTO liabilities.
- For seller carveouts, flag buyer cherry-picking, refusal of accrued PTO, missing comparable terms, and missing service-credit provisions.
- For buyer-side founder or executive restrictions, add non-compete or non-solicit treatment only when the playbook and holder or employee records support it.

Transition and separation:

- For transition services, compare duration to preferred and fallback months, require clean termination rights, and capture the required fee model. Quantify stranded-cost gaps or support costs from risk estimates or diligence records.
- For IP and domain transition, flag missing transitional trademark licenses, redirect obligations, domain maintenance, subdomain/page coverage, and license/redirect duration.
- For tax, add mutually agreed purchase-price allocation and consistent filings when required. Add transfer-tax allocation or split when the draft is silent.
- Add governing law and forum fixes when required by playbook or template and missing from the draft.
- Add outside-date extension protection when regulatory timing records support it.

Committee escalations:

- Use policy thresholds, not general playbook preferences, to decide inclusion.
- Provide draft metric, policy metric, delta, benchmark position, risk exposure, recommendation, and required conditions for each included term when the template asks for them.
- Aggregate only quantified exposure components that the template asks to include. Keep nonquantified components separate.

## Calculation Rules

- Currency amounts are integer dollars unless the template says otherwise.
- Percentages are percent points. Round to the exact precision in the prompt or template.
- Month and day values are integers.
- For percent-based amounts, use `round(value_basis * percent / 100)` unless the source gives a stated amount.
- Holder allocations use the cap table percentages or as-converted shares from source records. Apply each holder percentage to each consideration component, then total. Follow the prompt precision for holder percentages.
- Sum closing consent amount-at-risk only for required closing consents. Sum material contract revenue only for material contracts requiring consent or closing conditions.
- Count issues from the array actually returned. Count high/medium/low risk from issue records, not from all source records.
- For modeled exposure totals, use risk estimate low/high values and include only categories requested by the template or prompt.
- Recompute all totals after sorting and before final output.

## Output Discipline

- Start from the answer template and replace every placeholder with sourced values, `null`, `false`, empty arrays, or empty objects as appropriate.
- Match enum values exactly, including capitalization and underscores.
- Keep stable IDs in arrays sorted or prioritized as the template requires.
- Use template ordering when specified. Otherwise, sort issue arrays by explicit priority rank if present, then by requested counsel workflow, then by stable issue ID.
- For flexible nested metric objects that represent alternatives, include only the keys relevant to the selected issue plus required comparison keys. Do not leave irrelevant placeholder alternatives in the output.
- Do not invent source IDs, dates, amounts, risk ranges, benchmark sample sizes, or playbook thresholds.
- Do not include comments, markdown, or narrative outside the JSON.

Before finalizing, validate:

- The output parses as JSON.
- Top-level fields and required nested fields match the template.
- No placeholder strings remain.
- All source IDs come from fetched records or template-provided stable synthetic IDs.
- Every included issue has a defensible source fact and comparison rule.
- Totals, counts, deltas, and shortfalls reconcile to the returned arrays.
