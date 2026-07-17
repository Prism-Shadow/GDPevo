# test_002 Notes

## English

### Data and Source Lineage

This task belongs to `task_group_018`, derived from scenario `SCN_018_court_clerk_disposition_orders_and_financial_entries`. It remains in the Jefferson traffic and payment-plan distribution, with direct transfer anchors in `train_002` and `train_005`.

The shared generated environment is `task_group/task_group_018/env/data/clerk_ops.json`, exposed through the clerk operations HTTP service. This rework edits only `task_group/task_group_018/test_tasks/002/`. Solver-visible materials are `input/prompt.txt`, `input/payloads/answer_template.json`, and `input/payloads/jefferson_afternoon_traffic_packet.json`. The environment supplies live citation identity and posture, Jefferson traffic fee schedules with 2023-2024 and 2025 effective rows, Jefferson payment policy, hearing records, and stale export records.

### Task Definition and Scenario Fit

The solver acts as a Jefferson County Municipal Court traffic clerk preparing batch `JEF-TV-2025-07-16-PM-CONTROL` for financial-entry review. The target citations are `CIT-JEF-2023-00701`, `CIT-JEF-2024-00701`, `CIT-JEF-2024-00702`, `CIT-JEF-2024-00703`, `CIT-JEF-2025-00127`, `CIT-JEF-2025-00138`, and `CIT-JEF-2025-00701`.

This version is a more substantial rework after direct v2 calibration. It adds a prior-order fee schedule row, current-order fee schedule rows, a satisfied no-assessment row, a deferred-completion no-new-assessment row, a dismissed identity-conflict row, a return-to-court plan defect, below-minimum/default plan corrections, and controlled `source_resolution`, `assessment_status`, `fee_schedule_bucket`, `decision_flags`, and `plan_defect_code` fields. These changes reduce points obtainable from simple API lookup plus arithmetic because the high-value fields require choosing which source controls before calculating amounts.

### Material Map

The local packet gives target citation numbers, current bench or review notes, one signed correction slip, raw speed facts, candidate import codes, installment request snippets, and an older history pull. It intentionally does not include fee amounts, payment policy minimums, default first-due intervals, live identity values, or the final source-precedence decisions.

The shared environment provides:

- `GET /api/citations/<citation_number>` for live defendant names, original violation codes, live plea and disposition values, and older due-date facts.
- `GET /api/fees?county=Jefferson&matter_type=traffic&effective_on=<date>` for active fee rows. Jefferson has `TR-BASE` `115.00`, `TR-SPEED` `50.00`, and `TR-SCHOOL` `45.00` for 2023-2024, and `TR-BASE` `130.00`, `TR-SPEED` `60.00`, `TR-SCHOOL` `50.00`, and `TR-LATE` `25.00` for 2025.
- `GET /api/payment-policies?county=Jefferson` for `40.00` minimum monthly payment, 30-day default first due date, final-smaller-payment permission, and unsupported codes `CR-507`, `DUI-104`, and `TR-231`.
- `GET /api/stale-exports?county=Jefferson&name=financial_ledger_snapshot` and hearing records for stale status and history conflicts.

### Solution and Evaluation Basis

All entries use the citation number as `account_reference`.

`CIT-JEF-2023-00701` uses live identity `Owen Ibarra` but the signed correction slip controls over the live old violation and stale history. The final plea is `no_contest`, disposition `convicted`, order date `2024-11-20`, assessment status `assessed_prior_order`, and violation code `TR-201` because 58 in a 45 zone is 13 mph over. The prior Jefferson traffic schedule applies: `TR-BASE` `115.00` plus `TR-SPEED` `50.00`, total `165.00`. Excluded candidates are `CR-507`, `TR-260`, and `TR-LATE`. No new installment plan is entered because the July item is a return-to-court review defect.

`CIT-JEF-2024-00701` uses the current bench row over live pending/deferred values. The final plea is `no_contest`, disposition `convicted`, date `2025-07-16`, code `TR-202` because 61 in a 35 zone is 26 mph over, and the current fee schedule applies. Components are `TR-BASE` `130.00` and `TR-SPEED` `60.00`, total `190.00`. Excluded candidates are `DUI-104`, `TR-231`, and `TR-LATE`. The requested `30.00` monthly amount is below policy, so the entered plan uses `40.00`, first due `2025-08-15`, four full payments, final `30.00`, five payments total, final due `2025-12-15`.

`CIT-JEF-2024-00702` uses live identity `Felix Abbott` and live `satisfied` posture over the stale return-to-court history pull. It is a no-assessment satisfied row. No violation or fee schedule is used; all candidates `TR-231`, `TR-BASE`, and `TR-LATE` are excluded, and no plan is entered.

`CIT-JEF-2024-00703` uses the current bench deferred-completion dismissal. The final plea remains `deferred_entry`, disposition is `dismissed`, date `2025-07-16`, and the entry is `no_new_assessment_deferred_completion`. All candidates `TR-BASE`, `TR-LATE`, and `TR-SCHOOL` are excluded, and no plan is entered. The older first-due date is not carried forward.

`CIT-JEF-2025-00127` uses the current bench result over the stale plan date while retaining the live violation `TR-231` as the violation posture. `TR-231` is not a supported fee component, so only `TR-BASE` `130.00` is assessed. Excluded candidates are `DUI-104`, `TR-231`, and `TR-LATE`. The requested `35.00` monthly amount and old `2025-05-05` due date are corrected to the Jefferson minimum/default plan: `40.00`, first due `2025-08-15`, three full payments, final `10.00`, four payments total, final due `2025-11-15`.

`CIT-JEF-2025-00138` uses live identity `Kara Lopaz` and live dismissal over the stale adjacent-row Kara Lopez plan. It is `no_assessment_dismissed`, with code `none`, no components, excluded candidates `TR-244`, `TR-BASE`, `TR-LATE`, and `TR-SCHOOL`, and no plan.

`CIT-JEF-2025-00701` uses the current bench plea over live `not_guilty` and stale `not_imported` status. The live violation `TR-244` remains the citation violation, but only current `TR-BASE` `130.00` is assessed. Excluded candidates are `TR-244`, `TR-LATE`, and `TR-SCHOOL`. The approved `55.00` plan uses the policy default first due `2025-08-15`, two full payments, final `20.00`, three payments total, final due `2025-10-15`.

Batch totals are `assessed_total` `615.00`, `prior_schedule_assessed_total` `165.00`, `current_schedule_assessed_total` `450.00`, `base_fine_total` `505.00`, `speed_surcharge_total` `110.00`, `traffic_school_total` `0.00`, `assessed_entry_count` `4`, `no_assessment_entry_count` `3`, `dismissed_no_assessment_count` `2`, `satisfied_no_assessment_count` `1`, `excluded_candidate_fee_count` `22`, `unsupported_policy_code_count` `6`, `entered_plan_principal_total` `450.00`, `total_full_payments` `9`, `total_final_payment_amount` `60.00`, `total_payment_count` `12`, `default_first_due_count` `3`, `below_minimum_plan_count` `2`, `return_to_court_review_count` `1`, `entries_using_prior_fee_schedule` `1`, `entries_using_current_fee_schedule` `3`, `entries_with_source_override_flags` `7`, and `all_entered_plans_use_post_disposition_start` `true`.

The evaluator has nine exact-match scoring points with raw weights: SP001 identity/order/header fields (2), SP002 source resolution, posture, dates, assessment status, and flags (3), SP003 violation code/source/speed tier (3), SP004 fee schedule buckets, components, effective starts, and entry totals (3), SP005 excluded candidate codes and unsupported-code aggregate (2), SP006 plan action, defect, monthly amount, first due date, and first-due basis (3), SP007 installment counts, final amounts, and final due dates (2), SP008 monetary batch aggregates (2), and SP009 operational batch aggregates (2).

Likely model pitfalls are using the July 2025 review date for every fee schedule, charging no-assessment rows, using stale names or return-to-court rows as current authority, carrying forward old due dates, adding unsupported candidate codes as fee components, accepting below-minimum monthly requests, entering a plan for the return-to-court defect, or calculating equal installments instead of final smaller payments.

### Transfer Design

This is a test task. `train_002` anchors the traffic workflow: reconcile live citations with hearing packets, select fees by county, matter type, code, and effective date, exclude unsupported candidate codes, and calculate installment schedules as full payments plus a final smaller payment. `train_005` anchors the review and precedence behavior: include only matters requiring action, reject stale queue or packet values when current/live evidence supersedes them, reset plan schedules only for approved current orders, preserve existing/defect treatment when no new plan is authorized, and route return-to-court defects differently from entered plans.

The strongest transfer-dependent points are SP002, SP004, SP006, SP007, SP008, and SP009. SP002 requires train-learned source precedence across live records, signed corrections, current bench rows, and stale history. SP004 requires the `train_002` effective-date fee habit. SP006 and SP007 require the policy minimum, default due date, return-to-court/no-plan distinctions, and final-remainder convention from both anchors. SP008 and SP009 require carrying those row decisions into rollups.

### Construction Record

Author: Codex task-builder subagent. Created: 2026-07-07. Updated: 2026-07-07. Major changes in this second rework: changed the batch id and output schema, expanded to seven Jefferson citation rows, added prior/current effective fee schedule selection, added signed-history precedence, added satisfied/dismissed/deferred-completion no-assessment rows, added return-to-court and default-plan defects, moved major decisions into controlled fields, rewrote the answer and evaluator, and kept the solver-visible prompt free of SOP steps.

## 中文

### 数据与来源

本任务属于 `task_group_018`，来源场景为 `SCN_018_court_clerk_disposition_orders_and_financial_entries`。任务仍保持在 Jefferson traffic 和 payment-plan 分布内，主要迁移锚点为 `train_002` 与 `train_005`。

共享生成环境是 `task_group/task_group_018/env/data/clerk_ops.json`，通过 clerk operations HTTP 服务暴露。本次重做只修改 `task_group/task_group_018/test_tasks/002/`。求解者可见材料包括 `input/prompt.txt`、`input/payloads/answer_template.json` 和 `input/payloads/jefferson_afternoon_traffic_packet.json`。环境提供 live citation 身份和状态、Jefferson traffic fee schedule 的 2023-2024 与 2025 生效行、Jefferson payment policy、hearing 记录和 stale export 记录。

### 任务定义与场景适配

求解者扮演 Jefferson County Municipal Court 的 traffic clerk，准备批次 `JEF-TV-2025-07-16-PM-CONTROL` 的 financial-entry review。目标 citations 为 `CIT-JEF-2023-00701`、`CIT-JEF-2024-00701`、`CIT-JEF-2024-00702`、`CIT-JEF-2024-00703`、`CIT-JEF-2025-00127`、`CIT-JEF-2025-00138` 和 `CIT-JEF-2025-00701`。

这是在 direct v2 calibration 后的第二次更大幅度重做。它加入 prior-order fee schedule、current-order fee schedule、satisfied no-assessment、deferred-completion no-new-assessment、dismissed identity conflict、return-to-court plan defect、低于政策下限的 default plan correction，以及受控字段 `source_resolution`、`assessment_status`、`fee_schedule_bucket`、`decision_flags` 和 `plan_defect_code`。这些变化降低了仅靠直接 API lookup 和算术即可得分的比例，因为高权重点必须先判断哪个来源控制最终录入。

### 材料地图

本地 packet 提供目标 citation、当前 bench/review note、一份 signed correction slip、原始速度事实、候选 import codes、installment request 片段和 older history pull。它故意不提供 fee amount、payment policy minimum、default first-due interval、live identity 或最终 source-precedence 判断。

共享环境提供：

- `GET /api/citations/<citation_number>`：live defendant name、原始 violation code、live plea/disposition 和旧 due-date 信息。
- `GET /api/fees?county=Jefferson&matter_type=traffic&effective_on=<date>`：生效 fee rows。Jefferson 在 2023-2024 年的 `TR-BASE` 为 `115.00`、`TR-SPEED` 为 `50.00`、`TR-SCHOOL` 为 `45.00`；2025 年的 `TR-BASE` 为 `130.00`、`TR-SPEED` 为 `60.00`、`TR-SCHOOL` 为 `50.00`、`TR-LATE` 为 `25.00`。
- `GET /api/payment-policies?county=Jefferson`：最低月付 `40.00`、首期默认为 order 后 30 天、允许 final smaller payment，以及 unsupported codes `CR-507`、`DUI-104`、`TR-231`。
- `GET /api/stale-exports?county=Jefferson&name=financial_ledger_snapshot` 和 hearing records：提供 stale status 与 history conflict。

### 标准答案与评测依据

所有记录都使用 citation number 作为 `account_reference`。

`CIT-JEF-2023-00701` 使用 live identity `Owen Ibarra`，但 signed correction slip 优先于 live 旧 violation 和 stale history。最终 plea 为 `no_contest`，disposition 为 `convicted`，order date 为 `2024-11-20`，assessment status 为 `assessed_prior_order`。58 mph/45 mph 是超速 13 mph，对应 `TR-201`。适用 prior Jefferson traffic schedule：`TR-BASE` `115.00` 加 `TR-SPEED` `50.00`，总额 `165.00`。排除 `CR-507`、`TR-260` 和 `TR-LATE`。7 月事项是 return-to-court review defect，不录入新 plan。

`CIT-JEF-2024-00701` 使用当前 bench row 覆盖 live pending/deferred 值。最终 plea 为 `no_contest`，disposition 为 `convicted`，日期 `2025-07-16`。61 mph/35 mph 是超速 26 mph，对应 `TR-202`，适用 current fee schedule。Components 为 `TR-BASE` `130.00` 和 `TR-SPEED` `60.00`，总额 `190.00`。排除 `DUI-104`、`TR-231` 和 `TR-LATE`。请求月付 `30.00` 低于政策下限，所以使用 `40.00`，首期 `2025-08-15`，四期完整付款，最后 `30.00`，共五期，最后到期 `2025-12-15`。

`CIT-JEF-2024-00702` 使用 live identity `Felix Abbott` 和 live `satisfied` 状态，覆盖 stale return-to-court history pull。该行是 no-assessment satisfied row，不使用 violation 或 fee schedule；候选 `TR-231`、`TR-BASE`、`TR-LATE` 全部排除，不录入 plan。

`CIT-JEF-2024-00703` 使用当前 bench 的 deferred-completion dismissal。plea 仍为 `deferred_entry`，disposition 为 `dismissed`，日期 `2025-07-16`，状态为 `no_new_assessment_deferred_completion`。排除候选 `TR-BASE`、`TR-LATE`、`TR-SCHOOL`，不录入 plan，旧 first-due date 不沿用。

`CIT-JEF-2025-00127` 使用当前 bench result 覆盖 stale plan date，同时保留 live violation `TR-231` 作为 violation posture。`TR-231` 不是支持的 fee component，所以只评估 `TR-BASE` `130.00`。排除 `DUI-104`、`TR-231` 和 `TR-LATE`。请求月付 `35.00` 和旧 `2025-05-05` due date 被修正为 Jefferson policy 的最低额和默认首期：`40.00`，首期 `2025-08-15`，三期完整付款，最后 `10.00`，共四期，最后到期 `2025-11-15`。

`CIT-JEF-2025-00138` 使用 live identity `Kara Lopaz` 和 live dismissal，覆盖 stale adjacent-row Kara Lopez plan。它是 `no_assessment_dismissed`，code 为 `none`，无 components，排除 `TR-244`、`TR-BASE`、`TR-LATE`、`TR-SCHOOL`，不录入 plan。

`CIT-JEF-2025-00701` 使用当前 bench plea 覆盖 live `not_guilty` 和 stale `not_imported` status。live violation `TR-244` 保留为 citation violation，但只评估 current `TR-BASE` `130.00`。排除 `TR-244`、`TR-LATE` 和 `TR-SCHOOL`。批准的 `55.00` plan 使用政策默认首期 `2025-08-15`，两期完整付款，最后 `20.00`，共三期，最后到期 `2025-10-15`。

Batch totals 为：`assessed_total` `615.00`，`prior_schedule_assessed_total` `165.00`，`current_schedule_assessed_total` `450.00`，`base_fine_total` `505.00`，`speed_surcharge_total` `110.00`，`traffic_school_total` `0.00`，`assessed_entry_count` `4`，`no_assessment_entry_count` `3`，`dismissed_no_assessment_count` `2`，`satisfied_no_assessment_count` `1`，`excluded_candidate_fee_count` `22`，`unsupported_policy_code_count` `6`，`entered_plan_principal_total` `450.00`，`total_full_payments` `9`，`total_final_payment_amount` `60.00`，`total_payment_count` `12`，`default_first_due_count` `3`，`below_minimum_plan_count` `2`，`return_to_court_review_count` `1`，`entries_using_prior_fee_schedule` `1`，`entries_using_current_fee_schedule` `3`，`entries_with_source_override_flags` `7`，`all_entered_plans_use_post_disposition_start` 为 `true`。

评测器包含 9 个 exact-match scoring points：SP001 身份、顺序和 header 字段（2）；SP002 source resolution、posture、日期、assessment status 和 flags（3）；SP003 violation code/source/speed tier（3）；SP004 fee schedule bucket、components、effective start 与 entry total（3）；SP005 excluded candidate codes 和 unsupported-code aggregate（2）；SP006 plan action、defect、monthly amount、first due date 和 first-due basis（3）；SP007 installment counts、final amounts 和 final due dates（2）；SP008 monetary batch aggregates（2）；SP009 operational batch aggregates（2）。

常见错误包括把 2025 年 7 月 review date 用到所有 fee schedule、对 no-assessment rows 收费、把 stale name 或 return-to-court row 当作当前权威、沿用旧 due date、把 unsupported candidate code 当作 fee component、接受低于政策下限的月付、对 return-to-court defect 录入 plan，或把分期都算成等额而不保留 final smaller payment。

### 迁移设计

这是测试任务。`train_002` 锚定 traffic 工作流：协调 live citation 与 hearing packet；按 county、matter type、code 和 effective date 选择 fee；排除 unsupported candidate codes；把 installment schedule 算为完整付款加最后较小尾款。`train_005` 锚定 review 与 precedence 行为：只纳入需要处理的 matter；当 current/live evidence 覆盖 stale queue 或 packet 值时拒绝 stale 值；只有经当前 order 批准的 plan 才重置 schedule；没有新 plan 授权时保留 defect/no-plan 处理；return-to-court defect 与 entered plan 要区别处理。

最强迁移依赖评分点是 SP002、SP004、SP006、SP007、SP008 和 SP009。SP002 需要从训练中学到的 source precedence，在 live record、signed correction、current bench row 和 stale history 之间选择。SP004 需要 `train_002` 的 effective-date fee 经验。SP006 和 SP007 需要从两个锚点迁移 policy minimum、default due date、return-to-court/no-plan 区分和 final-remainder convention。SP008 与 SP009 要把逐行判断正确汇总到 batch totals。

### 构造记录

作者：Codex task-builder subagent。创建日期：2026-07-07。更新日期：2026-07-07。第二次重做的主要变化：更改 batch id 和 output schema，扩展为七条 Jefferson citation，加入 prior/current effective fee schedule selection、signed-history precedence、satisfied/dismissed/deferred-completion no-assessment rows、return-to-court 和 default-plan defects，将主要判断移入 controlled fields，重写标准答案和 evaluator，并保持 solver-visible prompt 不泄露 SOP 步骤。
