---
name: medbridge-sales-ops
description: Use for MedBridge Sales Ops API tasks that require account-ready JSON matching a provided answer template, including RFQ or quote pricing, EXW and freight decision packages, catalog tier selection, quote policies, opportunity milestone reconciliation, payments, revenue recognition, events, vouchers, and follow-up actions.
---

# MedBridge Sales Ops

## Core Workflow

1. Read the task prompt and `input/payloads/answer_template.json` first. Treat the template as the output contract: keep its keys, object nesting, enum vocabulary, booleans, nulls, money precision, and array semantics.
2. Resolve the API base URL from the runner text or environment. Query only the shared MedBridge Sales Ops API. Start with `GET /api`; use direct endpoints when available and fall back to collection lists or `GET /api/search?q=<text>` when an ID endpoint is not implemented.
3. Extract all target IDs and constraints from the prompt: customer, quote/RFQ/opportunity, product/module codes, quantity, quote/as-of date, contact, event, voucher, freight requirement, and any explicit instruction such as EXW-only or module-level pricing.
4. Fetch and cross-check the source records. Do not rely on prompt text alone when the API has a record. Reject distractor records that only partially match, such as wrong customer, wrong opportunity, wrong shipment size, unrelated route, explicit distractor/mismatch status, or component details when the task asks for module-level lines.
5. Fill only the requested template. Output valid JSON only, with no markdown, notes, or extra keys.

Use [references/medbridge_rules.md](references/medbridge_rules.md) for calculation and status rules. Use [scripts/medbridge_fetch.py](scripts/medbridge_fetch.py) to gather linked records quickly without hand-writing repeated curl calls.

## API Discovery

Useful collections:

- `customers`, `products`, `rfqs`, `quotes`, `freight-quotes`, `policies`
- `opportunities`, `invoices`, `payments`, `revenue-journals`, `events`, `vouchers`

Run the bundled helper from a task workspace:

```bash
python skill/scripts/medbridge_fetch.py "$TASK_ENV_BASE_URL" --quote-id "$QUOTE_ID"
python skill/scripts/medbridge_fetch.py "$TASK_ENV_BASE_URL" --rfq-id "$RFQ_ID"
python skill/scripts/medbridge_fetch.py "$TASK_ENV_BASE_URL" --opportunity-id "$OPPORTUNITY_ID"
python skill/scripts/medbridge_fetch.py "$TASK_ENV_BASE_URL" --search "$TEXT"
```

If the runner names the base URL as `<TASK_ENV_BASE_URL>` or `BASE_URL` but does not export it, paste the actual URL as the first argument.

## Quote And RFQ Packages

- For catalog pricing, fetch the quote or RFQ, customer, product records, and policies. Select the product `price_tiers` row whose `min_qty <= quantity <= max_qty`; treat `max_qty: null` as open-ended. Use tier `unit_price_usd`, `lead_time_days`, and product `shelf_life_months` unless the template explicitly asks for other fields.
- Compute `line_total` or `exw_total_usd` as `quantity * unit_price`. Use the template's numeric style; money fields are usually numeric JSON values, not strings.
- For module RFQs, use the RFQ's requested module lines as the line-item array. Keep module-level product codes and article numbers. Ignore component composition or worksheet details unless the prompt specifically requests component pricing.
- Apply policy records by `policy_area` and `applies_to`: new clients generally use prepayment terms, recurring NGO/catalog quotes can use approved net terms, indicative quotes without a confirmed destination remain EXW-only with freight excluded, and standard catalog offer validity comes from the quote-validity policy.
- For freight packages, include freight records that match the target quote, route/destination, shipment characteristics, and requested option set. When multiple records share a quote ID, exclude records marked or described as distractors, mismatches, archived routes, or wrong-size benchmarks.

## Freight Decisions

- `grand_total_usd = exw_total_usd + freight_cost_usd`.
- A freight option is valid on the quote date when `valid_until >= quote_date` and the record is not stale, mismatched, or otherwise inactive. If the template has `validity_status`, use `VALID` for valid active options and `STALE` for expired or stale-source options.
- `source_is_stale` is true when the freight record status is stale, the validity date precedes the quote date, or the source notes say the quote is stale/expired.
- Normalize transport modes and risk values to the template's casing, usually uppercase.
- Recommend the lowest total cost option that is valid and not high-risk. Exclude stale, expired, mismatch, and high border/customs risk options from recommendation unless the prompt requires a special urgent mode. If the cheapest option is excluded, recommend the next valid acceptable mode.
- Set freight reconfirmation flags from the freight policy and from any expired, stale, short-validity, or elevated-risk options. If the template asks for a warning string, make it concise and specific to the invalid or risky records.

## Opportunity Reconciliation

- Fetch the opportunity, customer, invoices, payments, revenue journals, event, and voucher. Join by `opportunity_id`, `customer_id`, `invoice_id`, `phase_id`, event ID, and voucher code.
- Use the opportunity amount as the won total. Sum milestone or invoice amounts for the phase total. `opportunity_matches_*` is true only when those amounts agree exactly at cent precision.
- For each milestone, derive paid and unpaid amounts from invoice fields and posted payments. Payment state is `PAID` when paid amount equals invoice amount, `PARTIAL` when paid amount is greater than zero but less than invoice amount, and `UNPAID` when paid amount is zero.
- Paid completed milestones require a posted revenue journal. Mark recognized milestones as recognized, paid milestones without a journal as missing revenue recognition, and unpaid milestones as not required yet. Top-level revenue status is complete only when every paid milestone has a matching posted journal.
- Collection actions target unpaid milestones. Use an overdue collection action when the due date is before the as-of date; otherwise use the template's monitor/not-due action if available.
- Event and voucher actions should come from event/voucher records tied to the same customer and opportunity. Normalize statuses to the enum labels in the template, and route invite tasks to account management unless the API or template indicates a different owner queue.
