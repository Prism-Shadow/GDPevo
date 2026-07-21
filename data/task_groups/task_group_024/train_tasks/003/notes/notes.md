# train_003 Hidden Notes

## English

### Data and Source Lineage

This task belongs to `SCN_024_engineering_portfolio_work_item_analytics`, based on the engineering operations source examples `E001`, `E002`, and especially `E003`. The task design brief assigns `train_003` to the release-readiness family for release `REL-ORION-2026-02`. The construction data comes from `task_group/task_group_024/env/portfolio.db`; no task-local business data payload is added beyond `input/payloads/answer_template.json`.

The relevant generated tables are `releases`, `milestones`, `work_items`, `blockers`, and `dependencies`. The environment exposes these through `/api/releases`, `/api/milestones`, `/api/work-items`, `/api/blockers`, `/api/dependencies`, and `/api/query`.

### Task Definition and Scenario Fit

The visible prompt asks the solver to assess whether the Orion February release train is ready to ship. The expected output is a structured JSON readiness summary with a ship decision, milestone completion metrics, non-complete gating work, blocker cause counts, dependency chains, and an aggregate readiness score.

This matches the task group because release readiness requires joining portfolio work items to milestones, blocker records, and dependency relationships. It exercises the release operations workflow represented by source example `E003`: identify the authoritative release scope, remove non-primary work from milestone denominators, separate completion from adjacent stale fields, propagate unresolved gates, and make a launch decision.

### Material Map

- `input/prompt.txt` gives the business request and the environment base URL placeholder `<TASK_ENV_BASE_URL>`.
- `input/payloads/answer_template.json` defines the exact JSON shape, enum choices, precision, and ordering rules.
- `output/answer.json` is the gold answer derived from `portfolio.db`.
- `eval/eval.py` scores the structured business outcomes with whole raw points.
- `eval/eval.sh` is the command-line entry point and accepts a candidate answer path as `$1`.
- `portfolio.db` provides the authoritative release, milestone, work item, blocker, and dependency rows used for answer construction.

### Solution and Evaluation Basis

Primary release work for `REL-ORION-2026-02` excludes work items with status `Cancelled`, status `Duplicate`, or a non-null `duplicate_of`. The remaining primary denominator has 16 work items. Complete release statuses are `Done`, `Verified`, and `Deployed`; `Closed` is not counted as complete for this release-readiness task. There are 11 complete primary items, so the readiness score is `11 / 16 = 0.688` rounded to three decimals.

Milestone metrics:

- `MIL-ORION-BETA`: 2 complete out of 2 primary, `100.0`.
- `MIL-ORION-GA`: 4 complete out of 6 primary, `66.7`.
- `MIL-ORION-HARDEN`: 3 complete out of 5 primary, `60.0`.
- `MIL-ORION-RC`: 2 complete out of 3 primary, `66.7`.

High-impact unresolved blockers are unresolved blockers with status `Open` or `Monitoring` and severity `Critical` or `High`. Orion has three such blocker causes: `release note evidence gap`, `open reliability rehearsal gap`, and `unresolved cve exception`. Only non-complete primary release items enter the gating work item set, so the high-impact blocker on complete item `WI-24024-008` contributes to blocker cause counts and the ship decision but not to `gating_work_item_ids`. The non-complete high-impact blocker gates are `WI-24024-010` and `WI-24024-012`.

Critical dependency chains are ordered paths from a non-complete blocked release item to a non-complete primary dependency. The Orion dependency rows for the non-complete release work either point to complete items or non-primary items, so the expected `critical_dependency_chains` list is empty. The ship decision is `NO_SHIP` because unresolved high-impact blockers remain.

Scoring uses six whole-point dimensions and a 14 point maximum:

- decision enum, weight 3;
- milestone metrics, weight 3;
- gating work item set, weight 3;
- blocker cause counts, weight 2;
- critical dependency chains, weight 2;
- readiness score, weight 1.

The evaluator normalizes enum casing, set ordering, milestone ordering by id, numeric precision, and blocker-cause objects. Each point is all-or-zero. Likely pitfalls include counting `Duplicate` item `WI-24024-154`, trusting `mirror_status`, treating `Closed` as complete, omitting a high-impact blocker on a completed item from cause counts, or treating complete dependency targets as critical chains.

### Transfer Design

As a train task, this item establishes the release-readiness conventions used by the later Zephyr test task. A solver can infer that release readiness uses authoritative `status`, `release_id`, `milestone_id`, `duplicate_of`, blocker severity/status, and dependency direction rather than stale mirror fields. It also teaches that milestone completion and readiness score use count-based primary denominators, while blockers and dependency gates are related but not identical outputs.

The transferable habits are to query all release-adjacent tables, build a primary work set before aggregating, keep completed-adjacent states separate, count blocker causes independently from gating item ids, and represent dependency chains in blocked-to-dependency order.

### Construction Record

Author: Codex task-builder worker. Created: 2026-07-18. Updated: 2026-07-18. Major changes: created the train task directory, solver prompt, answer template, gold answer, evaluator, and hidden notes for `train_003`.

## 中文

### 数据和来源

本任务属于 `SCN_024_engineering_portfolio_work_item_analytics`，来源示例为 `E001`、`E002` 和尤其相关的 `E003`。任务设计将 `train_003` 指定为发布就绪度任务，范围是发布 `REL-ORION-2026-02`。构造数据来自 `task_group/task_group_024/env/portfolio.db`；除 `input/payloads/answer_template.json` 外，没有额外的任务本地业务数据。

相关生成表包括 `releases`、`milestones`、`work_items`、`blockers` 和 `dependencies`。环境通过 `/api/releases`、`/api/milestones`、`/api/work-items`、`/api/blockers`、`/api/dependencies` 和 `/api/query` 暴露这些数据。

### 任务定义和场景适配

可见提示要求求解者评估 Orion 二月发布列车是否可以发布。期望输出是结构化 JSON，包含发布决策、里程碑完成指标、阻塞就绪度的未完成工作、阻塞原因计数、依赖链以及总体就绪分数。

这符合本任务组的工程运营分析场景，因为发布就绪度需要把发布工作项、里程碑、阻塞记录和依赖关系连接起来分析。它复现了来源示例 `E003` 的业务流程：确定权威发布范围，从分母中去除非主工作项，区分真实完成状态和陈旧镜像字段，传播未解决门禁，并形成上线决策。

### 材料地图

- `input/prompt.txt` 提供业务请求和环境基础地址占位符 `<TASK_ENV_BASE_URL>`。
- `input/payloads/answer_template.json` 定义准确的 JSON 结构、枚举、精度和排序规则。
- `output/answer.json` 是由 `portfolio.db` 推导出的标准答案。
- `eval/eval.py` 用整点权重评估结构化业务结果。
- `eval/eval.sh` 是命令行入口，使用 `$1` 接收候选答案路径。
- `portfolio.db` 提供发布、里程碑、工作项、阻塞和依赖的权威数据。

### 解答和评估依据

`REL-ORION-2026-02` 的主发布工作排除状态为 `Cancelled`、状态为 `Duplicate` 或 `duplicate_of` 非空的工作项。剩余主分母为 16 个工作项。完成状态为 `Done`、`Verified` 和 `Deployed`；在本发布就绪度任务中，`Closed` 不计为完成。主工作项中有 11 个完成，因此就绪分数为 `11 / 16 = 0.688`，保留三位小数。

里程碑指标如下：

- `MIL-ORION-BETA`：2/2，`100.0`。
- `MIL-ORION-GA`：4/6，`66.7`。
- `MIL-ORION-HARDEN`：3/5，`60.0`。
- `MIL-ORION-RC`：2/3，`66.7`。

高影响未解决阻塞是状态为 `Open` 或 `Monitoring` 且严重度为 `Critical` 或 `High` 的阻塞。Orion 有三个此类原因：`release note evidence gap`、`open reliability rehearsal gap` 和 `unresolved cve exception`。只有未完成的主发布工作项会进入 gating 集合，所以完成项 `WI-24024-008` 上的高影响阻塞会影响阻塞原因计数和发布决策，但不会进入 `gating_work_item_ids`。未完成且带有高影响阻塞的 gating 项是 `WI-24024-010` 和 `WI-24024-012`。

关键依赖链是从未完成的被阻塞发布工作项到未完成主依赖项的有序路径。Orion 中未完成发布工作相关的依赖要么指向已完成项，要么指向非主发布项，因此 `critical_dependency_chains` 为空。由于仍存在高影响未解决阻塞，发布决策为 `NO_SHIP`。

评分共有六个整点维度，满分 14 点：

- 决策枚举，权重 3；
- 里程碑指标，权重 3；
- gating 工作项集合，权重 3；
- 阻塞原因计数，权重 2；
- 关键依赖链，权重 2；
- 就绪分数，权重 1。

评估器会规范化枚举大小写、集合排序、里程碑按 id 排序、数字精度和阻塞原因对象。每个评分点都是全得或零分。常见错误包括计入 `Duplicate` 项 `WI-24024-154`、信任 `mirror_status`、把 `Closed` 当成完成、遗漏完成工作项上的高影响阻塞原因，或把已完成的依赖目标当成关键依赖链。

### 迁移设计

作为训练任务，本任务建立后续 Zephyr 测试任务所需的发布就绪度惯例。求解者可以从中归纳出发布就绪度应使用权威的 `status`、`release_id`、`milestone_id`、`duplicate_of`、阻塞严重度/状态和依赖方向，而不是陈旧的镜像字段。它还展示了里程碑完成度和就绪分数使用按数量计算的主分母，同时阻塞原因和 gating 工作项是相关但不完全相同的输出。

可迁移的方法包括：查询所有发布相关表，先建立主工作集合再聚合，区分完成和完成相邻状态，独立统计阻塞原因与 gating 项，并按“被阻塞项到依赖项”的方向表示依赖链。

### 构造记录

作者：Codex task-builder worker。创建日期：2026-07-18。更新日期：2026-07-18。主要变更：创建 `train_003` 的任务目录、求解者提示、答案模板、标准答案、评估器和隐藏说明。
