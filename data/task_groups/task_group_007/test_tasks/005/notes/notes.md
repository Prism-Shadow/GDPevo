# test_005 Notes

## English

This hidden construction note documents `test_005`, an integrated daily operations board for wave `TEST_BOARD_F` in `task_group_007`. It belongs to `SCN_007_erp_inventory_order_fulfillment` and combines the three recurring task families: fulfillment control, replenishment gaps, and supplier incident escalation.

The solver-visible materials are `input/prompt.txt`, `input/payloads/daily_board_memo.json`, `input/payloads/answer_template.json`, and the shared ERP API. The solver must inspect current order, customer, product, inventory, supplier, purchase-order, and incident data through public API endpoints rather than reading hidden env files. The output is a structured board with per-order decisions, replenishment gaps, incident escalations, ranked priority actions, and summary counts.

Material map: `/orders?wave=TEST_BOARD_F` defines the order population; `/customers` provides account and risk fields; `/products` provides active status, supplier ID, safety stock, cost, and weight; `/inventory` supports effective availability; `/incidents` and `/suppliers` support the escalation section. The local board memo fixes the board date, wave, risk supplier IDs, and allowed decision enums. The solution first builds one evidence row per order, then assigns the most specific decision: customer-risk orders become `customer_hold`, inactive product evidence becomes `data_review`, supplier quality exposure becomes `quality_review`, pure stock gaps become `backorder_or_replenish`, and only clean orders are `release`.

Evaluation uses eight exact-match scoring points with total raw weight 18: board identity (1), per-order decisions (3), reason codes and risk suppliers (3), replenishment gap lines (3), incident escalation suppliers (2), ranked priority actions (2), summary counts (2), and integrated consistency across decisions, shortage lines, and escalation suppliers (2). The evaluator compares each section at field level and returns a structured zero-score JSON for malformed or incomplete predictions rather than raising missing-key errors. The task is intentionally integrated: a direct solver may discover some facts locally, but high-value points benefit from train-derived experience about effective stock, customer overrides, incident filtering, supplier quality control, stable sorting, and controlled JSON output.

Solution basis: the board has twelve orders. `SO-70005` and `SO-70082` are customer holds; `SO-70047` is the only clean release; `SO-70054` is a stock-only replenishment case; `SO-70061` and `SO-70075` require data review because inactive products are involved; the remaining quality-review orders carry supplier-risk evidence from `SUP-003`, `SUP-006`, or `SUP-010`. The replenishment gap section includes only actual shortage lines after effective availability is computed. Incident escalations use the same three supplier-quality metrics as `train_005`, and priority actions are ranked as quality holds first, replenishment next, and customer-hold clearance third.

Transfer anchors: `train_001` anchors fulfillment and customer overrides; `train_002` anchors shortage and replenishment reasoning; `train_003` anchors incident aggregation; `train_004` anchors effective availability and allocation decisions; `train_005` anchors supplier quality controls. Task-specific difficulty comes from the larger `TEST_BOARD_F` order set and the need to combine three operation families in one board.

Construction record: authored as a task-builder rework for `test_005`; created and updated on 2026-06-01.

## Chinese

本隐藏说明记录 `test_005`，即 `task_group_007` 中 `TEST_BOARD_F` 波次的每日综合运营看板。该任务属于 `SCN_007_erp_inventory_order_fulfillment`，同时覆盖三个复用业务族：履约控制、补货缺口和供应商事件升级。

求解者可见材料包括 `input/prompt.txt`、`input/payloads/daily_board_memo.json`、`input/payloads/answer_template.json` 和共享 ERP API。求解者需要通过公开 API 查询当前订单、客户、产品、库存、供应商、采购订单和事件数据，不应读取隐藏的 env 文件。输出是结构化看板，包括订单级决策、补货缺口、事件升级供应商、排序后的优先动作和汇总计数。

材料映射：`/orders?wave=TEST_BOARD_F` 定义订单集合；`/customers` 提供账户和风险字段；`/products` 提供启用状态、供应商、安全库存、成本和重量；`/inventory` 用于计算有效库存；`/incidents` 和 `/suppliers` 用于事件升级部分。本地看板备忘录固定看板日期、波次、风险供应商 ID 和允许的决策枚举。解题时先为每个订单建立证据行，再选择最具体的决策：客户风险订单为 `customer_hold`，涉及停用产品为 `data_review`，供应商质量暴露为 `quality_review`，纯库存缺口为 `backorder_or_replenish`，只有无风险订单才是 `release`。

评估包含 8 个精确匹配评分点，原始总权重为 18：看板日期和波次（1）、逐订单决策（3）、原因码和风险供应商（3）、补货缺口行（3）、事件升级供应商（2）、排序后的优先动作（2）、汇总计数（2），以及决策、短缺和升级供应商之间的综合一致性（2）。评估器按字段比较各部分，并在预测缺字段或 JSON 格式错误时返回结构化零分而不是抛出缺键异常。该任务是综合型测试：直接求解者可以发现部分事实，但高价值评分点明显受益于训练中学到的有效库存、客户覆盖、事件筛选、供应商质量控制、稳定排序和受控 JSON 输出经验。

答案依据：该看板共有 12 个订单。`SO-70005` 和 `SO-70082` 是客户冻结；`SO-70047` 是唯一可放行订单；`SO-70054` 是单纯库存补货；`SO-70061` 和 `SO-70075` 因停用产品需要 data review；其他 quality-review 订单来自 `SUP-003`、`SUP-006` 或 `SUP-010` 的供应商质量风险。补货缺口部分只列出按 effective availability 计算后真实短缺的行。事件升级复用 `train_005` 的三类供应商质量指标，优先动作按质量风险冻结、补货、客户冻结清理的顺序排列。

迁移锚点：`train_001` 支撑履约和客户覆盖规则；`train_002` 支撑短缺和补货判断；`train_003` 支撑事件聚合；`train_004` 支撑有效库存和调拨决策；`train_005` 支撑供应商质量控制。任务自身难点来自更大的 `TEST_BOARD_F` 订单集合，以及必须把三个业务族合并成一个看板。

构建记录：由 `test_005` task-builder rework 创建；创建和更新日期为 2026-06-01。
