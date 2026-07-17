# Northstar Portfolio Migration Package Notes

## English

Data/source lineage: This test task belongs to `SCN_011_bank_branch_credit_risk_lending_committee`, using the task-group design derived from source examples `E001`, `E002`, and `E003`. It uses only shared public environment data under `task_group/task_group_011_bank_branch_credit_risk_lending_committee/env/`, especially the public API surfaces for branches, Northstar loans, Northstar branch metrics, credit policy, and FDIC Q4 2024 benchmarks. There are no task-local data payloads beyond `input/payloads/answer_template.json`.

Task definition: The solver receives an internal credit committee request for branch_id `NORTHSTAR` with review date `2025-03-31`. The expected output is structured JSON covering `branch_id`, `review_date`, `portfolio_regrade`, `npa_benchmark`, `material_downgrades`, and `top_problem_credit`. The regrade population is Northstar loans whose current rating is 3 or worse. The target set has 14 loans and $17,136,273.39 of exposure.

Scenario fit: This is a portfolio surveillance and lending-committee reporting task. It combines branch portfolio records, re-derived credit ratings, material downgrade identification, FDIC benchmark variance, and controlled credit actions, matching the source examples' branch credit review workflow while using a larger and noisier Northstar portfolio.

Material map: `/api/branches/NORTHSTAR` identifies the branch and benchmark set. `/api/branches/NORTHSTAR/loans` provides loan IDs, borrower names, current ratings, balances, DSCR, LTV, delinquency status, and notes. `/api/branches/NORTHSTAR/metrics` supplies 2025Q1 total loans outstanding and nonperforming loans. `/api/policies` supplies the dominant-factor risk-rating convention, delinquency floors, material-downgrade threshold, and action vocabulary. `/api/benchmarks/fdic/q4-2024` supplies `total_loans_noncurrent_pct`.

Solution and evaluation basis: The answer applies the policy's dominant worst-factor rating from available DSCR, LTV/collateral, and delinquency factors. A material downgrade is a final rating two or more notches worse than the current rating inside the target population. The final rating exposure totals are rating 4: 4 loans and $4,334,565.41; rating 5: 4 loans and $4,888,489.61; rating 6: 1 loan and $1,029,027.36; rating 7: 4 loans and $6,717,422.49; rating 8: 1 loan and $166,768.52. The material downgrade IDs are `NOR-LN-003`, `NOR-LN-007`, `NOR-LN-008`, `NOR-LN-011`, `NOR-LN-901`, and `NOR-LN-902`. Nonperforming exposure is $2,546,768.52, total loans are $23,400,285.78, branch NPA ratio is 0.1088, FDIC benchmark is 0.0098, and variance is 0.0990 or 990.35 bps. The top problem credit uses the worst final rating, then exposure as tie-breaker: `NOR-LN-018`, assigned `partial_chargeoff_review`. The high-balance severe delinquency override is `NOR-LN-901`, whose 90+ day payment status drives final rating 7 even though DSCR 1.42 and LTV 0.6900 would otherwise be lower-risk.

Evaluation scoring goals use exact matches with raw weights: SP001 target regrade count and exposure, weight 2; SP002 final-rating exposure totals, weight 3; SP003 material downgrade loan IDs, weight 3; SP004 NPA ratio and FDIC variance, weight 2; SP005 top problem credit and action, weight 2; SP006 severe delinquency override loan, weight 2; SP007 full current-rating migration distribution, weight 2; SP008 watch-list action coverage, weight 1. Common pitfalls are using all Northstar loans instead of current-rating-3-or-worse loans, averaging risk factors rather than using the worst factor, missing the severe delinquency override for `NOR-LN-901`, using only nonaccrual loans instead of the branch nonperforming loan amount for NPA, or comparing against the real-estate FDIC benchmark instead of total loans noncurrent.

Transfer design: This test is anchored by `train_001` and `train_004`. `train_001` transfers the target population boundary, dominant-factor regrade, material downgrade convention, branch-level NPA denominator, FDIC benchmark field, and action mapping used by SP001 through SP005 and SP008. `train_004` reinforces delinquency and adverse-risk handling, especially the idea that payment-status severity can control the final risk/action result, which supports SP006. The task-specific difficulty is Northstar's broader migration table, multiple current-rating 4 conflicts, and the separate high-balance delinquency override; the solver-visible prompt does not restate the hidden SOP or threshold table.

Construction record: Author `test_001` task-builder worker. Created 2026-06-03. Updated 2026-06-03. Major changes: created prompt, answer template, standard answer, evaluator, and bilingual notes for the Northstar portfolio migration package.

## 中文

数据和来源：本测试任务属于 `SCN_011_bank_branch_credit_risk_lending_committee`，任务组设计来自源示例 `E001`、`E002` 和 `E003`。任务只使用共享公开环境数据，主要包括分行、Northstar 贷款组合、Northstar 分行指标、信用政策以及 FDIC 2024 年第四季度基准的 API。除 `input/payloads/answer_template.json` 外，没有任务本地数据包。

任务定义：求解者看到的是面向信贷委员会的内部请求，目标分行为 `NORTHSTAR`，复核日期为 `2025-03-31`。预期输出是结构化 JSON，覆盖 `branch_id`、`review_date`、`portfolio_regrade`、`npa_benchmark`、`material_downgrades` 和 `top_problem_credit`。重评级范围是 Northstar 当前评级为 3 或更差的贷款。目标集合共有 14 笔贷款，风险敞口为 17,136,273.39 美元。

场景匹配：这是一个组合监控和信贷委员会报告任务。它要求整合分行贷款记录、重新推导的信用评级、重大下调识别、FDIC 基准差异和受控信用行动，符合源示例中的分行信用复核流程，同时使用更大、更嘈杂的 Northstar 贷款组合。

材料地图：`/api/branches/NORTHSTAR` 用于确认分行和基准集合。`/api/branches/NORTHSTAR/loans` 提供贷款 ID、借款人名称、当前评级、余额、DSCR、LTV、逾期状态和备注。`/api/branches/NORTHSTAR/metrics` 提供 2025Q1 贷款总额和不良贷款金额。`/api/policies` 提供主导最差因素评级规则、逾期下限、重大下调门槛和行动枚举。`/api/benchmarks/fdic/q4-2024` 提供 `total_loans_noncurrent_pct`。

解答和评估依据：标准答案使用政策中的主导最差因素规则，在可用的 DSCR、LTV/抵押品和逾期因素中取最差评级。重大下调定义为在目标范围内最终评级比当前评级差两个或更多等级。最终评级敞口合计为：评级 4 共 4 笔、4,334,565.41 美元；评级 5 共 4 笔、4,888,489.61 美元；评级 6 共 1 笔、1,029,027.36 美元；评级 7 共 4 笔、6,717,422.49 美元；评级 8 共 1 笔、166,768.52 美元。重大下调贷款 ID 为 `NOR-LN-003`、`NOR-LN-007`、`NOR-LN-008`、`NOR-LN-011`、`NOR-LN-901` 和 `NOR-LN-902`。不良贷款敞口为 2,546,768.52 美元，贷款总额为 23,400,285.78 美元，分行 NPA 比率为 0.1088，FDIC 基准为 0.0098，差异为 0.0990 或 990.35 个基点。最高问题信用按照最差最终评级、再按敞口打破并列确定，为 `NOR-LN-018`，行动为 `partial_chargeoff_review`。高余额严重逾期覆盖项为 `NOR-LN-901`，其 90 天以上逾期状态把最终评级推至 7，尽管 DSCR 1.42 和 LTV 0.6900 本身不会给出这么差的评级。

评估计分点采用精确匹配，原始权重为：SP001 重评级数量和敞口，权重 2；SP002 最终评级敞口合计，权重 3；SP003 重大下调贷款 ID 集合，权重 3；SP004 NPA 比率和 FDIC 差异，权重 2；SP005 最高问题信用和行动，权重 2；SP006 严重逾期覆盖贷款，权重 2；SP007 完整当前评级迁移分布，权重 2；SP008 观察名单行动覆盖，权重 1。常见错误包括把所有 Northstar 贷款都纳入范围、平均风险因素而不是取最差因素、漏掉 `NOR-LN-901` 的严重逾期覆盖、只用非应计贷款而不是分行不良贷款金额计算 NPA，或使用房地产 FDIC 基准而不是总贷款非当前基准。

迁移设计：本测试任务的迁移锚点是 `train_001` 和 `train_004`。`train_001` 迁移目标范围边界、主导因素重评级、重大下调规则、分行 NPA 分母、FDIC 基准字段和行动映射，支撑 SP001 到 SP005 以及 SP008。`train_004` 强化逾期和不利风险处理，尤其是付款状态严重性可以控制最终风险和行动结果，这支撑 SP006。任务特有难度在于 Northstar 的完整迁移表、多个当前评级 4 的冲突项，以及单独的高余额逾期覆盖项；求解者可见提示没有复述隐藏 SOP 或阈值表。

构造记录：作者为 `test_001` task-builder worker。创建日期 2026-06-03，更新日期 2026-06-03。主要变更：创建 Northstar 组合迁移包的提示、答案模板、标准答案、评估器和双语说明。
