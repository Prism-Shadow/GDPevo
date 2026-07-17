# Warehouse Recovery and Carrier-Cutoff Plan — Construction Notes

## English record

### Lineage, task definition, and scenario fit

This is the unseen integrated test task `test_005`, owned by `task-builder-test-005`, for scenario `SCN_022_sql_database_analytics` in `task_group_022`. Its source examples are `E001` (relational business aggregation), `E002` (stateful database reconciliation and correction conventions), and `E003` (tool-mediated operational analysis). The immediate design sources are `scratch/task_group_design.md`, `scratch/task_briefs/test_005.md`, the generated Atlas Commerce Operations environment, and the task-local recovery request and answer contract.

Construction used the retained `env/atlas_baseline.sqlite3` database read-only. Solvers receive no database file; they see the runtime only through `<TASK_ENV_BASE_URL>`. The visible request covers `WH-WEST-01` and `WH-CENTRAL-01`, production work created from `2026-06-22T00:00:00Z` through `2026-06-28T23:59:59Z`, a state cutoff of `2026-06-28T20:00:00Z`, a carrier-cutoff assessment at `2026-06-28T22:00:00Z`, and a 12-hour recovery horizon ending `2026-06-29T08:00:00Z`.

The expected work is to discover the schema, construct a production-demand task cohort that exists at the cutoff, reconcile imported event retries, reconstruct task/order/shipment/support state, calculate employee throughput from completed work, project facility recovery capacity, rank facilities and workers, apply local warehouse clocks to carrier exposure, link exposed orders to active severe support cases, and select controlled action/status enums. This is a realistic post-disruption command workflow: planned warehouse work is tied to employees and sometimes orders; execution events determine backlog; shipments and carrier observations determine customer exposure; support cases attach customer risk; and the resulting integrated rollup drives labor and carrier intervention.

### Material map

- `input/prompt.txt`: the recovery-command business request, runtime service location, read-only scope, and output destination.
- `input/payloads/recovery_request.json`: facilities, inclusive task window, state cutoff, adjusted carrier checkpoint, recovery horizon, task/capacity/exposure/support definitions, ranking rules, rounding, and action/status policies.
- `input/payloads/answer_template.json`: exact required keys and nested object shapes, types, units, precisions, list lengths, stable identifiers, ordering, and allowed enums; extra object fields are disallowed.
- `GET /api/schema`: table DDL, foreign keys, stable IDs, and indexes.
- `GET /api/data-dictionary`: timestamps, unit fields, normalized carrier observations, imported-source identity, and stale convenience-state context.
- `POST /api/sql`: all read-only exploration and analytical queries. This task does not use the transaction or correction-audit endpoints.
- `warehouses` and `employees`: facility timezone/cutoff facts and employee facility/active-interval facts.
- `warehouse_tasks` and `warehouse_task_events`: task scope, assignment, planned units, production class, imported lifecycle events, completed units, and productive minutes.
- `accounts`, `orders`, and `order_events`: production-demand flags, order linkage, and effective cancellation state for order-linked work.
- `shipments` and `carrier_scans`: physical order shipments and effective normalized delivery state.
- `support_cases` and `case_events`: order-linked priority and cutoff-active/reopened case state.
- `output/answer.json`: the reproducible hidden standard answer.
- `eval/eval.sh` and `eval/evaluator.py`: robust entry point and eight atomic weighted business-result checks.

### Cohort adjustment and exact hidden solution basis

The brief's original carrier condition was degenerate in the retained baseline. At `2026-06-28T20:00:00Z`, Central local time is 15:00 against a 16:45 cutoff and West local time is 13:00 against a 16:00 cutoff, so neither cutoff has passed and both `SP005` and `SP006` would be trivially empty. Under the common builder contract, the smallest task-local adjustment is a carrier assessment checkpoint two hours later at `2026-06-28T22:00:00Z`; all task, order, shipment, and support state remains fixed at the assigned 20:00Z cutoff. At the checkpoint, Central is 17:00 local and has passed 16:45, while West is 15:00 local and has not passed 16:00. The request explicitly exposes this checkpoint fact without exposing the event-reconciliation SOP.

Post-construction calibration exposed a separate genuine wording ambiguity. All three base and all three fewshot GPT-5.5/xhigh attempts read the former phrase “order-linked work must represent production demand that remains active at the state cutoff” as excluding an unfinished warehouse task whenever the linked order's lifecycle state was `DELIVERED`. Each attempt consequently reported only 25 backlog tasks and 1,050 planned units, and the error propagated through every downstream outcome. The visible definition now states the intended business scope directly: order-linked work must belong to a production account, effective `CANCELLED` demand is excluded at the cutoff, and an unfinished warehouse task is not removed merely because the linked order lifecycle is `DELIVERED`. This is a request fact about which operating work the recovery command wants counted. It does not reveal how event copies are reconciled, how the effective state is reconstructed, or which source wins, so the transferable SOP remains hidden. No hidden calculation or expected output changed.

Imported task, order, carrier, and case events are each deduplicated by `(source_system, external_event_id)`, retaining the row with greatest `(ingested_at, stable row ID)`. The retained baseline has 105,000 task-event rows for 101,000 effective import keys, 65,000 order-event rows for 62,400 keys, 80,000 carrier scans for 76,000 keys, and 28,000 case-event rows for 26,800 keys. For each task/order/case, cutoff state is the last effective event ordered by `(event_at, stable event ID)`; shipment state uses `(canonical_event_at, scan_row_id)`. Events after the state cutoff do not affect this report.

The initial facility/window population that exists by the state cutoff has 483 production-class task rows: 240 Central and 243 West. Tasks created after 20:00Z, although inside the wider supplied window, do not yet exist in the point-in-time population. Thirty-eight training rows in the same facilities/window before the cutoff are not production work. For order-linked tasks, internal/test demand and orders effectively `CANCELLED` at cutoff are excluded; `DELIVERED` order lifecycle state does not remove a warehouse task that is still unfinished, and unlinked facility production work remains eligible. The linked-demand rules exclude 13 Central and 16 West rows, leaving 227 eligible tasks in each facility. Fifty-four eligible task header snapshots disagree with reconstructed state, so `current_status` is not authoritative.

Effective eligible task state is:

| Warehouse | COMPLETED | CREATED | IN_PROGRESS | REWORK | STARTED | Backlog tasks | Backlog units |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| WH-CENTRAL-01 | 164 | 3 | 43 | 9 | 8 | 63 | 2,881 |
| WH-WEST-01 | 164 | 2 | 40 | 10 | 11 | 63 | 2,959 |
| Total | 328 | 5 | 83 | 19 | 19 | 126 | 5,840 |

Only final `COMPLETED` production outcomes contribute units and productive minutes. `REWORK` is an unfinished separate outcome and remains backlog. For every active employee, units per hour is the ratio of summed completed units to summed productive minutes multiplied by 60, not an average of task-level rates. The top three unrounded results used for capacity are:

| Warehouse | Employee | Completed units | Productive minutes | Units/hour |
| --- | --- | ---: | ---: | ---: |
| WH-CENTRAL-01 | EMP-0090 | 603 | 623 | 58.0738362761 |
| WH-CENTRAL-01 | EMP-0077 | 295 | 311 | 56.9131832797 |
| WH-CENTRAL-01 | EMP-0088 | 586 | 646 | 54.4272445820 |
| WH-WEST-01 | EMP-0051 | 848 | 852 | 59.7183098592 |
| WH-WEST-01 | EMP-0040 | 456 | 530 | 51.6226415094 |
| WH-WEST-01 | EMP-0046 | 374 | 446 | 50.3139013453 |

`EMP-0054` is not active because its interval ended on `2026-04-30T23:59:59Z`; all six capacity workers listed above are active at the state cutoff. Central projected capacity is `12 * (58.0738362761 + 56.9131832797 + 54.4272445820) = 2032.9711696544` units. West projected capacity is `12 * (59.7183098592 + 51.6226415094 + 50.3139013453) = 1939.8582325666` units. Both are below facility backlog, so recoverable units equal those capacities. The final total is `3972.83`. Unrounded coverage is `2032.9711696544 / 2881 = 0.7056477507` for Central and `1939.8582325666 / 2959 = 0.6555789904` for West, producing the requested ranking and displayed values `0.7056`, `0.6556`. Aggregate unrounded coverage is `3972.8294022210 / 5840 = 0.6802790072`.

Central has 46 distinct production orders linked to backlog. Thirteen have an effectively delivered shipment, leaving 33 exposed orders after the Central cutoff passes. West has 50 distinct backlog-linked orders and 40 with no effective delivered shipment, but none is exposed because the West cutoff has not passed at the assessment checkpoint. The exact exposed set is the ascending 33-ID list in `output/answer.json`.

The exposure evidence is materially event-derived. For example, Central backlog task `WT-018910` links to `ORD-010636`. Shipment `SHP-010173` has a stale delivered header, but its last effective carrier observation by canonical event time is `OUT_FOR_DELIVERY`, later than the imported `DELIVERED` observation. Support case `CASE-005556` links to `ORD-010636`, has priority `URGENT`, a stale `RESOLVED` header, and a final effective case event of `ESCALATED`; it is therefore active and is the sole severe linked case. Counting stable case IDs gives `severe_linked_support_escalation_count = 1`.

Because severe count is positive and aggregate projected coverage is below 0.80, the action is `REALLOCATE_AND_EXPEDITE`. Aggregate coverage is below 0.80, so the recovery status is `CRITICAL`.

The core standard-answer SQL basis is reproducible as follows; exposure and support CTEs continue the same pattern for their event families:

```sql
WITH
p AS (SELECT '2026-06-28T20:00:00Z' AS cutoff),
order_imports AS (
  SELECT e.*,
         ROW_NUMBER() OVER (
           PARTITION BY source_system, external_event_id
           ORDER BY ingested_at DESC, event_id DESC
         ) AS import_rank
  FROM order_events e
),
order_states AS (
  SELECT e.*,
         ROW_NUMBER() OVER (
           PARTITION BY order_id ORDER BY event_at DESC, event_id DESC
         ) AS state_rank
  FROM order_imports e, p
  WHERE import_rank = 1 AND event_at <= cutoff
),
task_imports AS (
  SELECT e.*,
         ROW_NUMBER() OVER (
           PARTITION BY source_system, external_event_id
           ORDER BY ingested_at DESC, task_event_id DESC
         ) AS import_rank
  FROM warehouse_task_events e
),
task_states AS (
  SELECT e.*,
         ROW_NUMBER() OVER (
           PARTITION BY task_id ORDER BY event_at DESC, task_event_id DESC
         ) AS state_rank
  FROM task_imports e, p
  WHERE import_rank = 1 AND event_at <= cutoff
),
eligible AS (
  SELECT t.*, s.event_type AS effective_status,
         s.units AS effective_units,
         s.productive_minutes AS effective_minutes
  FROM warehouse_tasks t
  LEFT JOIN task_states s ON s.task_id = t.task_id AND s.state_rank = 1
  LEFT JOIN orders o ON o.order_id = t.order_id
  LEFT JOIN accounts a ON a.account_id = o.account_id
  LEFT JOIN order_states os ON os.order_id = o.order_id AND os.state_rank = 1
  CROSS JOIN p
  WHERE t.warehouse_id IN ('WH-WEST-01', 'WH-CENTRAL-01')
    AND t.created_at BETWEEN '2026-06-22T00:00:00Z' AND cutoff
    AND t.work_class = 'PRODUCTION'
    AND (
      t.order_id IS NULL OR
      (a.is_internal = 0 AND a.is_test = 0
       AND COALESCE(os.event_type, '') <> 'CANCELLED')
    )
),
employee_rollup AS (
  SELECT e.warehouse_id, e.assigned_employee_id AS employee_id,
         SUM(CASE WHEN effective_status = 'COMPLETED'
                  THEN effective_units ELSE 0 END) AS units,
         SUM(CASE WHEN effective_status = 'COMPLETED'
                  THEN effective_minutes ELSE 0 END) AS minutes
  FROM eligible e
  JOIN employees emp ON emp.employee_id = e.assigned_employee_id
  CROSS JOIN p
  WHERE emp.active_from <= cutoff
    AND (emp.active_to IS NULL OR emp.active_to >= cutoff)
  GROUP BY e.warehouse_id, e.assigned_employee_id
)
SELECT warehouse_id, effective_status, COUNT(*) AS tasks,
       SUM(planned_units) AS planned_units
FROM eligible
GROUP BY warehouse_id, effective_status
ORDER BY warehouse_id, effective_status;
```

Carrier scans are deduplicated before choosing the last `canonical_event_at` state per shipment. Distinct backlog order IDs are rolled up so an order qualifies only when the count of effectively delivered shipments is zero. The 22:00Z checkpoint activates only the Central subset. Case events are independently deduplicated and ranked; priority is taken from `support_cases`, and a case is active when the last effective event is not `RESOLVED`. All counts use stable task, order, shipment, employee, or case IDs at their business grain. Only final displayed numbers are rounded.

### Output contract, atomic evaluation, and pitfalls

The output contains exactly eight business outcomes. `facility_recovery_ranking` has two objects in coverage order; `employee_candidates_by_facility` has two facility objects in warehouse-ID order and exactly two ranked employees each; the exposed IDs are unique and displayed ascending. Numeric JSON booleans and non-finite values are rejected by the evaluator.

The evaluator has raw total weight 18, and every point earns exactly `weight / 18` or zero:

- `SP001`, weight 3: both `backlog_summary.task_count = 126` and `backlog_summary.planned_units = 5840` must pass together as one backlog outcome.
- `SP002`, weight 3: `total_projected_recoverable_units = 3972.83`.
- `SP003`, weight 2: the exact ordered facility sequence and both four-decimal projected coverage values must match.
- `SP004`, weight 2: both facility objects, all four employee IDs, their order, and all two-decimal rates must match.
- `SP005`, weight 3: the candidate must be a duplicate-free string list whose normalized set equals the exact 33 exposed order IDs. Template display order remains ascending.
- `SP006`, weight 2: `severe_linked_support_escalation_count = 1`.
- `SP007`, weight 2: `recommended_action = REALLOCATE_AND_EXPEDITE`.
- `SP008`, weight 1: `recovery_status = CRITICAL`.

The points cover backlog, projected capacity, facility prioritization, labor candidates, order exposure, linked support risk, operational action, and recovery judgment as distinct business conclusions. An unreadable or non-object candidate fails all eight without a traceback. Ordinary business errors fail only their owning point. The standard answer self-scores 1.0. Independent sensitivity checks change one backlog numeric value (only `SP001` fails, score `15/18`), swap the facility ranking (only `SP003` fails, score `16/18`), and change the action enum (only `SP007` fails, score `16/18`).

Likely pitfalls are counting tasks created after the state cutoff; including training work; including internal/test or effectively cancelled linked demand; removing an unfinished task merely because its linked order lifecycle is `DELIVERED`; dropping legitimate unlinked facility work; trusting any denormalized `current_status`; counting retry imports; treating `REWORK` as completed; summing every completed event rather than final completed outcomes; using inactive `EMP-0054`; overlooking active high-throughput `EMP-0051`; averaging task-level rates; using two rather than three employees for capacity; rounding rates before projection or ranking; applying warehouse cutoffs in UTC; using the state cutoff instead of the adjusted carrier checkpoint for the local-clock test; using order-header warehouse instead of the backlog task facility; treating any historical delivered scan as final delivery; counting event rows rather than order/case IDs; treating stale resolved support headers as final; or applying action/status rules to rounded facility coverage rather than aggregate unrounded coverage.

### Transfer design: anchors versus exploration

The explicit train anchors are `train_001`, `train_004`, and `train_005`.

- `train_001` anchors production-account and effective cancellation exclusions for `SP001`, and effective shipment state/all-child order reasoning for `SP005`; the test-local request separately defines that delivered order lifecycle alone does not close unfinished warehouse work.
- `train_004` anchors task-event retry resolution, cutoff task state, production-versus-training/rework handling, completed-unit/productive-minute aggregation, final-only rounding, and stable employee ranking. These directly support `SP001`, `SP002`, `SP003`, and `SP004`.
- `train_005` anchors case-event retry resolution and the rule that active/reopened severe cases remain open until a later effective resolution. This directly supports `SP006`.
- `SP007` integrates transfer-dependent backlog/capacity/exposure/support outcomes. `SP008` depends on the transferred aggregation discipline plus this request's new threshold policy.

Transfer-dependent difficulty is recognizing source-copy identity, reconstructing point-in-time state instead of trusting snapshots, maintaining the correct stable business grain, applying production/cancellation eligibility to linked demand, separating rework from completion, calculating a ratio of sums, checking active employee intervals, and handling reopened support state. A solver can infer these habits from the three real train tasks without the test prompt restating the hidden SOP.

Task-specific exploration difficulty is separate: the solver must discover this June West/Central cohort, notice that the creation window extends past the state cutoff, calculate a three-worker 12-hour capacity rather than the train task's reported rate, convert the 22:00Z checkpoint into two facility-local clocks, associate carrier exposure with the backlog task facility, derive the new 33-order set, find the stale-state `CASE-005556` linkage, and apply the new action/status rules. Exact IDs and values are not transferable from train answers.

### Construction record

- Author: `task-builder-test-005`
- Created: `2026-07-16`
- Updated: `2026-07-16`
- Major changes: created the recovery request and exact output contract; made the minimal non-degenerate carrier-checkpoint adjustment; derived the standard answer from the retained baseline; implemented eight atomic weighted checks; validated full score and three independent mutations; clarified the production-demand scope after six calibration attempts consistently treated `DELIVERED` order lifecycle as removing unfinished warehouse work.

## 中文记录

### 来源、任务定义与场景适配

本任务是 `task_group_022` 中的未见测试任务 `test_005`，负责人为 `task-builder-test-005`，来源场景为 `SCN_022_sql_database_analytics`，来源样例为 `E001`、`E002`、`E003`。直接设计依据包括 `scratch/task_group_design.md`、`scratch/task_briefs/test_005.md`、Atlas Commerce Operations 共享环境以及本任务的恢复请求和答案模板。构建阶段只读使用保留的 `env/atlas_baseline.sqlite3`；求解器不会获得数据库文件，只能通过 `<TASK_ENV_BASE_URL>` 查询运行环境。

业务要求在 2026 年 6 月 28 日运营中断后，为 `WH-WEST-01` 与 `WH-CENTRAL-01` 生成恢复视图。任务创建窗口为 `2026-06-22T00:00:00Z` 至 `2026-06-28T23:59:59Z`，状态截止时间为 `2026-06-28T20:00:00Z`，承运商截单评估时点为 `2026-06-28T22:00:00Z`，12 小时恢复窗口结束于 `2026-06-29T08:00:00Z`。求解过程需要发现关系模式、建立截止时点生产需求任务群组、处理重复导入、重建任务/订单/发运/支持状态、计算员工吞吐和设施产能、进行稳定排序、转换本地时区、连接订单支持风险并输出动作与状态枚举。

这符合真实恢复指挥流程：仓库任务连接员工和订单，执行事件决定积压，发运与承运商扫描决定客户暴露，支持工单体现客户风险，最终的跨域汇总驱动劳动力重分配和承运商加急。

### 材料与接口用途

- `input/prompt.txt` 给出业务目标、运行服务入口、只读范围和输出位置。
- `recovery_request.json` 给出设施、时间范围、状态截止、调整后的承运商检查点、恢复窗口、指标定义、排序、舍入和政策规则。
- `answer_template.json` 规定精确键、嵌套结构、类型、单位、精度、列表长度、稳定标识、顺序和枚举，禁止对象额外字段。
- `/api/schema` 和 `/api/data-dictionary` 用于发现表、关系、时间、单位、来源字段、规范化承运商字段和便利快照语义；`/api/sql` 用于全部只读分析。
- 核心表为 `warehouses`、`employees`、`warehouse_tasks`、`warehouse_task_events`、`accounts`、`orders`、`order_events`、`shipments`、`carrier_scans`、`support_cases` 与 `case_events`。
- `output/answer.json` 是隐藏标准答案；`eval/eval.sh` 与 `evaluator.py` 实现八个原子加权结果检查。

### 群组调整与隐藏解答依据

原简报中的承运商条件在保留基线上会退化：20:00Z 时 Central 为本地 15:00，尚未超过 16:45；West 为本地 13:00，尚未超过 16:00，因此订单暴露与支持关联都会为空。按照共同构建合同，最小任务本地调整是把承运商截单评估设为两小时后的 22:00Z，同时任务、订单、发运和支持状态仍严格固定在 20:00Z。此时 Central 为 17:00，已超过 16:45；West 为 15:00，仍未超过 16:00。可见请求只公开这个任务事实，不公开事件消解流程。

构建后的校准还发现了一处真实措辞歧义。三次 base 与三次 fewshot 的 GPT-5.5/xhigh 尝试都把原来的“订单关联工作必须代表在状态截止时仍然活动的生产需求”理解为：只要关联订单生命周期在截止时为 `DELIVERED`，未完成仓库任务也应排除。六次尝试因此都只报告 25 个积压任务与 1,050 个计划单位，并使所有下游结果一起失败。现在可见定义直接说明预期业务范围：订单关联工作必须属于生产账户；截止时有效状态为 `CANCELLED` 的需求排除；未完成仓库任务不会仅因关联订单生命周期为 `DELIVERED` 而移除。这是恢复指挥部门对“哪些运营工作要计入”的请求事实，不说明事件副本如何消解、有效状态如何重建或哪个来源优先，因此没有泄露可迁移 SOP。隐藏计算与期望答案均未改变。

任务、订单、承运商和工单事件分别按 `(source_system, external_event_id)` 去重，保留 `(ingested_at, 稳定行 ID)` 最大的导入副本，再按业务事件时间与稳定事件 ID 选择截止前最后状态。全库 105,000 条任务事件对应 101,000 个有效导入键；65,000 条订单事件对应 62,400 个；80,000 条扫描对应 76,000 个；28,000 条工单事件对应 26,800 个。

在截止时点已存在的设施/窗口生产类任务共有 483 个：Central 240 个，West 243 个。窗口内但 20:00Z 后才创建的任务尚不属于点时群组。同范围截止前另有 38 个培训任务，不属于生产工作。订单关联任务需要排除内部/测试需求以及截止时有效取消的订单；订单生命周期为 `DELIVERED` 不会移除仍未完成的仓库任务，没有订单的合法设施生产任务也保留。Central 排除 13 个，West 排除 16 个，最终两设施各有 227 个合格任务。54 个合格任务的头表快照与事件重建状态不一致。

Central 有 164 个完成、3 个创建、43 个进行中、9 个返工、8 个已开始，因此积压 63 个、2,881 单位。West 有 164 个完成、2 个创建、40 个进行中、10 个返工、11 个已开始，因此积压 63 个、2,959 单位。合计积压为 126 个任务、5,840 单位。返工不是完成结果，仍属于积压。

员工速度按有效完成生产结果的总单位除以对应生产分钟再乘以 60，不能平均任务级速度。Central 的前三名为 `EMP-0090`（603/623，58.0738362761）、`EMP-0077`（295/311，56.9131832797）、`EMP-0088`（586/646，54.4272445820）；West 的前三名为 `EMP-0051`（848/852，59.7183098592）、`EMP-0040`（456/530，51.6226415094）、`EMP-0046`（374/446，50.3139013453）。`EMP-0054` 已于 4 月 30 日结束活动期，不能入选；上述六名产能员工在截止时均为活动状态。

Central 12 小时产能为 2032.9711696544，West 为 1939.8582325666，都小于设施积压，因此总可恢复单位为 `3972.83`。未舍入覆盖率分别为 Central 的 0.7056477507 和 West 的 0.6555789904，展示为 `0.7056`、`0.6556`，总体未舍入覆盖率为 `3972.8294022210 / 5840 = 0.6802790072`。

Central 有 46 个不同订单连接积压，其中 13 个存在有效已送达发运，剩余 33 个在 Central 截单已过后暴露。West 有 50 个积压关联订单，其中 40 个没有有效已送达发运，但由于 West 截单未过，它们不属于暴露集合。完整 33 个升序订单 ID 位于 `answer.json`。

具体证据 `WT-018910` 把 Central 积压连接到 `ORD-010636`。该订单的 `SHP-010173` 发运头显示已送达，但按规范事件时间的最后有效扫描是晚于送达观察的 `OUT_FOR_DELIVERY`，因此截止状态不是已送达。`CASE-005556` 连接该订单，优先级为 `URGENT`；头表错误显示 `RESOLVED`，而最后有效事件为 `ESCALATED`，所以它是唯一严重活动工单，计数为 1。

严重工单数大于 0 且总体覆盖率低于 0.80，因此建议动作是 `REALLOCATE_AND_EXPEDITE`；总体覆盖率低于 0.80，因此恢复状态是 `CRITICAL`。所有计数都使用稳定业务 ID，只对最终展示值舍入。英文部分的 SQL 给出可复现的任务/订单/员工核心查询；承运商和工单按同样的先去重、再截止排序模式处理。

### 原子评分与常见风险

评分共有八点，原始权重合计 18，每点只能完整获得 `weight/18` 或零分：

- `SP001`，权重 3：同时核对积压任务数 126 与计划单位 5,840。
- `SP002`，权重 3：核对总可恢复单位 `3972.83`。
- `SP003`，权重 2：核对两个设施的精确顺序和四位小数覆盖率。
- `SP004`，权重 2：核对两个设施、四名员工、员工顺序和两位小数速度。
- `SP005`，权重 3：核对无重复的完整 33 个暴露订单集合；模板要求升序展示，评分按集合归一化。
- `SP006`，权重 2：核对严重关联支持工单数 1。
- `SP007`，权重 2：核对建议动作 `REALLOCATE_AND_EXPEDITE`。
- `SP008`，权重 1：核对恢复状态 `CRITICAL`。

不可读取或顶层非对象答案稳定得到零分且不产生回溯；普通业务错误只影响对应原子点。标准答案得分 1.0。独立敏感性检查分别修改一个积压数值（只失败 `SP001`，得分 `15/18`）、交换设施排名（只失败 `SP003`，得分 `16/18`）和修改动作枚举（只失败 `SP007`，得分 `16/18`）。

常见错误包括：把状态截止后的任务计入积压；纳入培训、内部/测试或有效取消需求；仅因关联订单生命周期为 `DELIVERED` 就移除未完成任务；错误删除无订单设施任务；信任 `current_status`；重复计算导入副本；把返工当完成；使用所有历史完成事件；纳入已离职 `EMP-0054`；遗漏活动且高吞吐的 `EMP-0051`；平均任务速度；只用两名员工计算产能；提前舍入；按 UTC 比较本地截单；用 20:00Z 而不是 22:00Z 做截单评估；使用订单头仓库而不是积压任务设施；把任何历史送达观察当最终状态；按事件行数而不是订单/工单 ID 计数；以及用舍入后的设施覆盖率应用总体政策。

### 迁移锚点与任务特定探索的分离

明确训练锚点为 `train_001`、`train_004`、`train_005`。`train_001` 为 `SP001` 提供生产账户与有效取消排除经验，为 `SP005` 提供发运有效状态和订单汇总经验；测试任务本地请求另外定义了订单已送达本身不会关闭未完成仓库工作。`train_004` 为 `SP001` 至 `SP004` 提供任务导入去重、截止状态、生产/培训/返工区分、完成单位与分钟聚合、只在最终舍入以及稳定员工排序经验。`train_005` 为 `SP006` 提供工单导入去重、活动/重开状态直到后续解决的经验。`SP007` 集成上述迁移结果，`SP008` 结合迁移聚合习惯与新阈值政策。

迁移依赖难点是识别来源副本身份、重建点时状态、拒绝陈旧快照、维持稳定业务粒度、对订单关联任务应用生产与取消资格、区分返工和完成、使用总量之比、检查员工活动区间以及处理重开工单。可见测试请求不重新列出这些隐藏流程，求解器应从三个真实训练任务中推断。

任务特定探索难点则是发现本次六月两设施群组、注意创建窗口晚于状态截止、用三名员工投影 12 小时产能、把 22:00Z 转为两个本地时钟、用积压任务设施判断截单、推导新的 33 订单集合、找到陈旧状态的 `CASE-005556`，并应用新的动作/状态规则。训练答案不能直接提供这些精确 ID 和数值。

### 构建记录

- 作者：`task-builder-test-005`
- 创建日期：`2026-07-16`
- 更新日期：`2026-07-16`
- 主要变更：创建真实恢复请求与严格答案模板；进行最小非退化承运商检查点调整；从保留基线推导标准答案；实现八个原子加权评分点；完成满分与三项独立敏感性验证；在六次校准尝试一致把 `DELIVERED` 订单生命周期理解为移除未完成仓库工作后，澄清生产需求范围。
