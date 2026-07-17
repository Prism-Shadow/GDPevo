# Notes for test_005

## English

This test task is a board labor-cost sensitivity pack for `ENS-OAK` under `case_oak_sensitivity`. It is derived from `E002` and anchored by `train_002` and `train_005`.

The task asks for annual forecast totals, growth rates, Year + 2 quarter and pay-type detail, roster treatment counts, largest growth pay type, and a controlled risk classification. The risk rule is solver-visible in the request memo; the calculation logic still depends on the shared rate book, roster, and scenario drivers.

Transfer-dependent difficulty includes cumulative driver use, future-year seniority bands, quarter-week handling, and combined overscale/title treatment. Task-specific difficulty comes from the Oak roster's partial-quarter employees and a separate board sensitivity case.

There are 8 scoring points with raw weights 1, 3, 2, 2, 3, 2, 2, and 2. The evaluator exact-matches numeric totals and the risk enum.

Construction record: created by Codex on 2026-06-02.

## 中文

本测试任务是 `ENS-OAK` 在 `case_oak_sensitivity` 下的董事会 labor-cost sensitivity pack，来源于 `E002`，迁移锚点为 `train_002` 和 `train_005`。

任务要求年度预测总额、增长率、Year + 2 季度与 pay type 细分、roster 处理数量、最大增长 pay type，以及受控枚举的风险分类。风险规则在请求 memo 中可见，但核心计算仍依赖 rate book、roster 和 scenario drivers。

迁移依赖点包括 driver 累计、未来年度 seniority band、quarter weeks 和 combined overscale/title 处理。任务自身难点来自 Oak roster 的 partial-quarter 员工和不同的 sensitivity case。评分点 8 个，权重为 1、3、2、2、3、2、2、2。
