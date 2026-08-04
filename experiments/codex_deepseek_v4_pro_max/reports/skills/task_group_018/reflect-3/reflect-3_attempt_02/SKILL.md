# Court Operations Portal – Clerk Closeout & Reconciliation Skill

## Overview

This skill covers reconciling court case data from a Court Operations Portal with local payload documents (hearing notes, audit memos, finance worksheets, petition summaries, form excerpts) to produce structured JSON closeout packets for criminal, traffic, and post-sentencing dockets.

## Portal Interaction

### Available Endpoints

- `GET /api/cases` – case metadata (defendant, counsel, DOB, status, dates)
- `GET /api/charges` – per-count offense, plea, disposition, sentence, departure
- `GET /api/citations` – traffic citation records (speed, zone, plea, plan approval)
- `GET /api/docket-entries` – chronological case events
- `GET /api/fee-schedules` – current and stale fee amounts with effective/end dates
- `GET /api/payment-policies` – jurisdiction payment plan rules (min/max monthly, account fees, first-due timing, restitution priority)
- `GET /api/forms` – form metadata and placeholder instructions
- `GET /api/financial-petitions` – petition intake with balances and budget data
- `GET /api/search` – multi-entity search (aggregates cases, docket entries, petitions)
- `GET /api/jurisdictions` – jurisdiction metadata

### Query Strategy

1. **Search first** using target case/citation/petition identifiers to get all related entities at once.
2. **Pull fee schedules** for the relevant jurisdiction and filter to current effective entries (where `end_date` is null and `effective_date` ≤ disposition date). Ignore stale/archived schedules unless performing audit history.
3. **Pull payment policies** for the jurisdiction to determine installment plan constraints, account fee treatment, and first-due-date rules.
4. **Pull forms** to verify form IDs and placeholder instructions.

## Resolution Hierarchy

When portal data conflicts with local documents, resolve in this order:

1. **Hearing notes / courtroom transcript** – the authoritative record of what the judge ordered in open court.
2. **Audit memo / corroborating memo** – clerk-identified conflicts with explicit resolution direction.
3. **Fee schedule / payment policy** – current portal values for financial calculations.
4. **CMS case record** – for identity (DOB, name spelling) when not contested by hearing notes.
5. **Finance queue / worksheet** – lowest authority; treat as draft until reconciled.

## Identity & Counsel Conflicts

- When the finance queue or worksheet has a different DOB or name spelling than the CMS, resolve using the audit memo's direction or the hearing notes.
- **Counsel type** determines fee eligibility:
  - `public_defender` → PD user fee applies (confirm current fee schedule amount).
  - `appointed_private` → no PD user fee; the label "APD" on a worksheet or calendar may be shorthand for appointed private, not public defender. Check CMS `counsel_type` and hearing-note clarification.
  - `retained` → no PD user fee.
- When the defense cover memo or hearing notes contradict the finance queue's counsel label, use the hearing notes / memo.

## Fee Schedule Handling

- **Use the fee schedule effective on the disposition date**, not stale/archived amounts.
- Common stale patterns: a 2023 drug assessment of $125 when the 2025 schedule shows $250; an old SOF table showing $1,000 when the current schedule shows $1,150.
- **Mandatory fees** flagged `mandatory: true` must be included. **Conditional fees** (like PD user fee) apply only when the triggering condition is met.
- **Do not add** account-management, collection, late, DMV, restitution, copy, or certification fees unless the portal record or current schedule directly supports them and a triggering event (default, referral, order) is documented.

## Payment Policy Application

- **Account fee**: check the policy's `account_fee` field. If `0.0`, exclude the fee even if a worksheet carries a stale amount.
- **Monthly payment range**: the approved installment must fall within `[min_monthly, max_monthly]`.
- **First due date**: typically `first_due_days` after conviction or petition submission. When the petition provides a `candidate_first_due_date`, prefer it over recalculation.
- **Restitution priority**: when `restitution_priority` says "Restitution before fines and costs", apply payments to restitution first.
- **Return to court**: `return_to_court_offset_days` may inform a review date; use petition-provided return dates when available.

## Payment Schedule Calculation

1. `regular_installment_amount` = the approved monthly payment.
2. `full_installment_count` = `floor(total_due / monthly_payment)`.
3. `final_payment_amount` = `total_due - (full_installment_count × monthly_payment)`, rounded to cents.
4. `total_installments` = `full_installment_count + 1` when `final_payment_amount > 0`, else `full_installment_count`.
5. `final_due_date` = `first_due_date` + (`total_installments − 1`) months.
6. `down_payment` follows policy (`down_payment_required`).

## Audit Finding Patterns

Common audit issues to identify when reconciling:

- **Identity**: DOB mismatch between finance queue and CMS → resolve to CMS or corroborating memo value.
- **Counsel**: PD label when counsel is actually appointed private → correct classification.
- **Status**: Queue says "disposed" but no final order was signed → exclude from register, mark as deferred/pending, set `hold_unsigned_order`.
- **Fee schedule**: Stale assessment amount → update to current schedule.
- **Fee schedule**: Omitted mandatory fee (e.g., PD user fee when counsel is PD; lab fee on controlled-substance conviction) → add.
- **Fee schedule**: Fee applied that should not be (e.g., PD user fee for appointed-private; lab fee for amended non-lab charge) → exclude.
- **Departure**: CMS/queue says departure exists but judge expressly stated no departure → correct to `no_departure`.
- **Charge amendment**: Original charge amended to different offense → recalculate applicable fees and note the amendment.

## Charge & Disposition Handling

- When CMS charge data conflicts with hearing notes on plea, finding, or disposition, the hearing notes control.
- For amended charges: the original count that was amended away counts toward `dismissed_or_amended_away_counts`; the amended charge is the conviction count.
- **Departure status**: use hearing notes over CMS. If the judge said "no departure" or "top of range," use `no_departure` regardless of CMS departure fields.
- For misdemeanor offenses where departure analysis is not typical, use `not_evaluated_misdemeanor`.
- For pending/deferred cases: plea is `none` or `not_entered`, disposition is `pending`, departure is `not_applicable` or `not_entered_pending`.

## Case Status & Closeout Actions

- **Disposed with signed order** → `enter_disposition`, post financials.
- **Deferred / no signed order** → `hold_unsigned_order` or `no_closeout`; exclude from financial register.
- **Continued pending** → `pending_exclude`, no financial posting, note next status check date.

## Placeholder Convention

- Use **exactly** `"TBD from case file"` for any required field whose value is genuinely missing from all available sources (portal, hearing notes, petitions, intake sheets).
- **Never invent** identifiers (SSN, driver's license number), contact details (address, phone), probation officer names, or office locations.
- Fields commonly subject to placeholders: `ssn`, `driver_license_number`, `residence_address`, `mailing_address`, `phone_number`, `probation_officer`, `probation_office_location`.

## Enum Usage

- Always use the **exact enum string** from the answer template. Do not substitute prose descriptions for enum values.
- Pay close attention to enum sets specific to each task schema — e.g., `support_classification` uses `supportable` (not `supported_by_budget`), departure enums vary by task.
- Sort lists as directed by the answer template's `ordering_rules`.

## Currency & Date Formatting

- All monetary values: numbers rounded to **two decimal places**.
- Dates: **ISO 8601 YYYY-MM-DD**.
- Date-times: **ISO 8601 local YYYY-MM-DDTHH:MM:SS**.
- Use `null` for dates that should not be entered (e.g., disposition date for pending cases).

## Docket & Register Assembly

- Each disposed case gets a `sentencing_order` docket entry with the applicable `summary_code` that best describes its distinguishing feature (e.g., `conviction_no_pd_fee`, `conviction_drug_assessment`, `conviction_no_departure`).
- Held/deferred cases get a `disposition_hold` entry with `hold_unsigned_order`.
- Register totals aggregate only posted (not held) cases.

## Excluded Financial Items

- List every unsupported or stale charge that appeared in worksheets or intake notes but should **not** be included in the starting balance.
- Common categories: restitution (when no order exists), late fees, DMV fees, collection fees, returned-check fees, account-management fees (when policy says $0), traffic-school fees, court-appointed-attorney fees (when counsel is retained), court-reporter fees.
- Reason codes should match the exclusion rationale: `no_order_or_policy_support`, `not_part_of_balance`, `stale_schedule`, `no_triggering_event`, `not_current_policy`, `not_in_hearing_order`.

## General Workflow

1. Read the task prompt, answer template, and all local payloads.
2. Query the portal for every target case/citation/petition — use `search` for broad retrieval, then `cases`, `charges`, `citations`, `financial-petitions` for detail.
3. Pull `fee-schedules` and `payment-policies` for the relevant jurisdiction.
4. Pull `forms` for form metadata.
5. Identify every conflict between local documents and portal data.
6. Resolve conflicts using the resolution hierarchy.
7. Build the answer strictly matching the template schema, using exact enum values.
8. Validate currency precision, date formats, sort orders, and placeholder conventions.
