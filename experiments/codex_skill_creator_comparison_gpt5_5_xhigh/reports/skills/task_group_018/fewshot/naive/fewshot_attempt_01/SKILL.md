---
name: court-closeout-json
description: Solve court closeout, disposition register, payment plan, probation referral, and license order tasks by reconciling local payloads with a Court Operations Portal and returning schema-exact JSON.
---

# Court Closeout JSON Skill

Use this skill when a task asks for a clerk-ready JSON answer for court disposition closeout, docket/register reconciliation, traffic citation payment plans, financial petitions, probation referrals, license suspension orders, or similar post-disposition court packets.

## Core Rule

Return only the JSON object requested by the task. The local `input/payloads/answer_template.json` is the output contract: preserve its required top-level keys, field names, allowed enum values, list ordering rules, date/datetime formats, null rules, and currency precision. Do not add explanatory markdown or unsupported fields.

## One-Pass Workflow

1. Read the prompt and every file under `input/payloads/`.
2. Read `answer_template.json` first or revisit it before writing the answer. Treat it as authoritative over natural-language expectations.
3. Extract the target matters: cases, citations, petitions, jurisdiction, hearing/disposition dates, and listed portal endpoints.
4. Query the Court Operations Portal at the task's `<TASK_ENV_BASE_URL>` using only endpoints named or clearly relevant in the prompt. Use `/api/search` to locate identifiers when needed, then fetch structured records from matter-specific endpoints such as cases, citations, charges, docket entries, fee schedules, payment policies, forms, and financial petitions.
5. Reconcile local notes, worksheets, petitions, and portal records into one matter-by-matter fact table before composing JSON.
6. Apply the template's sorting rules and calculate totals from the accepted per-matter entries.
7. Validate the final object against the template manually: required keys present, enum strings exact, unsupported items excluded, numbers numeric, dates ISO-formatted, and no commentary outside JSON.

## Source Priority

Use the most authoritative source for each type of fact, not the first source encountered.

- Identity and case posture: prefer current portal case/citation records, unless local court notes explicitly say the portal must be corrected or verified.
- Hearing outcome and sentence: prefer signed order, courtroom/hearing notes, or sentencing intake facts over draft finance queues, scratchpads, legacy worksheets, and intake carry-forward rows.
- Counsel classification: distinguish public defender from appointed private counsel and retained counsel. Do not impose public-defender fees for appointed private or retained counsel unless current policy and the case record directly support it.
- Financial amounts: use the active fee schedule or payment policy for the disposition/petition date. Exclude stale schedules, archived fees, statutory maximum substitutions, draft rows, and fees with no triggering event.
- Form metadata: use current portal form records when available; use local form excerpts for required labels and placeholder behavior.
- Pending/unsigned matters: do not dispose, post financials, or include in disposed-register totals when no final order, signed disposition, accepted plea/finding, or required final status exists.

## Conflict Handling

When sources disagree, include an audit/conflict item if the schema has a place for it. State the stale or conflicted value, the corrected value, and a compact resolution source using the template's allowed enum vocabulary.

Common conflict patterns:

- Name or DOB mismatch between worksheet and CMS: use verified CMS/case-file identity, or the required placeholder when genuinely missing.
- Public-defender label copied from a calendar but corrected by counsel memo or courtroom note: classify as appointed private if the correction says county-appointed private counsel.
- Draft disposition or finance queue conflicts with docket status: hold or exclude when the final order was unsigned, continued, or pending.
- Controlled-substance or lab-assessment flags: only include assessment fees for the convicted/amended count that actually triggers the current schedule.
- Old local forms or scratchpads listing account-management, collection, late, DMV, returned-check, traffic-school, restitution, reporter, copy, or certification fees: exclude unless current policy plus case facts create that charge.

## Financial Rules

- Currency values must be JSON numbers rounded to cents. Do not quote money values.
- `total_due`, `amount_due`, `case_total`, and register totals are computed from included, supported line items only.
- Count only matters with postable dispositions in assessed/disposed totals. Held, pending, continued, unsigned, or excluded matters contribute zero unless the template says otherwise.
- For traffic citations, amount due is the current standard fine for the resolved tier plus supported jurisdictional surcharges; do not replace a standard fine with a statutory maximum unless the current schedule and disposition require it.
- For Virginia-style payment petitions, total due is fines/costs plus restitution plus policy-supported account fees. If policy excludes an account fee, set the fee amount to zero and mark the policy treatment or exclusion as the schema requires.
- If restitution exists and policy says it receives priority, set the payment application order accordingly; otherwise use the fines/costs-only or policy-specific order.

## Payment Schedule Math

Use the approved interval, first due date, regular installment amount, down payment, and total due from the accepted facts and policy.

- Balance for scheduling is `total_due - down_payment`.
- If the balance is zero, use zero installments only if allowed by the template; otherwise follow the template's no-agreement fields.
- For regular installment plans, compute:
  - `full_installment_count = floor(balance / regular_installment_amount)` when there is a nonzero remainder, otherwise `balance / regular_installment_amount`.
  - `final_payment_amount = remainder` when nonzero, otherwise the regular installment amount.
  - `total_installments = full_installment_count + 1` when there is a nonzero remainder, otherwise `full_installment_count`.
- `final_due_date` is the due date of the last installment, advancing by the interval from the first due date.
- `return_to_court_date` comes from the petition, policy, or form instruction when provided; otherwise derive it only if the policy gives a clear rule.

## Probation and License Packets

For post-sentencing form packets:

- Prepare probation referral fields only when supervised probation or a signed referral order exists.
- Use the conviction date, not release date or petition date, for license suspension start when the form/policy bases suspension on conviction.
- Calculate suspension end dates by adding the ordered number of months to the suspension start date.
- Use the exact placeholder text required by the payload or form metadata for missing identifiers, addresses, phone numbers, driver license numbers, probation officer names, and office locations.
- Do not invent contact details, identifiers, probation office data, attorney data, judge data, or balances absent from the available materials.

## Output Assembly Checklist

Before finalizing:

- The answer starts with `{` and ends with `}`.
- Every required top-level key from `answer_template.json` is present.
- Arrays are sorted exactly as the template requires, usually by case number, citation number, petition id, field name, or charge code.
- Nulls are used only where the template permits them; placeholders are used only where the materials require them.
- Dates use `YYYY-MM-DD`; local datetimes use `YYYY-MM-DDTHH:MM:SS`; times use the template's requested format.
- All totals equal the sum of included child records.
- Exclusion lists cover every unsupported/stale fee or charge surfaced by the prompt, local files, or portal, using the template's reason-code vocabulary.
- No task-specific notes, citations, names, amounts, or case facts from prior examples are carried into the answer.
