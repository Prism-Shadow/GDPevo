# train_004 Hidden Notes

## English

### Data lineage and task definition

This task belongs to `SCN_024_engineering_portfolio_work_item_analytics`, based on source examples `E001`, `E002`, and `E003`, and implements the portfolio-mix family described in `scratch/task_group_design.md`. The construction data comes from the generated shared environment database `task_group/task_group_024/env/portfolio.db`. The target row is `mix_targets.scope_id = train_004`, with quarter `2025-Q4`, team group `Mobile Client + Growth Experiences`, product area `Checkout`, and target percentages NewFeature 42.0, TechDebt 20.0, Reliability 24.0, Security 14.0.

The solver-visible task asks for a Q4 2025 Checkout portfolio-mix readout for teams `Mobile Client` and `Growth Experiences`. Solvers must use the environment endpoints or restricted SQL query access supplied at runtime and return only the JSON shape defined in `input/payloads/answer_template.json`.

### Scenario fit and material map

The task models a real engineering-operations workflow: portfolio analysts gather work items, apply portfolio inclusion and classification conventions, compare actual execution mix to target investment mix, and recommend a capacity rebalance. The important environment objects are:

- `work_items`: source of item ids, teams, product areas, statuses, close dates, duplicate references, titles, work types, labels, stale mirror fields, and legacy categories.
- `mix_targets`: source of the expected target allocation for `scope_id = train_004`.
- `input/prompt.txt`: solver-facing business request, intentionally high-level and not a worked SOP.
- `input/payloads/answer_template.json`: exact output contract, category order, enum choices, and one-decimal percentage precision.
- `output/answer.json`: standard answer constructed from the database.
- `eval/eval.py` and `eval/eval.sh`: deterministic raw whole-point evaluator.

### Solution and evaluation basis

Primary inclusion uses work items with `closed_at` from 2025-10-01 through 2025-12-31 inclusive, `team` in `Mobile Client` or `Growth Experiences`, `product_area = Checkout`, `status` in `Done`, `Verified`, `Deployed`, or `Closed`, no `duplicate_of`, and no `Cancelled` or `Duplicate` status. Same-scope Q4 distractors excluded from primary counting because of `Cancelled`, `Duplicate`, or `duplicate_of` are tracked separately.

Category precedence is Security, then Reliability, then TechDebt, then NewFeature. Security applies when `work_type` is `Security` or `Compliance`, or labels/title contain `security`, `cve`, `auth`, `encryption`, or `compliance`. Reliability applies when `work_type` is `Reliability` or `Incident`, or labels/title contain `reliability`, `incident`, `outage`, `latency`, or `flaky`. TechDebt applies when `work_type` is `Refactor`, `Chore`, or `Dependency`, or labels/title contain `refactor`, `migration`, `cleanup`, or `dependency`. NewFeature is the fallback. This precedence matters for `WI-24024-P022` (`auth` makes it Security), `WI-24024-P021` (`reliability` outranks `cleanup`), and `WI-24024-P024` (`migration`/`cleanup` makes it TechDebt despite feature labels).

Included ids are `WI-24024-P021`, `WI-24024-007`, `WI-24024-P022`, `WI-24024-P023`, `WI-24024-P024`, `WI-24024-P025`, `WI-24024-P026`, `WI-24024-P027`, and `WI-24024-P028`. Counts are NewFeature 1, TechDebt 1, Reliability 4, Security 3. With total 9, actual percentages are 11.1, 11.1, 44.4, and 33.3. Gaps are actual percentage minus target percentage: NewFeature -30.9, TechDebt -8.9, Reliability 20.4, Security 19.3. The largest deficit is NewFeature. The recommended action is `REBALANCE_CAPACITY` for NewFeature owned by `Growth Experiences`, because Growth Experiences owns the only included NewFeature record and is the natural team to restore Checkout growth-feature investment.

Excluded distractors are `WI-24024-P029` (`Duplicate` and `duplicate_of = WI-24024-P027`), `WI-24024-P030` (`Cancelled` with stale `mirror_status = Done`), and `WI-24024-P031` (`duplicate_of = WI-24024-P024` despite `status = Closed`).

The rubric has six whole-point scoring goals totaling 12 raw points:

- Included work item set, weight 3.
- Category counts, weight 3.
- Complete percentage and gap table, weight 2.
- Largest deficit category, weight 2.
- Recommended action owner team, weight 1.
- Excluded distractor set, weight 1.

Likely model pitfalls are counting stale mirror status instead of canonical status, using `legacy_category`, missing `auth`/`cve` security precedence, letting `cleanup` override reliability/security too early, treating duplicate records as primary work, or calculating percentages from story points instead of counts.

### Transfer design

As a train task, `train_004` reinforces transferable portfolio-mix conventions also needed by the test portfolio tasks: quarter closed-date boundaries, canonical status over stale mirror fields, duplicate exclusion, target lookup by `scope_id`, category precedence from work type plus labels/title, count-based one-decimal percentages, and action selection from the most negative gap. It is not a tutorial in the prompt, but comparing attempts to the standard answer can teach the hidden SOP and common data traps.

### Construction record

Author: Codex task-builder worker. Created: 2026-07-18. Updated: 2026-07-18. Major changes: created prompt, schema template, standard answer, bilingual hidden notes, and whole-point evaluator for `train_004`.

## 中文

### 数据来源和任务定义

本任务属于 `SCN_024_engineering_portfolio_work_item_analytics`，来源示例为 `E001`、`E002`、`E003`，实现 `scratch/task_group_design.md` 中的组合投入结构分析任务族。构造数据来自共享环境数据库 `task_group/task_group_024/env/portfolio.db`。目标行是 `mix_targets.scope_id = train_004`，季度为 `2025-Q4`，团队组为 `Mobile Client + Growth Experiences`，产品域为 `Checkout`，目标比例为 NewFeature 42.0、TechDebt 20.0、Reliability 24.0、Security 14.0。

求解者可见任务要求为 `Mobile Client` 和 `Growth Experiences` 两个团队生成 2025 年第四季度 Checkout 产品域的组合投入结构读数。求解者应通过运行时提供的环境端点或受限 SQL 查询访问数据，并只返回 `input/payloads/answer_template.json` 定义的 JSON 结构。

### 场景适配和材料地图

该任务模拟真实工程运营流程：组合分析人员收集工作项，应用组合口径的纳入和分类规则，将实际执行结构与目标投入结构比较，并提出容量再平衡建议。关键材料包括：

- `work_items`：提供工作项 id、团队、产品域、状态、关闭日期、重复项引用、标题、工作类型、标签、过期镜像字段和旧分类。
- `mix_targets`：提供 `scope_id = train_004` 的目标投入比例。
- `input/prompt.txt`：求解者可见的业务请求，保持高层描述，不写成标准答案步骤。
- `input/payloads/answer_template.json`：输出契约、分类顺序、枚举值和一位小数百分比精度。
- `output/answer.json`：由数据库构造出的标准答案。
- `eval/eval.py` 和 `eval/eval.sh`：确定性的整数原始分评测器。

### 解答和评测依据

主要纳入口径为：`closed_at` 在 2025-10-01 到 2025-12-31 之间且包含边界，`team` 为 `Mobile Client` 或 `Growth Experiences`，`product_area = Checkout`，`status` 为 `Done`、`Verified`、`Deployed` 或 `Closed`，`duplicate_of` 为空，并且状态不是 `Cancelled` 或 `Duplicate`。同范围、同季度中因为 `Cancelled`、`Duplicate` 或 `duplicate_of` 被排除的干扰项需要单独记录。

分类优先级为 Security、Reliability、TechDebt、NewFeature。`work_type` 为 `Security` 或 `Compliance`，或标签/标题包含 `security`、`cve`、`auth`、`encryption`、`compliance` 时归为 Security。`work_type` 为 `Reliability` 或 `Incident`，或标签/标题包含 `reliability`、`incident`、`outage`、`latency`、`flaky` 时归为 Reliability。`work_type` 为 `Refactor`、`Chore` 或 `Dependency`，或标签/标题包含 `refactor`、`migration`、`cleanup`、`dependency` 时归为 TechDebt。否则归为 NewFeature。该优先级影响 `WI-24024-P022`、`WI-24024-P021` 和 `WI-24024-P024` 等冲突记录。

纳入的 id 为 `WI-24024-P021`、`WI-24024-007`、`WI-24024-P022`、`WI-24024-P023`、`WI-24024-P024`、`WI-24024-P025`、`WI-24024-P026`、`WI-24024-P027`、`WI-24024-P028`。计数为 NewFeature 1、TechDebt 1、Reliability 4、Security 3。总数为 9，因此实际比例为 11.1、11.1、44.4、33.3。差距等于实际比例减目标比例：NewFeature -30.9、TechDebt -8.9、Reliability 20.4、Security 19.3。最大短缺类别是 NewFeature。建议动作为 `REBALANCE_CAPACITY`，类别为 NewFeature，负责人团队为 `Growth Experiences`，因为该团队拥有唯一纳入的 NewFeature 记录，也是恢复 Checkout 增长功能投入的自然责任团队。

排除的干扰项为 `WI-24024-P029`、`WI-24024-P030` 和 `WI-24024-P031`。它们分别因为重复状态和重复引用、取消状态但镜像字段显示 Done、以及虽然状态为 Closed 但有重复引用而不计入主要组合。

评测共六个整数原始分目标，总分 12：

- 纳入工作项集合，权重 3。
- 分类计数，权重 3。
- 百分比和差距表，权重 2。
- 最大短缺类别，权重 2。
- 建议动作的负责人团队，权重 1。
- 排除干扰项集合，权重 1。

常见错误包括使用 stale mirror status 而不是规范 status，使用 `legacy_category`，忽略 `auth` 或 `cve` 的安全优先级，让 `cleanup` 过早覆盖可靠性或安全分类，把重复记录计入主要工作项，或用 story points 而不是数量计算百分比。

### 迁移设计

作为训练任务，`train_004` 强化组合投入分析中可迁移的口径：季度关闭日期边界、规范状态优先于镜像字段、重复项排除、按 `scope_id` 查目标、根据工作类型和标签/标题做优先级分类、按数量计算一位小数百分比、以及根据最大负差距选择行动。提示本身不是教程，但通过对比尝试答案和标准答案，模型可以学习隐藏 SOP 和常见数据陷阱。

### 构造记录

作者：Codex task-builder worker。创建日期：2026-07-18。更新日期：2026-07-18。主要变更：为 `train_004` 创建提示、模板、标准答案、双语隐藏说明和整数分评测器。
