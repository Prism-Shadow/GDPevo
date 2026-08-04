 # Northwind ERP Operations Skill
 
 ## Overview
 
 This skill provides reusable instructions for solving operations tasks against the Northwind Components ERP API. The API exposes product, inventory, order, customer, supplier, purchase-order, BOM, incident, warehouse, and shipping-quote endpoints.
 
 ## API Conventions
 
 - All endpoints return JSON arrays or objects.
 - Date strings use `YYYY-MM-DD` format.
 - Currency values are numbers; round to two decimal places for output.
 - The base URL is supplied by the runner as `<TASK_ENV_BASE_URL>`.
 
 ### Common Endpoints
 
 | Endpoint | Description |
 |---|---|
 | `GET /products` | All products (active + inactive) |
 | `GET /products/{sku}` | Single product by SKU |
 | `GET /inventory` | All inventory records across warehouses |
 | `GET /orders` | All orders |
 | `GET /orders/{order_id}` | Single order with line items |
 | `GET /customers/{customer_id}` | Customer account details |
 | `GET /suppliers/{supplier_id}` | Supplier details including quality_status |
 | `GET /purchase_orders` | All purchase orders |
 | `GET /boms/{bom_id}` | Bill of materials with components |
 | `GET /incidents` | All quality/operations incidents |
 | `GET /warehouses` | Warehouse list with IDs and regions |
 | `GET /shipping/quote` | Shipping quote (requires query params) |
 
 ## Key Data Model Notes
 
 ### Product Fields
 - `active` (boolean): false means the SKU is inactive / product-master hold.
 - `weight_lb`: per-unit weight used for shipping calculations.
 - `supplier_id`: links to the supplier.
 - `unit_cost`: cost per unit.
 - `safety_stock`: safety-stock threshold.
 
 ### Inventory Fields
 - `on_hand`: total physical units in the warehouse.
 - `reserved`: units allocated to other orders.
 - `quarantined`: units in quality hold.
 - **Effective available** = `on_hand - reserved - quarantined`. Use this only when the task memo explicitly states that reserved, quarantined, or buffer stock should not be treated as freely available. Otherwise default to `on_hand`.
 
 ### Customer Fields
 - `account_status`: `active`, `blocked`, or `review_required`.
 - `risk_flag`: `none`, `fraud_watch`, or `credit_watch`.
 
 ### Incident Fields
 - `open_date`: date the incident was opened (use for filtering).
 - `close_date`: date closed (null if still open).
 - `incident_type`: `RMA` or `WORK_ORDER`.
 - `severity`: `low`, `medium`, `high`, or `critical`.
 - `status`: `open` or `closed`.
 - `resolution_cost`: numeric cost in USD.
 
 ### Purchase Order Fields
 - `status`: `open`, `confirmed`, `received`, or `cancelled`.
 - `warehouse_id`: destination warehouse.
 - `eta`: estimated arrival date.
 - `supplier_id`: supplier fulfilling the PO.
 
 ## Decision Rules
 
 ### Customer Exception / Blocking Precedence
 
 When classifying customer risk for fulfillment:
 1. `account_status == "blocked"` → `account_blocked`
 2. `risk_flag == "fraud_watch"` → `fraud_watch`
 3. `risk_flag == "credit_watch"` → `credit_watch`
 4. `account_status == "review_required"` → `review_required`
 5. Otherwise → `none`
 
 `review_required` is a flag only: it should appear in the `customer_exception` field but does **not** by itself block shipment or change the fulfillment decision. Only `account_blocked`, `fraud_watch`, and `credit_watch` force a `reject_hold` / `manual_review` outcome.
 
 ### Inventory Status Classification
 
 Determine per-order inventory status by checking every line's SKU at the requested warehouse:
 - If any line has an **inactive** product AND any line has **zero on-hand** → `inactive_and_shortage`
 - Else if any line has an **inactive** product → `inactive_sku`
 - Else if any line has **zero on-hand** → `shortage`
 - Else if any line has **on-hand < quantity** (but > 0) → `low_stock`
 - Else → `ready`
 
 Sort the per-status SKU lists ascending by SKU.
 
 ### Shipping Quotes
 
 Call `GET /shipping/quote` with query parameters:
 - `warehouse_id` — the order's warehouse.
 - `destination_zip` — the order's destination zip.
 - `weight_lb` — sum of `weight_lb × quantity` for **every** line (active and inactive).
 - `speed` — the order's `shipping_speed` field (e.g., `ground`, `two_day`, `overnight`).
 
 Use the returned `zone_distance`, `service_days`, and `total_cost` (round to 2 decimals).
 
 ### Transfer / Replenishment Logic
 
 When a warehouse cannot fully cover a line:
 1. Ship whatever is usable from the requested warehouse (`on_hand`, or `effective` if the memo requires it).
 2. Check **every other warehouse** for stock of the same SKU.
 3. Pick **one** source warehouse whose available quantity can cover the remaining shortfall. Prefer the warehouse with the highest available quantity.
 4. If no single warehouse can cover the full shortfall, the line is a **backorder** for the uncovered amount.
 
 ### PO Coverage for Production Planning
 
 - Only POs with `status` `open` or `confirmed` and `warehouse_id` matching the planning site count as coverage.
 - A PO is "timely" if its `eta` is strictly before the earliest target build date.
 - Report the full PO quantity as `timely_po_qty`, not limited to the shortfall amount.
 
 ### Incident Scorecard Recommendations
 
 For supplier quality scorecards, apply these precedence-ordered rules:
 1. `ESCALATE_SUPPLIER` when: supplier is on `quality_hold` with ≥ 3 filtered incidents, OR has any critical RMA, OR has ≥ 3 RMAs with ≥ $15,000 total resolution cost.
 2. `PROCESS_REVIEW` when: WORK_ORDER count ≥ 3 AND WORK_ORDER count > RMA count.
 3. `WATCHLIST` when: quality_status is `watch` or `quality_hold`, OR incident_count ≥ 4, OR total resolution cost ≥ $12,000, OR severe (high/critical) count ≥ 2.
 4. `MONITOR` otherwise.
 
 ## Common Pitfalls
 
 - **Inventory field**: Use `on_hand` for general fulfillment decisions unless the task memo explicitly says to exclude reserved/quarantined stock. The field named `requested_effective_available` in some templates may still expect `on_hand` — check the context.
 - **Incident type field**: The field is `incident_type` (not `type`).
 - **PO warehouse matching**: Only same-warehouse POs cover a planning-site gap.
 - **Shipping weight**: Always include all line items (including inactive SKUs) when computing total shipment weight.
 - **Rounding**: Currency to 2 decimals; percentages to 1 decimal; durations to 2 decimals.
 - **Sort order**: Always sort lists as specified in the answer template (usually by ID ascending, or by specific composite keys).
