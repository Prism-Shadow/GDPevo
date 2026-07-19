# test_001 Notes: Pediatric Speech Therapy Pend

## English

Data/source lineage: This test task belongs to `SCN_014_healthcare_payer_authorization_appeals`, with source-example influence from `E005` end-to-end prior authorization, `E006` payer nurse review, and the source-selection patterns summarized in `scratch/task_group_design.md`. The shared environment is `task_group/task_group_014/env/`, generated with seed `140417` and exposed through the SQLite-backed Northstar Health Plan service. The target environment record is `CASE-TE-001`. Task-local visible files are `input/prompt.txt`, `input/payloads/task_context.json`, and `input/payloads/answer_template.json`.

Task definition: The solver acts as a UM nurse reviewer and must return a structured disposition for pediatric speech therapy prior authorization case `CASE-TE-001`. Visible inputs identify the target case, role, reporting date, environment URL placeholder, SQL endpoint, and required output shape. The expected work is to inspect the case, request line, applicable policy, criteria rows, authorization state, documents, and document facts, then return a normalized JSON result.

Scenario fit: The task is in the clinical UM review family. It tests payer nurse review behavior, current-record source precedence, policy-criteria application, and routing when documentation is incomplete or internally conflicting. The object flow is case -> member/plan/provider -> request line -> policy criteria -> case criteria -> documents/facts -> authorization status.

Material map: `cases` identifies `CASE-TE-001`, request date `2026-06-04`, due date `2026-06-09`, stage `nurse_review`, status `needs_information`, and policy `POL-ST-PEDS-2026`. `request_lines` provides CPT `92507`, modifier `GN`, and `16` requested units. `policies` and `policy_criteria` define the pediatric speech therapy policy and its criteria. `case_criteria` contains `ST-POC` and `ST-CONFLICT`, both `not_met`, with nurse scope and pend-oriented gaps. `documents` distinguishes current documents `DOC-TE-001-NOTE` and `DOC-TE-001-POC` from stale document `DOC-TE-001-STALE`. `document_facts` records the current note frequency of 3 visits weekly, the plan-of-care frequency as 1-2 ambiguous, and duration as not stated. `authorizations` records zero approved units and status `pended`.

Solution/evaluation basis: The standard answer sets `case_id` to `CASE-TE-001`, recommendation `pend_for_information`, final status `pended`, route `request_more_information`, requested CPT `92507`, modifier `GN`, requested units `16`, approved units `0`, criteria results `ST-POC=not_met` and `ST-CONFLICT=not_met`, missing information codes `clarified_frequency`, `duration_weeks`, and `reconcile_note_plan_conflict`, evidence documents `DOC-TE-001-NOTE` and `DOC-TE-001-POC`, excluded document `DOC-TE-001-STALE`, and due date `2026-06-09`.

Rubric: The evaluator has six whole-point scoring goals with raw weights `[1, 3, 2, 2, 2, 1]`: target case and requested speech service; pend disposition and route; criteria result map; missing-information set; current evidence and stale exclusion; approved units and due date. These span service identification, UM routing, criteria adjudication, information-request content, source selection, and authorization timing/quantity. Each point is all-or-zero with exact enums, exact sets, ordered document lists, integer units, and date equality.

Transfer design: The main train anchor is `train_001`, where a nurse can approve only when all applicable criteria are met and current evidence must be used over stale or irrelevant records. `train_001` also anchors CPT/modifier/unit extraction and current evidence selection. Transfer-dependent scoring points here are the pend disposition and route, the criteria result map, the missing-information set, and the current evidence/stale exclusion check. Task-specific exploration remains necessary because the policy is pediatric speech therapy, the evidence conflict is between a current note and plan of care, and the target document IDs and due date are unique to this test case.

Likely model pitfalls: A solver may approve the requested units because the CPT and diagnosis are present, may rely on the stale export showing once-weekly therapy, may miss that the current note conflicts with the plan of care, may report only one missing item instead of frequency, duration, and reconciliation, or may escalate to MD rather than pend for information when both gaps are information completeness issues in nurse scope.

Construction record: Builder F created this task on 2026-07-18. Files created under `task_group/task_group_014/test_tasks/001/` include the solver prompt, task context, answer template, hidden notes, standard answer, evaluator, and eval shell wrapper. No other task directories or environment files were edited.

## Chinese

数据和来源：本测试任务属于 `SCN_014_healthcare_payer_authorization_appeals`，设计参考了 `E005` 的端到端授权流程、`E006` 的付款方护士审核流程，以及 `scratch/task_group_design.md` 中总结的证据来源优先级模式。共享环境位于 `task_group/task_group_014/env/`，由固定种子 `140417` 生成，并通过 Northstar Health Plan 的 SQLite 后端服务提供访问。目标业务记录是 `CASE-TE-001`。任务本地可见文件包括 `input/prompt.txt`、`input/payloads/task_context.json` 和 `input/payloads/answer_template.json`。

任务定义：求解者扮演 UM 护士审核员，需要为儿科言语治疗预授权案例 `CASE-TE-001` 返回结构化处置。可见输入给出目标案例、角色、报告日期、环境 URL 占位符、SQL 端点和输出格式。预期工作是查看案例、服务行、适用政策、审核标准、授权状态、文档和文档事实，然后生成标准化 JSON 结果。

场景契合：该任务属于临床 UM 审核族，检验付款方护士审核、当前记录优先、政策标准应用，以及在资料缺失或相互冲突时的流转决定。对象链路是案例 -> 会员/计划/服务方 -> 请求服务行 -> 政策标准 -> 案例标准 -> 文档/事实 -> 授权状态。

材料映射：`cases` 表给出 `CASE-TE-001`、请求日期 `2026-06-04`、截止日期 `2026-06-09`、阶段 `nurse_review`、状态 `needs_information` 和政策 `POL-ST-PEDS-2026`。`request_lines` 表给出 CPT `92507`、修饰符 `GN` 和 `16` 个请求单位。`policies` 和 `policy_criteria` 表定义儿科言语治疗政策及标准。`case_criteria` 表包含 `ST-POC` 和 `ST-CONFLICT`，二者均为 `not_met`，且属于护士审核范围并指向补充资料。`documents` 表区分当前文档 `DOC-TE-001-NOTE`、`DOC-TE-001-POC` 和过期文档 `DOC-TE-001-STALE`。`document_facts` 表记录当前病程记录每周 3 次，治疗计划每周 1-2 次且含糊，疗程周数未说明。`authorizations` 表记录批准单位为 0，状态为 `pended`。

解答和评估依据：标准答案为 `case_id=CASE-TE-001`，建议 `pend_for_information`，最终状态 `pended`，流转 `request_more_information`，请求 CPT `92507`，修饰符 `GN`，请求单位 `16`，批准单位 `0`，标准结果 `ST-POC=not_met` 和 `ST-CONFLICT=not_met`，缺失资料代码 `clarified_frequency`、`duration_weeks`、`reconcile_note_plan_conflict`，证据文档 `DOC-TE-001-NOTE` 和 `DOC-TE-001-POC`，排除文档 `DOC-TE-001-STALE`，截止日期 `2026-06-09`。

评分设计：评估器包含六个整点评分目标，原始权重为 `[1, 3, 2, 2, 2, 1]`：目标案例和请求言语治疗服务、待补充资料的处置和流转、标准结果映射、缺失资料集合、当前证据和过期文档排除、批准单位和截止日期。这些目标覆盖服务识别、UM 流转、标准判断、补件内容、证据来源选择、授权数量和时限。每个评分点均为全得或零分，使用精确枚举、精确集合、有序文档列表、整数单位和日期相等检查。

迁移设计：主要训练锚点是 `train_001`，其中可推断出护士只有在所有适用标准均满足时才能批准，并且当前证据优先于过期或无关记录。`train_001` 还锚定 CPT/修饰符/单位提取和当前证据选择。本测试中依赖迁移的高价值评分点包括待补充资料的处置和流转、标准结果映射、缺失资料集合，以及当前证据和过期文档排除。任务特有探索仍然必要，因为本案政策是儿科言语治疗，证据冲突发生在当前病程记录和治疗计划之间，且文档 ID 与截止日期均为本测试案例独有。

常见错误：模型可能因为 CPT 和诊断存在而直接批准单位，可能依赖显示每周一次治疗的过期导出，可能忽略当前病程记录与治疗计划之间的频率冲突，可能只列出一个缺失项而不是频率、疗程周数和冲突调和三项，或者在两个缺口都属于护士范围内资料完整性问题时错误转给医师审核。

构建记录：Builder F 于 2026-07-18 创建本任务。创建的文件均位于 `task_group/task_group_014/test_tasks/001/`，包括求解者提示、任务上下文、答案模板、隐藏说明、标准答案、评估器和 eval shell 包装脚本。未编辑其他任务目录或环境文件。

## 2026-07-19 Basis-Audit Update

English: The answer template and standard answer now use `basis_audit`, a business-grounded audit trail rather than an invented control-code layer. `source_precedence` records the source category, `precedence_record_order` records the ordered business source trail, `controlling_record_ids` records the environment records that directly control the result, and `exception_record_ids` records stale, missing, unsupported, unresolved, or route-priority records. For this task, `source_precedence` is `current_clinical_records_over_stale_export`, `precedence_record_order` is `DOC-TE-001-NOTE`, `DOC-TE-001-POC`, `DOC-TE-001-STALE`, controlling records are `DOC-TE-001-NOTE`, `DOC-TE-001-POC`, and exception records are `ST-POC`, `ST-CONFLICT`, `DOC-TE-001-STALE`; the test evaluator scores source category, precedence order, controlling records, and exception records as separate basis-audit points.

中文：答案模板和标准答案现在使用 `basis_audit`，这是基于业务依据的审计轨迹，而不是人为 control-code 层。`source_precedence` 记录来源类别，`precedence_record_order` 记录按优先级排列的业务来源轨迹，`controlling_record_ids` 记录直接决定结果的环境记录，`exception_record_ids` 记录过期、缺失、不支持、未解决或路线优先级记录。本任务中，`source_precedence` 为 `current_clinical_records_over_stale_export`，`precedence_record_order` 为 `DOC-TE-001-NOTE`, `DOC-TE-001-POC`, `DOC-TE-001-STALE`，控制记录为 `DOC-TE-001-NOTE`, `DOC-TE-001-POC`，例外记录为 `ST-POC`, `ST-CONFLICT`, `DOC-TE-001-STALE`；the test evaluator scores source category, precedence order, controlling records, and exception records as separate basis-audit points。
