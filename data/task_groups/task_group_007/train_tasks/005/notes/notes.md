# train_005 Notes

## English

This hidden construction note documents `train_005`, a supplier quality-hold and replenishment-freeze task for `task_group_007` under scenario `SCN_007_erp_inventory_order_fulfillment`. It is derived from source examples `E002` and `E003`: the task combines ERP decision controls with supplier incident analysis. The solver-visible materials are `input/prompt.txt`, `input/payloads/quality_hold_review_memo.json`, `input/payloads/answer_template.json`, and the shared ERP API. The solver must not inspect `env/` files directly.

The business task is to review selected suppliers over the window `2026-03-01` through `2026-06-30`, identify recent RMA/work-order quality risk, connect risky suppliers to open or confirmed purchase orders, and output controlled replenishment decisions. The required output includes the analysis window, supplier-level incident metrics, quality status, affected SKUs, sample incident IDs, held PO IDs, release supplier IDs, and summary rollups. The gold answer reviews `SUP-003`, `SUP-006`, and `SUP-010`: `SUP-003` is on `quality_hold` and freezes new replenishment; `SUP-006` is a watch supplier with severe recent evidence requiring buyer review; `SUP-010` remains monitor-only despite recent incidents because its current quality status and incident mix do not justify a replenishment freeze.

Material map: `/incidents` provides incident type, supplier, SKU, status, severity, and open dates; `/suppliers` provides supplier names and quality status; `/purchase_orders` provides open and confirmed POs that may need a hold; `/products` provides SKU-to-supplier linkage when needed. The task-local memo fixes the review window and target suppliers but does not reveal the answer. Incidents outside the date window are excluded before counting; sample incident IDs are sorted and capped at five. Held PO IDs are limited to current open or confirmed POs for suppliers whose decision is `freeze_new_replenishment` or `buyer_review_required`.

Evaluation uses eight exact-match scoring points with total raw weight 18: analysis window (1), supplier identities (2), incident/RMA/severity/open counts (3), quality statuses (2), affected SKU and sample incident sets (2), controlled replenishment decisions (3), held PO IDs globally and by supplier (3), and release suppliers plus summary rollups (2). The evaluator compares only the fields relevant to each scoring point and returns a structured zero-score JSON for malformed or incomplete predictions instead of crashing. Common pitfalls are using the wrong date window, mixing supplier IDs with similar names, treating all POs as hold candidates, ignoring supplier quality status, counting closed/cancelled POs as hold candidates, including more than five sample incidents, or producing free-form decisions outside the allowed enum.

Transfer design: this train task anchors supplier-quality controls for later tests. A solver comparing a blind attempt to the answer should infer that quality holds and recent severe RMA patterns can override normal replenishment, that incident filtering precedes aggregation, and that PO hold decisions should be tied to open or confirmed supplier POs.

Construction record: authored as a task-builder rework for `train_005`; created and updated on 2026-06-01.

## Chinese

本隐藏说明记录 `train_005`，它属于 `task_group_007` 和场景 `SCN_007_erp_inventory_order_fulfillment`。任务来源于示例 `E002` 和 `E003` 的业务分布：一方面需要做 ERP 控制决策，另一方面需要根据供应商事件记录判断质量风险。求解者可见材料只有 `input/prompt.txt`、`input/payloads/quality_hold_review_memo.json`、`input/payloads/answer_template.json` 和共享 ERP API；求解者不应直接查看 `env/` 目录。

业务目标是在 `2026-03-01` 到 `2026-06-30` 的窗口内审查指定供应商，识别近期 RMA 和工单质量风险，把风险供应商关联到 open 或 confirmed 状态的采购订单，并输出受控的补货控制决策。标准输出包括分析窗口、供应商事件指标、质量状态、受影响 SKU、样例事件 ID、冻结 PO ID、可放行供应商 ID 和汇总计数。标准答案审查 `SUP-003`、`SUP-006` 和 `SUP-010`：`SUP-003` 处于 `quality_hold`，因此冻结新补货；`SUP-006` 是 watch 供应商且有近期严重证据，需要 buyer review；`SUP-010` 虽有近期事件，但根据当前质量状态和事件组合只需 monitor。

材料映射：`/incidents` 提供事件类型、供应商、SKU、状态、严重度和开启日期；`/suppliers` 提供供应商名称和质量状态；`/purchase_orders` 提供需要判断是否冻结的采购订单；`/products` 可用于补充 SKU 和供应商关系。本地备忘录只固定审查窗口和目标供应商，不泄露答案。事件必须先按日期窗口筛选再计数；样例 incident ID 排序且最多保留 5 个。冻结 PO 只包括当前 open 或 confirmed 且对应供应商决策为 `freeze_new_replenishment` 或 `buyer_review_required` 的采购订单。

评估包含 8 个精确匹配评分点，原始总权重为 18：分析窗口（1）、供应商身份（2）、incident/RMA/严重/未结计数（3）、质量状态（2）、受影响 SKU 和样例事件集合（2）、受控补货决策（3）、全局和逐供应商冻结 PO（3）、可放行供应商和汇总计数（2）。评估器只比较每个评分点对应字段，并在预测缺字段或 JSON 格式错误时返回结构化零分而不是崩溃。常见错误包括使用错误日期窗口、混淆相似供应商名称、把所有采购订单都当作冻结候选、忽略供应商质量状态、把 closed/cancelled PO 计入冻结列表、样例事件超过 5 个，或输出模板未允许的自由文本决策。

迁移设计：该训练任务为后续测试中的供应商质量控制提供锚点。求解者在盲做并对照答案后，应能归纳出质量冻结和近期严重 RMA 会覆盖普通补货流程、事件必须先按窗口筛选再聚合、PO 冻结只应关联 open 或 confirmed 的相关供应商采购订单。

构建记录：由 `train_005` task-builder rework 创建；创建和更新日期为 2026-06-01。
