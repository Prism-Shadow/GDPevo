# train_002 Notes

## English

### Data/source lineage

This task belongs to `task_group_007`, scenario `SCN_007_erp_inventory_order_fulfillment`, using source examples `E001`, `E002`, and `E003` as the design basis. The task implements the replenishment/allocation family from the group design: a kit build requires BOM expansion, effective stock reconstruction, timely purchase-order coverage, transfer selection, and overstock exclusion.

The shared environment is `task_group/task_group_007/env/`. Solver-visible task-local material is limited to `input/payloads/production_memo.json` and `input/payloads/answer_template.json`. The solver is expected to query the shared API for BOMs, products, inventory, purchase orders, and warehouse context.

### Task definition

Production planning asks for a replenishment package for two WH_WEST kit builds:

- `BOM-300`, `Retrofit Kit 1`, 18 kits due `2026-06-06`.
- `BOM-301`, `Emergency Kit 2`, 18 kits due `2026-06-10`.

The expected answer is a structured JSON package with kit targets, component-level coverage, transfer requests, purchase requisitions, excluded components, and aggregate totals. The output schema is defined in `input/payloads/answer_template.json`.

### Scenario fit and material map

This is an ERP inventory and replenishment task aligned with source example `E001`: the solver must combine demand, current stock, safety stock, open supply, and business exclusions before recommending replenishment. It also uses the API workflow pattern from `E002` because the necessary facts are not all present in the local memo. The incident analytics example `E003` is not directly exercised here but remains part of the shared group context.

Important materials and environment surfaces:

- `production_memo.json`: identifies the two BOM IDs, build quantities, build dates, planning site, and API base URL.
- `GET /boms/<bom_id>`: supplies component SKUs and quantity per kit.
- `GET /products/<sku>`: supplies safety stock, overstock threshold, supplier, and unit cost.
- `GET /inventory?warehouse_id=&sku=`: supplies on-hand, reserved, and quarantined stock by warehouse.
- `GET /purchase_orders?sku=`: supplies PO status, ETA, quantity, warehouse, and supplier for PO coverage decisions.

### Solution and evaluation basis

The hidden solution uses these business conventions:

- Effective available stock is `on_hand - reserved - quarantined - safety_stock`.
- Component demand is the BOM quantity per kit multiplied by the target build quantity, summed across both target builds.
- Eligible timely PO coverage uses same-warehouse purchase orders with status `open` or `confirmed` and ETA on or before the relevant build date. `received` and `cancelled` orders are not counted as future coverage.
- Transfers use positive effective availability at other warehouses after preserving their safety stock. Transfer candidates are allocated by largest effective availability first for the SKU.
- Purchase requisitions cover the remaining uncovered quantity after target-site effective stock, timely PO coverage, and transfers.
- A target-site overstocked component with no remaining gap is excluded instead of requisitioned.
- Currency is rounded to two decimals.

For the selected builds, total component demand is:

- `NW-1005`: 90 units.
- `NW-1014`: 216 units.
- `NW-1034`: 72 units.
- `NW-1039`: 144 units.
- `NW-1049`: 144 units.
- `NW-1050`: 108 units.

The standard answer creates purchase requisitions for `NW-1014` (105 units from `SUP-011`), `NW-1034` (123 units from `SUP-004`), and `NW-1050` (32 units from `SUP-011`). It creates transfers for `NW-1014`, `NW-1049`, and `NW-1050`. It excludes `NW-1005` because `PO-50066` covers the same-warehouse gap before the build date, and excludes `NW-1039` because WH_WEST is already over the overstock threshold and effective availability covers the target demand.

The evaluator has eight exact-match scoring points:

- `SP001` weight 2: kit targets, build quantities, dates, and warehouse.
- `SP002` weight 2: component demand and WH_WEST effective availability.
- `SP003` weight 3: purchase requisition set, quantities, suppliers, dates, and costs.
- `SP004` weight 3: transfer request set and quantities.
- `SP005` weight 2: timely PO coverage and PO exclusion logic for `NW-1005`.
- `SP006` weight 2: overstock exclusion for `NW-1039` and excluded component list.
- `SP007` weight 3: component final actions and purchase/transfer quantities for all six SKUs.
- `SP008` weight 1: aggregate totals.

Likely model pitfalls include using on-hand stock without subtracting reserved, quarantined, and safety stock; treating received or cancelled POs as future coverage; ignoring the PO date; counting a late PO for `NW-1050`; purchasing `NW-1049` even though transfer coverage is available; and missing the overstock exclusion for `NW-1039`.

### Transfer design

As a train task, `train_002` anchors the replenishment/allocation conventions for later test tasks. A skill-builder comparing attempts against the standard answer should infer the effective-stock formula, the same-warehouse timely PO coverage rule, the treatment of late or ineligible POs, the use of inter-warehouse effective surplus before purchases, and the need to exclude overstocked or covered SKUs from requisitions. These conventions transfer especially to `test_002` and also support integrated operations decisions in `test_005`.

### Construction record

Author: task-builder subagent `train_002`.

Created: 2026-06-01.

Updated: 2026-06-01.

Major changes: Created the task folder, local production memo, answer template, standard answer, exact-match evaluator, and notes for the kit replenishment task.

