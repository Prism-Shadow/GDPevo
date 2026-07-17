# Northwind Components ERP Task Skill

Reusable workflow rules, field conventions, API habits, and pitfalls for task-group-007 dispatch, allocation, replenishment, and supplier-quality tasks.

---

## 1. API Reference & Entry Habits

**Base URL**
- Honor `environment_access.md` or task-local `api_base_url` when present. Do not default to `localhost` if a remote runner URL is provided.
- Health-check entry points: `GET /` and `GET /health`.

**Canonical Endpoints**
| Resource | Pattern | Notes |
|----------|---------|-------|
| Orders (list) | `GET /orders?wave=&required_date=&customer_id=` | Filter by wave first; paginate or bulk-fetch as needed. |
| Order detail | `GET /orders/<order_id>` | Use for line-level SKU, qty, warehouse, shipping speed, destination. |
| Products | `GET /products` or `GET /products/<sku>` | Check `active` flag and product master before release. |
| Customers | `GET /customers` or `GET /customers/<customer_id>` | Check account status, credit/fraud flags, and blocking state. |
| Warehouses | `GET /warehouses` | Enumerate IDs (e.g., `WH_NORTH`, `WH_CENTRAL`, `WH_WEST`). |
| Inventory | `GET /inventory?warehouse_id=&sku=` | **Critical:** treat only *effective* stock as available (see §3). |
| Purchase Orders | `GET /purchase_orders?supplier_id=&sku=&status=` | Eligible statuses for coverage are typically `open` or `confirmed`. |
| Shipping Quote | `GET /shipping/quote?warehouse_id=&destination_zip=&weight_lb=&speed=` | Returns `zone_distance`, `service_days`, `total_cost_usd`. Do not invent `/shipping` POST endpoints. |
| Incidents | `GET /incidents?start=&end=&supplier_id=&sku=&incident_type=&status=` | Date range filters inclusive; closed vs open status matters. |
| Suppliers | `GET /suppliers` | Includes `quality_status`, `name`, and related flags. |
| BOMs | `GET /boms` or `GET /boms/<bom_id>` | Returns kit components and per-unit quantities. |

**API Discipline**
- Always query live API records; never use cached snapshots.
- Do not invent undocumented endpoints (e.g., `/calculate_shipping`, POST shipping APIs).
- Fetch order details first, then fan out to inventory, customer, product, and quote endpoints.
- For BOM-based tasks, explode `GET /boms/<bom_id>` before calculating component demand.

---

## 2. Universal Output Conventions

### 2.1 Dates & Currency
- **Date format:** `YYYY-MM-DD` everywhere.
- **Currency:** USD, rounded to exactly **2 decimal places** (`total_cost_usd`, `extended_cost`, `total_resolution_cost`, `total_purchase_cost`, etc.).
- **Percentages:** Rounded to **1 decimal place** (e.g., `incident_percentage`).
- **Durations:** Rounded to **2 decimal places** (e.g., `avg_duration_days`).

### 2.2 Sorting Rules (Strict)
Apply the exact sort key specified; default to ascending unless noted otherwise.

| Context | Sort Keys |
|---------|-----------|
| Order records / line actions | `order_id` ascending, then `line_id` ascending |
| SKU lists inside records | ascending by SKU |
| Supplier rows | `supplier_id` ascending |
| Transfer requests (component planning) | `sku` ascending, then `quantity` descending, then `from_warehouse_id` ascending |
| Escalation lists | `incident_count` descending, then `total_resolution_cost` descending, then `supplier_id` ascending |
| Blocked/held ID lists | ascending string sort |
| Coverage PO IDs / supporting PO IDs | ascending string sort |

### 2.3 Controlled Vocabularies
Never invent enum values. Use only the allowed sets from the answer template.

**Inventory Status**
```
ready, low_stock, shortage, inactive_sku, inactive_and_shortage
```

**Customer Exception**
```
none, review_required, account_blocked, fraud_watch, credit_watch
```

**Final Decision (Expedite Queue)**
```
ship_now, delayed_release, manual_review, backorder, reject_hold
```

**Next Action (Expedite Queue)**
```
release_to_pick, delay_and_monitor, send_account_review, create_backorder,
hold_credit_or_fraud, escalate_product_master
```

**Line Action (Allocation)**
```
ship, transfer, backorder, manual_review
```

**Primary Reason (Allocation)**
```
none, account_blocked, account_review_required, fraud_watch,
inactive_product, insufficient_effective_stock
```

**Component Final Action (Kit Planning)**
```
no_action_stocked, transfer_only, purchase_required, timely_po_covered, overstock_excluded
```

**Exclusion Reason (Kit Planning)**
```
none, target_overstock, timely_po_covers_gap, stocked_no_gap
```

**Supplier Recommendation Code**
```
ESCALATE_SUPPLIER, PROCESS_REVIEW, WATCHLIST, MONITOR
```

**Supplier Quality Status**
```
approved, watch, quality_hold
```

**Procurement Decision**
```
freeze_new_replenishment, buyer_review_required, monitor_only
```

---

## 3. Inventory & Stock Rules

**Effective Available Calculation**
- Do **not** treat gross `available` quantity as freely usable.
- Subtract reserved, quarantined, and normal operating buffer quantities.
- Formula: `effective_available = available - reserved - quarantined - buffer` (or use the API-returned effective figure if provided).

**Transfer Eligibility**
- A transfer action is valid only when another warehouse can cover the *uncovered* quantity **without** dipping into protected stock (reserved / quarantined / buffer).
- Leave any usable requested-warehouse quantity as `ship_quantity`; only transfer the remainder.
- Choose **one** source warehouse per line.

**Product Master Gate**
- Inactive/discontinued SKUs block automatic release.
- Flag `inactive_skus` and `inactive_and_shortage` correctly; these orders may require `escalate_product_master` or `manual_review`.

---

## 4. Task-Type Workflows

### 4.1 Expedite Queue Decision (Wave-level dispatch)
1. Read the queue memo; extract `wave_id` and `order_ids`.
2. For each `order_id`:
   - `GET /orders/<order_id>` → lines, warehouse, shipping speed, destination zip, weight.
   - `GET /customers/<customer_id>` → exception flags (`account_blocked`, `fraud_watch`, `credit_watch`, `review_required`).
   - For each line SKU: `GET /products/<sku>` → active status.
   - `GET /inventory?warehouse_id=&sku=` → effective available vs. line qty.
   - `GET /shipping/quote` → `zone_distance`, `service_days`, `total_cost_usd`.
3. Classify `inventory_status` using the enum.
4. Derive `final_decision` and `next_action` from customer exception + inventory state.
5. Populate `shortage_skus`, `inactive_skus`, `low_stock_skus` sorted ascending.
6. Build `summary` with exact counts, sorted blocked/manual-review/backorder/inactive-sku ID lists, and total shipping cost (2 decimals).

### 4.2 Mixed-Warehouse Allocation & Transfer
1. Fetch all orders for the wave (`GET /orders?wave=`).
2. Per line:
   - Compute `requested_effective_available` at the requested warehouse.
   - If account or fraud flags exist → `manual_review`.
   - If inactive product → `manual_review` with `inactive_product` reason.
   - If effective stock ≥ line qty → `ship`.
   - Else check other warehouses for surplus effective stock (no protected-stock use). If found → `transfer`.
   - Else → `backorder`.
3. Set `ship_quantity`, `transfer_quantity`, `backorder_quantity` so they sum to the line qty.
4. `transfer_requests` gets one entry per transfer line.
5. `blocked_orders` = orders with account-level blocks (not line-only product reviews).
6. `order_rollup` = per-order outcome enum.
7. `summary` counts lines and units by action type.

### 4.3 Production Kit & Replenishment
1. Read production memo: `bom_id`s, `build_quantity`, `build_date`, `planning_site`.
2. For each BOM: `GET /boms/<bom_id>` → component list and per-unit qty.
3. Compute `total_required = bom_qty × build_quantity` per component.
4. For each component SKU:
   - `GET /inventory?warehouse_id=<planning_site>&sku=` → effective stock.
   - `GET /purchase_orders?sku=&status=` → timely PO qty at the same warehouse (open/confirmed).
   - Evaluate other warehouses for feasible `transfer_qty`.
5. Determine `final_action`:
   - If fully covered by effective stock → `no_action_stocked`.
   - If timely PO covers gap → `timely_po_covered`.
   - If transfer covers gap → `transfer_only`.
   - If purchase still required → `purchase_required`.
   - If target would create overstock → `overstock_excluded`.
6. Build `purchase_requisitions` with `unit_cost` and `extended_cost` (qty × unit_cost, 2 decimals).
7. Populate `excluded_components` with reason and supporting PO IDs.
8. `summary` totals: component count, purchase units/cost, transfer units, timely-PO-covered units.

### 4.4 Supplier Incident Scorecard
1. Read request JSON: `incident_date_filter`, `analysis_date`, `recommendation_policy`.
2. `GET /incidents?start=&end=` → filtered Q1 (or requested window) population.
3. `GET /suppliers` → enrich with supplier names and quality status.
4. Per supplier:
   - `incident_count` = filtered incidents for that supplier.
   - `incident_percentage` = supplier count / total filtered population × 100, **1 decimal**.
   - `total_resolution_cost` = sum of incident resolution costs, **2 decimals**.
   - `avg_duration_days`:
     - Closed incidents: calendar days from `open_date` to `close_date`.
     - Open incidents: calendar days from `open_date` to `analysis_date`.
     - Average of those values, **2 decimals**.
   - `rma_count`, `work_order_count`, `open_incident_count`.
   - `severe_incident_count` = incidents with severity `high` or `critical`.
5. Apply recommendation policy **in precedence order** (highest matching rule wins):
   1. `ESCALATE_SUPPLIER`
   2. `PROCESS_REVIEW`
   3. `WATCHLIST`
   4. `MONITOR`
6. `top_escalation_suppliers` = only `ESCALATE_SUPPLIER` rows, sorted by incident count desc, then cost desc, then supplier_id asc.
7. `highest_cost_supplier_id` = max `total_resolution_cost` in the filtered set.
8. `highest_share_supplier_id` = max `incident_percentage` in the filtered set.

### 4.5 Procurement Quality Hold Review
1. Read memo: `analysis_window`, `target_supplier_ids`.
2. For each target supplier:
   - `GET /suppliers` → `quality_status`, `supplier_name`.
   - `GET /incidents?start=&end=&supplier_id=` → recent incident list.
   - `GET /purchase_orders?supplier_id=&status=` → open/confirmed PO IDs.
3. Derive per-supplier metrics:
   - `recent_incident_count`, `recent_rma_count`, `severe_or_critical_count`, `open_incident_count`.
   - `affected_skus` = sorted unique SKUs from recent incidents.
   - `sample_incident_ids` = sorted list, **max 5**.
   - `held_po_ids` = sorted open/confirmed PO IDs for this supplier.
4. Decision mapping (typical policy; adapt to memo rules):
   - Strong risk (e.g., `quality_hold` with incidents, or critical RMAs, or high cost) → `freeze_new_replenishment`.
   - Moderate risk → `buyer_review_required`.
   - Low risk → `monitor_only`.
5. Aggregate:
   - `held_po_ids` = sorted unique union of all held PO IDs.
   - `release_supplier_ids` = sorted suppliers with `monitor_only`.
   - `summary` counts by decision type and total recent incidents.

---

## 5. Shipping Quote Rules
- Required fields: `zone_distance` (int), `service_days` (int), `total_cost_usd` (number, 2 decimals).
- Parameters: `warehouse_id`, `destination_zip`, `weight_lb`, `speed`.
- Quote the order’s requested shipping speed when specified in operator notes.
- Even if the decision is not `ship_now`, still obtain the quote if the memo asks for it.

---

## 6. Controlled Calculation Pitfalls

| Pitfall | Safe Practice |
|---------|---------------|
| Using gross inventory as available | Always compute or use **effective available** after subtracting reserved, quarantined, and buffer stock. |
| Wrong rounding | Currency → 2 decimals; percentages → 1 decimal; durations → 2 decimals. Do not truncate. |
| Missing sort | Every list in templates has a defined order; failing to sort fails validation. |
| Precedence inversion | Recommendation/decision policies are evaluated top-down; first matching rule wins. Do not merge rules. |
| Blocked vs. manual-review | Blocked orders are **account-level** stops (`account_blocked`, `fraud_watch`, `credit_watch`). Line-only issues (inactive SKU) go to `manual_review`, not `blocked_orders`. |
| Duration for open incidents | Use `analysis_date` as the close-proxy, not today’s wall-clock date, unless instructed otherwise. |
| Max sample caps | `sample_incident_ids` is often capped at 5; slice and sort before emitting. |
| Duplicate PO IDs in aggregates | De-duplicate held/supporting PO IDs across suppliers or components, then sort. |
| Transfer source protection | Never pull from reserved/quarantined/buffer stock at the source warehouse when approving a transfer. |
| Currency unit | Always label and compute in USD; do not mix units. |

---

## 7. JSON Output Discipline
- Return **only** the JSON object matching the answer template.
- Include every required top-level key and every nested required key.
- Use `null` only where the template explicitly allows it (e.g., `transfer_from` may be `null` when action is not `transfer`).
- Omit narrative text, markdown fences, or comments outside the JSON payload.
