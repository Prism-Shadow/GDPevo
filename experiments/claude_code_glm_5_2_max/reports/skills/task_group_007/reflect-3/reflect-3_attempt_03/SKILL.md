# Northwind ERP Fulfillment Decision Skill

Executable experience for solving ERP fulfillment evaluation tasks against the
shared Northwind ERP API. Covers six business families: expedite-queue dispatch,
BOM replenishment, supplier incident scorecards, allocation/transfer decisions,
and procurement quality-hold review.

## Remote API Access

Base URL: `<remote-env-url>`  (the prompt may reference a local
`http://127.0.0.1:8007`; prefer the remote URL given in `environment_access.md`.)

Always use `curl -sS --max-time 30 '<url>'`. The server speaks HTTP/1.0 and
closes each connection after every request. Parse responses with `python3 -c
"import json; ..."` or `jq`.

### Endpoints (GET unless noted)

| Endpoint | Purpose |
|---|---|
| `GET /health` | Manifest with record counts. |
| `GET /products` / `GET /products/<sku>` | SKU master: sku, name, category, active, safety_stock, overstock_threshold, unit_cost, weight_lb, supplier_id. |
| `GET /customers` / `GET /customers/<id>` | Customer master: customer_id, name, account_status, risk_flag, tier, margin_band. |
| `GET /warehouses` | warehouse_id, name, zip, region. |
| `GET /inventory?warehouse_id=&sku=` | on_hand, reserved, quarantined, last_count_date. |
| `GET /purchase_orders?supplier_id=&sku=&status=` | po_id, sku, quantity, eta, status, warehouse_id, supplier_id. |
| `GET /orders?wave=&required_date=&customer_id=` / `GET /orders/<id>` | order_id, customer_id, warehouse_id, warehouse_id, shipping_speed, destination_zip, required_date, priority, wave, lines[{line_id, sku, quantity, unit_price}]. |
| `GET /shipping/quote?warehouse_id=&destination_zip=&weight_lb=&speed=` | Returns base_rate, fuel_surcharge_rate, total_cost, service_days, zone_distance, carrier. |
| `GET /incidents?start=&end=&supplier_id=&sku=&incident_type=&status=` | incident_id, supplier_id, sku, incident_type, severity, status, open_date, close_date, resolution_cost, root_cause, warehouse_id. |
| `GET /suppliers` | supplier_id, name, quality_status, region. |
| `GET /boms` / `GET /boms/<bom_id>` | bom_id, name, warehouse_id, target_date, components[{sku, quantity_per_kit}]. |

### Efficient data gathering

Download all collections up front, then process in Python:

```bash
curl -sS --max-time 30 '<remote-env-url>/products' > /tmp/products.json
curl -sS --max-time 30 '<remote-env-url>/customers' > /tmp/customers.json
curl -sS --max-time 30 '<remote-env-url>/warehouses' > /tmp/warehouses.json
curl -sS --max-time 30 '<remote-env-url>/suppliers' > /tmp/suppliers.json
curl -sS --max-time 30 '<remote-env-url>/boms' > /tmp/boms.json
curl -sS --max-time 30 '<remote-env-url>/inventory' > /tmp/inventory.json
curl -sS --max-time 30 '<remote-env-url>/purchase_orders' > /tmp/purchase_orders.json
curl -sS --max-time 30 '<remote-env-url>/incidents' > /tmp/incidents.json
```

---

## Core Business Rules

### 1. Effective Available Stock

```
effective_available = on_hand - reserved - quarantined - safety_stock
```

- `safety_stock` comes from the **product master**, not the inventory record.
- Effective stock **can be negative** (more committed/protected than on hand).
  Always use the raw value for `target_effective_available` and gap calculations.
  Do NOT cap at zero — capping caused score drops in testing.
- No inventory record for a (warehouse, sku) pair ⇒ treat effective as 0 for
  that pair.

### 2. Customer Account / Risk Overrides (checked BEFORE inventory)

Customer fields: `account_status` (active, blocked, review_required) and
`risk_flag` (none, fraud_watch, credit_watch).

**Exception precedence** (pick the first that applies):

| Condition | `customer_exception` | Decision impact |
|---|---|---|
| account_status == blocked | `account_blocked` | reject_hold / hold_credit_or_fraud |
| risk_flag == fraud_watch | `fraud_watch` | manual_review / hold_credit_or_fraud |
| account_status == review_required | `review_required` | manual_review / send_account_review |
| risk_flag == credit_watch | `credit_watch` | manual_review / send_account_review |
| else | `none` | proceed to product / inventory check |

The account/risk check happens **before** the inventory check in the decision
flow, but `inventory_status` is still computed and reported for every order.

### 3. Product Status Check (after account, before inventory)

- If a product has `active == false` (inactive), the line gets
  `manual_review` / `escalate_product_master`.
- This check applies **per-line**, not per-order (in allocation tasks an order
  can have some inactive-SKU lines and some normal lines).

### 4. Inventory Status Classification

For each SKU line at the order's warehouse, compute `effective_available`:

| Condition | Classification |
|---|---|
| SKU inactive AND effective < ordered | `inactive_and_shortage` |
| SKU inactive (effective ≥ ordered) | `inactive_sku` |
| effective < ordered (SKU active) | `shortage` |
| effective ≥ ordered AND (effective − ordered) < safety_stock | `low_stock` |
| effective ≥ ordered AND (effective − ordered) ≥ safety_stock | `ready` |

**shortage_skus**: SKUs where effective < ordered quantity.
**low_stock_skus**: SKUs where effective ≥ ordered but remaining after
allocation is below safety_stock.
**inactive_skus**: SKUs where product `active == false`.

All SKU lists must be **sorted ascending** and de-duplicated.

### 5. Decision Precedence (per order or per line)

1. account_blocked → **reject_hold**, hold_credit_or_fraud
2. review_required / fraud_watch / credit_watch → **manual_review**, send_account_review (or hold_credit_or_fraud for fraud)
3. inactive product → **manual_review**, escalate_product_master
4. any shortage → **backorder**, create_backorder
5. low stock (no shortage) → **delayed_release**, delay_and_monitor
6. all available → **ship_now**, release_to_pick

### 6. Shipping Quotes

```
total_weight = Σ (product.weight_lb × line.quantity)   for all lines in the order
```

Call: `GET /shipping/quote?warehouse_id=<wh>&destination_zip=<zip>&weight_lb=<weight>&speed=<speed>`

Pass the **full-precision** weight (do not round before sending). The endpoint
returns `total_cost`, `service_days`, `zone_distance`. Round `total_cost` to 2
decimals for the answer. Use the order's `shipping_speed` field as `speed`.

Compute the shipping quote for **every** order in the queue, regardless of the
dispatch decision (even blocked/reviewed orders need a quote). The summary
`total_shipping_cost_usd` is the sum of all shipping quotes.

### 7. Rounding

- Currency: round to 2 decimal places.
- Percentages: round to 1 decimal place.
- Durations: round to 2 decimal places.
- All other quantities: integers (no rounding needed).

---

## Task Family SOPs

### Family A: Expedite Queue Dispatch (e.g. wave TRAIN_EXPEDITE_A)

**Input**: a memo listing order_ids to process, an `as_of_date`.

**Output shape** (`answer_template.json`):
```
{
  "wave_id": "<wave>",
  "records": [ {order_id, inventory_status, customer_exception,
                final_decision, next_action, shortage_skus, inactive_skus,
                low_stock_skus, shipping_quote:{zone_distance, service_days,
                total_cost_usd}} ],
  "summary": {order_count, decision_counts:{ship_now, delayed_release,
              manual_review, backorder, reject_hold}, total_shipping_cost_usd,
              blocked_order_ids, manual_review_order_ids, backorder_order_ids,
              inactive_sku_order_ids}
}
```

**Procedure**:
1. For each order_id in the memo (not all orders in the wave — only the memo
   list), fetch the order detail.
2. Check customer account_status/risk_flag → customer_exception.
3. For each line, compute effective stock at the order's warehouse → classify
   shortage / low_stock / inactive.
4. Determine inventory_status (combine across lines).
5. Apply decision precedence: account → product → inventory.
6. Compute shipping quote for all orders.
7. Sort records ascending by order_id.
8. `blocked_order_ids` = orders with customer_exception == account_blocked.
   `manual_review_order_ids` = orders with final_decision == manual_review.
   `backorder_order_ids` = orders with final_decision == backorder.
   `inactive_sku_order_ids` = orders that have at least one inactive SKU.

**Key**: The memo lists specific order_ids — only process those, not the entire
wave. Keep records sorted by order_id.

---

### Family B: BOM Replenishment (e.g. kit builds at a warehouse)

**Input**: a production memo with `target_builds` (bom_id, target_build_quantity,
target_build_date) and a `planning_site` (warehouse_id).

**Output shape**:
```
{
  "task_id": "<task_id>",
  "plan_date": "YYYY-MM-DD",
  "kit_targets": [{bom_id, kit_name, warehouse_id, build_quantity, build_date}],
  "component_plan": [{sku, total_required, target_effective_available,
      timely_po_qty, transfer_qty, purchase_requisition_qty, final_action,
      coverage_po_ids, exclusion_reason}],
  "transfer_requests": [{sku, from_warehouse_id, to_warehouse_id, quantity,
      needed_by}],
  "purchase_requisitions": [{sku, supplier_id, warehouse_id, quantity,
      needed_by, unit_cost, extended_cost}],
  "excluded_components": [{sku, reason, supporting_po_ids}],
  "summary": {component_count, total_purchase_units, total_purchase_cost,
      total_transfer_units, timely_po_covered_units}
}
```

**Procedure**:
1. **Compute demand**: For each BOM, multiply each component's
   `quantity_per_kit` by the build quantity. Sum across all builds for each SKU
   → `total_required`.
2. **Earliest build date**: For each SKU, the earliest `target_build_date`
   among all builds containing it → `needed_by` for transfers and purchases.
3. **Effective stock** at the planning site → `target_effective_available`
   (raw, can be negative).
4. **Timely POs**: Filter purchase orders where `status` in (open, confirmed),
   `warehouse_id` == planning site, `sku` matches, and `eta <= needed_by`.
   `timely_po_qty` = sum of all eligible PO quantities.
   `coverage_po_ids` = sorted list of eligible PO IDs.
5. **Gap calculation**:
   ```
   total_available = target_effective_available + timely_po_qty
   gap = max(0, total_required - total_available)
   ```
6. **Exclusion checks** (if no gap to fill):
   - If `effective >= total_required`:
     - If `effective >= product.overstock_threshold` → `target_overstock`,
       `overstock_excluded`
     - Else → `stocked_no_gap`, `no_action_stocked`
   - If `effective < total_required` but `total_available >= total_required`
     → `timely_po_covers_gap`, `timely_po_covered`
7. **Transfer** (if gap > 0): For each other warehouse, compute spare effective
   stock (same formula). Sort by spare descending. Transfer from one warehouse
   at a time (largest spare first), taking `min(spare, remaining_gap)`.
8. **Purchase requisition**: Remaining gap after transfers.
   `unit_cost` from product master, `extended_cost = unit_cost × quantity`.
   `supplier_id` from product master.
9. **final_action**:
   - `overstock_excluded` / `no_action_stocked` / `timely_po_covered`: excluded
   - `transfer_only`: gap fully covered by transfers
   - `purchase_required`: purchase needed (with or without transfers)
10. **Summary**:
    - `total_purchase_units` = sum of purchase_requisition_qty
    - `total_purchase_cost` = sum of extended_cost, 2 decimals
    - `total_transfer_units` = sum of transfer quantities
    - `timely_po_covered_units` = for each excluded `timely_po_covers_gap`
      component, `min(timely_po_qty, max(0, total_required - effective))`.
      **NOT** the raw total PO quantity — use the gap-coverage amount.

**Key learnings**:
- Effective stock stays raw (negative allowed). Capping at zero drops the score.
- `timely_po_covered_units` = the gap the timely PO actually fills, not the
  total PO quantity. For a component needing 90 with effective −16 and a 335-unit
  PO, the covered amount is 106 (90 − (−16)), not 335.
- `kit_targets` uses the **memo's** `target_build_date`, not the BOM record's
  `target_date`.
- Sort `component_plan` by sku. Sort `transfer_requests` by sku, then quantity
  descending, then from_warehouse_id ascending. Sort `purchase_requisitions`
  and `excluded_components` by sku.

---

### Family C: Supplier Incident Scorecard (e.g. Q1 review)

**Input**: a scorecard request with incident date filter (field, start, end,
inclusive), analysis_date, duration rule, percentage rule, recommendation
policy.

**Output shape**:
```
{
  "analysis_window": {start_date, end_date, analysis_date},
  "summary": {filtered_incident_count, supplier_count,
      total_resolution_cost, overall_rma_count, overall_work_order_count},
  "supplier_scorecard": [{supplier_id, supplier_name, incident_count,
      incident_percentage, total_resolution_cost, avg_duration_days,
      rma_count, work_order_count, open_incident_count, severe_incident_count,
      recommendation_code}],
  "top_escalation_suppliers": [supplier_id, ...],
  "highest_cost_supplier_id": "string",
  "highest_share_supplier_id": "string"
}
```

**Procedure**:
1. **Filter incidents** on `open_date` (per the request's field) within
   `[start_date, end_date]` **inclusive** (string comparison works for
   YYYY-MM-DD).
2. **Overall summary**:
   - `filtered_incident_count` = count of filtered incidents
   - `supplier_count` = distinct suppliers with ≥1 filtered incident
   - `total_resolution_cost` = sum of resolution_cost, 2 decimals
   - `overall_rma_count` / `overall_work_order_count` = counts by type
3. **Per-supplier rows** (sort by supplier_id ascending):
   - `incident_count` = count of filtered incidents for supplier
   - `incident_percentage` = incident_count / filtered_incident_count × 100,
     1 decimal
   - `total_resolution_cost` = sum, 2 decimals
   - `avg_duration_days`: for each incident, duration = (close_date −
     open_date).days if closed, else (analysis_date − open_date).days. Average
     across the supplier's incidents, 2 decimals.
   - `rma_count` / `work_order_count` = by type
   - `open_incident_count` = status == open
   - `severe_incident_count` = severity in {high, critical}
4. **Recommendation code** (precedence: ESCALATE_SUPPLIER > PROCESS_REVIEW >
   WATCHLIST > MONITOR):
   - **ESCALATE_SUPPLIER**: supplier `quality_status == quality_hold` AND
     `incident_count >= 3`, OR has any critical RMA (incident_type == RMA and
     severity == critical), OR (rma_count >= 3 AND total_resolution_cost >=
     15000.00)
   - **PROCESS_REVIEW**: work_order_count >= 3 AND work_order_count >
     rma_count
   - **WATCHLIST**: quality_status in {watch, quality_hold}, OR
     incident_count >= 4, OR total_resolution_cost >= 12000.00, OR
     severe_incident_count >= 2
   - **MONITOR**: none of the above
5. **top_escalation_suppliers**: supplier_ids with ESCALATE_SUPPLIER, ordered by
   incident_count descending, then total_resolution_cost descending, then
   supplier_id ascending.
6. **highest_cost_supplier_id**: supplier with max total_resolution_cost
   (ties broken by supplier_id ascending).
7. **highest_share_supplier_id**: supplier with max incident_count
   (ties broken by supplier_id ascending).

**Key**: The filter uses `open_date`, not `close_date`. Duration for open
incidents uses the `analysis_date`, not today's date. The percentage is a
percentage number (e.g. 23.7), not a fraction (0.237). Severe = {high,
critical}.

---

### Family D: Allocation / Transfer Decision (e.g. wave TRAIN_TRANSFER_B)

**Input**: a wave ID, order data, customer/product/inventory masters, an
allocation memo.

**Output shape**:
```
{
  "wave_id": "<wave>",
  "line_actions": [{order_id, line_id, sku, requested_warehouse,
      requested_effective_available, action, ship_quantity, transfer_from,
      transfer_quantity, backorder_quantity, primary_reason}],
  "transfer_requests": [{order_id, line_id, sku, from_warehouse,
      to_warehouse, quantity}],
  "blocked_orders": [order_id, ...],
  "order_rollup": [{order_id, outcome}],
  "summary": {total_orders, total_lines, ship_lines, transfer_lines,
      backorder_lines, manual_review_lines, blocked_orders, transfer_units,
      backorder_units}
}
```

**Procedure**:
1. For each order in the wave, determine the order-level exception:
   - account_blocked → all lines `manual_review`, primary_reason =
     `account_blocked`
   - fraud_watch → all lines `manual_review`, primary_reason = `fraud_watch`
   - review_required → all lines `manual_review`, primary_reason =
     `account_review_required`
2. For orders with no account exception, check each line:
   - If product `active == false` → `manual_review`, reason `inactive_product`
   - Else compute `effective_available` at the requested warehouse:
     - If effective ≥ quantity → `ship`, ship_quantity = quantity
     - If effective < quantity:
       - `usable = max(0, effective)` (cannot ship negative stock)
       - `remaining = quantity − usable`
       - Check other warehouses: if any has `effective >= remaining`
         (spare effective with safety stock preserved), transfer from the
         warehouse with the **largest** effective
         → `transfer`, ship_quantity = usable, transfer_from = that warehouse,
           transfer_quantity = remaining
       - If no single warehouse can cover the full remaining → `backorder`,
         ship_quantity = 0, backorder_quantity = quantity,
         primary_reason = `insufficient_effective_stock`
3. `requested_effective_available` = raw effective stock (can be negative).
4. **blocked_orders**: ALL orders stopped at account or customer-risk level
   (account_blocked, review_required, fraud_watch). NOT inactive-product-only
   orders. Sort ascending.
5. **order_rollup** outcomes:
   - All lines ship → `ready_to_ship`
   - Ship + transfer only (no backorder, no manual_review) → `needs_transfer`
   - Any backorder (no manual_review) → `has_backorder`
   - All lines manual_review → `manual_review`
   - manual_review mixed with other actions, or other mixed combinations →
     `mixed_actions`
6. **Summary**: counts and unit totals. `transfer_units` = sum of
   transfer_quantity, `backorder_units` = sum of backorder_quantity.

**Key**: For backorder lines, ship_quantity = 0 and backorder_quantity = full
quantity (the line cannot be partially shipped). For transfer lines, the full
uncovered portion must be coverable by a single warehouse — if no single
warehouse can cover, it's a backorder. Transfer source = warehouse with the
largest effective stock that can cover. Sort line_actions by order_id then
line_id. Sort transfer_requests by order_id then line_id.

---

### Family E: Procurement Quality-Hold Review

**Input**: a memo with `analysis_window` (start, end), `decision_choices`
(freeze_new_replenishment, buyer_review_required, monitor_only),
`target_supplier_ids`.

**Output shape**:
```
{
  "analysis_window": {start, end},
  "supplier_decisions": [{supplier_id, supplier_name, quality_status,
      recent_incident_count, recent_rma_count, severe_or_critical_count,
      open_incident_count, affected_skus, sample_incident_ids, decision,
      held_po_ids}],
  "held_po_ids": [po_id, ...],
  "release_supplier_ids": [supplier_id, ...],
  "summary": {suppliers_reviewed, freeze_count, buyer_review_count,
      monitor_count, held_po_count, total_recent_incidents}
}
```

**Procedure**:
1. **Filter incidents** for each target supplier: `open_date` within
   `[start, end]` inclusive.
2. Per supplier, compute:
   - `recent_incident_count` = filtered incident count
   - `recent_rma_count` = RMA-type count
   - `severe_or_critical_count` = severity in {high, critical}
   - `open_incident_count` = status == open
   - `affected_skus` = sorted unique SKUs from filtered incidents
   - `sample_incident_ids` = sorted incident IDs, capped at 5
3. **Decision logic** (best-effort thresholds from training):
   - **freeze_new_replenishment**: quality_hold AND recent_incident_count >= 3,
     OR any critical RMA, OR (rma_count >= 3 AND total_resolution_cost >=
     15000)
   - **buyer_review_required**: quality_hold AND incidents < 3, OR
     (watch AND (incidents >= 4 OR total_resolution_cost >= 15000 OR any
     critical incident))
   - **monitor_only**: none of the above
4. **held_po_ids** per supplier: all open/confirmed purchase order IDs for
   that supplier (regardless of decision — the template says "open or
   confirmed purchase order ids" without a held qualifier).
5. **Top-level held_po_ids**: union of held_po_ids from suppliers whose
   decision is freeze or buyer_review only (sorted, unique).
6. **release_supplier_ids**: suppliers with monitor_only (sorted).
7. **Summary** counts.

**Key uncertainty**: The exact decision thresholds for buyer_review vs
monitor_only were not fully resolved in training (all rounds scored 0.556).
The most likely split observed: quality_hold + significant incidents → freeze;
watch + moderate-to-high risk → buyer_review; watch + minor risk → monitor.
Treat `recent_incident_count >= 4` or `total_resolution_cost >= 15000` or
any critical incident as the buyer_review trigger for watch suppliers. Per-
supplier `held_po_ids` should list all open/confirmed POs, not just held ones.

---

## Common Misjudgments and Exclusion Rules

1. **Don't cap effective stock at zero.** Negative effective stock is valid
   and must be used in gap calculations. Capping dropped the BOM score from
   0.78 to 0.50.

2. **`timely_po_covered_units` is the gap covered, not total PO qty.** If a
   component needs 90, has effective −16, and a timely PO of 335 units, the
   covered amount is 106 (the shortfall), not 335.

3. **Only process orders listed in the memo, not the entire wave.** The
   `/orders?wave=` endpoint returns all orders in the wave, but the task memo
   specifies which order_ids to process.

4. **blocked_orders includes ALL account/risk-stopped orders** (blocked,
   review_required, fraud_watch), not just account_blocked. Inactive-product
   orders are NOT in blocked_orders (that's a line-level product issue).

5. **For allocation transfers, one warehouse must cover the FULL uncovered
   quantity.** If no single warehouse can cover the entire remaining amount,
   the line goes to backorder, not a multi-warehouse transfer.

6. **For allocation backorder lines, ship_quantity = 0.** The entire quantity
   is backordered — no partial ship.

7. **Incident filter uses `open_date`, not `close_date`.** Duration for open
   incidents uses `analysis_date`, not today. Percentages are percentage
   numbers (23.7), not fractions (0.237).

8. **Recommendation precedence is strict.** ESCALATE > PROCESS_REVIEW >
   WATCHLIST > MONITOR. A supplier meeting WATCHLIST criteria but also
   PROCESS_REVIEW criteria gets PROCESS_REVIEW. A supplier on quality_hold
   with >= 3 incidents gets ESCALATE even if it also meets PROCESS_REVIEW.

9. **Kit build dates come from the production memo**, not the BOM record's
   `target_date`. Use the memo's `target_build_date` for `needed_by` and
   `build_date` fields.

10. **Shipping weight uses full precision.** Don't round the weight before
    passing to `/shipping/quote`. Round only the returned `total_cost` to 2
    decimals.

11. **Transfer source selection = largest effective first.** Among warehouses
    that can cover the uncovered quantity, choose the one with the largest
    effective stock.

12. **Overstock exclusion**: `target_overstock` when effective >= total_required
    AND effective >= product.overstock_threshold. If effective >= total_required
    but below the threshold, it's `stocked_no_gap`.

---

## Reusable SOP (applies to unseen test tasks)

1. **Read the prompt and answer template carefully.** The template defines
   exact field names, types, ordering, and enum values. Match them precisely.
2. **Download all data collections** up front via the API endpoints listed above.
3. **Compute effective stock** = on_hand − reserved − quarantined − safety_stock
   (safety_stock from product master). Keep raw (negative allowed).
4. **Apply account/risk overrides before inventory** for any dispatch,
   allocation, or expedite task.
5. **Check product active status per line** before inventory for allocation
   tasks.
6. **Filter incidents on open_date inclusive** within the analysis window.
7. **Compute durations** using close_date for closed, analysis_date for open.
8. **Apply the recommendation/decision precedence** strictly
   (ESCALATE > PROCESS_REVIEW > WATCHLIST > MONITOR for scorecards;
   account > product > inventory for dispatch/allocation).
9. **Round correctly**: currency 2 decimals, percentages 1 decimal, durations 2
   decimals.
10. **Sort all lists** as specified in the template (by order_id, line_id, sku,
    supplier_id, etc.).
11. **Verify output shape** against the template before submitting: all required
    top-level keys, all item required keys, all enum values valid, all
    orderings correct.
12. **Use the remote API** (`<remote-env-url>`) with
    `curl -sS --max-time 30` for every call.
