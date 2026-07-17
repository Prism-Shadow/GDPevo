# Northwind ERP Operations Skill

## API Conventions

Base URL from `environment_access.md`; all endpoints relative to it.

### Core Endpoints

| Endpoint | Use |
|---|---|
| `/products/<sku>` | Active flag, category, supplier, safety_stock, overstock_threshold, unit_cost, weight_lb |
| `/customers/<customer_id>` | account_status, risk_flag, tier, margin_band |
| `/warehouses` | warehouse_id, zip, region |
| `/inventory?warehouse_id=&sku=` | on_hand, reserved, quarantined (omit sku for all) |
| `/orders?wave=` | Full order details with lines, warehouse, customer, shipping_speed, destination_zip |
| `/orders/<order_id>` | Single order detail |
| `/shipping/quote?warehouse_id=&destination_zip=&weight_lb=&speed=` | zone_distance, service_days, total_cost |
| `/incidents?start=&end=&supplier_id=&sku=&incident_type=&status=` | Date range filtering; all params optional |
| `/suppliers` | supplier_id, name, quality_status, region |
| `/boms` | bom_id, name, warehouse_id, components with quantity_per_kit |
| `/boms/<bom_id>` | Single BOM detail |
| `/purchase_orders?supplier_id=&sku=&status=` | po_id, status, quantity, eta, warehouse, supplier, sku |

### Effective Available Inventory

```
effective_available = on_hand - reserved - quarantined
```

All three deductions matter. Do NOT subtract safety_stock from effective. For transfer calculations from source warehouses, use the full effective (no safety-stock deduction).

### Shipping Quote Formula

Total weight = sum over all lines of (quantity × weight_lb). The quote endpoint already incorporates weight, zone, and speed into a single `total_cost` — no further multiplication needed. Round to 2 decimal places.

---

## Task Pattern: Expedite Queue (Dispatch Control)

**Trigger:** A wave memo lists orders requiring inventory, customer, and shipping checks.

### Classification Flow

For each order, evaluate every line SKU independently, then aggregate to order-level:

**Step 1 — Per-SKU checks:**
- **shortage:** `effective_available < line_quantity`
- **inactive:** `product.active == false`
- **low_stock:** `effective_available < product.safety_stock` (regardless of whether demand can be met)

**Step 2 — Per-order inventory_status (worst-case aggregation):**
- If ANY line is inactive AND ANY line has shortage → `inactive_and_shortage`
- Else if ANY line is inactive → `inactive_sku`
- Else if ANY line has shortage → `shortage`
- Else if ANY line has low_stock → `low_stock`
- Else → `ready`

**Step 3 — Customer exception (single value per order):**
Evaluate account_status and risk_flag. Only the most severe applies:
1. `account_blocked` — account_status is "blocked"
2. `fraud_watch` — risk_flag is "fraud_watch"
3. `credit_watch` — risk_flag is "credit_watch" (when account is not blocked)
4. `review_required` — account_status is "review_required" (when no higher-priority flag)
5. `none` — otherwise

**Step 4 — Final decision and next action:**

| Customer Exception | Inventory Status | final_decision | next_action |
|---|---|---|---|
| account_blocked | any | reject_hold | hold_credit_or_fraud |
| fraud_watch | any | reject_hold | hold_credit_or_fraud |
| credit_watch | any | manual_review | send_account_review |
| review_required | any | manual_review | send_account_review |
| none | ready | ship_now | release_to_pick |
| none | low_stock | delayed_release | delay_and_monitor |
| none | shortage | backorder | create_backorder |
| none | inactive_sku | manual_review | escalate_product_master |
| none | inactive_and_shortage | manual_review | escalate_product_master |

Account/risk issues always take precedence over inventory status for decision routing.

**Step 5 — SKU lists (per order):**
- `shortage_skus:` SKUs where effective < quantity, sorted ascending
- `inactive_skus:` SKUs where product.active is false, sorted ascending
- `low_stock_skus:` SKUs where effective < safety_stock but NOT in shortage, sorted ascending

Lists are mutually exclusive per SKU (a SKU appears in the highest-severity list only: shortage > inactive > low_stock).

**Step 6 — Shipping quote:**
Always request a quote regardless of final decision. Use the order's `shipping_speed` and `warehouse_id`, the order's `destination_zip`, and the total weight across all lines.

**Step 7 — Summary:**
- `blocked_order_ids:` orders where customer_exception is account_blocked or fraud_watch
- `manual_review_order_ids:` orders with final_decision "manual_review"
- `backorder_order_ids:` orders with final_decision "backorder"
- `inactive_sku_order_ids:` orders with any inactive SKU
- `total_shipping_cost_usd:` sum of all shipping quotes, rounded to 2 decimals

---

## Task Pattern: Kit Build Replenishment

**Trigger:** A production memo lists BOMs with target build quantities and dates at a planning warehouse.

### Component Plan Calculation

For each unique SKU across all BOMs:

1. **total_required** = sum over all BOMs of (build_quantity × quantity_per_kit)
2. **target_effective_available** = effective at the planning warehouse
3. **gap** = total_required - target_effective_available (negative gap means surplus)
4. **timely_po_qty** = sum of quantities from open/confirmed POs to the planning warehouse with ETA before the earliest build date needing that SKU

### Decision Logic

| Condition | final_action | exclusion_reason |
|---|---|---|
| gap ≤ 0 AND effective > overstock_threshold | overstock_excluded | target_overstock |
| gap ≤ 0 AND effective ≤ overstock_threshold | no_action_stocked | stocked_no_gap |
| gap > 0 AND timely_po_qty ≥ gap | timely_po_covered | timely_po_covers_gap |
| gap > 0 AND transfers cover full gap | transfer_only | none |
| gap > 0 AND transfers cover partial gap + purchase | purchase_required | none |
| gap > 0 AND no transfers + purchase | purchase_required | none |

### Transfers

For each SKU with a gap, check all other warehouses. Transfer up to the effective available (on_hand - reserved) from each source — do NOT subtract safety_stock. One SKU can have transfers from multiple warehouses.

### Transfer Requests Ordering

Sort by `sku` ascending, then `quantity` descending, then `from_warehouse_id` ascending.

### Purchase Requisitions

Use the SKU's `supplier_id` and `unit_cost` from the product record.
- `needed_by`: earliest build date requiring this component
- `extended_cost` = quantity × unit_cost, rounded to 2 decimals

### Excluded Components

List components where exclusion_reason is NOT "none". Sort by sku ascending. `supporting_po_ids` for timely_po_covers_gap; empty list for other reasons.

### Summary

- `component_count`: total number of unique SKUs in component_plan
- `total_purchase_units`: sum of all purchase_requisition quantities
- `total_purchase_cost`: sum of all extended_cost values, rounded to 2 decimals
- `total_transfer_units`: sum of all transfer quantities
- `timely_po_covered_units`: total_required amount covered by timely POs (the gap covered, not the PO quantity)

---

## Task Pattern: Supplier Incident Scorecard

**Trigger:** A scorecard request defines an incident date filter, analysis date, and recommendation policy.

### Incident Filtering

Filter incidents where `open_date` falls within the inclusive date range. All incidents in the filtered population are the denominator for percentages.

### Duration Calculation

- Closed incidents: calendar days from `open_date` to `close_date`
- Open incidents: calendar days from `open_date` to `analysis_date`

### Recommendation Code Precedence

Check conditions in order — first match wins:

1. **ESCALATE_SUPPLIER:** supplier is on quality_hold AND incident_count ≥ 3, OR has any critical-severity RMA, OR has ≥ 3 RMAs AND total_resolution_cost ≥ 15000.00
2. **PROCESS_REVIEW:** WORK_ORDER count ≥ 3 AND WORK_ORDER count > RMA count
3. **WATCHLIST:** quality_status is "watch" or "quality_hold", OR incident_count ≥ 4, OR total_resolution_cost ≥ 12000.00, OR severe_incident_count ≥ 2
4. **MONITOR:** none of the above

Severe severity values: "high" and "critical".

### Scorecard Ordering

- Rows: `supplier_id` ascending
- `top_escalation_suppliers`: incident_count descending, total_resolution_cost descending, supplier_id ascending
- `incident_percentage`: rounded to 1 decimal place
- All currency: rounded to 2 decimals
- `avg_duration_days`: rounded to 2 decimals

---

## Task Pattern: Allocation Desk (Mixed-Warehouse Transfer)

**Trigger:** A wave ID and allocation memo specifying line-level decisions across warehouses.

### Line Action Determination

Evaluate each order line independently:

**Step 1 — Hard blocks (force manual_review):**
- `account_status == "blocked"` → action=manual_review, primary_reason=account_blocked
- `risk_flag == "fraud_watch"` → action=manual_review, primary_reason=fraud_watch
- `risk_flag == "credit_watch"` → action=manual_review, primary_reason=credit_watch
- `account_status == "review_required"` → action=manual_review, primary_reason=account_review_required
- `product.active == false` → action=manual_review, primary_reason=inactive_product

Account/risk reasons take precedence over product reasons when both apply.

**Step 2 — Inventory processing (only if no hard block):**

Compute `effective_available` at the requested warehouse:
- If effective ≥ quantity → action=ship, ship_quantity=quantity
- If effective < quantity:
  - Ship any positive effective as `ship_quantity`
  - Check if ONE other warehouse has effective ≥ shortage
  - If yes → action=transfer, transfer_from=that warehouse, transfer_quantity=shortage
  - If no single warehouse can cover → action=backorder, backorder_quantity=shortage

**Transfer rule:** A single source warehouse must cover the FULL remaining shortage. If no single warehouse can, the line goes to backorder.

### primary_reason Precedence

When multiple conditions apply, use the highest precedence:
account_blocked > fraud_watch > credit_watch > account_review_required > inactive_product > insufficient_effective_stock > none

### Blocked Orders

Only orders with `account_blocked` or `fraud_watch` go into `blocked_orders`. credit_watch and review_required are NOT blockers but still force manual_review per line.

### Order Rollup

Per order:
- Any line is manual_review AND other actions exist → `mixed_actions`
- All lines manual_review → `manual_review`
- All lines ship → `ready_to_ship`
- Mix of ship and transfer → `needs_transfer`
- Mix of ship and backorder → `has_backorder`
- Other combinations → `mixed_actions`

---

## Task Pattern: Procurement Quality Control

**Trigger:** A set of target supplier IDs and an analysis window for reviewing replenishment controls.

### Decision Rules

| Supplier Status | Recent Incidents | Decision |
|---|---|---|
| quality_hold | any (≥ 1) | freeze_new_replenishment |
| watch | severe_or_critical ≥ 2 | buyer_review_required |
| watch | severe_or_critical < 2 | monitor_only |
| approved | any | monitor_only |

### Field Conventions

- `affected_skus`: sorted unique SKU strings from recent incidents
- `sample_incident_ids`: up to 5 sorted incident IDs from recent incidents
- `held_po_ids` per supplier: sorted list of open/confirmed PO IDs for that supplier
- Global `held_po_ids`: sorted unique union of held POs from all non-monitor_only suppliers
- `release_supplier_ids`: sorted list of supplier IDs with decision "monitor_only"
- `severe_or_critical_count`: incidents with severity "high" or "critical"
- `open_incident_count`: incidents with status "open"

---

## General Rules

### Controlled Enum Usage

Always use exact values from answer templates. Do not invent or abbreviate. Check template `allowed_values` lists before writing each field.

### Currency

All monetary values rounded to 2 decimal places. Use standard rounding (half-up).

### Sort Ordering

All lists sorted ascending by their natural key unless the template specifies otherwise. Primary key always stated first in multi-key sorts.

### Date Formats

All dates in `YYYY-MM-DD` format. Analysis windows use inclusive start and end dates.

### Warehouse IDs

Three warehouses only: `WH_NORTH`, `WH_CENTRAL`, `WH_WEST`. No other warehouse IDs exist in this domain.

### Product Active Flag

Always check `product.active` before classifying a line as shippable. Inactive products always trigger manual_review with primary_reason "inactive_product", regardless of stock levels.
