---
name: medbridge-sales-ops-json
description: Solve MedBridge Sales Ops API tasks that require account-ready JSON for quote/RFQ pricing, freight decisions, opportunity reconciliation, invoice/payment/revenue-recognition status, and event or voucher follow-up actions using a provided answer template.
---

# MedBridge Sales Ops JSON

Use this skill when a task asks for a MedBridge Sales Ops API response and a final JSON object matching `input/payloads/answer_template.json`.

## Workflow

1. Read the user prompt and the local `input/payloads/answer_template.json`.
2. Extract requested record identifiers, named customer/contact, quote or as-of date, product codes, quantities, event IDs, voucher codes, and any explicit output constraints.
3. Query the runner-provided API base URL. If useful, use `scripts/medbridge_fetch.py` to fetch records by ID, product code, voucher code, collection, or search term.
4. Read `references/medbridge_rules.md` before deriving totals, status flags, recommended transport modes, reconciliation state, or action values.
5. Produce only valid JSON matching the template. Preserve the template's object shape and controlled enum values; expand placeholder arrays when the API shows multiple applicable records.

## API Use

- Treat the live API as the source of truth for customers, products, RFQs, quotes, freight quotes, policies, opportunities, invoices, payments, revenue journals, events, and vouchers.
- Use `/api` or `/api/search` to discover links when direct IDs are not enough.
- Fetch direct records first, then fetch linked or filtered collections needed to confirm totals and relationships.
- Do not answer from examples or memory; use examples only as reusable patterns for calculations and output discipline.

## Output Discipline

- Return JSON only, with no Markdown fence or explanatory prose.
- Keep string, number, boolean, array, null, and date types consistent with the template.
- Use ISO `YYYY-MM-DD` dates. Use numeric money values, rounding to cents when the template requires two decimals.
- Do not include task-specific values from this skill package. Every final value must come from the current prompt, current template, current API records, or deterministic calculations from those records.
