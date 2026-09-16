## Northwind Operations Guide

This reference documents reusable operational patterns drawn from the Northwind Components ERP domain. Load this file when the task involves dispatch control, allocation, replenishment, supplier quality, or procurement decisions.

### Inventory Classification

Inventory status for an order line or set of lines is determined by comparing the requested quantity against effective available stock. The calculation differs by task context:

**For dispatch/expedite tasks:** Effective available = `on_hand` − `reserved` − `quarantined`. Do not subtract `safety_stock` for the expedite desk unless the task explicitly requires it.

**For allocation/transfer tasks:** Effective available = `on_hand` − `reserved` − `quarantined`. The allocation desk treats reserved, quarantined, and held stock as unavailable for the current wave.

**For replenishment/production tasks:** Effective available = `on_hand` − `reserved` − `quarantined`. Safety stock is not subtracted from effective available for the replenishment desk; instead, it is factored into the build-or-buy decision separately.

When effective available >= requested quantity, the line is `ready`. When effective available is positive but below the requested quantity, the line is `low_stock`. When effective available <= 0, the line is in `shortage`. When any SKU on an order is inactive (product `active` field is false), add the `inactive_sku` qualifier.

**Composite inventory statuses:**
- `ready`: every line has effective available >= requested quantity, and no SKU is inactive.
- `low_stock`: at least one line has positive but insufficient stock; no SKU is inactive; no line has effective available <= 0.
- `shortage`: at least one line has effective available <= 0 (or total effective available is below requested), no SKU is inactive.
- `inactive_sku`: at least one line's SKU has `active` = false, but no shortage.
- `inactive_and_shortage`: at least one SKU is inactive AND at least one line is in shortage (possibly the same SKU).

### Customer Exception Classification

Derived from the customer record (`account_status` and `risk_flag`):

| account_status | risk_flag | classification |
|----------------|-----------|----------------|
| active | none | `none` |
| active | fraud_watch | `fraud_watch` |
| active | credit_watch | `credit_watch` |
| blocked | any | `account_blocked` |
| review_required | any | `review_required` |

Exception severity: `account_blocked` > `fraud_watch` > `credit_watch` > `review_required` > `none`.

### Dispatch Decision Matrix

Combine inventory status and customer exception to select a final decision and next action:

1. If any line SKU is inactive: `manual_review` / `escalate_product_master`.
2. If customer exception is `account_blocked`: `reject_hold` / `hold_credit_or_fraud`.
3. If customer exception is `fraud_watch` or `credit_watch`: `manual_review` / `hold_credit_or_fraud`.
4. If customer exception is `review_required`:
   - With `ready` inventory: `manual_review` / `send_account_review`.
   - With `low_stock` or `shortage`: `manual_review` / `send_account_review`.
5. If customer exception is `none`:
   - `ready` → `ship_now` / `release_to_pick`
   - `low_stock` → `delayed_release` / `delay_and_monitor`
   - `shortage` → `backorder` / `create_backorder`
   - `inactive_sku` → `manual_review` / `escalate_product_master`

For dispatch, always request a shipping quote even for orders that will not ship immediately. Compute total weight as the sum of `product.weight_lb × line.quantity` across all lines on the order. Use the order's `shipping_speed` and `destination_zip` with the order's `warehouse_id`.

### Allocation Line-Level Decisions

For allocation tasks with mixed warehouses, evaluate each line individually. The primary release gate is the customer's `account_status` and `risk_flag`. Block any line on an order where the customer is blocked or under review before evaluating stock availability.

Line actions:
- `manual_review`: customer is `blocked`/`review_required`/`fraud_watch`/`credit_watch`, OR any line SKU is inactive.
- `ship`: effective available at the requested warehouse >= line quantity, and no customer/product block.
- `transfer`: requested warehouse cannot cover the line alone, but another warehouse can cover the gap. Leave the requested-warehouse quantity as `ship_quantity`. Pick the single best source warehouse for the uncovered quantity. Do not use stock from a warehouse that would go negative after the transfer (consider that warehouse's effective available).
- `backorder`: no combination of warehouses can cover the full quantity from effective stock, and no customer/product block.

For transfer lines, the `requested_effective_available` is the effective available at the requested warehouse only. The `ship_quantity` is the portion the requested warehouse can fulfill (min of requested_effective_available and quantity, floored at 0). The `transfer_quantity` is the remaining gap. The `transfer_from` is the single source warehouse chosen. Only one transfer source per line.

Use `insufficient_effective_stock` as the primary reason for backorder lines where the customer is clear and the product is active. Use `inactive_product` when the primary block is an inactive SKU. Use `account_blocked`, `account_review_required`, or `fraud_watch` for customer-driven blocks.

### Replenishment Planning

For kit-build replenishment tasks, compute component-level requirements from BOMs:

1. Total required = `quantity_per_kit × build_quantity` for each component.
2. Target effective available = `on_hand` − `reserved` − `quarantined` at the target warehouse. Do NOT subtract safety stock; it is not held aside for the replenishment desk.
3. Gap = total_required − target_effective_available.

**Timely POs:** For each component, find all POs for the target warehouse with the same SKU, status `open` or `confirmed`, and ETA on or before the component's earliest build date. Sum their quantities as `timely_po_qty`.

**Final actions for each component:**

- `overstock_excluded`: target_effective_available >= total_required AND the overstock check confirms the component should be excluded. Set `exclusion_reason` = `target_overstock`.
- `timely_po_covered`: gap > 0 but timely_po_qty >= gap. Set `exclusion_reason` = `timely_po_covers_gap`. List the POs in `coverage_po_ids`.
- `stocked_no_gap`: gap <= 0 and the component is not overstock per its overstock_threshold. Set `exclusion_reason` = `stocked_no_gap`.
- `transfer_only`: gap > 0, can be fully covered from other warehouses' effective available without those warehouses going negative.
- `purchase_required`: gap > 0, cannot be fully covered by transfers alone. Transfer what you can, then purchase the remainder.
- `no_action_stocked`: gap <= 0, fully stocked.

**Transfer requests:** When transferring for replenishment, pull from source warehouses starting with the one that has the largest effective available for that SKU. Never transfer more than the source warehouse's effective available. The `needed_by` date is the earliest `build_date` across all kits that require that component.

**Purchase requisitions:** The purchase quantity = gap − transfer_qty. Use the product's `supplier_id` as `supplier_id`, and `unit_cost` from the product master. `extended_cost` = `quantity × unit_cost`, rounded to 2 decimals.

### Supplier Incident Scorecard

For supplier quality scorecards, filter incidents by date range (inclusive) on `open_date`. Compute per-supplier:

- `incident_count`: total filtered incidents for the supplier.
- `incident_percentage`: `(supplier incident_count / total filtered incident population) × 100`, rounded to 1 decimal.
- `total_resolution_cost`: sum of `resolution_cost` for the supplier's filtered incidents, rounded to 2 decimals.
- `avg_duration_days`: average calendar-day duration. For closed incidents: `close_date − open_date`. For open incidents: `analysis_date − open_date`. Rounded to 2 decimals.
- `rma_count`: count of incidents where `incident_type` = `RMA`.
- `work_order_count`: count where `incident_type` = `WORK_ORDER`.
- `open_incident_count`: count where `status` = `open`.
- `severe_incident_count`: count where `severity` is `high` or `critical`.

### Recommendation Policy (Supplier Quality)

Recommendation codes, evaluated in precedence order. Use the first matching condition:

1. `ESCALATE_SUPPLIER`: supplier `quality_status` is `quality_hold` AND `incident_count` >= 3, OR the supplier has any RMA with severity `critical`, OR `rma_count` >= 3 AND `total_resolution_cost` >= 15000.00.
2. `PROCESS_REVIEW`: `work_order_count` >= 3 AND `work_order_count > rma_count`.
3. `WATCHLIST`: supplier `quality_status` is `watch` or `quality_hold`, OR `incident_count` >= 4, OR `total_resolution_cost` >= 12000.00, OR `severe_incident_count` >= 2.
4. `MONITOR`: none of the above apply.

### Procurement Quality Control

For procurement-control tasks targeting specific suppliers, analyze recent incidents (typically a trailing 4-month window or as specified) plus the supplier's current `quality_status` and open/confirmed POs:

- `freeze_new_replenishment`: supplier on `quality_hold` with significant recent incidents (e.g. >= 2 recent incidents with RMA involvement), OR supplier has recent critical RMA(s). Hold all open/confirmed POs.
- `buyer_review_required`: supplier on `watch` with recent incidents or severe/critical incidents, but not meeting freeze threshold. Hold open/confirmed POs for buyer decision.
- `monitor_only`: supplier has recent incidents but quality_status is `approved` or watch with low severity. No POs held. Can still note for monitoring.

The `held_po_ids` are the open or confirmed POs for the supplier. The `affected_skus` are the distinct SKUs from the supplier's recent incidents, sorted ascending. The `sample_incident_ids` are up to 5 incident IDs from the supplier's recent incidents, sorted ascending.

### Shipping Quotes

Request shipping quotes with:
- `warehouse_id`: the order's warehouse or the originating warehouse
- `destination_zip`: the order's `destination_zip`
- `weight_lb`: sum of (`product.weight_lb × line.quantity`) across all lines on the order
- `speed`: the order's `shipping_speed`

The quote returns `total_cost` (use as `total_cost_usd`), `zone_distance`, and `service_days`.

### General Rules

- Always fetch the full collection endpoints (`/orders`, `/products`, `/inventory`, `/customers`, `/suppliers`, etc.) rather than individual lookups, unless the task explicitly limits scope.
- Never guess values from the task memo alone; validate every data point against the live API.
- When an answer template specifies required keys and field types, produce exactly those keys in exactly that shape. Do not add or omit keys.
- Sort keys alphabetically within each JSON object for deterministic output.
- Round all currency values to exactly 2 decimal places. Round percentages to 1 decimal place. Round duration averages to 2 decimal places.
- For negative effective available, still report it as the raw integer; do not floor to 0.
