# Southport CRE and Mixed Decision Matrix Notes

English notes: This hidden construction note covers `test_005` in `SCN_011_bank_branch_credit_risk_lending_committee`, derived from source examples `E001`, `E002`, and `E003`. The task uses only shared public environment data for branch_id `SOUTHPORT`: branch capacity and CRE limit, Q1 metrics, sector exposures, the pending application queue, policy rules, and FDIC benchmark data. The only task-local payload is `input/payloads/answer_template.json`.

Task definition and fit: The solver must produce a lending-committee JSON decision matrix for a branch with an already elevated CRE book and a mixed application queue. This belongs to the group because it combines application framework selection, CRE stress, concentration management, capacity allocation, and controlled decision/reason codes.

Material map: `/api/branches/SOUTHPORT` supplies `lending_capacity_q1` and `cre_policy_limit_pct`; `/api/branches/SOUTHPORT/metrics` supplies total loans outstanding and delinquency context; `/api/branches/SOUTHPORT/loans` supports existing CRE exposure; `/api/branches/SOUTHPORT/applications` supplies `SOU-APP-001` through `SOU-APP-006` plus planted records `SOU-APP-901` and `SOU-APP-902`; `/api/policies` supplies stress and capacity/concentration conventions.

Solution and evaluation basis: Existing CRE exposure is `5359170.57`, existing concentration is `0.3289`, and the CRE policy limit is `0.2500`. Full booking of `SOU-APP-901` would produce CRE concentration `0.4087`, or `1587.36` bps over policy, so the correct path is `participation_required`. CRE dual stress gives stressed DSCR `1.18`, so the credit quality is strong enough but concentration requires participation. The answer retains `450891.35` of the CRE loan, approves `SOU-APP-902`, conditionally approves `SOU-APP-003`, and declines `SOU-APP-001`, `SOU-APP-002`, `SOU-APP-004`, `SOU-APP-005`, and `SOU-APP-006`. Committed bank capacity is `1517281.63` and remaining capacity is `3782718.37`.

Scoring: The evaluator uses nine exact-match points with raw weights: SP001 CRE recommendation/participation for `SOU-APP-901` weight 3; SP002 stressed DSCR and post-participation concentration weight 2; SP003 approved set weight 2; SP004 conditional set weight 2; SP005 declined set weight 2; SP006 framework selection for consumer/residential/C&I/SBA weight 2; SP007 committed and remaining capacity weight 2; SP008 low-FICO consumer decline reason weight 1; SP009 C&I approval conditions weight 2.

Transfer design: Important anchors are `train_005` for CRE weighted decision posture, stress arithmetic, and concentration-aware participation, and `train_002` for mixed-queue allocation, SBA net-exposure treatment, NESDCAP framework assignment for consumer/residential loans, controlled decline reasons, and C&I approval conditions. Transfer-dependent difficulty is concentrated in SP001, SP002, SP006, SP007, SP008, and SP009; task-specific exploration is needed to identify Southport application IDs and exact amounts.

Construction record: Author `test_005` task-builder worker. Created and updated 2026-06-03. Major change: completed minimum viable task files, answer, and exact-match evaluator.

# 中文说明

数据来源：本隐藏说明对应 `SCN_011_bank_branch_credit_risk_lending_committee` 的 `test_005`，源示例为 `E001`、`E002` 和 `E003`。任务只使用共享公开环境中的 `SOUTHPORT` 分行数据，包括分行额度、CRE 限额、季度指标、行业敞口、申请队列、政策和基准数据。任务本地仅有答案模板。

任务定义与场景匹配：求解者需要为 CRE 已经偏高的 Southport 分行制作贷款委员会 JSON 决策矩阵。该任务结合申请框架选择、CRE 压力测试、集中度约束、额度分配以及受控决策和拒绝原因，符合本任务组的信贷委员会工作流。

材料地图：`/api/branches/SOUTHPORT` 提供额度和 CRE 政策限额；`/api/branches/SOUTHPORT/metrics` 提供总贷款和逾期背景；`/api/branches/SOUTHPORT/loans` 用于计算现有 CRE 敞口；`/api/branches/SOUTHPORT/applications` 提供申请队列；`/api/policies` 提供压力和集中度惯例。

答案与评估依据：现有 CRE 敞口为 `5359170.57`，现有集中度为 `0.3289`，CRE 限额为 `0.2500`。若全额入账 `SOU-APP-901`，CRE 集中度为 `0.4087`，比政策高 `1587.36` 个基点，因此正确路径是 `participation_required`。CRE 压力 DSCR 为 `1.18`，说明信用质量可接受，但集中度要求参与安排。答案保留 CRE 银行敞口 `450891.35`，批准 `SOU-APP-902`，有条件批准 `SOU-APP-003`，拒绝 `SOU-APP-001`、`SOU-APP-002`、`SOU-APP-004`、`SOU-APP-005` 和 `SOU-APP-006`。占用额度为 `1517281.63`，剩余额度为 `3782718.37`。

迁移设计：`train_005` 是 CRE 压力、集中度和参与安排的锚点；`train_002` 是混合队列分配、SBA 净敞口、NESDCAP 框架、受控拒因和 C&I 条件的锚点。高价值评分点依赖这些训练任务中归纳出的经验，同时仍需针对 Southport 数据做具体检索和计算。
