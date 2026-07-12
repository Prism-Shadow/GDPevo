# Train 005 Notes

## English

Lineage: This task follows the stateful SQL correction pattern in the task group design. The original design table named LumaForms for train_005, but the builder request for this folder explicitly specifies AtlasDB, so the constructed task uses AtlasDB.

Task definition: The solver must apply approved data-quality ticket duplicate case `DQ-TKT-2026-03-B`, then recompute the March 2026 AtlasDB customer-impacting defect backlog from the shared SQLite database.

Scenario fit: The task exercises approved stateful repair, safe SQL updates, duplicate suppression, customer-impacting support-ticket filtering, month-window aggregation, SLA breach calculation, and account notification selection.

Material map: The visible prompt is `input/prompt.txt`; the output contract is `input/payloads/answer_template.json`; the canonical response is `output/answer.json`; stateful grading is implemented by `eval/eval.sh` and `eval/evaluate.py`.

Solution and evaluation basis: The approved case marks `TKT-DQ-MAR-B-001`, `TKT-DQ-MAR-B-002`, and `TKT-DQ-MAR-B-003` as duplicates of `TKT-DQ-MASTER-03-B`, with audit fields copied from `data_quality_cases`. Qualified March AtlasDB customer-impacting defect tickets exclude canceled tickets, internal or test accounts, duplicate tickets, non-impacting tickets, and non-defect categories. Backlog is measured as qualified tickets unresolved as of `2026-04-01 00:00:00`. SLA breach rate is the breached share of all qualified March tickets after the correction.

Transfer design: Test tasks can reuse the safe approved-case update pattern, audit-field discipline, duplicate exclusions, customer-impacting defect filters, and recomputation flow while changing product, period, and target rows.

Construction record: The expected metrics after correction are three changed tickets, twenty-two qualified tickets, backlog counts `P1=0`, `P2=1`, `P3=4`, `P4=5`, and SLA breach rate `0.7273`. Notification accounts are the external accounts with end-of-March backlog tickets, sorted by backlog count, highest severity, and account id.

## 中文

血缘说明：本任务沿用任务组中的有状态 SQL 修正模式。设计表最初把 train_005 写为 LumaForms，但本文件夹的构建请求明确要求 AtlasDB，因此最终任务使用 AtlasDB。

任务定义：求解者需要应用已批准的数据质量工单去重案例 `DQ-TKT-2026-03-B`，然后基于共享 SQLite 数据库重新计算 2026 年 3 月 AtlasDB 的客户影响型缺陷积压。

场景匹配：本任务覆盖已批准修复、安全 SQL 更新、重复工单排除、客户影响型支持工单筛选、月度窗口聚合、SLA 违约率计算以及需要通知的账户选择。

材料映射：可见提示为 `input/prompt.txt`；输出契约为 `input/payloads/answer_template.json`；标准答案为 `output/answer.json`；有状态评分由 `eval/eval.sh` 和 `eval/evaluate.py` 实现。

解法与评估依据：已批准案例把 `TKT-DQ-MAR-B-001`、`TKT-DQ-MAR-B-002`、`TKT-DQ-MAR-B-003` 标记为 `TKT-DQ-MASTER-03-B` 的重复工单，并从 `data_quality_cases` 写入审计字段。合格的 3 月 AtlasDB 客户影响型缺陷工单会排除取消工单、内部或测试账户、重复工单、非客户影响工单和非缺陷类别。积压按截至 `2026-04-01 00:00:00` 尚未解决的合格工单计算。SLA 违约率按修正后全部合格 3 月工单中的违约占比计算。

迁移设计：测试任务可以迁移安全的已批准案例更新方式、审计字段要求、重复工单排除、客户影响型缺陷筛选和修正后重算流程，同时更换产品、时间窗口和目标行。

构建记录：修正后的预期指标为变更 3 张工单、22 张合格工单、积压计数 `P1=0`、`P2=1`、`P3=4`、`P4=5`，SLA 违约率为 `0.7273`。通知账户是截至 3 月末仍有积压工单的外部账户，并按积压数量、最高严重级别和账户 id 排序。
