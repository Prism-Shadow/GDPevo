---
name: medbridge-sales-ops-json
description: Use this skill for MedBridge Sales Ops API tasks that require account-ready JSON for quotes, RFQs, catalog pricing, freight comparisons, opportunity milestone reconciliation, invoices, payments, revenue journals, events, or vouchers. Use it whenever the prompt mentions the MedBridge Sales Ops API, `<TASK_ENV_BASE_URL>`, BASE_URL, quote decision packages, EXW pricing, freight validity, revenue recognition, or CRM/accounting follow-up JSON.
---

# MedBridge Sales Ops JSON

Use this skill to answer MedBridge Sales Ops tasks that require a final JSON object matching an `input/payloads/answer_template.json` file.

The target task is data reconciliation, not prose generation. Read the prompt and template first, gather the source records from the API, derive only the fields the template asks for, validate the JSON shape, and return JSON only.

## Core Workflow

1. Read the user prompt and the local `input/payloads/answer_template.json`.
2. Resolve the API base URL from the prompt, environment, or an environment access note if one is staged with the task. Treat placeholders such as `<TASK_ENV_BASE_URL>` and `BASE_URL` as the runner-provided base URL.
3. Query the API for the exact business identifiers named in the prompt, such as customer IDs, RFQ IDs, quote IDs, product codes, opportunity IDs, event IDs, and voucher codes.
4. Use `/api/search?q=<identifier>` as the main discovery tool. It returns linked records across collections. Then fetch direct product, customer, quote, RFQ, opportunity, event, or voucher records when needed.
5. Build the answer from the template outward. Preserve key names, nesting, arrays, booleans, nulls, controlled enum strings, ISO dates, and numeric types required by the template.
6. Return only valid JSON. Do not include markdown, comments, code fences, or explanatory text.

For a quick record dump, use the bundled helper:

```bash
python skill/scripts/collect_medbridge.py --base-url "$TASK_ENV_BASE_URL" --term "<business-id>" --out /tmp/medbridge_records.json
```

Read [references/medbridge_rules.md](references/medbridge_rules.md) for the reusable derivation rules before filling a quote, freight, or opportunity reconciliation template.

## API Collections

Common collections are:

- `customers`
- `products`
- `rfqs`
- `quotes`
- `freight-quotes`
- `policies`
- `opportunities`
- `invoices`
- `payments`
- `revenue-journals`
- `events`
- `vouchers`

Prefer exact IDs from the prompt over broad listing. Search results can include distractors, so filter records by the target quote, RFQ, opportunity, customer, event, voucher, and product fields before deriving the answer.

## JSON Discipline

- Treat the answer template as the contract. Do not add extra keys unless the template clearly allows them.
- Use the template's controlled values, not raw API text, when an enum is declared.
- Use cent-level numbers for currency fields. JSON has no fixed decimal rendering guarantee, but compute values to two decimal places before writing them.
- Use `null` where the template expects null-capable fields and the business value is not applicable.
- Sort business arrays in the order implied by the template or prompt. For milestones, use ascending phase or milestone order. For freight, use the template order if modes are predeclared; otherwise use a stable mode order such as air, sea, road unless the prompt asks for another comparison order.

## Record Verification

Before finalizing, verify these source links:

- Customer IDs in the prompt match customer records referenced by quotes, RFQs, opportunities, events, and vouchers.
- Product codes in quote or RFQ lines have matching product catalog records.
- Quote freight records match the target quote ID and are not distractor routes.
- Opportunity phase invoice IDs match invoice records, and invoice records match the opportunity and customer.
- Posted payments and posted revenue journals match the correct invoice, opportunity, and phase.
- Event records and voucher records reference each other and the same opportunity or customer when the template asks for event or invite actions.

If a direct endpoint is unavailable for a record type, search the exact record ID instead of broad-listing all records.

## Final Validation

Run a local JSON parse before responding when possible:

```bash
python -m json.tool /tmp/final_answer.json >/dev/null
```

Also compare the final keys against `answer_template.json`. The final response should be the JSON object itself, not a file path or a summary.
