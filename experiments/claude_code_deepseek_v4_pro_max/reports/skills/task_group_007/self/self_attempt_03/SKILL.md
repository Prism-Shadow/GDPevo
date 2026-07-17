# Northwind ERP Operations Skill

## API Reference

**Base URL**: Use the shared ERP API at the URL provided by the runner. Do not use localhost.

### Endpoints

| Endpoint | Parameters | Returns |
|---|---|---|
| `GET /orders?wave=` | `wave` (wave ID) | All orders in the wave |
| `GET /orders/<order_id>` | — | Single order detail |
| `GET /products` | — | All products (54 SKUs) |
| `GET /products/<sku>` | — | Single product detail |
| `GET /customers` | — | All customers |
| `GET /customers/<customer_id>` | — | Single customer detail |
| `GET /warehouses` | — | WH_NORTH, WH_CENTRAL, WH_WEST |
| `GET /inventory?warehouse_id=&sku=` | optional filters | 162 records across 3 warehouses × 54 SKUs |
| `GET /purchase_orders?supplier_id=&sku=&status=` | optional filters | All POs; status: open, confirmed, received |
| `GET /shipping/quote?warehouse_id=&destination_zip=&weight_lb=&speed=` | all required | zone_distance, service_days, total_cost |
| `GET /incidents?start=&end=&supplier_id=&sku=&incident_type=&status=` | date filters required: YYYY-MM-DD | Filtered incidents |
| `GET /suppliers` | — | 12 suppliers with quality_status |
| `GET /boms` | — | All BOMs with components |
| `GET /boms/<bom_id>` | — | Single BOM detail |

### Critical Data Shapes

**Order**:
```json
{
  "order_id": "SO-70000", "wave": "TRAIN_EXPEDITE_A",
  "customer_id": "CUST-2012", "warehouse_id": "WH_CENTRAL",
  "destination_zip": "38247", "shipping_speed": "overnight|two_day|ground",
  "priority": "normal|high|critical", "required_date": "2026-05-19",
  "lines": [{"line_id": 1, "sku": "NW-1049", "quantity": 30, "unit_price": 113.51}]
}
```

**Inventory**:
```json
{"warehouse_id":"WH_CENTRAL","sku":"NW-1000","on_hand":5,"reserved":5,"quarantined":1,"last_count_date":"2025-11-21"}
```

**Product**:
```json
{"sku":"NW-1000","name":"Controller A-20","category":"electronics","active":true,
 "supplier_id":"SUP-003","unit_cost":116.62,"weight_lb":12.05,
 "safety_stock":46,"overstock_threshold":139}
```

**Customer**:
```json
{"customer_id":"CUST-2012","name":"Caldera Mfg","account_status":"active|blocked|review_required",
 "risk_flag":"none|fraud_watch|credit_watch","tier":"strategic|standard|economy","margin_band":"low|medium|high"}
```

**Shipping Quote**:
```json
{"warehouse_id":"WH_CENTRAL","destination_zip":"38247","speed":"overnight",
 "base_rate":77.95,"fuel_surcharge_rate":0.0925,"service_days":1,
 "total_cost":225.67,"weight_lb":50.0,"zone_distance":3,"carrier":"Northwind Parcel"}
```

**Incident**:
```json
{"incident_id":"INC-90003","supplier_id":"SUP-007","sku":"NW-1008",
 "incident_type":"RMA|WORK_ORDER","severity":"low|medium|high|critical",
 "status":"open|closed","open_date":"2026-01-01","close_date":"2026-01-23",
 "resolution_cost":2203.93,"root_cause":"count_variance|..."}
```

**Supplier**:
```json
{"supplier_id":"SUP-003","name":"Branson Relay Group","quality_status":"approved|watch|quality_hold","region":"Midwest"}
```

**BOM**:
```json
{"bom_id":"BOM-300","name":"Retrofit Kit 1","warehouse_id":"WH_WEST",
 "target_date":"2026-05-08","components":[{"sku":"NW-1049","quantity_per_kit":8}]}
```

---

## Key Calculation: Effective Available

```
effective_available = on_hand - reserved - quarantined
```

This is the fundamental inventory metric used across all tasks. Never use raw `on_hand` alone. Reserved and quarantined stock is not free for allocation.

---

## Task Pattern 1: Expedite Queue (train_001)

### Workflow
1. Fetch all orders in the target wave: `GET /orders?wave=<wave_id>`
2. **Filter to only the `order_ids` listed in the queue memo** — the wave may contain extra orders not in the memo.
3. Fetch all products, customers, and inventory in bulk (no-param calls).
4. For each memo order, look up its customer, warehouse, and each line's product + inventory.

### Inventory Status Classification
For each order, check all lines and determine the worst-case status:

| Condition | Status |
|---|---|
| Any line SKU is `active: false` AND any line has `effective < quantity` | `inactive_and_shortage` |
| Any line SKU is `active: false` (but all active lines have enough stock) | `inactive_sku` |
| Any line has `effective < quantity` (all SKUs active) | `shortage` |
| All lines `active: true`, all `effective >= quantity`, but any line `effective < overstock_threshold` | `low_stock` |
| All lines `active: true` and all `effective >= quantity` and all `effective >= overstock_threshold` | `ready` |

### Customer Exception Classification
Check the customer record (single field, per order):

| Customer State | Exception |
|---|---|
| `account_status == "blocked"` | `account_blocked` |
| `risk_flag == "fraud_watch"` | `fraud_watch` |
| `risk_flag == "credit_watch"` | `credit_watch` |
| `account_status == "review_required"` | `review_required` |
| None of the above | `none` |

**Precedence**: `blocked` > `fraud_watch` > `credit_watch` > `review_required` > `none`. Check in this order; return the first match.

### Final Decision Matrix

Evaluate in this strict order — first match determines both `final_decision` and `next_action`:

| Priority | Condition | Final Decision | Next Action |
|---|---|---|---|
| 1 | `account_blocked` or `fraud_watch` (any inventory) | `reject_hold` | `hold_credit_or_fraud` |
| 2 | `credit_watch` or `review_required` (any inventory) | `manual_review` | `send_account_review` |
| 3 | `inactive_sku` or `inactive_and_shortage` (customer `none`) | `manual_review` | `escalate_product_master` |
| 4 | `shortage` (customer `none`) | `delayed_release` | `delay_and_monitor` |
| 5 | `low_stock` (customer `none`) | `ship_now` | `release_to_pick` |
| 6 | `ready` (customer `none`) | `ship_now` | `release_to_pick` |

When both a customer exception (priority 2) and an inactive product exist, the `final_decision` is `manual_review` and the `next_action` is `escalate_product_master` — the product-master issue is the operational blocker. `account_blocked`/`fraud_watch` always override everything else.

### SKU Exception Lists
- **`shortage_skus`**: Lines where `effective < quantity` → list SKUs, sorted ascending.
- **`inactive_skus`**: Lines where `active == false` → list SKUs, sorted ascending.
- **`low_stock_skus`**: Lines where `active == true` AND `effective >= quantity` AND `effective < overstock_threshold` → list SKUs, sorted ascending.
- A SKU can appear in multiple lists if it meets multiple conditions. A SKU should NOT appear in `low_stock_skus` if it's already in `shortage_skus`.

### Shipping Quote
For each order, compute:
```
total_weight_lb = sum(product.weight_lb * line.quantity for each line)
```
Then call `GET /shipping/quote?warehouse_id=<order.warehouse_id>&destination_zip=<order.destination_zip>&weight_lb=<total_weight_lb>&speed=<order.shipping_speed>`.

The quote response fields map to the answer:
- `zone_distance` → `zone_distance` (integer)
- `service_days` → `service_days` (integer)
- `total_cost` → `total_cost_usd` (number, round to 2 decimals)

### Summary Aggregation
- `order_count`: number of memo orders processed
- `decision_counts`: count of each final_decision value
- `total_shipping_cost_usd`: sum of all shipping quotes, rounded to 2 decimals
- `blocked_order_ids`: orders where customer_exception in (account_blocked, fraud_watch), sorted ascending
- `manual_review_order_ids`: orders where final_decision == manual_review, sorted ascending
- `backorder_order_ids`: orders where final_decision == backorder, sorted ascending
- `inactive_sku_order_ids`: orders where inventory_status in (inactive_sku, inactive_and_shortage), sorted ascending

### Ordering
- `records` array: sort by `order_id` ascending (lexicographic string sort).
- All SKU lists: sort ascending.
- Summary lists: sort ascending.

---

## Task Pattern 2: Replenishment / Kit Run (train_002)

### Workflow
1. Fetch BOM details for each BOM in the production memo.
2. Fetch all products, all inventory, all purchase orders.
3. Aggregate component requirements across all BOMs.
4. For each unique component SKU, compute the coverage plan.

### Component Aggregation
For each BOM's components, compute per-SKU totals:
```
total_required = sum(component.quantity_per_kit * build_quantity) across all BOMs containing that SKU
```

The planning site is the warehouse from the production memo (e.g., `WH_WEST`).

### Component Plan Calculation
For each component SKU at the target warehouse:
```
target_effective_available = effective at target warehouse
gap = max(0, total_required - target_effective_available)
```

**Timely POs**: Filter POs where:
- `sku` matches
- `warehouse_id` matches target warehouse
- `status` is `open` or `confirmed`
- `eta` (date) is **on or before** the build date (use the earlier of the build dates if the SKU appears in multiple BOMs)

`timely_po_qty` = sum of quantities of all timely POs. `coverage_po_ids` = list of those PO IDs, sorted ascending.

### Final Action Determination
1. **Overstock check**: If `target_effective_available >= overstock_threshold` → `overstock_excluded`
2. **Stocked check**: If `gap <= 0` → `no_action_stocked` (exclusion: `stocked_no_gap`)
3. **Timely PO check**: If `timely_po_qty >= gap` → `timely_po_covered` (exclusion: `timely_po_covers_gap`)
4. **Transfer + Purchase**: otherwise compute transfers from other warehouses, then purchase requisition for remainder

### Transfer Logic
For the remaining gap after subtracting timely POs:
```
remaining_gap = max(0, gap - timely_po_qty)
```

Check other warehouses' effective available (exclude the target warehouse). Transfer from the warehouse with the **highest** effective available first, then the next highest, until `remaining_gap` is covered or all warehouses are exhausted.

```
transfer_qty = sum of quantities transferred from all other warehouses
purchase_requisition_qty = max(0, remaining_gap - transfer_qty)
```

**Final action** for transfer+purchase:
- If `purchase_requisition_qty == 0` (transfers cover everything) → `transfer_only`
- If `purchase_requisition_qty > 0` → `purchase_required`

### Transfer Requests
Each transfer from another warehouse becomes one record:
- `from_warehouse_id`: source warehouse
- `to_warehouse_id`: target warehouse (planning site)
- `quantity`: units transferred (integer)
- `needed_by`: the earlier of the build dates for BOMs containing this SKU

**Sorting**: by `sku` ascending → `quantity` descending → `from_warehouse_id` ascending.

### Purchase Requisitions
- `supplier_id`: from the product's `supplier_id`
- `warehouse_id`: target warehouse
- `quantity`: `purchase_requisition_qty`
- `needed_by`: the earlier of the build dates
- `unit_cost`: from product's `unit_cost`, rounded to 2 decimals
- `extended_cost`: `unit_cost * quantity`, rounded to 2 decimals

**Sorting**: by `sku` ascending.

### Excluded Components
Components with `exclusion_reason != "none"`:
- `target_overstock`: `target_effective_available >= overstock_threshold`
- `timely_po_covers_gap`: `timely_po_qty >= gap`
- `stocked_no_gap`: `gap <= 0` and not overstock

Each exclusion includes `supporting_po_ids` (sorted ascending, empty list if none).

### Summary
- `component_count`: total unique SKUs in the plan
- `total_purchase_units`: sum of all `purchase_requisition_qty`
- `total_purchase_cost`: sum of all `extended_cost`, rounded to 2 decimals
- `total_transfer_units`: sum of all `transfer_qty`
- `timely_po_covered_units`: sum of quantities from timely POs that cover gaps

---

## Task Pattern 3: Supplier Incident Scorecard (train_003)

### Workflow
1. Fetch all incidents in the date range: `GET /incidents?start=<start>&end=<end>`
2. Fetch all suppliers.
3. Group incidents by supplier. Only include suppliers with ≥1 incident.

### Duration Calculation
- **Closed incidents**: `(close_date - open_date)` in calendar days.
- **Open incidents**: `(analysis_date - open_date)` in calendar days.
- `avg_duration_days` = mean of all durations, rounded to **2 decimal places**.

### Incident Percentage
```
incident_percentage = (supplier_incident_count / total_filtered_incidents) * 100
```
Rounded to **1 decimal place**.

### Severity Classification
Severe severity values: `"high"`, `"critical"`.

### Recommendation Policy (Precedence Order)

**ESCALATE_SUPPLIER** — first match wins (OR conditions):
1. `quality_status == "quality_hold"` AND `incident_count >= 3`
2. Any incident where `incident_type == "RMA"` AND `severity == "critical"`
3. `rma_count >= 3` AND `total_resolution_cost >= 15000.00`

**PROCESS_REVIEW** (only if ESCALATE_SUPPLIER doesn't apply):
- `work_order_count >= 3` AND `work_order_count > rma_count`

**WATCHLIST** (only if neither above applies, OR conditions):
1. `quality_status` is `"watch"` or `"quality_hold"`
2. `incident_count >= 4`
3. `total_resolution_cost >= 12000.00`
4. `severe_incident_count >= 2`

**MONITOR**: none of the above.

Evaluate in strict precedence order: ESCALATE_SUPPLIER first, then PROCESS_REVIEW, then WATCHLIST, then MONITOR.

### Scorecard Output
- `supplier_scorecard`: rows sorted by `supplier_id` ascending.
- `top_escalation_suppliers`: supplier_ids where recommendation is `ESCALATE_SUPPLIER`, sorted by `incident_count` descending → `total_resolution_cost` descending → `supplier_id` ascending.
- `highest_cost_supplier_id`: supplier with max `total_resolution_cost`.
- `highest_share_supplier_id`: supplier with max `incident_percentage` (tiebreak: max `incident_count`).

### Summary
- `filtered_incident_count`: total incidents in date range
- `supplier_count`: distinct suppliers with ≥1 incident
- `total_resolution_cost`: sum of all resolution costs, rounded to 2 decimals
- `overall_rma_count`: total incidents of type RMA
- `overall_work_order_count`: total incidents of type WORK_ORDER

---

## Task Pattern 4: Allocation Desk (train_004)

### Workflow
1. Fetch all orders in the target wave.
2. Fetch all customers, products, and inventory.
3. For each order line, determine the action.

### Line Action Determination (Precedence)
Check in this order; first match wins:

1. **`manual_review`**: Customer `account_status == "blocked"` → reason: `account_blocked`
2. **`manual_review`**: Customer `risk_flag == "fraud_watch"` → reason: `fraud_watch`
3. **`manual_review`**: Customer `account_status == "review_required"` → reason: `account_review_required`
4. **`manual_review`**: Product `active == false` → reason: `inactive_product`
5. **`ship`**: `effective >= quantity` at requested warehouse → reason: `none`, `ship_quantity = quantity`
6. **`transfer`**: Another warehouse can cover the shortfall (see below) → reason: `insufficient_effective_stock`
7. **`backorder`**: No warehouse can cover → reason: `insufficient_effective_stock`

### Transfer Determination
When action is `transfer`:
```
ship_quantity = effective at requested warehouse (capped at line quantity)
shortfall = quantity - ship_quantity
```

Find a single source warehouse where `effective >= shortfall`. Prefer the one with the **highest effective available**. Only one source warehouse per line.

```
transfer_from = chosen source warehouse_id
transfer_quantity = shortfall
backorder_quantity = 0
```

If no single warehouse can cover the full shortfall, the line is `backorder`:
```
ship_quantity = 0
transfer_from = null, transfer_quantity = 0
backorder_quantity = quantity
```

### Transfer Requests
For each transfer line, create one transfer request:
- `from_warehouse`: source warehouse
- `to_warehouse`: order's requested warehouse
- `quantity`: transfer_quantity

Sort by `order_id` ascending → `line_id` ascending.

### Blocked Orders
Orders where ALL lines have action `manual_review` due to `account_blocked` or `fraud_watch` (not due to product or review_required issues). These are account-level blocks, not line-level. Sort ascending.

### Order Rollup
For each order, determine the single outcome:
- `ready_to_ship`: all lines have action `ship`
- `needs_transfer`: at least one transfer line, no backorders or manual_review
- `has_backorder`: at least one backorder line, no manual_review
- `manual_review`: at least one manual_review line
- `mixed_actions`: multiple action types that don't fit the above

### Summary (all integers)
- `total_orders`, `total_lines`
- `ship_lines`, `transfer_lines`, `backorder_lines`, `manual_review_lines`
- `blocked_orders` (count, not list)
- `transfer_units`, `backorder_units`
- `ship_lines` are lines with action `ship`; count `transfer_lines`, `backorder_lines`, `manual_review_lines` similarly.

### Ordering
- `line_actions`: sort by `order_id` asc → `line_id` asc
- `transfer_requests`: sort by `order_id` asc → `line_id` asc
- `order_rollup`: sort by `order_id` asc

---

## Task Pattern 5: Procurement Quality Control (train_005)

### Workflow
1. Fetch incidents per target supplier in the analysis date range.
2. Fetch supplier details for quality_status.
3. Fetch all purchase orders for each supplier.

### Decision Logic
For each supplier:

| Condition | Decision |
|---|---|
| `quality_status == "quality_hold"` | `freeze_new_replenishment` |
| `quality_status == "watch"` OR `recent_rma_count >= 2` OR `severe_or_critical_count >= 2` OR `open_incident_count >= 3` | `buyer_review_required` |
| Otherwise | `monitor_only` |

Evaluate in this order.

### Held POs
- For `freeze_new_replenishment` and `buyer_review_required` suppliers: include ALL open/confirmed POs for that supplier in `held_po_ids` (per supplier and in the global unique sorted list).
- For `monitor_only` suppliers: no POs held.

### Supplier Decision Fields
- `affected_skus`: unique SKUs from the supplier's incidents, sorted ascending.
- `sample_incident_ids`: up to 5 incident IDs, sorted ascending.
- `held_po_ids`: sorted list of open/confirmed PO IDs for this supplier (empty for monitor_only).
- All counts (`recent_incident_count`, `recent_rma_count`, etc.) are integers.

### Summary
- `suppliers_reviewed`: count of suppliers evaluated
- `freeze_count`, `buyer_review_count`, `monitor_count`: counts per decision
- `held_po_count`: total unique held PO IDs
- `total_recent_incidents`: sum of all recent incident counts

### Release Suppliers
`release_supplier_ids`: sorted list of supplier IDs where decision is `monitor_only`.

### Ordering
- `supplier_decisions`: sort by `supplier_id` ascending.
- All ID/PO lists: sorted ascending.

---

## Cross-Cutting Rules

### Currency Precision
All monetary values (`total_cost_usd`, `total_resolution_cost`, `unit_cost`, `extended_cost`, etc.): round to **2 decimal places** using standard rounding (`round(x, 2)`).

### Percentage Precision
Incident percentages: round to **1 decimal place**.

### Duration Precision
Average duration in days: round to **2 decimal places**.

### Sorting Conventions
- Order IDs, SKU strings, supplier IDs, PO IDs: **lexicographic string sort** (ascending).
- SKU lists within records: ascending lexicographic.
- When sort key includes multiple fields, apply in the order specified; use subsequent fields as tiebreakers.

### Null Handling
- Missing inventory records: treat as `on_hand=0, reserved=0, quarantined=0, effective=0`.
- `close_date: null` for open incidents: use `analysis_date` for duration calculation.
- `transfer_from` for non-transfer lines: `null` (JSON null).

### API Call Efficiency
- Fetch full lists (products, customers, inventory, suppliers, purchase_orders) once and index locally by key fields.
- Use filtered endpoints (`/incidents?start=&end=`, `/orders?wave=`) for date/wave scoping.
- Re-fetch individual resources only when the bulk data is insufficient.

### Common Pitfalls
1. **Using `on_hand` directly** instead of `effective = on_hand - reserved - quarantined`. Reserved and quarantined stock is unavailable.
2. **Including wave orders not in the memo** — always filter to the explicit `order_ids` list.
3. **Wrong precedence in decision trees** — account blocks/fraud always override inventory status.
4. **Forgetting to exclude shortage SKUs from low_stock_skus** — a SKU in shortage should not also appear in low_stock.
5. **Timely PO date comparison** — "timely" means PO `eta` ≤ build date. An open PO arriving after the build date does not help.
6. **Single-source transfer rule** — for allocation (train_004), choose ONE source warehouse that can cover the full shortfall; don't split transfers across multiple warehouses for a single line.
7. **Multi-source transfer rule** — for replenishment (train_002), transfers CAN come from multiple warehouses, sorted by quantity descending.
8. **Overstock threshold** — compare effective available against `overstock_threshold` from the product record at the target warehouse.
9. **Supplier quality_status in decisions** — `quality_hold` always triggers freeze (task 5) or ESCALATE (task 3); `watch` triggers buyer_review or WATCHLIST.
10. **Shipping quote uses total order weight** — sum `product.weight_lb × line.quantity` for ALL lines in the order.
