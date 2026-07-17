# test_005 Notes

## English

This task belongs to source scenario `SCN_002_crm_b2b_quote_account_response` and the milestone engagement-response family in `task_group_002`. It is the fifth test task and asks solvers to audit a multi-phase NGO portal rollout using the shared MedBridge Sales Ops API plus the task-local account handoff. Solver-visible materials are `input/prompt.txt` and `input/payloads/answer_template.json`; the expected response is `output/answer.json`.

The business case is opportunity `OPP-TE-SUNRISE` for `CUST-SUNRISE` / Sunrise Relief Network, with Priya Raman as the routing contact for this audit. The opportunity is won for USD 120,000.00 and must equal the sum of three phases: `MS1` USD 40,000.00, `MS2` USD 35,000.00, and `MS3` USD 45,000.00. `MS1` is paid and recognized, `MS2` is paid but missing its revenue journal, and `MS3` is unpaid, not yet due on 2026-06-01, and due on 2026-07-01. The total paid amount is USD 75,000.00 and the outstanding balance is USD 45,000.00.

The required primary accounting action is `RECORD_REVENUE_MS2`, due on 2026-06-01, for USD 35,000.00. It should debit `DEFERRED_REVENUE` and credit `IMPLEMENTATION_SERVICES_REVENUE`. The collection action for `MS3` is `MONITOR_UNPAID_NOT_DUE`, not an overdue collection notice. The training event is `EVT-SUNRISE-TRAINING`, live on 2026-06-20, and voucher `SUNRISESTAFF100` has discount 100 and 25 maximum uses. The training invite task is due on 2026-06-10 and must link the customer, opportunity, contact, event, and voucher.

The evaluator has twelve scoring points with the requested raw weights: phase sum and opportunity total (2), paid/unpaid invoice state (3), missing revenue-recognition action (3), outstanding balance (2), training event/voucher facts (2), CRM follow-up task routing (2), collection versus accounting action enum (2), four reconciliation control conventions (3 each), and contact linkage (1). Currency is compared at cent precision. Enums and IDs are normalized for casing and whitespace, but the expected business decisions are exact.

Likely pitfalls include treating the paid `MS2` invoice as fully reconciled even though revenue recognition is missing, issuing a collection notice for `MS3` before it is due, omitting the 2026-06-10 training invite due date, confusing the accounting action with the collection action, or failing to carry Priya Raman through all CRM-linked tasks.

Construction record: authored by Codex on 2026-06-01 for task-builder assignment `test_005`. Initial construction created the prompt, answer template, standard answer, evaluator, and bilingual notes under the assigned write scope.

## 中文

本任务属于源场景 `SCN_002_crm_b2b_quote_account_response`，对应 `task_group_002` 中的里程碑客户互动响应类别。这是第五个测试任务，要求求解器结合共享的 MedBridge Sales Ops API 和任务本地账户交接信息，审计一个多阶段 NGO 门户上线项目。求解器可见材料是 `input/prompt.txt` 和 `input/payloads/answer_template.json`；标准响应是 `output/answer.json`。

业务对象是 `CUST-SUNRISE` / Sunrise Relief Network 的机会 `OPP-TE-SUNRISE`，本次审计的任务路由联系人为 Priya Raman。该机会已赢单，金额为 120,000.00 美元，应等于三个阶段合计：`MS1` 为 40,000.00 美元，`MS2` 为 35,000.00 美元，`MS3` 为 45,000.00 美元。`MS1` 已付款且已确认收入，`MS2` 已付款但缺少收入分录，`MS3` 尚未付款，在 2026-06-01 尚未到期，到期日为 2026-07-01。已付款总额为 75,000.00 美元，未结余额为 45,000.00 美元。

必须执行的主会计动作为 `RECORD_REVENUE_MS2`，到期日为 2026-06-01，金额为 35,000.00 美元。该动作应借记 `DEFERRED_REVENUE`，贷记 `IMPLEMENTATION_SERVICES_REVENUE`。针对 `MS3` 的收款动作是 `MONITOR_UNPAID_NOT_DUE`，不是逾期催收通知。培训活动为 `EVT-SUNRISE-TRAINING`，在 2026-06-20 处于 live 状态；优惠券 `SUNRISESTAFF100` 的折扣为 100，最多使用 25 次。培训邀请任务到期日为 2026-06-10，并且必须关联客户、机会、联系人、活动和优惠券。

评估器包含十二个评分点，原始权重与任务要求一致：阶段合计和机会总额（2）、已付款/未付款发票状态（3）、缺失收入确认动作（3）、未结余额（2）、培训活动和优惠券事实（2）、CRM 后续任务路由（2）、收款动作与会计动作枚举区分（2）、四个核对控制约定（每项 3）、联系人关联（1）。货币按分比较；枚举和 ID 会做大小写与空白规范化，但业务判断必须精确匹配。

常见错误包括把已付款的 `MS2` 误认为已经完全核对完毕、在 `MS3` 尚未到期时发出催收通知、遗漏 2026-06-10 的培训邀请到期日、混淆会计动作和收款动作，或没有在所有 CRM 任务中携带 Priya Raman。

构建记录：Codex 于 2026-06-01 为任务构建器分配 `test_005` 编写。初始构建已在指定写入范围内创建提示、答案模板、标准答案、评估器和双语说明。
