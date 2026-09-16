---
name: court-ops-portal
description: Resolve court closeout and post-disposition packets by cross-referencing local case materials against a Court Operations Portal, producing structured JSON reconciliation answers with financial computation and placeholder discipline.
---

# Court Operations Portal Skill

Use this skill when a task asks you to prepare a court closeout, sentencing packet, post-disposition financial packet, traffic violation closeout, or similar structured reconciliation against a Court Operations Portal.

## Core Workflow

Every task in this domain follows the same pattern:

1. **Read everything local first.** Load every file in the payloads directory: memos, hearing notes, worksheet CSVs, form excerpts, intake summaries, petition summaries, and the answer template. The template defines the exact output shape, enums, field types, and ordering rules that you must follow.

2. **Query the portal for authoritative records.** Use the provided base URL at `<TASK_ENV_BASE_URL>`. The portal endpoints available are:
   - `GET /api/jurisdictions` — verify jurisdiction codes
   - `GET /api/cases` — fetch case records by case number
   - `GET /api/charges` — fetch charge records by case number
   - `GET /api/docket-entries` — fetch docket history by case number
   - `GET /api/citations` — fetch citation records (traffic matters)
   - `GET /api/fee-schedules` — fetch fee schedule for the jurisdiction
   - `GET /api/payment-policies` — fetch payment/payment-plan policy for the jurisdiction
   - `GET /api/forms` — fetch form metadata (IDs, labels, field requirements)
   - `GET /api/financial-petitions` — fetch financial petition records
   - `GET /api/search` — search by name, case number, or other identifier

   Use the portal to resolve conflicts, verify statuses, confirm fee amounts, and fill in missing details that the local materials cannot supply.

3. **Reconcile conflicts.** Compare local materials against portal data. When they disagree, resolve using this priority:
   - Portal case-management records are authoritative for identity (name, DOB), charge details, and current status.
   - Hearing notes and clerk memos are authoritative for what the judge actually said (departure findings, fee waivers, payment plan terms, and whether an order was signed).
   - Current fee schedules replace archived/legacy amounts.
   - Corroborating defense memos resolve ambiguities about counsel type (public defender vs. appointed private).

4. **Build the answer.** Produce a single JSON object that exactly matches the answer template schema. Follow every enum, every ordering rule, every format rule (ISO dates, currency to two decimals). Do not add fields not in the template.

5. **Run a self-check pass.** Before finalizing, verify: every required top-level key is present, every required sub-key is present, all enum values are from the template's allowed set, all currency values are numbers (not strings), all dates are ISO format, arrays are sorted per the template's ordering rules, and no unsupported fees or invented values appear.

## Financial Reconciliation Rules

These rules apply across every court-closeout task:

- **Current schedule beats archived.** If a local worksheet or intake note references an old fee amount (e.g., a 2023 drug assessment of $125 when the 2025 schedule says $250), use the current portal fee schedule.
- **Never add unsupported fees.** Do not include account-management fees, collection fees, DMV fees, returned-check fees, late-payment fees, traffic-school fees, restitution, court-appointed-attorney fees, or court-reporter fees unless the portal record, the current fee schedule, or the hearing order explicitly supports them. When in doubt, exclude and document in the exclusion list.
- **Fine waiver means zero, not omission.** If the hearing notes or case record says "fine waived," set the fine to 0.00. Do not omit the field.
- **Court costs are mandatory unless waived on record.** If a jurisdiction has a standard court cost from the fee schedule and the hearing notes do not explicitly waive it, include it.
- **Pending/unsigned orders produce no financials.** If a case is deferred, continued, or the final order was not signed, set its financial status to hold/exclude/do-not-post, zero out all amounts, and mark it in the exclusions section. Do not carry draft worksheet amounts into the register.
- **Payment plan math.** When computing installments:
  - `full_payment_count = floor(total_due / monthly_payment)`
  - `final_payment_amount = total_due - (full_payment_count * monthly_payment)`
  - If `final_payment_amount == 0`, then `total_installments = full_payment_count` and there is no separate final smaller payment.
  - Otherwise `total_installments = full_payment_count + 1`.
  - The final due date is `first_due_date + (total_installments - 1) * interval_months`.

## Identity and Counsel Audit Patterns

When local materials disagree about a defendant's name, DOB, or attorney:

- **Name/DOB conflict.** If the finance queue or worksheet has a slightly different name or DOB than the hearing notes, check the portal case record. The portal is authoritative for identity. If the portal also disagrees, the hearing notes (confirmed by the judge) have priority over a worksheet that may carry forward unverified intake values.
- **Counsel classification.** "PD" on a worksheet means public defender. "APD" without other context may mean appointed private defense (not public defender). Check portal records and corroborating memos. An appointed private attorney paid by the county is `appointed_private`, not `public_defender`. A `public_defender` classification triggers PD user fees where supported by the fee schedule; `appointed_private` does not.
- **Missing DOB.** Use `"TBD from case file"` as the dob_for_entry value, set identity_action to `use_placeholder_verify`, and add an audit flag like `dob_missing_verify`. Never borrow a DOB from a similarly named person in prior search results.

## Placeholder Discipline

When a required form field cannot be completed from the case file, hearing notes, petition, or portal:

- Use the exact value `"TBD from case file"` (or whatever placeholder the template specifies).
- Add the field to a placeholder_fields or placeholder_cases section with a reason code.
- Never invent SSNs, driver license numbers, mailing addresses, phone numbers, probation officer names, or probation office locations.
- Do not omit a required field just because it is missing; use the placeholder.

## Exclusion Discipline

Every task should explicitly list items excluded from the financial posting or register:

- **Pending/no-order cases.** List in the exclusions array with the reason and next check date.
- **Unsupported fees.** List every fee you considered but excluded because the portal, policy, or hearing order did not support it. Use the template's enum for reason codes (`no_order_or_policy_support`, `not_current_policy`, `no_triggering_event`, `not_in_hearing_order`, `not_part_of_balance`, `stale_schedule`, `unsupported_post_disposition`).
- **Stale charges.** Traffic closeouts in particular: if the intake cover sheet mentions an old SOF table or statutory maximum figure that does not match the current fee schedule, exclude those stale alternative amounts and note them.

## Portal Query Patterns

When you need to look up something specific:

- **Case records:** `GET /api/cases?case_number={case_number}` (or equivalent query params as the portal implements them)
- **Fee schedules:** `GET /api/fee-schedules?jurisdiction={jurisdiction_code}` to get the current schedule for the jurisdiction
- **Payment policies:** `GET /api/payment-policies?jurisdiction={jurisdiction_code}` for the jurisdiction's payment plan rules
- **Forms:** `GET /api/forms?form_id={form_id}` to get form label and field requirements
- **Search:** Use for name lookups when verifying identity, or for finding related records

If the portal returns no results for a query, treat the local materials as the best available source and flag any unresolvable conflicts in the audit findings.

## Output Format Checklist

Before submitting the answer, verify:

- [ ] All top-level keys from the answer template are present.
- [ ] Every required sub-key in every object is present.
- [ ] All enum values match the template's allowed set exactly (case-sensitive).
- [ ] All currency values are numbers with at most two decimal places, not strings.
- [ ] All dates are ISO 8601 YYYY-MM-DD (or YYYY-MM-DDTHH:MM:SS for datetimes).
- [ ] Arrays are sorted per the template's ordering rules.
- [ ] No invented identifiers, contact details, or fee amounts.
- [ ] Every conflict found between local and portal data has a corresponding audit finding entry.
- [ ] Pending cases have zero financials and appear in the exclusions.
- [ ] Unsupported fees appear in the exclusion list with reason codes.
- [ ] Placeholders use "TBD from case file" exactly where data is genuinely unavailable.

## Task-Type Specific Guidance

### Criminal Sentencing Closeout

Produces: audit_findings, case_dispositions, fee_reconciliation, docket_entries, register_totals.

Focus on identity/counsel/status/departure conflicts between financial queues, hearing notes, and portal records. Reconcile fee amounts against current schedules. Hold unsigned orders. Compute register totals by summing only disposed cases.

### Traffic Violation Closeout

Produces: matters (each with disposition, financial_entry, payment_plan, form_entry), excluded_charges, batch_totals.

Verify citation records and fee schedules from the portal. Match the fine tier to the violation code using the current schedule. Build payment plans from the amount due using the approved monthly payment. Use the citation number as the account reference when no separate account/case number exists. Exclude stale schedule amounts and unsupported fees.

### Post-Sentencing Field Packet

Produces: case_memo, cc1375, cc1379, budget_review, placeholder_fields, excluded_financial_items (or petitions, probation_referrals, license_orders, placeholder_cases for multi-petition variants).

Extract conviction/sentence details from the intake sheet. Cross-check portal for form metadata, payment policies, and financial petitions. Compute payment schedules from the total due and approved monthly amount. Budget reviews compare disposable income against policy bands. License suspension dates use the conviction date as the start (not release date) unless the materials specify otherwise. Placeholder all missing identifiers, addresses, and contact/office details.
