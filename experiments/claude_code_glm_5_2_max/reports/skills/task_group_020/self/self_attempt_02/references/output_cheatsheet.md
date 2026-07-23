# Output Cheatsheet

Quick reference for the formatting and enum discipline that recurs across workbench tasks. **The task's own `answer_template.json` is always authoritative** — when it states a different precision or enum set, follow the template, not this sheet.

## Numeric formatting
| Quantity | Rule |
|---|---|
| Currency | integer USD dollars (no cents, no `$`, no commas inside the JSON number) |
| Percent points | decimal; precision per prompt/template (commonly 2 decimals; sometimes 1 decimal; sometimes whole points) |
| Holder / security % | four decimals where the template requires |
| Months | integer |
| Dates | `YYYY-MM-DD` |
| Counts | integer |

## Recurring enum families (use the values the template lists — these are the common union)
- **risk_rating**: `LOW`, `MEDIUM`, `HIGH`
- **issue_status / status**: `in_policy`, `out_of_policy`, `missing_required_term`, `draft_exceeds_playbook`, `draft_below_playbook`
- **recommended_action**: `delete`, `revise`, `add`, `accept`, `escalate`, `approve`, `approve_with_conditions`, `reject`
- **business_outcome**: `closing_certainty`, `escrow_economics`, `indemnity_exposure`, `restrictive_covenants`, `employee_transition`, `tax_allocation`, `governing_law`, `regulatory_efforts`
- **condition_type**: `closing_condition`, `notice_only`, `post_closing_covenant`
- **closing_readiness / overall_status**: `READY`, `READY_WITH_CONDITIONS`, `NOT_READY`
- **recommendation (escalation)**: `approve`, `approve_with_conditions`, `reject`

## Stable IDs
- Always reuse the exact IDs the workbench returns (`term_id`, `consent_id`, `contract_id`, `finding_id`, `employee_id`, holder names, `estimate_id`, `blocker_id`).
- Use an **empty array** `[]` (not null, not omitted) for `source_term_ids` / ID lists when an issue is missing from the current draft, unless the template says otherwise.
- For "found / not_found" style fields use the template's enum (e.g., `not_found_in_current_records`, `found`, `not_applicable`).

## Quantification defaults
- Dollar amounts derive from the deal's **headline purchase price** unless a source explicitly names another basis.
- Always compute the **delta to fallback** (and to preferred where the template asks): `fallback − draft` for seller-protective direction, `draft − fallback` per the template's sign convention — match the template's field definition exactly.
- Exposure ranges use the workbench's risk-estimate low/high and cite the `estimate_id`.

## Structure & ordering
- Return a **single** JSON object matching the template's top-level shape, nested objects, and array-element fields exactly.
- Sort issue arrays as the template instructs (usually `issue_id` ascending, or counsel-workflow order).
- Provide `priority_order` / `negotiation_priority` from **highest** to **lowest** negotiation priority.
- Fill the summary/aggregate block: issue counts, risk counts, quantified exposure low/high, negotiation deltas, consent/employee/PTO totals, closing-blocker counts.

## Output discipline
- **Only** the JSON object. No prose, no markdown fences, no trailing commentary.
- Must parse as valid JSON and conform to every required field/enum in `answer_template.json`.
