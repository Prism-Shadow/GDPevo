# MedBridge Sales Ops API Reference

Base URL: `<TASK_ENV_BASE_URL>` (provided by the runner, typically `http://task-env:9002`)

Every endpoint returns JSON. All GET endpoints are read-only. The API serves a single
seeded dataset; do not write back.

## Root

`GET /api` — lists collections and allowed endpoints.

## Entity Endpoints

### Customers (`GET /api/customers`, `GET /api/customers/<id>`)

Key fields: `id`, `name`, `customer_type` (NGO / Commercial / Government Program),
`segment` (`recurring_ngo`, `new_ngo`, `recurring_commercial`, `implementation_services`,
`government_program`, `distributor`, `regional_hospital`), `status` (`active`, `prospect`),
`is_recurring` (bool), `payment_profile`, `grant_terms`, `contacts[].name/.email/.phone/.role`,
`region`, `country`, `notes`.

### Products (`GET /api/products`, `GET /api/products/<code>`)

Key fields: `code`, `article_number`, `name`, `family`, `unit`, `weight_kg`, `cbm`,
`cold_chain_required` (bool), `shelf_life_months`, `components[]` (informational only,
do not quote component-level), `price_tiers[]`.

**Price Tiers**: Each tier has `min_qty`, `max_qty` (null = unbounded),
`unit_price_usd`, `lead_time_days`. Select the tier where `confirmed_quantity` falls
inside `[min_qty, max_qty]`. Use the tier's `lead_time_days` and `shelf_life_months`.

### Quotes (`GET /api/quotes`, `GET /api/quotes/<id>`)

Key fields: `id`, `customer_id`, `quote_date`, `status` (`revision_requested`,
`advisory_requested`, `sent`, `draft`), `incoterm`, `confirmed_quantity`,
`primary_product_code`, `destination`, `line_items[]` (each with `product_code`,
`confirmed_quantity`, `prior_quote_quantity`, `prior_unit_price_usd`, `customer_note`),
`source_notes`, `quote_type`.

### RFQs (`GET /api/rfqs`, `GET /api/rfqs/<id>`)

Key fields: `id`, `customer_id`, `status` (`open`, `quoted`, `closed_lost`,
`superseded`, `archived`, `draft`), `request_type` (`indicative_module_quote`,
`product_quote`, `freight_comparison`, `module_quote`, `service_quote`,
`component_check`, `budgetary_check`), `incoterm_requested`, `destination`,
`requested_modules[]` (each with `product_code`, `quantity`),
`component_composition_distractors[]`, `quote_date`, `received_date`.

### Freight Quotes (`GET /api/freight-quotes`, `GET /api/freight-quotes/<id>`)

Key fields: `id`, `quote_id` (links to parent quote), `mode` (`air`, `sea`, `road`),
`cost_usd`, `transit_days_text` / `transit_days_min` / `transit_days_max`,
`valid_until`, `status` (`active`, `stale`, `mismatch`), `route_risk` (`low`, `medium`, `high`),
`risk_notes`, `cold_chain_support` (bool), `forwarder`, `origin`, `destination`,
`shipment_cbm`, `shipment_weight_kg`.

**Critical filter**: Only use freight records where `quote_id` matches the target quote,
`status` is `active` (not `stale` or `mismatch`), and `mode` is one of air/sea/road for
the target quote. Distractor freight records exist with different `quote_id` values,
wrong `shipment_cbm`/`shipment_weight_kg`, or `status: stale`.

**Validity check**: Compare `valid_until` against `quote_date`. A freight quote with
`valid_until` before `quote_date` is stale (expired) regardless of status field.
For `mode: road` with `route_risk: high` or stale validity, flag it.

### Opportunities (`GET /api/opportunities`, `GET /api/opportunities/<id>`)

Key fields: `id`, `customer_id`, `stage` (`closed_won`, `proposal`, `negotiation`),
`won_amount_usd`, `outstanding_amount_usd`, `contact`, `opportunity_name`, `owner`,
`won_date`, `phases[]` (each with `phase_id`, `name`, `amount_usd`, `completion_date`,
`invoice_id`).

### Invoices (`GET /api/invoices`, `GET /api/invoices/<id>`)

Key fields: `id`, `invoice_number`, `customer_id`, `opportunity_id`, `phase_id`,
`amount_usd`, `paid_amount_usd`, `outstanding_amount_usd`, `status` (`paid`, `unpaid`,
`overdue`, `draft`), `due_date`, `issue_date`, `billing_type` (all `milestone_service`).

### Payments (`GET /api/payments`, `GET /api/payments/<id>`)

Key fields: `id`, `invoice_id`, `opportunity_id`, `customer_id`, `amount_usd`,
`payment_date`, `method` (`wire`), `status` (all `posted`).

### Revenue Journals (`GET /api/revenue-journals`, `GET /api/revenue-journals/<id>`)

Key fields: `id`, `invoice_id`, `opportunity_id`, `phase_id`, `amount_usd`,
`debit_account`, `credit_account`, `posted_date`, `status` (all `posted`),
`memo`.

**Revenue recognition logic**: A milestone that is completed and paid must have a
corresponding revenue journal. If missing, it is `MISSING_REVENUE_JOURNAL`.
An unpaid milestone does not need a revenue journal (`NOT_REQUIRED_UNPAID`).

### Events (`GET /api/events`, `GET /api/events/<id>`)

Key fields: `id`, `customer_id`, `opportunity_id`, `name`, `event_date`,
`status` (`confirmed`, `scheduled`, `live`, `completed`, `tentative`),
`voucher_code`, `primary_contact`, `follow_up_owner`.

### Vouchers (`GET /api/vouchers`, `GET /api/vouchers/<code>`)

Key fields: `code`, `event_id`, `opportunity_id`, `customer_id`, `description`,
`discount_percent`, `max_redemptions`, `redemptions_used`, `status` (`active`),
`valid_until`.

### Policies (`GET /api/policies`, `GET /api/policies/<id>`)

Key fields: `id`, `name`, `policy_area`, `rule`, `terms_code`, `applies_to`,
`effective_date`.

### Search (`GET /api/search?q=<text>`)

Full-text search across records. Use for discovery when IDs are unknown.

## Entity Relationships

```
customer (1) ──< quotes (N)
customer (1) ──< rfqs (N)
customer (1) ──< opportunities (N)
customer (1) ──< invoices (N)
customer (1) ──< payments (N)
customer (1) ──< events (N)
customer (1) ──< vouchers (N)

quote (1) ──< freight-quotes (N)   via freight-quotes.quote_id
quote (1) ──< line_items (N)

opportunity (1) ──< phases (N)
opportunity (1) ──< invoices (N)   via invoices.opportunity_id
opportunity (1) ──< events (N)
opportunity (1) ──< vouchers (N)

phase ── invoice (1:1)            via invoices.phase_id
phase ── payment (1:1)            via payments.invoice_id
phase ── revenue-journal (0:1)    via revenue-journals.phase_id

rfq ──< requested_modules (N)     each with product_code, quantity

event ── voucher (1:1)            via events.voucher_code = vouchers.code
```
