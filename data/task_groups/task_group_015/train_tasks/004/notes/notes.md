# train_004 Notes

## English

### Data lineage and task definition

This task belongs to `SCN_015_healthcare_ehr_quality_governance` and uses the task-group design for `train_004`: mixed duplicate-review and FHIR-style orthopedic ServiceRequest QA. The source examples are `E001` duplicate patient merge review and `E004` FHIR referral order validation, with supporting conventions from `E002` and `E005` for referral-code and provider validation.

The solver-visible task names the focal objects `DUP-TR-004`, `P-55218`, possible duplicate `P-55281`, and draft order `SR-TR-004`. Evidence comes from the shared read-only environment in `task_group/task_group_015/env/data/records.json`, accessed by solvers only through the public HTTP endpoints. The only task-local payload is `input/payloads/answer_template.json`, which defines the normalized JSON shape and allowed enum values.

The expected work is to reconcile duplicate-candidate evidence, patient demographics, active conditions, encounters, the draft ServiceRequest, provider directory, ICD-10 directory, and service-code directory. The answer must not contain process instructions or SOP narration.

### Material map

- `/api/duplicates/DUP-TR-004` provides the candidate status, patient ids, match signals, conflict signals, and merge preview.
- `/api/patients/P-55218` and `/api/patients/P-55281` provide demographics, MRNs, contact information, insurance, and primary-care provider.
- `/api/patients/{id}/conditions` and `/api/patients/{id}/encounters` provide laterality and clinical-evidence context for the duplicate conflict and referral reasons.
- `/api/patients/P-55218/service-requests` provides the draft `SR-TR-004` fields.
- `/api/service-codes/ORTHO-CONSULT` verifies that the service code is active and belongs to orthopedics.
- `/api/icd10/M17.11` and `/api/icd10/S83.241A` verify code validity, chapter, laterality, and expected terms.
- `/api/providers/PRV-PCP-002` and `/api/providers/PRV-ORTHO-011` verify requester and performer roles.

### Solution basis

`DUP-TR-004` has match signals `same_dob`, `same_insurance`, and `similar_address`, but it remains `needs_review` because it also has `different_given_name`, `different_phone`, and `opposite_laterality_problem`. `P-55218` has right-knee evidence, while `P-55281` contributes left-knee evidence. The merge preview has no preferred target or source, so the normalized decision is `review_hold` with null merge target/source.

`SR-TR-004` belongs to `P-55218`, uses active service code `ORTHO-CONSULT`, is requested by `PRV-PCP-002`, and is performed by orthopedic provider `PRV-ORTHO-011`. The validated ServiceRequest state for the order is `status: active`, `intent: order`, and `priority: routine`, with authored date `2026-03-04` and occurrence date `2026-03-20`. The reason codes are `M17.11` and `S83.241A`; the ICD directory validates `M17.11` as Musculoskeletal and `S83.241A` as Injury, and the patient's active chart/encounters support both. The draft SBAR contains all four required sections: situation, background, assessment, and recommendation.

### Evaluation basis

The evaluator has seven whole-point scoring goals, each raw weight 2, total raw weight 14:

1. Duplicate decision: candidate id, `needs_review`, `review_hold`, correct patient ids, and null merge target/source.
2. Conflict and match signals: exact normalized sets for all conflict and match signals.
3. ServiceRequest id and service code: `SR-TR-004`, `P-55218`, `ORTHO-CONSULT`, and service-code validity.
4. Status, intent, priority, and dates: `active`, `order`, `routine`, `2026-03-04`, and `2026-03-20`.
5. Reason codes and validation: exact code set plus code validity, chapter, and patient-evidence booleans.
6. SBAR completeness: complete is true, all four sections present, no missing sections.
7. Provider assignment: requester `PRV-PCP-002`, performer `PRV-ORTHO-011`, and orthopedics service line.

Each scoring point is pass/fail with no within-point partial credit. Likely model pitfalls include treating same insurance and similar address as enough for an automatic merge, omitting the opposite-laterality conflict, preserving draft status instead of returning the validated active order state, using only one orthopedic reason code, or producing narrative SBAR text instead of normalized section coverage.

### Transfer design

As a train task, this case anchors two transferable conventions for later tasks. First, duplicate resolution must distinguish match signals from blocking conflicts and should not force a merge when the candidate status and merge preview remain unresolved. Second, FHIR-style referral QA should normalize ServiceRequest fields, service-code validity, provider service line, reason-code validation, and SBAR section coverage into structured outputs. These conventions recur in the test duplicate audit and ServiceRequest validation tasks without the prompt exposing procedural steps.

### Construction record

Author: Codex task-builder subagent for `train_004`. Created: 2026-07-17. Updated: 2026-07-17. Files created under `task_group/task_group_015/train_tasks/004/` only.

## 中文

### 数据来源和任务定义

本任务属于 `SCN_015_healthcare_ehr_quality_governance`，对应任务组设计中的 `train_004`：重复病人审查和 FHIR 风格骨科 ServiceRequest 质检的混合任务。主要来源示例是 `E001` 的重复病人合并审查和 `E004` 的 FHIR 转诊医嘱验证，同时使用 `E002`、`E005` 中关于转诊编码和服务方验证的约定。

求解者可见的任务只给出关键对象：`DUP-TR-004`、`P-55218`、可能重复病人 `P-55281`、以及草稿医嘱 `SR-TR-004`。证据来自共享只读环境 `task_group/task_group_015/env/data/records.json`，求解者只能通过公开 HTTP 端点访问。任务本地唯一载荷是 `input/payloads/answer_template.json`，用于规定标准化 JSON 结构和枚举值。

预期工作包括核对重复候选、病人人口学信息、活动诊断、就诊记录、ServiceRequest 草稿、服务方目录、ICD-10 目录和服务代码目录。答案中不应写入流程说明或 SOP 叙述。

### 材料映射

- `/api/duplicates/DUP-TR-004` 提供候选状态、病人 id、匹配信号、冲突信号和合并预览。
- `/api/patients/P-55218` 与 `/api/patients/P-55281` 提供人口学信息、MRN、联系方式、保险和 PCP。
- `/api/patients/{id}/conditions` 与 `/api/patients/{id}/encounters` 提供左右侧别和临床证据，用于判断重复冲突和转诊原因。
- `/api/patients/P-55218/service-requests` 提供草稿 `SR-TR-004` 字段。
- `/api/service-codes/ORTHO-CONSULT` 验证服务代码处于启用状态并属于骨科。
- `/api/icd10/M17.11` 与 `/api/icd10/S83.241A` 验证 ICD 代码、章节、侧别和期望术语。
- `/api/providers/PRV-PCP-002` 与 `/api/providers/PRV-ORTHO-011` 验证申请方和执行方角色。

### 答案依据

`DUP-TR-004` 的匹配信号为 `same_dob`、`same_insurance`、`similar_address`，但候选仍为 `needs_review`，因为同时存在 `different_given_name`、`different_phone` 和 `opposite_laterality_problem`。`P-55218` 支持右膝证据，而 `P-55281` 含有左膝证据。合并预览没有推荐目标或来源记录，因此标准化决策是 `review_hold`，合并目标和来源均为 null。

`SR-TR-004` 属于 `P-55218`，使用启用的服务代码 `ORTHO-CONSULT`，申请方为 `PRV-PCP-002`，执行方为骨科服务方 `PRV-ORTHO-011`。验证后的 ServiceRequest 状态字段为 `status: active`、`intent: order`、`priority: routine`，创建日期为 `2026-03-04`，发生日期为 `2026-03-20`。原因代码是 `M17.11` 与 `S83.241A`；ICD 目录验证 `M17.11` 属于 Musculoskeletal，`S83.241A` 属于 Injury，且病人的活动病历和就诊记录支持两者。草稿 SBAR 包含 situation、background、assessment、recommendation 四个必需部分。

### 评估依据

评估器有七个整点得分项，每项原始权重为 2，总权重为 14：

1. 重复审查决策：候选 id、`needs_review`、`review_hold`、正确病人 id、合并目标和来源为 null。
2. 冲突和匹配信号：冲突信号集合与匹配信号集合完全正确。
3. ServiceRequest id 和服务代码：`SR-TR-004`、`P-55218`、`ORTHO-CONSULT` 以及服务代码有效性。
4. 状态、意图、优先级和日期：`active`、`order`、`routine`、`2026-03-04`、`2026-03-20`。
5. 原因代码和验证：代码集合、有效性、章节和病人证据布尔值均正确。
6. SBAR 完整性：complete 为 true，四个部分均存在，缺失部分为空。
7. 服务方分配：申请方 `PRV-PCP-002`、执行方 `PRV-ORTHO-011`、服务线为 orthopedics。

每个得分项只有通过或不通过，没有项内部分分。常见错误包括把相同保险和相似地址误判为可自动合并、漏掉相反侧别冲突、把医嘱状态保留为 draft 而不是输出验证后的 active order 状态、只输出一个骨科原因代码，或输出叙述性 SBAR 文本而不是标准化覆盖情况。

### 迁移设计

作为训练任务，本任务为后续任务提供两个可迁移约定。第一，重复病人解析需要区分匹配信号和阻断性冲突，当候选状态和合并预览仍未解决时不能强行合并。第二，FHIR 风格转诊质检应把 ServiceRequest 字段、服务代码有效性、服务方服务线、原因代码验证和 SBAR 覆盖情况标准化为结构化输出。这些约定会在测试集的重复审查和 ServiceRequest 验证任务中复用，但不会在求解者可见提示中暴露流程步骤。

### 构建记录

作者：Codex task-builder subagent for `train_004`。创建日期：2026-07-17。更新日期：2026-07-17。仅在 `task_group/task_group_015/train_tasks/004/` 下创建文件。
