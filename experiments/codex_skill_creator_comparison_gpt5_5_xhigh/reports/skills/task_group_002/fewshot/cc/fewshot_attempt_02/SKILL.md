---
name: medbridge-sales-ops-json
description: Use this skill whenever a task asks for MedBridge Sales Ops API work, account-ready quote packages, RFQ pricing, freight comparisons, invoice/payment/revenue reconciliation, event or voucher follow-up routing, or any response that must match an answer_template.json from the task payload. It is especially relevant when the prompt mentions a shared task environment base URL, Sales Ops API records, JSON-only output, quote/RFQ IDs, opportunity IDs, milestone invoices, freight quotes, policies, or CRM/accounting follow-ups.
---

# MedBridge Sales Ops JSON

Use this skill to turn MedBridge Sales Ops API records into the exact JSON object requested by the current task template. The API data, prompt, and `input/payloads/answer_template.json` are the sources of truth. Do not reuse values from prior examples; derive every customer, amount, date, ID, status, and action from the current prompt and API records.

## Required Workflow

1. Read the user prompt and `input/payloads/answer_template.json`.
2. Resolve the API base URL from the prompt, runner context, or environment variable. Normalize it by removing a trailing slash before appending paths.
3. Fetch `GET /api` to confirm the service is reachable.
4. Retrieve records by explicit IDs from the prompt, then use `GET /api/search?q=<id-or-name>` to find linked records.
5. Read [references/medbridge-workflows.md](references/medbridge-workflows.md) before deriving values. It contains the quote, RFQ, freight, policy, and reconciliation rules.
6. Populate only the keys present in the current answer template. Preserve the template's nesting, array names, controlled enum labels, and date/number formatting expectations.
7. Validate the output as JSON and compare its shape to the template. You may run:

```bash
python <skill-root>/scripts/check_answer_shape.py input/payloads/answer_template.json /tmp/answer.json
```

8. Return only the final JSON. Do not include markdown, citations, notes, or explanatory text.

## Retrieval Rules

- Prefer direct endpoints for known IDs: `/customers/{id}`, `/products/{code}`, `/rfqs/{id}`, `/quotes/{id}`, `/opportunities/{id}`, `/events/{id}`, and `/vouchers/{code}`.
- Use `/api/search?q=<quote_id>` to discover freight quotes linked to a quote.
- Use `/api/search?q=<opportunity_id>` to discover linked invoices, payments, revenue journals, events, and vouchers.
- Fetch `/policies` when payment terms, quote validity, EXW scope, freight reconfirmation, module granularity, or revenue recognition rules are needed.
- Treat search results as candidates, not final facts. Filter out distractor or stale benchmark records unless the current template asks you to report them as current risks.

## Output Discipline

- Keep IDs stable and exact.
- Use ISO `YYYY-MM-DD` dates.
- Use money as numeric JSON values, not strings.
- Preserve cents where the template calls for two decimals, but do not quote numbers.
- Convert API statuses to the exact template enums, usually uppercase snake case.
- Keep arrays in the business order implied by the template: RFQ line order, freight mode comparison order, or milestone phase order.
- When a required value is unavailable after checking the relevant records, use the template's null or unknown-style enum if one is offered; otherwise leave a defensible empty string only if the template itself uses empty placeholders.
