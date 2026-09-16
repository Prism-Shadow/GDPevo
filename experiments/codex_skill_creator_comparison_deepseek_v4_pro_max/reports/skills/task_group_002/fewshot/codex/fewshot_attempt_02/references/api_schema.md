# MedBridge Sales Ops API Reference

Base URL: provided by the task runner as `<TASK_ENV_BASE_URL>` or `BASE_URL`.

All responses are JSON. Use `GET` exclusively. The API is read-only.

## Collections and Endpoints

| Collection | List Endpoint | Single-Record Endpoint |
|---|---|---|
| Root | `GET /api` | — |
| Search | `GET /api/search?q=<text>` | — |
| Customers | `GET /api/customers` | `GET /api/customers/<id>` |
| Products | `GET /api/products` | `GET /api/products/<code>` |
| RFQs | `GET /api/rfqs` | `GET /api/rfqs/<id>` |
| Quotes | `GET /api/quotes` | `GET /api/quotes/<id>` |
| Freight Quotes | `GET /api/freight-quotes` | `GET /api/freight-quotes/<id>` |
| Policies | `GET /api/policies` | `GET /api/policies/<id>` |
| Opportunities | `GET /api/opportunities` | `GET /api/opportunities/<id>` |
| Invoices | `GET /api/invoices` | `GET /api/invoices/<id>` |
| Payments | `GET /api/payments` | `GET /api/payments/<id>` |
| Revenue Journals | `GET /api/revenue-journals` | `GET /api/revenue-journals/<id>` |
| Events | `GET /api/events` | `GET /api/events/<id>` |
| Vouchers | `GET /api/vouchers` | `GET /api/vouchers/<code>` |

## Record Shapes

### Customer
```json
{
  "id": "CUST-XXXX",
  "name": "Customer name",
  "country": "...",
  "region": "...",
  "customer_type": "NGO | Commercial | Government Program",
  "segment": "new_ngo | recurring_ngo | recurring_commercial | government_program | ...",
  "status": "active | prospect",
  "is_recurring": true,
  "payment_profile": "NET_30_AFTER_PO | PREPAY_100 | ...",
  "client_since": "YYYY-MM-DD | null",
  "grant_terms": "...",
  "notes": "...",
  "contacts": [{"name": "...", "email": "...", "phone": "...", "role": "..."}]
}
```

Key decision fields: `segment`, `is_recurring`, `payment_profile`, `customer_type`, `status`.

### Product
```json
{
  "code": "PROD-CODE",
  "article_number": "MB-...",
  "name": "Product display name",
  "family": "...",
  "unit": "kit | module | pack | bundle | case | service",
  "cold_chain_required": true,
  "shelf_life_months": 24,
  "weight_kg": 8.5,
  "cbm": 0.055,
  "components": ["component a", "component b", ...],
  "price_tiers": [
    {
      "min_qty": 1,
      "max_qty": 149,
      "unit_price_usd": 129.50,
      "lead_time_days": 35,
      "lead_time_weeks": 5.0
    },
    {
      "min_qty": 150,
      "max_qty": null,
      "unit_price_usd": 114.00,
      "lead_time_days": 28,
      "lead_time_weeks": 4.0
    },
    ...
  ]
}
```

**Price tier matching:** For a confirmed quantity Q, select the tier where `min_qty <= Q <= max_qty`. When `max_qty` is null, the tier covers `Q >= min_qty`. Use the first matching tier (tiers are ordered). Extract `unit_price_usd`, `lead_time_days`, `shelf_life_months`.

### RFQ
```json
{
  "id": "RFQ-XX-...",
  "customer_id": "CUST-...",
  "status": "open | quoted | closed_lost | superseded | draft | archived",
  "request_type": "indicative_module_quote | product_quote | freight_comparison | module_quote | component_check | budgetary_check | service_quote",
  "incoterm_requested": "EXW | CPT | CIP | DAP | ...",
  "currency": "USD",
  "quote_date": "YYYY-MM-DD",
  "received_date": "YYYY-MM-DD",
  "destination": "...",
  "narrative": "...",
  "requested_modules": [
    {"product_code": "MODULE-A", "quantity": 10},
    ...
  ],
  "component_composition_distractors": ["warning about not splitting modules"]
}
```

The `component_composition_distractors` field warns against splitting modules into component SKUs. Keep quotes at the module level.

### Quote
```json
{
  "id": "Q-XX-...",
  "customer_id": "CUST-...",
  "primary_product_code": "PROD-CODE",
  "quote_date": "YYYY-MM-DD",
  "quote_type": "quote_revision_with_freight | product_quote | module_quote | freight_comparison | ...",
  "incoterm": "EXW plus freight options | EXW | CPT | ...",
  "currency": "USD",
  "status": "revision_requested | sent | draft | advisory_requested",
  "destination": "...",
  "confirmed_quantity": 360,
  "line_items": [
    {
      "line_id": "Q-...-L1",
      "product_code": "PROD-CODE",
      "confirmed_quantity": 360,
      "prior_quote_quantity": 240,
      "prior_unit_price_usd": 124.00,
      "customer_note": "..."
    }
  ],
  "source_notes": "..."
}
```

The `confirmed_quantity` on the quote or its line items is the authoritative quantity. Use `primary_product_code` for single-product quotes. `source_notes` often contains tier guidance.

### Freight Quote
```json
{
  "id": "FR-...",
  "quote_id": "Q-...",
  "mode": "air | sea | road",
  "cost_usd": 16200.00,
  "currency": "USD",
  "origin": "...",
  "destination": "...",
  "forwarder": "...",
  "transit_days_min": 4,
  "transit_days_max": 6,
  "transit_days_text": "4-6 days",
  "valid_until": "YYYY-MM-DD",
  "quote_date": "YYYY-MM-DD",
  "route_risk": "low | medium | high",
  "risk_notes": "...",
  "status": "active | stale | mismatch",
  "cold_chain_support": true,
  "shipment_cbm": 24.0,
  "shipment_weight_kg": 3300.0
}
```

**Linking to quotes:** Use `quote_id` to find freight records. Filter out records whose `status` is `stale` or `mismatch`.

**Validity check:** A freight record is valid on the quote date if `valid_until >= quote_date`. If `valid_until < quote_date`, it is stale/expired.

### Policy
```json
{
  "id": "POL-...",
  "name": "Policy display name",
  "policy_area": "payment_terms | quote_scope | freight | quote_lines | revenue_recognition | quote_validity | incoterms",
  "applies_to": "...",
  "rule": "Descriptive policy rule text",
  "terms_code": "...",
  "effective_date": "YYYY-MM-DD"
}
```

### Opportunity
```json
{
  "id": "OPP-...",
  "customer_id": "CUST-...",
  "opportunity_name": "...",
  "stage": "closed_won | proposal | negotiation",
  "won_amount_usd": 160000.00,
  "won_date": "YYYY-MM-DD",
  "outstanding_amount_usd": 80000.00,
  "currency": "USD",
  "owner": "...",
  "contact": "Contact Name",
  "notes": "...",
  "phases": [
    {
      "phase_id": "...-P1",
      "name": "Phase 1 description",
      "amount_usd": 60000.00,
      "completion_date": "YYYY-MM-DD",
      "invoice_id": "INV-...-P1"
    },
    ...
  ]
}
```

Phases map to invoices by `invoice_id`. Sum of `phases[].amount_usd` should equal `won_amount_usd` for a match check.

### Invoice
```json
{
  "id": "INV-...-P1",
  "invoice_number": "MBI-...-P1",
  "customer_id": "CUST-...",
  "opportunity_id": "OPP-...",
  "phase_id": "...-P1",
  "phase_name": "...",
  "billing_type": "milestone_service",
  "amount_usd": 60000.00,
  "paid_amount_usd": 60000.00,
  "outstanding_amount_usd": 0.00,
  "status": "paid | unpaid | overdue | draft",
  "issue_date": "YYYY-MM-DD",
  "due_date": "YYYY-MM-DD"
}
```

Status values: `paid`, `unpaid`, `overdue`, `draft`. Use `outstanding_amount_usd` for the unpaid portion.

### Payment
```json
{
  "id": "PAY-...-P1",
  "invoice_id": "INV-...-P1",
  "customer_id": "CUST-...",
  "opportunity_id": "OPP-...",
  "amount_usd": 60000.00,
  "method": "wire",
  "payment_date": "YYYY-MM-DD",
  "status": "posted"
}
```

### Revenue Journal
```json
{
  "id": "RJ-...-P1",
  "invoice_id": "INV-...-P1",
  "opportunity_id": "OPP-...",
  "phase_id": "...-P1",
  "amount_usd": 60000.00,
  "debit_account": "Deferred Revenue",
  "credit_account": "Implementation Services Revenue",
  "posted_date": "YYYY-MM-DD",
  "status": "posted"
}
```

Standard journal: debit Deferred Revenue, credit Implementation Services Revenue.

### Event
```json
{
  "id": "EVT-...",
  "name": "Event display name",
  "customer_id": "CUST-...",
  "opportunity_id": "OPP-...",
  "primary_contact": "Contact Name",
  "event_date": "YYYY-MM-DD",
  "status": "confirmed | scheduled | live | completed | tentative",
  "voucher_code": "VOUCHER-CODE",
  "follow_up_owner": "Account Management"
}
```

### Voucher
```json
{
  "code": "VOUCHER-CODE",
  "customer_id": "CUST-...",
  "opportunity_id": "OPP-...",
  "event_id": "EVT-...",
  "description": "...",
  "discount_percent": 100,
  "max_redemptions": 4,
  "redemptions_used": 0,
  "status": "active | draft | expired | disabled",
  "valid_until": "YYYY-MM-DD"
}
```

## Record Cross-Referencing

- **Quotes → Customers:** `quote.customer_id = customer.id`
- **Quotes → Products:** `quote.primary_product_code = product.code` or `quote.line_items[].product_code`
- **Freight → Quotes:** `freight.quote_id = quote.id`
- **RFQs → Customers:** `rfq.customer_id = customer.id`
- **RFQs → Products:** `rfq.requested_modules[].product_code = product.code`
- **Opportunities → Customers:** `opportunity.customer_id = customer.id`
- **Invoices → Opportunities:** `invoice.opportunity_id = opportunity.id`
- **Invoices → Phases:** `invoice.phase_id = phase.phase_id`
- **Payments → Invoices:** `payment.invoice_id = invoice.id`
- **Revenue Journals → Invoices:** `rj.invoice_id = invoice.id`
- **Revenue Journals → Phases:** `rj.phase_id = phase.phase_id`
- **Events → Opportunities:** `event.opportunity_id = opportunity.id`
- **Events → Customers:** `event.customer_id = customer.id`
- **Vouchers → Events:** `voucher.event_id = event.id`
- **Vouchers → Opportunities:** `voucher.opportunity_id = opportunity.id`

## Search

`GET /api/search?q=<text>` returns matching records across all collections. Use as a fallback when a direct ID lookup fails (e.g., a typo in the prompt's ID, or a record ID format mismatch).
