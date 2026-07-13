---
name: aster-deal-desk-ma-sop
description: Use for Aster Legal Deal Desk M&A transaction contract review and negotiation tasks.
---

# Aster Deal Desk M&A SOP

## Scope

Use this skill for Aster Legal Deal Desk tasks that ask for M&A draft term population, buyer/seller contract review, issue registers, committee escalation packets, policy checks, or transition-term flags. Work from the shared remote Web/API service named in the task prompt; do not use local environment source files.

## API Workflow

- Replace `<TASK_ENV_BASE_URL>` with the base URL from the prompt or `environment_access.md`.
- Start with `GET /api/health` only to confirm the service is reachable.
- Pull the target deal with `GET /api/deals/{deal_id}`. This aggregate is usually the fastest source because it includes `deal`, `documents`, `policy`, `clauses`, and `benchmarks`.
- Use direct endpoints when detail or filtering is needed:
  - `GET /api/deals` for the matter index.
  - `GET /api/documents/{doc_id}` for document sections.
  - `GET /api/policies/{policy_id}` for current playbook rules.
  - `GET /api/clauses?deal_id={deal_id}` for clause comparison records.
  - `GET /api/benchmarks?topic=...&industry=...&year=...` for market data.
  - `GET /api/search?q=...` for locating related records, then verify `deal_id` before relying on them.
- HTML pages mirror the same data and are useful for links and raw JSON blocks, but prefer JSON API responses for extraction.

## Source Precedence

1. The user prompt and `input/payloads/answer_template.json` control the required output shape, field names, enums, nullability, precision, and ordering.
2. The target deal record controls the matter facts: `deal_id`, client side, structure, parties, headline/equity value, signing date, closing deadline, policy ID, active/stale document lists, economics, schedules, and negotiation context.
3. Active documents, active clause records, and latest written client instructions control current draft terms. Filter on the requested `deal_id` and `version_status == "ACTIVE"`.
4. The current client playbook/policy controls preferred positions, thresholds, approval categories, fallbacks, and escalation triggers.
5. Deal-specific active schedules control structured facts: cap table/allocation, financial schedule, material contracts, regulatory status, employment terms, TSA, and IP transition.
6. Benchmarks support market context or quantification only when requested. They do not override active client instructions or policy thresholds.
7. Stale/template documents, stale clauses, stale cap tables, and generic form provisions are distractors unless the requested schema explicitly asks for superseded IDs or override codes.

When sources conflict, prefer the latest active deal-specific written instruction or active schedule over an older active summary, and prefer the current client policy over a standard-form policy.

## Review Pattern

- Read the answer template first and list every required field, enum, precision rule, and sorting rule.
- Pull the target deal aggregate and verify the exact `deal_id`; ignore similarly named deals.
- Separate active from stale/template sources before reasoning.
- For issue-register tasks, compare each active clause or draft term against the current client instructions and policy rule for the same topic. Include each material issue once.
- For first-draft or term-population tasks, populate from deal economics, active schedules, active cap table/allocation schedule, regulatory status, and current instructions. Then run policy checks.
- For committee escalation tasks, include only terms that require committee routing or an approval/recommendation under the policy or latest instructions, then compute aggregate risk from the included terms.
- For transition packages, evaluate employee transfer, TSA/service continuity, restrictive covenants, IP transition, escrow, and outside closing date from the active draft plus operating schedules.

## Math And Checks

- Currency fields are integer U.S. dollars with no symbols or commas.
- Percent fields are percentage points, not fractions. Round to the template precision, usually two decimals.
- Use the calculation base specified by the template, clause, or policy:
  - escrow, tax escrow, indemnity cap, basket, de minimis, and seller allocations usually use headline value unless the template says otherwise.
  - reverse termination fee and company break fee in public merger tasks usually use equity value.
  - NWC collar percent is `collar / equity_value * 100` unless a different base is specified.
- Compute amount fields as `base * percent / 100`, rounded to whole dollars. If the API gives both amount and percent, cross-check them and investigate material mismatches.
- Consideration mix must foot: cash at close + seller note + rollover equity + earnout = total consideration/headline value when those components are the full consideration.
- Seller allocations come from the active cap table or active allocation schedule. Apply each ownership percentage to each consideration component when component-level proceeds are required. Totals should foot to each component and to total consideration, allowing only rounding differences.
- Price per ownership percentage point is `equity_value / 100`. Per-share price is calculable only if the active cap table provides a share count; otherwise use the template’s null/no-share-count convention.
- Date intervals are calendar days unless the template says business days. Compute outside-closing days as `closing_deadline - signing_date`.
- For public merger exposure, quantify policy excess as the draft amount/percent over the policy threshold, and use null for numeric fields that do not apply.

## Field Conventions

- Use exact party, seller, employee, contract, approval, policy, clause, document, and benchmark names/IDs from the Deal Desk.
- Normalize natural-language draft terms to the template’s controlled enum values; do not invent enums.
- Use booleans, integers, numbers, nulls, and arrays as the template requires. Use `null` only when the schema permits or a value is not applicable.
- Source ID fields are audit fields: include concise supporting doc IDs, policy rule IDs, clause IDs, and benchmark IDs as requested, not prose explanations.
- Sort exactly as instructed. Common rules: issues by `issue_id` or `term_id`, sellers by seller name or seller ID, contracts by contract name, source IDs by doc ID, code lists alphabetically, committee members in the Deal Desk order unless the template says otherwise.
- If a schema says to omit non-issues or unused corrected-value fields, omit them. Do not add explanatory keys outside the template.

## Common Exclusions

- Do not rely on local env/source files, evaluator files, judge feedback, or unstaged answer files.
- Exclude stale/template clause records from active issue conclusions.
- Exclude stale cap tables from allocations unless documenting that they were superseded.
- Exclude records for similarly named but different deal IDs.
- Exclude generic standard-form provisions when a current client policy or deal-specific instruction applies.
- Exclude benchmark records marked by topic, industry, year, notes, or definition as mismatched distractors when a more specific current benchmark exists.
- For material consent lists, include only contracts matching the requested condition type and consent requirement; keep notices, post-closing notices, TSA/service items, and non-consent contracts in their separate fields when the schema provides them.
- Treat a no-HSR counsel/regulatory memo as controlling over generic HSR template language; include HSR cooperation-only language where policy calls for it.

## Answer Shaping

- Return exactly one JSON object when requested. Do not include Markdown, prose, citations outside fields, or comments.
- Keep top-level keys exactly as the template requires and in a clear template-compatible order.
- Before finalizing, check:
  - all required keys are present;
  - all enum values match the template;
  - all numbers use required precision and units;
  - arrays are sorted as required;
  - totals foot and policy thresholds were applied to the correct base;
  - no stale/template source was used as controlling evidence.
