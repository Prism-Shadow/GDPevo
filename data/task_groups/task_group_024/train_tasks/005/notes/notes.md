# English

Task `train_005` is an SLA aging task for Edge Services as of 2026-04-10, with a 21-day inclusive recent-closed window. The solver-facing prompt points to `<TASK_ENV_BASE_URL>` and asks for exact JSON matching the template without exposing the scoring rubric or hidden answer.

The answer was computed from the shared environment using the common SLA aging conventions: latest status history as effective state, reliability/security category precedence, SLA targets by category and severity, duplicate cluster representatives from the included population, escaped S1/S2 count, and missing-owner overdue triage.

Assumption: work items with `created_date` after the as-of date are outside the as-of review population, even if a later snapshot export has an open status. This avoids impossible negative age values.

# 中文

`train_005` 是 Edge Services 在 2026-04-10 的 SLA 老化任务，最近关闭窗口为向前 21 天且包含边界日期。面向求解器的提示使用 `<TASK_ENV_BASE_URL>`，要求输出与模板完全一致的 JSON，未暴露评分细则或隐藏答案。

答案基于共享环境并按通用 SLA 老化规则计算：使用状态历史中的最新有效状态，按可靠性/安全性优先级分类，按类别和严重级别套用 SLA 目标，从纳入人群中生成重复集群代表，统计逃逸的 S1/S2 项，并列出逾期且缺少负责人的工单。

假设：`created_date` 晚于 as-of 日期的工单不属于该 as-of 评审人群，即使后续快照导出的状态为开放，也不纳入计算。这样可以避免出现不合理的负数老化天数。

## Integration Audit Addendum

Lineage and materials: this task is an `E002`-style SLA aging task for Edge Services on 2026-04-10. It uses shared work items, status history, SLA policies, owner/team tables, duplicate-cluster fields, escaped severity flags, and the environment SLA policy document. Solver-visible payloads do not expose computed populations or overdue IDs.

Solution and evaluation basis: the answer includes reliability/security work with effective open status or recent closed status in the inclusive 21-day window, applies SLA targets, and emits normalized population, overdue, bucket, ranking, duplicate, escaped, and missing-owner outputs. The evaluator exact-matches seven business-result points.

Transfer role: paired with `train_002`, this task establishes that SLA conventions are not product-specific and that duplicate handling remains an audit output rather than a way to remove records from the population.

## 集成审核补充

数据来源与材料：本任务是 Edge Services 在 2026-04-10 的 `E002` 风格 SLA 老化任务。它使用共享工单、状态历史、SLA 政策、owner/team 表、duplicate-cluster 字段、escaped severity 标志以及环境 SLA 政策文档。求解者可见 payload 不暴露计算出的总体或逾期 ID。

解法与评测依据：答案纳入有效状态为 open 或处于 21 天包含边界最近关闭窗口内的 reliability/security 工单，应用 SLA 目标，并输出规范化总体、逾期、桶、排序、重复、escaped 和缺 owner 结果。评估器对七个业务结果点精确匹配。

迁移作用：该任务与 `train_002` 配对，说明 SLA 约定不是某个产品专属，并且重复集群处理是审计输出，不是从总体中删除记录。
