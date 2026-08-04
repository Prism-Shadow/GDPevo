 # Northwind ERP Operations Skill

 ## Overview

 This skill provides reusable patterns for solving Northwind Components ERP operations tasks. The ERP exposes a REST API with data about products, inventory, customers, orders, suppliers, purchase orders, BOMs, incidents, and shipping quotes. Tasks typically involve cross-referencing live API records to make dispatch, replenishment, allocation, or quality-control decisions.

 ## API Data Structures

 ### Products (`/products`, `/products/{sku}`)

 | Field | Type | Notes |
 |-------|------|-------|
 | `sku` | string | Primary key, format `NW-XXXX` |
 | `active` | boolean | False means product is discontinued/inactive |
 | `safety_stock` | integer | Minimum stock to retain as buffer |
 | `overstock_threshold` | integer | Upper bound before flagging excess |
 | `supplier_id` | string | Links to `/suppliers` |
 | `unit_cost` | number | Cost per unit in USD |
 | `weight_lb` | number | Weight per unit in pounds |

 ### Inventory (`/inventory`, `/inventory/{sku}`)

 | Field | Type | Notes |
 |-------|------|-------|
 | `on_hand` | integer | Physical units in warehouse |
 | `reserved` | integer | Units already allocated to orders |
 | `quarantined` | integer | Units held for quality inspection |
 | `warehouse_id` | string | `WH_NORTH`, `WH_CENTRAL`, or `WH_WEST` |

 **Effective available** = `on_hand - reserved - quarantined`

 **Freely available (for allocation)** = `max(0, effective_available - safety_stock)`

 Use effective available for general inventory checks. Use freely available when making allocation decisions that must not dip into safety-stock buffers.

 ### Customers (`/customers`, `/customers/{customer_id}`)

 | Field | Type | Notes |
 |-------|------|-------|
 | `account_status` | string | `active`, `blocked`, or `review_required` |
 | `risk_flag` | string | `none`, `fraud_watch`, or `credit_watch` |
 | `tier` | string | `strategic`, `standard`, or `economy` |

 **Customer exception priority (highest first):**
 1. `account_status == "blocked"` → account is locked
 2. `risk_flag == "fraud_watch"` → potential fraud
 3. `risk_flag == "credit_watch"` → credit risk
 4. `account_status == "review_required"` → needs account clearance

 ### Orders (`/orders`, `/orders/{order_id}`)

 Key fields: `order_id`, `customer_id`, `warehouse_id`, `destination_zip`, `shipping_speed` (`ground`, `two_day`, `overnight`), `priority`, `wave`, and `lines[]` (each with `line_id`, `sku`, `quantity`, `unit_price`).

 ### Purchase Orders (`/purchase_orders`)

 Each record is a flat item: `po_id`, `sku`, `quantity`, `status` (`open`, `confirmed`, `received`, `cancelled`), `supplier_id`, `warehouse_id`, `eta` (YYYY-MM-DD).

 A PO is considered **timely** when its `eta` is on or before the target date AND its status is `open` or `confirmed`.

 ### BOMs (`/boms`, `/boms/{bom_id}`)

 Each BOM has `bom_id`, `name`, `warehouse_id`, and `components[]` (each with `sku` and `quantity_per_kit`).

 ### Incidents (`/incidents`, `/incidents/{incident_id}`)

 | Field | Type | Notes |
 |-------|------|-------|
 | `incident_id` | string | `INC-XXXXX` |
 | `supplier_id` | string | Links to supplier |
 | `open_date` / `close_date` | YYYY-MM-DD | Close may be null |
 | `status` | string | `open` or `closed` |
 | `severity` | string | `low`, `medium`, `high`, `critical` |
 | `incident_type` | string | `RMA` or `WORK_ORDER` |
 | `resolution_cost` | number | USD |

 **Duration:** For closed incidents, calendar days from `open_date` to `close_date`. For open incidents, days from `open_date` to the analysis date.

 ### Shipping Quote (`/shipping/quote`)

 Required query parameters: `warehouse_id`, `destination_zip`, `weight_lb`, `speed`.

 Returns: `zone_distance` (int), `service_days` (int), `total_cost` (float USD).

 Always round `total_cost` to 2 decimals.

 ### Suppliers (`/suppliers`, `/suppliers/{supplier_id}`)

 Key fields: `supplier_id`, `name`, `quality_status` (`approved`, `watch`, `quality_hold`).

 ## Decision Patterns

 ### Inventory Status Classification

 For each order, evaluate all lines against the requested warehouse inventory:

- **`ready`**: Every line's effective available ≥ requested quantity AND effective available ≥ quantity + safety_stock.
- **`low_stock`**: Every line can be fulfilled (effective ≥ quantity) but at least one line's effective drops below `quantity + safety_stock`.
- **`shortage`**: At least one active-product line has effective available < requested quantity.
- **`inactive_sku`**: At least one line's product is inactive (`active == false`), and no active-line shortage exists.
- **`inactive_and_shortage`**: Both an inactive product AND an active-line shortage exist in the same order.

 Track three separate SKU lists:
- `shortage_skus`: active SKUs where effective < quantity (sorted ascending).
- `inactive_skus`: SKUs where product `active` is false (sorted ascending).
- `low_stock_skus`: active SKUs where effective ≥ quantity but effective < quantity + safety_stock (sorted ascending).

 An inactive SKU should NOT also appear in `shortage_skus` or `low_stock_skus`.

 ### Customer Exception Classification

 Check `account_status` and `risk_flag` in priority order:
 1. `account_blocked`: `account_status == "blocked"`
 2. `fraud_watch`: `risk_flag == "fraud_watch"`
 3. `credit_watch`: `risk_flag == "credit_watch"`
 4. `review_required`: `account_status == "review_required"`
 5. `none`: no flags present

 ### Final Decision Logic

 Combine inventory status and customer exception using this precedence:

 1. **Account/fraud issues always override inventory.** If customer exception is `account_blocked`, `fraud_watch`, `credit_watch`, or `review_required`, the order requires `manual_review` regardless of stock levels.
 2. **Inactive products require escalation.** If any line has an inactive SKU (regardless of customer status), flag for `manual_review` with product-master escalation.
 3. **Shortages become backorders.** When inventory is insufficient and no customer/product blocks exist, create a backorder.
 4. **Low stock gets delayed release.** When stock is tight but sufficient, delay and monitor.
 5. **Ready stock ships now.** When all lines are fully covered above safety stock levels, release to pick.

 Decision-to-action mapping:

| Final Decision | Next Action |
|---|---|
| `ship_now` | `release_to_pick` |
| `delayed_release` | `delay_and_monitor` |
| `manual_review` | `send_account_review` (customer issue) or `escalate_product_master` (inactive SKU) |
| `backorder` | `create_backorder` |
| `reject_hold` | `hold_credit_or_fraud` |

 ### Allocation Line Actions

 For each order line at its requested warehouse:

 1. Compute `free = max(0, effective_available - safety_stock)` at the requested warehouse.
 2. If `free >= quantity` → **`ship`** the full quantity.
 3. If `free < quantity` → look for a single other warehouse where `free >= shortage`. If found → **`transfer`** that shortage amount from the source warehouse. Leave the portion that can ship from the requested warehouse as `ship_quantity`.
 4. If no warehouse can fully cover the shortage → **`backorder`** the uncovered quantity. Include any shippable portion from the requested warehouse as `ship_quantity`.
 5. Customer account issues (blocked, fraud_watch) or inactive products force **`manual_review`** and block allocation.

 Transfer requests require: `order_id`, `line_id`, `sku`, `from_warehouse`, `to_warehouse`, `quantity`.

 ### Replenishment Planning

 For kit-build replenishment:

 1. Compute total required per SKU by summing `quantity_per_kit × build_quantity` across all BOMs.
 2. Subtract current effective available at the target warehouse to get the gap.
 3. Check for timely POs (same warehouse, same SKU, `open` or `confirmed` status, eta ≤ latest build date).
 4. If current stock covers → `no_action_stocked`.
 5. If timely POs cover the gap → `timely_po_covered`.
 6. If gap remains after POs → try inter-warehouse transfers (effective available at source warehouses).
 7. Any remaining gap → purchase requisition at the product's `unit_cost`.

 For transfers, prefer the source warehouse with the most available stock. Sort transfer requests by SKU ascending, then quantity descending, then `from_warehouse_id` ascending.

 Purchase requisitions include: `supplier_id` (from product master), `warehouse_id` (target), `quantity`, `needed_by`, `unit_cost` (rounded to 2 decimals), `extended_cost` (quantity × unit_cost, rounded to 2 decimals).

 Excluded components are those with `final_action` of `no_action_stocked`, `timely_po_covered`, or `overstock_excluded`.

 ### Supplier Incident Scorecard

 1. Filter incidents by `open_date` within the analysis window (inclusive).
 2. Group by `supplier_id`. Compute per-supplier: incident count, percentage of total filtered population (1 decimal), total resolution cost (2 decimals), average duration in days (2 decimals), RMA count, WORK_ORDER count, open incident count, severe (high/critical) incident count.
 3. Apply recommendation policy by precedence (first match wins):
    - `ESCALATE_SUPPLIER`: quality_hold with ≥3 incidents, OR any critical RMA, OR ≥3 RMAs with ≥$15,000 total cost.
    - `PROCESS_REVIEW`: WORK_ORDER count ≥3 AND exceeds RMA count.
    - `WATCHLIST`: quality_status is watch or quality_hold, OR incident count ≥4, OR total cost ≥$12,000, OR severe count ≥2.
    - `MONITOR`: none of the above.
 4. Sort scorecard rows by `supplier_id` ascending. List `top_escalation_suppliers` sorted by incident count descending, then cost descending, then supplier_id ascending.

 ### Quality Hold Review

 1. Filter incidents within the analysis window for target suppliers.
 2. Compute: recent incident count, RMA count, severe/critical count, open count, affected SKUs (sorted), sample incident IDs (up to 5, sorted).
 3. Find open/confirmed POs for each supplier.
 4. Decision rule: `quality_hold` → `freeze_new_replenishment`. `watch` → `buyer_review_required`. Otherwise → `monitor_only`.
 5. Only freeze-level suppliers contribute their PO IDs to the global `held_po_ids` list (sorted unique). Only monitor-level suppliers appear in `release_supplier_ids` (sorted).
 6. Each supplier's `held_po_ids` field should include their open/confirmed POs only if the decision is `freeze_new_replenishment`; otherwise an empty list.

 ## Shipping Quotes

 Always call `/shipping/quote` with all four parameters: `warehouse_id`, `destination_zip`, `weight_lb` (sum of `product.weight_lb × line.quantity` across all order lines), and `speed` (from the order's `shipping_speed` field). Round total cost to 2 decimal places.

 ## Formatting Rules

- **Currency** (USD): round to 2 decimal places.
- **Percentages**: round to 1 decimal place.
- **Durations** (days): round to 2 decimal places.
- **Counts**: integers.
- **Lists of IDs**: sort ascending unless a different sort order is specified.
- **Records/rows**: sort by the primary key ascending unless otherwise specified.

 ## API Interaction Pattern

 1. Fetch all relevant collections at the start (products, inventory, customers, orders, etc.).
 2. Build lookup indexes keyed by ID/SKU/warehouse for efficient cross-referencing.
 3. Process each task item by cross-referencing the memo/request data against the live API indexes.
 4. For shipping quotes, make individual API calls per order with the computed weight and speed parameters.
 5. Assemble the response strictly following the answer template shape and field names.
