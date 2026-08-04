---
name: court-clerk-portal
description: >
  Prepare court clerk packets by cross-referencing local case payloads
  (hearing notes, memos, financial extracts, petition summaries) against
  a Court Operations Portal with REST endpoints.  Reconcile identity/counsel
  audits, compute fee schedules, structure payment plans, handle docket
  register entries, and produce strict-schema JSON answers.  Use when the
  task involves closing out a criminal/traffic docket, preparing a
  post-disposition financial-supervision packet, or assembling a
  sentencing-closeout bundle with portal verification.
---

# Court Clerk Portal Reconciliation Skill

You act as a deputy court clerk preparing structured closeout packets
and post-disposition filings.  Every task follows the same general
pattern: read local payloads, query the Court Operations Portal via
REST, cross-reference the two, and return a JSON object that strictly
conforms to the supplied answer template.

## Standard Workflow

1. **Read every local payload first.**  The prompt lists the relevant
   payloads inside `input/payloads/`.  Read them all before querying
   the portal.  Typical payloads include hearing/courtroom notes,
   clerk audit memos, finance-queue extracts, petition summaries,
   sentencing intake sheets, budget worksheets, and local form
   excerpts.

2. **Read the answer template.**  Every task ships an
   `answer_template.json` or `input/payloads/answer_template.json`.
   It defines the exact JSON shape, required keys, enum values, sort
   orders, currency precision (two decimal places), and date format
   (ISO YYYY-MM-DD; datetimes ISO YYYY-MM-DDTHH:MM:SS).  Use only the
   enum values listed in the template; do not substitute prose or
   invent new enum members.

3. **Query the Court Operations Portal.**  The prompt identifies the
   available endpoints from this pool:
   - `GET /api/jurisdictions`
   - `GET /api/cases`
   - `GET /api/charges`
   - `GET /api/docket-entries`
   - `GET /api/citations`
   - `GET /api/fee-schedules`
   - `GET /api/payment-policies`
   - `GET /api/forms`
   - `GET /api/financial-petitions`
   - `GET /api/search`

   The base URL is defined by `TASK_ENV_BASE_URL` (read from
   `environment_access.md` when present).  Query portal endpoints
   for the specific cases, citations, or petitions named in the
   prompt—use case numbers, citation numbers, or petition IDs as
   query parameters.

4. **Cross-reference and reconcile.**  Compare the local payloads
   against the portal data.  Flag every inconsistency as an audit
   finding or resolution note.  Apply the reconciliation hierarchy
   described below.

5. **Populate the template** in the exact order and shape required.
   Sort lists as directed (typically by case_number, citation_number,
   or petition_id ascending).  Use enum values from the template.
   Use `null` for genuinely empty date/datetime fields.

## Conflict Resolution Hierarchy

When local payloads and portal data disagree, resolve in this order
of authority (highest first):

| Priority | Source | When to trust |
|----------|--------|---------------|
| 1 | Hearing / courtroom notes | What the judge orally pronounced or signed in open court controls the disposition, sentence, plea, and departure. |
| 2 | Clerk audit / corroborating memo | Resolves identity corrections (name, DOB) and counsel-type disputes when the memo cites a specific document (cover sheet, defense entry of appearance). |
| 3 | Portal / CMS record | Authoritative for identity (name, DOB), current case status, and the official docket-entries timeline. Use the portal DOB over worksheet DOB unless the hearing notes confirm the worksheet. |
| 4 | Current fee schedule (portal) | Authoritative for fee amounts.  Never use stale or archived amounts (e.g., a 2023 drug-assessment amount for a 2025 disposition). |
| 5 | Payment policy (portal) | Determines which fees are supported at all and which must be excluded. |
| 6 | Finance queue / import worksheet | Lowest priority. Its values are carry-forward drafts; they must be verified and corrected. |

### Specific reconciliation rules

- **Identity conflicts (name/DOB):** Prefer the portal CMS record,
  then the corroborating memo, then the hearing notes.  Use
  `"TBD from case file"` only when DOB is genuinely absent from all
  sources.

- **Counsel-type conflicts:** If a calendar abbreviation says "PD" or
  "APD" but a memo or hearing note clarifies that counsel is actually
  appointed-private (county-paid, not public-defender-office), use
  `appointed_private`.  Do not treat appointed-private cases as
  public-defender-fee eligible.

- **Departure-status conflicts:** The judge's oral pronouncement (as
  captured in hearing notes) overrides a legacy worksheet's departure
  label.  If the judge said "no departure," enter `no_departure`
  regardless of what old screens show.

- **Pending / deferred matters:** If no final signed order exists
  (even if a draft worksheet shows a plea and fine), the case is
  `deferred` or `pending`.  Do not post financial entries; set
  fee_status to `hold` or `do_not_post_pending`, and set financial
  totals to 0.00.  Include the matter in the exclusions list.

- **Amended charges:** If a charge was amended (e.g., from a
  controlled-substance count to misdemeanor theft), the conviction
  count follows the amended charge.  Do not carry over fees or lab
  assessments that were attached only to the original, unamended
  charge, unless the judge expressly ordered them on the amended
  charge.

- **Lab/crime-lab fees:** Only include when the conviction is for an
  offense that triggers a lab assessment AND the judge or fee
  schedule supports it.  A dismissed worksheet line does not create a
  lab fee even if the worksheet once carried one.

## Financial Rules

### Fee schedules

Always query the portal for the current fee schedule.  The schedule
is identified by jurisdiction and date.  Use the fee amounts from the
schedule, not from the finance queue or worksheet.

### Unsupported / excluded charges

**Never add these fees unless the portal record, current payment
policy, or a signed court order directly supports them:**

- Account-management / account-maintenance fees
- Collection referral fees
- DMV notice / reinstatement fees (separate from the court balance;
  DMV fees are paid to the DMV)
- Late-payment fees
- Returned-check fees
- Restitution (unless a restitution order exists)
- Court-appointed-attorney fees (unless expressly ordered)
- Court-reporter fees
- Traffic-school fees (unless ordered in the hearing)
- Copy / certification fees

When the answer template requires an excluded-charges or
excluded-financial-items section, list each unsupported charge with
its reason code (`no_triggering_event`, `not_current_policy`,
`no_order_or_policy_support`, `stale_schedule`,
`not_in_hearing_order`, `unsupported_post_disposition`).

### Payment plan math

When constructing a payment schedule:
- `total_due` = fines_and_costs_balance + restitution_balance
- `regular_installment_amount` = approved monthly payment
- `total_installments` = ceiling of (total_due / regular_installment_amount),
  except the last payment may be smaller
- `full_payment_count` = number of full regular payments before the
  final remainder
- `final_payment_amount` = total_due - (full_payment_count × regular_installment_amount);
  if this equals 0, the final payment is the regular amount
- `final_due_date` = first_due_date + (total_installments - 1) months
- `return_to_court_date` = typically 2 months after final_due_date
- Payment application order: if restitution balance > 0, payments
  apply to restitution first; otherwise fines and costs only

Round all currency values to two decimal places.

### Docket register batch totals

Sum the fee items only for cases with fee_status `post`.  Exclude
cases with fee_status `hold`, `do_not_post_pending`, or `exclude`.
Count disposed vs. held/pending cases separately.

## Placeholder Handling

### When to use "TBD from case file"

Use the placeholder `"TBD from case file"` only for fields that:
- Are required by the form or template, AND
- Are genuinely missing from all available sources (local payloads,
  portal records, hearing notes)

Typical placeholder fields: driver_license_number, mailing_address,
phone_number, residence_address, ssn, probation_officer,
probation_office_location.

Do NOT use placeholders for fields that can be derived from other
sources (e.g., DOB from CMS, counsel type from memo).

### Placeholder record structure

If the template calls for a placeholder list, include:
- `case_number`
- `placeholder_value`: `"TBD from case file"`
- `missing_fields`: array of field names that are missing

Sort missing_fields alphabetically.

## Enum and Format Discipline

- Use EXACTLY the enum values listed in the answer template.  Do not
  paraphrase, hyphenate differently, or substitute similar words.
- Snake_case and SCREAMING_SNAKE_CASE are significant; preserve them.
- Currency: numeric values to exactly two decimal places (e.g., `500.00`).
- Dates: ISO 8601 YYYY-MM-DD.
- Datetimes: ISO 8601 local YYYY-MM-DDTHH:MM:SS.
- Use `null` (not the string `"null"`) for genuinely absent
  date/datetime fields.
- Sort lists exactly as the template orders them.
- Do not add keys that are not in the template.
- Do not omit required top-level keys.

## Portal API Usage

Base URL: `<TASK_ENV_BASE_URL>` from `environment_access.md`.

Typical query patterns:
- `/api/cases?case_number=CASE-NO` — look up a single case
- `/api/charges?case_number=CASE-NO` — look up charges for a case
- `/api/docket-entries?case_number=CASE-NO` — docket history
- `/api/citations?citation_number=CITATION-NO` — traffic citation
- `/api/fee-schedules?jurisdiction=JURISDICTION` — active fee schedule
- `/api/payment-policies?jurisdiction=JURISDICTION` — payment policy
- `/api/forms?form_id=FORM-ID` — form metadata and field labels
- `/api/financial-petitions?petition_id=PETITION-ID` — petition details
- `/api/search?q=defendant+name` — broad search

Always query the portal for every case/citation/petition named in the
prompt.  Use the results to verify or correct the local payload data.

## Task-Type Patterns

### Criminal docket closeout (sentencing batch)

1. Read hearing notes + audit memo + finance queue extract.
2. Query portal for each case's charges, fee schedules.
3. Identify audit findings: identity mismatches, counsel
   reclassification, departure corrections, fee-schedule updates,
   deferred/pending matters.
4. Build case dispositions with charge summaries.
5. Reconcile fees per case, excluding unsupported items.
6. Build docket entries with entry dates and financial totals.
7. Compute register batch totals.

### Traffic violation closeout with payment plans

1. Read hearing closeout note + local form excerpt.
2. Query portal for citations, fee schedules, payment policies, forms.
3. For each citation: record disposition (plea, finding, date).
4. Determine the correct fine tier and fee schedule source from the
   violation speed and current schedule.
5. Compute amount_due (fine + surcharge), excluding stale or
   unsupported charges.
6. Structure the payment plan (monthly amount, first due date,
   installment count, final payment, final due date).
7. Reference the correct local form and account-reference handling.
8. List all excluded charges with reason codes.

### Post-sentencing field packet (single case)

1. Read sentencing intake facts + payment petition + budget +
   form field excerpt.
2. Query portal for case, charges, docket entries, payment policies,
   forms, financial petitions.
3. Build case memo with sentence summary.
4. Prepare CC-1375 probation referral if ordered.
5. Prepare CC-1379 license suspension + installment payment order.
6. Compute budget review (income, obligations, disposable income,
   support classification, policy band).
7. Exclude unsupported financial items.
8. List placeholder fields for missing identifiers.

### Multi-defendant petition + supervision packet

1. Read petition summaries + sentencing/probation notes.
2. Query portal for cases, payment policies, forms, financial
   petitions.
3. For each petition: classify (initial_installment, etc.), determine
   support classification, compute payment schedule.
4. Prepare CC-1375 probation referrals where ordered.
5. Prepare CC-1379 license suspension orders.
6. List placeholder cases with missing fields.
7. Compute payment schedules: installments, final payment, return
   date.
8. Enforce payment application order (restitution first if balance >
   0, otherwise fines_costs_only).

## General Rules

- Every output is a single JSON object with no surrounding markdown
  or prose (unless the prompt explicitly allows it).
- Do not invent fees, balances, conditions, identifiers, or contact
  information.
- Do not copy task-specific answer values (names, amounts, dates)
  from one task to another; each task has its own payloads and portal
  data.
- If the portal is unreachable, note which queries failed and proceed
  with local payloads as the best available data.
- If a required field cannot be populated from any source, use the
  designated placeholder (typically `"TBD from case file"`) rather
  than guessing.
