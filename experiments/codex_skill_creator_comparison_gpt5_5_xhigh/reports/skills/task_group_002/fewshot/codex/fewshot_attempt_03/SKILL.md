---
name: medbridge-sales-ops
description: Prepare MedBridge Sales Ops quote, freight, RFQ module, and account reconciliation JSON using the task environment API. Use when the prompt mentions the MedBridge Sales Ops API, quote or RFQ decision packages, EXW pricing, freight comparison, catalog tiers, policies, opportunity milestones, invoices, payments, revenue journals, events, vouchers, or an answer_template JSON.
---

# MedBridge Sales Ops

## Workflow

1. Read the user prompt and `input/payloads/answer_template.json` first. The final response must be valid JSON only and must match the template's keys, nesting, array expansion pattern, enum values, date format, and number style.
2. Get the task API base URL from the runner or from `environment_access.md` in the task workspace. Do not hardcode a training URL into the answer.
3. Query the API before calculating. Use exact IDs from the prompt when present; otherwise use `/api/search?q=<text>` and then verify by customer, product, opportunity, quote/RFQ date, status, and linked record IDs.
4. Use the API records as the source of truth over prompt prose when names or old quantities conflict. Treat prompt quantities, dates, event IDs, voucher codes, and contact names as constraints to verify against API records.
5. For quote, RFQ, freight, policy, invoice, payment, revenue, event, and voucher calculations, follow [decision_rules.md](references/decision_rules.md).
6. Return only the completed JSON object. Do not include markdown, citations, comments, or explanation outside the JSON.

## API Collection Helper

Use the helper when it is faster than manual `curl` calls:

```bash
python skill/scripts/collect_medbridge_records.py --base-url "$BASE_URL" --quote-id "<quote_id>"
python skill/scripts/collect_medbridge_records.py --base-url "$BASE_URL" --rfq-id "<rfq_id>"
python skill/scripts/collect_medbridge_records.py --base-url "$BASE_URL" --opportunity-id "<opportunity_id>" --event-id "<event_id>" --voucher-code "<voucher_code>"
```

The helper prints related API records and lightweight annotations. It does not write the final answer; still apply the template and decision rules yourself.

## Output Guardrails

- Preserve template field names exactly, including names that differ across tasks for the same concept.
- Expand template arrays when the source has multiple line items, milestones, freight modes, or follow-up tasks.
- Use numeric JSON values for money and quantities, not strings. Round currency values to two decimals when the template requests cent-level numbers.
- Use ISO `YYYY-MM-DD` dates or `null` exactly as the template permits.
- Use uppercase mode, risk, status, and action enum values when the template declares uppercase enums.
- Leave freight out only when the prompt or applicable policy says the quote is EXW-only or the destination is unconfirmed.
