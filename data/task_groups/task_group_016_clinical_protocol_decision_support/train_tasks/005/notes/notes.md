# train_005 Notes

## English

Data lineage: This task derives from `E003` complex care-management escalation, with support from protocol-bound assessment examples. It uses `CASE-CM-T001`, `PAT-CM-T001`, and `COMPLEX_CARE_2026`.

Task definition: The solver must produce a structured care-management escalation decision: high-risk classification, program type, chart concerns, assessment domains, consent strategy, care-plan problem areas, team disciplines, cadence, escalation triggers, and unsupported-guarantee avoidance.

Scenario fit and material map: `/api/care_cases?case_id=CASE-CM-T001` supplies high risk score, two admissions, food insecurity, utility risk, transportation barrier, and chart concerns. `/api/patients/PAT-CM-T001` supplies chronic disease and medication context. `/api/protocols/COMPLEX_CARE_2026` supplies complex-care minima and consent boundaries.

Solution and evaluation basis: Risk is high and program is `complex_care`. The answer includes uncontrolled diabetes, CKD4, recent high-acuity admissions, medication burden, SDoH barriers, and permission-based consent strategies. The evaluator uses 7 exact-match scoring points with raw weights 3, 2, 3, 3, 2, 2, and 1.

Transfer design: This train task teaches that care-management outputs must separate chart concerns from domains to confirm, handle first refusal with low-pressure consent, avoid guarantees, and build a multi-disciplinary weekly plan. It anchors `test_005`.

Construction record: Author Codex; created 2026-07-07; updated after final environment reconciliation.

## 中文

数据来源：本任务参考 `E003` 复杂护理管理升级，并结合协议化评估任务特点。它使用 `CASE-CM-T001`、`PAT-CM-T001` 和 `COMPLEX_CARE_2026`。

任务定义：求解者需要输出结构化护理管理升级决策，包括风险、项目类型、图表关注点、需确认的评估领域、同意策略、护理计划问题、团队角色、随访频率、升级触发条件和避免无根据承诺。

场景匹配与材料图：`/api/care_cases` 提供风险分数、两次住院、食物不安全、欠费风险、交通障碍和图表关注点；`/api/patients` 提供慢病和用药背景；协议提供复杂护理最低要求和同意边界。

解法与评估依据：风险为 high，项目为 `complex_care`。答案覆盖糖尿病失控、CKD4、近期高强度住院、用药负担、社会需求和基于许可的同意策略。评估包含 7 个精确匹配评分点。

迁移设计：这是训练任务，帮助模型学习区分图表风险和需成员确认的领域、处理首次拒绝、避免承诺，并建立多学科每周随访计划。它锚定 `test_005`。

构建记录：作者 Codex；创建于 2026-07-07；最终环境对齐后更新。
