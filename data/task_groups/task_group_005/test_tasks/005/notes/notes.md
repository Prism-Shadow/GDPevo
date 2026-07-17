# test_005 Notes - Controller Exception Report

## English

Data/source lineage: This hidden note documents `test_005` for `task_group_005`, the shared ERP finance scenario covering claims, AP bills, payments, prepaids, GL balances, and close reporting. This task aligns to the factory guides, `scratch/task_group_design.md`, `scratch/env_blueprint.md`, the generated environment data, and the existing transfer anchors in `train_003` and `train_004`. Solver-visible inputs are `input/prompt.txt`, `input/payloads/month_end_exception_scope.json`, and `input/payloads/answer_template.json`.

Task definition: The business request is an April 2025 controller exception report that combines two recurring close-work families. The reimbursement side uses candidate claim IDs from the payload and the current claims, AP bills, and payment records. The prepaid side uses accounts 1250 and 1251 for the March 2025 prepaid variance period, because the GL export in the environment has the March prepaid balances used by the current close review. The expected output is a compact structured report: readiness enum, exception IDs, type enums, materiality enums, owner queues, priority ranking, and signed net close impact.

Scenario fit: This task belongs to the group because it forces coordination across the same finance objects and source-precedence habits as the train tasks. The solver must avoid treating stale or irrelevant AP rows as authoritative, must distinguish cleared from processing payment state, and must roll prepaid schedule-vs-GL differences into a controller-level decision. It is not a one-file transformation; correct results require using mixed AP/claim and prepaid/GL records in the shared environment.

Material map: `month_end_exception_scope.json` fixes the close period, prepaid variance period, entity, reimbursement candidate claims, prepaid accounts, materiality thresholds, ID convention, and ranking rule. `/claims` supplies claim approval and paid states. `/api/ap/bills` supplies current bill amount, status, account, and claim linkage. `/api/ap/payments` supplies cleared versus processing payment evidence. `/prepaids/invoices` supplies prepaid invoice records and monthly amortization. `/gl/balances` supplies GL ending balances for accounts 1250 and 1251.

Solution and evaluation basis: The included reimbursement exceptions are `CLM-2025-0085` and `CLM-2025-OPS-017`. Both are approved reimbursement exposures that remain unreconciled at close: `CLM-2025-0085` has no current AP bill/payment settlement and therefore contributes its claim amount of 1398.54; `CLM-2025-OPS-017` has bill `AP-2025-REIM-017` for 1842.36, but payment `PAY-2025-0037` is processing rather than cleared, so the open close impact remains 1842.36. `CLM-2025-FIN-042` is excluded because its matched bill `AP-2025-0068` is fully paid by cleared payment `PAY-2025-0048`; stale scheduled row `AP-2025-0079` should not create a new controller exception. `CLM-2025-0011` and `CLM-2025-0064` are not included as reimbursement exposure exceptions because they are blocked claims rather than approved unreconciled reimbursement exposure.

The prepaid exceptions are account-level IDs `PREPAID-1250` and `PREPAID-1251`. From the prepaid schedule and March GL balances, account 1250 has schedule-minus-GL variance -290855.05 and account 1251 has variance 79342.94. Both exceed the high materiality threshold. Reimbursement exceptions are low materiality under the payload thresholds. AP owns the reimbursement exceptions; accounting owns prepaid variance exceptions. The impact direction is `decrease_asset` for `PREPAID-1250` and `increase_asset` for `PREPAID-1251`. Priority order by absolute impact is `PREPAID-1250`, `PREPAID-1251`, `CLM-2025-OPS-017`, `CLM-2025-0085`. Net close impact is -290855.05 + 79342.94 + 1842.36 + 1398.54 = -208271.21. Any exception makes `close_readiness` equal `not_ready`.

The evaluator uses ten exact-match scoring points: close readiness (weight 1), exception ID set (2), exception type mapping (2), materiality mapping (2), owner queue mapping (2), top-priority ranking (2), signed close impact by exception (3), impact direction by exception (3), net close impact total (3), and reimbursement exception detail consistency (1). Lists are normalized only where the answer template says they are unordered/ascending; the priority list is order-sensitive. Currency values round to cents.

Transfer design: The prepaid half maps directly to `train_003`, which anchors account-level schedule-vs-GL variance, variance sign, use of source monthly amortization, and treatment of accounts 1250/1251 as close reconciliation accounts. The reimbursement half maps to `train_004`, which anchors current ERP source precedence over stale AP context, cleared-only payment reduction, and the habit of excluding void, mismatched, unapproved, or blocked claim states from open reimbursement AP exposure. The test changes the output surface by requiring a controller rollup, materiality buckets, owner routing, ranking, and a signed combined impact rather than the train tasks' detailed schedule or AP batch outputs.

Likely model pitfalls: A solver may include blocked claims as controller exceptions, count the stale scheduled AP row for `CLM-2025-FIN-042`, reduce `CLM-2025-OPS-017` by a processing payment, reverse the prepaid variance sign, use April GL balances instead of the March prepaid variance period, or rank by signed amount instead of absolute impact.

Construction record: Created by Codex task-builder subagent for `test_005` on 2026-06-01. Files were written only under `task_group/task_group_005/test_tasks/005/`.

## 中文

数据来源：本隐藏说明记录 `task_group_005` 的 `test_005`。该任务属于共享 ERP 财务场景，涉及报销 claim、AP 账单、付款、预付费用、总账余额和关账报告。本任务依据工厂指南、`scratch/task_group_design.md`、`scratch/env_blueprint.md`、已生成的环境数据，以及 `train_003` 和 `train_004` 的迁移锚点构建。求解器可见输入为 `input/prompt.txt`、`input/payloads/month_end_exception_scope.json` 和 `input/payloads/answer_template.json`。

任务定义：业务请求是为 2025 年 4 月关账准备 controller 异常报告，合并两类反复出现的关账工作：未清报销敞口和预付费用对总账差异。报销部分使用 payload 中的候选 claim ID，并查询当前 claim、AP bill 和 payment 记录。预付部分使用 1250 和 1251 两个科目，差异期间为 2025 年 3 月，因为环境中的总账导出提供了本次关账复核所需的 3 月预付余额。输出是结构化报告，包括关账准备状态、异常 ID、异常类型、重要性、归属队列、优先级排序和带符号的净关账影响。

场景契合：本任务要求在同一组财务对象之间进行协调，并复用训练任务中的来源优先级经验。求解器需要避免把过期或无关 AP 行当作权威记录，需要区分 cleared 和 processing 的付款状态，还需要把预付台账与总账差异汇总到 controller 层面的判断中。这不是单文件转换任务；正确结果依赖共享环境中的 AP/claim 和 prepaid/GL 混合记录。

材料说明：`month_end_exception_scope.json` 固定关账期间、预付差异期间、实体、候选报销 claim、预付科目、重要性阈值、异常 ID 规则和排序规则。`/claims` 提供 claim 审批和付款状态；`/api/ap/bills` 提供当前 AP 账单金额、状态、科目和 claim 链接；`/api/ap/payments` 提供 cleared 与 processing 等付款证据；`/prepaids/invoices` 提供预付发票和月摊销；`/gl/balances` 提供 1250 和 1251 的总账期末余额。

答案和评分依据：报销异常为 `CLM-2025-0085` 和 `CLM-2025-OPS-017`。两者都是已批准但在关账时仍未清的报销敞口：`CLM-2025-0085` 没有当前 AP 账单或付款结清证据，因此使用 claim 金额 1398.54；`CLM-2025-OPS-017` 有账单 `AP-2025-REIM-017`，金额 1842.36，但付款 `PAY-2025-0037` 仍为 processing，不是 cleared，因此未清影响仍为 1842.36。`CLM-2025-FIN-042` 被排除，因为匹配账单 `AP-2025-0068` 已由 cleared 付款 `PAY-2025-0048` 全额支付；过期的 scheduled 行 `AP-2025-0079` 不应形成新的 controller 异常。`CLM-2025-0011` 和 `CLM-2025-0064` 是 blocked claim，不属于已批准未清报销敞口。

预付异常使用科目级 ID：`PREPAID-1250` 和 `PREPAID-1251`。根据预付台账和 3 月总账余额，1250 的台账减总账差异为 -290855.05，1251 的差异为 79342.94，二者均超过 high 重要性阈值。报销异常按阈值为 low。AP 队列负责报销异常，accounting 队列负责预付差异。`PREPAID-1250` 的影响方向为 `decrease_asset`，`PREPAID-1251` 的影响方向为 `increase_asset`。按绝对影响金额排序的优先级为 `PREPAID-1250`、`PREPAID-1251`、`CLM-2025-OPS-017`、`CLM-2025-0085`。净关账影响为 -290855.05 + 79342.94 + 1842.36 + 1398.54 = -208271.21。只要存在异常，`close_readiness` 就是 `not_ready`。

评估器包含 10 个精确匹配评分点：关账准备状态（权重 1）、异常 ID 集合（2）、异常类型映射（2）、重要性映射（2）、归属队列映射（2）、优先级排序（2）、逐异常带符号关账影响（3）、逐异常影响方向（3）、净关账影响总额（3），以及报销异常细节一致性（1）。只有模板要求升序或集合语义的列表会被归一化；优先级列表保持顺序敏感。金额按美分比较。

迁移设计：预付部分锚定 `train_003`，迁移内容包括科目级台账对总账差异、差异符号、使用源记录中的月摊销金额，以及把 1250/1251 作为关账核对科目的习惯。报销部分锚定 `train_004`，迁移内容包括当前 ERP 数据优先于过期 AP 上下文、只有 cleared 付款才减少 AP 敞口，以及 void、金额/供应商不匹配、未批准或 blocked 的 claim 不应被当作开放报销 AP 敞口。测试任务改变了输出界面：它要求 controller 汇总、重要性分桶、责任队列、排序和带符号综合影响，而不是训练任务中的详细台账或 AP 批次输出。

常见陷阱：模型可能把 blocked claim 纳入 controller 异常，错误计入 `CLM-2025-FIN-042` 的过期 scheduled AP 行，用 processing 付款抵减 `CLM-2025-OPS-017`，反转预付差异符号，使用 4 月总账余额而不是 3 月预付差异期间，或者按带符号金额而不是绝对影响排序。

构建记录：由 Codex task-builder subagent 于 2026-06-01 为 `test_005` 创建。所有文件仅写入 `task_group/task_group_005/test_tasks/005/`。
