---
name: harborcrm-reconciliation
description: Reconcile HarborCRM API records into exact JSON outputs that match a supplied answer template. Use when a task asks for event handoffs, sponsor finance summaries, badge or campaign-member reconciliation, trade-show prospecting, import-batch cleanup, or other structured CRM analysis using HarborCRM endpoints, policies, accounts, contacts, opportunities, invoices, exhibitors, badges, or campaign members.
---

# HarborCRM Reconciliation

## Workflow

1. Read the prompt and the provided answer template first.
2. Identify the task family from the template keys, then read `references/harborcrm_patterns.md`.
3. Fetch the HarborCRM endpoints named in the prompt, plus policy data whenever qualification, suppression, or due-date rules matter.
4. Build the candidate set from the event, show, or batch records, then join CRM accounts, contacts, opportunities, campaign members, invoices, and policies as needed.
5. Apply the family-specific rules in the reference file, sort every list exactly as requested, and recompute totals from the final included rows.
6. Return one JSON object only.

## Output Discipline

- Use only fields declared by the template.
- Keep IDs, enums, booleans, nulls, and date strings exact.
- Normalize email to lowercase trimmed text and phone numbers to digits only.
- Prefer the prompt's explicit business rules over any generic fallback.
- Do not add prose, code fences, or commentary around the JSON.

## Reference

Read `references/harborcrm_patterns.md` before composing the answer. It captures the recurring HarborCRM classification, sorting, normalization, and counting rules for the staged task families.
