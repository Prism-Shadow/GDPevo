# train_001 Notes - Benton Criminal Docket Audit

## English

### Data and Source Lineage

This task belongs to `SCN_018_court_clerk_disposition_orders_and_financial_entries` and is anchored primarily in source example `E001` with supporting conventions from `E002` and `E003`. It adapts the criminal sentencing docket audit pattern from the Arkansas example into a fictional Benton County clerk operations environment.

Shared environment data comes from `task_group/task_group_018/env/data/clerk_ops.json` through the HTTP service. The relevant live records are the Benton criminal cases `24-BEN-01005`, `25-BEN-00058`, `25-BEN-01002`, and `25-BEN-01007`, plus Benton criminal fee schedules, payment policy, financial obligations, docket records, attorneys, and stale exports. Task-local visible payloads are `benton_plea_minutes_2025-06-20.json`, `attorney_verification_memo_2025-06-21.json`, and `draft_finance_import_2025-06-21.csv`.

### Task Definition and Expected Work

The solver acts as a Benton County Circuit Court clerk after a four-case criminal plea and sentencing docket on 2025-06-20. The expected answer is a single JSON object matching `input/payloads/answer_template.json`. The solver must identify the four target matters, reconcile judge minutes with live records and the attorney memo, apply current Benton criminal fee rows effective on the hearing date, carry forward live ledger payment credits, and mark docket actions required before entry.

The task is intentionally not a form-fill exercise. It requires case-level source reconciliation, charge-level disposition mapping, current-fee selection, exclusion of unsupported draft import rows, and corrected balance calculations.

### Scenario Fit

This task matches the group scenario because it asks for clerk-ready disposition, financial, and docket-entry outputs after a criminal hearing. It preserves the source examples' difficulty drivers: multiple records for the same matter, stale or preliminary financial data, attorney/status conflicts, effective-date fee rows, and structured clerk output.

### Material Map

- Shared `/api/cases` and `/api/cases/<case_number>`: live case captions, charges, status, attorney, DOB, and existing posture.
- Shared `/api/fees?county=Benton&matter_type=criminal&effective_on=2025-06-20`: current fee schedule used for corrected fee components.
- Shared `/api/financial-obligations?case_number=...`: live amount-paid credits that reduce corrected balances.
- Shared `/api/payment-policies?county=Benton`: unsupported charge codes and county policy context.
- Shared `/api/docket?case_number=...` and stale export endpoints: docket/status conflict context.
- `benton_plea_minutes_2025-06-20.json`: authoritative hearing outcome facts for pleas, dismissals, sentences, warrant recalls, and restitution amounts.
- `attorney_verification_memo_2025-06-21.json`: counsel and representation corrections after hearing.
- `draft_finance_import_2025-06-21.csv`: preliminary finance data containing obsolete, unsupported, and missing rows; it is a trap source, not the final ledger.

### Solution and Evaluation Basis

Final case order is ascending by case number: `24-BEN-01005`, `25-BEN-00058`, `25-BEN-01002`, `25-BEN-01007`. All four end as `probation_active` after conviction on one charge and sentencing.

The current Benton criminal fee rows are `CR-CONV` 165.00, `CR-FILING` 95.00, `CR-PROB` 82.50 when probation is ordered, and `CR-REST-ADM` 25.00 when restitution is ordered. Restitution principal is added to the fee total. Draft import rows such as obsolete 150.00 conviction assessments, 15.00 restitution administration, `CR-507`, `CR-LATE`, and `PD-USER` are excluded. Corrected balances are calculated as new principal minus live ledger amount paid credit.

Scoring uses eight exact-match points, raw weights totaling 20:

1. Target metadata and case set/order, weight 2.
2. Charge-level pleas, dispositions, and verdicts, weight 3.
3. Final case status and sentence fields, weight 3.
4. Defense attorney, defense type, and discrepancy code, weight 2.
5. Fee component code/amount lists and new principal totals, weight 3.
6. Live credit and corrected balance due per case, weight 3.
7. Docket action booleans per case, weight 2.
8. Register totals, weight 2.

Likely pitfalls include treating the draft finance import as final, using obsolete fee rows on the older case, forgetting the filing assessment, adding unsupported failure-to-appear or public-defender quick-pick charges, ignoring live ledger credits, or preserving live attorney/status fields after the hearing packet and memo supersede them.

### Transfer Design

As a train task, this real docket lets a skill-builder infer several reusable conventions: hearing outcomes update disposition facts, live records provide existing case and ledger context, supplemental memos can resolve attorney conflicts, current effective-date schedules control fees, unsupported draft charges should be excluded, and final outputs should use controlled enums and stable ordering. Those habits transfer directly to later criminal-disposition and financial-audit tasks in this group.

### Construction Record

Author: Codex task-builder subagent. Created: 2026-07-07. Updated: 2026-07-07. Major changes: created full `train_001` task folder, local payloads, standard answer, bilingual notes, and exact-match evaluator.

## Chinese

### 数据与来源

本任务属于 `SCN_018_court_clerk_disposition_orders_and_financial_entries`，主要锚定源例 `E001` 的刑事 sentencing docket 审核流程，同时吸收 `E002` 的费用/付款纪律和 `E003` 的跨表一致性要求。任务把 Arkansas 刑事庭后处理迁移到虚构的 Benton County 书记员环境中。

共享环境数据来自 `task_group/task_group_018/env/data/clerk_ops.json`，解题时通过 HTTP 服务访问。关键 live records 是 Benton County 的 `24-BEN-01005`、`25-BEN-00058`、`25-BEN-01002`、`25-BEN-01007`，以及相关 fee schedule、payment policy、financial obligations、docket entries、attorneys 和 stale exports。任务本地可见材料包括法官 minute cards、律师核验 memo 和 draft finance import。

### 任务定义

解题者扮演 2025-06-20 刑事 plea/sentencing docket 后的 Benton County Circuit Court clerk，需要输出符合 `answer_template.json` 的 JSON。核心工作是确定四个目标案件，核对 judge minutes、live case records 和 attorney memo，使用 2025-06-20 生效的 Benton criminal fee rows，沿用 live ledger 中已支付金额作为 credit，并标注进入正式 docket 前需要的操作。

这不是简单填表任务。难点在于同一案件跨来源冲突、charge-level disposition 映射、effective-date fee 选择、排除 draft import 中的错误费用，以及计算 corrected balance。

### 场景适配

本任务符合当前法院书记员场景，因为它要求把庭审结果转化为 clerk-ready 的 disposition、financial entry 和 docket action。它保留了源例中的核心难点：多来源记录、陈旧或初稿财务数据、律师/状态冲突、生效日期费用表、以及结构化输出。

### 材料地图

- 共享 cases API：live caption、charges、status、attorney、DOB 和既有案件状态。
- 共享 fees API：按 Benton、criminal、2025-06-20 选择当前 fee rows。
- 共享 financial obligations API：读取 live amount-paid credits，用于 corrected balance。
- 共享 payment policy API：识别 unsupported charge codes 和县级政策背景。
- 共享 docket/stale export API：提供 status 和 stale-source 冲突背景。
- `benton_plea_minutes_2025-06-20.json`：庭审中 plea、dismissal、sentence、warrant recall 和 restitution 的权威来源。
- `attorney_verification_memo_2025-06-21.json`：庭后律师和 representation type 更正来源。
- `draft_finance_import_2025-06-21.csv`：包含过期、未支持和遗漏项目的初稿财务导入，是干扰材料，不是最终账目。

### 答案与评测依据

最终案件顺序按 case number 升序：`24-BEN-01005`、`25-BEN-00058`、`25-BEN-01002`、`25-BEN-01007`。四案均因至少一个 charge 定罪并宣告 probation，最终状态为 `probation_active`。

Benton criminal 当前费用为：`CR-CONV` 165.00，`CR-FILING` 95.00，probation ordered 时加入 `CR-PROB` 82.50，restitution ordered 时加入 `CR-REST-ADM` 25.00。restitution 本金加入 principal total。需要排除 draft import 里的过期 150.00 conviction assessment、15.00 restitution admin、`CR-507`、`CR-LATE` 和 `PD-USER`。corrected balance 等于 new principal total 减去 live ledger amount-paid credit。

评测包含 8 个 exact-match 评分点，原始权重合计 20：

1. 目标元数据和案件集合/顺序，权重 2。
2. charge-level plea、disposition、verdict，权重 3。
3. final case status 和 sentence fields，权重 3。
4. defense attorney、defense type、discrepancy code，权重 2。
5. fee component code/amount 列表和 new principal totals，权重 3。
6. 每案 live credit 和 corrected balance due，权重 3。
7. 每案 docket action booleans，权重 2。
8. register totals，权重 2。

常见错误包括把 draft finance import 当作最终账目、在旧案中沿用过期 fee row、漏掉 filing assessment、加入未支持的 failure-to-appear 或 public-defender quick-pick 费用、忽略 live ledger credits，或在 hearing packet 和 memo 已更新后仍保留旧的 live attorney/status 字段。

### 迁移设计

作为 train task，本任务让 skill-builder 通过真实解题和对照标准答案推断可迁移经验：庭审结果更新 disposition facts，live records 提供既有案卷和账目背景，补充 memo 可解决 attorney conflicts，按 effective date 选择当前 fee schedule，排除未支持的 draft charges，并按稳定顺序和受控枚举输出。这些经验可迁移到本组后续 criminal disposition、fee audit 和 docket-entry 任务。

### 构造记录

作者：Codex task-builder subagent。创建日期：2026-07-07。更新日期：2026-07-07。主要变更：创建 `train_001` 完整任务目录、本地 payload、标准答案、双语 notes 和 exact-match evaluator。
