# Globex North Q2 QBR Metrics Packet Notes

## English

### Data Lineage
- Source environment: ApexCloud Retention Operations API and its generated data under `task_group_004/env`.
- Account: `acct_globex_north`, legal name `Globex North Holdings LLC`.
- Period: `2026-Q2`, covering `2026-04-01` through `2026-06-30`.
- Revenue lineage: monthly account metrics `recognized_revenue`.
- Support and SLA lineage: account ticket export for the Q2 date range.
- NPS lineage: account NPS response export for the Q2 date range.

### Task Definition
The solver must create a formal JSON QBR metrics packet with monthly revenue, support ticket volume, SLA compliance, NPS, quarter highlights, source labels, internal review routing, and an ordered four-topic client agenda.

### Scenario Fit
This task fits a customer success director preparing QBR material for a deck, internal review, and client discussion. It requires reconciling metrics from several endpoint families without revealing hidden construction conventions in the user-facing prompt.

### Material Map
- `input/prompt.txt`: solver-facing request, account, quarter, endpoint hints, and required JSON shape.
- `input/payloads/answer_template.json`: empty structured response template.
- `output/answer.json`: canonical expected business result.
- `eval/eval.sh`: weighted evaluator for a submitted prediction or the canonical answer.

### Solution and Evaluation Basis
- Q2 revenue values are April `95756.67`, May `98509.22`, and June `105156.27`.
- Clean support ticket counts are April `4`, May `4`, and June `1`.
- SLA compliance is April `100.0`, May `75.0`, and June `100.0`.
- NPS values are April `45`, May `61`, and June `56`.
- Average revenue is `99807.39`; peak revenue is June at `105156.27`.
- Maximum SLA is `100.0`, represented by the first month reaching the maximum, April.
- Peak NPS is May at `61`; ticket trend is `improving`.
- Review routing is `customer_success`, due `2026-07-22`, with no technical signoff required.
- The evaluator uses eight weighted business-result checks matching the rubric plan.

### Transfer Design
This train task teaches QBR metric-source usage, support/NPS cleaning implications, highlight calculations, and review routing in a compact account-specific packet. The same pattern transfers to other accounts and quarters with different support, SLA, and NPS edge cases.

### Construction Record
Created the task folder contents only under `train_tasks/002/`. The answer was derived from the shared environment data and the hidden shared business rules. No generated environment source files were copied into the task payloads.

## 中文

### 数据血缘
- 来源环境：ApexCloud Retention Operations API，以及 `task_group_004/env` 下生成的数据。
- 账户：`acct_globex_north`，法定名称为 `Globex North Holdings LLC`。
- 周期：`2026-Q2`，覆盖 `2026-04-01` 至 `2026-06-30`。
- 收入血缘：月度账户指标中的 `recognized_revenue`。
- 支持与 SLA 血缘：Q2 日期范围内的账户工单导出。
- NPS 血缘：Q2 日期范围内的账户 NPS 响应导出。

### 任务定义
求解者需要生成正式 JSON QBR 指标包，包括月度收入、支持工单量、SLA 达标率、NPS、季度亮点、来源标签、内部评审安排，以及四个有顺序的客户会议议题。

### 场景适配
该任务适合客户成功负责人准备 QBR 材料，用于演示文稿、内部评审和客户沟通。任务要求从多个端点族整合指标，同时不在可见提示中暴露隐藏的构造规则。

### 材料地图
- `input/prompt.txt`：面向求解者的请求、账户、季度、端点提示和 JSON 结构要求。
- `input/payloads/answer_template.json`：空的结构化答案模板。
- `output/answer.json`：标准业务结果答案。
- `eval/eval.sh`：可评估提交预测或标准答案的加权评估器。

### 解法与评估依据
- Q2 收入分别为四月 `95756.67`、五月 `98509.22`、六月 `105156.27`。
- 清洁后的支持工单数分别为四月 `4`、五月 `4`、六月 `1`。
- SLA 达标率分别为四月 `100.0`、五月 `75.0`、六月 `100.0`。
- NPS 分别为四月 `45`、五月 `61`、六月 `56`。
- 平均收入为 `99807.39`；收入峰值为六月 `105156.27`。
- 最高 SLA 为 `100.0`，用首次达到最高值的四月表示。
- NPS 峰值为五月 `61`；工单趋势为 `improving`。
- 评审负责人为 `customer_success`，截止日期为 `2026-07-22`，不需要技术签字。
- 评估器使用八个加权业务结果检查，与评分计划一致。

### 迁移设计
该训练任务用于锚定 QBR 指标来源、支持和 NPS 清理影响、亮点计算，以及评审路由规则。相同模式可迁移到其他账户和季度，并覆盖不同的支持、SLA 和 NPS 边界情况。

### 构造记录
本次仅在 `train_tasks/002/` 下创建任务文件。答案来自共享环境数据和隐藏共享业务规则。未将生成环境源文件复制进任务 payload。
