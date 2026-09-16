---
name: medbridge-sales-ops
description: Query the MedBridge Sales Ops API to build quote-and-freight decision packages or account-ready engagement reconciliations. Use this skill whenever the user asks for a MedBridge quote, quote revision, freight comparison, RFQ pricing, milestone reconciliation, opportunity reconciliation, revenue recognition check, collection action, event invitation task, or any task that needs to pull and cross-reference records from the shared CRM/quote/logistics/engagement API.
---

# MedBridge Sales Ops

The MedBridge Sales Ops API is a shared CRM, quote, logistics, and milestone
engagement data service for medical supply sales operations. It surfaces
customers, products with quantity-tier pricing, quotes and RFQs, freight quotes,
policies that govern payment terms and freight rules, and milestone-based
engagement records (opportunities, invoices, payments, revenue journals, events,
and vouchers).

Use this skill for two families of task:

1. **Quote and freight decision packages** -- verify a quote or RFQ, look up the
   customer and product catalog, determine EXW pricing from the correct quantity
   tier, pull freight options, check freight validity and route risk, apply
   corporate policies, and recommend a transport mode.
2. **Engagement and account reconciliations** -- reconcile a won opportunity
   against its milestone phases, invoices, payments, and revenue recognition
   journals, detect gaps that need accounting or collection action, and route
   event invitations with voucher controls.

Both families return structured JSON. The user supplies an answer template; you
fill it from API data and business rules, never from guesses.

## API Access

The user provides a task environment base URL (usually as `<TASK_ENV_BASE_URL>`
or `BASE_URL`). All endpoints live under that base URL.

Every collection supports a list endpoint:

```
GET {base}/api/{collection}
```

and a single-record lookup via query parameter on the same path:

```
GET {base}/api/{collection}?id={record_id}
```

The voucher collection uses the `code` field as its lookup key:

```
GET {base}/api/vouchers?code={VOUCHER_CODE}
```

Available collections: `customers`, `products`, `quotes`, `rfqs`,
`freight-quotes`, `policies`, `opportunities`, `invoices`, `payments`,
`revenue-journals`, `events`, `vouchers`.

Always fetch the full list of `policies` first. Policy rules affect payment
terms, freight scope, quote granularity, and revenue recognition decisions
across every task.

## Task Category A: Quote and Freight Decisions

These tasks take a quote or RFQ identifier, a confirmed product and quantity, a
quote date, and an answer template, and produce a filled decision JSON.

### 1. Gather the source records

Start by fetching these collections in parallel. If the task mentions a quote
ID, fetch the quote; if it mentions an RFQ ID, fetch the RFQ. Then fetch the
customer, the product (or products for an RFQ), all freight quotes, and all
policies.

For a **quote revision task**:
- `GET /api/quotes?id=<QUOTE_ID>` -- confirms `primary_product_code`,
  `confirmed_quantity`, `customer_id`, `incoterm`, and source notes.
- `GET /api/customers?id=<CUSTOMER_ID>` -- payment profile, segment, contacts,
  region.
- `GET /api/products?code=<PRODUCT_CODE>` -- price tiers, lead time, shelf
  life, cold-chain flag.
- `GET /api/freight-quotes` and filter on `quote_id == <QUOTE_ID>` -- all
  freight options for this quote.
- `GET /api/policies` -- the full policy catalog.

For an **RFQ task** (indicative module quote, no destination):
- `GET /api/rfqs?id=<RFQ_ID>` -- `requested_modules` array with product codes
  and quantities. Ignore `component_composition_distractors`; quote at module
  level only unless the customer explicitly requests component-level pricing.
- `GET /api/customers?id=<CUSTOMER_ID>`.
- `GET /api/products?code=<CODE>` for each module in the RFQ.
- `GET /api/policies`.
- Do not fetch freight quotes. RFQs without a destination are EXW-only per
  policy `POL-INDICATIVE-EXW`.

### 2. Determine EXW pricing

For each product, scan its `price_tiers` array. A tier applies when:

```
confirmed_quantity >= tier.min_qty AND
(tier.max_qty is null OR confirmed_quantity <= tier.max_qty)
```

Pick the first matching tier (tiers are ordered). Use its `unit_price_usd`,
`lead_time_days`, and the product's `shelf_life_months`.

EXW total = `confirmed_quantity * unit_price_usd`.

For RFQs with multiple modules, compute each line item separately, then sum
line totals into the grand total.

### 3. Determine payment terms

Map the customer's `segment` field through the policies:

| Segment | Default payment terms |
|---------|----------------------|
| `recurring_ngo` | `NET_30_AFTER_PO` |
| `new_ngo` | `PREPAY_100` |
| `recurring_commercial` | `NET_30_AFTER_PO` |

The policy `POL-RECURRING-NGO-PAYMENT` and `POL-NEW-CLIENT-PAYMENT` encode
these rules. Always cross-check the customer's `grant_terms` and `notes` for
overrides.

### 4. Compare freight options (quote tasks only)

For each freight quote linked to the quote ID:

- **validity status** -- `VALID` if `valid_until >= quote_date`; `STALE`
  otherwise. An expired freight quote should not be used without a fresh quote.
- **source_is_stale** -- `true` when `valid_until < quote_date`.
- **risk level** -- map `route_risk` values: `"low"` to `"LOW"`, `"medium"` to
  `"MEDIUM"`, `"high"` to `"HIGH"`.
- **grand total** -- `EXW total + freight_cost_usd`.

### 5. Apply freight policies and recommend a mode

- Policy `POL-FREIGHT-RECONFIRM` (code `RECONFIRM_AT_ORDER`): all freight rates
  need reconfirmation at final order. Set `freight_reconfirmation_required` to
  `true`.
- Check whether every freight option is valid on the quote date. If any
  `valid_until < quote_date`, `all_freight_options_valid_on_quote_date` is
  `false`.
- **Recommended mode**: prefer the lowest-risk mode with a valid freight quote
  that has the lowest cost. Typically SEA is preferred when valid and low-risk
  (cost-effective for non-urgent NGO/commercial shipments). AIR is preferred
  when timing is critical and a valid air quote exists. ROAD is preferred only
  when SEA is unavailable or the destination is landlocked. Never recommend a
  STALE or high-risk freight quote unless no valid option exists; if all are
  problematic, flag the situation in the warnings.
- **Road warnings**: if the road freight quote is expired or has medium/high
  border risk, set `road_quote_invalid_or_stale` and include a warning about
  road viability.
- Policy `POL-EXW-SCOPE`: EXW excludes freight, insurance, import duty, customs
  clearance, and last-mile handling.

### 6. Fill the answer template

Read the answer template provided in the payload. Fill every field from the
data gathered above. Use the exact key names and structure from the template.
Money values use two decimal places. Dates use `YYYY-MM-DD`.

## Task Category B: Engagement and Account Reconciliation

These tasks take an opportunity ID, a customer ID, a contact name, event and
voucher IDs (when linked), a business date, and an answer template. They
produce a reconciliation JSON with accounting and follow-up actions.

### 1. Gather the source records

Fetch in parallel:
- `GET /api/opportunities?id=<OPPORTUNITY_ID>`
- `GET /api/customers?id=<CUSTOMER_ID>`
- `GET /api/invoices` and filter on `opportunity_id == <OPPORTUNITY_ID>`
- `GET /api/payments` and filter on `opportunity_id == <OPPORTUNITY_ID>`
- `GET /api/revenue-journals` and filter on `opportunity_id ==
  <OPPORTUNITY_ID>`
- `GET /api/events?id=<EVENT_ID>` (when an event ID is provided)
- `GET /api/vouchers?code=<VOUCHER_CODE>` (when a voucher code is provided)
- `GET /api/policies`

### 2. Reconcile opportunity and phases

Map the opportunity `stage`:
- `"closed_won"` to `"WON"`
- `"open"` to `"OPEN"`
- `"closed_lost"` to `"LOST"`

Sum the `amount_usd` of every phase in `opportunity.phases`. Compare with
`won_amount_usd`. If the phase total equals the won amount, the opportunity
matches its milestones.

The `outstanding_balance` is `opportunity.outstanding_amount_usd`.

### 3. Reconcile each milestone

For each phase in the opportunity, find the matching invoice by `invoice_id` on
the phase. For each invoice, find the matching payment(s) and revenue journal.

Order milestones by phase number (MS1, MS2, MS3 ascending).

For each milestone determine:

- **invoice_state** -- from the invoice `status`: `"paid"` to `"PAID"`,
  `"unpaid"` to `"OPEN"`.
- **payment_state** -- if invoice is paid and payment total >= invoice amount:
  `"PAID"`; if partial: `"PARTIAL"`; if no payments: `"UNPAID"`.
- **paid_amount** -- sum of payments for this invoice.
- **due_date** -- from the invoice.
- **recognition_status** -- check the revenue-journals collection for a journal
  matching the invoice or phase ID:
  * Paid invoice + revenue journal exists to `"RECOGNIZED"`
  * Paid invoice + no revenue journal to `"MISSING_REVENUE_JOURNAL"`
  * Unpaid invoice to `"NOT_REQUIRED_UNPAID"`

The global **recognition_status**:
- If every paid milestone has a revenue journal: `"COMPLETE_FOR_PAID_MILESTONES"`
- If any paid milestone is missing a revenue journal: `"MISSING_FOR_PAID_MILESTONES"`

### 4. Derive invoice and accounting actions

For each milestone:

- **Revenue recognition gap**: a paid milestone with no revenue journal needs a
  journal entry. The primary accounting action is `RECORD_REVENUE_MSx` (where x
  is the milestone number). The entry debits `DEFERRED_REVENUE` and credits
  `IMPLEMENTATION_SERVICES_REVENUE`. Owner queue is `ACCOUNTING`.
- If all paid milestones are recognized, the accounting action is
  `VERIFY_REVENUE_ONLY`.
- **Collection action**: an unpaid milestone whose `due_date` is in the future
  (relative to the business date) needs `MONITOR_UNPAID_NOT_DUE`. An overdue
  unpaid milestone needs `SEND_COLLECTION_NOTICE`. The collection task belongs
  to `ACCOUNT_MANAGEMENT` and names the contact from the task prompt.

### 5. Derive event and invite actions

For the linked event:
- Map `status`: `"scheduled"` to `"SCHEDULED"`, `"confirmed"` to `"ACTIVE"`,
  `"live"` to `"ACTIVE"`, `"completed"` to `"COMPLETED"`, `"cancelled"` to
  `"CANCELLED"`.
- For the linked voucher: map `status` to uppercase, and use `discount_percent`
  as the discount amount. Use `max_redemptions` as `max_uses`.
- Invite action: if the event is scheduled or active, the action is
  `SEND_BRIEFING_INVITE` (or the template's invite enum). The task is owned by
  `ACCOUNT_MANAGEMENT` and includes the contact name and customer ID.

### 6. Fill the answer template

Read the answer template. Fill every field from verified API data. Use cent-level
numbers for money (two decimal places), ISO `YYYY-MM-DD` dates, stable record
IDs, and the controlled enum values declared in the template. Never invent
values.

## Reference Files

- [references/api-schema.md](references/api-schema.md) -- Field-by-field
  documentation of every collection and its record shape.
- [references/business-rules.md](references/business-rules.md) -- Detailed
  policy application, enum-mapping tables, revenue recognition decision logic,
  and edge-case handling.
