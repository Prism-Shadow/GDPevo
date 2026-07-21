# train_002 Notes - Vraylar Coverage Appeal And Assistance Screen

## English

Data/source lineage: This task belongs to `SCN_014_healthcare_payer_authorization_appeals`, using source examples `E001` through `E007`, especially the drug coverage appeal and assistance workflow represented by `E002`. The shared generated environment is `task_group_014` with SQLite data in the Northstar payer operations service. The target business record is `APPEAL-TR-002` for `task_id = train_002`. The solver-visible task-local materials are `input/prompt.txt`, `input/payloads/task_context.json`, and `input/payloads/answer_template.json`.

Task definition: The solver acts as a pharmacy appeals coordinator preparing a structured appeal and manufacturer assistance intake disposition for `APPEAL-TR-002` as of `2026-05-08`. The expected answer is JSON with appeal identity, routing, deadline, prior medication evidence classification, criteria results, packet requirements, missing packet items, assistance program status, assistance missing fields, and the next action. Solvers should use the environment URL and the SQL/API records rather than any construction database files.

Scenario fit: This is a payer operations task in the appeal and coverage exception family. It requires reconciling a case record, appeal record, policy criteria, packet documents, drug trial evidence, and an assistance screen. It reflects the source scenario pattern where the payer appeal and the manufacturer assistance application are related but have separate gates and missing information.

Material map: `cases` identifies `APPEAL-TR-002` as a standard specialty drug coverage exception with policy `POL-DRUG-EXC-2026`. `appeals` provides `APL-TR-002`, `standard_internal`, `not_requested` expedited attestation, deadline `2026-06-07`, owner `appeals-rx`, and the required packet text. `documents` and `document_facts` show current denial notice, member authorization, and prescriber rationale documents. `drug_trials` separates documented `quetiapine` from undocumented or insufficient `lurasidone`. `case_criteria` and `policy_criteria` produce the `DRUG-AUTH`, `DRUG-DENIAL`, `DRUG-RATIONALE`, and `DRUG-FAILURES` results. `assistance_screen` names `Vraylar Connect`, commercial insurance, denial on file, missing household income proof, and a source status that maps to the normalized answer enum `eligible_missing_information`.

Solution and evaluation basis: The standard answer sets `case_id = APPEAL-TR-002`, `appeal_id = APL-TR-002`, `drug = Vraylar`, `appeal_path = standard_internal`, `expedited = false`, `appeal_deadline = 2026-06-07`, and `owner = appeals-rx`. It classifies documented failures as `["quetiapine"]` and insufficient failures as `["lurasidone"]`. Criteria are `DRUG-AUTH = met`, `DRUG-DENIAL = met`, `DRUG-RATIONALE = met`, and `DRUG-FAILURES = partial`. Required packet items are `denial_notice`, `member_authorization`, `prescriber_rationale`, `formulary_failure_evidence`, and `household_income_proof`. Missing packet items are `lurasidone_fill_record` and `household_income_proof`. Assistance is `Vraylar Connect`, `eligible_missing_information`, missing `household_income_proof`; the next action is `request_more_information`.

The evaluator has seven whole-point scoring goals with raw weights `[1, 2, 2, 2, 1, 2, 1]`: target appeal/drug/owner identity; appeal path, expedited flag, and deadline; documented versus insufficient drug-trial distinction; criteria result map; required packet set; missing packet plus assistance missing income proof; and next action plus assistance program/status. These points cover distinct business outcomes: case identity, appeal routing and timeliness, evidence sufficiency, policy criteria, packet assembly, assistance intake gap, and operational disposition. Each point is all-or-zero, with list fields normalized as sets where the business outcome is set membership.

Likely model pitfalls: confusing the assistance screen status `pending_missing_income_proof` with a final answer enum instead of normalizing it; treating the undocumented lurasidone mention as a documented failure; marking `DRUG-FAILURES` as fully met; omitting household income proof from required or missing packet items; inventing an expedited path; or collapsing the payer appeal and manufacturer assistance outcomes into one status.

Transfer design: As a train task, this solved example teaches by comparison that pharmacy appeal work requires preserving the separation between payer appeal eligibility and manufacturer assistance readiness, counting only documented prior therapy failures, mapping environment-specific source values into answer-template enums, and representing packet gaps as structured lists rather than narrative prose. It also anchors the convention that `appeals-rx` owns drug appeals and that an incomplete packet drives a request-more-information action.

Construction record: Built by task-builder Builder B on 2026-07-18. The task directory created is `task_group/task_group_014/train_tasks/002/`. Files added are the solver prompt, task context, answer template, standard answer, evaluator shell/Python scripts, and this hidden notes file. The standard answer was checked against the assignment facts and the generated environment records.

## Chinese

数据和来源脉络：本任务属于 `SCN_014_healthcare_payer_authorization_appeals`，来源示例为 `E001` 到 `E007`，其中最相关的是 `E002` 所代表的药品覆盖申诉和厂家援助流程。共享生成环境是 `task_group_014` 的 Northstar 付款方运营服务，内部使用 SQLite。目标业务记录为 `APPEAL-TR-002`，对应 `task_id = train_002`。解题者可见的本地材料包括 `input/prompt.txt`、`input/payloads/task_context.json` 和 `input/payloads/answer_template.json`。

任务定义：解题者扮演药房申诉协调员，在 `2026-05-08` 为 `APPEAL-TR-002` 准备结构化的覆盖申诉和厂家援助初筛处置。期望输出为 JSON，包含申诉身份、路径、截止日期、既往用药证据分类、标准结果、材料包要求、缺失材料、援助项目状态、援助缺失字段和下一步动作。解题者应使用环境 URL 及 SQL/API 记录，而不是查看构建用数据库文件。

场景适配：这是付款方运营中覆盖例外申诉流程的一部分。任务需要核对 case、appeal、政策标准、材料文档、药物试用证据和援助筛查记录。它体现了源场景中的关键关系：付款方申诉和厂家援助申请相关联，但二者的门槛和缺失信息需要分开判断。

材料映射：`cases` 表说明 `APPEAL-TR-002` 是标准优先级的 specialty drug 覆盖例外，政策为 `POL-DRUG-EXC-2026`。`appeals` 表给出 `APL-TR-002`、`standard_internal`、未请求加急、截止日 `2026-06-07`、负责人 `appeals-rx` 和所需材料说明。`documents` 与 `document_facts` 表明当前已有拒付通知、会员授权和处方医生理由。`drug_trials` 区分有文档支持的 `quetiapine` 与证据不足的 `lurasidone`。`case_criteria` 和 `policy_criteria` 生成 `DRUG-AUTH`、`DRUG-DENIAL`、`DRUG-RATIONALE`、`DRUG-FAILURES` 的结果。`assistance_screen` 给出 `Vraylar Connect`、商业保险、已有拒付、缺少 household income proof，并将来源状态归一化为答案枚举 `eligible_missing_information`。

答案和评估依据：标准答案中 `case_id = APPEAL-TR-002`，`appeal_id = APL-TR-002`，`drug = Vraylar`，`appeal_path = standard_internal`，`expedited = false`，`appeal_deadline = 2026-06-07`，`owner = appeals-rx`。有文档支持的失败用药是 `["quetiapine"]`，证据不足的是 `["lurasidone"]`。标准结果为 `DRUG-AUTH = met`、`DRUG-DENIAL = met`、`DRUG-RATIONALE = met`、`DRUG-FAILURES = partial`。所需材料为 `denial_notice`、`member_authorization`、`prescriber_rationale`、`formulary_failure_evidence`、`household_income_proof`。缺失材料为 `lurasidone_fill_record` 和 `household_income_proof`。援助项目为 `Vraylar Connect`，状态为 `eligible_missing_information`，缺失 `household_income_proof`；下一步为 `request_more_information`。

评估器包含七个整点评分目标，原始权重为 `[1, 2, 2, 2, 1, 2, 1]`：目标申诉、药品和负责人；申诉路径、是否加急和截止日期；有文档支持和证据不足的用药试用区分；标准结果映射；所需材料集合；缺失材料和援助收入证明缺口；下一步动作以及援助项目和状态。这些评分点覆盖不同业务结果：身份、路径和时效、证据充分性、政策标准、材料包、援助缺口和运营处置。每个评分点均为全有或全无；列表在业务上表示集合时按集合归一化评估。

常见错误：把来源中的 `pending_missing_income_proof` 直接当作最终答案枚举而不归一化；把没有 fill record 的 lurasidone 当作已充分记录的失败用药；把 `DRUG-FAILURES` 标成完全满足；漏掉 household income proof；错误设置加急路径；或把付款方申诉和厂家援助状态混为一谈。

迁移设计：作为训练任务，解完后对照标准答案可以推断出药品申诉流程的可迁移经验：付款方申诉资格与厂家援助准备状态必须分开保留，只计算有文档支持的既往用药失败，将环境中的来源状态映射到答案模板枚举，并用结构化列表表达材料缺口而不是散文描述。它也建立了 drug appeal 由 `appeals-rx` 负责、材料不完整时下一步为 request-more-information 的约定。

构建记录：由 task-builder Builder B 于 2026-07-18 创建。任务目录为 `task_group/task_group_014/train_tasks/002/`。新增文件包括 prompt、task context、answer template、standard answer、eval shell/Python 脚本和本隐藏 notes 文件。标准答案已与分配说明及生成环境记录核对。

## 2026-07-19 Basis-Audit Update

English: The answer template and standard answer now use `basis_audit`, a business-grounded audit trail rather than an invented control-code layer. `source_precedence` records the source category, `precedence_record_order` records the ordered business source trail, `controlling_record_ids` records the environment records that directly control the result, and `exception_record_ids` records stale, missing, unsupported, unresolved, or route-priority records. For this task, `source_precedence` is `payer_appeal_before_manufacturer_assistance`, `precedence_record_order` is `APL-TR-002`, `TRIAL-TR-002-1`, `TRIAL-TR-002-2`, `household_income_proof`, controlling records are `APL-TR-002`, `TRIAL-TR-002-1`, and exception records are `TRIAL-TR-002-2`, `household_income_proof`; the train evaluator scores this combined basis trail at low weight.

中文：答案模板和标准答案现在使用 `basis_audit`，这是基于业务依据的审计轨迹，而不是人为 control-code 层。`source_precedence` 记录来源类别，`precedence_record_order` 记录按优先级排列的业务来源轨迹，`controlling_record_ids` 记录直接决定结果的环境记录，`exception_record_ids` 记录过期、缺失、不支持、未解决或路线优先级记录。本任务中，`source_precedence` 为 `payer_appeal_before_manufacturer_assistance`，`precedence_record_order` 为 `APL-TR-002`, `TRIAL-TR-002-1`, `TRIAL-TR-002-2`, `household_income_proof`，控制记录为 `APL-TR-002`, `TRIAL-TR-002-1`，例外记录为 `TRIAL-TR-002-2`, `household_income_proof`；the train evaluator scores this combined basis trail at low weight。
