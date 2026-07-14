---
name: clerk-operations-json
description: Prepare clerk-ready JSON answers for court operations tasks using local packets plus the shared clerk operations API, including docket outcomes, counsel/status reconciliation, fee schedules, ledger credits, and payment-plan calculations.
---

# Clerk Operations JSON

Use this skill when a task asks for a clerk-ready JSON object based on local court packets and a shared clerk operations environment.

## Workflow

1. Read the answer template first. Treat it as the schema: required keys, enum spellings, ordering, null handling, and numeric precision all come from the template.
2. Read the local packet(s) and identify the target matters. Include only requested matters; exclude context-only, informational, `review_needed: false`, similar-name, or stale-export carryover rows.
3. Query the API at the base URL given in the prompt. Start with `GET /docs` if the surface is unfamiliar.
4. For each case/citation, pull the live record, docket, financial obligation, fee schedule for the relevant date, and county payment policy.
5. Resolve conflicts by source precedence, compute the final fields, then validate totals against the per-row values before returning JSON only.

Useful endpoints:

- `GET /api/cases/<case_number>`
- `GET /api/citations/<citation_number>`
- `GET /api/financial-obligations?case_number=<case_number>`
- `GET /api/fees?county=<county>&matter_type=<type>&effective_on=<YYYY-MM-DD>`
- `GET /api/payment-policies?county=<county>`
- `GET /api/docket?case_number=<case_number>`
- `GET /api/stale-exports?county=<county>&name=<export_name>`
- `GET /api/hearings?date=<YYYY-MM-DD>&county=<county>`
- `GET /api/search?q=<text>`

## Source Precedence

- Local current bench/hearing/review packets control the target list, current plea/disposition/sentence orders, review flags, packet receipts, approved petitions, and counsel confirmations.
- Live API records control identity, live status before the new entry, docket history, ledger principal, paid credits, balances, active plan dates/amounts, fee schedules, and payment policy.
- Stale exports are warnings only. Use them to spot conflicts, not to override a current packet or live record.
- Counsel confirmations in the packet override stale/live representation when the packet says the confirmation is current. A mismatch can be only attorney type, even when the attorney name matches.
- Current hearing notes override live case charge/status fields when the live case has not yet been updated after the hearing.
- Preserve an existing underlying disposition class for review-only rows when a real conviction/deferred/dismissal posture already exists; do not label it as ledger-review-only just because no new disposition was entered.

## Output Conventions

- Return exactly one JSON object, with no prose.
- Use template enum values verbatim.
- Sort arrays exactly as requested, usually by case number/citation number and fee/charge code.
- Currency fields are JSON numbers rounded to two decimals; dates are ISO `YYYY-MM-DD`.
- Use `null` for non-applicable plan amounts/dates when the template allows it. Use the county policy placeholder only for unknown required text fields.
- For citations with no separate case/account number, use the citation number as the account reference.
- `financial_delta` means `corrected_assessment_total - current_live_ledger_principal`; negative values are valid.
- For balance adjustments, `correction_amount` is positive when it reduces the live balance.
- Count placeholders only for fields actually populated with the placeholder string.

## Fee Rules

- Query the fee schedule with the county, matter type, and effective date of the relevant order/disposition/review.
- Apply mandatory fees only when their `applies_when` condition is supported by the order. Apply optional fees only when the hearing/review note supports them.
- Exclude candidate/import fee codes that are unsupported, obsolete for the order date, not ordered, or tied to dismissed/no-separate-fee charges.
- Filing fees can remain for filed matters even when no new disposition was entered, if supported by the live obligation and schedule.
- Do not add conviction fees for deferred, dismissed, pending, or no-disposition matters.
- Do not add probation, traffic-school, late, public-defender, restitution-admin, or return-to-court fees unless the order/policy support that specific component.
- Restitution increases principal and balance when ordered, but keep it separate from scheduled fee-code lists unless the template explicitly asks for restitution as a component.
- Use live ledger paid credits when computing corrected balance: `corrected_balance_due = corrected_principal - amount_paid_credit`, adjusted by packet credits when applicable.

## Payment Plans

- Always pull the county payment policy. It supplies minimum monthly amount, first-due offset, final-payment behavior, and placeholders.
- If the packet says an extended/existing plan was approved at live values, use the live monthly amount and first/next due date.
- If no first due date was announced, use `order_or_review_date + first_due_days_after_order`.
- If the court approved the lowest allowed amount, use the policy minimum. If a specific approved amount is within policy, use it.
- When the template has `full_payment_count` and `total_payment_count`, `full_payment_count = floor(balance_or_principal / monthly)` and `total_payment_count` includes the final smaller payment.
- When the template has only `installment_count` plus `final_payment_amount`, use total installments as `installment_count`.
- Final due date is the first due date plus `total_installments - 1` monthly intervals.
- For original sentencing/installment orders, calculate the schedule from original principal when `plan_basis` is `original_principal`, while still reporting live paid credits and current balance. For compliance replans, calculate from corrected balance.
- No plan means plan amount/date fields are `null` and counts are `0`.
- Packet receipts not posted to the live ledger should be posted as credits and can close the balance. Approved ability-to-pay petitions create revised plans; withdrawn petitions do not.

## Common Pitfalls

- Do not merge nearby similar case/citation numbers or similar defendant names from stale exports.
- Do not let a warrant recall replace the final posture; resolve the final status from the hearing result, sentence, and remaining open settings.
- Do not include context rows from stale queues just because they appear in a local packet.
- Do not trust live charge outcomes when the current bench packet says the clerk still needs to enter the plea/disposition.
- Do not list restitution inside scheduled fee-code arrays unless the template expressly wants it there.
- Do not count only full payments when the template's single count field represents total installments.
- Do not mark an existing plan as revised unless a current approved petition or order changed it.
