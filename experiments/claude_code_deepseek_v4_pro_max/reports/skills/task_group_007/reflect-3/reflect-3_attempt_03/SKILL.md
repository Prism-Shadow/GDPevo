# Northwind Components ERP — Replenishment & Dispatch Skill

## API Base
Use the shared ERP API base URL provided by the environment. All endpoints are read-only JSON GET.

## Core Endpoints
| Endpoint | Parameters | Notes |
|---|---|---|
| `/orders/<id>` | — | Order with lines, warehouse, shipping, customer |
| `/orders?wave=` | `wave` | All orders in a wave |
| `/products/<sku>` | — | `active`, `safety_stock`, `overstock_threshold`, `supplier_id`, `unit_cost`, `weight_lb` |
| `/customers/<id>` | — | `account_status` (active/blocked/review_required), `risk_flag` (none/fraud_watch/credit_watch), `tier` |
| `/inventory?warehouse_id=&sku=` | both required | `on_hand`, `reserved`, `quarantined` |
| `/warehouses` | — | `warehouse_id`, `zip`, `region`, `name` |
| `/shipping/quote?warehouse_id=&destination_zip=&weight_lb=&speed=` | all required | Returns `total_cost`, `service_days`, `zone_distance`. Speed: ground/two_day/overnight |
| `/incidents?start=&end=&supplier_id=&sku=&incident_type=&status=` | date range required | `open_date`, `close_date`, `severity`, `incident_type` (RMA/WORK_ORDER), `status`, `resolution_cost`, `supplier_id`, `sku` |
| `/suppliers` | — | `quality_status` (approved/watch/quality_hold) |
| `/boms/<id>` | — | `components` array with `sku` and `quantity_per_kit`, `warehouse_id` |
| `/purchase_orders?supplier_id=&sku=&status=` | — | `status` (open/confirmed), `eta`, `warehouse_id`, `quantity`, `supplier_id` |

## Inventory Effective Available
```
effective_available = on_hand - reserved - quarantined
```
- **Shortage**: `effective_available < requested_quantity`
- **Low stock**: `effective_available >= requested_quantity` AND `(effective_available - requested_quantity) < safety_stock`
- **Ready**: `effective_available >= requested_quantity` AND `(effective_available - requested_quantity) >= safety_stock`
- **Inactive**: `product.active == false`

## Customer Exception Mapping
| Condition | customer_exception |
|---|---|
| `account_status == "blocked"` | `account_blocked` |
| `account_status == "review_required"` | `review_required` |
| `risk_flag == "fraud_watch"` | `fraud_watch` |
| `risk_flag == "credit_watch"` | `credit_watch` |
| `account_status == "active"` AND `risk_flag == "none"` | `none` |

## Fulfillment Decision Logic
Use a precedence order across inventory and customer status for each order:
1. `customer_exception == "account_blocked"` → **reject_hold**, next_action: `hold_credit_or_fraud`
2. `customer_exception` in (review_required, fraud_watch, credit_watch) → **manual_review**, next_action: `send_account_review`
3. Any line has `inactive` SKU → **manual_review**, next_action: `escalate_product_master`
4. Any line has `shortage` → **backorder**, next_action: `create_backorder`
5. Any line has `low_stock` → **delayed_release**, next_action: `delay_and_monitor`
6. All lines `ready` → **ship_now**, next_action: `release_to_pick`

Inventory status (worst-case across order lines): `inactive_and_shortage` > `inactive_sku` > `shortage` > `low_stock` > `ready`. Use the worst condition that applies to any line.

## Shipping Quotes
- Compute total order weight: sum of `line.quantity × product.weight_lb` for all lines
- Call `/shipping/quote` with the order's `warehouse_id`, `destination_zip`, total weight, and `shipping_speed`
- Use `total_cost` from response as `total_cost_usd`, round to 2 decimal places

## BOM & Replenishment Calculations
- `total_required` = sum over all target builds of (`quantity_per_kit × build_quantity`) for that SKU
- `target_effective_available` = `on_hand - reserved - quarantined` at the planning warehouse
- **Timely PO**: same-warehouse, status open or confirmed, `eta` before the earliest build date using that SKU. Report full PO quantity in `timely_po_qty`
- `gap = total_required - target_effective_available - timely_po_qty` (if gap ≤ 0, the component is covered)
- **Transfers**: check other warehouses' `effective_available`. Single source per line. Sort transfer_requests by `sku` ASC, then `quantity` DESC, then `from_warehouse_id` ASC
- After transfers, remaining gap → `purchase_requisition_qty`
- `extended_cost = purchase_requisition_qty × product.unit_cost`, round to 2 decimals
- `needed_by` for purchase/transfer: earliest build date of any kit using that SKU
- **Overstock**: component is overstocked when `on_hand > overstock_threshold` at the target warehouse
- **Exclusion reason**: `target_overstock` (overstocked), `timely_po_covers_gap` (PO covers), `stocked_no_gap` (stock alone covers), or `none`
- `final_action`: `purchase_required`, `transfer_only`, `timely_po_covered`, `overstock_excluded`, `no_action_stocked`

## Allocation Desk (Mixed-Warehouse Transfer)
- `manual_review` for ALL lines when `account_status` is blocked, review_required, or `risk_flag` is fraud_watch
- `manual_review` for a single line when its product is inactive
- Otherwise: `ship` if `effective_available >= quantity`, `transfer` if another warehouse can cover the gap, `backorder` if no source can cover
- For transfer: `ship_quantity = min(requested_eff, quantity)`, `transfer_quantity = quantity - ship_quantity`, pick one source warehouse
- `primary_reason`: `none` (ship), `insufficient_effective_stock` (transfer/backorder), `account_blocked`, `account_review_required`, `fraud_watch`, `inactive_product`
- `blocked_orders`: orders where the stop is at account or risk level (blocked, fraud_watch), not product-level only
- Sort line_actions and transfer_requests by `order_id` ASC, then `line_id` ASC

## Incident Scorecard — Recommendation Policy (Precedence)
Evaluate in order, stop at first match:
1. **ESCALATE_SUPPLIER**: `quality_status == "quality_hold"` AND `≥3` filtered incidents — OR — any RMA with `severity == "critical"` — OR — `≥3` RMAs AND `total_resolution_cost ≥ 15000.00`
2. **PROCESS_REVIEW**: WORK_ORDER count `≥3` AND WORK_ORDER count `>` RMA count
3. **WATCHLIST**: `quality_status` in (watch, quality_hold) — OR — incident_count `≥4` — OR — total cost `≥12000.00` — OR — severe_count `≥2`
4. **MONITOR**: none of the above

## Incident Scorecard — Computations
- **Duration**: closed → `close_date - open_date` (calendar days); open → `analysis_date - open_date`. Round avg to 2 decimals
- **Percentage**: `incident_count / total_filtered × 100`, round to 1 decimal
- **Severe**: severity in (high, critical)
- **Cost**: round to 2 decimal places, USD
- Sort scorecard by `supplier_id` ASC
- `top_escalation_suppliers`: only ESCALATE_SUPPLIER suppliers, sorted by incident_count DESC → total_cost DESC → supplier_id ASC
- `highest_cost_supplier_id`: max `total_resolution_cost`
- `highest_share_supplier_id`: max `incident_percentage`

## Procurement Quality Control
- Query incidents filtered by analysis window and target supplier IDs
- Decision thresholds:
  - `quality_hold` → **freeze_new_replenishment**
  - `watch` status → **buyer_review_required**
  - `approved` with low incident count → **monitor_only**
- `held_po_ids` per supplier: all open/confirmed POs for non-monitor suppliers
- `release_supplier_ids`: suppliers with `monitor_only` decision
- `sample_incident_ids`: up to 5, sorted ascending
- `affected_skus`: unique SKUs from filtered incidents, sorted ascending
- Aggregate `held_po_ids`: sorted unique list across all suppliers

## Sorting & Ordering Conventions
- Order IDs: sort alphanumerically ascending (e.g., SO-70000 before SO-70007)
- SKU lists (shortage_skus, inactive_skus, low_stock_skus, affected_skus): sort ascending by SKU string
- PO ID lists: sort ascending
- Blocked/backorder/manual_review order ID lists: sort ascending
- Transfer requests: `sku` ASC → `quantity` DESC → `from_warehouse_id` ASC
- Line actions: `order_id` ASC → `line_id` ASC

## Currency & Precision
- All USD amounts: round to exactly 2 decimal places
- Percentages: round to 1 decimal place
- Durations (avg days): round to 2 decimal places
- Weights: use product `weight_lb × quantity` with full precision, pass to shipping quote API
