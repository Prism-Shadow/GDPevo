# train_003 construction and evaluation notes

## English

### Lineage and task definition

This is the real stateful train task assigned to `task-builder-train-003` for scenario `SCN_022_sql_database_analytics` in `task_group_022`. The source scenario examples are `E001`, `E002`, and `E003`: schema discovery and relational analytics, controlled data-quality repair, and sandboxed operational tool use. The task specializes the group design's carrier state reconstruction plus safe-correction family.

The business setting is an Atlas Commerce carrier quality review. The generated shared environment is constructed by `env/generate_data.py`; construction uses the retained `env/atlas_baseline.sqlite3` baseline. The task-local request `input/payloads/carrier_quality_request.json` fixes import batch `BATCH-03-01-2`, warehouse `WH-EAST-01`, cutoff `2026-03-19T23:59:59Z`, production shipment scope, backlog definition, and deterministic correction metadata. `input/prompt.txt` authorizes one minimal canonical correction and requires a post-change backlog report. `input/payloads/answer_template.json` is the exact solver-visible JSON contract, and `output/answer.json` is the reproducible standard answer.

The expected work is to discover the schema, isolate the requested cohort, resolve import retries and historical state, cross-check raw and canonical carrier values, measure the pre-change outcome, perform one guarded canonical update and one audit insert atomically, verify the row and audit receipt, reconstruct state again, and write the normalized result. The task is not a snapshot lookup: `shipments.current_status` can be stale, and imported carrier scans can have retried copies.

### Scenario fit and material map

This task models a real data-quality workflow between carrier ingestion, fulfillment operations, and audit governance. `shipments` links a physical shipment to an `orders` record and warehouse; `orders` links to `accounts` for production exclusions; `order_events` supplies effective cancellation state; `carrier_scans` carries raw source values, canonical operational values, source identity, import batch, ingestion time, and correction metadata; `source_import_batches` confirms batch identity; and `correction_audit` is the durable governance receipt. The carrier source flows from raw scan text and timestamp through canonical normalization into backlog reporting. The correction changes only that canonical layer.

Important materials and interfaces are:

- `input/prompt.txt`: analyst request, environment location, mutation authorization, and output destination.
- `input/payloads/carrier_quality_request.json`: task-specific scope, cutoff, backlog definition, allowed reason/actor, fixed audit identifiers, and success enum semantics.
- `input/payloads/answer_template.json`: exact keys, nesting, integer units/precision, enum choices, and prohibition on extra fields or arrays.
- `GET /api/schema`: table DDL and relationships.
- `GET /api/data-dictionary`: source/canonical field semantics and timestamp conventions.
- `POST /api/sql`: read-only exploration, anomaly isolation, and pre/post analytical queries.
- `POST /api/sql/transaction`: atomic guarded business update, audit insert, and optional in-transaction verification. It enforces approved tables/fields, primary-key and old-value guards, and expected total changes.
- `GET /api/correction-audit`: independent audit receipt verification.
- Shared generated tables `accounts`, `orders`, `order_events`, `shipments`, `carrier_scans`, `source_import_batches`, and `correction_audit`: evidence and state for this task.
- `output/answer.json`: hidden standard answer used by `eval/evaluator.py`.
- `eval/eval.sh` and `eval/evaluator.py`: task-local atomic weighted evaluation entry point and implementation.

### Exact hidden solution basis

Construction inspected the retained baseline through a read-only SQLite URI. Hypothetical mutation and post-change calculations were performed only on a mode-0600 temporary copy, which was deleted afterward. No task-local adjustment was necessary: the cohort is populated, the anomaly is unique, and the requested correction changes the backlog by one shipment.

Carrier import copies are deduplicated on `(source_system, external_event_id)`, retaining greatest `(ingested_at, scan_row_id)`. Order event copies use the same source/external rule, retaining greatest `(ingested_at, event_id)`. For each order, the latest retained event at or before the cutoff is ordered by `(event_at, event_id)`; effectively canceled orders are excluded. The cohort is the distinct production shipment set with `accounts.is_internal=0`, `accounts.is_test=0`, warehouse `WH-EAST-01`, and at least one retained carrier scan in batch `BATCH-03-01-2` whose `canonical_event_at` is at or before the cutoff. Shipment state is the latest retained carrier scan at or before the cutoff ordered by `(canonical_event_at, scan_row_id)`. Counts use distinct stable shipment IDs.

Within the batch/facility scope, comparing retained `raw_status` with `canonical_status` finds exactly one contradiction:

- `scan_row_id`: `SCN-0001272`
- `shipment_id`: `SHP-000212`
- corrected field: `canonical_status`
- old value: `IN_TRANSIT`
- raw-supported new value: `DELIVERED`
- unchanged source evidence: raw status `DELIVERED`, raw/canonical event time `2026-03-18T11:49:00Z`, source `CARRIER_HUB`, external event `CH-SHP-000212-6`

The pre-correction cohort has 102 shipments. Its effective final-state distribution is 31 `DELIVERED`, 16 `IN_TRANSIT`, 16 `LABEL_CREATED`, 30 `OUT_FOR_DELIVERY`, and 9 `PICKED_UP`. Therefore the pre-correction backlog count is `102 - 31 = 71`.

The approved atomic transaction updates the proven row with a stable primary-key and old-value guard:

```sql
UPDATE carrier_scans
SET canonical_status = 'DELIVERED',
    corrected_at = '2026-03-20T09:30:00Z',
    correction_reason = 'SOURCE_RECONCILIATION'
WHERE scan_row_id = 'SCN-0001272'
  AND canonical_status = 'IN_TRANSIT'
```

It also inserts exactly one `correction_audit` row with these values: audit ID `AUD-CQR-20260320-003`, correction key `CQR-20260320-EAST-CARRIER-003`, entity type `carrier_scan`, entity ID `SHP-000212`, source row ID `SCN-0001272`, field `canonical_status`, old/new `IN_TRANSIT`/`DELIVERED`, reason `SOURCE_RECONCILIATION`, corrected time `2026-03-20T09:30:00Z`, and actor `ops-data-quality`. The transaction expects two total changes: one business row and one audit row. Raw status, raw timestamp, source system, external event ID, import batch, shipment relationship, and all unrelated rows stay unchanged.

After commit, the guarded row reads `DELIVERED` and the fixed audit record exists. Re-running the same effective-state query leaves the cohort at 102, changes delivered shipments from 31 to 32, and changes backlog from 71 to 70. `backlog_delta` is defined as post minus pre, so it is `70 - 71 = -1`. Because one business row and one audit row committed and verification succeeded, `correction_status` is `APPLIED`.

### Output and atomic evaluation

The standard answer has five exact top-level objects/fields: `correction_target`, `mutation_result`, `audit_record`, `backlog_analysis`, and `correction_status`. All counts are JSON integers with zero decimal precision. No arrays or extra fields are permitted by the template. The evaluator uses strict JSON types, so booleans and floating-point spellings do not satisfy integer results.

The eight non-fractional scoring points total raw weight 18:

- `SP001`, weight 3: both the faulty `scan_row_id` and `shipment_id` must match. This is the anomaly-identification outcome.
- `SP002`, weight 3: `field_name`, `old_value`, and `new_value` must all match. This is the canonical correction decision.
- `SP003`, weight 2: `affected_business_rows` must be exactly one. This is the narrowly scoped mutation outcome; the endpoint contract enforces the key and old-value guard on a real successful update.
- `SP004`, weight 2: `audit_rows` must be one and every audit receipt field must match the approved and observed record. This is audit/idempotency compliance, not a duplicate of the business-row count.
- `SP005`, weight 2: pre-correction backlog shipment count must be 71.
- `SP006`, weight 3: post-correction backlog count must be 70 and delta must be -1. Both fields form one atomic before/after backlog outcome.
- `SP007`, weight 2: post-correction delivered shipment count must be 32. This independently validates the corrected final-state rollup.
- `SP008`, weight 1: correction status must be the controlled enum `APPLIED`.

Each point earns either its full `weight / 18` assigned score or zero. An unreadable JSON file or non-object candidate receives zero on every point without a traceback. Ordinary wrong values fail only the points whose paths they affect. The standard answer self-scores exactly 1.0. A numeric sensitivity mutation of the pre-backlog count fails only `SP005` and scores `16/18`; an enum mutation from `APPLIED` to `NOT_APPLIED` fails only `SP008` and scores `17/18`.

Likely solver pitfalls are using `shipments.current_status`; failing to collapse retry copies; including future scans after the cutoff; including internal/test accounts; counting joined scan rows instead of shipments; treating every raw/canonical difference outside the requested batch/facility as relevant; correcting a raw or source-identity field; omitting the old-value guard; performing the update and audit in separate transactions; using non-fixed audit identifiers; trusting reported change counts without re-querying; or reversing the backlog delta sign.

### Transfer design and construction record

The train transfer signal is cross-source anomaly identification, canonical-versus-raw judgment, source-copy deduplication, cutoff state reconstruction, a stable-ID plus old-value guard, canonical-only correction metadata, atomic audit/idempotency behavior, and stateful re-query. Comparing an attempt with the answer reveals which analytical conventions and mutation habits matter without making the solver-visible request a tutorial. These habits anchor later carrier and inventory correction tasks.

Transferable difficulty lies in schema-led exploration, retry resolution, event-derived state, safe mutation scope, audit governance, and post-change verification. Task-specific exploration difficulty lies in isolating batch `BATCH-03-01-2` at `WH-EAST-01`, discovering `SCN-0001272`/`SHP-000212`, and calculating the 71-to-70 backlog movement at this cutoff. The former can transfer; the exact identifiers and counts must be discovered from this task's shared data.

- Author: `task-builder-train-003`
- Created: `2026-07-16`
- Updated: `2026-07-16`
- Major changes: created the stateful carrier correction request, exact template, reproducible corrected-copy answer, eight-point evaluator, and sensitivity validation basis.

## 中文

### 来源、任务定义与场景适配

本任务是 `task_group_022` 中由 `task-builder-train-003` 负责的真实有状态训练任务，来源场景为 `SCN_022_sql_database_analytics`，参考样例为 `E001`、`E002`、`E003`。它把关系模式探索、数据质量安全修复和受控环境中的运营分析结合为“承运商状态重建 + 最小更正”工作流。

共享数据由 `env/generate_data.py` 生成，构建分析使用保留的 `env/atlas_baseline.sqlite3`。任务材料 `carrier_quality_request.json` 固定批次 `BATCH-03-01-2`、仓库 `WH-EAST-01`、截止时刻 `2026-03-19T23:59:59Z`、生产发运范围、积压定义以及确定性的审计元数据。求解者需要发现模式、确定范围、消除导入重试副本、按截止时刻重建状态、核对原始值与规范值、计算修复前指标、原子地完成一行规范字段更新与一行审计插入、复查结果并输出严格 JSON。

该任务符合 Atlas Commerce 的承运商质量复核场景：`shipments` 连接订单和仓库，`orders` 连接 `accounts` 以排除非生产账户，`order_events` 提供有效取消状态，`carrier_scans` 同时保存原始证据、规范化状态、来源标识、批次和更正元数据，`correction_audit` 保存治理凭证。数据从承运商原始扫描进入规范化运营层，再进入积压报表；本任务只修复规范化层，不改来源证据。

### 材料与接口用途

- `prompt.txt` 提供业务请求、环境入口、变更授权和输出位置。
- `carrier_quality_request.json` 提供范围、截止时刻、成功状态规则以及固定审计字段。
- `answer_template.json` 规定精确键、嵌套结构、整数单位与精度、枚举和禁止额外字段。
- `/api/schema` 与 `/api/data-dictionary` 用于理解表关系和字段语义。
- `/api/sql` 用于只读探索、异常识别及修复前后复算。
- `/api/sql/transaction` 用于带主键和旧值保护的一行更新、审计插入及原子提交，并校验预期总变更数。
- `/api/correction-audit` 用于独立核验审计凭证。
- `output/answer.json` 是可复现标准答案；`eval/eval.sh` 与 `evaluator.py` 执行原子加权评分。

### 隐藏解法与精确计算

构建阶段通过只读 SQLite URI 检查保留基线；所有假设性写入和修复后计算只在权限为 0600 的临时副本上执行，并在完成后删除，没有修改基线。数据非空、排名无并列问题，且目标更正会使积压减少一票，因此无需调整任务范围。

承运商副本按 `(source_system, external_event_id)` 去重，保留 `(ingested_at, scan_row_id)` 最大者；订单事件同理，稳定行标识为 `event_id`。订单与发运状态均只使用截止时刻之前的有效事件，并以事件时刻和稳定行标识确定最后状态。生产范围排除 `is_internal=1` 或 `is_test=1` 的账户以及截止时刻已有效取消的订单。批次成员要求至少有一条截止前的有效扫描属于目标批次，最终计数按唯一 `shipment_id` 完成。

唯一矛盾行为 `SCN-0001272`，发运为 `SHP-000212`；字段 `canonical_status` 的旧值是 `IN_TRANSIT`，原始状态支持的新值是 `DELIVERED`。修复前共有 102 个发运：31 个 `DELIVERED`、16 个 `IN_TRANSIT`、16 个 `LABEL_CREATED`、30 个 `OUT_FOR_DELIVERY`、9 个 `PICKED_UP`，所以积压为 71。

原子事务使用 `scan_row_id='SCN-0001272'` 和旧规范值 `IN_TRANSIT` 作为保护条件，将规范状态改为 `DELIVERED`，并写入更正时间与原因。审计行使用请求中固定的审计 ID、幂等键、实体/来源行/字段、旧值、新值、原因、时间和操作者；预期总变更数为 2，即一行业务记录和一行审计记录。提交后重新执行同一状态查询：总范围仍为 102，已送达从 31 变为 32，积压从 71 变为 70，`backlog_delta = 70 - 71 = -1`，因此状态为 `APPLIED`。

### 评分、风险与迁移信号

评分共 8 点、原始权重合计 18，所有点均整点通过或失败：`SP001`（3）核对扫描行和发运标识；`SP002`（3）核对字段及精确旧/新值；`SP003`（2）核对恰好一行业务变更；`SP004`（2）核对一行完整合规审计；`SP005`（2）核对修复前积压 71；`SP006`（3）同时核对修复后积压 70 和变化量 -1；`SP007`（2）核对修复后已送达 32；`SP008`（1）核对枚举 `APPLIED`。不可读或非对象 JSON 得 0 分，普通业务错误只影响相关评分点。标准答案得分为 1.0；将修复前积压改错只失去 `SP005`，得 `16/18`；将状态改为 `NOT_APPLIED` 只失去 `SP008`，得 `17/18`。

常见风险包括使用陈旧的 `current_status`、不消除重试副本、纳入截止时刻后的扫描、包含内部或测试账户、按联接行数而非发运标识计数、修复原始来源字段、缺少旧值保护、把更新和审计拆成两个事务、未使用固定审计标识、未在提交后复查，以及把变化量符号写反。

可迁移能力包括基于模式的探索、来源副本优先级、截止状态重建、原始与规范字段判断、主键加旧值保护、仅规范层修复、审计幂等契约和有状态复算。任务特定难点则是发现本批次与仓库中的精确目标行和 71 到 70 的指标变化；这些标识与数值不能从其他任务直接迁移。作者为 `task-builder-train-003`，创建和更新时间均为 `2026-07-16`；本次完成请求、模板、标准答案、八点评估器及敏感性验证依据。
