# English

Task `test_003` covers release readiness for `REL-VEGA-20` (`Vega 2.0`) as of `2026-06-30`. Solver-visible files are limited to the prompt, a small request context payload, and the answer template; they do not expose the full SOP, rubric, or computed answer.

The hidden answer was computed from the common release readiness rules: release scope is the union of direct release links and milestone-item links, effective status comes from status history as of the as-of date, cancelled items are excluded from milestone denominators, critical milestones and critical dependency participants define the critical path, active blockers on incomplete critical-path work produce gates, blocker causes use controlled enum normalization, and the ship/risk decisions follow the release gate policy.

Train anchors: `train_003` and `train_005`. `train_003` transfers the release readiness shape, milestone denominator handling, critical-path blocker propagation, ship decision, and risk-tier conventions. `train_005` reinforces blocker/owner triage patterns and security/reliability operational risk signals that appear in Vega's gating work.

Assumption: for the ordered representative chain, the lexicographically smallest critical dependency chain containing a gating item and ending in release-scoped critical work is `WI-0374 -> WI-0375`. `WI-0375` is the gating item in that chain.

# 中文

任务 `test_003` 覆盖 `REL-VEGA-20`（`Vega 2.0`）在 `2026-06-30` 的发布就绪度分析。求解器可见文件仅包括提示词、一个简短的请求上下文 payload，以及答案模板；不会暴露完整 SOP、评分细则或计算答案。

隐藏答案按通用发布就绪度规则计算：发布范围是直接 release 链接和 milestone-item 链接的并集；有效状态取截至日期前状态历史中的最新状态；取消项不进入里程碑分母；关键里程碑和关键依赖参与项定义关键路径；未完成关键路径工作上的 active blocker 形成 gate；blocker 原因按受控枚举归一化；发版决策和风险等级遵循 release gate 规则。

训练锚点：`train_003` 和 `train_005`。`train_003` 迁移发布就绪度输出结构、里程碑分母处理、关键路径 blocker 传播、发版决策和风险等级约定。`train_005` 强化 blocker/owner 分诊模式，以及 Vega gate 工作中出现的安全与可靠性运营风险信号。

假设说明：对于有序代表依赖链，包含 gating item 且终点为发布范围内关键工作的字典序最小关键依赖链是 `WI-0374 -> WI-0375`。在该链中，`WI-0375` 是 gating item。

## Integration Audit Addendum

Lineage and materials: this test task is drawn from `E003` and analyzes `REL-VEGA-20` on 2026-06-30. It uses release, milestone, milestone-item, work-item, status-history, dependency, blocker, owner, and team tables from the shared environment. The prompt gives the release ID but not the gate set, dependency chain, or decision.

Solution and evaluation basis: seven exact-match points score ship decision, gating item set, milestone completion, blocker cause counts, critical dependency chain, risk tier, and escalation owners. These outputs require reconstructing effective status, excluding cancelled items, propagating active blockers along critical dependencies, and mapping cause enums.

Transfer design: `train_003` teaches the release-readiness shape and denominator conventions through answer comparison, while `train_005` reinforces operational blocker/owner triage. Vega changes the release graph and has non-empty gates, so the test retains task-specific graph work.

## 集成审核补充

数据来源与材料：该测试任务来自 `E003`，分析 `REL-VEGA-20` 在 2026-06-30 的状态。它使用共享环境中的 release、milestone、milestone_items、work_items、status_history、dependencies、blockers、owners 和 teams 表。提示给出 release ID，但不提供 gate 集、依赖链或决策。

解法与评测依据：七个精确匹配点评分发版决策、gating item 集、里程碑完成率、blocker cause 计数、关键依赖链、风险等级和升级 owner。这些输出需要重建有效状态、排除取消项、沿关键依赖传播 active blocker，并映射 cause 枚举。

迁移设计：`train_003` 通过答案对比传递发布就绪输出形态和分母约定，`train_005` 强化运营 blocker/owner 分诊。Vega 改变 release 图并包含非空 gate，因此测试仍需要任务特定图探索。
