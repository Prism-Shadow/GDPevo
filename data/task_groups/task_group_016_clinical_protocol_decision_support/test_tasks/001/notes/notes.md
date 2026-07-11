# test_001 Notes

## English

Data lineage: This test task derives from `E001` and reuses the head-injury workflow established in `train_001`. It uses `PAT-H-X001`, `ENC-H-X001`, `OBS-H-X001-INR`, and `HEAD_INJURY_2026`.

Task definition: The solver must triage a telephone head-strike encounter with worsening headache, active anticoagulant use, and abnormal gait by spouse report. The output schema mirrors `train_001`.

Scenario fit and material map: `/api/encounters?encounter_id=ENC-H-X001` supplies the current phone-triage facts; `/api/observations?patient_id=PAT-H-X001` supplies INR evidence for anticoagulation context; `/api/patients/PAT-H-X001` supplies active warfarin medication; `/api/protocols/HEAD_INJURY_2026` supplies route and activity rules.

Solution and evaluation basis: The correct route is `urgent_ed` with urgent CT and ED disposition. Red flags are worsening headache, anticoagulant use, and abnormal gait. Activity restrictions and contraindications follow the same controlled pattern as `train_001`. The evaluator has 7 exact-match scoring points.

Transfer design: Anchors are `train_001` SP001-SP004. Transfer-dependent points are risk/CT route, red-flag set, activity restrictions, and contraindicated actions. What changes is that this case is a phone encounter with anticoagulant use and gait report rather than vomiting/drowsiness.

Construction record: Author Codex; created 2026-07-07; updated after final environment reconciliation.

## 中文

数据来源：本测试任务来自 `E001`，并复用 `train_001` 的头部外伤工作流。它使用 `PAT-H-X001`、`ENC-H-X001`、`OBS-H-X001-INR` 和 `HEAD_INJURY_2026`。

任务定义：求解者需要对电话分诊中的头部撞击病例进行结构化分诊。关键事实是头痛加重、正在抗凝治疗以及配偶报告步态异常。输出结构与 `train_001` 相同。

场景匹配与材料图：`/api/encounters` 提供电话分诊事实，`/api/observations` 提供 INR 证据，`/api/patients` 提供 warfarin 背景，协议提供分诊和活动规则。

解法与评估依据：正确路径为 `urgent_ed`，CT 为 urgent，处置为立即急诊。红旗包括头痛加重、抗凝使用和步态异常。评估包含 7 个精确匹配评分点。

迁移设计：锚点为 `train_001` 的 SP001-SP004。需要迁移的是红旗优先、CT/急诊路径、活动限制和禁忌行为；变化在于本例为电话分诊且红旗类型不同。

构建记录：作者 Codex；创建于 2026-07-07；最终环境对齐后更新。
