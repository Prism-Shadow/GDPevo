---
name: medbridge-sales-ops
description: Use this skill for MedBridge Sales Ops task-environment prompts that require quote/RFQ decision packages, freight comparisons, policy flags, opportunity reconciliation, invoice/payment/revenue checks, event/voucher follow-up, and final JSON matching an answer_template.json. It is especially relevant when the prompt mentions the shared MedBridge API, TASK_ENV_BASE_URL, BASE_URL, quotes, RFQs, customers, products, freight-quotes, policies, opportunities, invoices, payments, revenue-journals, events, or vouchers.
---

# MedBridge Sales Ops

Use this workflow to produce an account-ready JSON answer from the MedBridge Sales Ops API and the provided `input/payloads/answer_template.json`.

## Required Workflow

1. Read the prompt and `input/payloads/answer_template.json` first. Treat the template as the output schema and controlled-value source.
2. Resolve the API base URL from the prompt or environment, usually `TASK_ENV_BASE_URL` or `BASE_URL`. Verify `GET /api` before relying on records.
3. Extract stable identifiers from the prompt: quote IDs, RFQ IDs, opportunity IDs, customer IDs, event IDs, voucher codes, product codes, account names, quantities, and quote/as-of dates.
4. Read [references/medbridge-rules.md](references/medbridge-rules.md) before final assembly. It contains the pricing, freight, policy, and reconciliation rules needed for these tasks.
5. Optionally run the bundled collector from the skill directory to gather linked records and generic derived summaries:

   ```bash
   python scripts/collect_medbridge.py --base-url "$BASE_URL" --prompt-file input/prompt.txt
   ```

   Add explicit flags such as `--quote-id`, `--rfq-id`, `--opportunity-id`, `--customer-id`, `--event-id`, or `--voucher-code` when the prompt includes them.
6. Fetch authoritative API records, not just search snippets. `/api/<collection>` returns `{collection, count, records}` for list endpoints. Detail endpoints may be available for some collections; if a detail endpoint is absent, filter the list endpoint.
7. Fill only the keys present in the template. Return valid JSON only, with no markdown, comments, or explanatory wrapper text.

## Answer Discipline

- Use prompt-confirmed quantities, dates, IDs, and customer display names when the prompt explicitly provides them; use API records to verify and fill the remaining facts.
- Keep quote/RFQ lines at the granularity requested by the prompt and policy. Do not decompose module records into component SKUs unless the user explicitly asks for component-level pricing.
- Exclude records that are clearly distractors, superseded, mismatched, old benchmarks, or unrelated to the requested quote/RFQ/opportunity, even if they share a customer or product.
- Compute money from source numbers and round to cents. JSON numbers need not preserve trailing zeros, but calculations must be cent-level correct.
- Normalize statuses and actions to the enum strings declared in the template.
- Before final output, verify arithmetic: line totals, EXW totals, grand totals, phase totals, paid totals, outstanding balances, and recognized revenue totals.
