# Notes for train_005

## English

This train task extends `E002` into a two-year board forecast for `ENS-MAPLE` under scenario `case_maple_board`. It requires the solver to combine the compensation rate book, roster records, and scenario driver data.

The visible task asks for current, Year + 1, and Year + 2 annual totals; Year + 2 quarter totals; Year + 2 pay-type totals; growth rates; largest growth pay type; and roster treatment counts. It preserves the source example's driver-change modeling workflow in structured JSON form.

Material map: `/api/compensation/rate-book` provides pay types, MWS, title percentages, seniority bands, and forecast rules. `/api/compensation/rosters` provides ensemble-specific employees. `/api/compensation/scenarios` provides future-year growth factors.

The standard answer applies the scenario drivers cumulatively, advances years of service before assigning seniority bands, uses roster quarter weeks, and avoids double-counting title premiums when overscale notes say they are combined. Scoring uses 8 points with raw weights 1, 3, 2, 2, 3, 2, 1, and 1.

Transfer design: this task reinforces future-year driver handling and roster-note treatment for compensation tests `test_002` and `test_005`.

Construction record: created by Codex on 2026-06-02.

## 中文

本训练任务把 `E002` 的薪酬模型扩展为 `ENS-MAPLE` 在 `case_maple_board` 情景下的两年董事会预测。求解者需要结合 compensation rate book、roster 和 scenario drivers。

标准答案累计应用未来年度 driver，先推进 years of service 再判断 seniority band，使用 roster 中给定的 quarter weeks，并在 overscale note 表明已包含 title premium 时避免重复计算。评分点 8 个，权重为 1、3、2、2、3、2、1、1。

迁移设计：该任务强化未来年度驱动、seniority band 变化、quarter weeks 和 roster note 处理，会迁移到 `test_002` 和 `test_005`。
