# test_002 Hidden Notes

## English

This task belongs to `SCN_024_engineering_portfolio_work_item_analytics`, sourced from examples `E001`, `E002`, and `E003`. The task family is SLA aging for engineering work items. The task-builder assignment defines `test_002` as Core Services reliability/security SLA aging as of `2026-01-18` with a 10-day recent-closed window, using `task_group/task_group_024/env/portfolio.db` as construction data.

The solver-visible prompt asks the solver to use `<TASK_ENV_BASE_URL>` and the runtime access file to inspect work item and SLA data, then return JSON matching `input/payloads/answer_template.json`. The expected answer reports primary SLA population ids, overdue primary ids, aging buckets, team overdue counts, the top owner/team hotspot, duplicate clusters, missing-owner primary ids, and a three-decimal breach rate. The standard answer is `output/answer.json`; the evaluator entry point is `eval/eval.sh`.

Scenario fit: this represents a normal engineering operations SLA review. The workflow combines work-item state reconstruction, portfolio category resolution, duplicate hygiene, owner/team rollup, and due-date breach metrics. The important environment object is `work_items`; `sla_policy` is available as part of the environment but the construction for this task uses the explicit `due_at` values on the items. No task-local data payload is needed beyond the answer template.

Material map:

- `work_items`: source for `id`, `title`, `work_type`, `status`, `team`, `owner`, `created_at`, `due_at`, `closed_at`, `severity`, `labels`, `duplicate_of`, `mirror_status`, and `legacy_category`.
- `sla_policy`: shared policy context for severity-to-SLA expectations.
- `input/prompt.txt`: solver-visible business scope and output request without the detailed construction path.
- `input/payloads/answer_template.json`: exact JSON contract, field types, list ordering, bucket names, and rate precision.
- `output/answer.json`: canonical answer derived from the database.
- `eval/eval.py` and `eval/eval.sh`: deterministic whole-point evaluator.

Solution and evaluation basis: category resolution uses the task-group portfolio precedence `Security`, then `Reliability`, then `TechDebt`, then `NewFeature`, drawing signals from work type, labels, and title. The relevant categories are `Security` and `Reliability`. Records are in the `Core Services` or `Platform Core` team scope and existed by `2026-01-18`. Primary SLA records are active open work or work closed in the inclusive `2026-01-08` to `2026-01-18` window, excluding `Cancelled`, `Duplicate`, and rows with `duplicate_of` set. Duplicate rows that otherwise match team, category, and date scope are reported as duplicate clusters outside the primary denominator.

The included primary ids are `WI-24024-036`, `WI-24024-046`, `WI-24024-074`, `WI-24024-096`, `WI-24024-110`, `WI-24024-119`, `WI-24024-S041`, `WI-24024-S042`, `WI-24024-S043`, `WI-24024-S044`, `WI-24024-S045`, `WI-24024-S046`, `WI-24024-S047`, and `WI-24024-S048`. Overdue primary ids are `WI-24024-036`, `WI-24024-074`, `WI-24024-096`, `WI-24024-110`, `WI-24024-119`, `WI-24024-S041`, `WI-24024-S042`, `WI-24024-S044`, and `WI-24024-S046`. Open work is overdue when `due_at` is before `2026-01-18`; recently closed work is overdue when `due_at` is before `closed_at`; same-day due dates are not overdue.

Aging uses days from `created_at` to `2026-01-18` for open work and from `created_at` to `closed_at` for recently closed work. Bucket counts are `0-3=1`, `4-7=3`, `8-14=5`, `15-30=0`, and `31+=5`. Team overdue counts are `Core Services=4` and `Platform Core=5`. The top owner/team hotspot is `Core Services` / `Priya Stone` with 2 overdue primary items. Duplicate clusters are `WI-24024-S041 -> WI-24024-S049` and `WI-24024-S042 -> WI-24024-S050`. Missing-owner primary ids are `WI-24024-S046` and `WI-24024-S047`. The breach rate is `9 / 14 = 0.643`.

Rubric weights are seeded primary set 2, legacy primary set 1, duplicate exclusion from primary set 1, overdue primary set 3, aging buckets 2, hotspot owner/team 2, duplicate clusters 2, missing-owner ids 2, and breach rate 2, for a raw total of 17. These cover distinct business outcomes: SLA population construction across deterministic and generated records, duplicate hygiene in the denominator, deadline breach detection, age distribution, operational hotspot identification, duplicate reporting, ownership risk, and aggregate SLA rate. The evaluator uses whole points only and prints JSON details with expected and actual normalized values for each scoring point.

Likely model pitfalls include trusting `mirror_status` or `legacy_category`, missing random generated rows that still match the review, counting duplicates in the primary denominator, excluding recent closed rows, treating `WI-24024-S048` as overdue even though it is due on the as-of date, computing closed-item overdue status against the as-of date instead of `closed_at`, or deriving aging buckets from due dates instead of creation-to-effective-end age.

Transfer design: `train_002` and `train_005` are the transfer anchors. They teach the SLA-family conventions for combining open and recent-closed records, excluding duplicates from primary metrics while still reporting duplicate clusters, applying portfolio category precedence to SLA scopes, handling same-day due boundaries, finding missing owners, and computing breach rates. Transfer-dependent scoring points are the seeded and legacy primary sets, duplicate exclusion, overdue primary set, aging bucket counts, duplicate clusters, missing-owner ids, and breach rate. Task-specific exploration still requires discovering the Core Services and Platform Core matching rows, the ten-day window, the owner/team counts, and the exact noisy generated records in `portfolio.db`.

Construction record: authored by Codex for `test_002` on 2026-07-18. Created files are `input/prompt.txt`, `input/payloads/answer_template.json`, `notes/notes.md`, `output/answer.json`, `eval/eval.sh`, and `eval/eval.py`. The evaluator was run against the gold answer after construction.

## Chinese

本任务属于 `SCN_024_engineering_portfolio_work_item_analytics`，来源示例为 `E001`、`E002` 和 `E003`。任务类型是工程工作项 SLA aging。任务构建说明指定 `test_002` 为 `2026-01-18` 时点下 `Core Services` 和 `Platform Core` 团队的可靠性/安全 SLA aging 审查，最近关闭窗口为 10 天，构建数据来自 `task_group/task_group_024/env/portfolio.db`。

求解者可见的提示要求使用 `<TASK_ENV_BASE_URL>` 和运行时访问文件检查工作项与 SLA 数据，并返回符合 `input/payloads/answer_template.json` 的 JSON。预期输出包括主要 SLA 分母 id、逾期主要 id、aging bucket、团队逾期计数、最高 owner/team 热点、重复记录簇、缺少 owner 的主要 id，以及三位小数的 breach rate。标准答案在 `output/answer.json`，评测入口是 `eval/eval.sh`。

场景适配性：这是常见的工程运营 SLA 复盘流程，需要重建工作项状态、使用组合分类优先级、处理重复记录、做 owner/team 汇总，并计算截止日期违约指标。关键环境对象是 `work_items`；`sla_policy` 作为共享策略上下文存在，但本任务构建使用工作项上的显式 `due_at`。除答案模板外，本任务不需要额外本地 payload。

材料地图：

- `work_items`：提供 `id`、`title`、`work_type`、`status`、`team`、`owner`、`created_at`、`due_at`、`closed_at`、`severity`、`labels`、`duplicate_of`、`mirror_status` 和 `legacy_category`。
- `sla_policy`：提供严重等级到 SLA 期望的共享策略背景。
- `input/prompt.txt`：只给求解者业务范围和输出要求，不泄露详细构造路径。
- `input/payloads/answer_template.json`：定义精确 JSON 结构、字段类型、列表排序、bucket 名称和 rate 精度。
- `output/answer.json`：从数据库推导出的标准答案。
- `eval/eval.py` 和 `eval/eval.sh`：确定性的整点评测器。

解答和评估依据：类别解析使用任务组组合优先级 `Security`、`Reliability`、`TechDebt`、`NewFeature`，信号来自 work type、labels 和 title。本任务关注 `Security` 与 `Reliability`。记录必须属于 `Core Services` 或 `Platform Core`，并且在 `2026-01-18` 前已经存在。Primary SLA 记录是活跃开放工作，或在 `2026-01-08` 到 `2026-01-18` 闭区间内关闭的工作；排除 `Cancelled`、`Duplicate` 和 `duplicate_of` 非空的行。否则符合团队、类别和日期范围的重复行只作为 duplicate cluster 报告，不进入 primary 分母。

included primary ids 为 `WI-24024-036`、`WI-24024-046`、`WI-24024-074`、`WI-24024-096`、`WI-24024-110`、`WI-24024-119`、`WI-24024-S041`、`WI-24024-S042`、`WI-24024-S043`、`WI-24024-S044`、`WI-24024-S045`、`WI-24024-S046`、`WI-24024-S047`、`WI-24024-S048`。overdue primary ids 为 `WI-24024-036`、`WI-24024-074`、`WI-24024-096`、`WI-24024-110`、`WI-24024-119`、`WI-24024-S041`、`WI-24024-S042`、`WI-24024-S044`、`WI-24024-S046`。开放工作在 `due_at` 早于 `2026-01-18` 时逾期；最近关闭工作在 `due_at` 早于 `closed_at` 时逾期；同日到期不算逾期。

Aging 对开放工作使用 `created_at` 到 `2026-01-18` 的天数，对最近关闭工作使用 `created_at` 到 `closed_at` 的天数。bucket 计数为 `0-3=1`、`4-7=3`、`8-14=5`、`15-30=0`、`31+=5`。团队逾期计数是 `Core Services=4`、`Platform Core=5`。最高 owner/team 热点是 `Core Services` / `Priya Stone`，逾期主要项数量为 2。重复簇是 `WI-24024-S041 -> WI-24024-S049` 和 `WI-24024-S042 -> WI-24024-S050`。缺少 owner 的主要 id 是 `WI-24024-S046` 和 `WI-24024-S047`。breach rate 为 `9 / 14 = 0.643`。

评分权重为 seeded primary set 2、legacy primary set 1、primary 中排除 duplicate 1、overdue primary set 3、aging buckets 2、hotspot owner/team 2、duplicate clusters 2、missing-owner ids 2、breach rate 2，原始总分 17。这些覆盖不同业务结果：确定性和生成记录共同组成的 SLA 分母构造、分母中的重复项卫生、截止日期违约识别、年龄分布、运营热点识别、重复项报告、owner 风险和汇总 SLA 比率。评测器只给整点，并在 JSON details 中输出每个评分点的 expected 与 actual 规范化结果。

常见错误包括相信 `mirror_status` 或 `legacy_category`，漏掉随机生成但仍匹配审查范围的记录，把 duplicate 计入 primary 分母，漏掉最近关闭项，把 due date 正好为观察日的 `WI-24024-S048` 算作逾期，对关闭项用 as-of 而不是 `closed_at` 判断逾期，或用 due date 而不是 created-to-effective-end 年龄计算 aging bucket。

迁移设计：`train_002` 和 `train_005` 是迁移锚点。它们提供 SLA 任务族的约定：开放项与最近关闭项合并，重复项不进入 primary 指标但要报告，SLA 范围沿用组合类别优先级，同日到期边界处理，缺少 owner 检查，以及 breach rate 计算。依赖迁移的评分点包括 seeded 和 legacy primary set、duplicate exclusion、overdue primary set、aging bucket、duplicate clusters、missing-owner ids 和 breach rate。本测试仍需要探索 Core Services 与 Platform Core 的具体匹配记录、10 天窗口、owner/team 计数，以及 `portfolio.db` 中的噪声生成记录。

构建记录：由 Codex 于 2026-07-18 为 `test_002` 创建。创建的文件包括 `input/prompt.txt`、`input/payloads/answer_template.json`、`notes/notes.md`、`output/answer.json`、`eval/eval.sh` 和 `eval/eval.py`。构建后已用标准答案运行评测器。
