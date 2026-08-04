---
name: court-clerk-closeout
description: Process court closeout, disposition, and financial reconciliation tasks for criminal and traffic cases. Use when a task involves reconciling local hearing notes, memos, finance queues, petitions, and form metadata with a Court Operations Portal REST API to produce a structured JSON court packet (audit findings, dispositions, fee reconciliation, docket entries, payment plans, register totals, probation referrals, license orders, and placeholder handling).
---

# Court Clerk Closeout Skill

Produce structured, schema-compliant court closeout JSON packets by reconciling multiple data sources against a Court Operations Portal API. Follow this workflow for every task.

## Step 1 — Read the prompt

Extract from the prompt:
- The **target court**, **jurisdiction code**, and **closeout date**.
- The **list of target case or citation numbers**.
- Which **local payload files** are provided (hearing notes, audit memos, finance extracts, petitions, budget worksheets, form excerpts, sentencing notes).
- The **`<TASK_ENV_BASE_URL>`** placeholder for the portal base URL.

## Step 2 — Read every local payload file

Read each payload file listed in the prompt **completely**. Payloads may be Markdown (`.md`), JSON (`.json`), or CSV (`.csv`). Do not skip or skim any payload — each one contains data the answer must reconcile.

For each case or citation number appearing in any payload, collect:
- Defendant name, date of birth, and identity corrections.
- Counsel type (retained, public defender, appointed private) and attorney name.
- Charge / offense code, statute, plea, and finding.
- Sentence details: fines, jail time, probation, license suspension, and any special assessments mentioned in bench notes.
- Financial amounts queued, plus any supervisor or auditor notes flagging stale amounts, incorrect fee schedules, omitted fees, or draft-only statuses.

## Step 3 — Read the answer template

The prompt always references an `answer_template.json` in the payloads. Read it **first**, before producing the answer.

Extract from the template:
- Every **required top-level key** and their required nested keys.
- Every **enum** and its allowed values. Never emit a value outside the template's enums.
- **Ordering rules** (e.g., sort by `case_number` ascending).
- **Formatting rules**: dates as ISO `YYYY-MM-DD`, datetimes as ISO `YYYY-MM-DDTHH:MM:SS`, currency as numbers with two decimal places, `null` for missing dates where the template allows it.
- **Placeholder rules**: whether a literal string like `"TBD from case file"` is required for missing identifiers, and which fields qualify for it.

## Step 4 — Query the Court Operations Portal

Construct the base URL from `<TASK_ENV_BASE_URL>` (typically `http://task-env:9018/`). Available endpoints (read-only `GET`):

| Endpoint | Use for |
|---|---|
| `/api/cases` | Case records, defendant identity, status, counsel |
| `/api/charges` | Charge details, offense codes, plea/finding records |
| `/api/citations` | Traffic citation records (when processing traffic dockets) |
| `/api/docket-entries` | Docket text, prior entries, register actions |
| `/api/jurisdictions` | Court jurisdiction metadata |
| `/api/fee-schedules` | Current fee schedule amounts (drug assessments, court costs, lab fees, public defender user fees, etc.) |
| `/api/payment-policies` | Active payment policy rules (minimum/maximum installment, down-payment requirements, return-to-court triggers) |
| `/api/forms` | Form metadata, field groups, current revisions |
| `/api/financial-petitions` | Payment petitions and installment agreements |
| `/api/search` | Entity search (cases, defendants, citations) |

Query the portal for every case or citation number in scope. For each, fetch the most-current record from the relevant endpoints. Use portal data to cross-check and override stale local data.

## Step 5 — Reconcile conflicts

For every case or citation, compare the local payload data against portal records. Resolve conflicts using these rules:

**Identity conflicts** (name, DOB): Prefer the portal CMS record. If the local hearing note or defense memo explicitly states a correction, use the corrected value and flag the conflict.

**Counsel conflicts** (PD / APD / retained): If hearing notes or a corroborating memo state that a lawyer labeled "PD" is actually appointed private counsel, reclassify accordingly and flag the conflict. Public defender user fees apply only to actual public-defender cases.

**Status conflicts** (disposed vs. deferred/pending): If hearing notes state no final order was signed, classify the case as deferred/pending with `hold_unsigned_order` action — even if the finance queue lists a draft disposition. Do NOT post financial entries for held cases.

**Fee schedule conflicts**: Compare queued fee amounts against current portal fee schedules. Use the current schedule, not stale carry-forward amounts. If the portal shows a higher/lower drug assessment or court cost than the local worksheet, use the portal value.

**Departure conflicts**: If finance queue or legacy screens carry a departure label, but hearing notes state the judge expressly found no departure, override with `no_departure`. For misdemeanor-only sentences where departures are not formally evaluated, use `not_evaluated_misdemeanor`.

**Draft-only conflicts**: If a finance worksheet contains amounts but the case is continued/pending with no final order, exclude those amounts from the register and mark the entries as `do_not_post_pending`.

**Missing data**: When a form-required field (SSN, driver license number, address, phone, probation officer/office) is absent from ALL available materials, use the exact placeholder string `"TBD from case file"`. Never invent identifiers or contact details.

## Step 6 — Reconcile financials

For each case:
1. Determine `fee_status`: `post` for disposed cases with signed orders, `hold` or `do_not_post_pending` for cases without signed final orders.
2. List each fee item using only fee codes enumerated in the template (e.g., `fine`, `court_cost`, `drug_assessment`, `public_defender_user_fee`, `crime_lab_fee`).
3. Compute `case_total` as the sum of enabled fee items.
4. If the template asks for excluded/unsupported charges, list every charge that appears in local notes but has **no support** from the portal's current policy or an explicit court order. Use the template's `excluded_charges` / `excluded_financial_items` enums.

## Step 7 — Build payment plan schedules (when applicable)

When the template includes a payment plan:
1. Read the budget/petition data: monthly income, monthly obligations, requested amount.
2. Compare against portal payment policy (`/api/payment-policies`) for minimum/maximum bands.
3. Classify as `supportable` (within band), `below_policy_minimum`, or `above_policy_maximum`.
4. Compute the schedule: `total_due = fines_and_costs + restitution`. Divide by `regular_installment_amount`. If there is a remainder, compute `final_payment_amount = total_due % regular_installment_amount` (or equivalently `total_due - full_installment_count * regular_installment_amount`), and `total_installments = full_installment_count + 1`.
5. Set `first_due_date` and `return_to_court_date` from petition/case data. The final due date is `first_due_date + total_installments months` (adjust day-of-month to remain consistent if the template requires it).
6. Account fees are excluded by default unless the portal's current payment policy explicitly supports them.
7. When restitution is non-zero, set `payment_application_order` to `restitution_before_fines_costs`; otherwise use `fines_costs_only`.

## Step 8 — Build form referral entries

When the template includes form entries (CC-1375 probation referrals, CC-1379 license/installment orders, or local payment plan forms):
1. Check the portal `/api/forms` for the current form ID and label.
2. Populate form fields from case data: conviction date, probation term, report datetime, license suspension dates.
3. If no probation was ordered, set `cc1375_status` to `not_ordered` and `report_datetime` to `null`.
4. For license suspension, compute `suspension_end_date` as `suspension_start_date + suspension_months - 1 day`, adjusting for the template's expected convention.
5. List form labels/field groups as specified in the template's `form_entry` or `required_labels_used` sections.

## Step 9 — Compute batch / register totals

Aggregate across all disposed cases:
- `assessed_case_count` / `disposed_case_count`: number of cases with fee entries posted.
- `held_case_count` / `excluded_pending_count`: number of cases held without financial posting.
- For each fee type, sum across disposed cases to produce per-fee and grand totals.
- `combined_amount_due` / `batch_total_due`: sum of all case totals across posted cases.

## Step 10 — Assemble and validate the output

1. Build the JSON object with every required top-level key in the exact order shown in the template's `required_top_level_keys`.
2. Sort every array by the key specified in the template's ordering rules (typically `case_number` or `citation_number` or `petition_id` ascending; for excluded items, by `charge_code` or `item` name ascending; for placeholder fields, by `field` name ascending).
3. Verify every value against the template's enums — no free-text where an enum is expected.
4. Verify every currency value has exactly two decimal places.
5. Verify every date uses ISO format and every datetime uses ISO local format.
6. Emit raw JSON only — no markdown fences, no commentary.

## Common patterns across jurisdictions

### Criminal disposition closeout (Redwood County, Union County style)
- Audit findings array: identity, counsel, fee_schedule, departure, and status conflicts.
- Case dispositions array: one entry per case with charge summaries, pleas, departure statuses.
- Fee reconciliation array: court costs, fines, drug assessments, lab fees, PD user fees.
- Docket entries: sentencing orders for disposed cases, disposition holds for deferred cases.
- Batch totals across posted cases.

### Traffic violation closeout (Oregon 22nd JD style)
- Matters array sorted by citation number.
- Financial entry: violation code, fine tier, schedule source, standard fine, surcharges.
- Payment plan: extended payment with monthly installments and remainder handling.
- Excluded charges: stale schedules, unsupported fees, no-triggering-event fees.

### Post-sentencing packet (Gloucester County style)
- Case memo summarizing conviction, sentence, and required actions.
- CC-1375 probation referral and CC-1379 license/installment order.
- Budget review: income, obligations, disposable income, policy band classification.
- Payment schedule: monthly installments with remainder, return-to-court date.
- Placeholder fields: missing identifiers, addresses, contact details.
- Excluded financial items: fees with no order or policy support.

### Multi-case petition packet (Gloucester County multi-matter style)
- Petitions array sorted by petition_id.
- Probation referrals and license orders arrays.
- Placeholder cases with missing field inventories.
- Restitution vs. fines-and-costs payment application order.
