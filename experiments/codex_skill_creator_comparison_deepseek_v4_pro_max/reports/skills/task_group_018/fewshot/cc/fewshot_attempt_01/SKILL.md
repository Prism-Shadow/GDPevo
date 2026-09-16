---
name: court-clerk-closeout
description: Prepare court clerk closeout and financial reconciliation packets by cross-referencing local case materials against a Court Operations Portal REST API. Use this skill whenever the task involves court case docket closeout, sentencing disposition reconciliation, fee schedule audits, payment plan computation, traffic citation financial entry, probation referral packet assembly, license suspension orders, or any clerk-of-court batch register preparation. Trigger even when the user describes the work as "sentencing closeout," "disposition register," "post-sentencing packet," "traffic violation hearings," "financial petition review," or "clerk audit."
---

# Court Clerk Closeout

Reconcile local case materials (hearing notes, finance queue extracts, clerk
audit memos, petitions, form excerpts, intake worksheets) against the Court
Operations Portal REST API and produce a single structured JSON answer that
follows the provided answer template.

This skill covers criminal sentencing closeouts, traffic violation financial
entries, post-sentencing field packets, criminal disposition registers, and
financial petition reconciliations across multiple jurisdictions.

## Workflow overview

1. Read the prompt to identify the target cases/citations and the jurisdiction.
2. Read every attached payload file and the answer template.
3. Query the portal for every target case or citation, plus the active fee
   schedule, payment policy, and form metadata for the jurisdiction.
4. Reconcile conflicts across sources using the rules below.
5. Build the JSON answer matching the template schema, field types, and enums.

## Portal API

The task environment provides the Court Operations Portal. Use the base URL from
the `<TASK_ENV_BASE_URL>` placeholder in the prompt. All endpoints accept
standard GET query-string filters. Read [references/portal-api.md](references/portal-api.md)
for endpoint details before starting.

Key pattern: every target case number, citation number, or petition ID is
queryable through a dedicated endpoint. Use jurisdiction_code to scope fee
schedules and payment policies to the correct county.

## Reconciliation methodology

Reconciliation is not "pick one source." Cross-reference every available source,
surface discrepancies as audit findings, and produce a unified clerk-ready
entry. Read [references/reconciliation.md](references/reconciliation.md) for
the full methodology.

### Identity and demographics

When the defendant name or DOB differs across sources, resolve in this priority:

1. The Court Operations Portal CMS record (the authority for identity).
2. Defense cover memo or corroborating paper filing (for corrections the portal
   has not yet ingested).
3. Hearing notes (bench shorthand may carry typos).
4. Finance queue worksheet (carry-forward values may be stale).

Record identity mismatches as audit findings with `issue_type: "identity"`.
Record counsel mismatches as `issue_type: "counsel"`.

### Counsel classification and public defender fees

Classify counsel into `public_defender`, `appointed_private`, or `retained`.

A public-defender user fee (`fee_code: "public_defender_user_fee"`) applies
only when counsel is classified as `public_defender`. If the finance queue
labels someone "PD" but corroborating material (defense memo, judge clarification
on the record) shows the attorney is appointed private counsel paid by the
county, do not post the public-defender user fee. Record this as an audit finding
with `issue_type: "counsel"`.

An abbreviation like "APD" or "PD" on a calendar or finance queue is not
definitive; verify against hearing notes and defense filings.

### Status and final-order checks

A case with only a draft worksheet, an unsigned order, or a continued/status
hearing is not disposed. Do not enter a disposition, post financials, or include
it in the register totals.

- If hearing notes say the judge did not sign the order or the matter was
  continued, set `closeout_action: "hold_unsigned_order"` or the equivalent
  pending/exclude status from the template.
- Record the audit finding with `issue_type: "status"`.

### Departure findings

If a legacy or draft worksheet carries a departure notation (durational,
dispositional) that the hearing notes contradict, trust the judge's
pronouncement from the hearing notes. Record the conflict as
`issue_type: "departure"`.

If the offense is a misdemeanor and no departure evaluation was ordered, mark
departure_status as `not_evaluated_misdemeanor` or the nearest template enum.

### Fee schedule reconciliation

Read [references/fee-resolution.md](references/fee-resolution.md) for the full
fee-resolution procedure.

The portal `/api/fee-schedules` returns all fee records keyed by
`jurisdiction_code`. For every fee that a local worksheet or finance queue
references:

1. Match by jurisdiction, fee_type, and effective_date range.
2. Use only the fee record whose effective_date <= the disposition date and
   whose end_date is null or > the disposition date. Ignore stale records whose
   end_date has passed.
3. If a local worksheet uses an archived amount (e.g., "drug assessment 125"
   when the current schedule says 250), correct it to the current amount and
   flag the audit finding with `issue_type: "fee_schedule"`.
4. Mandatory fees (`mandatory: true`) apply whenever the conviction triggers
   them. Non-mandatory fees apply only when the portal or policy explicitly
   supports them for this case type.

### Stale and unsupported charges

A fee or charge that appears only in a stale schedule, an old sticky note, or
a worksheet scratchpad must be excluded unless:
- The active portal fee schedule includes it for this jurisdiction, AND
- The hearing order or disposition text authorizes it.

Explicitly list every unsupported charge as an excluded item in the answer.

### Payment plan calculations

When the template requires a payment schedule:

1. First due date = disposition_date + `first_due_days` from the payment policy
   (or the candidate date from local materials if provided).
2. If policy says first due date is "15th of the next month," adjust accordingly.
3. Installment amount: use the approved monthly amount from local materials, or
   compute from the policy band (`min_monthly` to `max_monthly`).
4. Down payment defaults to `0.00` unless policy says otherwise.
5. Installment math:
   - full_payment_count = floor(total_due / installment_amount)
   - final_payment_amount = total_due - (full_payment_count * installment_amount)
   - total_installments = full_payment_count + (1 if final_payment_amount > 0 else 0)
   - final_due_date = first_due_date + (total_installments - 1) months
   - If the final payment is \/usr/bin/bash, the last full payment is the final.
6. Return-to-court date = final_due_date + `return_to_court_offset_days` from
   the policy.
7. Restitution priority: when the payment policy says "Restitution before fines
   and costs," apply payments to restitution first. Otherwise, apply to fines
   and costs first.

### Budget review for petitions

When a petitioner submits a budget (income and obligations):

1. Disposable income = monthly_income - total_monthly_obligations.
2. If the requested monthly payment is within the policy band and <= disposable
   income, classify as `supported_by_budget` / `supportable`.
3. If above the policy maximum, classify as `above_policy_maximum`.
4. If below the policy minimum, classify as `below_policy_minimum`.
5. If the amount exceeds disposable income, classify as `unsupported_by_budget`.

## Placeholder rule

Do not invent missing identifiers (SSN, driver license number, address, phone,
probation officer name, probation office location) that are required by a form
but absent from all available materials. Use the exact placeholder string
required by the materials, typically `"TBD from case file"`.

List every missing field as a placeholder entry with a reason_code:
- `missing_identifier` for SSN, driver license number
- `missing_contact` for address, phone
- `missing_office_detail` for probation officer/office

## Answer construction

- Return one JSON object matching the answer template.
- Use enum values from the template; do not replace them with prose.
- Sort items as specified by the template ordering rules.
- Currency values must be numbers to two decimal places.
- Dates must be ISO YYYY-MM-DD. Date-times must be ISO YYYY-MM-DDTHH:MM:SS.
- If a case has no disposition, set financial amounts to 0.00 and disposition
  fields to null where needed.

## Register totals

When the answer requires batch/register totals:
- assessed_case_count / disposed_case_count: count of cases posted to the
  register.
- held_case_count / excluded_pending_count: count of cases held back.
- Fee totals: sum each fee type across all posted cases only.
- grand_total / batch_total_due: sum of all posted case totals.

## Jurisdiction notes

The portal returns jurisdiction records with `jurisdiction_code` values. Use the
code to scope all downstream queries:

- Arkansas: `AR-RC` (Redwood), `AR-UC` (Union), `AR-LC` (Lake), `AR-MC` (Madison), `AR-WC` (White)
- Oregon: `OR22-JEFF` (Jefferson), `OR27-CLAT` (Clatsop), `OR19-LINN` (Linn)
- Virginia: `VA-GLO` (Gloucester), `VA-HAM` (Hampton)

Arkansas forms use `AR_SENT_ORDER`. Oregon uses `OR_22JD_PLAN` / `OR_27JD_PLAN`.
Virginia uses `VA_CC1375` / `VA_CC1379`.

## Support files

- [references/portal-api.md](references/portal-api.md) — endpoint reference with
  query parameters and response shapes.
- [references/reconciliation.md](references/reconciliation.md) — full
  reconciliation methodology with step-by-step procedure and audit-flag
  decision tree.
- [references/fee-resolution.md](references/fee-resolution.md) — fee schedule
  matching, stale-fee detection, mandatory vs optional rules, and payment-policy
  driven installment math.
