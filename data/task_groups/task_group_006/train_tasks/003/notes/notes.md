# train_003 Notes

## English

Task definition: build a formal AP close task for the AX17/NOVA ProcureOps invoices `AP-LUMA-7714`, `AP-HEXEL-3309`, and `AP-VANTIX-2188`. The solver-visible work requires using shared ProcureOps endpoints rather than hidden files, plus a small local AP memo that identifies the close slice and opening-balance assumption.

Solution basis: invoice, PO, receipt, supplier, and payment records come from the shared environment. `AP-LUMA-7714` bills 240 units against receipt `RCV-BLUE-14`, which accepted 216 units, so the invoice remains on `QTY_VARIANCE` hold. `AP-HEXEL-3309` matches PO and receipt quantities and has scheduled payment `PAY-00001`, so it is released and fully scheduled. `AP-VANTIX-2188` has no receipt and remains on `NO_RECEIPT` hold. Vendor balances use the memo opening balance of 0.00, invoice totals from the invoice records, and scheduled payments through 2026-06-30.

Transfer purpose: this train task exposes reusable ProcureOps conventions for AP close work: invoice-to-PO-to-receipt matching, scheduled payment offsetting, controlled hold/release queues, and supplier/program close rollups. Test tasks can vary programs, suppliers, and local memo assumptions while preserving these reconciliation patterns.

Common pitfalls: using the PO total instead of the invoice total for vendor balance, treating open POs as receipts, missing the scheduled HEXEL payment, including unrelated generated AP invoices for the same suppliers, or using free-text reasons instead of controlled reason codes.

Evaluation: the evaluator has eight exact-match scoring points with raw weights 2, 3, 2, 2, 2, 1, 3, and 2. It checks task identity and target invoice set; invoice hold/release decisions; receipt quantity variances; invoice totals and payment offsets; supplier balance rows; controlled reason-code sets; program totals; and final queues plus total close balance.

Construction record: authored for task-builder subagent `train_003` on 2026-06-01. Created files only under `task_group/task_group_006/train_tasks/003/`. No shared environment, scratch design, seed scenario, other task folders, or `task_group.yaml` files were edited.

## 中文

任务定义：为 AX17/NOVA 的 ProcureOps 发票 `AP-LUMA-7714`、`AP-HEXEL-3309`、`AP-VANTIX-2188` 构建正式 AP 月结任务。求解者可见材料要求使用共享 ProcureOps 端点，并结合一个很小的本地 AP 备忘录，该备忘录只说明月结切片和期初余额假设。

答案依据：发票、采购订单、收货、供应商和付款记录来自共享环境。`AP-LUMA-7714` 按 240 件开票，但收货 `RCV-BLUE-14` 只验收 216 件，因此保持 `QTY_VARIANCE` 付款冻结。`AP-HEXEL-3309` 的采购订单、收货和发票数量一致，且存在计划付款 `PAY-00001`，因此可放行且余额已由计划付款抵减。`AP-VANTIX-2188` 没有收货记录，因此保持 `NO_RECEIPT` 冻结。供应商余额使用备忘录中的 0.00 期初余额、发票总额以及截至 2026-06-30 的计划付款。

迁移目的：该训练任务暴露 AP 月结中可迁移的 ProcureOps 口径，包括发票-采购订单-收货匹配、计划付款抵减、受控的冻结/放行队列，以及供应商和项目维度的汇总。测试任务可以更换项目、供应商和本地备忘录假设，但保留这些对账模式。

常见错误：用采购订单总额代替发票总额计算供应商余额；把未完成采购订单当成收货；漏掉 HEXEL 的计划付款；把同供应商的无关生成发票纳入范围；或用自由文本原因代替受控原因代码。

评测方式：评估器包含 8 个精确匹配得分点，原始权重为 2、3、2、2、2、1、3、2。检查任务标识和目标发票集合、发票冻结/放行判断、收货数量差异、发票总额和付款抵减、供应商余额行、受控原因代码集合、项目汇总，以及最终队列和总月结余额。

构建记录：由任务构建子代理 `train_003` 于 2026-06-01 创建。只在 `task_group/task_group_006/train_tasks/003/` 下创建文件。未编辑共享环境、scratch 设计、种子场景、其他任务目录或 `task_group.yaml`。
