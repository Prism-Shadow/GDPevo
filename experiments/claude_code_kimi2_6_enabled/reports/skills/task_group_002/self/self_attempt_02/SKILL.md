# MedBridge Sales Ops API Skill

## Overview

This skill covers interacting with the MedBridge Sales Ops API to produce two types of decision packages:
1. **Quote Decision Package** — pricing, freight comparison, transport recommendation, and policy warnings.
2. **Engagement Reconciliation** — opportunity-to-milestone reconciliation, revenue recognition, invoice/payment status, and CRM follow-up routing.

The API is read-only. Return only valid JSON matching the provided `answer_template.json`.

---

## API Base URL

Use the base URL provided by the environment:
- `GDPEVO_ENV_BASE_URL` or `API_BASE_URL` (e.g., `http://34.46.77.124:8002`)
- **Do not** use `localhost` or `127.0.0.1` unless the remote URL itself points there.

### Discovery Endpoint
`GET /api` returns the list of collections and supported endpoints. Collections:
- `customers`, `events`, `freight-quotes`, `invoices`, `opportunities`, `payments`, `policies`, `products`, `quotes`, `revenue-journals`, `rfqs`, `vouchers`
- `GET /api/search?q=<text>` for free-text search

### Access Patterns
- List all: `GET /api/<collection>` → `{ collection, count, records: [...] }`
- By ID: `GET /api/<collection>/<id>` → single record or `{ error, message }`

---

## Task Type 1: Quote Decision Package

### Required API Calls
1. `GET /api/quotes/<quote_id>` — confirmed quantity, product code, customer_id, quote_date, status
2. `GET /api/customers/<customer_id>` — customer name, region, payment terms overrides
3. `GET /api/products/<product_code>` — price tiers, lead time, shelf life
4. `GET /api/freight-quotes` — filter to those with `quote_id` matching the target quote
5. `GET /api/policies` — global payment terms, freight reconfirmation rules

### Calculation Rules

#### Pricing
- Select the **catalog tier** from `product.price_tiers` where `confirmed_quantity` falls within `[min_qty, max_qty]` (inclusive; `max_qty: null` means unbounded upper).
- `exw_total_usd = confirmed_quantity * selected_tier.unit_price_usd`
- Round to **two decimal places**.
- Payment terms come from `policies` (look for `payment_terms` field, typically under a policy record).

#### Freight Options
For each `freight-quotes` record tied to the quote:
- `grand_total_usd = exw_total_usd + freight_cost_usd` (two decimals)
- `validity_status`:
  - `"valid"` if `status == "active"` AND `valid_until` ≥ current business date
  - `"expired"` if `valid_until` < current business date
  - `"stale"` if `status == "stale"` or status indicates stale/mismatch
- `source_is_stale = true` when `status != "active"` (e.g., `"stale"`, `"mismatch"`)
- `customs_border_risk` = `route_risk` value (low / medium / high)
- `transit_days` = `transit_days_text` (e.g., `"4-6 days"`)

#### Transport Recommendation
- Prefer **active** freight quotes.
- Among active quotes, prefer **lowest `route_risk`** then shortest transit.
- If the road option is stale/invalid or has high border risk, flag it.
- `freight_reconfirmation_required = true` when:
  - Any selected/active freight has `valid_until` close to or before the current date, OR
  - Policy explicitly requires reconfirmation, OR
  - A stale road quote exists and was previously considered.

#### Warnings
- `road_quote_invalid_or_stale` — true if the road freight quote for this shipment is stale/expired or has high risk.
- `freight_warning` — human-readable summary of any risk/validity issue.
- `policy_terms` — copy relevant payment terms and reconfirmation flags from policies.

---

## Task Type 2: Engagement Reconciliation

### Required API Calls
1. `GET /api/opportunities/<opportunity_id>` — won amount, phases, outstanding amount, contact, stage
2. `GET /api/customers/<customer_id>` — customer name
3. `GET /api/invoices` — filter by `customer_id` or `opportunity_id`
4. `GET /api/payments` — filter by `customer_id` or `opportunity_id`
5. `GET /api/revenue-journals` — filter by `opportunity_id`
6. `GET /api/events` and `GET /api/vouchers` — as needed for event/voucher follow-up

### Reconciliation Logic

#### Milestone Mapping
- Opportunity `phases` array maps to milestones. Each phase has `phase_id`, `amount_usd`, `invoice_id`, `completion_date`.
- Order phases by their natural order (e.g., P1 → MS1, P2 → MS2, P3 → MS3).

#### Invoice & Payment State per Milestone
For each phase:
1. Find invoice by `phase.invoice_id` in the invoices collection.
2. Find payment(s) matching `invoice_id` or `customer_id`.
3. Determine:
   - `invoice_state`: `PAID` | `OPEN` | `VOID` | `UNKNOWN`
   - `payment_state`: `PAID` | `PARTIAL` | `UNPAID` | `UNKNOWN`
   - `paid_amount`: sum of payments for this invoice (two decimals)
   - `due_date`: from invoice record (`due_date` field), or `null`

#### Revenue Recognition Status
For each phase:
- `RECOGNIZED` — if there is a revenue-journal record with matching `phase_id` and status `"posted"`.
- `MISSING_REVENUE_JOURNAL` — if the milestone is **paid** (or mostly paid) but no matching revenue-journal exists.
- `NOT_REQUIRED_UNPAID` — if the milestone is unpaid; no recognition needed yet.
- `UNKNOWN` — if data is ambiguous.

#### Opportunity-Level Checks
- `phase_total_amount` = sum of all phase `amount_usd`
- `opportunity_matches_phase_total` = `abs(won_amount - phase_total_amount) < 0.01`
- `total_paid_amount` = sum of all milestone `paid_amount`
- `outstanding_balance` = `won_amount - total_paid_amount` (or from opportunity `outstanding_amount_usd` if provided)

#### Follow-Up Routing (invoice_actions)
- `primary_accounting_action`:
  - `RECORD_REVENUE_MS2` — if a paid milestone (typically MS2) is missing a revenue journal.
  - `VERIFY_REVENUE_ONLY` — if revenue journals exist for all paid milestones but need verification.
  - `NO_ACCOUNTING_ACTION` — otherwise.
- `collection_action`:
  - `SEND_COLLECTION_NOTICE` — if a milestone is unpaid AND past due date.
  - `MONITOR_UNPAID_NOT_DUE` — if unpaid but not yet due.
  - `NO_COLLECTION_ACTION` — if all paid.

#### Event & Voucher Actions (event_actions)
- Look up event by `event_id` and voucher by `voucher_code`.
- `event_status` mapping: `scheduled` → `SCHEDULED`, `confirmed` → `ACTIVE`, `live` → `ACTIVE`, `completed` → `COMPLETED`, `cancelled` → `CANCELLED`, `tentative` → `UNKNOWN`.
- `voucher_status` mapping: `active` → `ACTIVE`, `draft` → `DRAFT`, `expired` → `EXPIRED`, `disabled` → `DISABLED`.
- `invite_action`:
  - `SEND_BRIEFING_INVITE` — if event is active/scheduled and voucher is active.
  - `VERIFY_INVITE_SENT` — if event status suggests invite may already be sent.
  - `NO_INVITE_ACTION` — if event is completed/cancelled or voucher is expired.

---

## Common Pitfalls

1. **Do not use localhost** — Always use the remote base URL from `environment_access.md`.
2. **Currency precision** — All USD amounts must have exactly two decimal places in JSON output.
3. **Freight quote filtering** — Only include freight quotes whose `quote_id` matches the target quote. Distractor quotes exist in the collection.
4. **Stale vs active** — A freight quote can have `status: "active"` but `valid_until` in the past; treat as expired.
5. **Phase-to-milestone mapping** — The API uses `phases` with IDs like `HEL-P1`; map these to `MS1`, `MS2`, `MS3` in output ordered ascending.
6. **Payment aggregation** — Multiple payment records may exist per invoice; sum them.
7. **Do not include markdown or narrative** outside the JSON response.
8. **Enum values** — Match the exact enum strings in the answer template (case-sensitive).

---

## Data Model Quick Reference

### Quote
```json
{
  "id": "Q-...",
  "customer_id": "CUST-...",
  "quote_date": "YYYY-MM-DD",
  "confirmed_quantity": 360,
  "primary_product_code": "WC-KIT-A",
  "status": "revision_requested",
  "incoterm": "EXW plus freight options",
  "line_items": [{ "product_code": "...", "confirmed_quantity": 360, "prior_unit_price_usd": 124.0 }]
}
```

### Product
```json
{
  "code": "WC-KIT-A",
  "price_tiers": [{ "min_qty": 1, "max_qty": 149, "unit_price_usd": 129.5, "lead_time_days": 35 }],
  "shelf_life_months": 36
}
```

### Freight Quote
```json
{
  "id": "FR-...",
  "quote_id": "Q-...",
  "mode": "air|sea|road",
  "cost_usd": 16200.0,
  "status": "active|stale|mismatch",
  "valid_until": "YYYY-MM-DD",
  "route_risk": "low|medium|high",
  "transit_days_text": "4-6 days",
  "cold_chain_support": true|false
}
```

### Opportunity
```json
{
  "id": "OPP-...",
  "customer_id": "CUST-...",
  "stage": "closed_won|...",
  "won_amount_usd": 120000.0,
  "outstanding_amount_usd": 70000.0,
  "contact": "Name",
  "phases": [
    { "phase_id": "HEL-P1", "amount_usd": 50000.0, "invoice_id": "INV-...", "completion_date": "YYYY-MM-DD" }
  ]
}
```

### Invoice
```json
{
  "id": "INV-...",
  "customer_id": "CUST-...",
  "opportunity_id": "OPP-...",
  "phase_id": "HEL-P1",
  "amount_usd": 50000.0,
  "status": "issued|paid|void",
  "due_date": "YYYY-MM-DD"
}
```

### Payment
```json
{
  "id": "PAY-...",
  "invoice_id": "INV-...",
  "customer_id": "CUST-...",
  "amount_usd": 50000.0,
  "payment_date": "YYYY-MM-DD"
}
```

### Revenue Journal
```json
{
  "id": "RJ-...",
  "opportunity_id": "OPP-...",
  "phase_id": "HEL-P1",
  "invoice_id": "INV-...",
  "amount_usd": 50000.0,
  "status": "posted",
  "debit_account": "Deferred Revenue",
  "credit_account": "Implementation Services Revenue"
}
```

### Event
```json
{
  "id": "EVT-...",
  "opportunity_id": "OPP-...",
  "customer_id": "CUST-...",
  "status": "scheduled|confirmed|live|completed|cancelled|tentative",
  "event_date": "YYYY-MM-DD",
  "primary_contact": "Name",
  "voucher_code": "CODE"
}
```

### Voucher
```json
{
  "code": "CODE",
  "event_id": "EVT-...",
  "opportunity_id": "OPP-...",
  "customer_id": "CUST-...",
  "status": "active",
  "discount_percent": 50,
  "max_redemptions": 20,
  "redemptions_used": 0,
  "valid_until": "YYYY-MM-DD"
}
```
