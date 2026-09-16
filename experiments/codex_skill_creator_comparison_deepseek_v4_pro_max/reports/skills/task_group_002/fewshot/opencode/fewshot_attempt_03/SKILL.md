---
name: medbridge-sales-ops
description: Query the MedBridge Sales Ops API to prepare quote decision packages and account reconciliations. Use this skill whenever the user asks to verify customers, quotes, RFQs, products, freight, policies, opportunities, invoices, payments, revenue journals, events, or vouchers through the MedBridge Sales Ops API, or when they need to fill a JSON answer template with data from that API. This includes tasks where the task environment provides a base URL for the shared MedBridge API.
---

# MedBridge Sales Ops API Skill

This skill describes how to use the MedBridge Sales Ops API to produce quote
decision packages, account reconciliations, and engagement reconciliations. The
API is a shared CRM, quote, logistics, and milestone engagement data source.

## The API at a glance

The task environment provides the base URL as `<TASK_ENV_BASE_URL>` or a similar
placeholder. All endpoints are read-only GETs from `/api` namespaced paths.

### Collections and endpoints

| Collection   | List endpoint           | Detail endpoint                  |
|-------------|------------------------|---------------------------------|
| customers    | `GET /api/customers`   | `GET /api/customers/{id}`      |
| products     | `GET /api/products`    | `GET /api/products/{code}`     |
| quotes       | `GET /api/quotes`      | `GET /api/quotes/{id}`         |
| rfqs         | `GET /api/rfqs`        | `GET /api/rfqs/{id}`           |
| freight-quotes | `GET /api/freight-quotes` | `GET /api/freight-quotes/{id}` |
| opportunities | `GET /api/opportunities` | `GET /api/opportunities/{id}` |
| policies     | `GET /api/policies`    | Not available                  |
| invoices     | `GET /api/invoices`    | Not available                  |
| payments     | `GET /api/payments`    | Not available                  |
| revenue-journals | `GET /api/revenue-journals` | Not available            |
| events       | `GET /api/events`      | Not available                  |
| vouchers     | `GET /api/vouchers`    | Not available                  |

For collections without detail endpoints, fetch the full list and filter
client-side by `customer_id`, `opportunity_id`, `invoice_id`, or `event_id` as
needed.

There is also `GET /api/search?q={text}` for text search.

### Common record shapes

**Customer**: `id`, `name`, `country`, `region`, `customer_type`, `segment`,
`status` (active/prospect/…), `is_recurring`, `payment_profile`,
`grant_terms`, `contacts` array with `name`, `email`, `phone`, `role`.

**Product**: `code`, `name`, `family`, `article_number`, `unit`, `weight_kg`,
`cbm`, `cold_chain_required`, `shelf_life_months`, `price_tiers` array. Each
tier has `min_qty`, `max_qty` (may be `null` for unlimited top tier),
`unit_price_usd`, `lead_time_days`.

**Quote**: `id`, `customer_id`, `quote_date`, `primary_product_code`,
`incoterm`, `status`, `line_items` array, `confirmed_quantity`.

**RFQ**: `id`, `customer_id`, `quote_date`, `incoterm_requested`,
`request_type`, `requested_modules` array (each with `product_code`,
`quantity`), `destination`, `status`.

**Freight-quote**: `id`, `quote_id`, `mode` (air/sea/road), `origin`,
`destination`, `cost_usd`, `transit_days_min/max/text`, `valid_until`,
`route_risk` (low/medium/high), `cold_chain_support`, `risk_notes`, `status`
(active/stale/…), `forwarder`.

**Opportunity**: `id`, `customer_id`, `contact`, `opportunity_name`, `stage`
(closed_won/open/lost), `won_amount_usd`, `outstanding_amount_usd`, `phases`
array with `phase_id`, `name`, `amount_usd`, `completion_date`, `invoice_id`.

**Invoice**: `id`, `invoice_number`, `customer_id`, `opportunity_id`,
`phase_id`, `amount_usd`, `paid_amount_usd`, `outstanding_amount_usd`,
`status` (paid/unpaid/…), `due_date`, `issue_date`, `billing_type`.

**Payment**: `id`, `invoice_id`, `opportunity_id`, `customer_id`, `amount_usd`,
`payment_date`, `method`, `status` (posted/…), `reference`.

**Revenue-journal**: `id`, `invoice_id`, `opportunity_id`, `phase_id`,
`amount_usd`, `debit_account`, `credit_account`, `posted_date`, `status`.

**Event**: `id`, `name`, `customer_id`, `opportunity_id`, `event_date`,
`status` (scheduled/confirmed/live/completed/tentative/…),
`primary_contact`, `voucher_code`, `follow_up_owner`.

**Voucher**: `code`, `customer_id`, `event_id`, `opportunity_id`,
`discount_percent`, `max_redemptions`, `redemptions_used`, `status`
(active/draft/expired/disabled/…), `valid_until`.

**Policy**: `id`, `name`, `policy_area`, `rule`, `applies_to`, `terms_code`,
`effective_date`.

## General workflow

When asked to fill a JSON answer template from the MedBridge API, follow this
sequence:

1. **Read the template**. Every task provides a payload JSON that defines the
   output shape, field names, and allowed enum values. Study it before making
   any API calls so you know exactly what data to collect.

2. **Identify the root entity** (quote, RFQ, or opportunity) and call its
   detail endpoint by ID.

3. **Resolve related records in parallel**. For a quote task, fetch the
   customer, product, and freight-quotes collection in one parallel batch. For
   a reconciliation task, fetch the customer, opportunity detail, and the full
   collections for invoices, payments, revenue-journals, events, vouchers, and
   policies.

4. **Derive values using the rules below**. Apply price-tier selection,
   freight-validity checks, payment-status logic, revenue-recognition checks,
   and policy-based decisions as described in the following sections.

5. **Fill the template exactly**. Use the field names, casing, and enum values
   from the template. Do not invent new keys. Return only the JSON — no
   markdown fences, no commentary.

## Price-tier selection

When you need the unit price for a product at a given quantity, scan the
product's `price_tiers` array for the entry where `min_qty ≤ quantity ≤
max_qty`. Treat a `null` `max_qty` as unlimited. Once you find the matching
tier, use its `unit_price_usd`, `lead_time_days`, and the product's
`shelf_life_months`.

Do not use a tier where the quantity falls outside the range. Do not average
tiers.
The EXW total is `quantity × unit_price_usd` for the single matching tier.

For multi-product lists (module RFQs), apply tier selection independently to
each product code.

## Freight validity and risk

Each freight quote has a `valid_until` date. Compare it to the task's business
date (usually the quote date from the quote or RFQ).

- **Valid**: `valid_until >= business_date`.
- **Stale**: `valid_until < business_date`.

A stale freight quote is unreliable. Flag it, and do not recommend it as the
primary transport mode.

`route_risk` on the freight quote is a free-form string (`"low"`, `"medium"`,
`"high"`). Map to uppercase when the template expects an enum (e.g., `"LOW"`,
`"MEDIUM"`, `"HIGH"`).

The grand total for a freight option is `exw_total + freight_cost_usd`.

When there are three modes (air, sea, road), the recommended mode is typically
the cheapest valid option with acceptable risk. The mode value from the API is
lowercase (`"air"`, `"sea"`, `"road"`); map to uppercase when the template
expects it.

The policy `POL-FREIGHT-RECONFIRM` means freight rates should be marked as
requiring reconfirmation at final order. The policy `POL-EXW-SCOPE` means EXW
excludes freight, insurance, and duties unless explicitly added as options.

## Payment terms

Determine payment terms from the customer's segment, `is_recurring` flag, and
`payment_profile`, cross-referenced with matching policies.

- **New NGO clients** (segment `new_ngo`, no `client_since`, not `is_recurring`):
  policy `POL-NEW-CLIENT-PAYMENT` → `"PREPAY_100"`.
- **Recurring NGO customers**: policy `POL-RECURRING-NGO-PAYMENT` →
  `"NET_30_AFTER_PO"`.
- **Recurring commercial** (segment `recurring_commercial`):
  `"NET_30_AFTER_PO"`.
- **Implementation services** (segment `implementation_services`):
  `"MILESTONE_BILLING"` — payment terms are milestone-driven, not a single
  net-days code.

When a template field asks for `payment_terms`, use the value that matches the
customer's profile. Do not guess; verify against the customer record.

## Revenue recognition and milestone reconciliation

For reconciliation tasks, the core logic is:

1. **Collect phases** from the opportunity. Each phase has a `phase_id`,
   `amount_usd`, `completion_date`, and `invoice_id`.

2. **Find invoices** by filtering the invoices list on `opportunity_id`. Match
   each phase's `invoice_id` to an invoice record.

3. **Determine payment state** for each invoice:
   - If `status` is `"paid"` (fully paid, `outstanding_amount_usd == 0`),
     payment status is `"PAID"` and `amount_paid = amount_usd`.
   - If `status` is `"unpaid"` or `"open"` (nothing or partial paid),
     check `paid_amount_usd` and `outstanding_amount_usd`.
   - Cross-verify with the payments collection: sum all payments with matching
     `invoice_id` for `amount_paid`.

4. **Determine revenue recognition** for each milestone:
   - If the invoice is fully paid **and** a revenue journal exists with
     matching `invoice_id` in the revenue-journals list, recognition is
     `"RECOGNIZED"`.
   - If the invoice is fully paid **but** no matching revenue journal exists,
     recognition is `"MISSING_REVENUE_JOURNAL"` — this drives an accounting
     follow-up task.
   - If the invoice is unpaid (or partially paid), recognition is
     `"NOT_REQUIRED_UNPAID"` — revenue is not recognized until payment.

5. **Calculate matching**: The sum of all phase `amount_usd` values should
   equal the opportunity's `won_amount_usd`. Report whether they match.

6. **Outstanding balance**: Sum of unpaid `amount_usd` across all invoices
   for the opportunity. The opportunity record also carries
   `outstanding_amount_usd` as a cross-check.

Policy `POL-REVREC` describes the rule: when a milestone is complete and paid,
create or verify revenue recognition from deferred revenue to income; unpaid
future milestones remain outstanding and drive collection tasks when due or
overdue.

## Follow-up tasks

When the template includes follow-up tasks, derive them from the reconciliation
results:

- **Collection tasks**: For each unpaid milestone with a `due_date`, create a
  collection task. If the due date has already passed relative to the business
  date, the urgency increases. The contact, customer ID, and opportunity ID
  come from the opportunity and customer records.

- **Event-invitation tasks**: If an event is linked to the opportunity (match
  on `opportunity_id` and `customer_id` in the events list), and its status is
  not `"completed"`, create an invitation task. Include the voucher code and
  event ID. The invite should be sent before the event date.

- **Accounting tasks**: When a paid milestone has a missing revenue journal
  (`"MISSING_REVENUE_JOURNAL"`), create an accounting task to record revenue.
  The debit is `"DEFERRED_REVENUE"`, credit is
  `"IMPLEMENTATION_SERVICES_REVENUE"`, and the owner is `"ACCOUNTING"`.

## Module-level quoting

When an RFQ is for modules (the API's `request_type` is
`"indicative_module_quote"` or the RFQ includes `requested_modules`), quote at
module line level. Do not split modules into their components even if the
product record lists `components`. The policy `POL-MODULE-GRANULARITY` states
this rule explicitly.

## Indicative / EXW-only scope

When an RFQ has no confirmed destination (e.g., `"Destination pending donor
allocation"`), or the incoterm is EXW, do not include freight. The policy
`POL-INDICATIVE-EXW` requires EXW only with freight excluded. Mark
`freight_excluded: true` and set quote basis to `"EXW_ONLY"`.

## Quote validity

Per `POL-QUOTE-VALIDITY`, catalog pricing is valid for 30 calendar days from
the quote date. The template may ask for `offer_validity_days`; use `30`.

## WHO documentation

For IEHK-style emergency health kit quotes involving NGO or government
customers in the health sector, `who_documentation_required` is `true`.

## Stage mapping

When the template uses normalized stage values:
- `"closed_won"` → `"WON"`
- `"open"` → `"OPEN"`
- `"closed_lost"` → `"LOST"`

## Data formatting rules

- **Money**: Always use two decimal places (cents) for USD amounts. For example
  `12345.00`, not `12345` or `12345.0`.
- **Dates**: ISO `YYYY-MM-DD` format everywhere.
- **IDs**: Copy record IDs verbatim from the API. Do not transform, truncate,
  or prefix them.
- **Nulls**: Use `null` (JSON null), not `"null"` or `"NONE"`, when a field
  has no applicable value.
- **Enum values**: Use exactly the casing and spelling from the template's
  enum annotations. Do not invent values.
- **Text fields**: Copy transit day strings verbatim (e.g., `"4-6 days"`).
- **Freight mode**: API returns lowercase (`"air"`, `"sea"`, `"road"`) — map
  to uppercase (`"AIR"`, `"SEA"`, `"ROAD"`) when the template uses uppercase.

## Parallel data fetching

Fetch independent records in parallel batches. For quote tasks, the first
parallel batch after resolving the quote/RFQ should include the customer,
product(s), freight-quotes list, and policies list. For reconciliation tasks,
fetch the customer, opportunity detail, invoices list, payments list,
revenue-journals list, events list, vouchers list, and policies list all in one
parallel batch.

## Verification checklist

Before returning the final JSON, verify:
- The answer template's full structure is preserved (no missing or extra keys).
- Every number that came from the API is used as-is (price, quantity, amount).
- Price tier was matched on quantity range, not on an adjacent tier.
- Freight validity was checked against the business date for every option.
- Policy-derived values (payment terms, freight reconfirmation flag, quote
  validity, EXW scope) match the customer's profile and the task's context.
- Stage and status values are mapped to the template's enum vocabulary.
- The output is pure JSON with no surrounding text.

## Reference

For detailed field-level documentation on every API collection, read
[references/api-reference.md](references/api-reference.md). Consult it when you
need to confirm a field name, type, or the exact shape of a collection response
before writing your queries.
