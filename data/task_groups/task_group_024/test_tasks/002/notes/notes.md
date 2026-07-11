# English

Task `test_002` is a Mobile Platform SLA aging task for Reliability and Security work as of 2026-06-20. The recent closed window is 21 days inclusive, so terminal items use `closed_date` from 2026-05-30 through 2026-06-20 when otherwise eligible.

Train anchors: `train_002` and `train_005`. Those anchors transfer the effective-status reconciliation, Reliability/Security classification precedence, SLA target lookup, duplicate-cluster reporting, escaped S1/S2 counting, and owner/team hotspot ranking rules.

Assumptions: work-item records remain auditable individually even when they belong to duplicate clusters; duplicate cluster output reports the representative and included members rather than suppressing member records from the aging population.

# 中文

任务 `test_002` 是 Mobile Platform 在 2026-06-20 的 Reliability 和 Security SLA aging 任务。最近关闭窗口为 21 天且包含边界，因此符合条件的终态事项使用 2026-05-30 到 2026-06-20 之间的 `closed_date`。

训练锚点：`train_002` 和 `train_005`。这些锚点迁移有效状态校准、Reliability/Security 分类优先级、SLA 目标查表、重复集群报告、escaped S1/S2 计数，以及 owner/team 热点排序规则。

假设：即使工作项属于重复集群，也保留原始工作项记录用于审计；重复集群输出报告代表项和纳入人群中的成员，而不是从 aging 人群中压缩或去除成员记录。

## Integration Audit Addendum

Lineage and materials: this test task belongs to the `E002` SLA aging family and uses Mobile Platform data as of 2026-06-20. The solver must query shared environment work items, status history, SLA policies, owners, teams, duplicate clusters, and policy notes. The task-local payload does not list included or overdue records.

Solution and evaluation basis: seven exact-match scoring points cover effective included population, overdue IDs, aging buckets, ranked owner/team hotspots, duplicate representatives, escaped high-severity count, and missing-owner overdue IDs. Ranking points use deterministic tie-breaks, and duplicate clusters are reported without collapsing the population.

Transfer design: `train_002` and `train_005` anchor effective-status precedence, recently closed inclusion, SLA target lookup, hotspot tie-breaks, and duplicate reporting. The Mobile scope changes dates, teams, and severity distribution, preserving real exploration difficulty.

## 集成审核补充

数据来源与材料：该测试任务属于 `E002` SLA aging 族，使用 Mobile Platform 截至 2026-06-20 的数据。求解者必须查询共享环境中的 work_items、status_history、SLA policies、owners、teams、duplicate clusters 和政策说明。本地 payload 不列出纳入项或逾期项。

解法与评测依据：七个精确匹配评分点覆盖有效纳入总体、逾期 ID、老化桶、owner/team 热点排序、重复代表、高严重度 escaped 数量和缺 owner 逾期 ID。排序点使用确定性 tie-break，重复集群只报告，不折叠总体。

迁移设计：`train_002` 和 `train_005` 锚定有效状态优先级、最近关闭纳入、SLA 目标查表、热点排序和重复报告。Mobile 范围改变日期、团队和严重度分布，保留真实探索难度。
