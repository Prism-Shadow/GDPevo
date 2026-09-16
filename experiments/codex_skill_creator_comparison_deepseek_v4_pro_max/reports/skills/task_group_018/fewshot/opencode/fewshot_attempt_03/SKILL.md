---
name: court-clerk-closeout
description: Prepare court clerk closeout and field-packet JSON answers from local case materials and a Court Operations Portal REST API. Use when the user mentions court docket closeout, sentencing packets, traffic-violation disposition, post-sentencing field packets, clerk reconciliation, or defendant financial petitions. Do not use for generic legal document drafting or non-clerk workflows.
---

# Court Clerk Closeout and Field-Packet Preparation

You prepare structured, clerk-ready JSON closeout packages by reconciling local case materials with a Court Operations Portal REST API. You resolve conflicting data between local worksheets, hearing notes, intake forms, and the authoritative portal records; compute financials from active fee schedules and payment policies; draft form-field entries for probation referrals, license orders, and payment plans; and aggregate batch register totals.

## Core Workflow

Every closeout follows this sequence. Keep the steps explicit — do not merge or skip them even when the input looks simple.

1. **Read the answer template first.** It defines every required key, enum, ordering rule, currency rule, and date format. The template sits in `input/payloads/answer_template.json` unless the prompt specifies another path. Consume it before touching any case data.

2. **Read all local payloads.** The prompt names the relevant files — hearing notes, audit memos, finance queue extracts, worksheets, intake facts, petition summaries, probation notes, form excerpts. Read every file the prompt lists. These are the working materials; values embedded here must be cross-checked against the portal but are the primary source for courtroom events, plea entries, and judge instructions.

3. **Query the Court Operations Portal.** The prompt gives a base URL (usually `<TASK_ENV_BASE_URL>`) and a list of allowed endpoints. Query every endpoint that is relevant to the task. Not every endpoint listed needs to be called — but every case number, citation number, petition ID, or form ID referenced in the local materials must be verified against the portal.

   Standard endpoints and what they provide:
   - `GET /api/cases?case_number=...` — defendant identity, DOB, counsel of record, case status, offense codes
   - `GET /api/charges?case_number=...` — charge details, plea, disposition, departure findings
   - `GET /api/docket-entries?case_number=...` — docket history, entry dates, order status
   - `GET /api/citations?citation_number=...` — traffic citation data, violation code, defendant
   - `GET /api/fee-schedules?jurisdiction=...` — current fee amounts by offense tier and jurisdiction
   - `GET /api/payment-policies?jurisdiction=...` — payment-plan rules, installment ranges, account-fee treatment
   - `GET /api/forms?form_id=...` — form metadata, field labels, revision context
   - `GET /api/financial-petitions?petition_id=...` — petition status, balances, requested terms
   - `GET /api/jurisdictions?code=...` — jurisdiction details and codes
   - `GET /api/search?q=...` — general search for names, case numbers, identifiers

   Query patterns: prefer exact lookup (by case number, citation number, form ID) over broad search. When a local material says "confirm current schedule," that's a signal to pull the active fee schedule and payment policy from the portal.

4. **Cross-check and reconcile.** Compare every data point from local materials against the portal response. When they conflict, choose the authoritative source based on the record's nature:
   - **Identity fields (DOB, name spelling):** the portal is authoritative. Record the discrepancy as an audit finding.
   - **Counsel designation:** if the portal labels counsel as "PD" but a defense memo or judge's on-the-record statement confirms appointed private counsel, the courtroom record controls. Flag the correction.
   - **Case status:** a draft worksheet that shows "disposed" does not override a portal docket that shows "continued pending" or an unsigned order.
   - **Fee amounts:** the current portal fee schedule controls. A legacy amount on a worksheet or finance queue is stale and must be corrected.
   - **Departure findings:** hearing notes and the judge's on-the-record statements control. A legacy charge-screen label does not override the courtroom record.
   - **Plea and conviction:** the hearing notes are the primary record for what happened in open court.

5. **Structure the answer to the template.** Every top-level key in the answer template must be present in your output. Fill arrays with an item per case/citation/matter, sorted by the rule in the template (usually case number ascending). Use only the exact enum values the template defines — do not invent or approximate enum strings. Convert all money to numeric two-decimal-place values, all dates to ISO YYYY-MM-DD, and all datetimes to ISO local `YYYY-MM-DDTHH:MM:SS`.

## Audit and Reconciliation

When local materials and portal records disagree, surface the conflict explicitly in an audit section (the template key varies: `audit_findings`, `case_audit`, or similar). Each audit item must record:

- Which case or matter the conflict involves
- What type of conflict (identity, counsel, status, fee_schedule, departure)
- What the conflicted/stale value was and where it came from
- What the corrected value is
- Which source resolved the conflict (use_cms, use_hearing_notes, use_corrob_memo, use_fee_schedule, hold_unsigned_order, verify_before_entry, exclude_pending)

A case with no signed final order must not receive a disposition entry or financial posting. Flag it as deferred/pending, set the correct exclusion reason, record the next status-check date if available, and carry zero-dollar financials.

## Financial Computation

Compute fee totals from the active portal fee schedule, not from worksheet or queue carry-forward amounts. The general rule:

- **Fine:** from the hearing record, unless the judge waived it
- **Court cost:** mandatory, from the active fee schedule unless specifically waived
- **Special assessments (drug assessment, lab fee):** from the current schedule; confirm the schedule applies (controlled-substance convictions trigger drug assessment; lab fees trigger per the judge's announcement)
- **Public defender user fee:** post it only when counsel type is confirmed as public defender; if counsel is appointed private, do not post the fee
- **County surcharge:** from the fee schedule or local form excerpt

**Payment plans:** when a payment plan is in the materials or petition, compute the schedule:

- `total_due` = fines + costs + assessments + user fees (only those supported by record and policy)
- Divide the `total_due` by the `monthly_payment` amount to find the number of full installments
- The final payment is the remainder (never zero unless the division is exact)
- The first due date is from the hearing note or petition candidate date
- The return-to-court date follows the final due date by a standard interval (typically plus 60 days, unless the policy or petition says otherwise)

**Payment application order:** when both restitution and fines/costs exist, the order is set by the petition or note. If a petitioner requests restitution-first, honor it.

## Unsupported Fees and Exclusions

Never add fees that the record or policy does not support. Audit every fee line that appears in a worksheet or queue extract: if the portal fee schedule or payment policy does not authorize it, list it as excluded with a reason code. Common exclusions:

- `account_management_fee` / account-management charge — exclude unless current policy explicitly adds it; stale counter worksheets do not qualify
- `late_payment_fee` / `collection_fee` / `dmv_fee` / `returned_check_fee` — exclude unless there is a triggering event in the hearing record
- `traffic_school_fee` — exclude unless ordered in the hearing minute
- `restitution` — exclude unless the sentencing intake contains a restitution order
- `court_appointed_attorney_fee` / `court_reporter_fee` — exclude unless the sentencing order includes them
- `dmv_reinstatement_fee` — exclude from the court balance; it is a DMV matter
- Stale schedule amounts — flag and exclude, replacing with the current schedule amount

## Placeholder Handling

When a form field is required by the template but the available materials do not provide the value, use the exact placeholder string `TBD from case file`. Never invent identifiers, contact details, officer names, office locations, license numbers, SSNs, addresses, or phone numbers. List every placeholder field in the template's placeholder section with its reason code:

- `missing_identifier` — SSN, driver's license number, or other government identifier
- `missing_contact` — mailing address, residence address, phone number
- `missing_office_detail` — probation officer name, probation office location
- `missing_party_detail` — attorney name, judge assignment, or other party info

## Batch and Register Totals

When the template asks for aggregate totals, compute them across all disposed cases only (never include pending/deferred/held cases in financial totals):

- Count disposed vs. held/excluded cases
- Sum fines, court costs, assessments, and user fees across disposed cases
- Compute the grand total

## Enum Discipline

The answer template defines allowed values for every enum field. Do not approximate: if the template says `"no_contest"` for a plea, do not write `"nolo_contendere"` or `"no contest"`. If the template says `"supported_by_budget"` for a support classification, do not write `"supported"` or `"feasible"`. Match the template exactly.

If the answer template uses `null` for a missing date, use JSON `null`, not `"null"` or `""`.

## Budget Review

When a petition includes a budget (monthly income, obligations, disposable income), compute whether the requested monthly payment falls within the policy band. Classify it as `supported_by_budget` when disposable income exceeds the requested payment by a reasonable margin. If the policy sets a band with minimum and maximum monthly amounts, the selected installment must fall within that band.

## Form Entries

When the materials reference specific court forms (CC-1375, CC-1379, local payment-plan agreements), populate the template fields using:

- **Form ID and label:** from the form excerpt or portal forms endpoint
- **Header fields:** case number, defendant name, court, conviction date — from the case record
- **Substance fields:** probation term, report datetime, license suspension dates — from the sentencing intake or hearing notes
- **Account reference for payment plans:** the citation number or case number, as specified by the local form excerpt

## Ordering

Sort every array in the answer by the rule declared in the template. Most templates sort by `case_number` or `citation_number` ascending. Follow the rule — do not use the order materials appear in or any other ordering.

## Verification Before Finishing

Before writing the final answer:

1. Run through every required top-level key in the template and confirm it exists in your output.
2. Check that every fee line is supported by the active schedule or hearing order.
3. Confirm that no case with a pending/unsigned status received a disposition entry or financial posting.
4. Verify that all placeholder fields use exactly `TBD from case file`.
5. Confirm that all enum values match the template's allowed list exactly — no inventing, no prose substitutions.
6. Sum all batch totals and verify they match the individual case totals.
7. Confirm sorting rules are obeyed.
