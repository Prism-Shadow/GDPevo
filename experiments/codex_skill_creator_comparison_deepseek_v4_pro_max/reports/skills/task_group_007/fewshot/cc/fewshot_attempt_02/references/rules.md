# Northwind Business Rules Reference

This reference consolidates reusable decision patterns observed across the
Northwind Components ERP desk workflows. Use it alongside the answer template
and task memo for any operational desk task; the memo always takes precedence
when it states explicit thresholds or overrides.

---

## Inventory: effective available

For every SKU at every warehouse, the working quantity is:

    effective_available = on_hand - reserved

Quarantined stock is not part of effective available unless the task memo
explicitly directs you to include it. Reserved stock has already been allocated
and must not be double-counted.

### Negative effective available

When on_hand < reserved, effective available is negative. Treat this as zero
usable stock for the SKU at that warehouse: nothing can be shipped from that
location for that SKU.

---

## Product active status

Each product has an active field (boolean). An inactive product (active false)
means the SKU cannot be automatically released. Lines with inactive SKUs must
be flagged for manual review or escalation unless the task memo states
otherwise.

---

## Shipping-quote conventions

### Endpoint

    GET /shipping/quote?warehouse_id=<id>&destination_zip=<zip>&weight_lb=<weight>&shipping_speed=<speed>

Shipping speed values: ground, two_day, overnight. The response provides
total_cost, service_days, zone_distance, and other fields to map into the
answer template.

### Weight calculation

For a multi-line order, sum product weight_lb times line quantity across all
lines of the order. Look up weight_lb from the product records.

### When to request a quote

Some tasks ask for a shipping quote even for orders that are held or rejected.
Read the task memo: if it says quote is needed even if the queue decision is
not release, fetch the quote unconditionally for every order.

---

## Customer exception classification

The account_status and risk_flag fields from the customer record determine
whether the order receives automatic clearance or manual intervention.

| account_status   | risk_flag     | customer_exception |
| ---------------- | ------------- | ------------------ |
| active           | none          | none               |
| review_required  | none          | review_required    |
| review_required  | fraud_watch   | fraud_watch        |
| review_required  | credit_watch  | credit_watch       |
| blocked          | any           | account_blocked    |
| active           | fraud_watch   | fraud_watch        |
| active           | credit_watch  | credit_watch       |

The reasoning: fraud_watch and credit_watch are inherently blocking flags that
supersede active account status. Blocked accounts are always blocked regardless
of risk flag.

---

## Inventory status classification (expedite / dispatch)

For an order at its requested warehouse, compare each line SKU against both
the product active flag and the effective available at that warehouse.

| Condition | inventory_status |
| --------- | ---------------- |
| All SKUs active AND every line effective_available >= quantity | ready |
| All SKUs active AND at least one line 0 < effective_available < quantity AND no line effective_available <= 0 | low_stock |
| All SKUs active AND at least one line effective_available <= 0 | shortage |
| At least one inactive SKU AND all active SKUs have effective_available >= quantity | inactive_sku |
| At least one inactive SKU AND at least one SKU effective_available <= 0 | inactive_and_shortage |

Only apply the inventory status labels used in the answer template. If the
template defines a different set of allowed values, obey that set.

### Shortage SKU lists

- shortage_skus: SKUs with effective_available <= 0 at the requested warehouse
  (active SKUs only; inactive SKUs go in inactive_skus).
- inactive_skus: SKUs where active is false.
- low_stock_skus: SKUs where 0 < effective_available < line quantity.
  Sort each list ascending by SKU.

---

## Final decision and next action (expedite / dispatch)

Customer exception takes priority over inventory status. Apply this precedence:

1. account_blocked       -> reject_hold  / hold_credit_or_fraud
2. fraud_watch           -> reject_hold  / hold_credit_or_fraud
3. credit_watch          -> manual_review / hold_credit_or_fraud
4. review_required       -> manual_review / send_account_review
5. none (use inventory status):
   - ready                -> ship_now      / release_to_pick
   - low_stock            -> delayed_release / delay_and_monitor
   - shortage             -> backorder     / create_backorder
   - inactive_sku         -> manual_review / escalate_product_master
   - inactive_and_shortage -> manual_review / escalate_product_master

If the answer template provides a different mapping, use the template mapping.
This table captures the typical pairing seen across Northwind workflows.

---

## Allocation: line-level actions

When a task asks for line-level allocation decisions across one or more
warehouses:

### Step 1: check the requested warehouse

Compute effective_available for the line SKU at the requested warehouse. If
effective_available >= line quantity, the line can ship from that warehouse.

### Step 2: check for account / product blocks

Before clearing any line for ship or transfer, inspect:

- Customer record: account_status and risk_flag
- Product record: active flag

If the customer is blocked, in review, fraud_watch, or credit_watch, mark the
line as manual_review with the appropriate primary_reason. If any SKU on the
line is inactive, mark as manual_review with reason inactive_product.

### Step 3: find transfer sources

When the requested warehouse cannot fully cover a line and the line is not
blocked, check the other warehouses for the same SKU:

- Compute effective_available at each other warehouse.
- A warehouse can supply up to its effective_available, but must not dip into
  reserved or quarantined stock.
- Pick one source warehouse that can cover the remaining quantity (or as much
  as possible). If the task memo says to prefer a specific warehouse or region,
  follow that guidance.

### Step 4: classify the line

| Situation | action |
| --------- | ------ |
| Customer block / risk flag / inactive product | manual_review |
| Requested warehouse covers full quantity | ship |
| Requested warehouse + transfer covers full quantity | transfer |
| No combination of warehouses can cover the quantity | backorder |

For transfer lines, set ship_quantity to what the requested warehouse can
release and transfer_quantity to the gap filled from the source warehouse.
For backorder lines, set backorder_quantity to the uncovered amount.

### Order rollup outcomes

- manual_review if every line is manual_review.
- ready_to_ship if every non-blocked line is ship.
- needs_transfer if at least one line is transfer and no line is backorder or
  manual_review.
- has_backorder if at least one line is backorder and no line is manual_review.
- mixed_actions otherwise.

---

## Kit-build replenishment

### Computing component requirements

For each BOM and each component:

    total_required = build_quantity * quantity_per_kit

Sum across BOMs when the same SKU appears in multiple BOMs targeting the same
warehouse.

### Effective available at the build warehouse

    target_effective_available = effective_available_at_target - total_required

A negative target means the warehouse needs more stock.

### Timely purchase orders

A PO qualifies as timely for a component if:

- status is open or confirmed (not cancelled or received)
- warehouse_id matches the build warehouse
- eta is on or before build_date (use the earliest build date for the SKU
  when it appears in multiple BOMs)

Sum the quantities of all timely POs for the SKU. This is timely_po_qty.
List the po_id values in coverage_po_ids, sorted ascending.

### Closing the gap

After accounting for timely POs, close any remaining negative
target_effective_available:

1. Transfers from other warehouses: for every other warehouse that has positive
   effective_available for the SKU, pull as much as possible, up to the gap.
   Split across warehouses as needed; order transfer requests by quantity
   descending.

2. Purchase requisitions: any gap remaining after transfers is purchased from
   the SKU supplier (from the product record). Use the supplier supplier_id and
   the product unit_cost. extended_cost = quantity * unit_cost, rounded to two
   decimals.

### Final action and exclusion

| Situation | final_action | exclusion_reason |
| --------- | ------------ | ---------------- |
| target_effective_available >= 0, no transfers needed | overstock_excluded | target_overstock |
| gap entirely covered by timely POs | timely_po_covered | timely_po_covers_gap |
| target_effective_available >= 0, no gap | no_action_stocked | stocked_no_gap |
| gap closed entirely by transfers | transfer_only | none |
| gap requires purchases | purchase_required | none |

Components marked overstock_excluded or timely_po_covered go into both
component_plan and excluded_components.

---

## Supplier incident scorecard

### Incident filtering

Filter the full incident list by open_date within the inclusive date range
from the task request. Use only incidents whose open_date falls on or between
the start and end dates.

### Supplier-level aggregation

For every supplier that appears in the filtered set:

- incident_count: count of filtered incidents for this supplier
- incident_percentage: supplier_count / total * 100, rounded to one decimal
- total_resolution_cost: sum of resolution_cost, rounded to two decimals
- avg_duration_days: for closed incidents, close_date minus open_date in
  calendar days; for open incidents, analysis_date minus open_date. Compute
  the mean across all of the supplier filtered incidents, rounded to two
  decimals.
- rma_count: count where incident_type is RMA
- work_order_count: count where incident_type is WORK_ORDER
- open_incident_count: count where status is open
- severe_incident_count: count where severity is high or critical

### Recommendation codes

The task memo defines the recommendation policy as a set of conditions with a
precedence order. Apply conditions in the order given; the first matching
condition sets the code.

Common conditions seen across Northwind scorecards:

- ESCALATE_SUPPLIER: quality-hold supplier with many incidents, or critical
  RMAs, or high RMA count combined with high cost.
- PROCESS_REVIEW: work-order incidents dominate over RMAs.
- WATCHLIST: supplier is on watch or quality_hold, or incident count exceeds a
  threshold, or cost exceeds a threshold, or severe incidents exceed a
  threshold.
- MONITOR: none of the above.

Always read the exact thresholds from the task memo; they vary between
scorecard runs.

---

## Procurement quality-hold decisions

When reviewing suppliers for replenishment controls within a date window:

1. Fetch all incidents whose open_date falls within the window.
2. For each target supplier, count recent incidents, RMAs, severe/critical
   incidents, and open incidents.
3. Collect held POs: all open or confirmed POs for that supplier.
4. Apply the decision policy from the memo. Typical gradient:
   - freeze_new_replenishment: quality_hold suppliers with significant recent
     incident activity.
   - buyer_review_required: watch-status suppliers with concerning patterns.
   - monitor_only: suppliers with low or manageable risk.

### Affected SKUs

List every distinct SKU that appears in at least one recent incident for the
supplier. Sort ascending.

### Sample incident IDs

List up to 5 incident IDs from the supplier recent incidents, sorted
ascending.
