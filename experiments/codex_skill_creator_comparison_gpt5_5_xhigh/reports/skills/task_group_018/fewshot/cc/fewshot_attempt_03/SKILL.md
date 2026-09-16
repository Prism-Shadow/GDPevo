---
name: court-closeout-json
description: Prepare structured court clerk closeout JSON from local payloads and a Court Operations Portal. Use for criminal disposition registers, traffic violation payment plans, sentencing closeout packets, probation or license-suspension forms, financial petitions, fee-schedule reconciliation, unsupported-fee exclusions, placeholder handling, and exact answer_template-driven JSON outputs.
---

# Court Closeout JSON

## Operating Rule

Use this skill when a task asks for a clerk-ready JSON closeout or packet using local payloads plus a Court Operations Portal. Treat the prompt, local payloads, portal records, and `answer_template.json` as the complete source of truth. Return JSON only when the task asks for JSON; do not add markdown or explanatory prose.

## First Pass

1. Read the prompt and identify every target case number, citation number, petition ID, jurisdiction, hearing/disposition date, and requested output file/template.
2. Read `input/payloads/answer_template.json` before deriving values. Copy its required top-level structure, exact key names, enums, sort rules, date rules, numeric precision, and null/placeholder rules.
3. Read all other local payloads. Build a matter-by-matter evidence ledger with local hearing facts, queue or worksheet facts, petition facts, form excerpts, and conflict notes.
4. Query the portal for each target identifier and jurisdiction. Use direct filters first:
   - `/api/cases?case_number=...`
   - `/api/charges?case_number=...`
   - `/api/docket-entries?case_number=...`
   - `/api/citations?citation_number=...`
   - `/api/financial-petitions?petition_id=...`
   - `/api/fee-schedules?jurisdiction_code=...`
   - `/api/payment-policies?jurisdiction_code=...`
   - `/api/forms?jurisdiction_code=...`
   - `/api/search?q=...` for cross-resource checks
5. If several endpoint calls are needed, you may use `scripts/collect_portal_evidence.py`:

```bash
python /path/to/skill/scripts/collect_portal_evidence.py \
  --base-url "$TASK_ENV_BASE_URL" \
  --case CASE_NUMBER \
  --citation CITATION_NUMBER \
  --petition PETITION_ID \
  --jurisdiction JURISDICTION_CODE
```

## Reconciliation Priority

Use the source that is most authoritative for the field, not the source that appears first.

- Identity: use the portal case or citation record for verified name, DOB, jurisdiction, and status when it is specific to the target matter. If a DOB or required identifier is genuinely absent, use the template's placeholder rule rather than borrowing from search-neighbor records.
- Counsel: use explicit `counsel_type` or corroborating local notes over raw labels. Do not treat `APD`, `appointed private`, or county-paid appointed counsel as public defender unless the record says public defender.
- Disposition/status: signed final orders, courtroom disposition notes, and portal status control whether a matter is disposed. If the order is unsigned, continued, deferred, or pending, hold or exclude it and do not post financials unless the template explicitly asks for a pending entry.
- Charges and sentences: include only convicted or adjudicated counts. Exclude dismissed counts and counts amended away before conviction. Use portal charge details for offense codes, sentence numbers, probation, license months, and dispositions only when consistent with the final local disposition materials.
- Departures: do not preserve a legacy or worksheet departure label when the hearing record says the sentence was not a departure. If the template has a misdemeanor or not-applicable departure enum, use that rather than inventing felony-style analysis.

## Fees And Exclusions

Filter fee schedules by jurisdiction and effective date. A current row has `effective_date` on or before the disposition/hearing date and no `end_date` before that date. Ignore archived, stale, noise, copy, certification, collection, account-management, DMV, late, traffic-school, and returned-payment items unless a current policy or court order directly supports them.

- Criminal court costs: post the current mandatory court cost for disposed criminal matters when the template and schedule support it.
- Drug or crime-lab assessments: post only when the convicted count is a controlled-substance or lab-assessment-triggering conviction. Do not post after the charge is amended away or dismissed.
- Public-defender user fees: post only for actual public defender representation and only when not waived or excluded. Do not post for retained or appointed-private counsel.
- Fines: use the fine pronounced or shown for the convicted count; use zero when waived or no fine is announced.
- Traffic violations: choose the current standard fine by `violation_code` and jurisdiction, then add any mandatory county surcharge once per citation. Do not substitute a statutory maximum or stale standard fine for the active schedule amount.
- Virginia financial petitions: total due is fines/costs plus restitution plus any account fee that the current policy actually includes. If the local counter note mentions an old fee but policy amount is zero or unsupported, set the fee to zero and classify it as excluded if the template asks.

When the template asks for unsupported charges or excluded financial items, list every stale or unsupported item that the local materials flagged and map it to the closest allowed reason enum. Keep included unsupported totals at zero unless the output schema explicitly asks to report a mistakenly included amount.

## Payment Plans

Use court-approved or petition-requested amounts only after comparing them with the active payment policy and budget facts.

- Disposable income is monthly income minus monthly obligations.
- A requested installment is supported when it is within the policy min/max band and does not exceed disposable income. Use the template's exact support enum, such as `supportable`, `supported_by_budget`, `below_policy_minimum`, `above_policy_maximum`, `unsupported_by_budget`, or `needs_judge_review`.
- Use explicit local or portal first-due dates when present. Otherwise compute from the policy's `first_due_days` after the petition, disposition, or agreement date described by the task.
- For monthly plans, subtract any down payment from total due, then compute:
  - `full_installment_count = floor(remaining_balance / regular_installment_amount)`
  - `final_payment_amount = remaining_balance - full_installment_count * regular_installment_amount`
  - if the final amount is zero, total installments equals full installments and the final payment amount is the regular installment amount; otherwise total installments is full installments plus one.
  - final due date is the first due date plus `total_installments - 1` calendar months.
- Use an explicit return-to-court date when supplied. Otherwise add the policy's `return_to_court_offset_days` to the final due date if the template requires a return setting.
- Payment application follows the policy: restitution before fines/costs when restitution exists and the policy says so; otherwise fines/costs only or the template's closest enum.

## Forms, License Orders, And Placeholders

Use `/api/forms` and local form excerpts for form IDs, labels, required fields, visible labels, and account-reference instructions.

- Traffic payment plans usually use the citation number as account reference when no separate case or account number exists.
- Probation referral forms are prepared only when supervised probation or a referral order is actually present. If no referral order was signed, use the template's not-ordered enum and do not invent a report date.
- License suspension orders use the basis stated by the court record or form/policy. For DUI-style conviction consequences, the suspension normally starts on the conviction date unless the materials say otherwise. Suspension end date is the start date plus the stated number of calendar months.
- Use the exact placeholder text from the materials, commonly `TBD from case file`, for missing identifiers, addresses, phone numbers, driver-license numbers, probation officer names, and probation office locations. Do not invent contact details. Add placeholder summary entries only for fields the template asks you to report.

## Final JSON Check

Before answering:

1. Ensure the result parses as a single JSON object and matches the template's required keys.
2. Use exact enum tokens from the template; do not replace them with prose.
3. Sort every list according to the template. If no rule is given, sort by the matter identifier that names the item.
4. Recompute all totals from the included entries and verify held/excluded matters contribute zero unless the schema says otherwise.
5. Use ISO dates and local datetimes. Use JSON `null` only where the template permits it.
6. Keep money as JSON numbers rounded to cents, not strings.
7. Check that pending, unsigned, stale, unsupported, and placeholder facts are explicitly reflected when the template has fields for them.
