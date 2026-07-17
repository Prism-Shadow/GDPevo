# train_004 Notes: Summit watch-list stress and workout actions

## English

Data lineage: This task belongs to `SCN_011_bank_branch_credit_risk_lending_committee`, source examples `E001`, `E002`, and `E003`, and follows the task-group design for `train_004`. It uses only the shared environment data in `task_group_011_bank_branch_credit_risk_lending_committee/env`: branch `SUMMIT`, public policies, and loan records from the credit-office API/database.

Task definition: The solver-visible request asks for a committee-ready JSON watch-list packet for Summit as of 2025-03-31. The target population is loans with `current_rating >= 6`. The output must include `branch_id`, `watch_list_summary`, `stress_results`, `workout_queue`, and `severe_bucket_counts`.

Scenario fit and material map: `/api/branches/SUMMIT/loans` supplies the loan records; `/api/policies` supplies CDFI factor scores and the +200bp watch-list stress formula; `answer_template.json` defines the exact output schema. The workflow is a portfolio surveillance and workout triage task, matching the source examples' watch-list, stress, and adverse-classification work.

Solution basis: Summit has seven adversely rated loans totaling 7,675,179.41. CDFI-style objective factor scores use available LTV, FICO, liquidity months, and debt-to-asset factors; missing non-applicable factors are not scored. The `Projected Loss` classification is assigned to the underwater nonaccrual/loss-grade loan `SUM-LN-902`, consistent with the source scenario's projected-loss convention. Watch-list stress uses `stressed_dscr = dscr / 1.18`, rounded to two decimals, and flags breaches below 1.00. Action mapping follows the portfolio surveillance convention: rating 6 to `watchlist`, rating 7 to `special_assets`, and underwater/nonaccrual loss-grade exposure to `partial_chargeoff_review`.

Scoring basis: Seven exact-match points are used: SP001 adverse count/balance weight 2; SP002 risk classes weight 3; SP003 stressed DSCR breach set and DSCR values weight 3; SP004 largest problem exposure/action weight 2; SP005 projected-loss classification weight 2; SP006 severe bucket counts weight 2; SP007 monitoring cadence weight 1. Common pitfalls are using all Summit loans instead of adverse-rated loans, treating DSCR-missing loans as stress breaches, forgetting the underwater projected-loss override, or mis-sorting the severe bucket counts.

Transfer design: As a train task, this teaches by answer comparison how the shared policy fields, CDFI factor-score bins, watch-list stress formula, action enums, and payment-status/risk-rating cross-tabs are expected to be operationalized. It anchors later Central-branch watch-list stress work without exposing those test answers.

Construction record: Author `train_004_builder`; created and updated 2026-06-03. Major changes: created minimum complete prompt, template, standard answer, evaluator, and bilingual notes.

## 中文

数据来源：本任务属于 `SCN_011_bank_branch_credit_risk_lending_committee`，来源示例为 `E001`、`E002`、`E003`，对应任务组设计中的 `train_004`。任务只使用共享环境中的公开数据：`SUMMIT` 分行、公开政策和贷款记录。

任务定义：求解者需要为 2025-03-31 贷款委员会准备 Summit 分行观察名单压力测试 JSON。目标贷款为 `current_rating >= 6` 的不利评级贷款。输出包含 `branch_id`、`watch_list_summary`、`stress_results`、`workout_queue` 和 `severe_bucket_counts`。

场景适配与材料地图：`/api/branches/SUMMIT/loans` 提供贷款记录，`/api/policies` 提供 CDFI 因子评分和 +200bp 观察名单压力公式，`answer_template.json` 规定输出结构。本任务属于组合监控和问题贷款处置队列，与来源示例中的观察名单、压力测试和不利分类流程一致。

解答依据：Summit 有 7 笔不利评级贷款，余额合计 7,675,179.41。CDFI 客观因子评分使用可用的 LTV、FICO、流动性月数和负债资产比；缺失且不适用的因子不计分。`SUM-LN-902` 为抵押不足且非应计/损失级风险贷款，因此按来源场景约定归类为 `Projected Loss`。压力测试公式为 `stressed_dscr = dscr / 1.18`，保留两位小数，低于 1.00 标记为违约覆盖缺口。处置动作沿用组合监控约定：评级 6 为 `watchlist`，评级 7 为 `special_assets`，抵押不足且非应计损失级风险为 `partial_chargeoff_review`。

评分依据：共 7 个精确匹配评分点：SP001 不利评级数量和余额，权重 2；SP002 风险类别，权重 3；SP003 压力 DSCR 及违约集合，权重 3；SP004 最大问题敞口和动作，权重 2；SP005 预计损失分类，权重 2；SP006 严重评级桶的支付状态计数，权重 2；SP007 监控频率，权重 1。常见错误包括把所有 Summit 贷款纳入范围、把无 DSCR 贷款当成压力违约、遗漏抵押不足预计损失规则、或严重桶排序错误。

迁移设计：作为训练任务，本任务通过标准答案对比帮助求解者归纳共享政策字段、CDFI 因子评分、观察名单压力公式、动作枚举和支付状态交叉表的使用方式。它为后续 Central 分行观察名单压力测试提供迁移锚点，但不泄露测试答案。

构建记录：作者 `train_004_builder`；创建并更新于 2026-06-03。主要变更：创建最小完整的提示、模板、标准答案、评估器和双语说明。
