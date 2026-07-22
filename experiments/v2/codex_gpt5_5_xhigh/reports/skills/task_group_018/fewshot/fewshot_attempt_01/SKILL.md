---
name: reconcile-court-closeout
description: Reconcile court closeout and post-sentencing packet tasks from hearing notes, clerk memos, worksheets, intake packets, and Court Operations Portal data. Use when the work asks for schema-driven JSON outputs covering dispositions, fee reconciliation, payment plans, probation referrals, license-suspension orders, docket/register entries, or exclusion of stale or unsupported charges.
---

# Court Closeout Reconciler

## Workflow

1. Read the prompt, answer template, and every payload completely before deciding anything.
2. Inventory the required top-level keys, enums, sort rules, and precision rules from the template first.
3. Read `environment_access.md` for the running base URL, then use only the portal endpoints the prompt calls for.
4. Use portal lookups to verify the live record set:
   - `/api/jurisdictions` and `/api/citations` for citation-based tasks, court codes, and defendant/violation lookups
   - `/api/cases`, `/api/charges`, `/api/docket-entries` for identity, status, plea, and disposition facts
   - `/api/fee-schedules` and `/api/payment-policies` for current financial rules
   - `/api/forms` for form IDs, labels, and required fields
   - `/api/financial-petitions` for petition intake and budget math
   - `/api/search` when a fact is split across notes, templates, or portal records
5. Resolve conflicts using the most authoritative source available:
   - signed order or explicit hearing record
   - corroborating memo or form excerpt
   - current portal record, schedule, or policy
   - draft worksheet, queue extract, or archived carry-forward value
6. Build the JSON exactly to the template:
   - use required keys only
   - keep enum spellings exact
   - use ISO dates and money rounded to two decimals
   - sort arrays and subarrays exactly as instructed
   - preserve required placeholders verbatim when the file says to use them
7. Recompute totals from included items only.
   - round after summing
   - exclude unsupported, stale, or not-yet-triggered fees
   - hold pending or unsigned matters out of posted registers and financial entries
8. Return JSON only.

## Common Rules

- Treat the template as the contract; do not assume one fixed schema across tasks.
- Do not invent identifiers, contact details, or other missing case-file data.
- If a template provides an exclusion list, use it for disallowed amounts instead of inflating the balance.
- If a current fee schedule conflicts with an archived worksheet amount, use the current schedule.
- If a disposition is not final, do not post it as disposed.

## Sanity Check

- Every required key is present.
- Every ordered list is sorted correctly.
- Every total matches the line items that remain after exclusions.
- Every placeholder is either the template's required placeholder or omitted when the schema allows omission.
