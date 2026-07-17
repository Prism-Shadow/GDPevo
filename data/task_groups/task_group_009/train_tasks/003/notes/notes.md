# Notes for train_003

## English

This train task is derived from `E003`, the theatre CBA weekly payroll workbook. It targets production `PROD-HAMILTON-26` and uses the shared payroll rate book and production roster/schedule.

The task definition is to compute service counts, pay category totals, weekly total, per-musician totals, top-paid musician, and contract conflict flags. The visible materials are the prompt, environment access, payroll request, and answer template.

Material map: `/api/payroll/rate-book` provides service rates, time limits, premium percentages, doubles, vacation, substitute, and weekly guarantee rules. `/api/payroll/productions?production_id=PROD-HAMILTON-26` provides schedule rows and roster assignments.

The solution applies per-service pay, hourly rehearsal minimums, premium stacking, electronic substitute treatment, doubles, vacation, and guarantee adjustments. Conflict flags are derived from early rehearsals and services over CBA time limits. There are 8 scoring points with raw weights 2, 3, 2, 2, 3, 1, 2, and 2.

Transfer design: this formal train task teaches rate-book source precedence, schedule classification, premium stacking, substitute electronic treatment, and conflict-flag detection for `test_003`.

Construction record: created by Codex on 2026-06-02.

## 中文

本训练任务来源于 `E003` 的剧院 CBA 周薪 workbook，目标 production 为 `PROD-HAMILTON-26`。任务使用共享 payroll rate book 和 production roster/schedule。

标准解法计算 service counts、pay category totals、weekly total、per-musician totals、top-paid musician 和 CBA conflict flags。需要应用服务费率、rehearsal hourly minimum、premium stacking、electronic substitute、doubles、vacation 和 weekly guarantee adjustment。冲突 flags 来自过早 rehearsal 和超过 CBA time limit 的服务。

评分点 8 个，权重为 2、3、2、2、3、1、2、2。迁移设计重点是 rate-book 优先级、schedule 分类、premium stacking、substitute electronic 处理和冲突识别，这些将迁移到 `test_003`。
