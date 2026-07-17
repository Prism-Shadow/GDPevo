# train_002 — Refund settlement reconciliation / 退款结算核对

## English construction notes

### Lineage and task definition

This real train task belongs to `SCN_022_sql_database_analytics` and uses source examples `E001`, `E002`, and `E003` as design lineage. Its direct construction sources are the `train_002` assignment brief, the `train_002` section of `scratch/task_group_design.md`, the shared Atlas Commerce Operations interface, and the retained generated baseline `task_group/task_group_022/env/atlas_baseline.sqlite3`. The task-local visible materials are `input/prompt.txt`, `input/payloads/refund_reconciliation_request.json`, and `input/payloads/answer_template.json`.

Refund Operations and Payments Risk request a close-control reconciliation for production accounts with `accounts.tier='GOLD'`. The effective refund `service_date` window is 2026-03-01 through 2026-04-30 inclusive. The solver must return seven structured outcomes: eligible distinct refunded orders, settled logical refunds, linked reversals, net USD value, the top two normalized reasons, unresolved leakage order IDs, and the controlled cohort-risk enum.

The visible workflow is to discover the relational model through the authenticated service at `<TASK_ENV_BASE_URL>`, query the business data, reconcile the requested cohort, and write one object matching the answer template to `output/answer.json`. This is read-only work. The prompt intentionally does not disclose the retry precedence, production-flag filters, reversal mechanics, or round-at-end construction procedure.

### Scenario fit and material map

The task fits SQL Database Analytics because the result depends on multi-table operational lineage rather than a single record lookup. Provider attempts flow into `refund_attempts`; each row connects to `orders`, each order connects to `accounts`, daily currency conversion comes from `fx_rates`, and linked reversal records alter the financial interpretation of earlier refund activity. Imported retries and nonterminal outcomes create realistic reconciliation noise.

- `GET /api/schema`: exposes tables, keys, relationships, and indexes needed to discover the model.
- `GET /api/data-dictionary`: explains money units, FX units, timestamps, source identifiers, and production flags without giving the solution.
- `POST /api/sql`: supports the read-only CTE, joins, window functions, aggregation, and verification queries. The transaction and correction-audit endpoints are not needed.
- `accounts`: supplies `tier`, `is_internal`, and `is_test` for the production cohort.
- `orders`: supplies stable `order_id`, the account relationship, order currency, and `gross_amount_minor`.
- `refund_attempts`: supplies row and logical refund identifiers, retry identity, status, reason, amount, currency, service date, ingestion order, and reversal linkage.
- `fx_rates`: supplies `usd_per_unit` by `rate_date` and currency.
- `refund_reconciliation_request.json`: supplies the task-specific cohort, date range, candidate definition, ranking rule, monetary policy, and risk thresholds.
- `answer_template.json`: fixes the seven output keys, types, units, two-decimal money precision, enum choices, list sizes, and stable ordering; extra top-level fields are disallowed.
- `output/answer.json`: stores the reproducible standard answer.
- `eval/evaluator.py` and `eval/eval.sh`: implement the seven atomic weighted checks and the stable command-line entry point.

### Hidden solution and exact calculation basis

Construction used the retained SQLite baseline directly. Effective imports are obtained by partitioning `refund_attempts` on `(source_system, external_event_id)` and keeping row number 1 under `ingested_at DESC, refund_row_id DESC`. The retained rows are joined through `orders.account_id` to `accounts`, restricted to `tier='GOLD'`, `is_internal=0`, `is_test=0`, and the inclusive service-date window.

There are 593 physical refund rows before effective-copy selection and 549 effective rows after 44 retry copies are removed. The effective status counts are 484 `SETTLED`, 42 `FAILED`, 21 `VOIDED`, and 2 `REVERSED`. Failed and voided rows contribute neither countable settlement value nor reversal value.

The exact outcome basis is:

- `eligible_refunded_order_count = COUNT(DISTINCT order_id)` over effective settled logical refunds: **484**.
- `effective_settled_logical_refund_count = COUNT(DISTINCT refund_id)` for effective `SETTLED` rows: **484**.
- `effective_linked_reversal_count = COUNT(DISTINCT refund_id)` for effective `REVERSED` rows with a non-null `linked_refund_id`: **2**.
- Each contributing amount is `amount_minor / 100 × fx_rates.usd_per_unit`, joining `fx_rates.rate_date` to the row `service_date` and matching the row currency. Settled rows are positive; effective linked reversals are negative. The unrounded total is **115674.62179**, so `net_refund_amount_usd` is **115674.62**.
- Normalized reason is `UPPER(TRIM(reason_code))`. A reversal's negative amount is attributed to the normalized reason on its directly linked refund. The unrounded reason totals, in rank order, are `DAMAGED` 24630.42865, `NOT_AS_DESCRIBED` 24081.20811, `CUSTOMER_RETURN` 23150.57219, `DUPLICATE_CHARGE` 22887.60766, and `LATE_DELIVERY` 20924.80518. Sorting by net USD descending and then reason ascending yields **[DAMAGED, NOT_AS_DESCRIBED]**.
- Candidate analysis starts from eligible refunded orders. Per-order net value uses the same signed USD contributions. Order gross is `gross_amount_minor / 100 × usd_per_unit` in the order currency at the settled refund's `service_date`. An unreversed settled refund is one whose `refund_id` is not targeted by an effective in-scope linked reversal. The repeated-normalized-reason branch produces no order in this cohort; 29 orders qualify because net settled refund USD exceeds gross order USD.

The exact ascending candidate list is:

`ORD-000344`, `ORD-000436`, `ORD-000778`, `ORD-001237`, `ORD-001551`, `ORD-001845`, `ORD-002365`, `ORD-002486`, `ORD-004262`, `ORD-004502`, `ORD-004714`, `ORD-006117`, `ORD-007093`, `ORD-007527`, `ORD-007808`, `ORD-008014`, `ORD-008530`, `ORD-008622`, `ORD-009050`, `ORD-009142`, `ORD-009898`, `ORD-010367`, `ORD-010528`, `ORD-010602`, `ORD-012121`, `ORD-012803`, `ORD-013147`, `ORD-013581`, `ORD-013737`.

The candidate rate is `29 / 484 = 0.059917355...`, or about 5.9917%. It is not below 5%, and net refunds also exceed USD 50,000, so the exact `cohort_risk` is **HIGH**. Only the requested net amount is emitted as a monetary value, and it is rounded once to two decimals.

### Evaluation basis and atomic rubric

The raw weights total 16. Each point checks one distinct business result and earns either its full `weight / 16` assigned score or zero. A parse failure or non-object candidate deterministically fails all points without a traceback; an ordinary error in one field does not invalidate unrelated points.

| ID | Goal | Raw weight | Atomic pass logic |
| --- | --- | ---: | --- |
| `SP001` | Eligible distinct refunded-order population | 2 | The integer `eligible_refunded_order_count` exactly equals 484. |
| `SP002` | Effective settled logical refund count | 3 | The integer `effective_settled_logical_refund_count` exactly equals 484. |
| `SP003` | Effective linked reversal count | 2 | The integer `effective_linked_reversal_count` exactly equals 2. |
| `SP004` | Net refund amount USD | 3 | The numeric `net_refund_amount_usd`, evaluated at two-decimal half-up precision, exactly equals 115674.62. |
| `SP005` | Exact top-two reason ranking | 2 | `top_two_reason_codes` exactly equals the required two-item ordered array. |
| `SP006` | Exact unresolved leakage set | 3 | `unresolved_leakage_order_ids` exactly equals the complete ascending, duplicate-free standard array. |
| `SP007` | Cohort risk enum | 1 | `cohort_risk` is the exact controlled value `HIGH`. |

These goals cover population, logical event reconciliation, reversal activity, monetary exposure, reason prioritization, exception identification, and policy classification. None is a duplicate re-check of another output.

Likely model pitfalls include counting physical retry rows; trusting provider attempts without effective-copy selection; retaining internal or test accounts; treating failed or voided attempts as money; failing to subtract linked reversals; converting with an account currency or a single period rate; converting order gross on an unrelated date; rounding row values before aggregation; counting joined rows instead of stable refund/order IDs; ranking gross rather than net reasons; missing strict threshold comparisons; or returning the candidate set in unstable order.

### Train transfer signal and difficulty split

Solving this task and comparing an attempt with its structured answer can reveal reusable habits: inspect schema and dictionary before querying; resolve imported copies by stable upstream identity and ingestion precedence; distinguish row identifiers from logical business IDs; apply production exclusions; reconcile terminal settlement and linked reversal effects; join daily FX on the business service date; aggregate before rounding; and use deterministic secondary sorting. The risk enum also demonstrates how strict business thresholds should be evaluated from unrounded cohort facts.

The transfer-dependent difficulty is the reusable reconciliation discipline: deduplication, stable-ID counting, reversal subtraction, daily FX conversion, production filtering, and stable ranking. Task-specific exploration remains necessary to find the Atlas table relationships and fields, apply the GOLD and March-April scope, test both leakage predicates, calculate the candidate denominator, and apply this request's exact USD thresholds. The train task is a real operational analysis rather than a tutorial, but its answer provides a concrete signal for later tasks in the same operation family.

### Construction record

- Author: `task-builder-train-002`
- Created: 2026-07-16
- Updated: 2026-07-16
- Major change: initial construction of the real train task, reproducible standard answer, seven-point evaluator, and bilingual audit notes.
- Deviation: none. The specified cohort produced nonzero settlements, reversals, money, and leakage candidates, plus an untied reason ranking.

## 中文构建说明

### 数据谱系与任务定义

这个真实训练任务属于 `SCN_022_sql_database_analytics`，设计谱系来自源示例 `E001`、`E002` 和 `E003`。直接构建依据包括 `train_002` 任务简报、`scratch/task_group_design.md` 中的 `train_002` 小节、共享的 Atlas Commerce Operations 接口，以及保留的生成基线 `task_group/task_group_022/env/atlas_baseline.sqlite3`。任务本地的求解器可见材料是 `input/prompt.txt`、`input/payloads/refund_reconciliation_request.json` 和 `input/payloads/answer_template.json`。

退款运营与支付风险团队需要一份 GOLD 层级生产账户的关账核对报告。有效退款的 `service_date` 范围为 2026-03-01 至 2026-04-30，包含首尾日期。求解器必须返回七项结构化结果：符合条件的不同退款订单数、已结算逻辑退款数、关联冲正数、美元净额、前两个标准化原因、未解决泄漏订单编号以及受控的群组风险枚举。

可见工作流是通过 `<TASK_ENV_BASE_URL>` 上经过认证的服务发现关系模型、查询业务数据、核对指定群组，并将一个符合答案模板的对象写入 `output/answer.json`。本任务只读。提示刻意不公开重试副本优先级、生产标志过滤、冲正机制和最后统一舍入的完整构建过程。

### 场景契合度与材料地图

本任务符合 SQL 数据库分析场景，因为答案依赖多表运营谱系，而不是单行查找。供应商尝试进入 `refund_attempts`；每一行关联 `orders`，订单再关联 `accounts`；每日汇率来自 `fx_rates`；关联冲正记录会改变早期退款活动的财务解释。导入重试与非终态结果构成了真实的核对噪声。

- `GET /api/schema`：提供表、键、关系和索引，用于发现数据模型。
- `GET /api/data-dictionary`：解释金额单位、汇率单位、时间戳、来源标识和生产标志，但不直接给出解法。
- `POST /api/sql`：支持只读 CTE、连接、窗口函数、聚合和复核查询；本任务不需要事务与更正审计端点。
- `accounts`：提供生产群组所需的 `tier`、`is_internal` 和 `is_test`。
- `orders`：提供稳定的 `order_id`、账户关系、订单币种和 `gross_amount_minor`。
- `refund_attempts`：提供行级与逻辑退款标识、重试身份、状态、原因、金额、币种、服务日期、摄取顺序和冲正关联。
- `fx_rates`：按 `rate_date` 和币种提供 `usd_per_unit`。
- `refund_reconciliation_request.json`：提供任务特定的群组、日期范围、候选定义、排序规则、金额政策和风险阈值。
- `answer_template.json`：固定七个输出键、类型、单位、两位小数精度、枚举选择、列表大小和稳定顺序，并禁止额外顶层字段。
- `output/answer.json`：保存可复现的标准答案。
- `eval/evaluator.py` 与 `eval/eval.sh`：实现七个原子加权检查及稳定的命令行入口。

### 隐藏解法与精确计算依据

构建时直接使用保留的 SQLite 基线。先按 `(source_system, external_event_id)` 对 `refund_attempts` 分区，并按 `ingested_at DESC, refund_row_id DESC` 排序保留第一行，得到有效导入记录。然后通过 `orders.account_id` 连接 `accounts`，筛选 `tier='GOLD'`、`is_internal=0`、`is_test=0` 以及包含边界的服务日期范围。

有效副本选择之前共有 593 行物理退款记录；移除 44 个重试副本后有 549 行有效记录。有效状态计数为：484 个 `SETTLED`、42 个 `FAILED`、21 个 `VOIDED` 和 2 个 `REVERSED`。失败和作废记录既不贡献结算金额，也不贡献冲正金额。

精确结果依据如下：

- 对有效已结算逻辑退款计算不同 `order_id`，`eligible_refunded_order_count` 为 **484**。
- 对有效 `SETTLED` 行计算不同 `refund_id`，`effective_settled_logical_refund_count` 为 **484**。
- 对状态为 `REVERSED` 且 `linked_refund_id` 非空的有效行计算不同 `refund_id`，`effective_linked_reversal_count` 为 **2**。
- 每个贡献金额为 `amount_minor / 100 × fx_rates.usd_per_unit`，其中 `fx_rates.rate_date` 与该行 `service_date` 连接，并匹配该行币种。已结算行为正值，有效关联冲正为负值。未舍入总额是 **115674.62179**，因此 `net_refund_amount_usd` 为 **115674.62**。
- 标准化原因为 `UPPER(TRIM(reason_code))`。冲正负值归入它直接关联退款的标准化原因。按排名顺序，未舍入原因净额为：`DAMAGED` 24630.42865、`NOT_AS_DESCRIBED` 24081.20811、`CUSTOMER_RETURN` 23150.57219、`DUPLICATE_CHARGE` 22887.60766、`LATE_DELIVERY` 20924.80518。按净美元降序、原因升序排序得到 **[DAMAGED, NOT_AS_DESCRIBED]**。
- 候选分析从符合条件的退款订单开始。每个订单的净额使用相同的带符号美元贡献。订单毛额按已结算退款的 `service_date`，以订单币种计算 `gross_amount_minor / 100 × usd_per_unit`。未冲正的已结算退款是指其 `refund_id` 没有被范围内有效关联冲正指向。本群组中“相同标准化原因重复”分支没有产生订单；有 29 个订单因为退款净额超过订单毛额而入选。

精确升序候选列表为：

`ORD-000344`、`ORD-000436`、`ORD-000778`、`ORD-001237`、`ORD-001551`、`ORD-001845`、`ORD-002365`、`ORD-002486`、`ORD-004262`、`ORD-004502`、`ORD-004714`、`ORD-006117`、`ORD-007093`、`ORD-007527`、`ORD-007808`、`ORD-008014`、`ORD-008530`、`ORD-008622`、`ORD-009050`、`ORD-009142`、`ORD-009898`、`ORD-010367`、`ORD-010528`、`ORD-010602`、`ORD-012121`、`ORD-012803`、`ORD-013147`、`ORD-013581`、`ORD-013737`。

候选率为 `29 / 484 = 0.059917355...`，约为 5.9917%。它不低于 5%，而且退款净额也超过 50,000 美元，所以精确的 `cohort_risk` 为 **HIGH**。输出中只有请求的净额是金额字段，并且只在最后舍入为两位小数。

### 评估依据与原子评分规则

原始权重合计 16。每个评分点检查一个独立业务结果，只能获得完整的 `weight / 16` 分数或零分。解析失败或候选不是对象时，所有评分点会确定性失败且不输出回溯；某个普通字段错误不会使无关评分点失效。

| 编号 | 目标 | 原始权重 | 原子通过逻辑 |
| --- | --- | ---: | --- |
| `SP001` | 符合条件的不同退款订单群体 | 2 | 整数 `eligible_refunded_order_count` 精确等于 484。 |
| `SP002` | 有效已结算逻辑退款数 | 3 | 整数 `effective_settled_logical_refund_count` 精确等于 484。 |
| `SP003` | 有效关联冲正数 | 2 | 整数 `effective_linked_reversal_count` 精确等于 2。 |
| `SP004` | 美元退款净额 | 3 | 数值 `net_refund_amount_usd` 按两位小数四舍五入后精确等于 115674.62。 |
| `SP005` | 前两个原因的精确排名 | 2 | `top_two_reason_codes` 与要求的两项有序数组完全相同。 |
| `SP006` | 精确的未解决泄漏集合 | 3 | `unresolved_leakage_order_ids` 与完整、升序、无重复的标准数组完全相同。 |
| `SP007` | 群组风险枚举 | 1 | `cohort_risk` 精确等于受控值 `HIGH`。 |

这些目标分别覆盖群体、逻辑事件核对、冲正活动、金额风险、原因优先级、异常识别和政策分类，没有重复检查同一个答案事实。

常见模型错误包括：直接计数物理重试行；不做有效副本选择；保留内部或测试账户；把失败或作废尝试计入金额；没有减去关联冲正；使用账户币种或单一期间汇率；在无关日期换算订单毛额；先对逐行金额舍入再聚合；计算连接行数而非稳定退款或订单标识；按毛额而非净额排列原因；忽略严格小于的阈值；或者以不稳定顺序返回候选集合。

### 训练迁移信号与难度拆分

完成本任务并将尝试结果与结构化答案比较，可以提炼出可复用习惯：先查看模式和数据字典；按稳定上游身份与摄取优先级处理导入副本；区分行标识与逻辑业务标识；应用生产排除规则；核对终态结算与关联冲正；按业务服务日期连接每日汇率；聚合后再舍入；并使用确定性的次级排序。风险枚举也展示了如何基于未舍入的群组事实应用严格业务阈值。

依赖迁移的难点是可复用的核对纪律，包括去重、稳定标识计数、冲正扣减、每日汇率换算、生产过滤和稳定排名。任务特定探索仍然必不可少：找出 Atlas 表关系和字段、应用 GOLD 与 3—4 月范围、验证两个泄漏谓词、计算候选率分母，并应用本请求特有的美元阈值。本训练任务是真实运营分析而不是教程，但其答案会为同一操作族的后续任务提供具体迁移信号。

### 构建记录

- 作者：`task-builder-train-002`
- 创建日期：2026-07-16
- 更新日期：2026-07-16
- 主要变更：首次构建真实训练任务、可复现标准答案、七点评估器和双语审计说明。
- 偏差：无。指定群组产生了非零结算、冲正、金额和泄漏候选，原因排名也没有并列。
