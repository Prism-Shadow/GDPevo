---
name: court-clerk
description: Court clerk closeout, sentencing, and disposition packet preparation. Use when the task involves reconciling case records through a Court Operations Portal API to produce audit findings, case dispositions, fee reconciliation, docket entries, register totals, payment plans, probation referrals, license orders, or financial-field packets from local hearing notes, audit memos, finance extracts, petition summaries, or sentencing intake facts. Covers criminal sentencing closeouts, traffic violation payment plans, post-sentencing field packets (CC-1375/CC-1379), and criminal disposition batch registers.
---

# Court Clerk Operations

Prepare court clerk closeout, sentencing, and disposition packets by cross-referencing local hearing documents with the Court Operations Portal REST API. This skill covers the common reconciliation, financial, and form-entry patterns used by deputy clerks across criminal, traffic, and post-sentencing workflows.

## Workflow

Every task follows the same sequence:

1. Read every local payload file in the task's payloads directory, plus the answer template when one is provided.
2. Call the portal to retrieve authoritative records for each target case, citation, or petition.
3. Cross-reference local documents against portal records. Resolve every conflict using the reconciliation rules below.
4. Compute financial amounts from portal fee schedules and payment policies, never from stale local worksheets.
5. Build the output JSON conforming to the answer template, using the ordering, enum, date, and currency precision rules it specifies.

## Portal API

All endpoints are GET requests to `TASK_ENV_BASE_URL`. No authentication.

| Endpoint | Returns |
|---|---|
| `/api/jurisdictions` | Court metadata, jurisdiction codes, policy references |
| `/api/cases` | Case records: defendant, DOB, counsel type, status, disposition date |
| `/api/charges` | Charge records: offense, plea, disposition, fines, jail, probation, departure |
| `/api/docket-entries` | Docket history: filing, hearing, disposition, financial, and clerk-note entries |
| `/api/citations` | Traffic citation records: violation code, speed, disposition, payment plan status |
| `/api/fee-schedules` | Fee amounts by jurisdiction, effective date, and fee type (court_cost, assessment, user_fee) |
| `/api/payment-policies` | Installment plan rules: monthly band, first-due offset, account fee, restitution priority |
| `/api/forms` | Form metadata: required fields, placeholder instructions, revision dates |
| `/api/financial-petitions` | Payment petition records: balances, income, obligations, requested amounts |
| `/api/search` | Multi-entity search by case number, citation number, or name |

**Query pattern:** Use `/api/search?q=<case_number>` first to get a result set spanning cases, docket entries, charges, and citations in one call. Then call individual endpoints for fee schedules (`/api/fee-schedules`), payment policies (`/api/payment-policies`), and forms (`/api/forms`) which are not searchable by case number. For fee schedules, filter client-side by `jurisdiction_code` and `effective_date` -- use the schedule with the latest `effective_date` that is not past its `end_date` and is on or before the disposition date.

Full endpoint field descriptions are in [references/portal_endpoints.md](references/portal_endpoints.md). Load it when a field's meaning is unclear.

Detailed reconciliation decision trees and fee applicability tables are in [references/reconciliation_rules.md](references/reconciliation_rules.md). Load it for complex conflicts that go beyond the summaries below.

## Reconciliation Rules

### Identity conflicts

When defendant name or DOB differs between local worksheets and portal records:
- **Prefer the portal CMS record** (`source_system` = `AOC-CMS` or `VACMS`) over the finance queue or worksheet.
- If a hearing note or corroborating memo explicitly corrects the portal record, use that correction and cite the source as the resolution.
- When DOB is genuinely missing from all sources, use "TBD from case file" and flag the identity action as `use_placeholder_verify`.

### Counsel classification

- `counsel_type` in `/api/cases` is the authoritative record. But the `attorney_label_raw` field can be misleading: "APD" may mean appointed private counsel, not public defender.
- When a hearing note or corroborating memo says defense counsel is appointed private (county-paid, not the PD office), classify as `appointed_private` regardless of the raw label.
- Public Defender User Fee applies **only** when counsel is classified as `public_defender`. Never apply it to `appointed_private`, `retained`, or `unknown`.

### Case status and disposition

- Before posting any financial entry, confirm the case has a signed final order. Cases that are `deferred`, `continued`, or `pending` must not receive sentencing financial entries.
- A draft worksheet showing "disposed" does not override a docket note that says the final order was not signed. If the status is genuinely pending, the closeout action is `hold_unsigned_order` or `exclude_pending`.
- Use the disposition date from portal `/api/cases` or the hearing notes, not the audit memo date.

### Departure status

- Determine departure from the judge's actual pronouncement in the hearing notes, not from legacy worksheet labels.
- If the judge said "top of the range" or "no departure," the departure status is `no_departure` or `none`.
- For misdemeanors where departure isn't evaluated, use `not_evaluated_misdemeanor`.
- For pending cases with no final order, use `not_entered_pending`.

### Fee schedule conflicts

- A fee schedule is current when its `effective_date` is on or before the disposition date and its `end_date` is null or after the disposition date.
- A fee schedule is stale when its `end_date` predates the disposition date.
- Always use the current schedule amount. Flag stale amounts found in local worksheets as audit issues.
- Check `mandatory`: if true, the fee applies regardless of what the worksheet says. If false, check the notes field for applicability conditions (e.g., PD user fee only for public defender cases).

## Financial Computation

### Fee calculation

1. Start from `/api/fee-schedules` filtered to the case's jurisdiction.
2. For each fee with `effective_date` <= disposition date and (`end_date` is null or `end_date` >= disposition date):
   - Include if `mandatory` is true, or if the fee's `notes` and `statute` support it for this case.
   - Use the portal amount, not any local worksheet amount.
3. Court cost is always mandatory for disposed criminal cases. Its amount varies by jurisdiction.
4. Assessment fees (drug, crime lab) apply only when the conviction charge triggers them (controlled substance -> drug assessment and/or crime lab fee).
5. PD user fee applies only when `counsel_type` is `public_defender` and the case is disposed.
6. Fines come from the charge record (`/api/charges`) or hearing notes, not from fee schedules.

### Payment plan math

When building an installment schedule from a total balance and monthly payment:

```
full_payment_count = floor(total_due / monthly_payment)
final_payment_amount = total_due - (full_payment_count * monthly_payment)
total_installments = full_payment_count + (1 if final_payment_amount > 0 else 0)
```

- If `final_payment_amount` is 0, the schedule has `full_payment_count` equal installments.
- If `final_payment_amount` > 0, the last installment is the reduced amount.
- First due date: add `first_due_days` from the payment policy to the disposition date. If the policy notes specify a calendar convention (e.g., "15th of next month"), use that.
- Return-to-court date: add `return_to_court_offset_days` from the policy to the final due date.
- Down payment: use `down_payment_required` from the policy. Subtract from total before computing installments when nonzero.
- Monthly payment must fall within `[min_monthly, max_monthly]` from the policy. When the requested amount from a petition falls within this band and is supported by the budget, approve it.

### Payment application order

Follow the payment policy's `restitution_priority`:
- "Restitution before fines and costs" -> apply payments to restitution balance first, then fines/costs.
- "Restitution before discretionary fines" -> same ordering.
- "Not applicable" -> apply to fines/costs only (no restitution involved).

### Budget supportability

When a petition provides income and obligations:

```
monthly_disposable_income = monthly_income - total_monthly_obligations
```

- If `monthly_disposable_income >= requested_monthly_payment` and the requested amount is within `[min_monthly, max_monthly]`: `supportable` or `supported_by_budget`.
- If the requested amount is below `min_monthly`: `below_policy_minimum`.
- If the requested amount exceeds `max_monthly`: `above_policy_maximum`.
- If `monthly_disposable_income < min_monthly`: `unsupported_by_budget`.

## Placeholder Rules

Use the exact string "TBD from case file" for any field that is required by a form but missing from all available sources (portal, local payloads, hearing notes):

- SSN, driver's license number, mailing address, residence address, phone number
- Probation officer name, probation office location
- Any party detail not in the case file

Never invent these values. The form's `placeholder_instruction` from `/api/forms` confirms which fields get this treatment.

## Exclusion Rules

Exclude the following from financial postings and register totals unless the portal record or current policy directly supports them:

- Account management fees when `account_fee` in the payment policy is 0.00
- Collection fees, late payment fees, returned check fees, DMV fees when no triggering event (default, late payment, returned check, DMV referral) is recorded
- Traffic school fees not ordered in the hearing
- Restitution when no restitution order exists
- Court-appointed attorney fees, court reporter fees absent a specific order
- Stale fee schedule amounts -- always use current effective schedule

When excluding, include each item in the `excluded_charges` or `excluded_financial_items` array with its `reason_code` from the answer template enums.

## Output Conventions

- **Dates**: ISO 8601 `YYYY-MM-DD`. Date-times: `YYYY-MM-DDTHH:MM:SS`.
- **Currency**: Numbers to two decimal places (e.g., `150.00` not `150`).
- **Null values**: Use JSON `null` for genuinely absent dates (e.g., no disposition date for pending cases). Never use empty strings for dates or currency.
- **Sorting**: Follow the ordering rules in the answer template. When none specified, sort by case number or citation number ascending.
- **Enums**: Use the exact enum values from the answer template. Never substitute free text when an enum value exists.

## Anti-Patterns

- Do not post financial entries for pending, deferred, or continued cases that lack a signed final order.
- Do not carry forward fees or amounts from outdated worksheets or stale schedules.
- Do not add fees (account-management, collection, late, DMV, restitution, copy, certification) unless directly supported by the current portal fee schedule, payment policy, or a specific court order.
- Do not invent identifiers, addresses, phone numbers, or contact details.
- Do not use the audit memo date as the disposition date.
- Do not treat an `APD` label as public defender without checking corroborating sources.
- Do not include markdown or commentary in the JSON output; return only the JSON object.
