---
name: northwind-erp-operations
description: Solve Northwind Components ERP operational dispatch, replenishment, allocation, scorecard, and procurement-control tasks against a live REST API by following JSON answer templates and cross-referencing products, inventory, orders, BOMs, customers, suppliers, purchase orders, warehouses, shipping quotes, and incidents.
---

# Northwind ERP Operations

Use this skill when the task involves Northwind Components operational decisions -- expedite dispatch, kit replenishment, allocation transfer, supplier scorecards, or procurement quality control -- against a live shared ERP REST API.

## Core Pattern

Every Northwind operational task follows the same structure:

1. Read the business-context payload (memo, request, or notes) and the `answer_template.json` that defines the required output shape.
2. Query the live ERP API at the runner-provided `<TASK_ENV_BASE_URL>` to get current records for orders, products, customers, inventory, warehouses, BOMs, purchase orders, suppliers, and incidents.
3. Cross-reference live records against the business rules described below.
4. Return a single JSON object conforming strictly to the answer template. No narrative outside the JSON.

## API Reference

The API is read-only, unauthenticated, and served at `<TASK_ENV_BASE_URL>`. All endpoints accept GET only.

| Endpoint | Query parameters | Returns |
|---|---|---|
| `/health` | none | API health status |
| `/products` | none | Array of all products |
| `/products/<sku>` | path: sku | Single product |
| `/customers` | none | Array of all customers |
| `/customers/<customer_id>` | path: customer_id | Single customer |
| `/warehouses` | none | Array of all warehouses with zip codes |
| `/inventory` | `warehouse_id`, `sku` | Inventory record with on-hand, reserved, held, and quarantined quantities |
| `/orders` | `wave`, `required_date`, `customer_id` | Array of orders matching filters |
| `/orders/<order_id>` | path: order_id | Single order with lines (sku, quantity, requested warehouse) |
| `/shipping/quote` | `warehouse_id`, `destination_zip`, `weight_lb`, `speed` | Shipping quote with zone, days, and cost |
| `/purchase_orders` | `supplier_id`, `sku`, `status` | Array of purchase orders |
| `/incidents` | `start`, `end`, `supplier_id`, `sku`, `incident_type`, `status` | Array of incidents within window |
| `/suppliers` | none | Array of all suppliers with quality status and default warehouse |
| `/boms` | none | Array of all BOMs (ids and names) |
| `/boms/<bom_id>` | path: bom_id | BOM with component list (sku, quantity per) |

### API Usage Conventions

- Parallelize independent API calls to minimize round trips. For example, fetch all orders in a wave first, then batch product, inventory, and customer lookups based on the SKUs and customer IDs found.
- When a task references a specific date (e.g. `as_of_date` or `analysis_date`), use that date to filter incidents and purchase orders. For inventory, always query the live record; the API returns current state.
- Currency values from the API (shipping costs, unit costs, incident resolution costs) are in USD. Round all calculated costs to 2 decimal places.
- Sort list fields in ascending order by their natural key unless the answer template specifies a different ordering.

## Business Domain Concepts

### Effective Inventory

The API returns four inventory quantities per warehouse/SKU pair:
- `on_hand`: total physical units
- `reserved`: units allocated to released orders
- `held`: units in quality hold or quarantine
- `quarantined`: units under investigation

**Effective available** = `on_hand` - `reserved` - `held` - `quarantined`. A negative value means the warehouse is already over-committed. Always use effective available for fulfillment decisions, never raw on-hand.

### Customer Risk Flags

Customers carry status flags that override inventory availability:

| Flag | Meaning | Dispatch behavior |
|---|---|---|
| `review_required` | Account needs manual sign-off | Route to `manual_review`; do not release automatically |
| `account_blocked` | Account frozen | Route to `reject_hold` or `manual_review` with `hold_credit_or_fraud` |
| `fraud_watch` | Suspicious activity | Route to `manual_review` with `hold_credit_or_fraud` |
| `credit_watch` | Payment risk | Route to `manual_review` or `delayed_release` |

Customer exception checking is the first gate. If a customer has any risk flag, apply the most restrictive action before evaluating inventory.

### Product Master

Products carry an `active` boolean. An inactive (discontinued) product cannot be released through normal dispatch. Flag lines with inactive SKUs for `manual_review` with reason `inactive_product` or `escalate_product_master`. Inactive SKUs also appear in the `inactive_skus` lists for expedite tasks.

### Inventory Status Classification (Expedite)

For each order, classify the worst inventory status across all its lines:

| Status | Condition |
|---|---|
| `ready` | All lines have non-negative effective available and all SKUs are active |
| `low_stock` | Some lines have low but non-negative effective available; all SKUs active |
| `shortage` | At least one line has negative effective available; all SKUs active |
| `inactive_sku` | At least one line has an inactive SKU; all active SKUs have non-negative effective |
| `inactive_and_shortage` | At least one inactive SKU and at least one line with negative effective available |

### Dispatch Decision Mapping

| Customer exception | Inventory status | Final decision | Next action |
|---|---|---|---|
| `account_blocked` or `fraud_watch` | any | `reject_hold` | `hold_credit_or_fraud` |
| `review_required` or `credit_watch` | any | `manual_review` | `send_account_review` |
| `none` | `ready` | `ship_now` | `release_to_pick` |
| `none` | `low_stock` | `delayed_release` | `delay_and_monitor` |
| `none` | `inactive_sku` or `inactive_and_shortage` | `manual_review` | `escalate_product_master` |
| `none` | `shortage` | `backorder` | `create_backorder` |

### Allocation Line Actions (Transfer Review)

For mixed-warehouse allocation, evaluate each line independently:

- `ship`: the requested warehouse has enough effective available (>= line quantity)
- `transfer`: the requested warehouse cannot fill the full line, but another warehouse can cover the gap with its own effective stock. Ship what the requested warehouse can provide, transfer the remainder from one chosen source.
- `backorder`: no warehouse has sufficient effective stock to cover the line
- `manual_review`: customer has a risk flag or the SKU is inactive

Transfer source selection: pick the warehouse (other than the requested one) with the largest positive effective available for that SKU. Only use a single source per line.

### Kit Replenishment

When planning component material for BOM builds:

1. **Explode BOM**: component_required = BOM quantity_per * build_quantity. Sum across all kit targets for each SKU.
2. **Target effective available**: current effective available at the target warehouse plus all confirmed/open POs for that SKU at that warehouse with delivery before the build date.
3. **Gap**: total_required - target_effective_available. A positive gap needs covering.
4. **Coverage hierarchy** (most preferred first):
   - Timely PO coverage: open/confirmed POs at the target warehouse whose delivery date precedes the build date. POs in other statuses are not timely.
   - Inter-warehouse transfer: available effective stock at other warehouses (transferring warehouse must retain positive effective after the transfer).
   - Purchase requisition: buy what remains from the SKU's supplier.
5. **Component actions**:
   - `no_action_stocked`: gap <= 0 and no exclusion applies
   - `timely_po_covered`: timely POs fully cover the gap
   - `transfer_only`: transfers fully cover the gap, no purchase needed
   - `purchase_required`: purchase requisition needed (may be combined with transfers)
   - `overstock_excluded`: effective available already exceeds total required and no timely POs are in play
6. **Exclusions**: components with `target_overstock` (gap is negative and no timely POs), `timely_po_covers_gap` (POs cover it), or `stocked_no_gap` (already sufficient stock) go into `excluded_components`.
7. **Supplier mapping**: each product's `supplier_id` field identifies the default supplier. Use that supplier for purchase requisitions.
8. **Costs**: requisition `unit_cost` comes from the product record. `extended_cost` = unit_cost * quantity.

### Supplier Incident Scorecard

1. Filter incidents by `open_date` within the analysis window (inclusive on both ends).
2. Group by supplier. For each supplier compute:
   - Incident count and percentage of filtered population (round to 1 decimal)
   - Total resolution cost (sum of `resolution_cost` field, round to 2 decimals)
   - Average duration: for closed incidents, `close_date - open_date` in calendar days; for open incidents, `analysis_date - open_date`
   - RMA count (incidents with `incident_type` = RMA)
   - Work order count (incidents with `incident_type` = WORK_ORDER)
   - Open incident count (incidents with `status` = open)
   - Severe count (incidents with `severity` in high or critical)
3. **Recommendation codes** (apply in precedence order, first match wins):

| Code | Trigger conditions |
|---|---|
| `ESCALATE_SUPPLIER` | supplier `quality_status` = quality_hold AND incident_count >= 3; OR any critical RMA; OR RMA_count >= 3 AND total_resolution_cost >= 15000.00 |
| `PROCESS_REVIEW` | WORK_ORDER_count >= 3 AND WORK_ORDER_count > RMA_count |
| `WATCHLIST` | supplier `quality_status` in (watch, quality_hold); OR incident_count >= 4; OR total_resolution_cost >= 12000.00; OR severe_count >= 2 |
| `MONITOR` | none of the above |

### Procurement Quality Control

Given a list of target supplier IDs and an analysis window:

1. Fetch incidents for the window and the target suppliers. Also fetch supplier records for quality_status, and purchase orders for each supplier (status = open or confirmed).
2. For each supplier, compute: recent incident count, RMA count, severe/critical count, open incident count, affected SKUs (SKUs referenced in their incidents), and sample incident IDs (up to 5 most recent).
3. **Decision logic**:

| Decision | Conditions |
|---|---|
| `freeze_new_replenishment` | `quality_status` = quality_hold AND (recent_incident_count >= 3 OR severe_or_critical_count >= 1), AND there are open/confirmed POs to hold |
| `buyer_review_required` | `quality_status` = quality_hold OR watch AND recent_incident_count >= 2 AND there are open/confirmed POs; OR severe_or_critical_count >= 2 AND any quality status |
| `monitor_only` | none of the above |

4. `held_po_ids`: for suppliers with `freeze_new_replenishment` or `buyer_review_required`, include all their open/confirmed POs. For `monitor_only`, held_po_ids is empty.
5. `release_supplier_ids`: all suppliers whose decision is `monitor_only`.

### Shipping Quotes

Call `/shipping/quote` with:
- `warehouse_id`: the order's requested warehouse
- `destination_zip`: from the customer record
- `weight_lb`: sum of product weights across all order lines (product `weight_lb` field * line quantity)
- `speed`: from the order record (`shipping_speed` or `requested_speed` field)

If the order has no explicit speed, default to `standard`. The quote returns `zone_distance` (integer), `service_days` (integer), and `total_cost_usd` (number, 2 decimals).

## Cross-Reference Workflow

For typical operational tasks, follow this sequence:

1. Fetch the business payload and answer template from the input.
2. Extract the wave/order IDs/supplier IDs/BOM IDs from the payload.
3. Query orders (by wave or IDs) to get lines, SKUs, quantities, requested warehouses, and customer IDs.
4. Batch query products for all SKUs found, checking active status, weight, supplier, and unit cost.
5. Batch query customers for all customer IDs found, checking status flags and zip codes.
6. For inventory-sensitive tasks, query inventory for each warehouse/SKU combination.
7. For replenishment tasks, query BOMs and purchase orders for coverage analysis.
8. For scorecard/procurement tasks, query incidents within the specified date window and suppliers for quality status.
9. Compute decisions per the business rules above.
10. Request shipping quotes where the template requires them.
11. Assemble the JSON response matching the template exactly. Sort all lists as specified.

## Output Formatting Rules

- Currency values: round to 2 decimal places.
- Percentages: round to 1 decimal place.
- Duration averages: round to 2 decimal places.
- Sort list fields: ascending by their natural key (order_id, sku, supplier_id, line_id, incident_id, po_id) unless the template specifies a different sort order.
- Nullable fields: use JSON `null` (not the string "null") when the template allows it.
- Empty lists: use `[]`, never omit them.
- Date strings: use ISO 8601 YYYY-MM-DD format.
- Response must be valid JSON. No trailing commas, no comments, no narrative text outside the JSON root.
