# test_004 Notes

## English

Data/source lineage: This task belongs to `SCN_007_erp_inventory_order_fulfillment` and uses source examples `E001`, `E002`, and `E003`. The assigned brief is `test_004` in `scratch/task_builder_briefs.md`: build an order release task for `TEST_QUALITY_E` that combines fulfillment checks with supplier quality holds and active severe incidents. The shared generated environment under `task_group/task_group_007/env/` supplies the authoritative ERP API data. Task-local solver-visible payloads are `input/prompt.txt`, `input/payloads/release_control_memo.md`, and `input/payloads/answer_template.json`.

Task definition: The solver must inspect live API records for `TEST_QUALITY_E`, classify each order as `RELEASE_TO_SHIP`, `MANUAL_REVIEW`, or `BACKORDER_INVENTORY`, identify blocked SKUs, attach controlled reason codes, and produce a supplier-risk rollup. The expected JSON includes per-order decisions, inventory status, quality-hold suppliers, active severe incident IDs, risk supplier IDs, next actions, and summary counts.

Scenario fit and material map: This is an ERP release-control workflow using `/orders?wave=TEST_QUALITY_E`, `/customers/<customer_id>`, `/products/<sku>`, `/inventory?warehouse_id=&sku=`, `/suppliers`, and `/incidents?status=open`. It combines fulfillment control from `train_001` and `train_004` with supplier quality and incident analysis from `train_005` and `train_003`.

Solution basis: Effective available stock is `on_hand - reserved - quarantined - safety_stock`. An order has `SHORTAGE` when any ordered SKU is below the order quantity at the order warehouse. High and critical open incidents are active severe incidents. The supplier-risk rollup covers suppliers represented in the wave by ordered SKUs under supplier quality hold or by active severe incidents on ordered SKUs. Account blocked, account review, supplier quality hold, inactive product, and active severe incident conditions route covered orders to release-control review; uncovered orders without manual-review overrides become `BACKORDER_INVENTORY`; fully covered orders without risk become `RELEASE_TO_SHIP`.

Standard answer summary: 12 orders; 6 backorders, 5 manual reviews, and 1 release. Risk suppliers are `SUP-002`, `SUP-003`, `SUP-007`, `SUP-009`, `SUP-010`, and `SUP-011`. Active severe incidents counted in the wave are `INC-90028`, `INC-90043`, `INC-90048`, `INC-90154`, `INC-90174`, `INC-90182`, and `INC-90201`.

Evaluation is exact-match with 8 scoring points and total raw weight 17: SP1 release decisions, weight 3; SP2 inventory statuses and blocked SKUs, weight 2; SP3 reason code sets, weight 3; SP4 quality-hold supplier mapping, weight 2; SP5 active severe incident IDs and risk supplier IDs, weight 2; SP6 risk supplier rollup, weight 3; SP7 next actions, weight 1; SP8 summary counts and order-id sets, weight 1.

Likely pitfalls: using on-hand stock instead of effective availability; ignoring safety stock; treating only `critical` as severe and missing `high`; applying active severe incidents at whole-supplier level instead of ordered-SKU evidence for the rollup; missing inactive product `NW-1019`; allowing account review orders to backorder without release-control review.

Transfer design: `train_001` anchors customer override and fulfillment outcome conventions. `train_004` anchors effective availability and backorder/manual-review distinctions. `train_005` anchors supplier quality holds and incident-linked release control. `train_003` reinforces incident filtering and high/critical severity treatment. Transfer-dependent points are SP1, SP3, SP4, SP5, and SP6; SP2 also benefits from train-derived effective-stock calculation.

Construction record: Author `test_004` task-builder subagent. Created 2026-06-01. Updated 2026-06-01. Built only `task_group/task_group_007/test_tasks/004/` and `scratch/task_builder_reports/test_004.md`.

## 中文

数据来源：本任务属于 `SCN_007_erp_inventory_order_fulfillment`，来源样例为 `E001`、`E002`、`E003`。任务简述来自 `scratch/task_builder_briefs.md` 中的 `test_004`：围绕 `TEST_QUALITY_E` 订单波次，将履约放行检查、供应商质量冻结和仍处于开启状态的严重事件结合起来。共享环境 `task_group/task_group_007/env/` 提供权威 ERP API 数据；任务本地可见材料包括 `prompt.txt`、`release_control_memo.md` 和 `answer_template.json`。

任务定义：求解者需要查询实时 API，判断每个订单是放行、人工复核还是库存回补，并给出库存阻塞 SKU、受控原因码、质量冻结供应商、严重事件编号、风险供应商以及汇总计数。输出必须符合模板中的 JSON 结构。

场景适配：该任务属于 ERP 放行控制流程，结合了训练任务中的履约控制、有效库存计算、客户状态覆盖、供应商质量冻结和事件分析经验。它需要跨订单、客户、产品、库存、供应商和事件多类对象协调，不是单一文件查找。

答案依据：有效库存为 `on_hand - reserved - quarantined - safety_stock`。若任一订单行在请求仓库的有效库存低于订购数量，则该订单库存状态为 `SHORTAGE`。开启状态且严重级别为 high 或 critical 的事件视为活跃严重事件。风险供应商汇总只覆盖本波次订购 SKU 中被供应商质量冻结影响，或该订购 SKU 上存在活跃严重事件的供应商。

标准答案包含 12 个订单，结果为 6 个库存回补、5 个人工复核、1 个放行。风险供应商为 `SUP-002`、`SUP-003`、`SUP-007`、`SUP-009`、`SUP-010`、`SUP-011`。本波次计入的活跃严重事件为 `INC-90028`、`INC-90043`、`INC-90048`、`INC-90154`、`INC-90174`、`INC-90182`、`INC-90201`。

评估采用精确匹配，共 8 个评分点，原始总权重 17：SP1 订单放行结果，权重 3；SP2 库存状态和阻塞 SKU，权重 2；SP3 每个订单的原因码集合，权重 3；SP4 质量冻结供应商映射，权重 2；SP5 活跃严重事件和风险供应商，权重 2；SP6 风险供应商汇总，权重 3；SP7 下一步动作，权重 1；SP8 汇总计数和订单集合，权重 1。

迁移设计：`train_001` 支撑客户覆盖规则和履约结果分类，`train_004` 支撑有效库存与回补/复核区分，`train_005` 支撑供应商质量冻结和事件到放行控制的连接，`train_003` 强化严重级别和事件筛选习惯。高权重的 SP1、SP3、SP4、SP5、SP6 都依赖训练迁移；SP2 也依赖有效库存经验。

构建记录：作者为 `test_004` task-builder subagent。创建日期 2026-06-01，更新日期 2026-06-01。仅构建 `task_group/task_group_007/test_tasks/004/` 和 `scratch/task_builder_reports/test_004.md`。
