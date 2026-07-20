# English Notes

## Data and Source Lineage

This is `train_002` for `task_group_018`, derived from scenario `SCN_018_court_clerk_disposition_orders_and_financial_entries` and especially source example `E002` (Oregon traffic payment-plan closeout). It uses shared environment target citations `OR26-TR-1188` and `OR26-TR-1194`, the Oregon 22nd Judicial District / Jefferson County fee schedules, payment policy `POL-OR22-EPP`, and form catalog entry `OR_22JD_PLAN`.

Task-local solver-visible materials are:

- `input/payloads/hearing_closeout_note.md`: hearing closeout facts, plea/finding, approved payment amounts, and stale or unsupported fee distractions.
- `input/payloads/local_form_excerpt.md`: local extended-payment-plan form labels, account-reference convention, and obsolete account-fee distraction.
- `input/payloads/answer_template.json`: normalized JSON shape, enum values, currency precision, date format, and ordering rules.

## Task Definition and Scenario Fit

The solver acts as a court clerk closing two Oregon traffic violation hearings after a November 12, 2026 docket. The expected work is to reconcile local hearing notes with the Court Operations Portal, apply the current standard fine tier, add the Jefferson County surcharge once per citation, exclude unsupported add-on charges, compute the approved post-disposition payment plans, and produce clerk-ready structured closeout fields.

This fits the task group because it repeats the source scenario's court-clerk workflow: disposition authority comes from hearing notes, financial amounts come from effective public schedule/policy records, and the final output must avoid stale or unsupported charges while preserving local form conventions.

## Material Map

The solver should use `<TASK_ENV_BASE_URL>/api/citations` or `/api/search` to locate the target citation facts and current stored closeout values. `/api/fee-schedules` provides the active Jefferson County standard fine rows and the stale 2022 high-speed row. `/api/payment-policies` provides the extended payment-plan policy, including no automatic account fee and first-due-date convention. `/api/forms` provides the 22nd Judicial District plan form metadata. The local form excerpt adds the exact visible labels `Case # / Account #`, `Case/Account Balance`, `Action Table(s) / Notes`, and `TERMS of PAYMENT`, and clarifies citation-number account reference use when no separate case/account number exists.

## Solution and Evaluation Basis

For `OR26-TR-1188`, Sarah Benton was found in violation on a no-contest plea for ORS 811.109(5), 103 mph in a 65 mph zone. The active fee row is `F-OR22-100-2024`, standard fine $1,150. The Jefferson County surcharge is $5, so amount due is $1,155. The approved post-disposition extended payment plan is $50 monthly, first due 2026-12-15, with 23 full $50 payments and a final $5 payment, total 24 installments, final due 2028-11-15.

For `OR26-TR-1194`, Jonah Merritt was found in violation on a no-contest plea for ORS 811.109, 91 mph in a 55 mph zone, the 31-to-40-over tier. The active fee row is `F-OR22-31-2024`, standard fine $440. The Jefferson County surcharge is $5, so amount due is $445. The approved post-disposition extended payment plan is $55 monthly, first due 2026-12-15, with 8 full $55 payments and a final $5 payment, total 9 installments, final due 2027-08-15.

Excluded charges are the stale 2022 standard fine for the high-speed citation, statutory maximum substitution, late-payment fee, collection fee, DMV fee, returned-check fee, account-management fee, and traffic-school fee. These are unsupported because the active schedule/policy or hearing note does not trigger them.

The evaluator has 8 whole-point checks with raw weights:

- `SP001` weight 2: target citation set and no-contest, violation-found, post-disposition closeout.
- `SP002` weight 2: current standard fine tier and source for `OR26-TR-1188`.
- `SP003` weight 2: current standard fine tier and source for `OR26-TR-1194`.
- `SP004` weight 2: $5 Jefferson surcharge per citation, per-citation amount due, and $1,600 batch total.
- `SP005` weight 2: approved extended payment-plan terms, monthly payment, first due date, and no down payment.
- `SP006` weight 3: installment counts, final partial payments, total installments, and final due dates.
- `SP007` weight 2: form id/label, exact local labels, and citation number as account reference.
- `SP008` weight 2: excluded stale and unsupported charges with zero unsupported amount included.

These 8 points span at least four distinct outcomes: matter disposition, fine tier selection, surcharge/balance calculation, payment-plan terms, installment arithmetic, form/account-reference handling, and unsupported-charge exclusion. Each point is deterministic and all-or-nothing.

Likely model pitfalls include using the stale $1,000 high-speed row, substituting a statutory maximum for the standard fine, omitting the Jefferson County surcharge, adding unsupported late or account fees, treating the payment plan as pre-disposition, using a separate unknown account number instead of the citation number, or rounding the final installment away instead of recording the $5 remainder.

## Transfer Design

As a train task, this exposes real traffic-closeout conventions that fewshot skill builders can infer by comparing the input and standard answer: use the active standard fine schedule rather than stale or maximum figures; add only the county surcharge supported by current local policy; exclude unsupported late, collection, DMV, returned-check, and account charges; keep the payment plan post-disposition; compute full installments plus final remainder exactly; and use local form labels/account-reference conventions rather than inventing identifiers.

## Construction Record

Author: Codex task-builder subagent for `train_002`.
Created: 2026-07-18.
Updated: 2026-07-18.
Major changes: created the complete task folder, local payloads, answer template, standard answer, evaluator, and bilingual notes for the Oregon 22nd Judicial District traffic violation closeout/payment-plan task.

# 中文说明

## 数据和来源

本任务是 `task_group_018` 的 `train_002`，来自场景 `SCN_018_court_clerk_disposition_orders_and_financial_entries`，主要对应源示例 `E002` 的 Oregon traffic payment-plan closeout。任务使用共享环境中的目标 citation：`OR26-TR-1188` 和 `OR26-TR-1194`，以及 Oregon 22nd Judicial District / Jefferson County 的 fee schedule、payment policy `POL-OR22-EPP` 和 form catalog 条目 `OR_22JD_PLAN`。

本地可见材料包括：

- `input/payloads/hearing_closeout_note.md`：庭审 closeout 事实、plea/finding、批准的付款金额，以及 stale/unsupported fee 干扰项。
- `input/payloads/local_form_excerpt.md`：本地 extended payment plan 表格标签、account reference 规则，以及过时 account-fee 干扰项。
- `input/payloads/answer_template.json`：输出 JSON 的规范化结构、枚举、金额精度、日期格式和排序规则。

## 任务定义和场景匹配

解题者扮演 court clerk，在 2026-11-12 庭审后关闭两个 Oregon traffic violation matters。需要把本地庭审记录与 Court Operations Portal 中的 citation、fee schedule、payment policy、form metadata 对齐，选择当前有效的 standard fine tier，每个 citation 只加一次 Jefferson County surcharge，排除没有依据的附加费用，计算 post-disposition payment plan，并输出结构化 closeout 字段。

该任务符合本组场景，因为它复用了法院书记员的核心工作流：庭审记录决定 disposition，财务金额来自有效日期内的 schedule/policy，最终输出必须避免 stale 或 unsupported charges，同时保留本地表格字段和引用规则。

## 材料用途

`<TASK_ENV_BASE_URL>/api/citations` 或 `/api/search` 用于查找目标 citation 事实和系统记录。`/api/fee-schedules` 提供当前 Jefferson County standard fine 和 stale 2022 high-speed row。`/api/payment-policies` 提供 extended payment plan policy，包括没有自动 account fee。`/api/forms` 提供 22nd Judicial District plan form metadata。本地 form excerpt 给出表格实际可见标签：`Case # / Account #`、`Case/Account Balance`、`Action Table(s) / Notes`、`TERMS of PAYMENT`，并说明没有单独 case/account number 时使用 citation number。

## 答案和评估依据

`OR26-TR-1188` 的 Sarah Benton 对 ORS 811.109(5) no contest，violation found，速度 103/65。当前有效 fee row 是 `F-OR22-100-2024`，standard fine 为 $1,150；Jefferson County surcharge 为 $5；amount due 为 $1,155。付款计划为 post-disposition extended payment plan，每月 $50，首期 2026-12-15，23 个完整 $50 付款加最后 $5，共 24 期，最后到期日 2028-11-15。

`OR26-TR-1194` 的 Jonah Merritt 对 ORS 811.109 no contest，violation found，速度 91/55，属于 31-to-40-over tier。当前有效 fee row 是 `F-OR22-31-2024`，standard fine 为 $440；Jefferson County surcharge 为 $5；amount due 为 $445。付款计划为每月 $55，首期 2026-12-15，8 个完整 $55 付款加最后 $5，共 9 期，最后到期日 2027-08-15。

应排除的项目包括 stale 2022 high-speed standard fine、statutory maximum substitution、late-payment fee、collection fee、DMV fee、returned-check fee、account-management fee 和 traffic-school fee。这些项目没有当前 schedule/policy 或 hearing note 支持。

评估器包含 8 个 whole-point scoring checks，原始权重如下：

- `SP001` 权重 2：目标 citation 集合，以及 no-contest、violation-found、post-disposition closeout。
- `SP002` 权重 2：`OR26-TR-1188` 的当前 standard fine tier 和来源。
- `SP003` 权重 2：`OR26-TR-1194` 的当前 standard fine tier 和来源。
- `SP004` 权重 2：每个 citation 的 $5 Jefferson surcharge、每项 amount due 和 $1,600 batch total。
- `SP005` 权重 2：approved extended payment-plan terms、monthly payment、first due date 和 no down payment。
- `SP006` 权重 3：installment counts、final partial payments、total installments 和 final due dates。
- `SP007` 权重 2：form id/label、准确本地标签，以及 citation number 作为 account reference。
- `SP008` 权重 2：排除 stale/unsupported charges，且 included unsupported amount 为 0。

这些检查覆盖至少四类不同业务结果：matter disposition、fine tier selection、surcharge/balance calculation、payment-plan terms、installment arithmetic、form/account-reference handling、unsupported-charge exclusion。每个点都是确定性的全得或不得分。

常见错误包括使用 stale $1,000 high-speed row，把 statutory maximum 当成 standard fine，漏掉 Jefferson County surcharge，加入 late/account/collection 等没有依据的费用，把 agreement 当成 pre-disposition，捏造 separate account number，或没有保留 $5 final remainder。

## 迁移设计

作为 train task，本任务让 fewshot skill builder 可以从输入和标准答案中推断真实业务习惯：使用当前有效 standard fine schedule，不使用 stale 或 maximum 数字；只加入当前政策支持的 county surcharge；排除没有触发条件的 late、collection、DMV、returned-check、account charges；payment plan 是 post-disposition；完整期数加最后余款要精确计算；本地表格标签和 citation-number account reference 要按材料使用，不要捏造标识。

## 构建记录

作者：Codex task-builder subagent for `train_002`。
创建日期：2026-07-18。
更新日期：2026-07-18。
主要变更：创建了 Oregon 22nd Judicial District traffic violation closeout/payment-plan task 的完整任务目录、本地 payload、answer template、standard answer、evaluator 和 bilingual notes。
