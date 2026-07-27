---
name: court-closeout-reconciliation
description: Reconcile court closeout packets, sentencing or traffic disposition batches, payment-plan orders, and post-sentencing form packets by cross-checking hearing notes, worksheets, petitions, fee schedules, docket entries, and portal form metadata. Use when a prompt asks for a strict JSON answer, corrected disposition or status, fee or payment-plan math, register totals, placeholder handling, or form completion from a court operations portal.
---

# Court Closeout Reconciliation

Read the prompt, answer template, and every attached payload first. Identify the controlling matter type and schema before querying the portal.

## Workflow

1. Read all local evidence.
2. Query only the portal endpoints named in the prompt that matter for the task: cases or citations, charges, docket entries, fee schedules, payment policies, forms, financial petitions, jurisdictions, and search.
3. Reconcile conflicts by source precedence:
   - signed order, hearing notes, sentencing intake, or final courtroom minute
   - portal case, charge, docket, policy, fee, petition, and form metadata
   - clerk memos, petitions, worksheets, queue extracts, or archived figures
4. Treat stale worksheet numbers, draft forms, and carry-forward values as provisional.
5. Post only what the final record supports. Exclude continued, unsigned, deferred, or otherwise nonfinal matters from registers or financial entries unless the template explicitly asks for a hold or pending row.

## Reconciliation Rules

- Use the actual identity in the controlling record. Do not copy DOBs or names from similar cases.
- Classify counsel by actual representation status, not by initials, abbreviations, or queue labels.
- Verify current fee schedules and payment policies before carrying forward any charge that looks stale, archived, or memo-only.
- Omit unsupported add-on charges, especially account-management, collection, late, DMV, restitution, copy, certification, or similar fees, unless the current policy or final order authorizes them.
- Use the exact placeholder required by the materials for missing identifiers or contact fields. Do not invent substitutes.
- For local forms, prefer current portal form metadata and copy the field labels exactly.
- If no separate account number exists, use the citation number or case number as the account reference when the form or local excerpt says to do so.
- For approved payment plans, calculate installments from the supported balance, honor the approved first due date, and make the last installment the remainder when the balance does not divide evenly.
- Keep disputed departures, dismissals, amended-away counts, and pending matters separate from final convictions and posted financials.

## Output Discipline

- Match the template exactly.
- Preserve required key order, enum values, sorting rules, and null handling.
- Use ISO dates and round money to two decimals.
- Return JSON only. Do not add markdown, prose, or commentary.
