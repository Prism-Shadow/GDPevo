# ProcureOps Rules

## Core Joins

- Join suppliers by `supplier_id`; use `name`, `status`, and `risk_rating` for supplier context.
- Join items by `sku`; use `preferred_supplier_id` only as context unless the prompt asks for preferred sourcing.
- Join programs and budget snapshots by `program_id`. Prefer the budget snapshot whose `snapshot_date` is on or before the review date and closest to it; fall back to the program budget fields only when no snapshot exists.
- Join contracts by `contract_id` when a payload names one. Otherwise find active contracts matching `program_id`, `supplier_id`, and `sku`, with effective/expiry dates covering the review date.
- Join requisitions by `requisition_id` or by the PO's `requisition_id`.
- Join POs by `po_id`; line calculations come from `lines[*]` by `line_id`, `po_line_id`, or `sku`.
- Join receipts by `receipt_id` or by `po_id`; line calculations come from `lines[*]` by `po_line_id` and `sku`.
- Join invoices by `invoice_id` or by `po_id`; line calculations come from `lines[*]`.
- Join payments by `invoice_id`; include only scheduled/released payments within the date window stated in the prompt or memo.
- Join approval events by `object_id` and `object_type`; latest means the greatest `event_date`, with `event_id` as a deterministic tie-breaker.
- Join vendor risk events by `supplier_id`. A risk event is active for an as-of review when its `status` is `open` or `monitoring` and its `event_date` is on or before the review date.

## General Calculations

- Round currency to two decimals at the output boundary. Keep intermediate math unrounded when practical.
- Received quantity is the sum of relevant receipt line `quantity_received` values. Rejected quantity is the sum of `quantity_rejected` values.
- Billed quantity is the sum of relevant invoice line `quantity_billed` values.
- Quantity variance is billed quantity minus received quantity unless the template defines a different direction.
- Receipt completion ratio is received quantity divided by PO ordered quantity.
- Quantity variance percentage for close tasks is quantity variance divided by PO ordered quantity times 100.
- Contract price match is true when the PO or invoice unit price equals the contract unit price for the same SKU, after cent rounding.
- Received goods value is received quantity times PO unit price. Unreceived goods value is max(ordered quantity minus received quantity, 0) times PO unit price unless the template asks for billed-over-received exposure.

## AP Close And Payment Holds

Use target invoice IDs from the memo or payload; do not widen the slice unless instructed.

- `HOLD`: invoice status indicates hold/pending receipt, no matching receipt exists, or billed quantity exceeds received quantity.
- `RELEASE`: invoice is approved and has a clean three-way match, or the template's release criteria are otherwise satisfied.
- Reason codes:
  - `NO_RECEIPT`: no in-scope receipt for the invoice or PO.
  - `QTY_VARIANCE`: billed quantity exceeds received quantity or the invoice hold code indicates a quantity variance.
  - `APPROVED_THREE_WAY_MATCH`: approved invoice with billed quantity matching received quantity and PO terms.
  - `SCHEDULED_PAYMENT_FOUND`: an in-window scheduled or released payment exists for the invoice.
- Scheduled payment amount is the sum of in-window payments for the invoice.
- Net balance impact is invoice total minus scheduled payment amount.
- Vendor close balance is opening balance plus target invoice total minus in-window scheduled payments.
- Vendor balance status is `FULLY_SCHEDULED` when the close balance is zero because payments cover the target invoice total, `OPEN_HELD` when held invoice total remains, and `OPEN_APPROVED` when releasable unpaid invoice total remains.

## Receiving Closeout

For a receiving batch, use the named receipt as the batch anchor and join to its PO, supplier, contract, and invoice.

- Add `INVOICE_QTY_EXCEEDS_RECEIPT` when billed quantity is greater than received quantity.
- Add `PARTIAL_RECEIPT` when received quantity is less than PO ordered quantity.
- Add `SUPPLIER_WATCH_RISK` when the supplier risk rating is watch or worse, or when an active supplier risk event exists.
- Add `PRICE_MISMATCH` when invoice, PO, and contract unit prices do not match.
- Add `DAMAGE_REJECTION` when rejected quantity is positive or inspection status indicates damage/rejection.
- Use `NO_EXCEPTION` only when no other exception applies.
- Keep AP on hold and request shortage or supplier follow-up when there is an invoice quantity variance or partial receipt. Release only when receipt, invoice, PO, contract, and risk checks are clean under the template rules.

## AP Release With Chargebacks

Use local chargeback/register payloads for chargeback amount and status when provided; the API remains authoritative for invoice, PO, and receipt existence and totals.

- Chargeback amount is basis quantity times unit cost.
- Approved chargebacks reduce the release amount: net release equals invoice total minus approved chargeback amount.
- Pending quality chargebacks block release and contribute to pending chargeback total.
- If no in-scope receipt exists for a target PO/invoice, hold the invoice for missing receipt. When the template needs a receiving-exception row, use a deterministic missing marker based on the PO ID if no receipt ID exists.
- Exclude same-PO receipts that are not named in target receipt IDs unless the template asks to include all receipts for that PO.
- Typical decisions:
  - `release_net_after_approved_chargeback`: only approved chargeback exceptions remain.
  - `hold_pending_quality_chargeback`: a receipt or chargeback is still in quality review or inspection hold.
  - `hold_missing_receipt`: the API has no in-scope receipt for the target PO.

## Contract Change Control

For amendment or modular-change tasks:

- Verify the requested contract matches the requested `program_id`, `supplier_id`, and `sku`. If not, use the template's contract-mismatch rejection.
- Contract usage is the subtotal of non-cancelled PO lines tied to the contract unless the memo states another basis.
- Requested subtotal is requested quantity times contract unit price.
- Contract headroom before change is ceiling amount minus existing non-cancelled usage.
- Contract headroom after change is headroom before change minus requested subtotal.
- Budget remaining is budget cap minus committed amount from the chosen snapshot.
- Budget exposure is requested subtotal plus estimated tax, plus freight only when the memo provides freight.
- Maximum quantity with current budget is floor(remaining budget divided by per-unit budget exposure).
- Approval is OK only when the latest approval event action is one of the memo's allowed good actions.
- Supplier watch is context only when the memo says so; block supplier risk only for active severe events or when the template business rules make risk blocking.
- Decision priority: contract mismatch, combined budget and approval hold, budget hold, approval hold, supplier-risk hold, then release.
- Required actions should mirror the blockers and use `none` only when there are no blockers.

## Sourcing Nomination Readiness

Use package anchors from the memo or payload to identify target SKUs, requisitions, POs, and suppliers.

- Commercial basis is the active matching contract ID, or null if none exists.
- Receipt evidence includes in-scope receipts for package POs on or before the as-of date.
- Invoice exception IDs include in-scope invoices on or before the as-of date whose status or hold code indicates unresolved AP work.
- Risk event IDs include active supplier risk events as of the review date.
- Blocker codes:
  - `missing_contract`: no active matching contract.
  - `supplier_watch`: supplier risk rating is watch.
  - `open_supplier_risk`: active supplier risk event exists.
  - `ap_hold`: unresolved invoice hold/exception exists.
  - `pending_receipt`: no acceptable receipt evidence for the PO by the as-of date.
  - `late_due_date`: PO due date is before the as-of date while receipt evidence is incomplete.
  - `none`: only when no other blocker applies.
- Readiness and decision:
  - Ready/nominate when no blockers remain.
  - At risk/conditional nomination when contractual and receipt basics are present but AP or supplier-risk blockers remain.
  - Not ready/hold when contract is missing, receipt is missing/pending, due date is late with missing receipt, or other blocking controls prevent release.
- Committee queues are supplier ID sets derived from line decisions. Pick the next owner from the dominant unresolved blocker: AP holds to AP, missing receipt or due-date receipt issues to receiving/quality/program owner per template choices, missing contract or approval to buyer/program owner, and supplier risk to quality/supplier-risk owner.

## Output Checks

- Return valid JSON only.
- Preserve numeric types as numbers, not strings.
- Use null for absent optional IDs only when the template permits null.
- Sort arrays of IDs and controlled codes ascending unless the template states another ordering.
- For record lists matched by a row key, sort by that key after completing all calculations.
