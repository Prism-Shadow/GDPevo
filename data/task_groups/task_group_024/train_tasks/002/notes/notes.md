# train_002 Notes

## English

### Data and Source Lineage

This task belongs to source scenario `SCN_024_engineering_portfolio_work_item_analytics`, using the SLA-aging pattern from source example `E002` and the shared task-group conventions documented for `task_group_024`. The construction data is the generated SQLite database at `task_group/task_group_024/env/portfolio.db`, especially the `work_items` and `sla_policy` tables. The solver-visible payload is `input/payloads/answer_template.json`; the standard answer is `output/answer.json`; the deterministic evaluator is `eval/eval.py`.

### Task Definition

The business question is an SLA aging review for reliability and security work owned by `Infra Reliability` and `Data Platform` as of `2026-01-15`, with recently closed work included for a 14-day lookback. The expected output identifies included primary work item IDs, overdue primary IDs, aging bucket counts, overdue counts by team, the top owner/team hotspot, duplicate clusters, missing-owner primary IDs, and the breach rate. The prompt intentionally asks solvers to use portfolio category conventions and SLA aging judgment without exposing the full hidden construction procedure.

### Scenario Fit

The task represents a common engineering operations workflow: combining effective work-item state, category classification, due-date comparisons, duplicate handling, and owner/team rollups into an SLA risk summary. It fits the task group because it requires data exploration over the shared portfolio environment and uses the same recurring operational objects as the broader scenario: work items, owners, teams, statuses, due dates, closed dates, labels, and severity metadata.

### Material Map

- `work_items`: source of IDs, title/type/labels for category resolution, status, team, owner, created/due/closed dates, and duplicate links.
- `sla_policy`: available environment policy table; useful context for SLA work, though this task scores due-date aging directly from work-item records.
- `/api/work-items`, `/api/sla-policy`, and `/api/query`: solver-accessible routes for retrieving the same data through the runtime service.
- `input/prompt.txt`: visible business request and output ordering requirements.
- `input/payloads/answer_template.json`: exact JSON schema, field types, precision, and ordering rules.
- `output/answer.json`: gold answer constructed from the database.
- `eval/eval.py`: whole-point evaluator for the nine rubric outcomes.

### Solution and Evaluation Basis

Category classification follows the task-group portfolio precedence: `Security` before `Reliability` before `TechDebt` before `NewFeature`, using work type, labels, and title signals. SLA-relevant categories are `Security` and `Reliability`. The effective as-of population includes records in the two scoped teams that existed by `2026-01-15` and are either open (`Backlog`, `In Progress`, `Review`, `Reopened` with no `closed_at`) or recently closed in the inclusive `2026-01-01` to `2026-01-15` window. Primary metrics exclude `Cancelled`, `Duplicate`, and any record with `duplicate_of` set. Duplicate records are reported as clusters when their dates and category/team scope otherwise place them in the SLA review.

The included primary IDs are `WI-24024-022`, `WI-24024-089`, `WI-24024-095`, `WI-24024-S001`, `WI-24024-S002`, `WI-24024-S003`, `WI-24024-S004`, `WI-24024-S005`, `WI-24024-S006`, `WI-24024-S007`, and `WI-24024-S008`. The overdue primary IDs are `WI-24024-089`, `WI-24024-095`, `WI-24024-S001`, `WI-24024-S002`, `WI-24024-S004`, and `WI-24024-S006`. Aging uses `as_of - created_at` for open records and `closed_at - created_at` for recently closed records, producing bucket counts `0-3: 1`, `4-7: 1`, `8-14: 7`, `15-30: 0`, and `31+: 2`. The breach rate is `6 / 11 = 0.545` rounded to three decimals.

Rubric weights are: seeded primary set 2, legacy primary set 1, duplicate exclusion from the primary set 1, overdue set 3, aging bucket counts 2, team hotspot 2, duplicate clusters 1, missing-owner IDs 1, and breach rate 2, for a raw total of 15. These cover distinct outcomes: population construction across seeded and legacy records, duplicate hygiene in the primary denominator, deadline breach identification, aging analytics, operational hotspot rollup, duplicate reporting, ownership risk, and aggregate SLA rate. Each scoring point is all-or-zero. Likely pitfalls include using `mirror_status` or `legacy_category`, including future-created open records, treating same-day due dates as overdue, counting duplicate rows as primary items, excluding noisy-but-valid generated distractors that match the category rules, or calculating closed-item aging against the as-of date instead of `closed_at`.

### Transfer Design

As a train task, this example teaches transferable SLA-aging conventions for the task group: how open and recently closed records combine into one effective review population, how portfolio category precedence carries into SLA scopes, how due-date boundaries differ for open versus closed records, how duplicates are excluded from primary metrics but still reported, and how owner/team risk should be rolled up. Solvers can infer that future test SLA tasks will preserve these conventions while changing teams, dates, lookback windows, and the exact noisy distractor records.

### Construction Record

Author: Codex task builder. Created: 2026-07-18. Updated: 2026-07-18. Major changes: created the full train_002 task directory, constructed the gold answer from `portfolio.db`, defined the solver-visible template, and implemented the weighted evaluator.

## 中文

### 数据和来源

本任务属于来源场景 `SCN_024_engineering_portfolio_work_item_analytics`，采用来源示例 `E002` 的 SLA 老化分析模式，并遵循 `task_group_024` 的共享约定。构造数据来自生成的 SQLite 数据库 `task_group/task_group_024/env/portfolio.db`，主要使用 `work_items` 和 `sla_policy` 表。求解器可见的结构模板是 `input/payloads/answer_template.json`，标准答案是 `output/answer.json`，确定性评分器是 `eval/eval.py`。

### 任务定义

业务问题是在 `2026-01-15` 这个观察日，对 `Infra Reliability` 和 `Data Platform` 两个团队的可靠性与安全工作做 SLA 老化审查，并纳入最近 14 天关闭的工作。期望输出包括主要工作项 ID、逾期主要工作项 ID、老化桶计数、按团队统计的逾期数、最高 owner/team 热点、重复记录簇、缺少 owner 的主要工作项 ID，以及 SLA breach rate。提示词只要求使用组合分类和 SLA 判断，不向求解器暴露完整隐藏构造步骤。

### 场景契合度

该任务模拟工程运营中的常见流程：把工作项有效状态、类别判定、到期日比较、重复项处理、owner/team 汇总组合成 SLA 风险摘要。它符合本任务组，因为它需要探索共享组合环境中的数据，并使用工作项、owner、团队、状态、到期日、关闭日、标签和严重级别等共同对象。

### 材料映射

- `work_items`：提供 ID、title/type/labels、status、team、owner、created/due/closed 日期和 duplicate 关系。
- `sla_policy`：环境中的 SLA 策略表；本任务评分主要依据工作项自身的 due date 老化结果。
- `/api/work-items`、`/api/sla-policy`、`/api/query`：运行时可用于检索同一数据的接口。
- `input/prompt.txt`：求解器可见的业务请求和排序要求。
- `input/payloads/answer_template.json`：精确 JSON 结构、字段类型、精度和排序规则。
- `output/answer.json`：从数据库构造的标准答案。
- `eval/eval.py`：九个评分目标的整点评分器。

### 解答与评分依据

类别分类遵循任务组组合优先级：`Security` 高于 `Reliability`，再高于 `TechDebt` 和 `NewFeature`，并综合 work type、labels 和 title 信号。SLA 相关类别是 `Security` 和 `Reliability`。截至 `2026-01-15` 的有效集合包括两个目标团队中已经存在的记录，并且状态为 open 状态且无 `closed_at`，或在 `2026-01-01` 到 `2026-01-15` 闭区间内关闭。主要指标排除 `Cancelled`、`Duplicate` 和设置了 `duplicate_of` 的记录。重复记录如果日期、类别和团队范围仍然匹配审查范围，则作为 duplicate cluster 报告，但不计入主要 SLA 指标。

主要工作项 ID 为 `WI-24024-022`、`WI-24024-089`、`WI-24024-095`、`WI-24024-S001`、`WI-24024-S002`、`WI-24024-S003`、`WI-24024-S004`、`WI-24024-S005`、`WI-24024-S006`、`WI-24024-S007` 和 `WI-24024-S008`。逾期主要工作项 ID 为 `WI-24024-089`、`WI-24024-095`、`WI-24024-S001`、`WI-24024-S002`、`WI-24024-S004` 和 `WI-24024-S006`。open 记录的老化天数使用 `as_of - created_at`，最近关闭记录使用 `closed_at - created_at`，得到桶计数 `0-3: 1`、`4-7: 1`、`8-14: 7`、`15-30: 0`、`31+: 2`。breach rate 为 `6 / 11 = 0.545`，保留三位小数。

评分权重为：seeded primary set 2，legacy primary set 1，primary 中排除 duplicate 1，逾期集合 3，老化桶 2，团队热点 2，重复簇 1，缺少 owner 的 ID 1，breach rate 2，原始总分 15。这些覆盖不同业务结果：seeded 与 legacy 记录共同组成的集合构造、主要分母中的重复项治理、逾期识别、老化分析、运营热点、重复项报告、owner 风险和汇总 SLA 比率。每个评分点都是整点通过或失败。常见错误包括使用 `mirror_status` 或 `legacy_category`，纳入观察日之后才创建的 open 记录，把 same-day due 当成逾期，把重复记录计入主要指标，漏掉符合类别规则的噪声记录，或对最近关闭记录使用 as-of 日期而不是 `closed_at` 计算老化。

### 迁移设计

作为训练任务，本例提供可迁移的 SLA 老化约定：open 和最近关闭记录如何组合为一个有效审查集合，组合分类优先级如何迁移到 SLA 范围，到期比较如何因 open/closed 状态而不同，重复项如何排除于主要指标但仍需报告，以及 owner/team 风险如何汇总。求解器可以推断未来测试中的 SLA 任务会保留这些约定，但会改变团队、日期、lookback 窗口和具体噪声记录。

### 构造记录

作者：Codex task builder。创建日期：2026-07-18。更新日期：2026-07-18。主要变更：创建完整的 train_002 任务目录，从 `portfolio.db` 构造标准答案，定义求解器可见模板，并实现加权评分器。
