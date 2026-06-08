# Train 004 Notes: AX17 Tail-Lamp Variant Change Request

## English

Task purpose: build a modular procurement change-request task around `CR-LMP-228`, `PRG-AX17`, and the `LMP-228` AX17 tail-lamp variant. The solver sees only an English prompt, a small memo payload, and the shared ProcureOps API.

Source records used:
- Memo payload: `input/payloads/change_memo.json`, memo `MCR-AX17-TL-228`, quantity `781`, variant `AX17-TL-REV-B`.
- Program: `PRG-AX17`, budget cap `285000.00`, committed amount `216430.40`.
- Contract: `CR-LMP-228`, active fixed-price contract for `SUP-LUMA` / `LMP-228` / `PRG-AX17`, unit price `84.50`, ceiling `185000.00`.
- Existing non-cancelled contract POs: `PO-AX17-4481` subtotal `20280.00`, `PO-00027` subtotal `21125.00`, `PO-00031` subtotal `24589.50`. Total non-cancelled usage is `65994.50`.
- Cancelled contract POs excluded from usage: `PO-00008`, `PO-00041`.
- Approval event for source requisition `REQ-AX17-141`: latest event `APR-00001`, action `submitted`, actor `Compliance Desk`, date `2026-05-02`.
- Supplier `SUP-LUMA`: active, risk rating `watch`; open event set contains `VRE-00005`, but there are no open severe events.

Calculations:
- Contract headroom before change: `185000.00 - 65994.50 = 119005.50`.
- Requested subtotal: `781 * 84.50 = 65994.50`.
- Contract headroom after change: `119005.50 - 65994.50 = 53011.00`, so the contract ceiling check passes.
- Budget remaining: `285000.00 - 216430.40 = 68569.60`.
- Requested tax: `65994.50 * 7.25% = 4784.60`.
- Requested total: `65994.50 + 4784.60 = 70779.10`.
- Budget after change: `68569.60 - 70779.10 = -2209.50`, so the budget check fails.
- Maximum quantity under the current budget at the same unit price and tax basis is `756`.

Expected decision: `hold_for_budget_and_approval`. The contract itself covers the item and has ceiling headroom, and supplier risk is contextual only. The blockers are the negative program-budget result and the lack of a final approved approval event for `REQ-AX17-141`.

Scoring points:
- `SP1_identity_and_final_decision`, weight 2: exact match on change request identity fields and final decision.
- `SP2_contract_status_price_and_quantity`, weight 2: exact match on active contract, fixed price, unit price, ceiling, requested quantity/subtotal, and ceiling result.
- `SP3_contract_usage_and_headroom`, weight 3: exact match on non-cancelled contract usage and headroom before/after the change.
- `SP4_program_budget_exposure`, weight 3: exact match on the full budget object including remaining budget, tax, total, negative after-change amount, budget result, and max affordable quantity.
- `SP5_requisition_approval_state`, weight 2: exact match on latest source requisition approval event and failed approval flag.
- `SP6_supplier_risk_context_and_supporting_ids`, weight 1: exact match on supplier risk context and supporting PO/approval ID sets.
- `SP7_hold_actions_and_summary`, weight 2: exact match on required actions and summary.

Construction record: created for `task_group_006/train_tasks/004` on 2026-06-01. The task-specific design file requested by the builder prompt was not present under `6.1/006/task_factory/scratch`; the task was built from the workspace-level builder context, the explicit train_004 brief, and the shared environment data.

