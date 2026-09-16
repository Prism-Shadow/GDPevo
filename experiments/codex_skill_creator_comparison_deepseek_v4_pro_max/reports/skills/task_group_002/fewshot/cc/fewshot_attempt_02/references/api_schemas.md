# MedBridge API Response Schemas

This reference documents the response shape for every endpoint. Use it to know which fields exist before fetching data, so you can plan your template population without extra API calls.

Base URL is provided at runtime as `<TASK_ENV_BASE_URL>`.

## GET /api

Returns dataset metadata.

```json
{
  "collections": ["customers", "events", "freight-quotes", "invoices", "opportunities", "payments", "policies", "products", "quotes", "revenue-journals", "rfqs", "vouchers"],
  "description": "Shared CRM, quote, logistics, and milestone engagement data.",
  "service": "MedBridge Sales Ops",
  "generated_at": "2026-06-01T00:00:00Z",
  "seed": 62002
}
```

## GET /api/search?q={text}

Case-insensitive partial match across all collections. Returns matching records keyed by collection.

```json
{
  "q": "search term",
  "count": 8,
  "results": [
    {
      "collection": "customers",
      "id": "CUST-XXXX",
      "record": { }
    }
  ]
}
```

## GET /api/customers/{id}

```json
{
  "id": "CUST-HHA",
  "name": "HealthHands Alliance",
  "client_since": "2022-03-14",
  "country": "Kenya",
  "region": "East Africa",
  "customer_type": "NGO",
  "segment": "recurring_ngo",
  "is_recurring": true,
  "status": "active",
  "payment_profile": "NET_30_AFTER_PO",
  "grant_terms": "UNICEF emergency stock grant allows net terms after signed PO.",
  "notes": "Recurring wound-care buyer.",
  "contacts": [
    {
      "name": "Amina Kareem",
      "role": "Procurement Lead",
      "email": "amina.kareem@healthhands.example",
      "phone": "+254-20-555-1187"
    }
  ]
}
```

Key fields: `segment` determines payment terms; `is_recurring` distinguishes new vs repeat; `payment_profile` carries the billing profile label; `contacts[0].name` is the primary contact.

## GET /api/products/{code}

```json
{
  "code": "WC-KIT-A",
  "article_number": "MB-WC-A-0144",
  "name": "Wound-care stabilization kit",
  "family": "wound_care",
  "unit": "kit",
  "weight_kg": 8.5,
  "cbm": 0.055,
  "cold_chain_required": false,
  "shelf_life_months": 36,
  "components": ["sterile dressings", "tourniquet", "saline pods", "burn gel"],
  "price_tiers": [
    {
      "min_qty": 1,
      "max_qty": 149,
      "unit_price_usd": 129.5,
      "lead_time_days": 35,
      "lead_time_weeks": 5.0
    },
    {
      "min_qty": 300,
      "max_qty": 499,
      "unit_price_usd": 118.0,
      "lead_time_days": 28,
      "lead_time_weeks": 4.0
    },
    {
      "min_qty": 500,
      "max_qty": null,
      "unit_price_usd": 114.0,
      "lead_time_days": 28,
      "lead_time_weeks": 4.0
    }
  ]
}
```

Key fields: `price_tiers` array for quantity-based pricing; `article_number` for the SKU; `cold_chain_required` affects freight recommendation; `components` are informational and should not be split into line items unless the prompt explicitly asks for component-level pricing.

## GET /api/quotes/{id}

```json
{
  "id": "Q-TR-WC-1187",
  "quote_type": "quote_revision_with_freight",
  "status": "revision_requested",
  "customer_id": "CUST-HHA",
  "quote_date": "2026-06-01",
  "currency": "USD",
  "incoterm": "EXW plus freight options",
  "primary_product_code": "WC-KIT-A",
  "confirmed_quantity": 360,
  "destination": "Nairobi emergency warehouse",
  "source_notes": "Customer confirmed higher quantity by email.",
  "line_items": [
    {
      "line_id": "Q-TR-WC-1187-L1",
      "product_code": "WC-KIT-A",
      "confirmed_quantity": 360,
      "prior_quote_quantity": 240,
      "prior_unit_price_usd": 124.0,
      "customer_note": "Please revise to 360 units."
    }
  ]
}
```

Key fields: `quote_type` signals whether freight is included; `confirmed_quantity` drives price tier selection; `source_notes` may contain hints about which tier to select.

## GET /api/rfqs/{id}

```json
{
  "id": "RFQ-TR-IEHK-204",
  "status": "open",
  "customer_id": "CUST-NOVAID",
  "quote_date": "2026-06-01",
  "received_date": "2026-05-31",
  "currency": "USD",
  "request_type": "indicative_module_quote",
  "incoterm_requested": "EXW",
  "destination": "Destination pending donor allocation",
  "narrative": "Please provide indicative EXW pricing by IEHK-style module.",
  "requested_modules": [
    {"product_code": "IEHK-BASIC", "quantity": 10},
    {"product_code": "IEHK-SUPP-A", "quantity": 1}
  ],
  "component_composition_distractors": [
    "Paracetamol tabs listed under basic module"
  ]
}
```

Key fields: `requested_modules` drives the line items; `request_type: "indicative_module_quote"` signals EXW-only; `component_composition_distractors` is a deliberate trap; ignore it and quote at module level only.

## GET /api/freight-quotes/{id}

```json
{
  "id": "FR-WC-AIR",
  "quote_id": "Q-TR-WC-1187",
  "mode": "air",
  "origin": "Dubai free zone",
  "destination": "Nairobi",
  "forwarder": "SkyBridge Air Cargo",
  "cost_usd": 16200.0,
  "currency": "USD",
  "transit_days_min": 4,
  "transit_days_max": 6,
  "transit_days_text": "4-6 days",
  "valid_until": "2026-06-18",
  "route_risk": "low",
  "risk_notes": "Low risk direct uplift with confirmed capacity.",
  "cold_chain_support": false,
  "shipment_weight_kg": 3300.0,
  "shipment_cbm": 24.0,
  "status": "active"
}
```

Key fields: `mode` is one of `"air"`, `"sea"`, `"road"`; `transit_days_text` is the display-ready range; `valid_until` vs quote date determines staleness; `route_risk` maps to uppercase risk flags; `cold_chain_support` affects mode recommendation.

## GET /api/policies

Returns all policy records:

```json
{
  "collection": "policies",
  "count": 8,
  "records": [
    {
      "id": "POL-NEW-CLIENT-PAYMENT",
      "name": "New client prepayment",
      "policy_area": "payment_terms",
      "applies_to": "new NGO clients without approved credit history",
      "rule": "New NGO clients require PREPAY_100 before production release.",
      "terms_code": "PREPAY_100",
      "effective_date": "2026-01-01"
    }
  ]
}
```

Refer to `business_rules.md` for the mapping from these policies to concrete output values.

## GET /api/opportunities/{id}

```json
{
  "id": "OPP-TR-HELIOS",
  "opportunity_name": "Helios implementation acceleration",
  "customer_id": "CUST-HELIOS",
  "contact": "Mara Okafor",
  "owner": "Priya Shah",
  "stage": "closed_won",
  "won_date": "2026-04-22",
  "won_amount_usd": 120000.0,
  "currency": "USD",
  "outstanding_amount_usd": 70000.0,
  "notes": "Phase 1 paid and recognized; phase 2 remains unpaid.",
  "phases": [
    {
      "phase_id": "HEL-P1",
      "name": "Phase 1 discovery and setup",
      "amount_usd": 50000.0,
      "completion_date": "2026-05-10",
      "invoice_id": "INV-HELIOS-P1"
    },
    {
      "phase_id": "HEL-P2",
      "name": "Phase 2 rollout support",
      "amount_usd": 70000.0,
      "completion_date": "2026-06-24",
      "invoice_id": "INV-HELIOS-P2"
    }
  ]
}
```

Key fields: `phases[].invoice_id` links to invoices; `phases[].amount_usd` is the milestone amount; `won_amount_usd` must equal the sum of all phase amounts for `opportunity_matches_milestones` to be true.

## GET /api/invoices

Returns all invoices. Filter by `customer_id` and `opportunity_id`.

```json
{
  "collection": "invoices",
  "count": 15,
  "records": [
    {
      "id": "INV-HELIOS-P1",
      "invoice_number": "MBI-HELIOS-P1",
      "customer_id": "CUST-HELIOS",
      "opportunity_id": "OPP-TR-HELIOS",
      "phase_id": "HEL-P1",
      "phase_name": "Phase 1 discovery and setup",
      "billing_type": "milestone_service",
      "amount_usd": 50000.0,
      "paid_amount_usd": 50000.0,
      "outstanding_amount_usd": 0.0,
      "status": "paid",
      "issue_date": "2026-05-11",
      "due_date": "2026-05-25"
    }
  ]
}
```

Key fields: `status` is `"paid"`, `"unpaid"`, `"overdue"`, or `"draft"`; `paid_amount_usd` vs `amount_usd` determines full vs partial payment; `due_date` drives collection logic.

## GET /api/payments

Returns all payments. Filter by `customer_id` and `opportunity_id`.

```json
{
  "collection": "payments",
  "count": 9,
  "records": [
    {
      "id": "PAY-HELIOS-P1",
      "customer_id": "CUST-HELIOS",
      "opportunity_id": "OPP-TR-HELIOS",
      "invoice_id": "INV-HELIOS-P1",
      "amount_usd": 50000.0,
      "method": "wire",
      "reference": "WIRE-IOS-P1",
      "payment_date": "2026-05-18",
      "status": "posted"
    }
  ]
}
```

Key fields: `invoice_id` links payment to invoice; `amount_usd` is the payment amount; `status: "posted"` confirms the payment is applied.

## GET /api/revenue-journals

Returns all revenue recognition journal entries.

```json
{
  "collection": "revenue-journals",
  "count": 7,
  "records": [
    {
      "id": "RJ-HELIOS-P1",
      "opportunity_id": "OPP-TR-HELIOS",
      "invoice_id": "INV-HELIOS-P1",
      "phase_id": "HEL-P1",
      "amount_usd": 50000.0,
      "debit_account": "Deferred Revenue",
      "credit_account": "Implementation Services Revenue",
      "memo": "Recognize completed paid milestone revenue.",
      "posted_date": "2026-05-19",
      "status": "posted"
    }
  ]
}
```

Key fields: `invoice_id` links to the invoice being recognized; `status: "posted"` means revenue is recognized; absence of a journal for a paid invoice means recognition is missing.

## GET /api/events

Returns all events. Filter by `customer_id` and `opportunity_id`.

```json
{
  "collection": "events",
  "count": 7,
  "records": [
    {
      "id": "EVT-HELIOS-CELEBRATION",
      "name": "Helios partner celebration",
      "customer_id": "CUST-HELIOS",
      "opportunity_id": "OPP-TR-HELIOS",
      "event_date": "2026-07-22",
      "status": "confirmed",
      "primary_contact": "Mara Okafor",
      "voucher_code": "HELIOSVIP100",
      "follow_up_owner": "Account Management"
    }
  ]
}
```

Key fields: `status` is `"scheduled"`, `"confirmed"`, `"live"`, `"completed"`, `"cancelled"`, or `"tentative"`; `primary_contact` is used for invitation tasks; `voucher_code` links to the voucher.

## GET /api/vouchers

Returns all vouchers. Filter by `customer_id` and `event_id`.

```json
{
  "collection": "vouchers",
  "count": 7,
  "records": [
    {
      "code": "HELIOSVIP100",
      "customer_id": "CUST-HELIOS",
      "opportunity_id": "OPP-TR-HELIOS",
      "event_id": "EVT-HELIOS-CELEBRATION",
      "description": "VIP event access",
      "discount_percent": 100,
      "max_redemptions": 4,
      "redemptions_used": 0,
      "status": "active",
      "valid_until": "2026-07-22"
    }
  ]
}
```

Key fields: `discount_percent` is a percentage (50 means 50%); `max_redemptions` is the voucher use limit; `status: "active"` means the voucher can be used; `valid_until` is the voucher expiry date.
