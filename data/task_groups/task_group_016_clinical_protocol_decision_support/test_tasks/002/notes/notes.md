# test_002 Notes

## English

Data lineage: This test task derives from `E002` and is anchored by `train_002`. It uses `PAT-R-X001`, `ENC-R-X001`, respiratory observations, active escitalopram medication, sulfonamide allergy, and `RESP_ACUTE_2026`.

Task definition: The solver must classify a same-day respiratory visit with fever, cough, left lower lobe consolidation, normal oxygenation, sulfa allergy, and QT-risk medication. The output schema mirrors `train_002`.

Scenario fit and material map: `/api/encounters` gives symptoms and exam; `/api/observations` gives O2 and chest x-ray; `/api/patients` gives allergy; `/api/medication_requests` gives escitalopram; `/api/protocols/RESP_ACUTE_2026` gives site-of-care and antibiotic rules.

Solution and evaluation basis: The correct assessment is CAP with outpatient treatment. Severity factors are focal crackles and lobar consolidation; there are no ED criteria. Doxycycline is the protocol-compatible outpatient plan because sulfonamide is contraindicated and QT-risk medication makes macrolide/fluoroquinolone poor outpatient choices. The evaluator has 7 exact-match scoring points.

Transfer design: Anchors are `train_002` SP001-SP005. Transfer-dependent points are site of care, test set, antibiotic plan, and contraindicated classes. The changed difficulty is that the test case is outpatient rather than ED and uses a different allergy/QT combination.

Construction record: Author Codex; created 2026-07-07; updated after final environment reconciliation.

## 中文

数据来源：本测试任务来自 `E002`，由 `train_002` 锚定。它使用 `PAT-R-X001`、`ENC-R-X001`、呼吸相关观察值、escitalopram 用药、磺胺过敏和 `RESP_ACUTE_2026`。

任务定义：求解者需要判断一个发热咳嗽、左下肺实变、血氧正常、磺胺过敏且有 QT 风险用药的同日门诊病例。输出结构与 `train_002` 相同。

场景匹配与材料图：`/api/encounters` 提供症状和体检，`/api/observations` 提供血氧和胸片，`/api/patients` 提供过敏，`/api/medication_requests` 提供用药，协议提供路径和抗生素规则。

解法与评估依据：正确诊断为社区获得性肺炎，路径为门诊治疗。严重因素为局灶湿啰音和肺叶实变。因磺胺禁忌且 QT 风险用药限制大环内酯和氟喹诺酮，方案为 doxycycline。评估包含 7 个精确匹配评分点。

迁移设计：锚点为 `train_002` 的 SP001-SP005。需要迁移的是按当前生命体征和影像判断地点、根据过敏和用药限制抗生素；变化是测试病例不是急诊路径。

构建记录：作者 Codex；创建于 2026-07-07；最终环境对齐后更新。
