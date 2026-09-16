## RFQ Module-Level Quote

Use when the task provides an RFQ ID (e.g. RFQ-TR-xxx), customer, and asks for EXW-only module pricing.

### Step 1: Gather source records

1. `GET /api/rfqs/<rfq_id>` — confirm status, get `requested_modules[]`, `incoterm_requested`
2. `GET /api/customers/<customer_id>` — get segment, payment_profile, is_recurring, customer_type
3. For each module in `requested_modules[]`:
   - `GET /api/products/<product_code>` — get price_tiers, article_number, shelf_life_months, lead_time from tier
4. `GET /api/policies` — capture POL-INDICATIVE-EXW, POL-MODULE-GRANULARITY, POL-NEW-CLIENT-PAYMENT, POL-QUOTE-VALIDITY

### Step 2: Module granularity rule (POL-MODULE-GRANULARITY)

Quote at module level only. Do not split modules into component SKUs even if `GET /api/products/<code>` returns a `components[]` list. The RFQ's `component_composition_distractors[]` field confirms this is intentional noise.

When the RFQ narrative says "quote at module level" or "do not split into component SKUs", obey that exactly.

### Step 3: Price each line item

For each requested module:

1. Fetch the product by `product_code`
2. Use its first (or only) price tier since module RFQs typically have single-tier products; if multiple tiers exist, match quantity as in quote_revision.md
3. `unit_price` = tier's `unit_price_usd`
4. `lead_time_days` = tier's `lead_time_days`
5. `shelf_life_months` = product-level or tier `shelf_life_months`
6. `line_total = quantity * unit_price`
7. `article_number` from product

### Step 4: Payment terms for RFQ

- New NGO (customer_type == "NGO" AND is_recurring == false) → `PREPAY_100`
- Recurring NGO → `NET_30_AFTER_PO`

### Step 5: Quote controls

- `grand_total`: sum of all line totals
- `freight_excluded`: always `true` (incoterm is EXW, POL-INDICATIVE-EXW)
- `offer_validity_days`: 30 (POL-QUOTE-VALIDITY)
- `who_documentation_required`: `true` (standard for medical/WHO-governed kits)
- `quote_basis`: `"EXW_ONLY"`
- `currency`: `"USD"`

### Step 6: Fill the template

The template expects `quote_header`, `line_items[]`, and `quote_controls`. Fill all fields from API data. Two-decimal precision for all USD amounts. Dates in ISO `YYYY-MM-DD`.

### Quantity normalization

If the RFQ `requested_modules` has duplicate product codes across separate entries, consolidate them into a single line item with summed quantity (per POL-MODULE-GRANULARITY). But if the RFQ intentionally lists them separately with different quantities, keep them as separate lines.
