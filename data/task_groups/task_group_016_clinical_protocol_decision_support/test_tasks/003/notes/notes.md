# test_003 Notes

## English

Data lineage: This test task derives from `E004` and `E005`, anchored by `train_003` and `train_004`. It uses `PAT-K-X001` and `POTASSIUM_REPLETION_2026`.

Task definition: The solver must select the latest valid final potassium, ignore cancelled and stale observations, calculate oral replacement dose, and schedule paired follow-up serum potassium for the next day at 08:00.

Scenario fit and material map: `/api/observations?patient_id=PAT-K-X001&code=K` returns a cancelled same-day low value, a final critical-low value, and an older final value. The protocol card gives the 3.5 target, dose rule, NDC, and LOINC.

Solution and evaluation basis: `OBS-K-X001-FINAL` at 2.9 mEq/L is the latest valid final. The gap to 3.5 is 0.6, so the dose is 60 mEq. Follow-up is 2026-07-07T08:00:00-05:00 with LOINC `2823-3`. The evaluator has 6 exact-match scoring points.

Transfer design: Anchors are `train_003` SP001-SP004 and `train_004` final-status filtering. Transfer-dependent points are latest observation selection, dose calculation, and follow-up lab order. The changed difficulty is the lower final value and a cancelled distractor.

Construction record: Author Codex; created 2026-07-07; updated after final environment reconciliation.

## 中文

数据来源：本测试任务参考 `E004` 和 `E005`，由 `train_003` 与 `train_004` 锚定。它使用 `PAT-K-X001` 和 `POTASSIUM_REPLETION_2026`。

任务定义：求解者需要选择最新有效 final 血钾，忽略 cancelled 和陈旧记录，计算口服补钾剂量，并安排次日 08:00 复查血钾。

场景匹配与材料图：`/api/observations` 返回同日 cancelled 低值、final 危急低值和较旧 final 值。协议卡提供 3.5 目标、剂量规则、NDC 和 LOINC。

解法与评估依据：`OBS-K-X001-FINAL` 为 2.9 mEq/L，是最新有效 final。与目标差 0.6，因此剂量为 60 mEq。复查时间为 2026-07-07T08:00:00-05:00。评估包含 6 个精确匹配评分点。

迁移设计：锚点为 `train_003` SP001-SP004 和 `train_004` 的 final 状态过滤。迁移点是最新有效观察值选择、剂量计算和复查医嘱；变化是数值更低且有 cancelled 干扰项。

构建记录：作者 Codex；创建于 2026-07-07；最终环境对齐后更新。
