---
name: court-closeout-reconciliation
description: Use this skill for clerk-ready court disposition closeouts, sentencing registers, traffic violation payment plans, financial petitions, probation referrals, license-suspension orders, and related court operations JSON packets. It is especially important whenever a task combines local payload files with a Court Operations Portal and asks for strict schema JSON, fee reconciliation, payment schedule math, placeholder handling, exclusions, audit findings, or docket/register totals.
---

# Court Closeout Reconciliation

Use this skill when preparing structured court closeout or post-disposition JSON from local case materials and the Court Operations Portal. The core job is to reconcile competing sources, follow the supplied answer template exactly, and compute only supported financial and schedule fields.

## Operating Rules

- Return JSON only when the prompt asks for JSON. Do not include markdown, notes, citations, or explanations outside the object.
- Use only the user-provided local files and the task's Court Operations Portal. Do not infer laws, fee amounts, contact details, identifiers, or form fields from general knowledge.
- Treat `input/payloads/answer_template.json` as the contract for shape, enum spellings, required keys, sort order, date formats, null handling, and placeholder values.
- Read every local payload before finalizing. Local notes often explain stale worksheets, unsigned orders, amended charges, excluded fees, and placeholder policy.
- Query the portal endpoints named in the prompt. Portal responses use `{ "count": ..., "results": [...] }`; work from `results`.

## Portal Workflow

1. Identify every target `case_number`, `citation_number`, and `petition_id` from the prompt and payloads.
2. Find each target's jurisdiction from the target record, jurisdiction table, prompt, or local materials.
3. Query typed endpoints before relying on search:
   - Criminal cases: `/api/cases?case_number=...`, `/api/charges?case_number=...`, `/api/docket-entries?case_number=...`
   - Traffic citations: `/api/citations?citation_number=...`
   - Financial petitions: `/api/financial-petitions?petition_id=...` and, when useful, `?case_number=...`
   - Schedules/policies/forms: `/api/fee-schedules?jurisdiction_code=...`, `/api/payment-policies?jurisdiction_code=...`, `/api/forms?jurisdiction_code=...`
   - Jurisdiction lookup: `/api/jurisdictions`
4. Use `/api/search?q=...` only as a supplement or discovery aid. It may omit related records, so it is not authoritative for charges, citations, or petitions.
5. If a filter returns nothing but the endpoint is relevant, fetch the endpoint and filter locally by identifiers and jurisdiction.

## Source Precedence

Use this precedence model unless the task's materials give a more specific rule:

- The answer template controls output structure and enum wording.
- A final signed order, final hearing note, or explicit disposition note controls whether a matter can be posted. If the matter was continued, deferred for unsigned order, or lacks a final disposition, mark it held/pending/excluded as the template allows and post no financial register amount.
- Courtroom/hearing notes control final plea, finding, count outcome, sentence, signed-order status, judicially announced fines, and amendments when they conflict with stale intake or finance worksheets.
- Portal case records are strong evidence for case identity, jurisdiction, CMS status, counsel classification, DOB, disposition date, and current source-system values. Do not borrow identity data from search near-matches or similarly named people.
- Corroborating local memos can override shorthand labels, typo-prone bench sheets, and finance queue imports when they directly identify the correction.
- Raw labels are not enough for fee eligibility. For example, an appointed-private or APD-style label is not a public-defender user fee unless the reconciled counsel type is actually public defender.
- If a conflict remains unresolved and the template has audit, verify, placeholder, hold, or exclusion fields, surface the conflict there instead of silently choosing a value.

## Financial Rules

- Use fee schedules active on the disposition or hearing date for the target jurisdiction. A schedule with an `end_date` before the disposition date is stale.
- Include only fees supported by a current schedule, payment policy, final order, petition balance, or hearing directive.
- Exclude stale, scratchpad, late, collection, DMV, returned-check, traffic-school, copy/certification, account-management, attorney, court-reporter, and miscellaneous fees unless the final order or current policy directly triggers them.
- For criminal matters, post mandatory court costs for disposed convictions when the schedule supports them. Use a fine only when announced, ordered, or present in the reconciled charge record.
- Drug, controlled-substance, and crime-lab assessments apply only to final qualifying convictions. Do not apply them to dismissed, pending, or amended-away drug counts.
- Public defender user fees apply only when reconciled counsel classification is public defender and the current schedule/policy supports the fee. Do not apply them to retained or appointed-private counsel.
- For traffic citations, choose the current standard-fine tier by `violation_code` or speed-over-limit, then add the current per-citation county surcharge when required. Do not substitute a statutory maximum for the standard fine unless the template or policy explicitly says to.
- For financial petitions, compute `total_due` from supported balances after excluding policy-disallowed account fees. Include restitution only when the petition or portal shows a restitution balance.
- Batch/register totals sum only posted matters. Held, pending, unsigned, or excluded matters contribute zero to financial totals unless the template explicitly says otherwise.

## Payment And Date Math

Use `scripts/court_math.py` for installment and date calculations when available:

```bash
python scripts/court_math.py installments --total 999.99 --installment 80 --first-due 2030-01-15 --return-offset-days 45
python scripts/court_math.py add-months --date 2030-01-31 --months 2
```

Run those commands from the skill directory, or prefix `scripts/court_math.py` with the skill path. The script is generic; substitute task values. If you calculate manually:

- Remaining balance is `total_due - down_payment`.
- `total_installments = ceil(remaining_balance / regular_installment_amount)`.
- If there is a remainder, `final_payment_amount` is that remainder and `full_installment_count` is the number of full regular installments before it.
- If the balance divides evenly, the final payment is the regular installment amount and every installment is full.
- `final_due_date` is the first due date plus `total_installments - 1` calendar months, preserving the day where possible.
- `return_to_court_date` comes from the local materials or portal when supplied; otherwise compute from the governing policy offset when the template asks for it.
- For monthly disposable income, subtract monthly obligations from monthly income. Compare the proposed installment to both disposable income and the policy minimum/maximum before assigning support classification.
- For license suspensions, use the conviction date as the start basis unless the materials specifically identify release date, petition date, or another start basis. The suspension end date is the start date plus the number of suspension months.

## Placeholders

- Use the exact placeholder text required by the payloads, template, or portal form metadata. Commonly this is `TBD from case file`, but do not normalize if the task provides a different value.
- Use placeholders only for genuinely missing required identifiers or contact/office details such as SSN, driver license number, address, phone, probation officer, or probation office location.
- Do not use placeholders for amounts, dates, statuses, or counts that can be calculated or reconciled from available materials.
- When the template asks for placeholder summaries, list all missing fields and sort them exactly as the template directs.

## Output Assembly Checklist

Before final answer:

1. Confirm every required top-level key and nested required key from the answer template is present.
2. Use enum values exactly as written in the template.
3. Format dates as ISO dates or datetimes as requested; use `null` only when the template allows it.
4. Emit currency as JSON numbers rounded to cents, not strings.
5. Sort all arrays according to template instructions, usually by matter identifier and then issue/item name.
6. Recompute case totals, schedule totals, and batch/register totals from the final included line items.
7. Verify held or pending matters have no posted financial amount unless explicitly allowed.
8. Remove unsupported fees from balances and, when the template has an exclusions section, record the exclusion reason using the provided enum.
