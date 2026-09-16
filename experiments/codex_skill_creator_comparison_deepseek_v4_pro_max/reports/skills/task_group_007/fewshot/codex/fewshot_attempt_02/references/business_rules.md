# Northwind Components Business Rules

Standard decision logic shared across Northwind ERP workflows. These rules are
derived from patterns observed in supply-chain dispatch, allocation,
replenishment, quality, and procurement tasks.

---

## 1. Inventory Status Classification

For each order line or product SKU at a given warehouse, compute
`effective_available` as defined in api.md:
`on_hand - reserved - quarantined - safety_stock`.

Classify inventory status at the order level (worst-case across all lines):

| Status | Condition |
|---|---|
| `ready` | Every line's effective_available >= line quantity |
| `low_stock` | At least one line has 0 < effective_available < line quantity, and no shortages or inactive SKUs |
| `shortage` | At least one line's effective_available <= 0, and all SKUs are active |
| `inactive_sku` | At least one line references a SKU with product.active == false, and no shortages |
| `inactive_and_shortage` | At least one inactive SKU AND at least one shortage line |

Collect SKU lists:
- `shortage_skus`: SKUs where effective_available <= 0 (sorted ascending).
- `low_stock_skus`: SKUs where 0 < effective_available < line.quantity (sorted
  ascending).
- `inactive_skus`: SKUs where product.active == false (sorted ascending).

---

## 2. Customer Exception Classification

Look up the order's customer via `GET /customers/{customer_id}`. Classify
using this precedence:

| Exception | Condition |
|---|---|
| `account_blocked` | `account_status == "blocked"` |
| `fraud_watch` | `risk_flag == "fraud_watch"` (takes precedence over other statuses) |
| `credit_watch` | `risk_flag == "credit_watch"` and not fraud_watch |
| `review_required` | `account_status == "review_required"` and no higher exception |
| `none` | `account_status == "active"` and `risk_flag == "none"` |

When an order has any customer exception other than `none`, all lines are
stopped regardless of inventory status.

---

## 3. Expedite Dispatch Decision Logic

Used when a queue memo lists orders needing dispatch decisions. Combine
inventory status and customer exception to produce a final decision and next
action.

### Decision Table

| Customer Exception | Inventory Status | Final Decision | Next Action |
|---|---|---|---|
| none | ready | `ship_now` | `release_to_pick` |
| none | low_stock | `delayed_release` | `delay_and_monitor` |
| none | shortage | `backorder` | `create_backorder` |
| none | inactive_sku | `manual_review` | `escalate_product_master` |
| none | inactive_and_shortage | `manual_review` | `escalate_product_master` |
| review_required | any | `manual_review` | `send_account_review` |
| account_blocked | any | `reject_hold` | `hold_credit_or_fraud` |
| fraud_watch | any | `reject_hold` | `hold_credit_or_fraud` |
| credit_watch | any | `reject_hold` | `hold_credit_or_fraud` |

Priority: customer exception overrides inventory status. If customer exception
is `none`, inventory status alone determines the decision.

---

## 4. Allocation Desk Line-Level Decisions

Used when a transfer wave needs per-line actions across multiple warehouses.
Each line is classified independently (except customer blocks which stop the
whole order).

### Line Action Rules

1. **Check customer exception first**. If the order's customer has
   `account_status == "blocked"`, `risk_flag == "fraud_watch"`, `risk_flag ==
   "credit_watch"`, or `account_status == "review_required"` -> action is
   `manual_review` for ALL lines in that order, with `ship_quantity = 0`,
   `transfer_quantity = 0`, `backorder_quantity = 0`.

2. **Check product active status**. If the line's SKU has `product.active ==
   false` -> action is `manual_review` with `primary_reason =
   "inactive_product"`. Apply even if customer is clean.

3. **For clean customer + active product**:
   - If effective_available >= line.quantity -> `ship`, `ship_quantity =
     line.quantity`.
   - If effective_available < line.quantity but >= 0 -> `ship`, `ship_quantity
     = effective_available`. Remaining shortage evaluated for transfer vs
     backorder.
   - If effective_available <= 0 -> evaluate transfer potential first.

4. **Transfer evaluation**: For the shortage portion, check if another
   warehouse has effective_available covering the shortage. Choose the
   warehouse with the most effective_available (prefer WH_NORTH over
   WH_CENTRAL over WH_WEST when tied). If transfer is possible -> `transfer`
   action with `transfer_from` set to the source warehouse and
   `transfer_quantity` equal to the gap (up to the source's
   effective_available). Any remainder after transfer becomes
   `backorder_quantity`.

5. **If no transfer source can cover** -> `backorder` action with
   `backorder_quantity` equal to the uncovered gap.

### Primary Reason

| Value | When |
|---|---|
| `none` | Normal ship or transfer line |
| `account_blocked` | Customer account_status is blocked |
| `account_review_required` | Customer account_status is review_required |
| `fraud_watch` | Customer risk_flag is fraud_watch |
| `inactive_product` | Product.active is false |
| `insufficient_effective_stock` | Inventory cannot cover and no transfer source exists |

---

## 5. Kit Replenishment Logic

Used when a production memo specifies BOM builds at a target warehouse.

### Step 1: Compute Total Required

For each component SKU across all target BOMs:
```
total_required = sum(build_quantity * quantity_per_kit)
```
for all BOMs using that SKU.

### Step 2: Compute Target Effective Available

`target_effective_available` is the effective_available at the target warehouse
for that SKU (using the formula from Section 1).

### Step 3: Identify Timely POs

Filter purchase orders for: same SKU, same warehouse, status in `(open,
confirmed)`, ETA <= the earliest build date requiring that SKU. Sum quantities
across all timely POs for that SKU-warehouse pair.

### Step 4: Determine Gap

```
gap = total_required - target_effective_available - timely_po_qty
```

If gap <= 0 -> component is covered by existing stock or timely POs. Do not
requisition.

### Step 5: Transfer from Other Warehouses

For uncovered gap, check effective_available at other warehouses. Can pull from
the warehouse with the most effective_available (greedy, prefer WH_NORTH >
WH_CENTRAL > WH_WEST for ties). Transfer quantity cannot exceed the source's
effective_available.

### Step 6: Purchase Requisition for Remainder

After transfers, any remaining gap becomes a purchase requisition. Use the
SKU's `supplier_id` and `unit_cost` from `/products`. `needed_by` is the
earliest build date requiring that SKU. `extended_cost = quantity * unit_cost`.

### Final Actions and Exclusions

| Condition | final_action | exclusion_reason |
|---|---|---|
| Stock covers total_required | `no_action_stocked` | `stocked_no_gap` |
| Timely POs cover gap | `timely_po_covered` | `timely_po_covers_gap` |
| Effective available > overstock_threshold | `overstock_excluded` | `target_overstock` |
| Transfer-only covers gap | `transfer_only` | `none` |
| Purchase required | `purchase_required` | `none` |

An excluded component still appears in `component_plan` with its final_action
and exclusion_reason but generates no transfer or purchase requisition.

---

## 6. Supplier Incident Scorecard Rules

### Filtering

Filter incidents by `open_date` within the analysis window (inclusive).

### Supplier-Level Aggregation

For each supplier with at least one filtered incident:
- `incident_count`: total filtered incidents
- `incident_percentage`: (incident_count / total_filtered_incidents) * 100,
  rounded to 1 decimal
- `total_resolution_cost`: sum of resolution_cost
- `avg_duration_days`: mean of per-incident durations (closed: close_date -
  open_date, open: analysis_date - open_date), rounded to 2 decimals
- `rma_count`: count where incident_type == "RMA"
- `work_order_count`: count where incident_type == "WORK_ORDER"
- `open_incident_count`: count where status == "open"
- `severe_incident_count`: count where severity in ("high", "critical")

### Recommendation Policy (precedence order)

Evaluate each supplier against conditions in this order; first match wins:

1. **ESCALATE_SUPPLIER**: quality_status == "quality_hold" AND incident_count >=
   3, OR any incident severity == "critical", OR rma_count >= 3 AND
   total_resolution_cost >= 15000.00.
2. **PROCESS_REVIEW**: work_order_count >= 3 AND work_order_count > rma_count.
3. **WATCHLIST**: quality_status in ("watch", "quality_hold"), OR incident_count
   >= 4, OR total_resolution_cost >= 12000.00, OR severe_incident_count >= 2.
4. **MONITOR**: none of the above apply.

---

## 7. Procurement Quality Control Rules

Used when reviewing suppliers for replenishment freeze decisions.

### Inputs

- Recent incidents: filter by open_date within a recent window (e.g.
  2026-03-01 to 2026-06-30).
- Supplier quality_status from `/suppliers`.
- Open/confirmed POs for the supplier from `/purchase_orders`.

### Decision Logic

| Condition | Decision |
|---|---|
| quality_status == "quality_hold" AND recent_incident_count >= 5 | `freeze_new_replenishment` |
| quality_status == "watch" AND (recent_incident_count >= 3 OR severe/critical count >= 2) | `buyer_review_required` |
| quality_status == "approved" AND recent_incident_count >= 3 | `buyer_review_required` |
| Otherwise | `monitor_only` |

**Held POs**: For `freeze_new_replenishment` and `buyer_review_required`,
include all open/confirmed POs for that supplier as held_po_ids (sorted). For
`monitor_only`, held_po_ids is an empty list.

**Release suppliers**: suppliers whose decision is `monitor_only`.

---

## 8. Shipping Quote Computation

1. Look up the order from `GET /orders/{order_id}`.
2. Compute total_weight = sum(line.quantity * product.weight_lb) for all lines.
3. Call `GET /shipping/quote?warehouse_id=...&destination_zip=...&weight_lb=...&service=...`
   using order fields.
4. Return `zone_distance` (int), `service_days` (int), and `total_cost`
   (number, rounded to 2 decimals).

---

## 9. General Formatting and Sort Rules

- **Currency**: round to 2 decimal places.
- **Percentages**: round to 1 decimal place.
- **Durations**: round to 2 decimal places.
- **Sorting**: all lists sorted ascending by their primary key unless otherwise
  specified. For order-level lists, sort by `order_id` ascending. For SKU
  lists, sort by `sku` ascending. For supplier lists, sort by `supplier_id`
  ascending.
- **JSON output only**: never include narrative text outside the JSON response.
- **All values derived from live API calls**: do not hard-code values from task
  memos or templates.
