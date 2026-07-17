# train_005 Notes - Harbor Competing CRE Decision

## English

Data/source lineage: This task belongs to `SCN_011_bank_branch_credit_risk_lending_committee`, using task-group design derived from source examples `E001`, `E002`, and `E003`. It uses only shared public environment data in `task_group_011_bank_branch_credit_risk_lending_committee/env/`: Harbor branch records, Harbor metrics, Harbor loans, sector exposures, applications `HAR-APP-901` and `HAR-APP-902`, policies, and FDIC Q4 2024 benchmarks. There are no task-local data payloads beyond `input/payloads/answer_template.json`.

Task definition: The solver receives an internal committee request for `branch_id` `HARBOR` and must compare two mutually competing CRE applications. The expected JSON covers `branch_id`, `applications_compared`, `recommended_path`, `stress`, `concentration`, and `conditions`. The work requires selecting the stronger CRE path while recognizing that Harbor is already above its CRE policy limit and underperforming the FDIC delinquency benchmark.

Scenario fit: The task is a branch lending-committee decision workflow. It combines credit scoring, stressed DSCR, concentration management, benchmark variance, and controlled approval conditions, matching the source examples' CRE decision matrix and branch-risk reporting patterns.

Material map: `/api/branches/HARBOR` gives lending capacity and the CRE policy limit. `/api/branches/HARBOR/applications` gives the two CRE application records. `/api/branches/HARBOR/loans` supports total existing CRE exposure. `/api/branches/HARBOR/metrics` supplies 2025Q1 delinquency and total loans outstanding. `/api/policies` supplies CRE weighted-score weights and the CRE dual-stress formula. `/api/benchmarks/fdic/q4-2024` supplies `total_real_estate_30_89_pct`.

Solution and evaluation basis: The hidden answer scores CRE applications using policy weights collateral/exposure 36%, capacity 45%, character 5%, conditions 11%, and capital 3%. Construction sub-scores use the shared policy factor style: LTV/debt-to-asset factors, DSCR capacity bands, relationship/guarantor character, and sector/benchmark conditions. `HAR-APP-901` scores 2.6 and remains conditional quality; `HAR-APP-902` scores 4.4 and is weak. The CRE stress formula is `dscr * 0.85 / 1.18`, producing stressed DSCR values 1.06 and 0.95. Existing CRE exposure is $7,011,570.24 against $14,933,688.02 of loans, or 0.4695. Full booking of selected `HAR-APP-901` would produce 0.5349 CRE concentration, 2,449.15 bps over the 0.29 limit, so the correct path is `participation_required`. Harbor 2025Q1 branch delinquency is 0.2853 versus FDIC real-estate 30-89 benchmark 0.0051, a variance of 0.2802 or 2,802.00 bps.

Evaluation scoring goals use exact matches with raw weights: SP001 weighted CDFI scores for both CRE applications, weight 2; SP002 stressed DSCR values and breach flags, weight 2; SP003 selected application and path enum, weight 3; SP004 post-approval CRE concentration, weight 2; SP005 FDIC delinquency benchmark variance, weight 2; SP006 condition set for selected credit, weight 2; SP007 deferral reason set for the unselected credit, weight 1. Common pitfalls are approving both CRE credits, ignoring existing CRE over-concentration, using the FDIC noncurrent benchmark instead of the real-estate delinquency benchmark, or selecting the hotel application despite its stressed DSCR breach.

Transfer design: As a train task, this should let solvers infer transferable habits for later application-decision tasks: discover branch/application/policy/benchmark endpoints, apply weighted CRE scoring consistently, stress CRE DSCR with the dual-stress formula, treat existing over-limit CRE as grandfathered but not freely expandable, and express mitigated approval through controlled enums and conditions. It is not a tutorial; the solver-visible prompt does not include thresholds, scoring weights, or the calculation path.

Construction record: Author `train_005` task-builder worker. Created 2026-06-03. Updated 2026-06-03. Major changes: created prompt, answer template, standard answer, evaluator, and bilingual notes for the Harbor competing CRE decision.

## Chinese

数据和来源：本任务属于 `SCN_011_bank_branch_credit_risk_lending_committee`，任务组设计来自源示例 `E001`、`E002` 和 `E003`。它只使用 `task_group_011_bank_branch_credit_risk_lending_committee/env/` 中的共享公开环境数据：Harbor 分行记录、分行指标、贷款、行业敞口、申请 `HAR-APP-901` 和 `HAR-APP-902`、政策以及 FDIC 2024 年第四季度基准。除 `input/payloads/answer_template.json` 外，没有任务本地数据包。

任务定义：求解者收到面向信贷委员会的内部请求，目标分行为 `HARBOR`，需要比较两笔相互竞争的 CRE 申请。预期 JSON 覆盖 `branch_id`、`applications_compared`、`recommended_path`、`stress`、`concentration` 和 `conditions`。工作重点是在选择更强 CRE 方案的同时，识别 Harbor 已超过 CRE 政策限额且落后于 FDIC 逾期基准。

场景匹配：这是分行贷款委员会决策流程，结合信用评分、压力 DSCR、集中度管理、基准差异和受控审批条件，符合源示例中的 CRE 决策矩阵和分行风险报告模式。

材料地图：`/api/branches/HARBOR` 提供放款容量和 CRE 政策限额。`/api/branches/HARBOR/applications` 提供两笔 CRE 申请记录。`/api/branches/HARBOR/loans` 用于计算现有 CRE 敞口。`/api/branches/HARBOR/metrics` 提供 2025Q1 逾期率和总贷款余额。`/api/policies` 提供 CRE 加权评分权重和 CRE 双重压力公式。`/api/benchmarks/fdic/q4-2024` 提供 `total_real_estate_30_89_pct`。

解答和评估依据：隐藏答案使用政策权重计算 CRE 申请分数：抵押/敞口 36%、偿债能力 45%、品格 5%、条件 11%、资本 3%。构造子分数沿用共享政策的因素风格：LTV/债务资产比、DSCR 偿债能力分档、关系和担保人品格，以及行业和基准条件。`HAR-APP-901` 得分 2.6，属于有条件质量；`HAR-APP-902` 得分 4.4，属于弱项。CRE 压力公式为 `dscr * 0.85 / 1.18`，得到压力 DSCR 1.06 和 0.95。现有 CRE 敞口为 7,011,570.24 美元，总贷款为 14,933,688.02 美元，集中度为 0.4695。若全额入账所选 `HAR-APP-901`，CRE 集中度将为 0.5349，比 0.29 限额高 2,449.15 个基点，因此正确路径为 `participation_required`。Harbor 2025Q1 分行逾期率为 0.2853，FDIC 房地产 30-89 天逾期基准为 0.0051，差异为 0.2802，即 2,802.00 个基点。

评估得分点采用精确匹配和原始权重：SP001 两笔 CRE 申请的加权 CDFI 分数，权重 2；SP002 压力 DSCR 和突破标记，权重 2；SP003 所选申请和路径枚举，权重 3；SP004 批准后 CRE 集中度，权重 2；SP005 FDIC 逾期基准差异，权重 2；SP006 所选信用的条件集合，权重 2；SP007 未选信用的暂缓原因集合，权重 1。常见错误包括批准两笔 CRE、忽略既有 CRE 超限、使用 FDIC 非流动贷款基准而不是房地产逾期基准，或在酒店申请压力 DSCR 跌破阈值后仍选择它。

迁移设计：作为训练任务，它帮助求解者归纳后续申请决策任务所需的可迁移习惯：发现分行、申请、政策和基准端点；一致应用 CRE 加权评分；用双重压力公式测试 CRE DSCR；将既有超限 CRE 视为可存量保留但不能自由增加；并用受控枚举和条件表达缓释审批。它不是教程；求解者可见提示不包含阈值、评分权重或计算路径。

构造记录：作者为 `train_005` task-builder worker。创建日期 2026-06-03。更新日期 2026-06-03。主要变更：创建 Harbor 竞争 CRE 决策的提示、答案模板、标准答案、评估器和双语 notes。
