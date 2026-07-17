# Notes / 说明

## Data Lineage

English: This task is built from the ApexCloud Retention Operations environment in `task_group_004/env`. The answer uses the public API data surfaces represented by accounts, account metrics, support tickets, NPS responses, billing snapshots, and A/R aging. The assessment date is 2026-06-30 and the operating period is 2026-04-01 through 2026-06-30.

中文：本任务来自 `task_group_004/env` 中的 ApexCloud Retention Operations 环境。标准答案使用账户、账户月度指标、支持工单、NPS 回复、账单快照和应收账款账龄等公开 API 数据面。评估日期为 2026-06-30，分析期间为 2026-04-01 至 2026-06-30。

## Task Definition

English: The solver must review eight North America account IDs and return the top five accounts by renewal risk, including score, level, primary action, ARR, latest valid NPS, clean ticket count, overdue balance, reason codes, portfolio summary, and model checks.

中文：求解者需要审阅八个北美账户 ID，并返回续约风险最高的五个账户，包括风险分、等级、主要动作、ARR、最新有效 NPS、干净工单数、逾期余额、原因代码、组合汇总和模型检查项。

## Scenario Fit

English: The scenario fits a VP Customer Success workflow before a retention standup. It requires combining customer health, finance, support, and renewal context into a short action queue.

中文：该场景符合客户成功副总裁在留存会议前准备风险队列的工作流，需要把客户健康、财务、支持和续约背景合并为简短的行动队列。

## Material Map

English: `prompt.txt` gives the business request and output contract. `answer_template.json` shows the JSON shape and controlled enums. `answer.json` is the deterministic gold answer. `eval.sh` scores exact business outcomes and accepts an optional prediction path.

中文：`prompt.txt` 给出业务请求和输出契约。`answer_template.json` 展示 JSON 结构与受控枚举。`answer.json` 是确定性的标准答案。`eval.sh` 对业务结果做精确评分，并支持可选的预测文件路径。

## Solution And Evaluation Basis

English: Current ARR is taken from Q2 posted billing snapshots on 2026-06-30. Clean tickets exclude spam, duplicates, and cancelled records. Latest NPS ignores retracted responses and uses the last valid response in the Q2 period. Overdue balance is the 61-90 plus 90-plus A/R buckets at 2026-06-30. Risk ranking uses the shared retention-risk business rules, then sorts by score, current ARR, and account ID.

中文：当前 ARR 取自 2026-06-30 的 Q2 已发布账单快照。干净工单排除垃圾、重复和已取消记录。最新 NPS 忽略撤回回复，并取 Q2 期间最后一个有效回复。逾期余额为 2026-06-30 时 61-90 天与 90 天以上账龄桶之和。风险排名使用共享留存风险业务规则，然后按分数、当前 ARR 和账户 ID 排序。

## Transfer Design

English: This train task teaches billing ARR precedence, clean-ticket filtering, retracted-NPS handling, overdue collections priority, tenure risk direction, and controlled action enums. These conventions transfer to later strategic save-plan and executive watchlist tasks while leaving account-specific exploration necessary.

中文：本训练任务强化账单 ARR 优先级、干净工单过滤、撤回 NPS 处理、逾期收款优先级、 tenure 风险方向和受控动作枚举。这些规则会迁移到后续战略挽留计划和高管观察清单任务，但仍需要针对新账户重新探索数据。

## Construction Record

English: Builder `train_001` created only files under `train_tasks/001`. The evaluator embeds the expected business answer so it can score the bundled answer at full credit without depending on the live service.

中文：构建者 `train_001` 仅在 `train_tasks/001` 下创建文件。评估器内嵌预期业务答案，因此无需依赖实时服务即可给随附标准答案满分。

English: Updated 2026-06-01 to add neutral `policy_codes` for retention risk model, ARR source, support hygiene, and action-priority conventions. These codes are hidden in train answers for later skill transfer rather than exposed as test instructions.

中文：2026-06-01 更新：增加中性的 `policy_codes`，覆盖留存风险模型、ARR 来源、支持数据清洗和行动优先级约定。这些编码通过训练答案供后续技能迁移使用，而不是作为测试说明暴露。
