# Northwind ERP Operations Skill — task_group_007

## Environment

- **Base URL**: `http://34.46.77.124:8007` (from `environment_access.md`). Ignore any localhost/127.0.0.1 references in task prompts.
- All data lives behind this shared ERP API. No local .env files, no direct DB access.

## API Endpoints & Usage

The ERP exposes RESTful JSON endpoints. Known endpoints (call as needed per task):

| Endpoint | Returns |
|---|---|
| `GET /orders` | Sales orders with lines, status, warehouse, customer ref |
| `GET /products` | Product master: SKU, name, active flag, unit cost, supplier ref |
| `GET /customers` | Customer accounts: status flags, credit/review/fraud markers |
| `GET /inventory` | Per-warehouse quantities: qty_on_hand, reserved, quarantined, buffer |
| `GET /warehouses` | Warehouse list (ids: WH_NORTH, WH_CENTRAL, WH_WEST) |
| `GET /shipping-quotes` | Zone distance, service days, cost by order/warehouse pair |
| `GET /boms` | Bill of materials: components with quantity-per-kit |
| `GET /purchase-orders` | POs: status (open/confirmed/closed), supplier, warehouse, line items, delivery dates |
| `GET /suppliers` | Supplier master: name, quality_status, preferred supplier flags |
| `GET /incidents` | Quality incidents: open_date, close_date, severity, type (RMA/WORK_ORDER), supplier, resolution_cost |

Always fetch relevant records from the live API; never cache or hardcode.

## Inventory & Effective Availability

The key formula for all inventory-aware decisions:

```
effective_available = qty_on_hand - reserved - quarantined - buffer
```

- **reserved**: already allocated to other orders
- **quarantined**: held for quality inspection
- **buffer**: normal operating safety stock — not freely available
- A negative `effective_available` means a shortage exists.

For multi-warehouse tasks, compute effective_available per warehouse independently.

## Currency, Percentage & Duration Precision

| Measure | Precision | Example |
|---|---|---|
| **Currency (USD)** | 2 decimal places | `12345.67` |
| **Percentage** | 1 decimal place | `23.7` (meaning 23.7%) |
| **Duration (days)** | 2 decimal places | `58.22` |
| **Unit/quantity counts** | Integer | `216` |

Round with standard `round(x, n)` — never floor or ceil unless explicitly instructed.

## Sorting Conventions

**Primary sort**: always ascending by the principal key of the section (order_id, supplier_id, sku, bom_id).
**Multi-key sorts**: when a template specifies secondary/tertiary keys, apply them in the stated order.

Common patterns:
- `line_actions`: order_id asc, then line_id asc
- `transfer_requests`: sku asc, then quantity desc, then from_warehouse_id asc
- `component_plan`: sku asc
- `purchase_requisitions`: sku asc
- `supplier_scorecard`: supplier_id asc
- `top_escalation_suppliers`: incident_count desc, then total_resolution_cost desc, then supplier_id asc

All SKU lists (`shortage_skus`, `inactive_skus`, `low_stock_skus`, `affected_skus`, `sample_incident_ids`, `held_po_ids`, `coverage_po_ids`, `supporting_po_ids`, `blocked_order_ids`) sort ascending.

## Task Type 1: Expedite Queue Decision

**Trigger**: memo with `order_ids` + operator notes. References a wave like `TRAIN_EXPEDITE_A`.

**SOP**:
1. Fetch orders, products (for active flag), customers, inventory (all warehouses), and shipping quotes.
2. For each order:
   - **Inventory classification**: compare line quantity against effective_available at the order's warehouse. If any line SKU is inactive → `inactive_sku` contributes. If shortage → `shortage`. Both → `inactive_and_shortage`. Stock ok but some SKUs near threshold → `low_stock`.
   - **Customer exception**: check customer record for account flags → `none`, `review_required`, `account_blocked`, `fraud_watch`, `credit_watch`.
   - **Final decision** (priority logic):
     - `account_blocked` or `fraud_watch` → `reject_hold`
     - `review_required` or `credit_watch` → `manual_review`
     - Inventory `shortage` or `inactive_and_shortage` → `backorder`
     - `low_stock` → `delayed_release`
     - Otherwise → `ship_now`
   - **Next action** maps to decision: `create_backorder` for backorder, `send_account_review` for manual_review, `hold_credit_or_fraud` for reject_hold, `release_to_pick` for ship_now, `delay_and_monitor` for delayed_release.
   - **SKU exception lists**: classify each line SKU as shortage/inactive/low_stock based on effective_available vs ordered quantity.
3. If customer_exception overrides inventory (review_required/account_blocked/fraud_watch/credit_watch), the customer exception dominates: set `final_decision` to `manual_review` or `reject_hold`, and `next_action` accordingly. Still populate inventory_status and SKU lists truthfully.
4. **Shipping quote**: fetch per-order quote (zone_distance, service_days, total_cost_usd). Round cost to 2 decimals.

**Summary**: count each decision type. Populate `blocked_order_ids`, `manual_review_order_ids`, `backorder_order_ids`, `inactive_sku_order_ids`. Sum shipping costs.

## Task Type 2: Kit Build Replenishment

**Trigger**: production memo with `bom_ids`, `target_build_quantity`, `target_build_date`, `planning_site` warehouse.

**SOP**:
1. Fetch BOMs for each target. Fetch inventory for all warehouses. Fetch open/confirmed POs for the planning warehouse.
2. For each BOM, multiply component qty-per-kit × build_quantity to get per-component `total_required`. Aggregate across BOMs if a SKU appears in multiple kits.
3. Compute `target_effective_available` = effective_available_at_target_warehouse − total_required. Negative = gap.
4. **Timely POs**: open/confirmed POs at the target warehouse with delivery_date ≤ target_build_date. Their line quantities count toward `timely_po_qty`.
5. **Transfers**: check other warehouses for positive effective_available of the SKU. Source oldest build_date needs first.
6. **Purchase requisition**: remaining gap after PO coverage and transfers. Use supplier from product master. `extended_cost` = quantity × unit_cost (2 decimals).
7. **Final action**:
   - `target_effective_available ≥ 0` → `overstock_excluded` (if strictly positive excluding transfers) or `no_action_stocked` (if zero or within buffer)
   - Gap fully covered by timely POs → `timely_po_covered`
   - Gap covered fully by transfers with no purchase needed → `transfer_only`
   - Purchase needed → `purchase_required`
8. If `overstock_excluded`, add to `excluded_components` with reason `target_overstock`.
9. For `timely_po_covered`, add to `excluded_components` with reason `timely_po_covers_gap` and list supporting PO IDs.
10. `total_required` is total across all BOMs for that SKU (not per-kit).

**Transfer ordering**: sku asc, quantity desc, from_warehouse_id asc.

**Summary**: sum purchase units/cost, transfer units, timely PO covered units.

## Task Type 3: Supplier Incident Scorecard

**Trigger**: scorecard request with date filter (field `open_date`), analysis_date, severity values, recommendation policy.

**SOP**:
1. Fetch all incidents. Filter: `open_date` in [start_date, end_date] inclusive.
2. Fetch all suppliers. Join suppliers that have ≥1 filtered incident.
3. For each supplier:
   - `incident_count`: count of filtered incidents
   - `incident_percentage`: (supplier_count / total_filtered_count) × 100, rounded to 1 decimal
   - `total_resolution_cost`: sum of resolution_cost for closed incidents, rounded to 2 decimals
   - `avg_duration_days`: for closed incidents, avg of (close_date − open_date) in calendar days. For open incidents, (analysis_date − open_date). Round to 2 decimals.
   - `rma_count`: incidents where type = RMA
   - `work_order_count`: incidents where type = WORK_ORDER
   - `open_incident_count`: incidents with no close_date
   - `severe_incident_count`: incidents where severity ∈ [high, critical]
4. **Recommendation code** (apply in PRECEDENCE order — first match wins):
   - `ESCALATE_SUPPLIER`: supplier on `quality_hold` with ≥3 filtered incidents, OR any incident is critical RMA, OR ≥3 RMAs AND total_resolution_cost ≥ $15,000.00
   - `PROCESS_REVIEW`: WORK_ORDER count ≥ 3 AND WORK_ORDER > RMA count
   - `WATCHLIST`: quality_status is `watch` or `quality_hold`, OR incident_count ≥ 4, OR total_resolution_cost ≥ $12,000.00, OR severe_incident_count ≥ 2
   - `MONITOR`: none of the above
5. `top_escalation_suppliers`: only ESCALATE_SUPPLIER suppliers, ordered by incident_count desc → total_resolution_cost desc → supplier_id asc
6. `highest_cost_supplier_id`: supplier with max total_resolution_cost (ties: first by supplier_id asc)
7. `highest_share_supplier_id`: supplier with max incident_percentage (ties: first by supplier_id asc)

**Note**: the recommendation policy spec in the request document may vary per task — read it each time; the above is the common pattern.

## Task Type 4: Allocation Desk / Transfer Wave

**Trigger**: wave memo with order wave ID, line-level decision template.

**SOP**:
1. Fetch wave orders with lines. Fetch customers, products, inventory (all warehouses).
2. For each order line:
   - Compute `requested_effective_available` = effective_available at the line's warehouse.
   - **Check blocking conditions first** (these force `manual_review` regardless of stock):
     - Customer `account_blocked` → primary_reason `account_blocked`
     - Customer `fraud_watch` → primary_reason `fraud_watch`
     - Customer `review_required` flag → primary_reason `account_review_required`
     - Product `active` = false → primary_reason `inactive_product`
   - If no blocking condition:
     - requested_effective_available ≥ line_qty → action `ship`, ship_quantity = line_qty
     - requested_effective_available < line_qty → check other warehouses. If another warehouse has enough effective_available to cover the shortage → action `transfer`. Pick one source warehouse. `ship_quantity` = min(line_qty, requested_effective_available). `transfer_quantity` = line_qty − ship_quantity + (extra to replenish requested warehouse to non-negative if needed).
     - No warehouse can cover → action `backorder`, backorder_quantity = line_qty − max(0, requested_effective_available)
3. **Transfer requests**: one entry per transfer line with from_warehouse, to_warehouse, quantity = transfer_quantity.
4. **Blocked orders**: orders where ALL lines are blocked by account/fraud (not product-only reviews). Also include orders where the account itself is blocked/fraud/review even if some lines show stock.
5. **Order rollup** (per order, across all its lines):
   - All lines ship → `ready_to_ship`
   - Any transfer, no backorder/manual_review → `needs_transfer`
   - Any backorder, no manual_review → `has_backorder`
   - Any manual_review, no other non-manual_review actions → `manual_review`
   - Mix of action types (excluding manual_review dominated) → `mixed_actions`
6. `transfer_from` is null when action is not `transfer`.

## Task Type 5: Procurement Quality Control

**Trigger**: quality hold review memo with `target_supplier_ids` and analysis window.

**SOP**:
1. Fetch suppliers, incidents (filter by analysis window), and purchase orders.
2. For each target supplier:
   - `quality_status`: from supplier record (approved, watch, quality_hold)
   - `recent_incident_count`: incidents with open_date in analysis window
   - `recent_rma_count`: of those, how many are type RMA
   - `severe_or_critical_count`: of those, how many severity ∈ [high, critical]
   - `open_incident_count`: of those, how many have no close_date
   - `affected_skus`: distinct SKUs from incidents, sorted ascending
   - `sample_incident_ids`: up to 5 incident IDs from the filtered set, sorted ascending
   - `held_po_ids`: open/confirmed POs from this supplier (only if decision is freeze or buyer_review)
3. **Decision** (apply in order):
   - `freeze_new_replenishment`: supplier on quality_hold with significant recent incident/RMA pattern
   - `buyer_review_required`: supplier on watch with concerning but not critical incident pattern
   - `monitor_only`: low-risk, no hold needed
4. **held_po_ids** (top-level): sorted unique list of all held PO IDs across all suppliers.
5. **release_supplier_ids**: sorted list of supplier_ids with `monitor_only` decision.
6. **Summary**: count suppliers reviewed, decisions by type, total held POs, total recent incidents.

## General Field & Output Rules

1. **Always return valid JSON** matching the answer template exactly. No narrative outside the JSON.
2. **Required keys**: every key listed as required in the template must be present. Use empty arrays `[]` not `null` for empty lists.
3. **Null vs empty**: use `null` for `transfer_from` on non-transfer lines. Use `"none"` for `primary_reason` when there's no issue.
4. **Enum values**: use exactly the strings from the template's allowed_values. Case-sensitive.
5. **Integer fields**: order_count, line_id, quantities, counts — emit as integers (no decimals).
6. **Date format**: `YYYY-MM-DD` strings.
7. **Wave/ID case**: wave_ids and order_ids are case-sensitive. Preserve exactly as given.
8. **Coverage/supporting PO IDs**: list PO IDs that actually cover a gap. Only include open/confirmed POs with delivery before the needed date at the correct warehouse. Empty list `[]` if none.
9. **Re-check from API**: never assume inventory/customer/product state from a memo — always verify against the live ERP records.
