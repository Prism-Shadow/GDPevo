# train_003 Notes

## English

This task belongs to `SCN_015_healthcare_ehr_quality_governance`, source examples `E001` through `E005`, with the strongest direct lineage from the care-transition handoff example `E003`. The task uses only shared generated environment records from `task_group/task_group_015/env/data/records.json`; there are no task-local clinical facts beyond the solver-visible request and `input/payloads/answer_template.json`.

The business request is to assemble a normalized care transition packet for patient `P-44702` to orthopedic surgery provider `PRV-ORTHO-010`. The solver-visible prompt points to `<TASK_ENV_BASE_URL>` and asks for patient and recipient identity, active condition/medication/allergy keys, four relevant recent handoff encounters, latest immunization, disclosure, risk flags, and packet readiness. The intended work process is to query the patient chart endpoints, use active/current list state, distinguish the orthopedic handoff trail from unrelated or stale encounters, confirm the provider directory entry, and verify disclosure status.

Material map: `GET /api/patients/P-44702` supplies Thomas Bennett and MRN `E10044702`; `GET /api/providers/PRV-ORTHO-010` supplies Dr. Priya Nair at Cedar Orthopedic Institute; the condition, medication, and allergy endpoints supply the active normalized keys; the encounter endpoint supplies the orthopedic handoff trail and distractors used for the explicit source-selection section; the immunization endpoint supplies the newest immunization `IMM-1372CDAF` dated `2026-03-11`; the disclosure endpoint supplies `DISC-44702-ORTHO` with permitted surgical handoff status. The document endpoint has a final chart summary but is not independently scored because the brief focuses on packet readiness, not document enumeration.

The standard answer includes active condition keys `diabetes_type_2`, `hypertension`, `memory_loss`, `right_hip_oa`, and `right_knee_oa`; active medication keys `acetaminophen`, `baseline_med`, and `insulin_glargine`; active allergy keys `baseline_allergy` and `latex`. The four selected handoff encounters are `ENC-44702-0`, `ENC-44702-1`, `ENC-44702-2`, and `ENC-44702-3`, ordered newest to oldest. The source-selection block records the selection basis and excludes `ENC-0460F33D`, `ENC-0FE06CF3`, `ENC-44702-4`, and `ENC-FA393BB8`. Risk flags are controlled codes derived from active chart state and handoff notes: cognitive memory loss, fall-risk note required, hypertension, insulin-dependent diabetes, latex allergy, and perioperative glucose plan needed. The risk-flag evidence map ties those codes back to condition keys, medication keys, and encounter IDs where applicable. The disclosure is permitted and all required core packet components are present, so readiness is `ready_with_risk_flags` with `ready_to_send: true` and no blocking issue codes.

Evaluation uses 10 whole-point scoring goals with raw weights totaling 22: patient/recipient identity (2), active conditions (2), active medications (2), active allergies (1), handoff encounters (3), source-selection exclusions (3), latest immunization (1), disclosure (2), risk flags plus readiness (3), and risk-flag evidence mapping (3). Each point is pass/fail, with exact normalized set or object comparison after simple list normalization where appropriate. The scoring dimensions cover distinct business outcomes: identity/routing, active clinical state, encounter selection, immunization recency, disclosure authorization, final risk/readiness judgment, and evidence traceability.

This train task contributes transferable experience for later care-transition tasks: active state matters more than all historical rows, recent encounters must still be relevant to the handoff purpose, excluded encounters should be named when the packet must justify source selection, latest immunization is selected by date, disclosure must match recipient and purpose, and risk/readiness should be represented as normalized codes with supporting evidence rather than narrative. Likely model pitfalls are selecting the four newest encounters mechanically, omitting the baseline active medication or allergy keys, treating risk flags as free text, or marking the packet simply `ready` despite explicit perioperative risk issues.

Construction record: created by Codex task-builder subagent for `train_003` on 2026-07-17. Initial version creates the prompt, answer template, gold answer, bilingual notes, and local evaluator under `task_group/task_group_015/train_tasks/003/`.

## 中文

本任务属于 `SCN_015_healthcare_ehr_quality_governance`，来源示例为 `E001` 至 `E005`，其中与护理转接交接示例 `E003` 的关系最直接。任务只使用共享生成环境中的记录 `task_group/task_group_015/env/data/records.json`；除求解者可见的请求和 `input/payloads/answer_template.json` 之外，没有任务本地临床事实。

业务请求是为患者 `P-44702` 准备发给骨科手术提供者 `PRV-ORTHO-010` 的规范化护理转接包。求解者可见提示使用 `<TASK_ENV_BASE_URL>`，要求输出患者和接收方身份、当前活动的诊断/用药/过敏键、四条相关且较新的交接就诊、最新免疫接种、披露记录、风险标志和转接包就绪状态。预期流程是查询患者图表端点，使用活动/当前状态，区分骨科交接轨迹与无关或陈旧就诊，确认提供者目录记录，并验证披露状态。

材料映射：`GET /api/patients/P-44702` 提供 Thomas Bennett 和 MRN `E10044702`；`GET /api/providers/PRV-ORTHO-010` 提供 Cedar Orthopedic Institute 的 Dr. Priya Nair；诊断、用药和过敏端点提供活动 normalized key；就诊端点提供骨科交接轨迹和干扰记录，并支持显式来源选择部分；免疫端点提供日期为 `2026-03-11` 的最新免疫 `IMM-1372CDAF`；披露端点提供状态为 permitted、用途为 surgical handoff 的 `DISC-44702-ORTHO`。文档端点有最终版 chart summary，但本任务简报关注转接包就绪性而不是文档枚举，因此不单独评分。

标准答案包含活动诊断键 `diabetes_type_2`、`hypertension`、`memory_loss`、`right_hip_oa`、`right_knee_oa`；活动用药键 `acetaminophen`、`baseline_med`、`insulin_glargine`；活动过敏键 `baseline_allergy` 和 `latex`。四条选中的交接就诊为 `ENC-44702-0`、`ENC-44702-1`、`ENC-44702-2`、`ENC-44702-3`，按日期从新到旧排列。来源选择部分记录选择依据，并排除 `ENC-0460F33D`、`ENC-0FE06CF3`、`ENC-44702-4` 和 `ENC-FA393BB8`。风险标志使用受控代码，来自活动病历状态和交接备注：认知记忆问题、需要跌倒风险说明、高血压、胰岛素依赖型糖尿病、乳胶过敏以及围手术期血糖计划需求。风险标志证据映射把这些代码关联到相应的问题键、用药键和就诊 ID。披露记录已允许，核心转接包组件齐全，因此就绪状态为 `ready_with_risk_flags`，`ready_to_send: true`，且没有阻断问题代码。

评估包含 10 个整体通过/失败评分点，原始权重总和为 22：患者/接收方身份 (2)、活动诊断 (2)、活动用药 (2)、活动过敏 (1)、交接就诊 (3)、来源选择排除项 (3)、最新免疫 (1)、披露 (2)、风险标志加就绪状态 (3)、风险标志证据映射 (3)。每个评分点只给全分或零分，使用精确的规范化集合或对象比较，必要时仅做简单列表规范化。这些评分维度覆盖不同业务结果：身份和路由、活动临床状态、就诊选择、免疫接种时效、披露授权、最终风险/就绪判断以及证据可追溯性。

该训练任务为后续护理转接任务提供可迁移经验：活动状态比历史全量记录更重要，近期就诊仍必须与交接目的相关，需要说明来源选择时应列出被排除的就诊，最新免疫按日期选择，披露必须匹配接收方和用途，风险/就绪结果应使用规范化代码并带证据，而不是叙述文本。常见模型错误包括机械选择四条最新就诊、漏掉 baseline 活动用药或过敏键、把风险标志写成自由文本，或者忽略围手术期风险而把转接包简单标为 `ready`。

构造记录：由 Codex task-builder subagent 于 2026-07-17 为 `train_003` 创建。初始版本在 `task_group/task_group_015/train_tasks/003/` 下创建提示、答案模板、标准答案、双语说明和本地评估器。
