---
name: reflection-skill-attempt-01
description: Use for ProcureOps benchmark tasks that require joining local procurement task payloads with the ProcureOps API to produce exact JSON answers for sourcing readiness, receiving/AP holds, invoice close, contract changes, budget checks, approvals, supplier risk, and chargeback netting.
---

# ProcureOps Workflow Skill

## Scope

Use this skill when a task provides local `input/prompt.txt`, `input/payloads/*`, and a ProcureOps API base URL. The API is the system of record for operational data; local payloads define target IDs, task-specific rules, chargeback excerpts, and the required output shape.

Return only JSON when the prompt asks for JSON. Match the template keys, enum values, ordering, rounding, and ID spelling exactly.

## Standard SOP

1. Read the task prompt, answer template, and all files under the task's `input/payloads/`.
2. Extract target anchors: program IDs, PO IDs, receipt IDs, invoice IDs, requisition IDs, contract IDs, supplier IDs, SKUs, dates, and special local registers.
3. Query the API root to confirm endpoint names. In this group, use endpoints such as:
   - `/programs`
   - `/suppliers`
   - `/items`
   - `/contracts`
   - `/purchase_requisitions`
   - `/purchase_orders`
   - `/receipts`
   - `/ap_invoices`
   - `/payments`
   - `/approval_events`
   - `/budget_snapshots`
   - `/vendor_risk_events`
4. Prefer filtered API calls when supported, for example `?po_id=...`, `?invoice_id=...`, `?supplier_id=...`, `?object_id=...`, or `?program_id=...`.
5. Build joins by stable IDs, not names:
   - invoice -> PO by `po_id`
   - invoice -> receipt by `receipt_id` when present
   - receipt -> PO by `po_id`
   - PO -> contract by `contract_id`
   - PO -> requisition by `requisition_id`
   - PO/invoice/contract -> supplier by `supplier_id`
   - program -> budget snapshot by `program_id`
   - approval events -> requisition by `object_id`
6. Apply any as-of date from the prompt or payload. Use it for records explicitly described as as-of sensitive, especially receipt evidence, invoice exceptions, approval latest state, and open or monitoring risk events.
7. Calculate all numeric fields from API/local records, then round money to cents. Preserve integer quantities unless the template asks for decimal precision.
8. Sort list fields when the template says sorted or set-like. Common ordering is ID ascending; invoice and supplier balance rows are often sorted by ID.
9. Validate the final JSON against the answer template mentally before responding: required keys, enum values, nullability, precision, and list ordering.

## Endpoint Field Map

`programs`: `program_id`, `owner`, `budget_cap`, `committed_amount`, `status`, `priority`, `cost_center`.

`budget_snapshots`: `snapshot_id`, `program_id`, `budget_cap`, `committed_amount`, `pending_invoice_amount`, `currency`, `snapshot_date`.

`suppliers`: `supplier_id`, `name`, `status`, `risk_rating`, `payment_terms`, `region`.

`items`: `sku`, `description`, `preferred_supplier_id`, `standard_cost`, `uom`, `active`.

`contracts`: `contract_id`, `program_id`, `supplier_id`, `sku`, `status`, `price_type`, `unit_price`, `ceiling_amount`, dates, buyer.

`purchase_requisitions`: `requisition_id`, `program_id`, `sku`, `quantity`, `need_by`, `status`, `priority`, `requester`.

`purchase_orders`: `po_id`, `program_id`, `supplier_id`, `contract_id`, `requisition_id`, `status`, `due_date`, `ship_to`, `lines`, `subtotal`, `tax`, `total`, `currency`.

`receipts`: `receipt_id`, `po_id`, `supplier_id`, `warehouse_id`, `receipt_date`, `status`, `packing_slip`, `receiver`, `lines[].quantity_received`, `lines[].quantity_rejected`, `lines[].inspection_status`.

`ap_invoices`: `invoice_id`, `po_id`, `receipt_id`, `supplier_id`, `status`, `hold_code`, `invoice_date`, `lines[].quantity_billed`, `lines[].unit_price`, `subtotal`, `freight`, `tax`, `total`.

`payments`: `payment_id`, `invoice_id`, `supplier_id`, `status`, `scheduled_date`, `amount`.

`approval_events`: `event_id`, `object_id`, `object_type`, `action`, `actor`, `event_date`, `note_code`.

`vendor_risk_events`: `event_id`, `supplier_id`, `status`, `severity`, `event_type`, `event_date`, `related_object_id`.

## Business Rules

### General

- The API overrides memo text for operational facts. Local payloads override the API for task-specific target scope, chargeback excerpts, stale alias notes, and requested business controls.
- Treat supplier risk events as supplier-level context unless the template explicitly restricts to the related PO. Open/monitoring events for the same supplier can matter even when `related_object_id` is a different PO.
- `open_supplier_risk` means supplier risk event status is `open` or `monitoring` as of the relevant date.
- `supplier_watch` comes from supplier `risk_rating == "watch"`.
- High or severe supplier-risk blockers usually require an open/monitoring event with severe/high severity. A watch rating alone may be context only in change-control tasks.
- For latest approval, use the latest event for the source requisition as of the review date. Only actions explicitly listed as good actions, usually `approved`, satisfy approval.

### Sourcing Nomination Readiness

- Package memos name anchor SKUs, requisitions, and POs; use those anchors to select suppliers from the PO records.
- `commercial_basis_id` is the PO or line contract ID, or `null` if no contract exists.
- `receipt_evidence_ids` are same-PO receipts on or before the as-of date.
- `invoice_exception_ids` include same-PO invoice records on or before the as-of date that are on hold or pending/exceptional; include more than the memo-named invoice when same-PO exceptions exist.
- Use requisition `need_by` versus PO `due_date` for `late_due_date`; a PO due after the requisition need-by date is late even when the calendar as-of date is earlier.
- Use `pending_receipt` when the line has no receipt evidence or an invoice is pending receipt. Do not also label this as `ap_hold` unless the exception is an AP hold such as quantity or price variance.
- Readiness is worst-line driven:
  - missing contract, pending receipt, late due date, or severe unresolved blockers usually produce `hold` / `not_ready`.
  - AP holds, watch rating, or open supplier risk with otherwise usable evidence usually produce `conditional_nomination` / `at_risk`.
  - no blockers means `nominate` / `ready`.
- Committee action queues supplier IDs by decision. If any line is held or conditional, `send_to_committee` is usually `no`; choose `next_owner` from the dominant blocker owner, often `ap_team` for AP holds.

### Receiving And AP Hold Reconciliation

- Use the receipt/batch under review and its linked PO, supplier, contract, and invoice.
- Ordered quantity comes from the PO line. Received and rejected quantities come from the receipt line. Billed quantity and invoice unit price come from the invoice line.
- `short_qty_vs_po = ordered_qty - received_qty`.
- `unreceived_billed_qty = max(billed_qty - received_qty, 0)`.
- `receipt_completion_ratio = received_qty / ordered_qty`, rounded to the template precision.
- Received goods value is `received_qty * PO unit_price`; unreceived goods value is `unreceived_billed_qty * PO unit_price`.
- Contract price match compares PO/invoice unit price to the contract unit price for the PO contract.
- Exception codes:
  - `INVOICE_QTY_EXCEEDS_RECEIPT` when billed quantity exceeds received quantity.
  - `PARTIAL_RECEIPT` when received quantity is below ordered quantity or PO status is partial.
  - `SUPPLIER_WATCH_RISK` when the supplier is watch-rated or has open supplier risk.
  - `PRICE_MISMATCH` when invoice/PO/contract unit prices conflict.
  - `DAMAGE_REJECTION` when rejected quantity or damage/inspection status indicates rejection.
  - `NO_EXCEPTION` only when no other exception applies.
- Keep the invoice on hold for unresolved quantity, receipt, supplier-risk, or inspection exceptions.

### AP Close And Vendor Balances

- Restrict the close to the target invoice IDs only. Do not include other invoices for the same supplier unless the prompt says so.
- Opening balance may be supplied locally; apply it exactly.
- Quantity received for invoice decisions should come from the invoice-linked receipt when present. If the target invoice has no receipt, use `0.00` unless the task explicitly asks for PO-wide received quantity.
- `quantity_variance = quantity_billed - quantity_received`.
- `quantity_variance_pct = quantity_variance / PO ordered quantity * 100`, rounded as requested.
- Scheduled payments through the close horizon reduce balance for the target invoice. Use payments linked to that invoice and dated on or before the horizon.
- `net_balance_impact = invoice_total - scheduled_payment_amount`.
- Reason codes are controlled:
  - `APPROVED_THREE_WAY_MATCH` for approved invoice with matched PO/receipt quantity.
  - `SCHEDULED_PAYMENT_FOUND` when a qualifying scheduled payment exists.
  - `QTY_VARIANCE` for billed quantity above receipt or other quantity variance.
  - `NO_RECEIPT` when no receipt supports the invoice.
- Vendor balance status:
  - `FULLY_SCHEDULED` when target invoice balance is fully offset by scheduled payments.
  - `OPEN_HELD` when held invoices leave an open balance.
  - `OPEN_APPROVED` when releasable approved invoices remain unscheduled.

### Contract Change, Budget, And Approval

- Contract ceiling exposure uses line subtotal before tax and freight.
- Existing contract usage includes all non-cancelled POs on the contract, not just POs named in the memo. Exclude cancelled POs and list them separately when requested.
- `headroom_before_change = ceiling_amount - noncancelled_subtotal`.
- `requested_subtotal = requested_quantity * contract.unit_price`.
- `headroom_after_change = headroom_before_change - requested_subtotal`.
- Budget exposure follows the local memo. If it says line subtotal plus estimated tax and freight only when provided, compute `requested_total = subtotal + tax` unless local freight is specified.
- `remaining_budget = budget_cap - committed_amount`.
- `budget_after_change = remaining_budget - requested_total`.
- `max_quantity_with_current_budget = floor(remaining_budget / (unit_price * (1 + tax_rate)))` when budget exposure is unit subtotal plus tax.
- Decision priority:
  - contract mismatch or inactive/missing contract can reject.
  - failed budget and approval checks produce `hold_for_budget_and_approval`.
  - failed budget alone produces `hold_for_budget`.
  - failed approval alone produces `hold_for_approval`.
  - severe open supplier risk produces `hold_for_supplier_risk`.
  - all checks passing produces `release_amendment`.

### Receiving/AP Release With Chargebacks

- Use local target IDs exactly. If the packet says stale PO alias IDs are not present, use the generated PO/receipt IDs supplied in the packet.
- Local chargeback register entries are authoritative for chargeback ID, reason, basis quantity, unit cost, and status.
- Approved chargeback amount is `basis_quantity * unit_cost` for approved entries. Pending chargeback amount is the same calculation for pending entries.
- `net_release_amount = invoice_total - approved_chargeback_amount` only for release decisions. Use `0.00` for held missing-receipt or pending-quality decisions.
- Release decisions:
  - approved underage quantity chargeback -> `release_net_after_approved_chargeback` / `approved_qty_chargeback`.
  - approved AP quantity variance chargeback -> `release_net_after_approved_chargeback` / `approved_ap_quantity_variance`.
  - no receipt on target PO -> `hold_missing_receipt` / `no_receipt_on_po`.
  - inspection hold with pending quality chargeback -> `hold_pending_quality_chargeback` / `inspection_hold_pending_chargeback`.
- `receipt_ids_in_scope` should be the target receipt(s) used for that invoice/PO. Same-PO receipts outside the target or separate invoice scope belong in `excluded_same_po_receipt_ids`.
- Include a synthetic receiving exception row like `MISSING:<po_id>` when the target PO has no receipt and the template needs a receipt-like row.
- Receiving exception codes:
  - `Underage Quantity` when receipt quantity is less than PO ordered quantity.
  - `AP Quantity Variance` when invoice billed quantity exceeds received quantity while the receipt itself matches the PO.
  - `Inspection Hold` when receipt status is inspection hold.
  - `Severe Unmatched Quantity` for material underage/unmatched receipt cases in release packets.
- Summary totals are the sums of release/hold rows after chargeback classification.

## Common Pitfalls

- Do not use `/ap/invoices` if the API root advertises `/ap_invoices`.
- Do not trust local narrative comments that a receipt exists when the API target PO has no receipt.
- Do not count later same-PO receipts as evidence when an as-of date or target receipt scope excludes them; list them as excluded only when the template asks.
- Do not omit same-PO invoice exceptions just because they were not named in the memo.
- Do not treat supplier watch as automatically severe supplier risk in contract-change decisions.
- Do not include cancelled POs in contract ceiling usage.
- Do not include non-target invoices or payments in close-slice vendor balances.
- Do not subtract payments scheduled after the task's payment horizon.
- Do not use PO tax/total when the invoice has freight; invoice total is invoice subtotal plus invoice freight plus invoice tax.
- Do not output prose, comments, or markdown around the final JSON.
