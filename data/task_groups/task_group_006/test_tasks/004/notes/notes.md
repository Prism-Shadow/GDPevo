# test_004 Notes

## English

Task definition: this formal test task asks the solver to correct a stale WH-BLUE regional receiving dashboard for the North America operating review as of 2026-06-10. The solver sees only an English prompt, a stale dashboard export, and an answer template. The shared ProcureOps API provides the authoritative receipt, PO, AP invoice, and vendor-risk records.

Data lineage: the task belongs to `SCN_006_erp_procurement_supplier_receiving` and uses the generated environment under `task_group/task_group_006/env/`. The target slice is the local export's five WH-BLUE receipt IDs: `RCV-BLUE-14`, `RCV-00001`, `RCV-00004`, `RCV-00007`, and `RCV-00020`.

Solution basis: `RCV-BLUE-14` and `RCV-00001` are separate receipt rows for `PO-AX17-4481`; each must be matched to its invoice-linked AP record rather than merged by PO. `AP-LUMA-7714` is on `QTY_VARIANCE` hold with 24 billed-over-received units worth 2,028.00 USD. `AP-00001` is on `PRICE_VARIANCE` hold with 83 billed-over-received units worth 7,013.50 USD. `RCV-00004` has current approved AP invoice `AP-00007`, so it is the only release candidate, but it carries supplier-risk context through `VRE-00007`. `RCV-00007` has only a future invoice dated after the review date, so it remains not invoiced as of 2026-06-10 and its unbilled receipt value is 7,366.97 USD. `RCV-00020` is tied to held invoice `AP-00032` with `NO_RECEIPT` code and a 4-unit AP variance worth 1,183.76 USD. Open supplier-risk events are `VRE-00005`, `VRE-00007`, `VRE-00009`, and `VRE-00017`.

Scoring points: the evaluator has ten exact-match scoring points with raw weights `[3, 3, 2, 2, 3, 2, 2, 1, 3, 3]`: scope and target receipt set; dashboard row identities and operational statuses; AP hold/release/not-invoiced control sets; corrected row statuses and owners; quantity variances and financial totals; supplier-risk overlay; source precedence and stale export corrections; follow-up actions; transfer source-precedence and AP release policies; and chargeback, payment, and no-receipt transfer policies.

Train anchors: `train_002` anchors receipt, PO, AP invoice, and supplier-risk joins plus the distinction between receipt acceptance and AP release. `train_003` anchors AP close conventions, controlled hold codes, and invoice-to-receipt matching. `train_005` anchors invoice-linked receipt selection, same-PO receipt exclusion, net release versus hold decisions, and precedence of authoritative system/register data over request notes. This test changes the shape into a regional dashboard correction with a stale export and as-of filtering.

Construction record: created by the `test_004` task-builder subagent on 2026-06-01. Only files under `task_group/task_group_006/test_tasks/004/` were created or edited. The task-specific `scratch/task_group_design.md` file was not present in this workspace, so the task follows the available shared builder context, the explicit user brief, and the existing train-task transfer anchors.

Final calibration note: the last scoring point separately checks completeness of the chargeback, payment, and no-receipt transfer policies. It is supported by train-task AP release, chargeback, and source-precedence rules.

