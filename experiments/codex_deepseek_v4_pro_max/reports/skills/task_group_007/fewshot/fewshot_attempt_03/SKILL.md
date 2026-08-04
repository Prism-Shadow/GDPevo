## When to Use

Use this skill when the task involves interacting with the **Northwind ERP API** to solve supply-chain, inventory, procurement, logistics, or quality-control problems. The skill covers common task patterns: order expedite/allocation, BOM-based replenishment planning, supplier incident scorecards, and procurement quality-control reviews.

## API Connectivity

The API base URL is provided through one of:

- A runner-supplied `<TASK_ENV_BASE_URL>` placeholder in the prompt.
- The `GDPEVO_ENV_BASE_URL` environment variable or a local `environment_access.md` file.

Replace any `<TASK_ENV_BASE_URL>` placeholder with the actual base URL before making requests.

**Authentication:** None required. All endpoints are public GET.

Use `curl -s` with `--fail` or `-w "%{http_code}"` to detect errors. All responses are JSON. Round currency values to **two decimal places** and percentages to **one decimal place** unless the answer template specifies otherwise.

## API Endpoint Reference

Detailed schemas are in the companion file `api_reference.md`. Use it to understand response shapes.

### Summary of Available GET Endpoints

| Endpoint | Description |
|---|---|
| `GET /manifest` | API description (may return 404; not needed for tasks) |
| `GET /products` | All products (list) |
| `GET /products/{sku}` | Single product by SKU |
| `GET /inventory` | All inventory records (list, per SKU per warehouse) |
| `GET /warehouses` | All warehouses (list) |
| `GET /orders` | All orders (list) |
| `GET /orders/{order_id}` | Single order by ID |
| `GET /customers` | All customers (list) |
| `GET /customers/{customer_id}` | Single customer by ID |
| `GET /suppliers` | All suppliers (list) |
| `GET /purchase_orders` | All purchase orders (list) |
| `GET /boms` | All bills of materials (list) |
| `GET /boms/{bom_id}` | Single BOM by ID |
| `GET /incidents` | All quality incidents (list) |
| `GET /shipping/quote` | Shipping quote (query params required) |

### Key Lookup Patterns

- **Single-resource lookups** (`/products/{sku}`, `/orders/{order_id}`, `/customers/{customer_id}`, `/boms/{bom_id}`) return the resource directly.
- **Supplier and incident single lookups** (`/suppliers/{id}`, `/incidents/{id}`, `/purchase_orders/{po_id}`, `/warehouses/{warehouse_id}`) may return 404. Use the **list endpoints** and filter client-side by the ID field.
- **`/shipping/quote`** requires three query parameters: `warehouse_id`, `destination_zip`, and `weight_lb`.

## Common Data Model

### Product (`/products`, `/products/{sku}`)

```
sku, name, category, active (bool), supplier_id, unit_cost (USD),
safety_stock (int), overstock_threshold (int), weight_lb (float)
```

### Inventory (`/inventory`)

```
sku, warehouse_id, on_hand (int), reserved (int), quarantined (int),
last_count_date (YYYY-MM-DD)
```

### Effective Available Calculation

```
effective_available = on_hand - reserved - quarantined
available_after_safety = effective_available - safety_stock
```

Use `effective_available` for order-line clearance decisions. Use `available_after_safety` when deciding whether stock can be transferred out or when determining if a warehouse has surplus beyond its own safety-stock buffer.

### Order (`/orders`, `/orders/{order_id}`)

```
order_id, customer_id, warehouse_id, destination_zip, wave, priority,
shipping_speed, required_date, lines[{line_id, sku, quantity, unit_price}]
```

### Customer (`/customers`, `/customers/{customer_id}`)

```
customer_id, name, account_status (active|blocked|on_hold),
risk_flag (none|fraud_watch|credit_watch|review_required),
tier (standard|strategic|critical), margin_band (low|medium|high)
```

### Warehouse (`/warehouses`)

```
warehouse_id, name, region, zip
```

### Supplier (`/suppliers`)

```
supplier_id, name, region, quality_status (approved|watch|quality_hold)
```

### Purchase Order (`/purchase_orders`)

```
po_id, sku, supplier_id, warehouse_id, quantity, status (open|confirmed|cancelled|received),
eta (YYYY-MM-DD or null)
```

### BOM (`/boms`, `/boms/{bom_id}`)

```
bom_id, name, warehouse_id, target_date,
components[{sku, quantity_per_kit}]
```

### Incident (`/incidents`)

```
incident_id, sku, supplier_id, warehouse_id, incident_type (RMA|WORK_ORDER),
severity (low|medium|high|critical), status (open|closed),
open_date, close_date (or null), resolution_cost, root_cause
```

### Shipping Quote (`/shipping/quote`)

Query: `?warehouse_id=...&destination_zip=...&weight_lb=...`

```
warehouse_id, destination_zip, weight_lb, zone_distance (int),
service_days (int), total_cost (float), base_rate, fuel_surcharge_rate,
carrier, speed
```

## Task Pattern Recognition

When you receive a task, first identify which pattern it matches:

### Pattern A — Order Dispatch / Expedite

**Clues:** A wave ID with a list of order IDs, a memo asking for release/hold/review/backorder decisions per order.

**Approach:**
1. Fetch all listed orders (`/orders/{id}` for each).
2. For each order line, fetch the product (`/products/{sku}`) and inventory record for the order's warehouse.
3. Fetch the customer (`/customers/{customer_id}`) to assess account status and risk flags.
4. Classify each line's inventory status by comparing `effective_available` against the ordered quantity:
   - `ready`: all lines have sufficient effective stock and all products are active.
   - `shortage`: at least one line has insufficient effective stock.
   - `low_stock`: a line can be filled but would drop below a threshold (use product `safety_stock` as a guide).
   - `inactive_sku`: a line's product has `active: false`.
   - `inactive_and_shortage`: combined inactive and shortage conditions.
5. Classify customer exceptions from `account_status` and `risk_flag`:
   - `account_blocked`: `account_status` is `blocked`.
   - `fraud_watch` / `credit_watch`: matches `risk_flag`.
   - `review_required`: `account_status` is `on_hold` or `risk_flag` is `review_required`.
   - `none`: no issues.
6. Determine `final_decision` using a precedence rule:
   - `reject_hold`: customer is `account_blocked` or `fraud_watch`.
   - `manual_review`: customer is `review_required` or has `credit_watch`, OR a SKU is inactive, OR multiple conflicting signals.
   - `backorder`: shortage exists with no customer block.
   - `delayed_release`: shortage exists but can be partially filled now.
   - `ship_now`: ready with no exceptions.
7. Compute a shipping quote: sum `weight_lb` for all lines, call `/shipping/quote` with the order's `warehouse_id`, `destination_zip`, and total weight.
8. Build the summary: count decisions, sum shipping costs, collect IDs for each category.

### Pattern B — BOM Replenishment / Kit Planning

**Clues:** BOM IDs, target build quantities, a target warehouse, request for component coverage, transfers, and purchase requisitions.

**Approach:**
1. Fetch each BOM to get components and their `quantity_per_kit`.
2. Compute `total_required` per SKU: sum of `quantity_per_kit × build_quantity` across all BOMs.
3. For each component SKU, fetch the product master (`/products/{sku}`) for `safety_stock` and `supplier_id`.
4. Fetch inventory for the target warehouse. Compute `target_effective_available = effective_available - safety_stock`.
5. Fetch all purchase orders for the target warehouse. Filter to `open` or `confirmed` status. Sum `timely_po_qty` for POs with `eta` before/on the build date.
6. Determine the gap: `gap = total_required - target_effective_available - timely_po_qty`.
7. If `gap <= 0`, classify as `no_action_stocked` (no gap) or `timely_po_covered` (POs cover it) or `overstock_excluded` (target already overstocked beyond threshold).
8. If `gap > 0`, attempt to cover via transfers from other warehouses (check their inventory, compute availability after safety stock). Only transfer what's available after safety stock.
9. Any remaining gap becomes a `purchase_requisition_qty`. Use the product's `supplier_id` and `unit_cost`.
10. `extended_cost = purchase_requisition_qty × unit_cost`.

### Pattern C — Supplier Incident Scorecard

**Clues:** A date range (usually a quarter), request for supplier-level incident stats, a recommendation policy.

**Approach:**
1. Fetch all incidents and filter by `open_date` within the analysis window.
2. Fetch all suppliers and join on `supplier_id`.
3. For each supplier with at least one filtered incident, compute:
   - `incident_count`: total filtered incidents.
   - `incident_percentage`: `(count / total_filtered_population) × 100`, rounded to 1 decimal.
   - `total_resolution_cost`: sum of `resolution_cost`.
   - `avg_duration_days`: average of `close_date - open_date` (closed) or `analysis_date - open_date` (open).
   - `rma_count`: count where `incident_type == "RMA"`.
   - `work_order_count`: count where `incident_type == "WORK_ORDER"`.
   - `open_incident_count`: count where `status == "open"`.
   - `severe_incident_count`: count where `severity` is `high` or `critical`.
4. Apply the recommendation policy from the task payload. Policies typically use a precedence chain (e.g., ESCALATE_SUPPLIER > PROCESS_REVIEW > WATCHLIST > MONITOR) with conditions based on quality_status, incident counts, RMA counts, resolution cost, and severity.
5. Collect `top_escalation_suppliers` (those with ESCALATE_SUPPLIER code, sorted by incident_count descending).
6. Identify `highest_cost_supplier_id` and `highest_share_supplier_id` (highest percentage).

### Pattern D — Order Line Allocation / Transfer Desk

**Clues:** A wave ID, line-level decisions with ship/transfer/backorder/manual_review actions, transfer requests between warehouses.

**Approach:**
1. Fetch all orders in the wave. Use the `/orders` list and filter by `wave` field.
2. For each order line, fetch product, inventory for the requested warehouse, and customer.
3. Classify the line action:
   - `manual_review`: customer is blocked, on hold, fraud/credit watch, OR product is inactive.
   - `ship`: `effective_available >= quantity` with no account/product issues.
   - `transfer`: the requested warehouse can't fill alone, but another warehouse has sufficient stock (after safety stock). Set `ship_quantity` to what the requested warehouse can provide, `transfer_quantity` to the remainder from the source warehouse.
   - `backorder`: no warehouse can fill the line from effective stock.
4. For transfer lines, pick ONE source warehouse for the uncovered quantity.
5. Build `transfer_requests` list (one per transfer line).
6. Build `order_rollup` summarizing each order's overall outcome: `ready_to_ship`, `needs_transfer`, `has_backorder`, `manual_review`, or `mixed_actions`.

### Pattern E — Procurement Quality Control

**Clues:** Target supplier IDs, an analysis window, request for replenishment-control decisions (freeze, buyer review, monitor).

**Approach:**
1. Fetch all incidents, filter to the analysis window by `open_date`.
2. Fetch all suppliers, filter to target supplier IDs.
3. For each target supplier, join incidents, compute metrics (count, RMA count, severe count, open count).
4. Fetch all POs for each target supplier, filter to `open` or `confirmed` status within the window.
5. Determine `decision` for each supplier based on quality metrics and policy:
   - `freeze_new_replenishment`: supplier on `quality_hold` with high incident/RMA counts.
   - `buyer_review_required`: moderate risk signals.
   - `monitor_only`: low risk.
6. Collect `held_po_ids` (all open/confirmed POs for non-monitor suppliers).
7. `release_supplier_ids` are those with `monitor_only` decision.

## Output Conventions

### Reading Answer Templates

Every task includes an `answer_template.json` in the payloads. Study it carefully:
- **`required_top_level_keys`**: these are the keys your output JSON must contain.
- **`fields` / `field_rules`**: describes each key's type, allowed values, ordering, and precision.
- **Enum fields**: only use values listed in `allowed_values` / `allowed`.
- **Ordering**: always follow the sort order specified (usually ascending by ID or SKU).
- **Precision**: currency to 2 decimals, percentages to 1 decimal, durations to 2 decimals.

### Sorting Rules (default, unless template overrides)

- Lists of records: sort by the primary ID field ascending.
- SKU lists within a record: sort alphabetically ascending.
- Transfer requests: sort by SKU ascending, then quantity descending, then source warehouse ascending.

### Currency and Numeric Formatting

- Use Python's `round(value, 2)` for currency (USD).
- Use `round(value, 1)` for percentages.
- Use `round(value, 2)` for average durations.
- Always return numbers, not strings, for numeric fields.
- For `extended_cost`: `round(quantity * unit_cost, 2)`.

### Empty vs. Missing Values

- Empty lists: use `[]`, not `null` or missing keys.
- Nullable fields: use `null` (JSON null) when the template allows it (e.g., `transfer_from` when action is not transfer).
- Zero counts: use `0`, not `null`.

## General Workflow

1. **Read the prompt** (`prompt.txt`) to understand the task type, the wave/BOM/supplier targets, and any special instructions.
2. **Read all payload files** including the `answer_template.json` to know the exact output schema.
3. **Read `environment_access.md`** or the prompt for `<TASK_ENV_BASE_URL>` to get the API base URL.
4. **Fetch API data** in bulk where possible (use list endpoints, filter client-side). Only use single-resource endpoints for `/products/{sku}`, `/orders/{order_id}`, `/customers/{customer_id}`, `/boms/{bom_id}`.
5. **Process and join data** according to the pattern rules above.
6. **Validate** your output JSON against every constraint in the answer template before submitting.
7. **Write the final answer** as a single JSON object with no narrative text outside it.

## Data Processing Tips

- Use `jq` or Python for JSON processing. Python is preferred for complex calculations.
- When computing shipping quotes, sum the `weight_lb` across all order lines.
- `effective_available = on_hand - reserved - quarantined`. Do NOT subtract safety_stock for order-clearance decisions unless the task explicitly asks for "available after safety" transfers.
- For transfer sourcing, prefer the warehouse with the largest surplus after safety stock.
- Date comparisons: parse dates as `datetime.date` objects. The difference between two dates is `(d2 - d1).days`.
- Purchase order "timely" means `eta <= target_build_date` and `status in ("open", "confirmed")`.
- When a product has `active: false`, always flag it as `inactive_sku` or `inactive_product` regardless of inventory levels.
