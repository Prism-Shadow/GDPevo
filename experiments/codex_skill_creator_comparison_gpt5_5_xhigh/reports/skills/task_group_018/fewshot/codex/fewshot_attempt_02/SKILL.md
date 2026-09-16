---
name: court-closeout-reconciler
description: Reconcile court closeout tasks that require a structured JSON answer from local payloads and a Court Operations Portal. Use for criminal disposition registers, traffic citation closeouts, payment-plan packets, sentencing/probation/license form packets, fee-schedule audits, and tasks with answer_template.json plus endpoints such as cases, charges, citations, fee-schedules, payment-policies, forms, docket-entries, financial-petitions, or search.
---

# Court Closeout Reconciler

## Core Workflow

1. Read the user prompt, `answer_template.json`, and every local payload before querying the portal. Extract target case/citation/petition identifiers, jurisdiction, hearing or disposition date, required top-level keys, enum values, sorting rules, money precision, date formats, null/placeholder rules, and fields that must be calculated.
2. Query the portal narrowly with exact identifiers. Prefer typed endpoints first, then `search` if needed:
   - `cases?case_number=...`
   - `charges?case_number=...`
   - `docket-entries?case_number=...`
   - `citations?citation_number=...`
   - `financial-petitions?case_number=...` or `financial-petitions?petition_id=...`
   - `fee-schedules?jurisdiction_code=...`
   - `payment-policies?jurisdiction_code=...`
   - `forms?jurisdiction_code=...`
   If a filtered endpoint unexpectedly returns unrelated records, ignore records outside the target identifiers and do not use broad portal data to infer unseen matters.
3. Build a work table per matter containing local hearing facts, portal identity/status, charge/citation details, current schedules, policy values, and form metadata. Mark conflicts explicitly instead of silently choosing a source.
4. Fill the required JSON shape exactly. Use enum strings from the template, numeric money values rounded to cents, ISO dates, and `null` only when the template permits it. Sort every list exactly as instructed by the template.

## Source Priority

- Use portal case or citation records for verified identity, DOB, jurisdiction code, status, attorney name, and active citation speed/violation metadata unless a stronger local correction is corroborated by another source.
- Use local hearing notes, signed-order statements, and closeout memos for what the court actually accepted, found, continued, held, amended, or pronounced. These can override stale charge dispositions, worksheets, draft queues, and imported labels.
- Use current active fee schedules for mandatory costs, assessments, surcharges, and user fees. Ignore stale schedules, archived amounts, intake scratchpads, and obsolete form footers unless the current schedule or policy supports the charge.
- Use payment policies for first-due timing, account-fee treatment, monthly minimum/maximum bands, down-payment rules, restitution priority, and return-to-court offsets.
- Use form metadata for form IDs, labels, required fields, and placeholder instructions. Use local form excerpts for account-reference handling and visible field labels when the form endpoint does not provide that detail.

## Reconciliation Rules

- Do not post disposition financials for a matter that stayed pending, was continued, lacks a signed final order, or was explicitly held. Record the hold/exclusion using the template's status/action enums and leave financial totals at zero for that matter.
- Treat draft queue rows, old worksheets, and sticky notes as audit clues only. They are not authority for adding fines, assessments, late fees, collection fees, DMV fees, returned-check fees, traffic-school fees, account-management fees, restitution, attorney fees, reporter fees, copy fees, or certification fees.
- Public-defender user fees apply only when the resolved counsel classification is public defender and the hearing/order/policy does not waive or exclude the fee. Appointed-private or county-pay counsel is not public defender fee eligible.
- Controlled-substance convictions usually require the current drug or laboratory assessment when the active fee schedule marks it mandatory. Do not apply that assessment to an original controlled-substance count that was amended away, dismissed, or not the conviction count.
- For amended charges, count the final conviction count separately from dismissed or amended-away counts. Use the final offense and plea/finding from the hearing notes or signed order.
- For departures, prefer the judge's stated sentence characterization. A worksheet label or legacy charge-screen departure does not control if the judge or hearing note says there was no departure or that the sentence was simply top-of-range.
- For traffic citations, compute amount due from the current standard fine for the active violation code plus mandatory current surcharges. Do not substitute statutory maximum notes for a current standard fine unless the current schedule/policy requires it.

## Payment And Budget Math

- Total due is the sum of supported balances and current supported fees after exclusions. If restitution is present and policy gives it priority, set the payment application order accordingly; otherwise use the template's fines/costs-only or no-restitution enum.
- Disposable income is monthly income minus monthly obligations. Classify a requested installment as supported when it fits the policy band and does not exceed disposable income; otherwise choose the closest template enum for below-minimum, above-maximum, unsupported, or judge-review.
- For installment plans:
  - Balance to schedule = total due minus down payment.
  - Use a local or portal candidate first due date when one is provided. Otherwise add the payment policy's first-due offset to the petition, agreement, or disposition date identified by the materials.
  - Full installment count = floor(balance / regular installment).
  - If there is a remainder, add one final installment for the remainder.
  - If there is no remainder, the final installment is the regular installment.
  - Final due date is the first due date plus one interval for each installment after the first.
  - Return-to-court date is the final due date plus the policy offset unless a local/portal candidate date controls.
- Use `scripts/installment_math.py` when payment-plan arithmetic is non-trivial.

Example:

```bash
python3 skill/scripts/installment_math.py \
  --total 0 \
  --regular-amount 1 \
  --first-due-date 2025-01-15 \
  --return-offset-days 60
```

Replace the example arguments with task values; do not use the example result in an answer.

## Form And Placeholder Handling

- Use the exact placeholder text required by the local materials or form metadata. When the materials require a case-file placeholder, preserve that string exactly and do not invent identifiers, addresses, phone numbers, driver license numbers, probation officers, offices, or other contact details.
- Placeholder reports should include only fields that are required or naturally requested by the schema. Sort placeholder field paths or missing-field names alphabetically when the template says to do so.
- For traffic payment forms, if no separate court case or account number exists and the local form instructions say to use the citation, use the citation number as the account reference.
- For payment petitions, classify a first/current petition as an initial installment unless the materials identify a default, later review, deferred lump-sum agreement, exemption, or no-payment posture.
- For probation referral forms, prepare the referral only when supervised probation or a signed referral/reporting obligation exists. A report datetime on a payment-petition endpoint does not by itself create a referral if the local sentencing/probation materials say no referral order was signed. If no referral order was signed, use the template's not-ordered enum and do not invent report data.
- For license suspension forms, use the basis stated in the materials. DUI-style suspensions commonly start on conviction date unless the materials specify release date, petition date, or another start basis. Compute the end date by adding the ordered months to the start date.

## Output Checks

- Ensure every required top-level key is present and no markdown surrounds the JSON.
- Recalculate all subtotals and batch totals from the posted/assessed items only; held or excluded matters should affect only hold/exclusion counts.
- Confirm arrays are sorted by the template's ordering rule, not by the order in notes.
- Confirm excluded charges/items include only unsupported items actually raised by local materials, queue rows, scratchpads, stale schedules, or policy conflicts.
- Confirm audit findings state the conflict, corrected value, and resolution source when the schema asks for them.
