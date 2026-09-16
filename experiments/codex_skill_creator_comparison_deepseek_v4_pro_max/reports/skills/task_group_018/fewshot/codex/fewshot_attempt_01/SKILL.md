---
name: court-clerk
description: Structured court record retrieval, cross-source reconciliation, fee-schedule audit, and payment-plan computation for circuit/traffic court docket closeouts, post-sentencing field packets, and financial petition intake. Use when Codex needs to prepare a clerk-ready JSON answer for a court operations task that requires reconciling hearing notes, finance queues, petitions, or clerk memos against a live Court Operations Portal API, with answer_template.json schemas that include audit findings, case dispositions, fee reconciliation, docket entries, register totals, payment plans, probation referrals, license orders, placeholder handling, or unsupported-financial-item exclusions.
---

# Court Clerk Operations

## Overview

This skill covers structured clerk tasks that reconcile local case materials (hearing notes, audit memos, finance extracts, petitions, worksheets) with live portal data. The output is always a single JSON object conforming to a supplied `answer_template.json` schema.

## Core Workflow

Follow this sequence for every clerk task. The steps are ordered; later steps depend on earlier resolution.

### 1. Read the answer_template.json first

The template defines the exact output contract: required keys, enums, ordering rules, currency precision, and date format. Internalize these before reading case materials. Violating the schema (wrong enum, missing key, unsorted list) produces an invalid answer.

### 2. Map the API endpoints

Every task prompt lists available portal endpoints. Query them early to establish the current fee schedules, case records, charge screens, and payment policies you will reconcile against. The portal is reached at the URL embedded in the prompt (tagged as `TASK_ENV_BASE_URL`). All endpoints are read-only `GET` calls.

Typical endpoints:

- `GET /api/cases` -- case identity, status, counsel of record, DOB
- `GET /api/charges` -- charge codes, offense descriptions, statutes
- `GET /api/docket-entries` -- docket text, hearing outcomes, signed orders
- `GET /api/fee-schedules` -- current fines, costs, assessments, user fees by jurisdiction
- `GET /api/payment-policies` -- installment policies, minimum/maximum bands, account-fee rules
- `GET /api/forms` -- form metadata, labels, field groups
- `GET /api/citations` -- traffic citation records
- `GET /api/financial-petitions` -- filed petitions, budget data
- `GET /api/jurisdictions` -- jurisdiction codes and names
- `GET /api/search` -- search across records

Treat portal data as the authoritative CMS record unless local hearing notes describe a more recent or more specific courtroom event.

### 3. Read and reconcile local materials against the portal

Every task supplies local payloads (hearing notes, audit memos, finance extracts, petitions, worksheets). These carry bench-level corrections and local observations that may not yet be reflected in the portal. Reconcile in this priority order:

1. **Hearing notes** -- What the judge actually said/ordered in open court. Controls plea, finding, sentence terms, departure rulings, and whether a final order was signed.
2. **Corroborating memos** -- Clerk or law-clerk research memos. Controls counsel-type corrections and identity corrections when backed by paper-packet evidence.
3. **Portal / CMS** -- Identity records (DOB, name spelling). Use for DOB verification unless the portal record is also demonstrably wrong per corroborating memo.
4. **Current fee schedule** -- Use current portal fee schedule for dollar amounts. Never carry forward stale amounts from older worksheets or archived tables unless the current schedule matches.

### 4. Resolve audit conflicts

For every conflict between sources, emit an audit finding with:

- The case number
- The issue type (identity, counsel, status, fee_schedule, departure)
- The conflicted value (what the stale record says)
- The corrected value (what should be posted)
- The resolution source (which document or lookup controls the correction)

Common conflict patterns are in [references/audit-reconciliation.md](references/audit-reconciliation.md).

### 5. Apply fee-schedule currency

Always use the current fee schedule from the portal. Replace stale amounts. See [references/payment-computation.md](references/payment-computation.md).

### 6. Exclude unsupported financial items

Do not add fees that lack direct portal or hearing-note support. Common exclusion categories: account-management, collection, late-payment, DMV, returned-check, restitution, court-appointed-attorney, court-reporter, certification, copy, traffic-school fees.

Document each exclusion with the reason. See [references/placeholder-exclusion.md](references/placeholder-exclusion.md).

### 7. Handle deferred and pending cases

A case is not ready for financial posting when:

- No final sentencing order was signed
- No plea was accepted
- The matter was continued for status

For such cases: set financial totals to 0.00, use `hold` or `do_not_post` fee status, use `deferred` or `pending` case status, and emit a `hold_unsigned_order` or `exclude_no_final_order` docket/register action.

### 8. Compute payment plans

When a payment plan is required, compute the full schedule:

1. `total_due` = fines + costs + assessments + user fees (excluding unsupported items)
2. `regular_installment_amount` = approved monthly amount
3. `full_installment_count` = floor(total_due / installment_amount)
4. `final_payment_amount` = total_due - (full_installment_count * installment_amount)
5. `total_installments` = full_installment_count + (1 if final_payment > 0 else 0)
6. `final_due_date` = first_due_date + (total_installments - 1) months

When the final payment is 0.00 (balance divides evenly), `total_installments` = `full_installment_count` and `final_payment_amount` = 0.00.

Full rules are in [references/payment-computation.md](references/payment-computation.md).

### 9. Use placeholders, never invent

When a form requires a field (SSN, driver license number, address, phone, probation officer name/office) but no case material supplies it, use the exact placeholder string `TBD from case file`. Never guess, borrow from similarly named defendants, or substitute identifiers. Document each placeholder. See [references/placeholder-exclusion.md](references/placeholder-exclusion.md).

### 10. Produce the JSON answer

Assemble the output strictly against the template. Conform to every constraint:

- **Dates**: ISO `YYYY-MM-DD`; datetimes `YYYY-MM-DDTHH:MM:SS`
- **Currency**: numbers with exactly two decimal places
- **Enums**: use exactly the enum values from the template
- **Sorting**: obey every ordering rule in the template
- **Keys**: include every required key; do not add extra keys

## Portal API Usage

All portal endpoints are read-only `GET` calls. Query parameters vary by endpoint:

- `/api/cases?case_number=XX-YY-NNNN`
- `/api/charges?case_number=XX-YY-NNNN`
- `/api/docket-entries?case_number=XX-YY-NNNN`
- `/api/fee-schedules?jurisdiction=XX-YY`
- `/api/payment-policies?jurisdiction=XX-YY`
- `/api/forms?form_id=XX_NNNN`
- `/api/citations?citation_number=XX-YY-NNNN`
- `/api/financial-petitions?petition_id=XX-YY-NNNN`
- `/api/search?q=QUERY`

When jurisdiction codes are needed, query `/api/jurisdictions` to resolve the correct code for the court named in the task.

## Reference Files

- [audit-reconciliation.md](references/audit-reconciliation.md) -- Detailed conflict patterns, resolution-source priority rules, and enum mappings across audit types.
- [payment-computation.md](references/payment-computation.md) -- Fee schedule currency rules, payment plan math, budget-support classification, installment schedule derivation, and return-to-court date computations.
- [placeholder-exclusion.md](references/placeholder-exclusion.md) -- Placeholder rules, exclusion categories, reason codes, and form-field handling when identifiers are missing.
