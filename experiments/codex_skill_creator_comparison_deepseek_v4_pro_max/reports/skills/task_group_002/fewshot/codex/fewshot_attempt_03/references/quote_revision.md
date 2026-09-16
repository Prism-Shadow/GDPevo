## Quote Revision with Freight Comparison

Use this workflow when the task provides a quote ID (e.g. Q-TR-xxx), a customer, product code, confirmed quantity, and quote date, and asks for pricing plus freight options.

### Step 1: Gather source records

Fetch these via GET, filtering collection lists client-side where noted:

1. `GET /api/quotes/<quote_id>` — confirm quote exists, status is `revision_requested`
2. `GET /api/customers/<customer_id>` — get segment, payment_profile, is_recurring, customer_type
3. `GET /api/products/<product_code>` — get price_tiers[], shelf_life_months, cold_chain_required
4. `GET /api/freight-quotes` — filter by `quote_id` == the target quote; expect air, sea, road options
5. `GET /api/policies` — capture all policy rules; key ones are POL-RECURRING-NGO-PAYMENT, POL-NEW-CLIENT-PAYMENT, POL-FREIGHT-RECONFIRM, POL-QUOTE-VALIDITY, POL-EXW-SCOPE

### Step 2: Determine catalog tier pricing

Match `confirmed_quantity` to the product's price_tiers array. Find the tier where:
```
min_qty <= confirmed_quantity AND (max_qty >= confirmed_quantity OR max_qty is null)
```

Use that tier's `unit_price_usd`, `lead_time_days`, and `shelf_life_months`.

Calculate `exw_total_usd = confirmed_quantity * unit_price_usd`.

### Step 3: Determine payment terms

Rules, checked in order:

- If `customer_type == "NGO"` AND `is_recurring == true` → `NET_30_AFTER_PO` (POL-RECURRING-NGO-PAYMENT)
- If `customer_type == "NGO"` AND `is_recurring == false` → `PREPAY_100` (POL-NEW-CLIENT-PAYMENT)
- If `customer_type == "Commercial"` AND `is_recurring == true` → `NET_30_AFTER_PO`
- If `customer_type == "Government Program"` AND `is_recurring == true` → `NET_30_AFTER_PO`
- Default: use `customer.payment_profile` field value

### Step 4: Evaluate freight options

For each freight quote linked to the same `quote_id`:

**Validity check**: freight is VALID if `valid_until >= quote_date` AND `status != "stale"`. Otherwise STALE.

**Risk assessment**:
- `route_risk == "low"` → `LOW`, flag `NONE`
- `route_risk == "medium"` → `MEDIUM`, flag from risk_notes (e.g. `MEDIUM_BORDER_RISK`)
- `route_risk == "high"` → `HIGH`, flag from risk_notes

**Grand total**: `exw_total_usd + freight_cost_usd`

### Step 5: Recommend transport mode

Default recommendation:

1. Prefer SEA when available and valid (best balance of cost and reliability for bulk)
2. AIR when speed is critical and cargo supports it
3. Avoid ROAD when it has medium or high border risk, especially if stale

### Step 6: Policy flags

- `freight_reconfirmation_required`: always `true` (POL-FREIGHT-RECONFIRM)
- `all_freight_options_valid_on_quote_date`: `true` if every option's `valid_until >= quote_date`, `false` otherwise
- `recommended_mode`: result from step 5
- `customer_policy`: derived from customer segment (e.g. `RECURRING_NGO`, `RECURRING_COMMERCIAL`)

### Step 7: Fill the answer template

The template expects `quote_summary`, `freight_options[]`, and `policy_flags` sections. Fill every field with actual data from the API records. Use cent-level precision (two decimals) for all USD amounts. Dates in ISO `YYYY-MM-DD`.

### Warnings variant (train_004 style)

When the template includes `transport_decisions` with per-freight `validity_status` and `source_is_stale` fields, also populate:

- `validity_status`: `"VALID"` or `"STALE"`
- `source_is_stale`: `true` if `valid_until < quote_date` or `status == "stale"`
- `customs_border_risk`: `"LOW"`, `"MEDIUM"`, or `"HIGH"` mapped from `route_risk`
- `road_quote_invalid_or_stale`: `true` if the ROAD option is stale or expired
- `freight_warning`: include a human-readable note about reconfirmation and any expired options
