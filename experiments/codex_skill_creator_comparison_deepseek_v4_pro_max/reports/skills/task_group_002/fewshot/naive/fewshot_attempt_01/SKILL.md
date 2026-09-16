---
name: medbridge-sales-ops
description: Resolve MedBridge Sales Ops API tasks — quote pricing packages with freight comparison and mode recommendations, and account/engagement reconciliations with invoice, payment, revenue-recognition, event, and voucher routing.
---

# MedBridge Sales Ops Skill

Use the shared MedBridge Sales Ops REST API to build quote decision packages and
account reconciliations from live business records. Always treat the API as the
single source of truth for customer, product, pricing, freight, invoice,
payment, revenue-recognition, event, and voucher data.

## API

The runner provides the base URL through a variable named `<TASK_ENV_BASE_URL>`
in the prompt. Use it exactly as given. All endpoints are read-only GETs; no
authentication is needed. These are the available endpoints (listed in the
staged `environment_access.md`):

**Core entities**
`/api/customers`, `/api/customers/{id}`
`/api/products`, `/api/products/{code}`
`/api/quotes`, `/api/quotes/{id}`
`/api/rfqs`, `/api/rfqs/{id}`
`/api/freight-quotes`, `/api/freight-quotes/{id}`
`/api/policies`, `/api/policies/{id}`

**Finance / reconciliation**
`/api/opportunities`, `/api/opportunities/{id}`
`/api/invoices`, `/api/invoices/{id}`
`/api/payments`, `/api/payments/{id}`
`/api/revenue-journals`, `/api/revenue-journals/{id}`
`/api/events`, `/api/events/{id}`
`/api/vouchers`, `/api/vouchers/{code}`

Call `/api` to confirm the API is reachable at the start of every task.

## Data-fetching strategy

When the prompt mentions a specific record id, fetch that single record first
and then follow its foreign-key references. When the prompt asks for all
records of a type, use the collection endpoint.

### Quote pricing tasks

These tasks ask for a product price, freight options, and policy flags for a
given quote or RFQ. Gather data in this order:

1. `GET /api/quotes/{quote_id}` or `GET /api/rfqs/{rfq_id}` — the quote/RFQ
   record. Extract `customer_id`, `quote_date`, product codes, and quantities.
2. `GET /api/customers/{customer_id}` — name, payment terms, policy references,
   and customer category.
3. `GET /api/products/{product_code}` for every product code that appears in
   the quote or RFQ. The product response includes an array of catalog tier
   objects. Select the tier whose `min_quantity` and `max_quantity` band
   contains the confirmed quantity.
4. `GET /api/freight-quotes` — fetch the collection and match freight records
   to the product category or code by freight id pattern. The prompt or quote
   context determines which freight records are relevant; when in doubt,
   include all freight options that are clearly associated with the product
   family.
5. `GET /api/policies` — fetch relevant policies; use the customer's policy
   references or policy ids that appear in quote/freight records.

After gathering data, compute:

- `unit_price_usd` — from the matched catalog tier.
- `exw_total_usd` — `unit_price_usd * confirmed_quantity`.
- For each freight option: `grand_total_usd = exw_total_usd + freight_cost_usd`.
- Freight validity: a freight quote is VALID when its `valid_until` is on or
  after the quote date; it is STALE when `valid_until` is before the quote
  date.
- Payment terms: use the value from the customer record, or from the policy
  record that the customer or quote references.
- Recommended mode: prefer SEA when it is available, low-risk, and valid.
  Choose AIR when urgency or shelf-life constraints dominate.

### IEHK / module-level RFQ tasks

When the RFQ is for an IEHK module set, the catalog may expose sub-module
products (e.g. `IEHK-BASIC`, `IEHK-SUPP-A`, etc.) at the same price level.
Include all of them as separate line items with their own article numbers,
prices, lead times, and shelf lives. Do not aggregate into a single line.

### Account / engagement reconciliation tasks

These tasks ask for a full financial and operational reconciliation of an
opportunity. Gather data in this order:

1. `GET /api/opportunities/{opportunity_id}` — stage, won amount, milestone
   references, linked customer and contact.
2. `GET /api/customers/{customer_id}` — name and attributes.
3. `GET /api/invoices` — fetch the collection and filter by
   `opportunity_id`. Each invoice corresponds to a milestone phase.
4. `GET /api/payments` — fetch the collection and filter by invoice id to
   compute paid amounts.
5. `GET /api/revenue-journals` — fetch the collection and check which
   milestones have a revenue journal entry.
6. `GET /api/events/{event_id}` — when the prompt names an event.
7. `GET /api/vouchers/{voucher_code}` — when the prompt names a voucher.

After gathering data, apply these rules:

**Milestone reconciliation**
- `invoice_total` is the invoice amount.
- `payment_status` is PAID when the sum of payments for that invoice equals or
  exceeds the invoice total; PARTIAL when some payment exists but less than
  the total; UNPAID otherwise.
- `outstanding_balance` is the sum of `amount_unpaid` across all milestones.
- `opportunity_matches_milestones` is true when the sum of all invoice totals
  equals the won amount.

**Revenue recognition**
- For a PAID milestone: if a revenue-journal record exists for that milestone
  id, status is RECOGNIZED; if none exists, status is MISSING_REVENUE_JOURNAL.
- For an UNPAID milestone: status is NOT_REQUIRED_UNPAID.
- `recognition_status` summary: COMPLETE_FOR_PAID_MILESTONES when every paid
  milestone has a revenue journal; MISSING_FOR_PAID_MILESTONES when any paid
  milestone lacks one.

**Follow-up / action routing**
- An unpaid milestone with a due date generates a collection task. The action
  is SEND_COLLECTION_NOTICE when past due, MONITOR_UNPAID_NOT_DUE when the
  due date is still in the future.
- A scheduled event with an active voucher generates an event invitation task
  (action SEND_BRIEFING_INVITE or SEND_EVENT_INVITATION).
- Accounting action: when a paid milestone is missing a revenue journal,
  generate RECORD_REVENUE with debit DEFERRED_REVENUE and credit
  IMPLEMENTATION_SERVICES_REVENUE, owned by ACCOUNTING.
- The contact name from the prompt (or the opportunity's linked contact)
  is the assignee for all follow-up tasks.

## Output rules

- Return **only** valid JSON. No markdown fences, no explanatory text before
  or after the JSON object.
- All money values are numeric, in USD, with exactly two decimal places
  (e.g. `50000.00`).
- All dates are ISO 8601 `YYYY-MM-DD` strings.
- All record ids are strings, used exactly as they appear in API responses.
- Fill the template completely; leave no placeholder strings or zero defaults
  where real data is available.
- Use the enum values listed in the template for status/action fields; do not
  invent new ones.
- All `null` values in the template mean the data is genuinely absent, not
  zero or empty string. Only use `null` when the API provides no value.

## Common pitfalls

- Do not guess catalog tiers. Always match the confirmed quantity against the
  tier bands from the product response.
- Do not assume freight is valid. Always compare `valid_until` against the
  quote date.
- Do not mix up which freight records belong to which product. Match by
  freight id prefix/product category pattern.
- For reconciliation tasks, revenue journals are per-milestone; a paid
  milestone without one is a gap, but an unpaid milestone without one is
  expected.
- Check payment totals across all payments for an invoice, not just the first
  one returned.
- When the template asks for boolean fields like `freight_excluded`, use JSON
  booleans (`true`/`false`), not strings.
