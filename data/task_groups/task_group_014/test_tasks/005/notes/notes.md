# test_005 Notes: Rehab margin and authorization leakage review

## English

### Purpose

This formal test task asks an outpatient rehab director to prepare a 2025 margin and authorization leakage review through the shared SQL service. It is not a tutorial: solver-visible files provide only the role, business goal, SQL endpoint, target scope, and required output shape.

### Data lineage

The construction-visible manifest identifies the profitability focus as `CLN002`, `CLN004`, `Medicare Advantage`, and `Exchange`. The solver-facing analysis scope narrows the service set to outpatient rehab-adjacent categories:

- `Evaluation Management`
- `Pain Management`
- `Physical Therapy`

The canonical answer is derived from `encounters`, `clinic_costs`, `clinic_budgets`, and `claim_corrections`. Authorization leakage is tied to encounter denial code `CO-197` and correction type `authorization addendum`.

### Solution basis

The analysis period is calendar year 2025. Scored cells are the 12 clinic-plan-service combinations formed by two clinics, two plan types, and three service categories.

Financial derivation:

- Paid amount is summed from `encounters.paid_amount`.
- Open recovery uses only `claim_corrections.status = 'open'`.
- Net revenue is paid amount plus open recovery.
- Cost per unit is `clinic_costs.direct_cost_per_unit + clinic_costs.allocated_overhead_per_unit`.
- Total cost is units multiplied by cost per unit.
- Net margin is net revenue minus total cost.
- Margin percent is net margin divided by net revenue.
- Budget margin percent is the maximum 2025 `clinic_budgets.expected_margin_pct` for the same clinic and service category.
- Projected improvement after recovery is the additional net revenue required for a shortfall cell to reach its budget margin threshold after open recoveries have already been included: `total_cost / (1 - budget_margin_pct) - net_revenue`.

Classification and action basis:

- `major_shortfall` means margin percent is more than 0.05 below the budget margin percent.
- `on_or_above_budget` means margin percent is at or above the budget margin percent.
- Shortfall cells with at least five encounters are `persistent`; acceptable cells are `acceptable`.
- An action cell with any authorization-linked encounter uses `authorization_leakage_review`; other shortfall cells use `rate_floor_review`; acceptable cells use `no_action`.
- Authorization leakage amount is the expected recovery amount attached to authorization-addendum corrections or CO-197 encounters when such an amount exists. Authorization leakage encounter count also counts CO-197 denials with no recoverable correction amount.

Expected high-level results:

- The top loss driver is `CLN004` Medicare Advantage Physical Therapy.
- Eight of 12 cells require action.
- Four Pain Management cells are acceptable and excluded from action.
- Total net margin across the scoped portfolio is `-6100.34`.
- Total projected improvement after open recoveries is `92583.16`.
- Total authorization leakage amount is `1783.68` across eight authorization-linked encounters.

### Transfer anchors

- `train_005`: transfers the margin formula, open-recovery inclusion, budget threshold comparison, loss-driver ranking, and controlled payer action habits.
- `train_004`: transfers encounter aggregation discipline, correction-status treatment, and avoiding row multiplication when joining to budget/reference data.
- `train_001`: transfers authorization-denial interpretation as an operational leakage source rather than a pure rate issue.

### Scoring goals

The evaluator uses seven exact-match structured business-result points with raw weights 3, 2, 2, 2, 2, 1, and 1:

- margin metrics for all 12 payer-service cells;
- top three loss-driver ranking;
- authorization leakage amounts and counts;
- corrective action enum for flagged cells;
- projected improvement after recoveries/actions;
- persistent versus acceptable classification;
- acceptable cells excluded from action.

### Construction record

The construction-visible SQLite database was inspected directly to compute the canonical answer. Solver-visible prompt files disclose the fixed synthetic Basic Auth credentials for `<TASK_ENV_BASE_URL>/query`, while prompt and payload files do not include localhost, runtime ports, detailed scoring logic, or hidden answer paths.

## 中文

### 目的

这个正式测试任务要求门诊康复负责人通过共享 SQL 服务准备 2025 年利润率和授权泄漏复核。它不是教程：面向求解者的文件只提供角色、业务目标、SQL 端点、目标范围和输出格式。

### 数据来源

构建可见的 manifest 将盈利分析重点标为 `CLN002`、`CLN004`、`Medicare Advantage` 和 `Exchange`。面向求解者的分析范围进一步限定为门诊康复相关服务类别：

- `Evaluation Management`
- `Pain Management`
- `Physical Therapy`

标准答案来自 `encounters`、`clinic_costs`、`clinic_budgets` 和 `claim_corrections`。授权泄漏与 encounter 拒付代码 `CO-197` 以及 correction 类型 `authorization addendum` 相关。

### 解题依据

分析期间为 2025 全年。评分单元是两个诊所、两个计划类型和三个服务类别组成的 12 个诊所-计划-服务组合。

财务计算依据：

- 已付金额来自 `encounters.paid_amount` 汇总。
- 开放追回只纳入 `claim_corrections.status = 'open'`。
- 净收入等于已付金额加开放追回。
- 单位成本等于 `clinic_costs.direct_cost_per_unit + clinic_costs.allocated_overhead_per_unit`。
- 总成本等于单位数乘以单位成本。
- 净利润等于净收入减总成本。
- 利润率等于净利润除以净收入。
- 预算利润率使用同一诊所、服务类别、2025 年的 `clinic_budgets.expected_margin_pct` 最大值。
- 回收后预计改善额表示短缺单元在已纳入开放追回后达到预算利润率所需的额外净收入：`total_cost / (1 - budget_margin_pct) - net_revenue`。

分类和行动依据：

- `major_shortfall` 表示利润率比预算利润率低超过 0.05。
- `on_or_above_budget` 表示利润率达到或超过预算利润率。
- 至少 5 条 encounter 的短缺单元为 `persistent`；可接受单元为 `acceptable`。
- 存在任何授权相关 encounter 的行动单元使用 `authorization_leakage_review`；其他短缺单元使用 `rate_floor_review`；可接受单元使用 `no_action`。
- 授权泄漏金额来自授权补充 correction 或 CO-197 encounter 上存在的预期追回金额。授权泄漏 encounter 计数也包括没有可追回 correction 金额的 CO-197 拒付。

预期高层结果：

- 最大亏损驱动是 `CLN004` Medicare Advantage Physical Therapy。
- 12 个单元中有 8 个需要行动。
- 4 个 Pain Management 单元可接受并排除在行动之外。
- 范围内组合总净利润为 `-6100.34`。
- 纳入开放追回后的总预计改善额为 `92583.16`。
- 授权泄漏总金额为 `1783.68`，涉及 8 个授权相关 encounter。

### 迁移锚点

- `train_005`：迁移利润率公式、开放追回纳入、预算阈值比较、亏损驱动排序和受控付款方行动习惯。
- `train_004`：迁移 encounter 聚合、更正状态处理，以及连接预算或参考数据时避免行数膨胀。
- `train_001`：迁移将授权拒付理解为运营泄漏来源，而不是单纯费率问题。

### 评分目标

评估器使用七个精确匹配的结构化业务结果评分点，原始权重为 3、2、2、2、2、1 和 1：

- 全部 12 个付款方-服务单元的利润指标；
- 前三大亏损驱动排序；
- 授权泄漏金额和计数；
- 被标记单元的纠正行动枚举；
- 回收和行动后的预计改善额；
- 持续性与可接受分类；
- 因利润率可接受而排除行动的单元。

### 构建记录

构建时直接检查了 construction-visible SQLite 数据库来计算标准答案。面向求解者的 prompt 文件公开访问 `<TASK_ENV_BASE_URL>/query` 所需的固定合成 Basic Auth 凭据；prompt 和 payload 文件不包含 localhost、运行时端口、详细评分逻辑或隐藏答案路径。
