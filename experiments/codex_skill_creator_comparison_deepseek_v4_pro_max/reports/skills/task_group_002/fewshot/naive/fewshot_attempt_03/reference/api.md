# MedBridge Sales Ops API Field Reference

Base URL: `$BASE_URL` as provided by the task runner (typically `http://task-env:9002`).

All endpoints are read-only GET with no credentials.

## Endpoints

### GET /health
Returns service status. Always call first.
```json
{ "ok": true, "service": "MedBridge Sales Ops", "status": "ok" }
```

### GET /api
Lists available collections and endpoints.

### GET /api/search?q=<text>
Full-text search across all collections. Returns matching records from every
collection. Use when the prompt provides partial names or codes.

---

## Collections

### /api/customers

List fields:
- `id` — stable customer ID (e.g. `CUST-XXXX`)
- `name` — display name
- `customer_type` — `NGO`, `Commercial`, `Government Program`
- `segment` — `recurring_ngo`, `new_ngo`, `recurring_commercial`, `government_program`, `implementation_services`, `distributor`, `regional_hospital`
- `status` — `active`, `prospect`
- `is_recurring` — boolean
- `payment_profile` — payment terms description
- `country`, `region`
- `grant_terms` — grant-related restrictions
- `contacts[]` — array with `name`, `email`, `phone`, `role`
- `client_since` — date or null
- `notes` — free-text notes

### /api/products

List fields:
- `code` — product code (e.g. `WC-KIT-X`, `IEHK-XXXX`)
- `article_number` — ERP article number
- `name` — display name
- `family` — product family (e.g. `wound_care`, `emergency_health_kit`, `lab_diagnostics`)
- `unit` — `kit`, `module`, `pack`, `bundle`, `case`, `service`
- `weight_kg`, `cbm`
- `cold_chain_required` — boolean
- `shelf_life_months` — integer or null (null for services)
- `components[]` — component descriptions (not for itemized pricing)
- `price_tiers[]` — array of tier objects:
  - `min_qty`, `max_qty` (null means no upper bound)
  - `unit_price_usd`
  - `lead_time_days`
  - `lead_time_weeks`

### /api/quotes

List fields:
- `id` — quote ID (e.g. `Q-TR-XXXXXXX`, `Q-TR-XXXXXXX`)
- `quote_type` — `quote_revision_with_freight`, `module_quote_with_freight_advisory`, etc.
- `quote_date` — ISO date
- `currency` — `USD`
- `status` — `revision_requested`, `advisory_requested`, `sent`, `draft`
- `customer_id`
- `primary_product_code`
- `incoterm` — e.g. `EXW plus freight options`, `EXW only`
- `destination` — destination text
- `confirmed_quantity` — integer or null
- `line_items[]` — array:
  - `line_id`, `product_code`, `confirmed_quantity`
  - `prior_quote_quantity`, `prior_unit_price_usd` (if revision)
  - `customer_note`
- `source_notes` — hints about tier selection and distractor alerts
- `component_composition_distractors[]` — distractor warnings

### /api/rfqs

List fields:
- `id` — RFQ ID (e.g. `RFQ-TR-XXXXXXX`)
- `customer_id`
- `status` — `open`, `quoted`, `closed_lost`, `superseded`, `archived`, `draft`
- `quote_date` — ISO date
- `received_date` — ISO date
- `currency` — `USD`
- `incoterm_requested` — e.g. `EXW`, `CPT`, `DAP`
- `destination` — string or "Destination pending ..."
- `request_type` — `indicative_module_quote`, `product_quote`, etc.
- `narrative` — text description
- `requested_modules[]` — array:
  - `product_code`, `quantity`
- `component_composition_distractors[]` — distractor warnings

### /api/freight-quotes

List fields:
- `id` — freight ID (e.g. `FR-WC-AIR`, `FR-LD-SEA`)
- `quote_id` — parent quote ID
- `mode` — `air`, `sea`, `road`
- `status` — `active`, `stale`, `mismatch`
- `cost_usd` — freight cost
- `currency` — `USD`
- `transit_days_min`, `transit_days_max`, `transit_days_text`
- `valid_until` — ISO date
- `quote_date` — ISO date
- `origin`, `destination`
- `forwarder` — carrier name
- `route_risk` — `low`, `medium`, `high`
- `risk_notes` — free-text risk description
- `cold_chain_support` — boolean
- `shipment_cbm`, `shipment_weight_kg` — dimensions for distractor detection

### /api/policies

List fields:
- `id` — policy ID (e.g. `POL-NEW-CLIENT-PAYMENT`)
- `name` — display name
- `policy_area` — `payment_terms`, `quote_scope`, `freight`, `quote_lines`, `revenue_recognition`, `quote_validity`, `incoterms`
- `rule` — plain-language rule
- `terms_code` — machine-readable code
- `applies_to` — scope description
- `effective_date` — ISO date

### /api/opportunities

List fields:
- `id` — opportunity ID (e.g. `OPP-TR-XXXXXXX`)
- `customer_id`
- `opportunity_name` — display name
- `stage` — `closed_won`, `proposal`, `negotiation`
- `won_amount_usd` — total won amount
- `won_date` — ISO date or null
- `currency` — `USD`
- `outstanding_amount_usd` — amount still unpaid
- `contact` — primary contact name
- `owner` — internal owner
- `notes` — free-text
- `phases[]` — array:
  - `phase_id` — e.g. `HEL-P1`, `MER-P2`
  - `name` — phase description
  - `amount_usd` — phase amount
  - `completion_date` — ISO date or null
  - `invoice_id` — linked invoice ID

### /api/invoices

List fields:
- `id` — invoice ID (e.g. `INV-HELIOS-P1`)
- `invoice_number` — display number
- `customer_id`
- `opportunity_id`
- `phase_id` — links to opportunity phase
- `phase_name` — phase description
- `billing_type` — `milestone_service`
- `amount_usd` — invoice total
- `paid_amount_usd` — amount received
- `outstanding_amount_usd` — unpaid balance
- `status` — `paid`, `unpaid`, `overdue`, `draft`
- `issue_date`, `due_date` — ISO dates

### /api/payments

List fields:
- `id` — payment ID
- `invoice_id` — linked invoice
- `customer_id`
- `opportunity_id`
- `amount_usd` — payment amount
- `method` — `wire`
- `payment_date` — ISO date
- `reference` — wire reference
- `status` — `posted`

### /api/revenue-journals

List fields:
- `id` — journal ID
- `invoice_id` — linked invoice
- `opportunity_id`
- `phase_id` — links to opportunity phase
- `amount_usd` — recognized amount
- `debit_account` — always `Deferred Revenue`
- `credit_account` — always `Implementation Services Revenue`
- `memo` — description
- `posted_date` — ISO date
- `status` — `posted`

### /api/events

List fields:
- `id` — event ID (e.g. `EVT-MERIDIAN-BRIEFING`)
- `name` — display name
- `customer_id`
- `opportunity_id`
- `event_date` — ISO date
- `status` — `scheduled`, `confirmed`, `live`, `completed`, `tentative`
- `primary_contact` — contact name
- `voucher_code` — linked voucher
- `follow_up_owner` — owner queue

### /api/vouchers

List fields:
- `code` — voucher code (e.g. `VOUCHERXXXX`)
- `customer_id`
- `opportunity_id`
- `event_id` — linked event
- `description` — voucher description
- `discount_percent` — discount value (an integer percentage)
- `max_redemptions` — max uses
- `redemptions_used` — current count
- `status` — `active`, `draft`, `expired`, `disabled`
- `valid_until` — ISO date
