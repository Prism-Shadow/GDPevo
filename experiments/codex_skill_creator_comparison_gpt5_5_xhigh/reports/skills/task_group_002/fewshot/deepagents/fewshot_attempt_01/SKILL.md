---
name: medbridge-sales-ops
description: Solve MedBridge Sales Ops API tasks that require account-ready JSON for quote pricing, freight comparisons, RFQs, opportunity milestone reconciliation, revenue recognition, invoice follow-up, events, and vouchers. Use when prompts mention MedBridge Sales Ops, quote/RFQ/opportunity IDs, product catalog tiers, freight quotes, policies, or returning JSON matching an answer_template.json.
---

# MedBridge Sales Ops

## Core Workflow

1. Read the user prompt and the provided `input/payloads/answer_template.json`. Treat the template as the output contract: preserve keys, arrays, enum spellings, date format, nullability, and numeric precision style.
2. Identify the task family:
   - Quote or RFQ pricing: prompt mentions a quote/RFQ, products/modules, EXW pricing, freight, payment terms, or quote policies.
   - Engagement reconciliation: prompt mentions an opportunity, milestones/phases, invoices, payments, revenue journals, events, vouchers, or follow-up actions.
3. Resolve the task API base URL from the prompt or runner-provided environment. Use only the MedBridge API records needed for the IDs in the prompt/template.
4. Gather linked records with direct endpoints and ID-specific search. Prefer exact IDs from the prompt. Avoid broad listing unless direct fetch/search cannot identify a required linked record.
5. Apply the derivation rules in [references/derivation-rules.md](references/derivation-rules.md).
6. Return only valid JSON. Do not include markdown, comments, provenance notes, or extra keys.

## API Gathering

The API root is `/api`; useful collections include `customers`, `products`, `rfqs`, `quotes`, `freight-quotes`, `policies`, `opportunities`, `invoices`, `payments`, `revenue-journals`, `events`, and `vouchers`.

Use direct GETs when you know the ID:

```bash
curl -sS "$BASE_URL/api/quotes/$QUOTE_ID"
curl -sS "$BASE_URL/api/products/$PRODUCT_CODE"
curl -sS "$BASE_URL/api/customers/$CUSTOMER_ID"
```

Use search to collect linked records when the API does not expose a filtered list:

```bash
curl -sS "$BASE_URL/api/search?q=$QUOTE_ID"
curl -sS "$BASE_URL/api/search?q=$OPPORTUNITY_ID"
curl -sS "$BASE_URL/api/search?q=$EVENT_ID"
```

Optional helper: run [scripts/collect_context.py](scripts/collect_context.py) to extract IDs from a prompt and perform ID-specific searches:

```bash
python skill/scripts/collect_context.py --base-url "$BASE_URL" --prompt input/prompt.txt
```

## Output Discipline

- Build the response by filling the template, not by inventing a new schema.
- Use API values over prompt wording when they conflict, except for explicit user-confirmed quantities/dates in the prompt.
- Keep line items at the requested granularity. For module RFQs, quote module product codes and ignore component composition notes unless the template explicitly asks for components.
- Use uppercase enum values exactly as declared by the template.
- Use `null` where the template permits null and the value is not applicable.
