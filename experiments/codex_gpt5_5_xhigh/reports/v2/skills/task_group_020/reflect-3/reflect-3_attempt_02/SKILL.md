---
name: aster-deal-desk-ma-sop
description: Use for Aster Legal Deal Desk M&A transaction contract review and negotiation tasks.
---

# Aster Deal Desk M&A SOP

## Start With The Template

Read the task prompt and `input/payloads/answer_template.json` before using the Deal Desk. Treat the template as the output contract: required keys, enum spellings, list ordering, numeric precision, and null/empty-list conventions all come from it.

Return only the requested JSON object. Do not include Markdown, citations outside JSON fields, or explanatory memo text unless the template has a field for it.

## Remote Environment Workflow

Use the remote Deal Desk Web/API base URL supplied in the task. Prefer structured API responses over scraping pages when possible:

- `GET /api/deals/{deal_id}` for the main record, active/stale documents, active clauses, policy, and benchmarks.
- `GET /deals/{deal_id}` to cross-check page-rendered raw sections and active/stale labels.
- `GET /clauses/compare?deal_id={deal_id}` or the clauses API to inspect active clause comparisons and stale/template distractors.
- `GET /policies/{policy_id}` or policy API to inspect playbook rules, approval categories, thresholds, and fallback positions.
- `GET /benchmarks?industry=...&topic=...` only when the requested schema asks for benchmark IDs, sample sizes, market context, or exposure support.

Use `jq` to inspect the deal record by section: `.deal`, `.documents[]`, `.clauses[]`, `.policy`, `.benchmarks[]`. Keep the target `deal_id` fixed; similarly named codenames and neighboring deal IDs are common distractors.

## Source Precedence

Apply sources in this order:

1. The task prompt and answer template.
2. The target deal record for exact parties, structure, dates, values, policy ID, and active document IDs.
3. Active, deal-specific documents, especially latest written client instructions, current draft, signed term sheet, active cap table/allocation schedule, financial schedule, material contracts matrix, disclosure schedules, and committee charter.
4. Active clause comparison records for draft-vs-playbook deviations, clause IDs, calculation bases, and source document IDs.
5. The current client playbook or policy for default thresholds, approval routing, fallbacks, and preferred positions.
6. Benchmarks as supporting context only; policy thresholds and deal-specific client instructions control over market data.

When sources conflict, use active deal-specific materials over stale exports, templates, generic provisions, and older schedules. Latest written client instructions control over generic playbook defaults when they are more specific for the deal; otherwise use the playbook.

## Common Exclusions

Do not use stale cap tables, stale/template clauses, generic template provisions, or similarly named deals unless the task explicitly asks for superseded material. Do not invent missing approvals, consents, share counts, employee names, or benchmark values.

For issue registers, omit non-issues unless the template explicitly asks for within-policy terms. For consent fields, distinguish true material consent closing conditions from notices, covenants, and post-closing notices according to the target field names.

For HSR, do not add a filing condition when the active regulatory memo says no filing is required. Use the memo basis exactly: size-of-person not met, reportable thresholds not met after debt adjustments, counsel memo missing, or thresholds met.

## Field And Enum Conventions

Use exact names and IDs from the active deal record:

- Parties: buyer, seller/seller group, target, client side, committee members, employees, contracts, approvals.
- Dates: `YYYY-MM-DD`.
- Dollars: integer U.S. dollars, no commas or symbols.
- Percentages: percentage points, not fractions; round to the template precision.
- Enums: use template spellings exactly, usually uppercase snake case.
- Missing numeric values: use `null` only when the template allows it; otherwise use `0` for true zero-dollar or zero-percent terms.
- Lists: sort exactly as the template requires, commonly by ID/name alphabetically. Preserve committee-member order if the template says to use names as shown.

Use exact source IDs where requested. Prefer active clause IDs, active document IDs, policy IDs, and relevant benchmark IDs. Avoid stuffing source lists with stale/template IDs unless the field is about superseded materials.

## Calculation Checklist

Before finalizing, recompute and reconcile:

- Escrow, cap, basket, tax escrow, break fee, and reverse termination fee amounts from the specified base, usually headline or equity value.
- Aggregate escrow percent/amount from general plus tax escrow when requested.
- NWC collar percentage from `collar / equity_value * 100` when requested.
- Per-share price only if the active cap table provides a share count; otherwise use the template's no-share-count/null convention.
- Seller allocations from the active cap table or active allocation schedule. If only ownership percentages are provided, allocate each consideration component pro rata and verify component totals and total proceeds tie to deal consideration.
- Public merger exposure: use policy-threshold excess for fee excess fields; use full equity value only when the schema asks for uncapped/full-equity exposure.
- Date deltas, such as deadline days after signing, using calendar days unless the template says business days.

Round dollars to whole dollars. Round percentages to the requested decimal places. After calculations, verify subtotals tie back to headline/equity value and that sorted arrays remain sorted.

## Review Patterns

For buyer-side first drafts or term population, populate drafting-ready terms from the active term sheet, active financial schedule, active cap table/allocation schedule, material contracts matrix, and latest client instructions. Use policy checks to label current positions as within policy, approval required, override applied, or escalate-if-changed.

For seller-side counterparty-paper reviews, compare the active draft against latest client instructions and the seller playbook. Group related clause deviations under the template's issue IDs, include each material issue once, quantify corrected values where economic, and use a controlled recommended action.

For committee escalation packets, include terms requiring escalation and, if the template calls for it, within-policy terms as no-action entries. Route to the committee named by policy/charter, quantify fee excess or uncapped exposure only where supported, and keep non-quantified legal risk as null-dollar exposure unless the schema specifies otherwise.

For transition-term packages, combine active draft terms, disclosure schedules, material-contract dependencies, latest client instructions, and the operating playbook. Use deal-specific needed services plus controlling playbook requirements when building required service-code lists.

## Final JSON Shaping

Validate the final object against the template manually:

- All top-level required keys are present and no prose surrounds the JSON.
- Issue or term arrays are sorted by the template key.
- Required nested objects are present even when values are false, zero, empty, or null.
- Only allowed enum values appear.
- Source and override lists use active/current IDs unless the field is expressly about superseded records.
- No stale, template, or distractor deal facts are included.
