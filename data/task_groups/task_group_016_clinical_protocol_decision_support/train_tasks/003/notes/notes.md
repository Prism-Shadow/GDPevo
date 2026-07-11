# train_003 Notes

## English

Data lineage: This task derives from `E004` MedAgentBench potassium replacement and `E005` FHIR-style Observation retrieval. It uses `PAT-K-T001`, potassium observations, medication history, and protocol `POTASSIUM_REPLETION_2026`.

Task definition: The solver must identify the latest applicable potassium value and output whether replacement is required, the oral potassium dose, NDC, route, paired serum potassium follow-up order, ignored observation ids, and evidence ids. Current time is 2026-07-06T09:00:00-05:00.

Scenario fit and material map: `/api/observations?patient_id=PAT-K-T001&code=K` exposes final, preliminary, entered-in-error, and stale observations. `/api/protocols/POTASSIUM_REPLETION_2026` provides the target, dose rule, NDC, and LOINC. `/api/medication_requests` adds clinical context but is not itself the answer.

Solution and evaluation basis: The latest valid local-code final potassium is `OBS-K-T001-FINAL`, value 3.2 mEq/L. It is 0.3 below target, so the dose is 30 mEq. Follow-up serum potassium uses LOINC `2823-3` at 2026-07-07T08:00:00-05:00. Six exact-match points score latest result, replacement decision, medication order, follow-up lab, ignored ids, and identifiers.

Transfer design: This train task teaches final-status precedence, local code use, dose rounding, and next-morning follow-up timing. It anchors `test_003`.

Construction record: Author Codex; created 2026-07-07; updated after final environment reconciliation.

## 中文

数据来源：本任务参考 `E004` 钾补充协议和 `E005` FHIR Observation 检索，使用 `PAT-K-T001`、钾观察值、用药背景和 `POTASSIUM_REPLETION_2026`。

任务定义：求解者需要找出最新适用的血钾结果，并输出是否需要补钾、口服钾剂剂量、NDC、给药途径、配套复查血钾医嘱、忽略的观察值 ID 和证据 ID。当前时间为 2026-07-06T09:00:00-05:00。

场景匹配与材料图：`/api/observations` 包含 final、preliminary、entered-in-error 和陈旧记录；`/api/protocols/POTASSIUM_REPLETION_2026` 提供目标值、剂量规则、NDC 和 LOINC。

解法与评估依据：最新有效 final 本地代码血钾是 `OBS-K-T001-FINAL`，数值 3.2 mEq/L，低于目标 0.3，因此剂量为 30 mEq。复查血钾 LOINC 为 `2823-3`，时间为次日 08:00。评估有 6 个精确匹配评分点。

迁移设计：这是训练任务，帮助模型学习 final 状态优先、本地代码选择、剂量计算和次日上午复查时间。它锚定 `test_003`。

构建记录：作者 Codex；创建于 2026-07-07；最终环境对齐后更新。
