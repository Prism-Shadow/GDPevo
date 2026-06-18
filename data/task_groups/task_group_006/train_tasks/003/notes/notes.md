# train_003 Notes

## English

Task definition: build a formal AP close task for the AX17/NOVA ProcureOps invoices `AP-LUMA-7714`, `AP-HEXEL-3309`, and `AP-VANTIX-2188`. The solver-visible work requires using shared ProcureOps endpoints rather than environment files, plus a small local AP memo that identifies the close slice and opening-balance assumption.

Solution basis: invoice, PO, receipt, supplier, and payment records come from the shared environment. `AP-LUMA-7714` bills 240 units against receipt `RCV-BLUE-14`, which accepted 216 units, so the invoice remains on `QTY_VARIANCE` hold. `AP-HEXEL-3309` matches PO and receipt quantities and has scheduled payment `PAY-00001`, so it is released and fully scheduled. `AP-VANTIX-2188` has no receipt and remains on `NO_RECEIPT` hold. Vendor balances use the memo opening balance of 0.00, invoice totals from the invoice records, and scheduled payments through 2026-06-30.

Transfer purpose: this train task exposes reusable ProcureOps conventions for AP close work: invoice-to-PO-to-receipt matching, scheduled payment offsetting, controlled hold/release queues, and supplier/program close rollups. Test tasks can vary programs, suppliers, and local memo assumptions while preserving these reconciliation patterns.

Common pitfalls: using the PO total instead of the invoice total for vendor balance, treating open POs as receipts, missing the scheduled HEXEL payment, including unrelated generated AP invoices for the same suppliers, or using free-text reasons instead of controlled reason codes.

Evaluation: the evaluator has eight exact-match scoring points with raw weights 2, 3, 2, 2, 2, 1, 3, and 2. It checks task identity and target invoice set; invoice hold/release decisions; receipt quantity variances; invoice totals and payment offsets; supplier balance rows; controlled reason-code sets; program totals; and final queues plus total close balance.
