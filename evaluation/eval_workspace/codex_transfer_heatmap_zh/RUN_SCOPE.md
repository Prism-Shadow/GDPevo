# Run Scope

## Purpose

本实验分析 skill 在跨 task group 使用时的可迁移性。

固定 3 个代表 task group：

| Label | Task group | Scenario |
| --- | --- | --- |
| CRM | `task_group_002` | `SCN_002_crm_b2b_quote_account_response` |
| ERP | `task_group_006` | `SCN_006_erp_procurement_supplier_receiving` |
| Finance | `task_group_010` | `SCN_010_institutional_investment_strategy_portfolio_risk` |

矩阵行列都按上表顺序排列。

## Conditions

只运行：

```text
fewshot
reflect-3
```

只运行：

```text
harness: codex
```

不运行：

```text
base
self
claude_code
panofy
```

## @3 Definition

每个 `@3` 必须来自同一个 source task group 的 3 个既有独立 skill：

```text
skills/<mode>/<source_task_group_id>/<mode>_attempt_01/SKILL.md
skills/<mode>/<source_task_group_id>/<mode>_attempt_02/SKILL.md
skills/<mode>/<source_task_group_id>/<mode>_attempt_03/SKILL.md
```

对一个 source 和 target 不同的矩阵单元格 `<source> -> <target>`：

1. 取 `<source>` 下对应 mode 的 3 个 skill。
2. 让 `attempt_01` solver 使用 `attempt_01` skill，求解 `<target>` 的每道 test task。
3. 让 `attempt_02` solver 使用 `attempt_02` skill，求解同一批 target test tasks。
4. 让 `attempt_03` solver 使用 `attempt_03` skill，求解同一批 target test tasks。
5. 每道 target test task 得到 3 个 score，先算该题 `acc@3` 和 population `std@3`。
6. 单元格 `acc@3` 是 5 道 target test tasks 的 `acc@3` 平均值。
7. 单元格 `std@3` 是 5 道 target test tasks 的 `std@3` 平均值。

注意：这里的 3 次 attempt 不是同一个 skill 重跑三次，而是 3 个既有独立 skill。

source 和 target 相同的主对角线单元格不跑。

## Matrix Cells

每个 mode 有 6 个需要评分的单元格，3 个主对角线单元格不跑：

```text
task_group_002 -> task_group_006
task_group_002 -> task_group_010
task_group_006 -> task_group_002
task_group_006 -> task_group_010
task_group_010 -> task_group_002
task_group_010 -> task_group_006
```

`fewshot` 和 `reflect-3` 共 12 个需要评分的单元格。

## Remote Environment

`.env` 应使用每个 task group 单独的环境变量：

```text
GDPEVO_TASK_GROUP_002_ENV_BASE_URL=<remote env for task_group_002>
GDPEVO_TASK_GROUP_006_ENV_BASE_URL=<remote env for task_group_006>
GDPEVO_TASK_GROUP_010_ENV_BASE_URL=<remote env for task_group_010>
```

test solver 使用 target task group 的远程环境。
