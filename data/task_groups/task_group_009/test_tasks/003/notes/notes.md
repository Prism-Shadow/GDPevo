# Notes for test_003

## English

This test task extends `E003` and is anchored by `train_003`. It targets production `PROD-LYRIC-27`, which has a different service mix, more musicians, sound-check duration issues, and multiple premium combinations.

The task asks for service counts, category totals, weekly total, conflict flags, per-musician totals, and top-paid musician. The visible prompt does not provide step-by-step payroll logic; the solver must use the shared payroll rate book and production data.

Material map: `/api/payroll/rate-book` contains service rates, time limits, premium percentages, doubles, vacation, substitute, and guarantee rules. `/api/payroll/productions` contains schedule and roster assignments.

Transfer-dependent scoring points include premium stacking, substitute electronic treatment, doubles, weekly guarantee adjustments, service time-limit conflicts, and sorted conflict flags. Task-specific difficulty comes from the larger roster and additional sound-check mismatch flags. There are 9 scoring points with raw weights 2, 3, 2, 3, 3, 1, 2, 2, and 2.

Construction record: created by Codex on 2026-06-02.

## 中文

本测试任务延续 `E003` 的周薪与 CBA 控制流程，迁移锚点为 `train_003`。目标 production 为 `PROD-LYRIC-27`，它有不同的 service mix、更多音乐人、sound-check 时长问题和多种 premium 组合。

任务要求输出 service counts、category totals、weekly total、conflict flags、per-musician totals 和 top-paid musician。prompt 不给逐步 payroll 逻辑，求解者必须使用共享 payroll rate book 和 production 数据。

迁移依赖点包括 premium stacking、substitute electronic 处理、doubles、weekly guarantee adjustments、service time-limit conflicts 和 flags 排序。任务自身难点来自更大的 roster 和额外 sound-check mismatch。评分点 9 个，权重为 2、3、2、3、3、1、2、2、2。
