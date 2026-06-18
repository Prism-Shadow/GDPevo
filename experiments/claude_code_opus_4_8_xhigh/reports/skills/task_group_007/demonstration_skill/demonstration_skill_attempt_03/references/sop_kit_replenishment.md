# SOP: Kit / BOM build replenishment

**Shape of task:** a production memo names BOM builds (bom_id, target_build_quantity,
target_build_date) at a planning warehouse. Produce a replenishment package: per-component
coverage, inter-warehouse transfer requests, purchase requisitions, excluded components, and
summary totals. Output is
`{task_id, plan_date, kit_targets[], component_plan[], transfer_requests[],
purchase_requisitions[], excluded_components[], summary}`.

`plan_date` is the dataset/as-of date (memo issue date / `/health` generation date).
`task_id` is fixed by the template (e.g. `train_00X`).

## Aggregate requirements across all builds

The planning warehouse is the memo's `planning_site` (all kits build there even if a BOM's
own `warehouse_id` differs — confirm against the live BOM but plan at the requested site).

For each build, fetch `/boms/<bom_id>`. For each component line:
- `required_for_build = quantity_per_kit * target_build_quantity`.
- Accumulate `total_required[sku] += required_for_build` across all builds.
- Track per-SKU **earliest** build_date that uses it (this is the transfer `needed_by`).
- Track the **latest** build_date overall (this is the purchase-requisition `needed_by`).

`kit_targets[]`: one row per build `{bom_id, kit_name (from BOM name), warehouse_id (plan
site), build_quantity, build_date}`, sorted by `bom_id`.

## Per-component plan (decide in this order)

For each SKU (let `eff = effective_available(plan_wh, sku)`, negative allowed → this is
`target_effective_available`; `req = total_required[sku]`; `gap = req - eff`):

1. **Overstock exclusion (highest priority):** if `eff >= product.overstock_threshold` →
   `final_action = overstock_excluded`, `exclusion_reason = target_overstock`. No transfer,
   no purchase. (We already have more than the overstock ceiling at the plan site.)
2. **No gap:** else if `gap <= 0` → `final_action = no_action_stocked`,
   `exclusion_reason = stocked_no_gap`. Nothing to do.
3. **Timely PO coverage:** compute `timely_po_qty` = sum of `quantity` over **plan-warehouse**
   POs with `status ∈ {open, confirmed}` and `eta <= needed_by` (the SKU's earliest build
   date). If `timely_po_qty >= gap` → `final_action = timely_po_covered`,
   `exclusion_reason = timely_po_covers_gap`, `coverage_po_ids` = sorted ids of those POs.
   (POs that arrive *after* the build date, or are received/cancelled, are NOT timely and are
   ignored.)
4. **Transfers then purchase:** otherwise fill the remaining `gap` from other warehouses, then
   purchase the rest:
   - Compute `effective_available` at each **other** warehouse; keep those with a positive
     value. Sort sources by effective availability **descending**.
   - Greedily take `min(remaining_gap, source_eff)` from each source until the gap is covered
     or sources are exhausted. Sum taken = `transfer_qty`.
   - `purchase_requisition_qty = gap - transfer_qty` (>= 0).
   - `final_action = transfer_only` if `purchase_requisition_qty == 0` and `transfer_qty > 0`;
     `purchase_required` if `purchase_requisition_qty > 0`; (`no_action_stocked` only if both
     are 0, which step 2 already handled). `exclusion_reason = none`.

`component_plan` keys: `sku, total_required, target_effective_available, timely_po_qty,
transfer_qty, purchase_requisition_qty, final_action, coverage_po_ids, exclusion_reason`.
Sort by `sku`. `coverage_po_ids` is `[]` unless timely_po_covered.

This transfer rule **splits across multiple sources** (take the full usable amount from each,
biggest first) — different from the allocation-wave SOP's single-source all-or-nothing rule.

## transfer_requests

One entry per (sku, source warehouse) that contributed:
`{sku, from_warehouse_id, to_warehouse_id = plan_wh, quantity, needed_by = SKU earliest build
date}`. Sort by `sku` asc, then `quantity` **desc**, then `from_warehouse_id` asc.

## purchase_requisitions

One entry per SKU with `purchase_requisition_qty > 0`:
`{sku, supplier_id = product.supplier_id, warehouse_id = plan_wh, quantity, needed_by = latest
build date, unit_cost = product.unit_cost (2dp), extended_cost = unit_cost * quantity (2dp)}`.
Sort by `sku`.

## excluded_components

One entry per SKU whose `exclusion_reason != none`:
`{sku, reason, supporting_po_ids}`. `supporting_po_ids` = the timely PO ids for
`timely_po_covers_gap`; `[]` for `target_overstock` and `stocked_no_gap`. Sort by `sku`.
`reason` ∈ {target_overstock, timely_po_covers_gap, stocked_no_gap}.

## summary

- `component_count` = number of components in `component_plan`.
- `total_purchase_units` = sum of `purchase_requisition_qty`.
- `total_purchase_cost` = sum of `extended_cost` (2dp).
- `total_transfer_units` = sum of `transfer_qty`.
- `timely_po_covered_units` = sum of `total_required` (or the gap covered — use total_required
  of the timely-covered components as observed) for `timely_po_covered` components.
  Compute it as the sum of `total_required` over components whose final_action is
  `timely_po_covered`.

## Pitfalls
- Checking overstock **after** computing a purchase — overstock exclusion comes first.
- Counting POs that arrive after the build date, or non-open/confirmed POs, as timely.
- Using the plan-warehouse on-hand without subtracting reserved/quarantined/safety_stock.
- Single-sourcing a transfer here (this SOP splits across warehouses, biggest first).
- Wrong `needed_by`: transfers use the SKU's **earliest** build date; purchases use the
  **latest** build date.
- Pricing from a memo instead of `product.unit_cost`.
