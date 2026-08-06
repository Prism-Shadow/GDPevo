---
name: court-closeout-reconciliation
description: Reconcile clerk closeout packets for court dispositions, traffic citations, financial registers, payment petitions, probation referrals, license suspension orders, and form placeholders. Use when a task asks Codex to combine local hearing notes, worksheets, petitions, form excerpts, and case-management portal records into a structured JSON packet with current fees, payment plans, dispositions, exclusions, and audit decisions.
---

# Court Closeout Reconciliation

## Core Workflow

1. Read the prompt, answer template, and every local payload before filling any field. Treat the template as the contract: use its exact keys, enum values, date format, currency type, and sort rules.
2. Build a matter-by-matter evidence table from all available sources: local hearing/minute notes, finance worksheets, petition/budget summaries, form excerpts, portal case or citation records, charge rows, docket entries, fee schedules, payment policies, forms, and financial petition records.
3. Reconcile conflicts before writing JSON. Do not copy a worksheet or portal row blindly when a signed order, minute note, or current policy contradicts it.
4. Fill the output from the reconciled evidence table, then verify every total and every sort order.

## Source Hierarchy

- Use signed orders, courtroom minutes, hearing notes, or docket continuance notes to control disposition, plea, finding, sentence, probation referral, and hold/exclusion decisions.
- Use portal case or citation records to corroborate identity, jurisdiction, status, counsel, disposition dates, and petition metadata unless a local correction explicitly supersedes them.
- Use current effective fee schedules and current payment policies for amounts and account-fee treatment. Stale schedules, draft worksheets, statutory maximum notes, and old form footers are not enough to post a fee.
- Use form metadata labels when the schema asks for a form label and a current form record exists. Use local form excerpts for visible labels, account-reference rules, required section labels, and placeholder text when the portal does not provide the needed detail.
- Use the exact placeholder text from the materials, commonly `TBD from case file`, for missing identifiers, addresses, phone numbers, driver-license numbers, probation office details, or other required fields. Do not invent contact details or identifiers.

## Dispositions And Audit Decisions

- Mark a matter disposed only when a final disposition or signed order is supported. Pending, continued, deferred, or unsigned matters must be held or excluded according to the schema.
- For pending or unsigned matters, use null for disposition dates when the template says no disposition date should be entered. Keep next status or return dates in their specific fields.
- Distinguish public defender, appointed private, and retained counsel. Do not assess public-defender user fees for appointed-private counsel.
- For amended counts, post fees for the conviction count only. If a controlled-substance count is amended away, remove drug or lab assessments tied only to that count.
- For controlled-substance convictions, include mandatory current assessments when the schedule or hearing notes support them, even if the worksheet omitted them.
- Treat draft plea sheets and finance queues as nonfinal. They can explain an audit conflict, but they do not authorize disposition or financial posting.
- Enter departure status only when supported by the final sentence record. Remove stale departure labels when the hearing note or recorded bench statement says no departure was entered.

## Financials

- Compute each matter total from allowed fee items only: current court costs, fines actually imposed, mandatory assessments, policy-supported user/account fees, restitution balances, and approved surcharges.
- Exclude unsupported add-ons such as account-management, late, collection, DMV, returned-payment, traffic-school, copy, certification, court-appointed-attorney, or court-reporter fees unless the current policy or order directly supports them.
- Keep pending, continued, and unsigned matters out of posted register totals. If the schema has a pending/hold fee status, use that status and follow the schema for whether held amounts or zero posted amounts should be shown.
- Batch totals should reconcile exactly to the posted or approved matters described by the schema. Recompute subtotals by fee type after applying exclusions.

## Payment Petitions And Plans

- Classify first petitions as initial installment plans unless the materials identify a later review, default, deferral, or exemption.
- Use the requested installment amount when it falls within the policy band and the budget supports it. Otherwise classify it against the policy and budget enums.
- Exclude account fees when the local policy amount is zero or the fee is only from an old worksheet/footer. The amount due should not include excluded fees.
- Apply restitution before fines and costs when policy says so and restitution is part of the balance; use fines-and-costs-only when restitution is zero.
- Prefer an explicit first due date or return-to-court date from the packet. Otherwise derive dates from the current policy offsets and the petition/order date.
- For installment math, subtract any down payment, divide the remaining balance by the regular installment, count full installments, add one final installment for any remainder, and set the final due date by advancing the payment cadence from the first due date.

## Traffic Citations

- Derive the violation tier from the actual speed and speed limit, then match it to the current jurisdiction schedule.
- Add mandatory current surcharges once per citation when the schedule says to do so.
- Use the citation number as the account reference when the form or file says no separate case or account number exists.
- Exclude stale fine tables, statutory maximum substitutions, and optional post-disposition fees unless there is a current policy or triggering event.

## Probation And License Forms

- Prepare probation referral data only when supervised probation or a referral order is actually ordered. If the notes say no referral was signed, do not use a carried-forward report time.
- Prepare license suspension orders from the conviction and license notes. Use the explicit start basis if stated; otherwise use the conviction date for a conviction-triggered suspension.
- Use the form ID from current metadata. Preserve missing driver-license numbers and other required identifiers as placeholders.

## Output Checks

- Sort arrays exactly as the answer template instructs.
- Use enum strings exactly as listed; do not replace them with prose.
- Use JSON numbers for currency fields, not strings.
- Verify every case total, petition total, installment count, final payment, and batch subtotal.
- Do not include explanations, citations, or markdown in the final JSON unless the prompt explicitly asks for them.
