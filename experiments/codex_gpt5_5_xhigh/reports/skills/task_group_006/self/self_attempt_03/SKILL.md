---
name: procureops-reconciliation
description: Solve ProcureOps procurement, receiving, AP, contract-change, and payment-release reconciliation tasks using the live API plus task-local payloads, with exact JSON outputs.
---

# ProcureOps Reconciliation SOP

Use this skill for tasks that ask for ProcureOps readiness, receiving closeout, AP close, contract-change, or payment-release decisions. The usual deliverable is a single JSON object matching a task-local `answer_template.json`.

## Allowed Inputs And API Setup

- Read the prompt, the task-local answer template, and local payload files named by the prompt.
- Treat local payloads as scope hints and special business rules. Treat the ProcureOps API as the system of record for operational records.
- Use the base URL supplied by the runner or environment instructions. Start with `GET /`; endpoint names may differ from prose examples. In this environment family, AP and payments endpoints are exposed as `/ap_invoices` and `/payments`, not slash paths such as `/ap/invoices`.
- API collection responses are wrapped as:

```json
{"count": 0, "results": []}
```

- Pull relevant endpoint data and filter locally when needed. Do not inspect hidden outputs, evaluator files, environment source, judge APIs, or previous generated answers.

## Core Endpoint Map

Join records by these stable keys:

- `programs`: `program_id`, `owner`, `budget_cap`, `committed_amount`, status.
- `budget_snapshots`: `snapshot_id`, `program_id`, `snapshot_date`, `budget_cap`, `committed_amount`, `pending_invoice_amount`, currency.
- `suppliers`: `supplier_id`, `name`, `status`, `risk_rating`, payment terms.
- `items`: `sku`, description, category, preferred supplier, standard cost.
- `contracts`: `contract_id`, `program_id`, `supplier_id`, `sku`, status, `price_type`, `unit_price`, `ceiling_amount`.
- `purchase_requisitions`: `requisition_id`, `program_id`, `sku`, quantity, status, `need_by`.
- `purchase_orders`: `po_id`, `program_id`, `requisition_id`, `contract_id`, `supplier_id`, status, dates, `subtotal`, `tax`, `total`, `lines[]`.
- `receipts`: `receipt_id`, `po_id`, `supplier_id`, `receipt_date`, status, warehouse, packing slip, receiver, `lines[]`.
- `ap_invoices`: `invoice_id`, `po_id`, `receipt_id`, `supplier_id`, status, `hold_code`, `freight`, `subtotal`, `tax`, `total`, `lines[]`.
- `payments`: `payment_id`, `invoice_id`, `supplier_id`, status, `scheduled_date`, amount.
- `approval_events`: `event_id`, `object_type`, `object_id`, `event_date`, actor, action, note code.
- `vendor_risk_events`: `event_id`, `supplier_id`, `related_object_id`, `event_date`, status, severity, event type.

Line joins:

- PO lines use `line_id`.
- Receipt and AP lines use `po_line_id`.
- Also verify `sku` when joining a PO line to a receipt or invoice line.

## Output Discipline

- Return only the JSON object unless the user explicitly asks otherwise.
- Match the answer template exactly: required keys, allowed enum values, list ordering, nullability, numeric precision, and task IDs.
- Emit numbers as numbers, not strings, when the template says number.
- Sort IDs ascending when the template says sorted. Treat set-like fields as de-duplicated.
- Use `null` only when the template allows it.
- Round USD amounts to cents. Round ratios and percentages to the exact precision requested.
- Before finalizing, verify every evidence ID in the output exists in an API record or an allowed local payload.

## Date And Scope Rules

- Respect the task's `as_of`, close, or review date. Ignore receipts, invoices, approvals, payments, and risk events after that date unless the prompt explicitly includes a future cutoff.
- If a task names target invoices, POs, receipts, programs, or batches, keep calculations to that slice unless the template asks for broader context such as total contract usage.
- When an invoice has a `receipt_id`, use that receipt for invoice-level received quantity unless the task asks for all receipts on the PO.
- When an invoice has no `receipt_id`, invoice-level received quantity is usually `0.00` for AP close-style variance checks, even if unrelated receipts exist elsewhere.
- For receiving-batch tasks, reconcile the named receipt batch, not every receipt on the PO.
- For payment cutoff rules, include scheduled or already-paid payment records with dates on or before the cutoff and tied to the target invoices.
- For latest approval state, sort by `event_date` and use `event_id` as a tie-breaker if needed.
- Active supplier risk normally means status `open` or `monitoring`; status `closed` is not active. Severe active risk is an active event with high/severe severity, depending on the values present.

## Standard Calculations

Budget:

- Program headroom from a program or snapshot is `budget_cap - committed_amount`.
- Remaining budget in change-control work is the same headroom unless the task gives a different rule.
- Requested subtotal is `requested_quantity * unit_price`.
- Requested tax is `requested_subtotal * tax_rate`.
- Requested total is subtotal plus tax plus freight only when the local memo says freight is included.
- `budget_after_change = remaining_budget - requested_total`.
- `max_quantity_with_current_budget = floor(remaining_budget / (unit_price * (1 + tax_rate)))` when budget exposure includes tax and no freight.

Contract:

- Contract usage for a ceiling check is the sum of `subtotal` across POs with the same `contract_id`, excluding cancelled POs when instructed.
- `headroom_before_change = ceiling_amount - noncancelled_subtotal`.
- `headroom_after_change = headroom_before_change - requested_subtotal`.
- `ceiling_ok` is true only when the after-change headroom is non-negative.
- Reject or block a change when the memo contract, SKU, supplier, or program do not match the live contract.

Quantity and price reconciliation:

- `ordered_qty` comes from the PO line.
- `received_qty` comes from the relevant receipt line's `quantity_received`.
- `rejected_qty` comes from `quantity_rejected`, defaulting to 0 only if the schema truly omits it.
- `billed_qty` comes from the invoice line's `quantity_billed`.
- `short_qty_vs_po = ordered_qty - received_qty`.
- `unreceived_billed_qty = max(billed_qty - received_qty, 0)`.
- `receipt_completion_ratio = received_qty / ordered_qty`.
- `quantity_variance = billed_qty - received_qty`.
- `quantity_variance_pct = quantity_variance / ordered_qty * 100`.
- Goods exposure is usually quantity times the PO unit price unless the template specifically asks for invoice or contract value.
- `contract_price_match` is true only when PO/invoice unit price matches the contract unit price for the same SKU and supplier.

Invoice and payment amounts:

- Prefer API invoice `subtotal`, `freight`, `tax`, and `total` for financial output. Use line math mainly to validate variances.
- Vendor close balance in a target slice is `opening_balance + target_invoice_total - scheduled_payments`.
- Net release after an approved chargeback is `invoice_total - approved_chargeback_amount`.
- Chargeback amount from a local register is `basis_quantity * unit_cost`; split approved and pending amounts by the register status.

## Decision Patterns

Sourcing nomination readiness:

- Package anchors come from the local memo; enrich them with live requisition, PO, contract, receipt, invoice, supplier, budget, and risk records.
- `commercial_basis_id` is normally the active contract ID when one exists; use `null` when no valid contract/basis is present.
- Receipt evidence should be receipt IDs tied to the scoped PO and dated on or before the as-of date.
- Invoice exceptions should be AP invoice IDs tied to the scoped PO with hold, pending, receipt, price, or quantity issues as of the date.
- Risk evidence should be active supplier-risk event IDs for the selected supplier as of the date.
- Blocker mapping:
  - `missing_contract`: no active valid contract or commercial basis.
  - `supplier_watch`: supplier risk rating is watch when the template treats watch as a blocker.
  - `open_supplier_risk`: active risk event exists.
  - `ap_hold`: invoice is on hold, pending receipt, or has a hold code.
  - `pending_receipt`: no receipt, incomplete receipt, or PO still awaiting receipt.
  - `late_due_date`: due date is before the as-of date and delivery/receipt is not complete.
  - `none`: only when no other blocker applies.
- Use ready/nominate only for clean lines. Use conditional/at-risk for resolvable AP, receipt, watch, or non-severe risk issues. Use hold/not-ready for missing commercial basis, no receipt on a material AP hold, overdue unfulfilled PO, or severe active risk.

Receiving-control closeout:

- Reconcile the named receipt batch to its PO, supplier, contract, invoice, and risk context.
- Exception code mapping:
  - `INVOICE_QTY_EXCEEDS_RECEIPT`: billed quantity exceeds received quantity.
  - `PARTIAL_RECEIPT`: received quantity is less than ordered quantity.
  - `SUPPLIER_WATCH_RISK`: supplier risk rating is watch or the template flags watch risk.
  - `PRICE_MISMATCH`: PO, invoice, or contract unit prices differ.
  - `DAMAGE_REJECTION`: rejected quantity is positive or inspection/receipt status indicates damage/rejection.
  - `NO_EXCEPTION`: only when no other exception applies.
- Keep an invoice on hold when quantity, price, receipt, risk, or damage exceptions remain. Release only when the three-way match is clean and no task-specific hold remains.

AP close:

- Work only the invoices named by the close memo.
- Opening balance may be supplied by memo; do not infer prior balances outside the requested slice.
- `RELEASE` usually requires approved status, a valid receipt, no quantity variance, and no hold code.
- `HOLD` applies for missing receipt, quantity variance, or unresolved hold code.
- Reason code mapping:
  - `APPROVED_THREE_WAY_MATCH`: approved invoice, receipt evidence, billed quantity equals received quantity.
  - `NO_RECEIPT`: invoice has no receipt evidence where one is required.
  - `QTY_VARIANCE`: billed quantity differs from received quantity.
  - `SCHEDULED_PAYMENT_FOUND`: a payment for the target invoice is scheduled within the cutoff.
- `held_invoice_total` and `releasable_invoice_total` should follow the computed hold decision, not just raw invoice status.

Contract-change control:

- Validate live contract, program budget snapshot, latest approval event for the source requisition, supplier status, and active supplier risk.
- Decision priority:
  1. Contract, SKU, supplier, or program mismatch -> `reject_contract_mismatch`.
  2. Budget and approval both fail -> combined budget/approval hold when the template provides it.
  3. Budget fails -> budget hold.
  4. Approval fails -> approval hold.
  5. Severe active supplier risk -> supplier-risk hold.
  6. Otherwise release the amendment.
- Required actions should mirror the blockers. Use `none` only when there are no blockers.
- Approval is OK only when the latest relevant event action is in the memo's good-action list, commonly `approved`.

Receiving/AP release with chargebacks:

- Use local packet target IDs as the scope. If the packet says stale aliases are absent, use the live generated IDs listed in the packet.
- For each target invoice, join to its PO and the in-scope receipt IDs for that PO. Receipts on the same PO but outside the packet are supporting/excluded, not primary release evidence, unless the template asks for them.
- Approved chargebacks reduce the releasable amount. Pending quality chargebacks keep the invoice on hold.
- Missing receipt evidence produces a missing-receipt hold.
- Typical decision mapping:
  - Approved chargeback or approved AP quantity variance -> release net of approved chargeback.
  - No receipt on the PO/invoice -> hold for missing receipt.
  - Inspection hold or pending quality chargeback -> hold for quality chargeback.
- Summary queues should be derived from per-invoice decisions, not copied from raw invoice statuses.

## Common Pitfalls

- Do not use prompt examples of endpoint paths until confirming `GET /`.
- Do not accidentally include later receipts or duplicate same-PO receipts in an as-of invoice check.
- Do not count cancelled POs in contract ceiling usage when the memo says to exclude them.
- Do not let a supplier-level active risk event disappear just because it is related to a different PO, unless the template explicitly limits risk to a related object.
- Do not mark `NO_EXCEPTION` or `none` alongside real exception/blocker codes.
- Do not include narrative fields when the template expects controlled enum codes.
- Do not make list ordering depend on API order; sort by the template rule.
