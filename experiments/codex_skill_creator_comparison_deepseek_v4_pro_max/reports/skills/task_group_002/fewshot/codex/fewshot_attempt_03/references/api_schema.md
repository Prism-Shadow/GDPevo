## Endpoints and Data Model

### Base URL

`<TASK_ENV_BASE_URL>` — provided by the task runner as the base URL.

### List endpoints (GET /api/{collection})

All return `{ "collection": "...", "count": N, "records": [...] }`.

| Collection | Key fields per record |
|---|---|
| customers | id, name, country, customer_type, segment, payment_profile, status, contacts[], grant_terms, is_recurring |
| products | code, article_number, name, family, unit, price_tiers[], shelf_life_months, cold_chain_required, components[], weight_kg, cbm |
| quotes | id, customer_id, quote_date, primary_product_code, confirmed_quantity, currency, incoterm, status, line_items[], source_notes, destination |
| rfqs | id, customer_id, quote_date, status, request_type, incoterm_requested, destination, requested_modules[], narrative, component_composition_distractors[] |
| freight-quotes | id, quote_id, mode, cost_usd, transit_days_text, transit_days_min, transit_days_max, valid_until, route_risk, status, cold_chain_support, risk_notes |
| policies | id, name, policy_area, applies_to, rule, terms_code |
| opportunities | id, customer_id, contact, stage, won_amount_usd, currency, phases[], outstanding_amount_usd |
| invoices | id, invoice_number, opportunity_id, customer_id, phase_id, phase_name, amount_usd, paid_amount_usd, outstanding_amount_usd, status, due_date, billing_type |
| payments | id, invoice_id, customer_id, opportunity_id, amount_usd, payment_date, status, method |
| revenue-journals | id, invoice_id, opportunity_id, phase_id, amount_usd, debit_account, credit_account, status, posted_date |
| events | id, customer_id, opportunity_id, event_date, name, status, voucher_code, primary_contact |
| vouchers | code, customer_id, opportunity_id, event_id, discount_percent, max_redemptions, redemptions_used, status, valid_until |

### Lookup endpoints (GET /api/{collection}/{id})

Use for individual entities:
- `/api/customers/<id>` — by customer id string
- `/api/products/<code>` — by product code string
- `/api/quotes/<id>` — by quote id
- `/api/rfqs/<id>` — by RFQ id
- `/api/freight-quotes/<id>` — by freight id string
- `/api/policies/<id>` — by policy id
- `/api/opportunities/<id>` — by opportunity id
- `/api/invoices/<id>` — by invoice id
- `/api/payments/<id>` — by payment id
- `/api/revenue-journals/<id>` — by journal id
- `/api/events/<id>` — by event id
- `/api/vouchers/<code>` — by voucher code

### Cross-collection filtering

The API provides no query parameters beyond `/api/search?q=`. To find related records, fetch the collection list and filter client-side by the linking field:

- Freight quotes for a quote: GET `/api/freight-quotes`, filter by `quote_id`
- Invoices for an opportunity: GET `/api/invoices`, filter by `opportunity_id`
- Payments for an opportunity: GET `/api/payments`, filter by `opportunity_id`
- Revenue journals for an opportunity: GET `/api/revenue-journals`, filter by `opportunity_id`
- Events for an opportunity: GET `/api/events`, filter by `opportunity_id` or `customer_id`
- Vouchers for an opportunity: GET `/api/vouchers`, filter by `opportunity_id` or `event_id`

### Price Tier Matching

Products have `price_tiers[]` arrays. Each tier has `min_qty`, `max_qty` (nullable), `unit_price_usd`, `lead_time_days`, and `shelf_life_months`. To find the active tier for a given quantity:

1. Find the tier where `min_qty <= confirmed_quantity` AND `max_qty >= confirmed_quantity` (or `max_qty` is null).
2. Use that tier's `unit_price_usd`, `lead_time_days`, and `shelf_life_months`.

The product-level `shelf_life_months` is a summary; prefer the tier-specific value when a tier is matched.

### Opportunity Stages

The API uses string stage values:
- `closed_won` → treat as WON
- `open` / `negotiation` / `proposal` → treat as OPEN
- `closed_lost` → treat as LOST

### Invoice Statuses

- `paid` — fully paid
- `unpaid` — issued, not yet due or due but unpaid
- `overdue` — issued, past due, unpaid

### Freight Statuses and Risk

Freight records have:
- `status`: `active` (still valid) or `stale` (expired)
- `route_risk`: `low`, `medium`, `high`
- `valid_until`: date string; compare against quote/reference date

A freight option is VALID when `valid_until >= quote_date` AND `status != "stale"`. It is STALE/expired otherwise.
