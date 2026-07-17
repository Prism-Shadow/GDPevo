# English

Task train_002 builds the Payments reliability/security SLA aging exercise for as-of date 2026-02-15 with a 21-day inclusive recent-closed window.

Construction assumptions:
- Scope is all work items with `product = Payments`, not only the construction index's notable IDs.
- Work items created after the as-of date are excluded from the as-of population.
- Category classification follows the common precedence rules. Items with `reliability-review` labels are treated as Reliability before TechDebt.
- Recently closed items include `Verified`, `Done`, and `Closed` records with `closed_date` from 2026-01-25 through 2026-02-15 inclusive.

The evaluator has seven scoring points: included population, overdue ID set, aging buckets, owner/team hotspots, duplicate clusters, escaped high-severity count, and missing-owner overdue set.

# Chinese

任务 train_002 构建 Payments 产品在 2026-02-15 的可靠性/安全 SLA 老化分析，最近关闭窗口为包含边界的 21 天。

构建假设：
- 范围是所有 `product = Payments` 的工作项，不只使用 construction index 中的 notable IDs。
- 创建日期晚于 as-of 日期的工作项不纳入当日快照。
- 分类遵循公共优先级规则。带有 `reliability-review` 标签的工作项先按 Reliability 处理，而不是 TechDebt。
- 最近关闭项包括 `closed_date` 在 2026-01-25 到 2026-02-15 之间且状态为 `Verified`、`Done`、`Closed` 的记录，两个日期都包含在内。

评估器包含七个评分点：纳入总体、逾期 ID 集、老化桶、负责人/团队热点、重复簇、高严重度逃逸数量，以及缺少负责人的逾期集合。

## Integration Audit Addendum

Lineage and materials: this task is derived from `E002` and uses generated `work_items`, `status_history`, `sla_policies`, `owners`, `teams`, duplicate-cluster fields, and policy documents for a Payments reliability/security SLA review as of 2026-02-15. Solver-visible payloads provide scope and output schema, not included IDs or overdue IDs.

Solution and evaluation basis: the answer reconstructs effective status, includes open reliability/security items plus recently closed items in the inclusive 21-day window, applies severity/category SLA targets, and computes overdue IDs, aging buckets, owner/team hotspots, duplicate representatives, escaped S1/S2 counts, and missing-owner overdue items. Seven scoring points exact-match normalized lists, rankings, and counts.

Transfer role: this train task exposes stale-export reconciliation, recent closure boundaries, duplicate reporting, and hotspot tie-breaks through answer comparison. It anchors `test_002` and the SLA section of `test_004`.

## 集成审核补充

数据来源与材料：本任务来自 `E002`，使用生成的 `work_items`、`status_history`、`sla_policies`、`owners`、`teams`、重复集群字段和政策文档，对 Payments 在 2026-02-15 的可靠性/安全性 SLA 进行分析。求解者可见 payload 只提供范围和输出 schema，不提供纳入 ID 或逾期 ID。

解法与评测依据：答案重建有效状态，纳入 open 的 reliability/security 工单以及 21 天包含边界窗口内最近关闭的工单，按严重度/类别应用 SLA 目标，并计算逾期 ID、老化桶、owner/team 热点、重复代表、escaped S1/S2 计数和缺 owner 逾期项。七个评分点精确匹配规范化列表、排序和计数。

迁移作用：该训练任务通过答案对比暴露导出状态校准、最近关闭边界、重复报告和热点排序规则。它锚定 `test_002` 和 `test_004` 的 SLA 部分。
