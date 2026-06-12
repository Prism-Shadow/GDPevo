# Train 001 Notes

## English

Task purpose: this train task asks the solver to assemble a sourcing nomination readiness packet for PRG-AX17 using the shared ProcureOps endpoints. It is anchored in the supplier nomination workflow from the procurement/source-to-contract scenario, but the expected answer is structured operational evidence rather than process prose.

Source data: the prompt gives only the API base URL and a small local memo naming two package anchors. The answer requires API lookups across programs, requisitions, items, suppliers, contracts, purchase orders, receipts, AP invoices, budget snapshots, approval events, and vendor-risk events. The API, not the memo, is authoritative.

Gold derivation: PRG-AX17 is owned by Elena Marsh. Budget headroom is 285000.00 minus 216430.40, or 68569.60. The packet is not ready overall because DRV-AX17 is on hold. LMP-228 maps to SUP-LUMA, has active commercial basis CR-LMP-228, has PO-AX17-4481, and has receipt evidence RCV-BLUE-14 by 2026-06-01. It remains at risk because SUP-LUMA has watch risk, open supplier-risk event VRE-00005, and AP holds AP-00001 and AP-LUMA-7714. DRV-AX17 maps to SUP-VANTIX, but PO-AX17-4519 has no contract, no receipt by 2026-06-01, AP-VANTIX-2188 is pending receipt, VRE-00009 is open for the supplier, and the PO due date is after the requisition need-by date; the line is therefore held.

Transfer value: solvers should learn to reconcile local package anchors with live ERP-style records, separate conditional readiness from hard holds, use an as-of date for evidence, and report controlled structured decisions rather than free-form sourcing advice.

Evaluation: the evaluator uses seven exact-match scoring points with raw weights 1, 2, 2, 2, 2, 2, and 1. List-like fields are normalized as sets, and nomination lines are matched by SKU.
