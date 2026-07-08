# Northwind ERP Decision-Workflow Skill (task_group_007)

## 1. Environment & API Basics
- Start the shared ERP API from `task_group/task_group_007/env` with `bash setup.sh start`, or run `python server.py --host 127.0.0.1 --port 8007`.
- Base URL: `http://127.0.0.1:8007`.
- Use only the public API endpoints; do not inspect env files directly when solving.
- Read `environment_access.md` for any remote ERP API access details.

## 2. General JSON Output Discipline
- Return **only** a single JSON object matching the provided `answer_template.json`.
- No markdown, no narrative text outside the JSON.
- All currency values → **round to exactly 2 decimal places**.
- All percentages → follow template precision (commonly 1 decimal place).
- All durations → follow template precision (commonly 2 decimal places).
- Sort all lists as specified in the template; default to ascending unless otherwise stated.
- Use integer types for counts/quantities; never float.

## 3. Controlled Vocabularies (Exact Strings)
These enums appear across tasks. Use only the allowed literal values.

### Inventory Status
- `ready`, `low_stock`, `shortage`, `inactive_sku`, `inactive_and_shortage`

### Customer Exception
- `none`, `review_required`, `account_blocked`, `fraud_watch`, `credit_watch`

### Final Decision (Expedite / Allocation)
- `ship_now`, `delayed_release`, `manual_review`, `backorder`, `reject_hold`

### Next Action (Expedite)
- `release_to_pick`, `delay_and_monitor`, `send_account_review`, `create_backorder`, `hold_credit_or_fraud`, `escalate_product_master`

### Line Action (Allocation)
- `ship`, `transfer`, `backorder`, `manual_review`

### Primary Reason (Allocation)
- `none`, `account_blocked`, `account_review_required`, `fraud_watch`, `inactive_product`, `insufficient_effective_stock`

### Order Rollup Outcome (Allocation)
- `ready_to_ship`, `needs_transfer`, `has_backorder`, `manual_review`, `mixed_actions`

### Component Final Action (Replenishment)
- `no_action_stocked`, `transfer_only`, `purchase_required`, `timely_po_covered`, `overstock_excluded`

### Exclusion Reason (Replenishment)
- `none`, `target_overstock`, `timely_po_covers_gap`, `stocked_no_gap`

### Supplier Recommendation
- `ESCALATE_SUPPLIER`, `PROCESS_REVIEW`, `WATCHLIST`, `MONITOR`

### Supplier Quality Status
- `approved`, `watch`, `quality_hold`

### Procurement Decision
- `freeze_new_replenishment`, `buyer_review_required`, `monitor_only`

## 4. Data Fetching Patterns
For every task, fetch fresh live records rather than relying on cached snapshots.

### Common Endpoints (typical, verify with API docs)
- `/orders` or `/orders/{id}` — order headers and lines
- `/customers` or `/customers/{id}` — account status, risk flags
- `/products` or `/products/{id}` — product master, active/inactive
- `/inventory` or `/inventory/{warehouse}/{sku}` — on-hand, reserved, quarantined, buffer
- `/warehouses` — warehouse list and attributes
- `/shipping_quotes` or `/shipping/quotes` — zone distance, service days, cost
- `/boms` or `/boms/{id}` — BOM components and quantities
- `/purchase_orders` — open/confirmed POs with quantities, due dates, warehouse
- `/suppliers` or `/suppliers/{id}` — quality status, name
- `/incidents` — incident records with severity, type, dates, resolution cost

### Effective Available Inventory
- **Do not** treat total on-hand as freely available.
- Subtract reserved, quarantined, and normal operating buffer quantities.
- Use the API’s `effective_available` if provided; otherwise compute:
  `effective_available = on_hand - reserved - quarantined - buffer`.

## 5. Task-Specific Workflow Rules

### 5.1 Expedite Queue (wave decision)
1. For each `order_id` in the memo:
   - Fetch order lines, customer record, product master, inventory, and shipping quote.
2. Classify `inventory_status`:
   - If any line SKU is inactive → include `inactive_sku` or `inactive_and_shortage`.
   - If effective available < line quantity → `shortage` (or combined with inactive).
   - If effective available is low but covers line → `low_stock`.
   - Else `ready`.
3. Classify `customer_exception` from customer record flags (`review_required`, `account_blocked`, `fraud_watch`, `credit_watch`).
4. Determine `final_decision` and `next_action`:
   - Account blocked / fraud watch / credit watch → `reject_hold` + `hold_credit_or_fraud`.
   - Review required → `manual_review` + `send_account_review`.
   - Inactive SKU risk → `manual_review` + `escalate_product_master` (or combined with account review if both apply).
   - Shortage only → `backorder` + `create_backorder`.
   - Ready + no exception → `ship_now` + `release_to_pick`.
5. Populate SKU exception lists (`shortage_skus`, `inactive_skus`, `low_stock_skus`) sorted ascending.
6. Fill `shipping_quote` with `zone_distance`, `service_days`, `total_cost_usd` (2 decimals).
7. Build `summary`:
   - `order_count`, `decision_counts` (all keys present, integer), `total_shipping_cost_usd` (sum of quotes, 2 decimals).
   - `blocked_order_ids` → orders with `reject_hold`.
   - `manual_review_order_ids` → `manual_review`.
   - `backorder_order_ids` → `backorder`.
   - `inactive_sku_order_ids` → any order with at least one inactive SKU.
   - All ID lists sorted ascending.

### 5.2 Kit Build Replenishment (BOM-driven)
1. Read `production_memo.json` for target builds (BOM IDs, quantities, build dates).
2. For each BOM, fetch components and per-unit quantities.
3. Compute `total_required` = Σ(build_quantity × qty_per_unit) across all builds using that SKU.
4. Fetch current `effective_available` at the target warehouse (`target_effective_available`).
5. Fetch open/confirmed purchase orders for the same warehouse that arrive before the build date → `timely_po_qty`.
6. Compute gap = `total_required - target_effective_available - timely_po_qty`.
7. If gap > 0, evaluate inter-warehouse transfers:
   - For each other warehouse, compute transferable = `effective_available - buffer` (or API-provided transferable quantity).
   - Aggregate transfers; prefer warehouses with largest surplus.
   - `transfer_qty` = min(gap, total transferable across sources).
   - Create `transfer_requests` sorted by `sku` asc, then `quantity` desc, then `from_warehouse_id` asc.
8. Remaining gap after transfers → `purchase_requisition_qty`.
   - Use supplier from product master or preferred supplier endpoint.
   - `extended_cost` = `quantity × unit_cost` (2 decimals).
9. Determine `final_action`:
   - `target_effective_available` ≥ `total_required` and no gap → `no_action_stocked` or `overstock_excluded` if explicitly flagged.
   - `timely_po_qty` covers gap → `timely_po_covered`.
   - `transfer_qty` > 0 and purchase_requisition_qty == 0 → `transfer_only`.
   - `purchase_requisition_qty` > 0 → `purchase_required`.
10. `excluded_components` list:
    - `target_overstock` when `target_effective_available` already exceeds requirement and no action needed.
    - `timely_po_covers_gap` when PO covers full gap.
    - `stocked_no_gap` when no gap exists.
    - Sort by `sku` ascending.
11. Summary:
    - `component_count` = number of distinct SKUs in `component_plan`.
    - `total_purchase_units` = sum of `purchase_requisition_qty`.
    - `total_purchase_cost` = sum of `extended_cost` (2 decimals).
    - `total_transfer_units` = sum of `transfer_qty`.
    - `timely_po_covered_units` = sum of timely PO quantities that caused exclusion or coverage.

### 5.3 Supplier Incident Scorecard
1. Filter incidents by `open_date` within the requested window (inclusive).
2. Group by `supplier_id`.
3. For each supplier row:
   - `incident_count` = filtered count.
   - `incident_percentage` = (`incident_count` / total filtered incidents) × 100, rounded to 1 decimal.
   - `total_resolution_cost` = sum of `resolution_cost` for filtered incidents, 2 decimals.
   - `avg_duration_days`:
     - Closed incidents: calendar days from `open_date` to `close_date`.
     - Open incidents: calendar days from `open_date` to `analysis_date`.
     - Average across all filtered incidents, 2 decimals.
   - `rma_count` / `work_order_count` = counts by incident type.
   - `open_incident_count` = incidents without `close_date`.
   - `severe_incident_count` = incidents where `severity` is in `severe_severity_values` (e.g., `high`, `critical`).
4. Apply recommendation policy in strict precedence order:
   1. **ESCALATE_SUPPLIER** — supplier on `quality_hold` with ≥3 filtered incidents, OR any critical RMA, OR ≥3 RMAs and total resolution cost ≥ 15000.00.
   2. **PROCESS_REVIEW** — `work_order_count` ≥ 3 **and** `work_order_count` > `rma_count`.
   3. **WATCHLIST** — `quality_status` is `watch` or `quality_hold`, OR `incident_count` ≥ 4, OR total resolution cost ≥ 12000.00, OR `severe_incident_count` ≥ 2.
   4. **MONITOR** — default.
5. `top_escalation_suppliers` = all suppliers with `ESCALATE_SUPPLIER`, sorted by `incident_count` desc, then `total_resolution_cost` desc, then `supplier_id` asc.
6. `highest_cost_supplier_id` = supplier with max `total_resolution_cost` (break ties by `supplier_id` asc if needed).
7. `highest_share_supplier_id` = supplier with max `incident_percentage` (break ties similarly).

### 5.4 Mixed-Warehouse Allocation (Transfer Review)
1. Fetch all order lines for the wave.
2. For each line, fetch:
   - Order header (customer account status, risk flags).
   - Product master (active/inactive).
   - `requested_effective_available` at the line’s requested warehouse.
3. Determine `action` per line:
   - **Account blocked / fraud watch / credit watch at order level** → all lines `manual_review`, `primary_reason` = `account_blocked` / `fraud_watch`.
   - **Account review required** → all lines `manual_review`, `primary_reason` = `account_review_required`.
   - **Inactive product** → `manual_review`, `primary_reason` = `inactive_product`.
   - **Effective stock covers full quantity** → `ship`, `ship_quantity` = line quantity.
   - **Effective stock covers partial quantity** → `transfer`:
     - `ship_quantity` = usable requested-warehouse quantity.
     - Find one source warehouse where effective available (minus buffer) can cover the uncovered qty.
     - `transfer_from` = that warehouse; `transfer_quantity` = uncovered qty.
   - **No warehouse can cover uncovered qty** → `backorder`, `backorder_quantity` = uncovered qty.
4. `blocked_orders` = orders where the **entire order** is stopped at account/risk level (not line-only product reviews). Sort ascending.
5. `order_rollup`:
   - `ready_to_ship` = all lines are `ship`.
   - `needs_transfer` = at least one `transfer`, rest `ship`.
   - `has_backorder` = at least one `backorder`.
   - `manual_review` = all lines `manual_review`.
   - `mixed_actions` = anything else.
   - Sort by `order_id` ascending.
6. `transfer_requests` list:
   - One entry per `transfer` line with `from_warehouse`, `to_warehouse`, `quantity`.
   - Sort by `order_id` asc, then `line_id` asc.
7. `summary`:
   - Counts for `total_orders`, `total_lines`, `ship_lines`, `transfer_lines`, `backorder_lines`, `manual_review_lines`, `blocked_orders`.
   - `transfer_units` = sum of `transfer_quantity`.
   - `backorder_units` = sum of `backorder_quantity`.

### 5.5 Procurement Quality Hold Review
1. For each target `supplier_id`:
   - Fetch supplier record (name, `quality_status`).
   - Filter incidents in the analysis window (`start`–`end` inclusive on `open_date` or as specified).
   - Count `recent_incident_count`, `recent_rma_count`, `severe_or_critical_count`, `open_incident_count`.
   - Collect `affected_skus` (unique, sorted ascending).
   - Collect up to 5 `sample_incident_ids` (sorted ascending).
   - Fetch open or confirmed purchase orders for the supplier → `held_po_ids` (sorted ascending).
2. Determine `decision`:
   - `freeze_new_replenishment` — high risk (e.g., `quality_hold` with multiple incidents or severe/critical issues).
   - `buyer_review_required` — moderate risk (e.g., `watch` status with incidents).
   - `monitor_only` — low risk, no POs held.
   - Use task-specific policy from memo if provided; otherwise apply the precedence above.
3. Build top-level lists:
   - `held_po_ids` = sorted unique union of all supplier `held_po_ids`.
   - `release_supplier_ids` = suppliers with `monitor_only`, sorted ascending.
4. `summary`:
   - `suppliers_reviewed`, `freeze_count`, `buyer_review_count`, `monitor_count`, `held_po_count`, `total_recent_incidents`.

## 6. Sorting & Rounding Reference
- SKU lists, ID lists → **ascending alphanumeric**.
- Records with composite keys → follow template (e.g., `order_id` asc then `line_id` asc; `sku` asc then `quantity` desc then `from_warehouse_id` asc).
- Currency: round half-up to 2 decimals; ensure `52045.82` not `52045.8`.
- Percentages: 1 decimal place (e.g., `23.7`).
- Durations: 2 decimal places (e.g., `58.22`).

## 7. Common Pitfalls
- **Using raw on-hand instead of effective available** — always subtract reserved/quarantined/buffer.
- **Forgetting to include all enum keys** in summary objects (e.g., `decision_counts` must have every decision key, even if zero).
- **Treating open incidents as zero duration** — use `analysis_date` for open incidents.
- **Including transfer lines in blocked orders** — `blocked_orders` is account/risk-level only.
- **Missing `inactive_sku_order_ids`** in expedite summary — any order with at least one inactive SKU qualifies, regardless of final decision.
- **PO coverage eligibility** — only same-warehouse, open or confirmed POs arriving before the build date count as timely.
- **Transfer quantity logic** — do not transfer more than the gap; do not double-count target warehouse stock.
- **Recommendation precedence** — evaluate in strict order; once a condition matches, stop (do not fall through to lower codes).
- **Sample incident IDs** — cap at 5, sorted ascending; do not pad.
- **Held PO IDs** — only include open or confirmed POs; sort and deduplicate globally.
