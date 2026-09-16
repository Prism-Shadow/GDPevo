---
name: medbridge-sales-ops
description: Use this skill whenever the user asks you to work with the MedBridge Sales Ops API, reconcile quotes, build quote revision packages, handle RFQ pricing, perform account or engagement reconciliations, verify freight options, check revenue recognition, or prepare any MedBridge CRM/finance-ready JSON response. This includes tasks mentioning quote IDs like Q-TR-*, RFQ-TR-*, opportunity IDs like OPP-TR-*, customer IDs like CUST-*, freight IDs like FR-*, invoice IDs like INV-*, payment IDs like PAY-*, event IDs like EVT-*, voucher codes, MedBridge, or Sales Ops. Always consult this skill when the user provides a task environment base URL together with business identifiers from the MedBridge domain, even if the user does not name the API directly.
---

# MedBridge Sales Ops

Use a shared MedBridge Sales Ops REST API to verify customers, quotes, products, freight, policies, invoices, payments, revenue journals, events, and vouchers, then produce a business-ready JSON response from a supplied answer template.

## Core workflow

Every MedBridge task follows the same pattern. Start here regardless of the specific task type.

### Step 1: Read the answer template

Read the file at `input/payloads/answer_template.json`. This is the authoritative output schema. Every field, nested object, array element, and enum value declared in the template must appear in the final answer. Use the placeholder values to understand what needs to be populated.

If the template uses an enum annotation like `"enum: WON | OPEN | LOST"`, pick the value that matches the API data; do not invent new values.

### Step 2: Identify the business entities

From the user's prompt, extract:
- The **base URL** (provided as `<TASK_ENV_BASE_URL>` or a similar placeholder)
- The **primary record type and ID** (quote, RFQ, or opportunity)
- Any **secondary IDs** called out in the prompt (customer, product, freight, event, voucher)
- The **quote date** or **as-of date** (often `2026-06-01`)
- The **confirmed quantity** if this is a quote revision
- The **contact name** if the task requires follow-up routing

### Step 3: Fetch primary records from the API

Always start by hitting `GET {base_url}/api` to confirm the dataset description and seed. This gives you the list of available collections.

Then fetch the primary record using its specific endpoint. For example:
- Quote tasks: `GET {base_url}/api/quotes/{quote_id}`
- RFQ tasks: `GET {base_url}/api/rfqs/{rfq_id}`
- Opportunity tasks: `GET {base_url}/api/opportunities/{opportunity_id}`

From the primary record, extract all cross-referenced IDs: `customer_id`, `product_code`, linked `invoice_id` values, `event_id`, `voucher_code`.

### Step 4: Fetch and cross-verify all secondary records

Use the specific endpoints to pull every related record. Do not skip any entity mentioned in the template or prompt.

| Entity | Endpoint | Key fields to capture |
|--------|----------|-----------------------|
| Customer | `/api/customers/{id}` | `name`, `payment_profile`, `segment`, `customer_type`, `is_recurring`, `region`, `contacts` |
| Product | `/api/products/{code}` | `price_tiers`, `article_number`, `shelf_life_months`, lead time from matched tier, `cold_chain_required` |
| Freight quotes | `/api/freight-quotes/{id}` | `cost_usd`, `mode`, `transit_days_text`, `valid_until`, `route_risk`, `cold_chain_support` |
| Policies | `/api/policies` (list all) | `rule`, `terms_code`, `policy_area`, `applies_to` |
| Invoices | `/api/invoices` (list all) | Filter by `customer_id` and `opportunity_id` |
| Payments | `/api/payments` (list all) | Filter by `customer_id` and `opportunity_id` |
| Revenue journals | `/api/revenue-journals` (list all) | Filter by `opportunity_id` |
| Events | `/api/events` (list all) | Filter by `customer_id` and `opportunity_id` |
| Vouchers | `/api/vouchers` (list all) | Filter by `customer_id` and `event_id` |

For collection endpoints that return all records (invoices, payments, revenue-journals, events, vouchers), filter in memory by matching on the `customer_id` and/or `opportunity_id` from the primary record. Do not call individual-by-ID endpoints for records you have not confirmed exist; use the list endpoints.

The `GET {base_url}/api/search?q={text}` endpoint accepts a partial text match and returns records across all collections. Use it to quickly pull all records for a given customer or opportunity when the prompt only names one ID and you need the full cross-referenced set (e.g., searching for "HELIOS" returns customer, opportunity, invoices, payments, revenue journals, event, and voucher all at once).

### Step 5: Apply business rules

Read [references/business_rules.md](references/business_rules.md) for the full policy-to-logic mapping. Every task touches a subset of these rules. The API's `/api/policies` endpoint returns the canonical policy text, but the reference doc tells you how to translate each policy into concrete output fields.

Key rules to apply (see the reference for details):
- **Price tier matching**: Match confirmed quantity to the product's `price_tiers` entry where `min_qty <= quantity` and (`max_qty >= quantity` or `max_qty` is null). Use the `unit_price_usd` and `lead_time_days` from that tier.
- **Payment terms**: Map customer segment/payment_profile to the correct terms code (PREPAY_100 for new NGOs, NET_30_AFTER_PO for recurring, MILESTONE_BILLING for implementation services).
- **Freight validity**: A freight quote is stale when `valid_until` is before the quote date. Flag stale freight with `validity_status: "STALE"` and `source_is_stale: true`.
- **Freight reconfirmation**: Always set `freight_reconfirmation_required: true` unless the task is EXW-only with no freight.
- **Revenue recognition**: For each milestone that is PAID (invoice status `paid`), check whether a revenue journal exists for its `invoice_id`. If missing, flag as `MISSING_REVENUE_JOURNAL` or `REQUIRED_MISSING`.
- **Recommended mode**: Prefer the lowest-risk mode with valid freight. SEA is the default recommendation for non-urgent shipments; use AIR only when cold chain or urgency demands it.
- **Module granularity**: When the prompt says "module level only" or the RFQ type is `indicative_module_quote`, quote each module as a separate line item without splitting into components.

### Step 6: Fill the template and return

Populate every field in the answer template with values from the API data. The golden rules:

- **Money fields**: Use exactly two decimal places (`42480.00`, not `42480` or `42480.0`).
- **Dates**: Use ISO 8601 (`YYYY-MM-DD`).
- **IDs**: Use the stable record IDs from the API as-is (e.g., `"Q-TR-WC-1187"`, `"CUST-HHA"`).
- **Enums**: Match the controlled vocabulary from the template exactly. Never invent a new enum value.
- **Booleans**: `true` or `false`, not strings.
- **Null vs empty**: Use `null` only when the template or data genuinely has no value (e.g., a milestone with no due_date). Use `""` only when the template shows a string placeholder.
- **Array order**: For freight options, list AIR first, then SEA, then ROAD (fastest to slowest). For milestones, list in ascending order (MS1, MS2, MS3).

Return the JSON response directly with no surrounding markdown, no explanation, and no commentary. The consumer expects valid JSON and nothing else.

## Task-type variations

### Quote revision with freight

Used when the primary record is a `quote` with `quote_type: "quote_revision_with_freight"`. The template typically has a `quote_summary` (or `pricing`) section and a `freight_options` (or `transport_decisions`) array.

- Fetch the quote, customer, product, and every freight quote linked to the quote.
- Match the confirmed quantity to the correct price tier.
- Compute `exw_total_usd` = `confirmed_quantity * unit_price_usd`.
- For each freight option compute `grand_total_usd` = `exw_total_usd + freight_cost_usd`.
- Check each freight quote's `valid_until` against the quote date. If any freight `valid_until` < quote date, set validity flags and add a `freight_warning`.
- Map `route_risk` values: `"low"` maps to `"LOW"`, `"medium"` maps to `"MEDIUM"`, `"high"` maps to `"HIGH"`.

### Indicative module quote (EXW only, no freight)

Used when the primary record is an RFQ with `request_type: "indicative_module_quote"` and the prompt says "EXW only" or "freight excluded."

- Fetch the RFQ, customer, policies, and every product listed in `requested_modules`.
- The `POL-MODULE-GRANULARITY` policy confirms module-level quoting.
- The `POL-INDICATIVE-EXW` policy confirms "EXW only and exclude freight."
- For new NGO customers, payment terms are `PREPAY_100`.
- Set `freight_excluded: true` and `offer_validity_days: 30` (from `POL-QUOTE-VALIDITY`).

### Account/engagement reconciliation

Used when the primary record is an `opportunity` with `stage: "closed_won"`. The template typically has `account_status` (or `engagement_reconciliation`), `milestones`, `revenue_recognition`, `event`, and `follow_up_tasks`.

- Fetch the opportunity, customer, all invoices for that opportunity, all payments, all revenue journals, the linked event, and the linked voucher.
- For each milestone (phase), determine invoice state, payment state, and revenue recognition status:
  - **PAID**: invoice `status` is `"paid"` and `paid_amount_usd > 0`
  - **UNPAID**: invoice `status` is `"unpaid"` or `"overdue"` and `paid_amount_usd == 0`
  - **RECOGNIZED**: a revenue journal exists with matching `invoice_id` and `status: "posted"`
  - **MISSING_REVENUE_JOURNAL**: invoice is paid but no revenue journal exists for it
  - **NOT_REQUIRED_UNPAID**: invoice is unpaid; revenue recognition is not yet due
- Generate follow-up tasks:
  - **COLLECTION** task for any unpaid milestone with a due date. Set `next_action: "COLLECT_UNPAID_MILESTONE"` and target the contact from the prompt.
  - **EVENT_INVITATION** task for any linked event in `"scheduled"` or `"confirmed"` status. Set `next_action: "SEND_EVENT_INVITATION"` and use the event's `primary_contact` and `voucher_code`.
- For the accounting action: if a paid milestone is missing its revenue journal, the action is `RECORD_REVENUE_MSn` with debit `DEFERRED_REVENUE` and credit `IMPLEMENTATION_SERVICES_REVENUE`.

## Reference files

- [references/business_rules.md](references/business_rules.md): Full mapping from MedBridge policies to output field values, plus price tier matching, freight validity logic, and revenue recognition rules.
- [references/api_schemas.md](references/api_schemas.md): Response shapes for every API endpoint so you know what fields are available without needing to call the API just to inspect its structure.

Read these references when you need the detailed rules or schema definitions; they are not needed for every simple task.
