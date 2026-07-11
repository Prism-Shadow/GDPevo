# train_004 Notes

## English

Data lineage: This task derives from `E005` FHIR lab-event retrieval and uses shared Observation records for `PAT-L-T001` plus `FHIR_LAB_RETRIEVAL_2026`.

Task definition: The solver must decide whether final Hemoglobin A1c Observations with code `4548-4` exist in May 2026 for `PAT-L-T001`, then return the matched ids, count, first/last dates, exclusions, and query metadata.

Scenario fit and material map: `/api/observations` exposes May final A1c records plus an April boundary record, a panel header, and a preliminary duplicate. The protocol card defines exact patient/code matching, final-status filtering, panel exclusion, and inclusive month windows.

Solution and evaluation basis: The matched final May ids are `OBS-L-T001-A1C-2026-05-A` and `OBS-L-T001-A1C-2026-05-B`; the boolean is true and count is 2. Excluded ids are the April boundary, panel header, and preliminary record. The evaluator uses 6 exact-match scoring points.

Transfer design: This train task teaches FHIR-like retrieval habits: use exact code and patient id, filter final status, exclude panel headers, and respect inclusive month boundaries. It anchors `test_004` and supports potassium source precedence.

Construction record: Author Codex; created 2026-07-07; updated after final environment reconciliation.

## 中文

数据来源：本任务参考 `E005` FHIR 实验室事件检索，使用 `PAT-L-T001` 的 Observation 记录和 `FHIR_LAB_RETRIEVAL_2026`。

任务定义：求解者需要判断 `PAT-L-T001` 在 2026 年 5 月是否有 final 状态、代码为 `4548-4` 的 HbA1c Observation，并返回匹配 ID、数量、首末日期、排除 ID 和查询元数据。

场景匹配与材料图：`/api/observations` 提供 5 月 final A1c 记录，同时包含 4 月边界记录、panel header 和 preliminary 重复记录。协议卡定义精确患者和代码匹配、final 状态过滤、panel 排除和月份边界。

解法与评估依据：正确匹配 ID 为 `OBS-L-T001-A1C-2026-05-A` 和 `OBS-L-T001-A1C-2026-05-B`，布尔值为 true，数量为 2。评估包含 6 个精确匹配评分点。

迁移设计：这是训练任务，训练模型按精确代码、患者、final 状态和月份窗口检索 FHIR 风格 Observation。它锚定 `test_004`，也支持钾任务中的来源优先级。

构建记录：作者 Codex；创建于 2026-07-07；最终环境对齐后更新。
