# Train 003 Notes - Prepaid Close

## English

This hidden note documents `train_003`, a March 2025 prepaid close task for Aurisic US. The task belongs to `task_group_005`, which uses the shared ERP finance JSON API specified in `scratch/env_blueprint.md`. The task aligns to `scratch/task_group_design.md`, the factory guides, and generated environment data. The visible task input consists of `input/prompt.txt`, `input/payloads/prepaid_close_scope.json`, and `input/payloads/answer_template.json`.

The business request asks the solver to prepare a March close reconciliation for prepaid accounts 1250 and 1251. The selected invoice population is fixed in `prepaid_close_scope.json` and includes eight prepaid invoice IDs: `PPD-AUR-1250-JAN-001`, `PPD-AUR-1251-GOOD-001`, `PPD-2025-0001`, `PPD-2025-0002`, `PPD-2025-0008`, `PPD-2025-0013`, `PPD-2025-0014`, and `PPD-2025-0024`. Invoice attributes come from `/prepaids/invoices` or `/api/prepaids/invoices`; March 2025 GL ending balances come from `/gl/balances` or `/api/prepaids/gl-balances`.

The transfer value is the prepaid close pattern: map invoices to prepaid accounts, use straight-line monthly amortization from the source records, compute cumulative amortization through the close month, compute schedule ending balance, compare schedule ending balance to the GL balance, and classify the account using the variance policy. This train task also anchors the convention that non-empty `data_quality_flags` identify exception invoices, while `missing_contract_dates` is specifically the default or missing-term flag. Those conventions can transfer to later prepaid close and variance review tasks without being presented as a tutorial in the solver-visible prompt.

The standard answer uses the selected invoice records only. For account 1250, the selected original amount is 287,918.71, March amortization is 53,946.41, cumulative amortization through March is 105,118.21, schedule ending balance is 182,800.50, March GL balance is 473,655.55, and schedule-minus-GL variance is -290,855.05. For account 1251, the selected original amount is 714,319.13, March amortization is 80,216.04, cumulative amortization through March is 219,439.06, schedule ending balance is 494,880.07, March GL balance is 415,537.13, and schedule-minus-GL variance is 79,342.94. Both accounts exceed the absolute variance threshold of 100.00, so both account statuses are `requires_reconciliation`.

Invoice-level March ending balances are: `PPD-AUR-1250-JAN-001` 108,000.00; `PPD-AUR-1251-GOOD-001` 410,043.81; `PPD-2025-0001` 6,789.05; `PPD-2025-0002` 21,646.14; `PPD-2025-0008` 84,836.25; `PPD-2025-0013` 46,365.31; `PPD-2025-0014` 0.00; `PPD-2025-0024` 0.01. The default or missing-term invoice IDs are `PPD-2025-0002` and `PPD-2025-0013`. The exception invoice IDs are `PPD-2025-0001`, `PPD-2025-0002`, `PPD-2025-0013`, `PPD-2025-0014`, and `PPD-AUR-1251-GOOD-001`.

The evaluator has nine exact-match scoring points with raw weights 1, 2, 2, 2, 2, 1, 1, 3, and 1. They check the selected invoice population, account 1250 schedule totals, account 1251 schedule totals, account 1250 variance decision, account 1251 variance decision, default or missing-term invoice set, exception invoice set, invoice-level amortization and ending balances, and invoice-level flags. Numeric comparisons round to cents, lists are exact or sorted where the answer template states ascending order, and status fields are controlled enums. Likely model pitfalls include using the full prepaid population instead of the selected IDs, treating mid-month starts as daily prorations instead of using the source monthly amortization, reversing the variance sign, missing the GL account mapping, or ignoring data-quality flags.

Construction record: created by the task-builder subagent for `train_003` on 2026-06-01. The task files were written only under `task_group/task_group_005/train_tasks/003/`.

## 中文

本隐藏说明记录 `train_003`，这是 Aurisic US 的 2025 年 3 月预付费用结账任务。该任务属于 `task_group_005`，使用 `scratch/env_blueprint.md` 中说明的共享 ERP 财务 JSON API，并与 `scratch/task_group_design.md`、工厂指南和生成的环境数据保持一致。求解器可见输入包括 `input/prompt.txt`、`input/payloads/prepaid_close_scope.json` 和 `input/payloads/answer_template.json`。

业务目标是对预付账款科目 1250 和 1251 编制 2025 年 3 月结账核对。`prepaid_close_scope.json` 固定了八张发票：`PPD-AUR-1250-JAN-001`、`PPD-AUR-1251-GOOD-001`、`PPD-2025-0001`、`PPD-2025-0002`、`PPD-2025-0008`、`PPD-2025-0013`、`PPD-2025-0014` 和 `PPD-2025-0024`。发票属性来自 `/prepaids/invoices` 或 `/api/prepaids/invoices`；2025 年 3 月的总账余额来自 `/gl/balances` 或 `/api/prepaids/gl-balances`。

本训练任务的迁移点是预付结账模式：将发票映射到账户，使用源记录中的直线法月摊销额，计算截至结账月份的累计摊销，计算台账期末余额，再与总账余额比较并按差异政策分类账户。本任务还锚定两个字段惯例：非空 `data_quality_flags` 表示异常发票，`missing_contract_dates` 表示默认或缺失期限标记。这些经验可迁移到后续预付结账和差异复核任务，而不会在求解器可见提示中写成教程。

标准答案只使用选定发票。科目 1250 的选定原始金额合计为 287,918.71，3 月摊销为 53,946.41，截至 3 月累计摊销为 105,118.21，台账期末余额为 182,800.50，3 月总账余额为 473,655.55，台账减总账差异为 -290,855.05。科目 1251 的选定原始金额合计为 714,319.13，3 月摊销为 80,216.04，截至 3 月累计摊销为 219,439.06，台账期末余额为 494,880.07，3 月总账余额为 415,537.13，台账减总账差异为 79,342.94。两个科目的绝对差异都超过 100.00，因此账户状态均为 `requires_reconciliation`。

发票层面的 3 月期末余额为：`PPD-AUR-1250-JAN-001` 108,000.00；`PPD-AUR-1251-GOOD-001` 410,043.81；`PPD-2025-0001` 6,789.05；`PPD-2025-0002` 21,646.14；`PPD-2025-0008` 84,836.25；`PPD-2025-0013` 46,365.31；`PPD-2025-0014` 0.00；`PPD-2025-0024` 0.01。默认或缺失期限发票为 `PPD-2025-0002` 和 `PPD-2025-0013`。异常发票为 `PPD-2025-0001`、`PPD-2025-0002`、`PPD-2025-0013`、`PPD-2025-0014` 和 `PPD-AUR-1251-GOOD-001`。

评估器包含九个精确匹配评分点，原始权重为 1、2、2、2、2、1、1、3、1。评分点分别检查选定发票范围、1250 科目台账合计、1251 科目台账合计、1250 科目总账差异判断、1251 科目总账差异判断、默认或缺失期限发票集合、异常发票集合、发票层摊销和期末余额、发票层标记。金额按美分精度比较，列表按模板要求进行精确或排序匹配，状态字段使用受控枚举。常见错误包括使用全部预付发票而不是选定发票、把月摊销改成按日比例计算、差异方向反了、遗漏总账账户映射，或忽略数据质量标记。

构建记录：由 `train_003` 任务构建子代理于 2026-06-01 创建。所有任务文件仅写入 `task_group/task_group_005/train_tasks/003/`。
