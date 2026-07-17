# train_005 Notes

## English

This task belongs to source scenario `SCN_002_crm_b2b_quote_account_response`, using the milestone-client-engagement workflow derived from source example `E003` and the `task_group_002` design brief. It is a train task for the account-response family, focused on reconciling a won implementation opportunity, milestone invoices, payments, revenue recognition, and a related customer event/voucher. Solver-visible materials are `input/prompt.txt` and `input/payloads/answer_template.json`; the expected evidence comes from the shared MedBridge Sales Ops API described in `task_factory/scratch/env_blueprint.md`.

The business case is `OPP-TR-MERIDIAN` for `CUST-MERIDIAN` / Meridian Public Health, with Daniel Rees as the contact. The opportunity is won for USD 100,000.00 and should reconcile to three milestone phases: `MS1` USD 30,000.00, `MS2` USD 45,000.00, and `MS3` USD 25,000.00. `MS1` is paid and recognized, `MS2` is paid but missing the revenue journal, and `MS3` is unpaid with due date 2026-07-15, which is not yet due on the 2026-06-01 task date. The briefing event is `EVT-MERIDIAN-BRIEFING`; voucher `MERIDIANBRIEF50` is active for a USD 50.00 discount and 20 maximum uses.

The output schema has three top-level objects: `engagement_reconciliation`, `invoice_actions`, and `event_actions`. The answer records the phase sum, paid amount, outstanding balance, per-phase invoice/payment/recognition statuses, the required primary accounting action `RECORD_REVENUE_MS2`, the MS3 collection action `MONITOR_UNPAID_NOT_DUE`, and the invite action `SEND_BRIEFING_INVITE`. Revenue recognition is intentionally separate from cash receipt: the paid MS2 milestone still needs a deferred-revenue release journal, debiting `DEFERRED_REVENUE` and crediting `IMPLEMENTATION_SERVICES_REVENUE` for USD 45,000.00.

The evaluator has eight exact-match scoring points with raw weights matching the design brief: opportunity equals phases (2), invoice/payment states (3), outstanding balance (3), revenue recognition missing/present status (2), event/voucher state (2), CRM action routing (2), deferred revenue account action (1), and contact linkage (1). Currency is compared at cent precision; enums and IDs are normalized for casing and whitespace. Likely pitfalls include treating paid MS2 as fully reconciled despite the missing revenue journal, sending a collection notice for MS3 before its due date, omitting the contact from CRM tasks, or treating the voucher discount as a percent rather than a USD amount.

As a train task, this should help solvers infer reusable conventions for later engagement-reconciliation tasks: the opportunity amount must equal the service milestone total, payment and revenue recognition are different controls, paid completed milestones need recognition checks, unpaid future milestones should be monitored rather than escalated as overdue, and event/voucher follow-up belongs in CRM task routing with the account contact.

Construction record: authored by Codex on 2026-06-01, updated on 2026-06-01. Initial construction created the prompt, answer template, standard answer, evaluator, and bilingual notes for task-builder assignment `train_005`.

## 中文

本任务属于源场景 `SCN_002_crm_b2b_quote_account_response`，采用源示例 `E003` 中的里程碑客户互动工作流，并遵循 `task_group_002` 的设计说明。这是账户响应类的训练任务，核心是核对已赢得的实施机会、里程碑发票、付款、收入确认，以及相关客户活动和优惠券。求解器可见材料是 `input/prompt.txt` 和 `input/payloads/answer_template.json`；关键证据应来自 `task_factory/scratch/env_blueprint.md` 所描述的共享 MedBridge Sales Ops API。

业务对象是 `CUST-MERIDIAN` / Meridian Public Health 的机会 `OPP-TR-MERIDIAN`，联系人为 Daniel Rees。该机会已赢单，金额为 100,000.00 美元，应与三个里程碑阶段一致：`MS1` 为 30,000.00 美元，`MS2` 为 45,000.00 美元，`MS3` 为 25,000.00 美元。`MS1` 已付款且已确认收入，`MS2` 已付款但缺少收入分录，`MS3` 尚未付款，到期日为 2026-07-15，相对于任务日期 2026-06-01 尚未到期。简报活动为 `EVT-MERIDIAN-BRIEFING`；优惠券 `MERIDIANBRIEF50` 处于有效状态，折扣为 50.00 美元，最多使用 20 次。

输出结构包含三个顶层对象：`engagement_reconciliation`、`invoice_actions` 和 `event_actions`。标准答案记录阶段合计、已付款金额、未结余额、各阶段的发票/付款/收入确认状态，以及必须执行的主会计动作 `RECORD_REVENUE_MS2`、针对 MS3 的收款动作 `MONITOR_UNPAID_NOT_DUE`、邀请动作 `SEND_BRIEFING_INVITE`。收入确认与收款是两个独立控制点：MS2 虽然已经收款，但仍需要释放递延收入的分录，即借记 `DEFERRED_REVENUE`、贷记 `IMPLEMENTATION_SERVICES_REVENUE`，金额为 45,000.00 美元。

评估器包含八个精确匹配评分点，原始权重与设计说明一致：机会金额等于阶段合计（2）、发票和付款状态（3）、未结余额（3）、收入确认缺失/存在状态（2）、活动和优惠券状态（2）、CRM 动作路由（2）、递延收入会计动作（1）、联系人关联（1）。货币按分比较；枚举和 ID 会做大小写与空白规范化。常见错误包括把已付款的 MS2 误认为完全核对完毕、在 MS3 未到期前发送催收通知、CRM 任务遗漏联系人，或把优惠券折扣误解为百分比而不是美元金额。

作为训练任务，本任务帮助求解器归纳后续同类账户核对任务的可迁移规则：机会金额必须等于服务里程碑总额，付款和收入确认是不同控制，已付款且已完成的里程碑需要检查收入确认，尚未到期的未付款里程碑应监控而不是升级为逾期催收，活动/优惠券后续动作需要路由到 CRM 任务并关联账户联系人。

构建记录：Codex 于 2026-06-01 编写，并于 2026-06-01 更新。初始构建完成了任务构建器分配 `train_005` 所需的提示、答案模板、标准答案、评估器和双语说明。
