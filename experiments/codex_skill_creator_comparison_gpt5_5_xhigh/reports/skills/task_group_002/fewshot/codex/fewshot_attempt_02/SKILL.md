---
name: medbridge-sales-ops
description: Solve MedBridge Sales Ops API tasks that require account-ready JSON for quotes, RFQs, freight decisions, opportunities, invoices, payments, revenue journals, events, and vouchers. Use when the prompt asks Codex to query a shared MedBridge Sales Ops task API and return JSON matching an answer_template.json.
---

# MedBridge Sales Ops

## Core Workflow

1. Read the user prompt and the local `input/payloads/answer_template.json` before querying records. Treat the template as the required output contract, including field names, array shapes, enum strings, number/date formats, and nullable fields.
2. Resolve the API base URL from the prompt, runner instructions, or environment access file. Use only the provided MedBridge Sales Ops API and its documented GET endpoints.
3. Extract every stable identifier and exact business name from the prompt: customer IDs, quote IDs, RFQ IDs, opportunity IDs, product codes, event IDs, voucher codes, contacts, dates, and quantities.
4. Query the API with those identifiers. Prefer direct endpoints for known IDs, use `/api/search?q=...` for names and relationship discovery, and fetch full records before deriving final values.
5. Cross-check relationships across records. Do not trust a matching name or search hit unless the customer, opportunity, quote/RFQ, product, milestone, event, or voucher linkage agrees with the prompt and related records.
6. Load [references/answering-rules.md](references/answering-rules.md) for pricing, freight, milestone, revenue-recognition, event, voucher, and action-routing rules.
7. Produce only valid JSON matching the template. Do not include markdown, commentary, extra keys, or omitted required keys.

## API Helper

Use [scripts/medbridge_api.py](scripts/medbridge_api.py) to gather records repeatably:

```bash
python scripts/medbridge_api.py "$BASE_URL" --api
python scripts/medbridge_api.py "$BASE_URL" --search "customer or record id"
python scripts/medbridge_api.py "$BASE_URL" --get quotes "QUOTE_ID" --get customers "CUSTOMER_ID"
python scripts/medbridge_api.py "$BASE_URL" --list freight-quotes --list policies
```

The helper prints one JSON object containing every requested API response. Inspect the returned fields and relationships, then perform the business calculations yourself.

## Output Discipline

- Clone template array objects when the API contains multiple applicable line items, freight options, milestones, or tasks.
- Preserve the template's field names and controlled values exactly. If a field's placeholder describes a type rather than a literal value, replace it with the derived value of that type.
- Use numeric JSON values for money and quantities, not strings. Round currency calculations to cents when the template asks for cent-level values.
- Use ISO `YYYY-MM-DD` dates. Use the quote date or as-of date from the prompt when evaluating freight validity, receivables, and due-date actions.
- Leave a field `null` only when the template allows null or the underlying business value is genuinely absent.
- Before final response, parse the JSON mentally or with a local parser and compare every top-level and nested key against `answer_template.json`.
