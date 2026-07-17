# Construction and evaluation notes / 构建与评估说明

## English

### Lineage and task definition

- Task: `train_004`, owned by `task-builder-train-004`.
- Source scenario: `SCN_022_sql_database_analytics`; source examples: `E001`, `E002`, and `E003`.
- Design sources: `scratch/task_group_design.md` and `scratch/task_briefs/train_004.md`.
- Data source: the deterministic Atlas Commerce Operations SQLite dataset generated for `task_group_022`. Construction used the retained baseline read-only; solvers see the same business schema only through the authenticated service at `<TASK_ENV_BASE_URL>`.
- Task-local visible materials: `input/prompt.txt`, `input/payloads/warehouse_productivity_request.json`, and `input/payloads/answer_template.json`.

North Fulfillment Operations asks for a production-work health review for `WH-NORTH-01`. The creation window is inclusive from `2026-04-06T00:00:00Z` through `2026-04-12T23:59:59Z`, and operational state is evaluated at `2026-04-13T23:59:59Z`. The solver must return a single structured object with the eligible task total, completed units, employee productivity ranking, top productivity value, rework result, delayed high-priority set, bottom team, and facility classification. The task is observational; it requires no transaction or correction.

This belongs in the Atlas SQL analytics scenario because warehouse task headers, employee/team dimensions, and imported task events form a realistic operational flow: work is planned and assigned in `warehouse_tasks`, execution observations arrive in `warehouse_task_events`, employee ownership resolves through `employees`, and management decisions depend on cutoff-consistent aggregation rather than convenience snapshots.

### Material map and expected work

- `input/prompt.txt`: realistic business request, environment location, and output destination.
- `input/payloads/warehouse_productivity_request.json`: warehouse, inclusive creation bounds, cutoff, business metric definitions, ranking tie-breaks, and facility thresholds.
- `input/payloads/answer_template.json`: exact flat output schema, types, units, precision, enums, list uniqueness, and ordering; extra fields are disallowed.
- `GET /api/schema`: exposes table DDL, keys, and relevant indexes.
- `GET /api/data-dictionary`: explains timestamp, identifier, unit, source, and snapshot fields.
- `POST /api/sql`: supports the read-only exploration and final aggregation queries.
- `warehouse_tasks`: cohort, assignment, priority, due time, production class, and stale `current_status` snapshot.
- `warehouse_task_events`: append-only execution state, units, productive minutes, source identity, event time, and ingestion time.
- `employees`: maps assigned employees to stable team IDs.
- `warehouses`: identifies the requested facility.
- `output/answer.json`: reproducible standard answer.
- `eval/evaluator.py` and `eval/eval.sh`: eight atomic weighted checks and robust entry point.

The expected work is schema discovery, cohort validation, retry resolution, cutoff-state reconstruction, aggregation by facility/employee/team, stable ranking, delayed-set extraction, final-only rounding, and JSON validation. The solver-visible request supplies business facts but does not disclose the hidden source-resolution procedure.

### Exact hidden solution basis

Imported task-event copies are deduplicated by `(source_system, external_event_id)`, keeping the greatest `(ingested_at, task_event_id)`. From those effective imports at or before the cutoff, each task's state is its last event ordered by `(event_at, task_event_id)`. The eligible cohort is the 247 `warehouse_tasks` rows at `WH-NORTH-01` created within the inclusive request window with `work_class='PRODUCTION'`. This warehouse-work cohort does not add an account flag filter; 39 tasks have no order and warehouse eligibility is defined directly by the task record. Nineteen training rows in the same facility/window are not eligible.

The reusable SQL basis is:

```sql
WITH ranked_imports AS (
  SELECT e.*,
         ROW_NUMBER() OVER (
           PARTITION BY e.source_system, e.external_event_id
           ORDER BY e.ingested_at DESC, e.task_event_id DESC
         ) AS import_rank
  FROM warehouse_task_events AS e
),
effective_imports AS (
  SELECT *
  FROM ranked_imports
  WHERE import_rank = 1
    AND event_at <= '2026-04-13T23:59:59Z'
),
ranked_state AS (
  SELECT e.*,
         ROW_NUMBER() OVER (
           PARTITION BY e.task_id
           ORDER BY e.event_at DESC, e.task_event_id DESC
         ) AS state_rank
  FROM effective_imports AS e
),
task_state AS (
  SELECT * FROM ranked_state WHERE state_rank = 1
),
cohort AS (
  SELECT t.*, emp.team_id,
         s.event_type AS effective_status,
         s.units AS effective_units,
         s.productive_minutes AS effective_minutes
  FROM warehouse_tasks AS t
  JOIN employees AS emp
    ON emp.employee_id = t.assigned_employee_id
  JOIN task_state AS s
    ON s.task_id = t.task_id
  WHERE t.warehouse_id = 'WH-NORTH-01'
    AND t.created_at BETWEEN '2026-04-06T00:00:00Z'
                         AND '2026-04-12T23:59:59Z'
    AND t.work_class = 'PRODUCTION'
)
SELECT effective_status,
       COUNT(*) AS task_count,
       SUM(CASE WHEN effective_status = 'COMPLETED'
                THEN effective_units ELSE 0 END) AS completed_units,
       SUM(CASE WHEN effective_status = 'COMPLETED'
                THEN effective_minutes ELSE 0 END) AS completed_minutes
FROM cohort
GROUP BY effective_status
ORDER BY effective_status;
```

The effective state counts are 189 `COMPLETED`, 46 `IN_PROGRESS`, 5 `REWORK`, and 7 `STARTED`. Completed outcomes contribute 9,408 units and 11,982 productive minutes. Raw, undeduplicated completed event rows would incorrectly contribute 9,727 units, demonstrating that retry handling is material. Twenty-two eligible task snapshots disagree with their reconstructed state.

Employee units/hour is a ratio of sums, not an average of task-level rates: `60 * SUM(completed units) / SUM(completed productive minutes)`. The leading employee results are `EMP-0007` with `339 / 295 * 60 = 68.949152...`, `EMP-0006` with `509 / 477 * 60 = 64.025157...`, and `EMP-0008` with `803 / 873 * 60 = 55.189003...`; therefore the ordered top three are `[EMP-0007, EMP-0006, EMP-0008]` and the reported top value is `68.95`.

The rework result is `5 / 247 = 0.0202429...`, reported as count `5` and rate `0.0202`. Delayed high-priority selection uses priority in `{HIGH, URGENT}`, `due_at` strictly before the cutoff, and reconstructed status other than `COMPLETED`. The exact 41-ID set is the list in `output/answer.json`; its canonical display order is ascending `task_id`. Rework and unfinished `STARTED` outcomes remain delayed because neither is completed by cutoff.

Team completion rates are `55/73 = 0.753424...` for `WH-NORTH-01-TEAM-3`, `66/86 = 0.767441...` for team 1, and `68/88 = 0.772727...` for team 2. Team 3 is the unique lowest performer. Facility completion is `189/247 = 0.765182...` and rework is `5/247 = 0.0202429...`, so the second threshold applies and facility status is `PRESSURED`. Only final requested values are rounded.

### Atomic evaluation

The total raw weight is 17. Every point is whole-point pass/fail, with `assigned_score = weight / 17`; no point grants partial credit.

- `SP001`, weight 2: `eligible_production_task_count` is exactly integer 247.
- `SP002`, weight 3: `completed_production_units` is exactly integer 9408.
- `SP003`, weight 3: `top_three_employee_ids` is exactly the ordered three-ID ranking.
- `SP004`, weight 2: `top_employee_units_per_hour` is numeric and exactly 68.95 at the declared precision.
- `SP005`, weight 2: both `rework_task_count=5` and `rework_rate=0.0202` must pass together because they are one rework outcome.
- `SP006`, weight 3: `delayed_high_priority_task_ids` must be a duplicate-free string list whose normalized set equals the exact 41-task set. Order is normalized for scoring because the business outcome is a set, although the template requires ascending display order.
- `SP007`, weight 1: `lowest_performing_team_id` is exactly `WH-NORTH-01-TEAM-3`.
- `SP008`, weight 1: `facility_status` is exactly enum value `PRESSURED`.

An unreadable, invalid, or non-object candidate fails all points without a traceback. Valid objects are checked point by point so an ordinary error affects only its associated business outcome. Numeric values reject booleans and non-finite values.

Likely pitfalls are trusting `current_status`, counting retry copies, including training work, treating `REWORK` units/minutes as completed production, missing events at the inclusive cutoff, averaging task rates instead of using the ratio of sums, rounding before employee aggregation, treating only `IN_PROGRESS` as delayed, applying an unrelated account filter, ranking teams by raw completed count, or omitting the stable-ID tie-break.

### Transfer design and construction record

Solving this real train task and comparing with its answer exposes a reusable operating pattern: discover the relational model, resolve source retries by stable import identity, reconstruct task state at a cutoff, distinguish production from training and rework, aggregate numerator and denominator consistently, count stable task IDs, and use deterministic tie-breaks. These are the planned `C1`, `C3`, `C6`, and `C8` signals for later warehouse and broader effective-state tasks.

Transfer-dependent difficulty is not required from an earlier anchor because this is itself a train task; it establishes the anchor. Task-specific exploration difficulty remains substantial: finding the task/event/employee relationships, confirming event vocabulary and source retry behavior, validating the weekly cohort, deriving the 41-ID delayed set, and applying the facility thresholds. Later tasks can transfer the state/deduplication/productivity method while still exploring different warehouses, windows, cutoffs, and requested outcomes.

- Author: `task-builder-train-004`
- Created: `2026-07-16`
- Updated: `2026-07-16`
- Major changes: initial task materials, retained-baseline answer derivation, eight-point evaluator, full-score check, and independent sensitivity validation.

## 中文

### 数据血缘与任务定义

- 任务为 `train_004`，负责人为 `task-builder-train-004`。
- 来源场景为 `SCN_022_sql_database_analytics`，来源样例为 `E001`、`E002`、`E003`；设计依据为 `scratch/task_group_design.md` 与 `scratch/task_briefs/train_004.md`。
- 数据来自为 `task_group_022` 确定性生成的 Atlas Commerce Operations SQLite 数据集。构建阶段只读分析了保留的基线；求解器只能通过 `<TASK_ENV_BASE_URL>` 上经过认证的服务访问同一业务模式。
- 求解器可见的本地材料是 `input/prompt.txt`、`input/payloads/warehouse_productivity_request.json` 和 `input/payloads/answer_template.json`。

业务背景是 North Fulfillment Operations 需要审查 `WH-NORTH-01` 的生产作业健康度。任务创建时间窗为 `2026-04-06T00:00:00Z` 至 `2026-04-12T23:59:59Z`，两端均包含；状态截止时间为 `2026-04-13T23:59:59Z`。输出包括合格任务数、完成单位数、员工生产率排名、第一名生产率、返工结果、延误高优先级任务集合、最低团队以及设施状态。本任务只读，不需要事务或数据修正。

该任务符合 Atlas SQL 分析场景：`warehouse_tasks` 表示计划和分配，`warehouse_task_events` 表示从业务源导入的执行事件，`employees` 提供员工到团队的关系；管理结论必须由截止时点一致的事件状态与聚合产生，不能直接依赖便利快照。

### 材料映射与预期工作

- `input/prompt.txt` 给出真实业务请求、环境位置和输出位置。
- `warehouse_productivity_request.json` 给出仓库、含边界的创建窗口、截止时间、指标公式、排序规则和设施阈值。
- `answer_template.json` 规定精确的扁平 JSON 字段、类型、单位、精度、枚举、列表唯一性与稳定顺序，并禁止额外字段。
- `GET /api/schema` 用于发现表、键和索引；`GET /api/data-dictionary` 用于理解时间、标识符、单位、来源字段和快照字段；`POST /api/sql` 用于只读探索和聚合。
- 关键表为 `warehouse_tasks`、`warehouse_task_events`、`employees` 和 `warehouses`；标准答案位于 `output/answer.json`，评估入口为 `eval/eval.sh`。

预期工作包括模式发现、群组核验、重试副本消解、截止状态重建、按设施/员工/团队聚合、稳定排序、延误集合提取、仅对最终值舍入以及 JSON 校验。可见请求提供业务定义，但不泄露隐藏的来源优先级过程。

### 精确隐藏解法与计算

事件首先按 `(source_system, external_event_id)` 去重，并保留 `(ingested_at, task_event_id)` 最大的导入副本；再从截止时间之前的有效导入中，按 `(event_at, task_event_id)` 选择每个任务的最后事件。上文英文部分的 SQL 是可复现的标准查询基础。

合格群组是指定仓库和含边界创建窗口内 `work_class='PRODUCTION'` 的 247 个任务。该直接仓库作业群组不增加账户标志过滤；其中 39 个任务没有订单。相同仓库和窗口内的 19 个培训任务不合格。有效状态分布为 189 个 `COMPLETED`、46 个 `IN_PROGRESS`、5 个 `REWORK` 和 7 个 `STARTED`。完成结果贡献 9,408 个单位和 11,982 分钟。若不去重，错误的完成单位数会是 9,727；另有 22 个合格任务的 `current_status` 与重建状态不同。

员工每小时单位数使用总量之比：`60 * 完成单位总数 / 对应生产分钟总数`，而不是任务级比率的平均。前三名依次是 `EMP-0007`（`339/295*60=68.949152...`）、`EMP-0006`（`509/477*60=64.025157...`）和 `EMP-0008`（`803/873*60=55.189003...`），因此报告第一名为 `68.95`。

返工结果为 `5/247=0.0202429...`，最终输出数量 5、比率 `0.0202`。延误集合要求优先级为 `HIGH` 或 `URGENT`、`due_at` 严格早于截止时间、重建状态不是 `COMPLETED`，精确的 41 个 ID 见 `output/answer.json`，展示时按 `task_id` 升序。`REWORK` 和未结束的 `STARTED` 都未完成，因此仍属于延误。

三个团队的完成率分别为 team 3 的 `55/73=0.753424...`、team 1 的 `66/86=0.767441...` 和 team 2 的 `68/88=0.772727...`，所以最低团队唯一确定为 `WH-NORTH-01-TEAM-3`。设施完成率为 `189/247=0.765182...`，返工率为 `5/247=0.0202429...`，符合第二档规则，状态为 `PRESSURED`。只对最终要求的数值进行舍入。

### 原子评估

原始总权重为 17，每个评分点只能全得或零分，分配分值为 `weight/17`。

- `SP001`，权重 2：合格生产任务数必须为整数 247。
- `SP002`，权重 3：有效完成生产单位数必须为整数 9408。
- `SP003`，权重 3：前三员工 ID 必须与有序排名完全一致。
- `SP004`，权重 2：第一名每小时单位数必须为数值 `68.95`。
- `SP005`，权重 2：返工数 5 与四位小数返工率 `0.0202` 必须同时正确，这是同一个返工业务结果。
- `SP006`，权重 3：延误高优先级 ID 必须是无重复字符串列表，归一化后的集合精确等于 41 个标准 ID；评分忽略集合展示顺序，但模板要求升序。
- `SP007`，权重 1：最低团队必须为 `WH-NORTH-01-TEAM-3`。
- `SP008`，权重 1：设施状态枚举必须为 `PRESSURED`。

不可读、无效或顶层非对象的候选答案全部得零且不产生回溯。普通业务错误只影响对应的原子评分点。数值校验拒绝布尔值和非有限数。常见错误包括信任 `current_status`、重复计算重试副本、纳入培训任务、把 `REWORK` 的单位或分钟计入完成生产、遗漏含边界截止事件、平均任务级速率、提前舍入、只把 `IN_PROGRESS` 视为延误、添加无关账户过滤、按完成绝对数排名团队或遗漏稳定 ID 决胜规则。

### 迁移设计与构建记录

通过求解本训练任务并与答案对照，可以归纳出可迁移流程：发现关系模式、用稳定来源标识消解导入重试、重建截止状态、区分生产/培训/返工、保持分子分母一致、按稳定任务 ID 计数以及使用确定性决胜规则。这正是计划中的 `C1`、`C3`、`C6`、`C8` 训练信号。

本任务本身是训练锚点，因此不依赖更早训练任务的迁移知识。任务特定探索仍然较难：需要找到任务、事件和员工的关系，确认事件词汇及重试模式，核验周群组，推导 41 个延误 ID，并应用设施阈值。后续任务可以迁移状态、去重与生产率方法，同时仍需探索不同仓库、时间窗、截止点和输出结果。

- 作者：`task-builder-train-004`
- 创建日期：`2026-07-16`
- 更新日期：`2026-07-16`
- 主要变更：首次创建任务材料，基于保留基线推导答案，实现八点评估器，并进行满分和独立敏感性验证。
