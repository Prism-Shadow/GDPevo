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

## Chinese

### 数据与来源

本任务属于 `task_group_007`，场景为 `SCN_007_erp_inventory_order_fulfillment`，来源示例为 `E001`、`E002`、`E003`。任务对应设计中的补货与调拨业务族，使用共享的 Northwind Components ERP 环境，并通过公开 API 读取 BOM、产品、库存和采购订单数据。

求解者可见文件包括 `input/prompt.txt`、`input/payloads/service_parts_campaign_memo.json` 和 `input/payloads/answer_template.json`。活动编号为 `SERVICE_PARTS_JUNE_26`，包含两个构建目标：`WH_CENTRAL` 的 `BOM-307` 和 `WH_NORTH` 的 `BOM-308`。

### 任务定义

求解者需要为服务备件活动生成补货方案，输出 JSON 包括活动目标、组件需求与覆盖情况、仓库间调拨、采购申请、排除项和汇总指标。

关键约束包括：组件需求由 BOM 单套用量乘以构建数量得到；目标仓有效可用量为 `on_hand - reserved - quarantined - safety_stock`；只有同 SKU、同目标仓、状态为 open 或 confirmed 且 ETA 不晚于需求日期的采购订单可覆盖缺口；其他仓库的正有效可用量可先用于调拨；无需采购的组件用受控原因列入排除项；采购成本使用产品主数据中的 `unit_cost` 并保留两位小数。

### 场景适配与材料映射

该任务符合 ERP 库存补货场景，因为它需要综合 BOM 需求、产品主数据、仓库库存、采购订单时点、仓库间调拨和供应商采购信息。仅凭活动备忘录无法完成。

材料映射：活动备忘录提供 BOM、目标仓、数量和需求日期；`/boms/<bom_id>` 提供套件名称和组件用量；`/products` 提供安全库存、超储阈值、供应商和单位成本；`/inventory` 提供目标仓和供给仓库存；`/purchase_orders` 提供采购订单数量、ETA、状态、仓库和编号；答案模板规定输出结构和枚举。

### 答案与评估依据

标准答案使用 `WH_CENTRAL` 的 `BOM-307` 数量 12 和 `WH_NORTH` 的 `BOM-308` 数量 10，共 13 个组件/仓库行。需要采购的项目为 `WH_CENTRAL` 的 `NW-1006`、`NW-1012`，以及 `WH_NORTH` 的 `NW-1017`、`NW-1018`、`NW-1051`。需要调拨的项目为 `NW-1006`、`NW-1012`、`NW-1031`。`NW-1028`、`NW-1049`、`NW-1045` 由及时采购订单覆盖；`NW-1018` 和 `NW-1045` 用于检验晚到采购订单的处理。

评估器包含 8 个精确匹配评分点：活动目标、组件需求和有效可用量、采购申请、调拨请求、及时采购订单与晚到订单处理、排除项、组件最终动作、以及采购成本和数量等汇总指标。原始权重分别为 2、2、3、3、2、2、3、2。

常见错误包括把隔离库存当作可用、未扣除安全库存、使用错误仓库的采购订单、把晚到订单算作覆盖、调拨时未保留供给仓安全库存、或把不同目标仓的同一 SKU 合并计算。

### 迁移设计

本测试任务以 `train_002` 和 `train_004` 为迁移锚点。`train_002` 可迁移有效可用量公式、同仓及时采购订单覆盖、采购成本、超储与及时订单排除、以及先调拨后采购的处理习惯。`train_004` 可迁移跨仓调拨和按仓库分开计算库存状态的经验。

依赖迁移的评分点包括 `SP002`、`SP003`、`SP004`、`SP005`、`SP006` 和 `SP007`。任务本身仍需要新的数据探索，因为它使用了不同 BOM、两个目标仓、不同采购订单时点、更大的组件集合，以及需要按目标仓区分的组件行。

### 构造记录

作者：task-builder subagent `test_002`。创建日期：2026-06-01。更新日期：2026-06-01。主要变更：创建服务备件活动补货测试任务，覆盖 BOM 需求、两个仓库、采购订单时点、短缺、调拨、采购申请、排除项、采购总成本和 8 个精确匹配评分点。
