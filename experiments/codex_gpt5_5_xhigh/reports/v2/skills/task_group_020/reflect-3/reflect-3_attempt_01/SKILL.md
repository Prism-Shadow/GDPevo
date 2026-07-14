---
name: aster-deal-desk-ma-sop
description: Use for Aster Legal Deal Desk M&A transaction contract review and negotiation tasks.
---

# Aster Deal Desk M&A SOP

Use this for Aster Legal Deal Desk tasks that ask for buyer or seller M&A drafting data, issue registers, committee escalation packets, policy checks, or transition-term review.

## Remote Environment Workflow

- Use only the Deal Desk remote service identified by the task prompt. Do not look for local environment source or hidden data.
- Start with the task prompt and `input/payloads/answer_template.json`; the template controls top-level keys, required fields, enum spelling, list ordering, null handling, and numeric precision.
- Query the deal API first: `/api/deals/{deal_id}` usually bundles the deal profile, active/stale documents, clauses, policy, benchmarks, schedules, parties, economics, and record links.
- Use HTML pages such as `/deals/{deal_id}`, `/clauses/compare?deal_id=...`, `/policies/{policy_id}`, `/benchmarks?...`, and `/documents/{doc_id}` only to clarify or cross-check what the API returns.
- Prefer structured API JSON over scraping rendered text. If a field appears both in a summary and in an active document section, use the active document section for detail and the summary for reconciliation.

## Source Precedence

Apply sources in this order:

1. Active deal profile, current active draft, latest written client instructions, active term sheet, active financial schedules, active cap table or allocation schedule, active material-contract matrix, and active disclosure schedules.
2. The current client playbook or policy linked to the deal.
3. Active clause-comparison records for issue spotting and policy thresholds.
4. Current, on-point benchmarks only when the prompt asks for market context or quantification.
5. Stale cap tables, generic templates, stale clauses, superseded exports, and off-industry or old benchmarks only when a field explicitly asks for superseded sources or override context.

Latest written client instructions can narrow or override generic template language. Active schedules override stale schedules. Do not let a stale/template clause with the same label displace the active draft.

## Field Conventions

- Return JSON only. No Markdown, prose memo, citations outside JSON fields, or extra top-level keys.
- Copy exact deal IDs, document IDs, clause IDs, policy/rule IDs, party names, seller names, contract names, and employee display names. Preserve legal suffixes, punctuation, titles, and role descriptors when the template asks for displayed names.
- Use the template's enum values exactly. Normalize plain-language source text into the enum rather than inventing variants.
- Use integer U.S. dollars; no commas or currency symbols. Use percentages as percentage points, not fractions. Round percentages to the template precision.
- Use `null` for values that are not calculable or not applicable. Use `0` only for a real zero amount or percent.
- If the active cap table lacks share counts, set per-share price to `null` and use the template's no-share-count basis.
- Sort every list exactly as the template says. If no explicit order is given, use a stable logical order from the active source; for issue registers, usually sort by issue or term ID.
- When a field asks for document IDs, provide document IDs, not clause IDs. When it asks for source IDs generally, include concise supporting document, clause, policy rule, or benchmark IDs.

## Calculation Habits

- Reconcile consideration first: cash, note, rollover, earnout, escrows, and seller allocations should tie to headline/equity value as applicable.
- Seller gross proceeds usually equal ownership percent times the relevant value. Allocate each consideration component pro rata when the active cap table/allocation schedule says allocations follow ownership and no more specific allocation schedule is posted.
- Price per ownership percentage point is value divided by 100. Per-share price requires an actual share count.
- Escrow, cap, basket, break fee, and reverse termination fee amounts use the calculation base stated in the active clause or template, commonly headline value or equity value.
- NWC collar percent is `collar / equity_value * 100`, rounded as required.
- Date intervals are calendar days unless the source says business days.
- For policy excess, calculate `(draft percent - allowed threshold percent) * base`. Keep draft amount and excess amount separate when both fields exist.
- For aggregate risk totals, sum only quantified exposure fields; do not assign dollar values to non-quantified legal risks unless the schema provides a basis such as full equity value exposure.

## Review And Issue Rules

- Include only material active-draft deviations unless the schema explicitly wants all policy checks or all reviewed terms.
- Omit non-issues from issue registers. For policy-check packets, include all listed checks if the template requires a checks array sorted by check ID.
- Combine related deviations when the schema has a combined issue ID, such as survival/cap/basket or employee/TSA/IP transition.
- In seller-side reviews, financing conditions, broad restrictive covenants, buyer-favorable reset mechanics, omitted TSAs, retained WARN/severance exposure, and escrow/cap/basket deviations are common material issues.
- In buyer-side drafting packages, preserve specified material consents as closing conditions, keep no-HSR positions tied to the active antitrust memo, align cap with escrow when instructed, and flag approval only when a current term crosses a policy threshold.
- For committee escalation, distinguish approval required now from fallback or conditional triggers. Use non-quantified legal risk for blocked fiduciary outs, restricted MAE carve-outs, and weak covenants unless the template provides a dollar exposure basis.
- For transition packages, the priority issue list and structured flags must agree on whether employee transfer, TSA, restrictive covenant, IP transition, escrow, and closing deadline issues are present.

## Common Exclusions

- Do not use stale cap tables, template provisions, stale clause rows, or superseded drafts for current terms.
- Do not list contracts with `consent_required: false` as required consents; put notices or post-closing notices only in fields that ask for them.
- Do not add HSR filing conditions when the active memo says thresholds are not met; use cooperation-only or no-condition enum values as the template permits.
- Do not include unrelated approvals, off-point benchmarks, generic market data, or policy rules from another client/deal unless the active deal links them.
- Do not invent missing data such as share counts, employee names, approval bodies, or benchmark IDs.

## Final Check

Before answering:

- Validate the JSON parses and matches the template keys.
- Verify every enum against the template.
- Recalculate all dollar amounts, percentages, date intervals, and aggregate totals.
- Reconcile seller allocations and consideration totals to the deal value.
- Confirm all list ordering requirements.
- Confirm each issue or policy check is supported by active/current sources and excludes stale/template distractors.
