# Notes for test_002

## English

This test task is a compensation forecast for `ENS-CEDAR` under `case_cedar_negotiation`. It is derived from `E002` and anchored by `train_002` and `train_005`.

The solver must produce annual totals, growth rates, Year + 2 quarter totals, Year + 2 pay-type totals, largest growth pay type, and roster treatment counts. The prompt does not provide the operating method; it only names the requested ensemble and scenario.

The solution uses the compensation rate book, roster rows, and scenario drivers. Transfer-dependent scoring points include seniority band advancement, cumulative future-year drivers, combined overscale/title handling, partial-quarter weeks, and pay-type construction. Task-specific difficulty comes from a larger roster and a different scenario with title percentage multipliers.

There are 8 scoring points with raw weights 1, 3, 2, 2, 3, 2, 1, and 1. Exact matching checks the structured answer fields.

Construction record: created by Codex on 2026-06-02.

## 中文

本测试任务是 `ENS-CEDAR` 在 `case_cedar_negotiation` 情景下的薪酬预测，来源于 `E002`，迁移锚点为 `train_002` 和 `train_005`。

求解者需要输出年度总额、增长率、Year + 2 季度总额、Year + 2 pay type 总额、最大增长 pay type，以及 roster 处理数量。prompt 只说明目标 ensemble 和 scenario，不泄露操作步骤。

迁移依赖点包括 seniority band 随未来年度推进、future-year drivers 累计应用、combined overscale/title 处理、partial-quarter weeks 和 pay type 构造。任务自身难点来自更大的 roster 和包含 title percentage multiplier 的不同情景。评分点 8 个，权重为 1、3、2、2、3、2、1、1。
