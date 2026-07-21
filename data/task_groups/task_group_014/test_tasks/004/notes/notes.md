# test_004 Notes: PET MPI P2P Overturn

## English

### Data and Source Lineage

This test task belongs to `task_group_014`, scenario `SCN_014_healthcare_payer_authorization_appeals`, with source-example influence from `E007` peer-to-peer escalation and `E005` end-to-end prior authorization. The assigned design brief is `test_004: PET MPI P2P Overturn` in `scratch/task_builder_assignments.md`.

The shared generated environment is the Northstar Health Plan SQLite-backed payer-operations service described in `scratch/env_blueprint.md` and `task_group/task_group_014/env/manifest.json`, generated with seed `140417`. The target business record is `P2P-TE-004`. Task-local visible files are `input/prompt.txt`, `input/payloads/task_context.json`, and `input/payloads/answer_template.json`.

### Task Definition and Scenario Fit

The solver acts as a peer-to-peer coordinator closing a cardiac PET myocardial perfusion imaging authorization after the completed P2P discussion. The visible request identifies the case ID, role, reporting date, environment access shape, and required JSON output. The expected work is to inspect the target case, requested service line, PET MPI policy, current clinical evidence, completed P2P event, and authorization record, then return the final closure summary.

This task fits the P2P and appeal workflow family. It tests late-stage utilization management status reconstruction: a P2P outcome must be reconciled with policy criteria, new clinical information, final authorization state, letter type, and whether an adverse-path appeal deadline still applies.

### Material Map

`cases` identifies `P2P-TE-004`, policy `POL-PET-MPI-2026`, stage `medical_director`, status `p2p_complete`, request date `2026-06-07`, and due date `2026-06-12`. `request_lines` provides CPT `78431`, one requested unit, service date `2026-06-18`, and diagnosis codes. `policies` and `policy_criteria` define PET MPI requirements, including covered cardiac indication and at least one PET-over-SPECT factor. `documents` contains current addendum `DOC-TE-004-P2P`. `document_facts` records known CAD with angina, prior equivocal SPECT, and BMI 42. `p2p_events` records `P2P-TE-004-E1`, the new information supplied during the call, outcome `overturn_to_approval`, and final status `approved`. `authorizations` records `NPA-2406199`, approved CPT `78431`, one approved unit, and date range `2026-06-18` to `2026-06-18`.

### Solution and Evaluation Basis

The standard answer sets `case_id` `P2P-TE-004`, `p2p_id` `P2P-TE-004-E1`, requested CPT `78431`, P2P outcome `overturn_to_approval`, final status `approved`, criteria `PET-IND=met` and `PET-FACTOR=met`, resolved criteria `PET-FACTOR`, `new_information_changed_review=true`, supporting PET factors `prior_equivocal_spect` and `bmi_limitation`, authorization `NPA-2406199` for one unit on `2026-06-18`, letter type `approval`, recommended alternative `none`, and no internal appeal deadline.

The evaluator uses six whole-point scoring goals with raw weights `[1, 3, 2, 2, 2, 1]`: identity and requested CPT; overturn outcome and approved final status; final criteria result map; new-information flag with resolved criterion and supporting PET factors; authorization number, units, dates, and CPT; and approval letter with no denial path. These goals span identity/service extraction, P2P adjudication, criteria application, source-change interpretation, authorization issuance, and appeal-path handling. Each scoring point is all-or-zero with exact enum, list, date, integer, and object checks after light normalization.

Likely model pitfalls include copying the `train_004` uphold pattern without noticing the new patient-specific evidence, omitting `PET-FACTOR` from resolved criteria, treating BMI alone as sufficient while missing the prior equivocal SPECT factor, leaving a denial letter or internal appeal deadline in an approval outcome, or failing to connect the authorization row to the overturned P2P.

### Transfer Design

The main train anchor is `train_004`, where the standard answer shows that a PET MPI P2P turns on whether the call supplies new patient-specific evidence that resolves the PET-over-SPECT criterion gap. The transfer-dependent scoring points in this test are the overturn outcome and approved status, the criteria map with `PET-FACTOR=met`, the new-information flag with supporting PET factors, and the approval letter with no adverse appeal path. The task-specific exploration difficulty remains in locating the different test case, reading its addendum facts, connecting those facts to the policy criteria, and extracting the authorization values.

Secondary transfer comes from `train_001`, which reinforces current evidence source selection, and from `train_003`, which reinforces matching final authorization records rather than relying on stale or generic status summaries. The prompt does not restate the hidden SOP; it only asks for a realistic P2P closure product and leaves the solver to infer the source precedence and P2P decision rule from the shared environment and train anchors.

### Construction Record

Author: Builder I. Created: 2026-07-18. Updated: 2026-07-18. Major changes: created the `test_tasks/004` prompt, task context, answer template, standard answer, deterministic evaluator, eval wrapper, and bilingual notes. No files outside `task_group/task_group_014/test_tasks/004/` were edited.

## 中文

### 数据和来源沿革

本测试任务属于 `task_group_014`，场景为 `SCN_014_healthcare_payer_authorization_appeals`，主要参考 `E007` 的 peer-to-peer 升级流程，并与 `E005` 的端到端预授权流程相关。任务分配依据是 `scratch/task_builder_assignments.md` 中的 `test_004: PET MPI P2P Overturn`。

共享环境是 Northstar Health Plan 的 SQLite 支撑付款方运营服务，设计见 `scratch/env_blueprint.md` 和 `task_group/task_group_014/env/manifest.json`，使用固定种子 `140417` 生成。目标业务记录为 `P2P-TE-004`。本任务本地可见文件为 `input/prompt.txt`、`input/payloads/task_context.json` 和 `input/payloads/answer_template.json`。

### 任务定义和场景契合

求解者扮演 peer-to-peer 协调员，在心脏 PET 心肌灌注显像 P2P 已完成后关闭授权文件。可见请求给出案例 ID、角色、报告日期、环境访问方式和 JSON 输出格式。预期工作是查看目标案例、申请服务行、PET MPI 政策、当前临床证据、已完成的 P2P 事件和授权记录，然后返回最终关闭摘要。

该任务契合 P2P 和申诉流程族，检验后期利用管理中的状态重建：P2P 结果必须与政策标准、新临床信息、最终授权状态、信函类型，以及是否仍存在不利决定申诉期限进行核对。

### 材料地图

`cases` 表标识 `P2P-TE-004`、政策 `POL-PET-MPI-2026`、阶段 `medical_director`、状态 `p2p_complete`、请求日期 `2026-06-07` 和截止日期 `2026-06-12`。`request_lines` 表给出 CPT `78431`、一个请求单位、服务日期 `2026-06-18` 和诊断代码。`policies` 与 `policy_criteria` 定义 PET MPI 要求，包括受保的心脏适应证和至少一个 PET-over-SPECT 因素。`documents` 表包含当前补充文档 `DOC-TE-004-P2P`。`document_facts` 记录已知冠心病伴心绞痛、既往 SPECT 结果不明确，以及 BMI 42。`p2p_events` 表记录 `P2P-TE-004-E1`、通话中提供的新信息、结果 `overturn_to_approval` 和最终状态 `approved`。`authorizations` 表记录 `NPA-2406199`，批准 CPT `78431`，批准一个单位，日期范围为 `2026-06-18` 至 `2026-06-18`。

### 解答和评估依据

标准答案设置 `case_id` 为 `P2P-TE-004`，`p2p_id` 为 `P2P-TE-004-E1`，请求 CPT 为 `78431`，P2P 结果为 `overturn_to_approval`，最终状态为 `approved`，标准结果为 `PET-IND=met` 和 `PET-FACTOR=met`，已解决标准为 `PET-FACTOR`，`new_information_changed_review=true`，支持 PET 的因素为 `prior_equivocal_spect` 和 `bmi_limitation`，授权为 `NPA-2406199`、一个单位、日期 `2026-06-18`，信函类型为 `approval`，替代方式为 `none`，且无内部申诉期限。

评估器使用六个整点评分目标，原始权重为 `[1, 3, 2, 2, 2, 1]`：身份和请求 CPT；推翻结果与批准状态；最终标准结果映射；新信息标志、已解决标准和支持 PET 的因素；授权号、单位、日期和 CPT；批准信函且无拒绝路径。这些目标覆盖身份和服务提取、P2P 判定、标准应用、来源变化解释、授权签发和申诉路径处理。每个评分点均为全得或零分，评估器在轻量标准化后进行精确枚举、列表、日期、整数和对象检查。

常见错误包括照搬 `train_004` 的维持拒绝模式而忽略新的患者特异证据，漏报 `PET-FACTOR` 为已解决标准，只看到 BMI 而遗漏既往 SPECT 不明确因素，在批准结果中仍保留拒绝信或内部申诉期限，或未把授权记录与被推翻的 P2P 结果关联起来。

### 迁移设计

主要训练锚点是 `train_004`，其标准答案显示 PET MPI P2P 的关键在于通话是否提供新的患者特异证据，从而补足 PET-over-SPECT 标准缺口。本测试依赖迁移的评分点包括推翻结果和批准状态、`PET-FACTOR=met` 的标准映射、新信息标志和支持因素，以及批准信函且无不利申诉路径。任务特有难度仍在于定位不同测试案例、读取其补充事实、将这些事实连接到政策标准，并提取授权值。

次要迁移来自 `train_001`，它强化当前证据来源选择；也来自 `train_003`，它强化匹配最终授权记录，而不是依赖过期或泛化状态摘要。可见提示没有重述隐藏 SOP，只提出真实的 P2P 关闭工作产品，让求解者从共享环境和训练锚点中推断来源优先级和 P2P 判定规则。

### 构建记录

作者：Builder I。创建日期：2026-07-18。更新日期：2026-07-18。主要变更：创建 `test_tasks/004` 的提示、任务上下文、答案模板、标准答案、确定性评估器、eval 包装脚本和双语说明。未编辑 `task_group/task_group_014/test_tasks/004/` 之外的文件。

## 2026-07-19 Basis-Audit Update

English: The answer template and standard answer now use `basis_audit`, a business-grounded audit trail rather than an invented control-code layer. `source_precedence` records the source category, `precedence_record_order` records the ordered business source trail, `controlling_record_ids` records the environment records that directly control the result, and `exception_record_ids` records stale, missing, unsupported, unresolved, or route-priority records. For this task, `source_precedence` is `new_patient_specific_p2p_information`, `precedence_record_order` is `P2P-TE-004-E1`, `DOC-TE-004-P2P`, `PET-FACTOR`, `AUTH-TE-004`, controlling records are `DOC-TE-004-P2P`, `P2P-TE-004-E1`, `AUTH-TE-004`, and exception records are `PET-FACTOR`; the test evaluator scores source category, precedence order, controlling records, and exception records as separate basis-audit points.

中文：答案模板和标准答案现在使用 `basis_audit`，这是基于业务依据的审计轨迹，而不是人为 control-code 层。`source_precedence` 记录来源类别，`precedence_record_order` 记录按优先级排列的业务来源轨迹，`controlling_record_ids` 记录直接决定结果的环境记录，`exception_record_ids` 记录过期、缺失、不支持、未解决或路线优先级记录。本任务中，`source_precedence` 为 `new_patient_specific_p2p_information`，`precedence_record_order` 为 `P2P-TE-004-E1`, `DOC-TE-004-P2P`, `PET-FACTOR`, `AUTH-TE-004`，控制记录为 `DOC-TE-004-P2P`, `P2P-TE-004-E1`, `AUTH-TE-004`，例外记录为 `PET-FACTOR`；the test evaluator scores source category, precedence order, controlling records, and exception records as separate basis-audit points。
