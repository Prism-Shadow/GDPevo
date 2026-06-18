# test_001 Notes

## English

This test task belongs to `SCN_006_erp_procurement_supplier_receiving` and uses the shared ProcureOps environment plus the task-local dock memo/export. The requested scratch design files were absent from `6.1/006/task_factory/scratch`, so the task was built from the explicit builder brief and existing train-task anchors.

The solver must consolidate receiving control for `RCV-GOLD-27` as of `2026-06-02`. ProcureOps is authoritative for PO, receipt, AP invoice, contract, payment, and supplier-risk records; the memo/export is supporting context only.

Solution basis: `RCV-GOLD-27` belongs to `PO-NOVA-3107`, `PRG-NOVA-31`, and `SUP-HEXEL`; it received 180 units of `SEN-NOVA`, rejected 0, and matches the PO/contract/invoice unit price of 149.75. `AP-HEXEL-3309` is linked to the target receipt and releases for 28,909.24 with scheduled payment `PAY-00001`. `AP-00002` is a same-PO approved invoice with no receipt link, a higher unit price of 154.24, scheduled payment `PAY-00002`, and duplicate exposure of 29,901.03; it must be held for review. `RCV-00002` is a later same-PO receipt excluded from this closeout, and `RCV-00014` is a same-supplier but other-PO dock row outside scope. As of the review date, `SUP-HEXEL` has open risk event `VRE-00032`.

Evaluation uses eight exact-match scoring points with weights `[3, 3, 2, 2, 3, 2, 2, 1]`: target IDs/date; receipt controls; quantity/price reconciliation; invoice decisions; financial and payment totals; invoice receipt scope; source precedence plus supplier risk; follow-up actions. Lists are normalized as sets and currency is rounded to cents.

Transfer anchors: `train_002` anchors posted receipt to PO/AP reconciliation and separating receipt acceptance from AP release; `train_003` anchors invoice-to-receipt matching and scheduled payment treatment; `train_005` anchors same-PO receipt exclusion and source-precedence behavior. The test changes the target receipt, program, supplier risk as-of date, and duplicate invoice pattern.
