# Hidden Notes for test_005

## English Notes

### Data and Source Lineage

This task belongs to `task_group_018`, derived from `SCN_018_court_clerk_disposition_orders_and_financial_entries` and source examples `E001`, `E002`, and `E003`. It is a multi-county June 2025 clerk finance exception register. The shared clerk operations environment exposes generated case, docket, fee, payment-policy, stale-export, and financial-obligation records. The solver-visible local packet is `input/payloads/monthly_financial_exception_packet.json`, and the solver-visible output contract is `input/payloads/answer_template.json`.

This is the third calibration fix for `test_005`. After the prior rework, two clean-context direct attempts scored `18/24 = 0.75` and `15/24 = 0.625`, average `0.6875`. Both missed only the plan/exposure point and aggregate point, and one also missed source precedence. They still earned high-weight scope, priority, broad row classification, correction-basis, no-plan/collateral handling, and live-ledger points. This fix keeps the same underlying clerk workflow but reduces weight on directly observable fields and adds controlled audit fields for June actionability, source basis, neutral reconciliation families, plan recalculation basis, exposure basis, and aggregate recomputation.

### Task Definition and Scenario Fit

The solver must prepare the June 2025 central finance quality exception register. The work requires using the local intake packet together with live environment records to decide which candidate notices belong on the month-end register, rank included rows, resolve live/local/stale conflicts, correct balances, retain or revise payment-plan structures, identify collateral-only omissions, and recompute aggregate totals and case-number sets.

This matches the source scenario because it is a court clerk post-disposition reconciliation task: financial and docket entries cannot be released until the clerk reconciles local desk notices, live ledgers, fee schedules, payment plans, docket history, stale queues, and collateral-program records.

### Material Map

- `monthly_financial_exception_packet.json`: candidate notices from several desk channels. The third fix neutralizes final-sounding channel labels and status hints while retaining raw desk excerpts, local balance hints, fee-code candidates, trust/cash items, local terms, and collateral flags.
- `/api/cases` and `/api/cases/<case_number>`: live case posture, defendant names, disposition dates, restitution facts, DUI/collateral facts, and matter status.
- `/api/financial-obligations?case_number=<case_number>`: live balances, ledger status, fee components, paid credits, payment plans, missed payments, and current plan terms.
- `/api/fees?county=<county>&matter_type=<type>&effective_on=<date>`: active fee components used to decide unsupported fee rows.
- `/api/payment-policies?county=<county>`: first-due and installment conventions when a plan must be calculated.
- `/api/docket?case_number=<case_number>`: docket and collateral-entry status by the register close date.
- `/api/stale-exports`: stale context and distractor queues that should not override current packet and live records.

### Solution and Evaluation Basis

Included register rows are `25-COL-00112`, `24-LAN-01003`, `24-MID-01003`, `24-JEF-01005`, `25-BEN-01004`, and `24-MID-00077`. Excluded candidates are `24-COL-01003` (stale context only), `24-LAN-01005` (future/informational program calendar), and `24-BEN-01001` (similar-name receipt owner not confirmed).

Key row results:

- `25-COL-00112`: deferred Columbia matter. Remove unsupported `CR-CONV` from the live ledger, reducing `284.92` by `177.50` to `107.42`. Use packet-approved new terms of `50.00` monthly, first due `2025-08-14`, with two full payments and a `7.42` final payment due `2025-10-14`.
- `24-LAN-01003`: Lane matter with unsupported restitution administration component. Remove `CR-REST-ADM` `30.00`, retain the live `45.00` monthly plan, and recalculate the corrected `93.05` balance as two full payments plus `3.05` final due `2025-09-09`.
- `24-MID-01003`: Middlesex trust credit closeout. Apply packet trust credit `46.52` against the live pending-adjustment balance, leaving `0.00`, no plan, and no exposure.
- `24-JEF-01005`: Jefferson payment default. Keep the live ledger balance and live `40.00` plan terms, route to return-to-court, and compute `80.00` default exposure from two missed installments.
- `25-BEN-01004`: Benton DUI license abstract omission. No balance correction or plan exposure; the collateral trigger date is `2025-05-03`.
- `24-MID-00077`: Middlesex treatment referral omission. No balance correction or plan exposure; the collateral trigger date is `2024-06-14`.

The third-fix evaluator has eight exact-match scoring points, raw weights totaling 17:

| ID | Weight | Goal |
| --- | ---: | --- |
| `SP001` | 1 | Register identifiers, included/excluded case sets, and final rank order. |
| `SP002` | 1 | Basic row priority buckets, row classifications, and action codes. |
| `SP003` | 2 | Candidate-level June actionability, scope reason, exclusion basis, and source family audit. |
| `SP004` | 3 | Source precedence, live/local/stale source audit, and neutral reconciliation family codes. |
| `SP005` | 2 | Live ledger facts, amount basis, correction components, correction amounts, and corrected balances. |
| `SP006` | 3 | New-plan, existing-schedule, and return-to-court plan bases with installment math and exposure audit. |
| `SP007` | 2 | No-plan credit closeout and collateral-only zero-exposure handling. |
| `SP008` | 3 | Aggregate counts, monetary totals, row-audit counts, and recomputed case-number sets. |

Likely model pitfalls are including every packet item, following packet order rather than register priority, letting stale queue snippets override live records, treating the trust closeout as a payment plan, using a new plan amount where the live plan must be retained, failing to distinguish fee correction from credit closeout, assigning exposure to collateral-only rows, and not recomputing aggregates from the final row audit fields.

### Transfer Design

Train anchors:

- `train_002` anchors installment plan math, final smaller payments, first/final due dates, and use of live or approved monthly amounts.
- `train_004` anchors stale/live source discipline, fee-component cleanup, current-ledger comparison, and unsupported financial row removal.
- `train_005` anchors monthly review scoping, unposted receipt closeouts, payment-plan action routing, return-to-court handling, compliance/collateral follow-up, and aggregate case sets.

Transfer-dependent scoring is now concentrated in `SP003`, `SP004`, `SP006`, `SP007`, and `SP008`. These points require conventions inferable from train attempts and answer comparison: current source precedence over copied/stale desk snippets, June actionability rather than packet membership, plan basis after correction versus live schedule retention versus return-to-court default, exposure basis, and aggregate recomputation from audited rows. Task-specific exploration remains necessary because the counties, case numbers, live balances, docket gaps, fee components, trust item, payment status, missed-payment counts, and distractor notices are unique to this test.

### Construction Record

Author: task-builder rework for `task_group_018/test_005`.

Created: 2026-07-07.

Updated: 2026-07-07.

Major changes: Reworked only `test_tasks/005` for the third calibration fix; reduced prompt/payload/template leakage; neutralized packet channel/status hints; expanded the answer template and standard answer with controlled audit fields; changed the evaluator to 8 exact-match scoring points with raw weights `1`, `2`, and `3`; verified the evaluator scores `output/answer.json` as full credit.

## 中文说明

### 数据和来源

本任务属于 `task_group_018`，来源场景为 `SCN_018_court_clerk_disposition_orders_and_financial_entries`，对应源示例 `E001`、`E002`、`E003`。任务是 2025 年 6 月多县书记员财务异常登记表。共享 clerk operations 环境提供案件、案卷、费用表、付款政策、陈旧导出和财务义务记录。求解器可见的本地材料是 `input/payloads/monthly_financial_exception_packet.json`，输出格式由 `input/payloads/answer_template.json` 定义。

这是 `test_005` 的第三次校准修正。上一次重做后，两次 clean-context 直接尝试得分为 `18/24 = 0.75` 和 `15/24 = 0.625`，平均 `0.6875`。两次都只漏掉计划/风险点和汇总点，其中一次还漏掉来源优先级；但它们仍拿到了高权重的范围、优先级、宽泛行分类、修正依据、无计划/附带事项处理和实时账务点。本次修正保留同一书记员工作流，但降低直接可观察字段的权重，并增加受控 audit 字段，覆盖 June actionability、来源依据、中性 reconciliation family、计划重算依据、风险依据和汇总重算。

### 任务定义与场景契合性

求解器需要制作 2025 年 6 月中央财务质量异常登记表。工作包括把本地 intake packet 与实时环境记录结合，判断哪些候选通知应进入月末登记表、给纳入行排序、处理实时/本地/陈旧来源冲突、修正余额、保留或调整付款计划、识别纯附带事项遗漏，并重新计算汇总金额和案件集合。

这符合源场景，因为它是法院书记员的判后记录核对任务：财务和案卷条目释放前，必须核对本地 desk notice、实时 ledger、费用表、付款计划、docket history、陈旧队列和 collateral/program 记录。

### 材料地图

- `monthly_financial_exception_packet.json`：来自多个 desk channel 的候选通知。本次第三修正把最终判断味道较强的 channel label 和 status hint 中性化，同时保留 desk excerpt、本地余额提示、候选费用代码、信托/现金项目、本地计划条件和附带事项标记。
- `/api/cases` 与 `/api/cases/<case_number>`：实时案件姿态、被告姓名、处分日期、赔偿事实、DUI/附带事项事实和案件状态。
- `/api/financial-obligations?case_number=<case_number>`：实时余额、账务状态、费用组件、已付贷记、付款计划、漏付款次数和当前计划条件。
- `/api/fees?county=<county>&matter_type=<type>&effective_on=<date>`：有效费用组件，用于判断未支持费用行。
- `/api/payment-policies?county=<county>`：需要计算计划时的首期日期和分期惯例。
- `/api/docket?case_number=<case_number>`：截至登记关闭日的案卷和附带事项录入状态。
- `/api/stale-exports`：陈旧背景和干扰队列，不能覆盖当前 packet 和实时记录。

### 解答和评估依据

应纳入登记表的案件是 `25-COL-00112`、`24-LAN-01003`、`24-MID-01003`、`24-JEF-01005`、`25-BEN-01004`、`24-MID-00077`。排除的候选为 `24-COL-01003`（仅陈旧背景）、`24-LAN-01005`（未来/仅供参考的 program calendar）和 `24-BEN-01001`（相似姓名收据未确认属于列示案件）。

关键行结果如下：

- `25-COL-00112`：Columbia deferred 案件。实时账务中 `CR-CONV` 不受支持，去除 `177.50`，余额从 `284.92` 降至 `107.42`。使用 packet 批准的新计划：每月 `50.00`，首期 `2025-08-14`，两期足额付款加末期 `7.42`，末期到期日 `2025-10-14`。
- `24-LAN-01003`：Lane 案件中 restitution administration 组件不受支持。去除 `CR-REST-ADM` `30.00`，保留实时 `45.00` 月付计划，并把修正后 `93.05` 计算为两期足额付款加 `3.05` 末期，末期到期日 `2025-09-09`。
- `24-MID-01003`：Middlesex 信托贷记结清。将 packet 中 `46.52` 的 trust credit 计入实时 pending-adjustment 余额，余额为 `0.00`，无计划也无风险金额。
- `24-JEF-01005`：Jefferson 付款违约。保留实时 ledger 余额和实时 `40.00` 计划条件，路由为返庭，并按两次漏付计算 `80.00` 违约风险。
- `25-BEN-01004`：Benton DUI 驾照摘要遗漏。无余额修正、无计划风险，附带事项触发日期为 `2025-05-03`。
- `24-MID-00077`：Middlesex treatment referral 遗漏。无余额修正、无计划风险，附带事项触发日期为 `2024-06-14`。

第三修正版 evaluator 包含八个 exact-match 评分点，原始权重合计 17：

| ID | 权重 | 目标 |
| --- | ---: | --- |
| `SP001` | 1 | 登记表标识、纳入/排除案件集合和最终排序。 |
| `SP002` | 1 | 基本行优先级、行分类和行动代码。 |
| `SP003` | 2 | 候选层面的 June actionability、范围原因、排除依据和来源族 audit。 |
| `SP004` | 3 | 来源优先级、实时/本地/陈旧来源 audit 和中性 reconciliation family 代码。 |
| `SP005` | 2 | 实时账务事实、金额依据、修正组件、修正金额和修正后余额。 |
| `SP006` | 3 | 新计划、现有计划和返庭计划依据，以及分期计算和风险 audit。 |
| `SP007` | 2 | 贷记结清无计划处理，以及纯附带事项零风险处理。 |
| `SP008` | 3 | 汇总计数、金额合计、行 audit 计数和重新计算的案件集合。 |

常见错误包括纳入所有 packet 项、按 packet 顺序而不是登记优先级排序、让陈旧队列片段覆盖实时记录、把信托结清当成付款计划、应保留实时计划时改用新月付、混淆费用更正和贷记结清、给纯附带事项行分配风险金额，以及没有从最终行 audit 字段重新计算汇总。

### 迁移设计

训练锚点如下：

- `train_002` 锚定分期付款计算、较小末期付款、首期/末期日期，以及实时或已批准月付金额的使用。
- `train_004` 锚定陈旧/实时来源纪律、费用组件清理、当前 ledger 对比和未支持财务行移除。
- `train_005` 锚定月度 review 范围、未入账收据结清、付款计划行动路由、返庭处理、合规/附带事项跟进和汇总案件集合。

依赖迁移的评分现在集中在 `SP003`、`SP004`、`SP006`、`SP007` 和 `SP008`。这些评分点需要从训练任务尝试和对照答案中归纳出来的惯例：当前来源优先于复制/陈旧 desk snippet、以 June actionability 而不是 packet membership 定范围、修正后新计划与保留实时计划与返庭默认之间的计划依据、风险金额依据，以及从审计后的行重新计算汇总。任务内探索仍然必要，因为县份、案件号、实时余额、案卷缺口、费用组件、信托项目、付款状态、漏付款次数和干扰通知都是本测试独有的。

### 构造记录

作者：`task_group_018/test_005` rework builder。

创建日期：2026-07-07。

更新日期：2026-07-07。

主要变更：仅针对 `test_tasks/005` 做第三次校准修正；减少 prompt/payload/template 泄漏；中性化 packet channel/status hints；扩展 answer template 和标准答案，加入受控 audit 字段；将 evaluator 改为 8 个 exact-match 评分点，原始权重只使用 `1`、`2`、`3`；验证 evaluator 对 `output/answer.json` 给满分。
