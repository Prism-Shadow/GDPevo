# test_003 construction and evaluation notes

## English

### Lineage, task definition, and scenario fit

This is the unseen stateful test task `test_003`, owned by `task-builder-test-003`, for scenario `SCN_022_sql_database_analytics` in `task_group_022`. The source scenario examples are `E001`, `E002`, and `E003`: relational schema-led analysis, a controlled data-quality correction, and operational work through a sandboxed business service. The task follows `scratch/task_briefs/test_003.md` and the `test_003`/transfer-matrix design in `scratch/task_group_design.md`.

The business setting is an Atlas Commerce Inventory Control reconciliation. An ERP report says one APPAREL movement for warehouse `WH-WEST-01` and source document `DOC-0000028` was supplied in `EA` but normalized with a case multiplier. The solver must identify the effective conflicting movement, calculate availability at `2026-05-31T23:59:59Z`, make one approved canonical correction with one audit row, verify the state change, and recompute the active-family stockout-risk set, highest-risk SKU, and status.

The generated data comes from the shared `env/generate_data.py` business environment. Construction inspected the retained `env/atlas_baseline.sqlite3` only through a read-only SQLite URI; its observed SHA-256 was `a662aae89583e5ef4ad60d1516f5a6c48fb0cf026aae5b559264de2dfdb5a597`. The hypothetical update, audit insert, and post-change analytics were performed on a private mode-0600 temporary copy that was deleted. A final hash check confirmed that the retained baseline was unchanged.

This task fits the scenario because inventory availability is not a single-row lookup. `products` defines the active APPAREL population, `inventory_snapshots` supplies the starting point for each warehouse/SKU, and retry-prone `inventory_movements` supplies signed changes and demand evidence. The correction is governed through `correction_audit`. The workflow crosses raw ERP unit evidence, canonical each-unit normalization, cutoff analytics, a controlled atomic transaction, and a post-change operational decision.

### Visible materials and environment map

- `input/prompt.txt` is the realistic month-end control request, mutation authorization, workplace reference, preservation requirement, and output instruction.
- `input/payloads/inventory_control_request.json` fixes the warehouse, family, source document, cutoff, demand window and formula, active-SKU population, 100-EA planning buffer, risk ranking, status thresholds, approved correction metadata, paired-field audit encoding, and `APPLIED` success rule.
- `input/payloads/answer_template.json` defines every required object and field, integer units and zero-decimal precision, the unique ascending SKU list, controlled status enums, and the prohibition on additional properties.
- `GET /api/schema` exposes table DDL, keys, relationships, and indexes.
- `GET /api/data-dictionary` explains raw versus canonical quantities, UOM multipliers, ingestion identity, correction metadata, and timestamp conventions.
- `POST /api/sql` supports read-only discovery, uniqueness checks, pre-change metrics, and post-change verification.
- `POST /api/sql/transaction` supports the guarded canonical update and audit insert in one atomic request. The service requires a stable primary-key guard and an old-value guard for every corrected canonical business field.
- `GET /api/correction-audit` supports independent verification of the fixed audit record.
- `products`, `inventory_snapshots`, `inventory_movements`, `warehouses`, and `correction_audit` are the material shared tables.
- `output/answer.json` is the hidden reproducible standard result.
- `eval/eval.sh` and `eval/evaluator.py` provide the task-local eight-point atomic weighted evaluator.

The expected work is schema-led exploration, isolation of the requested effective anomaly, before-state aggregation, one safe transaction, verification, after-state aggregation, stable set/ranking construction, and exact JSON output. The visible request provides task-specific business definitions without publishing the hidden retry-resolution procedure or target identifiers.

### Task-local nondegeneracy adjustment

The brief's literal zero-margin risk rule produced no post-correction stockout-risk SKUs at this exact cohort and cutoff; the smallest projected margin was still `18.0` each. That would make the weight-3 set result an empty-list exercise. Under the common builder contract's nondegeneracy clause, this task adds one scalar request fact: `minimum_projected_operating_buffer_each = 100`, and a SKU is at risk when corrected available units minus seven-day demand is strictly below that buffer.

This is the only analytical deviation. The warehouse, APPAREL cohort, source document, cutoff, 14-day demand evidence, seven-day demand formula, availability formula, correction target, correction fields, and status-percentage thresholds remain unchanged. The 100-EA operating floor creates a meaningful post-correction set and preserves the intended re-query effect: the pre-correction count is 10 (`WATCH` at exactly 10%), while the corrected count is 9 (`CONTROLLED` at 9%). The solver-visible payload states the adjusted rule explicitly; the hidden procedure remains hidden.

### Exact hidden solution and reproducible calculations

Imported movement copies are deduplicated on `(source_system, external_event_id)`, retaining the greatest `(ingested_at, movement_row_id)`. The anomaly scope is applied to those retained copies. The following evidence is unique:

- `movement_row_id`: `IMR-0000110`
- `movement_id`: `MOV-0000110`
- `sku`: `SKU-00463`
- warehouse/family/document: `WH-WEST-01`, `APPAREL`, `DOC-0000028`
- source evidence: `raw_quantity=-40`, `raw_uom='EA'`, `raw_uom_multiplier=1`
- incorrect canonical values: `canonical_quantity_each=-800`, `canonical_uom_multiplier=20`
- corrected canonical values: `canonical_quantity_each=-40`, `canonical_uom_multiplier=1`
- movement evidence: `SALE` at `2026-05-13T10:41:00Z`, source `ERP_LEDGER`, external event `ERP-MOV-0000110`

The canonical correction follows the source-supported identity `canonical_quantity_each = raw_quantity * raw_uom_multiplier`, so `-40 * 1 = -40`. The raw values, source document, source system, external event, movement IDs, warehouse, SKU, type, occurrence time, and ingestion time remain unchanged.

For each of the 100 active APPAREL SKUs, construction selects the latest snapshot at or before the cutoff, then applies retained signed movements whose `occurred_at` is strictly after that SKU's snapshot and at or before the cutoff. Demand uses retained `SALE` rows from `2026-05-18T00:00:00Z` through `2026-05-31T23:59:59Z`, inclusive. Since seven times a 14-day daily average equals one half of the 14-day absolute sale total, `seven_day_demand_units = sale_units_14d / 2.0`.

The reproducible post-correction rollup basis is:

```sql
WITH effective_movements AS (
  SELECT *
  FROM (
    SELECT m.*,
           ROW_NUMBER() OVER (
             PARTITION BY source_system, external_event_id
             ORDER BY ingested_at DESC, movement_row_id DESC
           ) AS copy_rank
    FROM inventory_movements AS m
  )
  WHERE copy_rank = 1
),
latest_snapshots AS (
  SELECT *
  FROM (
    SELECT s.*,
           ROW_NUMBER() OVER (
             PARTITION BY s.warehouse_id, s.sku
             ORDER BY s.snapshot_at DESC
           ) AS snapshot_rank
    FROM inventory_snapshots AS s
    JOIN products AS p ON p.sku = s.sku
    WHERE s.warehouse_id = 'WH-WEST-01'
      AND p.product_family = 'APPAREL'
      AND p.is_active = 1
      AND s.snapshot_at <= '2026-05-31T23:59:59Z'
  )
  WHERE snapshot_rank = 1
),
movement_rollup AS (
  SELECT ls.sku,
         COALESCE(SUM(em.canonical_quantity_each), 0) AS movement_units,
         COALESCE(SUM(CASE
           WHEN em.movement_type = 'SALE'
            AND em.occurred_at >= '2026-05-18T00:00:00Z'
            AND em.occurred_at <= '2026-05-31T23:59:59Z'
           THEN ABS(em.canonical_quantity_each)
           ELSE 0 END), 0) AS sale_units_14d
  FROM latest_snapshots AS ls
  LEFT JOIN effective_movements AS em
    ON em.warehouse_id = ls.warehouse_id
   AND em.sku = ls.sku
   AND em.occurred_at > ls.snapshot_at
   AND em.occurred_at <= '2026-05-31T23:59:59Z'
  GROUP BY ls.sku
)
SELECT ls.sku,
       ls.on_hand_each - ls.reserved_each + mr.movement_units AS available_units,
       mr.sale_units_14d / 2.0 AS seven_day_demand_units,
       ls.on_hand_each - ls.reserved_each + mr.movement_units
         - mr.sale_units_14d / 2.0 AS projected_post_demand_units
FROM latest_snapshots AS ls
JOIN movement_rollup AS mr ON mr.sku = ls.sku
ORDER BY projected_post_demand_units ASC, ls.sku ASC;
```

The corrected SKU's latest snapshot is `2026-05-01T00:00:00Z`, with `on_hand_each=905` and `reserved_each=88`, a starting available balance of `817`. Effective later pre-correction movements are `+35`, `-800`, and `+21`, totaling `-744`; therefore pre-correction available units are `817 - 744 = 73`. After changing the faulty movement from `-800` to `-40`, the later-movement total is `+16`, post-correction available units are `817 + 16 = 833`, and the delta is `833 - 73 = 760`. The corrected SKU has no effective sale in the named 14-day demand window, so this availability delta does not change its window demand.

After the correction, projected post-demand values below the 100-EA operating buffer are:

| SKU | Projected post-demand each |
| --- | ---: |
| `SKU-00473` | 18.0 |
| `SKU-00415` | 44.0 |
| `SKU-00472` | 67.0 |
| `SKU-00471` | 70.0 |
| `SKU-00468` | 76.0 |
| `SKU-00466` | 85.0 |
| `SKU-00418` | 88.0 |
| `SKU-00413` | 94.0 |
| `SKU-00467` | 94.0 |

The output set is displayed by SKU ascending: `SKU-00413`, `SKU-00415`, `SKU-00418`, `SKU-00466`, `SKU-00467`, `SKU-00468`, `SKU-00471`, `SKU-00472`, `SKU-00473`. The ranking is by projected value ascending and then SKU, so `SKU-00473` is the unique highest-risk SKU. Nine of 100 active APPAREL SKUs are at risk; `9/100 = 0.09`, strictly fewer than 10%, so the corrected status is `CONTROLLED`. Before correction, `SKU-00463` had projected value `73.0`, producing 10 at-risk SKUs and `WATCH`; after correction it leaves the risk set.

On the private copy, the exact guarded update was equivalent to:

```sql
UPDATE inventory_movements
SET canonical_quantity_each = -40,
    canonical_uom_multiplier = 1,
    corrected_at = '2026-06-01T08:45:00Z',
    correction_reason = 'UOM_SOURCE_RECONCILIATION'
WHERE movement_row_id = 'IMR-0000110'
  AND canonical_quantity_each = -800
  AND canonical_uom_multiplier = 20;
```

The same transaction inserted exactly one `correction_audit` row: audit ID `AUD-INV-20260601-003`, correction key `INV-20260601-WEST-APPAREL-003`, entity type `inventory_movement`, entity ID `MOV-0000110`, source row ID `IMR-0000110`, field name `canonical_quantity_each+canonical_uom_multiplier`, old value `{"canonical_quantity_each":-800,"canonical_uom_multiplier":20}`, new value `{"canonical_quantity_each":-40,"canonical_uom_multiplier":1}`, reason `UOM_SOURCE_RECONCILIATION`, corrected time `2026-06-01T08:45:00Z`, and actor `inventory-data-quality`. The transaction produced one business-row change and one audit-row change. Post-change row and audit queries matched, so `correction_status` is `APPLIED`.

### Output contract and atomic evaluation

The output has four exact top-level objects: `correction_target`, `mutation_result`, `availability_reconciliation`, and `stockout_analysis`. Integer fields use true JSON integers; booleans and floating spellings do not satisfy integer checks. The risk list must contain unique strings in ascending SKU order. Extra fields are prohibited by the template. The evaluator remains diagnostic: an unreadable or non-object candidate fails all points without a traceback, while ordinary business errors fail only their associated whole points.

The eight atomic scoring points total raw weight 19:

- `SP001`, weight 3: `movement_row_id`, `movement_id`, and `sku` must all match. This is the cross-source anomaly identification outcome.
- `SP002`, weight 3: both old/new canonical quantity values and both old/new canonical multiplier values must match. This is the canonical-versus-raw correction decision.
- `SP003`, weight 2: `affected_business_rows=1`, `audit_rows=1`, and `correction_status=APPLIED` must all match. These fields jointly represent one controlled transaction/audit success outcome.
- `SP004`, weight 2: pre-correction available units for the corrected SKU must be integer `73`.
- `SP005`, weight 3: post-correction available units `833` and delta `760` must both match. They form one before/after correction result.
- `SP006`, weight 3: the exact unique nine-SKU post-correction risk list must match in ascending order. This is the stable set outcome.
- `SP007`, weight 2: highest-risk SKU must be `SKU-00473`. This is the projected-margin ranking outcome.
- `SP008`, weight 1: corrected stockout status must be enum `CONTROLLED`. This is the family-level threshold judgment.

Each point earns either all of `weight / 19` or zero; no within-point fraction exists. The points cover target identification, correction judgment, mutation governance, before/after inventory, risk-set construction, ranking, and classification rather than duplicating one fact. The standard answer scores exactly `19/19 = 1.0`.

Likely solver pitfalls include trusting a raw joined row count; failing to collapse movement retry copies; applying the document filter before establishing effective copies; using a non-latest snapshot; including movements at or before the chosen snapshot; omitting the inclusive cutoff; using signed rather than absolute SALE quantity for demand; dividing by seven rather than fourteen before multiplying by seven; overlooking the task-local 100-EA buffer; including inactive family SKUs; correcting only one of the two inconsistent canonical fields; changing raw/source identity; omitting either old-value guard; separating the update from the audit insert; trusting change counts without re-querying; reversing the availability delta; sorting the risk list by projected value instead of SKU; or using `<=` instead of strict `<` for thresholds.

### Transfer design and construction record

The explicit test anchors are `train_003` and `train_004`.

- `train_003` anchors `SP001`, `SP002`, and `SP003`: compare source evidence with canonical values, isolate one effective contradiction, preserve raw/source identity, guard the stable primary key and every old canonical value, append one deterministic audit in the same controlled transaction, and re-query before reporting success. What changes is the business table and the corrected field pair: inventory quantities and multipliers replace carrier status.
- `train_004` anchors `SP006`: resolve imported copies by source identity, aggregate cutoff-consistent effective outcomes, count stable business IDs, and produce deterministic sets. What changes is the inventory snapshot-plus-movement model and a SKU risk set instead of warehouse task outcomes.
- The transfer habits also support `SP004`/`SP005` through cutoff-safe aggregation and post-mutation re-query. The exact snapshot arithmetic, 14-day demand window, 100-EA buffer, SKU ranking, and status boundary remain task-specific exploration for `SP004` through `SP008`.

The transfer-dependent difficulty is recognizing the hidden effective-copy convention, making the canonical-versus-raw decision, executing a guarded one-row plus one-audit transaction, verifying it, and constructing a stable effective set. The task-specific difficulty is discovering the inventory schema, the unique APPAREL document contradiction, the signed snapshot/movement arithmetic, the demand-period aggregation, the exact nine-SKU set, the projected-margin ranking, and the 9% status. The solver-visible prompt names the business request and public services but does not restate the transferable SOP or any hidden target ID/value.

- Author: `task-builder-test-003`
- Created: `2026-07-16`
- Updated: `2026-07-16`
- Major changes: created the stateful inventory control request, documented the one-field nondegeneracy adjustment, derived the standard answer on a private corrected copy, implemented eight atomic weighted points, and established full-score and sensitivity validation targets.

## 中文

### 数据来源、任务定义与场景适配

本任务是 `task_group_022` 中的未见有状态测试任务 `test_003`，负责人为 `task-builder-test-003`，场景为 `SCN_022_sql_database_analytics`，来源样例为 `E001`、`E002`、`E003`。设计依据是 `scratch/task_briefs/test_003.md` 以及 `scratch/task_group_design.md` 中的 `test_003` 方案和迁移矩阵。业务背景是库存控制团队需要核对 `WH-WEST-01`、`APPAREL`、来源单据 `DOC-0000028` 的 ERP 单位异常，并在 `2026-05-31T23:59:59Z` 截止点重新计算可用库存和缺货风险。

共享业务数据由 `env/generate_data.py` 生成。构建阶段通过只读 SQLite URI 检查保留基线 `env/atlas_baseline.sqlite3`，观察到的 SHA-256 为 `a662aae89583e5ef4ad60d1516f5a6c48fb0cf026aae5b559264de2dfdb5a597`。所有假设更新、审计插入和修复后计算都只在权限为 0600 的私有临时副本中完成，随后删除；最终哈希复核确认保留基线未被修改。

该任务符合关系数据库运营分析场景：`products` 定义有效 APPAREL SKU，`inventory_snapshots` 提供每个仓库/SKU 的期初状态，`inventory_movements` 提供可能有导入重试的带符号变动和销售需求证据，`correction_audit` 提供治理凭证。任务跨越 ERP 原始单位证据、规范化 each 数量、截止时点聚合、受控原子事务和修复后的运营判断，不能简化为单行查询。

### 材料和接口映射

- `input/prompt.txt` 给出真实月末核对请求、变更授权、数据保护要求、环境入口和输出位置。
- `inventory_control_request.json` 固定仓库、品类、来源单据、截止时间、需求窗口及公式、有效 SKU 群组、100-EA 运营缓冲、排序与状态阈值、确定性审计元数据和成功规则。
- `answer_template.json` 规定全部键、嵌套对象、整数单位与精度、唯一升序 SKU 列表、枚举以及禁止额外字段。
- `/api/schema` 和 `/api/data-dictionary` 用于理解表关系、原始/规范字段、来源身份和时间语义。
- `/api/sql` 用于只读探索、唯一性检查以及修复前后复算。
- `/api/sql/transaction` 用于在一个事务中执行带主键和两个旧值保护的规范字段更新及一行审计插入。
- `/api/correction-audit` 用于独立核验固定审计记录。
- `output/answer.json` 是可复现标准答案，`eval/eval.sh` 和 `evaluator.py` 实现八个原子加权评分点。

预期工作包括模式探索、有效副本消解、异常定位、修复前聚合、安全事务、修复后核验、稳定集合与排名计算，以及严格 JSON 输出。可见材料只提供本任务的业务定义，不公开隐藏的导入副本处理流程和目标 ID。

### 非退化调整

任务简报中的原始零边际规则在该固定群组和截止时间下得到空的修复后风险集合，最低预测余额仍为 `18.0` each。空列表会使权重 3 的集合结果退化。依据通用构建约定，本任务只增加一个标量请求事实：最低预测运营缓冲为 `100` each，当“修复后可用量减七日需求”严格小于 100 时判定风险。

这是唯一分析偏离。仓库、APPAREL 群组、来源单据、截止时间、14 天需求证据、七日需求公式、可用量公式、修复目标、修复字段和状态百分比阈值均未改变。该调整使修复前风险数为 10、状态为 `WATCH`，修复后风险数为 9、状态为 `CONTROLLED`，从而保留了修复后复算的业务意义。求解器可见请求明确写出 100-EA 规则，但没有泄露隐藏流程。

### 精确隐藏解法与计算

库存变动先按 `(source_system, external_event_id)` 去重，保留 `(ingested_at, movement_row_id)` 最大的副本，再应用任务范围。唯一异常证据如下：

- 行 ID `IMR-0000110`，业务变动 ID `MOV-0000110`，SKU `SKU-00463`；
- 原始证据为 `raw_quantity=-40`、`raw_uom='EA'`、`raw_uom_multiplier=1`；
- 错误规范值为数量 `-800`、乘数 `20`；
- 正确规范值为数量 `-40`、乘数 `1`；
- 事件为 `2026-05-13T10:41:00Z` 的 `SALE`，来源为 `ERP_LEDGER`，外部事件为 `ERP-MOV-0000110`。

规范数量按原始证据计算为 `-40 * 1 = -40`。所有原始值、来源身份、单据、仓库、SKU、变动类型和时间保持不变。

100 个有效 APPAREL SKU 都有截止前快照。每个 SKU 取截止前最新快照，再累加快照之后且不晚于截止点的有效带符号变动。需求窗口为 `2026-05-18T00:00:00Z` 至 `2026-05-31T23:59:59Z`，两端包含；七日需求等于 14 日有效 `SALE` 绝对规范数量总和的一半。英文部分给出的 SQL 是可复现的精确汇总基础。

目标 SKU 的最新快照为 `2026-05-01T00:00:00Z`，`on_hand_each=905`、`reserved_each=88`，快照可用量为 `817`。修复前后续有效变动是 `+35`、`-800`、`+21`，合计 `-744`，所以修复前可用量为 `73`。把异常变动改为 `-40` 后，后续变动合计 `+16`，修复后可用量为 `833`，增量为 `760`。该 SKU 在指定 14 天需求窗口中没有有效销售，因此需求不随此次修复改变。

修复后严格低于 100 each 的风险 SKU 及预测余额为：`SKU-00473` 18、`SKU-00415` 44、`SKU-00472` 67、`SKU-00471` 70、`SKU-00468` 76、`SKU-00466` 85、`SKU-00418` 88、`SKU-00413` 94、`SKU-00467` 94。输出按 SKU 升序为 `SKU-00413`、`SKU-00415`、`SKU-00418`、`SKU-00466`、`SKU-00467`、`SKU-00468`、`SKU-00471`、`SKU-00472`、`SKU-00473`。按预测余额升序再按 SKU 排序，最高风险 SKU 是 `SKU-00473`。风险比例为 `9/100=0.09`，严格低于 10%，所以状态为 `CONTROLLED`。修复前 `SKU-00463` 的预测余额为 73，风险数为 10，状态为 `WATCH`。

私有副本中的更新同时修改 `canonical_quantity_each=-40`、`canonical_uom_multiplier=1`、固定更正时间和原因，并以 `movement_row_id='IMR-0000110'`、旧数量 `-800`、旧乘数 `20` 作为保护条件。相同事务插入一行审计：`AUD-INV-20260601-003`、`INV-20260601-WEST-APPAREL-003`、实体类型 `inventory_movement`、实体 ID `MOV-0000110`、来源行 ID `IMR-0000110`、字段名 `canonical_quantity_each+canonical_uom_multiplier`、旧值 `{"canonical_quantity_each":-800,"canonical_uom_multiplier":20}`、新值 `{"canonical_quantity_each":-40,"canonical_uom_multiplier":1}`、原因 `UOM_SOURCE_RECONCILIATION`、时间 `2026-06-01T08:45:00Z`、操作者 `inventory-data-quality`。业务行和审计行变更数均为 1，复查成功，因此更正状态为 `APPLIED`。

### 原子评估、风险点与迁移设计

八个评分点总原始权重为 19，每点只能全得或零分：

- `SP001`，权重 3：异常行 ID、变动 ID 和 SKU 全部正确。
- `SP002`，权重 3：规范数量和规范乘数的旧值、新值全部正确。
- `SP003`，权重 2：业务行数 1、审计行数 1、状态 `APPLIED` 全部正确，作为一个受控事务结果。
- `SP004`，权重 2：修复前可用量为整数 73。
- `SP005`，权重 3：修复后可用量 833 和增量 760 同时正确。
- `SP006`，权重 3：九个 SKU 的唯一升序风险列表完全正确。
- `SP007`，权重 2：最高风险 SKU 为 `SKU-00473`。
- `SP008`，权重 1：修复后状态为枚举 `CONTROLLED`。

每点分配值为 `weight/19`，没有点内部分得分。不可读或顶层非对象的答案全部得零且不产生回溯；普通业务错误只影响关联点。标准答案为 `19/19=1.0`。

常见错误包括信任重复导入行、在建立有效副本前过滤、使用非最新快照、错误包含快照时刻的变动、遗漏截止边界、用带符号销售量计算需求、错误使用 7 而不是 14 作为平均天数、忽略 100-EA 缓冲、纳入停用 SKU、只修复一个规范字段、修改原始或来源字段、遗漏任一旧值保护、分开提交更新与审计、不复查事务结果、写反增量、按风险值而不是 SKU 展示集合，或把严格小于写成小于等于。

明确训练锚点为 `train_003` 和 `train_004`。`train_003` 支撑 `SP001`、`SP002`、`SP003`：迁移原始证据与规范值核对、有效异常定位、原始/来源字段保护、稳定主键和旧值保护、同一事务审计以及修复后复查；变化在于本任务使用库存数量与乘数，而不是承运商状态。`train_004` 支撑 `SP006`：迁移来源身份去重、截止一致聚合、稳定业务 ID 计数和确定性集合；变化在于这里是快照加变动的 SKU 风险集合。截止一致聚合和复查习惯也帮助 `SP004`、`SP005`。

迁移依赖难点是识别有效副本约定、作出规范字段判断、完成带保护的一行更新加一行审计、核验结果并构造稳定集合。任务特定探索难点是发现库存表关系、定位唯一 APPAREL 单据异常、计算带符号快照/变动、聚合需求窗口、得到九个 SKU、完成预测余额排名和 9% 状态判断。求解器可见材料没有公开这些隐藏目标 ID、数值或完整 SOP。

- 作者：`task-builder-test-003`
- 创建日期：`2026-07-16`
- 更新日期：`2026-07-16`
- 主要变更：创建有状态库存控制任务，记录唯一非退化调整，在私有修复副本上推导答案，实现八个原子加权评分点，并建立满分与敏感性验证目标。
