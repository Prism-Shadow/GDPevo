---
name: aster-deal-desk-ma-sop
description: Use for Aster Legal Deal Desk M&A transaction contract review and negotiation tasks.
---

# Aster Deal Desk M&A SOP

Use this skill for Aster Legal Deal Desk tasks that ask for structured JSON term population, contract issue registers, committee escalation packets, transition packages, or policy-check outputs.

## First Pass

1. Read the task prompt and `input/payloads/answer_template.json` before querying the Deal Desk. The template controls top-level keys, field names, allowed enums, nullability, numeric precision, and list ordering.
2. Identify the exact `deal_id` from the prompt and work only that deal.
3. Query the shared Deal Desk using the task-provided base URL. Start with `GET /api/deals/{deal_id}` because it usually returns the deal profile, active/stale document lists, policy, clauses, schedules, economics, parties, and benchmarks in one place.
4. Use web pages such as `/deals/{deal_id}`, `/clauses/compare?deal_id=...`, `/policies/{policy_id}`, and `/benchmarks?...` only to clarify or cross-check the API payload.

## Source Precedence

Use this authority order when sources conflict:

1. The task prompt and answer template for output contract.
2. Active deal record fields: structure, parties, economics, dates, policy ID, schedules, and record links.
3. Latest active client instructions, usually `client_positions` and active email/client instruction documents.
4. Active current draft, term sheet, financial schedule, material contract matrix, disclosure schedules, committee charter, and active cap table/allocation schedule.
5. Applicable client playbook or policy for thresholds, preferred/fallback positions, approval owners, and rule IDs.
6. Active clause comparison records for draft/playbook deviations.
7. Benchmarks only when the requested schema asks for benchmark fields or market support.
8. Stale, legacy, or template documents only as superseded/override evidence; never use them as controlling terms.

Treat `version_status: ACTIVE` as controlling. Treat `STALE` and `TEMPLATE` records as distractors unless the output has fields such as `superseded_doc_ids`, override codes, or source audit notes.

## API Habits

- Filter all clauses and documents to the target `deal_id`.
- Prefer exact IDs from the environment: `DOC-*`, `CL-*`, `P-*`, benchmark IDs, and policy rule IDs where the schema asks for them.
- If a field says `source_doc_ids`, include document IDs, not clause IDs.
- If a field says `source_ids`, clause, document, policy, and benchmark IDs may be appropriate; keep them concise and audit-relevant.
- Confirm whether a list is supposed to contain only material/active items or all flags including notices and non-consent items.

## Normalization Rules

- Return JSON only. Do not add memo text, Markdown, citations outside JSON, comments, or trailing commas.
- Use exact enum values from the template, not display text from the Deal Desk.
- Dollars are integer USD with no commas or symbols.
- Percent fields are decimal percentage points, not fractions: use `7.5`, not `0.075`.
- Month fields are integers. Dates are `YYYY-MM-DD`.
- Use `null` only when the template permits it and the source does not support a value.
- Preserve exact party, seller, contract, employee, and approval names unless the template asks for generated IDs.
- Generate stable seller IDs from names only when requested: uppercase snake case, remove punctuation, preserve meaningful entity words.
- Sort every list according to the template. Common orders: issue IDs or term IDs alphabetically, policy checks by `check_id`, seller allocations by `seller_name` or `seller_id`, contracts by contract name, source doc IDs ascending, and enum/code lists alphabetically.

## Math Checks

Always recompute and sanity-check economic fields:

- Consideration mix must sum to total/headline value unless the source states otherwise.
- Pro rata seller proceeds equal `component amount * ownership_percent / 100`; round to whole dollars and verify totals.
- Escrow, tax escrow, caps, baskets, break fees, reverse fees, and policy excesses use the base named in the schema or clause, usually headline value or equity value.
- Aggregate escrow is general escrow plus tax escrow when both are part of the requested indemnity package.
- Per ownership percentage point equals `equity_value / 100`.
- Use `per_share_price_usd: null` and the no-share-count enum if the active cap table has ownership percentages but no share count.
- NWC collar percent is `collar / equity_value * 100`, rounded per template.
- Calendar-day deadline checks count actual days from signing to outside date.
- For escalation packets, keep draft amount, excess amount, and exposure amount conceptually separate.

## Common Deal Conclusions

- Buyer first drafts usually use active cap tables/allocation schedules, buyer form positions, material consents as closing conditions, no HSR filing condition when counsel memo says thresholds are not met, and policy checks for each requested rule.
- Seller APA reviews usually flag financing conditions, excessive escrow/cap, tipping or low baskets, missing TSA, retained WARN/severance, broad restrictive covenants, missing IP transition boundaries, and buyer-friendly NWC resets.
- Public merger escalation packets usually omit within-policy break fees and focus on committee-triggering RTFs, blocked fiduciary outs, post-closing R&W survival, restricted MAE carve-outs, and weak regulatory covenants if tied to deal certainty.
- Carve-out transition packages should connect TSA duration/service scope, employee transfer, IP/trademark transition, restrictive covenants, escrow, and closing deadline to the active draft, current client instruction, and carve-out playbook.
- HSR and other approvals are separate: if HSR is not required, use the no-filing/cooperation-only position; still list other regulatory or customer approvals where the schema asks.

## Answer Shaping

- For term population, pull core terms from the deal profile, economics from financial schedules, allocations from the active cap/allocation source, and closing flags from material contract and regulatory schedules.
- For issue registers, include each material active deviation once. Omit non-issues. Put only relevant normalized fields in `corrected_value`.
- For committee escalation, include only terms requiring escalation or a recommendation. Aggregate risk should reflect the highest-severity live drivers and list primary drivers sorted as requested.
- For transition flags, populate every requested flag object even when some fields are not disputed; use `issue_present` to distinguish deviations.
- For policy checks, include every requested check ID. Keep current policy status separate from conditional escalation triggers and risk-memo overrides.
- Before finalizing, validate JSON syntax, required keys, enum spellings, list ordering, and arithmetic totals.
