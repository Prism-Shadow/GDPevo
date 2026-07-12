# Notes / 备注

## English

Hidden builder note for `test_002`. Solver-visible content stays English-only and avoids SOP leakage. Transfer anchors are `train_002` packet freshness/completeness and `train_004` chart-created-versus-chart-ready.

Key scoring conventions: draft/missing/expired packet items are unusable; stale usable labs/screens go in `stale_items`; packet blockers route to `referring_facility` before capacity or chart-prep routing. Chart prep requires complete demographics, history, problems, current vitals, care plan or instructions, and sent orientation.

Gold highlights: TR-2644 has expired confidentiality, draft referring contact, and stale labs/screen; TR-2659 has missing authorization, draft confidentiality, expired screen, and stale labs; TR-2671 has missing authorization/screen plus expired confidentiality/labs; TR-2688 has missing authorization/labs and expired screen with waitlist capacity; TR-2693 has expired allergy list, draft authorization, and missing confidentiality/prescription/screen/labs with waitlist capacity.

Post-review rework: exact-match scoring now uses ten groups and a 16-point maximum. Freshness-window handling, the top-level `freshness_exception_transfers` rollup, and chart missing-section sets carry more weight because direct attempts were over-scoring when they copied packet decisions but missed cross-page transfer conventions.

## 中文

`test_002` 隐藏构建备注。面向解题者内容只用英文，且不泄露 SOP。迁移锚点是 `train_002` 的资料包完整性/时效性，以及 `train_004` 的 chart 已创建但未必 ready。

关键评分约定：draft/missing/expired 的资料不可用；可用但过期于 freshness 规则的 labs/screens 放入 `stale_items`；资料包阻塞优先于容量或 chart-prep 路由，owner 为 `referring_facility`。Chart prep 需要 demographics、history、problems、current vitals、care plan 或 instructions，以及已发送 orientation。

标准答案要点：TR-2644 有过期 confidentiality、draft referring contact、stale labs/screen；TR-2659 有 missing authorization、draft confidentiality、expired screen、stale labs；TR-2671 有 missing authorization/screen 和 expired confidentiality/labs；TR-2688 有 missing authorization/labs、expired screen，容量 waitlist；TR-2693 有 expired allergy list、draft authorization、missing confidentiality/prescription/screen/labs，容量 waitlist。

评审后返工：精确匹配评分现在包含十组、最高 16 分。freshness 窗口判断、顶层 `freshness_exception_transfers` 汇总，以及 chart missing-section 集合权重更高，因为直接尝试会复制资料包大类判断，却漏掉这些跨页面迁移规则。
