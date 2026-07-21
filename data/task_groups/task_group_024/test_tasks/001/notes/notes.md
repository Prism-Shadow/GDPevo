# test_001 Hidden Notes

## English

This task belongs to `SCN_024_engineering_portfolio_work_item_analytics`, sourced from the engineering operations examples `E001`, `E002`, and `E003`. The specific family is portfolio work-mix classification and target-gap analysis. The task-builder assignment names `test_001` as the Q4 2025 Data Reliability portfolio mix review for the `Data Platform` and `Observability` teams, using `task_group/task_group_024/env/portfolio.db` as construction data and the `mix_targets` row where `scope_id = test_001` as the target mix source.

The solver-visible prompt asks the solver to use the shared environment at `<TASK_ENV_BASE_URL>`, find the `test_001` Q4 scope, classify qualifying work items into `NewFeature`, `TechDebt`, `Reliability`, and `Security`, compute count-based percentages and target gaps, identify under-invested categories, report owner and team exposure by category, report excluded Q4 same-scope candidate ids and reason counts, and select a controlled action enum. The local payload `input/payloads/answer_template.json` defines the exact JSON shape, category order, percentage precision, list ordering, and allowed actions. The standard answer is `output/answer.json`; the evaluator entry point is `eval/eval.sh`.

Scenario fit: this is a realistic engineering portfolio review. It combines work item filtering, taxonomy classification, target comparison, and operational action selection. The important environment objects are `work_items` and `mix_targets`. `work_items` supplies ids, titles, types, statuses, teams, product areas, labels, close dates, duplicate links, and stale mirror fields. `mix_targets` supplies the target mix percentages for the named scope. The task intentionally includes stale or conflicting fields such as `mirror_status` and `legacy_category`; the final solution is based on canonical fields and task-family conventions.

Solution basis:

- Target row: `test_001`, `2025-Q4`, team group `Data Platform + Observability`, product area `Data Reliability`, targets `NewFeature=30.0`, `TechDebt=26.0`, `Reliability=28.0`, `Security=16.0` percent.
- Included work items are canonical Q4 2025 closed portfolio records for the two teams and product area, with qualifying terminal statuses and no duplicate link. The included ids are `WI-24024-005`, `WI-24024-P041`, `WI-24024-P042`, `WI-24024-P043`, `WI-24024-P044`, `WI-24024-P045`, `WI-24024-P046`, `WI-24024-P047`, and `WI-24024-P048`.
- Classification precedence used for construction is `Security`, then `Reliability`, then `TechDebt`, then `NewFeature`. Security is triggered by `Security` or `Compliance` work type or security-related title/label terms. Reliability is triggered by `Reliability` or `Incident` work type or reliability/incident/outage/latency/flaky title/label terms. Tech debt is triggered by `Refactor`, `Chore`, or `Dependency` work type or refactor/migration/cleanup/dependency title/label terms. Items not matched earlier are `NewFeature`.
- Category counts are `NewFeature=0`, `TechDebt=3`, `Reliability=4`, `Security=2`, total `9`.
- Actual percentages are count based and rounded to one decimal: `0.0`, `33.3`, `44.4`, and `22.2`.
- Gaps are `actual_pct - target_pct`: `NewFeature=-30.0`, `TechDebt=7.3`, `Reliability=16.4`, `Security=6.2`.
- The only under-invested category is `NewFeature`, so the recommended action is `REBALANCE_CAPACITY`.
- Q4 same-team and same-product candidate rows excluded from the final mix are `WI-24024-P049` because it is a duplicate, `WI-24024-P050` because it is cancelled, and `WI-24024-P051` because it has `duplicate_of = WI-24024-P043`.
- Category owner counts are empty for `NewFeature`; `TechDebt` has `Devon Wells=2` and `Liam Chen=1`; `Reliability` has `Devon Wells=1`, `Liam Chen=2`, and `UNASSIGNED=1`; `Security` has `Avery Quinn=1` and `Liam Chen=1`. Category team counts are empty for `NewFeature`; `TechDebt` has `Data Platform=1` and `Observability=2`; `Reliability` has `Data Platform=3` and `Observability=1`; `Security` has `Data Platform=1` and `Observability=1`. Exclusion reason counts are `cancelled=1`, `duplicate_status=1`, and `duplicate_of=2`.

Evaluation basis and rubric: the evaluator awards whole raw points only, for a total of 19. The scoring goals are included set (2), category counts (2), category percentages (1), gap table (1), under-invested categories (1), category owner counts (2), category team counts (2), excluded ids (3), exclusion reason counts (2), and action enum (3). These cover distinct business outcomes: scope qualification, taxonomy classification, numeric mix measurement, target comparison, investment decisioning, owner/team exposure, exclusion handling, and action selection. Lists are normalized as sorted unique sets except where ordered category rows are declared. Percentages are rounded to one decimal. No free-form prose is scored.

Likely model pitfalls include using `mirror_status` instead of canonical `status`, trusting `legacy_category`, counting duplicate or cancelled Q4 rows, treating labels with overlapping security/reliability/tech-debt terms without precedence, using story points instead of item counts, subtracting gaps in the wrong direction, or listing all out-of-quarter same-scope rows as exclusions.

Transfer design: `train_001` and `train_004` are the transfer anchors. They teach the portfolio inclusion window, duplicate/cancelled exclusion, category precedence, count-based percentage math, and actual-minus-target gap convention. Transfer-dependent scoring points are the included set, category counts, percentage/gap calculations, under-invested category selection, and action enum. Task-specific exploration still requires discovering the `test_001` target row and the exact noisy Data Reliability work items in this database.

Construction record: authored by Codex for `test_001` on 2026-07-18. Created files are `input/prompt.txt`, `input/payloads/answer_template.json`, `notes/notes.md`, `output/answer.json`, `eval/eval.sh`, and `eval/eval.py`. The evaluator was designed to be deterministic and self-contained.

## 中文

本任务属于 `SCN_024_engineering_portfolio_work_item_analytics`，来源示例为 `E001`、`E002` 和 `E003`。任务类型是工程工作项组合占比分析。任务构建说明指定 `test_001` 为 2025 年第四季度 `Data Platform` 与 `Observability` 团队在 `Data Reliability` 产品域上的组合复盘，构建数据来自 `task_group/task_group_024/env/portfolio.db`，目标占比来自 `mix_targets` 表中 `scope_id = test_001` 的记录。

求解者可见的提示只要求使用 `<TASK_ENV_BASE_URL>` 中的共享环境，找到 `test_001` 的 Q4 范围，将符合条件的工作项归类到 `NewFeature`、`TechDebt`、`Reliability`、`Security`，计算数量、百分比、目标差距、投入不足类别、按类别统计 owner 和 team 暴露、被排除的 Q4 同范围候选项及其原因计数，以及受控枚举动作。`input/payloads/answer_template.json` 定义了精确的 JSON 结构、类别顺序、百分比精度、列表排序和动作枚举。标准答案在 `output/answer.json`，评测入口是 `eval/eval.sh`。

场景适配性：这是一个真实的工程组合复盘流程，包含工作项筛选、分类法判断、目标占比比较和运营动作选择。关键环境对象是 `work_items` 和 `mix_targets`。`work_items` 提供 id、标题、类型、状态、团队、产品域、标签、关闭日期、重复项关系以及干扰性的旧字段；`mix_targets` 提供指定范围的目标占比。任务故意包含 `mirror_status` 和 `legacy_category` 等陈旧或冲突字段，最终答案应基于规范字段和任务族约定。

解答依据：

- 目标行是 `test_001`，季度 `2025-Q4`，团队组 `Data Platform + Observability`，产品域 `Data Reliability`，目标百分比分别为 `NewFeature=30.0`、`TechDebt=26.0`、`Reliability=28.0`、`Security=16.0`。
- 纳入项是两个团队和该产品域中 2025 年第四季度关闭、状态合格、且没有重复项链接的规范组合记录。纳入 id 为 `WI-24024-005`、`WI-24024-P041`、`WI-24024-P042`、`WI-24024-P043`、`WI-24024-P044`、`WI-24024-P045`、`WI-24024-P046`、`WI-24024-P047`、`WI-24024-P048`。
- 构建时使用的分类优先级是 `Security`、`Reliability`、`TechDebt`、`NewFeature`。安全类由安全/合规类型或标题和标签中的安全相关词触发；可靠性类由可靠性/事故类型或可靠性、事故、故障、延迟、不稳定相关词触发；技术债由重构、杂项、依赖类型或重构、迁移、清理、依赖相关词触发；之前都未命中的项目归为 `NewFeature`。
- 类别计数为 `NewFeature=0`、`TechDebt=3`、`Reliability=4`、`Security=2`，总数为 `9`。
- 实际百分比按工作项数量计算并保留一位小数：`0.0`、`33.3`、`44.4`、`22.2`。
- 差距为 `actual_pct - target_pct`：`NewFeature=-30.0`、`TechDebt=7.3`、`Reliability=16.4`、`Security=6.2`。
- 唯一投入不足类别是 `NewFeature`，因此推荐动作是 `REBALANCE_CAPACITY`。
- Q4 同团队同产品域但从最终组合中排除的候选项是 `WI-24024-P049`、`WI-24024-P050`、`WI-24024-P051`，原因分别是重复状态、取消状态、以及 `duplicate_of = WI-24024-P043`。
- 类别 owner 计数：`NewFeature` 为空；`TechDebt` 为 `Devon Wells=2`、`Liam Chen=1`；`Reliability` 为 `Devon Wells=1`、`Liam Chen=2`、`UNASSIGNED=1`；`Security` 为 `Avery Quinn=1`、`Liam Chen=1`。类别 team 计数：`NewFeature` 为空；`TechDebt` 为 `Data Platform=1`、`Observability=2`；`Reliability` 为 `Data Platform=3`、`Observability=1`；`Security` 为 `Data Platform=1`、`Observability=1`。排除原因计数为 `cancelled=1`、`duplicate_status=1`、`duplicate_of=2`。

评测依据和 rubric：评测器只给整点原始分，总分 19。评分项为纳入集合 2 分、类别计数 2 分、百分比 1 分、差距表 1 分、投入不足类别 1 分、类别 owner 计数 2 分、类别 team 计数 2 分、排除 id 3 分、排除原因计数 2 分、动作枚举 3 分。这些覆盖不同业务结果：范围资格、分类法、数值度量、目标比较、投入决策、owner/team 暴露、排除处理和动作选择。除声明为有序的类别表外，列表按排序去重集合比较。百分比保留一位小数。不评测自由文本。

常见错误包括使用 `mirror_status` 而不是规范 `status`，相信 `legacy_category`，计入重复或取消的 Q4 行，未按优先级处理安全/可靠性/技术债标签冲突，用 story points 而不是工作项数量计算，差距方向算反，或把所有季度外同范围行也列入排除项。

迁移设计：`train_001` 和 `train_004` 是迁移锚点。它们提供组合任务的关闭窗口、重复和取消排除、类别优先级、按数量计算百分比、以及实际减目标的差距约定。依赖迁移的高价值评分点包括纳入集合、类别计数、百分比和差距、投入不足类别以及动作枚举。本测试仍需要在本地数据中探索 `test_001` 目标行和具体的 Data Reliability 噪声工作项。

构建记录：由 Codex 于 2026-07-18 为 `test_001` 创建。创建的文件包括 `input/prompt.txt`、`input/payloads/answer_template.json`、`notes/notes.md`、`output/answer.json`、`eval/eval.sh` 和 `eval/eval.py`。评测器设计为确定性且自包含。
