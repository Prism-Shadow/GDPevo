---
name: court-closeout-json
description: Use this skill for court-operations tasks that require clerk-ready JSON closeout packets, disposition registers, payment plans, financial-petition reviews, probation referrals, license orders, fee reconciliation, docket actions, placeholders, and audit findings from local payloads plus a Court Operations Portal API.
---

# Court Closeout JSON

## Core Workflow

1. Read the prompt, `input/payloads/answer_template.json`, and every local payload before writing anything. Treat the template as the contract for top-level keys, required fields, enum spellings, sorting, date formats, null handling, and currency precision.
2. Extract target identifiers: case numbers, citation numbers, petition IDs, jurisdiction codes, hearing/disposition dates, and named local files. Do not query unrelated matters.
3. Fetch portal records for each target. Use targeted filters first:
   - Criminal matters: `/api/search?q={case_number}`, `/api/cases?case_number={case_number}`, `/api/charges?case_number={case_number}`, `/api/docket-entries?case_number={case_number}`.
   - Traffic matters: `/api/citations?citation_number={citation_number}`.
   - Financial petitions: `/api/financial-petitions?petition_id={petition_id}` and, when needed, `/api/financial-petitions?case_number={case_number}`.
   - Jurisdiction context: `/api/jurisdictions?jurisdiction_code={jurisdiction_code}`, `/api/fee-schedules?jurisdiction_code={jurisdiction_code}`, `/api/payment-policies?jurisdiction_code={jurisdiction_code}`, `/api/forms?jurisdiction_code={jurisdiction_code}`.
4. Reconcile sources instead of transcribing one source. Local hearing or sentencing notes usually explain what the judge ordered; portal case records usually control verified identity, status, active forms, active policies, and current fee schedules; local worksheets and scratchpads are lower-confidence audit inputs.
5. Produce one JSON object only. Validate that it parses, contains every required key, uses enum values exactly, respects ordering rules, and that totals equal the included line items.

Optional helper: `scripts/portal_snapshot.py` collects targeted portal responses into one JSON document. Optional calculator: `scripts/payment_math.py` computes installment counts and final due dates.

## Reconciliation Rules

Use current, target-specific facts. Do not carry forward draft, legacy, or scratchpad values when another source shows they are stale.

Status and disposition:
- Enter a disposed/sentenced matter only when the record supports a final disposition, accepted plea or finding, and signed/final order. If the matter was continued, deferred, unsigned, or lacks a final order, mark the closeout as hold/exclude/pending as allowed by the template and do not post financials.
- For amended charges, base conviction counts and charge-triggered fees on the final convicted offense, not the original or amended-away count.
- Treat bench-trial guilty outcomes separately from plea outcomes when the template distinguishes them.
- Record departure findings only when the final record expressly supports them. Reject legacy or draft departure labels.

Identity and counsel:
- Prefer portal/CMS identity fields for names, DOBs, jurisdiction codes, and case/citation status when available.
- Preserve explicit corrections in hearing notes or audit memos when they clarify counsel or party identity.
- Classify appointed private counsel separately from public defender counsel. Do not attach public-defender-only fees to retained or appointed-private cases.
- If a required identifier or contact field is genuinely absent, use the exact placeholder required by the template, form metadata, or local payload. Do not invent identifiers, addresses, phone numbers, license numbers, probation offices, or officer names.

Fees and financial entries:
- Use fee schedule rows active on the hearing/disposition date. Ignore rows whose effective/end dates make them stale for the matter.
- Include mandatory court costs, standard fines, surcharges, assessments, user fees, restitution, or account fees only when the current schedule, policy, final order, or conviction trigger supports them.
- Exclude unsupported add-ons such as account-management, collection, late, DMV, returned-payment, traffic-school, attorney, court-reporter, copy, certification, or restitution items unless the prompt materials or portal policy show a triggering order or event.
- For held/pending matters, set financial lines to zero or empty as the template requires, and exclude them from posted-register totals.
- Compute totals from included items, not from queued worksheet totals.

Payment plans and petitions:
- Classify first petitions as initial installment agreements unless the prompt or portal shows a default, subsequent review, deferred-only agreement, or exemption.
- Compute disposable income as monthly income minus monthly obligations. Compare the approved/requested installment to policy minimums, policy maximums, and disposable income to select the template's support classification.
- Apply restitution priority from payment policy when restitution is part of the balance. Otherwise use the template's fines-and-costs-only classification when no restitution is due.
- Exclude account fees when policy sets them to zero or does not authorize them, even if a counter worksheet carried an old fee row.
- For installment math, subtract any down payment from the balance, divide by the regular installment, create a final remainder installment when needed, and set the final due date by advancing from the first due date by `total_installments - 1` intervals. If the balance divides evenly, the final payment amount is the regular installment.
- Compute return-to-court dates from the policy offset after the final due date unless the local petition gives a candidate date that matches the policy.

Forms, Referrals, And License Orders:
- Use portal form IDs and labels when the answer template asks for form metadata.
- Prepare probation referral fields only when supervised probation or a referral order is present. If not ordered, use the template's not-ordered status and null/zero values as required.
- For license orders, start the suspension from the basis stated by the sentence, policy, or template. For DUI-style conviction consequences, the start basis is commonly the conviction date unless the materials say otherwise.
- List placeholder fields/cases in the template's required order, including missing form-required identifiers and contact details.

## Final Checks

- JSON only; no markdown wrapper.
- Dates are ISO strings; local datetimes keep seconds when required.
- Currency values are JSON numbers rounded to cents.
- Use `null` only where the template permits or requests it.
- Sort every list exactly as instructed. If no instruction is given, sort target matters by their primary identifier for deterministic output.
- Audit findings should describe only material conflicts that affect entry, posting, placeholder handling, or exclusions.
