# May Peak Delivery Reliability — Construction Notes

## English record

### Lineage, task definition, and scenario fit

This unseen test task belongs to `SCN_022_sql_database_analytics` and the Atlas Commerce Operations setting in `task_group_022`. The source examples are `E001` (multi-table SQL aggregation and hidden business filters), `E002` (stateful data-quality and source-reconciliation conventions), and `E003` (tool-based operational analysis with exact results). Immediate design sources are `scratch/task_group_design.md`, `scratch/task_briefs/test_001.md`, the common task-builder contract, the retained generated SQLite baseline, and the task-local request and output-contract payloads.

The business request is a delivery reliability closeout for orders attributed to `CMP-MAYPEAK-26` and created during the campaign master record's official active window. The cutoff is `2026-06-15T23:59:59Z`. The solver sees a business-facing prompt, a request payload containing campaign-specific policy definitions, a strict JSON output contract, and authenticated read-only access to the workplace service. Expected work is to discover the relational model, determine the production campaign cohort, establish effective order and shipment outcomes at the cutoff, roll shipments to stable orders, compare warehouses and carriers, identify severe orders, and return the exact JSON result.

The task fits the scenario because the scorecard crosses `campaigns`, `accounts`, `orders`, `order_events`, `shipments`, `carrier_scans`, and warehouse/carrier identifiers. It tests cutoff-sensitive state reconstruction, source-copy reconciliation, all-child completeness, stable business-ID aggregation, exact ranking, and policy classification. It requires no workplace mutation.

The construction database is `task_group/task_group_022/env/atlas_baseline.sqlite3`. The campaign master row is `CMP-MAYPEAK-26`, with active window `2026-05-18T00:00:00Z` through `2026-05-31T23:59:59Z`. Concrete source examples include eligible order `ORD-000008`, its relationships through `shipments`, imported lifecycle observations in `order_events`, and carrier observations in `carrier_scans`. The complete exact severe set is stored in `output/answer.json`.

### Material map

- `input/prompt.txt`: realistic closeout request, runtime placeholder, read-only scope, and output destination.
- `input/payloads/delivery_reliability_request.json`: campaign and cutoff facts; order completeness, on-time, partial/unshipped, severe, warehouse, carrier, rate, ranking, rounding, and status definitions.
- `input/payloads/answer_template.json`: exact top-level and nested keys, types, units, four-decimal rates, list ordering, ID patterns, controlled service-status enum, and additional-property prohibitions.
- `GET /api/schema`: table, key, type, and relationship discovery.
- `GET /api/data-dictionary`: public meanings of normalized carrier fields, import identity, ingestion timestamps, and convenience status fields.
- `POST /api/sql`: authenticated read-only SQL analysis endpoint.
- `campaigns`, `accounts`, `orders`, `order_events`: campaign window, order attribution, production flags, and order cutoff state.
- `shipments`, `carrier_scans`: physical shipment coverage, carrier code, shipment promise, and effective delivery state/time.
- `warehouses`: warehouse master context; the scored ranking uses the stable warehouse ID assigned to each order.
- `output/answer.json`: standard answer derived from the retained baseline.
- `eval/evaluator.py` and `eval/eval.sh`: eight atomic weighted checks and robust evaluation entry point.

### Hidden solution basis and exact calculations

For construction, imported event copies are deduplicated by `(source_system, external_event_id)`, retaining the greatest `(ingested_at, stable row ID)`. Effective order or shipment state at the cutoff is the latest retained event at or before the cutoff by `(business event time, stable event row ID)`. Production excludes internal/test accounts, and orders whose effective state is canceled by the cutoff are ineligible. Header `current_status` snapshots are not authoritative.

The full database contains 65,000 order-event rows representing 62,400 effective import keys and 80,000 carrier-scan rows representing 76,000 effective import keys. The campaign/window join yields 723 attributed orders. Of these, 27 are attached to internal accounts and 15 to test accounts, leaving 681 production orders. Effective order state excludes 20 canceled orders, for 661 eligible orders. A snapshot-only cancellation filter would find 31 production campaign-window orders and is therefore wrong.

The eligible cohort has 726 physical shipments. Effective cutoff state marks 344 shipments delivered. Rolling all associated shipments to orders gives 309 complete orders and 140 orders for which every shipment is on time. The overall on-time complete-order rate is `140 / 661 = 0.2118003025...`, reported as `0.2118`. The partial-or-unshipped outcome is `661 - 309 = 352` orders.

Warehouse calculations preserve the eligible-order denominator and rank on exact fractions before display rounding:

| Warehouse | Eligible | Complete | On-time complete | Exact rate basis | Reported rate |
| --- | ---: | ---: | ---: | --- | ---: |
| `WH-EAST-01` | 131 | 67 | 32 | 32/131 | 0.2443 |
| `WH-NORTH-01` | 126 | 55 | 28 | 28/126 | 0.2222 |
| `WH-SOUTH-01` | 141 | 70 | 30 | 30/141 | 0.2128 |
| `WH-WEST-01` | 131 | 60 | 26 | 26/131 | 0.1985 |
| `WH-CENTRAL-01` | 132 | 57 | 24 | 24/132 | 0.1818 |

The table is already in the required descending reliability order. There is no exact rate tie.

Of the 352 incomplete orders, 11 have no physical shipment and therefore no latest shipment promise. The other 341 are more than 36 hours beyond their latest shipment promise at the cutoff. No complete cohort order has any shipment more than 36 hours late. The severe set therefore contains 341 ascending IDs. It begins `ORD-000008`, `ORD-000081`, `ORD-000108`, `ORD-000131`, `ORD-000158` and ends `ORD-013761`, `ORD-013811`, `ORD-013838`, `ORD-013938`, `ORD-013988`. The SHA-256 of the newline-joined sorted ID list is `37a721a911feca8380431c6699755e70f2f9751beb56e3e54ea79a07ecc22fb0`.

Carrier rate calculations include only effectively delivered shipments attached to eligible orders:

| Carrier | Effective delivered shipments | Late delivered shipments | Exact rate basis | Reported rate |
| --- | ---: | ---: | --- | ---: |
| `SKYPOST` | 84 | 51 | 51/84 | 0.6071 |
| `ROADRUNNER` | 91 | 51 | 51/91 | 0.5604 |
| `PARCELPRO` | 84 | 47 | 47/84 | 0.5595 |
| `NOVA` | 85 | 36 | 36/85 | 0.4235 |

`SKYPOST` is the exact highest-late-rate carrier. The severe rate is `341 / 661 = 0.5158850...`. The on-time rate is below 0.80 and the severe rate is not below 0.10, so the final service status is `CRITICAL`.

The order-level standard answer is reproducible from this retained-baseline query; final grouping divides integer business counts, ranks exact fractions, and rounds only displayed rates:

```sql
WITH
params AS (SELECT '2026-06-15T23:59:59Z' AS cutoff),
campaign AS (
  SELECT campaign_id, starts_at, ends_at
  FROM campaigns
  WHERE campaign_id = 'CMP-MAYPEAK-26'
),
deduplicated_order_events AS (
  SELECT *, ROW_NUMBER() OVER (
    PARTITION BY source_system, external_event_id
    ORDER BY ingested_at DESC, event_id DESC
  ) AS import_rank
  FROM order_events
),
order_state_candidates AS (
  SELECT *, ROW_NUMBER() OVER (
    PARTITION BY order_id
    ORDER BY event_at DESC, event_id DESC
  ) AS state_rank
  FROM deduplicated_order_events, params
  WHERE import_rank = 1 AND event_at <= cutoff
),
eligible_orders AS (
  SELECT o.order_id, o.warehouse_id
  FROM orders o
  JOIN accounts a ON a.account_id = o.account_id
  JOIN campaign c ON c.campaign_id = o.campaign_id
  LEFT JOIN order_state_candidates os
    ON os.order_id = o.order_id AND os.state_rank = 1
  WHERE o.order_created_at >= c.starts_at
    AND o.order_created_at <= c.ends_at
    AND a.is_internal = 0
    AND a.is_test = 0
    AND COALESCE(os.event_type, '') <> 'CANCELLED'
),
deduplicated_scans AS (
  SELECT *, ROW_NUMBER() OVER (
    PARTITION BY source_system, external_event_id
    ORDER BY ingested_at DESC, scan_row_id DESC
  ) AS import_rank
  FROM carrier_scans
),
shipment_state_candidates AS (
  SELECT *, ROW_NUMBER() OVER (
    PARTITION BY shipment_id
    ORDER BY canonical_event_at DESC, scan_row_id DESC
  ) AS state_rank
  FROM deduplicated_scans, params
  WHERE import_rank = 1 AND canonical_event_at <= cutoff
),
order_rollup AS (
  SELECT e.order_id, e.warehouse_id,
    COUNT(s.shipment_id) AS shipment_count,
    SUM(CASE WHEN ss.canonical_status = 'DELIVERED'
             THEN 1 ELSE 0 END) AS delivered_count,
    SUM(CASE WHEN ss.canonical_status = 'DELIVERED'
              AND ss.canonical_event_at <= s.promised_delivery_at
             THEN 1 ELSE 0 END) AS on_time_count,
    SUM(CASE WHEN ss.canonical_status = 'DELIVERED'
              AND julianday(ss.canonical_event_at) >
                  julianday(s.promised_delivery_at, '+36 hours')
             THEN 1 ELSE 0 END) AS over_36h_count,
    MAX(s.promised_delivery_at) AS latest_shipment_promise
  FROM eligible_orders e
  LEFT JOIN shipments s ON s.order_id = e.order_id
  LEFT JOIN shipment_state_candidates ss
    ON ss.shipment_id = s.shipment_id AND ss.state_rank = 1
  GROUP BY e.order_id, e.warehouse_id
),
classified AS (
  SELECT *,
    CASE WHEN shipment_count > 0 AND delivered_count = shipment_count
         THEN 1 ELSE 0 END AS is_complete,
    CASE WHEN shipment_count > 0
               AND delivered_count = shipment_count
               AND on_time_count = shipment_count
         THEN 1 ELSE 0 END AS is_on_time_complete,
    CASE WHEN (
      NOT (shipment_count > 0 AND delivered_count = shipment_count)
      AND latest_shipment_promise IS NOT NULL
      AND julianday((SELECT cutoff FROM params)) >
          julianday(latest_shipment_promise, '+36 hours')
    ) OR (
      shipment_count > 0 AND delivered_count = shipment_count
      AND over_36h_count > 0
    ) THEN 1 ELSE 0 END AS is_severe
  FROM order_rollup
)
SELECT order_id, warehouse_id, is_complete, is_on_time_complete, is_severe
FROM classified
ORDER BY order_id;
```

Using the same `eligible_orders` and `shipment_state_candidates` CTEs, carrier inputs are reproduced with:

```sql
SELECT s.carrier_code,
       COUNT(*) AS effective_delivered_shipments,
       SUM(CASE WHEN ss.canonical_event_at > s.promised_delivery_at
                THEN 1 ELSE 0 END) AS late_delivered_shipments
FROM eligible_orders e
JOIN shipments s ON s.order_id = e.order_id
JOIN shipment_state_candidates ss
  ON ss.shipment_id = s.shipment_id
 AND ss.state_rank = 1
 AND ss.canonical_status = 'DELIVERED'
GROUP BY s.carrier_code;
```

### Evaluation design and likely pitfalls

All scoring points are atomic whole-point checks. The total raw weight is 18; a passing point earns exactly `weight / 18` and a failing point earns zero. An unreadable or non-object candidate fails every point without a traceback. An ordinary error in one requested business result affects only its corresponding point.

| ID | Exact atomic pass condition | Weight |
| --- | --- | ---: |
| `SP001` | `eligible_production_order_count` is the exact expected JSON integer. | 2 |
| `SP002` | `effectively_complete_order_count` is the exact expected JSON integer. | 3 |
| `SP003` | `on_time_complete_order_rate` is a finite JSON number equal to the expected four-decimal rate. | 3 |
| `SP004` | `partial_or_unshipped_order_count` is the exact expected JSON integer. | 2 |
| `SP005` | `warehouse_reliability_ranking` exactly matches all ordered warehouse objects and four-decimal rates. | 2 |
| `SP006` | `severe_exception_order_ids` exactly matches the unique ascending standard list. | 3 |
| `SP007` | `highest_late_rate_carrier` exactly matches the carrier-code/rate object. | 2 |
| `SP008` | `service_status` exactly matches the controlled enum. | 1 |

These eight points cover eligibility, effective completion, service rate, backlog, facility comparison, exception identification, carrier performance, and final business classification. Related counts reconcile arithmetically but remain separately requested operational outcomes; no point receives fractional credit or re-scores another field.

Likely model pitfalls include using campaign attribution without the official creation window; retaining internal/test accounts or effective cancellations; trusting `current_status`; counting import retry rows; filtering on ingestion time instead of business event time; treating a partially delivered multi-shipment order as complete; treating a no-shipment order as vacuously complete or severe; using the order promise instead of each shipment promise; dividing on-time orders by completed orders; ranking on rounded rates; omitting represented warehouses; treating overdue-undelivered shipments as delivered carrier observations; and counting joined rows instead of stable orders or shipments.

### Transfer design and train anchors

The explicit train anchors are `train_001` and `train_003`. `train_001` anchors production-cohort exclusions for `SP001`; all-physical-shipment completion and cutoff state for `SP002`; complete-order on-time calculation and final rounding for `SP003`; and severe-exception construction for `SP006`. `train_003` reinforces source-copy identity, normalized carrier observations, effective carrier state, and stable event ordering for `SP002` and `SP006`. The transfer matrix therefore places the highest-weight eligibility, completion, rate, and severe-set goals on learned operational conventions rather than on a prompt-level checklist.

Transfer-dependent difficulty consists of identifying import-copy identity, selecting authoritative event-derived state, handling stale snapshots, applying production exclusions, preserving stable business grains, and requiring all physical shipments for order completion. Task-specific exploration difficulty consists of finding the May Peak window and cardinalities, applying the June 15 cutoff and 36-hour threshold, discovering five represented warehouse IDs, building the complete warehouse ranking, defining delivered-only carrier denominators, comparing four carriers, and applying the new status thresholds. The visible request supplies necessary campaign-specific policy facts but does not restate the transferable reconciliation SOP or answer path.

### Construction record and adjustment

- Author: `task-builder-test-001`
- Created: `2026-07-16`
- Updated: `2026-07-16`
- Major changes: created realistic test input and exact output schema; derived and independently cross-checked the standard answer from the retained SQLite baseline; implemented eight atomic weighted evaluator points; prepared numeric, ranking, and independent-outcome sensitivity checks.
- Data-driven design adjustment: the high-level group design describes three warehouses, but the generated eligible cohort contains five. The task brief explicitly requires all warehouse IDs represented in the cohort, so the standard answer and evaluator include all five. No cohort filter was invented to force three.

## 中文记录

### 数据溯源、任务定义与场景适配

本未见测试任务属于 `SCN_022_sql_database_analytics`，业务环境是 `task_group_022` 的 Atlas Commerce Operations。来源样例为 `E001`（多表 SQL 聚合和隐藏业务过滤）、`E002`（有状态数据质量与来源协调约定）和 `E003`（要求精确结果的工具化运营分析）。直接依据包括 `scratch/task_group_design.md`、`scratch/task_briefs/test_001.md`、公共构建约定、保留的生成式 SQLite 基线，以及本任务自己的请求和输出模板。

业务目标是在 `2026-06-15T23:59:59Z` 截止时点，为归因于 `CMP-MAYPEAK-26` 且创建于活动官方窗口内的生产订单生成交付可靠性记分卡。求解者能看到真实英文请求、活动特定的业务定义、严格 JSON 契约，以及只读查询接口。预期工作涵盖发现关系模式、确定生产订单队列、还原订单和发运的有效截止状态、按稳定订单汇总、比较仓库和承运商、识别严重异常并返回精确 JSON。该任务跨越活动、账户、订单、订单事件、发运、承运商扫描与仓库标识，符合长链路 SQL 运营分析场景，且不需要修改数据。

构建数据来自 `task_group/task_group_022/env/atlas_baseline.sqlite3`。活动主记录窗口为 `2026-05-18T00:00:00Z` 至 `2026-05-31T23:59:59Z`。具体证据例子包括合格订单 `ORD-000008`、`shipments` 中的物理发运关系、`order_events` 中的生命周期事件和 `carrier_scans` 中的承运商观察。完整严重异常集合保存在 `output/answer.json`。

### 材料用途

- `input/prompt.txt` 提供业务化关账请求、运行服务占位符、只读范围和输出位置。
- `input/payloads/delivery_reliability_request.json` 提供活动、截止时间、完成、准时、部分或未发运、严重异常、仓库、承运商、排序、舍入与状态规则。
- `input/payloads/answer_template.json` 精确规定键、类型、单位、四位小数、列表顺序、ID 格式、状态枚举和禁止额外字段。
- `GET /api/schema` 与 `GET /api/data-dictionary` 用于发现表关系和字段含义，`POST /api/sql` 用于只读分析。
- `campaigns`、`accounts`、`orders`、`order_events` 决定活动窗口、归因、生产资格和取消状态；`shipments`、`carrier_scans` 决定物理发运、承运商、承诺时间与有效送达状态。
- `output/answer.json` 是标准答案；`eval/evaluator.py` 和 `eval/eval.sh` 实现八个原子加权评分点。

### 隐藏解答与精确计算

构建时先按 `(source_system, external_event_id)` 消除导入副本，保留 `(ingested_at, 稳定行 ID)` 最大的记录，再按业务事件时间和稳定事件行 ID 取得截止时点最后状态。生产队列排除内部账户、测试账户和截止时已有效取消的订单，不能信任头表的 `current_status` 快照。65,000 条订单事件对应 62,400 个有效导入键，80,000 条承运商扫描对应 76,000 个有效导入键。

活动窗口内共有 723 个归因订单，其中内部账户订单 27 个、测试账户订单 15 个，剩余 681 个生产订单；再排除 20 个有效取消订单，得到 661 个合格订单。若只用快照取消状态会错误识别 31 个。合格队列包含 726 个物理发运，截止时有效送达 344 个。按订单汇总后有 309 个完整订单、140 个全部发运均准时的订单，准时完整订单率为 `140/661 = 0.2118`，部分或未发运订单为 `352`。

仓库排名依次为：`WH-EAST-01` 的 `32/131 = 0.2443`，`WH-NORTH-01` 的 `28/126 = 0.2222`，`WH-SOUTH-01` 的 `30/141 = 0.2128`，`WH-WEST-01` 的 `26/131 = 0.1985`，`WH-CENTRAL-01` 的 `24/132 = 0.1818`。排序使用未舍入比率，结果没有精确并列。

352 个未完成订单中有 11 个没有物理发运和最晚承诺，其余 341 个在截止时超过最晚发运承诺 36 小时；没有完整订单出现超过 36 小时的发运迟到。因此严重集合含 341 个升序 ID，换行连接后的 SHA-256 为 `37a721a911feca8380431c6699755e70f2f9751beb56e3e54ea79a07ecc22fb0`。承运商结果为：`SKYPOST` 84 个有效送达中 51 个迟到，`51/84 = 0.6071`，高于 `ROADRUNNER` 的 `0.5604`、`PARCELPRO` 的 `0.5595` 和 `NOVA` 的 `0.4235`。严重率为 `341/661 = 0.515885...`，所以最终状态为 `CRITICAL`。英文部分的 SQL 是可复现的精确标准答案依据，只在最终显示时舍入。

### 评分、常见错误与迁移设计

总原始权重为 18，每点只能获得完整 `weight/18` 或零分：`SP001` 合格生产订单数（2），`SP002` 有效完整订单数（3），`SP003` 准时完整订单率（3），`SP004` 部分或未发运数（2），`SP005` 全部仓库可靠性排名及比率（2），`SP006` 精确严重异常集合（3），`SP007` 最高迟到率承运商及比率（2），`SP008` 服务状态枚举（1）。不可读取或非对象 JSON 得零分且不会输出回溯；普通错误只影响对应评分点。八点覆盖资格、完成、服务率、积压、设施比较、异常识别、承运商表现和最终分类，没有点内部分给分。

常见错误包括遗漏官方创建窗口、纳入内部/测试账户或有效取消订单、信任快照状态、重复计算导入重试、用导入时间代替业务时间、把部分送达订单当作完成、把无发运订单当作自动完成或严重异常、使用订单承诺代替每个发运承诺、把完成订单作为准时率分母、按舍入值排序、漏掉代表仓库、把未送达逾期发运纳入已送达承运商分母，以及计算连接行而不是稳定业务 ID。

明确训练锚点是 `train_001` 和 `train_003`。`train_001` 为 `SP001` 提供生产队列排除约定，为 `SP002` 提供所有物理发运均完成的截止状态约定，为 `SP003` 提供完整订单准时率与最终舍入约定，并为 `SP006` 提供严重异常构造经验。`train_003` 强化了 `SP002` 和 `SP006` 所需的来源副本身份、规范化承运商观察和稳定事件顺序。迁移依赖难点是识别重试副本、选择事件推导状态、处理滞后快照、使用稳定业务粒度和执行全子对象完成判断；任务特有探索难点是新活动窗口、6 月 15 日截止、36 小时阈值、五仓库完整排名、四承运商比较和新状态阈值。可见请求提供任务特定政策，但没有泄露可迁移的完整操作规程。

### 构建记录与调整

- 作者：`task-builder-test-001`
- 创建日期：`2026-07-16`
- 更新日期：`2026-07-16`
- 主要变更：创建真实测试输入和精确输出模板；从保留 SQLite 基线推导并独立交叉验证标准答案；实现八个原子加权评分点；准备数值、排名和独立结果敏感性测试。
- 数据驱动调整：任务组高层设计描述三个仓库，但生成后的合格队列实际包含五个。任务简报明确要求返回队列中所有仓库 ID，因此标准答案和评估器包含全部五个，没有人为增加过滤条件来强制三个。
