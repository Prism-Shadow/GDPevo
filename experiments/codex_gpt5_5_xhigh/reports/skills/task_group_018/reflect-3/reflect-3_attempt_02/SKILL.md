---
name: court-closeout-reconciliation
description: Reconcile court hearing notes, portal records, fee schedules, payment policies, and form metadata into strict JSON closeout packets for criminal, traffic, probation, and payment-plan tasks. Use when a task asks to resolve conflicting court data, compute fees or totals, hold unfinalized matters, and fill a schema-driven answer template.
---

# Court Closeout Reconciliation

Use this workflow whenever a task asks for a structured court closeout, payment-plan packet, probation packet, or sentencing reconciliation.

## Workflow

1. Read the prompt, answer template, and all attached local payloads.
2. Pull the portal records needed to verify identity, status, charges, docket text, fees, policies, petitions, and form fields.
3. Resolve conflicts in this order:
   - signed order, hearing notes, and docket text
   - current portal case, citation, charge, and docket records
   - current fee schedule, payment policy, and form metadata
   - queue, worksheet, draft, or stale carry-forward values
4. Keep only values supported by the controlling source. Do not guess names, contact details, account numbers, license numbers, or fees.
5. Recompute money from the supported record and current policy. Exclude stale, unsupported, or barred charges.
6. For matters that are held, deferred, continued, or unsigned, do not post them to the register totals. Keep the status or hold fields the schema asks for and leave posted totals at zero.
7. Format exactly to the template:
   - ISO dates
   - currency to two decimals
   - exact enum values
   - required sort order
8. Preserve required placeholders exactly as provided when a field cannot be completed from the case file.

## Common Checks

- Use current fee schedules, not archived worksheet amounts.
- Apply counsel-based fee rules exactly as the schedule or policy says.
- For traffic payment plans, use the citation number as the account reference when no separate account exists and the form allows it.
- Keep unsupported add-ons out of the starting balance and out of posted totals.
- Return JSON only.
