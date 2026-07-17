# train_005 Notes - Wasco County Compliance Review After Sentencing

## English

### Data Lineage

This task belongs to `task_group_018`, sourced from `SCN_018_court_clerk_disposition_orders_and_financial_entries` and anchored in examples `E001`, `E002`, and `E003`. The shared environment is `task_group/task_group_018/env/`, especially `env/data/clerk_ops.json` exposed through the clerk operations HTTP API. The task-local solver-visible files are `input/prompt.txt`, `input/payloads/answer_template.json`, and `input/payloads/wasco_compliance_packet.json`.

The task brief in `scratch/task_group_design.md` defines `train_005` as a Wasco County compliance review after sentencing, covering restitution, community-service credit, ability-to-pay petitions, payment-plan due dates, live CMS/ledger data, and local packet evidence. The local packet was constructed from generated Wasco cases already present in the environment plus task-local post-sentencing notices.

### Task Definition and Scenario Fit

The solver acts as the Wasco compliance desk and prepares a structured JSON review for packet matters that require action. The visible prompt points the solver to `{ENV_BASE_URL}` and the local packet. The expected output is one JSON object with five included cases, corrected balances, compliance statuses, payment-plan details, next actions, and aggregate counts.

This fits the scenario because it mirrors court clerk post-disposition work: the clerk must reconcile a local review packet with live case records, stale queue records, financial obligations, payment policies, restitution notices, and community-service completion evidence. It exercises the same distribution as the source examples: official clerk records are not enough by themselves, local hearing or packet evidence changes some entries, and the final answer must be precise enough for financial and docket entry.

### Material Map

- `wasco_compliance_packet.json`: Provides the review date, which packet items are action matters, receipt-credit evidence, service-provider completion notices, restitution trust notes, and ability-to-pay petition outcomes.
- `GET /api/cases/<case_number>`: Provides matter type, sentence terms, community-service hours ordered, restitution ordered, case status, and live defendant/case facts.
- `GET /api/financial-obligations?case_number=<case_number>`: Provides live ledger balances, current payment-plan fields, paid amounts, order dates, and ledger status.
- `GET /api/payment-policies?county=Wasco`: Provides the 35-day first-due convention, minimum/maximum monthly payment values, and final-smaller-payment convention.
- `GET /api/stale-exports?county=Wasco&name=probation_review_queue`: Provides the queue source and stale carryover/distractor context.
- `GET /api/docket?case_number=<case_number>`: Provides review, filing, disposition, and return-to-court docket context.

### Solution and Evaluation Basis

Included cases are the five packet rows with `review_needed: true`: `23-WAS-00144`, `23-WAS-01002`, `24-WAS-00290`, `24-WAS-01001`, and `24-WAS-01003`. `23-WAS-01003` and `24-WAS-01002` are distractors because the packet marks them as informational/name-check rows only.

Key answer construction:

- `23-WAS-00144`: The live ledger shows `39.39` due, but the packet contains an unposted receipt for exactly `39.39`, so the corrected balance is `0.00`, status is `paid_after_credit`, and the action is `post_receipt_close`.
- `23-WAS-01002`: Live balance is `317.86`. The approved June 2, 2025 ability-to-pay petition changes the monthly payment to `75.00`. Wasco policy puts the first revised due date 35 days after June 2, so first due is `2025-07-07`; four full payments of `75.00` plus a final `17.86` payment make five installments with final due `2025-11-07`. Community service is complete.
- `24-WAS-00290`: Live balance is `245.86`, including open restitution. The packet has no signed revised plan, confirms no restitution disbursement, and reports only 4 of 10 community-service hours complete. The existing plan remains `60.00` monthly from the live next due date `2025-02-13`, leaving four full payments and a final `5.86`, with final due `2025-06-13`. Because the ledger is delinquent and restitution/service remain open, the next action is `issue_return_to_court_notice`.
- `24-WAS-01001`: The live plan is current with `32.51` remaining, a `35.00` monthly amount, and one final payment due on `2025-01-27`. There is no new financial petition, so the action is `continue_monitoring`.
- `24-WAS-01003`: The live ledger is paid, restitution is confirmed disbursed, but 64 of 80 service hours are verified, leaving 16 hours and a `community_service_followup` action.

The evaluator has eight exact-match scoring points:

| ID | Goal | Raw weight |
| --- | --- | --- |
| SP01 | Correct included matters, ordering, county, task id, review date, and count. | 2 |
| SP02 | Correct source-conflict and packet-exception codes for every included case. | 2 |
| SP03 | Correct live ledger balances, packet credits, corrected balances, and aggregate corrected balance. | 3 |
| SP04 | Correct revised ability-to-pay plan for `23-WAS-01002`. | 3 |
| SP05 | Correct remaining-plan treatment for `24-WAS-00290` and `24-WAS-01001`. | 2 |
| SP06 | Correct restitution status across all five included cases. | 2 |
| SP07 | Correct community-service status and remaining hours for affected cases. | 2 |
| SP08 | Correct financial status, next-action routing, return-to-court count, and receipt-credit closeout set. | 3 |

Likely model pitfalls include including packet distractors, accepting stale queue values over live ledger fields, ignoring the unposted receipt, recalculating a withdrawn petition as if it were approved, omitting final smaller payments, using the wrong first-due basis for the revised plan, and treating restitution as closed without the trust-account note.

### Transfer Design

As a train task, this should teach transferable experience without being a tutorial. After attempting the task and comparing to the answer, a skill-builder can infer that clerk work often requires live environment records plus local packet evidence, that stale exports can contain action rows and distractors, that approved petitions can reset payment-plan schedules while withdrawn petitions do not, that final smaller payments must be represented explicitly, and that unknown or absent compliance sources should not be invented. This anchors later test work involving financial exception ranking, plan defect calculations, source precedence, and action-code routing.

### Construction Record

Author: Codex task-builder subagent
Created: 2026-07-07
Updated: 2026-07-07
Major changes: Created the full `train_005` task folder with prompt, task-local packet, answer template, bilingual notes, standard answer, and exact-match evaluator.

## 中文

### 数据来源

本任务属于 `task_group_018`，来源场景为 `SCN_018_court_clerk_disposition_orders_and_financial_entries`，参考样例为 `E001`、`E002`、`E003`。共享环境位于 `task_group/task_group_018/env/`，核心数据是通过 clerk operations HTTP API 暴露的 `env/data/clerk_ops.json`。本任务本地可见材料包括 `input/prompt.txt`、`input/payloads/answer_template.json` 和 `input/payloads/wasco_compliance_packet.json`。

`scratch/task_group_design.md` 将 `train_005` 定义为 Wasco County 判后 compliance review，覆盖 restitution、community-service credit、ability-to-pay petition、payment-plan due date、CMS/ledger 现场数据和本地 packet 证据。本地 packet 使用环境中已有的 Wasco 案件，并补充了判后收据、服务机构和请愿材料。

### 任务定义与场景契合

求解者扮演 Wasco compliance desk，为需要处理的 packet matters 生成结构化 JSON。prompt 要求使用 `{ENV_BASE_URL}` 和本地 packet。标准输出包含五个纳入案件、修正余额、合规状态、付款计划、后续动作和汇总字段。

该任务符合场景，因为法院书记员在 disposition 后经常要把本地 review packet 与 live case record、stale queue、financial obligation、payment policy、restitution notice、community-service 证明相互核对。它与源样例保持同一类难点：单一官方记录不足以完成任务，本地听审或 packet 证据会改变部分录入，最终结果必须能用于财务和 docket entry。

### 材料地图

- `wasco_compliance_packet.json`：提供 review date、哪些 packet items 需要处理、未入账收据、服务完成证明、restitution trust note、ability-to-pay petition 结果。
- `GET /api/cases/<case_number>`：提供 matter type、sentence、community-service ordered hours、restitution ordered、case status 等 live case facts。
- `GET /api/financial-obligations?case_number=<case_number>`：提供 live ledger balance、当前 payment-plan 字段、已付金额、order date 和 ledger status。
- `GET /api/payment-policies?county=Wasco`：提供 35 天 first-due 规则、月付上下限和 final smaller payment 约定。
- `GET /api/stale-exports?county=Wasco&name=probation_review_queue`：提供 stale queue 和干扰项背景。
- `GET /api/docket?case_number=<case_number>`：提供 review、filing、disposition、return-to-court 等 docket 背景。

### 标准答案与评测依据

纳入案件是五个 `review_needed: true` 的 packet rows：`23-WAS-00144`、`23-WAS-01002`、`24-WAS-00290`、`24-WAS-01001`、`24-WAS-01003`。`23-WAS-01003` 和 `24-WAS-01002` 是干扰项，因为 packet 标为 informational/name-check。

关键答案逻辑如下：

- `23-WAS-00144`：live ledger 余额是 `39.39`，packet 中有相同金额的未入账 receipt，因此修正余额为 `0.00`，状态为 `paid_after_credit`，动作为 `post_receipt_close`。
- `23-WAS-01002`：live balance 为 `317.86`。2025-06-02 批准的 ability-to-pay petition 把月付改为 `75.00`。Wasco policy 要求首期在 order date 后 35 天，因此 first due 是 `2025-07-07`；四期 `75.00` 加最后一期 `17.86`，共五期，final due 为 `2025-11-07`。社区服务已完成。
- `24-WAS-00290`：live balance 为 `245.86`，restitution 仍未结清。packet 没有签署新的付款计划，确认无 restitution disbursement，并显示 10 小时中只完成 4 小时。继续使用 live plan 的 `60.00` 月付和 `2025-02-13` next due，剩余四期整额加最后 `5.86`，final due 为 `2025-06-13`。因 ledger delinquent 且 restitution/service 未完成，后续动作为 `issue_return_to_court_notice`。
- `24-WAS-01001`：live plan 当前为 current，剩余 `32.51`，月付 `35.00`，一笔尾款 due `2025-01-27`。没有新的财务 petition，因此动作为 `continue_monitoring`。
- `24-WAS-01003`：live ledger 已 paid，restitution 已 disbursed，但 80 小时中只验证 64 小时，剩余 16 小时，需 `community_service_followup`。

评测器包含八个 exact-match 评分点，raw weight 分别为 2、2、3、3、2、2、2、3。评分点覆盖纳入案件、source-conflict code、余额和汇总、批准的新付款计划、现有计划处理、restitution status、community service、financial status 和 next-action routing。

模型常见错误包括纳入干扰项、把 stale queue 当作 live record、忽略未入账 receipt、把 withdrawn petition 当作 approved petition、漏掉 final smaller payment、对 revised plan 使用错误 first-due 基准，以及没有 trust-account 证据就把 restitution 关闭。

### 迁移设计

作为训练任务，本任务不是教程，但求解后对照答案可以提炼出可迁移经验：clerk 工作需要同时使用 live environment records 和本地 packet 证据；stale exports 同时可能包含真实 action rows 和干扰项；approved petition 会重置付款计划，而 withdrawn petition 不会；final smaller payment 必须显式表示；缺失或未支持的合规信息不能发明。这些经验将支撑后续 test tasks 中的 financial exception ranking、plan defect calculation、source precedence 和 action-code routing。

### 构造记录

作者：Codex task-builder subagent
创建日期：2026-07-07
更新日期：2026-07-07
主要变更：创建完整 `train_005` task folder，包括 prompt、本地 packet、answer template、双语 notes、标准答案和 exact-match evaluator。
