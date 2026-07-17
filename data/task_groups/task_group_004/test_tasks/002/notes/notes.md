# Lumen Rail Q3 QBR Readiness Packet Notes

## English

### Data lineage
- Source service: ApexCloud Retention Operations API on port 8074.
- Source files used for construction: `accounts.json`, `account_metrics.json`, `support_tickets.json`, and `nps_responses.json`.
- Account scope: `acct_lumen_rail`, legal name `Lumen Rail Systems Ltd.`.
- Period scope: 2026-Q3, months `2026-07`, `2026-08`, `2026-09`, date range `2026-07-01` through `2026-09-30`.

### Task definition
- The solver must produce a formal QBR readiness packet with monthly metrics, highlights, metric source labels, review routing, and a client meeting plan.
- The visible prompt gives the API and endpoint families, the requested account and period, the exact output shape, due dates, channel slug, meeting date, and controlled enum choices.

### Scenario fit
- This is a Customer Success readiness task, matching the QBR rollup conventions from the training anchor.
- It also exercises risk-aware agenda selection because Lumen Rail has a September SLA deterioration and a September NPS decline from the August peak.

### Material map
- Revenue is sourced from monthly account metrics recognized revenue.
- Support tickets are derived from the support export for the requested date range.
- SLA compliance is derived from support ticket SLA outcomes.
- NPS is derived from valid survey responses in each month.
- Review routing is derived from the quarter-level service reliability pattern.

### Solution and evaluation basis
- Monthly rows are ordered July, August, September 2026.
- Revenue values are `94016.00`, `99027.22`, and `100184.47`.
- Support ticket counts are `5`, `4`, and `4`.
- SLA compliance values are `100.0`, `100.0`, and `50.0`.
- NPS values are `67`, `74`, and `54`.
- Highlights: average revenue `97742.56`, peak revenue month `2026-09`, peak revenue `100184.47`, max SLA month `2026-07`, max SLA `100.0`, peak NPS month `2026-08`, peak NPS `74`, average SLA `83.3`, total support tickets `13`.
- The evaluator checks exact business outputs with the rubric weights from the task brief and accepts an optional prediction path.

### Transfer design
- The task transfers the same QBR monthly rollup and metric source conventions as `train_002`.
- The client agenda transfers the risk-aware selection pattern from `train_005` while using this test task's own agenda and risk theme enums.

### Construction record
- Built inside `test_tasks/002/` only.
- No environment source data was copied into solver-visible payloads.
- `eval/eval.sh` evaluates the bundled answer by default and supports a caller-provided prediction JSON path.

## 中文

### 数据血缘
- 源服务是运行在 8074 端口的 ApexCloud Retention Operations API。
- 构造时使用的源文件包括 `accounts.json`、`account_metrics.json`、`support_tickets.json` 和 `nps_responses.json`。
- 账户范围是 `acct_lumen_rail`，法定名称为 `Lumen Rail Systems Ltd.`。
- 时间范围是 2026-Q3，月份为 `2026-07`、`2026-08`、`2026-09`，日期区间为 `2026-07-01` 到 `2026-09-30`。

### 任务定义
- 求解者需要输出正式的 QBR 准备包，包含月度指标、摘要亮点、指标来源标签、内部评审路由和客户会议计划。
- 可见提示提供 API 和端点族、账户和期间、精确输出结构、截止日期、频道标识、会议日期以及受控枚举选项。

### 场景适配
- 这是客户成功团队的 QBR 准备场景，符合训练锚点中的 QBR 汇总约定。
- 该任务也覆盖风险感知议程选择，因为 Lumen Rail 在 9 月出现 SLA 明显下滑，且 NPS 从 8 月峰值下滑。

### 材料映射
- 收入来自账户月度指标中的确认收入。
- 支持工单来自请求日期范围内的支持导出。
- SLA 达标率来自支持工单中的 SLA 结果。
- NPS 来自每个月的有效调研反馈。
- 评审路由由季度层面的服务可靠性表现决定。

### 解法与评测依据
- 月度行顺序为 2026 年 7 月、8 月、9 月。
- 收入值为 `94016.00`、`99027.22`、`100184.47`。
- 支持工单数为 `5`、`4`、`4`。
- SLA 达标率为 `100.0`、`100.0`、`50.0`。
- NPS 值为 `67`、`74`、`54`。
- 摘要亮点包括平均收入 `97742.56`、收入峰值月份 `2026-09`、收入峰值 `100184.47`、最高 SLA 月份 `2026-07`、最高 SLA `100.0`、最高 NPS 月份 `2026-08`、最高 NPS `74`、平均 SLA `83.3`、总支持工单数 `13`。
- 评测器按任务说明中的权重对业务结果进行精确匹配，并支持可选的预测文件路径。

### 迁移设计
- 该任务迁移 `train_002` 的 QBR 月度汇总和指标来源约定。
- 客户议程迁移 `train_005` 的风险感知选择思路，同时使用本测试任务自己的议程和风险主题枚举。

### 构造记录
- 所有文件只在 `test_tasks/002/` 内创建。
- 没有将环境源数据复制到求解者可见的 payload 文件中。
- `eval/eval.sh` 默认评测内置答案，也支持调用方传入预测 JSON 路径。
