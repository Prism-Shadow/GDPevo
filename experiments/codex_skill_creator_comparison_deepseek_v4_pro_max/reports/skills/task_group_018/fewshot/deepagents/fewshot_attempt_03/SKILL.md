---
name: court-clerk-reconciliation
description: "Court-clerk reconciliation and financial closeout workflow for criminal, traffic, and post-sentencing dockets. Use when a deputy clerk task requires: (1) cross-referencing local hearing notes, audit memos, finance worksheets, petition summaries, or form excerpts against a Court Operations Portal REST API, (2) resolving identity/counsel/fee/status/departure conflicts across conflicting sources, (3) computing per-case financial totals (fines, costs, assessments, user fees, surcharges), (4) structuring approved post-disposition payment plans with installment math, (5) preparing CC-1375 probation referrals, CC-1379 license-suspension/installment orders, or local payment-plan forms, (6) identifying unsupported or stale charges for exclusion, or (7) assembling docket-register entries with batch totals from a multi-case closeout batch."
license: MIT
compatibility: designed for deepagents-code
---

# Court Clerk Reconciliation

## Overview

Produce structured JSON closeout packets by reconciling local case materials against a Court Operations Portal. Follow a fixed reconciliation hierarchy, use the portal to verify records against current schedules and policies, compute financial totals and payment plans, and flag all unsupported charges for exclusion.

## Core Workflow

1. Read every local payload file and the answer template.
2. Query the portal for each target case, its charges, fee schedules, payment policies, forms, and any jurisdiction/citation/docket records needed to fill the template.
3. Apply the reconciliation hierarchy (see [reconciliation-rules.md](references/reconciliation-rules.md)).
4. Compute case-level financials, payment plans, and register totals. Apply exclusion rules for unsupported charges (see [fee-rules.md](references/fee-rules.md)).
5. Map form fields and use the exact placeholder `"TBD from case file"` for any required field the available materials cannot fill (see [forms-reference.md](references/forms-reference.md)).
6. Assemble the answer object sorted by case/citation number ascending, with ISO dates and currency to two decimal places. Use only the enum values declared in the answer template.

## Reconciliation Hierarchy

When sources conflict, resolve by this priority chain (highest to lowest):

1. **Courtroom hearing notes / bench statements** — judge's oral pronouncements override draft worksheets, legacy screens, and finance queue extracts on disposition, departure status, plea, and sentence terms.
2. **Clerk audit/corroboration memos** — override finance queue records on identity (name spelling, DOB) and counsel classification (appointed-private vs. public defender).
3. **Current portal records** (CMS, fee schedules, payment policies, forms) — override stale or archived amounts, obsolete fee codes, and local worksheet figures.
4. **Docket entries / minute notes** — when a final signed order is missing, the case stays deferred/excluded regardless of what a draft worksheet says.
5. **Finance queue extracts** — lowest authority; use only when no higher source conflicts.

For details and example patterns, see [reconciliation-rules.md](references/reconciliation-rules.md).

## Portal Query Strategy

Query the portal endpoints listed in the task prompt. Typical patterns:

- `GET /api/cases?case_number=X` or `/api/citations?citation_number=Y` for case identity, status, and party records.
- `GET /api/charges?case_number=X` for offense codes, plea, and charge disposition.
- `GET /api/docket-entries?case_number=X` for signed orders and entry history.
- `GET /api/fee-schedules?jurisdiction=Z` for current fee amounts.
- `GET /api/payment-policies?jurisdiction=Z` for installment rules, account-fee treatment, payment application order.
- `GET /api/forms?form_id=F` for form metadata and field requirements.
- `GET /api/financial-petitions?petition_id=P` when a payment petition is in play.
- `GET /api/search?q=term` for cross-reference lookups.

See [portal-query-patterns.md](references/portal-query-patterns.md) for complete query patterns for each docket type.

## Financial Calculation Rules

Every fee posted to a case must be supported by the current fee schedule, the judge's order, or the active payment policy. Do not carry forward fees from stale schedules or draft worksheets. Detailed rules and payment-plan math are in [fee-rules.md](references/fee-rules.md).

Core principles:

- Court costs are jurisdiction-specific flat amounts (verify from the portal fee schedule; do not assume a fixed number).
- Fines are taken from the sentencing pronouncement or the active fee schedule for traffic violations.
- Drug/crime-lab assessments must be verified against the current schedule.
- Public-defender user fees post only when counsel is classified as public defender, not appointed-private.
- Exclude account-management fees, collection fees, late fees, DMV notice fees, returned-check fees, restitution, and copy/certification fees unless directly supported by the current policy or judge's order.
- For traffic-violation matters, exclude stale schedule amounts and statutory-maximum substitutions when the current schedule provides a specific tier.

## Payment Plan Math

For installment agreements, compute the schedule from the total due and the approved monthly amount:

- `total_installments = ceil(total_due / monthly_payment)`
- `full_payment_count = floor(total_due / monthly_payment)`
- `final_payment_amount = total_due - (full_payment_count * monthly_payment)`
- `final_due_date` advances from `first_due_date` by `(total_installments - 1)` months.
- `return_to_court_date` is typically 60 days after `final_due_date`.

When a petition includes a budget: disposable income = monthly_income - total_monthly_obligations. If the requested installment is within the policy band and does not exceed disposable income, classify as `supportable` or `supported_by_budget`.

## Placeholder Convention

For any required template or form field that cannot be completed from the portal, case file, or local materials, use the exact string `"TBD from case file"`. Never invent names, identifiers, addresses, phone numbers, license numbers, probation-officer names, or office locations. See [forms-reference.md](references/forms-reference.md) for a complete field mapping.

## Answer Assembly

- Sort all lists by case_number or citation_number ascending, unless the template specifies a different order.
- Use ISO YYYY-MM-DD dates and YYYY-MM-DDTHH:MM:SS datetimes.
- All currency values are numeric and rounded to two decimal places.
- Use enum string values exactly as declared in the answer template; do not replace them with narrative prose.
- Return a single JSON object matching the template structure. Do not wrap in markdown code fences unless the task prompt explicitly asks for them.
