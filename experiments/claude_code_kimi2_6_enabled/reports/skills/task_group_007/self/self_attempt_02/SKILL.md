# Northwind Components ERP Task Group Skill

## 1. Environment & API Access

- **Read `environment_access.md` first.** It overrides any localhost/127.0.0.1 references in task prompts. Use only the remote base URL declared there (e.g. `http://34.46.77.124:8007`).
- **Do not** read, list, or inspect `env/` source directories. Do not run `setup.sh` or `server.py`.
- **Base URL:** Use the URL from `environment_access.md`. All endpoints are read-only GET.
- **Do not invent endpoints.** The canonical list is:
  - `GET /`, `GET /health`
  - `GET /products`, `GET /products/<sku>`
  - `GET /customers`, `GET /customers/<customer_id>`
  - `GET /warehouses`
  - `GET /inventory?warehouse_id=&sku=` (both params optional; returns list)
  - `GET /purchase_orders?supplier_id=&sku=&status=` (returns list)
  - `GET /orders?wave=&required_date=&customer_id=` (returns list), `GET /orders/<order_id>`
  - `GET /shipping/quote?warehouse_id=&destination_zip=&weight_lb=&speed=`
  - `GET /incidents?start=&end=&supplier_id=&sku=&incident_type=&status=` (returns list)
  - `GET /suppliers`
  - `GET /boms`, `GET /boms/<bom_id>`

## 2. Core Data Models

### Order
```json
{
  "order_id": "SO-XXXXX",
  "customer_id": "CUST-XXXX",
  "destination_zip": "XXXXX",
  "lines": [{"line_id": 1, "quantity": 10, "sku": "NW-XXXX", "unit_price": 123.45}],
  "priority": "normal|high|critical|low",
  "required_date": "YYYY-MM-DD",
  "shipping_speed": "ground|two_day|overnight",
  "warehouse_id": "WH_NORTH|WH_CENTRAL|WH_WEST",
  "wave": "STRING"
}
```

### Product
```json
{
  "sku": "NW-XXXX",
  "name": "...",
  "category": "...",
  "active": true|false,
  "supplier_id": "SUP-XXX",
  "unit_cost": 123.45,
  "weight_lb": 12.34,
  "safety_stock": 10,
  "overstock_threshold": 100
}
```

### Customer
```json
{
  "customer_id": "CUST-XXXX",
  "name": "...",
  "account_status": "active|blocked|review_required",
  "risk_flag": "none|fraud_watch|credit_watch",
  "tier": "strategic|standard|economy",
  "margin_band": "high|medium|low"
}
```

### Inventory Record
```json
{
  "sku": "NW-XXXX",
  "warehouse_id": "WH_...",
  "on_hand": 100,
  "reserved": 20,
  "quarantined": 5,
  "last_count_date": "YYYY-MM-DD"
}
```
- **Effective available** = `on_hand - reserved - quarantined`. This is the only quantity usable for wave release, transfer sourcing, or stock checks.

### Supplier
```json
{
  "supplier_id": "SUP-XXX",
  "name": "...",
  "quality_status": "approved|watch|quality_hold",
  "region": "..."
}
```

### Incident
```json
{
  "incident_id": "INC-XXXXX",
  "supplier_id": "SUP-XXX",
  "sku": "NW-XXXX",
  "warehouse_id": "WH_...",
  "incident_type": "RMA|WORK_ORDER",
  "severity": "low|medium|high|critical",
  "status": "open|closed",
  "open_date": "YYYY-MM-DD",
  "close_date": "YYYY-MM-DD|null",
  "resolution_cost": 1234.56,
  "root_cause": "..."
}
```

### Purchase Order
```json
{
  "po_id": "PO-XXXXX",
  "supplier_id": "SUP-XXX",
  "sku": "NW-XXXX",
  "warehouse_id": "WH_...",
  "quantity": 100,
  "status": "open|confirmed|cancelled|received",
  "eta": "YYYY-MM-DD"
}
```
- For coverage calculations, only `open` and `confirmed` POs count as "timely."

### BOM
```json
{
  "bom_id": "BOM-XXX",
  "name": "...",
  "warehouse_id": "WH_...",
  "target_date": "YYYY-MM-DD",
  "components": [{"sku": "NW-XXXX", "quantity_per_kit": 4}]
}
```

### Shipping Quote
```json
{
  "zone_distance": 3,
  "service_days": 1,
  "total_cost": 225.67,
  "base_rate": 77.95,
  "fuel_surcharge_rate": 0.0925,
  "carrier": "Northwind Parcel"
}
```
- `speed` must be exactly `ground`, `two_day`, or `overnight`.
- `weight_lb` is the total order weight (sum of `line.quantity * product.weight_lb`).

## 3. Controlled Vocabularies (Exact Strings)

### Inventory Status
- `ready`, `low_stock`, `shortage`, `inactive_sku`, `inactive_and_shortage`

### Customer Exception
- `none`, `review_required`, `account_blocked`, `fraud_watch`, `credit_watch`
- **Mapping rule:**
  - `account_status == "blocked"` → `account_blocked`
  - `risk_flag == "fraud_watch"` → `fraud_watch`
  - `risk_flag == "credit_watch"` → `credit_watch`
  - `account_status == "review_required"` → `review_required`
  - otherwise → `none`

### Final Decision (Expedite)
- `ship_now`, `delayed_release`, `manual_review`, `backorder`, `reject_hold`

### Next Action (Expedite)
- `release_to_pick`, `delay_and_monitor`, `send_account_review`, `create_backorder`, `hold_credit_or_fraud`, `escalate_product_master`

### Line Action (Allocation)
- `ship`, `transfer`, `backorder`, `manual_review`

### Primary Reason (Allocation)
- `none`, `account_blocked`, `account_review_required`, `fraud_watch`, `inactive_product`, `insufficient_effective_stock`

### Final Action (Kit Replenishment)
- `no_action_stocked`, `transfer_only`, `purchase_required`, `timely_po_covered`, `overstock_excluded`

### Exclusion Reason (Kit Replenishment)
- `none`, `target_overstock`, `timely_po_covers_gap`, `stocked_no_gap`

### Recommendation Code (Supplier Scorecard)
- `ESCALATE_SUPPLIER`, `PROCESS_REVIEW`, `WATCHLIST`, `MONITOR`

### Supplier Decision (Quality Hold Review)
- `freeze_new_replenishment`, `buyer_review_required`, `monitor_only`

## 4. Sorting Rules (Mandatory)

- **Records by order:** ascending by `order_id`.
- **Lines within order:** ascending by `line_id`.
- **SKU lists:** ascending alphabetical.
- **Supplier lists / scorecard rows:** ascending by `supplier_id`.
- **Transfer requests:** ascending by `sku`, then descending by `quantity`, then ascending by `from_warehouse_id`.
- **Component plan / excluded components:** ascending by `sku`.
- **Kit targets:** ascending by `bom_id`.
- **PO ID lists:** ascending.
- **Incident ID lists:** ascending.
- **Order ID lists (summary blocks):** ascending.

## 5. Rounding Rules

- **Currency (USD):** always round to exactly 2 decimal places in output.
- **Percentages:** round to 1 decimal place.
- **Durations (days):** round to 2 decimal places.
- **Integers:** do not round; use exact integer arithmetic.

## 6. Workflow Patterns by Task Type

### 6.1 Expedite Queue Decision (train_001 style)
1. Read the queue memo to get the `wave_id` and the list of `order_ids` to evaluate.
2. Fetch the wave's orders via `/orders?wave=...` or individual `/orders/<id>` calls.
3. For each order:
   - Fetch customer via `/customers/<customer_id>`.
   - For each line SKU, fetch product via `/products/<sku>` and inventory via `/inventory?warehouse_id=...&sku=...`.
   - Determine `inventory_status`:
     - If any SKU `active == false` → includes `inactive_sku`.
     - If effective available < requested quantity → includes `shortage`.
     - If effective available >= quantity but < safety_stock → `low_stock`.
     - Otherwise `ready`.
     - Combine `inactive_sku` + `shortage` → `inactive_and_shortage`.
   - Determine `customer_exception` using the mapping in §3.
   - Determine `final_decision` and `next_action` based on exception + inventory:
     - `account_blocked` → `reject_hold` / `send_account_review` (or `hold_credit_or_fraud` if credit_watch)
     - `fraud_watch` / `credit_watch` → `reject_hold` / `hold_credit_or_fraud`
     - `review_required` → `manual_review` / `send_account_review`
     - `inactive_sku` → `backorder` or `manual_review` / `escalate_product_master`
     - `shortage` → `backorder` / `create_backorder`
     - `low_stock` → `delayed_release` / `delay_and_monitor`
     - All clear → `ship_now` / `release_to_pick`
   - Populate `shortage_skus`, `inactive_skus`, `low_stock_skus` (sorted ascending).
   - Call `/shipping/quote?warehouse_id=...&destination_zip=...&weight_lb=...&speed=...` for the shipping object.
4. Build `summary`:
   - `order_count`
   - `decision_counts` with exact keys: `ship_now`, `delayed_release`, `manual_review`, `backorder`, `reject_hold`
   - `total_shipping_cost_usd` (sum of all record shipping quotes, 2 decimals)
   - `blocked_order_ids`, `manual_review_order_ids`, `backorder_order_ids`, `inactive_sku_order_ids` (sorted ascending)

### 6.2 Kit Replenishment / Production Planning (train_002 style)
1. Read the production memo to get `planning_site` (e.g. `WH_WEST`) and target builds (`bom_id`, `build_quantity`, `build_date`).
2. Fetch each BOM via `/boms/<bom_id>`.
3. For each component SKU:
   - `total_required` = Σ(`build_quantity` × `quantity_per_kit`) across all target BOMs.
   - Fetch inventory at `planning_site` and all other warehouses.
   - `target_effective_available` = `on_hand - reserved - quarantined` at `planning_site`.
   - Fetch POs via `/purchase_orders?sku=...&status=open` and `status=confirmed`. Sum `timely_po_qty` for POs at the planning site.
   - Determine `overstock_excluded` if effective stock + incoming POs would push total above `overstock_threshold`.
   - Compute gap = `total_required - target_effective_available - timely_po_qty`.
   - If gap > 0 and another warehouse has effective available without dropping below its own safety stock, create a `transfer_request` with `transfer_qty = min(gap, other_effective_available)`.
   - If gap still > 0 after transfers, create a `purchase_requisition` with:
     - `quantity` = remaining gap
     - `unit_cost` from `/products/<sku>` `unit_cost`
     - `extended_cost` = `quantity * unit_cost` (rounded to 2 decimals)
     - `needed_by` = earliest `build_date`
     - `supplier_id` from product
     - `warehouse_id` = planning site
   - Set `final_action` and `exclusion_reason` per the controlled vocab.
   - `coverage_po_ids` = sorted list of PO IDs that cover the timely portion.
4. Sort `component_plan` by `sku` ascending.
5. Sort `transfer_requests` by `sku` asc, `quantity` desc, `from_warehouse_id` asc.
6. Sort `purchase_requisitions` by `sku` ascending.
7. Build `summary` with exact keys from template.

### 6.3 Supplier Incident Scorecard (train_003 style)
1. Read the scorecard request JSON for `incident_date_filter`, `analysis_date`, `recommendation_policy`, etc.
2. Fetch incidents via `/incidents?start=...&end=...` using the filter window.
3. Fetch all suppliers via `/suppliers`.
4. For each supplier with at least one filtered incident:
   - `incident_count` = count of filtered incidents for that supplier.
   - `incident_percentage` = (`incident_count` / total filtered incidents) × 100, rounded to 1 decimal.
   - `total_resolution_cost` = sum of `resolution_cost` for filtered incidents, rounded to 2 decimals.
   - `avg_duration_days`:
     - Closed: `close_date - open_date` (calendar days)
     - Open: `analysis_date - open_date` (calendar days)
     - Average across all filtered incidents, rounded to 2 decimals.
   - `rma_count` = count where `incident_type == "RMA"`.
   - `work_order_count` = count where `incident_type == "WORK_ORDER"`.
   - `open_incident_count` = count where `status == "open"`.
   - `severe_incident_count` = count where `severity` in (`high`, `critical`).
   - Apply recommendation policy in **strict precedence order** (`ESCALATE_SUPPLIER` > `PROCESS_REVIEW` > `WATCHLIST` > `MONITOR`). Check each rule exactly as defined in the request JSON.
5. Sort scorecard rows by `supplier_id` ascending.
6. `top_escalation_suppliers` = supplier_ids with `recommendation_code == "ESCALATE_SUPPLIER"`, sorted by `incident_count` desc, then `total_resolution_cost` desc, then `supplier_id` asc.
7. `highest_cost_supplier_id` = supplier with max `total_resolution_cost` (tie-break not specified; use first or supplier_id ascending for stability).
8. `highest_share_supplier_id` = supplier with max `incident_percentage`.

### 6.4 Mixed-Warehouse Allocation (train_004 style)
1. Fetch all orders for the wave via `/orders?wave=...`.
2. For each order, fetch the customer record.
3. For each line:
   - Fetch product (`/products/<sku>`) and inventory at the requested warehouse (`/inventory?warehouse_id=...&sku=...`).
   - `requested_effective_available` = `on_hand - reserved - quarantined` at requested warehouse.
   - **Account-level block first:** If `account_status == "blocked"`, the entire order is blocked. All lines get `action = "manual_review"`, `primary_reason = "account_blocked"`.
   - If `account_status == "review_required"` → `manual_review` / `account_review_required`.
   - If `risk_flag == "fraud_watch"` → `manual_review` / `fraud_watch`.
   - If `risk_flag == "credit_watch"` → `manual_review` / `credit_watch`.
   - If product `active == false` → `manual_review` / `inactive_product`.
   - If `requested_effective_available >= quantity` → `ship` with `ship_quantity = quantity`.
   - If `requested_effective_available < quantity`:
     - Check other warehouses for effective available (without dipping below their safety stock). If found, `transfer` with `ship_quantity = requested_effective_available`, `transfer_quantity = quantity - ship_quantity`.
     - If no other warehouse can cover, `backorder` with `backorder_quantity = quantity - requested_effective_available`.
4. `transfer_requests` list: one entry per transfer line, sorted by `order_id` asc, `line_id` asc.
5. `blocked_orders`: list of `order_id` strings where `account_status == "blocked"`, sorted ascending.
6. `order_rollup`: for each order, determine `outcome`:
   - `ready_to_ship` if all lines are `ship`
   - `needs_transfer` if any line is `transfer` and none are `manual_review`/`backorder`
   - `has_backorder` if any line is `backorder`
   - `manual_review` if any line is `manual_review`
   - `mixed_actions` if multiple different actions apply
7. `summary` must include all required integer keys from the template.

### 6.5 Quality Hold Review / Supplier Replenishment Control (train_005 style)
1. Read the memo for `analysis_window` (`start`, `end`) and `target_supplier_ids`.
2. For each target supplier:
   - Fetch supplier via `/suppliers/<supplier_id>`.
   - Fetch incidents via `/incidents?supplier_id=...&start=...&end=...`.
   - Fetch POs via `/purchase_orders?supplier_id=...&status=open` and `status=confirmed`.
   - Compute:
     - `recent_incident_count` = count of incidents in window.
     - `recent_rma_count` = count of RMA incidents in window.
     - `severe_or_critical_count` = count with severity `high` or `critical`.
     - `open_incident_count` = count with `status == "open"`.
     - `affected_skus` = sorted unique list of SKUs from incidents.
     - `sample_incident_ids` = sorted list of incident IDs, capped at 5.
     - `held_po_ids` = sorted list of open/confirmed PO IDs for this supplier.
   - Determine `decision` based on policy:
     - `freeze_new_replenishment` if `quality_status == "quality_hold"` AND significant incident/PO risk.
     - `buyer_review_required` if `quality_status == "watch"` or moderate incident load.
     - `monitor_only` if low risk.
   - The exact thresholds come from the task memo; use the memo's policy text.
3. `held_po_ids` (top-level) = sorted unique union of all per-supplier `held_po_ids`.
4. `release_supplier_ids` = sorted list of supplier_ids with `decision == "monitor_only"`.
5. Build `summary` with exact keys from template.

## 7. Common Pitfalls

- **Do not use localhost/127.0.0.1** unless `environment_access.md` explicitly points there. Always use the declared remote base URL.
- **Do not read env files** or task evaluation internals.
- **Effective inventory** is `on_hand - reserved - quarantined`. Never use raw `on_hand` for availability decisions.
- **Shipping weight** = sum of `quantity * product.weight_lb` across all lines in the order. Pass the total to `/shipping/quote`.
- **Shipping speed** must be exactly `ground`, `two_day`, or `overnight` (matching the order's `shipping_speed` field).
- **Date filters on incidents** are inclusive of both `start_date` and `end_date`.
- **PO status filtering:** only `open` and `confirmed` count as "eligible" or "timely" for coverage. `cancelled` and `received` do not.
- **Safety stock** is a product-level field. Do not treat it as unavailable unless the task memo explicitly says so; it is a threshold for `low_stock` classification, not a reserve quantity.
- **Overstock threshold** is used in kit replenishment to decide `overstock_excluded`.
- **Nulls:** `transfer_from` and similar fields can be `null`; include them literally, not as empty strings.
- **JSON output:** Return exactly one JSON object. Do not wrap in markdown code fences in the final answer if the judge expects raw JSON.
- **Currency precision:** Always round to exactly 2 decimals. Use `round(value, 2)`; do not truncate.
- **Percentage precision:** Round to exactly 1 decimal place.
- **Controlled vocabularies:** Use the exact strings listed in §3. Any deviation causes validation failure.
- **Sort stability:** When ties exist, fall back to `supplier_id` or `order_id` ascending to ensure deterministic output.
- **Capped lists:** `sample_incident_ids` is capped at 5. Take the first 5 after sorting ascending.
- **Account vs. line blocking:** In allocation tasks, `blocked_orders` is for **account-level** blocks only (`account_status == "blocked"`). Do not include orders here just because individual lines have product issues.
