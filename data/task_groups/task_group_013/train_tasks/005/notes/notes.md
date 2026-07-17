# train_005 Notes - Referral-To-Chart Activation: Pulmonary Referral Intake

## English

Data/source lineage: This task belongs to `task_group_013`, source scenario `SCN_013_healthcare_patient_intake_transfer`, and uses the task-group referral and chart-readiness operation families derived from examples `E003` and `E005`, with transfer-adjacent routing habits from `E001`. The shared generated environment is `task_group/task_group_013/env/`, backed by `env/data/clinic.db`. The target business object is referral batch `PULM-JUN-02`, containing referrals `REF0010` through `REF0015`.

Task definition: The solver sees a normal office request and the answer template. They must use `<TASK_ENV_BASE_URL>` to inspect referrals, patients, ICD metadata, documents, and chart artifacts. The expected output combines referral scheduling readiness, code/clinical discrepancies, auth and records blockers, duplicate review results, chart artifact work for referrals that can proceed, correspondence template selection for non-ready referrals, and the non-ready action priority order.

Scenario fit: This is a healthcare intake coordination task. It combines referral intake audit logic from the orthopedic referral family with EHR chart activation logic from new-patient/chart onboarding. The work reflects a realistic handoff from referral scheduling to chart-prep staff: a referral can be clinically schedulable while still needing chart artifacts before appointment confirmation.

Material map: `GET /referrals?batch_id=PULM-JUN-02` identifies the target referrals. `GET /patients/{patient_id}` confirms identity and distinguishes false duplicate flags. `GET /icd/{code}` supplies service-family metadata for referral-code consistency. `GET /documents` can corroborate document availability, though the referral row has the controlling records/imaging flags for this batch. `GET /chart/{patient_id}` supplies chart artifacts and current/stale status. `POST /query` can be used for bulk reconciliation.

Solution basis: `REF0010` and `REF0013` are ready for scheduling. `REF0011` is a pulmonary-batch referral carrying `I25.10`, a cardiology-family code. `REF0014` has a pulmonary asthma code but a pain-evaluation clinical reason, which requires clarification before pulmonary scheduling. `REF0015` has a pulmonary symptom code but also a pain-evaluation clinical reason, missing records, denied authorization, and an already scheduled appointment that should not be confirmed. `REF0012` is blocked by missing records and denied authorization. No target referral is a true duplicate; `REF0013` and `REF0014` are only false duplicate-review flags because patient identity and clinical condition differ. Imaging blockers are empty.

Chart activation basis: For ready pulmonary referrals, the pre-visit chart needs current demographics, active problems, medications, allergies, vitals, labs, and consent. `P048` already has current demographics and medications but stale active problems and lacks allergies, vitals, labs, and consent, so `REF0010` requires updating those five artifacts. `P051` has stale demographics, active problems, and medications, and lacks allergies, vitals, labs, and consent, so `REF0013` requires seven artifacts. Both are existing charts, so the chart action is `update_chart`.

Evaluation basis: The evaluator uses seven whole scoring points with raw weights `[3, 2, 2, 2, 2, 2, 2]`. SP001 checks readiness status and blocker-code sets for all six referrals. SP002 checks the clinical/code discrepancy set. SP003 checks authorization, records, and imaging blocker sets. SP004 checks duplicate handling and false duplicate-review clearing. SP005 checks chart activation needs for ready referrals. SP006 checks correspondence template type and reason-code sets for each non-ready referral. SP007 checks priority ordering and tier assignment. Each point is all-or-nothing; reason, blocker, and artifact arrays are normalized as sets.

Priority basis: The urgent unresolved clinical discrepancy `REF0014` is rank 1 and `tier_1_immediate`. `REF0015` is rank 2 because it is blocked and already scheduled, requiring appointment-hold handling before routine follow-up. `REF0011` and `REF0012` are routine tier-2 items, ordered with clinical-code clarification before ordinary auth/records repair.

Transfer design: As a train task, this formal answer exposes transferable habits for later test tasks without presenting a tutorial in the prompt. Solvers comparing attempts with the answer can infer that service-family code conflicts and clinical reason mismatches block scheduling, that duplicate notes must be tested against identity and condition rather than accepted literally, that authorization and records gaps are separate blockers, that chart existence is not the same as chart readiness, and that correspondence templates should follow the dominant operational blocker.

Likely model pitfalls: Common errors include treating all pulmonary-family codes as ready despite a mismatched clinical reason, treating `REF0013` and `REF0014` as true duplicates because of the notes field, ignoring an appointment that was scheduled before clearance, over-using PBM/coverage records that are not referral readiness gates for this task, or listing chart gaps for blocked referrals rather than only ready referrals.

Construction record: Created by Codex task-builder for `train_005` on 2026-07-17. Files created under `task_group/task_group_013/train_tasks/005/` only.

## 中文

数据来源：本任务属于 `task_group_013`，源场景是 `SCN_013_healthcare_patient_intake_transfer`。它使用来自 `E003` 的图表启用/建档经验和来自 `E005` 的转诊审核经验，并借鉴 `E001` 中非就绪病例的联络路由习惯。共享环境位于 `task_group/task_group_013/env/`，数据来自 `env/data/clinic.db`。目标对象是转诊批次 `PULM-JUN-02`，包含 `REF0010` 到 `REF0015`。

任务定义：求解者只能看到办公室式请求和答案模板，需要通过 `<TASK_ENV_BASE_URL>` 查询转诊、患者、ICD 元数据、文档和图表工件。输出要同时覆盖排程就绪性、临床/编码不一致、授权与病历阻塞、重复处理、可排程转诊的图表补建需求、非就绪转诊的函件模板，以及非就绪事项的优先顺序。

场景匹配：这是医疗转诊 intake 协调任务，连接了转诊排程审核和 EHR 图表启用两个工作流。它模拟转诊办公室与图表准备人员之间的交接：转诊本身可以进入排程，但确认预约前仍可能需要补齐结构化图表工件。

材料地图：`GET /referrals?batch_id=PULM-JUN-02` 用于定位目标转诊；`GET /patients/{patient_id}` 用于核对身份并排除误报重复；`GET /icd/{code}` 用于判断编码的服务科别；`GET /documents` 可辅助核对支持文件，但本批次以转诊行中的 records/imaging 标志作为控制字段；`GET /chart/{patient_id}` 用于查看图表工件及其 current/stale 状态；`POST /query` 可用于批量核对。

答案依据：`REF0010` 和 `REF0013` 可进入排程。`REF0011` 属于肺科批次但使用心内科代码 `I25.10`。`REF0014` 使用肺科哮喘代码，但临床原因是疼痛评估，需要澄清。`REF0015` 使用肺科症状代码，但也有疼痛评估原因，并且缺少病历、授权被拒、已有未清关预约。`REF0012` 因缺少病历和授权被拒而阻塞。目标转诊中没有真实重复；`REF0013` 和 `REF0014` 的 possible duplicate 只是误报，因为患者身份和临床问题不同。影像阻塞为空。

图表启用依据：可排程的肺科转诊在确认前需要 current demographics、active problems、medications、allergies、vitals、labs 和 consent。`P048` 已有 current demographics 和 medications，但 active problems 过期，且缺 allergies、vitals、labs、consent，因此 `REF0010` 需要补五项。`P051` 的 demographics、active problems、medications 均过期，且缺 allergies、vitals、labs、consent，因此 `REF0013` 需要补七项。两者已有图表，所以动作是 `update_chart`。

评价依据：评估器包含 7 个整点评分项，原始权重为 `[3, 2, 2, 2, 2, 2, 2]`。SP001 检查六个转诊的就绪状态和阻塞代码集合；SP002 检查临床/编码不一致集合；SP003 检查授权、病历、影像阻塞集合；SP004 检查重复处理和误报重复的清除；SP005 检查可排程转诊的图表启用需求；SP006 检查非就绪转诊的函件模板和原因代码；SP007 检查优先顺序和优先级层级。每项只有全得或不得分；原因、阻塞和工件数组按集合归一化。

优先级依据：紧急且存在未解决临床澄清问题的 `REF0014` 为第 1 位、`tier_1_immediate`。`REF0015` 因为已排预约但未清关，排第 2 位，需要先发 appointment hold。`REF0011` 和 `REF0012` 都是常规 tier-2 项，临床/编码澄清优先于普通授权/病历补件。

迁移设计：作为训练任务，本任务不是教程，但标准答案能让后续技能生成器推断可迁移规则：服务科别编码冲突和临床原因不匹配会阻止排程；重复备注必须用身份和病情核实，不能照单全收；授权和病历缺口是不同阻塞；已有 chart 不等于 chart-ready；函件模板应匹配主导的运营阻塞。

常见错误：把所有肺科 family 代码都当成可排程而忽略 clinical reason；因为 notes 字段把 `REF0013` 和 `REF0014` 错判为重复；忽略未清关却已排预约的问题；把 PBM/coverage 当作本任务的主要转诊门槛；或为被阻塞转诊列出图表补建需求。

构建记录：由 Codex task-builder 于 2026-07-17 创建，仅写入 `task_group/task_group_013/train_tasks/005/`。
