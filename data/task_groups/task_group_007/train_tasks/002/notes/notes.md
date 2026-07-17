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

Major changes: Created the task folder, local production memo, answer template, standard answer, exact-match evaluator, and bilingual notes for the kit replenishment task.

## 中文

### 数据和来源

本任务属于 `task_group_007`，场景为 `SCN_007_erp_inventory_order_fulfillment`，设计依据来自源示例 `E001`、`E002` 和 `E003`。任务对应任务组中的补货与调拨类工作：根据套件 BOM 展开需求，重建有效库存，检查及时采购订单覆盖，选择仓库调拨，并排除不应补货的过量库存物料。

共享环境位于 `task_group/task_group_007/env/`。求解器可见的本地材料只有 `input/payloads/production_memo.json` 和 `input/payloads/answer_template.json`。求解器需要通过共享 API 查询 BOM、产品主数据、库存、采购订单和仓库信息。

### 任务定义

生产计划要求为 WH_WEST 的两个套件生产批次准备补货方案：

- `BOM-300`，`Retrofit Kit 1`，18 套，目标日期 `2026-06-06`。
- `BOM-301`，`Emergency Kit 2`，18 套，目标日期 `2026-06-10`。

标准输出是结构化 JSON，包括套件目标、组件覆盖情况、调拨请求、采购申请、排除组件和汇总指标。输出格式由 `input/payloads/answer_template.json` 规定。

### 场景匹配和材料说明

该任务是典型 ERP 库存补货任务，与源示例 `E001` 的库存、需求和排除逻辑一致；同时沿用了 `E002` 的 API 查询工作方式，因为本地备忘录并不包含全部事实。`E003` 的事故分析不在本任务中直接使用，但仍属于同一共享业务环境。

关键材料和接口包括：

- `production_memo.json`：给出两个 BOM、生产数量、目标日期、计划仓库和 API 地址。
- `GET /boms/<bom_id>`：获取组件 SKU 和单套用量。
- `GET /products/<sku>`：获取安全库存、过量库存阈值、供应商和单位成本。
- `GET /inventory?warehouse_id=&sku=`：获取各仓库的现有、预留和隔离库存。
- `GET /purchase_orders?sku=`：获取采购订单状态、预计到货日期、数量、仓库和供应商。

### 答案和评估依据

隐藏答案使用以下业务约定：

- 有效可用库存为 `on_hand - reserved - quarantined - safety_stock`。
- 组件需求为 BOM 单套用量乘以目标生产数量，并在两个目标批次之间合并。
- 及时采购订单必须是同仓库、状态为 `open` 或 `confirmed`，且 ETA 不晚于相关生产日期；`received` 和 `cancelled` 不作为未来覆盖。
- 调拨使用其他仓库扣除安全库存后的正有效可用量，并按该 SKU 的有效可用量从大到小分配。
- 采购申请只覆盖目标仓有效库存、及时采购订单和调拨之后仍未覆盖的数量。
- 目标仓已经超过过量库存阈值且无剩余缺口的组件应排除，不再采购。
- 金额四舍五入到两位小数。

本任务的组件总需求为 `NW-1005` 90、`NW-1014` 216、`NW-1034` 72、`NW-1039` 144、`NW-1049` 144、`NW-1050` 108。标准答案为 `NW-1014`、`NW-1034` 和 `NW-1050` 创建采购申请；为 `NW-1014`、`NW-1049` 和 `NW-1050` 创建调拨；排除 `NW-1005`，因为 `PO-50066` 已及时覆盖缺口；排除 `NW-1039`，因为 WH_WEST 已过量且有效库存覆盖需求。

评估器包含 8 个精确匹配评分点：套件目标、组件需求和有效库存、采购申请、调拨请求、`NW-1005` 的及时 PO 覆盖、`NW-1039` 的过量排除、六个 SKU 的最终动作和数量，以及汇总指标。常见错误包括只看现有库存、不扣预留和隔离库存、把已收货或取消的 PO 当作未来覆盖、把 `NW-1050` 的迟到 PO 算入覆盖、忽略可调拨库存，或遗漏 `NW-1039` 的过量库存排除。

### 迁移设计

作为训练任务，`train_002` 用于锚定补货与调拨类任务的可迁移约定。技能构建器通过比较尝试答案和标准答案，应能归纳出有效库存公式、同仓及时 PO 覆盖规则、迟到或无效 PO 的处理、采购前优先使用可调拨有效余量，以及排除已覆盖或过量库存 SKU 的做法。这些经验主要迁移到 `test_002`，也会帮助 `test_005` 的综合运营看板任务。

### 构建记录

作者：task-builder subagent `train_002`。

创建日期：2026-06-01。

更新日期：2026-06-01。

主要变更：创建任务目录、本地生产备忘录、答案模板、标准答案、精确匹配评估器和双语说明。
