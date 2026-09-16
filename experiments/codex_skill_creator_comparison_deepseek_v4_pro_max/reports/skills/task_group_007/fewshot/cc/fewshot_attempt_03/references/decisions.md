# Northwind ERP Decision Frameworks

Operational decision rules for each Northwind desk type. These frameworks describe how to reason about the data — they are not hardcoded lookup tables. Always cross-check the task's answer template for the exact enum values and output shape.

---

## 1. Expedite / Dispatch Control

Used when a queue memo lists order IDs and asks for per-order release decisions.

### Inventory status classification (per order)

For each order, inspect every line's SKU at the order's warehouse_id:

1. Compute effective_available = on_hand - reserved - quarantined for each SKU/warehouse.
2. Check the product's active flag.

Classify into exactly one status, using the worst applicable condition:

- **inactive_and_shortage**: At least one line's SKU is active=false AND at least one line's SKU has effective_available <= 0.
- **inactive_sku**: At least one line's SKU is active=false AND no line has effective_available <= 0.
- **shortage**: At least one line has effective_available <= 0 AND all SKUs are active.
- **low_stock**: At least one line has effective_available <= safety_stock (with effective_available > 0) AND no shortage AND all SKUs active.
- **ready**: All lines have effective_available > safety_stock AND all SKUs are active.

### Customer exception classification

Read the customer record for the order's customer_id:

| Condition | exception value |
|---|---|
| account_status == "blocked" | account_blocked |
| account_status == "review_required" | review_required |
| risk_flag == "credit_watch" (and account not blocked) | credit_watch |
| risk_flag == "fraud_watch" (and account not blocked) | fraud_watch |
| Otherwise | none |

### Final decision and next action

Decide by combining inventory status with customer exception. The general precedence is: account-level blocks > customer-risk flags > inventory shortages > stock levels.

| inventory_status | customer_exception | typical final_decision | typical next_action |
|---|---|---|---|
| any | account_blocked | reject_hold | hold_credit_or_fraud |
| any | fraud_watch | manual_review | hold_credit_or_fraud |
| any | credit_watch | manual_review | hold_credit_or_fraud |
| any | review_required | manual_review | send_account_review |
| shortage | none | backorder | create_backorder |
| inactive_sku | none | manual_review | escalate_product_master |
| inactive_and_shortage | none | manual_review | escalate_product_master |
| low_stock | none | delayed_release | delay_and_monitor |
| ready | none | ship_now | release_to_pick |

When an order has inactive SKUs, also set that order in inactive_sku_order_ids in the summary.

### SKU exception lists

- **shortage_skus**: All SKUs in the order where effective_available <= 0 at the order's warehouse. Sorted ascending.
- **inactive_skus**: All SKUs in the order where product.active is false. Sorted ascending.
- **low_stock_skus**: All SKUs in the order where effective_available > 0 but <= safety_stock. Sorted ascending.

### Shipping quotes

Always fetch a quote for every order in the memo, even for orders that are being held or rejected. Compute total weight from products, call the quote endpoint with the order's warehouse_id and destination_zip.

---

## 2. Replenishment / Kit Build Planning

Used when a production memo specifies BOMs, build quantities, and a planning warehouse.

### Step 1: Explode BOMs

For each BOM in the memo, multiply each component's quantity_per_kit by the target build_quantity. Sum across BOMs to get total_required per SKU.

### Step 2: Compute availability at the planning site

For each component SKU, get effective_available at the planning warehouse. Compute:

```
target_effective_available = effective_available - total_required
```

Negative means the warehouse is short after fulfilling the build; positive means surplus.

### Step 3: Check timely POs

A purchase order is "timely" for a component when ALL of these hold:
- status is "open" or "confirmed"
- warehouse_id matches the planning site
- eta is on or before the build date needing this component (use the earliest build date that requires this SKU)

Sum quantity across all timely POs for that SKU/warehouse. If the gap (abs(min(target_effective_available, 0))) is covered by timely PO quantity, the component is covered.

### Step 4: Check overstock

If effective_available >= overstock_threshold, the SKU is overstocked and should be excluded from replenishment — do not send more stock to this warehouse.

### Step 5: Fill gaps

For components not covered by timely POs and not overstocked, compute the remaining gap:

```
gap = max(0, total_required - effective_available)
```

1. **Transfers**: Check other warehouses for available effective inventory on this SKU. Do not drain a source warehouse below safety_stock unless the task instructions permit it. Use the best source (most available, or geographically closest). Record as transfer_requests.

2. **Purchase requisitions**: Any gap remaining after transfers becomes a purchase requisition. Use the SKU's supplier_id and unit_cost from the product master. Compute extended_cost = quantity * unit_cost, rounded to 2 decimals.

### Component plan final_action values

| Condition | final_action |
|---|---|
| effective_available >= overstock_threshold | overstock_excluded |
| Timely PO quantity covers the gap | timely_po_covered |
| Gap covered by transfers alone | transfer_only |
| Gap requires purchases (possibly with transfers) | purchase_required |
| effective_available >= total_required, not overstocked, no gap | no_action_stocked |

### Exclusion

Components with final_action overstock_excluded or timely_po_covered go into excluded_components with the appropriate reason and supporting PO IDs.

### Transfer and purchase ordering

- transfer_requests: Sort by sku ascending, then quantity descending, then from_warehouse_id ascending.
- purchase_requisitions: Sort by sku ascending.

---

## 3. Supplier Quality Scorecard

Used when a scorecard request specifies an incident date range and a recommendation policy.

### Step 1: Filter incidents

Keep only incidents where open_date falls within [start_date, end_date] (inclusive). This is the filtered incident population.

### Step 2: Aggregate per supplier

For each supplier with at least one filtered incident, compute:

- incident_count: Total filtered incidents
- incident_percentage: (count / filtered_population_total) * 100, rounded to 1 decimal
- total_resolution_cost: Sum of resolution_cost, rounded to 2 decimals
- avg_duration_days: Average duration. For closed incidents: calendar days from open_date to close_date. For open incidents: calendar days from open_date to analysis_date. Rounded to 2 decimals.
- rma_count: Count where incident_type == "RMA"
- work_order_count: Count where incident_type == "WORK_ORDER"
- open_incident_count: Count where status == "open"
- severe_incident_count: Count where severity in ["high", "critical"]

### Step 3: Apply recommendation policy

The task's scorecard request defines a recommendation_policy with precedence (first match wins). Apply each code's conditions in precedence order. Typical conditions involve combinations of quality_status, incident counts, RMA counts, total cost, and severity. Read the policy from the task payload — do not hardcode thresholds.

### Step 4: Top escalation and highest

- top_escalation_suppliers: suppliers where recommendation_code is the highest-precedence escalation code, sorted by incident_count descending, then total_resolution_cost descending, then supplier_id ascending.
- highest_cost_supplier_id: supplier with highest total_resolution_cost
- highest_share_supplier_id: supplier with highest incident_percentage

---

## 4. Allocation / Transfer Wave

Used when a wave memo asks for line-level decisions across a mixed-warehouse order set.

### Line-level decision logic

Process each line in this priority order:

#### 1. Customer account gates (apply to ALL lines of the order)

If the customer's account_status is "blocked": all lines get action=manual_review, primary_reason=account_blocked. Continue to next order.

If the customer's account_status is "review_required": all lines get action=manual_review, primary_reason=account_review_required. Continue to next order.

If the customer's risk_flag is "fraud_watch": all lines get action=manual_review, primary_reason=fraud_watch. Continue to next order.

#### 2. Product status

If the SKU's active is false: action=manual_review, primary_reason=inactive_product. Continue to next line.

#### 3. Inventory check

Compute effective_available at the line's requested_warehouse for that SKU.

- If effective_available >= quantity: **ship** the full quantity. ship_quantity = quantity, primary_reason = "none".
- If 0 < effective_available < quantity: **ship** what's available, **transfer** the remaining gap from another warehouse. ship_quantity = effective_available. Find one other warehouse with the needed gap quantity in effective_available (without draining below 0). transfer_from = that warehouse, transfer_quantity = gap. primary_reason = "none".
- If effective_available <= 0: Check other warehouses. If any has enough effective_available to cover the full quantity, **transfer** the full quantity from that warehouse. If no warehouse can cover, **backorder** the full quantity. primary_reason = "insufficient_effective_stock".

#### Transfer source selection

When transferring, pick a single source warehouse. Prefer the warehouse closest to the destination that has enough effective_available. Do not split transfers across multiple source warehouses for one line.

### Blocked orders

Collect order_ids where customer status blocked the entire order (account_blocked, account_review_required, fraud_watch). Sort ascending.

### Order rollup

For each order, derive one outcome from its lines:
- All lines ship → ready_to_ship
- All lines manual_review → manual_review
- At least one transfer and no backorder/manual_review → needs_transfer
- At least one backorder and no manual_review → has_backorder
- Mix of ship/transfer/backorder → mixed_actions

---

## 5. Procurement Quality Review

Used when a quality hold review memo lists target suppliers and an analysis window.

### Step 1: Gather data

Fetch incidents within the analysis window (open_date between start and end, inclusive). Fetch supplier records for target supplier IDs. Fetch purchase orders for those suppliers with status "open" or "confirmed".

### Step 2: Compute per-supplier metrics

Same aggregation as the scorecard (incident counts, RMA counts, severity counts, open counts, total cost), but limited to the analysis window and target suppliers.

### Step 3: Decision

Based on quality_status, incident severity, RMA rate, and open incident count, assign one of:
- **freeze_new_replenishment**: Highest concern. Supplier has active quality_hold with substantial incident history. Hold all open/confirmed POs.
- **buyer_review_required**: Moderate concern. Supplier shows quality issues or watch status with incidents that need human review.
- **monitor_only**: Low concern. No action needed — supplier can continue normal replenishment.

The decision thresholds are informed by the supplier's quality_status and the magnitude of its incident record relative to other reviewed suppliers. Interpret the data holistically — more severe status, more incidents, more RMAs, and open incidents all push toward stronger intervention.

### Step 4: Collect held POs

For each supplier with a hold or review decision, collect all open/confirmed POs as held_po_ids. For monitor_only suppliers, held_po_ids is empty. The global held_po_ids is the sorted unique union.

### Step 5: Affected SKUs and sample incidents

- affected_skus: sorted unique SKUs from recent incidents for each supplier.
- sample_incident_ids: up to 5 incident IDs from the supplier's recent incidents, sorted ascending.
