# Court Closeout Reconciliation Rules

## Matter Status

- Post a disposition only when the final hearing/order facts show a plea, finding, sentence, or signed final order that the template treats as disposed.
- Hold or exclude a matter when the record says continued, deferred, no final order, unsigned order, status issue, or no plea accepted. Financial posting is not allowed for these matters unless the template says otherwise.
- Use `null` for dates only when the template allows it. Otherwise use the required placeholder or the relevant hearing/disposition date supported by the evidence.

## Identity And Counsel

- Prefer portal CMS identity and DOB when available and consistent with the target matter.
- If identity fields are missing and the payload warns against borrowing from another matter, use the exact placeholder required by the payload or template.
- Distinguish public defender from appointed private counsel. Appointed private, APD-as-appointed-private, county-pay private, and retained counsel are not public-defender user-fee eligible unless the current policy explicitly says otherwise.
- Use local corrections for counsel only when corroborated by a memo, docket note, hearing note, or portal record.

## Charges, Dispositions, And Departures

- Use final courtroom/hearing facts for the accepted plea, finding, amendment, convicted count, sentence, and whether a count was dismissed or amended away.
- Do not copy stale charge-screen values when they conflict with a final hearing note or signed order.
- Apply controlled-substance, laboratory, or drug assessment fees only to final convictions that still qualify after amendments and dismissals.
- Treat departure status as none or not applicable unless the final record explicitly supports a departure finding. A judge's statement that the sentence is top-of-range or not a departure controls over draft worksheet labels.
- For bench trials, use the schema's no-plea or not-applicable enum if no plea was entered.

## Fee Posting

- Start each matter at zero and add only fees supported by the final disposition plus the current effective fee schedule or payment policy.
- Use pronounced fines when the criminal sentence sets a fine. Use the current standard fine and mandatory surcharge for traffic violations when the fee schedule controls the amount due.
- Add court costs only when a disposed matter is eligible and the current schedule supports them.
- Add public-defender user fees only for public-defender representation when not waived and supported by policy or schedule.
- Add restitution only when the order or petition balance supports restitution.
- Exclude unsupported or stale items such as account-management fees, collection fees, late fees, DMV or reinstatement fees, returned-check fees, traffic-school fees, attorney fees, reporter fees, copy fees, certification fees, old schedule amounts, and statutory maximum substitutions unless current policy or the final order expressly authorizes them.
- Held, pending, deferred, and unsigned-order matters should have no posted fee items and zero financial totals unless the template explicitly asks for a different treatment.

## Payment Petitions And Plans

- Classify first petitions as initial installment requests unless the evidence shows a default, subsequent review, deferred-payment order, or exemption.
- Compute disposable income as monthly income minus monthly obligations.
- Check requested installment amounts against the current policy band and disposable income:
  - below the policy minimum means below-policy classification;
  - above the policy maximum means above-policy classification;
  - greater than disposable income means unsupported by budget;
  - otherwise the request is budget-supported.
- Use the policy account fee, not stale counter notes or obsolete form footers.
- Apply restitution priority from policy. When restitution exists and policy prioritizes restitution, classify the application order accordingly; otherwise use fines-and-costs-only for matters with no restitution balance.
- Compute installment schedules from the balance after any down payment. The last installment is the remainder when the balance does not divide evenly.
- Compute the final due date by adding `total_installments - 1` calendar months to the first due date for monthly plans.
- Compute return-to-court dates from explicit candidate dates when provided and supported; otherwise add the policy return-to-court offset to the final due date.

## Forms And Placeholders

- Use current portal form metadata for form IDs and labels.
- Preserve local form labels required by the template, including account-reference label text when the template asks for it.
- Use citation number as the account reference for a traffic matter when the form rule says no separate case or account number exists.
- Use placeholders only for missing identifiers, contact details, party details, probation office details, and similar form-required fields. Do not use placeholders for legal outcomes, balances, fees, or dates that can be derived from the evidence.
- Sort placeholder fields alphabetically when the template requests field-name ordering.

## Totals And Exclusions

- Recalculate batch totals from the emitted matter rows after all holds and exclusions.
- Count disposed, assessed, held, pending, or excluded matters according to the schema definitions, not according to stale worksheet status.
- Include an exclusion row only when the template asks for unsupported, stale, pending, or omitted items.
- For unsupported-charge totals, use zero when the answer is reporting the amount actually included after correction.
