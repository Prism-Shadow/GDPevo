# train_001 Notes - Redwood Branch Rating Migration Review

## English

Data/source lineage: This task belongs to `SCN_011_bank_branch_credit_risk_lending_committee`, using the task-group design derived from source examples `E001`, `E002`, and `E003`. It uses only shared public environment data under `task_group_011_bank_branch_credit_risk_lending_committee/env/`, especially the API surfaces for branches, Redwood loans, Redwood branch metrics, credit policy, and FDIC Q4 2024 benchmarks. There are no task-local data payloads beyond `input/payloads/answer_template.json`.

Task definition: The solver receives an internal credit committee request for branch_id `REDWOOD` with review date `2025-03-31`. The expected output is a structured JSON object covering `branch_id`, `review_date`, `portfolio_regrade`, `npa_benchmark`, `material_downgrades`, and `top_problem_credit`. The regrade population is Redwood loans whose current rating is 3 or worse. The target set has 15 loans and $13,072,381.11 of exposure.

Scenario fit: The task is a portfolio surveillance and lending-committee reporting task. It requires reconciling branch portfolio records, policy rules, rating migration, external FDIC benchmark variance, and controlled follow-up actions, matching the source examples' branch credit review workflow.

Material map: `/api/branches/REDWOOD` identifies the branch and FDIC benchmark set. `/api/branches/REDWOOD/loans` provides current ratings, balances, DSCR, LTV, delinquency status, borrower names, and notes. `/api/branches/REDWOOD/metrics` supplies 2025Q1 total loans outstanding and branch nonperforming loans. `/api/policies` supplies the risk-rating policy, dominant-factor convention, and material-downgrade threshold. `/api/benchmarks/fdic/q4-2024` supplies `total_loans_noncurrent_pct`.

Solution and evaluation basis: The answer uses the policy's dominant worst-factor rating from available DSCR, LTV, and delinquency factors. A material downgrade is two or more notches worse than the current rating inside the target population. Nonperforming exposure is $1,725,000.00, total loans are $15,191,701.54, branch NPA ratio is 0.1135, FDIC benchmark is 0.0098, and variance is 0.1037 or 1,037.49 bps. The top problem credit is `RED-LN-901`, a nonaccrual exposure to Cedar Harbor Properties LLC, assigned `partial_chargeoff_review`.

Evaluation scoring goals use exact matches with raw weights: SP001 target regrade count and exposure, weight 2; SP002 final-rating exposure totals, weight 3; SP003 material downgrade loan IDs, weight 3; SP004 NPA ratio and FDIC variance, weight 2; SP005 top problem credit and action, weight 2; SP006 current-rating-3 migration distribution, weight 2; SP007 watch-list action coverage, weight 1. Common pitfalls are treating all Redwood loans as the regrade population, including current-rating-2 `RED-LN-009` as a material downgrade, using the branch delinquency 30+ percentage as the NPA ratio, or comparing against the wrong FDIC real-estate benchmark.

Transfer design: As a train task, this should let solvers infer transferable habits for later portfolio surveillance tasks: discover the relevant public API endpoints, preserve the target population boundary, apply the dominant-factor rating convention, use the total-loans noncurrent FDIC benchmark for branch-level NPA variance, and convert adverse regrades into controlled watch-list actions. It is not a tutorial; the prompt does not expose thresholds or a step list, so the transferable method comes from solving the task and comparing against the standard answer.

Construction record: Author `train_001` task-builder worker. Created 2026-06-03. Updated 2026-06-03. Major changes: created prompt, answer template, standard answer, evaluator, and bilingual notes for the Redwood branch rating migration review.

## Chinese

数据和来源：本任务属于 `SCN_011_bank_branch_credit_risk_lending_committee`，任务组设计来自源示例 `E001`、`E002` 和 `E003`。任务只使用共享公开环境数据，主要包括分行、Redwood 贷款组合、Redwood 分行指标、信用政策以及 FDIC 2024 年第四季度基准的 API。除 `input/payloads/answer_template.json` 外，没有任务本地数据包。

任务定义：求解者看到的是面向信贷委员会的内部请求，目标分行为 `REDWOOD`，复核日期为 `2025-03-31`。预期输出是结构化 JSON，覆盖 `branch_id`、`review_date`、`portfolio_regrade`、`npa_benchmark`、`material_downgrades` 和 `top_problem_credit`。重评级范围是 Redwood 当前评级为 3 或更差的贷款。目标集合共有 15 笔贷款，风险敞口为 13,072,381.11 美元。

场景匹配：这是一个组合监控和信贷委员会报告任务。它要求把分行贷款记录、政策规则、评级迁移、外部 FDIC 基准差异和受控后续行动整合成委员会可用的结果，符合源示例中的分行信用复核流程。

材料地图：`/api/branches/REDWOOD` 用于确认分行和 FDIC 基准集。`/api/branches/REDWOOD/loans` 提供当前评级、余额、DSCR、LTV、逾期状态、借款人名称和备注。`/api/branches/REDWOOD/metrics` 提供 2025Q1 总贷款余额和不良贷款数据。`/api/policies` 提供风险评级政策、主导最差因素规则和重大下调阈值。`/api/benchmarks/fdic/q4-2024` 提供 `total_loans_noncurrent_pct`。

解答和评估依据：标准答案按照政策中的主导最差因素规则，从可用的 DSCR、LTV 和逾期因素重新派生评级。重大下调是在目标范围内最终评级比当前评级差两个或更多等级。不良敞口为 1,725,000.00 美元，总贷款余额为 15,191,701.54 美元，分行 NPA 比率为 0.1135，FDIC 基准为 0.0098，差异为 0.1037，即 1,037.49 个基点。最高问题贷款是 `RED-LN-901`，借款人为 Cedar Harbor Properties LLC，状态为非应计，行动为 `partial_chargeoff_review`。

评估得分点采用精确匹配和原始权重：SP001 目标重评级数量和敞口，权重 2；SP002 最终评级敞口汇总，权重 3；SP003 重大下调贷款 ID，权重 3；SP004 NPA 比率和 FDIC 差异，权重 2；SP005 最高问题贷款及行动，权重 2；SP006 当前评级 3 的迁移分布，权重 2；SP007 观察名单行动覆盖，权重 1。常见错误包括把所有 Redwood 贷款都纳入重评级范围，把当前评级为 2 的 `RED-LN-009` 纳入重大下调，误用 30 天以上逾期率作为 NPA 比率，或使用错误的 FDIC 房地产基准。

迁移设计：作为训练任务，它帮助求解者归纳后续组合监控任务所需的可迁移经验：发现相关公开 API，保持目标总体边界，应用主导最差因素评级规则，使用总贷款非流动 FDIC 基准计算分行 NPA 差异，并把不利重评级转换为受控观察名单行动。它不是教程；提示中没有暴露阈值或步骤清单，方法需要通过实际求解并对照标准答案获得。

构造记录：作者为 `train_001` task-builder worker。创建日期 2026-06-03。更新日期 2026-06-03。主要变更：创建 Redwood 分行评级迁移复核的提示、答案模板、标准答案、评估器和双语 notes。
