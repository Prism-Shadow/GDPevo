# Spring Campaign Fulfillment Scorecard — Construction Notes

## English record

### Lineage, task definition, and scenario fit

This real train task belongs to `SCN_022_sql_database_analytics` and the Atlas Commerce Operations setting in `task_group_022`. Its source anchors are `E001` (BIRD-Interact multi-turn business aggregation), `E002` (LiveSQLBench stateful correction/re-query conventions), and `E003` (WorkBench tool-based operational analytics). The immediate design sources are `scratch/task_group_design.md`, `scratch/task_briefs/train_001.md`, the generated shared environment, and the task-local request and schema payloads.

The business request is a cutoff-based fulfillment scorecard for orders attributed to `CMP-SPRING-26` and created inside the campaign master record's official window. The cutoff is `2026-04-15T23:59:59Z`. The solver sees a realistic request, a JSON Schema output contract, and authenticated read-only access to the shared workplace service. The expected work is to discover the relational model, establish the eligible production cohort, reconstruct order and shipment state at the cutoff, roll shipment facts to orders, aggregate service metrics by warehouse region, classify severe exceptions, and return exact structured output.

This fits the SQL analytics scenario because the business result crosses campaign, account, order, warehouse, shipment, and append-only event data. Imported retry copies and lagging convenience snapshots make a direct header-table aggregation incorrect. The task combines the scenario's long-horizon schema exploration, source reconciliation, cutoff-sensitive state reconstruction, many-to-one rollup, stable ranking, and final policy classification. It is analytical and requires no mutation.

Generated data lineage is the retained baseline `task_group/task_group_022/env/atlas_baseline.sqlite3`. The campaign source example is `campaigns.campaign_id = 'CMP-SPRING-26'`, whose master window is `2026-03-01T00:00:00Z` through `2026-03-31T23:59:59Z`. Concrete evidence examples include eligible order `ORD-000018`, physical shipment relationships in `shipments`, imported order lifecycle rows in `order_events`, and carrier observations in `carrier_scans`. The task-local payload `input/payloads/fulfillment_request.json` supplies the cutoff, definitions, formulas, ordering, and status thresholds without exposing the hidden reconciliation procedure.

### Material map

- `input/prompt.txt`: business-facing request, runtime service location placeholder, read-only scope, and output destination.
- `input/payloads/fulfillment_request.json`: campaign ID, cutoff, completeness/on-time/severity definitions, rate denominators, regional ranking rule, final rounding rule, and status thresholds.
- `input/payloads/answer_template.json`: exact top-level keys, types, 4-decimal ratio units, two-item ordered region object shape, severe-ID pattern/order, status enum, and prohibition on extra properties.
- `GET /api/schema`: public table and column discovery.
- `GET /api/data-dictionary`: public meanings for normalized carrier fields, source identity, ingestion time, and convenience status fields.
- `POST /api/sql`: read-only SQL analysis endpoint used for all task calculations.
- `campaigns`, `accounts`, `orders`, `order_events`: official window, production flags, order attribution, and effective cancellation state.
- `warehouses`, `shipments`, `carrier_scans`: warehouse region, physical shipment promises, and imported normalized carrier observations.
- `output/answer.json`: reproducible standard answer.
- `eval/evaluator.py` and `eval/eval.sh`: seven atomic weighted checks and the task evaluation entry point.

### Hidden solution basis and exact calculations

Imported rows are first deduplicated on `(source_system, external_event_id)`, retaining the greatest `(ingested_at, stable row ID)`. The retained baseline contains 65,000 `order_events` rows representing 62,400 effective import keys (2,600 retry copies) and 80,000 `carrier_scans` rows representing 76,000 effective import keys (4,000 retry copies). For each business entity, cutoff state is then the latest deduplicated event at or before the cutoff, ordered by the canonical event time and stable event row ID.

The campaign/window join yields 1,603 attributed orders. Excluding 44 internal and 40 test-account orders leaves 1,519 production orders. The latest effective order event excludes 42 orders whose cutoff state is `CANCELLED`, leaving 1,477 eligible production orders. This reconstruction matters: 56 production campaign-window orders have the denormalized header snapshot `CANCELLED`, while only 42 have final effective cancellation state.

Among eligible orders, 1,625 physical shipments exist. Their effective cutoff states contain 772 delivered shipments, compared with 1,009 `shipments.current_status = 'DELIVERED'`; 385 shipment rows disagree on delivered versus non-delivered classification. Rolling all shipments to their stable order IDs gives 685 complete orders and 281 orders for which every shipment is on time. The overall rate is `281 / 1477 = 0.1902505...`, reported as `0.1903`. The incomplete count is `1477 - 685 = 792`.

Regional calculations use the region of `orders.warehouse_id` and rank on the unrounded fraction:

| Region | Eligible | Complete | On-time complete | Unrounded rate | Reported rate |
| --- | ---: | ---: | ---: | ---: | ---: |
| CENTRAL | 285 | 126 | 51 | 51/285 | 0.1789 |
| SOUTH | 280 | 132 | 51 | 51/280 | 0.1821 |
| EAST | 303 | 138 | 57 | 57/303 | 0.1881 |
| WEST | 303 | 142 | 57 | 57/303 | 0.1881 |
| NORTH | 306 | 147 | 65 | 65/306 | 0.2124 |

Therefore the exact worst-two result is CENTRAL followed by SOUTH. EAST and WEST are an exact downstream tie and demonstrate the stable ascending-region tie-break even though neither enters the worst two.

Of the 792 incomplete orders, 772 have at least one shipment and are more than 24 hours beyond their latest shipment promise at cutoff. The remaining 20 have no physical shipment and therefore no shipment promise: they are incomplete but do not meet that severe condition. No complete order in this cohort has a shipment delivered more than 24 hours late. The severe set therefore contains 772 sorted IDs. It starts `ORD-000018`, `ORD-000026`, `ORD-000041`, `ORD-000068`, `ORD-000087` and ends `ORD-013898`, `ORD-013902`, `ORD-013971`, `ORD-013979`, `ORD-013998`. The SHA-256 of the newline-joined sorted ID list is `3e2ee00ffbb8e0d3c8be33744085f9fa048e3807f392c409c8bb0c38d0b1aed0`; the complete exact list is in `output/answer.json`.

The severe rate is `772 / 1477 = 0.5226811...`. The on-time rate is below 0.78 and the severe rate is not below 0.12, so neither HEALTHY nor WATCH applies; the standard status is `CRITICAL`.

The standard answer was constructed from the retained baseline with this reproducible classification query; Python only grouped these returned stable order rows, divided integer counts, ranked the exact fractions, rounded final displayed rates, and serialized JSON:

```sql
WITH
params AS (SELECT '2026-04-15T23:59:59Z' AS cutoff),
campaign AS (
  SELECT campaign_id, starts_at, ends_at
  FROM campaigns
  WHERE campaign_id = 'CMP-SPRING-26'
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
    PARTITION BY order_id ORDER BY event_at DESC, event_id DESC
  ) AS state_rank
  FROM deduplicated_order_events, params
  WHERE import_rank = 1 AND event_at <= cutoff
),
eligible_orders AS (
  SELECT o.order_id, w.region
  FROM orders o
  JOIN accounts a ON a.account_id = o.account_id
  JOIN warehouses w ON w.warehouse_id = o.warehouse_id
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
  SELECT e.order_id, e.region,
         COUNT(s.shipment_id) AS shipment_count,
         SUM(CASE WHEN ss.canonical_status = 'DELIVERED' THEN 1 ELSE 0 END)
           AS delivered_count,
         SUM(CASE WHEN ss.canonical_status = 'DELIVERED'
                   AND ss.canonical_event_at <= s.promised_delivery_at
                  THEN 1 ELSE 0 END) AS on_time_shipment_count,
         SUM(CASE WHEN ss.canonical_status = 'DELIVERED'
                   AND julianday(ss.canonical_event_at) >
                       julianday(s.promised_delivery_at, '+24 hours')
                  THEN 1 ELSE 0 END) AS over_24h_late_count,
         MAX(s.promised_delivery_at) AS latest_shipment_promise
  FROM eligible_orders e
  LEFT JOIN shipments s ON s.order_id = e.order_id
  LEFT JOIN shipment_state_candidates ss
    ON ss.shipment_id = s.shipment_id AND ss.state_rank = 1
  GROUP BY e.order_id, e.region
),
classified AS (
  SELECT *,
    CASE WHEN shipment_count > 0 AND delivered_count = shipment_count
         THEN 1 ELSE 0 END AS is_complete,
    CASE WHEN shipment_count > 0
               AND delivered_count = shipment_count
               AND on_time_shipment_count = shipment_count
         THEN 1 ELSE 0 END AS is_on_time_complete,
    CASE WHEN (
           NOT (shipment_count > 0 AND delivered_count = shipment_count)
           AND latest_shipment_promise IS NOT NULL
           AND julianday((SELECT cutoff FROM params)) >
               julianday(latest_shipment_promise, '+24 hours')
         ) OR (
           shipment_count > 0 AND delivered_count = shipment_count
           AND over_24h_late_count > 0
         ) THEN 1 ELSE 0 END AS is_severe
  FROM order_rollup
)
SELECT order_id, region, is_complete, is_on_time_complete, is_severe
FROM classified
ORDER BY order_id;
```

### Evaluation design and pitfalls

All points are whole-point pass/fail checks. The total raw weight is 16; a passing point earns exactly `weight / 16`, otherwise zero. An unreadable or non-object candidate deterministically fails all points without a traceback. Ordinary errors are isolated to the corresponding result field.

| ID | Goal and exact atomic logic | Weight |
| --- | --- | ---: |
| SP001 | `eligible_production_order_count` is exactly the expected JSON integer. | 2 |
| SP002 | `effectively_complete_order_count` is exactly the expected JSON integer. | 3 |
| SP003 | `on_time_complete_order_rate` is a finite JSON number exactly equal to the expected 4-decimal ratio. | 3 |
| SP004 | `incomplete_order_count` is exactly the expected JSON integer. | 2 |
| SP005 | `worst_warehouse_regions` exactly matches the ordered two-object result, including region names and their 4-decimal rates. | 2 |
| SP006 | `severe_exception_order_ids` exactly matches the unique ascending standard list. | 3 |
| SP007 | `overall_status` exactly matches the controlled enum. | 1 |

The seven goals span eligibility, cutoff completion, SLA rate, backlog size, regional ranking, exception identification, and policy classification. Although some values reconcile arithmetically, they are distinct requested business outcomes and no point fractionally re-scores another field.

Likely model pitfalls are filtering on campaign attribution without the official creation window; including internal/test accounts or final cancellations; counting imported retry rows; trusting `current_status`; filtering by ingestion time instead of business event time; treating a partially delivered multi-shipment order as complete; treating a no-shipment order as vacuously complete or severe; using the order promise instead of each shipment promise; dividing the on-time numerator by complete orders; ranking rounded rates; counting joined rows rather than stable order IDs; and rounding intermediate values.

### Transfer design

Solving this real train task and comparing an attempt with the standard answer exposes a reusable operational analytics pattern: discover the schema and dictionary, identify source-copy identity, deduplicate before cutoff reconstruction, treat denormalized status as a convenience rather than authority, apply production and cancellation exclusions at the order grain, require all child shipments for completeness, preserve stable IDs through aggregation, rank on unrounded metrics with a stable tie-break, and round only displayed outputs. These are the train signals for event-state reconstruction, import reconciliation, production cohort control, all-child completeness, and deterministic aggregation.

Transfer-dependent difficulty is concentrated in recognizing retry-copy identity, reconstructing effective event state, distrusting stale snapshots, choosing stable business-ID grains, and handling all-shipment completeness. Task-specific exploration difficulty is discovering the Spring campaign's window and cardinalities, applying the April 15 cutoff, implementing this request's 24-hour severe rule and status thresholds, and mapping orders to warehouse regions. The visible request supplies task-specific policy facts while leaving the reusable SOP to be inferred from genuine database work and answer comparison.

### Construction record

- Author: `task-builder-train-001`
- Created: `2026-07-16`
- Updated: `2026-07-16`
- Major changes: created the real train request and exact schema; derived the answer from the retained SQLite baseline; implemented seven atomic weighted evaluator points; validated the standard answer and independent mutations.
- Design deviation: none. The design summary's phrase “two regions” is realized as the requested worst-two regional ranking; the business brief defines no regional cohort restriction, so all warehouse regions remain eligible.

## 中文记录

### 数据溯源、任务定义与场景适配

本任务是 `SCN_022_sql_database_analytics` 中的真实训练任务，业务背景为 `task_group_022` 的 Atlas Commerce Operations。来源锚点包括 `E001`（多轮业务数据库聚合）、`E002`（有状态修正与复查所使用的安全数据约定）和 `E003`（工具化运营分析）。直接设计依据是 `scratch/task_group_design.md`、`scratch/task_briefs/train_001.md`、共享生成环境以及本任务的请求和输出模板。

业务目标是在 `2026-04-15T23:59:59Z` 截止时点，为归因于 `CMP-SPRING-26` 且创建于该活动官方窗口内的生产订单生成履约记分卡。求解者可看到真实业务请求、严格 JSON Schema，以及只读的数据库查询接口。主要对象关系是活动—订单—账户—仓库—发运—承运商事件；工作过程需要发现模式、确定资格订单、还原截止状态、把发运事实汇总到订单、计算区域指标、识别严重异常并输出结构化结果。

保留的构建基线为 `task_group/task_group_022/env/atlas_baseline.sqlite3`。活动主数据窗口是 `2026-03-01T00:00:00Z` 至 `2026-03-31T23:59:59Z`。示例证据包括订单 `ORD-000018`、`shipments` 中的物理发运关系、`order_events` 中的订单事件和 `carrier_scans` 中的承运商观察。此任务符合 SQL 分析场景，因为结果跨越多个关系表，并且存在重复导入、滞后快照、截止时点状态、子对象全量完成判断、稳定排序和政策分类。

### 材料用途

- `input/prompt.txt` 给出业务请求、运行时服务占位符、只读范围和输出位置。
- `input/payloads/fulfillment_request.json` 给出活动、截止时间、完成/准时/严重异常定义、分母、区域排序、舍入和状态阈值。
- `input/payloads/answer_template.json` 严格规定键、类型、四位小数、两项区域排序、异常订单 ID 顺序和状态枚举，并禁止额外字段。
- `GET /api/schema` 与 `GET /api/data-dictionary` 用于发现模式和字段语义，`POST /api/sql` 用于只读分析。
- `campaigns`、`accounts`、`orders`、`order_events` 决定活动窗口、生产资格和取消状态；`warehouses`、`shipments`、`carrier_scans` 决定区域、承诺时间和实际承运商状态。
- `output/answer.json` 是可复现标准答案；`eval/evaluator.py` 与 `eval/eval.sh` 实现七个原子评分点。

### 隐藏解答依据与精确计算

先按 `(source_system, external_event_id)` 去重，保留 `(ingested_at, 稳定行 ID)` 最大的导入副本，再按业务事件时间和稳定事件 ID 取得截止时点的最后状态。65,000 条订单事件对应 62,400 个有效导入键，80,000 条承运商扫描对应 76,000 个有效导入键。活动窗口内共有 1,603 个归因订单；排除 44 个内部账户订单和 40 个测试账户订单后为 1,519 个，再排除 42 个最终有效状态为 `CANCELLED` 的订单，得到 1,477 个合格生产订单。

合格订单关联 1,625 个物理发运。有效截止状态中有 772 个已送达发运，而发运头快照显示 1,009 个，送达/未送达判断共有 385 个不一致。按稳定订单 ID 汇总后，685 个订单完成，281 个订单的全部发运都准时，所以总体准时完整订单率为 `281 / 1477 = 0.1903`，未完成订单数为 `792`。

区域结果按未舍入比例排序：CENTRAL 为 `51/285 = 0.1789`，SOUTH 为 `51/280 = 0.1821`，因此最差两区依次为 CENTRAL、SOUTH。EAST 与 WEST 都是 `57/303`，验证了区域名称升序的稳定并列规则。

792 个未完成订单中，772 个有关联发运且截止时点已超过最晚发运承诺 24 小时；其余 20 个没有物理发运和发运承诺，因此未满足该严重条件。本队列没有任何已完成订单出现超过 24 小时的发运迟到。精确异常集合含 772 个升序 ID，完整列表在 `output/answer.json`，换行连接后的 SHA-256 为 `3e2ee00ffbb8e0d3c8be33744085f9fa048e3807f392c409c8bb0c38d0b1aed0`。严重异常率为 `772/1477 = 0.5226811...`；总体准时率低于 0.78 且严重异常率不低于 0.12，所以状态为 `CRITICAL`。上方 SQL 是标准答案的精确分类依据，只在最终显示时舍入。

### 评分、风险与迁移设计

总原始权重为 16，每个评分点只能得到完整的 `weight/16` 或零分：`SP001` 合格订单数（2），`SP002` 完成订单数（3），`SP003` 总体准时率（3），`SP004` 未完成订单数（2），`SP005` 最差两区及其比率（2），`SP006` 精确升序严重异常集合（3），`SP007` 总体状态枚举（1）。不可读取或非对象 JSON 会稳定地得到零分；普通业务错误只影响对应字段。七点分别覆盖资格、完成、服务率、积压、区域排序、异常识别和政策结论，不进行点内部分给分。

常见错误包括遗漏官方创建窗口、纳入内部/测试账户或已取消订单、重复计算导入重试、信任 `current_status`、用导入时间代替业务时间、把部分送达的多发运订单当作完成、把无发运订单当作自动完成或严重异常、使用订单承诺代替每个发运承诺、用完成订单作为准时率分母、按已舍入值排序、计算连接行而不是稳定订单 ID，以及过早舍入。

可迁移难点是识别导入副本身份、还原有效事件状态、识别滞后快照、维持稳定业务粒度、执行所有子发运完成规则和稳定排序。任务特有探索难点是发现 Spring 活动窗口和实际基数、应用 4 月 15 日截止时间、实现本请求的 24 小时严重规则与状态阈值，以及把订单映射到仓库区域。通过真实求解并与标准答案比较，可以迁移上述操作规程；可见请求仅提供本任务政策事实，没有泄露完整隐藏流程。

### 构建记录

- 作者：`task-builder-train-001`
- 创建日期：`2026-07-16`
- 更新日期：`2026-07-16`
- 主要变更：建立真实训练请求与严格模板；从保留 SQLite 基线推导标准答案；实现七个原子加权评分点；验证标准答案和相互独立的错误变体。
- 设计偏差：无。设计摘要中的“两区”按业务简报实现为最差两区排名；简报没有限制区域队列，因此所有仓库区域都参与资格计算。
