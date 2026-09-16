# MedBridge Sales Ops API Reference

## Field Reference by Collection

### Customers

| Field | Type | Description |
|---|---|---|
| id | string | Customer ID (e.g. CUST-HHA) |
| name | string | Organization name |
| status | string | active / prospect / inactive |
| customer_type | string | NGO / Commercial |
| segment | string | recurring_ngo / new_ngo / recurring_commercial / implementation_services |
| is_recurring | boolean | Whether established repeat buyer |
| payment_profile | string | NET_30_AFTER_PO / PREPAY_100 / NEW_CLIENT_REVIEW / MILESTONE_BILLING |
| country | string | Country name |
| region | string | Geographic region |
| grant_terms | string | Donor or grant restrictions |
| notes | string | Account notes |
| contacts[] | array | Name, email, phone, role |

### Products

| Field | Type | Description |
|---|---|---|
| code | string | Product code (e.g. WC-KIT-A) |
| article_number | string | Internal article number |
| name | string | Product display name |
| family | string | Product family |
| unit | string | Unit of measure |
| shelf_life_months | integer | Shelf life in months |
| cold_chain_required | boolean | Whether cold chain applies |
| weight_kg | float | Unit weight |
| cbm | float | Unit cubic meters |
| components[] | array | Component list (ignore for module quotes) |
| price_tiers[] | array | Tiered pricing entries |
| price_tiers[].min_qty | integer | Minimum quantity for tier |
| price_tiers[].max_qty | integer or null | Maximum quantity; null = unlimited |
| price_tiers[].unit_price_usd | float | Unit price in USD |
| price_tiers[].lead_time_days | integer | Lead time in days |

### Quotes

| Field | Type | Description |
|---|---|---|
| id | string | Quote ID (e.g. Q-TR-WC-1187) |
| customer_id | string | Linked customer |
| quote_date | string | ISO date |
| quote_type | string | quote_revision_with_freight / indicative_module_quote |
| status | string | revision_requested / open |
| incoterm | string | EXW plus freight options / EXW |
| currency | string | USD |
| primary_product_code | string | Main product |
| confirmed_quantity | integer | Confirmed order quantity |
| destination | string | Delivery destination |
| line_items[] | array | Line items with product_code, confirmed_quantity, prior_quote_quantity, prior_unit_price_usd |
| source_notes | string | Processing guidance |

### RFQs

| Field | Type | Description |
|---|---|---|
| id | string | RFQ ID (e.g. RFQ-TR-IEHK-204) |
| customer_id | string | Linked customer |
| quote_date | string | ISO date |
| request_type | string | indicative_module_quote |
| incoterm_requested | string | EXW |
| destination | string | May be pending |
| requested_modules[] | array | Modules with product_code and quantity |
| component_composition_distractors[] | array | Ignore; composition noise for module RFQs |
| narrative | string | Request context |

### Freight Quotes

| Field | Type | Description |
|---|---|---|
| id | string | Freight quote ID (e.g. FR-WC-AIR) |
| quote_id | string | Linked quote ID |
| mode | string | air / sea / road |
| cost_usd | float | Freight cost |
| transit_days_min | integer | Minimum transit days |
| transit_days_max | integer | Maximum transit days |
| transit_days_text | string | Formatted transit range |
| valid_until | string | Expiry date |
| route_risk | string | low / medium / high |
| risk_notes | string | Risk description |
| origin | string | Shipment origin |
| destination | string | Shipment destination |
| forwarder | string | Carrier name |
| cold_chain_support | boolean | Cold chain capability |
| status | string | active / expired |

### Opportunities

| Field | Type | Description |
|---|---|---|
| id | string | Opportunity ID (e.g. OPP-TR-HELIOS) |
| customer_id | string | Linked customer |
| opportunity_name | string | Display name |
| stage | string | closed_won / open / closed_lost |
| won_amount_usd | float | Total won value |
| won_date | string | ISO date |
| contact | string | Primary contact name |
| owner | string | Account owner |
| outstanding_amount_usd | float | Unpaid balance |
| phases[] | array | Milestone phases |
| phases[].phase_id | string | Phase code (e.g. HEL-P1) |
| phases[].name | string | Phase display name |
| phases[].amount_usd | float | Phase value |
| phases[].completion_date | string | ISO date |
| phases[].invoice_id | string | Linked invoice ID |

### Invoices

| Field | Type | Description |
|---|---|---|
| id | string | Invoice ID (e.g. INV-HELIOS-P1) |
| customer_id | string | Linked customer |
| opportunity_id | string | Linked opportunity |
| phase_id | string | Linked phase |
| amount_usd | float | Invoice amount |
| paid_amount_usd | float | Amount paid |
| outstanding_amount_usd | float | Amount remaining |
| status | string | paid / unpaid |
| issue_date | string | ISO date |
| due_date | string or null | ISO date or null |

### Payments

| Field | Type | Description |
|---|---|---|
| id | string | Payment ID |
| invoice_id | string | Linked invoice |
| customer_id | string | Linked customer |
| opportunity_id | string | Linked opportunity |
| amount_usd | float | Payment amount |
| payment_date | string | ISO date |
| method | string | wire |
| status | string | posted |

### Revenue Journals

| Field | Type | Description |
|---|---|---|
| id | string | Journal ID (e.g. RJ-HELIOS-P1) |
| invoice_id | string | Linked invoice |
| opportunity_id | string | Linked opportunity |
| phase_id | string | Linked phase |
| amount_usd | float | Recognized amount |
| debit_account | string | Deferred Revenue |
| credit_account | string | Implementation Services Revenue |
| posted_date | string | ISO date |
| status | string | posted |

### Events

| Field | Type | Description |
|---|---|---|
| id | string | Event ID (e.g. EVT-HELIOS-CELEBRATION) |
| name | string | Event display name |
| customer_id | string | Linked customer |
| opportunity_id | string | Linked opportunity |
| status | string | scheduled / confirmed / live / tentative / completed / cancelled |
| event_date | string | ISO date |
| voucher_code | string | Linked voucher code |
| primary_contact | string | Contact name |
| follow_up_owner | string | Account Management |

### Vouchers

| Field | Type | Description |
|---|---|---|
| code | string | Voucher code (e.g. HELIOSVIP100) |
| customer_id | string | Linked customer |
| opportunity_id | string | Linked opportunity |
| event_id | string | Linked event |
| discount_percent | integer | Discount percentage |
| max_redemptions | integer | Maximum uses |
| redemptions_used | integer | Current redemptions |
| status | string | active / draft / expired / disabled |
| valid_until | string | ISO date |

### Policies

| Field | Type | Description |
|---|---|---|
| id | string | Policy ID (e.g. POL-FREIGHT-RECONFIRM) |
| name | string | Policy name |
| policy_area | string | Domain (payment_terms, freight, quote_scope, revenue_recognition, etc.) |
| rule | string | Policy rule text |
| terms_code | string | Policy code |
| applies_to | string | Policy scope |
