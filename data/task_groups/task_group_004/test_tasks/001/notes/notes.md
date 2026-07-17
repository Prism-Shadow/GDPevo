# Strategic Renewal Save Plan Notes

## English

### Data Lineage
The task uses the ApexCloud Retention Operations API backed by the task_group_004 environment data. Account profile data comes from `accounts.json`; billing ARR comes from posted billing snapshots; support quality comes from `support_tickets.json`; NPS comes from `nps_responses.json`; usage comes from `account_metrics.json`; and overdue receivables come from `ar_aging.json`.

### Task Definition
The solver must review 10 named strategic/enterprise renewal-cycle accounts as of 2026-09-30, rank them by the shared retention-risk policy, and return the top 6 save-plan accounts with operational metrics, actions, and portfolio totals.

### Scenario Fit
This fits a CRO save-plan workflow because it combines renewal timing, collections exposure, support health, customer sentiment, usage trajectory, and ARR size into a single intervention queue.

### Material Map
- `input/prompt.txt`: solver-facing business request and output constraints.
- `input/payloads/answer_template.json`: JSON response shape.
- `output/answer.json`: canonical expected result.
- `eval/eval.sh`: exact-match business-result evaluator with optional prediction path.

### Solution And Evaluation Basis
The canonical answer uses 2026-09-30 posted billing ARR, Q3 2026 clean support tickets, Q3 valid NPS responses, Q3 account usage, and A/R aging as of 2026-09-30. The six selected accounts are ordered by risk score descending, then current ARR descending, then account_id ascending. The evaluator gives weighted credit for ordered accounts, scores and levels, actions, ARR and ARR-at-risk, support and NPS metrics, overdue amounts, summary action counts, and quality checks.

### Transfer Design
The task transfers patterns from the retention scoring and action-priority training tasks: use posted billing as the ARR source of truth, filter invalid support/NPS records, apply the shared risk/action policy, and summarize the portfolio without exposing the hidden formula in the prompt.

### Construction Record
Built for task_group_004/test_tasks/001 only. No environment files were copied into payloads. The evaluator defaults to this task's own `output/answer.json` and should score it at full credit.

## 中文

### 数据血缘
本任务使用 task_group_004 环境中的 ApexCloud Retention Operations API。账户资料来自 `accounts.json`，当前 ARR 来自已发布的 billing snapshot，支持质量来自 `support_tickets.json`，NPS 来自 `nps_responses.json`，使用率来自 `account_metrics.json`，逾期应收来自 `ar_aging.json`。

### 任务定义
求解者需要以 2026-09-30 为评估日，审查 10 个指定的战略或企业续约周期账户，按照共享留存风险规则排序，并返回前 6 个需要 save-plan 干预的账户及其运营指标、行动和组合汇总。

### 场景适配
该场景符合 CRO 的续约挽留工作流，因为它把续约窗口、收款风险、支持健康度、客户情绪、使用趋势和 ARR 规模合并成一个可执行的干预队列。

### 材料映射
- `input/prompt.txt`：面向求解者的业务请求和输出约束。
- `input/payloads/answer_template.json`：JSON 答案结构。
- `output/answer.json`：标准答案。
- `eval/eval.sh`：支持可选预测路径的精确业务结果评分脚本。

### 解法与评估依据
标准答案使用 2026-09-30 的已发布 billing ARR、2026 年第三季度 clean support tickets、第三季度有效 NPS、第三季度账户使用率，以及 2026-09-30 的 A/R aging。前 6 个账户按风险分降序、当前 ARR 降序、account_id 升序排列。可见提示中的质量检查字段已改为较通用的数据政策名称，避免直接泄露具体过滤规则；评估器按权重检查账户顺序、风险分和等级、行动、ARR 和风险 ARR、支持与 NPS 指标、逾期金额、行动汇总计数和质量检查。

### 迁移设计
本任务迁移了留存评分和行动优先级训练任务中的模式：使用已发布 billing 作为 ARR 事实来源，过滤无效 support/NPS 记录，应用共享风险与行动规则，并在 prompt 中不暴露隐藏公式的前提下汇总组合结果。

### 构建记录
只在 task_group_004/test_tasks/001 范围内构建。没有把环境源文件复制到 payload。评估器默认评估本任务自己的 `output/answer.json`，应获得满分。

English update 2026-06-01: added neutral retention `policy_codes` aligned with train_001/train_005 and consolidated evaluator policy scoring into two business-result points.

中文更新 2026-06-01：增加与 train_001/train_005 对齐的中性留存 `policy_codes`，并将评估器中的政策编码评分合并为两个业务结果点。
