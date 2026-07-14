---
name: aster-deal-desk-ma-sop
description: Use for Aster Legal Deal Desk M&A transaction contract review and negotiation tasks.
---

# Aster Legal Deal Desk M&A SOP

Use this workflow for Aster Deal Desk tasks that ask for buyer/seller term population, APA/SPA issue registers, public merger committee packets, or transition-term review JSON.

## Access

- Read `environment_access.md` and replace `<TASK_ENV_BASE_URL>` with `GDPEVO_ENV_BASE_URL`.
- Use the remote Web/API service only. Do not look for or use local environment source/data files.
- Prefer JSON APIs over scraping rendered HTML:
  - `GET /api/health` to confirm service availability.
  - `GET /api/deals/{deal_id}` as the first source. It returns `deal`, `documents`, `policy`, `clauses`, and `benchmarks`.
  - `GET /api/documents/{doc_id}` for full active document sections.
  - `GET /api/policies/{policy_id}` for controlling playbook/risk memo rules.
  - `GET /api/clauses?deal_id={deal_id}` for clause comparison records.
  - `GET /api/benchmarks?...` only when benchmarks are requested or needed for a quantified escalation field.
  - `GET /api/search?q=...` only to locate a known target source; search results include lookalike distractors.
- Stay on the requested `deal_id`. Do not let similarly named deals, `linked_deals`, or broad search hits affect the answer.

## Source Precedence

1. The prompt and `answer_template.json` control required keys, allowed enums, numeric formats, and sort order.
2. The requested deal record controls identity fields: `deal_id`, parties, structure, dates, client side, values, `policy_id`, industry, and status.
3. Active deal documents and active structured schedules control transaction facts. Use `deal.active_documents`, document `version_status: ACTIVE`, and `related_ids` matching the target deal.
4. Latest written client instructions and active draft terms are the main comparison point for review tasks. Apply them with the controlling policy/playbook; if a client instruction is more specific, use it for the client position while still applying policy approval/escalation rules.
5. Active schedules override stale schedules. In particular, use active cap tables/allocation schedules over stale exports; use active material consent matrices, financial schedules, disclosure schedules, and committee records over generic draft language.
6. Clause comparison records are issue-identification aids. Use only `version_status: ACTIVE` clauses for current draft conclusions unless the output specifically asks for superseded or override documents.
7. Benchmarks are secondary support. Prefer matching topic, industry/peer set, current year, and definitions. Treat records marked older samples, definition mismatches, or outside core peer set as distractors unless the task explicitly asks for them.
8. Stale, template, generic form, and unrelated matter records are exclusions. Include their IDs only when the schema asks for `superseded_doc_ids`, override sources, or similar audit fields.

## Data Handling

- Use exact names, IDs, titles, and dates from the remote records. Do not normalize legal entity names beyond the template's enum/id requirements.
- Document `sections[].text` may contain serialized JSON. Parse it mentally or with tooling; do not rely on truncated snippets.
- Preserve real booleans and arrays. Use `[]` for no list items, `null` only where the template says a value is not applicable or incalculable.
- Map source wording to template enums exactly. Convert displayed/lowercase values like `closing` or `deductible` to the allowed uppercase enum only when the template requires it.
- For audit fields, use source IDs such as document IDs, policy rule IDs, clause IDs, and benchmark IDs. Do not write prose evidence memos inside `source_ids`.

## Calculations

- Use the template's stated base: headline value, equity value, active cap table share count, ownership percentage, revenue, or calendar days. Confirm against `clause.calculation_base` when available.
- Currency fields are integer USD with no commas or symbols. Percent fields are percentage points, not fractions, normally rounded to two decimals. Month fields are integers.
- Prefer scheduled dollar amounts and scheduled ownership percentages when provided. Calculate only when the template asks for a derived value or the API gives percentages/components but not the final field.
- Common formulas:
  - Escrow/cap/basket/tax amounts: `base_value * percent / 100`.
  - Percentage from amount: `amount / base_value * 100`.
  - Price per ownership percentage point: value divided by `100`.
  - Seller proceeds: active ownership percent times the relevant consideration pool, unless an active allocation schedule provides exact amounts.
  - NWC collar percent: `collar / equity_value * 100`.
  - Closing deadline days: calendar-day difference between signing date and outside closing date.
  - Policy excess: draft amount or percent minus the policy threshold, using the policy's stated base.
- After calculating, check that component consideration totals equal total/headline/equity values as applicable, seller allocation percentages sum to 100% when expected, and summed exposure/excess fields do not double count the same issue.

## Review Judgments

- Include only material issues in issue lists unless the schema explicitly requires a fixed check list. Omit non-issues rather than adding `NO_ISSUE` when the template says to include material issues only.
- Buyer SPA/term-population tasks usually require drafting-ready current terms: active cap/allocation source, consideration mix, active material consents, HSR memo status, escrow/cap/basket, NWC, employment/restrictive covenant position, transition services, and IP assignment/transition flags.
- Seller APA review tasks compare the active buyer draft against seller playbook and current client instructions. Common material deviations include financing or lender-diligence conditions, over-policy escrow/cap/basket/survival, missing de minimis, working-capital resets, broad restrictive covenants, weak employee transfer/WARN allocation, omitted TSA, open-ended IP/trademark rights, and misplaced material consent/HSR conditions.
- Public merger committee tasks focus on committee-route terms: RTF and break fees on equity value, fiduciary-out or superior-proposal restrictions, post-closing R&W survival/indemnity in public-style mergers, MAE carve-out omissions, and regulatory covenant weakness. Aggregate risk should reflect the highest-severity drivers and quantified exposure/excess only once.
- Carve-out APA transition tasks prioritize employee transfer, TSA service continuity, restrictive covenant scope/duration, IP transition/trademark phase-out, escrow economics, and outside closing date sufficiency.
- Approval owner/category should come from the controlling policy rule or current client instruction. Do not invent approval bodies.

## Answer Shaping

- Return exactly what the prompt requests, usually one JSON object and no Markdown/prose.
- Match the template's top-level keys and omit unapproved fields. In flexible objects like `corrected_value`, include only fields relevant to that issue.
- Use exact allowed enum strings. Do not use lowercase source labels, narrative statuses, or synonyms.
- Sort every list according to the template: issue IDs/check IDs alphabetically or ascending, seller IDs/names as specified, contract names alphabetically, code lists alphabetically, source IDs ascending, and approval bodies alphabetically when requested.
- Use stable uppercase snake-case seller IDs only when the schema asks for them; otherwise preserve displayed seller names from the active cap table.
- Keep narrative out of structured fields unless the schema expressly asks for a short string. The answer should be auditably sourced by IDs and normalized values, not by prose explanation.
- Validate final JSON before returning: no comments, no trailing commas, no currency symbols, no percent signs in numeric fields, dates as `YYYY-MM-DD`, and all required keys present.
