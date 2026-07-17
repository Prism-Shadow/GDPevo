# Notes for train_002

## English

This train task is derived from `E002`, the orchestra CBA compensation forecast model. It asks for the current-year compensation summary for `ENS-REDWOOD` using the shared compensation rate book and roster data.

The task definition requires quarter totals, annual pay-type totals, annual total, largest pay type, and counts for combined overscale/title notes and partial-quarter employees. The visible inputs are the prompt, environment access payload, request memo, and answer template.

Material map: `/api/compensation/rate-book` supplies MWS, pay types, title premium percentages, seniority bands, quarter weeks, and business rules. `/api/compensation/rosters?ensemble_id=ENS-REDWOOD` supplies employee roster attributes, overscale, years of service, quarter weeks, and notes.

The solution calculates Minimum Weekly Scale, Titled Position Premium, Seniority, and Overscale for each roster row and quarter. If a roster row says combined overscale includes title premium, title premium should not be added separately. Partial-quarter rows use their listed quarter weeks. The seven scoring points have raw weights 2, 3, 3, 2, 1, 2, and 2.

Transfer design: this task teaches the solver to separate rate-book assumptions from roster inputs, use quarter weeks, and inspect overscale/title notes. Those conventions transfer to compensation forecast test tasks.

Construction record: created by Codex on 2026-06-02 from fixed-seed compensation data.

## 中文

本训练任务对应 `E002` 的乐团 CBA 薪酬模型。目标是使用共享 compensation rate book 与 roster，计算 `ENS-REDWOOD` 的当年薪酬汇总。

任务需要输出季度总额、年度 pay type 总额、年度总额、最大 pay type，以及 combined overscale/title 和 partial-quarter 员工数量。可见材料包括 prompt、环境入口、请求 memo 和答案模板。

标准解法按 roster 每行和每个季度计算 Minimum Weekly Scale、Titled Position Premium、Seniority 和 Overscale。若 roster 标注 overscale 已包含 title premium，则不能再额外加 title premium；若员工为 partial-quarter，则使用该行给出的 quarter weeks。评分点 7 个，权重为 2、3、3、2、1、2、2。

迁移设计：该训练任务帮助求解者学到 rate assumptions 与 roster inputs 分离、quarter weeks 使用、overscale/title note 检查等方法，这些会迁移到后续 compensation forecast 测试任务。
