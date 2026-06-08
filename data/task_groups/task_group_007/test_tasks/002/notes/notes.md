# test_002 Notes

## English

### Data and Source Lineage

This task belongs to `task_group_007` for scenario `SCN_007_erp_inventory_order_fulfillment`, using source examples `E001`, `E002`, and `E003`. The task follows the replenishment/allocation family in the group design. It uses the shared Northwind Components ERP environment under `task_group/task_group_007/env/` through public API endpoints only, especially `/boms`, `/products`, `/inventory`, and `/purchase_orders`.

The task-local solver-visible files are `input/prompt.txt`, `input/payloads/service_parts_campaign_memo.json`, and `input/payloads/answer_template.json`. The campaign memo defines campaign `SERVICE_PARTS_JUNE_26` with two build targets: `BOM-307` for `WH_CENTRAL` and `BOM-308` for `WH_NORTH`.

### Task Definition and Expected Work

The solver must produce a replenishment package for a service-parts campaign. The required output is a structured JSON object containing campaign targets, component-level demand and coverage, transfer requests, purchase requisitions, excluded components, and summary totals.

Important constraints:

- Component demand comes from ERP BOM components multiplied by the requested build quantity.
- Target effective availability is `on_hand - reserved - quarantined - product.safety_stock` at the target warehouse.
- Only open or confirmed purchase orders for the same SKU and same target warehouse can cover demand, and only when `eta` is on or before the component needed-by date.
- Positive effective availability at non-target warehouses can be used for transfers before creating a purchase requisition.
- Components with no gap, target overstock, or timely PO coverage should be excluded from purchase requisitions with controlled reasons.
- Purchase requisition costs use product `unit_cost`, rounded to cents.

### Scenario Fit and Material Map

This task fits the ERP inventory and replenishment scenario because it requires combining BOM demand, product master fields, warehouse inventory, PO timing, inter-warehouse allocation, and supplier purchasing data. It is not solvable from the campaign memo alone.

Material map:

- `service_parts_campaign_memo.json`: campaign id, plan date, BOM ids, target warehouses, build quantities, and needed-by dates.
- `/boms/<bom_id>`: kit names and component quantities per kit.
- `/products/<sku>` or `/products`: safety stock, overstock threshold, supplier id, and unit cost.
- `/inventory?warehouse_id=&sku=`: target and donor warehouse quantities.
- `/purchase_orders?sku=&status=`: PO quantities, ETAs, statuses, warehouses, and ids.
- `answer_template.json`: required output keys, field types, enum choices, precision, and sorting rules.

### Solution and Evaluation Basis

The standard answer uses `BOM-307` quantity 12 at `WH_CENTRAL` and `BOM-308` quantity 10 at `WH_NORTH`. It creates 13 component/warehouse rows. Purchase requisitions are required for `NW-1006` and `NW-1012` at `WH_CENTRAL`, and `NW-1017`, `NW-1018`, and `NW-1051` at `WH_NORTH`. Transfer requests are required for `NW-1006`, `NW-1012`, and `NW-1031`. Timely PO coverage excludes `NW-1028`, `NW-1049`, and `NW-1045`; `NW-1018` and `NW-1045` also test late-PO handling through `late_po_ids`.

The evaluator has 8 exact-match scoring points with raw weights:

- `SP001` weight 2: campaign targets, warehouses, quantities, kit names, and needed-by dates.
- `SP002` weight 2: component demand and target effective availability for all rows.
- `SP003` weight 3: purchase requisition SKU/warehouse set, suppliers, quantities, dates, and costs.
- `SP004` weight 3: transfer request set and quantities.
- `SP005` weight 2: timely PO coverage and late-PO exclusion fields.
- `SP006` weight 2: excluded components and controlled reasons.
- `SP007` weight 3: final actions and purchase/transfer quantities for every component.
- `SP008` weight 2: aggregate counts, purchase units, purchase cost, transfer units, PO-covered units, and warehouse purchase units.

All scoring is deterministic and exact-match after normalization of list ordering and currency to two decimals. Likely pitfalls include treating quarantined stock as available, counting safety stock as usable, applying POs from the wrong warehouse, counting late POs as coverage, ignoring donor warehouse safety stock, or aggregating `NW-1018` across warehouses instead of keeping target rows separate.

### Transfer Design

This test is anchored by `train_002` and `train_004`. From `train_002`, a solver can infer the effective availability convention, same-warehouse timely PO coverage, purchase requisition costing, overstock/timely-PO exclusions, and transfer-before-purchase workflow. From `train_004`, a solver can transfer inter-warehouse allocation habits and the need to keep warehouse-specific availability separate.

Transfer-dependent scoring points are `SP002`, `SP003`, `SP004`, `SP005`, `SP006`, and `SP007`. Task-specific exploration remains substantial because this task uses different BOMs, two target warehouses, a component that appears in different warehouse contexts, different PO timing, and a larger component set than the replenishment train task.

### Construction Record

Author: task-builder subagent `test_002`. Created: 2026-06-01. Updated: 2026-06-01. Major changes: created a complete test task for service-parts campaign replenishment with BOM demand, two warehouses, PO timing, shortages, transfers, purchase requisitions, exclusions, aggregate purchase cost, and an 8-point exact-match evaluator.

