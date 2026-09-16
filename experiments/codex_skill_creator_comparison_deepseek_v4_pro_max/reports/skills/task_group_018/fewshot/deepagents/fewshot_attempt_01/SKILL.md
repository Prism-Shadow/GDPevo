---
name: court-clerk-closeout
description: "Complete court clerk closeout, disposition, and financial-reconciliation packet preparation for circuit and traffic courts. Reconciles hearing notes, worksheets, audit memos, petition summaries, and other local court materials against a Court Operations Portal providing cases, charges, citations, docket entries, fee schedules, payment policies, forms, financial petitions, and search endpoints. Produces structured JSON answer objects matching a supplied answer template with exact enum values, ISO dates, and two-decimal currency. Use when the task involves: (1) criminal sentencing or traffic-violation closeout packages, (2) post-disposition financial and supervision packet preparation, (3) fee reconciliation across conflicting court records, (4) payment-plan schedule computation, or (5) audit-driven register/ledger closeout with disposition-status decisions."
license: MIT
compatibility: designed for deepagents-code
---

# Court Clerk Closeout

## Overview

Produce clerk-ready closeout, disposition, and financial-reconciliation packets
by reconciling local court materials with a remote Court Operations Portal. The
common pattern: read the supplied answer template first to lock in the output
shape, then systematically reconcile every field across all local payloads and
portal records before producing a single structured JSON answer.

## Core Workflow

Follow these steps in order. Skip only when a step is genuinely inapplicable.

### 1. Lock in the answer template

The task prompt always references a local `answer_template.json`. Read it first.
It defines:

- Required top-level keys and their shapes
- Allowed enum values for every categorical field
- Ordering rules (sort keys and directions)
- Currency precision (two decimal places) and date format (ISO YYYY-MM-DD)

Do not deviate from template enum values, field names, or ordering rules. If the
template says `"no_contest"` is the enum, do not write `"no contest"` or
`"No Contest"`.

### 2. Read every local payload

Read every file under `input/payloads/`. These are hearing notes, audit memos,
worksheets, form excerpts, petition summaries, and intake sheets. They contain
ground-truth courtroom events, clerk notes, and known conflicts.

Treat each payload's conflicts and warnings as authoritative reconciliation
instructions. When a hearing note contradicts a worksheet, the hearing note
controls disposition facts. When an audit memo flags a fee as stale, the
portal's current schedule controls the amount.

### 3. Query the Court Operations Portal

The task environment provides a base URL (typically `<TASK_ENV_BASE_URL>`).
See [references/portal_api.md](references/portal_api.md) for endpoint details.

Query strategy, in order:

| Step | Endpoints | Purpose |
|------|-----------|---------|
| 1 | `GET /api/jurisdictions` | Confirm jurisdiction codes, policy references, timezones |
| 2 | `GET /api/fee-schedules` | Get current fee amounts for the target jurisdiction |
| 3 | `GET /api/payment-policies` | Get installment rules, first-due offsets, return-to-court offsets |
| 4 | `GET /api/forms` | Confirm form IDs, labels, and required fields |
| 5 | Case-specific endpoints | `/api/cases`, `/api/charges`, `/api/citations`, `/api/docket-entries`, `/api/financial-petitions` — query by case/citation number |
| 6 | `GET /api/search` | Cross-reference defendant names or case numbers when needed |

### 4. Cross-reference and reconcile

For every case or matter, compare each fact across all sources:

**Identity.** Defendant name spelling and DOB. When local materials disagree,
prefer the audit memo or CMS record over the finance queue. Prefer hearing notes
for courtroom facts. Record identity conflicts in audit findings.

**Counsel.** Who represented the defendant. Decode abbreviations: "PD" means
public defender. "APD" may mean "appointed private defense," not "assistant
public defender" — verify from the hearing record or audit memo. When the judge
or audit memo clarifies counsel type, that overrides worksheet labels.

**Status.** Is the case disposed, deferred, pending, or continued? An unsigned
order, a continued hearing, or a draft worksheet means the case is not disposed.
Exclude it from financial posting and mark it as hold or exclude.

**Charges.** What was the conviction offense? If a charge was amended (e.g.,
controlled-substance amended to misdemeanor theft), the conviction is the
amended charge. Dismissed or amended-away counts must be tracked separately from
convicted counts.

**Departures.** Did the judge pronounce a departure? If the judge called the
sentence "top of the range" or "not a departure," record `no_departure`
regardless of worksheet labels. For misdemeanors where departure analysis is
not applicable, use `not_evaluated_misdemeanor`. For pending cases with no
disposition, use `not_entered_pending`.

### 5. Compute financial entries

See [references/fee_reconciliation.md](references/fee_reconciliation.md) for
detailed rules. Core principles:

- Use the **current** fee schedule: filter portal results to items where
  `effective_date` ≤ disposition date and (`end_date` is null or `end_date` ≥
  disposition date).
- Apply **mandatory** fees for the conviction charge type (court costs always;
  drug assessment or lab fee for controlled-substance convictions).
- Apply **conditional** fees only when the condition is met (public defender
  user fee only when counsel is actually a public defender).
- **Do not add** account-management, late-payment, collection, DMV,
  returned-check, copy, certification, or restitution fees unless the court
  order or current policy explicitly supports them.

### 6. Handle payment plans

When the task includes payment plan or installment order computation, use
`scripts/payment_calc.py` for deterministic schedule math:

```
python3 scripts/payment_calc.py <total_due> <monthly_amount> <first_due_date>
```

The script computes full-payment count, final payment amount, total
installments, and final due date. See [scripts/payment_calc.py](scripts/payment_calc.py).

Key rules:
- Down payment is $0.00 unless the order specifies one.
- First due date comes from the petition/order, or compute from policy
  `first_due_days` after the petition/submission date.
- Return-to-court date = final due date + policy `return_to_court_offset_days`.
- Monthly amount must fit within the policy band (`min_monthly` ≤ amount ≤
  `max_monthly`) and be affordable from disposable income.
- Restitution priority: when policy says "restitution before fines and costs,"
  apply payments to restitution first. Mark `payment_application_order`
  accordingly.

### 7. Identify exclusions

Every template has a section for items excluded from the starting balance or
register:

- **Stale fees:** Old-schedule amounts superseded by current schedules.
- **Unsupported charges:** Fees not ordered by the court and not mandated by
  current policy (account-management, late, collection, DMV, returned-check,
  traffic-school).
- **Pending/continued cases:** Cases without a signed final order. Exclude from
  financial posting, note the next status date.
- **Not-in-hearing-order items:** Fees on worksheets or sticky notes that the
  judge did not pronounce.

### 8. Assemble the final JSON

Produce a single JSON object. Follow these rules exactly:

- Sort every array according to the ordering rules in the answer template.
- Use ISO YYYY-MM-DD for dates, ISO YYYY-MM-DDTHH:MM:SS for datetimes.
- All currency values are numbers rounded to two decimal places (e.g., `150.00`,
  not `150` or `"150.00"`).
- Use exactly the enum strings from the template. No prose substitutions, no
  title-casing.
- For fields that genuinely cannot be completed from available materials, use
  the placeholder `"TBD from case file"`. Never invent values.
- Null fields stay JSON `null`, not the string `"null"`.
- Do not wrap the JSON in markdown code fences unless the task prompt explicitly
  requests markdown.

## Placeholder Discipline

When a form field is required but the value is absent from all case materials
(SSN, driver license number, address, phone, probation officer name, probation
office location), use the exact string `"TBD from case file"`. Never guess,
borrow from similar cases, or use a generic "Unknown" label.

## Payment Application Order

When a payment plan includes both restitution and fines/costs:

- If jurisdiction policy says "restitution before fines and costs," set
  `payment_application_order` to `"restitution_before_fines_costs"` and compute
  the schedule against the combined balance.
- If no restitution is owed, use `"fines_costs_only"`.

## License Suspension Dates

License suspension effective date is the conviction date (not the release date),
unless the task materials explicitly state otherwise. The end date is computed
by adding the suspension months to the start date.

## Resources

- [references/portal_api.md](references/portal_api.md) — Portal endpoint reference
- [references/fee_reconciliation.md](references/fee_reconciliation.md) — Fee reconciliation rules
- [scripts/payment_calc.py](scripts/payment_calc.py) — Payment schedule computation
