# Test 005 Notes / 测试 005 说明

## English

Lineage: This task implements the stateful ticket-correction workflow for `test_005` in the SQL database analytics task group. The final design, direct builder assignment, prompt, answer, and evaluator all use LumaForms.

Task definition: The solver must apply approved data-quality ticket correction case `DQ-TKT-2026-05-D`, then recompute the May 2026 LumaForms customer-impacting defect backlog and notification list from the shared SQLite database.

Scenario fit: The task exercises approved stateful repair, safe SQL updates, duplicate suppression, customer-impacting ticket filtering, month-window aggregation, SLA breach calculation, and account notification selection.

Material map: The visible prompt is `input/prompt.txt`; the output contract is `input/payloads/answer_template.json`; the canonical response is `output/answer.json`; stateful grading is implemented by `eval/eval.sh` and `eval/evaluate.py`.

Solution and evaluation basis: The approved case marks `TKT-DQ-MAY-D-001` and `TKT-DQ-MAY-D-002` as duplicates of `TKT-DQ-MASTER-05-D`, with audit fields copied from `data_quality_cases`. Qualified May LumaForms customer-impacting defect tickets exclude canceled tickets, internal or test accounts, duplicate tickets, non-impacting tickets, and non-defect categories. Backlog is measured as qualified tickets unresolved as of `2026-06-01 00:00:00`. SLA breach rate is the breached share of all qualified May tickets after the correction.

Transfer design: This test reuses the train-stateful pattern of exact approved-case updates, audit-field discipline, duplicate exclusions, customer-impacting defect filters, and recomputation after state change. The transfer challenge is identifying the new product, period, target rows, and resulting account notification list.

Construction record: Created only under `task_group/task_group_022/test_tasks/005/`. The expected metrics after correction are two changed tickets, twenty qualified tickets, backlog counts `P1=1`, `P2=2`, `P3=1`, `P4=4`, and SLA breach rate `0.8000`. Notification accounts are the external accounts with end-of-May backlog tickets, sorted by backlog count, highest severity, and account id.

## 中文

来源：本任务实现 SQL 数据库分析任务组中 `test_005` 的有状态工单修正流程。最终设计、直接构建指令、提示、答案和 evaluator 均使用 LumaForms。

任务定义：求解者需要应用已批准的数据质量工单修正案例 `DQ-TKT-2026-05-D`，然后基于共享 SQLite 数据库重新计算 2026 年 5 月 LumaForms 的客户影响型缺陷积压和通知名单。

场景匹配：本任务覆盖已批准修复、安全 SQL 更新、重复工单排除、客户影响型工单筛选、月度窗口聚合、SLA 违约率计算以及需要通知的账户选择。

材料映射：可见提示为 `input/prompt.txt`；输出契约为 `input/payloads/answer_template.json`；标准答案为 `output/answer.json`；有状态评分由 `eval/eval.sh` 和 `eval/evaluate.py` 实现。

解法与评估依据：已批准案例把 `TKT-DQ-MAY-D-001` 和 `TKT-DQ-MAY-D-002` 标记为 `TKT-DQ-MASTER-05-D` 的重复工单，并从 `data_quality_cases` 写入审计字段。合格的 5 月 LumaForms 客户影响型缺陷工单会排除取消工单、内部或测试账户、重复工单、非客户影响工单和非缺陷类别。积压按截至 `2026-06-01 00:00:00` 尚未解决的合格工单计算。SLA 违约率按修正后全部合格 5 月工单中的违约占比计算。

迁移设计：本测试迁移训练任务中的精确已批准案例更新、审计字段要求、重复工单排除、客户影响型缺陷筛选和状态变更后重算流程。迁移难点是识别新的产品、时间窗口、目标行和最终账户通知名单。

构建记录：仅在 `task_group/task_group_022/test_tasks/005/` 下创建文件。修正后的预期指标为变更 2 张工单、20 张合格工单、积压计数 `P1=1`、`P2=2`、`P3=1`、`P4=4`，SLA 违约率为 `0.8000`。通知账户是截至 5 月末仍有积压工单的外部账户，并按积压数量、最高严重级别和账户 id 排序。
