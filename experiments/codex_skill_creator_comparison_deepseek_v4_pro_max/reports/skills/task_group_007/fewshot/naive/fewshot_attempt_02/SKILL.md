---
name: northwind-erp-operations
description: Solve Northwind Components ERP operations tasks using the shared REST API. Covers expedite queues, replenishment planning, supplier scorecards, allocation decisions, and procurement quality controls with structured JSON outputs.
---

# Northwind ERP Operations Skill

Use this skill when a task involves the Northwind Components ERP shared REST API for warehouse, inventory, order, supplier, incident, or BOM-based operations. The tasks always produce structured JSON answers from live API data combined with a local input payload (memo, template, or request specification).

## API Reference

All business data lives behind the shared ERP API. The runner supplies the base URL as `<TASK_ENV_BASE_URL>`. Use GET requests only; no authentication is needed.

### Endpoints

| Endpoint | Query Parameters | Returns |
|----------|-----------------|---------|
| `GET /health` | none | API health status |
| `GET /products` | none | All products |
| `GET /products/<sku>` | none | Single product |
| `GET /customers` | none | All customers |
| `GET /customers/<customer_id>` | none | Single customer |
| `GET /warehouses` | none | All warehouses |
| `GET /inventory` | `?warehouse_id=&sku=` | Filtered inventory records |
| `GET /purchase_orders` | `?supplier_id=&sku=&status=` | Filtered purchase orders |
| `GET /orders` | `?wave=&required_date=&customer_id=` | Filtered sales orders |
| `GET /orders/<order_id>` | none | Single order with lines |
| `GET /shipping/quote` | `?warehouse_id=&destination_zip=&weight_lb=&speed=` | Shipping quote |
| `GET /incidents` | `?start=&end=&supplier_id=&sku=&incident_type=&status=` | Filtered quality incidents |
| `GET /suppliers` | none | All suppliers |
| `GET /boms` | none | All bill-of-materials records |
| `GET /boms/<bom_id>` | none | Single BOM with components |

Query string values follow standard URL encoding. Date filters use `YYYY-MM-DD` format and are inclusive on both ends.

## Domain Model

### Entity Relationships

- **Order** (`SO-*`) belongs to a **Customer** (`CUST-*`), contains one or more **Lines** each with a **SKU**, **quantity**, and **requested warehouse**.
- **Product** (`NW-*`) has a **status** (active or inactive), **unit_weight_lb**, and is sourced from a **Supplier** (`SUP-*`).
- **Warehouse** (`WH_NORTH`, `WH_CENTRAL`, `WH_WEST`) holds **Inventory** with `on_hand`, `reserved`, `quarantined`, and `buffer_stock` fields.
- **Effective available** inventory = `on_hand - reserved - quarantined - buffer_stock`.
- **Purchase Order** (`PO-*`) has a **status** (open, confirmed, received, closed), **supplier**, **warehouse**, **sku**, and **delivery_date**.
- **Supplier** (`SUP-*`) has a **quality_status** (approved, watch, quality_hold).
- **Incident** (`INC-*`) has a **type** (RMA or WORK_ORDER), **severity** (low, medium, high, critical), **status** (open, closed), **open_date**, **close_date**, **resolution_cost**, and links to a **supplier** and **sku**.
- **BOM** (`BOM-*`) has a **name** and **components**, each with a **sku** and **quantity_per**.

### Key Field Meanings

| Field | Meaning |
|-------|---------|
| `on_hand` | Physical units present in the warehouse |
| `reserved` | Units already committed to other orders |
| `quarantined` | Units held for quality inspection |
| `buffer_stock` | Minimum operating reserve that must not be consumed |
| `effective_available` | `on_hand - reserved - quarantined - buffer_stock` |

## Decision Frameworks

### 1. Expedite Queue Decision Logic

For each order in an expedite queue memo, query its order lines, customer record, and each line's product and inventory at the requested warehouse, then apply this cascade:

**Step A: Inventory Status**
- Query inventory for each order-line SKU at the requested warehouse.
- If any SKU has `effective_available <= 0`: classify that SKU by root cause.
  - If the product `status` is `inactive` and inventory is also at or below zero: `inactive_and_shortage`.
  - If the product `status` is `inactive` but inventory is positive: `inactive_sku`.
  - If inventory is at or below zero with an active product: `shortage`.
  - If inventory is below the ordered quantity but above zero: `low_stock`.
- If every line's `effective_available >= ordered_quantity`: `ready`.

**Step B: Customer Exception**
- Check the order's customer record.
- If `account_status` is `blocked`: `account_blocked`.
- If `account_status` is `review` or `flagged`: `review_required`.
- If `fraud_alert` is active: `fraud_watch`.
- If `credit_risk` is flagged: `credit_watch`.
- Otherwise: `none`.

**Step C: Final Decision and Next Action (combined)**
Apply the most restrictive outcome from these precedence rules:

1. If `customer_exception` is `account_blocked` -> `reject_hold` / `hold_credit_or_fraud`.
2. If `customer_exception` is `fraud_watch` -> `reject_hold` / `hold_credit_or_fraud`.
3. If `customer_exception` is `review_required` -> `manual_review` / `send_account_review` (even if inventory is fine).
4. If `customer_exception` is `credit_watch` -> `manual_review` / `send_account_review` (even if inventory is fine).
5. If `inventory_status` is `inactive_and_shortage` and no blocking customer exception -> `manual_review` / `escalate_product_master`.
6. If `inventory_status` is `inactive_sku` and no blocking customer exception -> `manual_review` / `escalate_product_master`.
7. If `inventory_status` is `shortage` and no blocking customer exception -> `backorder` / `create_backorder`.
8. If `inventory_status` is `low_stock` and no blocking customer exception -> `delayed_release` / `delay_and_monitor`.
9. Otherwise -> `ship_now` / `release_to_pick`.

**Step D: SKU Lists**
- `shortage_skus`: SKUs with `effective_available <= 0` and product status is active. Sorted ascending.
- `inactive_skus`: SKUs whose product `status` is `inactive`. Sorted ascending.
- `low_stock_skus`: SKUs where `0 < effective_available < ordered_quantity` and product is active. Sorted ascending.

**Step E: Shipping Quote**
Call `GET /shipping/quote` for each order using the order's `warehouse_id`, the customer's `destination_zip`, the sum of `unit_weight_lb * quantity` across all lines, and the appropriate shipping `speed`. Use the operator note or order data to determine the speed; default to the speed requested on the order when unspecified.

### 2. Replenishment / Kit Build Planning

For a BOM-based kit build run:

**Step A: Gather Requirements**
- Query each BOM to get its components (SKU, quantity_per).
- Multiply by `target_build_quantity` to get `total_required` per SKU (sum across BOMs when a SKU appears in multiple BOMs).

**Step B: Check Warehouse Stock**
- Query inventory for each component SKU at the target warehouse.
- Compute `effective_available` using the formula above.

**Step C: Check Purchase Orders**
- Query POs at the target warehouse for each component SKU with `status=open` or `status=confirmed`.
- A PO is **timely** if its `delivery_date` is on or before the earliest `target_build_date` for that component.
- Sum timely PO quantities into `timely_po_qty`.

**Step D: Determine Action**
- Compute `gap = total_required - effective_available`.
- If `gap <= 0` and `effective_available >= total_required`: `no_action_stocked`.
- If `effective_available` exceeds `total_required` by a wide margin and the SKU is not needed: `overstock_excluded`.
- If timely POs cover the full gap: `timely_po_covered` (exclude from transfers and purchases).
- If `gap > 0` after POs, try inter-warehouse transfers from other warehouses with positive effective available.
- Any remaining gap after transfers becomes a `purchase_requisition_qty`.

**Step E: Transfers**
- For each transfer-needed SKU, check all other warehouses for available inventory.
- Prefer warehouses with the most available stock. Record `from_warehouse_id`, `to_warehouse_id`, `quantity`, and `needed_by` (earliest build date for that SKU).
- Sort transfer_requests by SKU ascending, then quantity descending, then from_warehouse_id ascending.

**Step F: Purchase Requisitions**
- For each SKU still short after transfers, create a purchase requisition.
- Use the SKU's primary supplier from the product record, the target warehouse, and the remaining gap as `quantity`.
- `needed_by` is the earliest build date for that SKU.
- `unit_cost` comes from the product's `standard_cost` field. `extended_cost = quantity * unit_cost`, rounded to 2 decimals.
- Sort by SKU ascending.

**Step G: Excluded Components**
- SKUs with `final_action` of `timely_po_covered` -> reason `timely_po_covers_gap`, list coverage POs.
- SKUs with `final_action` of `overstock_excluded` -> reason `target_overstock`.
- SKUs with `final_action` of `no_action_stocked` -> reason `stocked_no_gap`.
- Sort by SKU ascending.

**Step H: Summary**
- `component_count`: number of distinct component SKUs.
- `total_purchase_units`: sum of all `purchase_requisition_qty` values.
- `total_purchase_cost`: sum of all `extended_cost` values, rounded to 2 decimals.
- `total_transfer_units`: sum of all transfer `quantity` values.
- `timely_po_covered_units`: sum of `total_required - target_effective_available` for components whose gap is fully covered by timely POs. Track the actual gap covered, not the full PO quantity.

### 3. Supplier Incident Scorecard

**Step A: Filter Incidents**
- Query `GET /incidents` with `start` and `end` dates, inclusive.
- Use the full incident population for the denominator in percentage calculations.

**Step B: Per-Supplier Aggregation**
- Query `GET /suppliers` for names and quality statuses.
- For each supplier with at least one filtered incident:
  - `incident_count`: total incidents in the window.
  - `incident_percentage`: `(incident_count / total_filtered_incidents) * 100`, rounded to 1 decimal.
  - `total_resolution_cost`: sum of `resolution_cost` across incidents, rounded to 2 decimals.
  - `avg_duration_days`: average of `close_date - open_date` for closed incidents or `analysis_date - open_date` for open ones, in calendar days, rounded to 2 decimals.
  - `rma_count`: count where `incident_type` is `RMA`.
  - `work_order_count`: count where `incident_type` is `WORK_ORDER`.
  - `open_incident_count`: count where `status` is `open`.
  - `severe_incident_count`: count where `severity` is `high` or `critical`.
  - `recommendation_code`: apply the policy cascade below.

**Step C: Recommendation Cascade**
Evaluate conditions in this exact precedence order:

1. `ESCALATE_SUPPLIER`: supplier `quality_status` is `quality_hold` AND `incident_count >= 3`, OR any incident has `severity=critical` AND `incident_type=RMA`, OR `rma_count >= 3` AND `total_resolution_cost >= 15000.00`.
2. `PROCESS_REVIEW`: `work_order_count >= 3` AND `work_order_count > rma_count` (and ESCALATE_SUPPLIER does not apply).
3. `WATCHLIST`: `quality_status` is `watch` or `quality_hold`, OR `incident_count >= 4`, OR `total_resolution_cost >= 12000.00`, OR `severe_incident_count >= 2`.
4. `MONITOR`: none of the above conditions apply.

**Step D: Top-Level Summary**
- `filtered_incident_count`: total incidents matching the date filter.
- `supplier_count`: count of suppliers with at least one filtered incident.
- `total_resolution_cost`: sum of all resolution costs, rounded to 2 decimals.
- `overall_rma_count`: total RMA incidents in the window.
- `overall_work_order_count`: total WORK_ORDER incidents in the window.
- `highest_cost_supplier_id`: supplier with maximum `total_resolution_cost`. Break ties with lowest `supplier_id`.
- `highest_share_supplier_id`: supplier with maximum `incident_count`. Break ties with lowest `supplier_id`.

### 4. Allocation Desk (Mixed-Warehouse Transfer Review)

**Step A: Load the Wave**
- Query `GET /orders?wave=<wave_id>` to get all orders in the wave.
- Each order contains lines with `sku`, `quantity`, and `warehouse_id`.

**Step B: Check Customer Status First**
- For each order, query the customer record.
- If the customer's `account_status` is `blocked`: every line in that order gets `action=manual_review` with `primary_reason=account_blocked`. The order joins `blocked_orders`.
- If `account_status` is `review` or `flagged`: every line gets `action=manual_review` with `primary_reason=account_review_required`. The order joins `blocked_orders`.
- If `fraud_alert` is active: every line gets `action=manual_review` with `primary_reason=fraud_watch`. The order joins `blocked_orders`.

**Step C: Check Product Status**
- For each non-blocked line, query the product record.
- If `status` is `inactive`: `action=manual_review`, `primary_reason=inactive_product`. The order is not necessarily added to `blocked_orders` (only account/customer-risk orders go there).

**Step D: Check Inventory**
- Query inventory for the SKU at the requested warehouse.
- Compute `effective_available`.
- `requested_effective_available` is the value for the line's SKU at the requested warehouse.

**Step E: Determine Action**
- If `effective_available >= ordered_quantity` and no blocking condition: `action=ship`, `ship_quantity=ordered_quantity`.
- If `effective_available < ordered_quantity` and no blocking condition:
  - Check other warehouses for the same SKU. Use any available inventory (positive `effective_available`) from other warehouses.
  - If combined available (requested warehouse + other warehouses) >= ordered_quantity: `action=transfer`.
    - `ship_quantity` = amount the requested warehouse can supply (min of `effective_available` and `ordered_quantity`).
    - `transfer_quantity` = the remainder.
    - Pick one source warehouse for the transfer (prefer the one with most available stock).
  - If combined available is still insufficient: `action=backorder`, `backorder_quantity = ordered_quantity - ship_quantity`.

**Step F: Order Rollup**
- For each order, determine the single `outcome`:
  - All lines `ship` -> `ready_to_ship`.
  - One or more lines `manual_review` and the rest are shippable -> `manual_review`.
  - One or more lines `transfer` and no `manual_review` or `backorder` -> `needs_transfer`.
  - One or more lines `backorder` and no `manual_review` -> `has_backorder`.
  - Mix of `ship`, `transfer`, and `backorder` -> `mixed_actions`.
  - Any `manual_review` line overrides: the order outcome is `manual_review`.

### 5. Procurement Quality Control

**Step A: Load Target Suppliers**
- Query each target supplier by ID to get `supplier_name` and `quality_status`.

**Step B: Load Recent Incidents**
- Query `GET /incidents?start=<start>&end=<end>&supplier_id=<id>` for each target supplier.
- Count `recent_incident_count`, `recent_rma_count` (type=RMA), `severe_or_critical_count` (severity=high or critical), `open_incident_count` (status=open).
- Collect `affected_skus` (unique SKUs from incidents, sorted ascending).
- Collect up to 5 `sample_incident_ids` (sorted ascending).

**Step C: Load Open/Confirmed POs**
- Query `GET /purchase_orders?supplier_id=<id>&status=open` and `status=confirmed`.
- These are the candidate `held_po_ids` when a decision freezes or holds replenishment.

**Step D: Decision Rules**
Apply in precedence order:

1. `freeze_new_replenishment`: supplier `quality_status` is `quality_hold` AND `recent_incident_count >= 1`. Hold all open/confirmed POs for that supplier.
2. `buyer_review_required`: supplier `quality_status` is `watch` OR `severe_or_critical_count >= 2` OR `recent_rma_count >= 2`. Hold all open/confirmed POs for that supplier.
3. `monitor_only`: none of the above apply. No POs held.

**Step E: Aggregate Outputs**
- `held_po_ids`: union of all held PO IDs across suppliers, deduplicated and sorted ascending.
- `release_supplier_ids`: supplier IDs where decision is `monitor_only`, sorted ascending.
- Summary: `suppliers_reviewed`, counts by decision type, `held_po_count`, `total_recent_incidents`.

## Output Conventions

### General Rules

- Every answer is a single JSON object matching the provided answer template exactly.
- Do not include narrative text, explanations, or markdown outside the JSON.
- Sort lists as specified by each template (usually by `order_id`, `line_id`, `sku`, or `supplier_id` ascending).
- All currency values: round to exactly 2 decimal places. Use standard rounding (half-up).
- All percentage values: round to exactly 1 decimal place when specified.
- All duration values: round to exactly 2 decimal places when specified.
- Integer fields must be whole numbers (no decimal places).
- When a template dictates an enum for a field, use only the allowed values.
- Empty lists use `[]`, not `null`.
- Include all required top-level keys even when their values are empty lists or zeros.
- Compute `effective_available` as `on_hand - reserved - quarantined - buffer_stock` in every inventory check. Do not use raw `on_hand`.
- When a customer check triggers `manual_review` on an order, all lines in that order receive `manual_review` regardless of individual line inventory status.

### Common Pitfalls

- Do not treat `reserved`, `quarantined`, or `buffer_stock` as available inventory.
- Do not overlook product `status` when classifying SKUs; an inactive product whose inventory is also at/below zero produces `inactive_and_shortage`, not plain `shortage`.
- In allocation tasks, `blocked_orders` includes only account-level and customer-risk blocks (account_blocked, account_review_required, fraud_watch), not product-level `inactive_product` reviews.
- In replenishment, a timely PO's quantity counts toward coverage but the gap covered by that PO is `min(po_qty, gap)`, not the full PO quantity, for summary totals.
- For shipping quotes, sum the weights of all lines in the order. Use the order's warehouse and the customer's destination zip.
- When an answer template specifies a `required_value` for a field (e.g., `wave_id`), use that exact value.
- In scorecards, duration for open incidents uses the analysis date as the close date.
- The `total_shipping_cost_usd` summary is the sum of all individual `total_cost_usd` values, rounded to 2 decimals.
- In BOM planning, when a SKU appears in multiple BOMs, sum the required quantities. The earliest build date across BOMs drives the `needed_by` date for that SKU.
- In allocation, `transfer_requests` ordering: sort by `order_id` ascending, then `line_id` ascending (not by SKU).
- In expedite, the `final_decision` for `inactive_and_shortage` and `inactive_sku` is `manual_review` with `next_action` of `escalate_product_master`, unless a higher-precedence customer exception applies.

## Workflow Pattern

Every Northwind ERP task follows this general sequence:

1. **Read the local payload** (memo, request spec, or production memo) and the answer template from `input/payloads/`.
2. **Query the ERP API** for all relevant entities: orders, customers, products, inventory, warehouses, suppliers, POs, BOMs, incidents, or shipping quotes as needed.
3. **Cross-reference** the API data against the request: match orders to customers, lines to inventory and products, suppliers to incidents and POs, BOM components to stock levels.
4. **Apply the decision framework** appropriate to the task type (expedite, replenishment, scorecard, allocation, or procurement-quality).
5. **Populate the answer template** with computed values, following all ordering and formatting rules.
6. **Return only the JSON** object - no prose, no markdown wrapping, no extra commentary.
