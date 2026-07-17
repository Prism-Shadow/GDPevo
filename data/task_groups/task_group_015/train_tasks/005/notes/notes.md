# train_005 Notes - MAR26-ORTHO-A Referral Audit

## English

### Data and Source Lineage

This task is part of `task_group_015`, derived from scenario `SCN_015_healthcare_ehr_quality_governance` and especially source example `E005`, the orthopedic referral data-quality audit. It also shares conventions with `E002` and `E004` because the solver must reconcile referral fields with ICD-10 and provider data exposed through the shared EHR environment.

The solver-visible input is `input/prompt.txt` plus `input/payloads/answer_template.json`. There are no task-local data payloads beyond the schema. The business data comes from the shared read-only environment generated at `task_group/task_group_015/env/data/records.json` and exposed through HTTP endpoints. The focal batch is `MAR26-ORTHO-A`.

### Task Definition and Material Map

The task asks for a formal March orthopedic referral audit. The expected answer is normalized JSON containing:

- batch identity and counts;
- referrals whose ICD-10 code is invalid for the orthopedic musculoskeletal tracking range;
- referrals whose code laterality or clinical narrative does not match the ICD-10 directory terms;
- duplicate referral groups;
- duplicate-tiering policy for same-patient resubmission rows;
- shared-insurance/different-patient anomalies;
- documentation, authorization, and imaging follow-up queues;
- Tier 1, Tier 2, and Tier 3 action-plan assignments;
- summary counts.

Relevant environment surfaces are:

- `GET /api/referrals?batch=MAR26-ORTHO-A` for the batch rows;
- `GET /api/referrals/{referral_id}` for detail checks;
- `GET /api/icd10` and `GET /api/icd10/{code}` for code chapter, laterality requirement, and expected narrative terms;
- `GET /api/patients/{patient_id}` and patient search for duplicate and unique-patient validation;
- `GET /api/providers/{provider_id}` for action owner/provider IDs.

The prompt intentionally does not list procedural SOP steps. The answer template removes output-format ambiguity while leaving the audit decisions to be inferred from the environment.

### Solution Basis

The batch contains 19 referral rows and 18 unique patient IDs. `REF-MAR-004` and `REF-MAR-019-DUP` are the same patient, `P-55218`, and the latter row is explicitly marked as a duplicate resubmission. The duplicate-tiering policy records that all rows in the same-patient resubmission group are duplicate-blocker action rows until the group is consolidated. The separate shared-insurance anomaly `ANOM-MAR-INS-881144` links `P-55218` and `P-55281` through insurance ID `INS-881144`; this is an insurance-membership verification issue, not a patient merge instruction.

The orthopedic audit treats the expected tracked ICD-10 chapter as `Musculoskeletal`. Codes in other chapters are out of range even when clinically orthopedic-adjacent. The invalid or out-of-range set is:

`REF-MAR-001`, `REF-MAR-003`, `REF-MAR-005`, `REF-MAR-006`, `REF-MAR-011`, `REF-MAR-012`, `REF-MAR-015`, `REF-MAR-017`, `REF-MAR-018`, and `REF-MAR-019-DUP`.

The laterality or narrative mismatch set is:

`REF-MAR-001`, `REF-MAR-002`, `REF-MAR-003`, `REF-MAR-005`, `REF-MAR-006`, `REF-MAR-007`, `REF-MAR-009`, `REF-MAR-011`, `REF-MAR-012`, `REF-MAR-013`, `REF-MAR-014`, `REF-MAR-015`, `REF-MAR-016`, `REF-MAR-017`, and `REF-MAR-018`.

Documentation and authorization queues are based on structured fields and notes:

- `authorization_missing`: authorization status is `missing`.
- `authorization_pending`: no referrals remain in this queue for the gold answer.
- `records_request`: `office_note` is absent from `documents_received`.
- `imaging_follow_up`: the note says imaging is pending or the row lacks both `xray` and `mri`.

Action-plan tiering is encoded as normalized assignment lists:

- Tier 1: urgent referrals with coding or duplicate blockers: `REF-MAR-004`, `REF-MAR-009`, `REF-MAR-015`, `REF-MAR-019-DUP`.
- Tier 2: routine referrals with coding, authorization, records, or imaging blockers: `REF-MAR-001`, `REF-MAR-002`, `REF-MAR-003`, `REF-MAR-005`, `REF-MAR-006`, `REF-MAR-007`, `REF-MAR-011`, `REF-MAR-012`, `REF-MAR-013`, `REF-MAR-014`, `REF-MAR-016`, `REF-MAR-017`, `REF-MAR-018`.
- Tier 3: administrative document completion without a coding/auth clinical blocker: `REF-MAR-008`, `REF-MAR-010`.

No referral remains validated ready with no scored follow-up assignment after the duplicate group is routed for consolidation.

### Evaluation Basis

The evaluator has ten whole-point scoring goals with raw weights totaling 22:

1. Batch identity and row/unique-patient counts, weight 3.
2. Invalid/out-of-range chapter/code referrals, weight 3.
3. Laterality or narrative mismatch referrals, weight 2.
4. Duplicate group identification and duplicate-resubmission tiering policy, weight 2.
5. Shared-insurance/different-patient anomaly identification, weight 2.
6. Authorization, records, and imaging follow-up queues, including the empty pending-authorization queue, weight 2.
7. Tier 1 action-plan assignments, weight 2.
8. Tier 2 action-plan assignments, weight 2.
9. Tier 3 action-plan assignments, weight 2.
10. Summary counts, weight 2.

Each point is all-or-nothing. The evaluator normalizes referral IDs from the relevant JSON sections, compares exact sets, and checks integer counts. It does not score prose or evidence wording.

Likely model pitfalls include treating all S-codes as acceptable because they are orthopedic injuries, missing the duplicate row when counting the batch, confusing missing `office_note` with imaging gaps, counting `REF-MAR-004` as Tier 1 despite no unresolved audit blocker, failing to separate duplicate rows from unique patients, or converting the shared-insurance anomaly into an unsafe patient merge recommendation.

### Transfer Design

As a train task, this is a formal solved example of the referral data-quality audit family. A fewshot skill can infer that orthopedic referral audits require checking ICD chapter, expected terms, laterality, patient-level duplicate resubmissions, shared-insurance anomalies that require verification rather than merge, structured documentation fields including empty queues, note-derived blockers, and tier assignments. These conventions are intended to transfer to later referral readiness and orthopedic batch-audit test tasks without the solver-visible prompt listing the SOP.

### Construction Record

Author: task-builder subagent for `train_005`.

Created: 2026-07-17.

Updated: 2026-07-17.

Major changes: Created the solver prompt, answer template, standard answer, evaluator, and notes for `MAR26-ORTHO-A`.

## 中文

### 数据与来源

本任务属于 `task_group_015`，来源场景为 `SCN_015_healthcare_ehr_quality_governance`，主要借鉴源示例 `E005` 的骨科转诊质量审计。它也与 `E002` 和 `E004` 共享经验，因为求解者需要把转诊字段、ICD-10 代码目录、患者信息和服务提供者信息进行交叉核对。

求解者可见的输入只有 `input/prompt.txt` 和 `input/payloads/answer_template.json`。本任务没有额外的本地数据载荷。业务数据来自共享只读环境，生成数据位于 `task_group/task_group_015/env/data/records.json`，但求解者只能通过 HTTP 端点访问。目标批次是 `MAR26-ORTHO-A`。

### 任务定义与材料映射

任务要求完成一份正式的三月骨科转诊审计。标准输出是规范化 JSON，包括批次身份与计数、ICD-10 代码章节越界记录、代码叙述或左右侧不匹配记录、重复转诊组、共享保险但不同患者的异常、文档/授权/影像跟进队列、Tier 1/2/3 行动计划分配，以及汇总计数。

相关环境入口包括转诊批次查询、转诊详情、ICD-10 查询、患者详情或搜索，以及服务提供者目录。提示词没有写出操作步骤；答案模板只约束输出结构，具体审计判断需要由环境数据推导。

### 解答依据

该批次有 19 行转诊记录，涉及 18 个唯一患者 ID。`REF-MAR-004` 与 `REF-MAR-019-DUP` 都属于患者 `P-55218`，后者在备注中明确是重复提交。重复分层策略记录：同一患者重复提交组内的所有行在合并处理前都作为 duplicate-blocker 行动项。另一个共享保险异常 `ANOM-MAR-INS-881144` 通过保险 ID `INS-881144` 关联 `P-55218` 和 `P-55281`；这是需要核验保险成员关系的问题，不是患者合并指令。

骨科审计中，期望跟踪的 ICD-10 章节是 `Musculoskeletal`。即使某些损伤代码与骨科临床相关，只要章节不是该章节，就作为越界代码。越界代码集合为：

`REF-MAR-001`、`REF-MAR-003`、`REF-MAR-005`、`REF-MAR-006`、`REF-MAR-011`、`REF-MAR-012`、`REF-MAR-015`、`REF-MAR-017`、`REF-MAR-018`、`REF-MAR-019-DUP`。

左右侧或叙述不匹配集合为：

`REF-MAR-001`、`REF-MAR-002`、`REF-MAR-003`、`REF-MAR-005`、`REF-MAR-006`、`REF-MAR-007`、`REF-MAR-009`、`REF-MAR-011`、`REF-MAR-012`、`REF-MAR-013`、`REF-MAR-014`、`REF-MAR-015`、`REF-MAR-016`、`REF-MAR-017`、`REF-MAR-018`。

文档和授权队列根据结构化字段和备注推导：授权缺失来自 `authorization_status` 为 `missing`；`authorization_pending` 在标准答案中为空队列；病历请求来自 `documents_received` 中缺少 `office_note`；影像跟进来自备注显示影像待处理，或附件中同时缺少 `xray` 和 `mri`。

行动计划分层为：Tier 1 是紧急且有编码或重复阻断的问题；Tier 2 是常规但存在编码、授权、病历或影像阻断的问题；Tier 3 是没有编码或授权临床阻断、只需行政性文档补齐的问题。重复组被送入合并处理后，没有剩余的无评分跟进分配的已验证可安排记录。

### 评估依据

评估器包含 10 个整点通过或失败的评分项，原始权重总计 22：批次身份和计数 3 分，越界代码 3 分，左右侧或叙述不匹配 2 分，重复组和重复提交分层策略 2 分，共享保险异常 2 分，授权/病历/影像队列及空的授权待处理队列 2 分，Tier 1/2/3 各 2 分，汇总计数 2 分。每项都是全有或全无，不给项内部分分。评估器从相应 JSON 区域提取转诊 ID，做精确集合比较，并核对整数计数，不评价自由文本质量。

常见错误包括把所有 S 代码都当作可接受的骨科代码、忽略重复行导致批次数量错误、把缺少 `office_note` 与影像缺失混为一谈、把无未解决审计阻断的 `REF-MAR-004` 放进 Tier 1、没有区分记录行数和唯一患者数，或把共享保险异常错误升级成患者合并建议。

### 迁移设计

作为训练任务，本任务是转诊质量审计家族的正式已解样例。通过输入和标准答案，少样本技能可以归纳出需要检查 ICD 章节、代码期望术语、左右侧、患者级重复提交、需要核验而不能直接合并的共享保险异常、包含空队列在内的结构化文档字段、备注中的阻断信号以及行动计划分层。这些经验会迁移到后续转诊准备度和骨科批次审计测试任务，但不会在求解者可见提示中直接写成 SOP。

### 构建记录

作者：`train_005` task-builder subagent。

创建日期：2026-07-17。

更新日期：2026-07-17。

主要变更：为 `MAR26-ORTHO-A` 创建提示词、答案模板、标准答案、评估器和双语说明。
