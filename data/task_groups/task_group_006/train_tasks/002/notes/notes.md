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

