# test_004 construction and evaluation notes / test_004 构建与评估说明

## English

### Lineage, task definition, and scenario fit

- Source scenario: `SCN_022_sql_database_analytics`; source examples: `E001`, `E002`, and `E003`.
- Design sources: `scratch/task_builder_common.md`, `scratch/task_briefs/test_004.md`, the `test_004` design section, and the transfer coverage matrix in `scratch/task_group_design.md`.
- Construction data: the retained generated Atlas Commerce SQLite baseline at `task_group/task_group_022/env/atlas_baseline.sqlite3`. The runtime exposes the same relational content through the public authenticated query service.
- Task-local solver materials are `input/prompt.txt`, `input/payloads/operations_health_request.json`, and `input/payloads/answer_template.json`. The standard answer is `output/answer.json`.

This is an unseen integrated test task. Strategic Account Operations needs a Q2 health rollup for production accounts whose `accounts.segment='STRATEGIC'` and `accounts.region='WEST'`. The activity interval is `2026-04-01T00:00:00Z` through `2026-06-30T23:59:59Z`, inclusive, and the end timestamp is also the effective-state cutoff. The output combines fulfillment, refunds, and support at account grain, then produces portfolio aggregates, a worst-account ranking, an exception set, a dominant-risk decision, and a portfolio status.

The task fits the Atlas Commerce scenario because a single account portfolio is represented across `accounts`, `orders`, physical shipments and imported carrier events, refund attempts and FX rates, and support cases with lifecycle events. The analyst must coordinate those relational paths, preserve stable business-ID grain, reconcile effective histories, normalize components at account level, and make controlled rollup decisions. No mutation is requested.

Expected work is to inspect the schema and dictionary, identify the production account cohort, derive each component from its relevant effective records, aggregate by account without join multiplication, apply the task-local formulas to unrounded values, and serialize only the required JSON fields.

### Material map

| Material | Purpose |
| --- | --- |
| `input/prompt.txt` | Realistic analyst request, runtime location, allowed read-only query surface, and delivery instruction. |
| `input/payloads/operations_health_request.json` | Q2 scope, SLA hours, local component and rollup formulas, classification thresholds, and rounding rule. |
| `input/payloads/answer_template.json` | Exact required keys, types, units, precision, list order, object keys, enums, and no-extra-field rules. |
| `GET /api/schema` | Public table, column, relationship, and index discovery. |
| `GET /api/data-dictionary` | Public business descriptions and field semantics. |
| `POST /api/sql` | Authenticated read-only analytical queries against the runtime database. |
| `accounts` | Segment, region, and production-population flags. |
| `orders`, `order_events` | Quarter order scope, order currency/gross, and effective cancellation state. |
| `shipments`, `carrier_scans` | Physical shipment promises and effective delivery outcomes. |
| `refund_attempts`, `fx_rates` | Effective quarter refund cash flow and service-date USD conversion. |
| `support_cases`, `case_events` | Case cohort, priority, lifecycle state, waiting intervals, reopenings, and resolution clock. |
| `output/answer.json` | Reproducible standard outcome. |
| `eval/eval.sh`, `eval/evaluator.py` | Eight atomic weighted business-result checks. |

### Hidden solution basis and exact calculations

All calculations below use stable IDs and retain full precision until the final output.

1. Eligible accounts: filter to `segment='STRATEGIC'`, `region='WEST'`, `is_internal=0`, and `is_test=0`, ordered by `account_id`. This yields 30 accounts:

   `ACC-0040`, `ACC-0073`, `ACC-0078`, `ACC-0082`, `ACC-0124`, `ACC-0166`, `ACC-0170`, `ACC-0175`, `ACC-0208`, `ACC-0217`, `ACC-0259`, `ACC-0263`, `ACC-0268`, `ACC-0310`, `ACC-0314`, `ACC-0356`, `ACC-0365`, `ACC-0398`, `ACC-0403`, `ACC-0407`, `ACC-0449`, `ACC-0458`, `ACC-0491`, `ACC-0500`, `ACC-0542`, `ACC-0584`, `ACC-0588`, `ACC-0593`, `ACC-0635`, `ACC-0639`.

2. Fulfillment: deduplicate `order_events` by `(source_system, external_event_id)`, retaining greatest `(ingested_at, event_id)`, and take the latest event at or before cutoff by `(event_at, event_id)`. In-window cohort orders whose effective state is `CANCELLED` are excluded. Deduplicate `carrier_scans` in the same import-key manner using `(ingested_at, scan_row_id)`, then obtain each shipment's last state at cutoff by `(canonical_event_at, scan_row_id)`. An order is complete only when all its physical shipments are effectively `DELIVERED`; it is on time only when every effective delivery timestamp is no later than that shipment's `promised_delivery_at`. There are 345 eligible orders, 132 complete orders, 57 on-time complete orders, 213 incomplete orders, and 75 complete-but-late orders. Failures are `213 + 75 = 288`; therefore the portfolio rate is `288 / 345 = 0.834782608695...`, output as `0.8348`.

3. Refunds: deduplicate `refund_attempts` by `(source_system, external_event_id)`, retaining greatest `(ingested_at, refund_row_id)`. Assign refund activity to accounts through `refund_attempts.order_id -> orders.account_id` and use the refund row's `service_date` for the quarter boundary. Effective `SETTLED` rows add value; effective linked `REVERSED` rows reduce value; `FAILED` and `VOIDED` rows contribute zero. Each contributing row is converted using `fx_rates.usd_per_unit` on its own `service_date`. The cohort-quarter has 125 settled rows worth USD `29189.111710`, 11 failed rows, 6 voided rows, and no qualifying linked reversal in this slice. Net exposure is output as USD `29189.11`. This zero reversal count is a data outcome, not a change to the reconciliation rule.

4. Gross denominator for account refund ratios: convert each fulfillment-eligible order's `gross_amount_minor / 100` with the order currency's FX rate on the UTC date of `order_created_at`; do not round per order. Portfolio gross eligible order value is USD `289872.177110`.

5. Support: use cases opened in-window for eligible accounts. Deduplicate `case_events` by `(source_system, external_event_id)`, retaining greatest `(ingested_at, case_event_id)`, and order effective events through cutoff by `(event_at, case_event_id)`. Resolution time ends at the first `RESOLVED` after the most recent `REOPENED`, otherwise at the first `RESOLVED`; a case not finally resolved uses the cutoff. Subtract each `WAITING_CUSTOMER` interval through its next `CUSTOMER_REPLIED`, or through the endpoint if still waiting. A breach is active hours strictly greater than the priority threshold. The 146 eligible cases comprise 32 URGENT/26 breaches, 43 HIGH/27 breaches, 33 MEDIUM/7 breaches, and 38 LOW/9 breaches. Total breaches are 69, so `69 / 146 = 0.472602739726...`, output as `0.4726`.

6. Per-account calculations use `health = 0.45*F + 0.30*R + 0.25*S`. The construction audit table below shows eligible/failed orders, unrounded-enough component rates, net/gross USD, cases/breaches, and health. The underlying calculation retained full decimal precision even where this table is shortened.

| Account | Orders | Failed | F | Net refund USD | Gross USD | R | Cases | Breaches | S | Health |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| ACC-0040 | 11 | 10 | 0.90909091 | 1292.368330 | 13987.278150 | 0.09239598 | 6 | 4 | 0.66666667 | 0.60347637 |
| ACC-0073 | 10 | 9 | 0.90000000 | 2507.061810 | 5278.808190 | 0.47492951 | 7 | 4 | 0.57142857 | 0.69033600 |
| ACC-0078 | 9 | 7 | 0.77777778 | 964.835320 | 4877.048050 | 0.19783183 | 6 | 1 | 0.16666667 | 0.45101621 |
| ACC-0082 | 12 | 11 | 0.91666667 | 1506.393420 | 7579.948790 | 0.19873398 | 3 | 2 | 0.66666667 | 0.63878686 |
| ACC-0124 | 10 | 6 | 0.60000000 | 629.873830 | 13439.592320 | 0.04686703 | 7 | 2 | 0.28571429 | 0.35548868 |
| ACC-0166 | 14 | 11 | 0.78571429 | 2179.099890 | 8739.998190 | 0.24932498 | 3 | 2 | 0.66666667 | 0.59503559 |
| ACC-0170 | 10 | 10 | 1.00000000 | 0.000000 | 5249.091050 | 0.00000000 | 3 | 2 | 0.66666667 | 0.61666667 |
| ACC-0175 | 10 | 10 | 1.00000000 | 1185.272900 | 10327.881780 | 0.11476438 | 6 | 5 | 0.83333333 | 0.69276265 |
| ACC-0208 | 12 | 11 | 0.91666667 | 227.924480 | 14493.271640 | 0.01572623 | 6 | 3 | 0.50000000 | 0.54221787 |
| ACC-0217 | 14 | 14 | 1.00000000 | 326.511570 | 15591.395060 | 0.02094178 | 3 | 2 | 0.66666667 | 0.62294920 |
| ACC-0259 | 13 | 10 | 0.76923077 | 2215.444020 | 10849.624920 | 0.20419545 | 5 | 1 | 0.20000000 | 0.45741248 |
| ACC-0263 | 13 | 11 | 0.84615385 | 0.000000 | 11681.154770 | 0.00000000 | 6 | 2 | 0.33333333 | 0.46410256 |
| ACC-0268 | 14 | 12 | 0.85714286 | 310.476170 | 13137.009760 | 0.02363370 | 4 | 2 | 0.50000000 | 0.51780440 |
| ACC-0310 | 13 | 13 | 1.00000000 | 608.765340 | 8242.850260 | 0.07385374 | 5 | 3 | 0.60000000 | 0.62215612 |
| ACC-0314 | 14 | 10 | 0.71428571 | 1498.910930 | 9078.805670 | 0.16510001 | 6 | 2 | 0.33333333 | 0.45429191 |
| ACC-0356 | 14 | 12 | 0.85714286 | 112.003300 | 13830.864840 | 0.00809807 | 3 | 1 | 0.33333333 | 0.47147704 |
| ACC-0365 | 14 | 11 | 0.78571429 | 930.306240 | 13119.113690 | 0.07091228 | 6 | 4 | 0.66666667 | 0.54151178 |
| ACC-0398 | 9 | 8 | 0.88888889 | 1678.565660 | 7662.073320 | 0.21907460 | 6 | 1 | 0.16666667 | 0.50738905 |
| ACC-0403 | 9 | 9 | 1.00000000 | 817.673410 | 6124.549320 | 0.13350752 | 5 | 3 | 0.60000000 | 0.64005226 |
| ACC-0407 | 14 | 14 | 1.00000000 | 1430.761410 | 10120.013120 | 0.14137940 | 3 | 2 | 0.66666667 | 0.65908049 |
| ACC-0449 | 10 | 6 | 0.60000000 | 670.724250 | 6938.773670 | 0.09666323 | 6 | 3 | 0.50000000 | 0.42399897 |
| ACC-0458 | 13 | 9 | 0.69230769 | 1509.620460 | 13264.597480 | 0.11380824 | 3 | 0 | 0.00000000 | 0.34568093 |
| ACC-0491 | 13 | 11 | 0.84615385 | 1677.422180 | 9960.911490 | 0.16840047 | 3 | 1 | 0.33333333 | 0.51462271 |
| ACC-0500 | 10 | 8 | 0.80000000 | 666.873800 | 6099.636940 | 0.10933008 | 6 | 5 | 0.83333333 | 0.60113236 |
| ACC-0542 | 13 | 11 | 0.84615385 | 119.140530 | 13257.744300 | 0.00898649 | 3 | 3 | 1.00000000 | 0.63346518 |
| ACC-0584 | 9 | 6 | 0.66666667 | 1389.541970 | 5118.232570 | 0.27148863 | 5 | 1 | 0.20000000 | 0.43144659 |
| ACC-0588 | 8 | 7 | 0.87500000 | 311.050520 | 4172.524760 | 0.07454732 | 6 | 2 | 0.33333333 | 0.49944753 |
| ACC-0593 | 10 | 5 | 0.50000000 | 1177.711940 | 5206.840380 | 0.22618553 | 4 | 1 | 0.25000000 | 0.35535566 |
| ACC-0635 | 9 | 8 | 0.88888889 | 83.381870 | 13000.082470 | 0.00641395 | 5 | 3 | 0.60000000 | 0.55192418 |
| ACC-0639 | 11 | 8 | 0.72727273 | 1161.396160 | 9442.460160 | 0.12299720 | 6 | 2 | 0.33333333 | 0.44750522 |

7. Ranking on the unrounded health values yields `ACC-0175` (`0.692762645904...`), `ACC-0073` (`0.690335997161...`), and `ACC-0407` (`0.659080487470...`), output at four decimals as `0.6928`, `0.6903`, and `0.6591`.

8. The original task-local critical rule (`health >= 0.30` or at least two component rates `>= 0.25`) classified all 30 eligible accounts and made SP006 duplicate SP001. Retained-baseline analysis supported the smallest explicit policy adjustment: an account is critical when its unrounded health is at least `0.60` or at least two unrounded component rates are at least `0.60`. The adjusted rule yields this 14-ID ascending set:

   `ACC-0040`, `ACC-0073`, `ACC-0082`, `ACC-0166`, `ACC-0170`, `ACC-0175`, `ACC-0217`, `ACC-0310`, `ACC-0365`, `ACC-0403`, `ACC-0407`, `ACC-0500`, `ACC-0542`, `ACC-0635`.

   Thirteen of these accounts meet the two-component condition; `ACC-0073` is included by its unrounded health score `0.690335997160...`. The result is a nonempty proper subset at `14 / 30 = 46.6666...%`. With the component threshold held at `0.60`, health-threshold sensitivity checks at `0.59`, `0.61`, `0.65`, and `0.69` all reproduce the same 14-account set, supporting stability rather than a boundary artifact. Cohort, dates, component formulas, ranking, other outputs, rubric IDs/weights, transfer design, and environment remain unchanged.

9. The arithmetic mean component rates are fulfillment `0.832230639730...`, refunds `0.121669720449...`, and support `0.482460317460...`. Weighted average contributions are respectively `0.374503787879...`, `0.036500916135...`, and `0.120615079365...`; dominant risk is `FULFILLMENT`. Mean health is `0.531619783379...`. The adjusted critical share is still at least 25%, so the downstream portfolio status remains `CRITICAL`.

### Evaluation design and likely pitfalls

There are eight atomic points with raw total weight 19. Each point passes in full or earns zero; `assigned_score = weight / 19`. Numeric checks normalize to the declared decimal precision, ordered lists are compared exactly, ranking items require exactly `account_id` and `health_score`, and enums are exact. An unreadable or non-object candidate receives zero without a traceback. Extra or malformed values affect only their relevant business point.

| ID | Goal | Weight | Atomic pass rule |
| --- | --- | ---: | --- |
| SP001 | Eligible strategic-account set | 2 | `eligible_account_ids` exactly equals the 30-ID ascending list. |
| SP002 | Fulfillment failure rate | 3 | `portfolio_fulfillment_failure_rate` equals `0.8348` at four decimals. |
| SP003 | Net refund exposure USD | 3 | `portfolio_net_refund_exposure_usd` equals `29189.11` at cents precision. |
| SP004 | Active-clock support breach rate | 3 | `portfolio_support_breach_rate` equals `0.4726` at four decimals. |
| SP005 | Bottom-three health ranking | 2 | All three ordered IDs and all three four-decimal scores match as one atomic ranking outcome. |
| SP006 | Critical account set | 3 | `critical_account_ids` exactly equals the ascending 14-ID critical set. |
| SP007 | Dominant risk | 2 | `dominant_risk_dimension` is exactly `FULFILLMENT`. |
| SP008 | Portfolio status | 1 | `portfolio_status` is exactly `CRITICAL`. |

Likely pitfalls include trusting stale `current_status` fields; failing to deduplicate imported copies before state reconstruction; counting joined rows instead of orders, shipments, refunds, or cases; treating one delivered shipment as a complete multi-shipment order; converting gross orders or refunds on the wrong date; including failed or voided refund attempts; timing support by wall clock without customer-wait pauses; treating a reopened case as finally resolved; using portfolio ratios instead of arithmetic account means for dominant contribution; rounding before ranking or threshold tests; and sorting the worst accounts in the wrong direction.

### Transfer design

Transfer anchors are explicit:

- `train_001` anchors production eligibility, effective order/shipment outcomes, all-shipment completeness, final rounding, and stable ranking. It primarily supports SP001, SP002, and the fulfillment inputs to SP005/SP006.
- `train_002` anchors imported refund deduplication, logical refund status/reversal treatment, service-date FX conversion, and net USD aggregation. It primarily supports SP003 and the refund inputs to SP005/SP006.
- `train_005` anchors production support cohorts, effective case state, customer-wait pauses, reopened cases, resolution SLA comparison, and stable account ranking. It primarily supports SP001, SP004, and the support inputs to SP005/SP006.

Transfer-dependent difficulty is concentrated in the high-weight component outcomes SP001-SP004 and in producing correct component inputs for integrated SP005-SP006. The solver-visible prompt deliberately names established effective conventions but does not restate the hidden deduplication, state reconstruction, reversal, or pause-interval procedures.

Task-specific exploration difficulty is separate: discovering the cross-domain joins for this new strategic WEST cohort, using the Q2 date fields correctly, building the order-gross USD denominator, normalizing three account-level rates, applying the local health and critical formulas, ranking on unrounded health, comparing weighted arithmetic means for SP007, and applying portfolio thresholds for SP008. These local rules are appropriately stated in the request payload.

### Construction record

- Author: `task-builder-test-004`
- Created: `2026-07-16`
- Updated: `2026-07-16`
- Major changes: created the unseen integrated request, exact output template, retained-baseline standard answer, eight-point atomic evaluator, bilingual construction notes, and sensitivity-test record; then reworked only the task-local critical policy from `0.30`/`0.25` to `0.60`/`0.60` after retained-baseline analysis showed the original SP006 was degenerate. The solver-visible request, standard critical set, evaluator truth, and bilingual notes were updated consistently. No environment, design, task-group index, other task, calibration file, review file, or skill was changed.
- Validation: independent baseline reproduction recovered all retained component counts and amounts exactly. The updated standard answer scored `1.0` with all eight points passing. A fulfillment-rate-only mutation scored `16/19 = 0.8421052631578947` and failed only SP002. An independent swap of the first two ranking entries scored `17/19 = 0.8947368421052632` and failed only SP005. Removing one ID only from the critical set scored `16/19 = 0.8421052631578947` and failed only SP006. Health-threshold sensitivity from `0.59` through `0.69`, with the `0.60` component condition retained, preserved the exact 14-account set. A missing candidate returned zero without a traceback.

## 中文

### 数据来源、任务定义与场景适配

- 来源场景为 `SCN_022_sql_database_analytics`，来源示例为 `E001`、`E002`、`E003`。
- 设计依据包括 `scratch/task_builder_common.md`、`scratch/task_briefs/test_004.md`、设计文档中的 `test_004` 小节及迁移覆盖矩阵。
- 构建时使用保留的 Atlas Commerce SQLite 基线 `task_group/task_group_022/env/atlas_baseline.sqlite3`；运行时通过相同数据内容的鉴权查询服务访问。
- 求解器可见材料为 `input/prompt.txt`、`input/payloads/operations_health_request.json` 和 `input/payloads/answer_template.json`；标准答案为 `output/answer.json`。

这是一个未见过的综合测试任务。业务目标是对 WEST 区域的生产型 STRATEGIC 账户进行 2026 年第二季度运营健康汇总。活动区间为 `2026-04-01T00:00:00Z` 至 `2026-06-30T23:59:59Z`，后者同时作为状态截止点。输出将履约、退款和客服三个领域归一到账户粒度，再生成组合汇总、最差账户排名、关键账户集合、主导风险和组合状态。

该任务符合 Atlas Commerce 场景，因为同一账户组合的数据分布在 `accounts`、`orders`、实体运单与承运商事件、退款尝试与汇率、客服工单与生命周期事件中。分析者必须协调这些关系路径，保持稳定业务 ID 粒度，重建有效历史，完成账户级归一化并做汇总判断。本任务不需要写入或更正数据。

预期流程是先检查模式和数据字典，确定生产账户群体，分别从有效记录计算三个组件，避免连接放大，在未舍入数值上应用本地公式，最后只输出模板要求的 JSON 字段。

### 材料映射

- `input/prompt.txt`：真实业务请求、运行时位置、只读查询接口及交付说明。
- `operations_health_request.json`：季度范围、SLA 小时数、本地组件与汇总公式、状态阈值和舍入要求。
- `answer_template.json`：精确键名、类型、单位、精度、列表顺序、对象键、枚举值及禁止额外字段要求。
- `GET /api/schema`：发现公开表、字段、关系和索引；`GET /api/data-dictionary`：读取公开业务语义；`POST /api/sql`：执行鉴权只读分析查询。
- `accounts` 确定账户群体；`orders` 与 `order_events` 确定订单范围及取消状态；`shipments` 与 `carrier_scans` 确定实体运单承诺和交付结果；`refund_attempts` 与 `fx_rates` 计算有效退款美元金额；`support_cases` 与 `case_events` 计算优先级、等待区间、重开状态和解决时钟。
- `output/answer.json` 保存可复现标准结果；`eval/eval.sh` 与 `eval/evaluator.py` 实现八个原子加权检查。

### 隐藏解法依据与精确计算

所有计算均以稳定 ID 为粒度，并只在最终输出时舍入。账户群体筛选 `segment='STRATEGIC'`、`region='WEST'`、`is_internal=0`、`is_test=0`，得到上方英文部分列出的 30 个升序账户 ID。

履约部分先按导入键去重订单事件，再在截止点按事件时间和稳定事件 ID 取最终状态，排除有效取消订单；承运商扫描也先按导入键去重，再使用规范化事件时间重建每个实体运单的截止状态。只有全部实体运单有效交付的订单才完整，且全部交付时间不晚于各自承诺时间才按时。最终共有 345 个合格订单、132 个完整订单、57 个按时完整订单、213 个不完整订单和 75 个完整但迟到订单，因此失败数为 288，组合失败率 `288/345=0.834782608695...`，输出 `0.8348`。

退款部分按 `(source_system, external_event_id)` 去重，并以 `service_date` 判断季度范围。有效结算增加金额，有效关联冲正减少金额，失败和作废记录不贡献金额；每条贡献记录都使用自身 `service_date` 的汇率。该账户季度切片包含 125 条结算记录，金额 USD `29189.111710`；另有 11 条失败、6 条作废，没有符合条件的关联冲正。因此净敞口输出 USD `29189.11`。冲正数为零是数据结果，并未改变对冲正规则的要求。退款比率分母将每个合格订单的 `gross_amount_minor/100` 按 `order_created_at` 的 UTC 日期汇率换算，组合毛额为 USD `289872.177110`。

客服部分选取窗口内创建的合格账户工单，对事件按导入键去重并在截止点前排序。解决终点是最近一次重开后的第一次 `RESOLVED`；若无重开，则为第一次 `RESOLVED`；未最终解决则使用截止点。从总时长中减去客户等待区间，活动时间严格超过对应优先级阈值才算违约。146 个合格工单中，URGENT 为 32/26 个违约、HIGH 为 43/27、MEDIUM 为 33/7、LOW 为 38/9，总违约数 69，因此 `69/146=0.472602739726...`，输出 `0.4726`。

账户健康度使用 `0.45*F + 0.30*R + 0.25*S`。上方共享审计表记录了 30 个账户的订单、退款、客服及健康度中间值。按未舍入健康度降序并以账户 ID 升序打破并列，前三名为 `ACC-0175`、`ACC-0073`、`ACC-0407`，输出分数分别为 `0.6928`、`0.6903`、`0.6591`。

原任务本地关键规则（健康度 `>=0.30`，或至少两个组件率 `>=0.25`）把 30 个合格账户全部判为关键账户，导致 SP006 与 SP001 重复。保留基线分析支持最小且明确的策略调整：未舍入健康度至少为 `0.60`，或三个未舍入组件率中至少两个达到 `0.60`，即判为关键账户。调整后的 14 个升序 ID 为：`ACC-0040`、`ACC-0073`、`ACC-0082`、`ACC-0166`、`ACC-0170`、`ACC-0175`、`ACC-0217`、`ACC-0310`、`ACC-0365`、`ACC-0403`、`ACC-0407`、`ACC-0500`、`ACC-0542`、`ACC-0635`。其中 13 个满足双组件条件；`ACC-0073` 由未舍入健康度 `0.690335997160...` 纳入。关键集合占比为 `14/30=46.6666...%`，是非空真子集。保持组件阈值 `0.60` 时，将健康阈值分别改为 `0.59`、`0.61`、`0.65` 和 `0.69` 都得到完全相同的 14 个账户，说明该集合稳定而非边界偶然。账户群体、日期、组件公式、排名、其他输出、评分 ID/权重、迁移设计和环境均未改变。

三个账户平均组件率分别为 `0.832230639730...`、`0.121669720449...`、`0.482460317460...`，加权平均贡献分别为 `0.374503787879...`、`0.036500916135...`、`0.120615079365...`，所以主导风险为 `FULFILLMENT`。平均健康度为 `0.531619783379...`。调整后的关键账户占比仍不低于 25%，因此下游组合状态仍为 `CRITICAL`。

### 评估设计与常见错误

评估包含八个原子评分点，原始总权重为 19，每点只能获得全部 `weight/19` 或零分。数值按模板声明精度规范化，列表按要求精确比较，排名对象必须恰好包含 `account_id` 与 `health_score`，枚举值精确比较。不可读或非对象 JSON 返回零分且不抛出回溯。各点定义如下：SP001 合格账户集合（2）；SP002 履约失败率（3）；SP003 退款净敞口（3）；SP004 活动时钟客服违约率（3）；SP005 最差三账户排名与分数（2）；SP006 关键账户集合（3）；SP007 主导风险（2）；SP008 组合状态（1）。每个检查都是独立业务结果，不进行点内部分给分。

常见错误包括信任过时的 `current_status`，未先去重导入副本，因连接放大而数错业务实体，把单个运单交付误认为多运单订单完整，使用错误日期换汇，将失败或作废退款计入金额，客服时钟未扣除客户等待，误判重开工单已最终解决，用组合总体比率代替账户算术平均贡献，在排名或阈值判断前提前舍入，以及错误使用排名方向。

### 迁移设计：迁移依赖与专项探索分离

- `train_001` 提供生产群体、有效订单/运单结果、全运单完整性、最终舍入和稳定排名经验，主要支撑 SP001、SP002 以及 SP005/SP006 的履约输入。
- `train_002` 提供退款导入去重、逻辑状态与冲正处理、服务日期汇率和净美元汇总经验，主要支撑 SP003 以及 SP005/SP006 的退款输入。
- `train_005` 提供生产客服群体、有效工单状态、客户等待暂停、重开逻辑、解决 SLA 和稳定账户排名经验，主要支撑 SP001、SP004 以及 SP005/SP006 的客服输入。

迁移依赖难度集中在高权重 SP001-SP004，以及为综合 SP005-SP006 提供正确组件输入。求解器可见请求只引用既有有效口径，没有复述隐藏的导入去重、状态重建、冲正或暂停区间操作流程。

任务专项探索难度与此分开：发现新 WEST STRATEGIC 群体的跨域连接，正确使用第二季度日期字段，构建订单毛额美元分母，归一化三个账户率，在未舍入值上应用健康与关键规则，比较加权账户算术平均以决定 SP007，并应用组合阈值得到 SP008。这些本地规则已合理写入请求载荷。

### 构建记录

- 作者：`task-builder-test-004`
- 创建日期：`2026-07-16`
- 更新日期：`2026-07-16`
- 主要变更：先创建综合测试请求、精确输出模板、基线标准答案、八点原子评估器、双语构建说明和敏感性测试记录；随后依据保留基线分析，仅将任务本地关键策略从 `0.30`/`0.25` 调整为 `0.60`/`0.60`，解决原 SP006 退化问题，并一致更新求解器可见请求、标准关键集合、评估器真值和双语说明。未修改环境、设计文档、任务组索引、其他任务、校准/审查文件或技能。
- 验证结果：独立基线复现精确恢复了所有组件计数和金额；更新后的标准答案得分 `1.0`，八个评分点全部通过。仅修改履约失败率的候选得分为 `16/19 = 0.8421052631578947`，只失败 SP002；独立交换排名前两项的候选得分为 `17/19 = 0.8947368421052632`，只失败 SP005；仅从关键集合删除一个 ID 的候选得分为 `16/19 = 0.8421052631578947`，只失败 SP006；在保留组件阈值 `0.60` 时，将健康阈值从 `0.59` 调整到 `0.69` 仍保持完全相同的 14 个账户；缺失候选文件时返回零分且无回溯。
