# test_003 Hidden Notes

## English

### Data and Source Lineage

This task belongs to `SCN_024_engineering_portfolio_work_item_analytics`, based on source examples `E001`, `E002`, and especially the release-readiness pattern from `E003`. The task-builder assignment defines `test_003` as a release-readiness test task for `REL-ZEPHYR-2026-03`. The construction data is the generated SQLite database at `task_group/task_group_024/env/portfolio.db`; no extra business payload is used beyond the solver-visible `input/payloads/answer_template.json`.

The authoritative rows come from `releases`, `milestones`, `work_items`, `blockers`, and `dependencies`. These same objects are exposed in the environment through the release, milestone, work item, blocker, dependency, and restricted query endpoints.

### Task Definition and Scenario Fit

The solver-visible task asks for a release-readiness assessment for the Zephyr March release train. The expected answer is a structured JSON object containing a ship decision, milestone completion metrics, readiness gates, high-impact blocker causes, critical dependency chains, non-hard-gate watch items, low/medium blocker cause counts, milestone watch ownership, and an aggregate readiness score.

This fits the engineering operations analytics scenario because the work requires joining release planning records, milestone ownership, work item state, blocker severity/status, and dependency direction into a business launch decision. It is a test transfer of the release-readiness workflow established by `train_003`, with new release topology, stale mirror statuses, duplicate distractors, high-impact blocker records, and external dependency blockers.

### Material Map

- `input/prompt.txt` gives the solver the business request, output expectations, ordering rules, and the `<TASK_ENV_BASE_URL>` placeholder.
- `input/payloads/answer_template.json` defines the required JSON fields, enum choices, list ordering, and numeric precision.
- `output/answer.json` is the gold answer derived from `portfolio.db`.
- `eval/eval.py` implements deterministic whole-point checks for each rubric goal.
- `eval/eval.sh` accepts a candidate answer path as `$1` and invokes the Python evaluator.
- `portfolio.db` provides the release, milestone, work item, blocker, and dependency evidence used for construction.

### Solution and Evaluation Basis

Primary release work for `REL-ZEPHYR-2026-03` excludes status `Cancelled`, status `Duplicate`, and any work item with non-null `duplicate_of`. The excluded release rows are `WI-24024-016`, `WI-24024-069`, `WI-24024-077`, and `WI-24024-078`. The primary denominator is therefore 19 work items.

The complete readiness statuses are `Closed`, `Done`, `Verified`, and `Deployed`. The complete primary work items are `WI-24024-013`, `WI-24024-015`, `WI-24024-027`, `WI-24024-031`, `WI-24024-091`, `WI-24024-092`, `WI-24024-104`, `WI-24024-126`, `WI-24024-146`, and `WI-24024-153`. The readiness score is `10 / 19 = 0.526` rounded to three decimals.

Milestone metrics:

- `MIL-ZEPHYR-BETA`: 4 complete out of 5 primary, `80.0`.
- `MIL-ZEPHYR-GA`: 2 complete out of 6 primary, `33.3`.
- `MIL-ZEPHYR-HARDEN`: 3 complete out of 6 primary, `50.0`.
- `MIL-ZEPHYR-RC`: 1 complete out of 2 primary, `50.0`.

High-impact unresolved blockers are blocker rows with status `Open` or `Monitoring` and severity `Critical` or `High`. Zephyr has one such blocker: `BLK-24024-003` on `WI-24024-017`, with cause `missing encryption audit evidence`. Medium open blockers on complete items are not high-impact for the blocker-cause scoring point, although they would matter for a watch decision if no higher gate existed.

The gating work item ids are non-complete primary release items gated by unresolved high-impact blockers or by non-complete dependency targets. The expected sorted set is `WI-24024-017`, `WI-24024-054`, `WI-24024-087`, and `WI-24024-140`. External dependency targets `WI-24024-132`, `WI-24024-050`, and `WI-24024-127` appear in dependency chains but not in the Zephyr gating id set. Other incomplete release items are not listed because they do not have a high-impact unresolved blocker and do not start a critical dependency chain.

The expected critical dependency chains, sorted lexicographically by path, are `["WI-24024-054", "WI-24024-132"]`, `["WI-24024-087", "WI-24024-050"]`, and `["WI-24024-140", "WI-24024-127"]`. The decision is `NO_SHIP` because both a high-impact unresolved blocker and critical non-complete dependency gates exist.

The non-hard-gate watch items are `WI-24024-014`, `WI-24024-032`, `WI-24024-079`, `WI-24024-090`, and `WI-24024-115`. Unresolved low- or medium-impact blocker cause counts are `dependency validation late=1`, `owner unavailable=1`, and `release note evidence gap=1`. The watch milestone summary is `MIL-ZEPHYR-BETA / API Foundations / 1`, `MIL-ZEPHYR-GA / Release Engineering / 2`, `MIL-ZEPHYR-HARDEN / Data Platform / 1`, and `MIL-ZEPHYR-RC / Revenue Platform / 1`.

The rubric has nine whole-point dimensions and a 23 point maximum:

- decision enum, weight 3;
- milestone metrics, weight 3;
- gating work item set, weight 3;
- blocker cause counts, weight 2;
- critical dependency chains, weight 2;
- non-hard-gate watch item set, weight 3;
- low/medium blocker cause counts, weight 3;
- watch milestone summary, weight 3;
- readiness score, weight 1.

The evaluator normalizes enum casing, set ordering, milestone ordering by id, numeric precision, blocker cause objects, and dependency-chain ordering. Each scoring point is all-or-zero and returns JSON details. Likely pitfalls are trusting `mirror_status`, counting duplicate rows, listing every incomplete release item as a gate, missing the dependency direction, adding external dependency ids to `gating_work_item_ids`, or omitting dependency pairs that point outside the release but still block release work.

### Transfer Design

The transfer anchor is `train_003`. Solving `train_003` teaches the release-readiness conventions that must be inferred here: build a primary release work set first, use authoritative status rather than mirror status, count blocker causes separately from gating ids, and express dependency chains from blocked work to dependency.

Transfer-dependent scoring points are especially `decision_enum`, `milestone_metrics`, `gating_set`, `dependency_chains`, and `readiness_score`. Task-specific exploration is still required to identify Zephyr's exact release rows, four milestones, blocker records, duplicate distractors, and external dependency targets. The visible prompt intentionally asks for the business outputs without restating the full hidden SOP, so the train task supplies the reusable method while the test data supplies the new evidence.

### Construction Record

Author: Codex task-builder worker. Created: 2026-07-18. Updated: 2026-07-18. Major changes: created the `test_003` prompt, answer template, gold answer, evaluator, and bilingual hidden notes.

## 中文

### 数据和来源

本任务属于 `SCN_024_engineering_portfolio_work_item_analytics`，来源示例为 `E001`、`E002`，并且尤其对应 `E003` 的发布就绪度模式。任务构造分配将 `test_003` 定义为发布 `REL-ZEPHYR-2026-03` 的测试任务。构造数据来自生成的 SQLite 数据库 `task_group/task_group_024/env/portfolio.db`；除求解者可见的 `input/payloads/answer_template.json` 外，没有额外业务载荷。

权威数据行来自 `releases`、`milestones`、`work_items`、`blockers` 和 `dependencies`。环境也通过发布、里程碑、工作项、阻塞、依赖和受限查询端点暴露这些对象。

### 任务定义和场景适配

可见任务要求求解者评估 Zephyr 三月发布列车的发布就绪度。期望答案是结构化 JSON，包含发布决策、里程碑完成指标、就绪度门禁、高影响阻塞原因、关键依赖链、非硬门禁 watch 项、低/中影响阻塞原因、里程碑 watch 归属和总体就绪分数。

本任务符合工程运营分析场景，因为它需要把发布计划记录、里程碑归属、工作项状态、阻塞严重度/状态和依赖方向连接为业务上线决策。它是 `train_003` 所建立的发布就绪度流程的测试迁移，变化点包括新的发布拓扑、陈旧镜像状态、重复项干扰、高影响阻塞记录和外部依赖阻塞。

### 材料地图

- `input/prompt.txt` 向求解者提供业务请求、输出预期、排序规则和 `<TASK_ENV_BASE_URL>` 占位符。
- `input/payloads/answer_template.json` 定义必需 JSON 字段、枚举、列表排序和数字精度。
- `output/answer.json` 是从 `portfolio.db` 推导出的标准答案。
- `eval/eval.py` 对每个评分目标执行确定性的整点检查。
- `eval/eval.sh` 使用 `$1` 接收候选答案路径并调用 Python 评估器。
- `portfolio.db` 提供构造所用的发布、里程碑、工作项、阻塞和依赖证据。

### 解答和评估依据

`REL-ZEPHYR-2026-03` 的主发布工作排除状态为 `Cancelled`、状态为 `Duplicate` 或 `duplicate_of` 非空的工作项。被排除的发布行是 `WI-24024-016`、`WI-24024-069`、`WI-24024-077` 和 `WI-24024-078`。因此主分母为 19 个工作项。

就绪度完成状态是 `Closed`、`Done`、`Verified` 和 `Deployed`。完成的主工作项为 `WI-24024-013`、`WI-24024-015`、`WI-24024-027`、`WI-24024-031`、`WI-24024-091`、`WI-24024-092`、`WI-24024-104`、`WI-24024-126`、`WI-24024-146` 和 `WI-24024-153`。就绪分数为 `10 / 19 = 0.526`，保留三位小数。

里程碑指标如下：

- `MIL-ZEPHYR-BETA`：4/5，`80.0`。
- `MIL-ZEPHYR-GA`：2/6，`33.3`。
- `MIL-ZEPHYR-HARDEN`：3/6，`50.0`。
- `MIL-ZEPHYR-RC`：1/2，`50.0`。

高影响未解决阻塞是状态为 `Open` 或 `Monitoring` 且严重度为 `Critical` 或 `High` 的阻塞行。Zephyr 有一个此类阻塞：`BLK-24024-003`，位于 `WI-24024-017`，原因为 `missing encryption audit evidence`。完成项上的中等未解决阻塞不属于高影响阻塞原因评分点，但如果没有更高门禁，它们会影响观察发布决策。

gating 工作项是由于高影响未解决阻塞或未完成依赖目标而受阻的主发布未完成项。期望排序集合为 `WI-24024-017`、`WI-24024-054`、`WI-24024-087` 和 `WI-24024-140`。外部依赖目标 `WI-24024-132`、`WI-24024-050` 和 `WI-24024-127` 会出现在依赖链中，但不属于 Zephyr gating id 集合。其他未完成发布项没有高影响未解决阻塞，也不是关键依赖链的起点，因此不列入。

期望关键依赖链按路径字典序排序为 `["WI-24024-054", "WI-24024-132"]`、`["WI-24024-087", "WI-24024-050"]` 和 `["WI-24024-140", "WI-24024-127"]`。发布决策是 `NO_SHIP`，因为同时存在高影响未解决阻塞和关键未完成依赖门禁。

非硬门禁 watch 项为 `WI-24024-014`、`WI-24024-032`、`WI-24024-079`、`WI-24024-090`、`WI-24024-115`。未解决低/中影响阻塞原因计数为 `dependency validation late=1`、`owner unavailable=1`、`release note evidence gap=1`。watch 里程碑摘要为 `MIL-ZEPHYR-BETA / API Foundations / 1`、`MIL-ZEPHYR-GA / Release Engineering / 2`、`MIL-ZEPHYR-HARDEN / Data Platform / 1`、`MIL-ZEPHYR-RC / Revenue Platform / 1`。

评分共有九个整点维度，满分 23 点：

- 决策枚举，权重 3；
- 里程碑指标，权重 3；
- gating 工作项集合，权重 3；
- 阻塞原因计数，权重 2；
- 关键依赖链，权重 2；
- 非硬门禁 watch 工作项集合，权重 3；
- 低/中影响阻塞原因计数，权重 3；
- watch 里程碑摘要，权重 3；
- 就绪分数，权重 1。

评估器会规范化枚举大小写、集合排序、里程碑按 id 排序、数字精度、阻塞原因对象和依赖链排序。每个评分点都是全得或零分，并返回 JSON 细节。常见错误包括信任 `mirror_status`、计入重复项、把所有未完成发布项都列为 gating、弄错依赖方向、把外部依赖 id 加入 `gating_work_item_ids`，或遗漏指向发布外部但仍阻塞发布工作的依赖对。

### 迁移设计

迁移锚点是 `train_003`。求解 `train_003` 可以归纳出本任务所需的发布就绪度惯例：先建立主发布工作集合，使用权威状态而不是镜像状态，分开统计阻塞原因和 gating id，并按“被阻塞工作到依赖项”的方向表示依赖链。

依赖迁移的评分点主要是 `decision_enum`、`milestone_metrics`、`gating_set`、`dependency_chains` 和 `readiness_score`。任务本地探索仍然需要识别 Zephyr 的具体发布行、四个里程碑、阻塞记录、重复项干扰和外部依赖目标。可见提示有意只要求业务输出而不复述完整隐藏流程，因此训练任务提供可复用方法，测试数据提供新的证据。

### 构造记录

作者：Codex task-builder worker。创建日期：2026-07-18。更新日期：2026-07-18。主要变更：创建 `test_003` 的提示、答案模板、标准答案、评估器和双语隐藏说明。
