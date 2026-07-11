# English Notes

Task `test_005` combines release readiness with a release-scoped portfolio allocation review for Atlas Admin.

- Release scope: `REL-ATLAS-Q3`, as of `2026-07-15`.
- Portfolio scope: Atlas Admin, `2026-Q2`, as of `2026-06-30`, restricted to closed eligible work linked to `REL-ATLAS-Q3`.
- The solver-facing prompt intentionally points to environment APIs and policy documents without listing the full SOP, scoring rubric, or computed answers.
- Train anchors: `train_001` and `train_004` cover portfolio mix/category gap transfer; `train_003` covers release readiness transfer; `train_005` reinforces security/reliability recognition and blocker-style operational reasoning.

# 中文说明

`test_005` 将发布就绪度检查与发布范围内的组合投入分析结合起来，目标产品为 Atlas Admin。

- 发布范围：`REL-ATLAS-Q3`，截至日期为 `2026-07-15`。
- 组合范围：Atlas Admin，`2026-Q2`，截至日期为 `2026-06-30`，并且只包含链接到 `REL-ATLAS-Q3` 的已关闭合格工作项。
- 面向求解器的提示只指向环境 API 和政策文档，不暴露完整流程、评分细则或计算答案。
- 训练锚点：`train_001` 和 `train_004` 对应组合分类与差距计算迁移；`train_003` 对应发布就绪度迁移；`train_005` 强化安全/可靠性识别以及阻塞类运营推理。

## Integration Audit Addendum

Lineage and materials: this combined test draws from `E001` and `E003`. It analyzes `REL-ATLAS-Q3` release readiness as of 2026-07-15 and release-linked Atlas Admin Q2 closed work for allocation. Evidence comes from releases, milestones, milestone items, dependencies, blockers, work items, status history, portfolio targets, owner/team records, and policy documents.

Solution and evaluation basis: eight exact-match points score release ship decision, gating items, milestone completion, blocker cause counts, dependency chain, release-scoped eligible portfolio set, portfolio mix/gaps/follow-up mapping, and combined action. The correct combined action is `ReleaseGateEscalation` because active release gates exist.

Transfer design: work-mix conventions transfer from `train_001` and `train_004`; release-readiness conventions transfer from `train_003`; operational security/reliability recognition and escalation habits are reinforced by `train_005`. Atlas changes the release train, scope restriction, and gating graph, so high-value points remain data-specific.

## 集成审核补充

数据来源与材料：该组合测试来自 `E001` 和 `E003`。它分析 `REL-ATLAS-Q3` 在 2026-07-15 的发布就绪度，并分析与该 release 关联的 Atlas Admin 2026-Q2 已关闭工单投入结构。证据来自 releases、milestones、milestone_items、dependencies、blockers、work_items、status_history、portfolio targets、owner/team 记录和政策文档。

解法与评测依据：八个精确匹配点评分发版决策、gating items、里程碑完成率、blocker cause 计数、依赖链、release-scoped portfolio eligible 集、portfolio mix/gap/follow-up 映射和 combined action。正确 combined action 是 `ReleaseGateEscalation`，因为存在 active release gate。

迁移设计：work-mix 约定从 `train_001` 和 `train_004` 迁移；release-readiness 约定从 `train_003` 迁移；安全/可靠性识别和升级习惯由 `train_005` 强化。Atlas 改变 release train、范围限制和 gating 图，因此高价值评分点仍依赖新数据探索。
