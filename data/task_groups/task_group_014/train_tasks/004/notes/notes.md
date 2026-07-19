# train_004 Notes: PET MPI P2P Uphold

## English

### Data and Source Lineage

This task belongs to `task_group_014`, scenario `SCN_014_healthcare_payer_authorization_appeals`, with the strongest source-example alignment to `E007` peer-to-peer escalation and secondary alignment to `E005` end-to-end prior authorization. The task design brief is `train_004: PET MPI P2P Uphold` from `scratch/task_builder_assignments.md`.

The shared generated environment is the Northstar Health Plan SQLite-backed service described in `scratch/env_blueprint.md` and `task_group/task_group_014/env/manifest.json`. The target business record is `P2P-TR-004`. Task-local solver materials are `input/prompt.txt`, `input/payloads/task_context.json`, and `input/payloads/answer_template.json`.

### Task Definition and Scenario Fit

The solver acts as a peer-to-peer coordinator closing an authorization file after a completed PET myocardial perfusion imaging peer-to-peer discussion. The visible prompt provides the target case ID, environment access shape, and the required structured JSON output. The solver must retrieve the case, request line, policy, current clinical evidence, P2P event, and authorization record from the environment, then determine whether the P2P changed the intended adverse decision.

This fits the group because it tests late-stage utilization management coordination: policy criteria, evidence gaps, P2P notes, final authorization status, adverse-letter handling, and appeal deadline calculation must be reconciled as one audit trail. The key relationship is that the P2P can change the decision only when new patient-specific evidence closes the original PET-over-SPECT criterion gap.

### Material Map

`input/prompt.txt` is the business request. `input/payloads/task_context.json` identifies `P2P-TR-004`, the requester role, reporting date, and a small appeals memo without final answer values. `input/payloads/answer_template.json` defines the required fields, enum choices, date precision, list ordering, and expected object shape.

Environment records used for the solution include `cases` for current stage/status and policy ID, `request_lines` for CPT `78431`, `policies` and `policy_criteria` for PET MPI criteria, `documents` and `document_facts` for current clinical evidence, `case_criteria` for criterion results, `p2p_events` for the completed P2P and adverse outcome, and `authorizations` for final denial status. The P2P date `2026-05-13` drives the 180-day internal appeal deadline.

### Solution and Evaluation Basis

The standard answer records `case_id` `P2P-TR-004`, `p2p_id` `P2P-TR-004-E1`, requested CPT `78431`, P2P outcome `uphold_intended_adverse_decision`, final status `denied`, criteria results `PET-IND=met` and `PET-FACTOR=not_met`, unresolved criterion `PET-FACTOR`, `new_information_changed_review=false`, missing PET factors `prior_equivocal_spect`, `bmi_limitation`, and `attenuation_artifact`, letter type `denial`, recommended alternative `SPECT MPI`, and internal appeal deadline `2026-11-09`.

The evaluator uses six whole-point checks with raw weights 1, 3, 2, 2, 1, and 1. They cover: identity/requested CPT; P2P outcome and final status; criterion-result map; unresolved criterion, missing factors, and no-review-change flag; denial letter plus alternative modality; and the 180-day appeal deadline. Each scoring point is all-or-zero. Likely model pitfalls include treating provider preference as new evidence, missing the distinction between a covered CAD indication and a PET-over-SPECT factor, using the case due date rather than the adverse P2P date for the appeal deadline, or omitting one missing factor.

### Transfer Design

As a train task, this example lets a later skill infer that P2P resolution requires source reconciliation rather than narrative summarization. The reusable habits are: identify current case and policy records through the environment; apply criterion IDs as structured outputs; separate indication criteria from modality-specific factors; treat unsupported P2P preference as non-changing information; preserve final authorization status separately from P2P outcome; and calculate adverse-decision appeal windows from the adverse determination date. The solved example should transfer to PET P2P test work without making this prompt a tutorial.

### Construction Record

Author: Builder D. Created: 2026-07-18. Updated: 2026-07-18. Major changes: created the train task directory, solver inputs, hidden standard answer, deterministic evaluator, and bilingual construction notes for `P2P-TR-004`.

## 中文

### 数据和来源沿革

本任务属于 `task_group_014`，场景为 `SCN_014_healthcare_payer_authorization_appeals`，最直接对应来源示例 `E007` 的 peer-to-peer 升级流程，并与 `E005` 的端到端授权流程有次要关联。任务设计依据是 `scratch/task_builder_assignments.md` 中的 `train_004: PET MPI P2P Uphold`。

共享环境是 Northstar Health Plan 的 SQLite 支撑服务，其设计见 `scratch/env_blueprint.md` 和 `task_group/task_group_014/env/manifest.json`。目标业务记录为 `P2P-TR-004`。本任务本地材料包括 `input/prompt.txt`、`input/payloads/task_context.json` 和 `input/payloads/answer_template.json`。

### 任务定义和场景契合

解题者扮演 peer-to-peer 协调员，在 PET 心肌灌注显像的 P2P 已完成后关闭授权文件。可见提示给出目标 case ID、环境访问方式和结构化 JSON 输出要求。解题者需要从环境中查询病例、申请行、政策、当前临床证据、P2P 事件和授权记录，再判断 P2P 是否改变了原拟不利决定。

该任务契合本组的后期利用管理流程：政策标准、证据缺口、P2P 记录、最终授权状态、不利决定信函和申诉期限必须合并成一条审计轨迹。关键关系是：只有新的、患者特异性的证据能补足原来的 PET-over-SPECT 标准缺口时，P2P 才能改变决定。

### 材料地图

`input/prompt.txt` 是业务请求。`input/payloads/task_context.json` 标识 `P2P-TR-004`、请求角色、报告日期和简短申诉备忘录，但不包含最终答案值。`input/payloads/answer_template.json` 定义必需字段、枚举值、日期精度、列表顺序和对象结构。

用于求解的环境记录包括：`cases` 中的当前阶段、状态和政策 ID；`request_lines` 中的 CPT `78431`；`policies` 和 `policy_criteria` 中的 PET MPI 标准；`documents` 和 `document_facts` 中的当前临床证据；`case_criteria` 中的标准结果；`p2p_events` 中的已完成 P2P 和不利结果；以及 `authorizations` 中的最终拒绝状态。P2P 日期 `2026-05-13` 用于计算 180 天内部申诉期限。

### 解答和评估依据

标准答案记录 `case_id` 为 `P2P-TR-004`，`p2p_id` 为 `P2P-TR-004-E1`，申请 CPT 为 `78431`，P2P 结果为 `uphold_intended_adverse_decision`，最终状态为 `denied`，标准结果为 `PET-IND=met` 和 `PET-FACTOR=not_met`，未解决标准为 `PET-FACTOR`，`new_information_changed_review=false`，缺失的 PET 因素为 `prior_equivocal_spect`、`bmi_limitation` 和 `attenuation_artifact`，信函类型为 `denial`，推荐替代方式为 `SPECT MPI`，内部申诉期限为 `2026-11-09`。

评估器使用六个整点评分项，原始权重为 1、3、2、2、1、1。它们分别覆盖：身份和申请 CPT；P2P 结果及最终状态；标准结果映射；未解决标准、缺失因素和评审未改变标志；拒绝信和替代影像方式；以及 180 天申诉期限。每个评分项只有全得或零分。常见错误包括把医生偏好当作新证据、混淆 CAD 适应证和 PET-over-SPECT 因素、用 case 到期日而非不利 P2P 日期计算期限，或漏掉某个缺失因素。

### 迁移设计

作为训练任务，本例让后续技能推断 P2P 处理不是单纯叙述摘要，而是来源核对和结构化判定。可迁移习惯包括：通过环境定位当前 case 和政策记录；用标准 ID 输出结构化结果；区分适应证标准和影像方式特异因素；把没有新增患者特异证据的 P2P 偏好视为不改变评审；将最终授权状态与 P2P 结果分开；并从不利决定日期计算申诉窗口。该已解样例应帮助后续 PET P2P 测试任务，但可见提示本身不写成教程。

### 构建记录

作者：Builder D。创建日期：2026-07-18。更新日期：2026-07-18。主要变更：为 `P2P-TR-004` 创建训练任务目录、解题输入、隐藏标准答案、确定性评估器和双语构建说明。

## 2026-07-19 Basis-Audit Update

English: The answer template and standard answer now use `basis_audit`, a business-grounded audit trail rather than an invented control-code layer. `source_precedence` records the source category, `precedence_record_order` records the ordered business source trail, `controlling_record_ids` records the environment records that directly control the result, and `exception_record_ids` records stale, missing, unsupported, unresolved, or route-priority records. For this task, `source_precedence` is `new_patient_specific_p2p_information`, `precedence_record_order` is `P2P-TR-004-E1`, `DOC-TR-004-CARD`, `PET-FACTOR`, controlling records are `DOC-TR-004-CARD`, `P2P-TR-004-E1`, and exception records are `PET-FACTOR`, `prior_equivocal_spect`, `bmi_limitation`, `attenuation_artifact`; the train evaluator scores this combined basis trail at low weight.

中文：答案模板和标准答案现在使用 `basis_audit`，这是基于业务依据的审计轨迹，而不是人为 control-code 层。`source_precedence` 记录来源类别，`precedence_record_order` 记录按优先级排列的业务来源轨迹，`controlling_record_ids` 记录直接决定结果的环境记录，`exception_record_ids` 记录过期、缺失、不支持、未解决或路线优先级记录。本任务中，`source_precedence` 为 `new_patient_specific_p2p_information`，`precedence_record_order` 为 `P2P-TR-004-E1`, `DOC-TR-004-CARD`, `PET-FACTOR`，控制记录为 `DOC-TR-004-CARD`, `P2P-TR-004-E1`，例外记录为 `PET-FACTOR`, `prior_equivocal_spect`, `bmi_limitation`, `attenuation_artifact`；the train evaluator scores this combined basis trail at low weight。
