# Test 005 Notes: NOVA Headlamp Redesign Price-Change Control

## English

Task purpose: this test task asks the solver to produce a structured post-nomination price-change control file for a NOVA headlamp redesign. The solver sees an English prompt, a small English memo, and the shared ProcureOps API. The task is anchored on `PRG-NOVA-31`, `CR-NOVA-311`, `REQ-NOVA-302`, and `PO-NOVA-3107`.

Data lineage and material map: `input/payloads/headlamp_price_change_memo.json` names the memo `PCR-NOVA-HL-311`, the redesign reference `HL-NOVA-REV-C`, the impacted quantity `180`, and the proposed unit price `154.24`. The authoritative records are in the shared environment: `/programs/PRG-NOVA-31`, `/contracts/CR-NOVA-311`, `/purchase_requisitions/REQ-NOVA-302`, `/purchase_orders?contract_id=CR-NOVA-311`, `/receipts?po_id=PO-NOVA-3107`, `/ap/invoices?supplier_id=SUP-HEXEL`, `/approval_events?object_id=REQ-NOVA-302`, `/budget_snapshots/BUD-PRG-NOVA-31`, `/suppliers/SUP-HEXEL`, and `/vendor_risk_events?supplier_id=SUP-HEXEL`.

Solution basis: the active indexed contract `CR-NOVA-311` covers `SUP-HEXEL` / `SEN-NOVA` for `PRG-NOVA-31` at a baseline unit price of `149.75` with a `240000.00` ceiling. The memo's proposed unit price is `154.24`, so the delta is `4.49`, an uplift of `3.00%`. For `180` impacted units, the incremental subtotal is `808.20`; tax at `7.25%` is `58.59`; freight is `0.00`; incremental total is `866.79`.

Contract usage uses all non-cancelled purchase orders against `CR-NOVA-311`, not only the named NOVA PO. The included PO set is `PO-NOVA-3107`, `PO-00013`, `PO-00026`, and `PO-00042`, totaling `81613.75`. There are no cancelled contract POs to exclude. Contract headroom before the change is `158386.25`, and after the incremental price-delta exposure it is `157578.05`, so the ceiling check passes.

Program budget uses `BUD-PRG-NOVA-31`: budget cap `420000.00`, committed amount `358204.15`, remaining budget `61795.85`, and budget after this incremental price change `60929.06`, so budget passes. `REQ-NOVA-302` is converted and its latest approval event is `APR-00002`, action `approved`, actor `Procurement Lead`, dated `2026-05-08`. The nominated PO is received, with as-of receipt evidence `RCV-GOLD-27`; `AP-HEXEL-3309` is the matched invoice. `AP-00002` carries the proposed price but has no receipt and should be controlled as an unmatched price-variance invoice rather than used as payment evidence.

Supplier risk: `SUP-HEXEL` is active with risk rating `medium`. As of `2026-06-01`, the open event set is `VRE-00032`, the monitoring event set is `VRE-00010`, and there are no severe open events as of the memo date. Later open high events in the data are not part of the as-of answer. Supplier risk therefore does not block the amendment.

Expected decision: `release_price_amendment`. Required actions are `issue_price_delta_amendment` and `block_unmatched_price_invoice`; blocker count is `0`, currency is `USD`, and the file is ready to release.

Scoring points use seven exact-match checks with train-design weights:
- `SP1_identity_and_final_decision`, weight 2.
- `SP2_contract_price_and_change_basis`, weight 2.
- `SP3_contract_usage_and_ceiling`, weight 3.
- `SP4_budget_incremental_exposure`, weight 3.
- `SP5_nomination_and_approval_evidence`, weight 2.
- `SP6_supplier_risk_and_invoice_control`, weight 1.
- `SP7_actions_and_summary`, weight 2.

Transfer design: train task `train_001` anchors nomination readiness, conditional evidence, supplier-risk context, and as-of evidence handling. Train task `train_003` anchors NOVA invoice and payment-control reconciliation, including `AP-HEXEL-3309` as releasable evidence. Train task `train_004` anchors post-nomination change-control calculations: contract usage from non-cancelled POs, budget exposure with tax, approval-state checks, and structured hold/release decisions. The test changes the entity set to NOVA, uses an indexed price-delta amendment rather than a fixed-price quantity amendment, and adds an unmatched price-variance invoice that must be controlled without blocking the commercial amendment.

Construction record: created by Codex for `task_group_006/test_tasks/005` on 2026-06-01. The task-specific `scratch/task_group_design.md` was not present in `6.1/006/task_factory/scratch`; construction used the workspace builder context, available guides, train anchors, and shared environment records. Solver-visible files are English-only and do not include scoring weights, hidden derivation, or SOP steps.

