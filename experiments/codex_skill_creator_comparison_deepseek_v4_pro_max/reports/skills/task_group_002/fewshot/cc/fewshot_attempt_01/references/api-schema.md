# API Schema Reference

Field-by-field documentation for every MedBridge Sales Ops API collection.
Each section describes one collection, its record shape, and how it links to
other collections.

## Reading individual records

List endpoints (`GET /api/{collection}`) return all records. Single-record
lookups use query parameters on the same path:

- `GET /api/{collection}?id={record_id}` for most collections
- `GET /api/vouchers?code={VOUCHER_CODE}` for vouchers (keyed by `code`)

For filtering on relationships, fetch the list endpoint and filter the
`records` array on the relevant foreign-key field. Example: to find all
invoices for an opportunity, fetch `/api/invoices` and keep records where
`opportunity_id == "<OPP_ID>"`.

---

## customers

| Field | Type | Notes |
|-------|------|-------|
| id | string | Primary key, e.g. `CUST-HHA` |
| name | string | Display name |
| client_since | string or null | ISO date of first engagement |
| contacts | array | List of contact objects |
| contacts[].name | string | Contact person name |
| contacts[].email | string | Email address |
| contacts[].phone | string | Phone number |
| contacts[].role | string | Job title |
| country | string | Country name |
| customer_type | string | e.g. `NGO`, `Commercial` |
| grant_terms | string or null | Donor or grant restrictions on payment |
| is_recurring | boolean | Whether this is a repeat buyer |
| notes | string | Free-text account notes |
| payment_profile | string | e.g. `NET_30_AFTER_PO`, `NEW_CLIENT_REVIEW` |
| region | string | Geographic region |
| segment | string | `recurring_ngo`, `new_ngo`, `recurring_commercial` |
| status | string | `active`, `prospect`, `inactive` |

**Key fields for quote tasks**: `segment` (drives payment terms), `payment_profile`, `grant_terms`.

**Key fields for reconciliation tasks**: `id` (links to opportunity), `contacts` (contact routing).

---

## products

| Field | Type | Notes |
|-------|------|-------|
| article_number | string | Internal article code |
| cbm | number | Cubic metres per unit |
| code | string | Primary key, e.g. `WC-KIT-A`, `IEHK-BASIC` |
| cold_chain_required | boolean | Whether cold-chain logistics apply |
| components | array of strings | Sub-components (for module products) |
| family | string | Product family |
| name | string | Human-readable product name |
| price_tiers | array | Quantity-tier pricing |
| price_tiers[].min_qty | integer | Minimum quantity for this tier |
| price_tiers[].max_qty | integer or null | Maximum quantity (null = no upper bound) |
| price_tiers[].unit_price_usd | number | EXW unit price in USD |
| price_tiers[].lead_time_days | integer | Production/supply lead time |
| price_tiers[].lead_time_weeks | number | Same as lead_time_days in weeks |
| shelf_life_months | integer | Product shelf life |
| unit | string | Unit of measure (`kit`, `module`, etc.) |
| weight_kg | number | Weight in kg per unit |

**Tier selection logic**: the tiers array is ordered. For a confirmed quantity,
find the first tier where `min_qty <= confirmed_quantity` AND
(`max_qty is null OR confirmed_quantity <= max_qty`).

---

## quotes

| Field | Type | Notes |
|-------|------|-------|
| id | string | Primary key, e.g. `Q-TR-WC-1187` |
| confirmed_quantity | integer or null | Confirmed unit count |
| currency | string | Always `USD` |
| customer_id | string | FK to customers |
| destination | string | Delivery destination |
| incoterm | string | e.g. `EXW plus freight options` |
| line_items | array | Quote lines |
| line_items[].line_id | string | Line identifier |
| line_items[].product_code | string | FK to products |
| line_items[].confirmed_quantity | integer | Quantity for this line |
| line_items[].prior_quote_quantity | integer | Previous quote quantity |
| line_items[].prior_unit_price_usd | number | Previous unit price |
| line_items[].customer_note | string | Customer request text |
| primary_product_code | string | Main product code |
| quote_date | string | ISO date `YYYY-MM-DD` |
| quote_type | string | e.g. `quote_revision_with_freight` |
| source_notes | string | Internal guidance on quote handling |
| status | string | e.g. `revision_requested` |

---

## rfqs

| Field | Type | Notes |
|-------|------|-------|
| id | string | Primary key, e.g. `RFQ-TR-IEHK-204` |
| customer_id | string | FK to customers |
| currency | string | Always `USD` |
| destination | string or null | Delivery destination (may be pending) |
| incoterm_requested | string | e.g. `EXW` |
| narrative | string | Customer request description |
| quote_date | string | ISO date `YYYY-MM-DD` |
| received_date | string | ISO date when RFQ was received |
| request_type | string | e.g. `indicative_module_quote` |
| requested_modules | array | Modules to quote |
| requested_modules[].product_code | string | FK to products |
| requested_modules[].quantity | integer | Requested quantity |
| component_composition_distractors | array of strings | Internal notes about module composition; ignore for quoting |
| status | string | e.g. `open` |

**Important**: `component_composition_distractors` is intentionally included to
test whether the solver quotes at the correct granularity. Quote at module level
using `requested_modules`, not component level.

---

## freight-quotes

| Field | Type | Notes |
|-------|------|-------|
| id | string | Primary key, e.g. `FR-WC-AIR` |
| quote_id | string | FK to quotes |
| mode | string | `air`, `sea`, `road` |
| cost_usd | number | Freight cost in USD |
| currency | string | Always `USD` |
| origin | string | Shipment origin |
| destination | string | Shipment destination |
| forwarder | string | Logistics provider name |
| cold_chain_support | boolean | Whether cold-chain is supported |
| shipment_weight_kg | number | Total shipment weight |
| shipment_cbm | number | Total shipment volume |
| transit_days_min | integer | Minimum transit days |
| transit_days_max | integer | Maximum transit days |
| transit_days_text | string | Display text, e.g. `4-6 days` |
| route_risk | string | `low`, `medium`, `high` |
| risk_notes | string | Free-text risk description |
| quote_date | string | ISO date when freight was quoted |
| valid_until | string | ISO date of freight quote expiry |
| status | string | e.g. `active` |

**Validity**: a freight quote is valid on a given date if `valid_until >= date`.
Expired freight quotes are STALE and should not be used for a recommendation
without reconfirmation.

---

## policies

| Field | Type | Notes |
|-------|------|-------|
| id | string | Primary key, e.g. `POL-FREIGHT-RECONFIRM` |
| name | string | Policy name |
| policy_area | string | `payment_terms`, `quote_scope`, `freight`, `quote_lines`, `revenue_recognition`, `quote_validity`, `incoterms` |
| applies_to | string | Who or what the policy covers |
| rule | string | The policy rule in prose |
| terms_code | string | Machine-readable code |
| effective_date | string | ISO date when policy took effect |

**Always fetch all policies**. The eight canonical policies are listed in
[business-rules.md](business-rules.md).

---

## opportunities

| Field | Type | Notes |
|-------|------|-------|
| id | string | Primary key, e.g. `OPP-TR-HELIOS` |
| opportunity_name | string | Descriptive name |
| customer_id | string | FK to customers |
| contact | string | Primary contact name |
| owner | string | Account owner |
| currency | string | Always `USD` |
| stage | string | `closed_won`, `open`, `closed_lost` |
| won_amount_usd | number | Total won value |
| won_date | string or null | ISO date of close |
| outstanding_amount_usd | number | Current unpaid balance |
| notes | string | Free-text notes |
| phases | array | Milestone phases |
| phases[].phase_id | string | Phase identifier, e.g. `HEL-P1` |
| phases[].name | string | Phase name |
| phases[].amount_usd | number | Phase value |
| phases[].completion_date | string | ISO date of completion |
| phases[].invoice_id | string | FK to invoices |

---

## invoices

| Field | Type | Notes |
|-------|------|-------|
| id | string | Primary key, e.g. `INV-HELIOS-P1` |
| invoice_number | string | Human-readable number |
| amount_usd | number | Invoice total |
| customer_id | string | FK to customers |
| opportunity_id | string | FK to opportunities |
| phase_id | string | Links to opportunity phase |
| phase_name | string | Phase description |
| billing_type | string | e.g. `milestone_service` |
| issue_date | string | ISO date |
| due_date | string | ISO date when payment is due |
| paid_amount_usd | number | Amount already paid |
| outstanding_amount_usd | number | Remaining unpaid balance |
| status | string | `paid`, `unpaid` |

---

## payments

| Field | Type | Notes |
|-------|------|-------|
| id | string | Primary key, e.g. `PAY-HELIOS-P1` |
| invoice_id | string | FK to invoices |
| opportunity_id | string | FK to opportunities |
| customer_id | string | FK to customers |
| amount_usd | number | Payment amount |
| method | string | Payment method (`wire`) |
| payment_date | string | ISO date of payment |
| reference | string | Payment reference code |
| status | string | `posted` |

---

## revenue-journals

| Field | Type | Notes |
|-------|------|-------|
| id | string | Primary key, e.g. `RJ-HELIOS-P1` |
| invoice_id | string | FK to invoices |
| opportunity_id | string | FK to opportunities |
| phase_id | string | Links to opportunity phase |
| amount_usd | number | Journal amount |
| debit_account | string | Account debited |
| credit_account | string | Account credited |
| memo | string | Journal description |
| posted_date | string | ISO date when journal was posted |
| status | string | `posted` |

**Key fact**: a revenue journal exists only when the milestone is paid AND
recognized. Missing journals for paid milestones are accounting gaps.

---

## events

| Field | Type | Notes |
|-------|------|-------|
| id | string | Primary key, e.g. `EVT-HELIOS-CELEBRATION` |
| name | string | Event name |
| opportunity_id | string | FK to opportunities |
| customer_id | string | FK to customers |
| primary_contact | string | Contact person |
| follow_up_owner | string | Owner team |
| event_date | string | ISO date of event |
| status | string | `scheduled`, `confirmed`, `live`, `completed`, `cancelled`, `tentative` |
| voucher_code | string | FK to vouchers |

**Status mapping for task output**:
- `scheduled` → `SCHEDULED`
- `confirmed` or `live` → `ACTIVE`
- `completed` → `COMPLETED`
- `cancelled` → `CANCELLED`

---

## vouchers

| Field | Type | Notes |
|-------|------|-------|
| code | string | Primary key (used as lookup), e.g. `HELIOSVIP100` |
| description | string | Voucher description |
| event_id | string | FK to events |
| opportunity_id | string | FK to opportunities |
| customer_id | string | FK to customers |
| discount_percent | number | Discount value (may represent a percent or flat amount) |
| max_redemptions | integer | Maximum uses |
| redemptions_used | integer | Number already redeemed |
| status | string | `active`, `draft`, `expired`, `disabled` |
| valid_until | string | ISO date of voucher expiry |

**Mapping for task output**: use `discount_percent` as the discount amount,
`max_redemptions` as `max_uses`, and map `status` to uppercase.
