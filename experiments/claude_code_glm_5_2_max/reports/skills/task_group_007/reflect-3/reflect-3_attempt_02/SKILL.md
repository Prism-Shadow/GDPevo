# Northwind ERP Fulfillment Solver — Transferable Business Rules

This skill encodes the business rules and SOPs needed to solve Northwind ERP
fulfillment tasks using the shared remote API. It covers six task families:
expedite-queue decisions, BOM replenishment, supplier incident scorecards,
mixed-warehouse allocation, quality-hold review, and shipping quotes.

## API Usage

**Base URL:** `<remote-env-url>`

**Calling convention:** `curl -sS --max-time 30 '<url>'`
The server speaks HTTP/1.0 and closes each connection. Use `python3 -c
"import json,sys; print(json.dumps(json.load(sys.stdin), indent=2))"` to
parse JSON, or pipe through `jq` if available.

**Endpoints (all GET):**

| Endpoint | Key params | Returns |
|---|---|---|
| `/health` | — | manifest, record counts, seed |
| `/products` / `/products/<sku>` | — | sku, name, active, safety_stock, overstock_threshold, unit_cost, weight_lb, supplier_id, category |
| `/customers` / `/customers/<id>` | — | customer_id, name, account_status, risk_flag, tier, margin_band |
| `/warehouses` | — | warehouse_id, name, zip, region |
| `/inventory` | `warehouse_id=`, `sku=` | on_hand, reserved, quarantined, last_count_date |
| `/purchase_orders` | `supplier_id=`, `sku=`, `status=` | po_id, sku, supplier_id, warehouse_id, status, eta, quantity |
| `/orders?wave=` / `/orders/<id>` | `wave=`, `required_date=`, `customer_id=` | order_id, customer_id, warehouse_id, destination_zip, shipping_speed, priority, required_date, lines[] |
| `/shipping/quote` | `warehouse_id=`, `destination_zip=`, `weight_lb=`, `speed=` | total_cost, zone_distance, service_days, base_rate, fuel_surcharge_rate, carrier |
| `/incidents` | `start=`, `end=`, `supplier_id=`, `sku=`, `incident_type=`, `status=` | incident_id, supplier_id, sku, incident_type, severity, status, open_date, close_date, resolution_cost, root_cause, warehouse_id |
| `/suppliers` | — | supplier_id, name, quality_status |
| `/boms` / `/boms/<bom_id>` | — | bom_id, name, warehouse_id, target_date, components[]{sku, quantity_per_kit} |

**Warehouse IDs and ZIPs:** WH_NORTH=07102, WH_CENTRAL=60607, WH_WEST=89502.

**Shipping speeds:** `ground`, `two_day`, `overnight`.

**Customer account_status values:** `active`, `blocked`, `review_required`.
**Customer risk_flag values:** `none`, `fraud_watch`, `credit_watch`.

**Incident severity values:** `low`, `medium`, `high`, `critical`.
"Severe" = severity in {high, critical}.

**PO status values:** `open`, `confirmed`, `received`, `cancelled`.
"Open or confirmed" means status ∈ {open, confirmed}.

---

## Core Stock Calculations

### Effective available stock
```
gross     = on_hand - reserved - quarantined
effective = gross - safety_stock        # may be negative; floor at 0 for output fields
```
Use `max(0, effective)` when reporting an "effective_available" or
"effective_available" integer field. Keep the true (possibly negative)
value for internal gap arithmetic.

### Shipping weight
```
total_weight_lb = sum(product.weight_lb * line.quantity  for each line)
```
Pass the full float to `/shipping/quote?weight_lb=<total>`. The API returns
`total_cost` (USD), `zone_distance` (integer), `service_days` (integer).

---

## Task Family 1 — Expedite-Queue Decision (per-order classification)

**Input:** A memo listing order IDs in an expedite wave.
**Output:** `wave_id`, `records[]` (sorted by order_id), `summary`.

### Per-order fields
Each record requires: `order_id`, `inventory_status`, `customer_exception`,
`final_decision`, `next_action`, `shortage_skus`, `inactive_skus`,
`low_stock_skus`, `shipping_quote`.

### Customer exception (check first, in this order)
1. `account_status == "blocked"` → `account_blocked`
2. `account_status == "review_required"` → `review_required`
3. `risk_flag == "fraud_watch"` → `fraud_watch`
4. `risk_flag == "credit_watch"` → `credit_watch`
5. Otherwise → `none`

If a customer has both `blocked` status and a risk flag, the exception is
`account_blocked` (status takes priority).

### SKU classification (per line, per order's warehouse)
For each line in the order, look up the product and inventory at the
order's warehouse:

- **Inactive SKU** (`product.active == false`): add to `inactive_skus`.
  Do NOT also add to `shortage_skus`.
- **Shortage** (for active SKUs only): `effective < quantity` → add to
  `shortage_skus`.
- **Low stock** (for any active SKU not already a shortage):
  `effective >= quantity` AND `(effective - quantity) < safety_stock`
  → add to `low_stock_skus`.
- Otherwise: the SKU is ready.

All SKU lists are sorted ascending by SKU string.

### Inventory status (per order, precedence high→low)
1. Any inactive SKU AND any shortage SKU → `inactive_and_shortage`
2. Any inactive SKU (no shortage) → `inactive_sku`
3. Any shortage SKU (no inactive) → `shortage`
4. Any low-stock SKU (no shortage, no inactive) → `low_stock`
5. All ready → `ready`

### Decision precedence (high→low)
| Precedence | Condition | final_decision | next_action |
|---|---|---|---|
| 1 | customer_exception == account_blocked | `reject_hold` | `hold_credit_or_fraud` |
| 2 | customer_exception in {review_required, fraud_watch, credit_watch} | `manual_review` | `send_account_review` |
| 3 | Any inactive SKU (no account exception) | `manual_review` | `escalate_product_master` |
| 4 | Any shortage (no account exception, no inactive) | `backorder` | `create_backorder` |
| 5 | Any low stock (no above) | `delayed_release` | `delay_and_monitor` |
| 6 | All ready | `ship_now` | `release_to_pick` |

**Important:** Account exception takes full precedence over product/inventory
status, including inactive SKUs. When the customer is under review AND a
line has an inactive product, the next_action is `send_account_review`
(not `escalate_product_master`), because the account check comes first.

### Shipping quote (all orders, regardless of decision)
For every order, compute the shipping quote using the order's warehouse,
destination ZIP, total line-item weight, and the order's `shipping_speed`.
The quote is always populated, even for backorder/reject/manual-review orders.

### Summary
- `order_count`: number of records
- `decision_counts`: object with keys ship_now, delayed_release,
  manual_review, backorder, reject_hold → integer counts
- `total_shipping_cost_usd`: sum of all shipping_quote.total_cost_usd,
  rounded to 2 decimals
- `blocked_order_ids`: orders with final_decision == reject_hold, sorted
- `manual_review_order_ids`: orders with final_decision == manual_review, sorted
- `backorder_order_ids`: orders with final_decision == backorder, sorted
- `inactive_sku_order_ids`: orders that have at least one inactive SKU,
  sorted

### Common misjudgments
- Using `gross < ordered` for shortage instead of `effective < ordered`.
  This misses SKUs that would consume safety stock (physical stock exists
  but is below the safety buffer).
- Adding inactive SKUs to `shortage_skus` in addition to `inactive_skus`.
  Inactive SKUs should appear ONLY in `inactive_skus`.
- Using `(gross - ordered) < safety_stock` for low_stock. This is
  mathematically identical to `effective < ordered` (i.e., it IS shortage).
  The correct low_stock test is `(effective - ordered) < safety_stock`
  applied only when `effective >= ordered`.
- Forgetting the shipping quote on non-release orders.
- Omitting low_stock_skus entries when the order also has shortage. The
  lists are independent — low_stock_skus should still be populated even
  if the order status is "shortage".

---

## Task Family 2 — BOM Replenishment Package

**Input:** A production memo naming BOM IDs, build quantities, and build
dates at a target warehouse.
**Output:** `task_id`, `plan_date`, `kit_targets`, `component_plan`,
`transfer_requests`, `purchase_requisitions`, `excluded_components`,
`summary`.

### Demand calculation
```
for each build in the memo:
    for each component in the BOM:
        demand[sku] += quantity_per_kit * build_quantity
needed_by[sku] = earliest build_date among builds that use this SKU
```

### Component plan (sorted by sku ascending)
For each component SKU at the target warehouse:

1. **target_effective_available** =
   `max(0, on_hand - reserved - quarantined - safety_stock)` at target wh.
2. **gap** = `max(0, total_required - target_effective_available)`.
3. **timely_po_qty** = sum of `po.quantity` across all POs for this SKU
   that are: status ∈ {open, confirmed} AND `po.warehouse_id == target_wh`
   AND `po.eta <= needed_by`. Use the RAW total (do NOT cap at gap).
   `coverage_po_ids` = sorted list of the corresponding po_id strings.
4. **remaining_after_po** = `max(0, gap - timely_po_qty)`.
5. **Transfer sources:** For every other warehouse, compute
   `spare = max(0, gross - safety_stock)` where
   `gross = on_hand - reserved - quarantined` at that warehouse.
   Sort sources by spare descending, then warehouse_id ascending. Draw
   from the largest first until the gap is met or all sources exhausted.
   `transfer_qty` = total transferred.
6. **purchase_requisition_qty** = `max(0, remaining_after_po - transfer_qty)`.

### Final action and exclusion reason
| Condition | final_action | exclusion_reason |
|---|---|---|
| gap == 0 AND effective > overstock_threshold | `overstock_excluded` | `target_overstock` |
| gap == 0 AND effective <= overstock_threshold | `no_action_stocked` | `stocked_no_gap` |
| gap > 0 AND remaining_after_po == 0 | `timely_po_covered` | `timely_po_covers_gap` |
| gap > 0 AND remaining_after_po > 0 AND purchase == 0 AND transfer > 0 | `transfer_only` | `none` |
| gap > 0 AND purchase > 0 | `purchase_required` | `none` |

Components with gap == 0 or remaining_after_po == 0 are added to
`excluded_components` (sorted by sku). Excluded components have
`supporting_po_ids` (sorted; empty for overstock/stocked, populated for
timely_po_covers_gap). Excluded components are NOT in transfer_requests
or purchase_requisitions.

### Transfer requests (sorted by sku asc, quantity desc, from_warehouse_id asc)
Each: `{sku, from_warehouse_id, to_warehouse_id, quantity, needed_by}`.
`needed_by` = earliest build date for that SKU.

### Purchase requisitions (sorted by sku asc)
Each: `{sku, supplier_id, warehouse_id, quantity, needed_by, unit_cost,
extended_cost}`.
- `supplier_id` and `unit_cost` come from the product master.
- `extended_cost` = `round(unit_cost * quantity, 2)`.
- `warehouse_id` = target warehouse.

### Summary
- `component_count`: total components in component_plan
- `total_purchase_units`: sum of purchase_requisition_qty
- `total_purchase_cost`: sum of extended_cost, rounded to 2 decimals
- `total_transfer_units`: sum of transfer_qty
- `timely_po_covered_units`: sum of `min(timely_po_qty, gap)` for each
  component where remaining_after_po == 0

### Common misjudgments
- Capping `timely_po_qty` at the gap. The field reports total eligible
  PO quantity, not the amount consumed.
- Using `stocked_no_gap` instead of `target_overstock` when
  effective > overstock_threshold but has no gap. Both conditions produce
  an exclusion, but the reason must match.
- Checking POs at all warehouses for "same-warehouse" POs. Only POs at the
  target warehouse count.
- Forgetting `supporting_po_ids` for `timely_po_covers_gap` exclusions.
- Computing `needed_by` as the LATEST build date. Use the EARLIEST.

---

## Task Family 3 — Supplier Incident Scorecard

**Input:** A request JSON specifying a date filter on `open_date`
(inclusive start/end), an `analysis_date`, duration rules, percentage
precision, and a recommendation policy.
**Output:** `analysis_window`, `summary`, `supplier_scorecard`,
`top_escalation_suppliers`, `highest_cost_supplier_id`,
`highest_share_supplier_id`.

### Incident filtering
Fetch `/incidents?start=<start>&end=<end>`. The date filter applies to
`open_date`. Both dates are inclusive.

### Per-supplier metrics (only suppliers with ≥1 filtered incident)
Group incidents by `supplier_id`. For each:
- `incident_count`: number of filtered incidents for that supplier
- `incident_percentage` = `round(incident_count / total_filtered * 100, 1)`
- `total_resolution_cost` = `round(sum(resolution_cost), 2)`
- `avg_duration_days` = `round(mean(durations), 2)`, where:
  - Closed: `(close_date - open_date).days`
  - Open: `(analysis_date - open_date).days`
- `rma_count`: incidents with type == RMA
- `work_order_count`: incidents with type == WORK_ORDER
- `open_incident_count`: status == open
- `severe_incident_count`: severity in {high, critical}

`supplier_scorecard` sorted by supplier_id ascending.

### Recommendation policy (precedence high→low)
Test each supplier against the highest-precedence rule first. The first
match wins.

1. **ESCALATE_SUPPLIER** — supplier `quality_status == "quality_hold"` AND
   `incident_count >= 3`, OR any RMA incident with severity == critical,
   OR `rma_count >= 3` AND `total_resolution_cost >= 15000.00`.
2. **PROCESS_REVIEW** — `work_order_count >= 3` AND
   `work_order_count > rma_count`.
3. **WATCHLIST** — `quality_status` in {watch, quality_hold}, OR
   `incident_count >= 4`, OR `total_resolution_cost >= 12000.00`, OR
   `severe_incident_count >= 2`.
4. **MONITOR** — none of the above.

### Top escalation suppliers
`top_escalation_suppliers`: list of supplier_id strings where
recommendation_code == ESCALATE_SUPPLIER, sorted by:
1. `incident_count` descending
2. `total_resolution_cost` descending
3. `supplier_id` ascending

### Highest cost/share
- `highest_cost_supplier_id`: supplier_id with the max
  `total_resolution_cost`.
- `highest_share_supplier_id`: supplier_id with the max `incident_count`.

### Summary
- `filtered_incident_count`: total incidents in the filtered population
- `supplier_count`: count of suppliers with ≥1 filtered incident
- `total_resolution_cost`: sum across ALL filtered incidents, rounded to 2 decimals
- `overall_rma_count`: total RMA-type incidents in the population
- `overall_work_order_count`: total WORK_ORDER-type incidents

### Common misjudgments
- Using close_date instead of open_date for the primary date filter.
- Duration for open incidents must use `analysis_date`, NOT today's date.
- Percentage denominator is the TOTAL filtered population, not the supplier
  count.
- Recommendation precedence is strict — a supplier matching ESCALATE must
  not be tested against PROCESS_REVIEW or WATCHLIST.

---

## Task Family 4 — Mixed-Warehouse Allocation (line-level decisions)

**Input:** An order wave with orders across multiple warehouses. Each order
has multiple lines. A desk memo specifies allowed actions.
**Output:** `wave_id`, `line_actions`, `transfer_requests`,
`blocked_orders`, `order_rollup`, `summary`.

### Per-line action (sorted by order_id asc, then line_id asc)
For each order, fetch the customer record first and determine the
customer-level reason:

- `account_status == "blocked"` → reason = `account_blocked`, order is blocked
- `risk_flag == "fraud_watch"` → reason = `fraud_watch`, order is blocked
- `risk_flag == "credit_watch"` → reason = `account_review_required` (no
  separate credit_watch enum value; maps to review), order is blocked
- `account_status == "review_required"` → reason = `account_review_required`,
  order is blocked
- No account/risk issue → proceed to product/inventory checks

**Decision:**
1. If the order has an account/risk block → ALL lines in that order:
   `action = "manual_review"`, `primary_reason = <account reason>`,
   `ship_quantity = 0`, all other quantities 0.
2. If the product (SKU) is inactive → that line:
   `action = "manual_review"`, `primary_reason = "inactive_product"`.
3. If `effective >= quantity` at the requested warehouse:
   `action = "ship"`, `ship_quantity = quantity`, reason = `none`.
4. If `effective < quantity` at the requested warehouse:
   - `ship_quantity = min(effective, quantity)` (what the requested wh can ship)
   - `remaining = quantity - ship_quantity`
   - Check other warehouses: `spare = max(0, gross - safety_stock)` at each.
     Pick the warehouse with the most spare.
   - If that spare >= remaining:
     `action = "transfer"`, `transfer_from = <best_wh>`,
     `transfer_quantity = remaining`, reason = `insufficient_effective_stock`.
   - Else:
     `action = "backorder"`, `ship_quantity = 0`,
     `backorder_quantity = quantity` (full line),
     reason = `insufficient_effective_stock`.

**Key:** When an order is blocked at the account/risk level, ALL its lines
get the account reason — even if a line's product is inactive. The account
reason takes precedence per-line.

### blocked_orders (sorted list of order IDs)
Orders stopped at the account or customer-risk level (account_blocked,
fraud_watch, credit_watch, review_required). This does NOT include
orders that only have inactive-product line-level issues.

### Line action fields
```
order_id, line_id, sku,
requested_warehouse,    # enum: WH_NORTH | WH_CENTRAL | WH_WEST
requested_effective_available,  # integer, effective at the requested wh
action,                 # ship | transfer | backorder | manual_review
ship_quantity,          # integer (0 for manual_review/backorder)
transfer_from,          # warehouse or null
transfer_quantity,      # integer (0 unless action == transfer)
backorder_quantity,     # integer (0 unless action == backorder)
primary_reason           # none | account_blocked | account_review_required
                        # | fraud_watch | inactive_product | insufficient_effective_stock
```

### Transfer requests (sorted by order_id, then line_id)
Each: `{order_id, line_id, sku, from_warehouse, to_warehouse, quantity}`.

### Order rollup (sorted by order_id)
| Outcome | Condition |
|---|---|
| `manual_review` | Order is in blocked_orders (all lines manual_review due to account/risk) |
| `ready_to_ship` | All lines are "ship" |
| `needs_transfer` | All lines are "ship" and/or "transfer" (at least one transfer) |
| `has_backorder` | All lines are "backorder" |
| `manual_review` | Any line is manual_review (for non-blocked orders with inactive product) |
| `mixed_actions` | Multiple different non-ship actions |

### Summary
- `total_orders`, `total_lines`
- `ship_lines`, `transfer_lines`, `backorder_lines`, `manual_review_lines`
- `blocked_orders` (count of blocked order IDs)
- `transfer_units`, `backorder_units`

### Common misjudgments
- Excluding `review_required` or `credit_watch` orders from
  `blocked_orders`. All account-level and customer-risk-level stops belong
  in the list.
- Using `inactive_product` as the per-line reason when the order is already
  blocked at the account level. Account reason takes precedence per-line.
- Setting `ship_quantity` to the effective amount AND backordering the rest.
  For `backorder` action, `ship_quantity = 0` and `backorder_quantity` is
  the full line quantity.
- For transfer, setting `ship_quantity = 0` when the requested warehouse
  has SOME effective stock. Ship what's available, transfer the rest.

---

## Task Family 5 — Quality-Hold Replenishment Control

**Input:** A memo listing target supplier IDs and an analysis window
(start/end dates).
**Output:** `analysis_window`, `supplier_decisions`, `held_po_ids`,
`release_supplier_ids`, `summary`.

### Per-supplier metrics (sorted by supplier_id asc)
For each target supplier, fetch incidents in the analysis window
(`/incidents?start=<start>&end=<end>&supplier_id=<sid>` — date filter
applies to open_date, inclusive):

- `recent_incident_count`: total incidents in window
- `recent_rma_count`: RMA-type incidents
- `severe_or_critical_count`: severity in {high, critical}
- `open_incident_count`: status == open
- `affected_skus`: sorted unique SKU strings from the incidents
- `sample_incident_ids`: sorted incident_id strings, max 5

### Decision logic
| quality_status | Condition | decision |
|---|---|---|
| `quality_hold` | always | `freeze_new_replenishment` |
| `watch` | `severe_or_critical_count >= 2` | `buyer_review_required` |
| `watch` | `severe_or_critical_count < 2` | `monitor_only` |
| `approved` | significant incident volume (>=4 incidents or >=2 severe or >=3 RMAs) | `buyer_review_required` |
| `approved` | otherwise | `monitor_only` |

### Held POs
For suppliers with `freeze_new_replenishment` or `buyer_review_required`:
fetch ALL POs for that supplier and collect those with status in {open,
confirmed}. These are `held_po_ids` for that supplier.

For `monitor_only` suppliers: `held_po_ids` = empty list.

### Top-level fields
- `held_po_ids`: sorted unique union of all held PO IDs across all
  freeze/buyer-review suppliers.
- `release_supplier_ids`: sorted list of supplier_ids with decision ==
  `monitor_only`.

### Summary
- `suppliers_reviewed`: count of supplier_decisions entries
- `freeze_count`, `buyer_review_count`, `monitor_count`
- `held_po_count`: length of held_po_ids
- `total_recent_incidents`: sum of recent_incident_count across all suppliers

### Common misjudgments
- Using incident_count threshold for buyer_review on watch suppliers. The
  correct trigger for watch suppliers is `severe_or_critical_count >= 2`,
  not raw incident count.
- Setting all watch suppliers to `monitor_only` regardless of severe
  incidents. Watch suppliers with >= 2 severe/critical incidents should be
  `buyer_review_required`.
- Including held POs for monitor_only suppliers. Only freeze/buyer-review
  suppliers' POs are held.
- Not sorting `sample_incident_ids` or exceeding the max-5 cap.

---

## Reusable SOP (applies to all task families)

1. **Read the prompt and answer template carefully.** The template
   specifies required keys, enums, and sort orders. Missing a key or using
   an out-of-enum value causes large score losses.
2. **Fetch the products list once** and cache it. Most tasks need
   safety_stock, overstock_threshold, unit_cost, weight_lb, active flag,
   and supplier_id.
3. **Fetch all customers for the wave** and cache. Check account_status
   and risk_flag.
4. **Compute effective stock** = `max(0, on_hand - reserved - quarantined -
   safety_stock)`. Reserve the un-floored value for internal gap math.
5. **Check account/risk first** for any order-level classification. The
   precedence is always: blocked > fraud/credit > review > inactive >
   shortage > low_stock > ready.
6. **Shipping quotes** use `total_cost` (not `cost_usd`) from the API
   response. The answer field may be named `total_cost_usd` per the
   template.
7. **Round all currency to 2 decimals**, percentages to the specified
   precision (usually 1 decimal for scorecard, 2 for duration).
8. **Sort every list** exactly as the template specifies. Common sort keys:
   sku ascending, order_id ascending, supplier_id ascending, incident_id
   ascending, quantity descending.
9. **Floor effective stock at 0 in output fields** but use the true value
   for gap and remaining calculations.
10. **Verify enum values** — fields like `primary_reason`, `action`,
    `final_decision`, `quality_status`, and `decision` have restricted
    allowed values. Never use a value not in the template's enum.
