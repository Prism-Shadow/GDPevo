# Run Scope

## Purpose

This experiment analyzes cross-task transfer of existing skills.

It fixes three representative task groups:

| Label | Task group | Scenario |
| --- | --- | --- |
| CRM | `task_group_002` | `SCN_002_crm_b2b_quote_account_response` |
| ERP | `task_group_006` | `SCN_006_erp_procurement_supplier_receiving` |
| Finance | `task_group_010` | `SCN_010_institutional_investment_strategy_portfolio_risk` |

Rows and columns use this same order.

## Conditions

Run only:

```text
fewshot
reflect-3
```

Run only:

```text
harness: codex
```

Do not run:

```text
base
self
claude_code
panofy
```

## @3 Definition

Each `@3` must come from 3 existing independently generated skills for the same
source task group:

```text
skills/<mode>/<source_task_group_id>/<mode>_attempt_01/SKILL.md
skills/<mode>/<source_task_group_id>/<mode>_attempt_02/SKILL.md
skills/<mode>/<source_task_group_id>/<mode>_attempt_03/SKILL.md
```

For one off-diagonal matrix cell `<source> -> <target>` where source and target
are different task groups:

1. Use the 3 skills under `<source>` for the selected mode.
2. Let the `attempt_01` solver use the `attempt_01` skill to solve every test
   task in `<target>`.
3. Let the `attempt_02` solver use the `attempt_02` skill for the same target
   test tasks.
4. Let the `attempt_03` solver use the `attempt_03` skill for the same target
   test tasks.
5. Each target test task receives 3 scores. Compute that task's `acc@3` and
   population `std@3`.
6. The cell `acc@3` is the average of the 5 target test-task `acc@3` values.
7. The cell `std@3` is the average of the 5 target test-task `std@3` values.

The 3 attempts are not reruns of the same skill. They must use 3 independent
pre-generated skills from the same source task group.

Diagonal cells where source and target are the same task group are not run.

## Matrix Cells

Each mode has 6 scored cells. The 3 diagonal cells are not run:

```text
task_group_002 -> task_group_006
task_group_002 -> task_group_010
task_group_006 -> task_group_002
task_group_006 -> task_group_010
task_group_010 -> task_group_002
task_group_010 -> task_group_006
```

`fewshot` and `reflect-3` together produce 12 scored cells.

## Remote Environment

`.env` should use one environment variable per task group:

```text
GDPEVO_TASK_GROUP_002_ENV_BASE_URL=<remote env for task_group_002>
GDPEVO_TASK_GROUP_006_ENV_BASE_URL=<remote env for task_group_006>
GDPEVO_TASK_GROUP_010_ENV_BASE_URL=<remote env for task_group_010>
```

Test solvers use the target task group's remote environment.
