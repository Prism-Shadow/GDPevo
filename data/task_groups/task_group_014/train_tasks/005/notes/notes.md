# train_005 Notes

## English

Task: Outpatient rehab payer-service profitability action list.

Data lineage: The task uses the shared SQLite payer operations environment for `task_group_014`. The construction-visible manifest identifies the profitability focus as `CLN001`, `CLN003`, `Commercial`, and `Medicaid`. The standard answer was computed from `encounters`, `clinic_costs`, `clinic_budgets`, and `claim_corrections`.

Solver-facing access: The prompt requires solvers to use `<TASK_ENV_BASE_URL>/query` and discloses the fixed synthetic Basic Auth credentials, but does not expose a local file path, runtime port, or direct answer endpoint.

Scope and basis: The analysis period is calendar year 2025. The scored cells are the 12 combinations of two clinics, two plan types, and three outpatient rehab-adjacent service categories: `Evaluation Management`, `Pain Management`, and `Physical Therapy`. The task intentionally uses `plan_type` rather than the encounter `payer` value because this generated dataset stores one displayed payer name across plan types.

Profitability formula: Net revenue is paid amount plus only open expected recoveries. Total cost is units multiplied by direct plus allocated overhead cost per unit. Net margin and margin percent are compared with the maximum budget margin threshold for the same clinic, fiscal year, and service category.

Transfer design: This trains solvers to join encounter aggregates to cost and budget tables, include only open correction recoveries, distinguish plan type from payer display name, rank loss drivers, and produce controlled payer actions. These habits transfer to the paired test profitability task without disclosing its target facts.

Scoring goals: The evaluator has seven exact-match business-result points with raw weights 3, 2, 2, 2, 2, 1, and 1. It scores margin metrics, top loss-driver ranking, action choices, budget variance classes, open recovery inclusion, persistence/noise classes, and portfolio totals.

Construction record: The top three losses are `CLN003` Commercial Evaluation Management, `CLN001` Commercial Evaluation Management, and `CLN001` Commercial Physical Therapy. Eight of the 12 cells are major shortfalls and require action.

## 中文

任务：门诊康复按付款类型和服务类别生成盈利能力行动清单。

数据来源：本任务使用 `task_group_014` 的共享 SQLite 付款方运营环境。构建可见的清单将盈利分析重点标为 `CLN001`、`CLN003`、`Commercial` 和 `Medicaid`。标准答案由 `encounters`、`clinic_costs`、`clinic_budgets` 和 `claim_corrections` 计算得到。

求解访问方式：提示要求求解者通过 `<TASK_ENV_BASE_URL>/query` 使用 SQL，并公开固定合成 Basic Auth 凭据，但不暴露本地数据库路径、运行时端口或直接答案接口。

范围和依据：分析期间为 2025 全年。评分单元是两个诊所、两个计划类型和三个门诊康复相关服务类别的 12 个组合：`Evaluation Management`、`Pain Management` 和 `Physical Therapy`。本任务明确使用 `plan_type`，因为生成数据中的 encounter `payer` 字段在多个计划类型下使用同一个显示名称。

盈利公式：净收入等于已付金额加上仅处于 open 状态的预期追回金额。总成本等于服务单位数乘以直接成本和分摊间接成本之和。净利润和利润率与同一诊所、财年、服务类别下的最高预算利润率阈值比较。

迁移设计：本训练任务让求解者练习将 encounter 聚合结果连接到成本和预算表，只纳入 open 的更正追回金额，区分计划类型和付款方显示名称，排序亏损驱动因素，并输出受控行动枚举。这些习惯可迁移到对应测试盈利任务，但不会泄露测试目标事实。

评分目标：评估器包含七个精确匹配的业务结果评分点，原始权重为 3、2、2、2、2、1 和 1。评分内容包括利润指标、前三大亏损驱动排序、行动选择、预算差异分类、open 追回金额纳入、持续性与噪声分类，以及组合汇总数值。

构建记录：前三大亏损是 `CLN003` Commercial Evaluation Management、`CLN001` Commercial Evaluation Management 和 `CLN001` Commercial Physical Therapy。12 个单元中有 8 个为重大短缺并需要行动。
