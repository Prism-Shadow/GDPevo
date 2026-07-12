# train_002 Notes

## English

Data lineage: This task derives from source examples `E002` and `E001`, using respiratory assessment, objective vitals, imaging, allergy checks, and protocol-bound planning. It uses `PAT-R-T001`, `ENC-R-T001`, `RESP_ACUTE_2026`, medication request `MEDREQ-R-T001-SERTRALINE`, and respiratory observations.

Task definition: The solver must classify an acute respiratory visit and choose route, tests, antibiotic plan, contraindicated antibiotic classes, precautions, and evidence ids. The encounter has fever, productive cough, pleuritic pain, focal crackles, CXR infiltrate, O2 90%, RR 26, penicillin allergy, and active sertraline.

Scenario fit and material map: `/api/encounters` supplies the visit; `/api/observations` supplies O2 and CXR; `/api/patients/PAT-R-T001` supplies allergy information; `/api/medication_requests` supplies QT-risk medication; `/api/protocols/RESP_ACUTE_2026` supplies local routing and medication rules.

Solution and evaluation basis: CAP is present, but O2 below 92 and tachypnea route the case to `ed_evaluation`. Because ED evaluation supersedes outpatient antibiotic selection, the controlled antibiotic plan is `no_antibiotic_protocol`; contraindicated classes include penicillin plus QT-risk macrolide/fluoroquinolone outpatient options. The evaluator uses 7 exact-match scoring points.

Transfer design: This train task establishes respiratory source reconciliation: current vitals and imaging decide severity, while allergies and active QT-risk medications constrain protocol choices. It anchors `test_002`.

Construction record: Author Codex; created 2026-07-07; updated after final environment reconciliation.

## 中文

数据来源：本任务参考 `E002` 成人呼吸道就诊和 `E001` 中的结构化临床评估方式，使用 `PAT-R-T001`、`ENC-R-T001`、`RESP_ACUTE_2026`、用药记录和呼吸相关观察值。

任务定义：求解者需要判断急性呼吸道就诊的诊断、就诊地点、检查、抗生素方案、禁忌药物类别、返回警示和证据 ID。当前病例有发热、咳痰、胸膜性疼痛、局灶湿啰音、胸片浸润、血氧 90%、呼吸频率 26、青霉素过敏和正在使用 sertraline。

场景匹配与材料图：`/api/encounters` 提供就诊，`/api/observations` 提供血氧和胸片，`/api/patients` 提供过敏，`/api/medication_requests` 提供 QT 风险用药，`/api/protocols/RESP_ACUTE_2026` 提供本地规则。

解法与评估依据：病例符合社区获得性肺炎，但低氧和呼吸急促使路径为 `ed_evaluation`。因需急诊评估，门诊抗生素方案为 `no_antibiotic_protocol`，禁忌类别包括青霉素以及 QT 风险相关的大环内酯和氟喹诺酮。评估包含 7 个精确匹配评分点。

迁移设计：这是训练任务，帮助模型学习用当前生命体征和影像判断严重程度，并结合过敏和 QT 风险用药限制治疗选择。它锚定 `test_002`。

构建记录：作者 Codex；创建于 2026-07-07；最终环境对齐后更新。
