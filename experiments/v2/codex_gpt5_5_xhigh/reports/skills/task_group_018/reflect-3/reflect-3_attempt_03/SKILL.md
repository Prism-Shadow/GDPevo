---
name: court-packet-reconciliation
description: Prepare clerk-ready court closeout, disposition, payment-plan, supervision, and form-packet JSON outputs from mixed local records and official case/fee/policy/form data. Use when a task requires reconciling hearing notes, worksheets, case records, charges, payment petitions, fee schedules, policies, forms, missing identifiers, pending matters, and stale or conflicting financial entries into a strict answer template.
---

# Court Packet Reconciliation

## Workflow

1. Read the prompt, local payloads, and answer template before filling any fields. Treat the template as the contract: required keys, enum spellings, sort order, date format, null handling, and currency precision all control the output.
2. Build a short private reconciliation table per matter. Track identity, status, plea/finding, sentence, fee basis, payment-plan basis, form requirements, missing fields, exclusions, and totals.
3. Compare each source against the role it is best suited for:
   - Use courtroom notes, signed-order notes, sentencing intake, and petition intake for what the court actually ordered.
   - Use official case/citation records for verified identity, DOB, case status, counsel, and filing metadata unless the local material flags the field as missing or unresolved.
   - Use current fee schedules and payment policies for amounts, eligibility, account fees, minimum payments, due dates, and priority rules.
   - Use current form metadata and local form excerpts for form IDs, labels, account-reference handling, required fields, and placeholder text.
4. Resolve conflicts explicitly in the output when the schema has audit or exclusion fields. Do not carry stale worksheet/import values into the corrected disposition or financial totals.
5. Produce only the requested JSON object unless the user asks for explanation.

## Authority Rules

- A final courtroom disposition or sentencing note beats a stale charge row, finance queue, worksheet outcome, or old import.
- A pending, continued, unsigned, deferred, or no-final-order matter must not receive a final disposition or financial posting just because a draft queue contains plea, conviction, or fee values.
- Verified identity from official records is usable for entry. If the materials say an identifier is missing or must be verified, use the exact required placeholder and do not borrow from similar names, prior searches, or inferred demographics.
- Counsel classifications matter for fees. Do not treat retained counsel or appointed private counsel as public defender representation unless the current record supports that classification.
- Assessments and special fees attach only when the current conviction, order, schedule, and policy support them. Remove fees tied to amended-away, dismissed, pending, stale, untriggered, or unsupported entries.
- A statutory maximum note, obsolete schedule, old account-maintenance row, sticky-note fee, or future-triggered collection/late/returned-payment/DMV item is not part of the starting balance unless a current order or policy makes it due.
- Restitution priority applies only to supported restitution balances. Keep restitution, fines/costs, assessments, user fees, and account fees separate when the schema separates them.

## Financial Math

- Sum totals from posted/supported items only. Held, pending, excluded, waived, unsupported, and stale amounts contribute zero unless the schema asks for a separate excluded amount.
- Payment-plan amount due is the supported balance after down payment: fines/costs plus supported restitution plus included policy fees.
- Confirm the requested installment amount against the policy band and available budget. Classify unsupported, below-minimum, above-maximum, or manual-review cases using the schema enums.
- For installment schedules, count full regular installments with floor division, add one final installment for any remainder, and set the final payment to the remainder. If the balance divides evenly, the final payment is the regular installment and total installments equals the full-installment count.
- Compute the final due date by adding `total_installments - 1` payment intervals to the first due date. Use explicit due dates from current materials when supplied; otherwise calculate from the active policy anchor.
- Use the active policy for return-to-court dates and ignore stale candidate dates that were derived from obsolete schedules or notes.

## Form And Placeholder Handling

- Fill form IDs, labels, account references, and required labels from current form metadata or local excerpts. If no separate case or account number exists and the form says to use another matter identifier, use that identifier exactly.
- Use the exact placeholder text required by the materials for missing identifiers, addresses, phone numbers, driver license numbers, probation-office details, or other required form fields.
- List missing fields only when the answer template asks for them, sorted exactly as instructed.
- Do not invent probation officers, office locations, contact details, license numbers, addresses, account numbers, or conditions.

## Output Checks

- Match every top-level key and nested shape in the template.
- Use enum values exactly; do not replace them with prose.
- Sort arrays by the template's ordering rule.
- Use ISO `YYYY-MM-DD` dates and local `YYYY-MM-DDTHH:MM:SS` datetimes when required.
- Use numeric currency values, not strings.
- Use `null` only where the template permits it; otherwise use the required placeholder or enum.
- Recalculate batch/register totals after exclusions and holds.
