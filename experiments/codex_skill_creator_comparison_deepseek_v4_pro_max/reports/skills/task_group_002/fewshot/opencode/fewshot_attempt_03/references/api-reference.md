# MedBridge Sales Ops API Reference

Full field-level documentation for each collection in the MedBridge Sales Ops
API. All endpoints are read-only GETs against `<TASK_ENV_BASE_URL>/api/...`.

---

## Customers

```
GET /api/customers
GET /api/customers/{id}
```

| Field            | Type     | Notes                                            |
|------------------|----------|--------------------------------------------------|
| id               | string   | Stable customer ID (e.g., `CUST-ABC`)            |
| name             | string   | Full organisation name                           |
| country          | string   | Country name                                     |
| region           | string   | Region (e.g., `East Africa`, `West Africa`)      |
| customer_type    | string   | `NGO`, `Commercial`, `Government Program`, etc.  |
| segment          | string   | `recurring_ngo`, `new_ngo`, `recurring_commercial`, `implementation_services` |
| status           | string   | `active`, `prospect`, etc.                       |
| is_recurring     | boolean  | True if repeat buyer                              |
| payment_profile  | string   | `NET_30_AFTER_PO`, `NEW_CLIENT_REVIEW`, `MILESTONE_BILLING`, etc. |
| grant_terms      | string   | Human-readable grant restrictions                |
| client_since     | string/null | ISO date or null for new clients               |
| contacts         | array    | Each entry: `name`, `email`, `phone`, `role`     |
| notes            | string   | Free-form CRM notes                              |

---

## Products

```
GET /api/products
GET /api/products/{code}
```

| Field              | Type        | Notes                                        |
|--------------------|-------------|----------------------------------------------|
| code               | string      | Product code (e.g., `WC-KIT-XX`, `IEHK-XX`) |
| name               | string      | Display name                                 |
| family             | string      | Product family                                |
| article_number     | string      | Internal SKU                                 |
| unit               | string      | Unit of measure (`kit`, `module`, `pack`)    |
| weight_kg          | number      | Weight per unit                              |
| cbm                | number      | Volume per unit (cubic meters)               |
| cold_chain_required| boolean     | Requires cold-chain transport                |
| shelf_life_months  | number      | Months before expiry                         |
| components         | array       | Component descriptions (strings)             |
| price_tiers        | array       | Each tier: see below                         |

**Price tier entry:**

| Field            | Type        | Notes                                    |
|------------------|-------------|------------------------------------------|
| min_qty          | number      | Inclusive lower bound                    |
| max_qty          | number/null | Inclusive upper bound; null = unlimited  |
| unit_price_usd   | number      | USD price per unit in this tier          |
| lead_time_days   | number      | Production lead time                     |
| lead_time_weeks  | number      | Same as days, in weeks                   |

---

## Quotes

```
GET /api/quotes
GET /api/quotes/{id}
```

| Field                | Type   | Notes                                      |
|----------------------|--------|--------------------------------------------|
| id                   | string | Quote ID (e.g., `Q-TR-XX-9999`)            |
| customer_id          | string | FK to customers                            |
| quote_date           | string | ISO date                                   |
| incoterm             | string | `EXW`, `EXW plus freight options`, etc.    |
| status               | string | `revision_requested`, `active`, etc.       |
| quote_type           | string | `quote_revision_with_freight`, etc.        |
| primary_product_code | string | Main product code                          |
| confirmed_quantity   | number | Confirmed total quantity                   |
| currency             | string | Always `USD` in this environment           |
| destination          | string | Destination description                    |
| source_notes         | string | Guidance notes                             |
| line_items           | array  | Each: `line_id`, `product_code`, `confirmed_quantity`, `prior_quote_quantity`, `prior_unit_price_usd`, `customer_note` |

---

## RFQs

```
GET /api/rfqs
GET /api/rfqs/{id}
```

| Field                    | Type   | Notes                                     |
|--------------------------|--------|-------------------------------------------|
| id                       | string | RFQ ID                                    |
| customer_id              | string | FK to customers                           |
| quote_date               | string | ISO date                                  |
| incoterm_requested       | string | Requested incoterm                        |
| request_type             | string | `indicative_module_quote`, etc.           |
| destination              | string | Destination description                   |
| status                   | string | `open`, etc.                              |
| received_date            | string | ISO date                                  |
| narrative                | string | Request description                       |
| requested_modules        | array  | Each: `product_code`, `quantity`          |
| component_composition_distractors | array | Distractor strings to ignore      |

---

## Freight Quotes

```
GET /api/freight-quotes
GET /api/freight-quotes/{id}
```

| Field                | Type        | Notes                                      |
|----------------------|-------------|--------------------------------------------|
| id                   | string      | Freight ID (e.g., `FR-XX-AIR`)             |
| quote_id             | string      | FK to the parent quote                     |
| mode                 | string      | `air`, `sea`, `road` (lowercase)           |
| origin               | string      | Origin description                         |
| destination          | string      | Destination description                    |
| cost_usd             | number      | Freight cost in USD                        |
| transit_days_min     | number      | Minimum transit days                       |
| transit_days_max     | number      | Maximum transit days                       |
| transit_days_text    | string      | Human-readable range (e.g., `"4-6 days"`)  |
| valid_until          | string      | ISO date — freight quote expires after this |
| route_risk           | string      | `low`, `medium`, `high` (lowercase)        |
| risk_notes           | string      | Human-readable risk description            |
| cold_chain_support   | boolean     | Cold-chain capability                      |
| status               | string      | `active`, `stale`, etc.                    |
| forwarder            | string      | Freight forwarder name                     |
| quote_date           | string      | ISO date of the freight quote              |
| currency             | string      | Always `USD`                               |
| shipment_cbm         | number      | Total shipment volume                      |
| shipment_weight_kg   | number      | Total shipment weight                      |

---

## Opportunities

```
GET /api/opportunities
GET /api/opportunities/{id}
```

| Field                | Type   | Notes                                     |
|----------------------|--------|-------------------------------------------|
| id                   | string | Opportunity ID                            |
| customer_id          | string | FK to customers                           |
| contact              | string | Primary contact name                      |
| opportunity_name     | string | Display name                              |
| stage                | string | `closed_won`, `open`, `closed_lost`       |
| won_amount_usd       | number | Total won value                           |
| outstanding_amount_usd | number | Remaining unpaid                          |
| won_date             | string | ISO date when won                         |
| owner                | string | Internal owner                            |
| notes                | string | Free-form notes                           |
| phases               | array  | Each: `phase_id`, `name`, `amount_usd`, `completion_date`, `invoice_id` |

---

## Invoices (list-only)

```
GET /api/invoices
```

| Field                  | Type   | Notes                                       |
|------------------------|--------|---------------------------------------------|
| id                     | string | Invoice ID (e.g., `INV-XXX-P1`)          |
| invoice_number         | string | Display number                              |
| customer_id            | string | FK to customers                             |
| opportunity_id         | string | FK to opportunities                         |
| phase_id               | string | Phase reference                             |
| phase_name             | string | Phase display name                          |
| amount_usd             | number | Total invoice amount                        |
| paid_amount_usd        | number | Amount paid so far                          |
| outstanding_amount_usd | number | Amount still owed                           |
| status                 | string | `paid`, `unpaid`, `open`, `void`            |
| due_date               | string/null | ISO due date or null                      |
| issue_date             | string | ISO issued date                             |
| billing_type           | string | `milestone_service`, etc.                   |

---

## Payments (list-only)

```
GET /api/payments
```

| Field            | Type   | Notes                                      |
|------------------|--------|--------------------------------------------|
| id               | string | Payment ID                                 |
| invoice_id       | string | FK to invoices                             |
| opportunity_id   | string | FK to opportunities                        |
| customer_id      | string | FK to customers                            |
| amount_usd       | number | Payment amount                             |
| payment_date     | string | ISO date                                   |
| method           | string | `wire`, etc.                               |
| status           | string | `posted`, etc.                             |
| reference        | string | Payment reference                          |

---

## Revenue Journals (list-only)

```
GET /api/revenue-journals
```

| Field            | Type   | Notes                                      |
|------------------|--------|--------------------------------------------|
| id               | string | Journal ID                                 |
| invoice_id       | string | FK to invoices                             |
| opportunity_id   | string | FK to opportunities                        |
| phase_id         | string | Phase reference                            |
| amount_usd       | number | Recognized amount                          |
| debit_account    | string | Debit account name                         |
| credit_account   | string | Credit account name                        |
| posted_date      | string | ISO date posted                            |
| status           | string | `posted`, etc.                             |
| memo             | string | Description                                |

---

## Events (list-only)

```
GET /api/events
```

| Field            | Type   | Notes                                      |
|------------------|--------|--------------------------------------------|
| id               | string | Event ID                                   |
| name             | string | Display name                               |
| customer_id      | string | FK to customers                            |
| opportunity_id   | string | FK to opportunities                        |
| event_date       | string | ISO event date                             |
| status           | string | `scheduled`, `confirmed`, `live`, `completed`, `tentative` |
| primary_contact  | string | Contact name                               |
| voucher_code     | string | Linked voucher code                        |
| follow_up_owner  | string | Owner department                           |

---

## Vouchers (list-only)

```
GET /api/vouchers
```

| Field            | Type   | Notes                                      |
|------------------|--------|--------------------------------------------|
| code             | string | Voucher code (FK)                          |
| description      | string | Description                                |
| customer_id      | string | FK to customers                            |
| event_id         | string | FK to events                               |
| opportunity_id   | string | FK to opportunities                        |
| discount_percent | number | Discount percentage                        |
| max_redemptions  | number | Maximum uses                               |
| redemptions_used | number | Redemptions consumed                       |
| status           | string | `active`, `draft`, `expired`, `disabled`   |
| valid_until      | string | ISO expiry date                            |

---

## Policies (list-only)

```
GET /api/policies
```

| Field          | Type   | Notes                                        |
|----------------|--------|----------------------------------------------|
| id             | string | Policy ID                                    |
| name           | string | Display name                                 |
| policy_area    | string | `payment_terms`, `freight`, `quote_scope`, `quote_lines`, `revenue_recognition`, `incoterms`, `quote_validity` |
| rule           | string | Human-readable rule text                     |
| applies_to     | string | Target audience description                  |
| terms_code     | string | Machine-readable code                        |
| effective_date | string | ISO date                                     |

### Key policies

| ID                          | terms_code                    | Meaning                                                      |
|-----------------------------|-------------------------------|--------------------------------------------------------------|
| `POL-NEW-CLIENT-PAYMENT`    | `PREPAY_100`                 | New NGO clients pay 100% upfront                             |
| `POL-RECURRING-NGO-PAYMENT` | `NET_30_AFTER_PO`            | Recurring NGOs get net-30 terms                              |
| `POL-INDICATIVE-EXW`        | `EXW_ONLY_EXCLUDE_FREIGHT`   | Indicative quotes without destination exclude freight        |
| `POL-MODULE-GRANULARITY`    | `MODULE_LINES`               | Module RFQs quoted at module level                           |
| `POL-FREIGHT-RECONFIRM`     | `RECONFIRM_AT_ORDER`         | Freight rates require reconfirmation at final order          |
| `POL-REVREC`                | `RECOGNIZE_PAID_COMPLETE_MILESTONES` | Recognize revenue on paid, completed milestones    |
| `POL-QUOTE-VALIDITY`        | `QUOTE_VALID_30_DAYS`        | Pricing valid 30 days from quote date                        |
| `POL-EXW-SCOPE`             | `EXW_EXCLUSIONS`             | EXW excludes freight, insurance, duties, last-mile           |
