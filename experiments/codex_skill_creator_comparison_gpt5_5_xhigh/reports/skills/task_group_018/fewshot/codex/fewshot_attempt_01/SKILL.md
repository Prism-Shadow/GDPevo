---
name: court-portal-closeout-json
description: Prepare clerk-ready court closeout, disposition, payment-plan, probation-referral, license-order, and financial-register JSON answers from local payload files plus a Court Operations Portal. Use when a task provides an answer_template.json, court hearing or sentencing notes, finance or petition payloads, and portal endpoints such as cases, charges, docket entries, citations, fee schedules, payment policies, forms, financial petitions, or search.
---

# Court Portal Closeout JSON

Use this skill to produce a single JSON object for court closeout and post-disposition packet tasks. Work from the current task only; do not reuse case-specific values from examples or prior tasks.

## Core Workflow

1. Read the prompt, then read every file under `input/payloads/`, especially `answer_template.json`.
2. Extract the target matter identifiers, jurisdiction, hearing/disposition dates, petition IDs, and required output sections.
3. Query the Court Operations Portal with targeted filters instead of scanning broad endpoint responses. You can use [scripts/portal_collect.py](scripts/portal_collect.py) to gather a compact evidence snapshot.
4. Reconcile local materials against portal records, keeping an evidence note for every conflict, exclusion, and computed amount.
5. Build the answer to match the template exactly: required top-level keys, nested keys, enum strings, ordering rules, dates, nulls, and numeric money values.
6. Validate totals, sort order, and unsupported-item exclusions before returning JSON only.

## Portal Collection

Prefer identifier-filtered calls:

```bash
python skill/scripts/portal_collect.py \
  --base-url "$TASK_ENV_BASE_URL_OR_LITERAL_URL" \
  --case CASE_ID \
  --citation CITATION_ID \
  --petition PETITION_ID \
  --jurisdiction JURISDICTION_CODE
```

Useful direct endpoint patterns:

- `GET /api/cases?case_number=...`
- `GET /api/charges?case_number=...`
- `GET /api/docket-entries?case_number=...`
- `GET /api/citations?citation_number=...`
- `GET /api/financial-petitions?petition_id=...`
- `GET /api/fee-schedules?jurisdiction_code=...`
- `GET /api/payment-policies?jurisdiction_code=...`
- `GET /api/forms?jurisdiction_code=...`
- `GET /api/search?q=...` for discovery or cross-checks

Treat portal `{"count": ..., "results": [...]}` responses as collections. If a filtered call returns multiple records, keep only records matching the target identifier and jurisdiction unless the prompt asks for related matters.

## Source Precedence

- The answer template controls output shape, enum spelling, sorting, currency precision, and date/null formatting.
- The portal controls current CMS identity, case or citation status, counsel classification, current fee schedules, active payment policy, and form metadata.
- Local signed hearing notes, sentencing intake facts, and petition materials control the courtroom disposition, sentence terms, ordered probation, approved/requested payment amount, and explicit exclusions when they are more specific than stale portal or finance queue values.
- Finance queues, scratchpads, older worksheets, and sticky-note fee lists are audit evidence, not authority. Do not carry forward stale schedule amounts or optional fees without a current schedule/policy and a triggering order or event.
- If a final order was not signed, the matter is pending, continued, deferred, or held by the prompt, do not post disposition financials. Use the template's hold, exclude, pending, or null-date representation.
- Do not invent identifiers, contact details, addresses, officer names, account numbers, or probation-office details. Use the exact placeholder required by the task materials or template.

## Financial Rules

Use active fee schedules effective on the disposition or hearing date. A schedule with an `end_date` before the disposition date is stale. Match by jurisdiction plus the relevant `fee_type`, `violation_code`, `statute`, or assessment marker.

Common reconciliation patterns:

- Post mandatory court costs only for matters that are actually being disposed or financially entered.
- Post controlled-substance drug or lab assessments only when the convicted count and current jurisdiction schedule support them.
- Post public-defender user fees only when the verified counsel type is public defender. Exclude appointed-private, retained, unknown, or conflict-labeled counsel unless the current record supports public defender treatment.
- For traffic violations, compute amount due from the active standard fine for the citation's violation tier plus any active county surcharge. Do not substitute a statutory maximum or stale standard fine unless the template explicitly asks to record it as excluded.
- For Virginia-style installment packets, total due is fines/costs plus restitution plus only policy-supported account fees. If the current policy account fee is zero or the order does not support a fee, exclude it.
- Record unsupported or stale charges in the template's exclusion section with allowed reason codes. Keep unsupported-charge totals included in the balance at zero unless the task specifically asks to quantify an erroneous inclusion.

## Payment Schedules

Use the approved or requested installment amount only if it fits the current policy band and the budget/disposable-income evidence. Classify out-of-band or unaffordable amounts with the template's available enum.

For installment math, after subtracting any down payment:

- `full_installment_count = floor(remaining_balance / installment_amount)`
- If there is a nonzero remainder, `final_payment_amount = remainder` and `total_installments = full_installment_count + 1`.
- If there is no remainder, `final_payment_amount = installment_amount` and `total_installments = full_installment_count`.
- `final_due_date` is the first due date plus `total_installments - 1` payment intervals.
- `return_to_court_date` comes from the local petition/candidate date when provided; otherwise use the policy offset from the final due date when the template requires one.

Use [scripts/payment_schedule.py](scripts/payment_schedule.py) for monthly schedule arithmetic.

## Form And Placeholder Handling

Use portal form IDs and labels when forms are required. Preserve local form label requirements such as account-reference labels or required sections if the template asks for them.

For traffic plans, use the citation number as the account reference when no separate case or account number exists and the form/policy permits it.

For probation referrals and license/installment orders:

- Prepare a probation referral only when probation is ordered or the form/prompt requires one.
- Use conviction date as the license-suspension start when the order or notes state that basis. Do not use release date unless the task specifically says the suspension starts on release.
- Keep missing driver license, SSN, address, phone, probation officer, and office-location fields as the task's required placeholder.

## Output Checks

Before finalizing:

- Confirm every required key exists and no extra top-level keys were added unless the template allows them.
- Sort each list exactly as the template says.
- Use allowed enum values verbatim.
- Use ISO dates and local datetimes in the requested format.
- Use JSON numbers for money, not strings. Round calculations to cents.
- Recompute every case total, petition total, unsupported total, and batch/register total from the itemized entries.
- Return JSON only; do not include markdown, comments, citations, or explanatory prose.
