# train_001 Notes

## English

Data lineage: This task derives from `SCN_016_healthcare_clinical_protocol_decision_support`, especially `E001` pediatric head-injury assessment. It uses the shared ClinicProtocol API records for `PAT-H-T001` and `ENC-H-T001`, plus protocol `HEAD_INJURY_2026`.

Task definition: The solver must produce structured head-injury triage JSON from the encounter and local protocol. The relevant current facts are repeated vomiting and increasing drowsiness after a basketball head injury, with GCS 15 and a reliable observer. The output captures route, CT recommendation, disposition, red flags, activity restrictions, follow-up timing, contraindicated actions, and evidence ids.

Scenario fit and material map: `/api/encounters?encounter_id=ENC-H-T001` supplies the visit facts; `/api/observations?encounter_id=ENC-H-T001` supplies supporting vitals; `/api/protocols/HEAD_INJURY_2026` supplies the local routing rules. This mirrors the seed head-injury SOAP task but converts the result into exact structured decisions.

Solution and evaluation basis: The correct route is `urgent_ed` because repeated vomiting and increasing drowsiness are protocol red flags. CT is `urgent`, disposition is `send_to_ed_now`, and the plan blocks same-day play, self-driving, and unsupervised home observation. The evaluator has 7 exact-match scoring points with weights 3, 3, 2, 2, 1, 1, and 1.

Transfer design: This is a train task. It teaches through answer comparison that current encounter red flags outrank reassuring normal GCS or stale problem-list context, and that head-injury outputs should use controlled route, CT, activity, and contraindication enums.

Construction record: Author Codex; created 2026-07-07; updated after env-builder reconciliation to use worker-generated July 2026 data.

## 中文

数据来源：本任务来自 `SCN_016_healthcare_clinical_protocol_decision_support`，主要参考 `E001` 儿童头部外伤评估。任务使用共享 ClinicProtocol API 中的 `PAT-H-T001`、`ENC-H-T001` 和 `HEAD_INJURY_2026` 协议。

任务定义：求解者需要根据当前就诊和本地协议输出结构化头部外伤分诊 JSON。关键事实是篮球运动中头部受伤后反复呕吐和嗜睡加重，同时 GCS 为 15 且有可靠观察者。

场景匹配与材料图：`/api/encounters` 提供就诊事实，`/api/observations` 提供支持性生命体征，`/api/protocols/HEAD_INJURY_2026` 提供分诊规则。本任务把原始 SOAP 式评估转化为可精确评分的结构化决策。

解法与评估依据：因反复呕吐和嗜睡加重属于红旗，正确路径为 `urgent_ed`，CT 为 `urgent`，处置为 `send_to_ed_now`。评估包含 7 个精确匹配评分点，权重为 3、3、2、2、1、1、1。

迁移设计：这是训练任务。通过对照答案，模型应学会当前就诊红旗优先于正常 GCS 或陈旧病史，并使用受控枚举表达分诊、CT、活动限制和禁忌行为。

构建记录：作者 Codex；创建于 2026-07-07；在环境构建器完成后更新为 2026 年 7 月数据。
