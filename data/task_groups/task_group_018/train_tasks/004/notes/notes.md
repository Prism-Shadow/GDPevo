# train_004 Notes

## English

### Data lineage and task definition

This is `task_group_018` / `train_004`, built from scenario `SCN_018_court_clerk_disposition_orders_and_financial_entries` and source examples `E001`, `E002`, and `E003`. The task uses the shared clerk operations environment in `task_group/task_group_018/env/`, especially Marion County case records, attorney records, criminal fee schedules, financial obligations, and docket records. The task-local payload is `input/payloads/marion_mixed_misdemeanor_packet.json`, a stale clerk export plus hearing, financial-review, and counsel-confirmation notes.

The solver-visible request asks for a corrected Marion County mixed misdemeanor update file. The output must follow `input/payloads/answer_template.json` and contain case-level status, disposition, representation, approved fee-code, financial-delta, and docket-action fields. The intended target cases are the five records in the stale export with `queue` equal to `mixed_misdemeanor_docket`: `23-MAR-01004`, `24-MAR-01004`, `25-MAR-01001`, `25-MAR-01002`, and `25-MAR-01003`. The traffic and compliance rows in the packet are distractors.

### Scenario fit and material map

The task fits the scenario because it mirrors a clerk post-hearing reconciliation workflow: a stale local export conflicts with live CMS records, the bench packet changes only some hearing facts, counsel confirmations correct representation details, and the financial update depends on fee schedules and live ledger principal amounts.

Material usage:

- Shared environment `/api/cases` and `/api/cases/<case_number>`: live Marion case status, disposition dates, charges, defense information, and filing dates.
- Shared environment `/api/financial-obligations?case_number=<case_number>`: current live `principal_amount` used as the comparison base.
- Shared environment `/api/fees?county=Marion&matter_type=criminal&effective_on=<date>`: criminal filing and conviction assessments by effective date.
- Shared environment `/api/attorneys`: confirms Marion-capable attorneys and supported defense types.
- Task payload stale export: gives the work queue and stale values to reconcile, including distractors.
- Task payload hearing/review notes: gives the current warrant recall for `24-MAR-01004`, the new disposition for `25-MAR-01003`, and the financial-review limits for `25-MAR-01001` and `25-MAR-01002`.
- Task payload counsel confirmations: resolves counsel type conflicts for `24-MAR-01004`, `25-MAR-01001`, and `25-MAR-01002`.

### Solution and answer basis

The five output rows are sorted by case number. `23-MAR-01004` remains probation active with its 2024 disposition and old filing assessment of `105.00`; no live update is needed. `24-MAR-01004` has its warrant recalled by the packet, remains open without disposition, keeps only the old filing assessment of `105.00`, and uses Nolan Pierce as retained counsel. `25-MAR-01001` remains closed from `2025-07-22`; the final approved fees are `CR-CONV` and `CR-FILING` for `287.50`, so the live principal `327.50` is reduced by `40.00`. `25-MAR-01002` remains deferred from `2025-09-22`; no conviction or restitution fee is approved, so only `CR-FILING` for `110.00` remains and the live principal `327.50` is reduced by `217.50`. `25-MAR-01003` receives the new `2026-06-18` conviction/probation outcome; there was no live ledger principal, so `CR-CONV` plus `CR-FILING` creates a `287.50` positive delta.

The aggregate answer has `case_count = 5`, `financial_adjustment_count = 3`, `total_financial_delta = 30.00`, and representation mismatch cases `24-MAR-01004`, `25-MAR-01001`, and `25-MAR-01002`.

Scoring uses nine exact-match points with raw weights:

- `case_set_and_order`, weight 2: target case set and ascending order.
- `resolved_statuses_and_dates`, weight 3: resolved status and disposition date for every case.
- `disposition_classes`, weight 2: disposition class and convicted charge count.
- `representation_corrections`, weight 2: attorney, defense type, and mismatch flag.
- `approved_fee_codes`, weight 3: approved fee-code set by case.
- `case_financial_totals`, weight 3: current ledger principal and corrected approved principal to cents.
- `financial_deltas_and_count`, weight 3: per-case deltas and adjustment count.
- `docket_actions`, weight 2: case-level docket action code.
- `aggregate_rollup`, weight 2: case count, total delta, and mismatch case list.

Likely model pitfalls include treating every stale export row as in scope, using stale status over live records, retroactively applying 2025 fees to 2024 dispositions, posting `CR-REST-ADM` without restitution, posting `CR-PROB` when the note says no separate setup fee, treating statute codes such as `CR-507` as fee codes, and missing counsel-type corrections when the attorney name is unchanged.

### Transfer design

As a train task, this task lets a later skill-builder infer several reusable conventions after comparing a blind attempt with the answer: live records normally beat stale local exports; hearing notes alter only the facts actually heard or reviewed; counsel confirmations can override stale/live representation type; fee schedules must be selected by county, matter type, and effective date; unsupported or unpronounced financial rows should not be carried forward; current ledger principal is the comparison base for deltas; and structured outputs should use controlled enums and stable case ordering. These are intended to transfer to the test tasks involving stale-source resolution, fee cleanup, representation mismatch flags, and docket-action decisions.

### Construction record

Author: task-builder subagent for `train_004`.

Created: 2026-07-07.

Updated: 2026-07-07.

Major changes: created the task-local packet, answer template, standard answer, bilingual notes, and exact-match evaluator for the Marion County mixed misdemeanor stale-export task.

## 中文

### 数据来源与任务定义

本任务是 `task_group_018` 的 `train_004`，来源于场景 `SCN_018_court_clerk_disposition_orders_and_financial_entries` 以及样例 `E001`、`E002`、`E003`。任务使用共享 clerk operations 环境，重点涉及 Marion County 的案件记录、律师记录、刑事费用表、财务义务和 docket 记录。任务本地材料是 `input/payloads/marion_mixed_misdemeanor_packet.json`，其中包含过期的书记员导出、庭审记录、财务复核记录和律师确认信息。

求解者需要生成 Marion County 混合轻罪 docket 的更正后 JSON 文件，格式由 `input/payloads/answer_template.json` 定义。目标案件是本地过期导出中 `queue` 为 `mixed_misdemeanor_docket` 的五个案件：`23-MAR-01004`、`24-MAR-01004`、`25-MAR-01001`、`25-MAR-01002`、`25-MAR-01003`。导出中的 traffic 和 compliance 行是干扰项。

### 场景契合与材料地图

该任务模拟书记员在庭审后进行案件管理系统更新的真实流程：本地导出已经过期，实时 CMS 记录与其冲突，庭审材料只改变部分事实，律师确认材料修正代理类型，财务更新需要结合有效日期费用表和实时 ledger principal。

材料用途如下：

- 共享环境 `/api/cases` 和 `/api/cases/<case_number>`：用于核对实时案件状态、处分日期、指控、辩护信息和立案日期。
- 共享环境 `/api/financial-obligations?case_number=<case_number>`：用于取得当前实时 `principal_amount`，作为 delta 计算基准。
- 共享环境 `/api/fees?county=Marion&matter_type=criminal&effective_on=<date>`：用于按有效日期查 Marion 刑事案件 filing 和 conviction assessment。
- 共享环境 `/api/attorneys`：用于核对 Marion 可用律师和代理类型。
- 本地 stale export：用于确定工作队列和需要调和的过期字段，并包含干扰行。
- 本地 hearing/review notes：用于确定 `24-MAR-01004` 的 warrant recall、`25-MAR-01003` 的新处分，以及 `25-MAR-01001`、`25-MAR-01002` 的财务复核限制。
- 本地 counsel confirmations：用于解决 `24-MAR-01004`、`25-MAR-01001`、`25-MAR-01002` 的代理类型冲突。

### 答案与评估依据

五个输出行按案件号升序排列。`23-MAR-01004` 保持 probation active 和 2024 年处分，仅保留旧 filing assessment `105.00`，无需更新。`24-MAR-01004` 根据材料撤销 warrant，案件保持 open 且无处分，只保留旧 filing assessment `105.00`，律师类型改为 Nolan Pierce retained。`25-MAR-01001` 保持 `2025-07-22` 的 closed disposition，最终费用为 `CR-CONV` 和 `CR-FILING`，合计 `287.50`，相对实时 principal `327.50` 减少 `40.00`。`25-MAR-01002` 保持 `2025-09-22` 的 deferred disposition，没有 conviction 或 restitution fee，仅保留 `CR-FILING` `110.00`，相对实时 principal `327.50` 减少 `217.50`。`25-MAR-01003` 根据 `2026-06-18` 的新庭审结果进入 conviction/probation；实时 ledger 中没有 principal，因此新增 `CR-CONV` 与 `CR-FILING` 共 `287.50`。

汇总答案为 `case_count = 5`，`financial_adjustment_count = 3`，`total_financial_delta = 30.00`，代理冲突案件为 `24-MAR-01004`、`25-MAR-01001`、`25-MAR-01002`。

评估包含九个精确匹配评分点：

- `case_set_and_order`，权重 2：目标案件集合和升序顺序。
- `resolved_statuses_and_dates`，权重 3：每案的最终状态和处分日期。
- `disposition_classes`，权重 2：处分类别和 convicted charge 数量。
- `representation_corrections`，权重 2：律师、代理类型和冲突标记。
- `approved_fee_codes`，权重 3：每案批准费用代码集合。
- `case_financial_totals`，权重 3：当前 ledger principal 和更正后 principal。
- `financial_deltas_and_count`，权重 3：每案 delta 和需财务调整案件数量。
- `docket_actions`，权重 2：每案 docket action code。
- `aggregate_rollup`，权重 2：案件数、总 delta 和代理冲突案件列表。

常见错误包括：把 stale export 中所有行都当作目标案件、用过期状态覆盖实时记录、把 2025 费用追溯到 2024 处分、在没有 restitution 时保留 `CR-REST-ADM`、在 note 明确未宣告 setup fee 时加入 `CR-PROB`、把 `CR-507` 等 statute 当成 fee code、以及在律师姓名未变但代理类型已变时漏标 representation mismatch。

### 迁移设计

作为训练任务，本任务可让后续 skill-builder 在对照标准答案后归纳出可迁移规则：实时记录通常优先于过期本地导出；庭审材料只改变本次庭审或复核涉及的事实；律师确认可修正过期或实时记录中的代理类型；费用表必须按 county、matter type 和 effective date 选择；未支持或未宣告的财务项目不能沿用；delta 应以当前实时 ledger principal 为基准；结构化输出应使用受控枚举和稳定排序。这些经验会迁移到后续测试任务中的过期来源调和、费用清理、代理冲突标记和 docket action 判断。

### 构造记录

作者：`train_004` task-builder subagent。

创建日期：2026-07-07。

更新日期：2026-07-07。

主要变更：创建 Marion County 混合轻罪 stale export 任务的本地材料、答案模板、标准答案、双语 notes 和精确匹配 evaluator。
