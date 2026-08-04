## When to Use

Use this skill whenever a MedBridge Sales Ops task requires verifying business records across customers, quotes, RFQs, products, freight quotes, policies, opportunities, invoices, payments, revenue journals, events, or vouchers and producing a structured JSON answer from a provided answer template. The skill applies to quote decision packages, indicative RFQ quotes, account reconciliations, and engagement reconciliations.

## Environment and API Setup

### Base URL

The runner supplies the API base URL as `<TASK_ENV_BASE_URL>` or `<BASE_URL>` in the prompt. Substitute this value into every request URL.

### Available Endpoints (all GET)

- `/api` — API root / health check
- `/api/search` — search across entities
- `/api/customers` — list all customers
- `/api/customers/{id}` — single customer by ID
- `/api/products` — list all products
- `/api/products/{code}` — single product by code
- `/api/rfqs` — list all RFQs
- `/api/rfqs/{id}` — single RFQ by ID
- `/api/quotes` — list all quotes
- `/api/quotes/{id}` — single quote by ID
- `/api/freight-quotes` — list all freight quotes
- `/api/freight-quotes/{id}` — single freight quote by ID
- `/api/policies` — list all policies
- `/api/policies/{id}` — single policy by ID
- `/api/opportunities` — list all opportunities
- `/api/opportunities/{id}` — single opportunity by ID
- `/api/invoices` — list all invoices
- `/api/invoices/{id}` — single invoice by ID
- `/api/payments` — list all payments
- `/api/payments/{id}` — single payment by ID
- `/api/revenue-journals` — list all revenue journals
- `/api/revenue-journals/{id}` — single revenue journal by ID
- `/api/events` — list all events
- `/api/events/{id}` — single event by ID
- `/api/vouchers` — list all vouchers
- `/api/vouchers/{code}` — single voucher by code

No POST endpoints are available. All data retrieval is read-only.

## Entity Resolution Rules

### Core Principle

Every entity referenced in the prompt or template must be verified by fetching it from the API. Never assume or fabricate data.

### Resolution Chain by Task Type

**Quote Decision Package** (prompt gives a quote ID):
1. Fetch the quote by ID → yields `customer_id`, `product_code`, `confirmed_quantity`, `quote_date`
2. Fetch the customer by `customer_id` → yields name, policy links
3. Fetch the product by `product_code` → yields catalog tiers (qty ranges, unit_price, lead_time, shelf_life). Match the correct tier by `confirmed_quantity` (the tier whose `min_quantity` ≤ quantity ≤ `max_quantity`)
4. Fetch freight quotes — identify the records linked to the quote/customer/route. Expect modes: AIR, SEA, ROAD (or a subset)
5. Fetch policies — identify customer or quote-level policy records for payment terms, quote basis, and freight reconfirmation rules

**Indicative RFQ Quote** (prompt gives an RFQ ID):
1. Fetch the RFQ by ID → yields `customer_id`, requested product/module codes, quantities
2. Fetch the customer by `customer_id`
3. Fetch each requested product by code → yields catalog tiers, pricing
4. Fetch policies for payment terms and offer validity
5. Do NOT fetch freight quotes (no destination; freight excluded)

**Account Reconciliation** (prompt gives an opportunity ID and customer ID):
1. Fetch the opportunity by ID → yields stage, won_amount, customer_id
2. Fetch the customer by ID → yields name
3. Fetch all invoices — filter/identify those linked to the opportunity (milestone invoices)
4. For each invoice: fetch related payments to determine paid/unpaid status
5. For each invoice: fetch related revenue journal entries to determine recognition status
6. Fetch the event by ID (if referenced) → yields date, voucher link
7. Fetch the voucher by code (if referenced) → yields discount, max_uses, status
8. Verify the contact person exists and is linked to the customer and opportunity

**Engagement Reconciliation** (prompt gives opportunity ID, customer ID, event ID, voucher code):
1-7: Same as Account Reconciliation, plus explicit event/voucher verification
8. Compute accounting actions: if a paid milestone lacks a revenue journal, the action is `RECORD_REVENUE_<milestone>`. If all paid are recognized, `VERIFY_REVENUE_ONLY`.
9. Compute collection actions: if an invoice is unpaid and past due, `SEND_COLLECTION_NOTICE`. If unpaid but not yet due, `MONITOR_UNPAID_NOT_DUE`.
10. Compute event invite actions: if the event is SCHEDULED and voucher is ACTIVE, `SEND_BRIEFING_INVITE`.

## Pricing and Catalog Tiers

Products have quantity-based catalog tiers. Each tier defines:
- `min_quantity` / `max_quantity` — the quantity range for this tier
- `unit_price_usd` — price per unit in USD
- `lead_time_days` — manufacturing/shipping lead time
- `shelf_life_months` — product shelf life

Matching rule: find the tier where `min_quantity ≤ confirmed_quantity ≤ max_quantity`.

## Freight Evaluation Rules

### Mode-Specific Characteristics

Each freight quote carries:
- `mode`: AIR, SEA, or ROAD
- `freight_cost_usd`: transport cost
- `transit_days`: estimated transit time
- `valid_until`: expiration date of the freight quote
- `risk_level`: LOW, MEDIUM, or HIGH
- `risk_flag`: NONE, MEDIUM_BORDER_RISK, or other route-specific flags

### Validity and Staleness

- A freight option is **valid** on the quote date if `valid_until ≥ quote_date`.
- A freight option is **stale/invalid** if `valid_until < quote_date`.
- `all_freight_options_valid_on_quote_date` is `true` only when every retrieved freight option passes the validity check against the quote date.
- `freight_reconfirmation_required` is `true` when any freight option is stale, OR when the policy record mandates reconfirmation.

### Mode Recommendation

Recommend the lowest-risk valid mode. Precedence: AIR > SEA > ROAD (lower risk preferred). If multiple modes have the same risk level, prefer the one with the lowest cost among them.

### EXW-Plus-Freight Pricing

- `exw_total_usd = confirmed_quantity × unit_price_usd` (from the matched catalog tier)
- `grand_total_usd = exw_total_usd + freight_cost_usd` (per freight option)

## Policy Resolution

Policy records define account-level controls. When available:
- `payment_terms`: e.g., `PREPAY_100`, `NET_30`
- `quote_basis`: e.g., `EXW`, `EXW_ONLY`
- `freight_reconfirmation_required`: boolean flag from policy
- `offer_validity_days`: number of days the quote is valid
- `who_documentation_required`: boolean for WHO documentation needs

When a policy record is absent, derive payment terms from the customer record if available, or default to `PREPAY_100`.

## Revenue Recognition Rules

For each milestone invoice:
1. Check payment status: does a payment record exist? What is the paid amount?
2. If an invoice has any payment (partial or full), check whether a revenue journal entry exists for that invoice/milestone.
3. Recognition statuses:
   - `RECOGNIZED`: invoice has a payment AND a revenue journal entry exists
   - `MISSING_REVENUE_JOURNAL` / `REQUIRED_MISSING`: invoice has a payment BUT no revenue journal entry exists
   - `NOT_REQUIRED_UNPAID`: invoice has no payments

Global recognition determination:
- `COMPLETE_FOR_PAID_MILESTONES`: every paid invoice has a revenue journal
- `MISSING_FOR_PAID_MILESTONES`: at least one paid invoice lacks a revenue journal
- `NOT_REQUIRED`: no invoices have payments

## Accounting and Collection Actions

### Accounting Action

- If a paid milestone lacks a revenue journal → `RECORD_REVENUE_<milestone_id>`, debit `DEFERRED_REVENUE`, credit `IMPLEMENTATION_SERVICES_REVENUE`, owner `ACCOUNTING`
- If all paid milestones are recognized → `VERIFY_REVENUE_ONLY`, milestone `NONE`, amounts 0, debit/credit `NONE`, owner `ACCOUNTING`
- If nothing is paid → `NO_ACCOUNTING_ACTION`, owner `NONE`

### Collection Action

- If an invoice is unpaid with a due date in the past (relative to the current business date) → `SEND_COLLECTION_NOTICE`, owner `COLLECTIONS`
- If an invoice is unpaid but the due date is in the future → `MONITOR_UNPAID_NOT_DUE`, owner `ACCOUNT_MANAGEMENT`
- If everything is paid → `NO_COLLECTION_ACTION`, owner `NONE`

## Event and Voucher Rules

- Fetch events by event ID. Check `event_status`: SCHEDULED, ACTIVE, COMPLETED, CANCELLED.
- Fetch vouchers by voucher code. Check `voucher_status`: ACTIVE, DRAFT, EXPIRED, DISABLED.
- An invite should be sent (`SEND_BRIEFING_INVITE`) when the event is SCHEDULED and the voucher is ACTIVE.
- The invite task owner is `EVENTS`, contact and customer ID come from the reconciliation.

## Output Rules

### JSON-Only

Return only valid JSON matching the provided `answer_template.json`. Never include markdown fences, prose, or explanatory text outside the JSON structure.

### Data Formatting

- **Dates**: ISO `YYYY-MM-DD` format. Use `null` for absent dates.
- **Money**: Numbers with exactly two decimal places (e.g., `1500.00`).
- **IDs**: Use stable record IDs exactly as returned by the API.
- **Enums**: Use only the controlled values declared in the template's enum annotations. Do not invent new values.
- **Booleans**: Use JSON `true`/`false` literals.
- **Nulls**: Use `null` when a value is inapplicable or unavailable; do not use empty strings or zero as substitutes.

### Template Fidelity

Match the template structure exactly: field names, nesting, array ordering, and enum sets. Do not add, remove, or rename fields. If the template shows three freight options (AIR, SEA, ROAD), output three objects even if fewer were retrieved — mark missing ones with empty/default values.

## Workflow Checklist

Before producing output, verify:
1. Every entity ID from the prompt has been fetched and cross-checked via the API
2. Catalog tier is correctly matched to the confirmed quantity
3. Freight validity is checked against the quote date (or current business date)
4. Policy records have been consulted for payment terms and reconfirmation flags
5. Revenue journal coverage has been checked for every paid milestone
6. All monetary values are in USD with exactly 2 decimal places
7. The output passes structural validation against the answer template
8. No markdown or explanatory text surrounds the JSON
