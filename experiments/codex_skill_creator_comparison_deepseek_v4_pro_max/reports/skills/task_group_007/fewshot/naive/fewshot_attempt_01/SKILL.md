---
name: northwind-erp-ops
description: Solve Northwind Components ERP operational tasks using the shared REST API and structured decision logic. Covers expedite dispatch, kit-build replenishment, supplier incident scorecards, allocation/transfer review, and procurement quality controls.
---

# Northwind ERP Operations

Solve operational tasks for Northwind Components using its shared ERP REST API. The API base URL is supplied by the runtime as `<TASK_ENV_BASE_URL>` or an equivalent placeholder. All endpoints are read-only (GET). There is no authentication.

## Domain Model

### Products

Each product has a `sku` (string, e.g. `NW-1000`), `name`, `unit_cost` (float USD), `is_active` (boolean), `supplier_id`, and a `product_master` flag. Inactive SKUs (`is_active: false`) cannot be shipped; lines referencing them require `manual_review` with reason `inactive_product`.

### Customers

Each customer has a `customer_id` (string, e.g. `CUST-200`), `customer_name`, and status fields that drive exception classification:

- `account_status`: `active`, `blocked`, or `review_required`. `blocked` means reject/held decisions. `review_required` means manual review.
- `risk_flag`: `none`, `fraud_watch`, or `credit_watch`. `fraud_watch` takes precedence; it triggers `manual_review` with reason `fraud_watch`. `credit_watch` triggers `manual_review` with reason `credit_watch`.

When any customer-level block (account blocked, fraud watch, credit watch) is active, every line in that order is held for manual review regardless of inventory status.

### Warehouses

Three warehouses: `WH_NORTH`, `WH_CENTRAL`, `WH_WEST`. Each has a `warehouse_id`, `warehouse_name`, and a `zip_code`.

### Inventory

Query `/inventory?warehouse_id=<id>&sku=<sku>` to get per-warehouse per-SKU stock. The response shape varies by API version. Read the actual response fields and adapt:

- `on_hand`: physical units in the warehouse
- `reserved`: units allocated against open orders
- `quarantined`: units held for quality inspection
- `available`: may already be computed by the API as `on_hand - reserved`

**Effective available** for all dispatch, allocation, and replenishment decisions:
- If the API response includes a field named `effective_available`, use it directly.
- If `available` is present and represents `on_hand - reserved`, compute `effective_available = available - quarantined`.
- If only raw counts are present, compute `effective_available = on_hand - reserved - quarantined`.
- Treat any missing field (e.g. `quarantined`) as 0.

Inventory status for a line against a requested warehouse:
- `ready`: effective available >= line quantity
- `low_stock`: 0 < effective available < line quantity
- `shortage`: effective available <= 0
- `inactive_sku`: the product `is_active` is false
- `inactive_and_shortage`: the SKU is inactive AND effective available <= 0

### Orders

Query `/orders?wave=<wave>&required_date=<date>&customer_id=<id>` or `/orders/<order_id>`. Each order has `order_id`, `customer_id`, `warehouse_id` (the requested ship-from warehouse), `lines` (array with `line_id`, `sku`, `quantity`, `unit_price`), `status`, and `requested_shipping_speed` (`standard`, `express`, or `overnight`).

### Purchase Orders

Query `/purchase_orders?supplier_id=<id>&sku=<sku>&status=<status>`. Each PO has `po_id`, `supplier_id`, `warehouse_id`, `sku`, `quantity`, `delivery_date`, `unit_cost`, and `status` (`draft`, `open`, `confirmed`, `received`, `closed`, `cancelled`). Only `open` and `confirmed` POs count as eligible coverage.

A PO is timely if its `delivery_date` is on or before the target build or dispatch date.

### Suppliers

Query `/suppliers` or `/suppliers/<id>`. Each supplier has `supplier_id`, `supplier_name`, and `quality_status` (`approved`, `watch`, `quality_hold`).

### BOMs (Bills of Materials)

Query `/boms/<bom_id>`. Each BOM has `bom_id`, `bom_name`, `warehouse_id` (the build site), and `components` (array with `sku`, `quantity_per_kit`). Some BOM responses include a `kit_name` field.

### Incidents

Query `/incidents?start=<YYYY-MM-DD>&end=<YYYY-MM-DD>&supplier_id=<id>&sku=<sku>&incident_type=<type>&status=<status>`. Each incident has `incident_id`, `supplier_id`, `sku`, `incident_type` (`RMA` or `WORK_ORDER`), `severity` (`low`, `medium`, `high`, `critical`), `status` (`open`, `closed`, `in_review`), `open_date`, `close_date` (null if open), `resolution_cost` (float USD), and `description`.

### Shipping Quotes

`GET /shipping/quote?warehouse_id=<id>&destination_zip=<zip>&weight_lb=<float>&speed=<standard|express|overnight>` returns `zone_distance` (integer), `service_days` (integer), `total_cost_usd` (float USD, round to 2 decimals).

Compute total weight for a quote by summing across all lines in the order. If per-product weights are not directly available from the product endpoint, estimate a reasonable per-unit weight (often 1-5 lb) and multiply by line quantities. Use the product master's weight field if present.

## Common Computation Rules

### Currency

All USD values rounded to 2 decimal places. Use standard rounding (half-up). Extended cost = quantity * unit_cost.

### Percentages

Rounded to 1 decimal place. Denominator is always the full filtered population for that analysis.

### Durations

Rounded to 2 decimal places. For closed incidents: calendar days from `open_date` to `close_date`. For open incidents: calendar days from `open_date` to analysis date.

### List Ordering

Sort by the primary key ascending (string/numeric natural order) unless the answer template specifies a different ordering. For transfer requests the typical sort is `sku` ascending, then `quantity` descending, then `from_warehouse_id` ascending, but always defer to the template when it is explicit.

### Top-Level Consistency

Every count/aggregate in the summary must match the detail records. Recompute summaries from the detail records rather than maintaining them independently.

## Task-Type Workflows

### 1. Expedite Dispatch

Given a wave ID and an order list (from a memo), for each order:

1. Fetch the order, its customer, and its lines from the API.
2. For each line, fetch the product (check `is_active`) and inventory at the order's warehouse.
3. Compute inventory status per line across the order. Aggregate to an order-level inventory status: the worst-case among lines (order of precedence: `inactive_and_shortage` > `inactive_sku` > `shortage` > `low_stock` > `ready`).
4. Determine customer exception: check `account_status`, `risk_flag`. `account_blocked` takes precedence over `fraud_watch` over `credit_watch` over `review_required` over `none`.
5. Decision matrix:
   - `account_blocked` or `fraud_watch` → `reject_hold` / `hold_credit_or_fraud`
   - `credit_watch` or `review_required` AND inventory not ready → `manual_review` / `send_account_review`
   - `review_required` AND inventory ready → `manual_review` / `send_account_review`
   - Any `inactive_sku` → `manual_review` / `escalate_product_master`
   - `shortage` or `inactive_and_shortage` with no account block → `backorder` / `create_backorder`
   - `low_stock` with no account block → `delayed_release` / `delay_and_monitor`
   - `ready` with no account block → `ship_now` / `release_to_pick`
6. When an account exception is present alongside inventory issues, the account exception drives the decision (account flags override inventory status).
7. Get a shipping quote for each order. Use the order's `requested_shipping_speed`, the warehouse's `zip_code`, and the customer's zip (from `/customers/<customer_id>`) to call the quote endpoint. Estimate total weight from line quantities.
8. Populate exception SKU lists: `shortage_skus` (lines where effective available <= 0), `inactive_skus` (lines where `is_active` is false), `low_stock_skus` (0 < available < qty). Remove duplicates, sort ascending.
9. Build the summary from the completed records.

### 2. Kit-Build Replenishment

Given a list of BOMs with target build quantities and dates at a planning warehouse:

1. Fetch each BOM. Sum component requirements: for each component SKU, `total_required = sum over all BOMs using that SKU of (build_quantity * quantity_per_kit)`.
2. Fetch inventory at the target warehouse for each component SKU. Compute `target_effective_available = effective_available - total_required`. A negative value means a gap.
3. Fetch all purchase orders for each component SKU at the target warehouse with status `open` or `confirmed`. Sum their quantities as `timely_po_qty` if `delivery_date` is on or before the earliest build date that requires that SKU. Some components may only be needed for later builds; the PO deadline is the earliest build date for that component.
4. For components with a gap after POs: check other warehouses for transferrable stock.
   - For each other warehouse, compute effective available. If positive, that quantity is eligible for transfer.
   - Allocate transfer quantity from warehouses with the most effective available first (descending order), up to the remaining gap.
   - Record each transfer as a separate transfer request line.
5. After transfers, any remaining gap requires a purchase requisition.
   - Use the SKU's supplier from the product master (`supplier_id`).
   - Use the product's `unit_cost` from the product API.
   - `needed_by` is the earliest build date requiring that component.
6. Final action per component:
   - Effective available already >= total_required → `no_action_stocked` or `overstock_excluded` (exclude if > total_required by a margin consistent with overstock policy).
   - Gap covered entirely by timely POs → `timely_po_covered`
   - Gap covered entirely by transfers → `transfer_only`
   - Gap requires new POs → `purchase_required`
7. Excluded components are those with `final_action` of `no_action_stocked`, `overstock_excluded`, or `timely_po_covered`. Only `timely_po_covered` and `overstock_excluded` and `stocked_no_gap` appear in the `excluded_components` list with supporting PO IDs.
8. Summarize component count, purchase units/cost, transfer units, and timely-PO-covered units.

### 3. Supplier Incident Scorecard

Given a date range, analysis date, and recommendation policy:

1. Fetch all incidents within the date range (`open_date` between start and end inclusive).
2. Fetch all suppliers to get names and quality statuses.
3. Filter incidents to the date window. Group by `supplier_id`.
4. For each supplier with at least one incident:
   - Count total incidents, RMA incidents, WORK_ORDER incidents, open incidents, severe incidents (severity `high` or `critical`).
   - Sum `resolution_cost`.
   - Compute average duration: for each incident, days = `close_date - open_date` if closed, or `analysis_date - open_date` if open. Average across all supplier incidents.
   - Compute `incident_percentage` = (supplier incident count / total filtered incidents) * 100, rounded to 1 decimal.
5. Apply recommendation policy in precedence order. The task payload (typically a scorecard request JSON or memo) supplies the exact policy rules: thresholds, conditions, and the full precedence chain. Read the policy from the task payload rather than assuming fixed thresholds. The general pattern across the four tiers:
   - **ESCALATE_SUPPLIER**: highest severity; triggered by quality_hold status combined with incident volume, any critical RMA, or high RMA count with high resolution cost.
   - **PROCESS_REVIEW**: triggered when WORK_ORDER count exceeds RMA count by a defined margin.
   - **WATCHLIST**: triggered by watch/quality_hold status, moderate incident count, moderate resolution cost, or moderate severe-incident count.
   - **MONITOR**: fallback when no higher-precedence condition applies.

   Evaluate conditions in precedence order and assign the first matching tier. The task payload defines the numeric thresholds for each tier.
6. `highest_cost_supplier_id`: supplier with max `total_resolution_cost`. Break ties by lowest `supplier_id`.
7. `highest_share_supplier_id`: supplier with max `incident_count`. Break ties by lowest `supplier_id`.
8. `top_escalation_suppliers`: suppliers with recommendation `ESCALATE_SUPPLIER`, ordered by incident count descending, then total resolution cost descending, then supplier_id ascending.

### 4. Allocation / Transfer Desk

Given a wave ID and a desk memo with order context:

1. Fetch all orders in the wave via `/orders?wave=<wave_id>`.
2. For each order, get the customer and check status fields. Orders with `account_blocked`, `fraud_watch`, `credit_watch`, or `review_required` are fully blocked: every line becomes `manual_review` with the corresponding primary reason. Add these orders to `blocked_orders`.
3. For non-blocked orders, process each line:
   - Fetch product master to check `is_active`. Inactive product → `manual_review` with reason `inactive_product`.
   - Fetch inventory at the requested warehouse. Compute `requested_effective_available`.
   - If `requested_effective_available >= line quantity` → `ship`, `ship_quantity = line quantity`.
   - If `0 < requested_effective_available < line quantity` → `ship_quantity = requested_effective_available`, check other warehouses for the remainder.
   - If `requested_effective_available <= 0` → `ship_quantity = 0`, check other warehouses.
   - For the uncovered quantity, check each other warehouse's effective available. If any warehouse can fully cover the remainder → `transfer`, pick the warehouse with the highest effective available as `transfer_from`, `transfer_quantity = uncovered`. If no warehouse can fully cover → `backorder`, `backorder_quantity = uncovered`.
   - Transfer source selection: pick the single warehouse with the most effective available. Do not split transfers across multiple warehouses unless explicitly required.
4. `primary_reason`: `none` for clean lines, `insufficient_effective_stock` for backorder lines, `inactive_product` for inactive SKU lines, and the appropriate account/risk reason for blocked orders.
5. For order rollup: if all lines are `ship` → `ready_to_ship`. If any line is `transfer` → `needs_transfer`. If any line is `backorder` → `has_backorder`. If any line is `manual_review` → `manual_review`. Mixed cases where there is no `manual_review` but a combination of ship/transfer/backorder → `mixed_actions`.
6. `transfer_requests` list: one entry per transfer line. `from_warehouse` is the `transfer_from`, `to_warehouse` is the requested warehouse, `quantity` is the `transfer_quantity`.

### 5. Procurement Quality Review

Given an analysis window, a list of target supplier IDs, and a decision policy in the task memo:

1. Fetch incidents for each target supplier within the analysis window (`open_date` between start and end inclusive).
2. Fetch each supplier's current `quality_status` from the supplier endpoint.
3. Fetch all open and confirmed purchase orders for each target supplier. Only `open` and `confirmed` POs count as held.
4. For each supplier, compute:
   - `recent_incident_count`: total incidents in the window.
   - `recent_rma_count`: incidents where `incident_type` is `RMA`.
   - `severe_or_critical_count`: incidents where `severity` is `high` or `critical`.
   - `open_incident_count`: incidents where `status` is `open`.
   - `affected_skus`: distinct SKUs from incidents, sorted ascending.
   - `sample_incident_ids`: incident IDs for this supplier, sorted ascending, capped at 5.
5. Decision logic: the task memo or policy payload defines the exact conditions per supplier. Read it from the task materials before applying decisions. The general hierarchy is:
   - `freeze_new_replenishment`: highest risk; typically quality_hold with recent incidents, or high severe/critical counts, or watch status with multiple RMAs. All open/confirmed POs for this supplier are held.
   - `buyer_review_required`: moderate risk; typically watch status with incidents (but not meeting freeze criteria), or approved supplier with isolated severe/RMA incidents. Open/confirmed POs are held.
   - `monitor_only`: low risk; no concerning patterns trigger the higher tiers. POs are released.

   Evaluate conditions in precedence order and assign the first matching tier. The task payload defines the numeric thresholds.
6. `held_po_ids`: all open/confirmed POs for suppliers whose decision is NOT `monitor_only`. Deduplicated, sorted ascending.
7. `release_supplier_ids`: suppliers whose decision is `monitor_only`, sorted ascending.

## General Process

1. Read the task prompt and all payload files in `input/payloads/`. The prompt identifies the task type and supplies `<TASK_ENV_BASE_URL>`.
2. Identify the answer template (usually `answer_template.json` in the payloads directory). The output must conform exactly: every required key present, every enum value from the allowed set, every list sorted as specified, and every numeric value rounded correctly.
3. Query the API in order: fetch reference data first (products, customers, suppliers, warehouses), then task-specific data (orders, inventory, BOMs, incidents, POs). Reuse responses for repeated lookups on the same entity.
4. Compute decisions per entity, applying domain rules from the sections above.
5. Assemble the output JSON with all records sorted as specified and all summary fields computed from the detail records.
6. Return only the JSON object. No narrative explanation, no markdown fences unless the prompt explicitly requests a wrapped format.
