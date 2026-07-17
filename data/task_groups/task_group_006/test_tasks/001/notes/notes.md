# test_001 Notes

## English

This test task belongs to `SCN_006_erp_procurement_supplier_receiving` and uses the shared ProcureOps environment plus the task-local dock memo/export. The requested scratch design files were absent from `6.1/006/task_factory/scratch`, so the task was built from the explicit builder brief and existing train-task anchors.

The solver must consolidate receiving control for `RCV-GOLD-27` as of `2026-06-02`. ProcureOps is authoritative for PO, receipt, AP invoice, contract, payment, and supplier-risk records; the memo/export is supporting context only.

Solution basis: `RCV-GOLD-27` belongs to `PO-NOVA-3107`, `PRG-NOVA-31`, and `SUP-HEXEL`; it received 180 units of `SEN-NOVA`, rejected 0, and matches the PO/contract/invoice unit price of 149.75. `AP-HEXEL-3309` is linked to the target receipt and releases for 28,909.24 with scheduled payment `PAY-00001`. `AP-00002` is a same-PO approved invoice with no receipt link, a higher unit price of 154.24, scheduled payment `PAY-00002`, and duplicate exposure of 29,901.03; it must be held for review. `RCV-00002` is a later same-PO receipt excluded from this closeout, and `RCV-00014` is a same-supplier but other-PO dock row outside scope. As of the review date, `SUP-HEXEL` has open risk event `VRE-00032`.

Evaluation uses eight exact-match scoring points with weights `[3, 3, 2, 2, 3, 2, 2, 1]`: target IDs/date; receipt controls; quantity/price reconciliation; invoice decisions; financial and payment totals; invoice receipt scope; source precedence plus supplier risk; follow-up actions. Lists are normalized as sets and currency is rounded to cents.

Transfer anchors: `train_002` anchors posted receipt to PO/AP reconciliation and separating receipt acceptance from AP release; `train_003` anchors invoice-to-receipt matching and scheduled payment treatment; `train_005` anchors same-PO receipt exclusion and source-precedence behavior. The test changes the target receipt, program, supplier risk as-of date, and duplicate invoice pattern.

Construction record: created by task-builder subagent for `task_group_006/test_tasks/001` on 2026-06-01. Files were created only for this task folder.

## Chinese

本测试任务属于 `SCN_006_erp_procurement_supplier_receiving`，使用共享 ProcureOps 环境和任务本地 dock memo/export。`6.1/006/task_factory/scratch` 中没有请求的 scratch 设计文件，因此任务依据明确的 builder brief 和已有训练任务锚点构建。

求解者需要以 `2026-06-02` 为截止日，为 `RCV-GOLD-27` 制作合并收货控制文件。ProcureOps 是 PO、receipt、AP invoice、contract、payment 和 supplier-risk 记录的权威来源；memo/export 只提供辅助上下文。

解答依据：`RCV-GOLD-27` 属于 `PO-NOVA-3107`、`PRG-NOVA-31` 和 `SUP-HEXEL`；收货 `SEN-NOVA` 180 件，拒收 0 件，PO、合同和关联发票单价均为 149.75。`AP-HEXEL-3309` 关联目标 receipt，可按 28,909.24 放行，并有排程付款 `PAY-00001`。`AP-00002` 是同一 PO 上已批准但没有 receipt link 的发票，单价 154.24，排程付款 `PAY-00002`，重复风险敞口为 29,901.03，应进入复核。`RCV-00002` 是后续同 PO 收货，本次关闭排除；`RCV-00014` 是同供应商但不同 PO 的 dock 行，不在范围内。截至复核日，`SUP-HEXEL` 的开放风险事件为 `VRE-00032`。

评估使用八个精确匹配评分点，权重为 `[3, 3, 2, 2, 3, 2, 2, 1]`：目标 ID/日期；收货控制；数量/价格核对；发票决策；财务和付款合计；发票 receipt scope；来源优先级和供应商风险；后续行动。列表按集合归一化，金额保留到美分。

迁移锚点：`train_002` 锚定已过账 receipt 与 PO/AP 的核对，以及 receipt 接受和 AP 放行的区分；`train_003` 锚定发票到 receipt 的匹配和排程付款处理；`train_005` 锚定同 PO receipt 排除和来源优先级。本测试改变了目标 receipt、项目、供应商风险截止日和重复发票模式。

构建记录：由 `task_group_006/test_tasks/001` 的 task-builder subagent 于 2026-06-01 创建。文件仅为本任务目录创建。
