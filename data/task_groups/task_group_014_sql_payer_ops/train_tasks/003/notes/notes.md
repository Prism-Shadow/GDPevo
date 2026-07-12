# Train 003 Notes: Medication Appeal And Assistance Routing

## English

Builder: `builder_train_003`

Task goal: teach solvers to query the SQLite SQL service for medication appeal worklists, combine drug policy requirements with trial evidence, and keep payer appeal routing separate from manufacturer assistance routing.

Data lineage:
- Target bucket: `train_drug_batch`
- Target medication cases: `MED00001`, `MED00002`, `MED00003`, `MED00004`
- Primary tables used: `medication_cases`, `members`, `plans`, `appeals`, `medication_trials`, `drug_policy_requirements`, `assistance_programs`, `household_financials`
- Construction source: shared generated SQLite database in the task group environment.

Solution basis:
- `MED00001` has Remicade diagnosis and biosimilar step evidence, but no explicit TB screening evidence; assistance is blocked by income above the program limit.
- `MED00002` has Dupixent diagnosis but no topical steroid failure; assistance is blocked by government insurance, lack of commercial insurance, income, missing denial letter, and missing consent.
- `MED00003` has Eliquis diagnosis evidence and is appeal ready with expedited classification; assistance is blocked by government insurance and lack of commercial insurance.
- `MED00004` has Ozempic diagnosis but no metformin step therapy; assistance is not permanently blocked but needs denial letter and consent, so it routes to the manufacturer assistance team while the payer appeal evidence is collected.

Scoring design:
- Eight exact-match scoring points with raw weights 3, 2, 2, 2, 1, 2, 1, and 1.
- The evaluator compares structured business results rather than SQL text.
- Lists of scalar values are normalized for order, while medication cases are matched by stable case ID.

Transfer design:
- This train task prepares solvers for specialty medication appeal dockets by practicing plan-type source selection, policy gate evaluation, expedited appeal handling, assistance exclusions, and appeal-versus-assistance separation.

Construction record:
- Created under the assigned write scope only: `train_tasks/003/**`.
- Non-note files are English only.
- Solver-visible prompt uses `<TASK_ENV_BASE_URL>`, discloses the fixed synthetic Basic Auth credentials, and does not hard-code a runtime host or port.

## Chinese

构建者：`builder_train_003`

任务目标：训练解题者通过 SQLite SQL 服务查询药品申诉工作清单，把药品政策要求与既往用药证据结合起来，并且把付款方申诉路径和厂家援助路径分开处理。

数据来源：
- 目标批次：`train_drug_batch`
- 目标药品案例：`MED00001`、`MED00002`、`MED00003`、`MED00004`
- 主要数据表：`medication_cases`、`members`、`plans`、`appeals`、`medication_trials`、`drug_policy_requirements`、`assistance_programs`、`household_financials`
- 构建来源：任务组环境中共享生成的 SQLite 数据库。

标准答案依据：
- `MED00001` 有 Remicade 诊断和生物类似药阶梯治疗证据，但没有明确的结核筛查证据；厂家援助因收入超过项目上限而受阻。
- `MED00002` 有 Dupixent 诊断，但没有外用激素失败证据；厂家援助因政府保险、缺少商业保险、收入超限、缺少拒付信和缺少同意书而受阻。
- `MED00003` 有 Eliquis 诊断证据，申诉已就绪并符合加急分类；厂家援助因政府保险和缺少商业保险而受阻。
- `MED00004` 有 Ozempic 诊断，但没有二甲双胍阶梯治疗证据；厂家援助没有永久性阻断因素，但需要拒付信和同意书，因此厂家援助团队可跟进，同时继续补齐付款方申诉证据。

评分设计：
- 八个精确匹配评分点，原始权重为 3、2、2、2、1、2、1、1。
- 评估器比较结构化业务结果，而不是 SQL 文本。
- 标量列表会做顺序归一化，药品案例按稳定案例 ID 匹配。

迁移设计：
- 本训练任务帮助解题者准备 specialty medication 申诉任务，重点练习计划类型来源选择、政策门槛判断、加急申诉分类、厂家援助排除规则，以及申诉和援助路径分离。

构建记录：
- 只在指定写入范围 `train_tasks/003/**` 下创建文件。
- 非 notes 文件全部为英文。
- 面向解题者的 prompt 使用 `<TASK_ENV_BASE_URL>` 并公开固定合成 Basic Auth 凭据，但没有写入运行时主机或端口。
