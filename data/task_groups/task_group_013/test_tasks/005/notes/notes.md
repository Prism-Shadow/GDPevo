# test_005 Notes - Referral-To-Chart Activation: Cardiology Pre-Visit Intake

## English

Data/source lineage: This task belongs to `task_group_013`, source scenario `SCN_013_healthcare_patient_intake_transfer`, and uses the shared Cedar Ridge Intake Coordination Portal in `task_group/task_group_013/env/`. The target object is cardiology referral batch `CARD-JUL-03`, containing referrals `REF0024` through `REF0029`. It is a test task in the referral-to-chart activation family, anchored by `train_002` for referral readiness and duplicate handling, `train_004` for chart-readiness conventions, and `train_005` for the combined referral-to-chart handoff.

Task definition: The solver sees an office request, the environment base URL placeholder, and the JSON answer template. They must use the portal endpoints or read-only SQL to inspect target referrals, ICD metadata, patient identity, documents, and chart artifacts. The expected output covers readiness for each referral, clinical/code discrepancy referrals, authorization/records/imaging blockers, duplicate handling, chart activation gaps for referrals that can proceed, correspondence queue selection, and priority order for non-ready work.

Scenario fit: This is a realistic healthcare intake coordination task. It combines referral office review with EHR pre-visit activation: a cardiology referral can only move toward appointment confirmation after referral coding, document, authorization, duplicate, and chart-readiness issues have been reconciled.

Material map: `GET /referrals?batch_id=CARD-JUL-03` identifies the six target referrals. `GET /patients/{patient_id}` confirms identity for duplicate review and chart action. `GET /icd/{code}` provides service-family and chapter metadata. `GET /documents` can reveal referral support documents, though the generated referral row flags are the controlling records and imaging indicators for this batch. `GET /chart/{patient_id}` exposes current, stale, draft, or missing chart artifacts. `POST /query` can be used for bulk joins across these tables.

Solution basis: `REF0028` is the only ready referral: it has cardiology code `I25.10`, a cardiology-compatible reason, records present, imaging present, no authorization blocker, and no true duplicate. `REF0024`, `REF0027`, and `REF0029` carry orthopedic code `M54.16` in a cardiology batch, so they require clinical/code clarification. `REF0025` carries pulmonary-family symptom code `R06.02` in the cardiology batch and is also a code-family discrepancy. `REF0026` uses cardiology code `I25.10`, but the referral reason is pain evaluation; it is also missing records and has pending authorization, so it is blocked rather than merely under review. `REF0029` also has missing records, denied authorization, and an appointment scheduled before clearance.

Duplicate basis: `REF0027` and `REF0028` have possible-duplicate notes, but they are distinct patients with different DOBs and different conditions. The correct duplicate group list is empty, and both notes are cleared as false duplicate-review flags. This transfers directly from `train_002` and `train_005`: duplicate handling is based on patient identity plus close service/condition, not on a note or referring practice alone.

Chart activation basis: Cardiology pre-visit confirmation requires current demographics, active problems, medications, allergies, vitals, and consent for referrals that are otherwise ready. Labs are not part of this cardiology pre-visit activation output, unlike the pulmonary train task. `P065` already has an existing chart but only stale demographics and stale active-problems rows; medications, allergies, vitals, and consent are absent. Therefore `REF0028` has `chart_action` `update_chart` and must create or refresh `active_problems`, `allergies`, `consent`, `demographics`, `medications`, and `vitals`.

Correspondence and priority basis: Non-ready referrals with only a code-family issue use `clinical_code_clarification`: `REF0024`, `REF0025`, and `REF0027`. `REF0026` uses `auth_records_request` because records and pending authorization are the operational blockers, while retaining `clinical_reason_mismatch` as a reason code. `REF0029` uses `appointment_hold_notice` because it has an appointment scheduled before clearance plus denied authorization, missing records, and wrong service-family code. Priority order is `REF0024` first as an urgent unresolved clinical/code issue (`tier_1_immediate`), then the remaining code-family clarification queue `REF0025`, `REF0026`, and `REF0027`, followed by `REF0029` as the administrative appointment hold after clinical routing is established; all of those remaining items are `tier_2_short_term`.

Evaluation basis: The evaluator has seven whole scoring points with raw weights `[3, 2, 2, 2, 2, 2, 2]`. SP001 checks readiness status and blocker-code sets for all six referrals. SP002 checks the clinical/code discrepancy set. SP003 checks authorization, records, and imaging blocker sets. SP004 checks duplicate handling and false-duplicate clearing. SP005 checks chart activation gaps for ready referrals. SP006 checks correspondence template type and reason-code sets. SP007 checks priority ordering and tier assignment. These points cover at least four distinct outcomes: referral readiness, coding quality, document/authorization blockers, duplicate disposition, chart activation, correspondence routing, and queue prioritization. Each point is all-or-nothing, with reason, blocker, and artifact arrays normalized as sets.

Transfer design: High-value scoring points depend on train anchors. `train_002` anchors referral code-family review, duplicate grouping by patient/condition, blocker sets, and priority tiering. `train_004` anchors the distinction between an existing chart and a chart-ready state with current structured artifacts. `train_005` anchors the combined referral-to-chart activation workflow, false duplicate clearing, correspondence template selection, and not listing chart gaps for referrals that cannot proceed. The cardiology test changes service line, target code family, reason patterns, and chart artifact set, so the train examples help but do not reveal the answer.

Likely model pitfalls: A solver may treat `R06.02` as acceptable for cardiology because shortness of breath can be cardiology-adjacent, even though the portal metadata places it in the pulmonary family. Another common error is accepting possible-duplicate notes at face value, listing chart gaps for all blocked referrals, counting the draft imaging document on `REF0028` as an imaging blocker despite the referral row indicating imaging received, or over-prioritizing the scheduled `REF0029` appointment hold ahead of unresolved clinical/code routing work.

Construction record: Author: Codex task-builder. Created: 2026-07-17. Updated: 2026-07-17. Major changes: created `test_tasks/005` prompt, answer template, standard answer, evaluator, and notes only.

## 中文

数据来源：本任务属于 `task_group_013`，源场景为 `SCN_013_healthcare_patient_intake_transfer`，使用共享的 Cedar Ridge Intake Coordination Portal，环境目录为 `task_group/task_group_013/env/`。目标对象是心内科转诊批次 `CARD-JUL-03`，包含 `REF0024` 到 `REF0029`。这是转诊到病历启用工作流的测试任务，训练锚点包括 `train_002` 的转诊就绪与重复处理、`train_004` 的病历就绪判断，以及 `train_005` 的转诊和建档联合交接。

任务定义：求解者只能看到办公室式请求、环境 URL 占位符和 JSON 模板。需要通过门户接口或只读 SQL 查询目标转诊、ICD 元数据、患者身份、文档和病历工件。输出要覆盖每条转诊的就绪状态、临床/编码差异、授权/病历/影像阻塞、重复处理、可推进转诊的病历启用缺口、函件队列以及非就绪事项优先级。

场景契合：这是医疗 intake 协调办公室的真实工作。它把转诊审核和 EHR 预约前建档连接起来：心内科转诊要进入预约确认，必须同时清理编码、附件、授权、重复和病历结构化材料问题。

材料映射：`GET /referrals?batch_id=CARD-JUL-03` 用于取得六条目标转诊；`GET /patients/{patient_id}` 用于核对身份并判断重复和病历动作；`GET /icd/{code}` 提供服务族和章节信息；`GET /documents` 可辅助查看附件，但本批次以转诊行中的 records 和 imaging 标志作为控制字段；`GET /chart/{patient_id}` 展示 current、stale、draft 或缺失的病历工件；`POST /query` 可用于批量连接这些表。

答案依据：`REF0028` 是唯一 ready 的转诊，它具有心内科代码 `I25.10`、心内科兼容原因、病历和影像已收到、无授权阻塞且没有真实重复。`REF0024`、`REF0027`、`REF0029` 在心内科批次中使用骨科代码 `M54.16`，需要临床/编码澄清。`REF0025` 在心内科批次中使用肺科服务族代码 `R06.02`，同样是编码服务族差异。`REF0026` 虽然使用心内科代码 `I25.10`，但转诊原因是 pain evaluation，并且缺少病历、授权 pending，因此是 blocked。`REF0029` 还缺少病历、授权 denied，且已有未清关预约。

重复依据：`REF0027` 和 `REF0028` 的 notes 中有 possible duplicate，但它们是不同患者、不同 DOB、不同病情。正确的重复组为空，二者都应作为误报重复被清除。这个判断迁移自 `train_002` 和 `train_005`：重复要按患者身份和相近服务/病情判断，不能只看备注或转诊来源。

病历启用依据：心内科预约前确认需要 current demographics、active problems、medications、allergies、vitals 和 consent。与肺科训练任务不同，本心内科输出不要求 labs。`P065` 已有 chart，但 demographics 和 active problems 均过期，medications、allergies、vitals、consent 缺失。因此 `REF0028` 的 `chart_action` 是 `update_chart`，需要补建或刷新 `active_problems`、`allergies`、`consent`、`demographics`、`medications`、`vitals`。

函件与优先级依据：只有编码服务族问题的非就绪转诊使用 `clinical_code_clarification`，包括 `REF0024`、`REF0025`、`REF0027`。`REF0026` 使用 `auth_records_request`，因为病历缺失和授权 pending 是主要运营阻塞，同时保留 `clinical_reason_mismatch` 原因码。`REF0029` 使用 `appointment_hold_notice`，因为它在清关前已有预约，并且授权 denied、病历缺失、服务族编码错误。优先级为 `REF0024` 第一，因为它是 urgent 且有未解决临床/编码问题；随后处理剩余临床/编码路由队列 `REF0025`、`REF0026`、`REF0027`，最后是行政性的预约暂停 `REF0029`；这些剩余事项均为 `tier_2_short_term`。

评价依据：评估器包含七个整点评分项，原始权重为 `[3, 2, 2, 2, 2, 2, 2]`。SP001 检查六条转诊的就绪状态和阻塞码集合；SP002 检查临床/编码差异集合；SP003 检查授权、病历、影像阻塞集合；SP004 检查重复处理和误报重复清除；SP005 检查 ready 转诊的病历启用缺口；SP006 检查函件模板和原因码；SP007 检查优先顺序和优先级层级。这些评分覆盖转诊就绪、编码质量、文档/授权、重复处理、病历启用、函件路由和队列优先级等多个不同业务结果。每项只有全得或不得分，原因码、阻塞码和工件数组按集合归一化。

迁移设计：高价值评分项依赖训练锚点。`train_002` 锚定编码服务族审核、按患者和病情识别重复、阻塞集合和优先级；`train_004` 锚定“已有 chart 不等于 chart-ready”的结构化工件判断；`train_005` 锚定转诊到建档的联合流程、误报重复清除、函件模板选择，以及只为可推进转诊列出病历缺口。本测试任务换成心内科服务线、不同编码族、不同转诊原因和不同病历工件集合，因此训练样本能提供方法但不会泄露答案。

常见错误：模型可能因为气短在现实中也可能与心内科相关，而把 `R06.02` 当成心内科可接受代码；也可能照单接受 possible duplicate 备注；为所有 blocked 转诊列出病历缺口；把 `REF0028` 的 draft imaging document 当成影像阻塞而忽略转诊行中的 imaging received；或把已预约的 `REF0029` 过度提前到尚未解决的临床/编码路由事项之前。

构建记录：作者 Codex task-builder。创建日期 2026-07-17。更新日期 2026-07-17。主要变更：仅在 `test_tasks/005` 下创建 prompt、答案模板、标准答案、评估器和说明文件。
