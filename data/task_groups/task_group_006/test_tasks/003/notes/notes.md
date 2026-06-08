# Test 003 Notes

## English

Task purpose: this test task asks for a structured sourcing shortlist and nomination-gate packet for `PRG-NOVA-31`, focused on `SEN-NOVA` and RFQ packet `NOVA-SRC-31`. It converts the E003 sourcing workflow theme into operational ERP evidence: candidate shortlist decisions, supplier risk checks, commercial support, and a controlled nomination-gate result.

Data sources: the solver-visible prompt points to the shared ProcureOps API and the small English-only local memo `input/payloads/sourcing_memo.md`. The memo contains only RFQ response cards and a signoff tracker. Authoritative operational records come from the API endpoints for programs, suppliers, contracts, purchase requisitions, purchase orders, receipts, AP invoices, AP payments, budget snapshots, and vendor risk events.

Gold derivation: `REQ-NOVA-302` requests 180 units of `SEN-NOVA` by 2026-06-22. `PRG-NOVA-31` is owned by Ravi Menon and has budget headroom of `420000.00 - 358204.15 = 61795.85`. `SUP-HEXEL` is the preferred shortlisted supplier because it is active, has active commercial basis `CR-NOVA-311`, PO `PO-NOVA-3107`, receipt `RCV-GOLD-27`, approved invoice `AP-HEXEL-3309`, and scheduled payment `PAY-00001`; it remains at risk because open or monitoring supplier events `VRE-00010` and `VRE-00032` exist as of 2026-06-01. `SUP-ORION` is a backup shortlist supplier because it is active, low risk, technically approved, and has enough memo capacity but lacks a signed Nova commercial basis. `SUP-BLUESTEM` is excluded for conditional technical fit, capacity shortfall, missing contract, and supplier risk events `VRE-00001` and `VRE-00017`. `SUP-NORD` is excluded because the API supplier status is `quality_hold` and risk rating is `high`.

Nomination gate basis: the memo's signoff tracker shows ER, Finance, and Quality signed, while Program Manager is pending. The selected supplier is therefore not cleared for final nomination; the expected gate decision is `hold_for_missing_program_manager_signoff`, readiness `at_risk`, next owner `program_owner`, and committee routing `no`.

Train anchors: `train_tasks/001` anchors the nomination-readiness structure, as-of supplier risk handling, shortlist/hold style decisions, and budget-headroom convention. `train_tasks/002` anchors supplier risk and blocker-code reconciliation against operational records. `train_tasks/003` anchors use of invoice, receipt, and payment evidence to support release-style business decisions.

Evaluation: seven exact-match scoring points use raw weights `1, 2, 2, 2, 2, 2, 1`. Lists are normalized as sets, candidate rows are matched by `supplier_id`, and USD fields are rounded to cents. The scoring points cover scope and requirement; program budget and shortlist sets; candidate API status and risk; sourcing decisions and blockers; selected supplier commercial support; nomination gate signoffs and decision; and recommended actions/source records.

Construction record: the requested `scratch/task_group_design.md` was not present under this task factory's scratch directory at build time. The available workspace-level `scratch/task_builder_context.md`, the seed E003 sourcing-rubric anchors, existing train tasks, and the shared environment data were used. Files were created only under `task_group/task_group_006/test_tasks/003/`.

