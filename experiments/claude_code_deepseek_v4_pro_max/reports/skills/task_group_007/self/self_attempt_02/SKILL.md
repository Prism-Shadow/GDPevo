# Northwind Components ERP — Operational Skill

## Base URL

```
GDPEVO_ENV_BASE_URL=http://34.46.77.124:8007
```

All endpoints are relative to this base. No localhost, no environment setup scripts.

---

## API Endpoint Reference

| Endpoint | Method | Key Query Params | Returns |
|---|---|---|---|
| `/health` | GET | — | Service status |
| `/products` | GET | — | All 54 products (active + inactive) |
| `/products/<sku>` | GET | — | Single product detail |
| `/customers` | GET | — | All 40 customers |
| `/customers/<customer_id>` | GET | — | Single customer (also used by `/orders/<id>`) |
| `/warehouses` | GET | — | 3 warehouses: WH_NORTH, WH_CENTRAL, WH_WEST |
| `/inventory` | GET | `?warehouse_id=&sku=` | Inventory records (both params optional; omit for all) |
| `/purchase_orders` | GET | `?supplier_id=&sku=&status=` | POs; status values: open, confirmed, received, cancelled |
| `/orders` | GET | `?wave=&customer_id=` | Orders filtered by wave or customer |
| `/orders/<order_id>` | GET | — | Single order detail (same shape as list item) |
| `/shipping/quote` | GET | `?warehouse_id=&destination_zip=&weight_lb=&speed=` | Quote with total_cost, zone_distance, service_days |
| `/incidents` | GET | `?start=&end=&supplier_id=&sku=&incident_type=&status=` | Date range REQUIRED; other filters optional |
| `/suppliers` | GET | — | All 12 suppliers with quality_status and region |
| `/boms` | GET | — | All BOMs with components and warehouse |
| `/boms/<bom_id>` | GET | — | Single BOM detail |

**Critical**: `/incidents` requires `start` and `end` params (YYYY-MM-DD). Always pass both. Date filter is inclusive on both ends.

---

## Core Calculations

### Effective Available Inventory

```
effective = on_hand - quarantined - reserved
```

- **on_hand**: total physically present
- **quarantined**: held for quality inspection — NOT available
- **reserved**: allocated to other orders/waves — NOT available
- **Negative effective**: possible when quarantined + reserved > on_hand; treat as 0 (no stock available)
- **Safety stock**: minimum buffer per product (`product.safety_stock`), used for low_stock classification
- **Overstock threshold**: per-product cap (`product.overstock_threshold`), used in replenishment exclusion logic

**Never use on_hand alone for availability decisions.** Always compute `effective = on_hand - quarantined - reserved`.

### Shipping Quote Weight

```
order_weight_lb = sum(product.weight_lb × line.quantity) for every line in the order
```

- Get `product.weight_lb` from `/products/<sku>` or the full `/products` list
- Do NOT estimate weight; compute exactly from the live product master
- Call `/shipping/quote` with the order's `warehouse_id`, `destination_zip`, computed `weight_lb`, and `shipping_speed`
- Use the response's `total_cost` directly as `shipping_quote.total_cost_usd`
- Also use `zone_distance` (integer) and `service_days` (integer) from the response

### Currency Precision

All cost/money fields must be **rounded to 2 decimal places** using standard rounding (round half up). Use `round(value, 2)`.

### Percentage Precision

When specified, round percentages to **1 decimal place** (e.g., `round(pct, 1)`).

### Duration Precision

Average durations rounded to **2 decimal places**.

---

## Task 1: Expedite Queue Dispatch (train_001 pattern)

### Data Gathering

1. Fetch orders for the wave: `GET /orders?wave=<wave_id>`
2. Filter to the `order_ids` listed in the expedite memo
3. For each order's customer: `GET /customers/<customer_id>` (or index the full `/customers` list)
4. For each order's line SKUs: `GET /products/<sku>` (or index the full `/products` list)
5. For each order's warehouse + SKU: `GET /inventory?warehouse_id=<wh>&sku=<sku>` (or index all inventory)
6. For each order: `GET /shipping/quote?warehouse_id=<wh>&destination_zip=<zip>&weight_lb=<weight>&speed=<speed>`

### Inventory Status Classification (per order)

Check each line's SKU at the order's warehouse:

1. **inactive_sku**: any line SKU has `product.active == false`
2. **shortage**: any line where `effective_available < line.quantity` at the requested warehouse
3. **low_stock**: all lines covered (`effective >= quantity`) BUT any SKU has `effective < product.safety_stock`
4. **ready**: all lines covered AND all SKUs at or above safety stock

**Priority / combined statuses**:
- `inactive_and_shortage`: at least one inactive SKU **and** at least one shortage
- `inactive_sku`: inactive SKU(s) present, but no shortage (all covered)
- `shortage`: no inactive SKUs, but at least one line uncovered
- `low_stock`: all covered, but at least one SKU below safety stock
- `ready`: all covered and all above safety stock

### Customer Exception Classification

From the customer record (`account_status` and `risk_flag`):

| Customer State | Exception |
|---|---|
| `account_status == "blocked"` | `account_blocked` |
| `risk_flag == "fraud_watch"` (and not blocked) | `fraud_watch` |
| `risk_flag == "credit_watch"` (and not blocked) | `credit_watch` |
| `account_status == "review_required"` (no risk flag) | `review_required` |
| `account_status == "active"` and `risk_flag == "none"` | `none` |

**Precedence**: `account_blocked` takes priority over risk flags. If both blocked and fraud_watch/credit_watch, exception is `account_blocked`.

### SKU Lists

- **shortage_skus**: SKUs where `effective < line.quantity` at the requested warehouse. Sorted ascending.
- **inactive_skus**: SKUs where `product.active == false`. Sorted ascending.
- **low_stock_skus**: SKUs where `effective >= line.quantity` but `effective < product.safety_stock`. Sorted ascending.

### Decision Matrix

Map (customer_exception, inventory_status) → (final_decision, next_action):

| Exception ↓ / Inventory → | ready | low_stock | shortage | inactive_sku | inactive_and_shortage |
|---|---|---|---|---|---|
| **none** | ship_now / release_to_pick | delayed_release / delay_and_monitor | backorder / create_backorder | manual_review / escalate_product_master | backorder / create_backorder |
| **review_required** | manual_review / send_account_review | manual_review / send_account_review | manual_review / send_account_review | manual_review / send_account_review | manual_review / send_account_review |
| **account_blocked** | reject_hold / hold_credit_or_fraud | reject_hold / hold_credit_or_fraud | reject_hold / hold_credit_or_fraud | reject_hold / hold_credit_or_fraud | reject_hold / hold_credit_or_fraud |
| **fraud_watch** | reject_hold / hold_credit_or_fraud | reject_hold / hold_credit_or_fraud | reject_hold / hold_credit_or_fraud | reject_hold / hold_credit_or_fraud | reject_hold / hold_credit_or_fraud |
| **credit_watch** | reject_hold / hold_credit_or_fraud | reject_hold / hold_credit_or_fraud | reject_hold / hold_credit_or_fraud | reject_hold / hold_credit_or_fraud | reject_hold / hold_credit_or_fraud |

**Key rule**: Customer exceptions (`review_required`, `account_blocked`, `fraud_watch`, `credit_watch`) override inventory status. If customer has any exception, the decision is determined by that exception regardless of inventory.

**Special case**: `inactive_and_shortage` without customer exception → `backorder` (the shortage is the binding constraint).

### Shipping Quote Per Order

Call `/shipping/quote` with the order's:
- `warehouse_id` from the order
- `destination_zip` from the order
- `weight_lb` = sum of product weights × quantities (all lines)
- `speed` from the order (use exactly as-is: `ground`, `two_day`, `overnight`)

Return the `zone_distance`, `service_days`, and `total_cost` from the response. **Always fetch a quote even for non-release decisions** — memo notes may explicitly require it.

---

## Task 2: Kit Build Replenishment (train_002 pattern)

### Data Gathering

1. Get BOMs: `GET /boms/<bom_id>` for each target BOM
2. Get all inventory for the planning warehouse: `GET /inventory?warehouse_id=<wh>`
3. Get all inventory for other warehouses (for transfers): `GET /inventory` and filter
4. Get all products: `GET /products` (need unit_cost, supplier_id, active status, overstock_threshold, safety_stock)
5. Get POs for the planning warehouse: `GET /purchase_orders?status=open` and `?status=confirmed`
6. Get suppliers: `GET /suppliers` (for names and quality status)

### Component Requirements

For each unique SKU across all target BOMs:
```
total_required = sum(bom.component.quantity_per_kit × target_build_quantity) over all BOMs containing that SKU
```

### Timely PO Check

A PO is "timely" for a build if:
- `po.warehouse_id == planning_warehouse`
- `po.status` is `"open"` or `"confirmed"` (NOT `received` — received is already in inventory; NOT `cancelled`)
- `po.eta` falls within a reasonable window before or on the build date

**PO statuses**: `open` (not yet confirmed but active), `confirmed` (committed), `received` (already delivered, counted in on_hand), `cancelled` (void — ignore completely).

`timely_po_qty` = sum of quantities from timely POs that haven't been received yet.

### Effective Available (for replenishment)

```
target_effective_available = effective_available at planning warehouse
```

Where `effective_available = on_hand - quarantined - reserved`.

**Important**: The `target_effective_available` is what's immediately usable. POs marked `received` are already in `on_hand`. Only count `open`/`confirmed` POs in `timely_po_qty`.

### Gap Calculation

```
gap = total_required - target_effective_available - timely_po_qty
```

If `gap <= 0` → sufficiently covered.

### Transfer Logic

When the planning warehouse has insufficient stock:
1. Check other warehouses for the same SKU
2. Effective available at other warehouses = `on_hand - quarantined - reserved` (same formula)
3. Do NOT use protected stock from other warehouses. The transfer quantity should not reduce the source warehouse's effective below 0.
4. `transfer_qty = min(gap, effective_available_at_source)`
5. A single line can get transfers from multiple warehouses if needed
6. Transfer needed_by = the earliest build_date across BOMs requiring this SKU

### Purchase Requisition Logic

After transfers:
```
purchase_requisition_qty = max(0, gap - transfer_qty)
```

For each purchase requisition:
- `supplier_id`: from `product.supplier_id`
- `warehouse_id`: the planning warehouse
- `unit_cost`: from `product.unit_cost`
- `extended_cost`: `round(purchase_requisition_qty × unit_cost, 2)`
- `needed_by`: earliest build_date for BOMs needing this SKU

### Final Action Enum

| Condition | final_action |
|---|---|
| effective >= total_required (fully stocked) | `no_action_stocked` |
| timely POs cover the gap, no transfer/purchase needed | `timely_po_covered` |
| only transfers needed (no purchase) | `transfer_only` |
| purchase requisition needed (may also include transfers) | `purchase_required` |
| effective > overstock_threshold | `overstock_excluded` |

### Exclusion Logic

A component is **excluded** (goes to `excluded_components` list, not `component_plan`) when:
- **target_overstock**: `effective_available > product.overstock_threshold` at the planning warehouse
- **timely_po_covers_gap**: `timely_po_qty >= gap` and no transfer or purchase is needed
- **stocked_no_gap**: `effective_available >= total_required` and no purchasing or transfer action needed

If excluded for timely_po_covers_gap or stocked_no_gap, the SKU still appears in `component_plan` with appropriate `exclusion_reason`. Only `target_overstock` excluded components go to the `excluded_components` list.

### Transfer Request Ordering

Sort by: `sku` ASC → `quantity` DESC → `from_warehouse_id` ASC.

### Ordering Rules Summary

- `kit_targets`: by `bom_id` ASC
- `component_plan`: by `sku` ASC
- `transfer_requests`: by `sku` ASC, then `quantity` DESC, then `from_warehouse_id` ASC
- `purchase_requisitions`: by `sku` ASC
- `excluded_components`: by `sku` ASC

---

## Task 3: Supplier Incident Scorecard (train_003 pattern)

### Data Gathering

1. Get Q1 incidents: `GET /incidents?start=2026-01-01&end=2026-03-31`
2. Get all suppliers: `GET /suppliers`
3. No other endpoints needed for scoring

### Filtered Incident Population

The entire incident list returned by the date-filtered query IS the filtered population. All incidents with `open_date` within the inclusive range are included.

### Duration Calculation

- **Closed incident**: `(close_date - open_date)` in calendar days
- **Open incident**: `(analysis_date - open_date)` in calendar days, where analysis_date is provided in the scorecard request
- Round to 2 decimal places for `avg_duration_days`

### Incident Percentage

```
incident_percentage = round(supplier.incident_count / total_filtered_incidents × 100, 1)
```

Denominator is ALL Q1-filtered incidents, not just the supplier's.

### Severity Classification

- **severe**: `severity` is `"high"` or `"critical"` (case-sensitive, lowercase)
- **open**: `status == "open"` (no close_date, or close_date is null)

### Supplier Scorecard Row Computation

For each supplier with at least one incident in the filtered set:
- `incident_count`: total incidents for this supplier
- `incident_percentage`: `round(count / total × 100, 1)`
- `total_resolution_cost`: sum of all resolution_cost, rounded to 2 decimals
- `avg_duration_days`: average of per-incident durations, rounded to 2 decimals
- `rma_count`: count where `incident_type == "RMA"`
- `work_order_count`: count where `incident_type == "WORK_ORDER"`
- `open_incident_count`: count where `status == "open"`
- `severe_incident_count`: count where `severity` in `["high", "critical"]`

Rows sorted by `supplier_id` ASC.

### Recommendation Code Precedence

Evaluate in strict order; first match wins:

1. **ESCALATE_SUPPLIER** if ANY of:
   - Supplier `quality_status == "quality_hold"` AND `incident_count >= 3`
   - Any incident has `incident_type == "RMA"` AND `severity == "critical"`
   - `rma_count >= 3` AND `total_resolution_cost >= 15000.00`

2. **PROCESS_REVIEW** if:
   - `work_order_count >= 3` AND `work_order_count > rma_count`

3. **WATCHLIST** if ANY of:
   - Supplier `quality_status` is `"watch"` or `"quality_hold"`
   - `incident_count >= 4`
   - `total_resolution_cost >= 12000.00`
   - `severe_incident_count >= 2`

4. **MONITOR**: none of the above conditions triggered

**Critical trap**: ESCALATE_SUPPLIER condition 1 says "quality_hold with at least 3 filtered incidents" — both parts must be true. Just being on quality_hold alone is not enough for escalation; it needs 3+ incidents too.

### Top Escalation Suppliers

Only suppliers whose `recommendation_code == "ESCALATE_SUPPLIER"`.
Sorted by: `incident_count` DESC → `total_resolution_cost` DESC → `supplier_id` ASC.

### Highest Cost / Highest Share

- `highest_cost_supplier_id`: supplier with the maximum `total_resolution_cost`
- `highest_share_supplier_id`: supplier with the maximum `incident_percentage`

---

## Task 4: Allocation Desk — Mixed Warehouse (train_004 pattern)

### Data Gathering

1. Get all orders for wave: `GET /orders?wave=<wave_id>`
2. Get all customers referenced in those orders
3. Get all products referenced in order lines
4. Get inventory for all 3 warehouses: `GET /inventory` (no filter)
5. Build an index: `effective[sku][warehouse] = on_hand - quarantined - reserved`

### Line-Level Decision Logic

For each line in each order:

1. **Customer/product gate first**:
   - If `customer.account_status == "blocked"` → `manual_review`, reason `account_blocked`
   - If `customer.risk_flag == "fraud_watch"` → `manual_review`, reason `fraud_watch`
   - If `customer.account_status == "review_required"` → `manual_review`, reason `account_review_required`
   - If `product.active == false` → `manual_review`, reason `inactive_product`

2. **Inventory check** (if passed gate):
   - `requested_effective_available = effective[sku][requested_warehouse]`
   - If `requested_effective_available >= quantity` → `ship`, `ship_quantity = quantity`
   - If `requested_effective_available < quantity`:
     - Check other warehouses for the SKU
     - `shortfall = quantity - requested_effective_available`
     - If another warehouse has `effective >= shortfall` → `transfer`
     - Otherwise → `backorder`

### Transfer Selection

When a line needs transfer:
- `ship_quantity = requested_effective_available` (what the requested warehouse CAN supply, may be 0)
- `transfer_quantity = shortfall` (the uncovered amount)
- Pick ONE source warehouse that can cover the full shortfall
- `transfer_from` = that warehouse's ID
- If no single warehouse can cover the shortfall → `backorder` instead of partial transfer
- `backorder_quantity = shortfall` only if no transfer is possible

### Restricted Stock

**Never treat quarantined or reserved stock as available.** The `effective` formula already handles this.

### Transfer Request Records

Only create `transfer_requests` entries for lines where `action == "transfer"`:
- `order_id`, `line_id`, `sku` from the order line
- `from_warehouse`: the source warehouse (`transfer_from`)
- `to_warehouse`: the order's requested warehouse
- `quantity`: the `transfer_quantity`

### Order Rollup

For each order, determine the overall outcome:
- `ready_to_ship`: all lines are `ship`
- `needs_transfer`: at least one `transfer`, no backorders or manual reviews
- `has_backorder`: at least one `backorder`, no manual reviews
- `manual_review`: at least one `manual_review`
- `mixed_actions`: multiple action types across lines (e.g., some ship, some backorder)

### Blocked Orders

`blocked_orders` list: order_ids where customer account is blocked or has elevated risk (`account_status == "blocked"` or `risk_flag in ["fraud_watch", "credit_watch"]`).

### Ordering Rules

- `line_actions`: by `order_id` ASC, then `line_id` ASC
- `transfer_requests`: by `order_id` ASC, then `line_id` ASC
- `blocked_orders`: by order_id ASC
- `order_rollup`: by `order_id` ASC

---

## Task 5: Procurement Quality Control (train_005 pattern)

### Data Gathering

1. Get suppliers: `GET /suppliers` (filter to target IDs)
2. Get incidents for the analysis window: `GET /incidents?start=<start>&end=<end>&supplier_id=<id>` for each target supplier
3. Get POs for each supplier: `GET /purchase_orders?supplier_id=<id>&status=open` and `?status=confirmed`
4. Get products for affected SKUs: `GET /products/<sku>` for each SKU in incidents

### Decision Logic

For each target supplier, evaluate:

1. **freeze_new_replenishment** if:
   - Supplier `quality_status == "quality_hold"`, OR
   - Any incident has `severity == "critical"` and `incident_type == "RMA"`, OR
   - `severe_or_critical_count >= 3` (severity in `["high", "critical"]`)

2. **buyer_review_required** if:
   - Supplier `quality_status == "watch"`, OR
   - `recent_incident_count >= 3`, OR
   - `recent_rma_count >= 2`

3. **monitor_only**: none of the above triggered

### Held PO IDs

For suppliers with `freeze_new_replenishment` or `buyer_review_required`:
- Collect all POs where `status in ["open", "confirmed"]` for that supplier
- These go in the supplier's `held_po_ids` list AND the top-level `held_po_ids` list
- Sorted ASC in both places

### Affected SKUs

Unique SKUs that appear in any incident for this supplier in the analysis window. Sorted ASC.

### Sample Incident IDs

Up to 5 incident IDs from the supplier's recent incidents. Sorted ASC. Pick the first 5 alphabetically/numerically.

### Release Supplier IDs

Suppliers whose decision is `monitor_only`. These have no held POs.

### Ordering

- `supplier_decisions`: by `supplier_id` ASC
- All internal lists (affected_skus, sample_incident_ids, held_po_ids): sorted ASC
- `held_po_ids` (top-level): sorted ASC, unique
- `release_supplier_ids`: sorted ASC

---

## Cross-Cutting Patterns & Pitfalls

### Enum Values Are Case-Sensitive and Lowercase

All controlled vocabularies use **lowercase_with_underscores**. Never capitalize or use spaces in enum values. Examples: `"ship_now"`, `"review_required"`, `"quality_hold"`, `"fraud_watch"`.

### Sorting Is Always Required

Every list field in every answer template has a specified sort order. **Always sort.** Common defaults:
- Order IDs, SKUs, Supplier IDs: ASC string sort
- Secondary sorts vary by task — read the template carefully

### Never Hardcode Data

All product, customer, inventory, incident, and PO data comes from the live API. Do not cache or assume values from training examples.

### Inventory: Effective, Not On-Hand

Every task that checks stock must use `effective = on_hand - quarantined - reserved`. This is the single most important formula in the system.

### Null/None Handling

- `close_date: null` means the incident is open
- `transfer_from: null` is valid when action is not `transfer`
- Use JSON `null`, not the string `"null"`

### Date Formats

- Input dates: `YYYY-MM-DD` strings
- Date arithmetic: use calendar days (not business days)
- `required_date` on orders is the customer-requested date; it is NOT the same as build_date in replenishment

### PO Status Lifecycle

`open` → `confirmed` → `received` (or `cancelled` at any stage).
- Only `open` and `confirmed` count as "timely" POs for replenishment
- `received` POs are already in `on_hand` inventory
- `cancelled` POs should be ignored entirely

### Warehouse IDs

Only three exist: `WH_NORTH`, `WH_CENTRAL`, `WH_WEST`.
- `WH_NORTH`: New Jersey, zip 07102, Northeast
- `WH_CENTRAL`: Illinois, zip 60607, Midwest
- `WH_WEST`: Nevada, zip 89502, West

### Shipping Speed Values

`ground`, `two_day`, `overnight` — pass these exactly as they appear on the order.

### Supplier Quality Statuses

`approved`, `watch`, `quality_hold` — three states reflecting increasing concern.

### Customer State Fields

Two independent dimensions:
- `account_status`: `active`, `blocked`, `review_required`
- `risk_flag`: `none`, `fraud_watch`, `credit_watch`

A customer can be `active` with `fraud_watch` — the risk flag still matters.

### Product Active Flag

`product.active == false` means the SKU is discontinued/inactive. Inactive SKUs should trigger `escalate_product_master` or `manual_review` depending on the task context. Orders with inactive SKUs cannot be automatically released.

### Incident Type Values

`RMA` and `WORK_ORDER` — two types. RMA = return/quality issue from customer. WORK_ORDER = internal operational issue.

### Root Cause Values (incidents)

`customer_return`, `supplier_defect`, `count_variance`, `incorrect_pick`, `carrier_damage` — these are informational but do not directly drive decisions.

### Currency Fields

- `total_cost_usd`, `resolution_cost`, `unit_cost`, `extended_cost`, `total_purchase_cost`, `total_shipping_cost_usd`
- All rounded to 2 decimal places
- Sum BEFORE rounding intermediate values, round only the final result

### Summary Totals Must Be Exact

Every summary section requires counts and sums that exactly match the detail records. Recompute from the detail lists — do not estimate. Common traps:
- `total_shipping_cost_usd` = sum of all order shipping quotes, rounded to 2 decimals
- `decision_counts` = tally of each `final_decision` across all records
- `total_purchase_cost` = sum of all `extended_cost` in purchase requisitions

---

## SOP: Processing Any Train Task

1. **Read the prompt and answer template** to understand required output shape
2. **Read any memo/payload** for task-specific parameters (wave IDs, BOM IDs, supplier IDs, date ranges)
3. **Fetch all needed API data**: products, customers, inventory, orders, incidents, POs as applicable
4. **Build lookup indexes** in memory: `products[sku]`, `customers[id]`, `inventory[sku][wh]`, etc.
5. **Process each record** following the classification rules documented above
6. **Sort every list** according to the answer template's ordering rules
7. **Compute summary** by aggregating from the sorted detail lists
8. **Validate**: all enum values match the allowed set; all currency fields rounded to 2 decimals; all lists sorted
9. **Output** a single JSON object matching the answer template exactly — no extra keys, no narrative text
