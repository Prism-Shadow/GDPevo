# SOP: Kit-build replenishment package

A memo names target builds (each: `bom_id`, `target_build_quantity`, `target_build_date`) at a planning
warehouse. Produce a per-component plan, inter-warehouse transfer requests, purchase requisitions,
exclusions, and summary totals. Submit only replenishment still needed after live stock, timely PO
coverage, and feasible transfers.

## Data to pull
- `GET /boms/<id>` for each target BOM (kit `name`, components with per-kit quantity).
- `GET /products` (safety_stock, overstock_threshold, supplier_id, unit_cost).
- `GET /inventory` (planning warehouse + all other warehouses).
- `GET /purchase_orders` (filter by sku; consider only the planning warehouse + status open/confirmed).

## Aggregate requirements (by SKU across all builds)
- `total_required[sku] = sum over builds that use the SKU of (per_kit_qty * build_quantity)`.
  A SKU in multiple BOMs aggregates across them.
- `needed_by[sku]` = the **earliest** `build_date` among builds that use the SKU.

## Per-component availability and gap (at the planning warehouse)
- `target_effective_available = on_hand - reserved - quarantined - safety_stock` (signed; may be negative).
- `gap = total_required - target_effective_available` (negative effective enlarges the gap).

## Timely PO coverage
`timely_po_qty` = sum of quantities of **same-(planning)-warehouse** POs for the SKU with
`status in {open, confirmed}` and `eta <= needed_by[sku]`. A PO whose eta is after needed_by is **not**
timely and does not count. Record the covering `coverage_po_ids` (sorted).

## Decision precedence per component (first match)
1. `target_effective_available >= overstock_threshold` → `overstock_excluded` / reason `target_overstock`.
   The warehouse is already at/above its overstock line; do not add stock.
2. `gap <= 0` → `no_action_stocked` / reason `stocked_no_gap`.
3. `timely_po_qty >= gap` → `timely_po_covered` / reason `timely_po_covers_gap`; list the coverage POs.
4. Otherwise fill `remaining = gap - timely_po_qty`:
   - Pull from other warehouses' **positive effective available** as transfers (greedy: most-available
     first, tie-break warehouse_id ascending), one transfer row per (sku, source warehouse).
   - Any leftover after transfers becomes a purchase requisition.
   - If transfers cover the whole remaining → `transfer_only`.
   - If a purchase remainder exists → `purchase_required` (may also carry transfers).

Set `exclusion_reason = none` for components that take real action (transfer/purchase). The reason enum is
only `target_overstock` / `timely_po_covers_gap` / `stocked_no_gap` for excluded ones.

## Transfer rows
One row per (sku, source warehouse): `sku`, `from_warehouse_id`, `to_warehouse_id` (= planning wh),
`quantity`, `needed_by` (= component needed_by). Sort by `sku` asc, then `quantity` desc, then
`from_warehouse_id` asc.

## Purchase requisitions
`supplier_id` from product master; `warehouse_id` = planning wh; `quantity` = purchase remainder;
`needed_by` = component needed_by; `unit_cost = round(product.unit_cost, 2)`;
`extended_cost = round(unit_cost * quantity, 2)`. Sort by sku asc.

## Excluded components
One row per excluded SKU: `sku`, `reason` (the exclusion_reason), `supporting_po_ids` (sorted; the
timely coverage POs for `timely_po_covers_gap`, else empty). Sort by sku asc.

## Summary (recompute from rows)
- `component_count` = number of components in the plan.
- `total_purchase_units` = sum of purchase_requisition quantities.
- `total_purchase_cost` = sum of extended_costs, 2 dp.
- `total_transfer_units` = sum of transfer quantities.
- `timely_po_covered_units` = sum over `timely_po_covered` components of the **gap each one covered**
  (i.e. its `gap`/`total_required - target_effective_available`), **NOT** the full PO quantities.
  This is the corrected definition — report covered demand units, not the size of the covering PO.
