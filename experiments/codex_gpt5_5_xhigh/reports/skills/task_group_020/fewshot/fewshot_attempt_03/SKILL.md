---
name: aster-deal-desk-ma-sop
description: Use for Aster Legal Deal Desk M&A transaction contract review and negotiation tasks.
---

# Aster Deal Desk M&A SOP

Use this skill for Aster Legal Deal Desk tasks that ask for buyer-side or seller-side M&A term population, APA/SPA draft review, committee escalation packets, policy checks, or transition-term issue packages.

## First Pass

1. Read the prompt and `input/payloads/answer_template.json` before using the Deal Desk. The template controls output keys, enums, type choices, nullability, sorting, and precision.
2. Get the remote base URL from `environment_access.md` and substitute it for `<TASK_ENV_BASE_URL>`.
3. Use only the public Deal Desk web/API surfaces. Do not look for or use local environment source files.
4. Work only on the requested deal ID. Filter all searches and API calls by that deal ID.
5. Identify the client side, deal structure, requested work product, and controlling playbook/policy family before evaluating terms.

## Source Precedence

Apply sources in this order unless a task-specific instruction says otherwise:

1. Prompt and answer template: output contract, requested deal, client side, schema, enums, required ordering.
2. Active/current deal profile: parties, structure, values, dates, HSR status, closing posture.
3. Latest written client instructions or risk memo: deal-specific overrides, fallback positions, superseded documents.
4. Current client-side playbook or policy for the transaction type: approval thresholds, fallback positions, required approvals.
5. Active draft and clause comparison records: what is actually in the counterparty/current draft.
6. Active cap table or active allocation schedule: seller names, roles, ownership, proceeds allocation, share count if provided.
7. Material contract, disclosure, consent, employment, IP, TSA, tax, NWC, and regulatory records.
8. Benchmarks and committee records, only when the template asks for benchmark or routing fields.
9. Stale drafts, stale cap tables, generic templates, and superseded exports are distractors. Use them only to identify overrides or superseded source IDs when the template requests that.

Deal-specific written instructions can override generic playbook defaults. Active cap tables/allocation schedules override stale exports. Active draft/clause records override templates. Counsel/regulatory memo conclusions override assumptions from industry labels or asset descriptions.

## Remote Environment Habits

- Prefer structured API responses or Deal Desk detail pages over free-text scraping.
- Pull the record IDs you need, then fetch details: deal profile, documents, active draft, clause records, playbook/policy, benchmarks, committee, cap table/allocation schedule, consent/material contract records, disclosure schedules, and written instructions.
- Check `active`, `current`, `superseded`, `as_of`, version, and date fields before relying on a document.
- Keep source document, clause, policy, rule, benchmark, and committee IDs with the conclusion they support. Output only the source ID fields the template requests.
- Do not browse unrelated deals. Do not infer missing facts from similar training examples.

## Field Conventions

- Return exactly the requested JSON object. No Markdown, prose memo, or citations outside JSON fields when the task asks for JSON only.
- Use the template's top-level keys and omit unrequested keys.
- Use exact names, legal entity suffixes, document IDs, clause IDs, rule IDs, policy IDs, and dates from Deal Desk records.
- Use enum values exactly as listed in the template.
- Currency fields are integer U.S. dollars with no commas, symbols, or decimals.
- Percent fields are percentage points, not fractions. Round to the precision in the template, commonly two decimals.
- Month, day, and count fields are integers.
- Use `null` for numeric fields that do not apply or cannot be calculated under the template. Use empty arrays for no listed items.
- Booleans should reflect the legal conclusion, not whether the topic was mentioned.
- If a stable seller ID is requested, use uppercase snake case from the seller name unless the Deal Desk provides a specific ID.

## Ordering Rules

Follow the template first. Common ordering patterns:

- `seller_allocations`: by `seller_name` or `seller_id`, whichever the template specifies.
- Issue, term, check, and driver lists: by `issue_id`, `term_id`, or `check_id` alphabetically.
- Contract/consent names, employee names, code lists, TSA service codes, approval bodies, override codes, and document IDs: alphabetically or ascending when specified.
- Include each material issue once. In issue registers, omit non-issues unless the template explicitly requires a full policy check list.

## Math And Reconciliation

Check all calculations before final output:

- Consideration mix should sum to total/headline/equity value when the template includes all components.
- Seller proceeds usually equal ownership percent times the applicable consideration pool. Allocate each component when the template requests cash, note, rollover, earnout, and total proceeds.
- If an active cap table includes share count, per-share price is equity value divided by active shares. If no share count is available, use the template's no-share-count basis and `null` per-share price.
- Price per 1.00 as-converted ownership percentage point is value divided by 100.
- Escrow, cap, basket, tax escrow, reverse termination fee, and other percentage amounts equal the stated base times percent divided by 100. Confirm whether the base is headline value, equity value, or another template-specified base.
- Aggregate escrow percent/amount should equal general plus tax escrow when both are included.
- NWC collar percent is collar divided by equity value, expressed as a percent, unless the template specifies a different base.
- Deadline day counts are calendar days between signing and outside closing/deadline dates.
- Aggregate quantified exposure fields should sum the non-null numeric exposure/excess fields required by the template. Do not count non-quantified legal risk unless the Deal Desk provides a numeric exposure for it.
- Reconcile rounded whole-dollar allocations to the source schedule or total value. If a source schedule provides explicit rounded amounts, use it.

## Common Legal Conclusions

Use the controlling documents, but these patterns recur:

- Material customer/vendor/government consents with required consent language and meaningful revenue/operational impact are closing conditions. Notice-only items are not consent conditions unless the playbook says otherwise.
- HSR should be a filing/closing condition only when the HSR analysis says it is required or thresholds are met. If not required, use cooperation-only or omit condition language as the template permits. If the memo is missing, use the template's unclear/missing-memo code.
- Buyer-side first drafts usually use active cap table/allocation schedules, targeted restrictive covenants, specified material consents, objective earnout mechanics, and no HSR condition when counsel says HSR is not required.
- Seller-side review usually challenges financing conditions, lender diligence conditions, broad buyer outs, escrow above policy, caps/baskets outside policy, working-capital resets inconsistent with instructions, and escrow periods longer than survival.
- Reverse termination fees may be a fallback only when the seller playbook allows a financing-condition fallback; this does not mean the financing condition is acceptable.
- Broad worldwide, affiliate-wide, or all-business restrictive covenants usually require narrowing or escalation. Prefer transferred/target business, existing products, and current territories when the policy requires limited scope.
- Employee transfer packages often require comparable offers for all business employees and buyer responsibility for WARN/severance for transferred employees when the seller playbook says so.
- TSA/service continuity should include required operational services from disclosures and material-contract dependencies, sorted by code.
- IP transition terms should protect retained IP boundaries and limit trademark phase-out or transition licenses to the policy period and scope.
- NWC terms should use the active target/collar and the specified adjustment mechanic; do not reset targets to stale or counterparty values without support.

## Answer Shaping By Task Type

For first-draft term population:

- Populate all requested drafting fields, even when a policy check is within policy.
- Use active deal profile and active cap table/allocation schedule for values and allocations.
- Include policy checks sorted by check ID when the template asks for a full checklist.
- Record overrides and superseded source IDs only in fields designed for that purpose.

For counterparty draft review or issue registers:

- Compare the active draft against current client instructions and the applicable playbook.
- Include only material deviations or requested priority issues.
- For economic issues, output corrected policy values and calculated amounts.
- `source_ids` should be concise audit anchors: draft/clause, active instructions, financial schedule, playbook, and benchmark where relevant.

For committee escalation packets:

- Include terms that require committee route, approval, or renegotiation.
- Use committee member names exactly from the Deal Desk committee record.
- Quantify exposure only where the template provides fields and the Deal Desk supports the calculation.
- Aggregate risk should reflect the highest material risk and the primary driver terms listed in sorted order.

For transition packages:

- Separate priority deviations from structured transition flags.
- Employee, TSA, restrictive covenant, IP, escrow, and deadline flags should reflect the current draft plus client/playbook target and fallback positions.
- Use required approval owner enums from the template.

## Final Validation

Before returning:

1. Parse the JSON mentally or with a JSON validator if available.
2. Confirm every enum value appears in the template.
3. Confirm all required keys are present and no extra keys were added.
4. Confirm numbers use the required unit and precision.
5. Confirm sorted lists are actually sorted.
6. Confirm source IDs are deal-specific and active/current unless intentionally listed as superseded.
7. Confirm the answer contains no narrative outside the JSON object.
