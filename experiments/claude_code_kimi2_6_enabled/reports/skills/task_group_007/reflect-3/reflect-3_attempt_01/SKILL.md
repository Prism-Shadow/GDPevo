# Northwind Components ERP Task Skill

## API Conventions

- Base URL: read from `environment_access.md` (do not assume localhost).
- Core endpoints:
  - `GET /orders?wave=` — wave membership; may return more orders than the memo lists. **Always restrict to the memo's `order_ids`.**
  - `GET /orders/<order_id>` — order detail with lines, warehouse, customer, shipping_speed, destination_zip.
  - `GET /products` and `GET /products/<sku>` — product master; includes `active`, `weight_lb`, `safety_stock`, `overstock_threshold`, `unit_cost`, `supplier_id`.
  - `GET /customers/<customer_id>` — `account_status` (active/blocked/review_required), `risk_flag` (none/fraud_watch/credit_watch).
  - `GET /inventory?warehouse_id=&sku=` — returns list with `on_hand`, `reserved`, `quarantined`.
  - `GET /warehouses` — warehouse list.
  - `GET /shipping/quote?warehouse_id=&destination_zip=&weight_lb=&speed=` — shipping cost; **weight_lb must be exact**.
  - `GET /purchase_orders?supplier_id=&sku=&status=` — PO list; check status values carefully (`open`, `confirmed`, `received`, `cancelled`).
  - `GET /incidents?start=&end=&supplier_id=&sku=&incident_type=&status=` — incident filtering.
  - `GET /suppliers` — supplier master with `quality_status`.
  - `GET /boms/<bom_id>` — BOM components with `quantity_per_kit`.

## Field Conventions & Calculations

### Inventory Effective Available
Universal formula across tasks:
```
effective_available = on_hand - reserved - quarantined
```
Never treat reserved or quarantined as freely available.

### Shipping Quote Weight
**Critical:** Use actual product `weight_lb`, never estimates.
```python
weight_lb = sum(line['quantity'] * products[line['sku']]['weight_lb'] for line in order['lines'])
```
Then call `/shipping/quote` with exact `weight_lb` and the order's `shipping_speed`.

### Currency & Rounding
- All USD values: `round(value, 2)`.
- Percentages: follow template precision (often 1 decimal place).
- Durations: follow template precision (often 2 decimal places).

### Sorting Discipline
The answer template always specifies ordering. Common patterns:
- `order_id` ascending
- `sku` ascending
- `supplier_id` ascending
- Multi-key sorts (e.g., transfer requests: `sku` asc, `quantity` desc, `from_warehouse_id` asc)
Apply exactly; do not rely on API return order.

## Controlled Vocabulary & Decision Precedence

### Expedite Queue Decisions (train_001 pattern)
1. **Account-level blocks first:**
   - `account_status == 'blocked'` → `reject_hold` / `hold_credit_or_fraud`
   - `risk_flag == 'fraud_watch'` or `'credit_watch'` → `manual_review` / `send_account_review`
2. **Then inventory:**
   - Inactive SKU(s) present → `backorder` or `inactive_and_shortage`; next_action `escalate_product_master`
   - Shortage (effective_available < quantity) → `backorder` / `create_backorder`
   - Low stock (effective_available >= quantity but < safety_stock) → `delayed_release` / `delay_and_monitor`
   - Ready → `ship_now` / `release_to_pick`
3. **Then account review:**
   - `account_status == 'review_required'` → `manual_review` / `send_account_review`

### Allocation Line Actions (train_004 pattern)
Per-line decision hierarchy:
1. `account_status == 'blocked'` → `manual_review`, `primary_reason = 'account_blocked'`
2. `risk_flag == 'fraud_watch'` → `manual_review`, `primary_reason = 'fraud_watch'`
3. `account_status == 'review_required'` → `manual_review`, `primary_reason = 'account_review_required'`
4. `product.active == False` → `manual_review`, `primary_reason = 'inactive_product'`
5. Inventory check:
   - `effective_available >= quantity` → `ship`
   - Else check other warehouses for transfer (one source warehouse; leave usable requested-warehouse quantity as `ship_quantity`)
   - If transfer covers gap → `transfer`
   - Else → `backorder` with `primary_reason = 'insufficient_effective_stock'`

**Blocked orders:** Only orders stopped at account/customer-risk level, not line-only product reviews.

### BOM Replenishment (train_002 pattern)
- `total_required = sum(quantity_per_kit * build_quantity)` across all BOMs for the SKU.
- `target_effective_available` = effective stock at the target build warehouse.
- Timely POs = same-warehouse `open` or `confirmed` POs for the SKU.
- Gap = `max(0, total_required - target_effective_available - timely_po_qty)`.
- Transfers: evaluate other warehouses' `effective_available` without dropping below `safety_stock` (or follow memo's "protected stock" rule).
- Exclusion reasons when no gap or overstock:
  - `target_overstock` if target effective > `overstock_threshold`
  - `stocked_no_gap` if gap == 0
  - `timely_po_covers_gap` if POs fully cover
- Final actions map to exclusion reasons: `overstock_excluded`, `no_action_stocked`, `timely_po_covered`, `transfer_only`, `purchase_required`.

### Supplier Scorecards (train_003 pattern)
- Filter incidents strictly by the `open_date` window in the request JSON.
- Duration: calendar days (`close_date - open_date` for closed; `analysis_date - open_date` for open).
- Percentage: `incident_count / total_filtered_incidents`, rounded to specified precision.
- Recommendation policy precedence is strict top-to-bottom; evaluate in given order and stop at first match.
- Tie-breaking for top escalation: `incident_count` desc, `total_resolution_cost` desc, `supplier_id` asc.

### Supplier Quality Hold Review (train_005 pattern)
- Analysis window: strict date filter on `open_date`.
- Held POs: `open` or `confirmed` purchase orders for the supplier.
- Decisions:
  - `freeze_new_replenishment` for suppliers on `quality_hold` with significant incident load, or any critical/open incidents.
  - `buyer_review_required` for `watch` status with notable risk.
  - `monitor_only` otherwise.
- `release_supplier_ids` = only those with `monitor_only` decision.

## Common Pitfalls

1. **Wrong shipping weight** — using `quantity * 0.5` instead of actual `weight_lb`. This causes large cost errors.
2. **Ignoring quarantined inventory** — forgetting to subtract `quarantined` from `on_hand`.
3. **Wrong precedence** — account `blocked` must be checked before inventory; `review_required` precedence may vary by task type.
4. **Sorting** — missing multi-key sorts or assuming API returns are already ordered.
5. **PO status filtering** — including `received` or `cancelled` POs when only `open`/`confirmed` count.
6. **Date inclusivity** — check whether incident date filters are inclusive or exclusive.
7. **BOM multiplication** — remember to multiply `quantity_per_kit` by `build_quantity` for each target build.
