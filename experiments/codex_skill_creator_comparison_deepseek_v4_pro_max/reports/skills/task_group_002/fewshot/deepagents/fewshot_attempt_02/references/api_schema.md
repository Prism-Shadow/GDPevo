## MedBridge Sales Ops API — Entity Schema Reference

### API root

`GET /api` returns a `collections` list and the seed; the base URL is supplied as `<TASK_ENV_BASE_URL>` at runtime.

All collection endpoints return paginated objects with `collection`, `count`, and `records`. Use `GET /api/search?q=<text>` for cross-entity search.

---

### products

```
GET /api/products
GET /api/products/<code>
```

| Field | Type | Notes |
|-------|------|-------|
| code | string | Product code used in quotes/RFQs |
| article_number | string | Internal article number |
| name | string | Display name |
| family | string | e.g. wound_care, emergency_health_kit, diagnostics, maternal, cholera, field_clinic, ppe |
| unit | string | kit, module, pack, case, etc. |
| shelf_life_months | integer | |
| cold_chain_required | boolean | |
| cbm | float | Cubic meters per unit |
| weight_kg | float | Weight in kg per unit |
| components | array of strings | Sub-components for product description only |
| price_tiers | array | Quantity-based tiered pricing |

**price_tiers** entries:
- `min_qty`, `max_qty` (max_qty can be null for the highest tier)
- `unit_price_usd` (float)
- `lead_time_days`, `lead_time_weeks`

**Tier matching**: For a given quantity, select the tier where `min_qty <= quantity` AND (`max_qty >= quantity` OR `max_qty` is null). Always use the catalog tier price; do not hardcode or carry forward prior quote prices.

---

### customers

```
GET /api/customers
GET /api/customers/<id>
```

| Field | Type | Notes |
|-------|------|-------|
| id | string | Customer ID |
| name | string | Legal entity name |
| customer_type | string | NGO, Commercial, Government Program |
| segment | string | recurring_ngo, new_ngo, recurring_commercial, new_commercial, government_program |
| is_recurring | boolean | |
| status | string | active, prospect, suspended |
| country | string | |
| region | string | |
| payment_profile | string | NET_30_AFTER_PO, NEW_CLIENT_REVIEW, etc. |
| grant_terms | string | Narrative funding context |
| notes | string | Account context hints |
| contacts | array of {name, email, phone, role} | |

**Segment to payment terms mapping:**
- `new_ngo` → PREPAY_100 (POL-NEW-CLIENT-PAYMENT)
- `recurring_ngo` → NET_30_AFTER_PO unless grant_terms restrict
- `recurring_commercial` → NET_30_AFTER_PO
- `new_commercial` → PREPAY_100
- `government_program` → NET_30_AFTER_PO

---

### quotes

```
GET /api/quotes
GET /api/quotes/<id>
```

| Field | Type | Notes |
|-------|------|-------|
| id | string | Quote ID |
| customer_id | string | |
| quote_date | string | YYYY-MM-DD; business date for validity checks |
| quote_type | string | quote_revision_with_freight, indicative_module_quote, product_quote |
| status | string | revision_requested, etc. |
| incoterm | string | EXW plus freight options, EXW only, etc. |
| currency | string | USD |
| confirmed_quantity | integer or null | Revision qty (null for indicative) |
| primary_product_code | string | |
| destination | string | |
| line_items | array | Each line has product_code, confirmed_quantity, customer_note, prior_quote_quantity, prior_unit_price_usd |
| source_notes | string | Processing guidance for the solver |

---

### rfqs

```
GET /api/rfqs
GET /api/rfqs/<id>
```

| Field | Type | Notes |
|-------|------|-------|
| id | string | |
| customer_id | string | |
| request_type | string | indicative_module_quote, product_quote |
| status | string | open, etc. |
| incoterm_requested | string | |
| quote_date | string | Business date for the quote |
| destination | string | May be pending; if no confirmed destination, exclude freight |
| requested_modules | array | Each has product_code, quantity |
| narrative | string | Processing instructions |
| component_composition_distractors | array | Lines to ignore; stay at module level |

**Module RFQ rule**: Quote only the modules listed in `requested_modules` at module level. Do not split into component SKUs listed in `component_composition_distractors`. Include every requested module as a separate line item.

---

### freight-quotes

```
GET /api/freight-quotes
GET /api/freight-quotes/<id>
```

| Field | Type | Notes |
|-------|------|-------|
| id | string | Freight quote ID |
| quote_id | string | Linked quote ID |
| mode | string | air, sea, road |
| cost_usd | float | Freight cost |
| transit_days_min, transit_days_max | integer | |
| transit_days_text | string | Formatted display |
| valid_until | string | YYYY-MM-DD; key for staleness |
| cold_chain_support | boolean | |
| route_risk | string | low, medium, high |
| risk_notes | string | |
| status | string | active, expired, etc. |
| origin, destination, forwarder | string | |

**Validity check**: Compare `quote_date` (from the quote) to `valid_until`. If `valid_until < quote_date`, the freight quote is stale and must be flagged.

**Risk mapping**: route_risk `low` → LOW/NONE, `medium` → MEDIUM with border/customs flag, `high` → HIGH with explicit warning.

**Mode recommendation**: Prefer SEA for cost/reliability balance unless time urgency or cold-chain constraints dictate AIR. Avoid ROAD when route_risk is medium/high or the quote is stale.

---

### policies

```
GET /api/policies
GET /api/policies/<id>
```

| Field | Type | Notes |
|-------|------|-------|
| id | string | |
| name | string | Display name |
| policy_area | string | payment_terms, freight, quote_scope, quote_lines, revenue_recognition, quote_validity, incoterms |
| rule | string | The rule body |
| terms_code | string | Canonical code |
| applies_to | string | Scope |
| effective_date | string | |

Key policies:
- **POL-RECURRING-NGO-PAYMENT**: Recurring NGOs → NET_30_AFTER_PO
- **POL-NEW-CLIENT-PAYMENT**: New NGOs → PREPAY_100
- **POL-INDICATIVE-EXW**: RFQ without destination → EXW only, exclude freight
- **POL-FREIGHT-RECONFIRM**: Freight reconfirmation required at final order; valid only through valid_until
- **POL-MODULE-GRANULARITY**: Module RFQs stay at module line level
- **POL-REVREC**: Completed paid milestones require revenue recognition (deferred revenue → income); unpaid milestones remain outstanding
- **POL-QUOTE-VALIDITY**: Catalog pricing valid 30 days from quote_date; freight may expire sooner
- **POL-EXW-SCOPE**: EXW excludes freight, insurance, duty, customs, last-mile

---

### opportunities

```
GET /api/opportunities
GET /api/opportunities/<id>
```

| Field | Type | Notes |
|-------|------|-------|
| id | string | Opportunity ID |
| customer_id | string | |
| opportunity_name | string | |
| contact | string | Primary contact name |
| owner | string | Internal owner |
| stage | string | closed_won, etc. (map to WON/OPEN/LOST) |
| won_amount_usd | float | |
| outstanding_amount_usd | float | Total unpaid across phases |
| won_date | string | |
| notes | string | Processing hints |
| phases | array | Each has phase_id, name, amount_usd, completion_date, invoice_id |

**Stage mapping**: `closed_won` → WON. Use the literal from the template constraints.

**Phase total match**: Sum `phases[].amount_usd` and compare to `won_amount_usd`.

---

### invoices

```
GET /api/invoices
GET /api/invoices/<id>
```

| Field | Type | Notes |
|-------|------|-------|
| id | string | |
| invoice_number | string | |
| opportunity_id | string | |
| customer_id | string | |
| phase_id | string | Links to opportunity phase |
| phase_name | string | |
| amount_usd | float | Invoice total |
| paid_amount_usd | float | Amount paid |
| outstanding_amount_usd | float | Unpaid balance |
| status | string | paid, unpaid, partial |
| issue_date, due_date | string | |
| billing_type | string | milestone_service |

**Invoice status to payment mapping**: Use `paid_amount_usd` and `outstanding_amount_usd`. If outstanding > 0 and status is unpaid, payment_state is UNPAID. If outstanding == 0 and status is paid, payment_state is PAID. For partial, PARTIAL.

---

### payments

```
GET /api/payments
GET /api/payments/<id>
```

| Field | Type | Notes |
|-------|------|-------|
| id | string | |
| invoice_id | string | |
| opportunity_id | string | |
| customer_id | string | |
| amount_usd | float | |
| method | string | wire |
| payment_date | string | |
| reference | string | |
| status | string | posted |

---

### revenue-journals

```
GET /api/revenue-journals
GET /api/revenue-journals/<id>
```

| Field | Type | Notes |
|-------|------|-------|
| id | string | |
| opportunity_id | string | |
| invoice_id | string | |
| phase_id | string | |
| amount_usd | float | |
| debit_account | string | Deferred Revenue |
| credit_account | string | Implementation Services Revenue |
| memo | string | |
| posted_date | string | |
| status | string | posted |

**Revenue recognition status:**
- Paid invoice with matching revenue journal → RECOGNIZED
- Paid invoice with missing revenue journal → MISSING_REVENUE_JOURNAL
- Unpaid invoice → NOT_REQUIRED_UNPAID

---

### events

```
GET /api/events
GET /api/events/<id>
```

| Field | Type | Notes |
|-------|------|-------|
| id | string | |
| customer_id | string | |
| opportunity_id | string | |
| name | string | |
| event_date | string | |
| primary_contact | string | |
| voucher_code | string | Links to voucher |
| status | string | scheduled, confirmed, live, completed, tentative |
| follow_up_owner | string | |

---

### vouchers

```
GET /api/vouchers
GET /api/vouchers/<code>
```

| Field | Type | Notes |
|-------|------|-------|
| code | string | Voucher code (endpoint uses code, not id) |
| customer_id | string | |
| opportunity_id | string | |
| event_id | string | |
| description | string | |
| discount_percent | integer | Discount value (100 = free, 50 = 50% off, etc.) |
| max_redemptions | integer | |
| redemptions_used | integer | |
| status | string | active, expired, disabled, draft |
| valid_until | string | |

**Discount field in answers**: The `voucher_discount` or `discount_amount` field reflects `discount_percent` (just the integer value, e.g. 100.00 for 100%, 50.00 for 50%).
