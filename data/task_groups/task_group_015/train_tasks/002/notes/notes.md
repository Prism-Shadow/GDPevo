# train_002 Notes / 说明

## English

### Data lineage and task definition

This train task belongs to `SCN_015_healthcare_ehr_quality_governance`, source examples `E001`-`E005`, with closest lineage to `E002` referral coordination and `E005` referral data-quality audit. The task design brief is the cardiology referral coordination case for referral `REF-FEB-CARD-007` and patient `P-20177` from batch `FEB26-CARD`.

The solver-visible input is `input/prompt.txt` plus `input/payloads/answer_template.json`. There are no task-local clinical payloads; all business facts come from the shared read-only environment through `<TASK_ENV_BASE_URL>` endpoints. The required output is a normalized JSON referral packet covering patient/referral identity, active diagnoses and ICD validation, allergy readiness, encounter and document evidence, receiving provider, authorization/readiness, medication highlights, and controlled referral-letter field choices.

### Scenario fit and material map

This task represents a realistic EHR referral coordination workflow: a referral row must be reconciled with structured chart state, clinical evidence, document availability, provider directory data, and ICD metadata before a specialist letter can be sent.

Important environment records and endpoints:

- `GET /api/referrals/REF-FEB-CARD-007`: referral header, diagnosis narrative/code, authorization, document receipt flags, receiving provider, coordination note.
- `GET /api/patients/P-20177`: patient demographics and identifiers.
- `GET /api/patients/P-20177/conditions`: active condition set used for the clinical diagnosis/code section.
- `GET /api/icd10/I50.32` and `GET /api/icd10/R06.02`: code chapter and expected narrative terms.
- `GET /api/patients/P-20177/allergies`: active sulfa allergy details.
- `GET /api/patients/P-20177/encounters`: signed encounter evidence, including the referral-relevant `ENC-20177-20260211`.
- `GET /api/patients/P-20177/documents`: final echocardiogram `DOC-ECHO-20177` and chart summary.
- `GET /api/providers/PRV-CARD-020`: receiving cardiologist details.
- `GET /api/patients/P-20177/medications`: active medication highlights, especially furosemide and lisinopril.

### Solution and evaluation basis

The standard answer is built from these evidence points:

- Referral/patient identity: `P-20177`, `REF-FEB-CARD-007`, `FEB26-CARD`, cardiology, requested `2026-02-15`.
- Active diagnosis set: `E11.9`, `I10`, `I50.32`, `M17.11`, and `R06.02`. The referral-relevant codes are `I50.32` primary and `R06.02` supporting. ICD metadata validates `I50.32` as Circulatory and narrative-compatible with chronic diastolic heart failure/HFpEF.
- Allergy details: active `sulfa antibiotics`, reaction `rash`, severity `moderate`, source `referral_form`. The referral note asks to confirm sulfa details; the chart allergy record supplies the needed substance, reaction, severity, and active status, so the normalized readiness is `complete_documented`.
- Recent encounter evidence: `ENC-20177-20260211`, signed office visit on `2026-02-11`, diagnoses `I50.32` and `R06.02`, medication mentioned `furosemide`, care plan for cardiology referral for exertional dyspnea and HFpEF review. Later encounters are distractors because they are not the referral-relevant cardiology evidence.
- Required document evidence: final echocardiogram `DOC-ECHO-20177`, dated `2025-11-12`, and office note receipt indicated by the referral row. No required documents are missing.
- Receiving provider: `PRV-CARD-020`, Dr. Renee Okafor, Cardiologist, Summit Heart Center, phone `555-430-2020`, fax `555-430-2299`.
- Medication highlights: furosemide as the heart-failure diuretic and lisinopril for blood-pressure management. Atorvastatin is active in the data but is not a cardiology referral highlight for this packet.
- Authorization/readiness: authorization `approved`, referral `open`, urgency `routine`, no blockers, overall `ready_to_send`, and referral-letter choices aligned to the evidence.

The local evaluator has 8 whole-pass/fail scoring points, total raw weight 15:

- Identity and referral header, weight 2.
- Clinical diagnoses and code validation, weight 2.
- Allergy details and readiness, weight 2.
- Recent encounter evidence, weight 2.
- Echocardiogram/document packet evidence, weight 2.
- Receiving provider, weight 2.
- Medication highlights, weight 1.
- Authorization/readiness and letter readiness choices, weight 2.

Each point is deterministic. It earns all assigned score only when the complete business outcome passes; otherwise it earns zero. Letter-field choices are checked inside the corresponding business dimensions to avoid duplicate scoring.

Likely model pitfalls include picking the latest encounter instead of the referral-relevant cardiology encounter, treating the referral coordination note as an unresolved allergy blocker despite complete allergy fields, omitting `R06.02` as a supporting code, missing the final echocardiogram document id, confusing PCP and receiving cardiologist, or listing all active medications without distinguishing referral-relevant highlights.

### Transfer design

As a train task, this case helps fewshot skill generation infer recurring conventions for the task group: active/current chart state matters; referral diagnosis validation uses both structured condition records and ICD metadata; allergy readiness requires substance, reaction, severity, and active status; referral evidence should select clinically relevant signed encounters rather than simply the newest encounter; required documents need status and document ids; referral letters use controlled fields for diagnosis, allergy, encounter, document packet, medication, recipient, authorization, and readiness choices.

These conventions are intended to transfer to `test_002` and support other referral/order tasks without making this task a tutorial. The solver-visible prompt states the business goal and output contract but does not disclose the hidden evidence path.

### Construction record

Author: task-builder subagent for `train_002`. Created: 2026-07-17. Updated: 2026-07-17. Major changes: created prompt, answer template, standard answer, bilingual notes, and deterministic evaluator under `task_group/task_group_015/train_tasks/002/`.

## 中文

### 数据来源与任务定义

本训练任务属于 `SCN_015_healthcare_ehr_quality_governance`，来源示例为 `E001`-`E005`，最接近的来源是 `E002` 转诊协调和 `E005` 转诊数据质量审计。任务设计对象是批次 `FEB26-CARD` 中的心脏科转诊 `REF-FEB-CARD-007`，患者为 `P-20177`。

求解者可见材料为 `input/prompt.txt` 和 `input/payloads/answer_template.json`。本任务没有额外的本地临床材料；所有业务事实都来自共享只读环境的 `<TASK_ENV_BASE_URL>` 接口。期望输出是规范化 JSON，涵盖患者和转诊身份、活动诊断与 ICD 校验、过敏准备状态、就诊和文档证据、接收医生、授权和准备状态、重点药物，以及受控的转诊信字段选择。

### 场景适配与材料地图

该任务模拟真实 EHR 转诊协调：工作人员需要把转诊记录与结构化病历、临床证据、文档状态、医生目录和 ICD 元数据相互核对，才能发送专科信。

关键环境记录和接口包括：

- `GET /api/referrals/REF-FEB-CARD-007`：转诊头信息、诊断叙述和代码、授权状态、已收到文档、接收医生、协调备注。
- `GET /api/patients/P-20177`：患者人口学和标识符。
- `GET /api/patients/P-20177/conditions`：活动诊断集合。
- `GET /api/icd10/I50.32` 和 `GET /api/icd10/R06.02`：代码章节和预期叙述词。
- `GET /api/patients/P-20177/allergies`：活动磺胺类过敏详情。
- `GET /api/patients/P-20177/encounters`：已签名就诊证据，尤其是 `ENC-20177-20260211`。
- `GET /api/patients/P-20177/documents`：最终版超声心动图 `DOC-ECHO-20177` 和病历摘要。
- `GET /api/providers/PRV-CARD-020`：接收心脏科医生信息。
- `GET /api/patients/P-20177/medications`：活动药物重点，尤其是 furosemide 和 lisinopril。

### 解答与评估依据

标准答案依据如下证据构建：

- 患者和转诊身份：`P-20177`、`REF-FEB-CARD-007`、`FEB26-CARD`、心脏科、请求日期 `2026-02-15`。
- 活动诊断集合：`E11.9`、`I10`、`I50.32`、`M17.11`、`R06.02`。与转诊最相关的是主代码 `I50.32` 和支持代码 `R06.02`。ICD 元数据表明 `I50.32` 属于循环系统，并与慢性舒张性心力衰竭/HFpEF 叙述匹配。
- 过敏详情：活动过敏为 `sulfa antibiotics`，反应 `rash`，严重度 `moderate`，来源 `referral_form`。转诊备注要求确认磺胺过敏；病历中过敏记录已经包含物质、反应、严重度和活动状态，因此规范化状态为 `complete_documented`。
- 近期就诊证据：`ENC-20177-20260211`，`2026-02-11` 已签名门诊，诊断 `I50.32` 和 `R06.02`，提到药物 `furosemide`，照护计划写明因劳力性呼吸困难和 HFpEF 复核转心脏科。更晚的就诊是干扰项，因为它们不是本次心脏科转诊的相关证据。
- 必需文档证据：最终版超声心动图 `DOC-ECHO-20177`，日期 `2025-11-12`，转诊记录也显示已收到 office note。没有缺失的必需文档。
- 接收医生：`PRV-CARD-020`，Dr. Renee Okafor，心脏科医生，Summit Heart Center，电话 `555-430-2020`，传真 `555-430-2299`。
- 药物重点：furosemide 是心衰相关利尿剂，lisinopril 与血压管理相关。atorvastatin 在数据中为活动药物，但不是本转诊包的重点药物。
- 授权和准备状态：授权 `approved`，转诊 `open`，紧急度 `routine`，无阻塞问题，整体为 `ready_to_send`，转诊信字段选择与证据一致。

本地评估器包含 8 个整点通过/失败评分项，总原始权重 15：

- 身份和转诊头信息，权重 2。
- 临床诊断和代码校验，权重 2。
- 过敏详情和准备状态，权重 2。
- 近期就诊证据，权重 2。
- 超声心动图和文档包证据，权重 2。
- 接收医生，权重 2。
- 药物重点，权重 1。
- 授权/准备状态和信件准备选择，权重 2。

每个评分项都是确定性的。只有完整业务结果通过时才获得该项全部分数，否则为零。转诊信字段选择合并在对应业务维度中检查，避免重复计分。

常见错误包括选择最新就诊而不是与心脏科转诊相关的就诊、把协调备注误判为未解决过敏阻塞、漏掉支持代码 `R06.02`、漏掉最终版超声心动图文档 id、混淆 PCP 和接收心脏科医生，或列出所有活动药物但没有区分转诊相关重点。

### 迁移设计

作为训练任务，本案例帮助 fewshot skill 生成器推断任务组中的复用约定：只纳入活动/当前病历状态；转诊诊断校验需要结合结构化诊断和 ICD 元数据；过敏准备状态需要物质、反应、严重度和活动状态；转诊证据应选择临床相关的已签名就诊，而不是简单选择最新就诊；必需文档需要状态和文档 id；转诊信使用受控字段表达诊断、过敏、就诊、文档包、药物、收件人、授权和准备状态。

这些约定旨在迁移到 `test_002` 并支持其他转诊/医嘱任务，但本任务不是教程。求解者可见 prompt 只说明业务目标和输出契约，不泄露隐藏证据路径。

### 构建记录

作者：`train_002` task-builder subagent。创建日期：2026-07-17。更新日期：2026-07-17。主要变更：在 `task_group/task_group_015/train_tasks/002/` 下创建 prompt、answer template、标准答案、双语 notes 和确定性评估器。
