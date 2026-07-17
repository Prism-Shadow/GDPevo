# test_001 Notes

## English

Data/source lineage: This task belongs to `task_group_005`, the shared ERP finance environment for close operations over claims, AP bills, payments, vendors, compliance, prepaids, GL balances, and close logs. The task uses generated environment data exposed through the shared API specified in `scratch/env_blueprint.md`. The solver-visible input is only `input/prompt.txt` plus `input/payloads/answer_template.json`.

Task definition: The solver must prepare an April 2025 reimbursement close decision for six candidate claim IDs across four employees: Avery Lee, Cameron Price, Riley Morgan, and Jordan Patel. The expected JSON separates approved-unpaid claims from blocked claims and already-paid claims, totals the approved-unpaid payable amount, identifies claims safe to mark closed downstream, assigns controlled exception reasons, and sets the batch status.

Scenario fit: The task exercises the reimbursement/AP close family in the group. It requires reconciling claim lifecycle state with AP bill and payment state, handling duplicate/noisy flags, and not trusting one stale-looking source row when another AP/payment record gives the effective state.

Material map: `claims.json` provides claim amount, employee, category, approval, receipt, policy flag, and lifecycle status. `bills.json` provides AP bill linkage and status for the claim IDs, including the duplicate/stale AP snapshot around `CLM-2025-FIN-042`. `payments.json` confirms cleared or in-process payments for linked AP bills. `close_logs.json` gives general April close context but is not the source of the claim-level answer.

Solution and evaluation basis: `CLM-2025-0085` and `CLM-2025-OPS-017` are approved and unpaid as of the April close decision, so they are payable; their amounts are 1398.54 and 1842.36, totaling 3240.90. `CLM-2025-0011` is submitted but not approved. `CLM-2025-0064` is submitted with missing receipt support and duplicate noise, so the controlled blocking reason is missing receipt. `CLM-2025-0032` is already paid. `CLM-2025-FIN-042` is already paid after reconciling the paid claim-linked AP bill and cleared payment despite a duplicate/stale AP snapshot and duplicate policy flag. The paid claims are also the `crm_close_claim_ids`. The batch can proceed for payable claims while retaining blocks, so `batch_status` is `ready_to_pay_with_blocks`.

Scoring points: 8 exact-match points are used. `payable_claim_ids` weight 3; `blocked_claim_ids` weight 2; `paid_claim_ids` weight 2; `ap_open_balance_total` weight 2; `crm_close_claim_ids` weight 1; payable/paid exception reasons weight 3; blocked exception reasons weight 2; `batch_status` weight 1. Total raw weight is 16.

Transfer design: This test maps to the reimbursement close and stale-source reconciliation habits intended to be learned from `train_001` and `train_004`. The transferable skill is to derive effective claim disposition by combining claim status, approval/receipt facts, AP bill status, and payment status instead of copying a single noisy field. `train_001` anchors approved/unpaid versus blocked reimbursement decisions, while `train_004` anchors duplicate or stale snapshot handling across AP/payment records. This test changes the employees, claim mix, April period, and output schema, and adds a partial-support/processing-noise pattern.

Likely model pitfalls: treating all April-submitted travel claims as payable; excluding `CLM-2025-FIN-042` only because of duplicate flags; treating an in-process payment on `CLM-2025-OPS-017` as already paid for April close; adding non-candidate IDs from environment search; or using free-form exception text instead of the controlled enums.

Construction record: Created by task-builder subagent for `task_group_005` `test_001` on 2026-06-01. The construction uses only task-local files under `task_group/task_group_005/test_tasks/001/`.

## Chinese

数据来源：本任务属于 `task_group_005`，共享环境是 ERP 财务关账系统，包含报销、AP 账单、付款、供应商、合规、预付、总账余额和关账日志。任务使用通过 `scratch/env_blueprint.md` 中共享 API 暴露的生成数据。求解者可见材料只有 `input/prompt.txt` 和 `input/payloads/answer_template.json`。

任务定义：求解者需要为 2025 年 4 月的报销关账批次做决策。候选数据包含 4 名员工的 6 个 claim。标准输出需要区分已批准未支付、阻塞、已支付的 claim，计算待支付金额，给出可在下游关闭的 claim，分配受控异常原因，并确定批次状态。

场景适配：该任务属于报销与 AP 关账工作流。它要求把 claim 生命周期、AP 账单状态、付款状态放在一起核对，并处理重复标记、缺失票据、旧快照冲突等噪声，不能只相信单一字段。

材料映射：`claims.json` 提供 claim 金额、员工、类别、审批、票据、政策标记和状态。`bills.json` 提供 claim 与 AP 账单的关联及状态，其中 `CLM-2025-FIN-042` 存在重复/旧快照冲突。`payments.json` 用来确认相关 AP 账单是否已经清算或仍在处理中。`close_logs.json` 提供 4 月关账背景，但不是 claim 级答案的直接依据。

解答依据：`CLM-2025-0085` 和 `CLM-2025-OPS-017` 在 4 月关账时已批准且未支付，因此进入 payable，金额分别为 1398.54 和 1842.36，总额为 3240.90。`CLM-2025-0011` 只是 submitted，尚未 approved。`CLM-2025-0064` 为 submitted 且票据缺失，并带有重复噪声，因此阻塞原因为 missing receipt。`CLM-2025-0032` 已支付。`CLM-2025-FIN-042` 虽有重复标记和旧 AP 快照，但关联的 AP 账单和付款证明其已支付。已支付的两个 claim 也是可在下游关闭的 claim。批次状态为 `ready_to_pay_with_blocks`。

评分设计：共 8 个精确匹配评分点。`payable_claim_ids` 权重 3；`blocked_claim_ids` 权重 2；`paid_claim_ids` 权重 2；`ap_open_balance_total` 权重 2；`crm_close_claim_ids` 权重 1；payable/paid 的异常原因权重 3；blocked 的异常原因权重 2；`batch_status` 权重 1。总原始权重为 16。

迁移设计：本测试映射到 `train_001` 和 `train_004` 中应学习到的报销关账与旧快照冲突处理经验。可迁移能力是综合 claim 状态、审批/票据事实、AP 账单状态和付款状态来判断有效业务状态，而不是复制单一噪声字段。`train_001` 锚定 approved/unpaid 与 blocked 的报销决策，`train_004` 锚定 AP/付款记录中的重复或旧快照处理。本测试更换了员工、claim 组合、4 月期间和输出结构，并增加了 partial support 与 processing payment 的噪声。

常见错误：把所有 4 月提交的 travel claim 都当成可支付；因为 duplicate 标记而排除 `CLM-2025-FIN-042`；把 `CLM-2025-OPS-017` 的处理中付款误判为 4 月已支付；从环境中加入非候选 claim；或使用自由文本异常原因而不是受控枚举。

构造记录：由 `task_group_005` 的 `test_001` task-builder subagent 于 2026-06-01 创建。构造仅写入 `task_group/task_group_005/test_tasks/001/` 下的任务本地文件。
