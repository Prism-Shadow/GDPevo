# Northwind Components ERP Skill — Task Group 007

## Environment & API Basics
- **Base URL**: `http://34.46.77.124:8007` (use only this; ignore any localhost references in task text).
- **Allowed endpoints** (GET unless noted):
  - `/`, `/health`
  - `/products`, `/products/<sku>`
  - `/customers`, `/customers/<customer_id>`
  - `/warehouses`
  - `/inventory?warehouse_id=&sku=`
  - `/purchase_orders?supplier_id=&sku=&status=`
  - `/orders?wave=&required_date=&customer_id=`, `/orders/<order_id>`
  - `/shipping/quote?warehouse_id=&destination_zip=&weight_lb=&speed=`
  - `/incidents?start=&end=&supplier_id=&sku=&incident_type=&status=`
  - `/suppliers`
  - `/boms`, `/boms/<bom_id>`
- **Shipping quote**: returns `total_cost` (not `total_cost_usd`). Map it to `total_cost_usd` in output.
- **Weight calculation**: use `products[sku]['weight_lb'] * quantity` per line, sum for order total.
- Do not invent endpoints (e.g., no `/shipping`, no POST APIs).

---

## 1. Expedite Queue Decisions (train_001 pattern)

### Workflow
1. Read `expedite_queue_memo.json` for the order id list and wave id.
2. Fetch each order (`/orders/<id>`), its customer (`/customers/<id>`), and each line's inventory at the order's warehouse (`/inventory?warehouse_id=&sku=`).
3. Fetch all products to get `active`, `safety_stock`, `weight_lb`.

### Field Conventions
- **customer_exception** (enum): controlled by `account_status` and `risk_flag`:
  - `blocked` → `account_blocked`
  - `fraud_watch` → `fraud_watch`
  - `credit_watch` → `credit_watch`
  - `review_required` → `review_required`
  - otherwise → `none`
- **inventory_status** (enum):
  - `inactive_and_shortage` — at least one inactive SKU AND at least one shortage
  - `inactive_sku` — at least one inactive SKU, no shortage
  - `shortage` — at least one shortage, no inactive SKU
  - `low_stock` — no shortage/inactive, but at least one line where effective < qty + safety_stock
  - `ready` — none of the above
- **effective_available** = `on_hand - reserved - quarantined` (never negative).
- **shortage_skus**: effective < requested quantity.
- **low_stock_skus**: effective < qty + safety_stock (but not shortage).
- **inactive_skus**: `active == false` in product master.
- All SKU lists sorted ascending.

### Decision Priority
1. Customer-level blocks (`account_blocked`, `fraud_watch`, `credit_watch`) → `reject_hold` / `hold_credit_or_fraud`
2. `review_required` → `manual_review` / `send_account_review`
3. Inventory problems:
   - `inactive_and_shortage` or `inactive_sku` → `backorder` / `create_backorder` or `escalate_product_master`
   - `shortage` → `backorder` / `create_backorder`
   - `low_stock` → `delayed_release` / `delay_and_monitor`
   - `ready` → `ship_now` / `release_to_pick`

### Summary Rules
- `blocked_order_ids`: `final_decision == reject_hold`, sorted ascending.
- `manual_review_order_ids`: `final_decision == manual_review`, sorted ascending.
- `backorder_order_ids`: `final_decision == backorder`, sorted ascending.
- `inactive_sku_order_ids`: `inventory_status` in (`inactive_sku`, `inactive_and_shortage`), sorted ascending.
- `total_shipping_cost_usd`: sum of quotes, rounded to 2 decimals.

### Pitfalls
- Do not use `status` field on products; use `active` boolean.
- Shipping quote field is `total_cost`, not `total_cost_usd`.
- `records` must be sorted by `order_id` ascending.

---

## 2. Kit Build Replenishment (train_002 pattern)

### Workflow
1. Read `production_memo.json` for BOM ids, build quantities, build dates, target warehouse.
2. Fetch BOMs (`/boms/<id>`), products, inventory, and purchase_orders.
3. Compute `total_required = sum(quantity_per_kit * build_quantity)` across all builds per SKU.

### Field Conventions
- **target_effective_available** = `max(0, on_hand - reserved - quarantined)` at target warehouse.
- **timely_po_qty**: sum of `open` or `confirmed` POs for that SKU at target warehouse with `eta <= needed_by` (latest build date).
- **coverage_po_ids**: sorted PO ids that contribute to timely_po_qty.
- **transfer_qty**: sum of feasible transfers from other warehouses after POs are applied.
  - For each source warehouse, `available_for_transfer = max(0, src_effective - safety_stock)`.
  - Only transfer what is needed to close the gap.
- **purchase_requisition_qty**: remaining gap after stock + POs + transfers.

### Final Action & Exclusion Logic
- `no_action_stocked` / `stocked_no_gap`: target effective >= total_required.
- `timely_po_covered` / `timely_po_covers_gap`: gap is fully covered by timely POs (after stock).
- `transfer_only` / `none`: gap fully covered by inter-warehouse transfers.
- `purchase_required` / `none`: still a gap after all sources.
- `overstock_excluded` / `target_overstock`: ONLY when target effective > overstock_threshold AND there is no gap (target already covers requirement). If there is a gap, do NOT overstock-exclude; still need replenishment.

### Sorting
- `kit_targets`: by `bom_id` ascending.
- `component_plan`: by `sku` ascending.
- `transfer_requests`: by `sku` asc, then `quantity` desc, then `from_warehouse_id` asc.
- `purchase_requisitions`: by `sku` ascending.
- `excluded_components`: by `sku` ascending.

### Pitfalls
- Do not exclude overstock items that still have a coverage gap.
- `timely_po_qty` is from POs at the **same target warehouse**.
- Currency fields (`unit_cost`, `extended_cost`) rounded to 2 decimals.

---

## 3. Supplier Incident Scorecard (train_003 pattern)

### Workflow
1. Read `q1_scorecard_request.json` for date range, analysis_date, recommendation policy, and severe severity values.
2. Fetch `/incidents?start=&end=` and `/suppliers`.
3. Filter incidents by `open_date` in range (inclusive).

### Field Conventions
- **incident_percentage** = `incident_count / filtered_incident_count * 100`, rounded to 1 decimal.
- **avg_duration_days**:
  - Closed incidents: calendar days from `open_date` to `close_date`.
  - Open incidents: calendar days from `open_date` to `analysis_date`.
  - Average of all durations, rounded to 2 decimals.
- **rma_count**, **work_order_count**: counts within the filtered population per supplier.
- **open_incident_count**: incidents with `status == 'open'`.
- **severe_incident_count**: incidents with `severity` in the configured severe list (e.g., `high`, `critical`).

### Recommendation Policy (precedence order)
1. `ESCALATE_SUPPLIER`:
   - supplier on `quality_hold` with >= 3 filtered incidents, OR
   - any critical RMA, OR
   - >= 3 RMAs AND total filtered resolution cost >= 15000.00
2. `PROCESS_REVIEW`:
   - WORK_ORDER incidents >= 3 AND exceed RMA incidents
3. `WATCHLIST`:
   - quality_status is `watch` or `quality_hold`, OR
   - filtered incident_count >= 4, OR
   - total filtered resolution cost >= 12000.00, OR
   - severe_incident_count >= 2
4. `MONITOR`: default when none of the above apply.

### Sorting
- `supplier_scorecard`: by `supplier_id` ascending.
- `top_escalation_suppliers`: by `incident_count` desc, then `total_resolution_cost` desc, then `supplier_id` asc.
- `highest_cost_supplier_id`: supplier with max `total_resolution_cost`.
- `highest_share_supplier_id`: supplier with max `incident_percentage`.

### Pitfalls
- Use `open_date` for filtering, not `close_date`.
- Percentage denominator is the **total filtered incident population**, not per-supplier.
- Currency and duration precision must match template exactly (2 decimals).

---

## 4. Mixed-Warehouse Allocation (train_004 pattern)

### Workflow
1. Fetch all orders for the wave (`/orders?wave=`).
2. For each line, compute effective available at requested warehouse.
3. Check customer account status and risk flags; check product active status.

### Field Conventions
- **requested_effective_available** = `max(0, on_hand - reserved - quarantined)` at requested warehouse.
- **action** logic:
  - If customer `account_status == 'blocked'` OR `risk_flag == 'fraud_watch'` → `manual_review` (order-level block).
  - If `account_status == 'review_required'` → `manual_review` (line-level).
  - If product `active == false` → `manual_review`.
  - If `requested_effective_available >= quantity` → `ship`.
  - Else try transfer from another warehouse (effective >= needed, no safety-stock subtraction for allocation decisions unless memo explicitly says so).
    - If transfer found → `transfer`, `ship_quantity` = requested effective, `transfer_quantity` = needed.
    - Else → `backorder`, `ship_quantity` = requested effective, `backorder_quantity` = needed.
- **blocked_orders**: list of `order_id` where `account_status == 'blocked'` (NOT fraud_watch). Sorted ascending.
- **primary_reason**:
  - `account_blocked` for blocked orders
  - `fraud_watch` for fraud_watch orders
  - `account_review_required` for review_required
  - `inactive_product` for inactive SKUs
  - `insufficient_effective_stock` for transfer/backorder lines
  - `none` for ship lines

### Order Rollup Outcomes
- `ready_to_ship`: all lines ship.
- `needs_transfer`: at least one transfer, no backorder/manual_review.
- `has_backorder`: at least one backorder, no transfer/manual_review.
- `manual_review`: any manual_review line.
- `mixed_actions`: otherwise (mix of ship/transfer/backorder).

### Sorting
- `line_actions`: by `order_id` asc, then `line_id` asc.
- `transfer_requests`: by `order_id` asc, then `line_id` asc.
- `blocked_orders`: ascending.
- `order_rollup`: by `order_id` ascending.

### Pitfalls
- `blocked_orders` is ONLY for `account_status == blocked`, not fraud_watch.
- For transfer lines, `ship_quantity` should be the usable quantity at the requested warehouse (not 0).
- Do not subtract safety stock from effective available unless the memo explicitly instructs it.

---

## 5. Quality Hold Review (train_005 pattern)

### Workflow
1. Read `quality_hold_review_memo.json` for target supplier ids and analysis window.
2. Fetch incidents in window and all purchase_orders.

### Field Conventions
- **recent_incident_count**: incidents in window for that supplier.
- **recent_rma_count**: RMA incidents in window.
- **severe_or_critical_count**: incidents with severity `high` or `critical`.
- **open_incident_count**: incidents with `status == 'open'`.
- **affected_skus**: sorted unique SKUs from incidents.
- **sample_incident_ids**: sorted incident ids, max 5.
- **held_po_ids**: sorted open/confirmed PO ids for that supplier.

### Decision Logic
- `freeze_new_replenishment`: use when supplier quality_status is `quality_hold` OR there are severe/critical incidents in window.
- `buyer_review_required`: use when there are recent incidents but no freeze triggers.
- `monitor_only`: use when no recent incidents and quality_status is `approved`.
- Adjust based on task-specific memo policy if provided.

### Summary
- `suppliers_reviewed`: count of target suppliers.
- `freeze_count`, `buyer_review_count`, `monitor_count`: counts by decision.
- `held_po_count`: total unique held PO ids across all suppliers.
- `total_recent_incidents`: sum of recent_incident_count across reviewed suppliers.

### Sorting
- `supplier_decisions`: by `supplier_id` ascending.
- `held_po_ids`: sorted unique list.
- `release_supplier_ids`: sorted list of monitor_only suppliers.

### Pitfalls
- Ensure `held_po_ids` are unique across the entire output.
- Only include POs with status `open` or `confirmed`.
- Max 5 sample incident ids per supplier.

---

## General JSON Output Rules
- Match the exact keys and nesting in `answer_template.json`.
- Sort all lists as specified in each template.
- Currency: round to exactly 2 decimal places.
- Percentages: round to exactly 1 decimal place.
- Durations: round to exactly 2 decimal places.
- Use integers for counts and quantities.
- Do not include narrative text outside the JSON object.

---

## Common API Pitfalls
- Always use `urllib.request` or equivalent; `requests` may not be installed.
- URL-encode query parameters if they contain special characters.
- Handle missing inventory records as zero effective available.
- Product `active` is a boolean; do not rely on a `status` string.
