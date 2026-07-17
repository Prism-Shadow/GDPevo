# train_001 Notes - Expense-to-AP Control

## English

This task belongs to `task_group_005`, a shared finance-operations environment for Northwind-style ERP work. The assigned brief is `train_001, Expense-to-AP control`: the solver receives a small reimbursement batch and must use the public API base URL, not hidden environment files, to classify claims for close readiness. The required claims are `CLM-2025-OPS-017`, `CLM-2025-FIN-042`, `CLM-2025-0090`, `CLM-2025-0080`, `CLM-2025-0038`, and `CLM-2025-0037`.

Visible inputs are `input/prompt.txt` and `input/payloads/answer_template.json`. The useful public API surfaces are `/api/claims/{claim_id}`, `/api/ap/bills`, and `/api/ap/payments` on `http://127.0.0.1:8005`. The task intentionally includes distractor AP records: `CLM-2025-FIN-042` has one valid paid AP bill and one unrelated scheduled AP bill; several other claims have AP bills whose amount, vendor, status, or existence does not support reimbursement release.

The solution basis is exact business-state reconstruction across claim, AP bill, and payment objects. `CLM-2025-OPS-017` is payable because it is approved with attached support and has a matching open reimbursement bill `AP-2025-REIM-017` for USD 1,842.36. `CLM-2025-FIN-042` is paid because `AP-2025-0068` matches the claim amount and has a cleared payment, while the scheduled `AP-2025-0079` is a distractor because it does not match the claim amount/vendor. `CLM-2025-0090`, `CLM-2025-0080`, `CLM-2025-0038`, and `CLM-2025-0037` are blocked: they either have no usable reimbursement bill or only mismatched/void AP records, so each requires expense-case/AP-link cleanup. The valid open AP reimbursement balance is therefore USD 1,842.36, and the batch status is `blocked` because at least one reviewed claim is blocked.

The evaluator has eight exact-match scoring points with raw weights totaling 16: payable claim set (3), blocked claim set (3), paid claim set (2), AP open balance total to cents (2), CRM cleanup claim set (2), overall batch status enum (2), reviewed claim count (1), and partition consistency across the requested batch (1). The evaluator normalizes by total raw weight and accepts a prediction path as its first argument, defaulting in `eval.sh` to `output/answer.json`. Set-valued claim lists are compared independent of order; the prompt still asks for sorted lists to reduce output variability.

Likely model pitfalls include trusting claim `status` alone, counting every AP bill linked by `claim_id`, treating processing payments as cleared, accepting scheduled bills with mismatched amount/vendor, or excluding partial-support claims even when a matching paid bill and cleared payment already settle the claim. These pitfalls are deliberate because the broader task group expects agents to learn that effective close status must be reconstructed from multiple ERP objects rather than copied from one field.

Transfer design: as a train task, this is a real calibration sample rather than a tutorial. By attempting it and comparing against the answer, a solver can infer reusable habits for later tasks: use the public API endpoints, join objects by stable IDs, verify amount/vendor/status before treating AP records as valid, distinguish paid from payable from blocked, treat mismatched AP links as cleanup cases, and compute close-level totals only from valid open items. These habits should transfer to later expense/AP, prepaid, compliance, and close-readiness tasks without exposing a full SOP in the solver-visible prompt.

Construction record: created by the task-builder subagent for `train_001` on 2026-06-01. The final files were written only under `task_group/task_group_005/train_tasks/001/`. The task aligns to `scratch/task_group_design.md` and the shared API blueprint in `scratch/env_blueprint.md`; generated environment JSON was inspected only to determine the hidden standard answer.

## Chinese

本任务属于 `task_group_005`，共享环境是一个 Northwind 风格的财务运营 ERP 数据与 API 环境。任务简述为 `train_001, Expense-to-AP control`：求解器需要处理一个小型报销批次，并通过公开 API base URL 获取证据，而不是读取隐藏的环境数据文件。批次中的 claim 是 `CLM-2025-OPS-017`、`CLM-2025-FIN-042`、`CLM-2025-0090`、`CLM-2025-0080`、`CLM-2025-0038` 和 `CLM-2025-0037`。

求解器可见输入是 `input/prompt.txt` 和 `input/payloads/answer_template.json`。主要公开 API 是 `http://127.0.0.1:8005` 下的 `/api/claims/{claim_id}`、`/api/ap/bills`、`/api/ap/payments`。本任务特意放入了干扰性的 AP 记录：`CLM-2025-FIN-042` 既有一个真正匹配且已支付的 AP bill，也有一个不应计入该 claim 状态的 scheduled AP bill；其他几个 claim 则存在金额、供应商、状态不匹配，或者没有可用 AP bill 的情况。

标准答案依据 claim、AP bill、payment 三类对象的有效状态重建。`CLM-2025-OPS-017` 是 payable，因为它已批准、凭证完整，并且有金额为 1,842.36 美元的开放报销 AP bill `AP-2025-REIM-017`。`CLM-2025-FIN-042` 是 paid，因为 `AP-2025-0068` 与 claim 金额匹配且付款 cleared；`AP-2025-0079` 虽然也挂了同一 claim_id，但金额和供应商不匹配，是干扰项。`CLM-2025-0090`、`CLM-2025-0080`、`CLM-2025-0038` 和 `CLM-2025-0037` 都是 blocked，因为没有可释放到 AP 的有效报销 bill，或只有不匹配/作废的 AP 记录，因此需要费用 case 或 AP 链接清理。有效开放 AP 报销余额为 1,842.36 美元；由于存在 blocked 项，批次状态为 `blocked`。

评估器包含 8 个精确匹配评分点，原始权重合计 16：payable claim 集合 3 分、blocked claim 集合 3 分、paid claim 集合 2 分、AP 开放余额 2 分、CRM 清理 claim 集合 2 分、批次状态枚举 2 分、reviewed claim 数量 1 分、批次 claim 分区一致性 1 分。评估脚本按原始权重归一化。`eval.sh` 接收预测 JSON 路径作为第一个参数，默认使用 `output/answer.json`。claim 列表在评估时按集合比较，但 prompt 仍要求排序以减少输出差异。

常见错误包括只相信 claim 的 `status` 字段、把所有通过 `claim_id` 挂接的 AP bill 都计入、把 processing payment 当作 cleared、接受金额或供应商不匹配的 scheduled bill、或者在已有匹配且已清算付款的情况下因为 partial support 而错误排除已支付 claim。这些错误点是有意设计的，因为任务组希望模型学习 close 状态需要跨 ERP 对象重建，而不是从单个字段复制。

迁移设计：作为训练任务，它是一个真实校准样本，不是教程。求解器在盲做并对照答案后，可以总结出后续任务可迁移的经验：使用公开 API、按稳定 ID 联结对象、在认定 AP 记录有效前检查金额/供应商/状态、区分 paid/payable/blocked、将不匹配 AP 链接视为需要清理的 case，并且只用有效开放项计算 close 层面的余额。这些经验可以迁移到后续费用/AP、预付、合规和关账准备任务，同时 solver 可见 prompt 中没有暴露完整 SOP。

构造记录：由 `train_001` task-builder subagent 于 2026-06-01 创建。最终文件只写入 `task_group/task_group_005/train_tasks/001/`。本任务与 `scratch/task_group_design.md` 和 `scratch/env_blueprint.md` 中的共享 API 蓝图一致；仅为确定隐藏标准答案而检查生成的环境 JSON。
