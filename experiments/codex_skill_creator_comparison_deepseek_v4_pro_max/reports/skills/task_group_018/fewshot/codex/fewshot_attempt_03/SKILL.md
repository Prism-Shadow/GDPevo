---
name: court-clerk-reconciliation
description: Reconcile court clerk closeout packets, post-sentencing field packets, and disposition batches by cross-checking local case materials against a Court Operations Portal REST API. Use when Codex needs to help a deputy court clerk prepare a reconciled JSON answer from an answer template, hearing notes, audit memos, finance extracts, petition summaries, and portal records for criminal, traffic, or post-disposition matters that involve audit-finding resolution, identity/counsel verification, fee-schedule reconciliation, docket-register entries, payment-plan math, probation referrals, license orders, excluded charges, and placeholder handling for missing identifiers.
---

# Court Clerk Reconciliation

## Workflow

1. **Read the answer template** (`answer_template.json`) — it defines the exact output schema, required keys, enums, ordering rules, and field rules (currency precision, date format).

2. **Read all local payloads** — hearing notes, audit memos, finance extracts, form excerpts, petition summaries, sentencing notes, worksheets, etc.

3. **Query the Court Operations Portal** at `<TASK_ENV_BASE_URL>` for every relevant endpoint. See [references/api.md](references/api.md) for complete endpoint documentation and schemas. Query by case number, jurisdiction code, or citation number as the task demands. Always fetch:
   - `/api/cases` — for defendant identity, counsel type, status
   - `/api/charges` — for offense codes, pleas, dispositions, sentences
   - `/api/fee-schedules` — for current mandatory fees
   - `/api/payment-policies` — for installment plan parameters
   - `/api/forms` — for form IDs, labels, and placeholder instructions
   - Any other endpoints the task mentions (docket-entries, citations, financial-petitions, jurisdictions, search)

4. **Reconcile conflicts** using the hierarchy in [references/rules.md](references/rules.md). The general priority: portal CMS record > hearing notes > corroborating memo > fee schedule > hold unsigned. Every conflict becomes an audit finding with a resolution source.

5. **Build the answer JSON** matching the answer template exactly — use only its enums, fill every required key, and respect ordering rules, currency precision (two decimal places), and ISO date format.

6. **Validate** before finalizing: no invented identifiers (use `TBD from case file`), no unsupported fees, totals sum correctly across posted cases only.

## Key Principles

- **Never invent identifiers, contact details, or fee amounts.** Use `TBD from case file` for genuinely missing fields (SSN, DL#, address, phone, probation officer/office).
- **Fee schedules effective on the disposition date control.** Stale schedules are audit findings, not current amounts.
- **Public defender user fees apply only when counsel type is `public_defender`.** Appointed private counsel (`appointed_private`) do not trigger PD fees.
- **Unsigned orders → hold.** Do not post financial entries for cases without a signed disposition order.
- **Exclude unsupported charges explicitly.** Account-management fees, collection fees, DMV fees, late fees, returned-check fees, traffic-school fees, and restitution are excluded unless the portal policy or court order directly supports them.

## Resources

- [references/api.md](references/api.md) — Full Court Operations Portal API documentation with endpoint schemas
- [references/rules.md](references/rules.md) — Reconciliation rules, resolution hierarchy, payment-plan math, and fee/total computation patterns
