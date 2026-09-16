# Northwind ERP Operations Desk Reference

Detailed workflows and decision rules for the five operations domains. Load
this file when the task requires a specific desk workflow beyond the summaries
in [SKILL.md](../SKILL.md).

---

## Domain 1: Expedite / Order Fulfillment

### Trigger

A task provides a wave or queue of order IDs requiring expedite decisions.
Often accompanied by a memo with operator notes. The task supplies an answer
template and may specify the wave ID.

### Workflow

1. Fetch `/orders` and filter to the wave's order IDs.
2. For each order, fetch the customer from `/customers`.
3. For each order line, fetch the product from `/products` and inventory from
   `/inventory` at the order's warehouse_id.
4. Compute effective_available per line: `on_hand - reserved - quarantined`.
5. Determine `inventory_status`:
   - All lines: effective_available >= line quantity AND all products active → `"ready"`
   - All covered but at least one line dips below safety_stock → `"low_stock"`
   - Any line short (effective_available < quantity) AND all active → `"shortage"`
   - Any line has inactive product AND no shortage → `"inactive_sku"`
   - Any line has inactive product AND shortage → `"inactive_and_shortage"`
6. Determine `customer_exception`:
   - `account_status = "blocked"` → `"account_blocked"`
   - `risk_flag = "fraud_watch"` → `"fraud_watch"`
   - `risk_flag = "credit_watch"` → `"credit_watch"`
   - `account_status = "review_required"` → `"review_required"`
   - Otherwise → `"none"`
7. Determine `final_decision` and `next_action` (first match wins, this order):
   - customer_exception is `"account_blocked"` or `"fraud_watch"` → reject_hold / hold_credit_or_fraud
   - customer_exception is `"review_required"` or `"credit_watch"` → manual_review / send_account_review
   - inventory_status is `"inactive_sku"` or `"inactive_and_shortage"` → manual_review / escalate_product_master
   - inventory_status is `"shortage"` → backorder / create_backorder
   - inventory_status is `"low_stock"` → delayed_release / delay_and_monitor
   - inventory_status is `"ready"` → ship_now / release_to_pick
8. Build `shortage_skus` (sorted): all SKUs where effective_available < line_qty.
9. Build `inactive_skus` (sorted): all SKUs where product.active is false.
10. Build `low_stock_skus` (sorted): all SKUs where effective_available - line_qty < safety_stock but effective_available >= line_qty.
11. Get shipping quote: compute total weight as sum over all lines of
    (product.weight_lb × line.quantity), use order's shipping_speed and
    destination_zip, call `/shipping/quote` from the order's warehouse_id.
    Use the `total_cost` field for total_cost_usd.

### Summary

- Count decisions (ship_now, delayed_release, manual_review, backorder, reject_hold).
- Sum all shipping quote total_cost_usd values.
- Collect blocked, manual_review, backorder, and inactive_sku order IDs separately.

---

## Domain 2: Kit Build / Replenishment Planning

### Trigger

A task provides a production memo with BOM IDs, target build quantities, build
dates, and a planning site warehouse. The task supplies an answer template.

### Workflow

1. Fetch the named BOMs from `/boms`.
2. Compute `total_required` per component SKU across all kit targets:
   `sum(kit.quantity_per_kit × build_quantity)`.
3. For each unique component SKU at the planning warehouse:
   - Get inventory record from `/inventory` at the planning warehouse.
   - Get product master from `/products`.
   - `effective_available = on_hand - reserved - quarantined`.
   - `target_effective_available = effective_available - total_required`.
4. Check timely purchase orders for the SKU at the planning warehouse:
   - Filter `/purchase_orders` for SKU, warehouse matching planning site,
     status in ("open", "confirmed"), eta <= max(build_dates) + 1 day.
   - Sum quantities; cap at the shortage amount.
5. Transfers: for the uncovered gap (after own stock and timely POs), check
   `/inventory` at all other warehouses. For each alternate warehouse,
   `available = on_hand - reserved - quarantined - safety_stock`. The transfer
   pool is any positive available from non-target warehouses.
6. Purchase requisition: any remaining gap not covered by stock, timely POs,
   or transfers becomes a purchase requisition.
7. **Transfer-purchase split**: apply transfers first (up to the gap), then
   purchase for the remainder. Do not double-count.

### Decision field values

**final_action:**
- All lines covered by own stock alone → `"no_action_stocked"`
- Only transfers needed → `"transfer_only"`
- Purchase needed (even with transfers) → `"purchase_required"`
- Timely PO covers gap → `"timely_po_covered"`
- target_effective_available > overstock_threshold → `"overstock_excluded"`

**exclusion_reason:**
- `"target_overstock"` when target_effective_available > overstock_threshold
- `"timely_po_covers_gap"` when timely POs cover the negative target_effective_available
- `"stocked_no_gap"` when target_effective_available >= 0 and not overstock
- `"none"` otherwise

### Transfer requests

Sort by sku ascending, quantity descending, from_warehouse_id ascending.
`from_warehouse_id` is the source warehouse with available stock.
`quantity` is how much to transfer (up to the gap for that SKU).

When multiple source warehouses are needed, prefer the one with the largest
available pool first. Set `needed_by` to the earliest build_date for any kit
needing that SKU.

### Purchase requisitions

`supplier_id` from the product's `/products` record.
`unit_cost` from the product's `/products` record.
`extended_cost = unit_cost × quantity` (rounded to 2 decimals).
`needed_by` is the latest build_date for any kit needing that SKU.
`warehouse_id` is the planning site.

### Excluded components

Only include SKUs with exclusion_reason other than `"none"`.
Include supporting_po_ids for timely_po_covers_gap exclusions.

### Summary

- `timely_po_covered_units`: sum of timely_po_qty across components where
  the gap was covered by POs (i.e., the full negative target_effective_available
  that got covered by POs, not necessarily the full PO quantity).

---

## Domain 3: Supplier Incident Scorecard

### Trigger

A task provides a scorecard request with date filter, analysis date, and a
recommendation policy block defining the codes, precedence, and triggering
conditions.

### Workflow

1. Fetch `/incidents` and filter by open_date in the analysis window
   (inclusive of both start and end dates).
2. Fetch `/suppliers` to get supplier names and quality_status.
3. For each supplier with at least one filtered incident:
   - `incident_count`: total filtered incidents
   - `incident_percentage`: (incident_count / total_filtered_incidents) × 100,
     rounded to 1 decimal place
   - `total_resolution_cost`: sum of resolution_cost, rounded to 2 decimals
   - `avg_duration_days`: average of per-incident durations (closed: close_date - open_date;
     open: analysis_date - open_date), rounded to 2 decimals
   - `rma_count`: count where incident_type = "RMA"
   - `work_order_count`: count where incident_type = "WORK_ORDER"
   - `open_incident_count`: count where status = "open"
   - `severe_incident_count`: count where severity in ("high", "critical")
4. Apply recommendation policy code evaluation in precedence order
   (ESCALATE_SUPPLIER → PROCESS_REVIEW → WATCHLIST → MONITOR), stopping at
   the first match.
5. Sort scorecard rows by supplier_id ascending.

### Recommendation policy evaluation (from the task-provided rules)

Apply each code's conditions in precedence order. If a supplier matches multiple
codes, use the highest-precedence one.

Typical conditions (exact rules come from the task's recommendation_policy block):
- **ESCALATE_SUPPLIER**: supplier on quality_hold with ≥ 3 filtered incidents,
  or any critical RMA, or ≥ 3 RMAs and ≥ 15000.00 total resolution cost.
- **PROCESS_REVIEW**: WORK_ORDER count ≥ 3 and exceeds RMA count.
- **WATCHLIST**: quality_status is watch or quality_hold, or incident_count ≥ 4,
  or total_resolution_cost ≥ 12000.00, or severe_incident_count ≥ 2.
- **MONITOR**: none of the above.

### Top escalation and peak suppliers

- `top_escalation_suppliers`: supplier_ids where recommendation_code is
  ESCALATE_SUPPLIER, sorted by incident_count descending, then
  total_resolution_cost descending, then supplier_id ascending.
- `highest_cost_supplier_id`: supplier_id with max total_resolution_cost.
  Break ties with supplier_id ascending.
- `highest_share_supplier_id`: supplier_id with max incident_percentage.
  Break ties with supplier_id ascending.

---

## Domain 4: Cross-Warehouse Allocation / Transfer Desk

### Trigger

A task provides a wave ID and a desk memo. Every order line in the wave must
be classified. The answer template specifies line-action records, transfer
requests, blocked orders, order rollup, and summary.

### Workflow

1. Fetch `/orders` and filter to the wave ID. Expand all lines across all
   orders.
2. For each order, fetch the customer from `/customers`.
3. For each line, fetch the product from `/products` and inventory from
   `/inventory` at the requested warehouse.
4. Compute `requested_effective_available = on_hand - reserved - quarantined`
   at the requested warehouse.
5. Determine action (first match wins):
   - Customer account_status is `"blocked"` or risk_flag is `"fraud_watch"` →
     `"manual_review"`, reason `"account_blocked"` or `"fraud_watch"`
   - Customer account_status is `"review_required"` or risk_flag is
     `"credit_watch"` → `"manual_review"`, reason `"account_review_required"`
   - Product active is false → `"manual_review"`, reason `"inactive_product"`
   - `requested_effective_available >= line.quantity` → `"ship"`,
     ship_quantity = line.quantity, reason `"none"`
   - `requested_effective_available < line.quantity`:
     - Check alternate warehouses: for each other warehouse, compute
       `available = on_hand - reserved - quarantined - safety_stock`.
       If alternate available >= shortage_qty, action is `"transfer"`.
       Pick the alternate warehouse with the most available stock.
       ship_quantity = whatever the requested warehouse can cover
       (min(requested_effective_available, line.quantity), never below 0).
       transfer_from = chosen alternate warehouse,
       transfer_quantity = shortage_qty.
     - If no transfer covers the shortage → `"backorder"`,
       backorder_quantity = shortage_qty.
6. Build transfer_requests from lines with action `"transfer"`, sorted by
   order_id ascending then line_id ascending.
7. Build blocked_orders: distinct order_ids where any line has reason
   account_blocked, account_review_required, or fraud_watch. Sorted ascending.
8. Build order_rollup per order (sorted by order_id ascending):
   - All lines action = "ship" → `"ready_to_ship"`
   - Any line action = "transfer", none backorder/manual_review → `"needs_transfer"`
   - Any line action = "backorder", none manual_review → `"has_backorder"`
   - Any line action = "manual_review" → `"manual_review"`
   - Mixed of ship, transfer, backorder (no manual_review) → `"mixed_actions"`

### Safe-stock rule

When computing transfer availability from alternate warehouses, subtract
safety_stock from their effective_available. Do not transfer inventory that
would push the source warehouse below its safety_stock threshold.

### Summary

Count total orders, total lines, ship/transfer/backorder/manual_review lines,
blocked orders, and total transfer and backorder units.

---

## Domain 5: Procurement Quality Risk Control

### Trigger

A task provides a quality-hold review memo with an analysis window, target
supplier IDs, and decision choices. The task supplies an answer template.

### Workflow

1. Fetch `/suppliers` for the target supplier IDs to get names and
   quality_status.
2. Fetch `/incidents` and filter by open_date within the analysis window
   for those suppliers.
3. Fetch `/purchase_orders` to find open or confirmed POs from those suppliers.
4. For each target supplier, compute:
   - `recent_incident_count`: total incidents in the window
   - `recent_rma_count`: incidents where incident_type = "RMA"
   - `severe_or_critical_count`: incidents where severity in ("high", "critical")
   - `open_incident_count`: incidents where status = "open"
   - `affected_skus`: unique SKUs from incidents and POs, sorted ascending
   - `sample_incident_ids`: up to 5 incident IDs from the window, sorted
   - `held_po_ids`: open/confirmed POs for this supplier, sorted ascending
5. Determine decision (first match in this order):
   - quality_status is `"quality_hold"` AND (severe_or_critical_count > 0
     OR recent_rma_count >= 3 OR recent_incident_count >= 6) →
     `"freeze_new_replenishment"`
   - quality_status is `"watch"` OR severe_or_critical_count >= 2 OR
     recent_incident_count >= 4 → `"buyer_review_required"`
   - otherwise → `"monitor_only"`
6. Build `held_po_ids`: sorted unique list of PO IDs from all supplier_decisions
   where decision is not `"monitor_only"`.
7. Build `release_supplier_ids`: sorted supplier IDs where decision is
   `"monitor_only"`.

### Summary

Count suppliers reviewed, freeze decisions, buyer_review decisions, monitor
decisions, held POs, and total recent incidents across all reviewed suppliers.
