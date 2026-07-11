# English

Task `test_004` is a combined portfolio mix plus SLA aging test for Core Services. The solver-visible prompt uses `<TASK_ENV_BASE_URL>`, points to `request_context.json`, and asks for exact JSON matching `answer_template.json` without exposing the rubric or hidden answer.

The hidden answer was computed from the shared environment using the common portfolio and SLA rules: quarter-end effective status from status history, category precedence, target-gap rounding, 21-day inclusive recent-closed SLA inclusion, owner/team hotspot tie-breaks, duplicate cluster representatives, and the combined action enum.

Train anchors:
- `train_001`: portfolio closed-work eligibility, category precedence, target gaps, and allocation follow-up actions.
- `train_002`: SLA inclusion, overdue detection, owner/team hotspots, duplicate clusters, and missing-owner triage.
- `train_004`: portfolio target comparison and gap rounding for a later-quarter product review.
- `train_005`: SLA duplicate handling, status-history precedence, and missing-owner reliability/security triage.

Assumption: the SLA scope is all Core Services reliability/security work items visible as of 2026-06-30, not only items whose `quarter` is 2026-Q2. The portfolio scope remains restricted to Core Services 2026-Q2 closed work.

# 中文

`test_004` 是 Core Services 的组合测试，覆盖组合投资结构和 SLA 老化。面向求解器的提示使用 `<TASK_ENV_BASE_URL>`，引用 `request_context.json`，并要求输出与 `answer_template.json` 完全一致的 JSON；提示中没有暴露评分细则或隐藏答案。

隐藏答案基于共享环境并按通用组合投资和 SLA 规则计算：使用状态历史确定季度末有效状态，按类别优先级分类，按目标差距规则取整，SLA 最近关闭窗口为向前 21 天且包含边界日期，按规则排序 owner/team 热点，生成重复集群代表，并选择组合动作枚举。

训练锚点：
- `train_001`：已完成工单的组合投资口径、类别优先级、目标差距和分配跟进行动。
- `train_002`：SLA 纳入范围、逾期判断、owner/team 热点、重复集群和缺 owner 分诊。
- `train_004`：后续季度产品评审中的组合目标对比和差距取整。
- `train_005`：SLA 重复集群处理、状态历史优先级，以及可靠性/安全性缺 owner 分诊。

假设：SLA 范围为截至 2026-06-30 可见的全部 Core Services 可靠性/安全性工单，不仅限于 `quarter` 为 2026-Q2 的工单。组合投资范围仍只限 Core Services 2026-Q2 的已完成工单。

## Integration Audit Addendum

Lineage and materials: this combined test draws from both `E001` and `E002`. It uses Core Services portfolio targets and Q2 work items for the mix section, plus all visible Core Services reliability/security work as of 2026-06-30 for the SLA section. Required evidence is distributed across work items, status history, targets, SLA policies, owners, teams, duplicate clusters, and policy docs.

Solution and evaluation basis: eight exact-match points score portfolio eligible set, category counts, under-investment/follow-up, SLA included population, overdue set, hotspot ranking, duplicate/missing-owner triage, and the combined action enum. The expected action is `PortfolioOnlyFollowUp` because the under-invested categories are not reliability/security even though SLA overdue work exists.

Transfer design: this task intentionally combines recurring operation families. It rewards transfer from both work-mix train tasks and both SLA train tasks, while requiring fresh Core Services exploration and synthesis.

## 集成审核补充

数据来源与材料：该组合测试同时来自 `E001` 和 `E002`。mix 部分使用 Core Services 的组合目标和 Q2 工单，SLA 部分使用截至 2026-06-30 可见的全部 Core Services reliability/security 工单。证据分布在 work_items、status_history、targets、SLA policies、owners、teams、duplicate clusters 和政策文档中。

解法与评测依据：八个精确匹配点评分 portfolio eligible 集、类别计数、低配/跟进、SLA 纳入总体、逾期集、热点排序、重复/缺 owner 分诊和 combined action 枚举。预期动作是 `PortfolioOnlyFollowUp`，因为低配类别不是 reliability/security，即使存在 SLA 逾期项。

迁移设计：该任务有意组合两个重复操作族。它奖励从两个 work-mix 训练任务和两个 SLA 训练任务迁移经验，同时仍要求对 Core Services 做新的探索和综合判断。
