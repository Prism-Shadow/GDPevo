---
name: reflection-skill-attempt-02
description: Use for ProcureOps benchmark tasks that require reconciling procurement, receiving, AP, budget, approval, contract, and supplier-risk records from a local API into controlled JSON outputs.
---

# ProcureOps Workflow Skill

Use this skill when a task asks for a procurement control packet, AP close/release decision, sourcing nomination, change-control file, receiving reconciliation, or similar JSON answer from the ProcureOps API.

## Standard Workflow

1. Read the task prompt, local payloads, and answer template first.
2. Treat local payloads as task anchors only: target IDs, memo date, chargeback excerpts, and requested controlled vocabularies.
3. Treat the ProcureOps API as source of truth for programs, suppliers, items, contracts, requisitions, POs, receipts, invoices, payments, approvals, budget snapshots, and vendor risk.
4. Fetch the API root to confirm available endpoints. In this benchmark the public names are typically:
   `programs`, `suppliers`, `items`, `contracts`, `purchase_requisitions`, `purchase_orders`, `receipts`, `ap_invoices`, `payments`, `approval_events`, `budget_snapshots`, and `vendor_risk_events`.
5. Build joins from the local target IDs outward:
   invoice -> PO -> requisition/program/contract/supplier/receipt/payment/risk/approval.
6. Apply the answer template exactly. Return only JSON, preserve required enum strings, and sort lists where requested.

For local API access, use the supplied base URL, usually `http://127.0.0.1:8006`. If `curl` tries a proxy for localhost, retry with:

```bash
curl --noproxy "*" -sS http://127.0.0.1:8006/<endpoint>
```

## Field Definitions

Use these definitions consistently:

- `program budget headroom` or `remaining_budget`: `budget_cap - committed_amount`.
- `po quantity`: the quantity on the PO line for the target SKU.
- `received_qty`: sum target receipt line `quantity_received`; use `0.00` when no receipt exists.
- `rejected_qty`: receipt line `quantity_rejected`.
- `billed_qty`: invoice line `quantity_billed`.
- `short_qty_vs_po`: `ordered_qty - received_qty`.
- `unreceived_billed_qty`: `max(billed_qty - received_qty, 0)`.
- `receipt_completion_ratio`: `received_qty / ordered_qty`, rounded to the template precision.
- `quantity_variance`: `quantity_billed - quantity_received`.
- `quantity_variance_pct`: `quantity_variance / PO quantity * 100`.
- `received_goods_value`: `received_qty * PO unit_price`.
- `unreceived_goods_value`: `unreceived_billed_qty * PO unit_price`.
- `invoice_total`: API invoice `total`, which already includes freight and tax.
- `scheduled_payment_amount`: matching payment amount only when the task's date window and payment status qualify it.
- `net_balance_impact`: `invoice_total - scheduled_payment_amount`.
- `contract ceiling exposure`: requested subtotal before tax and freight.
- `budget exposure`: requested line subtotal plus estimated tax; include freight only if the memo provides freight.
- `max_quantity_with_current_budget`: floor of `remaining_budget / (unit_price * (1 + tax_rate))`.

Round USD amounts to cents unless the template specifies another precision.

## Business Rules

### Dates and Scope

- Use the task's `as_of`, `close_date`, or `review_as_of` as the cutoff.
- Include invoice exceptions by invoice date on or before the cutoff, even if their linked receipt is after the cutoff.
- Include receipt evidence only when the receipt date is on or before the cutoff and the receipt is in scope for the target PO.
- For vendor-risk lists, include supplier-wide events with status `open` or `monitoring` on or before the cutoff; exclude `closed`.
- Do not broaden AP close tasks beyond the named invoices. Opening balance is whatever the memo says, often `0.00` for the slice.

### Supplier Risk

- Supplier `risk_rating: watch` creates watch context and usually a `supplier_watch` or `SUPPLIER_WATCH_RISK` flag when the template has one.
- Open or monitoring vendor-risk events are supplier-wide unless the prompt narrows them to a PO.
- `severe_open_event_ids` means open or monitoring events with high severity.
- A watch rating alone is normally context only for change release; hold supplier risk only for supplier hold status or severe open risk.

### Nomination Readiness

- Select the supplier from the package PO or contract, not from the item preferred supplier if the PO already exists.
- `commercial_basis_id` is the active matching contract ID; use `null` when no matching contract exists.
- `late_due_date` means the PO due date is after the requisition `need_by` date.
- Use `missing_contract` when the PO has no matching contract for the line.
- Use `pending_receipt` when there is no receipt evidence for the package PO by the cutoff.
- Use `ap_hold` for non-receipt AP hold problems; a no-receipt invoice is represented by `pending_receipt` rather than a separate `ap_hold` blocker.
- Overall readiness is `not_ready` if any line is held, `at_risk` if no holds but any conditional line exists, otherwise `ready`.
- Committee owner should follow the dominant blocker; AP exception packets commonly go to `ap_team`.

### Receiving Reconciliation

- Join receipt -> PO -> supplier -> contract -> invoice.
- `INVOICE_QTY_EXCEEDS_RECEIPT` applies when billed quantity exceeds received quantity.
- `PARTIAL_RECEIPT` applies when received quantity is less than PO quantity.
- `PRICE_MISMATCH` applies when invoice or PO unit price differs from the contract unit price.
- `DAMAGE_REJECTION` applies when receipt rejected quantity is positive or inspection indicates damage/variance that the task maps to damage.
- Keep the invoice on hold for quantity or receipt exceptions; do not release just because the receipt status is accepted.

### AP Close

- Match payments by invoice ID.
- Reduce the close balance only for scheduled payments inside the task's through date; do not reduce for absent, blocked, or out-of-window payments.
- `APPROVED_THREE_WAY_MATCH`: approved invoice, matching PO/receipt quantity, and no hold code.
- `NO_RECEIPT`: invoice has no usable receipt; do not also add `QTY_VARIANCE` unless the template explicitly asks for every mathematical variance.
- `QTY_VARIANCE`: billed quantity differs from received quantity when a receipt exists.
- `SCHEDULED_PAYMENT_FOUND`: a qualifying payment record reduces the invoice balance.
- Vendor balance status:
  - `FULLY_SCHEDULED`: close balance is zero because qualifying payments equal invoice total.
  - `OPEN_HELD`: held invoice total is positive.
  - `OPEN_APPROVED`: releasable balance remains but is not fully scheduled.

### Change Control

- Verify contract ID, supplier ID, program ID, SKU, status, unit price, and ceiling.
- Existing contract usage excludes cancelled POs; include confirmed, open, partial receipt, received, closed, and other noncancelled statuses.
- Approval status uses the latest approval event for the source requisition by event date. Only `approved` is approval-ok unless the memo says otherwise.
- Budget check uses the budget snapshot for the program and the memo tax rule.
- Decision priority:
  - contract mismatch -> `reject_contract_mismatch`
  - budget and approval fail -> `hold_for_budget_and_approval`
  - budget fail only -> `hold_for_budget`
  - approval fail only -> `hold_for_approval`
  - severe supplier risk fail -> `hold_for_supplier_risk`
  - all checks pass -> `release_amendment`

### AP Release With Chargebacks

- Local chargeback registers are authoritative for chargeback status and basis amount when the prompt provides them.
- Approved chargeback amount is `basis_quantity * unit_cost` for approved rows.
- Pending chargebacks do not reduce net release; they hold the invoice when quality review is pending.
- `net_release_amount`: `invoice_total - approved_chargeback_amount` for released invoices, otherwise `0.00`.
- Include only named target receipts in `receipt_ids_in_scope`.
- Same-PO receipts not named in the packet but present by the review date go in `excluded_same_po_receipt_ids`.
- If a target PO has no receipt, add a receiving exception row with `receipt_id` as `MISSING:<po_id>`, `chargeback_status: not_applicable`, and `resolution_status: missing_receipt`.
- Use `Severe Unmatched Quantity` when a target receipt/invoice pair has a material underage or unmatched quantity exception in the packet's chargeback context.

## Common Pitfalls

- Do not use `/ap/invoices` if the API root exposes `ap_invoices`; follow the root endpoint names.
- Do not trust local aliases when the packet says shared generated IDs should be used.
- Do not ignore invoices dated before the cutoff just because their receipt appears after the cutoff.
- Do not treat closed vendor-risk events as active risk.
- Do not limit supplier risk to the target PO unless the template says so.
- Do not include cancelled POs in contract ceiling usage.
- Do not subtract payments that are blocked, absent, or outside the task's payment window.
- Do not release an AP invoice solely because the receipt status is accepted; quantity, AP hold, and chargeback state still control release.
- Do not omit evidence/source IDs when the template asks for them; include API record IDs such as supplier, SKU, contract, PO, receipt, invoice, and risk event IDs used in the answer.
