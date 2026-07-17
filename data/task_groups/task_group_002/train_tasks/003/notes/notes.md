# train_003 Hidden Notes

## English

### Data lineage and task definition

This task belongs to `task_group_002`, scenario `SCN_002_crm_b2b_quote_account_response`, and is anchored most directly in source example `E003` plus the milestone engagement response family described in `task_factory/scratch/task_group_design.md`. It uses the shared MedBridge Sales Ops API described in `task_factory/scratch/env_blueprint.md`; no task-local business data payload is provided other than `input/payloads/answer_template.json`.

The solver-visible prompt asks for an account-ready reconciliation for Helios Health Alliance using opportunity `OPP-TR-HELIOS`, customer `CUST-HELIOS`, and contact Mara Okafor. The expected work is to pull CRM opportunity/customer/contact records, invoice and payment records, revenue journal records, event records, and voucher records from the shared API, then return the structured JSON required by the template.

### Scenario fit and material map

This is a CRM/account-management reconciliation workflow rather than a quote calculation. It connects the won opportunity, phased milestone invoices, payment state, revenue recognition, and customer engagement event into account follow-up tasks. The relevant shared API entry points are `/api/opportunities`, `/api/customers`, `/api/invoices`, `/api/payments`, `/api/revenue-journals`, `/api/events`, `/api/vouchers`, `/api/policies`, and `/api/search?q=Helios`.

`input/prompt.txt` provides the realistic account request and target IDs without exposing the final amounts or task due dates. `input/payloads/answer_template.json` defines the exact output shape, money precision, dates, stable IDs, and controlled enum values. `output/answer.json` records the canonical reconciliation. `eval/eval.py` implements exact-match scoring for the eight business results; `eval/eval.sh` is the entry point and accepts an optional candidate path.

### Solution and evaluation basis

Canonical facts: opportunity `OPP-TR-HELIOS` for customer `CUST-HELIOS` / Helios Health Alliance is stage `WON` with amount `120000.00`. Milestone `MS1` totals `50000.00`, is paid, has `50000.00` paid and `0.00` unpaid, and has revenue recognized. Milestone `MS2` totals `70000.00`, is unpaid, has due date `2026-07-10`, and creates the outstanding balance of `70000.00`. Revenue recognition status is `COMPLETE_FOR_PAID_MILESTONES`, recognized milestones are `["MS1"]`, missing required milestones are empty, and recognized amount is `50000.00`.

The event facts are `EVT-HELIOS-CELEBRATION` on `2026-07-22`, voucher `HELIOSVIP100`, discount value `100.00`, and max uses `4`. The collection follow-up task is due `2026-07-10`, tied to `MS2`, amount due `70000.00`, contact Mara Okafor, customer `CUST-HELIOS`, opportunity `OPP-TR-HELIOS`, and action `COLLECT_UNPAID_MILESTONE`. The invitation follow-up task is due `2026-07-01`, tied to the same customer/opportunity/contact plus the event and voucher, and action `SEND_EVENT_INVITATION`.

Scoring points and raw weights: CRM opportunity total/stage (2), milestone invoice totals (2), paid/unpaid balance (3), revenue recognition entry status (2), event/voucher facts (2), collection task fields (2), invite task fields (1), contact linkage (1). The evaluator normalizes by total raw weight `15`. Currency comparisons are cent-tolerant. Lists are normalized by stable IDs where applicable. Free-form wording is not scored except controlled task titles are present but not required by the evaluator.

Likely pitfalls include treating the won opportunity as complete and missing the unpaid second milestone, recognizing revenue for an unpaid milestone, summing only paid invoices instead of all milestone invoices, omitting the event/voucher from CRM tasks, or linking the task to the customer but not the opportunity/contact.

### Transfer design

As a train task, this should teach reusable conventions for the milestone engagement family: opportunity value should match the sum of milestone invoice totals; collection work follows unpaid or due milestones, not paid milestones; revenue recognition is separate from payment receipt and applies to completed paid milestones; customer engagement events and vouchers must feed CRM invitation tasks; and account follow-ups need stable linkage to customer, opportunity, and contact. These conventions transfer to later milestone reconciliation test tasks without making them simple copies, because those tasks vary phase counts, overdue states, missing journals, and event/voucher conditions.

### Construction record

Author: Codex main agent. Created: 2026-06-01. Updated: 2026-06-01. Major changes: created the train_003 prompt, answer template, canonical answer, bilingual notes, and exact-match evaluator within the assigned write scope.

## 中文

### 数据来源与任务定义

本任务属于 `task_group_002`，来源场景为 `SCN_002_crm_b2b_quote_account_response`，主要承接源示例 `E003` 的 milestone engagement response 业务线，也符合 `task_factory/scratch/task_group_design.md` 中对 `train_003` 的设计。任务使用 `task_factory/scratch/env_blueprint.md` 描述的共享 MedBridge Sales Ops API；除 `input/payloads/answer_template.json` 之外，没有额外的任务本地业务数据。

对求解器可见的 prompt 要求针对 Helios Health Alliance 做账户核对，目标记录为 opportunity `OPP-TR-HELIOS`、customer `CUST-HELIOS`，联系人 Mara Okafor。预期求解流程是从共享 API 查询 CRM 商机、客户、联系人、invoice、payment、revenue journal、event 和 voucher 记录，再按模板返回结构化 JSON。

### 场景适配与材料地图

这是 CRM / account management 的 milestone reconciliation 工作流，不是报价计算。它把已赢单商机、分阶段账单、收款状态、收入确认和客户活动连接成后续 CRM 任务。相关共享 API 入口包括 `/api/opportunities`、`/api/customers`、`/api/invoices`、`/api/payments`、`/api/revenue-journals`、`/api/events`、`/api/vouchers`、`/api/policies` 和 `/api/search?q=Helios`。

`input/prompt.txt` 提供真实业务请求和目标 ID，但不直接暴露最终金额和任务截止日期。`input/payloads/answer_template.json` 定义精确输出结构、金额精度、日期、稳定 ID 和受控枚举。`output/answer.json` 是标准答案。`eval/eval.py` 对八个关键业务结果做精确匹配评分；`eval/eval.sh` 是入口脚本，并支持可选候选答案路径。

### 答案与评测依据

标准事实：`OPP-TR-HELIOS` 属于 `CUST-HELIOS` / Helios Health Alliance，stage 为 `WON`，金额为 `120000.00`。Milestone `MS1` 总额 `50000.00`，已付款，已付 `50000.00`，未付 `0.00`，并已收入确认。Milestone `MS2` 总额 `70000.00`，未付款，due date 为 `2026-07-10`，因此 outstanding balance 为 `70000.00`。收入确认状态为 `COMPLETE_FOR_PAID_MILESTONES`，已确认 milestone 为 `["MS1"]`，缺失的必需确认为空，已确认金额为 `50000.00`。

活动信息为 `EVT-HELIOS-CELEBRATION`，日期 `2026-07-22`，voucher `HELIOSVIP100`，discount value `100.00`，max uses `4`。collection task 截止日期为 `2026-07-10`，关联 `MS2`，amount due `70000.00`，联系人 Mara Okafor，客户 `CUST-HELIOS`，商机 `OPP-TR-HELIOS`，动作为 `COLLECT_UNPAID_MILESTONE`。invitation task 截止日期为 `2026-07-01`，关联同一客户、商机、联系人、活动和 voucher，动作为 `SEND_EVENT_INVITATION`。

评分点和原始权重：CRM opportunity total/stage (2)，milestone invoice totals (2)，paid/unpaid balance (3)，revenue recognition entry status (2)，event/voucher facts (2)，collection task fields (2)，invite task fields (1)，contact linkage (1)。总原始权重为 `15`，最终得分按比例归一化。金额按美分容差比较，列表按稳定 ID 归一化；自由文本不作为独立评分点。

常见错误包括：把 won opportunity 当作全流程结束而漏掉第二阶段未收款；对未付款 milestone 也做收入确认；只汇总已付款 invoice 而不是全部 milestone invoice；CRM task 中漏掉 event/voucher；或者只关联客户而没有关联 opportunity 和 contact。

### 迁移设计

作为 train task，本任务应让求解器总结 milestone engagement 类任务的可迁移规则：opportunity 金额应等于 milestone invoice 总和；collection 动作来自未付或到期的 milestone，而不是已付款阶段；收入确认和收款是不同控制点，已完成且已付款的 milestone 需要收入确认；客户活动和 voucher 要进入 CRM invitation task；后续任务需要稳定关联 customer、opportunity 和 contact。这些经验会迁移到后续 milestone reconciliation 测试任务，但测试任务会改变阶段数量、逾期状态、缺失 journal 和活动/voucher 条件，因此不会变成简单复制。

### 构造记录

作者：Codex main agent。创建日期：2026-06-01。更新日期：2026-06-01。主要变更：在指定写入范围内创建 `train_003` 的 prompt、answer template、标准答案、双语 notes 和精确匹配 evaluator。
