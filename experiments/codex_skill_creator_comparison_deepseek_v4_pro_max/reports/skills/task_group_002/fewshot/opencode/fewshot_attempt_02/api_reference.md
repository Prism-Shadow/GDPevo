# MedBridge Sales Ops API Reference

Full field-level documentation for every GET endpoint. The base URL is provided
in the task prompt as `<TASK_ENV_BASE_URL>`, `${BASE_URL}`, or
`${TASK_ENV_BASE_URL}`.

---

## Customers

### GET /api/customers
Returns a list of all customer summary records.

| Field | Type | Description |
|---|---|---|
| `customer_id` | string | Unique customer identifier (e.g., `CUST-HHA`, `CUST-GHL`, `CUST-HELIOS`) |
| `name` | string | Customer display name |

### GET /api/customers/{customer_id}
Returns the full customer record.

| Field | Type | Description |
|---|---|---|
| `customer_id` | string | Unique customer identifier |
| `name` | string | Customer display name |
| `type` | string | Customer classification used to match policies (`NGO`, `COMMERCIAL`, `GOVERNMENT`, etc.) |
| `category` | string | Alternate classification field (may be used instead of `type`) |
| `payment_terms_policy` | string | Direct payment terms override on the customer record (if present, prefer this over the policy lookup) |
| `preferred_freight_mode` | string | Customer's preferred transport mode (`AIR`, `SEA`, `ROAD`) |

---

## Products

### GET /api/products
Returns a list of all product summary records.

| Field | Type | Description |
|---|---|---|
| `code` | string | Product code (e.g., `WC-KIT-A`, `LD-REAGENT-44`, `IEHK-BASIC`) |
| `description` | string | Product description |
| `article_number` | string | Catalog article number (e.g., `500101`) |
| `tiers` | array | Summary of pricing tiers (fetch individual product for full tier details) |

### GET /api/products/{product_code}
Returns a single product with full tier details.

| Field | Type | Description |
|---|---|---|
| `code` | string | Product code |
| `description` | string | Product description |
| `article_number` | string | Catalog article number |
| `tiers` | array of tier objects | Pricing tiers, each containing: |
| `tiers[].min_quantity` | integer | Minimum quantity for this tier |
| `tiers[].max_quantity` | integer | Maximum quantity for this tier |
| `tiers[].unit_price` | number | Price per unit in USD |
| `tiers[].lead_time_days` | integer | Manufacturing/shipping lead time in days |
| `tiers[].shelf_life_months` | integer | Product shelf life in months |

---

## Quotes

### GET /api/quotes
Returns a list of all quote summary records.

### GET /api/quotes/{quote_id}
Returns a single quote.

| Field | Type | Description |
|---|---|---|
| `quote_id` | string | Unique quote identifier (e.g., `Q-TR-WC-1187`) |
| `customer_id` | string | Linked customer |
| `quote_date` | string | Quote date ISO `YYYY-MM-DD` |
| `product_code` | string | Product being quoted |
| `quantity` | integer | Confirmed quantity |
| `basis` | string | Quote basis (`EXW`, `EXW_PLUS_FREIGHT_OPTIONS`) |
| `status` | string | Quote status |

---

## RFQs

### GET /api/rfqs
Returns a list of all RFQ summary records.

### GET /api/rfqs/{rfq_id}
Returns a single RFQ.

| Field | Type | Description |
|---|---|---|
| `rfq_id` | string | Unique RFQ identifier (e.g., `RFQ-TR-IEHK-204`) |
| `customer_id` | string | Linked customer |
| `date` | string | RFQ date ISO `YYYY-MM-DD` |
| `items` | array | Line items, each containing: |
| `items[].product_code` | string | Product code |
| `items[].quantity` | integer | Requested quantity |
| `basis` | string | Quote basis requested |

---

## Freight Quotes

### GET /api/freight-quotes
Returns a list of all freight quote summary records.

### GET /api/freight-quotes/{freight_id}
Returns a single freight quote.

| Field | Type | Description |
|---|---|---|
| `freight_id` | string | Unique freight quote identifier (e.g., `FR-WC-AIR`, `FR-LD-ROAD`) |
| `mode` | string | Transport mode (`AIR`, `SEA`, `ROAD`) |
| `cost` | string or number | Freight cost in USD (may be a string with currency formatting — parse to a number) |
| `transit_days` | string | Transit duration (e.g., `4-6 days`, `10-14`) |
| `valid_until` | string | Freight quote expiry date ISO `YYYY-MM-DD` |
| `risk_level` | string | Route risk (`LOW`, `MEDIUM`, `HIGH`) |
| `risk_flag` | string | Risk descriptor (`NONE`, `MEDIUM_BORDER_RISK`, etc.); may also appear as `customs_border_risk` |
| `customs_border_risk` | string | Alternate name for risk flag (`LOW`, `HIGH`, `MEDIUM`, `NONE`); the API may use either field name |
| `product_code` | string | Product this freight quote applies to |

**Important:** `risk_flag` and `customs_border_risk` are the same concept. The API may use one field name or the other depending on the freight record. Read whichever field is present and map it to the template's expected field name.

---

## Policies

### GET /api/policies
Returns a list of all policy summary records.

### GET /api/policies/{policy_id}
Returns a single policy.

| Field | Type | Description |
|---|---|---|
| `customer_type` | string | Customer classification this policy applies to (`NGO`, `RECURRING_NGO`, `COMMERCIAL`, etc.) |
| `quote_basis` | string | Default quote basis |
| `payment_terms` | string | Payment terms for this customer type (`NET_30_AFTER_PO`, `PREPAY_100`, etc.) |
| `freight_reconfirmation_required` | boolean | Whether freight must be reconfirmed at final order |
| `recommended_freight_mode` | string | Recommended transport mode (`AIR`, `SEA`, `ROAD`) |
| `offer_validity_days` | integer | How many days the offer is valid |
| `who_documentation_required` | boolean | Whether WHO documentation is required |

**Matching customers to policies:** Look up the customer's `type` or `category` field, then match it to the policy's `customer_type` field. If the customer record has a `payment_terms_policy` field, that takes precedence over the policy lookup.

---

## Opportunities

### GET /api/opportunities
Returns a list of all opportunity summary records.

### GET /api/opportunities/{opportunity_id}
Returns a single opportunity.

| Field | Type | Description |
|---|---|---|
| `opportunity_id` | string | Unique opportunity identifier (e.g., `OPP-TR-HELIOS`) |
| `customer_id` | string | Linked customer |
| `stage` | string | Opportunity stage (`WON`, `OPEN`, `LOST`) |
| `amount` | number | Won amount in USD |
| `milestones` | array | Milestone phases, each containing: |
| `milestones[].milestone_id` | string | Milestone identifier (`MS1`, `MS2`, `MS3`) |
| `milestones[].amount` | number | Milestone amount in USD |
| `milestones[].phase_number` | integer | Phase order number |

---

## Invoices

### GET /api/invoices
Returns a list of all invoice summary records.

### GET /api/invoices/{invoice_id}
Returns a single invoice.

| Field | Type | Description |
|---|---|---|
| `invoice_id` | string | Unique invoice identifier |
| `customer_id` | string | Linked customer |
| `opportunity_id` | string | Linked opportunity |
| `milestone_id` | string | Linked milestone (`MS1`, `MS2`, `MS3`) |
| `phase_number` | integer | Phase number matching the milestone |
| `total` | number | Invoice total in USD |
| `status` | string | Invoice status (`OPEN`, `PAID`, `VOID`) |
| `due_date` | string or null | Due date ISO `YYYY-MM-DD`, or `null` when paid |

---

## Payments

### GET /api/payments
Returns a list of all payment summary records.

### GET /api/payments/{payment_id}
Returns a single payment.

| Field | Type | Description |
|---|---|---|
| `payment_id` | string | Unique payment identifier |
| `invoice_id` | string | Linked invoice |
| `amount` | number | Payment amount in USD |

---

## Revenue Journals

### GET /api/revenue-journals
Returns a list of all revenue journal summary records.

### GET /api/revenue-journals/{journal_id}
Returns a single revenue journal entry.

| Field | Type | Description |
|---|---|---|
| `journal_id` | string | Unique journal identifier |
| `milestone_id` | string | Linked milestone (`MS1`, `MS2`, `MS3`) |
| `invoice_id` | string | Linked invoice |
| `amount` | number | Recognized amount in USD |
| `debit_account` | string | Debit account name |
| `credit_account` | string | Credit account name |

---

## Events

### GET /api/events
Returns a list of all event summary records.

### GET /api/events/{event_id}
Returns a single event.

| Field | Type | Description |
|---|---|---|
| `event_id` | string | Unique event identifier (e.g., `EVT-HELIOS-CELEBRATION`) |
| `customer_id` | string | Linked customer |
| `opportunity_id` | string | Linked opportunity |
| `date` | string | Event date ISO `YYYY-MM-DD` |
| `status` | string | Event status (`SCHEDULED`, `ACTIVE`, `COMPLETED`, `CANCELLED`) |
| `voucher_code` | string | Linked voucher code |

---

## Vouchers

### GET /api/vouchers/{voucher_code}
Returns a single voucher by its code.

| Field | Type | Description |
|---|---|---|
| `code` | string | Voucher code (e.g., `HELIOSVIP100`, `MERIDIANBRIEF50`) |
| `status` | string | Voucher status (`ACTIVE`, `DRAFT`, `EXPIRED`, `DISABLED`) |
| `discount` | number | Discount amount in USD |
| `max_uses` | integer | Maximum number of uses |
