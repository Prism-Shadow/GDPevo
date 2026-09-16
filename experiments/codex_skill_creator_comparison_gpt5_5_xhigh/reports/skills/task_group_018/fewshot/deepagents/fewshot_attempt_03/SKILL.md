---
name: court-ops-closeout-json
description: Reconcile Court Operations Portal records with local clerk, hearing, finance, petition, form, fee-schedule, and payment-policy payloads to produce strict clerk-ready JSON for criminal or traffic disposition closeouts, fee registers, payment plans, probation referrals, license-suspension orders, audit findings, exclusions, and case-file placeholders.
---

# Court Ops Closeout JSON

## Core Workflow

1. Read the prompt, `answer_template.json`, and every local payload before querying the portal.
2. Extract target identifiers: case numbers, citation numbers, petition IDs, jurisdiction, hearing/disposition dates, and named forms.
3. Let the answer template control the output shape, required keys, enum spelling, ordering rules, date format, money precision, and whether missing values should be `null`, empty arrays, or placeholders.
4. Query the portal narrowly, using only identifiers from the prompt or payloads. Keep a small source map of which fact came from local notes, CMS/citation records, charges, fee schedules, payment policies, forms, and petitions.
5. Reconcile conflicts by source priority and finality. Record audit/exclusion fields only when the template requests them.
6. Assemble JSON only. Validate it parses, uses the exact enum values, satisfies required keys, applies sorting rules, and keeps money as numeric values rounded to cents.

## Portal Fetch Plan

Use the task's base URL from the prompt or `environment_access.md`. Prefer endpoint filters over broad dumps:

- Case identity/status: `GET /api/cases?case_number=...`
- Criminal charges/sentence fields: `GET /api/charges?case_number=...`
- Docket status/history: `GET /api/docket-entries?case_number=...`
- Traffic matters: `GET /api/citations?citation_number=...`
- Financial petitions: `GET /api/financial-petitions?petition_id=...`
- Jurisdiction schedules: `GET /api/fee-schedules?jurisdiction_code=...`
- Payment rules: `GET /api/payment-policies?jurisdiction_code=...`
- Form metadata: `GET /api/forms?jurisdiction_code=...`
- Discovery fallback: `GET /api/search?q=...` when an identifier does not resolve through the specific endpoint.

If a portal record is missing, do not invent it. Use local evidence if it is final and sufficient; otherwise mark the field for verification according to the template.

## Source Priority

- The template is authoritative for structure and allowed values.
- Signed/final hearing notes, courtroom disposition notes, and final orders control what the court actually did: plea accepted, finding, final/pending status, sentence, fine waiver/imposition, supervised probation, next setting, and whether an order was signed.
- CMS case or citation records usually control normalized identity, DOB, jurisdiction code, status, attorney name, counsel type, offense/violation code, and disposition date. Use them to correct local typos unless a local final-order note explicitly says the record is unresolved or pending verification.
- Current fee schedules, payment policies, and form metadata override stale worksheets, scratchpads, obsolete footer text, and carried-forward finance rows.
- Local finance queues and worksheets are audit inputs, not posting authority, when they conflict with final disposition notes or current schedules.
- Corroborating memos can classify counsel or explain an audit conflict, especially when raw labels are ambiguous.

## Disposition Rules

- Do not enter a disposed register item when the matter was continued, the plea/order was draft-only, or the final order was unsigned. Use the template's hold, pending, excluded, or no-closeout enum and set financials to zero unless the schema says otherwise.
- A no-contest plea plus a court finding is a guilty/violation disposition where the relevant enum distinguishes plea from finding.
- A bench-trial guilty finding generally has no plea; use the template's `not_applicable`, `none`, or equivalent enum instead of forcing a plea.
- Count dismissed or amended-away charges separately when the schema asks. Apply offense-specific assessments only to the convicted count, not to a charge amended away before conviction.
- Treat departure flags carefully. A draft/legacy departure label is not enough; use the judge's final statement, current charge record, and the enum closest to no departure, misdemeanor not evaluated, or pending not entered.

## Fee And Register Rules

- Select fee schedule rows current on the disposition/hearing date: `effective_date <= date` and `end_date` absent or after the date.
- Post court costs only for matters that should enter disposition/financials and only when the current schedule or final order supports them.
- Post fines from the final court sentence or current traffic fine tier, not from stale scratchpads or statutory maximum notes unless the template and policy require that exact source.
- Add offense-specific assessments only when the convicted offense triggers them under the current schedule.
- Add public-defender user fees only when the reconciled counsel type is public defender and current policy/schedule supports the fee. Appointed-private counsel, including county-paid private counsel or ambiguous APD labels clarified as private appointment, is not public defender fee eligible.
- Exclude account-management, collection, late, DMV, returned-check, traffic-school, restitution, attorney, reporter, copy, certification, and similar charges unless a current policy, schedule, final order, or triggering event directly supports them.
- Batch/register totals include posted matters only. Held or pending matters count only in the template's held/excluded counters and should contribute zero to money totals.

## Payment Plan Math

For installment schedules:

- Total due is the reconciled fines/costs balance plus restitution plus only policy-supported account fees.
- The approved installment is usually the requested or hearing-approved amount if it falls within the payment policy band and fits disposable income (`monthly_income - monthly_obligations`).
- Classify support from the policy band and budget using the template's exact enums.
- If restitution exists and policy gives it priority, use the corresponding application-order enum.
- First due date comes from the portal/payload when provided; otherwise derive it from policy days after disposition/petition date.
- Final due date for monthly plans is the first due date plus `total_installments - 1` calendar months.
- Return-to-court date comes from the payload when provided; otherwise derive it from the policy offset after the final due date when the schema asks for it.

Use `scripts/payment_schedule.py` for recurring monthly math when helpful:

```bash
python scripts/payment_schedule.py --total 0 --monthly 1 --first-due 2099-01-01
```

Replace the sample numbers with task values. Map the helper's generic keys to the schema names, such as `full_payment_count` or `full_installment_count`.

## Forms And Placeholders

- Use current portal form IDs and labels when the schema asks for form metadata.
- Preserve required form labels from local excerpts when the template expects label lists.
- Use the exact placeholder specified by the task materials, commonly `TBD from case file`, for missing identifiers, addresses, phone numbers, driver license numbers, probation officer names, probation office locations, and similar form-required details.
- Do not create placeholders for facts that are not required by the output schema.
- Sort placeholder records and missing-field lists exactly as instructed.
- If a probation referral was not ordered, do not prepare the referral and do not fill a report datetime from a portal field unless the template requires a separate audit note.

## Output Checklist

- Return one JSON object and no markdown.
- Include every required top-level key; omit extra keys unless the template allows them.
- Use exact enum spellings from the template.
- Use ISO dates and local datetimes as requested.
- Use numeric money values rounded to cents.
- Use `null` only where the template permits it; otherwise use the required placeholder or enum.
- Sort all arrays by the template's ordering rules.
- Recompute every subtotal and total from the selected posted items, not from stale source totals.
