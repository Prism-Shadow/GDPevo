---
name: clerk-operations-reconciliation
description: Prepare clerk-ready JSON for court docket, citation, financial, probation, traffic, DUI, misdemeanor, and compliance reconciliation tasks using local packets plus the shared Clerk Operations API. Use when tasks require resolving live court records against stale exports, fee schedules, payment policies, ledgers, counsel/status conflicts, installment plans, and strict answer_template JSON schemas.
---

# Clerk Operations Reconciliation

## Workflow

1. Read the prompt, `answer_template.json`, and task-local packet files first. Treat the template as binding for top-level keys, enum values, nullability, ordering, date formats, and aggregate names.
2. Get the remote base URL from the prompt or `environment_access.md`. Use `/docs` once if endpoint names are unclear.
3. Identify the target matters from the packet, not from broad API searches. Exclude context-only, name-similarity, stale-export-only, and `review_needed: false` records unless the prompt explicitly includes them.
4. Query live records individually:
   - `/api/cases/<case_number>` or `/api/citations/<citation_number>`
   - `/api/financial-obligations?case_number=<id>`
   - `/api/fees?county=<county>&matter_type=<type>&effective_on=<YYYY-MM-DD>`
   - `/api/payment-policies?county=<county>`
   - `/api/docket?case_number=<case_number>` and `/api/stale-exports?...` when conflicts need resolution
5. Build the answer from a source-precedence pass, then a money/plan pass, then a final schema/order pass.

## Source Precedence

- Current bench, minute, review, counsel-confirmation, receipt, provider, restitution, and petition notes in the local packet override stale exports and older live fields for the action being prepared.
- Live case/citation records supply stable identity, existing status, existing charges, existing disposition dates, court names, and unchanged legal posture.
- Live financial obligations supply current ledger principal, amount paid, balance, existing monthly amount, and existing due dates.
- Fee schedules and payment policies control supported fee codes, active amounts, minimum plan amounts, default due dates, and unsupported charge codes.
- Stale exports are warning/context only. Use them to mark conflicts or avoid wrong nearby records; do not copy stale status, attorney, balance, license dates, or imported charges over newer packet/live records.

## Fees And Balances

- Use the fee schedule active on the disposition/order date for new or corrected assessments. For unchanged existing obligations, keep the live ledger principal and components unless the packet says to correct them.
- Enter only supported schedule fee codes whose `applies_when` condition is satisfied. Mandatory filing fees remain valid on open/no-disposition cases when a live filing obligation exists; do not zero them just because no plea was entered.
- Do not assess unsupported charge/statute codes as fees. Candidate/import codes that are unsupported or not supported by the order go in the template's excluded-code field when one exists.
- Add restitution as principal when ordered, and add a restitution administration fee only when the schedule supports it and restitution was actually ordered. Remove restitution/probation add-ons when the packet says none was pronounced.
- Compute `corrected_balance_due = corrected principal or live balance basis - credits/corrections`, rounded to two decimals. When a field says positive correction amounts reduce the balance, use a positive number for receipts/credits being posted.
- `financial_delta` means corrected assessment total minus current live ledger principal. Count financial adjustments from nonzero deltas when the template defines it that way.

## Payment Plans

- Use existing live plan amount and due date when the packet says to keep or extend an existing plan.
- For new/revised plans, use the judge-approved amount if present; if the order says "lowest allowed", use the county policy `min_monthly`. If no first date was announced, add policy `first_due_days_after_order` to the order/review date.
- Respect the template's plan basis. Some collateral packets calculate installments from `original_principal` while still reporting live amount paid and current balance; compliance replans usually calculate from corrected current balance.
- If final smaller payments are allowed, divide the plan basis by the monthly amount: full regular payments are `floor(total/monthly)`, final payment is the remainder, and total installments include the final smaller payment when the remainder is nonzero.
- Advance final due dates by calendar months from the first due date, not by repeated day-count offsets.
- When no plan applies, use `null` for amount/date fields and `0` for counts if the template allows that. For `keep_existing` or `send_return_to_court`, preserve existing plan fields if a live plan remains relevant.

## Output Conventions

- Return JSON only. Use numbers for money, rounded to two decimals, and ISO `YYYY-MM-DD` dates.
- Order rows exactly as requested, usually ascending by case/citation number. Sort fee-code and excluded-code arrays when the template says to.
- Use only allowed enum strings. Let action fields carry operational steps such as warrant recall, attorney update, return-to-court notice, post-credit close, or community-service follow-up; keep status fields as the resolved legal/financial posture.
- Use the policy `unknown_field_placeholder` such as `TBD from case file` only for genuinely unavailable required identity/form fields.
- Aggregate totals must be recomputed from the emitted rows after rounding decisions are final.

## Common Pitfalls

- Do not include stale-export neighbors, similar names, or packet rows marked informational/no review.
- Do not let stale exports override live ledgers, current packet notes, counsel confirmations, or provider/receipt notices.
- Do not treat every warrant recall as the final case status; often the resolved status is open or probation-active while the recall is a separate action flag.
- Do not add optional school, late, probation, public-defender, restitution-admin, or unsupported statute fees unless the order and active schedule both support them.
- Do not use current-balance installment math when the template asks for original-principal plan basis.
- Do not null out existing plan fields for return-to-court or keep-existing actions when the live plan is still the relevant plan context.
