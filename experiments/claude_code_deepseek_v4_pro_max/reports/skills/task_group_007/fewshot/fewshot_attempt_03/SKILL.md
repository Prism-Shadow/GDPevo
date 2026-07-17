# Northwind ERP Operations — Task Group 007 Skill

## Environment

- **Base URL**: `http://34.46.77.124:8007` (always; ignore any prompt mentioning localhost or 127.0.0.1)
- All data comes from live API calls; do not use cached/static values
- Return **only** JSON matching the supplied `answer_template.json` — no narrative text outside the JSON

## Entity ID Conventions

| Entity | Pattern | Example |
|--------|---------|---------|
| Sales Orders | `SO-XXXXX` (5 digits) | `SO-70000` |
| Products / SKUs | `NW-XXXX` (4 digits) | `NW-1003` |
| Suppliers | `SUP-XXX` (3 digits) | `SUP-003` |
| Purchase Orders | `PO-XXXXX` (5 digits) | `PO-50066` |
| Incidents | `INC-XXXXX` (5 digits) | `INC-90004` |
| BOMs | `BOM-XXX` (3 digits) | `BOM-300` |
| Warehouses | `WH_NORTH`, `WH_CENTRAL`, `WH_WEST` | — |

## Common API Endpoints

Use standard REST patterns against the base URL. Key resource paths (inferred from task requirements):

- `/orders` — sales orders with lines, quantities, requested warehouses
- `/orders/{id}` — single order detail including line items with SKU and qty
- `/products` — product master: SKU, name, is_active, supplier_id, unit_cost
- `/products/{sku}` — single product detail
- `/customers` — customer master: status flags (blocked, review_required, fraud_watch, credit_watch)
- `/customers/{id}` — single customer detail
- `/inventory` — warehouse×SKU inventory: on_hand, reserved, quarantined, buffer
- `/warehouses` — warehouse list
- `/suppliers` — supplier master: name, quality_status
- `/suppliers/{id}` — single supplier detail
- `/incidents` — quality incidents: open_date, close_date, severity, type (RMA/WORK_ORDER), resolution_cost, supplier_id, sku, status
- `/purchase-orders` — POs with status, delivery_date, warehouse_id, sku, quantity
- `/purchase-orders/{id}` — single PO detail
- `/boms` — BOM structures with component SKUs and quantities
- `/boms/{id}` — single BOM detail
- `/shipping-quotes` — shipping quotes by order/warehouse: zone_distance, service_days, total_cost

## Numeric Precision Rules

| Measure | Precision | Example |
|---------|-----------|---------|
| Currency (USD) | **2 decimal places**, round half-up | `16412.62` |
| Percentages | **1 decimal place** | `23.7` (means 23.7%) |
| Duration (days) | **2 decimal places** | `58.22` |
| All integer counts | exact integer | `8` |

## Sorting Rules (Consistent Across All Tasks)

- **Order IDs**: ascending string sort (`SO-70000` < `SO-70007`)
- **SKUs**: ascending string sort (`NW-1000` < `NW-1003`)
- **Supplier IDs**: ascending string sort (`SUP-001` < `SUP-003`)
- **Line IDs**: ascending integer
- **Transfer requests**: by `sku` ascending, then `quantity` descending, then `from_warehouse_id` ascending
- **Summary lists** (blocked_order_ids, etc.): ascending
- Always apply the ordering specified in the answer template — templates are authoritative

## Common Enum Values

### Customer Exception / Status
`none`, `review_required`, `account_blocked`, `fraud_watch`, `credit_watch`

### Inventory Status (per-order rollup)
`ready`, `low_stock`, `shortage`, `inactive_sku`, `inactive_and_shortage`

### Fulfillment Decisions
`ship_now`, `delayed_release`, `manual_review`, `backorder`, `reject_hold`

### Next Actions
`release_to_pick`, `delay_and_monitor`, `send_account_review`, `create_backorder`, `hold_credit_or_fraud`, `escalate_product_master`

### Line Actions (allocation)
`ship`, `transfer`, `backorder`, `manual_review`

### Primary Reasons (allocation)
`none`, `account_blocked`, `account_review_required`, `fraud_watch`, `inactive_product`, `insufficient_effective_stock`

### Order Outcomes (rollup)
`ready_to_ship`, `needs_transfer`, `has_backorder`, `manual_review`, `mixed_actions`

### Replenishment Final Actions
`no_action_stocked`, `transfer_only`, `purchase_required`, `timely_po_covered`, `overstock_excluded`

### Exclusion Reasons
`none`, `target_overstock`, `timely_po_covers_gap`, `stocked_no_gap`

### Recommendation Codes (scorecard)
`ESCALATE_SUPPLIER`, `PROCESS_REVIEW`, `WATCHLIST`, `MONITOR`

### Quality Hold Decisions
`freeze_new_replenishment`, `buyer_review_required`, `monitor_only`

### Quality Status
`approved`, `watch`, `quality_hold`

### Severity Values (for "severe" classification)
`high`, `critical`

---

## Desk 1: Expedite Queue Dispatch (train_001 pattern)

**Input**: Wave memo with `order_ids`, answer template with enums.

**Per-order logic**:

1. **Inventory Status** — check every line SKU on the order:
   - If any SKU `is_active == false` AND any SKU has shortage → `inactive_and_shortage`
   - If any SKU `is_active == false` (but no shortage) → `inactive_sku`
   - If any SKU has `effective_available < ordered_qty` → `shortage`
   - If all SKUs available but some below buffer threshold → `low_stock`
   - Otherwise → `ready`
   - Populate `shortage_skus` (effective < ordered), `inactive_skus` (is_active=false), `low_stock_skus` (effective > 0 but below threshold), each sorted ascending

2. **Customer Exception** — read customer status from API:
   - `account_blocked`, `review_required`, `fraud_watch`, `credit_watch`, or `none`

3. **Final Decision + Next Action** — precedence order (first match wins):

   | Customer Exception | → | Final Decision | Next Action |
   |---|---|---|---|
   | `account_blocked` | | `reject_hold` | `hold_credit_or_fraud` |
   | `review_required` | | `manual_review` | `send_account_review` |
   | `fraud_watch` | | `manual_review` | `send_account_review` |
   | `credit_watch` | | `manual_review` | `send_account_review` |

   When customer exception is `none`, use inventory status:

   | Inventory Status | → | Final Decision | Next Action |
   |---|---|---|---|
   | `ready` | | `ship_now` | `release_to_pick` |
   | `low_stock` | | `delayed_release` | `delay_and_monitor` |
   | `shortage` | | `backorder` | `create_backorder` |
   | `inactive_sku` | | `manual_review` | `escalate_product_master` |
   | `inactive_and_shortage` | | `manual_review` | `escalate_product_master` |

4. **Shipping Quote** — fetch from `/shipping-quotes` for the order (respect requested shipping speed/destination warehouse). Fields: `zone_distance` (int), `service_days` (int), `total_cost_usd` (2 decimals).

5. **Summary**:
   - `order_count`: total records
   - `decision_counts`: count of each decision value (all five keys always present, even if 0)
   - `total_shipping_cost_usd`: sum of all `total_cost_usd` (2 decimals)
   - `blocked_order_ids`: orders with `reject_hold` (sorted)
   - `manual_review_order_ids`: orders with `manual_review` (sorted)
   - `backorder_order_ids`: orders with `backorder` (sorted)
   - `inactive_sku_order_ids`: orders where `inactive_skus` is non-empty (sorted)

---

## Desk 2: Kit Build Replenishment (train_002 pattern)

**Input**: Production memo with BOM IDs, build quantities, build dates, target warehouse.

**Core calculation per component SKU**:

1. **total_required** = sum over all kit targets of (BOM component quantity × build_quantity)

2. **target_effective_available** = `effective_available` at the target warehouse − `total_required`
   - `effective_available` = on_hand − reserved − quarantined − buffer
   - Positive value = surplus; negative = shortage relative to full coverage

3. **Total gap to fill** = `max(0, total_required − target_effective_available)`

4. **Coverage priority chain** (fill the gap in order):
   - **Timely POs**: open/confirmed POs for this SKU at the target warehouse with `delivery_date` before the earliest build date
   - **Transfers**: available effective stock at other warehouses (exclude reserved/quarantined/buffer)
   - **Purchase requisition**: remaining gap = `max(0, total_gap − timely_po_qty − transfer_qty)`

5. **final_action** determination:
   - `target_effective_available >= 0` and no other demand → `overstock_excluded`
   - `timely_po_qty >= total_gap` → `timely_po_covered`
   - `total_gap > 0` and `total_gap == transfer_qty` (no purchase needed) → `transfer_only`
   - `purchase_requisition_qty > 0` → `purchase_required`
   - `total_gap == 0` and not overstock → `no_action_stocked`

6. **Transfer requests**: Split across source warehouses, prefer warehouses with most available stock. Sort by `sku` asc → `quantity` desc → `from_warehouse_id` asc. `needed_by` = earliest build date that needs this component.

7. **Purchase requisitions**: Use supplier from product master (`/products/{sku}`). `unit_cost` from product/supplier data. `extended_cost = quantity × unit_cost` (2 decimals). Sort by `sku` asc. `needed_by` = latest build date requiring this component.

8. **Excluded components**: Components with `overstock_excluded` or `timely_po_covered` final action. `reason` = `target_overstock` or `timely_po_covers_gap`. Sort by `sku` asc. `supporting_po_ids` sorted ascending.

9. **Summary**:
   - `component_count`: distinct SKUs in component_plan
   - `total_purchase_units`: sum of all `purchase_requisition_qty`
   - `total_purchase_cost`: sum of all `extended_cost` (2 decimals)
   - `total_transfer_units`: sum of all `transfer_qty` in transfer_requests
   - `timely_po_covered_units`: sum of `(total_required − target_effective_available)` for components where `final_action == "timely_po_covered"`

---

## Desk 3: Supplier Incident Scorecard (train_003 pattern)

**Input**: Date range, analysis date, recommendation policy.

**Procedure**:

1. Fetch all incidents from `/incidents`. Filter to those with `open_date` between `start_date` and `end_date` (inclusive).

2. For each supplier with ≥1 filtered incident, compute:
   - `incident_count`: number of filtered incidents
   - `incident_percentage`: `(supplier_incidents / total_filtered_incidents) × 100`, rounded to **1 decimal**
   - `total_resolution_cost`: sum of `resolution_cost`, rounded to **2 decimals**
   - `avg_duration_days`: for each incident, duration = `close_date − open_date` (closed) or `analysis_date − open_date` (open). Average all durations, round to **2 decimals**
   - `rma_count`: incidents where `type == "RMA"`
   - `work_order_count`: incidents where `type == "WORK_ORDER"`
   - `open_incident_count`: incidents where `status` is open (no close_date)
   - `severe_incident_count`: incidents where `severity` ∈ `{high, critical}`

3. **Recommendation code** — evaluate in precedence order, first match wins:
   - `ESCALATE_SUPPLIER`: `quality_status == "quality_hold" AND incident_count >= 3`, OR any incident with critical RMA, OR `rma_count >= 3 AND total_resolution_cost >= 15000.00`
   - `PROCESS_REVIEW`: `work_order_count >= 3 AND work_order_count > rma_count`
   - `WATCHLIST`: `quality_status` ∈ `{watch, quality_hold}`, OR `incident_count >= 4`, OR `total_resolution_cost >= 12000.00`, OR `severe_incident_count >= 2`
   - `MONITOR`: none of the above

4. **Sort** scorecard rows by `supplier_id` ascending.

5. **top_escalation_suppliers**: only suppliers with `ESCALATE_SUPPLIER`, ordered by `incident_count` desc → `total_resolution_cost` desc → `supplier_id` asc.

6. **highest_cost_supplier_id**: supplier with max `total_resolution_cost`. **highest_share_supplier_id**: supplier with max `incident_percentage`. (Ties: lower `supplier_id`.)

---

## Desk 4: Allocation Desk — Mixed-Warehouse Transfer (train_004 pattern)

**Input**: Wave ID, order lines from API.

**Per-line action decision** — evaluated in this precedence order:

| Condition | Action | ship_qty | transfer_qty | backorder_qty | primary_reason |
|---|---|---|---|---|---|
| Customer `account_blocked` | `manual_review` | 0 | 0 | 0 | `account_blocked` |
| Customer `review_required` flag | `manual_review` | 0 | 0 | 0 | `account_review_required` |
| Customer `fraud_watch` flag | `manual_review` | 0 | 0 | 0 | `fraud_watch` |
| Product `is_active == false` | `manual_review` | 0 | 0 | 0 | `inactive_product` |
| Any other order-line on same order triggers manual_review | `manual_review` | 0 | 0 | 0 | same reason as triggering line |
| `effective_available >= ordered_qty` | `ship` | ordered_qty | 0 | 0 | `none` |
| `effective_available < ordered_qty` AND another warehouse can cover shortfall | `transfer` | effective_available | shortfall | 0 | `none` |
| `effective_available < ordered_qty` AND no warehouse can cover | `backorder` | 0 | 0 | ordered_qty | `insufficient_effective_stock` |

**Contagion rule**: If any line on an order is `manual_review`, ALL lines on that order become `manual_review` with the same `primary_reason` as the triggering line.

**Transfer details**:
- `transfer_from`: single source warehouse with highest available effective stock (not reserved/quarantined/buffer)
- `transfer_quantity`: amount transferred from source (shortfall quantity)
- `ship_quantity`: min(ordered_qty, effective_available at requested warehouse) — the portion the requested warehouse CAN fulfill
- When requested warehouse has zero or negative effective, `ship_quantity = 0`

**Order rollup** — classify each order by its line actions (precedence: manual_review > mixed > backorder > transfer > ship):
- Any line `manual_review` → `manual_review`
- Mix of `ship`+`transfer`+`backorder` (no manual_review) → `mixed_actions`
- Any `backorder` (no manual_review, no mixed ship/transfer) → `has_backorder`
- Any `transfer` (no manual_review, no backorder) → `needs_transfer`
- All `ship` → `ready_to_ship`

**blocked_orders**: all order_ids with any `manual_review` line (sorted). Include account-blocked, account-review, fraud-watch, and inactive-product orders.

**Summary** counts: `total_orders`, `total_lines`, `ship_lines`, `transfer_lines`, `backorder_lines`, `manual_review_lines`, `blocked_orders`, `transfer_units` (sum of transfer_quantity), `backorder_units` (sum of backorder_quantity).

---

## Desk 5: Procurement Quality Hold Review (train_005 pattern)

**Input**: Target supplier IDs, analysis window dates, decision policy.

**Per-supplier analysis**:

1. Fetch incidents in the date window for each target supplier.
2. Fetch supplier master for `quality_status` and `supplier_name`.
3. Fetch open/confirmed POs for the supplier (any warehouse).

**Computed fields per supplier**:
- `recent_incident_count`: incidents in window
- `recent_rma_count`: incidents where `type == "RMA"`
- `severe_or_critical_count`: incidents where `severity` ∈ `{high, critical}`
- `open_incident_count`: incidents still open (no close_date)
- `affected_skus`: distinct SKUs from the supplier's incidents (sorted ascending)
- `sample_incident_ids`: up to 5 IDs from the supplier's incidents (sorted ascending)

**Decision logic**:
- `freeze_new_replenishment`: `quality_status == "quality_hold"` with significant issues (multiple incidents, high severity)
- `buyer_review_required`: moderate incident count, or `quality_status == "watch"` with concerning patterns
- `monitor_only`: low incident count, no immediate action needed

**held_po_ids** (per supplier): open/confirmed POs for that supplier's `affected_skus` (sorted). The global `held_po_ids` is the sorted union across all suppliers.

**release_supplier_ids**: suppliers whose decision is `monitor_only` (sorted).

**Summary**: `suppliers_reviewed`, `freeze_count`, `buyer_review_count`, `monitor_count`, `held_po_count`, `total_recent_incidents`.

---

## Field Pitfalls

1. **Null vs empty**: Use `null` for `transfer_from` when action is not `transfer`. Use `[]` for empty SKU/PO lists, not `null`.
2. **All enum values must match exactly** — case-sensitive, underscores preserved. Never invent new values.
3. **Shipping cost is per-order, not per-line** — look up once per order.
4. **Effective available is net of all holds**: `on_hand − reserved − quarantined − buffer`. Never use raw `on_hand`.
5. **Contagion rule in allocation (Desk 4)**: one blocked line blocks the whole order. Apply before computing inventory-based actions for other lines.
6. **Recommendation precedence in scorecard (Desk 3)**: evaluate ESCALATE_SUPPLIER first, then PROCESS_REVIEW, then WATCHLIST, then MONITOR. Do not skip tiers.
7. **Transfer filling order**: exhaust the largest source warehouse first. Split transfers across warehouses only when a single source cannot cover the full shortfall.
8. **Currency rounding**: always round to 2 decimals using half-up. Compute `extended_cost` from the rounded `unit_cost × quantity` and round the result too.
9. **Percentage rounding**: round to 1 decimal place. Values like 2.63… → `2.6`.
10. **Template keys**: every key in the answer template must appear in the output, even if its value is 0 or `[]`. Do not omit keys.

## Reusable SOP

1. Read the input memo/prompt and `answer_template.json` first — the template defines the exact output shape and enum values.
2. Query the ERP API for all referenced entities (orders, products, customers, inventory, suppliers, incidents, POs, BOMs, shipping quotes).
3. Compute effective inventory: `on_hand − reserved − quarantined − buffer` per warehouse×SKU.
4. Apply decision logic in the documented precedence order — customer/account flags before inventory, product status before stock levels.
5. Build output JSON matching the template exactly — sort all lists as specified, use correct precision, include all required keys.
6. Compute summary/rollup fields last after all per-record decisions are finalized.
7. Validate: check all enum values against allowed sets, verify numeric precision, confirm sort orders.
