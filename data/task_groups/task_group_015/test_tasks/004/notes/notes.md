# test_004 Notes

## English

### Data and source lineage

This task belongs to scenario `SCN_015_healthcare_ehr_quality_governance`, using the source-example family around EHR referral/order quality, FHIR-style ServiceRequest validation, referral coordination, and care-transition evidence selection. The specific design brief is the test task `test_004`: validate neurology ServiceRequest `SR-TE-004` for patient `P-91804`.

The task uses only the shared generated environment under `task_group/task_group_015/env/data/records.json`, exposed to solvers through HTTP endpoints. There are no task-local evidence payloads beyond `input/payloads/answer_template.json`.

### Task definition

The solver-visible prompt asks for normalized JSON validating a draft neurology ServiceRequest and deciding the filing disposition for a ready order. The solver should query `<TASK_ENV_BASE_URL>` for the patient, ServiceRequest, active conditions, medications, encounters, provider directory, service-code directory, and ICD-10 metadata. The answer must identify the request and patient, validate the ServiceRequest administrative fields, confirm the neurology service/provider, validate coded reasons against current chart evidence, select the key encounter and medication support, record SBAR section completeness, and separate the source draft status from the ready-to-file active order status.

Important objects:

- Patient `P-91804`, Owen Mercer, enterprise MRN `E10091804`.
- Draft ServiceRequest `SR-TE-004`.
- Performer `PRV-NEURO-040`, Dr. Hannah Stern at Lakeside Neurology.
- Service code `NEURO-CONSULT`.
- Reason codes `G20.A1` and `R41.3`.
- Key encounter `ENC-91804-20260409`.
- Key medication `MED-05C47E07`, carbidopa/levodopa.

### Scenario fit and transfer design

This task fits the referral/order quality-control operation family in the group. It combines directory validation, ICD/chart reconciliation, current-state clinical support, and SBAR completeness. It is a test task, so the solver-visible prompt does not list procedural steps. Transfer should come from `train_004`, which establishes the ServiceRequest field pattern and SBAR section convention, and from `train_002`/`train_003`, which reinforce recent signed encounter selection, active/current clinical evidence, and medication highlight conventions.

Transfer-dependent scoring goals include the ServiceRequest field validation, service/provider validation, draft-to-active filing disposition, reason-code validation against conditions and ICD metadata, evidence encounter selection, medication/current condition support, and SBAR completeness. Task-specific exploration is still required because all patient, code, provider, medication, encounter, and request values are different from the train tasks.

### Material map

- `GET /api/patients/P-91804`: patient identity and primary-care provider.
- `GET /api/patients/P-91804/service-requests`: draft request `SR-TE-004`.
- `GET /api/service-codes/NEURO-CONSULT`: active neurology consultation service code.
- `GET /api/providers/PRV-NEURO-040`: performer service line and directory identity.
- `GET /api/icd10/G20.A1` and `GET /api/icd10/R41.3`: valid ICD metadata and chapters.
- `GET /api/patients/P-91804/conditions?status=active`: active Parkinson disease and memory-loss condition support.
- `GET /api/patients/P-91804/medications?status=active`: active carbidopa/levodopa evidence.
- `GET /api/patients/P-91804/encounters`: signed 2026-04-09 office visit with both reason codes, the medication mention, and neurology referral note.
- `input/payloads/answer_template.json`: solver-visible normalized output shape.

### Solution and evaluation basis

The standard answer records `SR-TE-004` for `P-91804` and patient demographics from the patient endpoint. The source ServiceRequest status is `draft`, but the validated ready-to-file order status is `active`; intent is `order`, priority is `routine`, authored date is `2026-04-10`, occurrence date is `2026-04-28`, and all validation flags are true because these are allowed values and the occurrence date follows authored date. The filing disposition records `source_status: draft`, `ready_to_file_status: active`, `action: file_as_active_order`, `ready_to_file: true`, and no hold reason codes. The service code `NEURO-CONSULT` is valid and active, and the performer is `PRV-NEURO-040` with service line `neurology`; requester is `PRV-PCP-002`.

Both reason codes are valid and supported by active conditions: `G20.A1` has chapter `Nervous system` and maps to condition `COND-A6D0DA4D`; `R41.3` has chapter `Symptoms` and maps to condition `COND-2EEFD6B5`. The key evidence encounter is `ENC-91804-20260409`, a signed office visit on `2026-04-09` with diagnoses `G20.A1` and `R41.3`, medication mention `carbidopa/levodopa`, and care-plan note requesting neurology referral for worsening tremor and gait freezing. The key medication is active `MED-05C47E07`, carbidopa/levodopa `25/100 mg` oral three times daily. The SBAR text has all four required sections: situation, background, assessment, and recommendation.

The evaluator has eight whole-pass scoring points, with raw weights totaling 17:

1. Request and patient identity.
2. Service code and provider assignment.
3. Ready-to-file active status, intent, priority, dates, and validation flags.
4. Draft-source to active-order filing disposition.
5. Reason codes and ICD/chart validation.
6. Key evidence encounter.
7. Key medication and current active condition support.
8. SBAR section completeness.

Each point is deterministic and all-or-nothing. Lists are normalized as sets where declared. Likely model pitfalls are using a distractor recent encounter from 2026-04-11 that does not support the neurology reason, copying the source `draft` status into the ready-to-file order instead of recording `active` with a separate filing decision, treating the metformin baseline medication as referral-relevant, or reporting free-text SBAR summaries instead of normalized section coverage.

### Construction record

Author: task-builder subagent for `test_004`.

Created: 2026-07-17.

Updated: 2026-07-17.

Major changes: Created prompt, answer template, standard answer, bilingual notes, and deterministic evaluator for the neurology ServiceRequest validation task.

## 中文

### 数据和来源

本任务属于 `SCN_015_healthcare_ehr_quality_governance` 场景，延续 EHR 转诊/医嘱质量治理、FHIR 风格 ServiceRequest 校验、转诊协调和交接证据选择等源示例。具体任务是测试任务 `test_004`：校验患者 `P-91804` 的神经内科 ServiceRequest `SR-TE-004`。

任务只使用共享生成环境 `task_group/task_group_015/env/data/records.json` 中的数据，解题者只能通过 HTTP 端点访问。除 `input/payloads/answer_template.json` 外，没有额外的任务本地证据 payload。

### 任务定义

面向解题者的提示要求输出规范化 JSON，用于校验一条草稿状态的神经内科 ServiceRequest，并决定可归档医嘱的 filing disposition。解题者应查询 `<TASK_ENV_BASE_URL>` 中的患者、ServiceRequest、活动问题、用药、就诊、服务提供者目录、服务代码目录和 ICD-10 元数据。答案需要确认请求和患者身份、校验 ServiceRequest 管理字段、确认神经内科服务和执行医生、根据当前病历证据校验原因编码、选择关键就诊和用药证据，记录 SBAR 段落完整性，并把来源草稿状态与可归档 active 医嘱状态分开表示。

关键对象包括：患者 `P-91804` Owen Mercer，企业 MRN `E10091804`；草稿 ServiceRequest `SR-TE-004`；执行医生 `PRV-NEURO-040`；服务代码 `NEURO-CONSULT`；原因编码 `G20.A1` 和 `R41.3`；关键就诊 `ENC-91804-20260409`；关键用药 `MED-05C47E07` carbidopa/levodopa。

### 场景适配和迁移设计

该任务属于本任务组中的转诊/医嘱质量控制操作族，结合了目录校验、ICD 与病历一致性、当前临床证据和 SBAR 完整性。作为测试任务，提示中不列出操作步骤。迁移知识主要来自 `train_004` 的 ServiceRequest 字段模式和 SBAR 段落约定，以及 `train_002`、`train_003` 中关于近期已签署就诊、活动临床证据和用药摘要的经验。

依赖迁移的评分目标包括 ServiceRequest 字段校验、服务和提供者校验、draft-to-active 归档处置、原因编码与 ICD/病历证据校验、关键就诊选择、用药与当前问题支持、SBAR 完整性。任务仍需要新的环境探索，因为患者、编码、医生、用药、就诊和请求值都不同于训练任务。

### 材料映射

- `GET /api/patients/P-91804`：患者身份和 PCP。
- `GET /api/patients/P-91804/service-requests`：草稿请求 `SR-TE-004`。
- `GET /api/service-codes/NEURO-CONSULT`：有效的神经内科会诊服务代码。
- `GET /api/providers/PRV-NEURO-040`：执行医生和服务线。
- `GET /api/icd10/G20.A1` 与 `GET /api/icd10/R41.3`：ICD 元数据和章节。
- `GET /api/patients/P-91804/conditions?status=active`：活动的 Parkinson disease 和 memory loss 条件证据。
- `GET /api/patients/P-91804/medications?status=active`：活动 carbidopa/levodopa 用药证据。
- `GET /api/patients/P-91804/encounters`：2026-04-09 已签署门诊就诊，包含两个原因编码、用药提及和神经内科转诊说明。
- `input/payloads/answer_template.json`：解题者可见的规范化输出结构。

### 答案和评估依据

标准答案记录 `SR-TE-004` 对应患者 `P-91804`，患者人口学信息来自患者端点。来源 ServiceRequest 状态为 `draft`，但经校验后可归档医嘱状态为 `active`；意图为 `order`，优先级为 `routine`，创建日期 `2026-04-10`，发生日期 `2026-04-28`；这些字段和日期顺序均有效。归档处置记录 `source_status: draft`、`ready_to_file_status: active`、`action: file_as_active_order`、`ready_to_file: true`，且没有 hold reason codes。服务代码 `NEURO-CONSULT` 有效且启用，执行医生为 `PRV-NEURO-040`，服务线为 `neurology`，请求者为 `PRV-PCP-002`。

两个原因编码都有效并由活动病情支持：`G20.A1` 属于 `Nervous system`，对应条件 `COND-A6D0DA4D`；`R41.3` 属于 `Symptoms`，对应条件 `COND-2EEFD6B5`。关键就诊为 `ENC-91804-20260409`，日期 `2026-04-09`，已签署门诊，就诊诊断包含 `G20.A1` 和 `R41.3`，提及 carbidopa/levodopa，并注明因震颤和步态冻结加重需要神经内科转诊。关键用药为活动状态的 `MED-05C47E07`，carbidopa/levodopa `25/100 mg`，口服，每日三次。SBAR 包含 situation、background、assessment、recommendation 四个段落。

评估器有八个整点评分项，原始权重总和为 17：请求与患者身份；服务代码和提供者；可归档 active 状态、意图、优先级、日期与验证标志；来源草稿到 active 医嘱的归档处置；原因编码和 ICD/病历验证；关键就诊证据；关键用药和当前活动条件支持；SBAR 段落完整性。每项都是确定性全有或全无评分。常见错误包括选择 2026-04-11 的无关近期就诊，把来源 `draft` 状态直接复制到可归档医嘱而没有给出 `active` 和单独 filing decision，把 metformin 当作相关用药，或输出自由文本 SBAR 摘要而非规范化段落覆盖。

### 构造记录

作者：`test_004` task-builder subagent。

创建日期：2026-07-17。

更新日期：2026-07-17。

主要变更：创建神经内科 ServiceRequest 校验任务的提示、答案模板、标准答案、双语 notes 和确定性评估器。
