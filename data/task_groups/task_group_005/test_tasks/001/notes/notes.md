# test_001 Notes

## English

Task definition: The solver must prepare an April 2025 reimbursement close decision for six candidate claim IDs across four employees: Avery Lee, Cameron Price, Riley Morgan, and Jordan Patel. The expected JSON separates approved-unpaid claims from blocked claims and already-paid claims, totals the approved-unpaid payable amount, identifies claims safe to mark closed downstream, assigns controlled exception reasons, and sets the batch status.

Scenario fit: The task exercises the reimbursement/AP close family in the group. It requires reconciling claim lifecycle state with AP bill and payment state, handling duplicate/noisy flags, and not trusting one stale-looking source row when another AP/payment record gives the effective state.

Material map: `claims.json` provides claim amount, employee, category, approval, receipt, policy flag, and lifecycle status. `bills.json` provides AP bill linkage and status for the claim IDs, including the duplicate/stale AP snapshot around `CLM-2025-FIN-042`. `payments.json` confirms cleared or in-process payments for linked AP bills. `close_logs.json` gives general April close context but is not the source of the claim-level answer.

Solution and evaluation basis: `CLM-2025-0085` and `CLM-2025-OPS-017` are approved and unpaid as of the April close decision, so they are payable; their amounts are 1398.54 and 1842.36, totaling 3240.90. `CLM-2025-0011` is submitted but not approved. `CLM-2025-0064` is submitted with missing receipt support and duplicate noise, so the controlled blocking reason is missing receipt. `CLM-2025-0032` is already paid. `CLM-2025-FIN-042` is already paid after reconciling the paid claim-linked AP bill and cleared payment despite a duplicate/stale AP snapshot and duplicate policy flag. The paid claims are also the `crm_close_claim_ids`. The batch can proceed for payable claims while retaining blocks, so `batch_status` is `ready_to_pay_with_blocks`.

Scoring points: 8 exact-match points are used. `payable_claim_ids` weight 3; `blocked_claim_ids` weight 2; `paid_claim_ids` weight 2; `ap_open_balance_total` weight 2; `crm_close_claim_ids` weight 1; payable/paid exception reasons weight 3; blocked exception reasons weight 2; `batch_status` weight 1. Total raw weight is 16.

Transfer design: This test maps to the reimbursement close and stale-source reconciliation habits intended to be learned from `train_001` and `train_004`. The transferable skill is to derive effective claim disposition by combining claim status, approval/receipt facts, AP bill status, and payment status instead of copying a single noisy field. `train_001` anchors approved/unpaid versus blocked reimbursement decisions, while `train_004` anchors duplicate or stale snapshot handling across AP/payment records. This test changes the employees, claim mix, April period, and output schema, and adds a partial-support/processing-noise pattern.

Likely model pitfalls: treating all April-submitted travel claims as payable; excluding `CLM-2025-FIN-042` only because of duplicate flags; treating an in-process payment on `CLM-2025-OPS-017` as already paid for April close; adding non-candidate IDs from environment search; or using free-form exception text instead of the controlled enums.
