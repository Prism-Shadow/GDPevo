---
name: court-clerk-closeout
description: Reusable workflow for court clerk post-hearing closeout tasks: reconcile multiple evidence sources against the Court Operations Portal, resolve audit conflicts, compute fee reconciliation and payment plan arithmetic, produce structured JSON matching a provided answer template, and enforce placeholder and exclusion discipline.
---

# Court Clerk Closeout Skill

You are completing a court clerk post-hearing or post-sentencing closeout task. The task will supply local payloads (hearing notes, audit memos, finance extracts, worksheets, form excerpts, petition summaries, sentencing/probation notes), an `answer_template.json` that defines the required output shape, and the Court Operations Portal URL in `<TASK_ENV_BASE_URL>`.

## Workflow

1. Read every local payload in full.
2. Read the `answer_template.json` to learn the exact output schema, enums, ordering rules, and field constraints.
3. Query the Court Operations Portal for current records, fee schedules, payment policies, and form metadata. The available endpoints are listed in the prompt; always check `/health` first to confirm the portal is reachable.
4. Reconcile conflicts across sources using the rules below.
5. Build the answer JSON file strictly matching the template.

## Evidence Source Priority

When sources disagree, prefer:

1. Court Operations Portal (CMS of record) — for identity, fee schedule amounts, policy, and form metadata.
2. Hearing/courtroom notes — for plea, finding, sentence, departure statements, and whether a final order was signed.
3. Corroborating memos (clerk audit memos, supervisor notes) — for resolving ambiguous labels.
4. Finance queue extracts and worksheets — useful as starting data but must be corrected against higher sources.

## Audit and Conflict Resolution

Audit findings identify discrepancies between sources. Use exactly the `issue_type` values from the template's enum when present, otherwise these five categories cover the domain:

- **identity**: Wrong name spelling, wrong DOB. Resolution: use CMS (`use_cms`) when the portal record is definitive; use hearing notes (`use_hearing_notes`) when a correction was stated on the record. If DOB is absent even from the portal, use `verify_before_entry` and set DOB to `"TBD from case file"`.
- **counsel**: A label like "PD" or "APD" that could mean public defender or appointed private counsel. Resolution: hearing notes and corroborating memos control the final classification. If confirmed as appointed private counsel paid by the county, classify as `appointed_private` and do NOT treat the case as public-defender-fee eligible.
- **status**: A worksheet shows a case as "disposed" or "ready to post" but no final order was signed. Resolution: use `hold_unsigned_order` and do not post financials or enter a disposition.
- **fee_schedule**: A worksheet or legacy import carries a stale fee amount or omits a required assessment. Resolution: lookup the current fee schedule from the portal; use `use_fee_schedule`. Override the stale amount with the current schedule value.
- **departure**: A draft worksheet or legacy screen carries a departure label, but the judge did not state a departure on the record, or explicitly stated it is standard-range. Resolution: use hearing notes. Set departure to `no_departure` when the judge called it top-of-range or standard. Use `not_applicable` or `not_evaluated_misdemeanor` when departure is not a relevant concept for the offense class.

## Fee Rules

- Only post fees that are supported BOTH by the current portal fee schedule AND by the courtroom order.
- A public defender user fee applies only when counsel is confirmed as `public_defender`. Appointed private counsel is NOT PD-fee eligible.
- When a fee schedule has a current revision, never use an older/archived schedule amount.
- Do NOT add unsupported charges: account-management fees, collection fees, DMV/DMV-reinstatement fees, late-payment fees, returned-check fees, restitution (unless ordered), court-appointed-attorney fees, court-reporter fees, traffic-school fees, or any copy/certification fees — unless the portal record or current fee schedule directly supports them AND the judge ordered them.
- For cases held/pending/continued without a signed final order: set all fee amounts to zero, fee status to `hold` or `do_not_post_pending` or `exclude`, and do not include them in register totals.
- Account fees appearing in counter worksheets: check the current payment policy from the portal before carrying forward. If policy excludes them, zero them out and record `excluded_by_policy`.

## Fee Schedule Lookup

When the prompt gives you `<TASK_ENV_BASE_URL>`, query the portal for fee schedules. Match the schedule to the jurisdiction, offense tier, and revision year. Use the most current revision. The fee schedule yields the standard fine and any mandatory surcharges or assessments. The total amount due for a matter is the sum of all posted fee items.

### Common Fee Codes

These four appear across templates but adapt to whatever enum the template provides:

- `fine` — the base fine from the fee schedule or judge's order.
- `court_cost` — mandatory court costs.
- `drug_assessment` / `crime_lab_fee` — controlled-substance conviction assessments.
- `public_defender_user_fee` — PD user fee, only when PD-confirmed.

## Departure Handling

- If the judge explicitly stated a departure on the record, use the stated departure type (`durational_departure`, `dispositional_departure`).
- If the judge explicitly stated the sentence is standard, top-of-range, or not a departure, use `no_departure` (or `none`).
- For misdemeanors where departure is not typically evaluated, use `not_evaluated_misdemeanor`.
- For pending/continued cases, use `not_entered_pending` or `not_applicable`.
- Never carry forward a departure label from a draft worksheet that contradicts the hearing record.

## Payment Plan Math

When computing an installment schedule from an amount due and a monthly payment:

```
full_payment_count = floor(amount_due / monthly_payment)
final_payment_amount = amount_due - (full_payment_count * monthly_payment)
total_installments = full_payment_count + (final_payment_amount > 0 ? 1 : 0)
final_due_date = first_due_date + (total_installments - 1) months
```

If a candidate return-to-court date is provided in the petition or form, use it after verifying it is reasonable (typically 18-24 months after first due for nonpayment triggers). If absent, compute approximately 20 months after first due or use `null`.

- `down_payment` defaults to 0 unless a down payment was ordered.
- The interval is `monthly` unless the template or order specifies otherwise.
- If restitution is ordered and the template's `payment_application_order` enum allows, apply restitution-first when the petitioner requested it (`restitution_before_fines_costs`). Otherwise use `fines_costs_only`.

### Budget Review

When a petition includes income and obligations:

```
monthly_disposable = monthly_income - monthly_obligations
```

If the requested monthly payment is within a policy band (check the portal's payment-policy for actual bands; typical minimum is $50/month and maximum is $100/month for installment plans), classify as `supportable` or `supported_by_budget`. If below the policy minimum, classify as `below_policy_minimum`. If above the maximum, `above_policy_maximum`. If obligations exceed income, `unsupported_by_budget`.

## Placeholder Discipline

When a form field is required but the value is genuinely absent from all sources (local payloads and portal records), use the placeholder string `"TBD from case file"`. Never invent identifiers, addresses, phone numbers, license numbers, probation officer names, office locations, or contact details.

Fields that commonly need placeholders: `ssn`, `driver_license_number`, `residence_address`, `mailing_address`, `phone_number`, `probation_officer`, `probation_office_location`.

## Form References

When local payloads reference a form family (e.g., CC-1375, CC-1379), query the portal's `/api/forms` to get the current form metadata. Use the form ID and label from the portal if available; otherwise use the payload's description. The account reference for a traffic citation without a separate case number is the citation number itself.

## Template Adherence

The `answer_template.json` is authoritative for output structure. Follow it exactly:

- Use its enums; do not substitute prose for enum values.
- Use its required keys; do not omit any.
- Sort array elements by the field given in the template's ordering rules.
- Use two-decimal-dollar currency numbers and ISO YYYY-MM-DD dates.
- Match the top-level key names, nested key names, and field types from the template.
- When the template defines a `task_id`, include it in the output as specified.

## Docket and Register Entries

- Post a `sentencing_order` or `SENTENCING_ORDER_ENTERED` docket entry only when a signed final order exists (signed sentencing order handed to clerk).
- For cases without a signed final order (continued, deferred, or held), use `disposition_hold` or `CONTINUED_NO_DISPOSITION` and set the entry date to `null`. The `register_action` is `exclude_no_final_order`.
- Financial register totals sum only disposed/posted cases. Held/pending cases contribute zero to all totals.
- `summary_code` for the docket entry labels the nature of the conviction (e.g., `conviction_no_pd_fee` when PD fee was excluded, `conviction_drug_assessment` when a drug assessment applies, `hold_unsigned_order` for held cases).

## Excluded Charges

When the template includes an `excluded_charges` or `excluded_financial_items` section, enumerate every unsupported or stale charge, the matter(s) it applies to, and the reason. Common reason codes:

- `stale_schedule` — fee amount from an old/archived schedule version.
- `unsupported_post_disposition` — charge would substitute a different fee basis post-disposition without authority.
- `not_in_hearing_order` — not ordered by the judge.
- `not_current_policy` — current portal policy does not support this charge.
- `no_triggering_event` — the event that would trigger the fee (late payment, collections referral, returned check, etc.) has not occurred.
- `no_order_or_policy_support` — no order exists and policy does not authorize it.
- `not_part_of_balance` — the item is not part of the current balance (e.g., a post-judgment reinstatement fee).

## Multi-Matter Batches

When the task covers multiple cases or citations in one batch:

- Sort all case/citation-level arrays by case_number or citation_number ascending.
- Compute batch totals as the sum of posted (non-excluded) individual totals.
- Include a count of disposed versus held/pending matters.
- Excluded matters still appear in the output with their exclusion reason, next status date, and `financial_posting_allowed: false`.

## Query Strategy for the Portal

The portal's available endpoints are listed in the prompt. Prioritize these queries:

1. `/api/cases` or `/api/citations` to verify identity and status for the target matters.
2. `/api/fee-schedules` to get current fee amounts.
3. `/api/payment-policies` to check policy bands and account-fee treatment.
4. `/api/forms` for form metadata when template or payloads reference forms.
5. `/api/financial-petitions` to verify petition status when petitions are in the task.
6. `/api/charges` for charge details when needed for offense codes.
7. `/api/docket-entries` to verify prior docket state.
8. `/api/search` to find records when direct endpoints don't cover the needed data.
9. `/api/jurisdictions` when jurisdiction codes need confirmation.

## Final Output

Produce a single JSON file matching the template. The output goes to the path specified in the prompt, or as a final answer if no path is given. Do not include markdown wrappers around the JSON object unless the prompt explicitly asks for them.
