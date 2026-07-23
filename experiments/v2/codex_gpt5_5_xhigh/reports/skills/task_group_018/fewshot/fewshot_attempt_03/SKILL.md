---
name: court-packet-assembler
description: Assemble court closeout and sentencing packet JSON from staged hearing notes, petitions, worksheets, form excerpts, templates, and Court Operations Portal records. Use when a task provides an answer template plus local payloads and asks for reconciled dispositions, fee tables, payment plans, probation or license orders, placeholders, exclusions, or register totals.
---

# Court Packet Assembler

Use this skill for staged court packet tasks where the answer must be a single JSON object matching `answer_template.json`.

## Workflow

1. Read `prompt.txt`, every file under `payloads/`, and `answer_template.json` first.
2. Read `environment_access.md` for the portal base URL. Query only the listed endpoints the packet needs, usually jurisdictions, cases or citations, charges, docket-entries, fee-schedules, payment-policies, forms, financial-petitions, and search.
3. Treat signed orders, hearing notes, portal records, and current fee or policy data as authoritative. Treat worksheets, queue extracts, draft forms, stale memos, and older revisions as conflict sources to reconcile, not as final truth.
4. Follow the template exactly: required keys, nesting, enum values, ordering rules, date formats, currency precision, and `null` handling. Return JSON only.
5. Surface every material conflict in the designated audit, exclusion, or placeholder section. Do not silently merge contradictory facts.
6. Use the exact placeholder the packet requires, usually `TBD from case file`, for missing identifiers, addresses, phone numbers, license numbers, officer details, or similar required form fields.
7. Exclude fees, charges, or matters unless a current order, current schedule, or current policy supports them. Keep pending or unsigned matters out of posted financial totals.
8. Compute payment-plan schedules from the approved balance and installment amount, including any final remainder installment and any required return-to-court date.
9. Sort arrays and totals exactly as the template instructs.

## Packet Shapes

- Build `audit_findings` / `case_dispositions` / `fee_reconciliation` / `docket_entries` / `register_totals` for disposition closeouts.
- Build `matters` / `excluded_charges` / `batch_totals` for citation payment-plan closeouts.
- Build `case_memo` / `cc1375` / `cc1379` / `budget_review` / `placeholder_fields` / `excluded_financial_items` for post-sentencing packets.
- Build `petitions` / `probation_referrals` / `license_orders` / `placeholder_cases` for petition-and-supervision packets.
