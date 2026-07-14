# Clerk Operations Skill

## Overview

This skill prepares clerk-ready structured JSON responses for court clerk operations tasks. You work with a shared clerk operations REST API (live records, fee schedules, payment policies, financial ledgers, docket entries, stale exports) together with local task-specific payloads (bench minutes, attorney verifications, compliance packets, stale extracts, finance drafts).

## Environment

All API access is through `<TASK_ENV_BASE_URL>`, which points to the live clerk operations environment. The environment serves eight counties: Benton, Lane, Gloucester, Marion, Wasco, Columbia, Jefferson, Middlesex — each with its own fee schedule rows, payment policies, and case records.

Key endpoints:
- `GET /api/cases/<case_number>` — live case record (status, charges, attorneys, sentence)
- `GET /api/cases?county=<c>&matter_type=<t>&status=<s>` — filtered case listing
- `GET /api/citations/<citation_number>` — live citation (traffic matters)
- `GET /api/fees?county=<c>&matter_type=<t>&effective_on=<YYYY-MM-DD>` — fee schedule active on that date
- `GET /api/payment-policies?county=<c>` — installment plan constraints and unsupported charge codes
- `GET /api/financial-obligations?case_number=<cn>` — live ledger: principal, fee components, amount paid, balance due, payment plan details
- `GET /api/docket?case_number=<cn>` — docket entry history
- `GET /api/hearings?date=<d>&county=<c>` — calendar hearings
- `GET /api/attorneys` — attorney directory with defense types and active status
- `GET /api/stale-exports?county=<c>&name=<export_name>` — older queue extracts for conflict warnings
- `GET /api/search?q=<text>` — full-text search

## Source Precedence

Always resolve conflicts in this order:

1. **Live environment records** — the current source of truth for case status, charges, attorneys, financial ledger balances
2. **Local packet / bench notes** — override live records for hearing outcomes (plea, disposition, verdict, sentence) and attorney verifications when the packet post-dates the live snapshot
3. **Stale export / draft import** — use only for conflict detection and warning flags; never use their amounts, status values, or attorney assignments as final values

When the local packet says "warrant recalled in open court" but the live case still shows `status: "warrant"`, the packet controls the outcome. When a local attorney verification memo says "Laura Kim is the verified attorney, not Theresa Walsh," the verified attorney replaces the live record.

When a stale export or draft finance import carries fee amounts or status hints that contradict the live environment, the live environment wins. Flag the conflict but compute from live data.

## Fee Calculation

### Querying the schedule
```
GET /api/fees?county=<county>&matter_type=<type>&effective_on=<disposition_or_hearing_date>
```
Use the hearing date or disposition date as `effective_on` — not the current date. The API returns only rows where `effective_start <= effective_on AND (effective_end IS NULL OR effective_end >= effective_on)`.

### Applying fees
- **Mandatory fees** (`mandatory: true`): always include when the triggering condition is met (conviction entered, case filed, license suspension ordered, treatment ordered)
- **Non-mandatory fees** (`mandatory: false`): include only when the bench order explicitly triggers them (probation ordered → CR-PROB; restitution ordered → CR-REST-ADM; traffic school elected → TR-SCHOOL; speed violation → TR-SPEED)
- **Excluded fee codes**: check the county's payment policy `unsupported_charge_codes` list — never include fees with those codes regardless of schedule presence
- **Fee codes in import workpapers that are not in the active schedule**: exclude them and list in the output's excluded/not-entered list
- **Restitution**: use the bench card amount; add it to the principal total
- **No fee code appearing in a draft import or stale extract should be carried forward unless it matches an active, triggered schedule row**

### Fee schedule transitions
Fee schedules can change at year boundaries. If a disposition date is in 2024, query `effective_on=2024-MM-DD` and accept rows with `effective_start` before that date and `effective_end` after it (or null). Rows labeled "Obsolete" in their description are still valid if their effective range covers the transaction date.

## Payment Plan / Installment Calculation

Use the county payment policy:
- `min_monthly` / `max_monthly` — bounds for monthly payment amount
- `allows_final_smaller_payment` — if true, the last installment can be smaller than the regular monthly amount
- `first_due_days_after_order` — when no first due date is announced on the record, compute: `order_date + first_due_days_after_order`

### Computing the schedule
1. **Monthly amount**: use the amount from the live citation/case if the bench says "keep existing"; otherwise use the requested amount, clamped to `[min_monthly, max_monthly]`
2. **First due date**: use the existing live record date if the bench says to keep it; otherwise compute from order date + policy days
3. **full_payment_count** = `floor(principal / monthly_amount)`
4. **final_payment_amount** = `principal - full_payment_count * monthly_amount`
5. **total_payment_count** = `full_payment_count + (1 if final_payment_amount > 0 else 0)`
6. If `allows_final_smaller_payment` is false and there is a remainder, add one more full payment instead
7. **final_due_date** = `first_due_date + (total_payment_count - 1) months`

## Financial Reconciliation

- **new_principal_total** / **corrected_assessment_total**: sum of all applicable fee schedule amounts + restitution from bench card
- **amount_paid_credit**: from live financial obligation `amount_paid`
- **corrected_balance_due**: `new_principal_total - amount_paid_credit`
- **financial_delta**: `corrected_assessment_total - current_ledger_principal` (positive = additional assessment needed; negative = credit/refund)
- If the live environment has no financial obligation for a case, treat `current_ledger_principal` as `0.00`

## Discrepancy Detection

Compare the local packet against live records to identify these conflict types:
- **attorney_conflict**: local verified attorney differs from live case `defense_attorney`
- **status_conflict**: bench outcome status differs from live case `status`
- **financial_schedule_conflict**: draft import amounts don't match the fee schedule
- **attorney_and_status_conflict**: both of the above
- **status_and_financial_conflict**: status mismatch + financial discrepancy
- **identity_conflict**: defendant name/DOB mismatch suggesting wrong case
- **no_source_conflict**: packet and live records are consistent
- **live_ledger_vs_packet_receipt**: a receipt in the packet is not posted to the live ledger
- **petition_changes_payment_plan**: an ability-to-pay petition modifies the existing plan
- **packet_service_shortfall**: community service hours verified short of the ordered amount

## Output Conventions

- All dates in ISO `YYYY-MM-DD` format
- All currency values rounded to 2 decimal places
- All enum values must match the answer template exactly (case-sensitive)
- Lists ordered as specified by the template (usually by case_number, charge_id, or fee_code ascending)
- Boolean fields use JSON `true`/`false`
- `null` for optional fields that genuinely have no value, `"TBD from case file"` for identity fields explicitly marked as unknown-placeholder

## Workflow Rules

1. **Read the answer template first** — it defines the exact output shape, required keys, enum values, and ordering rules
2. **Identify all target cases/citations** from the local packet
3. **For each target, fetch live records in parallel**: case/citation, financial obligations, docket, fee schedule (matching county + matter_type + effective date), payment policy
4. **Fetch stale exports** only if referenced in the packet or task prompt; use them for conflict flagging, not for final values
5. **Reconcile**: apply source precedence to resolve each field
6. **Compute financials**: build fee component lists from the schedule, not from draft imports
7. **Compute installment plans**: apply payment policy constraints
8. **Compute aggregate totals**: sum across cases
9. **Validate**: every key in the template is present; all enum values match the template; ordering matches template requirements

## Pitfalls

- **Wrong effective date on fee query**: always use the disposition/hearing date, not today's date or the packet date
- **Copying draft import amounts**: draft finance CSVs often carry obsolete or wrong amounts; always recompute from the live fee schedule
- **Including unsupported fees**: CR-507, TR-231, DUI-104, CMP-072, CR-610 appear in some counties' unsupported lists — check the payment policy
- **Matter type on fee queries**: criminal cases use `matter_type=criminal`, DUI cases use `matter_type=dui`, traffic citations use `matter_type=traffic`, compliance uses `matter_type=compliance`
- **Citation vs case number**: for traffic matters, the citation number is the account reference unless the live citation record provides a separate case number
- **Non-mandatory fees triggered without order**: don't include CR-PROB unless probation was actually ordered; don't include CR-REST-ADM unless restitution was ordered
- **Stale export as truth**: stale export data is explicitly noted with conflict hints like "attorney may be prior assignment," "balance is from a prior ledger batch," "charge text may predate amendment" — never use these as final values
- **Not filtering to packet matters**: many tasks include informational or non-review items in the packet or stale export; include only cases where `review_needed: true` or where the bench/packet explicitly requests action
- **Ignoring the template**: each task has a specific answer_template.json with enum values, required keys, and ordering that may differ from other tasks
- **Fee schedule year boundary**: a 2024 disposition uses the 2024-active schedule; a 2025 disposition uses the 2025-active schedule; different amounts for the same fee code
