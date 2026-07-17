# train_002 Notes - Orthopedic Referral Readiness: June Spine And Joint Batch

## English

Data/source lineage: This train task belongs to `task_group_013`, based on scenario `SCN_013_healthcare_patient_intake_transfer` and especially source example `E005`, the orthopedic referral intake audit. It uses the generated shared Cedar Ridge Intake Coordination Portal in `task_group/task_group_013/env/`, with target referral batch `ORTHO-JUN-01`. The solver-visible local files are `input/prompt.txt` and `input/payloads/answer_template.json`; all clinical, coding, patient, duplicate, insurance, imaging, records, and authorization evidence comes from the portal data.

Task definition: The business request is to audit the June spine and joint referral batch before scheduling. The solver must use the portal endpoints or read-only SQL to reconcile the referral rows with patient identity and ICD metadata, then produce structured JSON with referral-level review records, ICD discrepancy records, duplicate groups, shared insurance anomalies, blocker sets, ready-to-schedule referrals, a follow-up action plan, and summary counts. The prompt intentionally does not provide a procedure list or final values.

Scenario fit: This task is a direct healthcare intake coordination workflow. It mirrors the source secretary/referral audit work: a scheduling office has to catch coding quality problems, duplicate faxes, missing attachments, payer authorization gaps, and non-clinical insurance anomalies before appointments are released to schedulers.

Material map: `GET /referrals?batch_id=ORTHO-JUN-01` exposes the nine target referrals. `GET /patients/{patient_id}` or SQL joins provide patient identity for duplicate and insurance checks. `GET /icd/{code}` provides chapter, service family, and laterality metadata. The referral rows contain `records_received`, `imaging_received`, `auth_required`, `auth_status`, `appointment_scheduled`, `urgency`, `insurance_id`, and referring-office contact fields. No task-local payload contains the answer.

Solution basis: The E005 convention audits orthopedic referrals against the `M00-M99` musculoskeletal ICD chapter. Therefore referrals with `S83.512A` are chapter discrepancies even though the generated ICD metadata labels the service family as orthopedics. The discrepancy referrals are `REF0001`, `REF0005`, `REF0006`, `REF0007`, `REF0008`, and `REF0009`, all with observed chapter `S00-T88` and expected chapter `M00-M99`. No additional narrative or laterality mismatch is scored in this batch because the available referral narrative fields do not assert a conflicting side.

Duplicate basis: `REF0007` and `REF0009` are the same patient `P046` / Finley Iqbal, same DOB, same service line, same code, and same referral reason, despite different referring-practice text. The group is `DUP-ORTHO-JUN-01-001`, with `REF0007` retained as the primary row and `REF0009` consolidated.

Shared insurance basis: Insurance ID `DUP-INS-ORTHO` appears on distinct patients `P043` (`REF0004`) and `P044` (`REF0005`). This is a true shared-insurance anomaly. The repeated `INS-P046` on `REF0007` and `REF0009` is not scored as a shared-insurance anomaly because it belongs to the duplicate same-patient group.

Blocker and readiness basis: Missing records are `REF0003` and `REF0006`; missing imaging is `REF0002` and `REF0006`; authorization blockers are `REF0003` with `denied` and `REF0006` with `pending`. The ready-to-schedule set is empty because every referral has at least one unresolved code, duplicate, shared-insurance, records, imaging, authorization, or existing-appointment review issue. Statuses are `under_review` for coding/clinical review rows, `blocked` for records/imaging/auth blockers, and `admin_followup` for the insurance-only anomaly on `REF0004`.

Priority basis: `REF0001` and `REF0005` are Tier 1 because they are urgent referrals with unresolved coding/data-quality risk. `REF0002`, `REF0003`, `REF0006`, `REF0007`, `REF0008`, and `REF0009` are Tier 2 because they require routine short-term records, imaging, authorization, duplicate, scheduled-appointment, or corrected-code follow-up. `REF0004` is Tier 3 because the only issue is administrative insurance verification.

Evaluation basis: The evaluator has eight whole weighted points: SP001 ICD discrepancy set and issue metadata (weight 3); SP002 duplicate grouping and consolidation recommendation (2); SP003 shared insurance anomaly excluding legitimate duplicate sharing (2); SP004 missing records and imaging blocker sets (2); SP005 authorization blockers and statuses (2); SP006 ready-to-schedule set (3); SP007 priority tiers, action codes, and readiness statuses for follow-up referrals (3); SP008 summary counts by urgency, readiness status, and issue type (1). Each point is all-or-nothing. The raw weights sum to 18.

Likely model pitfalls: A solver may treat all orthopedic service-family ICD rows as valid and miss that the office is auditing against the M chapter convention from E005. Another likely error is flagging `INS-P046` as an insurance anomaly even though it is the same patient duplicate, or treating `REF0004` as ready despite the distinct-patient shared policy ID. Models may also overlook the scheduled appointment on `REF0008`, omit the duplicate `REF0009`, or give Tier 1 to all urgent rows without checking what is unresolved.

Transfer design: As a train task, this provides transferable experience for later referral tasks: use the M-chapter audit convention, separate chapter/narrative/laterality discrepancy types, match duplicates by patient identity and condition rather than referring practice, exclude same-patient duplicate sharing from shared-insurance anomalies, combine records/imaging/auth gates for readiness, and assign tiers from urgency plus unresolved issue type. It is a real solved task, not a tutorial; the skill should be inferred from comparing the input with `output/answer.json`.

Construction record: Author: Codex task-builder. Created: 2026-07-17. Updated: 2026-07-17. Major changes: created full train_002 task files, standard answer, and deterministic evaluator for `ORTHO-JUN-01`.

## 中文

数据来源：本训练任务属于 `task_group_013`，来源场景为 `SCN_013_healthcare_patient_intake_transfer`，主要继承 `E005` 的骨科转诊审核工作。任务使用共享的 Cedar Ridge Intake Coordination Portal 生成数据，目标批次是 `ORTHO-JUN-01`。求解者可见文件只有 `input/prompt.txt` 和 `input/payloads/answer_template.json`；诊断编码、患者身份、重复转诊、保险号、影像、病历和授权证据都来自环境门户。

任务定义：业务背景是六月脊柱与关节转诊批次在进入排班队列前需要清理。求解者需要通过门户接口或只读 SQL 汇总转诊行、患者身份和 ICD 元数据，输出结构化 JSON，包括逐条转诊审核、ICD 差异、重复组、共享保险异常、缺失资料/影像、授权阻塞、可排班集合、后续行动优先级和汇总计数。提示语刻意不写操作步骤，也不泄露答案。

场景契合：该任务体现医疗 intake 协调办公室的真实工作。办公室在放行排班前，需要识别编码质量问题、重复传真、附件缺失、付款方授权缺口以及非临床性的保险数据异常。

材料映射：`GET /referrals?batch_id=ORTHO-JUN-01` 给出九条目标转诊。`GET /patients/{patient_id}` 或 SQL join 可用于患者身份核对。`GET /icd/{code}` 提供章节、服务族和侧别元数据。转诊表字段提供 records、imaging、auth、urgency、insurance_id、appointment 和转诊办公室信息。本任务没有任何本地 payload 直接包含答案。

解题依据：按照 `E005` 的骨科办公室习惯，本任务按 `M00-M99` 肌肉骨骼章节审核。因此 `S83.512A` 虽然在生成数据中 service_family 为 orthopedics，但仍属于 `S00-T88` injury 章节，不符合 M 章节要求。ICD 章节差异转诊为 `REF0001`、`REF0005`、`REF0006`、`REF0007`、`REF0008`、`REF0009`。本批次没有额外计分的叙述或侧别矛盾，因为可用叙述字段没有写出相反侧别。

重复与保险依据：`REF0007` 和 `REF0009` 是同一患者 `P046`，同一 DOB、服务线、编码和转诊原因，应合并到 `REF0007`。保险号 `DUP-INS-ORTHO` 同时出现在不同患者 `P043` 和 `P044` 上，因此是真正的共享保险异常。`INS-P046` 出现在 `REF0007` 和 `REF0009` 上不算共享保险异常，因为那是同一患者重复转诊。

阻塞与排班依据：缺失病历为 `REF0003`、`REF0006`；缺失影像为 `REF0002`、`REF0006`；授权阻塞为 `REF0003` 的 `denied` 和 `REF0006` 的 `pending`。可排班集合为空，因为每条转诊都至少有编码、重复、共享保险、资料、影像、授权或已预约复核问题。状态划分为 coding/clinical review 的 `under_review`、资料/影像/授权问题的 `blocked`、以及只有保险核对的 `admin_followup`。

优先级依据：`REF0001` 和 `REF0005` 是 urgent 且存在未解决编码或数据质量风险，所以为 Tier 1。`REF0002`、`REF0003`、`REF0006`、`REF0007`、`REF0008`、`REF0009` 是常规短期跟进，属于 Tier 2。`REF0004` 只有行政性保险号核实，属于 Tier 3。

评估依据：评估器有八个整点评分项：SP001 ICD 差异集合及元数据，权重 3；SP002 重复组和合并建议，权重 2；SP003 排除同一患者重复后的共享保险异常，权重 2；SP004 缺失病历和影像集合，权重 2；SP005 授权阻塞及状态，权重 2；SP006 可排班集合，权重 3；SP007 后续转诊的优先级、行动码和 readiness 状态，权重 3；SP008 urgency、readiness 和 issue 类型汇总计数，权重 1。每项都是整点通过或失败，总权重 18。

常见模型错误：模型可能只看 service_family 为 orthopedics 而忽略 M 章节规则；可能把同一患者重复转诊的 `INS-P046` 错判为共享保险异常；也可能把 `REF0004` 当作 ready 而忽略不同患者共享保险号。其他风险包括漏掉已预约但仍需编码复核的 `REF0008`、漏掉重复行 `REF0009`、或只按 urgent 字段机械分 Tier。

迁移设计：作为训练任务，它向后续转诊任务传递可迁移经验：骨科按 M 章节审核、区分章节/叙述/侧别差异、按患者身份和病情而不是转诊来源识别重复、同一患者重复不算共享保险异常、将资料/影像/授权组合为 readiness gate，并结合 urgency 与未解决问题类型划分优先级。这是正式训练样本，不是教程；技能应从输入和标准答案的对照中归纳出来。

构造记录：作者 Codex task-builder。创建日期 2026-07-17。更新日期 2026-07-17。主要变更：为 `ORTHO-JUN-01` 创建完整 train_002 任务文件、标准答案和确定性评估器。
