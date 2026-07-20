# English Notes

## Data and Source Lineage

This is `test_002` for `task_group_018`, derived from scenario `SCN_018_court_clerk_disposition_orders_and_financial_entries`, with primary source-example affinity to `E002` (Oregon traffic payment-plan closeout). It uses shared environment target citations `OR27-TR-2201`, `OR27-TR-2208`, and `OR27-TR-2219`; jurisdiction `OR27-CLAT`; fee rows `F-OR27-100-2025`, `F-OR27-21-2025`, and `F-OR27-SUR-2025`; payment policy `POL-OR27-EPP`; and form catalog entry `OR_27JD_PLAN`.

Task-local solver-visible materials are:

- `input/payloads/clatsop_hearing_closeout_memo.md`: hearing dispositions, approved payment amounts, a dismissed high-speed matter, and unsupported fee/enhancement distractions.
- `input/payloads/clatsop_payment_form_excerpt.md`: 27th Judicial District form labels, citation-number account-reference rule, old setup-charge distraction, and duplicate-like citation sample references.
- `input/payloads/answer_template.json`: required JSON structure, enum values, currency/date precision, ordering rules, and nullable no-plan fields.

## Task Definition and Scenario Fit

The solver acts as a court clerk closing a March 24, 2027 Oregon traffic hearing batch for Clatsop County. The expected work is to reconcile local hearing notes with the Court Operations Portal, apply current standard fine tiers and the Clatsop surcharge only to payable violation-found matters, leave the dismissed matter with zero financial entry and no payment plan, calculate installment schedules, use the 27th Judicial District payment form conventions, and summarize batch totals.

This task fits the scenario because it is the same legal-office closeout workflow as the source examples: courtroom notes determine disposition posture, public CMS/environment records determine active schedules and policy/form metadata, and the final clerk output must avoid unsupported financial entries while preserving citation/account references.

## Material Map

The prompt directs solvers to `<TASK_ENV_BASE_URL>` and allowed endpoints: `/api/citations`, `/api/fee-schedules`, `/api/payment-policies`, `/api/forms`, and `/api/search`. The target citation rows confirm defendant names, speed facts, hearing dates, plea/disposition status, amount-due components, and stored plan facts. The fee schedule endpoint supplies the current Clatsop 100+ mph fine of $1,200, the current 21-to-30-over fine of $265, and the $10 Clatsop County surcharge. The payment policy confirms no down payment, no automatic account fee, and citation-number account reference handling. The form endpoint confirms `OR_27JD_PLAN`, while the local form excerpt supplies the visible labels used in the expected output.

The duplicate-like citation references in the local materials are deliberate distractions. `OR27-TR-2201A`, `OR27-TR-2208B`, `OR27-TR-2219-VOID`, `OR27-TR-2210`, and `OR27-TR-2291` are not target matters.

## Solution and Evaluation Basis

For `OR27-TR-2201`, Mina Patel entered a no-contest plea and was found in violation on 2027-03-24 for ORS 811.109(5), 104 mph in a 65 mph zone. Current fee row `F-OR27-100-2025` sets the standard fine at $1,200. Add the $10 Clatsop surcharge for an amount due of $1,210. The approved post-disposition plan is $110 monthly, no down payment, first due 2027-04-23. This produces 11 full payments, no partial remainder, 11 total installments, and final due date 2028-02-23.

For `OR27-TR-2208`, Victor Lane entered a guilty plea and was found in violation on 2027-03-24 for ORS 811.109, 81 mph in a 55 mph zone, the 21-to-30-over tier. Current fee row `F-OR27-21-2025` sets the standard fine at $265. Add the $10 Clatsop surcharge for an amount due of $275. The approved post-disposition plan is $55 monthly, no down payment, first due 2027-04-23. This produces 5 full payments, no partial remainder, 5 total installments, and final due date 2027-08-23.

For `OR27-TR-2219`, Leah Crane entered a not-guilty plea and the matter was dismissed by court. Even though the citation was high-speed and appears in the batch scratchpad, the final closeout has standard fine $0, surcharge $0, amount due $0, no agreement, no installments, and no payment form. The account reference remains the citation number for identification.

Batch totals are 3 matters, 2 payable matters, 1 dismissed matter, $1,465 combined standard fines, $20 combined surcharge, $1,485 combined amount due, 16 total installments scheduled, and $0 unsupported charges included.

The evaluator has 9 whole-point checks with raw weights:

- `SP001` weight 1: target citation set, identities, pleas/findings, disposition date, and agreement sequence.
- `SP002` weight 1: current standard fine tier/source/amount for `OR27-TR-2201`.
- `SP003` weight 1: current standard fine tier/source/amount for `OR27-TR-2208`.
- `SP004` weight 1: dismissed `OR27-TR-2219` has zero financial entry and no payment plan.
- `SP005` weight 1: Clatsop surcharge, payable matter balances, and financial batch totals.
- `SP006` weight 1: payment status/type, monthly amount, no down payment, and first due dates for payable matters.
- `SP007` weight 2: installment counts, final partial-remainder values, final due dates, and batch scheduled-installment count.
- `SP008` weight 3: 27th Judicial District form id/label, required labels, and citation-number account references.
- `SP009` weight 3: excludes unsupported work-zone, traffic-school, late, collection, DMV, returned-check, account-management, and copied-dismissal fine charges with zero unsupported charge total.

These checks span more than four distinct business outcomes: matter identification/disposition, fine-tier selection, dismissed-matter treatment, surcharge and balance calculation, payment-plan terms, date/installment arithmetic, form/account-reference handling, unsupported-charge exclusion, and batch aggregation. Each point is deterministic and all-or-nothing. The heavier checks focus on account-reference/form discipline and unsupported-charge exclusion, because those were the non-obvious transfer decisions not directly solved by the public citation rows.

Likely model pitfalls include treating the dismissed high-speed citation as payable, adding a work-zone multiplier, using the duplicate-like citation strings as account references, adding the old setup/account fee, omitting the Clatsop surcharge, using a 31-to-40 tier for `OR27-TR-2208`, or computing final due dates as if the first due date were month zero.

## Transfer Design

Transfer anchors:

- `train_002` is the direct Oregon traffic closeout anchor. It demonstrates use of current standard fine tiers, county surcharge, exclusion of unsupported traffic fees, post-disposition agreement sequencing, citation-number account references, and full-installment plus final-remainder arithmetic.
- `train_005` is a secondary payment-schedule anchor for installment count and final due date discipline across a different court-payment workflow.

Transfer-dependent scoring goals are `SP002`, `SP003`, `SP005`, `SP006`, `SP007`, `SP008`, and `SP009`. The solver benefits from inferring from `train_002` that current schedule rows control over scratchpad values, county surcharges are added only when a payable disposition exists, unsupported late/collection/DMV/account/traffic-school fees are excluded, payment plans are post-disposition, and citation numbers are used as account references when no separate account exists. The task-specific work is new: a different Oregon district and county, three target citations rather than two, a dismissed high-speed matter, 2025 Clatsop form labels, duplicate-like citation distractions, and batch totals.

The solver-visible prompt does not state the hidden SOP. It gives a realistic closeout assignment, materials, endpoints, and output requirements; the transfer knowledge must be inferred from solved train tasks and applied to the new facts.

## Construction Record

Author: Codex task-builder subagent for `test_002`.
Created: 2026-07-18.
Updated: 2026-07-18.
Major changes: created the complete task folder for an Oregon 27th Judicial District / Clatsop County traffic hearing batch, including local payloads, answer template, standard answer, deterministic evaluator, and bilingual notes; later calibration rework adjusted rubric weights while preserving the same scoring points and standard answer.

# 中文说明

## 数据和来源

本任务是 `task_group_018` 的 `test_002`，来自场景 `SCN_018_court_clerk_disposition_orders_and_financial_entries`，主要对应源示例 `E002` 的 Oregon traffic payment-plan closeout。任务使用共享环境中的目标 citation：`OR27-TR-2201`、`OR27-TR-2208` 和 `OR27-TR-2219`；辖区 `OR27-CLAT`；fee rows `F-OR27-100-2025`、`F-OR27-21-2025`、`F-OR27-SUR-2025`；payment policy `POL-OR27-EPP`；以及 form catalog 条目 `OR_27JD_PLAN`。

本地可见材料包括：

- `input/payloads/clatsop_hearing_closeout_memo.md`：庭审 disposition、批准的付款金额、一个 dismissed high-speed matter，以及无依据费用和 enhancement 干扰项。
- `input/payloads/clatsop_payment_form_excerpt.md`：27th Judicial District 表格标签、citation-number account-reference 规则、旧 setup charge 干扰项，以及类似重复 citation 的样例编号。
- `input/payloads/answer_template.json`：输出 JSON 结构、枚举、金额和日期精度、排序规则，以及 dismissed/no-plan 字段的 null 规则。

## 任务定义和场景匹配

解题者扮演 court clerk，处理 2027-03-24 Clatsop County traffic hearing batch。需要把本地庭审记录与 Court Operations Portal 对齐，选择当前有效的 standard fine tier，只对 payable violation-found matters 加 Clatsop surcharge，让 dismissed matter 保持零金额且无 payment plan，计算 installment schedule，使用 27th Judicial District 的 payment form 规则，并汇总 batch totals。

该任务符合本场景，因为它复用了法院书记员 closeout 工作流：庭审记录决定 disposition posture，CMS/environment 记录提供有效的 schedule、policy 和 form metadata，最终输出必须避免无依据的 financial entries，并保留正确的 citation/account references。

## 材料用途

prompt 指向 `<TASK_ENV_BASE_URL>` 和允许的端点：`/api/citations`、`/api/fee-schedules`、`/api/payment-policies`、`/api/forms`、`/api/search`。目标 citation rows 用于确认被告姓名、速度事实、庭审日期、plea/disposition、amount due 组成和付款计划事实。fee schedule 端点给出 Clatsop 当前 100+ mph fine 为 $1,200，21-to-30-over fine 为 $265，以及 $10 Clatsop County surcharge。payment policy 确认无 down payment、无自动 account fee，并使用 citation number 作为 account reference。form endpoint 确认 `OR_27JD_PLAN`，本地 form excerpt 给出期望输出中的可见标签。

本地材料中的类似重复 citation 是有意干扰。`OR27-TR-2201A`、`OR27-TR-2208B`、`OR27-TR-2219-VOID`、`OR27-TR-2210` 和 `OR27-TR-2291` 都不是目标事项。

## 答案和评估依据

`OR27-TR-2201` 的 Mina Patel 于 2027-03-24 no contest，violation found，违反 ORS 811.109(5)，104/65。当前 fee row `F-OR27-100-2025` 的 standard fine 是 $1,200；加 $10 Clatsop surcharge 后 amount due 为 $1,210。post-disposition 付款计划为每月 $110，无 down payment，首期 2027-04-23，共 11 个完整付款，无 partial remainder，最后到期日 2028-02-23。

`OR27-TR-2208` 的 Victor Lane 于 2027-03-24 guilty，violation found，违反 ORS 811.109，81/55，属于 21-to-30-over tier。当前 fee row `F-OR27-21-2025` 的 standard fine 是 $265；加 $10 Clatsop surcharge 后 amount due 为 $275。post-disposition 付款计划为每月 $55，无 down payment，首期 2027-04-23，共 5 个完整付款，无 partial remainder，最后到期日 2027-08-23。

`OR27-TR-2219` 的 Leah Crane 为 not guilty，因 officer nonappearance 被 court dismissed。即使它是 high-speed citation 并出现在 batch scratchpad 中，最终 closeout 应为 standard fine $0、surcharge $0、amount due $0、无 agreement、无 installments、无 payment form。account reference 仍用 citation number 作为识别信息。

Batch totals 为 3 个 matters，2 个 payable matters，1 个 dismissed matter，combined standard fines $1,465，combined surcharge $20，combined amount due $1,485，scheduled installments 总数 16，unsupported charges included 为 $0。

评估器包含 9 个 whole-point checks，原始权重如下：

- `SP001` 权重 1：目标 citation 集合、身份、plea/finding、disposition date 和 agreement sequence。
- `SP002` 权重 1：`OR27-TR-2201` 的当前 standard fine tier/source/amount。
- `SP003` 权重 1：`OR27-TR-2208` 的当前 standard fine tier/source/amount。
- `SP004` 权重 1：dismissed `OR27-TR-2219` 为零 financial entry 且无 payment plan。
- `SP005` 权重 1：Clatsop surcharge、payable matter balances 和 financial batch totals。
- `SP006` 权重 1：payable matters 的 payment status/type、monthly amount、no down payment 和 first due dates。
- `SP007` 权重 2：installment counts、final partial-remainder values、final due dates 和 batch scheduled-installment count。
- `SP008` 权重 3：27th Judicial District form id/label、required labels 和 citation-number account references。
- `SP009` 权重 3：排除 work-zone、traffic-school、late、collection、DMV、returned-check、account-management 和 copied-dismissal fine charges，且 unsupported charge total 为零。

这些检查覆盖超过四类不同业务结果：matter identification/disposition、fine-tier selection、dismissed-matter treatment、surcharge and balance calculation、payment-plan terms、date/installment arithmetic、form/account-reference handling、unsupported-charge exclusion 和 batch aggregation。每个检查都是确定性的全得或不得分。较高权重集中在 account-reference/form discipline 和 unsupported-charge exclusion，因为这些是 public citation rows 不能直接给出的非显然迁移决策。

常见错误包括把 dismissed high-speed citation 当作 payable，加入 work-zone multiplier，使用类似重复 citation 字符串作为 account references，加入旧 setup/account fee，漏掉 Clatsop surcharge，把 `OR27-TR-2208` 当作 31-to-40 tier，或把首期日期当作第零个月来计算 final due dates。

## 迁移设计

迁移锚点：

- `train_002` 是直接的 Oregon traffic closeout 锚点。它展示了当前 standard fine tier、county surcharge、排除 unsupported traffic fees、post-disposition agreement sequencing、citation-number account references，以及完整期数加 final remainder 的计算习惯。
- `train_005` 是次要的 payment-schedule 锚点，用于跨不同法院付款工作流迁移 installment count 和 final due date 纪律。

依赖迁移的评分点是 `SP002`、`SP003`、`SP005`、`SP006`、`SP007`、`SP008` 和 `SP009`。解题者需要从 `train_002` 推断：当前有效 schedule rows 优先于 scratchpad 数字；只有 payable disposition 才加 county surcharge；late/collection/DMV/account/traffic-school 等没有触发条件的费用要排除；payment plans 是 post-disposition；没有单独 account 时使用 citation number。任务自身的新难点包括：新的 Oregon district 和 county、三个目标 citations、一个 dismissed high-speed matter、2025 Clatsop form labels、类似重复 citation 干扰项，以及 batch totals。

solver-visible prompt 没有写出隐藏 SOP。它只提供真实 closeout 请求、材料、端点和输出要求；迁移知识需要从已解 train tasks 中推断并应用到新事实。

## 构建记录

作者：Codex task-builder subagent for `test_002`。
创建日期：2026-07-18。
更新日期：2026-07-18。
主要变更：创建了 Oregon 27th Judicial District / Clatsop County traffic hearing batch 的完整任务目录，包括本地 payload、answer template、standard answer、确定性 evaluator 和 bilingual notes；后续 calibration rework 调整了 rubric weights，但保留相同 scoring points 和 standard answer。
