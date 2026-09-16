
## API Reference

### Health

`GET /api` -- returns collection list, endpoints, and service metadata.

### Search

`GET /api/search?q=<text>` -- case-insensitive search across all collections. Returns matching records with their collection name and id.

### Customers

`GET /api/customers` -- list all.
`GET /api/customers/{id}` -- single record.

Fields: `id`, `name`, `country`, `region`, `customer_type`, `status`, `segment`, `is_recurring`, `client_since`, `payment_profile`, `grant_terms`, `notes`, `contacts[]` (array of `{name, email, phone, role}`).

Common segments: `recurring_ngo`, `recurring_commercial`, `new_ngo`, `implementation_services`.
Common payment profiles: `NET_30_AFTER_PO`, `NEW_CLIENT_REVIEW`, `MILESTONE_BILLING`.

### Products

`GET /api/products` -- list all.
`GET /api/products/{code}` -- single record.

Fields: `code`, `article_number`, `name`, `family`, `unit`, `weight_kg`, `cbm`, `cold_chain_required`, `shelf_life_months`, `components[]`, `price_tiers[]`.

`price_tiers[]` elements: `min_qty`, `max_qty` (nullable), `unit_price_usd`, `lead_time_days`, `lead_time_weeks`.

### Quotes

`GET /api/quotes` -- list all.
`GET /api/quotes/{id}` -- single record.

Fields: `id`, `customer_id`, `quote_date`, `currency`, `incoterm`, `status`, `quote_type`, `primary_product_code`, `confirmed_quantity`, `destination`, `source_notes`, `line_items[]`.

`line_items[]` elements: `line_id`, `product_code`, `confirmed_quantity` or `requested_quantity`, `prior_quote_quantity` (optional), `prior_unit_price_usd` (optional), `customer_note`.

### Freight Quotes

`GET /api/freight-quotes` -- list all.
`GET /api/freight-quotes/{id}` -- single record.

Fields: `id`, `quote_id`, `mode` (air/sea/road), `origin`, `destination`, `forwarder`, `cost_usd`, `currency`, `transit_days_text`, `transit_days_min`, `transit_days_max`, `valid_until`, `quote_date`, `status`, `route_risk` (low/medium/high), `risk_notes`, `cold_chain_support`, `shipment_weight_kg`, `shipment_cbm`.

### RFQs

`GET /api/rfqs` -- list all.
`GET /api/rfqs/{id}` -- single record.

Fields: `id`, `customer_id`, `quote_date`, `received_date`, `request_type`, `incoterm_requested`, `currency`, `destination`, `status`, `narrative`, `requested_modules[]`, `component_composition_distractors[]`.

`requested_modules[]` elements: `product_code`, `quantity`.

### Opportunities

`GET /api/opportunities` -- list all.
`GET /api/opportunities/{id}` -- single record.

Fields: `id`, `customer_id`, `opportunity_name`, `stage` (open/closed_won/closed_lost), `won_amount_usd`, `won_date`, `outstanding_amount_usd`, `currency`, `contact`, `owner`, `notes`, `phases[]`.

`phases[]` elements: `phase_id`, `name`, `amount_usd`, `completion_date`, `invoice_id`.

### Invoices

`GET /api/invoices` -- list all.
`GET /api/invoices/{id}` -- single record.

Fields: `id`, `invoice_number`, `customer_id`, `opportunity_id`, `phase_id`, `phase_name`, `billing_type`, `amount_usd`, `paid_amount_usd`, `outstanding_amount_usd`, `status` (paid/unpaid/partial), `issue_date`, `due_date`.

### Payments

`GET /api/payments` -- list all.
`GET /api/payments/{id}` -- single record.

Fields: `id`, `customer_id`, `opportunity_id`, `invoice_id`, `amount_usd`, `payment_date`, `method`, `reference`, `status` (posted/pending).

### Revenue Journals

`GET /api/revenue-journals` -- list all.
`GET /api/revenue-journals/{id}` -- single record.

Fields: `id`, `opportunity_id`, `invoice_id`, `phase_id`, `amount_usd`, `debit_account`, `credit_account`, `memo`, `posted_date`, `status` (posted/pending).

### Events

`GET /api/events` -- list all.
`GET /api/events/{id}` -- single record.

Fields: `id`, `name`, `customer_id`, `opportunity_id`, `event_date`, `primary_contact`, `voucher_code`, `follow_up_owner`, `status` (scheduled/confirmed/live/completed/tentative).

### Vouchers

`GET /api/vouchers` -- list all.
`GET /api/vouchers/{code}` -- single record.

Fields: `code`, `customer_id`, `opportunity_id`, `event_id`, `description`, `discount_percent`, `max_redemptions`, `redemptions_used`, `valid_until`, `status` (active/draft/expired/disabled).

### Policies

`GET /api/policies` -- list all.

Fields: `id`, `name`, `policy_area`, `applies_to`, `rule`, `terms_code`, `effective_date`.

Key policies referenced across all tasks:

| Policy ID | Area | Terms Code | Rule |
|---|---|---|---|
| POL-RECURRING-NGO-PAYMENT | payment_terms | NET_30_AFTER_PO | Recurring NGO -> NET_30_AFTER_PO |
| POL-NEW-CLIENT-PAYMENT | payment_terms | PREPAY_100 | New NGO -> PREPAY_100 |
| POL-INDICATIVE-EXW | quote_scope | EXW_ONLY_EXCLUDE_FREIGHT | No destination -> EXW only |
| POL-FREIGHT-RECONFIRM | freight | RECONFIRM_AT_ORDER | Freight rates need reconfirmation |
| POL-MODULE-GRANULARITY | quote_lines | MODULE_LINES | Keep to module level |
| POL-REVREC | revenue_recognition | RECOGNIZE_PAID_COMPLETE_MILESTONES | Recognize paid completed milestones |
| POL-QUOTE-VALIDITY | quote_validity | QUOTE_VALID_30_DAYS | 30-day catalog quote validity |
| POL-EXW-SCOPE | incoterms | EXW_EXCLUSIONS | EXW excludes freight/insurance/duty |
