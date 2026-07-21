# test_004 Notes - Lake County Criminal Closeout

## English Review Notes

### Data and Source Lineage

This task belongs to `task_group_018`, source scenario `SCN_018_court_clerk_disposition_orders_and_financial_entries`, with source examples `E001`, `E002`, and `E003`. It is a test task in the Arkansas criminal closeout family. The closest train anchors are `train_001` and `train_004`.

The shared Court Operations Portal contains the target Lake County records for `LC-25-0320`, `LC-25-0326`, `LC-24-0899`, and `LC-25-0331` in the generated `cases`, `charges`, `docket_entries`, `jurisdictions`, and `fee_schedules` data exposed by the public API. The task-local solver-visible payloads are `lake_hearing_notes_2025-06-18.md`, `lake_counsel_memo_and_worksheet.csv`, `lake_finance_queue_payloads.json`, and `answer_template.json`.

### Task Definition and Scenario Fit

The solver acts as a Lake County Arkansas criminal clerk preparing Judge Mercer's June 18, 2025 closeout. They must reconcile courtroom notes, a counsel worksheet, finance queue rows, and portal records before producing disposition entries, exclusion decisions, counsel and source audit findings, financial postings, docket action codes, and register totals.

This fits the task group because it is the same office workflow as the Arkansas train tasks: multi-case criminal disposition closeout, noisy queue data, counsel-type ambiguity, signed-order versus draft status, fee posting, docket language, and register balancing. The task is not a template copy because it adds Lake-specific count merging, a filing-date conflict, a public-defender fee waiver, and one continued matter.

### Material Map

`GET /api/cases` supplies official Lake case identities, DOBs, counsel types, attorney names, status, disposition dates, filing dates, source systems, and case notes. `GET /api/charges` supplies charge rows and sentencing fields, but the solver must reconcile stale or generic charge fields with the hearing notes. `GET /api/docket-entries` provides source/status hints, including the continued posture of `LC-25-0331`. `GET /api/fee-schedules` supplies the current Lake County circuit criminal court cost of `145.00`. `GET /api/search` can locate the same target objects when the solver does not know endpoint filters.

The hearing notes are the best local source for courtroom outcomes: `LC-25-0320` has counts 2 and 3 merged into count 1, no-contest deferred disposition, a `250.00` fine, and a durational departure; `LC-25-0326` is nolle prosequi with court costs and a public-defender user-fee waiver; `LC-24-0899` is a bench-trial guilty finding with appointed private counsel and no departure; `LC-25-0331` is continued with no final order. The counsel memo and finance queue deliberately contain noisy user-fee, filing-date, merged-count, and source/disposition conflicts.

### Solution and Evaluation Basis

The standard answer includes `LC-24-0899`, `LC-25-0320`, and `LC-25-0326` in final closeout entries and excludes `LC-25-0331` as `continued_no_final_order` with next status date `2025-07-16`. Counsel resolves to appointed private for `LC-24-0899`, retained for `LC-25-0320`, and public defender for `LC-25-0326` and `LC-25-0331`; only the disposed public-defender case has a user-fee decision, and that line is waived by the judge. The final amounts are `1145.00` for `LC-24-0899`, `395.00` for `LC-25-0320`, `145.00` for `LC-25-0326`, and `0.00` for `LC-25-0331`. Register totals are 3 included cases, 1 excluded pending/continued matter, 3 disposition entries, 3 financial entries, `1250.00` fines, `435.00` court costs, `0.00` user fees, `0.00` assessments, and `1685.00` grand total.

The evaluator has eight whole-point scoring checks with raw weights `[1, 3, 2, 3, 1, 1, 3, 1]`:

- `SP001`: final included case set and detailed continued exclusion record.
- `SP002`: audit findings for counsel, filing/source, merged-count, departure, user-fee, and continued-status conflicts.
- `SP003`: counsel-type reconciliation and conditional public-defender user-fee treatment for all target cases.
- `SP004`: disposition outcomes, closeout actions, dates, merged counts, pleas, sentences, and pending treatment.
- `SP005`: departure and non-departure classification.
- `SP006`: per-case financial posting, fee inclusion/exclusion, and case totals.
- `SP007`: docket/register action language codes, entry codes, dates, and amount due.
- `SP008`: aggregate register counts and dollar totals.

These checks cover at least six distinct outcomes: inclusion/exclusion, audit/source conflict handling, counsel and user-fee decisions, disposition/count treatment, departure classification, finance, docket action language, and aggregate totals. Each scoring point is all-or-nothing with no fractional credit inside a point. The higher weights emphasize audit/source conflict handling, final disposition treatment, and docket/register action language, which are the recurring closeout decisions most dependent on train-derived experience.

Likely pitfalls include posting separate court costs for merged counts 2 and 3 in `LC-25-0320`, treating `APD private` as public defender in `LC-24-0899`, posting the queued public-defender user fee despite the waiver in `LC-25-0326`, using the counsel worksheet filing date instead of the portal filed date, entering `LC-25-0331` from the draft queue, or copying the old departure flag on `LC-24-0899`.

### Transfer Design

Train anchors: `train_001` anchors conditional public-defender user-fee handling, source/queue conflict logging, signed-order discipline, docket summary codes, and register totals. `train_004` anchors appointed-private versus public-defender reconciliation, continued/pending exclusion, current jurisdictional court-cost lookup, count/outcome reconciliation from hearing notes, and aggregate register computation.

Transfer-dependent scoring points are `SP002`, `SP003`, `SP006`, `SP007`, and `SP008`. The solver benefits from train-derived experience by knowing that counsel labels like APD can mean appointed private rather than public defender, public-defender/user-fee lines are conditional and can be excluded or waived, pending or continued matters do not receive disposition or financial postings, current fee schedules override staging rows, and docket/register outputs use controlled action codes. Task-specific exploration remains necessary for the Lake case identifiers, the merged-count facts, the Lake `145.00` cost schedule, the filing-date conflict, and the exact register totals.

### Construction Record

Author: Codex task-builder subagent for `test_004`.

Created: 2026-07-18.

Updated: 2026-07-18.

Major changes: created `test_tasks/004/` with solver prompt, three realistic local payloads, answer template, standard answer, deterministic evaluator, and bilingual notes. Later calibration rework adjusted rubric weights while preserving the same scoring points and standard answer.

## 中文审阅说明

### 数据和来源

本任务属于 `task_group_018`，来源场景为 `SCN_018_court_clerk_disposition_orders_and_financial_entries`，参考示例为 `E001`、`E002` 和 `E003`。它是阿肯色刑事结案登记系列的测试任务，最直接的训练锚点是 `train_001` 和 `train_004`。

共享的 Court Operations Portal 中包含 Lake County 目标案件 `LC-25-0320`、`LC-25-0326`、`LC-24-0899`、`LC-25-0331`，相关数据分布在案件、指控、案卷、辖区和费用表接口中。本任务本地可见材料包括庭审记录、律师备忘和工作表、财务队列 JSON，以及答案模板。

### 任务定义和场景契合

解题者扮演 Lake County 阿肯色刑事书记员，为 Mercer 法官 2025-06-18 的刑事庭次做结案。需要在庭审记录、律师工作表、财务队列和门户记录之间核对，输出处分录入、排除事项、律师和来源审计、费用、案卷动作代码以及登记簿总额。

该任务符合任务组的核心工作流：多案件刑事结案、队列噪声、律师类型歧义、已签命令与草稿状态区分、费用录入、案卷语言和登记簿平衡。它不是简单套用训练题，因为新增了 Lake County 的合并罪数、立案日期冲突、公设辩护人费用豁免，以及一个继续审理事项。

### 材料用途

`GET /api/cases` 用于核对身份、DOB、律师类型、律师姓名、状态、处分日期、立案日期、来源系统和案件备注。`GET /api/charges` 提供指控和量刑字段，但需要与庭审记录核对。`GET /api/docket-entries` 提供状态和来源线索，尤其是 `LC-25-0331` 的继续审理状态。`GET /api/fee-schedules` 给出 Lake County 当前刑事法院成本 `145.00`。`GET /api/search` 可用于查找目标对象。

庭审记录是处分结果的主要本地证据：`LC-25-0320` 的第 2、3 项并入第 1 项，作无抗辩延期处分，罚金 `250.00`，并标记为量期偏离；`LC-25-0326` 是 nolle prosequi，收普通法院成本，且公设辩护人使用费被法官豁免；`LC-24-0899` 是法官审判有罪，律师是 appointed private，且无偏离；`LC-25-0331` 继续审理，没有最终命令。律师备忘和财务队列提供故意设置的用户费、立案日期、合并罪数、来源和处分冲突。

### 标准答案和评分依据

标准答案将 `LC-24-0899`、`LC-25-0320` 和 `LC-25-0326` 纳入最终结案登记，并将 `LC-25-0331` 作为 `continued_no_final_order` 排除，下一次状态日期为 `2025-07-16`。律师类型分别为 appointed private、retained、public defender、public defender；唯一已处分的公设辩护人案件 `LC-25-0326` 的使用费被法官豁免。每案金额为 `1145.00`、`395.00`、`145.00` 和 `0.00`。登记簿汇总为 3 个纳入案件、1 个排除事项、3 个处分录入、3 个财务录入、罚金 `1250.00`、法院成本 `435.00`、用户费 `0.00`、评估费 `0.00`、总额 `1685.00`。

评估器有 8 个整点评分项，权重为 `[1, 3, 2, 3, 1, 1, 3, 1]`，分别检查纳入和排除、审计冲突、律师和用户费、处分与合并罪数、偏离分类、每案费用、案卷动作语言和登记簿总额。评分覆盖至少六类不同业务结果，每个评分项只有全对或零分。较高权重集中在 audit/source conflict、final disposition treatment 和 docket/register action language，这些是更依赖训练经验迁移的 recurring closeout decisions。

常见错误包括给 `LC-25-0320` 的合并第 2、3 项分别加法院成本；把 `LC-24-0899` 的 `APD private` 当作公设辩护人；在 `LC-25-0326` 中录入已豁免的公设辩护人费用；使用律师工作表中的错误立案日期；根据草稿队列录入 `LC-25-0331`；或照抄 `LC-24-0899` 的旧偏离标记。

### 迁移设计

训练锚点：`train_001` 支持迁移公设辩护人使用费的条件处理、来源和队列冲突记录、签署命令纪律、案卷摘要代码和登记簿汇总。`train_004` 支持迁移 appointed private 与 public defender 的区分、继续或待定事项排除、当前辖区法院成本查询、从庭审记录核对指控结果，以及汇总登记簿金额。

依赖迁移的评分点是 `SP002`、`SP003`、`SP006`、`SP007` 和 `SP008`。训练经验应帮助解题者认识到 APD 标签可能不是公设辩护人，公设辩护人费用是有条件的并可能被排除或豁免，继续审理事项不能录入处分或财务记录，当前费用表优先于队列金额，并且案卷和登记簿输出使用受控动作代码。任务本身仍要求探索 Lake 的具体案号、合并罪数、`145.00` 法院成本、立案日期冲突和精确汇总金额。

### 构造记录

作者：`test_004` 的 Codex 任务构造子代理。

创建日期：2026-07-18。

更新日期：2026-07-18。

主要变更：创建 `test_tasks/004/` 下的提示、三个真实感本地材料、答案模板、标准答案、确定性评估器和双语说明；后续 calibration rework 调整了 rubric weights，但保留相同 scoring points 和 standard answer。
