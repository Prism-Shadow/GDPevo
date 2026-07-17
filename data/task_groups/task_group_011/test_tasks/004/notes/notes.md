# test_004 Notes: Central branch watch-list stress report

## English

Data lineage: This task belongs to `SCN_011_bank_branch_credit_risk_lending_committee`, source examples `E001`, `E002`, and `E003`, and follows the task-group design for `test_004`. It uses only shared public environment data for branch `CENTRAL`: loans, branch metrics, public policy, and the FDIC Q4 2024 benchmark.

Task definition: The solver-visible request asks for a committee-ready JSON packet for Central as of 2025-03-31. The target population is loans with `current_rating >= 6`. The output includes `branch_id`, `watch_list_summary`, `stress_results`, `workout_queue`, `severe_bucket_counts`, and `npa_benchmark`.

Scenario fit and material map: `/api/branches/CENTRAL/loans` supplies loan records, `/api/branches/CENTRAL/metrics?quarter=2025Q1` supplies total and nonperforming loan balances, `/api/policies` supplies factor-score and stress conventions, and `/api/benchmarks/fdic/q4-2024` supplies the benchmark. This is a portfolio surveillance, stress, and workout triage workflow in the same family as the source examples.

Solution and evaluation basis: Central has seven adversely rated loans totaling 8,959,908.25. Available LTV, FICO, liquidity-month, and debt-to-asset factors produce the CDFI-style class map in `answer.json`; missing non-applicable factors are not scored. The large hotel loan `CEN-LN-901` is underwater and nonaccrual, so it is the projected-loss exposure and receives `partial_chargeoff_review`. The +200bp watch-list stress uses `dscr / 1.18`, rounded to two decimals, and all four adverse loans with DSCR breach 1.00 after stress. NPA exposure is 7,753,634.12 over total loans of 20,504,486.58, producing a 0.3781 branch ratio and 3,683.43 bps variance over the FDIC 0.0098 benchmark.

Scoring basis: Seven exact-match scoring points are used: SP001 adverse count/balance weight 2; SP002 risk class mapping and projected-loss set weight 3; SP003 stressed DSCR breach set weight 3; SP004 dominant problem exposure/action weight 2; SP005 severe bucket counts weight 2; SP006 NPA/FDIC variance weight 2; SP007 monitoring cadence weight 1. Common pitfalls include using all weak-looking Central loans instead of only current-rating adverse loans, treating missing DSCR as a breach, missing the projected-loss override, or using the wrong FDIC benchmark field.

Transfer design: The main transfer anchor is `train_004`, which establishes CDFI factor scoring, watch-list stress arithmetic, projected-loss treatment, workout action enums, and severe bucket counts. `train_001` anchors NPA numerator/denominator handling and the FDIC total-loans noncurrent benchmark comparison. High-value scoring points SP002, SP003, SP004, SP005, and SP006 depend on those anchors plus Central-specific exploration.

Construction record: Author `test_004_builder`; created and updated 2026-06-03. Major changes: created minimum complete prompt, answer template, standard answer, evaluator, and bilingual notes.

## 中文

数据来源：本任务属于 `SCN_011_bank_branch_credit_risk_lending_committee`，来源示例为 `E001`、`E002`、`E003`，对应任务组设计中的 `test_004`。任务只使用共享公共环境中 `CENTRAL` 分行的贷款、分行指标、公开政策和 FDIC 2024Q4 基准数据。

任务定义：求解者需要为 2025-03-31 贷款委员会准备 Central 分行观察名单压力测试 JSON。目标范围是 `current_rating >= 6` 的不利评级贷款。输出包含 `branch_id`、`watch_list_summary`、`stress_results`、`workout_queue`、`severe_bucket_counts` 和 `npa_benchmark`。

场景适配与材料地图：`/api/branches/CENTRAL/loans` 提供贷款记录，`/api/branches/CENTRAL/metrics?quarter=2025Q1` 提供贷款总额和不良贷款余额，`/api/policies` 提供因子评分和压力测试规则，`/api/benchmarks/fdic/q4-2024` 提供 FDIC 基准。本任务属于组合监控、压力测试和问题贷款处置流程，与来源示例的业务分布一致。

解答和评估依据：Central 有 7 笔不利评级贷款，余额合计 8,959,908.25。标准答案使用可用的 LTV、FICO、流动性月数和负债资产比计算 CDFI 风格因子评分；缺失且不适用的因子不计分。大型酒店贷款 `CEN-LN-901` 抵押不足且为非应计，因此属于预计损失敞口，处置动作为 `partial_chargeoff_review`。+200bp 观察名单压力测试使用 `dscr / 1.18` 并保留两位小数，四笔有 DSCR 的不利评级贷款压力后均低于 1.00。NPA 敞口为 7,753,634.12，总贷款为 20,504,486.58，分行比率为 0.3781，相对 FDIC 0.0098 基准高 3,683.43 个基点。

评分依据：共有 7 个精确匹配评分点：SP001 不利评级数量和余额，权重 2；SP002 风险类别和预计损失集合，权重 3；SP003 压力 DSCR 违约集合，权重 3；SP004 最大问题敞口和处置动作，权重 2；SP005 严重评级桶计数，权重 2；SP006 NPA/FDIC 差异，权重 2；SP007 监控频率，权重 1。常见错误包括把所有看似较弱的 Central 贷款纳入范围、把缺失 DSCR 当成违约、遗漏预计损失覆盖规则，或选错 FDIC 基准字段。

迁移设计：主要迁移锚点是 `train_004`，它建立了 CDFI 因子评分、观察名单压力测试、预计损失处理、处置动作枚举和严重桶计数的做法。`train_001` 锚定 NPA 分子分母和 FDIC 总贷款非流动基准比较。高价值评分点 SP002、SP003、SP004、SP005 和 SP006 依赖这些迁移知识以及 Central 特定数据探索。

构建记录：作者 `test_004_builder`；创建并更新于 2026-06-03。主要变更：创建最小完整的提示、答案模板、标准答案、评估器和双语说明。
