# train_004 Notes

## English

Data/source lineage: This task belongs to `task_group_005`, the shared ERP finance scenario covering claims, AP bills, payments, close logs, compliance objects, prepaids, vendors, and GL balances. It uses generated environment data from `task_group/task_group_005/env/data/claims.json`, `bills.json`, `payments.json`, and `close_logs.json`, plus the task-local stale export `input/payloads/stale_ap_snapshot.csv`. The assigned brief is an expense-to-AP conference reimbursement batch with a stale AP export and a late or partial payment.

Task definition: The solver sees five candidate claim IDs and a stale AP snapshot, then must use the current shared ERP API data to decide which claims can stay in the conference reimbursement AP batch. The expected output is the JSON shape in `answer_template.json`: eligible claim IDs, not-ready claim IDs, AP balances by claim, stale snapshot correction enums, close-log requirement, and batch status.

Scenario fit: This is a finance operations reconciliation task in the same distribution as the task group: source records disagree, AP exports can be stale, and the correct decision depends on coordinating expense claim state, AP bill state, payment state, and close-log context. The task intentionally includes one approved unpaid/in-flight reimbursement (`CLM-2025-OPS-017`) and one paid reimbursement with partial support cleanup (`CLM-2025-FIN-042`).

Material map: The local snapshot is solver-visible context only. `claims.json` establishes approval, paid, receipt, policy, and support states. `bills.json` supplies current AP bill status, bill amount, bill vendor, account, and void/scheduled/paid states. `payments.json` supplies cleared versus processing or scheduled payment evidence. `close_logs.json` identifies the AP close log affected by late April AP changes.

Solution and evaluation basis: `CLM-2025-FIN-042` is eligible for the batch close view because the matched current bill is `AP-2025-0068`, paid for 2675.00 by cleared payment `PAY-2025-0048`; the stale `AP-2025-0079` row has the wrong amount/vendor and should be replaced. `CLM-2025-OPS-017` is eligible but has an open AP balance of 1842.36 because `PAY-2025-0037` is processing, not cleared; its late payment state must update the stale snapshot. `CLM-2025-0080` is not ready because the linked AP bill amount/vendor do not reconcile to the claim, so its balance is treated as 0.00 for this reimbursement batch until corrected. `CLM-2025-0038` is not ready because the AP bill is void and the claim has partial receipt/over-limit support. `CLM-2025-0015` is not ready because the current claim is not approved despite the stale snapshot. The AP close log requiring attention is `CLOSE-2025-04-009`; the batch status is `needs_ap_refresh`.

Scoring goals: 8 exact-match points are used: eligible claim set (weight 2), not-ready claim set (2), balances for eligible claims (2), balances for not-ready claims (2), stale corrections for eligible claims (2), stale corrections for not-ready claims (2), close-log required flag and IDs (2), and batch status (1). Numeric balances are normalized to cents. Lists are sorted before scoring.

Transfer design: As a train task, this should teach through answer comparison that local AP exports are not authoritative, void bills and mismatched bill amount/vendor links should not be treated as open reimbursement AP, and payment status matters: cleared payments reduce AP balance, while processing or scheduled payments do not. It also reinforces close-log awareness when late AP activity occurs after a close log. These habits transfer to later tasks involving stale ERP extracts, source precedence, and structured finance status decisions.

Likely model pitfalls: A model may copy the stale snapshot, count the scheduled `AP-2025-0079` row for `CLM-2025-FIN-042`, reduce balance for a processing payment, treat a void AP bill as open AP, or accept an unapproved claim because the snapshot says approved.

Construction record: Created by Codex task-builder subagent for `train_004` on 2026-06-01. Files written only under `task_group/task_group_005/train_tasks/004/`.

## 中文

数据来源：本任务属于 `task_group_005` 共享 ERP 财务场景，环境包含报销申请、AP 账单、付款、关账日志、合规对象、预付、供应商和总账余额。本任务使用环境中的 `claims.json`、`bills.json`、`payments.json`、`close_logs.json`，以及任务本地的过期导出 `input/payloads/stale_ap_snapshot.csv`。任务简述是会议报销从 Expense 到 AP 的批处理，包含过期 AP 导出和迟到/部分付款。

任务定义：求解者看到五个候选 claim ID 和一份过期 AP 快照，需要使用当前共享 ERP API 数据判断哪些申请可以保留在会议报销 AP 批次中。输出字段包括 eligible claim、not-ready claim、按 claim 的 AP 余额、快照修正枚举、是否需要关账日志处理以及批次状态。

场景契合：这是典型财务运营对账任务：来源记录冲突、AP 导出可能过期，正确结论依赖 Expense 申请状态、AP 账单状态、付款状态和关账日志的协同判断。任务中特意包含一个已批准但付款仍在途的报销 `CLM-2025-OPS-017`，以及一个已付款但有部分支持清理痕迹的报销 `CLM-2025-FIN-042`。

材料说明：本地快照只是求解者可见的上下文，不是权威来源。`claims.json` 提供审批、付款、收据、政策标记和支持状态；`bills.json` 提供当前 AP 账单状态、金额、供应商、科目以及 void/scheduled/paid 状态；`payments.json` 提供 cleared、processing、scheduled 等付款证据；`close_logs.json` 用于识别受到四月迟到 AP 变更影响的关账日志。

答案和评分依据：`CLM-2025-FIN-042` 应保留在批次关账视角中，因为当前匹配账单是已付款的 `AP-2025-0068`，金额 2675.00，并由 cleared 付款 `PAY-2025-0048` 支付；过期快照里的 `AP-2025-0079` 金额和供应商不匹配，应替换。`CLM-2025-OPS-017` 可保留，但因 `PAY-2025-0037` 是 processing 而非 cleared，AP 余额仍为 1842.36。`CLM-2025-0080` 因 AP 账单金额/供应商与 claim 不匹配而不 ready，本批次余额按 0.00 处理。`CLM-2025-0038` 因 AP 账单已 void 且存在 partial receipt/over-limit 支持问题而不 ready。`CLM-2025-0015` 当前 claim 未批准，不应因过期快照显示 approved 而进入批次。需要关注的 AP 关账日志是 `CLOSE-2025-04-009`，批次状态为 `needs_ap_refresh`。

评分点：共 8 个精确匹配评分点：eligible claim 集合（权重 2）、not-ready claim 集合（2）、eligible claim 余额（2）、not-ready claim 余额（2）、eligible claim 的快照修正（2）、not-ready claim 的快照修正（2）、close log required 标志和 ID（2）、batch status（1）。金额按美分归一化，列表排序后评分。

迁移设计：作为训练任务，本任务通过答案对比让模型学到：本地 AP 导出不是权威来源；void 账单、金额/供应商不匹配的 AP 链接不能直接视为报销开放 AP；付款状态很关键，cleared 才减少余额，processing 或 scheduled 不减少余额；迟到 AP 活动需要关注关账日志。这些经验可迁移到后续使用过期 ERP 摘要、来源优先级和结构化财务状态判断的任务。

常见陷阱：模型可能直接复制过期快照，把 `CLM-2025-FIN-042` 的 scheduled 旧账单计入余额，用 processing 付款抵减余额，把 void 账单当作开放 AP，或因为快照显示 approved 而接受当前未批准的 claim。

构造记录：由 Codex task-builder subagent 于 2026-06-01 为 `train_004` 创建。所有文件仅写入 `task_group/task_group_005/train_tasks/004/`。
