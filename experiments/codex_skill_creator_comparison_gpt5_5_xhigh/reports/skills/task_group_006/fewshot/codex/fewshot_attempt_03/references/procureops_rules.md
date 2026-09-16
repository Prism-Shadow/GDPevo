# ProcureOps Rules

Use these rules as a checklist. The prompt and answer template always override this reference.

## Contents

- [Endpoint Shapes](#endpoint-shapes)
- [Date Handling](#date-handling)
- [Quantities](#quantities)
- [Currency](#currency)
- [Nomination Readiness](#nomination-readiness)
- [Receiving And AP Close](#receiving-and-ap-close)
- [Change Control](#change-control)
- [Release And Chargeback Reviews](#release-and-chargeback-reviews)

## Endpoint Shapes

ProcureOps collection endpoints return JSON shaped as:

```json
{"count": 0, "results": []}
```

Common endpoints and join keys:

- `/suppliers`: `supplier_id`, `name`, `status`, `risk_rating`, payment terms.
- `/items`: `sku`, `preferred_supplier_id`, `standard_cost`, `active`.
- `/programs`: `program_id`, `owner`, `budget_cap`, `committed_amount`, status.
- `/contracts`: `contract_id`, `program_id`, `supplier_id`, `sku`, `status`, `price_type`, `unit_price`, `ceiling_amount`.
- `/purchase_requisitions`: `requisition_id`, `program_id`, `sku`, `quantity`, `need_by`, `status`.
- `/purchase_orders`: `po_id`, `program_id`, `supplier_id`, `contract_id`, `requisition_id`, `status`, `due_date`, `lines`, `subtotal`, `tax`, `total`.
- `/receipts`: `receipt_id`, `po_id`, `supplier_id`, `status`, `receipt_date`, `warehouse_id`, `lines`.
- `/ap/invoices`: `invoice_id`, `po_id`, `receipt_id`, `supplier_id`, `status`, `hold_code`, `lines`, `subtotal`, `freight`, `tax`, `total`.
- `/ap/payments`: `payment_id`, `invoice_id`, `supplier_id`, `status`, `scheduled_date`, `amount`.
- `/approvals`: `event_id`, `object_id`, `object_type`, `action`, `actor`, `event_date`.
- `/budget_snapshots`: `snapshot_id`, `program_id`, `snapshot_date`, `budget_cap`, `committed_amount`, `pending_invoice_amount`.
- `/vendor_risk_events`: `event_id`, `supplier_id`, `related_object_id`, `status`, `severity`, `event_date`.

## Date Handling

- As-of reviews: include receipts, invoices, approvals, budget snapshots, and risk events only when their relevant date is on or before the review date.
- Payment-close tasks may specify a future payment horizon; include scheduled or released payments through that horizon when the prompt says scheduled payments reduce balance. Exclude blocked payments unless the template explicitly asks for them.
- Choose the latest approval or budget snapshot by date, breaking ties by ID when needed.

## Quantities

- Match PO, receipt, and invoice lines by `po_line_id` when present, otherwise by `sku`.
- `ordered_qty` comes from the PO line.
- `received_qty` is the sum of in-scope receipt line `quantity_received`.
- `rejected_qty` is the sum of in-scope receipt line `quantity_rejected`, defaulting to zero.
- `billed_qty` is the sum of invoice line `quantity_billed` for the scoped invoice or invoice group.
- `short_qty_vs_po = ordered_qty - received_qty`.
- `unreceived_billed_qty = max(billed_qty - received_qty, 0)`.
- `receipt_completion_ratio = received_qty / ordered_qty` when ordered quantity is nonzero.
- `quantity_variance = billed_qty - received_qty`.
- `quantity_variance_pct = quantity_variance / ordered_qty * 100`.

## Currency

- Use API currency fields when present; examples use USD.
- Calculate with decimal values and round final currency fields to two decimals.
- Invoice total usually equals subtotal plus freight plus tax; prefer the API invoice `total` field when the template asks for invoice total.
- Received goods value is received quantity times PO unit price.
- Unreceived goods value is unreceived billed quantity times PO unit price.
- Contract price match is true when PO and invoice line prices match the contract unit price for the same SKU/supplier/program.

## Nomination Readiness

For sourcing nomination or readiness packets:

- Anchor package lines from the local payload, then verify the requisitions, POs, suppliers, contracts, receipts, invoices, budgets, and risks through the API.
- A commercial basis normally exists when the package PO has a non-null contract ID matching the line supplier and SKU.
- Receipt evidence IDs are accepted or accepted-with-note receipts for the scoped PO as of the review date.
- Invoice exception IDs are scoped AP invoices with hold-like statuses or hold codes as of the review date.
- Supplier risk IDs are open or monitoring events for the selected supplier as of the review date; include supplier-level events even when their related object is not the target PO if the template asks for supplier-risk context.
- Typical blocker codes:
  - `missing_contract`: no valid commercial basis for the selected PO/supplier/SKU.
  - `supplier_watch`: supplier risk rating is watch.
  - `open_supplier_risk`: at least one open or monitoring risk event.
  - `ap_hold`: at least one on-hold invoice or active hold code.
  - `pending_receipt`: no acceptable receipt evidence when receipt is required.
  - `late_due_date`: PO due date is later than the requisition need-by date or other stated need date.
  - `none`: only when no blockers apply.
- Map readiness conservatively: no blockers is ready; only controllable AP/risk watch issues is usually at risk; missing contract, missing receipt, late due date, severe supplier risk, or multiple blocking controls is not ready.

## Receiving And AP Close

For receiving closeout, invoice review, and close-balance tasks:

- Scope to target batches or invoices from the payload. Do not include other invoices on the same supplier unless the template asks for vendor-level history.
- Join invoice to PO, supplier, receipt, contract, payment, and risk records.
- Keep invoice on hold when billed quantity exceeds received quantity, no receipt exists, invoice status is hold-like, or hold code is present.
- Release when the invoice is approved, a three-way match is supported, and no active hold condition remains.
- Reason codes should be controlled values from the template, not prose.
- Vendor close balance is opening balance plus scoped invoice totals minus included scheduled payments.
- Supplier balance status is usually fully scheduled when close balance is zero, open held when any scoped invoice is held, otherwise open approved.
- Program summaries aggregate only scoped invoices unless the prompt states otherwise.

## Change Control

For contract amendment or modular change tasks:

- Verify the memo contract, supplier, SKU, program, and requisition against API records. Reject or hold if the API relationship does not match the requested change.
- Contract usage should exclude cancelled POs unless the local payload says otherwise.
- `headroom_before_change = ceiling_amount - noncancelled_contract_subtotal`.
- `requested_subtotal = requested_quantity * contract_unit_price`.
- `headroom_after_change = headroom_before_change - requested_subtotal`.
- Budget remaining is budget cap minus committed amount from the applicable program or budget snapshot.
- Budget exposure is line subtotal plus tax, and freight only if the local payload supplies freight or says to include it.
- `max_quantity_with_current_budget = floor(remaining_budget / unit_price_with_required_tax_or_freight)`.
- Approval is OK only when the latest relevant approval action is in the local payload's good-action list or the template's accepted state.
- Supplier risk is OK unless the supplier is inactive/on hold or an open severe risk event blocks release. Watch ratings can be context-only when the payload says so.
- Decision priority: contract mismatch first; then combined budget/approval holds; then single budget, approval, or supplier-risk holds; release only when all required checks pass.

## Release And Chargeback Reviews

For receiving/AP release files:

- Use local packet target IDs to determine the exact PO, receipt, and invoice scope.
- Use API PO, receipt, and AP records for invoice totals and receipt existence.
- Use local chargeback registers for chargeback reason, basis quantity, unit cost, and approval status when the API lacks those records.
- Chargeback amount is basis quantity times unit cost.
- Approved chargebacks reduce the release amount. Pending chargebacks hold the invoice unless the template says otherwise.
- If a target PO has no in-scope receipt, create the template's missing-receipt representation if required and hold the invoice for missing receipt.
- `receipt_ids_in_scope` are target receipt IDs that belong to the invoice or its PO. `excluded_same_po_receipt_ids` are same-PO API receipts outside the packet scope when the template asks for them.
- Receiving exception codes should come from the local chargeback reason, receipt status, and quantity comparison:
  - Underage quantity when received quantity is below ordered quantity or local chargeback reason says underage.
  - AP quantity variance when billed quantity exceeds received quantity or local chargeback reason says AP quantity variance.
  - Inspection hold when receipt status is inspection hold.
  - Severe unmatched quantity when the template/local packet marks the shortage as severe or the mismatch is material enough under the task's stated rules.
- Summary queues and totals aggregate the scoped decisions only.
