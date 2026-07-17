# test_002 — Refund leakage and provider exposure / 退款泄漏与供应商风险敞口

## English construction notes

### Lineage, task definition, and scenario fit

This unseen test task belongs to `SCN_022_sql_database_analytics` and carries design lineage from source examples `E001`, `E002`, and `E003`. Its direct construction sources are the `test_002` assignment brief, the `test_002` section and transfer coverage matrix in `scratch/task_group_design.md`, the shared Atlas Commerce Operations interface, and the retained generated baseline `task_group/task_group_022/env/atlas_baseline.sqlite3`. Task-local solver-visible materials are `input/prompt.txt`, `input/payloads/provider_exposure_request.json`, and `input/payloads/answer_template.json`.

Refund Operations and Payments Risk request the May-June provider-exposure close for production accounts with `accounts.tier='PLATINUM'`. The effective refund `service_date` window is 2026-05-01 through 2026-06-30 inclusive. The required structured outcomes are the eligible distinct refunded-order population, effective settled logical refund count, effective reversed USD, total net provider exposure, a complete provider exposure ranking, unresolved leakage order IDs, the dominant normalized reason, and the controlled exposure-status enum.

The visible workflow is read-only: discover the relational model through the authenticated service at `<TASK_ENV_BASE_URL>`, analyze the business records, and save one object conforming to the answer template at `output/answer.json`. The task fits SQL Database Analytics because the answer requires coordinated interpretation of provider attempts in `refund_attempts`, order and account relationships in `orders` and `accounts`, and daily currency conversion in `fx_rates`. Retry copies, noncontributing outcomes, linked delayed reversals, multiple currencies, and task-specific rankings prevent a single-row lookup from answering the request.

### Material map

- `GET /api/schema` exposes solver-facing tables, keys, relationships, and indexes needed for schema discovery.
- `GET /api/data-dictionary` explains source identifiers, ingestion timestamps, minor currency units, daily FX units, and production flags without identifying the target rows or publishing the reconciliation procedure.
- `POST /api/sql` supports read-only CTEs, window functions, joins, aggregation, and verification queries. The transaction and correction-audit endpoints are not needed.
- `accounts` supplies `tier`, `is_internal`, and `is_test` for cohort eligibility.
- `orders` supplies stable `order_id`, the account relationship, order currency, and `gross_amount_minor`.
- `refund_attempts` supplies physical row IDs, logical refund IDs, import identity, status, normalized-input reason text, amounts, currencies, service dates, ingestion order, providers, and reversal linkage.
- `fx_rates` supplies `usd_per_unit` by `rate_date` and currency.
- `provider_exposure_request.json` supplies the PLATINUM/window scope, monetary basis, provider and reason ranking rules, leakage predicates, and strict status thresholds.
- `answer_template.json` fixes all eight top-level keys, types, units, two-decimal money precision, nested provider keys, list ordering, reason and status choices, and the prohibition on extra fields.
- `output/answer.json` is the reproducible standard answer.
- `eval/evaluator.py` and `eval/eval.sh` implement the eight atomic weighted checks and robust command-line entry point.

### Hidden solution and reproducible calculation basis

Construction used the retained SQLite baseline directly. Imported refund copies are partitioned by `(source_system, external_event_id)`; the row with greatest `(ingested_at, refund_row_id)` is retained. The effective rows are joined through `orders.account_id` to `accounts`, then restricted to `tier='PLATINUM'`, `is_internal=0`, `is_test=0`, and the inclusive service-date window. This leaves 502 effective rows from 546 physical in-scope rows. Effective status counts are 447 `SETTLED`, 37 `FAILED`, 15 `VOIDED`, and 3 linked `REVERSED` rows. Failed and voided rows do not contribute counts or money.

The exact calculation basis is:

- The 447 effective `SETTLED` rows contain 447 distinct `refund_id` values and 447 distinct `order_id` values. Therefore `effective_settled_logical_refund_count = 447` and `eligible_refunded_order_count = 447`.
- Each money contribution is `amount_minor / 100 × fx_rates.usd_per_unit`, joining the row's currency and `service_date`. Settled contributions total exactly **110221.41728 USD** before display rounding.
- The three effective linked reversal rows total exactly **1678.66937 USD** on their own service-date FX rates. Therefore `effective_reversed_amount_usd = 1678.67`.
- Net provider exposure is settled USD minus linked reversal USD: `110221.41728 - 1678.66937 = 108542.74791`, producing `net_provider_exposure_usd = 108542.75` after one final two-decimal half-up rounding.
- Provider net totals before display rounding are `BRAINTREE = 37708.88283`, `ADYEN = 36425.84035`, and `STRIPE = 34408.02473`. Independent final rounding gives 37708.88, 36425.84, and 34408.02. Sorting by unrounded net exposure descending, then provider ascending, yields the standard complete provider ranking. The independently rounded provider display values need not sum to the independently rounded portfolio total because of cent-level rounding.
- Normalized reason is `UPPER(TRIM(reason_code))`. Settlements are positive. Each linked reversal is negative and is attributed to the normalized reason on its directly linked refund row. Net reason totals are `LATE_DELIVERY = 23169.54847`, `DUPLICATE_CHARGE = 21879.66669`, `DAMAGED = 21363.20680`, `CUSTOMER_RETURN = 21116.85299`, and `NOT_AS_DESCRIBED = 21013.47296`. Descending net USD with ascending reason as the tie-break makes `LATE_DELIVERY` dominant.
- Candidate analysis begins with the 447 eligible settled-refund orders. Per-order net settled USD uses the same signed contributions. Order gross is converted from `orders.gross_amount_minor` and order currency using FX on that order's in-scope settled refund service date. An unreversed settled logical refund has no effective in-scope linked reversal targeting its `refund_id`. Seventeen orders exceed gross; no order enters through the repeated-same-reason branch. The complete ascending union is `ORD-001142`, `ORD-002888`, `ORD-003638`, `ORD-004692`, `ORD-004807`, `ORD-005208`, `ORD-005465`, `ORD-005820`, `ORD-006234`, `ORD-006754`, `ORD-007555`, `ORD-007597`, `ORD-008141`, `ORD-010010`, `ORD-010598`, `ORD-011441`, and `ORD-012214`.
- The leakage candidate rate is `17 / 447 = 0.0380313199...`, below 6% but not below 2%. Net provider exposure is above USD 60,000. Applying the policy in LOW, MODERATE, HIGH order therefore gives `exposure_status = HIGH`.

Only requested displayed money fields are rounded, each independently and only after its underlying aggregate is complete. Provider ranking uses the unrounded aggregates and the declared stable tie-break.

### Evaluation basis and atomic rubric

The raw weights total 17. Each point checks one distinct business result and earns either all of `weight / 17` or zero. An unreadable candidate or a JSON value that is not an object deterministically fails all eight points without a traceback. Ordinary field errors fail only the relevant point.

| ID | Goal | Raw weight | Atomic pass logic |
| --- | --- | ---: | --- |
| `SP001` | Eligible distinct refunded-order population | 2 | `eligible_refunded_order_count` is the exact integer 447. |
| `SP002` | Effective settled logical refund count | 3 | `effective_settled_logical_refund_count` is the exact integer 447. |
| `SP003` | Effective reversed amount USD | 2 | `effective_reversed_amount_usd`, evaluated at two-decimal half-up precision, exactly equals 1678.67. |
| `SP004` | Net provider exposure USD | 3 | `net_provider_exposure_usd`, evaluated at two-decimal half-up precision, exactly equals 108542.75. |
| `SP005` | Complete provider exposure ranking | 2 | The ordered array has exactly the three standard provider objects, exact nested keys, exact provider order, and exact two-decimal provider amounts. |
| `SP006` | Unresolved leakage order set | 3 | `unresolved_leakage_order_ids` exactly equals the complete ascending, duplicate-free standard array. |
| `SP007` | Dominant normalized reason | 1 | `dominant_normalized_reason_code` exactly equals the controlled standard value. |
| `SP008` | Exposure status | 1 | `exposure_status` exactly equals the controlled standard value. |

These points cover population, logical event reconciliation, reversal value, portfolio money, provider allocation and priority, exception identification, reason attribution, and policy classification. Provider ranking is not a duplicate of total exposure: it evaluates the complete allocation and order across every represented provider, while SP004 evaluates the portfolio aggregate.

Likely model pitfalls include counting physical retry rows; using `refund_row_id` instead of logical `refund_id`; retaining internal or test accounts; counting failed or voided outcomes; omitting delayed linked reversals; applying one period FX rate or the order/account currency to refund rows; converting order gross on an unrelated date; rounding each row before aggregation; subtracting reversals from the total but not from provider or reason rollups; ranking providers on settled gross instead of net exposure; returning only the leading provider; checking only one leakage predicate; computing the candidate-rate denominator from physical attempts; or treating strict “below” thresholds as inclusive.

### Test transfer design and difficulty split

The explicit train anchor is `train_002`, with effective-event deduplication reinforced by `train_004`. From `train_002`, a solver can transfer production-account exclusion, import-copy precedence, the distinction between physical rows and logical refunds, terminal outcome treatment, linked reversal subtraction, service-date FX, round-at-end aggregation, stable ranking, and leakage-candidate construction. `train_004` reinforces selecting an effective event copy before aggregating stable business outcomes.

The transfer coverage is deliberate: SP002 depends on the latest-ingestion and terminal-outcome habits anchored by `train_002` and `train_004`; SP003 depends on linked reversal treatment and reversal-date FX from `train_002`; SP004 depends on net USD exposure construction from `train_002`; and SP006 depends on carrying the unresolved leakage definition across a different cohort. SP001 also benefits from the production exclusion convention.

Task-specific exploration remains substantial. Solvers must discover the PLATINUM May-June cohort, inspect a different provider/currency mix, account for three delayed reversals, calculate all provider allocations rather than only a top subset, derive a new dominant reason, enumerate a new candidate set, and apply different USD and rate thresholds. SP005 and SP007 are primarily task-specific exploration outcomes, while SP008 combines the newly calculated facts with task-local policy. The solver-visible prompt and payload provide the business request facts without restating the transferable effective-copy, reversal, exclusion, or rounding procedure.

### Construction record

- Author: `task-builder-test-002`
- Created: 2026-07-16
- Updated: 2026-07-16
- Major change: initial construction of the unseen test task, exact payload/template, reproducible standard answer, eight-point evaluator, and bilingual audit notes.
- Deviation or concern: none. The assigned cohort produced nonzero settlements and reversals, all three providers, an untied provider and reason ranking, and 17 leakage candidates. The repeated-reason predicate contributes no additional candidate, but the requested candidate union is nonempty and stable.

## 中文构建说明

### 数据谱系、任务定义与场景契合度

这个未见测试任务属于 `SCN_022_sql_database_analytics`，设计谱系来自源示例 `E001`、`E002` 和 `E003`。直接构建依据包括 `test_002` 任务简报、`scratch/task_group_design.md` 中的 `test_002` 小节与迁移覆盖矩阵、共享 Atlas Commerce Operations 接口，以及保留的生成基线 `task_group/task_group_022/env/atlas_baseline.sqlite3`。任务本地的求解器可见材料是 `input/prompt.txt`、`input/payloads/provider_exposure_request.json` 和 `input/payloads/answer_template.json`。

退款运营与支付风险团队需要 PLATINUM 层级生产账户的五月至六月供应商风险敞口关账报告。有效退款 `service_date` 范围为 2026-05-01 至 2026-06-30，包含首尾日期。要求的结构化结果包括：符合条件的不同退款订单群体、有效已结算逻辑退款数、有效冲正美元额、供应商总净敞口、完整供应商敞口排名、未解决泄漏订单编号、主导标准化原因以及受控的敞口状态枚举。

可见流程是只读分析：通过 `<TASK_ENV_BASE_URL>` 上经过认证的服务发现关系模型，分析业务记录，并把符合答案模板的单个对象保存到 `output/answer.json`。本任务符合 SQL 数据库分析场景，因为答案需要协调解释 `refund_attempts` 中的供应商尝试、`orders` 与 `accounts` 中的订单账户关系，以及 `fx_rates` 中的每日汇率。重试副本、不贡献金额的结果、延迟关联冲正、多币种和任务特定排名使它无法通过单行查询完成。

### 材料地图

- `GET /api/schema` 提供求解器可见表、键、关系和索引，用于模式发现。
- `GET /api/data-dictionary` 解释来源标识、摄取时间戳、最小货币单位、每日汇率单位和生产标志，但不会指出目标行或公开完整核对步骤。
- `POST /api/sql` 支持只读 CTE、窗口函数、连接、聚合和复核查询；本任务不需要事务或更正审计端点。
- `accounts` 提供群组资格所需的 `tier`、`is_internal` 与 `is_test`。
- `orders` 提供稳定 `order_id`、账户关系、订单币种和 `gross_amount_minor`。
- `refund_attempts` 提供物理行编号、逻辑退款编号、导入身份、状态、原因文本、金额、币种、服务日期、摄取顺序、供应商与冲正关联。
- `fx_rates` 按 `rate_date` 和币种提供 `usd_per_unit`。
- `provider_exposure_request.json` 提供 PLATINUM 与日期范围、金额基础、供应商和原因排名规则、泄漏谓词与严格状态阈值。
- `answer_template.json` 固定八个顶层键、类型、单位、两位小数精度、供应商嵌套键、列表顺序、原因与状态选项，并禁止额外字段。
- `output/answer.json` 保存可复现标准答案。
- `eval/evaluator.py` 与 `eval/eval.sh` 实现八个原子加权检查和稳健命令行入口。

### 隐藏解法与可复现计算依据

构建时直接使用保留的 SQLite 基线。按 `(source_system, external_event_id)` 对导入退款副本分区，保留 `(ingested_at, refund_row_id)` 最大的行。然后通过 `orders.account_id` 连接 `accounts`，筛选 `tier='PLATINUM'`、`is_internal=0`、`is_test=0` 和包含边界的服务日期范围。范围内 546 个物理行经有效副本选择后剩余 502 行。有效状态计数为 447 个 `SETTLED`、37 个 `FAILED`、15 个 `VOIDED` 和 3 个有关联的 `REVERSED` 行。失败与作废行不贡献计数或金额。

精确计算依据如下：

- 447 个有效 `SETTLED` 行包含 447 个不同 `refund_id` 和 447 个不同 `order_id`，因此 `effective_settled_logical_refund_count = 447`，`eligible_refunded_order_count = 447`。
- 每个金额贡献为 `amount_minor / 100 × fx_rates.usd_per_unit`，按该行币种与 `service_date` 连接。已结算贡献在显示舍入前精确合计 **110221.41728 美元**。
- 三个有效关联冲正行按各自服务日期汇率精确合计 **1678.66937 美元**，所以 `effective_reversed_amount_usd = 1678.67`。
- 供应商净敞口等于已结算美元减去关联冲正美元：`110221.41728 - 1678.66937 = 108542.74791`，最终统一按两位小数四舍五入得到 `net_provider_exposure_usd = 108542.75`。
- 各供应商显示舍入前的净额为 `BRAINTREE = 37708.88283`、`ADYEN = 36425.84035`、`STRIPE = 34408.02473`；独立最终舍入后为 37708.88、36425.84 和 34408.02。按未舍入净额降序、供应商升序打破并列，得到完整标准排名。由于每个供应商显示值和组合总额都独立舍入，显示值之和可能与组合显示总额相差一美分。
- 标准化原因采用 `UPPER(TRIM(reason_code))`。结算为正，关联冲正为负，并归入其直接关联退款行的标准化原因。原因净额为：`LATE_DELIVERY = 23169.54847`、`DUPLICATE_CHARGE = 21879.66669`、`DAMAGED = 21363.20680`、`CUSTOMER_RETURN = 21116.85299`、`NOT_AS_DESCRIBED = 21013.47296`。按净美元降序、原因升序打破并列，主导原因为 `LATE_DELIVERY`。
- 候选分析从 447 个符合条件的结算退款订单开始。每个订单的净结算美元使用相同带符号贡献。订单毛额从 `orders.gross_amount_minor` 与订单币种换算，并使用该订单范围内已结算退款的服务日期汇率。未冲正的已结算逻辑退款是没有范围内有效关联冲正指向其 `refund_id` 的退款。17 个订单超过毛额；没有订单通过“相同原因至少两笔未冲正退款”分支进入。完整升序并集为 `ORD-001142`、`ORD-002888`、`ORD-003638`、`ORD-004692`、`ORD-004807`、`ORD-005208`、`ORD-005465`、`ORD-005820`、`ORD-006234`、`ORD-006754`、`ORD-007555`、`ORD-007597`、`ORD-008141`、`ORD-010010`、`ORD-010598`、`ORD-011441` 和 `ORD-012214`。
- 泄漏候选率是 `17 / 447 = 0.0380313199...`，低于 6% 但不低于 2%；供应商净敞口高于 60,000 美元。按 LOW、MODERATE、HIGH 顺序应用政策，得到 `exposure_status = HIGH`。

只有请求显示的金额字段才舍入；每个底层聚合完成后独立舍入一次。供应商排名使用未舍入聚合与声明的稳定并列规则。

### 评估依据与原子评分规则

原始权重合计 17。每个评分点检查一个不同业务结果，只能获得完整的 `weight / 17` 分数或零分。无法读取的候选或非对象 JSON 会确定性地使八个点全部失败且不显示回溯；普通字段错误只影响相关评分点。

| 编号 | 目标 | 原始权重 | 原子通过逻辑 |
| --- | --- | ---: | --- |
| `SP001` | 符合条件的不同退款订单群体 | 2 | `eligible_refunded_order_count` 是精确整数 447。 |
| `SP002` | 有效已结算逻辑退款数 | 3 | `effective_settled_logical_refund_count` 是精确整数 447。 |
| `SP003` | 有效冲正美元额 | 2 | `effective_reversed_amount_usd` 按两位小数四舍五入后精确等于 1678.67。 |
| `SP004` | 供应商净敞口美元额 | 3 | `net_provider_exposure_usd` 按两位小数四舍五入后精确等于 108542.75。 |
| `SP005` | 完整供应商敞口排名 | 2 | 有序数组恰好包含三个标准供应商对象、精确嵌套键、精确供应商顺序与精确两位小数金额。 |
| `SP006` | 未解决泄漏订单集合 | 3 | `unresolved_leakage_order_ids` 与完整、升序、无重复的标准数组完全相同。 |
| `SP007` | 主导标准化原因 | 1 | `dominant_normalized_reason_code` 精确等于受控标准值。 |
| `SP008` | 敞口状态 | 1 | `exposure_status` 精确等于受控标准值。 |

这些评分点覆盖群体、逻辑事件核对、冲正价值、组合金额、供应商分配与优先级、异常识别、原因归因和政策分类。供应商排名并不重复总敞口：SP005 检查全部供应商的完整分配和次序，而 SP004 检查组合聚合值。

常见模型错误包括：直接计算物理重试行；使用 `refund_row_id` 而不是逻辑 `refund_id`；保留内部或测试账户；计入失败或作废结果；遗漏延迟关联冲正；使用单一期汇率或用订单/账户币种处理退款行；在无关日期换算订单毛额；逐行舍入后再聚合；只从总额减去冲正却不调整供应商或原因汇总；按结算毛额而非净敞口排列供应商；只返回第一名供应商；只检查一个泄漏谓词；用物理尝试数计算候选率分母；或把严格“低于”误当成包含边界。

### 测试迁移设计与难度拆分

明确训练锚点是 `train_002`，并由 `train_004` 加强有效事件去重经验。从 `train_002` 可迁移生产账户排除、导入副本优先级、物理行与逻辑退款的区别、终态结果处理、关联冲正扣减、服务日期汇率、聚合后舍入、稳定排名和泄漏候选构造。`train_004` 进一步强化先选择有效事件副本、再聚合稳定业务结果的习惯。

迁移覆盖是有意设计的：SP002 依赖 `train_002` 与 `train_004` 锚定的最新摄取和终态结果习惯；SP003 依赖 `train_002` 中的关联冲正处理与冲正日期汇率；SP004 依赖 `train_002` 的美元净敞口构造；SP006 依赖把未解决泄漏定义迁移到不同群组。SP001 也受益于生产群组排除约定。

任务特定探索仍然很多。求解器必须发现 PLATINUM 五月至六月群组，检查不同的供应商与币种组合，处理三个延迟冲正，计算全部供应商分配而非只取前几名，推导新的主导原因，列举新的候选集合，并应用不同金额与比例阈值。SP005 与 SP007 主要属于任务特定探索结果，SP008 则把新计算事实与本任务政策结合。求解器可见提示和载荷只提供业务请求事实，不会重述可迁移的有效副本、冲正、排除或舍入完整过程。

### 构建记录

- 作者：`task-builder-test-002`
- 创建日期：2026-07-16
- 更新日期：2026-07-16
- 主要变更：首次构建未见测试任务、精确载荷与模板、可复现标准答案、八点评估器和双语审计说明。
- 偏差或关注：无。指定群组产生非零结算与冲正、三个供应商、无并列的供应商和原因排名，以及 17 个泄漏候选。重复原因谓词没有增加候选，但请求的候选并集非空且稳定。
