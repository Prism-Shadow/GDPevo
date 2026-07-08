# Northwind Components ERP Dispatch & Procurement Skill

## Scope
Reusable workflow rules for Northwind Components ERP tasks involving expedite queues, production kit planning, supplier scorecards, warehouse allocation, and quality-hold reviews.

## API Access Rules
1. **Base URL**: Use `GDPEVO_ENV_BASE_URL` from `environment_access.md`. Do not start local env scripts or use `localhost`/`127.0.0.1` unless `environment_access.md` explicitly directs there.
2. **Allowed endpoints only**:
   - `GET /`, `/health`
   - `GET /products`, `/products/<sku>`
   - `GET /customers`, `/customers/<customer_id>`
   - `GET /warehouses`
   - `GET /inventory?warehouse_id=&sku=`
   - `GET /purchase_orders?supplier_id=&sku=&status=`
   - `GET /orders?wave=&required_date=&customer_id=`, `/orders/<order_id>`
   - `GET /shipping/quote?warehouse_id=&destination_zip=&weight_lb=&speed=`
   - `GET /incidents?start=&end=&supplier_id=&sku=&incident_type=&status=`
   - `GET /suppliers`
   - `GET /boms`, `/boms/<bom_id>`
3. Do not invent endpoints (e.g., `/shipping`, `/calculate_shipping`, or POST shipping APIs).

## General Workflow
1. Read the task prompt, memo, and `answer_template.json` carefully before calling the API.
2. Identify all required entities (orders, SKUs, customers, suppliers, BOMs) from the memo or prompt.
3. Fetch live data from the ERP in dependency order:
   - Orders/waves first to get the population.
   - Customers and products next (many tasks need account/product status for release decisions).
   - Inventory per warehouse, then purchase orders, then incidents, then shipping quotes.
4. Compute all derived fields (inventory_status, decisions, counts, costs) in-memory.
5. Build the JSON output exactly matching `answer_template.json`, with correct sorting and rounding.
6. Return **only** the JSON object. No markdown fences, no narrative outside JSON.

## Sorting Conventions
Apply sorting **exactly** as stated in each task’s `answer_template.json`. Common patterns observed:
- **Orders / order lines**: ascending by `order_id`, then by `line_id`.
- **SKUs**: ascending alphabetical.
- **Suppliers**: ascending by `supplier_id`.
- **Transfer requests**: ascending by `sku`, then descending by `quantity`, then ascending by `from_warehouse_id`.
- **Purchase order / incident IDs**: ascending alphabetical.
- **Top escalation lists**: descending by incident count, then descending by resolution cost, then ascending by `supplier_id`.
- **Blocked / held / release lists**: ascending alphabetical.

## Rounding & Precision
- **Currency (USD)**: always round to **2 decimal places**.
- **Percentages**: round to **1 decimal place** unless template says otherwise.
- **Durations (days)**: round to **2 decimal places** when specified.
- **Quantities**: integer units, no rounding.

## Controlled Vocabulary (Task-Agnostic Patterns)
### Inventory Status
- `ready`, `low_stock`, `shortage`, `inactive_sku`, `inactive_and_shortage`
### Customer Exceptions
- `none`, `review_required`, `account_blocked`, `fraud_watch`, `credit_watch`
### Final Decisions (Expedite / Allocation)
- `ship_now`, `delayed_release`, `manual_review`, `backorder`, `reject_hold`
### Line Actions (Allocation)
- `ship`, `transfer`, `backorder`, `manual_review`
### Component Actions (Kit Planning)
- `no_action_stocked`, `transfer_only`, `purchase_required`, `timely_po_covered`, `overstock_excluded`
### Exclusion Reasons
- `none`, `target_overstock`, `timely_po_covers_gap`, `stocked_no_gap`
### Recommendation Codes (Supplier)
- `ESCALATE_SUPPLIER`, `PROCESS_REVIEW`, `WATCHLIST`, `MONITOR`
### Quality Decisions
- `freeze_new_replenishment`, `buyer_review_required`, `monitor_only`

## API Usage Habits by Task Type

### 1. Expedite Queue (Wave Decisions)
**Required data per order**:
- Order header and lines from `/orders/<order_id>`
- Customer record from `/customers/<customer_id>` for exception flags
- Product master from `/products/<sku>` for `active`/`inactive` status
- Inventory from `/inventory?warehouse_id=&sku=` for each line
- Shipping quote from `/shipping/quote?warehouse_id=&destination_zip=&weight_lb=&speed=`

**Decision logic** (precedence matters):
1. If any line SKU is inactive → `inventory_status` includes `inactive_sku`.
2. If inventory < requested qty → include `shortage_skus`.
3. If inventory is low but not zero/short → include `low_stock_skus`.
4. Customer flags (`account_blocked`, `fraud_watch`, `credit_watch`) override to `reject_hold`/`manual_review`.
5. Map final decision to next action using the controlled vocabulary.

**Shipping quote**: Always include when requested, even if the final decision is not `ship_now`. Quote object requires `zone_distance`, `service_days`, `total_cost_usd`.

**Summary rules**:
- `blocked_order_ids`: orders with `reject_hold` (or account-blocked).
- `manual_review_order_ids`: orders with `manual_review`.
- `backorder_order_ids`: orders with `backorder`.
- `inactive_sku_order_ids`: orders containing any inactive SKU.

### 2. Production Kit / BOM Planning
**Required data**:
- BOM definitions from `/boms/<bom_id>` for each target build
- Inventory across all warehouses from `/inventory`
- Purchase orders from `/purchase_orders` filtered by `supplier_id`/`sku`/`status`

**Planning arithmetic**:
- `total_required` = BOM qty per kit × `build_quantity`.
- `target_effective_available` = on-hand − reservations − quarantine − operating buffer.
- `timely_po_qty` = sum of open or confirmed PO quantities for the **same warehouse** that can arrive before `build_date`.
- Gap = `total_required` − `target_effective_available` − `timely_po_qty`.

**Action routing**:
- If gap ≤ 0 and no overstock risk → `no_action_stocked` / `stocked_no_gap`.
- If timely PO covers gap → `timely_po_covered`.
- If another warehouse has surplus → `transfer_only` (create transfer request).
- Else → `purchase_required` (create purchase requisition).
- If target would overstock → `overstock_excluded`.

**Transfer request sorting**: `sku` asc → `quantity` desc → `from_warehouse_id` asc.
**Purchase requisition fields**: `unit_cost` and `extended_cost` (qty × unit_cost) rounded to 2 decimals.

### 3. Supplier Incident Scorecard
**Required data**:
- Incidents from `/incidents?start=&end=&supplier_id=`
- Suppliers from `/suppliers`

**Filtering**:
- Apply date filter on `open_date` (or field specified in request) inclusive.
- Exclude incidents outside the analysis window before any aggregation.

**Aggregation per supplier**:
- `incident_count`: count in filtered population.
- `incident_percentage`: (`incident_count` / total filtered incidents) × 100, rounded to 1 decimal.
- `total_resolution_cost`: sum of resolution costs, rounded to 2 decimals.
- `avg_duration_days`: average duration for that supplier’s filtered incidents, rounded to 2 decimals.
  - Closed: calendar days from `open_date` to `close_date`.
  - Open: calendar days from `open_date` to `analysis_date`.
- `rma_count` / `work_order_count`: split by `incident_type`.
- `open_incident_count`: status still open.
- `severe_incident_count`: severity in `["high", "critical"]`.

**Recommendation precedence** (highest match wins):
1. `ESCALATE_SUPPLIER` if quality_hold + ≥3 incidents, OR any critical RMA, OR ≥3 RMAs + ≥15000.00 resolution cost.
2. `PROCESS_REVIEW` if work_order incidents ≥3 and work_orders > RMAs.
3. `WATCHLIST` if quality_status is `watch`/`quality_hold`, OR incidents ≥4, OR resolution cost ≥12000.00, OR severe_incidents ≥2.
4. `MONITOR` otherwise.

**Top escalation list**: only `ESCALATE_SUPPLIER` suppliers, sorted by incident_count desc, total_resolution_cost desc, supplier_id asc.

### 4. Warehouse Allocation / Transfer Review
**Required data**:
- Wave orders from `/orders?wave=TRAIN_TRANSFER_B`
- Customers and products for status flags
- Inventory from `/inventory?warehouse_id=&sku=` for each line

**Effective available stock**:
- Treat reserved, quarantined, and normal operating buffer as **not freely available**.
- Use the API’s effective/available figure if it already excludes those; otherwise subtract them from on-hand.

**Line action logic**:
1. If account or product status blocks automatic release → `manual_review`.
2. If requested warehouse effective available ≥ line qty → `ship`.
3. Else if another warehouse has unprotected surplus to cover the gap → `transfer`.
   - `ship_quantity` = what the requested warehouse can provide.
   - `transfer_quantity` = remaining gap.
   - Choose **one** source warehouse per line.
4. Else → `backorder`.

**Transfer request object**:
- Include `from_warehouse`, `to_warehouse`, `quantity`.
- Sort by `order_id` asc, `line_id` asc.

**Order rollup**:
- `ready_to_ship`: all lines are `ship`.
- `needs_transfer`: at least one `transfer`.
- `has_backorder`: at least one `backorder`.
- `manual_review`: at least one `manual_review`.
- `mixed_actions`: more than one action type across lines.

**Blocked orders**: orders stopped at account/customer-risk level (not line-only product reviews). Sort ascending.

### 5. Quality Hold / Procurement Control
**Required data**:
- Suppliers from `/suppliers`
- Incidents from `/incidents?start=&end=&supplier_id=`
- Purchase orders from `/purchase_orders?supplier_id=&status=` (open or confirmed)

**Per supplier**:
- `recent_incident_count`, `recent_rma_count`, `severe_or_critical_count`, `open_incident_count`.
- `affected_skus`: sorted unique SKUs from incidents.
- `sample_incident_ids`: up to 5 sorted incident IDs.
- `held_po_ids`: sorted open/confirmed PO IDs.

**Decision mapping** (precedence-based; task policy may vary, but typical pattern):
- `freeze_new_replenishment`: highest risk (e.g., quality_hold + multiple severe incidents).
- `buyer_review_required`: medium risk.
- `monitor_only`: lowest risk.

**Global lists**:
- `held_po_ids`: union of all held POs across reviewed suppliers, sorted unique.
- `release_supplier_ids`: suppliers whose decision is `monitor_only`, sorted.

## Common Pitfalls
- **Using localhost when remote URL is mandated**: Always check `environment_access.md` first.
- **Inventing endpoints**: Only use the indexed endpoints; no POST, no `/shipping` without `/quote`.
- **Ignoring sorting rules**: Each list has a specific sort key; mismatched order causes rejection.
- **Wrong rounding**: Currency must be exactly 2 decimals; percentages 1 decimal where specified.
- **Treating protected stock as available**: Reserved, quarantined, and buffer quantities are not free for allocation.
- **Missing summary fields**: Every template has a `summary` object with required keys; do not omit them.
- **Including narrative**: Output must be **only** the JSON object.
- **Date formats**: Use `YYYY-MM-DD` for dates; preserve timezone-aware timestamps from API if needed.
- **Controlled vocabulary mismatch**: Enum values are case-sensitive and must match the template exactly.
