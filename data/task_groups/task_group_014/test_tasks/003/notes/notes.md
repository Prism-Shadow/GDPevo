# test_003 Notes - Knee Arthroscopy Claim Correction

## English

### Data/source lineage

This task belongs to `task_group_014`, derived from scenario `SCN_014_healthcare_payer_authorization_appeals` and source examples `E001` through `E007`. The closest source anchors are `E003` for reimbursement benchmark selection and `E004` for payer-service payment analytics. The specific assignment is `test_003: Knee Arthroscopy Claim Correction` for Builder H. The shared environment is the generated Northstar Health Plan SQLite-backed service documented in `scratch/env_blueprint.md` and `task_group/task_group_014/env/manifest.json`, generated with seed `140417`.

The target business record is `CLAIM-TE-003`. Construction validation used the shared generated data in `cases`, `members`, `plans`, `providers`, `claims`, `claim_lines`, `documents`, `document_facts`, `policies`, `policy_criteria`, and `payment_benchmarks`. Solver-visible task-local payloads are `input/payloads/task_context.json` and `input/payloads/answer_template.json`; they identify the target claim/case, requester role, reporting date, environment access shape, and required output schema without exposing the final amounts or decisions.

### Task definition and scenario fit

The solver acts as a payment integrity analyst handling an outpatient knee arthroscopy claim in the June 10, 2026 reporting queue. The solver must use the shared service endpoints, usually `POST /sql/query`, to inspect the target claim, member plan type, authorization number, service-date benchmark rows, claim lines, and support documents. The requested work product is a structured correction packet with claim identity, plan context, benchmark source/version, aggregate totals, line-level correction or denial decisions, route, and priority.

This fits the Northstar payer operations scenario because it combines claim payment review, authorization-effective context, payer plan-type matching, effective-dated fee schedule selection, CPT/modifier matching, and payment integrity routing. It is a test analogue to the cardiac SPECT claim repricing train task, but changes the service family to outpatient surgery and adds a modifier-denial line that offsets the upward correction.

### Material map

- `input/prompt.txt`: visible business request, environment access instructions, and JSON output requirement.
- `input/payloads/task_context.json`: target claim/case ID `CLAIM-TE-003`, payment integrity role, reporting date, service domain, and a short queue memo.
- `input/payloads/answer_template.json`: required output keys, currency precision, enum choices, line ordering, and modifier null convention.
- `claims`: target claim has auth number `NPA-2406121`, paid total `2010.00`, paid-review status, and payer `Northstar Health Plan`.
- `members` and `plans`: target member `M-TE-003` is active on the `workers_comp` plan type, which drives the benchmark match.
- `cases`: target case `CLAIM-TE-003` is in payment integrity with service domain `outpatient_surgery`.
- `claim_lines`: line 1 is CPT `29881` with modifier `RT`; line 2 is CPT `29881` with modifier `59`.
- `payment_benchmarks`: the current matching source is `Northstar WC Surgery Schedule` version `2026`; rows for the same CPT include a `RT` allowed amount and a zero-allowed `59` modifier row. Distractor rows with other plan types and source names exist.
- `documents` and `document_facts`: current remittance document `DOC-TE-003-EOB` records paid total and schedule-review evidence; corrected allowed amounts and recovery are derived from current benchmark rows.
- `output/answer.json`: hidden standard answer.
- `eval/evaluator.py` and `eval/eval.sh`: deterministic six-point whole-score evaluator.

### Solution and evaluation basis

The correct identity is claim ID `CLAIM-TE-003`, case ID `CLAIM-TE-003`, and auth number `NPA-2406121`. The member plan type is `workers_comp`. The applicable benchmark is `Northstar WC Surgery Schedule`, version `2026`, matched by payer, plan type, service domain, CPT, modifier, and service date.

Totals: paid total is `2010.00`, corrected allowed total is `2420.00`, and net recovery is `410.00`.

Line-level basis:

- `CL-TE-003-1`: CPT `29881`, modifier `RT`, units `1`, paid `1660.00`, corrected allowed amount `2420.00`, recovery `760.00`, disposition `correct_upward`.
- `CL-TE-003-2`: CPT `29881`, modifier `59`, units `1`, paid `350.00`, corrected allowed amount `0.00`, recovery `-350.00`, disposition `deny_unsupported_modifier`.

The resubmission route is `payment_integrity_correction` and priority is `standard`.

The evaluator has six whole-point scoring goals with raw weights totaling 11:

1. Correct claim, case, and authorization identity, weight 1.
2. Correct benchmark source/version and workers-comp plan context, weight 2.
3. Correct paid total, corrected allowed total, and net recovery, weight 3.
4. Correct line 1 upward correction amount and disposition, weight 2.
5. Correct line 2 unsupported-modifier denial and negative recovery, weight 2.
6. Correct resubmission route and priority, weight 1.

Each scoring point is all-or-zero. Currency values are normalized to cents, IDs are compared case-insensitively, enum-like values tolerate spaces and hyphens by normalizing to underscores, and null-like modifier strings are accepted for absent modifiers. Likely pitfalls include using a commercial or distractor schedule instead of the workers-comp schedule, ignoring modifier matching, treating the `59` line as separately payable, computing gross upward correction `760.00` instead of net recovery `410.00`, failing to preserve the negative line-level recovery, or using an expedited route for a routine payment correction.

### Transfer design

This test task is anchored by `train_003` and `train_005`. From `train_003`, solvers should transfer the habit of matching current benchmark rows by payer, plan type, service domain, CPT, modifier, effective dates, and line units before aggregating totals. From `train_005`, solvers should transfer workers-comp and charge-sensitive payer-segment awareness, plus the need to separate payment-correction routing from general monitoring.

Transfer-dependent scoring points are the benchmark/workers-comp point, the aggregate totals point, both line disposition points, and the route/priority point. These require more than reading the prompt: the solver must reconstruct the current payment context from environment tables and apply the trained source-selection and line-level correction conventions. Task-specific difficulty comes from the knee arthroscopy service family, the modifier `59` zero-allowed row, the offsetting negative recovery, and distractor benchmark rows.

### Construction record

Author: Builder H. Created: 2026-07-18. Updated: 2026-07-18. Major changes: created the complete `test_tasks/003` package, verified target environment rows, wrote the standard answer from the assignment and generated data, and implemented a six-point deterministic evaluator that scores the standard answer at 1.0.

## 中文

### 数据来源与血缘

本任务属于 `task_group_014`，来源场景为 `SCN_014_healthcare_payer_authorization_appeals`，来源示例为 `E001` 至 `E007`。最接近的来源锚点是 `E003` 的报销基准选择，以及 `E004` 的付款方服务线支付分析。本任务的具体分配为 Builder H 的 `test_003: Knee Arthroscopy Claim Correction`。共享环境是 Northstar Health Plan 的 SQLite 后端服务，见 `scratch/env_blueprint.md` 和 `task_group/task_group_014/env/manifest.json`，数据种子为 `140417`。

目标业务记录为 `CLAIM-TE-003`。构建核对时使用了共享生成数据中的 `cases`、`members`、`plans`、`providers`、`claims`、`claim_lines`、`documents`、`document_facts`、`policies`、`policy_criteria` 和 `payment_benchmarks` 表。解题者可见的任务本地负载是 `input/payloads/task_context.json` 和 `input/payloads/answer_template.json`；它们给出目标索赔/案件、请求者角色、报告日期、环境访问方式和输出结构，但不暴露最终金额或决策。

### 任务定义与场景适配

解题者扮演支付完整性分析师，处理 2026-06-10 报告队列中的一笔门诊膝关节镜索赔。解题者需要使用共享服务端点，通常是 `POST /sql/query`，查看目标索赔、会员计划类型、授权号、服务日期对应的基准费率行、索赔行和支持文件。预期工作产物是结构化纠错包，包含索赔身份、计划上下文、基准来源和版本、汇总金额、行级纠错或拒付决策、路由和优先级。

该任务符合 Northstar 付款方运营场景，因为它结合了索赔支付复核、授权有效状态、付款方计划类型匹配、有效期内费率表选择、CPT/修饰符匹配和支付完整性路由。它是心脏 SPECT 索赔重定价训练任务的测试对应任务，但服务线换成门诊手术，并增加了一条修饰符拒付行，该行会抵消向上纠错金额的一部分。

### 材料地图

- `input/prompt.txt`：可见业务请求、环境访问说明和 JSON 输出要求。
- `input/payloads/task_context.json`：目标索赔/案件 ID `CLAIM-TE-003`、支付完整性角色、报告日期、服务域和简短队列备忘。
- `input/payloads/answer_template.json`：必需输出字段、金额精度、枚举、行排序和修饰符空值约定。
- `claims`：目标索赔包含授权号 `NPA-2406121`、已付总额 `2010.00`、paid-review 状态和付款方 `Northstar Health Plan`。
- `members` 与 `plans`：目标会员 `M-TE-003` 为有效的 `workers_comp` 计划类型，这是基准匹配的关键。
- `cases`：目标案件 `CLAIM-TE-003` 处于支付完整性阶段，服务域为 `outpatient_surgery`。
- `claim_lines`：第 1 行为 CPT `29881`、修饰符 `RT`；第 2 行为 CPT `29881`、修饰符 `59`。
- `payment_benchmarks`：当前匹配来源为 `Northstar WC Surgery Schedule` 版本 `2026`；同一 CPT 下有 `RT` 的允许金额行和允许金额为零的 `59` 修饰符行。环境还包含其他计划类型和来源名称的干扰基准。
- `documents` 与 `document_facts`：当前付款说明文件 `DOC-TE-003-EOB` 记录已付总额和费率表复核证据；正确允许金额和追回金额需要从当前基准行推导。
- `output/answer.json`：隐藏标准答案。
- `eval/evaluator.py` 与 `eval/eval.sh`：确定性的六点评估器。

### 解法与评估依据

正确身份为 claim ID `CLAIM-TE-003`、case ID `CLAIM-TE-003` 和授权号 `NPA-2406121`。会员计划类型为 `workers_comp`。适用基准是 `Northstar WC Surgery Schedule`，版本 `2026`，需要按付款方、计划类型、服务域、CPT、修饰符和服务日期匹配。

汇总金额：已付总额为 `2010.00`，正确允许总额为 `2420.00`，净追回金额为 `410.00`。

行级依据如下：

- `CL-TE-003-1`：CPT `29881`，修饰符 `RT`，单位 `1`，已付 `1660.00`，纠正允许金额 `2420.00`，追回 `760.00`，处置为 `correct_upward`。
- `CL-TE-003-2`：CPT `29881`，修饰符 `59`，单位 `1`，已付 `350.00`，纠正允许金额 `0.00`，追回 `-350.00`，处置为 `deny_unsupported_modifier`。

提交路由为 `payment_integrity_correction`，优先级为 `standard`。

评估器包含六个整点评分目标，原始权重总计 11：

1. 索赔、案件和授权身份正确，权重 1。
2. 基准来源/版本和工伤赔付计划上下文正确，权重 2。
3. 已付总额、纠正允许总额和净追回金额正确，权重 3。
4. 第 1 行向上纠错金额和处置正确，权重 2。
5. 第 2 行不支持修饰符的拒付和负追回金额正确，权重 2。
6. 提交路由和优先级正确，权重 1。

每个评分点都是全得或零分。金额按美分归一化，ID 比较忽略大小写，枚举类值允许通过空格和连字符归一为下划线，空修饰符也会按空值处理。常见错误包括使用商业或干扰费率表而非工伤赔付费率表、忽略修饰符匹配、把 `59` 行当作可单独支付、只计算 `760.00` 的总向上纠错而不是 `410.00` 的净追回、不保留行级负追回金额，或把常规支付纠错错误设为加急路由。

### 迁移设计

本测试任务由 `train_003` 和 `train_005` 锚定。从 `train_003`，解题者应迁移按付款方、计划类型、服务域、CPT、修饰符、有效日期和行单位匹配当前基准，再进行汇总的习惯。从 `train_005`，解题者应迁移对工伤赔付和收费敏感付款方分段的认识，以及区分支付纠错路由和一般监控的习惯。

依赖迁移的评分点包括基准/工伤赔付上下文、汇总金额、两条行级处置以及路由/优先级。这些不能仅通过读取提示完成；解题者必须从环境表中重建当前支付上下文，并应用训练任务中可推断的来源选择和行级纠错约定。任务特有难点来自膝关节镜服务线、`59` 修饰符的零允许金额行、抵消性的负追回金额以及基准干扰行。

### 构建记录

作者：Builder H。创建日期：2026-07-18。更新日期：2026-07-18。主要变更：创建完整的 `test_tasks/003` 包，核对目标环境记录，依据分配说明和生成数据写入标准答案，并实现六个确定性整点评分项的评估器；标准答案应得 1.0。

## 2026-07-19 Basis-Audit Update

English: The answer template and standard answer now use `basis_audit`, a business-grounded audit trail rather than an invented control-code layer. `source_precedence` records the source category, `precedence_record_order` records the ordered business source trail, `controlling_record_ids` records the environment records that directly control the result, and `exception_record_ids` records stale, missing, unsupported, unresolved, or route-priority records. For this task, `source_precedence` is `effective_benchmark_by_plan_modifier_and_date`, `precedence_record_order` is `BM-TE-003-29881RT`, `BM-TE-003-2988159`, `CL-TE-003-2`, controlling records are `CL-TE-003-1`, `CL-TE-003-2`, `BM-TE-003-29881RT`, `BM-TE-003-2988159`, and exception records are `CL-TE-003-2`; the test evaluator scores source category, precedence order, controlling records, and exception records as separate basis-audit points.

中文：答案模板和标准答案现在使用 `basis_audit`，这是基于业务依据的审计轨迹，而不是人为 control-code 层。`source_precedence` 记录来源类别，`precedence_record_order` 记录按优先级排列的业务来源轨迹，`controlling_record_ids` 记录直接决定结果的环境记录，`exception_record_ids` 记录过期、缺失、不支持、未解决或路线优先级记录。本任务中，`source_precedence` 为 `effective_benchmark_by_plan_modifier_and_date`，`precedence_record_order` 为 `BM-TE-003-29881RT`, `BM-TE-003-2988159`, `CL-TE-003-2`，控制记录为 `CL-TE-003-1`, `CL-TE-003-2`, `BM-TE-003-29881RT`, `BM-TE-003-2988159`，例外记录为 `CL-TE-003-2`；the test evaluator scores source category, precedence order, controlling records, and exception records as separate basis-audit points。
