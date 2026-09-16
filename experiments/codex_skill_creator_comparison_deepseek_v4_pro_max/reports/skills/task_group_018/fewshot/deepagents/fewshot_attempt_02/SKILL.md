---
name: court-clerk-reconciliation
description: "Court clerk reconciliation of local case materials (hearing notes, audit memos, finance extracts, petition summaries) against a Court Operations Portal REST API. Produces structured JSON closeout packets matching supplied answer templates. Use when the task involves: (1) sentencing or disposition closeout for a batch of criminal or traffic cases, (2) post-sentencing field packets with probation referrals and installment orders, (3) post-disposition financial and supervision packets, (4) reconciling conflicting identity, counsel, fee-schedule, or departure records between local materials and a portal, (5) constructing payment-plan schedules from portal policy bands and petitioner budgets, (6) identifying unsupported fees to exclude from financial entries, or (7) filling structured JSON answer templates with enumerated field values."
license: MIT
compatibility: designed for deepagents-code
---

# Court Clerk Reconciliation

## Overview

Reconcile local court case materials against a Court Operations Portal REST API to produce structured JSON closeout, field-packet, or register answers. The portal provides read-only GET endpoints for cases, charges, citations, docket entries, fee schedules, payment policies, forms, financial petitions, jurisdictions, and search.

## Workflow

1. Parse the task prompt for: target cases/citations, the answer template path, available portal endpoints, and the payloads directory.
2. Read the answer template JSON from the payloads directory first. It defines the required output shape, enum values, field types, and ordering rules.
3. Read all local payloads (hearing notes, audit memos, finance extracts, petition summaries, form excerpts, worksheets).
4. For each target case or citation, query the relevant portal endpoints. See [portal_api.md](references/portal_api.md) for endpoint details and query patterns.
5. Reconcile conflicts following the rules in [reconciliation_patterns.md](references/reconciliation_patterns.md).
6. Fill the JSON answer template with reconciled values. Follow all enum values, ordering rules, currency precision (two decimal places), ISO date formats, and placeholder rules from the template and reconciliation patterns.
7. Return only the completed JSON object. Do not include markdown fences or commentary unless the template explicitly requires a task_id or similar wrapper key.

## Querying the Portal

The portal base URL is given in the task prompt as `<TASK_ENV_BASE_URL>`. All endpoints are unauthenticated GET. Query each target case or citation across the relevant endpoints. Combine portal records with local payloads: local materials control courtroom events the portal may not yet reflect; the portal controls current fee schedule amounts, form metadata, and payment policy parameters.

Full endpoint reference: [portal_api.md](references/portal_api.md)

## Reconciliation Rules

Detailed rules for audit conflicts, fee reconciliation, payment plan construction, placeholder handling, and case status decisions are in [reconciliation_patterns.md](references/reconciliation_patterns.md). Key principles:

- **Identity conflicts**: Use the portal CMS record for DOB and name corrections unless the local hearing note or corroborating memo provides a definitive correction. When a DOB is genuinely missing from all sources, use `"TBD from case file"`.
- **Counsel conflicts**: Treat "APD" abbreviations and "PD" labels as tentative. When a corroborating memo or judge's on-record statement confirms appointed private counsel, classify as `appointed_private`. Public defender fee eligibility depends on actual counsel classification, not the label.
- **Fee schedule staleness**: When a local worksheet carries an older dollar amount (e.g., drug assessment 125 vs. current 250), replace it with the current portal fee schedule amount. Never carry forward archived amounts.
- **Departure conflicts**: When a legacy worksheet shows a departure but the hearing notes confirm the judge said no departure, the hearing notes control. Use `no_departure`.
- **Unsigned orders**: When the docket note or hearing record states no final order was signed, set status to `deferred`/`pending`, do not post financial entries, and use a disposition-hold docket entry.
- **Unsupported fees**: Exclude account-management, collection, DMV, late-payment, returned-check, traffic-school, and restitution fees unless the portal payment policy or a specific court order directly supports them. Set excluded amounts to 0.00.
- **Placeholders**: For missing identifiers (SSN, driver license number, addresses, phone numbers) and missing contact/office details (probation officer name, probation office location), use exactly `"TBD from case file"`. Never invent values.
- **Payment plans**: Use the portal payment policy for minimum/maximum monthly bands. Compute installment count as `floor(total_due / monthly_amount)`, with a final payment for the remainder. Sort petitions and referrals as directed by the answer template.

## Common Answer Template Shapes

The answer template JSON in the payloads directory defines the exact output shape. Common top-level keys include:

- **audit_findings**: Array of conflict resolutions (case_number, issue_type, conflicted_value, corrected_value, resolution_source).
- **case_dispositions / dispositions**: Array of per-case disposition records with charge summaries, plea, status, and closeout actions.
- **fee_reconciliation / fee_entries**: Array of per-case financial entries with fee items/line items and case totals.
- **docket_entries / docket_register**: Array of per-case docket actions with entry types, codes, and financial totals, plus batch register totals.
- **matters**: Array of per-citation records with disposition, financial entry, payment plan, and form-entry sub-objects.
- **case_memo / cc1375 / cc1379**: Case-management memo fields, probation referral fields, and license-suspension/installment-order fields for post-sentencing packets.
- **petitions / probation_referrals / license_orders**: Financial petition reconciliation and supervision packet sections.
- **excluded_charges / excluded_financial_items / exclusions**: Arrays of charges, fees, or cases excluded from the current posting.
- **placeholder_fields / placeholder_cases**: Arrays of fields or cases that require `"TBD from case file"` values.
- **register_totals / batch_totals**: Aggregate financial and count totals for the batch.

The template also defines enums, ordering rules, required keys, and field types. Follow them exactly.

## Resources

This skill includes reference documentation:

- [portal_api.md](references/portal_api.md): Complete API endpoint reference and query patterns.
- [reconciliation_patterns.md](references/reconciliation_patterns.md): Detailed rules for identity, counsel, fee, departure, status, and payment-plan reconciliation.
