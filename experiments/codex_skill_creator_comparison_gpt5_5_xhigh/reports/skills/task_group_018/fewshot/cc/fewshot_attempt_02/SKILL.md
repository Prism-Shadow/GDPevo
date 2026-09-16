---
name: court-operations-closeout
description: Reconcile court closeout, disposition register, traffic citation, payment-plan, probation referral, and license/order packets from local case materials plus a Court Operations Portal API. Use for strict JSON clerk workflows involving sentencing closeouts, criminal financial registers, traffic violation payments, fee schedules, payment policies, forms, financial petitions, unsupported-fee exclusions, and missing-field placeholders.
---

# Court Operations Closeout

Use this skill when a task asks for a clerk-ready JSON package from local court materials and a Court Operations Portal. The recurring work is not legal research; it is evidence reconciliation, active-policy lookup, arithmetic, and strict schema production.

## Core Workflow

1. Read the user prompt, `input/payloads/answer_template.json`, and every local payload file before drafting output.
2. Treat the answer template as the output contract. Preserve required top-level keys, nested shapes, enum spellings, date/currency rules, null rules, and sorting rules exactly.
3. Identify every target case number, citation number, petition id, jurisdiction, hearing/disposition date, and named local source.
4. Query the Court Operations Portal for the relevant identifiers and jurisdiction records. Prefer targeted lookups over dumping whole collections.
5. Reconcile conflicts using the source hierarchy below.
6. Compute financial totals, payment schedules, placeholder lists, audit rows, exclusions, and register totals.
7. Validate that the final response is parseable JSON and contains no markdown or commentary.

## Portal Use

Use the base URL supplied by the task prompt. If the prompt uses a placeholder and an `environment_access.md` file is present in the task workspace, read it only to obtain the base URL and allowed endpoints.

Common endpoint patterns:

- `/api/search?q=IDENTIFIER` to discover all records for a case, citation, petition, or party identifier.
- `/api/cases?case_number=CASE`
- `/api/charges?case_number=CASE`
- `/api/docket-entries?case_number=CASE`
- `/api/citations?citation_number=CITATION`
- `/api/financial-petitions?petition_id=PETITION`
- `/api/financial-petitions?case_number=CASE`
- `/api/jurisdictions?jurisdiction_code=JURISDICTION`
- `/api/fee-schedules?jurisdiction_code=JURISDICTION`
- `/api/payment-policies?jurisdiction_code=JURISDICTION`
- `/api/forms?jurisdiction_code=JURISDICTION`

If an endpoint ignores a filter, use `/api/search` for each identifier and filter the returned `results` locally by `result_type`, `case_number`, `citation_number`, `petition_id`, or `jurisdiction_code`.

## Source Hierarchy

Use all sources together. The best answer usually comes from recognizing which field each source is authoritative for.

- Use current portal case/citation/petition records for normalized identifiers, DOBs, jurisdiction codes, counsel classifications, statuses, disposition dates, form metadata, active fee schedules, payment policies, and financial petition balances.
- Use hearing notes, signed-order notes, sentencing intake sheets, and explicit local court memos for the actual courtroom outcome when they contradict stale worksheets, finance queues, old charge screens, or carry-forward portal charge fields.
- Use current portal fee schedules, payment policies, and form metadata over scratchpads, archived schedules, obsolete form footers, statutory-maximum notes, or intake guesses.
- Treat finance queues and worksheets as audit inputs, not final truth. They often contain stale fees, draft dispositions, copied counsel labels, missing DOBs, or charges that were amended away.
- Do not invent missing identifiers, addresses, phone numbers, driver license numbers, probation officer names, office locations, or similar form fields. Use the exact placeholder required by the template or local form materials.

When the schema asks for audit findings, record the conflict and the corrected value. When it does not, apply the corrected value silently.

## Disposition Rules

For criminal closeouts and disposition registers:

- Enter a disposed case only when a plea, finding, sentence, or signed final order is supported by the local notes and portal status/docket records.
- Hold or exclude matters that are pending, continued, deferred for status, missing a final order, or explicitly marked draft-only. Do not post financial obligations for those matters unless the template has a separate hold row.
- Follow the template's date rule for pending matters. Some schemas want the hearing date with a hold action; others require `null` where no disposition date should be entered.
- Normalize pleas and outcomes to the template enums: no-contest plus guilty finding is a guilty/violation-found disposition, bench-trial findings may have no plea, and no accepted plea/finding remains pending.
- Use amended convictions as the conviction count. If a controlled-substance count was amended away or dismissed, do not apply drug or lab assessments for that count.
- Count dismissed, nolle-prosequi, amended-away, or pending counts only where the schema asks for them.
- For departure fields, use an explicit judge or hearing note that says top-of-range/no-departure over a stale departure label. For misdemeanors or pending matters, choose the template enum that means not applicable, not evaluated, or not entered.

## Counsel And Identity

- Prefer normalized `counsel_type` from the portal or an explicit court/defense memo over raw labels.
- Do not treat appointed-private counsel, county-pay appointed counsel, or an "APD" label clarified as appointed private as public defender representation.
- Apply public-defender user fees only when current policy/schedule supports the fee and the reconciled counsel classification is public defender.
- Prefer verified CMS/portal DOB and spelling when a queue or bench shorthand conflicts, unless a local case-file correction is more specific and corroborated.
- If identity data is genuinely missing and the template allows a placeholder, use the exact placeholder string and add the corresponding audit/placeholder entry when requested.

## Fees And Exclusions

Select fees by jurisdiction, effective date, end date, fee type, violation code/statute, and any notes that limit when the fee applies.

- Active fee: `effective_date` is on or before the relevant disposition/hearing/event date, and `end_date` is absent or after that date.
- Court costs usually apply to disposed convictions when the active schedule marks them mandatory.
- Fines come from the pronounced sentence, citation record, or reliable current charge/financial record. Do not use draft fines after a case is held or continued.
- Drug, controlled-substance, or crime-lab assessments apply only to convicted counts that still support the assessment under the active schedule.
- County traffic surcharges apply once per citation only when the active schedule says they are mandatory.
- Account-management, collection, late-payment, DMV, traffic-school, restitution, attorney, reporter, copy, certification, and similar fees require current policy or an actual triggering order/event. Otherwise list them as excluded if the schema provides an exclusion section.
- Stale schedules, archived amounts, obsolete form footers, and statutory maximum notes are not starting balances unless the current schedule or order explicitly selects them.

Totals should include only posted or approved obligations. Held, pending, excluded, unsupported, and stale items contribute zero unless the template has a separate unsupported-total field.

## Traffic Citation Closeout

For traffic matters:

- Use the portal citation record for `violation_code`, speed, zone, plea, disposition, plan approval, first due date, monthly payment, jurisdiction, and defendant details.
- Use the violation code when present. If missing, classify speed tiers from the actual speed and speed over limit according to the local schedule.
- Combine the current standard fine with any current mandatory per-citation surcharge to get the amount due.
- Treat payment-plan agreements approved after a finding as post-disposition agreements when local notes say the agreement followed disposition.
- Use form metadata and local form excerpts for form id, visible label, required labels, and account-reference handling. If no separate court account exists, use the citation number when the local form or policy instructs that.
- Exclude old standard fines, statutory maximum substitutions, and optional post-disposition charges unless current policy and a triggering event support them.

## Virginia Financial And Supervision Packets

For post-sentencing payment, probation, and license packets:

- Use sentencing intake or courtroom disposition notes for conviction date, offense, sentence, probation order, license suspension basis, and whether a referral form is required.
- Use financial petition records for petition sequence, balances, income, obligations, requested monthly amount, restitution balance, default status, petition date, and jurisdiction.
- Classify first petitions as initial installment requests unless local materials identify a deferred payment, subsequent review, or no-payment exemption. Treat second/default-review petitions according to the template enums and local policy.
- Compute disposable income as monthly income minus monthly obligations.
- Compare the requested or approved monthly payment to the policy minimum, policy maximum, and disposable income. Map the result to the schema's support enum, using the closest available wording.
- Include account fees only when the active jurisdiction policy supports them for the matter. If a counter worksheet carries an unsupported account-fee row, set the fee amount to zero and record exclusion or excluded treatment if requested.
- Apply restitution first when there is a restitution balance and the active policy states that priority. Otherwise use fines/costs-only or the closest template enum.
- License suspensions for DUI-style convictions usually start on the conviction date unless the local materials specify release date or petition date as the basis. Compute the end date by adding the ordered months.
- Prepare probation referral fields only when supervised probation or a referral order is present. Otherwise use the template's not-ordered status, zero months, and `null` report datetime if those fields are required.

## Payment Schedule Math

Use `scripts/payment_schedule.py` for installment arithmetic when available. Run it from the package root, or substitute the path to this skill directory:

```bash
python scripts/payment_schedule.py --total TOTAL --monthly MONTHLY --first-due YYYY-MM-DD --down DOWN --return-offset-days DAYS
```

Rules to apply whether calculating manually or with the script:

- Remaining balance is total due minus down payment.
- Full installment count is the floor of remaining balance divided by monthly payment.
- If there is a nonzero remainder, add one final installment for the remainder.
- If there is no remainder and the balance is positive, the final payment amount is the regular monthly amount and total installments equal the full installment count.
- Final due date is the first due date plus `total_installments - 1` calendar months.
- Return-to-court date comes from the petition/local candidate date when supplied; otherwise add the policy offset days to the final due date.
- Round money to cents after each final calculation, and emit JSON numbers rather than strings.

## Placeholder Lists

Use placeholders only for fields that are required but genuinely absent from the provided case file, portal response, policy, or form metadata.

- Use the exact placeholder value from the materials.
- Include driver license, SSN, addresses, phone numbers, probation officer, office location, and similar missing required details when the schema asks for placeholder tracking.
- Do not add placeholders for fields that are optional, not requested by the template, or derivable from reliable records.
- Sort placeholder arrays and missing-field arrays exactly as the template instructs.

## Output Discipline

- Return one JSON object only.
- Use enum values exactly as written in `answer_template.json`.
- Use ISO dates and local ISO datetimes as required by the template.
- Use `null` only when the template allows or requires it.
- Sort every list according to the template. If no explicit rule exists, sort by the natural identifier used by that list.
- Recalculate subtotals and grand totals from the rows you are emitting.
- Before final response, parse the JSON with a local JSON parser and check that all referenced IDs, totals, statuses, and exclusions are internally consistent.
