 # Northwind ERP Operations Skill

 ## Overview
 This skill provides reusable patterns for interacting with a shared Northwind Components ERP API to produce structured operational decisions. The API exposes read-only GET endpoints for live entity records. All answers must be returned as JSON objects that conform exactly to the provided answer templates.

 ## Environment
 - The API base URL is supplied as `<TASK_ENV_BASE_URL>` at runtime. Substitute this placeholder with the actual URL for all requests.
 - No authentication is required.
 - Only use the listed GET endpoints. Do not call `/health`, reset, reseed, or any judge endpoints.

 ## Available Endpoints
 - `GET /products` — all products
 - `GET /products/{sku}` — single product
 - `GET /inventory` — all inventory records (warehouse-level stock)
 - `GET /warehouses` — all warehouses
 - `GET /orders` — all orders
 - `GET /orders/{order_id}` — single order
 - `GET /customers` — all customers
 - `GET /customers/{customer_id}` — single customer
 - `GET /suppliers` — all suppliers
 - `GET /purchase_orders` — all purchase orders
 - `GET /boms` — all bills of materials
 - `GET /boms/{bom_id}` — single BOM
 - `GET /incidents` — all quality incidents
 - `GET /shipping/quote?warehouse_id=...&destination_zip=...&weight_lb=...&speed=...` — parcel quote

 ## Core Data Concepts

 ### Effective Available Inventory
 Compute the freely available stock at a warehouse for a given SKU:
 ```
 effective = on_hand - reserved - quarantined
 available = max(0, effective - safety_stock)
 ```
 - `safety_stock` comes from the product master record.
 - Clamp to zero — negative values mean no stock is freely available.
 - This applies to both the target warehouse and any source warehouse considered for transfers.

 ### Overstock
 A SKU is overstocked at a warehouse when `effective > overstock_threshold`. Overstocked components should be excluded from replenishment plans (action: `overstock_excluded`).

 ### Customer Risk Classification
 Evaluate in priority order:
 1. `account_status == "blocked"` → `account_blocked`
 2. `risk_flag == "fraud_watch"` → `fraud_watch`
 3. `risk_flag == "credit_watch"` → `fraud_watch` (credit risk is treated as fraud-level for primary reason)
 4. `account_status == "review_required"` → `account_review_required`
 5. Otherwise → `none`

 For allocation/expedite decisions, any of these customer exceptions triggers `manual_review` for all lines on the order, regardless of inventory position.

 ### Product Active Status
 A product with `active == false` is inactive. Lines with inactive products should be flagged for `manual_review` with reason `inactive_product`. However, customer-level exceptions take precedence over product-level issues when determining the primary reason.

 ### Shipping Quotes
 Call the shipping quote endpoint with the order's actual `shipping_speed` (not a default). The API returns `zone_distance`, `service_days`, and `total_cost`. Map `total_cost` to `total_cost_usd` in the output, rounded to 2 decimal places.

 ## Decision Frameworks

 ### Expedite Queue (Order-Level Release Decisions)
 For each order in the wave:
 1. Compute per-line inventory status at the order's warehouse using effective available.
 2. Classify each SKU: `shortage` (available ≤ 0), `low_stock` (0 < available < quantity), or ready.
 3. Aggregate to order-level `inventory_status`: `inactive_and_shortage` > `inactive_sku` > `shortage` > `low_stock` > `ready`.
 4. Determine `customer_exception` using the risk classification above.
 5. Derive `final_decision` and `next_action`:
    - `account_blocked` → `reject_hold` / `hold_credit_or_fraud`
    - `fraud_watch` or `credit_watch` → `manual_review` / `hold_credit_or_fraud`
    - `review_required` → `manual_review` / `send_account_review`
    - inactive product → `manual_review` / `escalate_product_master`
    - `shortage` → `backorder` / `create_backorder`
    - `low_stock` → `delayed_release` / `delay_and_monitor`
    - `ready` → `ship_now` / `release_to_pick`

 ### Allocation Desk (Line-Level Transfer Decisions)
 For each order line in the wave:
 1. Check customer exceptions first (customer-level blocks override inventory checks).
 2. If line is blocked by customer or product status → `manual_review`.
 3. Otherwise, check if the requested warehouse's available stock covers the line quantity → `ship`.
 4. If not, search other warehouses for available stock (preserving their safety stock). Choose one source warehouse.
 5. If a transfer can cover the remaining quantity → `transfer`. If not fully coverable → `backorder`.
 6. The `ship_quantity` is what the requested warehouse provides; `transfer_quantity` is what the source warehouse provides; `backorder_quantity` is the uncovered remainder.
 7. `blocked_orders` includes all orders with `account_blocked`, `fraud_watch`, `credit_watch`, or `review_required` customer exceptions.

 ### Replenishment Planning (Kit Build / MRP)
 1. Parse the production memo for target BOMs, build quantities, and build dates.
 2. For each BOM component, compute `total_required = quantity_per_kit × build_quantity` across all BOMs.
 3. Determine the earliest build date that requires each SKU.
 4. Compute the available inventory at the target warehouse (subtract safety stock).
 5. Check for timely open/confirmed purchase orders at the target warehouse with ETA ≤ build date.
 6. If a PO covers the shortfall → `timely_po_covered`. List the covering PO IDs.
 7. If overstocked → `overstock_excluded`.
 8. Otherwise, transfer available stock from other warehouses (preserving each source's safety stock), then create a purchase requisition for any remaining shortfall.
 9. `final_action`: `transfer_only` (no purchase needed), `purchase_required` (purchase needed, possibly with transfers), `timely_po_covered`, `overstock_excluded`, or `no_action_stocked`.

 ### Supplier Incident Scorecard
 1. Filter incidents by `open_date` within the analysis window (inclusive).
 2. Group by `supplier_id`. Compute per-supplier: incident count, RMA count, work order count, open count, severe count (severity in `high` or `critical`), total resolution cost, and average duration.
 3. Duration for closed incidents = calendar days from `open_date` to `close_date`; for open incidents = days from `open_date` to the analysis date.
 4. Percentages use the total filtered incident population as denominator, rounded to 1 decimal place.
 5. Apply recommendation policy in precedence order:
    - `ESCALATE_SUPPLIER`: quality_hold with ≥ 3 filtered incidents, or any critical RMA, or ≥ 3 RMAs with ≥ 15000 total resolution cost.
    - `PROCESS_REVIEW`: WORK_ORDER ≥ 3 and WORK_ORDER > RMA count.
    - `WATCHLIST`: quality_status is watch or quality_hold, or incident_count ≥ 4, or total_resolution_cost ≥ 12000, or severe_count ≥ 2.
    - `MONITOR`: none of the above.
 6. Report top escalation suppliers sorted by incident_count desc, total_resolution_cost desc, supplier_id asc.

 ### Quality Hold / Procurement Review
 1. Filter incidents by `open_date` within the specified window for the target suppliers.
 2. Compute per-supplier statistics (incident count, RMA count, severe/critical count, open count, affected SKUs, sample incident IDs).
 3. List open/confirmed POs for each supplier.
 4. Decision rules:
    - `quality_hold` with any recent incidents → `freeze_new_replenishment`
    - `watch` with ≥ 2 severe/critical incidents → `buyer_review_required`
    - `watch` with < 2 severe/critical → `monitor_only`
    - Any critical RMA → `freeze_new_replenishment`
    - Otherwise → `monitor_only`
 5. `held_po_ids`: all open/confirmed POs for suppliers with `freeze_new_replenishment`.
 6. `release_supplier_ids`: suppliers with `monitor_only`.

 ## General Rules

 ### Sorting
 - Always sort lists by the keys specified in the answer template (ascending unless stated otherwise).
 - For multi-key sorts, respect the exact key precedence and direction documented in the template.

 ### Numeric Precision
 - Currency values (USD): round to 2 decimal places using standard rounding.
 - Percentages: round to 1 decimal place.
 - Durations (days): round to 2 decimal places.
 - All counts and quantities: integers.

 ### Dates
 - Parse all dates from the API in `YYYY-MM-DD` format.
 - Date-range filters are inclusive of both start and end dates.
 - Duration calculations use calendar days.

 ### JSON Output
 - Return only the JSON object matching the answer template — no narrative text, no markdown wrapping, no extra keys.
 - Use the exact field names, enum values, and structures from the template.

 ### Error Handling
 - If a single-record endpoint returns 404 (e.g., `/inventory/{sku}`), fall back to fetching and filtering the list endpoint.
 - Handle missing inventory records as zero available stock.
 - Treat `cancelled` POs as unavailable; only `open` and `confirmed` POs are actionable.
 - Treat `received` POs as already reflected in on-hand inventory.

 ### Transfer Selection
 - When multiple source warehouses can cover a shortfall, choose the one that can fully cover the remaining quantity. If none can fully cover, choose the one with the most available stock.
 - Always preserve the source warehouse's safety stock — only transfer stock above the safety buffer.
