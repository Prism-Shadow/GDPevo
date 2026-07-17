# Northwind Components ERP Task Skill

## API Access Habits
- **Base URL**: Use the remote ERP URL from `environment_access.md` (e.g. `http://34.46.77.124:8007`). Do not default to `localhost` or `127.0.0.1` unless the access file explicitly says so.
- **Read-only GET endpoints**: `/products`, `/products/<sku>`, `/customers`, `/customers/<customer_id>`, `/warehouses`, `/inventory`, `/purchase_orders`, `/orders`, `/orders/<order_id>`, `/shipping/quote`, `/incidents`, `/suppliers`, `/boms`, `/boms/<bom_id>`.
- **Query parameters**:
  - `/inventory?warehouse_id=&sku=`
  - `/purchase_orders?supplier_id=&sku=&status=` (status values: `open`, `confirmed`)
  - `/orders?wave=&required_date=&customer_id=`
  - `/shipping/quote?warehouse_id=&destination_zip=&weight_lb=&speed=`
  - `/incidents?start=&end=&supplier_id=&sku=&incident_type=&status=`
- **Shipping quote response** uses the key `total_cost` (not `total_cost_usd`). Round it to 2 decimals when populating `total_cost_usd` in output.

## Inventory & Stock Conventions
- **Effective available** at a warehouse = `on_hand - reserved - quarantined`. Never treat reserved or quarantined stock as freely available.
- **Effective available can be negative** when `quarantined > on_hand`. Report the raw computed integer unless the template explicitly asks for `max(0, …)`. If the template says “integer units”, the raw value is usually expected.
- **Product master** has `active` (boolean), `safety_stock`, `overstock_threshold`, `unit_cost`, `weight_lb`, `supplier_id`.
- **Inactive SKUs** (`active == false`) are a first-class exception that typically forces `manual_review` or `escalate_product_master` depending on the task type.

## Sorting & Rounding Rules
- **Currency**: always round to exactly 2 decimal places (`round(value, 2)`).
- **Percentages**: round to 1 decimal place when the template says so.
- **Durations / averages**: round to 2 decimal places when required.
- **List ordering**: follow the template literally. Common sorts:
  - `order_id` ascending
  - `sku` ascending
  - `supplier_id` ascending
  - For transfers: `sku` ascending, then `quantity` descending, then `from_warehouse_id` ascending.
  - For scorecards / supplier rows: `supplier_id` ascending.
  - For escalations: `incident_count` descending, then `total_resolution_cost` descending, then `supplier_id` ascending.
- **Dedup before sorting**: `affected_skus`, `sample_incident_ids`, and similar lists must be deduplicated before sorting.

## Controlled Vocabulary & Field Mapping
### Customers → Exceptions
Map `account_status` and `risk_flag` to the exact enum values in the template:
- `account_status == "blocked"` → `account_blocked`
- `account_status == "review_required"` → `review_required` (or `account_review_required` when the template uses that enum value)
- `risk_flag == "fraud_watch"` → `fraud_watch`
- `risk_flag == "credit_watch"` → `credit_watch`
- No flags → `none`

### Expedite / Dispatch Decisions
- `inventory_status` order of precedence:
  1. Any inactive SKU → `inactive_sku` or `inactive_and_shortage` if there is also a shortage.
  2. Any shortage (`effective < line qty`) → `shortage`.
  3. Any low-stock SKU (`effective >= qty` but `effective < safety_stock`) → `low_stock`.
  4. Otherwise → `ready`.
- `final_decision` / `next_action` must be chosen from the allowed enums. Customer exceptions and inventory status interact; the exact precedence is task-specific, so prefer the most restrictive condition that applies to the line or order.
- Shipping quotes must be requested for **every** order in the memo, even if the decision is hold or backorder. Weight = sum of `quantity * weight_lb` across all lines.

### Allocation Desk (Mixed-Warehouse Transfer)
- **Blocked orders**: orders stopped at account or customer-risk level. The list should contain order IDs where the customer is `blocked`, `fraud_watch`, `credit_watch`, or `review_required` (the exact set depends on the task; include all non-`none` customer-risk statuses unless the memo narrows it).
- Every line in a blocked order should still appear in `line_actions` with `action = manual_review` and the appropriate `primary_reason`.
- **Transfer logic**:
  - `ship` if requested-warehouse effective available ≥ line quantity.
  - `transfer` if requested warehouse cannot fill the line, but **a single other warehouse** has enough effective available to cover the uncovered quantity without using protected stock.
  - `backorder` if no single warehouse can cover the uncovered quantity.
  - For a transfer line, `ship_quantity` = usable requested-warehouse quantity (`max(0, req_eff)`), `transfer_quantity` = line qty − ship_quantity, and `transfer_from` is the source warehouse.
  - `requested_effective_available` should be the raw computed integer (can be negative).

### Kit Replenishment (WH_WEST pattern)
1. Compute `total_required` per SKU by summing `quantity_per_kit * build_quantity` across all target BOMs.
2. `target_effective_available` = current effective stock at the planning site.
3. `gap = max(0, total_required − target_effective_available)`.
4. **Timely POs**: sum quantities of `open` or `confirmed` purchase orders for the **same warehouse and SKU** whose ETA is on or before the build date (use the earliest build date that needs the SKU as the cutoff). Store PO IDs in `coverage_po_ids`.
5. **Overstock check**: if `target_effective_available > overstock_threshold`, the component is typically excluded (`target_overstock`).
6. If no gap and not overstock → `no_action_stocked` / `stocked_no_gap`.
7. If timely POs cover the gap → `timely_po_covered` / `timely_po_covers_gap`.
8. Otherwise, evaluate **inter-warehouse transfers** from other warehouses. Transferable quantity at a source = `max(0, source_eff − safety_stock)` or simply `max(0, source_eff)` depending on the task memo; use the source with the largest feasible quantity first.
9. Remaining gap after transfers becomes `purchase_requisition_qty`.
10. `excluded_components` should list every SKU whose `exclusion_reason != none`.

### Supplier Scorecards
- Filter incidents by `open_date` inside the analysis window (inclusive).
- **Duration**:
  - Closed incidents: calendar days from `open_date` to `close_date`.
  - Open incidents: calendar days from `open_date` to `analysis_date`.
- **Percentage** = `supplier_incident_count / total_filtered_incidents * 100`, rounded to 1 decimal.
- **Recommendation policy precedence** is strict: evaluate codes in the order given (e.g. `ESCALATE_SUPPLIER` → `PROCESS_REVIEW` → `WATCHLIST` → `MONITOR`). Stop at the first match.
- `highest_cost_supplier_id` = max `total_resolution_cost` (tie-break by `supplier_id` ascending).
- `highest_share_supplier_id` = max `incident_percentage` (tie-break by cost, then `supplier_id`).

### Quality-Hold / Procurement Review
- Count incidents in the requested window per supplier.
- Count `recent_rma_count` (incident_type == `RMA`), `severe_or_critical_count` (`severity` in `high` or `critical`), and `open_incident_count` (`status == open`).
- `affected_skus` = sorted unique SKU list from that supplier’s incidents.
- `sample_incident_ids` = sorted incident IDs, capped at 5.
- `held_po_ids` per supplier = sorted `open` or `confirmed` purchase order IDs for that supplier.
- Global `held_po_ids` = union of all per-supplier held PO IDs (usually only for suppliers whose decision is **not** `monitor_only`).

## Common Pitfalls
- Do **not** process orders that are in the wave but **not** in the task memo. The memo defines the exact population.
- Do **not** invent endpoints (e.g. `/shipping`, `/calculate_shipping`). Only use the endpoints listed in `environment_access.md`.
- Do **not** forget to include `quarantined` when computing effective available.
- Do **not** assume `total_cost_usd` exists in the shipping-quote response; the field is `total_cost`.
- Watch for **negative** effective available values when `quarantined > on_hand`; report the raw integer unless the template explicitly caps it.
- Rounding must be exact: 2 decimals for currency, 1 decimal for percentages where specified.
- Sorting is part of correctness; always sort lists before embedding them in the answer.
- Enum values are case-sensitive and must match the template exactly.
