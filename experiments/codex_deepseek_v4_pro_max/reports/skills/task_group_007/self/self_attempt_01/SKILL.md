## When to Use

Use this skill whenever the task involves Northwind Components ERP operations — expedite queues, replenishment planning, supplier incident scorecards, allocation desk decisions, or procurement quality reviews. The skill applies to any task that provides a `<TASK_ENV_BASE_URL>`, a task memo, and an answer template JSON.

## API Setup

The shared ERP API is available at the URL provided by the runner as `TASK_ENV_BASE_URL`. Always read the base URL from the prompt or task context — never hardcode it.

- **Authentication**: None required for the endpoints in scope.
- **Discovery**: Start every new task by calling `GET <TASK_ENV_BASE_URL>/manifest` to confirm available endpoints and record shapes. Do not skip this step.
- **Pagination**: Endpoints support offset/limit pagination (`?offset=0&limit=50` or similar). Loop until you have retrieved all records before performing any analysis. A single page is never the full dataset.

## Task Input Conventions

Every Northwind task follows the same input pattern:

1. **`prompt.txt`** — Natural‑language instructions. Contains the `<TASK_ENV_BASE_URL>` placeholder, the task objective, and any decision‑rule hints.
2. **Memo / request payload** — A JSON or Markdown file in `input/payloads/` that scopes the task: wave IDs, order IDs, BOM IDs, supplier IDs, analysis date windows, policy rules, and decision‑choice enums.
3. **`answer_template.json`** — The exact output schema. Every key, type, enum value, sort order, and precision rule in the template is a hard requirement.

**Prime directive**: The answer template is authoritative. If the template says `sort ascending by order_id`, you sort ascending by `order_id`. If it restricts a field to an enum, you must use one of those values exactly. Return **only** valid JSON that matches the template.

## Data Enrichment Patterns

Never trust a single endpoint in isolation. Cross‑reference the following entity graphs for every task:

| Starting Entity | Enrich With |
|---|---|
| Orders / order lines | Products (active/inactive status, SKU master), Customers (account status, fraud/credit flags) |
| SKUs | Inventory records per warehouse, Products (master data) |
| BOMs | Component SKUs → Inventory per warehouse, Purchase Orders (open/confirmed) |
| Purchase Orders | Suppliers (quality_status, name), Products (SKU) |
| Incidents | Suppliers (quality_status, name), SKUs affected |

## Effective Inventory Calculation

Effective available stock is **not** the raw `quantity_on_hand` or `available` field. Always subtract:

- Reserved quantities (allocated to other orders)
- Quarantined / quality‑hold quantities
- Normal operating buffer (if the task or memo specifies one)

Only treat the remainder as freely allocatable. When multiple warehouses stock the same SKU, evaluate each warehouse independently.

## Decision Frameworks

### Expedite Queue (wave‑based)

For each order in the queue memo, classify along two axes then combine:

**Inventory status** (per‑line then roll up to order):
- `ready` — every line SKU has sufficient effective stock at the requested warehouse
- `low_stock` — at least one line has limited but non‑zero effective stock
- `shortage` — at least one line has zero effective stock
- `inactive_sku` — at least one line SKU is inactive in the product master
- `inactive_and_shortage` — both inactive SKU and shortage conditions present

**Customer exception** (from the customer record):
- `account_blocked` — customer account is blocked
- `fraud_watch` — fraud flag is active
- `credit_watch` — credit hold or watch flag is active
- `review_required` — any other non‑standard account status
- `none` — account is in good standing

**Final decision mapping** (inventory × customer):
- Ready + none → `ship_now` / `release_to_pick`
- Low stock + none → `delayed_release` / `delay_and_monitor`
- Shortage (any customer) → `backorder` / `create_backorder`
- Inactive SKU (any customer) → `manual_review` / `escalate_product_master`
- Blocked / fraud / credit (any inventory) → `reject_hold` / `hold_credit_or_fraud`
- Review‑required customer (ready or low stock) → `manual_review` / `send_account_review`

### Replenishment (BOM‑based kit builds)

For each component SKU in the target BOMs:

1. Compute `total_required` = BOM quantity per kit × target build quantity, summed across all BOMs.
2. Compute `target_effective_available` = effective stock at the planning warehouse for that SKU.
3. Sum `timely_po_qty` = open or confirmed purchase orders for that SKU at the planning warehouse where `delivery_date` ≤ build date.
4. Determine gap: `gap = total_required - (target_effective_available + timely_po_qty)`.
5. If gap ≤ 0 → component is already covered. Either `no_action_stocked`, `stocked_no_gap`, or `timely_po_covers_gap`. Exclude from replenishment.
6. If gap > 0 → check other warehouses for transfer potential (effective stock not needed locally). Prefer the warehouse with the most excess stock.
7. Remaining gap after transfers → purchase requisition from the supplier listed on the product master.

### Supplier Incident Scorecard

1. Retrieve all incidents in the analysis date range from `/incidents`.
2. Filter to the analysis window (inclusive on both start and end).
3. For each supplier with at least one filtered incident, compute: incident count, RMA count, WORK_ORDER count, open count, severe count (severity in `high` or `critical`), total resolution cost, average duration.
4. Apply recommendation codes using the **precedence chain** from the request policy:
   - `ESCALATE_SUPPLIER` first — quality_hold with ≥ 3 incidents, or any critical RMA, or ≥ 3 RMAs + ≥ 15000 cost.
   - `PROCESS_REVIEW` next — WORK_ORDER count ≥ 3 AND exceeds RMA count.
   - `WATCHLIST` next — quality_status is watch/quality_hold, or incident_count ≥ 4, or cost ≥ 12000, or severe ≥ 2.
   - `MONITOR` — fallback when no higher rule matches.
5. Percentages use the total filtered incident population as denominator, rounded to 1 decimal.

### Allocation Desk (mixed‑warehouse wave)

For each order line in the wave:

1. Look up the customer record. If status is `account_blocked`, `fraud_watch`, or `review_required` → `manual_review`.
2. Look up the product. If `inactive` → `manual_review`.
3. Compute requested warehouse effective available for the SKU.
4. If effective available ≥ requested quantity → `ship` (ship_quantity = requested, all else 0).
5. If effective available < requested but > 0 → check other warehouses. If another warehouse has excess effective stock to cover the gap → `transfer` (ship_quantity = what the requested warehouse can provide, transfer_quantity = gap from one best source warehouse). Otherwise → `backorder`.
6. If effective available = 0 → same transfer‑or‑backorder logic, with ship_quantity = 0.

### Procurement Quality Review

For each target supplier:

1. Retrieve the supplier record for `quality_status`.
2. Retrieve recent incidents for that supplier in the analysis window.
3. Count: total incidents, RMAs, severe/critical, open incidents.
4. Map to decision:
   - `freeze_new_replenishment` — quality_hold with active quality incidents, severe/critical count high, or open RMAs.
   - `buyer_review_required` — moderate incident activity, watch status, or borderline metrics.
   - `monitor_only` — approved status with minimal or no recent incidents.
5. Collect open/confirmed POs from `/purchase_orders` for that supplier as `held_po_ids` (for freeze or buyer_review decisions) or note them for monitoring.

## Shipping Quotes

Call `GET <TASK_ENV_BASE_URL>/shipping/quote` with the order's origin warehouse, destination (from customer or order), and requested service speed. Use the response fields: `zone_distance` (integer), `service_days` (integer), `total_cost_usd` (number, round to 2 decimals).

## Output Rules

- Return **only** valid JSON. No markdown fences, no narrative text outside the JSON object.
- Every key listed in the answer template must be present. No missing keys. No extra top‑level keys.
- Enum values must match the template exactly (case‑sensitive).
- Sort all lists as specified in the template. Default sort is ascending by ID field.
- Currency values: always round to 2 decimal places (USD).
- Percentage values: round to 1 decimal place unless the template says otherwise.
- Null fields: use JSON `null` (not the string `"null"` or omission).
- Empty lists: use `[]`, never omit.

## Warehouse Conventions

The three Northwind warehouses:

- `WH_NORTH`
- `WH_CENTRAL`
- `WH_WEST`

These are the only valid warehouse identifiers. Warehouse IDs in API responses and template enums will always be one of these three.

## Common Pitfalls

- **Not fetching all pages**: Always paginate fully. Partial data leads to wrong decisions.
- **Using raw stock instead of effective stock**: Always subtract reserved, quarantined, and held quantities.
- **Mixing up sort orders**: Check the template for each list. Some sort by `order_id`, others by `supplier_id` or `sku`. Some have multi‑key sorts.
- **Ignoring the precedence chain in scorecards**: Recommendation codes must be evaluated in strict precedence order — first match wins.
- **Including excluded components in replenishment**: If a component is already covered by stock or timely POs, it belongs in the excluded list, not in transfer or purchase requisitions.
- **Not rounding currency**: Every dollar amount must have exactly 2 decimal places.
- **Using inactive products**: Always check product master `active` / `status` before assuming a SKU can be shipped.
