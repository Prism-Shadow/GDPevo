# train_003 Notes - Cardiac SPECT Claim Repricing

## English

### Data/source lineage

This task belongs to `task_group_014`, derived from `SCN_014_healthcare_payer_authorization_appeals`, especially the reimbursement and benchmark-selection workflows represented by source examples `E003` and `E004`. The task design is the `train_003: Cardiac SPECT Claim Repricing` assignment for Builder C. The shared environment is the Northstar Health Plan SQLite-backed service described by `scratch/env_blueprint.md` and `task_group/task_group_014/env/manifest.json`, generated with seed `140417`.

The target business record is `CLAIM-TR-003`. Construction checks used the shared generated database tables `cases`, `claims`, `claim_lines`, `documents`, `document_facts`, `policies`, `policy_criteria`, `case_criteria`, `payment_benchmarks`, `members`, and `plans`. The solver-visible local payloads are `input/payloads/task_context.json` and `input/payloads/answer_template.json`; they provide the target ID, role, reporting date, access shape, and output schema but not the final repricing results.

### Task definition and scenario fit

The business user is a payment integrity analyst who needs a correction packet for a cardiac SPECT claim after a provider payment concern. The solver must use the environment endpoints, especially `POST /sql/query` if desired, to inspect the claim, claim lines, case context, current payment benchmark, and stale benchmark distractor. The expected output is a structured JSON repricing packet with claim identity, benchmark source/version, stale source rejection, totals, line-level corrections, route, and priority.

This fits the payer operations scenario because it combines claim payment review, effective benchmark selection, CPT/modifier matching, per-unit allowed amount application, and operational correction routing. It also supports transfer to later claim/payment tasks: solvers should learn that current, effective benchmark schedules take precedence over stale exports, and that line correction amounts must match payer, plan type, service domain, CPT, modifier, and units.

### Material map

- `input/prompt.txt`: visible business request, environment access instructions, and final JSON requirement.
- `input/payloads/task_context.json`: target claim/case ID, role, reporting date, and a small intake memo.
- `input/payloads/answer_template.json`: required JSON keys, enum choices, currency precision, modifier null convention, and line ordering.
- `claims`: target row has claim ID `CLAIM-TR-003`, case ID `CLAIM-TR-003`, auth number `NPA-2404980`, paid total `940.00`, and claim status `paid_stale_schedule`.
- `claim_lines`: three target lines with CPT/modifier/units and paid amounts.
- `cases`, `policies`, `policy_criteria`, `case_criteria`: payment integrity context and the current-schedule criterion.
- `documents` and `document_facts`: remittance evidence for paid total and the legacy schedule marker; corrected allowed amounts and recovery are derived from `payment_benchmarks`.
- `payment_benchmarks`: current `Northstar Commercial Imaging Schedule` `2026Q2` rows and stale `Legacy Imaging Export` row.
- `output/answer.json`: hidden standard answer.
- `eval/evaluator.py` and `eval/eval.sh`: deterministic whole-point scoring.

### Solution and evaluation basis

The correct identity is claim ID `CLAIM-TR-003`, case ID `CLAIM-TR-003`, and auth number `NPA-2404980`. The current benchmark is `Northstar Commercial Imaging Schedule`, version `2026Q2`; `Legacy Imaging Export` is rejected as stale. The paid total is `940.00`, the correct allowed total is `1175.00`, and the recovery amount is `235.00`.

Line-level basis:

- `CL-TR-003-1`: CPT `78452`, modifier `TC`, units `1`, paid `608.00`, current allowed `760.00`, recovery `152.00`, disposition `correct_upward`.
- `CL-TR-003-2`: CPT `A9500`, modifier `null`, units `2`, paid `288.00`, current allowed `360.00`, recovery `72.00`, disposition `correct_upward`.
- `CL-TR-003-3`: CPT `93016`, modifier `null`, units `1`, paid `44.00`, current allowed `55.00`, recovery `11.00`, disposition `correct_upward`.

The operational route is `payment_integrity_correction` and priority is `standard`.

The evaluator has six whole-point scoring goals with raw weights totaling 11:

1. Correct claim, case, and authorization identity, weight 1.
2. Correct current benchmark source/version and stale source rejection, weight 2.
3. Correct paid total, correct allowed total, and recovery amount, weight 3.
4. Correct line-level CPT, modifier, units, and stable ordering, weight 1.
5. Correct line-level paid, corrected allowed, recovery, and dispositions, weight 3.
6. Correct resubmission route and standard priority, weight 1.

Each point is all-or-zero. Currency is normalized to cents, IDs are normalized case-insensitively, enum fields are lowercased for comparison, and null-like modifier strings are accepted as null. Likely model pitfalls include using the stale `Legacy Imaging Export` rates because they equal the original paid amounts, ignoring modifier `TC`, failing to multiply the A9500 benchmark by two units, sorting lines by CPT instead of claim-line order, or treating the underpayment as negative because the plan owes an upward correction.

### Transfer design

As a train task, this is a real solved example rather than a tutorial. Comparing attempts against the standard answer can teach several transferable habits: inspect claim and line records before aggregating totals; use effective-dated payment benchmarks rather than legacy exports; match rate rows by payer, plan type, service domain, CPT, modifier, and service date; apply units at the line level; return operational enums instead of narrative explanations; and keep stale-source rejection explicit. These habits anchor `test_003` and contribute to the mixed queue claim item in `test_005`.

### Construction record

Author: Builder C. Created: 2026-07-18. Updated: 2026-07-18. Major changes: created the complete `train_tasks/003` package, verified target database rows, wrote the standard answer from the assignment and database evidence, and implemented the six-point evaluator.

## 中文

### 数据来源与血缘

本任务属于 `task_group_014`，来源场景是 `SCN_014_healthcare_payer_authorization_appeals`，主要承接源示例 `E003` 和 `E004` 中的支付基准选择、索赔复核和纠错计算工作流。任务设计来自 Builder C 的 `train_003: Cardiac SPECT Claim Repricing` 分配说明。共享环境是 Northstar Health Plan 的 SQLite 后端服务，由 `scratch/env_blueprint.md` 和 `task_group/task_group_014/env/manifest.json` 描述，数据种子为 `140417`。

目标业务记录为 `CLAIM-TR-003`。构造时核对了共享数据库中的 `cases`、`claims`、`claim_lines`、`documents`、`document_facts`、`policies`、`policy_criteria`、`case_criteria`、`payment_benchmarks`、`members` 和 `plans` 表。解题者可见的本地材料只有 `input/payloads/task_context.json` 与 `input/payloads/answer_template.json`，它们提供目标 ID、角色、报告日期、访问方式和输出结构，但不提供最终重定价结果。

### 任务定义与场景适配

业务角色是支付完整性分析师，需要为一笔心脏 SPECT 索赔准备纠错包。解题者需要通过环境端点，必要时使用 `POST /sql/query`，查看索赔、索赔行、案件上下文、现行支付基准和过期基准干扰项。输出应为结构化 JSON，包含索赔身份、基准来源和版本、被拒绝的过期来源、汇总金额、行级纠错、提交路径和优先级。

该任务符合医疗支付方运营场景，因为它结合了索赔支付复核、有效期内基准选择、CPT/修饰符匹配、按单位应用允许金额以及运营纠错路由。它也为后续测试任务提供迁移经验：当前有效的基准表优先于旧导出，行级纠错必须匹配付款方、计划类型、服务域、CPT、修饰符和单位。

### 材料地图

- `input/prompt.txt`：可见业务请求、环境访问说明和 JSON 输出要求。
- `input/payloads/task_context.json`：目标索赔/案件 ID、角色、报告日期和简短 intake 备忘。
- `input/payloads/answer_template.json`：必需 JSON 字段、枚举、金额精度、修饰符空值约定和行排序规则。
- `claims`：目标行包含 `CLAIM-TR-003`、案件 ID `CLAIM-TR-003`、授权号 `NPA-2404980`、已付总额 `940.00` 和状态 `paid_stale_schedule`。
- `claim_lines`：三条目标索赔行，包含 CPT、修饰符、单位和已付金额。
- `cases`、`policies`、`policy_criteria`、`case_criteria`：支付完整性上下文和当前基准规则。
- `documents` 与 `document_facts`：EOB 证据、已付总额和旧费率表标记；正确允许金额和追回金额需要从 `payment_benchmarks` 推导。
- `payment_benchmarks`：当前 `Northstar Commercial Imaging Schedule` `2026Q2` 行，以及过期 `Legacy Imaging Export` 行。
- `output/answer.json`：隐藏标准答案。
- `eval/evaluator.py` 与 `eval/eval.sh`：确定性的整点评分器。

### 解法与评估依据

正确身份为 claim ID `CLAIM-TR-003`、case ID `CLAIM-TR-003`、授权号 `NPA-2404980`。当前基准为 `Northstar Commercial Imaging Schedule`，版本 `2026Q2`；`Legacy Imaging Export` 应作为过期来源被拒绝。已付总额为 `940.00`，正确允许总额为 `1175.00`，追回金额为 `235.00`。

行级依据如下：

- `CL-TR-003-1`：CPT `78452`，修饰符 `TC`，单位 `1`，已付 `608.00`，当前允许 `760.00`，追回 `152.00`，处置为 `correct_upward`。
- `CL-TR-003-2`：CPT `A9500`，修饰符 `null`，单位 `2`，已付 `288.00`，当前允许 `360.00`，追回 `72.00`，处置为 `correct_upward`。
- `CL-TR-003-3`：CPT `93016`，修饰符 `null`，单位 `1`，已付 `44.00`，当前允许 `55.00`，追回 `11.00`，处置为 `correct_upward`。

运营路径为 `payment_integrity_correction`，优先级为 `standard`。

评估器包含 6 个整点评分目标，原始权重总计 11：

1. 索赔、案件和授权身份正确，权重 1。
2. 当前基准来源/版本正确，且正确拒绝过期来源，权重 2。
3. 已付总额、正确允许总额和追回金额正确，权重 3。
4. 行级 CPT、修饰符、单位和稳定排序正确，权重 1。
5. 行级已付金额、纠正允许金额、追回金额和处置正确，权重 3。
6. 纠错提交路径和标准优先级正确，权重 1。

每个评分点都是全得或零分。金额按美分归一化，ID 比较忽略大小写，枚举字段按小写比较，类似 null 的修饰符字符串可按空值处理。常见错误包括使用 `Legacy Imaging Export` 旧费率、忽略 `TC` 修饰符、未将 A9500 基准乘以 2 个单位、按 CPT 而不是索赔行顺序排序，或把上调纠错金额记成负数。

### 迁移设计

作为训练任务，本任务是一个真实已解样本，而不是教程。通过比较尝试答案和标准答案，可以推断出可迁移的工作习惯：先检查索赔和行记录再汇总；使用有效期内支付基准而非旧导出；按付款方、计划类型、服务域、CPT、修饰符和服务日期匹配费率；在行级应用单位；返回运营枚举而非叙述；明确记录过期来源被拒绝。这些经验会锚定 `test_003`，并帮助处理 `test_005` 中的索赔纠错项。

### 构造记录

作者：Builder C。创建日期：2026-07-18。更新日期：2026-07-18。主要变更：创建完整的 `train_tasks/003` 包；核对目标数据库记录；根据分配说明和数据库证据写入标准答案；实现六点评估器。

## 2026-07-19 Basis-Audit Update

English: The answer template and standard answer now use `basis_audit`, a business-grounded audit trail rather than an invented control-code layer. `source_precedence` records the source category, `precedence_record_order` records the ordered business source trail, `controlling_record_ids` records the environment records that directly control the result, and `exception_record_ids` records stale, missing, unsupported, unresolved, or route-priority records. For this task, `source_precedence` is `effective_benchmark_by_plan_modifier_and_date`, `precedence_record_order` is `BM-TR-003-78452`, `BM-TR-003-A9500`, `BM-TR-003-93016`, `BM-OLD-78452`, controlling records are `CL-TR-003-1`, `CL-TR-003-2`, `CL-TR-003-3`, `BM-TR-003-78452`, `BM-TR-003-A9500`, `BM-TR-003-93016`, and exception records are `BM-OLD-78452`; the train evaluator scores this combined basis trail at low weight.

中文：答案模板和标准答案现在使用 `basis_audit`，这是基于业务依据的审计轨迹，而不是人为 control-code 层。`source_precedence` 记录来源类别，`precedence_record_order` 记录按优先级排列的业务来源轨迹，`controlling_record_ids` 记录直接决定结果的环境记录，`exception_record_ids` 记录过期、缺失、不支持、未解决或路线优先级记录。本任务中，`source_precedence` 为 `effective_benchmark_by_plan_modifier_and_date`，`precedence_record_order` 为 `BM-TR-003-78452`, `BM-TR-003-A9500`, `BM-TR-003-93016`, `BM-OLD-78452`，控制记录为 `CL-TR-003-1`, `CL-TR-003-2`, `CL-TR-003-3`, `BM-TR-003-78452`, `BM-TR-003-A9500`, `BM-TR-003-93016`，例外记录为 `BM-OLD-78452`；the train evaluator scores this combined basis trail at low weight。
