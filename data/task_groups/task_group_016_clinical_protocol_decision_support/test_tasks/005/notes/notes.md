# test_005 Notes

## English

Data lineage: This test task derives from `E003` and is anchored by `train_005`. It uses `CASE-CM-X001`, `PAT-CM-X001`, and `COMPLEX_CARE_2026`.

Task definition: The solver must produce a structured complex-care escalation decision for a high-risk COPD/HFrEF case with unstable housing, medication cost concerns, missed pulmonary rehab, transportation barriers, and behavioral-health history.

Scenario fit and material map: `/api/care_cases?case_id=CASE-CM-X001` supplies risk score, admissions, SDoH flags, and assigned team. `/api/patients/PAT-CM-X001` supplies chronic problems, allergy, and medication background. `/api/protocols/COMPLEX_CARE_2026` supplies risk/program, consent, and care-plan minima.

Solution and evaluation basis: Risk is high and program is `complex_care`. Correct outputs include COPD exacerbation risk, heart-failure recent admission, housing instability, inhaler affordability, pulmonary rehab transport, multi-disciplinary team, weekly cadence, and no unsupported guarantees. The evaluator uses 7 exact-match scoring points.

Transfer design: Anchor is `train_005`. Transfer-dependent points are risk/program classification, assessment-domain selection, consent strategy, and care-plan disciplines/cadence/escalation. The changed difficulty is a COPD/HF/housing case rather than diabetes/CKD/utility-food insecurity.

Construction record: Author Codex; created 2026-07-07; updated after final environment reconciliation.

## 中文

数据来源：本测试任务来自 `E003`，由 `train_005` 锚定。它使用 `CASE-CM-X001`、`PAT-CM-X001` 和 `COMPLEX_CARE_2026`。

任务定义：求解者需要为高风险 COPD/HFrEF 病例输出复杂护理管理升级决策。该病例涉及住房不稳定、吸入药费用、错过肺康复、交通障碍和行为健康史。

场景匹配与材料图：`/api/care_cases` 提供风险分数、住院、社会需求和团队；`/api/patients` 提供慢病、过敏和用药背景；协议提供风险、同意和护理计划最低要求。

解法与评估依据：风险为 high，项目为 `complex_care`。正确输出包括 COPD 急性加重风险、近期心衰住院、住房不稳定、吸入药负担、肺康复交通、多学科团队、每周随访和避免无根据承诺。评估包含 7 个精确匹配评分点。

迁移设计：锚点为 `train_005`。迁移点是风险和项目判断、评估领域选择、同意策略、多学科计划和升级触发；变化是疾病组合与社会需求不同。

构建记录：作者 Codex；创建于 2026-07-07；最终环境对齐后更新。
