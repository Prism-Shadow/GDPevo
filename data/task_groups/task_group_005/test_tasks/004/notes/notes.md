# test_004 Notes - Payment Release Board

## English

This test task belongs to `task_group_005`, the shared ERP finance and compliance environment. The task brief is a payment release board combining employee reimbursement and vendor compliance gates. It uses the shared generated environment under `task_group/task_group_005/env/`, especially AP bills, payments, claims, vendors, and compliance objects, plus the task-local payload `input/payloads/release_board_batch.json`.

Visible solver inputs are `input/prompt.txt`, `input/payloads/release_board_batch.json`, and `input/payloads/answer_template.json`. The prompt names five AP bill IDs: `AP-2025-0010`, `AP-2025-0041`, `AP-2025-0065`, `AP-2025-0106`, and `AP-2025-REIM-017`. The local payload also names the expected board business IDs: `BUS-2025-0011`, `BUS-2025-0018`, `BUS-2025-0023`, `BUS-2025-0041`, and `BUS-2025-0058`. The review date is `2025-06-01`.

The task fits the scenario because a finance operator must coordinate AP state, reimbursement claim state, payment state, vendor master identity, and compliance profile state before releasing a payment run. It is not a single-table lookup: the solver must join `bill_id` to `claim_id` when present, confirm no cleared payment has already settled the item, map `vendor_id` to `business_id`, and apply the entity gate consistently across vendor invoices and reimbursement clearing bills.

Material map: `/api/ap/bills` provides candidate bill amounts, statuses, due dates, claim links, and vendor IDs. `/api/ap/payments` distinguishes cleared payments from processing records. `/api/claims/{claim_id}` or `/api/claims` provides claim approval and receipt state for reimbursement-linked bills. `/api/compliance/objects` or profile endpoints provide bank, risk, license, PEP, sanctions, missing field, and tax facts. `/api/vendors` can verify vendor identities but is not the final compliance source.

Solution basis: `AP-2025-0010` releases because it is an approved vendor bill for `BUS-2025-0018`; the business has verified bank, clear screening, no PEP, no missing fields, active license on `2025-06-01`, and risk score below the override threshold. `AP-2025-0106` releases because it is a scheduled vendor bill for `BUS-2025-0011`; the compliance profile is also releaseable even though the review status is not a release decision by itself. `AP-2025-0041` holds for compliance escalation because `BUS-2025-0041` has bank `name_mismatch`, possible PEP, malformed tax ID, and expired license. `AP-2025-REIM-017` has a valid reimbursement/AP match for `CLM-2025-OPS-017`, but its mapped business `BUS-2025-0058` has possible PEP and expired/missing license evidence, so it holds for compliance escalation. `AP-2025-0065` holds first on the AP/claim gate because it is linked to `CLM-2025-0006`, whose claim state is only `submitted` and whose amount does not support the AP bill; its business `BUS-2025-0023` is also compliance-blocked by expired license, missing address, and risk score `74`.

The standard answer releases `AP-2025-0010` and `AP-2025-0106`, holds the other three bills, marks compliance-blocked businesses as `BUS-2025-0023`, `BUS-2025-0041`, and `BUS-2025-0058`, ranks released bills by due date as `AP-2025-0106` then `AP-2025-0010`, and totals released AP balance to USD `40210.43`.

Evaluation has eight exact-match scoring points with raw weights totaling 18, covering the requested business result fields: release bill set with released reason tags (3), hold bill set (2), claim-gate hold reason for `AP-2025-0065` (2), compliance hold reasons for `AP-2025-0041` and `AP-2025-REIM-017` (3), compliance-blocked business set (3), priority ranking (2), released AP total to cents (2), and board status enum (1). Lists are normalized as sorted sets except `payment_priority_ranking`, which must preserve order. Numeric comparison is rounded to two decimals.

Transfer design: this test maps directly to `train_001` and `train_005`. From `train_001`, the solver should transfer the habit of reconstructing reimbursement/AP/payment state instead of trusting one bill or claim field: matching amounts, claim approval, receipt state, and processing-versus-cleared payments matter. From `train_005`, the solver should transfer entity-gate judgment: compliance profile is authoritative, PEP and sanctions concerns escalate, license is compared to the stated review date, bank `name_mismatch` is distinct from other bank states, placeholder or malformed tax IDs are invalid, and risk score around or above the learned threshold blocks release. The new difficulty is the integrated board: the task combines vendor invoices and employee reimbursements in one release output and asks for payment priority plus a released-balance total.

Likely pitfalls include releasing `AP-2025-REIM-017` from AP state alone, ignoring compliance on reimbursement clearing vendors, treating `review_status` as the final decision, releasing `AP-2025-0065` because the bill itself is approved, including processing payments as cleared settlements, sorting the priority list lexicographically instead of by due date, or omitting `BUS-2025-0023` from compliance-blocked IDs because its bill already fails the claim gate.

Construction record: created by the task-builder subagent for `test_004` on 2026-06-01. Files were written only under `task_group/task_group_005/test_tasks/004/`. The task aligns to `scratch/task_group_design.md` and `scratch/env_blueprint.md`; shared environment JSON was inspected to determine the hidden standard answer.

## Chinese

本测试任务属于 `task_group_005`，共享环境是 ERP 财务与合规审查环境。任务简述是构建一个付款放行看板，把员工报销清算账单和供应商合规闸口合并判断。任务使用共享环境 `task_group/task_group_005/env/` 中的生成数据，主要包括 AP bills、payments、claims、vendors 和 compliance objects，并使用本任务本地输入 `input/payloads/release_board_batch.json`。

求解器可见输入包括 `input/prompt.txt`、`input/payloads/release_board_batch.json` 和 `input/payloads/answer_template.json`。Prompt 给出五个 AP bill：`AP-2025-0010`、`AP-2025-0041`、`AP-2025-0065`、`AP-2025-0106`、`AP-2025-REIM-017`。本地 payload 还给出看板涉及的业务主体：`BUS-2025-0011`、`BUS-2025-0018`、`BUS-2025-0023`、`BUS-2025-0041`、`BUS-2025-0058`。复核日期为 `2025-06-01`。

该任务符合本任务组场景，因为财务人员在放行付款批次前，需要同时协调 AP 状态、报销 claim 状态、付款状态、供应商主数据身份和合规档案状态。它不是单表查询：求解器需要在 bill 存在 `claim_id` 时关联 claim，确认没有 cleared payment 已经结清，按 `vendor_id` 映射到 `business_id`，并把同一套实体闸口一致应用于供应商发票和报销清算账单。

材料说明：`/api/ap/bills` 提供候选账单金额、状态、到期日、claim 链接和 vendor ID；`/api/ap/payments` 用于区分 cleared 付款和 processing 记录；`/api/claims/{claim_id}` 或 `/api/claims` 提供报销相关账单的审批和凭证状态；`/api/compliance/objects` 或 profile 端点提供银行、风险、许可证、PEP、制裁筛查、缺失字段和税号事实；`/api/vendors` 可用于确认供应商身份，但最终合规事实以 compliance profile 为准。

标准答案依据如下：`AP-2025-0010` 可以放行，因为它是 `BUS-2025-0018` 的 approved 供应商账单，该业务主体银行已验证、筛查清晰、无 PEP、无缺失字段、许可证在 `2025-06-01` 仍有效，且风险分低于覆盖阈值。`AP-2025-0106` 可以放行，因为它是 `BUS-2025-0011` 的 scheduled 供应商账单，合规档案同样满足放行条件；环境中的 `review_status` 本身不能直接当作放行结论。`AP-2025-0041` 因合规升级而暂缓，因为 `BUS-2025-0041` 存在银行 `name_mismatch`、possible PEP、税号格式异常和许可证过期。`AP-2025-REIM-017` 对 `CLM-2025-OPS-017` 来说 AP/报销匹配有效，但其映射业务主体 `BUS-2025-0058` 存在 possible PEP 以及许可证过期/缺失，因此因合规升级暂缓。`AP-2025-0065` 首先在 AP/claim 闸口暂缓，因为它关联的 `CLM-2025-0006` 仍只是 `submitted`，且 claim 金额不能支撑该 AP bill；其业务主体 `BUS-2025-0023` 也因许可证过期、地址缺失和风险分 `74` 被合规阻断。

标准输出放行 `AP-2025-0010` 和 `AP-2025-0106`，暂缓其余三个 bill；合规阻断业务主体为 `BUS-2025-0023`、`BUS-2025-0041`、`BUS-2025-0058`；按到期日排序的付款优先级为 `AP-2025-0106` 后 `AP-2025-0010`；放行 AP 金额合计为 USD `40210.43`。

评估器包含八个精确匹配评分点，原始权重总计 18，对应题目要求的业务结果字段：放行 bill 集合及其 released 原因标签 3 分、暂缓 bill 集合 2 分、`AP-2025-0065` 的 claim 闸口暂缓原因 2 分、`AP-2025-0041` 和 `AP-2025-REIM-017` 的合规暂缓原因 3 分、合规阻断 business 集合 3 分、付款优先级排序 2 分、放行 AP 总额到美分 2 分、看板状态枚举 1 分。除 `payment_priority_ranking` 必须保序外，列表按集合归一化比较；金额四舍五入到两位小数比较。

迁移设计：本测试任务明确锚定 `train_001` 和 `train_005`。从 `train_001`，求解器应迁移出重建报销/AP/付款有效状态的习惯，而不是只信一个 bill 或 claim 字段：金额匹配、claim 审批、凭证状态、processing 与 cleared payment 的区别都重要。从 `train_005`，求解器应迁移实体闸口判断：合规档案是权威来源，PEP 和制裁相关风险进入升级，许可证按指定复核日期判断，银行 `name_mismatch` 与其他银行状态要区分，占位或格式异常税号无效，风险分接近或超过训练中学到的阈值会阻断放行。新的难点是集成看板：任务把供应商发票和员工报销放在同一个放行输出里，并要求付款优先级和放行金额合计。

常见错误包括只根据 AP 状态放行 `AP-2025-REIM-017`，忽略报销清算供应商的合规状态，把 `review_status` 当作最终决策，因为 bill 本身 approved 而放行 `AP-2025-0065`，把 processing payment 当作已结清，按字典序而不是到期日排序优先级，或者因为 `AP-2025-0065` 已经在 claim 闸口失败而漏掉 `BUS-2025-0023` 的合规阻断。

构建记录：由 `test_004` task-builder subagent 于 2026-06-01 创建。文件仅写入 `task_group/task_group_005/test_tasks/004/`。本任务与 `scratch/task_group_design.md` 和 `scratch/env_blueprint.md` 一致；为确定隐藏标准答案检查了共享环境 JSON。
