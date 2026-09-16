---
name: court-closeout-reconciliation
description: Use this skill for clerk-ready court closeout, disposition register, traffic citation, sentencing packet, financial petition, probation referral, license suspension, payment-plan, fee reconciliation, or Court Operations Portal JSON tasks. Trigger whenever the user asks to reconcile local court payloads with portal records and return a structured JSON answer for criminal or traffic matters.
---

# Court Closeout Reconciliation

Use this skill to prepare structured court-operations JSON from local payloads plus the Court Operations Portal. The common failure mode is trusting one noisy source too much. Treat the task as reconciliation: identify the target matters, gather exact portal records, resolve conflicts by evidence strength, compute money and schedules, then validate against the provided template.

## Core Workflow

1. Read the user prompt, `answer_template.json`, and every local payload file before querying the portal.
2. Extract the target identifiers: case numbers, citation numbers, petition IDs, jurisdiction, hearing/disposition dates, and required output sections.
3. If the prompt uses `<TASK_ENV_BASE_URL>`, read `environment_access.md` in the workspace and use its `base_url`.
4. Query the portal only for target records and the relevant jurisdiction metadata:
   - Cases: `/api/cases?case_number=...`
   - Charges: `/api/charges?case_number=...`
   - Docket: `/api/docket-entries?case_number=...`
   - Citations: `/api/citations?citation_number=...`
   - Financial petitions: `/api/financial-petitions?petition_id=...`
   - Fee schedules, payment policies, and forms by jurisdiction code.
   - Use `/api/search?q=...` only as a fallback when the exact endpoint or identifier type is unclear.
5. Ignore unrelated portal records if a broad query returns them. Do not use non-target records as examples.
6. Build the answer in the exact template shape. Use the template's enum spellings, top-level keys, required nested keys, nullability, and ordering rules.

## Evidence Hierarchy

Use the sources for the jobs they are strongest at:

- The answer template controls output shape, enum values, sort order, date formats, and whether JSON values should be `null`, strings, numbers, booleans, objects, or arrays.
- Current case or citation records control identity, jurisdiction code, CMS status, counsel classification, DOB when present, citation speed/statute facts, and disposition dates unless a local final-order note clearly says no disposition should be entered.
- Hearing, sentencing, courtroom, and closeout notes control what actually happened in court: plea, finding, signed or unsigned order, continuation, amended charge, conviction count, sentence, probation order, license consequence, and judge-stated fee or departure corrections.
- Financial queues, scratchpads, legacy charge screens, worksheet rows, and draft disposition sheets are audit material. Use them to identify conflicts, not as final authority when a stronger source contradicts them.
- Current fee schedules control supported fee amounts, effective dates, mandatory assessments, surcharges, and public-defender/user-fee eligibility. Pick the schedule whose effective date range contains the disposition or hearing date.
- Current payment policies control installment bands, down-payment/account-fee treatment, first-due-date rules, return-to-court offsets, and restitution priority.
- Form metadata and local form excerpts control form IDs, labels, required visible labels, and placeholder instructions.

## Conflict Rules

Apply these rules consistently:

- Do not post financials for pending, continued, deferred, or unsigned-order matters unless the template expressly asks for a hold entry. Held/excluded matters usually get zero financial totals.
- For matters without a final disposition, follow the template's date convention: use `null` when it says no disposition date should be entered; use the hearing/hold date only when the schema models a dated hold entry.
- Do not create a conviction or disposition from a draft worksheet when notes or CMS status show no final order.
- If a DOB or identifier is missing from the available case file, use the exact placeholder specified by the materials; do not borrow from similar search results.
- Treat appointed private counsel as distinct from public defender. Add public-defender user fees only when the final counsel classification is public defender and the current schedule/policy supports the fee.
- Add drug, lab, or controlled-substance assessments only when the final conviction is on a qualifying controlled-substance count. If a controlled-substance charge was amended away or dismissed, exclude that assessment.
- A judge's statement that a sentence is top-of-range or not a departure overrides stale departure labels on charge screens or draft worksheets.
- For bench trials, use the template's non-plea enum when the output separates plea from finding.
- For probation referrals, prepare the referral only when the sentencing/probation materials show supervised probation or a signed referral order. A portal report date alone is not enough if local notes say no referral was ordered.
- For license suspension packets, use the start basis directed by the materials and template. When months are required, add calendar months to the start date for the suspension end date.
- Map plea strings to the template's enum style exactly, such as `no contest` versus `no_contest`.
- Exclude stale schedules, obsolete form-footers, statutory-maximum notes, account-management charges, collection fees, late fees, DMV fees, returned-check fees, traffic-school fees, restitution, attorney fees, and other add-ons unless a current policy, schedule, portal record, or hearing order directly supports them.

## Financial Math

Use numeric JSON values for currency and round to cents.

- Case total is the sum of supported posted fee items only.
- Batch totals count only posted/assessed matters. Held or excluded matters contribute to held/excluded counts and zero posted money.
- For traffic matters, compute `amount_due` from the current standard fine for the violation tier plus mandatory current surcharges. Do not substitute an old fine table or a statutory maximum for the current fine schedule.
- For criminal matters, combine the court-imposed fine, current court cost, mandatory qualifying assessments, and supported user fees. Waived fines stay zero.
- For petitions, total due is supported fines/costs plus restitution and supported fees after excluding policy-disallowed account fees.

## Payment Schedules

For installment plans, compute from the approved amount, down payment, first due date, and total due.

- Balance for installments is `total_due - down_payment`.
- If balance divides evenly by the regular installment, total installments equals the quotient and the final payment equals the regular installment.
- If there is a remainder, full installment count is `floor(balance / regular_installment)`, final payment is the remainder, and total installments is full count plus one.
- The final due date is the first due date plus `total_installments - 1` payment intervals.
- Return-to-court dates come from a local candidate date when it is clearly approved, otherwise from the payment policy offset applied to the final due date.
- Classify support by comparing the approved/requested payment to disposable income and the policy minimum/maximum band. Within band and affordable is supportable/supported; below band, above band, or greater than disposable income should use the template's corresponding enum.
- Apply restitution priority exactly as the current policy says when both restitution and fines/costs are present.

## Forms And Placeholders

- Use portal form IDs and labels when available; reconcile them with local form excerpts.
- For traffic payment plans with no separate case or account number, use the citation number as the account reference when the form materials say to do so.
- Use the exact placeholder text from the payload or form metadata for missing driver license numbers, SSNs, addresses, phone numbers, probation officer names, probation office locations, or similar missing form details.
- Include placeholder listings only for fields the output schema asks you to list. Sort placeholder fields as directed by the template.

## Final Validation

Before answering:

- Return JSON only, with no markdown wrapper or explanatory prose.
- Check that every required key from the template is present and no enum value has been paraphrased.
- Apply all sort rules in the template.
- Verify dates are ISO formatted and date-times use the requested local datetime format.
- Recalculate every case total, installment total, final payment, final due date, and batch total.
- Confirm excluded or unsupported charges have the template's required reason codes.
- Confirm no target matter is missing and no non-target matter is included.
