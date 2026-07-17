# train_002 Notes

## English

Data lineage: this task belongs to `SCN_006_erp_procurement_supplier_receiving`, based mainly on the warehouse package inspection and vendor chargeback workflow in source example `E002`, with AP and supplier-control context from `E001`. It uses the shared ProcureOps environment under `task_group/task_group_006/env/` and one task-local payload, `input/payloads/receiving_memo.md`.

Task definition: the solver receives a closeout request for receiving batch `RCV-BLUE-14`. The visible prompt points to the local ProcureOps API and asks for a structured JSON answer using `input/payloads/answer_template.json`. The solver must join receipt, purchase order, contract, supplier, AP invoice, item, and supplier-risk records to decide whether the batch/invoice can be released or must stay on hold.

Material map: `/receipts/RCV-BLUE-14` gives the posted receipt, quantity received, receipt status, warehouse, receiver, and packing slip. `/purchase_orders/PO-AX17-4481` gives the ordered quantity, unit price, program, buyer, status, and contract. `/contracts/CR-LMP-228` confirms the fixed contract price. `/ap/invoices/AP-LUMA-7714` gives the billed quantity, invoice total, AP hold status, and hold code. `/suppliers/SUP-LUMA`, `/items/LMP-228`, and `/vendor_risk_events?supplier_id=SUP-LUMA` provide supplier identity, item identity, and risk context. The memo clarifies that this is a posted-receipt closeout review and not a new receipt transaction.

Solution basis: the PO ordered 240 units of `LMP-228`, the receipt posted 216 received and 0 rejected, and the invoice billed 240. The shortage versus PO and the unreceived billed quantity are both 24. At the fixed unit price of 84.50 USD, the accepted goods value is 18,252.00 USD and the unreceived goods exposure is 2,028.00 USD. The invoice has status `on_hold` with hold code `QTY_VARIANCE`; the PO is `partial_receipt`; the receipt itself is `accepted`. The correct disposition is to accept the partial receipt for the posted 216 units, keep the invoice on hold, record shortage follow-up, and request a supplier credit or remaining delivery. Supplier `SUP-LUMA` has watch risk and one open supplier-level risk event, `VRE-00005`.

Evaluation: the evaluator performs exact-match checks on eight structured scoring points with raw weights totaling 17:

- `SP001_batch_identity`, weight 2: target task and batch plus receipt/PO/supplier/warehouse identifiers.
- `SP002_line_quantity_reconciliation`, weight 3: SKU, ordered, received, rejected, billed, shortage, unreceived billed quantity, completion ratio, and price fields.
- `SP003_invoice_hold_status`, weight 2: invoice ID, invoice status, hold code, receipt status, PO status, and exception-code set.
- `SP004_financial_variance`, weight 2: accepted goods value, unreceived goods value, invoice subtotal, freight, tax, and total.
- `SP005_business_disposition`, weight 3: controlled batch, AP, receiving, and supplier actions.
- `SP006_supplier_risk_context`, weight 1: risk rating, open-risk boolean, and open event IDs.
- `SP007_source_record_set`, weight 2: API record IDs and task-local payload reference.
- `SP008_contract_price_consistency`, weight 2: line-level contract/PO/invoice price agreement and absence of a price-mismatch exception.

Likely model pitfalls include treating the receipt status `accepted` as permission to release the invoice, using the invoice billed quantity as the accepted quantity, ignoring the supplier watch risk, treating the memo as a substitute for API evidence, or inventing a damage rejection even though no rejected quantity is posted.

Transfer design: as a train task, this task anchors receiving-control conventions for later procurement tasks: join the posted receipt to the PO and AP invoice, separate receipt acceptance from AP release, calculate billed-unreceived exposure from system quantities, treat controlled exception codes as structured outputs, and use supplier risk only as context rather than as a replacement for quantity reconciliation.

Construction record: author `task-builder train_002`; created 2026-06-01; updated 2026-06-01. The design file requested in `scratch/task_group_design.md` was not present in this workspace, so this task follows the explicit build brief and the shared task-builder context.

## 中文

数据来源：本任务属于 `SCN_006_erp_procurement_supplier_receiving`，主要继承源示例 `E002` 的仓库收货检查与供应商扣款流程，并结合 `E001` 的应付与供应商控制语境。任务使用 `task_group/task_group_006/env/` 下的共享 ProcureOps 环境，以及一个任务本地材料 `input/payloads/receiving_memo.md`。

任务定义：求解者收到收货批次 `RCV-BLUE-14` 的关闭复核请求。可见提示指向本地 ProcureOps API，并要求按 `input/payloads/answer_template.json` 输出结构化 JSON。求解者需要关联收货、采购订单、合同、供应商、应付发票、物料和供应商风险记录，判断该批次及对应发票是否可以放行，或是否应继续保持冻结。

材料地图：`/receipts/RCV-BLUE-14` 提供已过账收货、实收数量、收货状态、仓库、收货人和装箱单。`/purchase_orders/PO-AX17-4481` 提供订购数量、单价、项目、采购员、订单状态和合同。`/contracts/CR-LMP-228` 确认固定合同价格。`/ap/invoices/AP-LUMA-7714` 提供应付发票的开票数量、发票总额、冻结状态和冻结代码。`/suppliers/SUP-LUMA`、`/items/LMP-228` 和按供应商筛选的 `/vendor_risk_events` 提供供应商、物料和风险背景。本地 memo 说明这是一项已过账收货的关闭复核，而不是新建收货交易。

解答依据：采购订单订购 `LMP-228` 共 240 件，收货记录显示实收 216 件、拒收 0 件，发票开票 240 件。因此相对订单短缺 24 件，未收货但已开票数量也是 24 件。固定单价为 84.50 美元，已收货物价值为 18,252.00 美元，未收货风险金额为 2,028.00 美元。发票状态为 `on_hold`，冻结代码为 `QTY_VARIANCE`；采购订单状态为 `partial_receipt`；收货记录本身为 `accepted`。正确处置是接受已过账的 216 件部分收货，继续冻结发票，记录短缺跟进，并要求供应商开具贷项或补交剩余货物。供应商 `SUP-LUMA` 的风险等级为 watch，且有一个开放的供应商层面风险事件 `VRE-00005`。

评估方式：评估器对八个结构化评分点做精确匹配，原始权重合计 17：

- `SP001_batch_identity`，权重 2：目标任务和批次，以及收货、采购订单、供应商、仓库等标识。
- `SP002_line_quantity_reconciliation`，权重 3：SKU、订购量、实收量、拒收量、开票量、短缺量、未收货已开票量、完成比例和价格字段。
- `SP003_invoice_hold_status`，权重 2：发票 ID、发票状态、冻结代码、收货状态、采购订单状态和异常代码集合。
- `SP004_financial_variance`，权重 2：已收货物价值、未收货货物价值、发票小计、运费、税额和总额。
- `SP005_business_disposition`，权重 3：批次、应付、收货和供应商动作。
- `SP006_supplier_risk_context`，权重 1：风险等级、是否存在开放风险、开放事件 ID。
- `SP007_source_record_set`，权重 2：API 记录 ID 和本地 payload 引用。
- `SP008_contract_price_consistency`，权重 2：合同、采购订单、发票单价一致性，以及没有价格不符异常。

常见错误包括：把收货状态 `accepted` 误解为可以放行发票；把发票开票数量当作实收数量；忽略供应商 watch 风险；用 memo 代替 API 证据；或在没有拒收数量的情况下编造损坏拒收。

迁移设计：作为训练任务，本任务锚定后续采购任务中的收货控制约定：把已过账收货与采购订单、应付发票关联起来；区分收货接受和应付放行；根据系统数量计算未收货但已开票风险；把异常代码作为结构化输出；并且把供应商风险作为背景，而不是替代数量核对。

构建记录：作者 `task-builder train_002`；创建日期 2026-06-01；更新日期 2026-06-01。工作区内未找到请求读取的 `scratch/task_group_design.md`，因此本任务按用户明确的构建说明和共享 task-builder context 完成。
