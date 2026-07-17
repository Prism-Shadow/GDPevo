# test_002 Notes - Orthopedic Referral Readiness: July Fracture And Tendon Batch

## English

Data/source lineage: This test task belongs to `task_group_013`, from scenario `SCN_013_healthcare_patient_intake_transfer` and especially source example `E005`, the referral intake audit. It uses the generated shared Cedar Ridge Intake Coordination Portal in `task_group/task_group_013/env/`, with target referral batch `ORTHO-JUL-04`. Solver-visible local files are only `input/prompt.txt` and `input/payloads/answer_template.json`; patient identity, referral, ICD, insurance, records, imaging, appointment, and authorization evidence all come from the portal data.

Task definition: Cedar Ridge Spine and Joint needs the July fracture and tendon referral batch audited before scheduler release. The solver must reconcile referral rows with patient identity and ICD metadata, then return structured JSON containing referral-level readiness, ICD discrepancy records, duplicate groups, shared insurance anomalies, missing-records and missing-imaging blockers, authorization blockers, the ready-to-schedule set, a follow-up action plan, and summary counts. The prompt avoids a procedural SOP list and does not reveal the final values.

Scenario fit: This is a healthcare intake coordination workflow in the same family as the source and train referral tasks. The office must catch coding problems, duplicate faxes, shared insurance identifiers, missing packet evidence, authorization gaps, and appointment-state issues before referrals are handed to schedulers.

Material map: `GET /referrals?batch_id=ORTHO-JUL-04` exposes the eight target referrals. `GET /patients/{patient_id}` or read-only SQL joins provide patient names and DOBs for duplicate and shared-insurance checks. `GET /icd/{code}` provides ICD chapter, service family, and laterality metadata. The referral table fields `records_received`, `imaging_received`, `auth_required`, `auth_status`, `appointment_scheduled`, `appointment_date`, `urgency`, `insurance_id`, `referring_practice`, and `notes` provide the remaining blocker and action-plan evidence. No task-local payload contains an answer-like roster or solution.

Solution basis: The train referral convention audits orthopedic referrals against the `M00-M99` musculoskeletal chapter. `REF0017` and `REF0020` use `J44.9`, observed chapter `J00-J99`, a pulmonary diagnosis that conflicts with the orthopedic referral context; they are coded as both `icd_chapter_mismatch` and `narrative_mismatch`. `REF0018` uses `S83.512A`, an orthopedic service-family code but observed chapter `S00-T88`, so it is an `icd_chapter_mismatch` against expected `M00-M99`. No laterality mismatch is scored because the generated referral narrative does not assert an opposite left/right side.

Duplicate and insurance basis: `REF0021` and `REF0023` are the same patient `P059` / Taylor Bennett, same DOB, same service line, same code, same referral reason, same records/imaging/auth state, and different referring-practice text. They form `DUP-ORTHO-JUL-04-001`; keep `REF0021` and consolidate `REF0023`. Insurance ID `DUP-INS-ORTHO` appears on distinct patients `P057` (`REF0019`) and `P058` (`REF0020`), so it is a true shared-insurance anomaly. Repeated `INS-P059` on `REF0021` and `REF0023` is not a shared-insurance anomaly because it belongs to the same-patient duplicate group.

Blocker and readiness basis: Missing records are `REF0018`, `REF0021`, and `REF0023`. Missing imaging is `REF0017`, `REF0021`, and `REF0023`. Authorization blockers are `REF0018` with `denied`, plus `REF0021` and `REF0023` with `pending`. `REF0016` is the only ready-to-schedule referral: M chapter code, no duplicate or shared-insurance issue, records and imaging present, and authorization not required. `REF0019` is `admin_followup` because its only issue is shared-insurance verification. `REF0022` is `admin_followup` because it is already scheduled and needs appointment review rather than a new scheduling release.

Priority basis: `REF0020` is Tier 1 because it is urgent and has unresolved clinical/coding plus shared-insurance risk. `REF0017`, `REF0018`, `REF0021`, and `REF0023` are Tier 2 because they require routine short-term coding, records, imaging, authorization, or duplicate follow-up. `REF0019` and `REF0022` are Tier 3 administrative follow-up. `REF0016` has no priority tier because it is ready.

Evaluation basis: The evaluator has eight whole weighted scoring points: SP001 ICD discrepancy set and issue metadata (weight 3); SP002 duplicate grouping and consolidation recommendation (2); SP003 shared insurance anomaly excluding legitimate same-patient duplicate sharing (2); SP004 missing records and missing imaging blocker sets (2); SP005 authorization blockers and statuses (2); SP006 ready-to-schedule set (3); SP007 readiness statuses, priority tiers, issue codes, and action codes for follow-up referrals (3); SP008 summary counts by urgency, readiness status, and issue type (1). Each point is all-or-nothing. Raw weights sum to 18, and the standard answer self-scores to 1.0.

Transfer design: This test task is anchored by `train_002` and reinforced by `train_005`. The intended transferred knowledge is that orthopedic referral audit uses the M chapter convention, code/narrative/laterality are separate discrepancy types, same-patient duplicate referrals are consolidated rather than treated as shared-insurance anomalies, distinct-patient policy reuse is an administrative anomaly, records/imaging/auth gates determine readiness, and priority tiers combine urgency with unresolved issue type. The task-specific exploration burden is the new July batch composition, the `J44.9` pulmonary mismatch, the `P059` duplicate pair, the `P057`/`P058` shared insurance anomaly, and the already-scheduled row.

Likely model pitfalls: A solver may accept `S83.512A` because its service family is orthopedics while missing the M chapter convention from train. Another likely error is flagging `INS-P059` as a shared-insurance anomaly despite the same-patient duplicate, or making `REF0019` ready despite the distinct-patient shared insurance ID. Models may also over-score laterality when no opposite-side narrative exists, omit the already-scheduled `REF0022`, or classify all urgent referrals as Tier 1 without checking readiness.

Construction record: Author: Codex task-builder. Created: 2026-07-17. Updated: 2026-07-17. Major changes: created full test_002 task files, standard answer, and deterministic evaluator for `ORTHO-JUL-04`.

## 中文

数据来源：本测试任务属于 `task_group_013`，来源场景为 `SCN_013_healthcare_patient_intake_transfer`，主要对应 `E005` 的转诊审核工作。任务使用共享的 Cedar Ridge Intake Coordination Portal 生成数据，目标批次为 `ORTHO-JUL-04`。求解者可见文件只有 `input/prompt.txt` 和 `input/payloads/answer_template.json`；患者身份、转诊、ICD、保险号、病历、影像、预约和授权证据都来自门户环境。

任务定义：Cedar Ridge Spine and Joint 需要在排班放行前审核七月骨折与肌腱相关转诊批次。求解者需要把转诊行、患者身份和 ICD 元数据交叉核对，输出结构化 JSON，包括逐条 readiness、ICD 差异、重复组、共享保险异常、缺失病历/影像、授权阻塞、可排班集合、后续行动计划和汇总计数。提示语不写 SOP 步骤，也不泄露答案。

场景契合：这是医疗 intake 协调办公室的转诊排班准备工作，与源示例和训练任务属于同一业务族。办公室在把转诊交给排班员之前，需要识别编码问题、重复传真、共享保险号、资料缺口、授权问题和预约状态问题。

材料映射：`GET /referrals?batch_id=ORTHO-JUL-04` 给出八条目标转诊。`GET /patients/{patient_id}` 或只读 SQL join 可用于患者姓名和 DOB 核对。`GET /icd/{code}` 提供 ICD 章节、服务族和侧别元数据。转诊表字段 `records_received`、`imaging_received`、`auth_required`、`auth_status`、`appointment_scheduled`、`appointment_date`、`urgency`、`insurance_id`、`referring_practice` 和 `notes` 提供阻塞和行动计划证据。本地 payload 不包含答案式清单。

解题依据：训练转诊任务中可归纳出骨科转诊按 `M00-M99` 肌肉骨骼章节审核。`REF0017` 和 `REF0020` 使用 `J44.9`，观察章节为 `J00-J99`，且是肺部诊断，与骨科转诊背景不符，因此同时标为 `icd_chapter_mismatch` 和 `narrative_mismatch`。`REF0018` 使用 `S83.512A`，虽然 service family 是 orthopedics，但观察章节是 `S00-T88`，所以相对预期 `M00-M99` 是章节差异。本批次不计分侧别矛盾，因为生成数据里的转诊叙述没有写出相反左右侧。

重复与保险依据：`REF0021` 和 `REF0023` 是同一患者 `P059` / Taylor Bennett，同一 DOB、服务线、编码、转诊原因、records/imaging/auth 状态，只是转诊机构文字不同。它们构成 `DUP-ORTHO-JUL-04-001`，保留 `REF0021` 并合并 `REF0023`。保险号 `DUP-INS-ORTHO` 出现在不同患者 `P057` (`REF0019`) 和 `P058` (`REF0020`) 上，因此是真正的共享保险异常。`REF0021` 和 `REF0023` 重复使用 `INS-P059` 不算共享保险异常，因为它们属于同一患者重复转诊。

阻塞与排班依据：缺失病历为 `REF0018`、`REF0021`、`REF0023`。缺失影像为 `REF0017`、`REF0021`、`REF0023`。授权阻塞为 `REF0018` 的 `denied`，以及 `REF0021` 和 `REF0023` 的 `pending`。`REF0016` 是唯一可排班转诊，因为编码为 M 章节、没有重复或共享保险问题、病历和影像齐全、且不需要授权。`REF0019` 只有共享保险核实问题，所以是 `admin_followup`。`REF0022` 已有预约，因此需要预约复核而不是新放行排班，也归为 `admin_followup`。

优先级依据：`REF0020` 为 Tier 1，因为它是 urgent 且存在未解决的临床/编码与共享保险风险。`REF0017`、`REF0018`、`REF0021`、`REF0023` 为 Tier 2，因为它们需要常规短期编码、病历、影像、授权或重复处理。`REF0019` 和 `REF0022` 为 Tier 3 行政跟进。`REF0016` 已 ready，因此没有优先级。

评估依据：评估器包含八个整点评分项：SP001 ICD 差异集合及元数据，权重 3；SP002 重复组和合并建议，权重 2；SP003 排除同一患者重复后的共享保险异常，权重 2；SP004 缺失病历和影像集合，权重 2；SP005 授权阻塞及状态，权重 2；SP006 可排班集合，权重 3；SP007 后续转诊的 readiness、优先级、issue code 和 action code，权重 3；SP008 urgency、readiness 和 issue 类型汇总计数，权重 1。每项都是全有或全无。原始权重总和为 18，标准答案自评为 1.0。

迁移设计：本测试任务的训练锚点是 `train_002`，并由 `train_005` 强化。需要迁移的知识包括：骨科转诊按 M 章节审核，章节/叙述/侧别是不同差异类型，同一患者重复转诊应合并而不视为共享保险异常，不同患者复用保险号是行政异常，records/imaging/auth gate 决定 readiness，优先级由 urgency 和未解决问题类型共同决定。任务自身探索难点在于新的七月批次、`J44.9` 肺部编码不匹配、`P059` 重复组、`P057`/`P058` 共享保险异常，以及已预约的 `REF0022`。

常见模型错误：模型可能因为 `S83.512A` 的 service family 是 orthopedics 而接受它，忽略训练任务中的 M 章节规则。另一个常见错误是把同一患者重复转诊的 `INS-P059` 错判为共享保险异常，或者把 `REF0019` 当作 ready 而忽略不同患者共享保险号。模型也可能在没有相反侧别叙述时过度标注 laterality，漏掉已预约的 `REF0022`，或只根据 urgent 字段把所有急件都设为 Tier 1。

构造记录：作者 Codex task-builder。创建日期 2026-07-17。更新日期 2026-07-17。主要变更：为 `ORTHO-JUL-04` 创建完整 test_002 任务文件、标准答案和确定性评估器。
