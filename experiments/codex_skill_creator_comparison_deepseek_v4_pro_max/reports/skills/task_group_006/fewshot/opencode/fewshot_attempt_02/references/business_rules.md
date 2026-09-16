# ProcureOps Business Rules

These rules are reused across all ProcureOps task types. They never change
between tasks. When a task appears to introduce a new code or formula, derive it
from the rules below unless the memo explicitly provides a different value (e.g.,
a memo-provided tax rate).

## Rounding and precision

- All USD amounts: `round(value, 2)` (cents). Use standard arithmetic rounding,
  not banker's rounding.
- Ratios and percentages: round to the precision stated in the answer template.
  When the template says precision 4, keep 4 decimal places.
- Unit prices and subtotals from the API are already in cents precision; do not
  re-round them unless you multiply them.

## List ordering

Sort all lists of strings ascending (lexical order). Even when the template
describes a field as "set" or "evaluator sorts values", emit the list in sorted
order. The evaluator will re-sort for comparison, but emitting sorted output
reduces silent mismatches.

## Contract ceiling check

For a contract ceiling-usage calculation:

1. Gather all purchase orders that reference the contract_id via
   `contract_id` field.
2. Exclude POs with status "cancelled".
3. Sum the `subtotal` of remaining POs. This is `noncancelled_subtotal`.
4. `headroom_before_change = ceiling_amount - noncancelled_subtotal`.
5. Requested subtotal = `requested_quantity * unit_price` (from contract).
6. `headroom_after_change = headroom_before_change - requested_subtotal`.
7. `ceiling_ok = headroom_after_change >= 0`.

## Program budget check

For program budget impact:

1. Find the budget snapshot for the program at (or closest before) the as_of date.
2. `budget_cap` and `committed_amount` come from the snapshot.
3. `remaining_budget = budget_cap - committed_amount`.
4. `requested_tax = requested_subtotal * (tax_rate_percent / 100)`. Round to
   cents. Only include freight if the memo provides a freight amount.
5. `requested_total = requested_subtotal + requested_tax + freight` (if any).
6. `budget_after_change = remaining_budget - requested_total`.
7. `budget_ok = budget_after_change >= 0`.
8. `max_quantity_with_current_budget = floor(remaining_budget / (unit_price * (1 + tax_rate_percent / 100)))`.
   Round down to the nearest integer.

## Approval check

For approval state of a requisition:

1. Fetch all approval events where `object_id` matches the requisition_id and
   `object_type` is "requisition".
2. Sort by event_date descending, then event_id descending for ties.
3. The first event is the latest approval event.
4. The task's business_controls specify which actions count as "good" (typically
   only "approved"). If the latest action is not in the good-actions list,
   `approval_ok = false`.

## Supplier risk check

For supplier risk context:

1. Fetch all vendor_risk_events for the supplier_id.
2. Active events: status is "open" or "monitoring".
3. Closed events: status is "closed" -- exclude these from counts.
4. `has_open_supplier_risk = true` if any active events exist for this supplier.
5. `open_event_ids` = list of event_id for active events, sorted ascending.
6. `severe_open_event_ids` = open_event_ids filtered to severity "high".
7. `supplier_risk_ok = true` unless there is a severe open event. A "watch"
   risk_rating on the supplier record is informational and does not, by itself,
   block the decision unless the business_controls say otherwise.

## Blocker codes (sourcing nomination)

These apply to nomination-line readiness checks. Determine codes by inspecting
cross-referenced records:

| Code | When to apply |
|------|--------------|
| `missing_contract` | No active contract exists linking the SKU, supplier_id, and program_id for this line. A contract must have status "active". |
| `supplier_watch` | The supplier's `risk_rating` on `/suppliers` is "watch" or "high". |
| `open_supplier_risk` | The supplier has at least one vendor_risk_event with status "open" or "monitoring". |
| `ap_hold` | At least one invoice for this line's PO has status "on_hold" or "pending_receipt". |
| `pending_receipt` | The PO quantity has not been fully received (sum of all receipt quantities < ordered quantity), and at least one invoice shows status "pending_receipt". |
| `late_due_date` | The PO's `due_date` is earlier than the as_of_date and the PO status is not "fully_received". |
| `none` | None of the above conditions apply. |

Sort blocker_codes ascending. When no blockers exist, use `["none"]`.

When multiple codes apply, include all of them. The overall readiness for the
line is:
- `ready` if blockers is `["none"]`
- `at_risk` if blockers contain only `supplier_watch` and/or `open_supplier_risk`
  but no operational blocker (no ap_hold, pending_receipt, late_due_date,
  missing_contract)
- `not_ready` if any operational blocker exists

## Nomination decisions

Based on readiness_status:
- `ready` -> "nominate"
- `at_risk` -> "conditional_nomination"
- `not_ready` -> "hold"

## Committee action

- `nominate_now_supplier_ids`: suppliers with decision "nominate"
- `conditional_supplier_ids`: suppliers with decision "conditional_nomination"
- `hold_supplier_ids`: suppliers with decision "hold"
- `send_to_committee`: "yes" if any line is "nominate" or "conditional_nomination",
  otherwise "no"
- `next_owner`: the role most relevant to the dominant blocker type:
  - "ap_team" if dominant blocker is ap_hold or pending_receipt
  - "buyer" if dominant blocker is missing_contract or late_due_date
  - "quality_ops" if dominant blocker is open_supplier_risk or supplier_watch
  - "finance_ops" if budget-related
  - "program_owner" otherwise

## Receiving closeout formulas

For line reconciliation:

- `ordered_qty` = PO line quantity
- `received_qty` = sum of receipt line quantities for the PO line
- `rejected_qty` = sum of receipt line rejected quantities
- `billed_qty` = sum of invoice line quantities billed for the PO line
- `short_qty_vs_po` = ordered_qty - received_qty
- `unreceived_billed_qty` = billed_qty - received_qty (floor at 0)
- `receipt_completion_ratio` = received_qty / ordered_qty, rounded to 4 decimal places
- `contract_price_match` = PO unit_price equals contract unit_price

## Invoice review exception codes (receiving closeout)

| Code | When to apply |
|------|--------------|
| `INVOICE_QTY_EXCEEDS_RECEIPT` | billed_qty > received_qty for any line |
| `PARTIAL_RECEIPT` | received_qty < ordered_qty for any line |
| `SUPPLIER_WATCH_RISK` | supplier risk_rating is "watch" or "high" |
| `PRICE_MISMATCH` | PO unit_price != contract unit_price |
| `DAMAGE_REJECTION` | rejected_qty > 0 for any line |
| `NO_EXCEPTION` | None of the above apply |

## AP close desk formulas

For invoice-level decisions:

- `quantity_billed` = sum of invoice line quantity_billed
- `quantity_received` = sum of receipt quantities for matching PO. If no receipt, 0.
- `quantity_variance` = quantity_billed - quantity_received
- `quantity_variance_pct` = (quantity_variance / PO ordered quantity) * 100,
  rounded to 1 decimal place
- `scheduled_payment_amount` = sum of payment amounts for the invoice_id
  where scheduled_date falls within the look-ahead window, and status is
  "scheduled" or "released"
- `net_balance_impact` = invoice_total - scheduled_payment_amount
- `release_to_payment` = true when (hold_decision is "RELEASE" AND
  scheduled_payment_amount > 0)

Hold decision logic:

- "HOLD" if invoice status is "on_hold" or "pending_receipt", OR quantity_variance != 0
- "RELEASE" if invoice status is "approved" AND quantity_variance == 0

Reason codes (per invoice, sorted alphabetically):

| Code | When to apply |
|------|--------------|
| `APPROVED_THREE_WAY_MATCH` | invoice status is "approved", quantity_variance == 0, and at least one receipt exists for the PO |
| `NO_RECEIPT` | No receipt exists for the PO |
| `QTY_VARIANCE` | quantity_variance != 0 |
| `SCHEDULED_PAYMENT_FOUND` | scheduled_payment_amount > 0 |

## Vendor balance formulas (AP close desk)

- `opening_balance` = task-provided opening amount for the supplier (usually 0.00
  for a close-slice)
- `invoice_total` = sum of invoice totals for this supplier in scope
- `scheduled_payments` = sum of scheduled_payment_amount across invoices for
  this supplier
- `held_invoice_total` = sum of invoice_total where hold_decision is "HOLD"
- `releasable_invoice_total` = sum of invoice_total where hold_decision is "RELEASE"
- `close_balance` = opening_balance + invoice_total - scheduled_payments
- `balance_status`:
  - "FULLY_SCHEDULED" if close_balance == 0
  - "OPEN_APPROVED" if close_balance > 0 and held_invoice_total == 0
  - "OPEN_HELD" if close_balance > 0 and held_invoice_total > 0

## Change-control decision logic

Based on the contract, budget, approval, and supplier risk checks:

| Conditions | Decision |
|------------|----------|
| All checks pass | "release_amendment" |
| Budget fails, approval fails, other pass | "hold_for_budget_and_approval" |
| Budget fails only | "hold_for_budget" |
| Approval fails only | "hold_for_approval" |
| Supplier risk fails (severe open event) | "hold_for_supplier_risk" |
| Contract ceiling fails | "reject_contract_mismatch" |

If multiple hold conditions apply, use the combined decision string like
"hold_for_budget_and_approval". The allowed decision values are defined by
the answer template's enum.

Required actions (sorted ascending):

| Action | Trigger |
|--------|---------|
| `obtain_final_requisition_approval` | approval_ok is false |
| `raise_budget_exception_or_reduce_quantity` | budget_ok is false |
| `resolve_supplier_risk_hold` | supplier_risk_ok is false |
| `none` | All checks pass |

## AP release file rules

For each target invoice, determine the release decision:

1. Look up the PO, receipt(s), and invoice in the ProcureOps records.
2. Check the local chargeback_register (provided in the memo payload) for any
   chargeback entries matching this invoice_id.
3. Decision logic:

| Condition | Decision | Primary Reason |
|-----------|----------|----------------|
| Chargeback with status "pending_quality_review" | "hold_pending_quality_chargeback" | "inspection_hold_pending_chargeback" |
| No receipt exists for the PO | "hold_missing_receipt" | "no_receipt_on_po" |
| Chargeback with status "approved" and no pending chargebacks | "release_net_after_approved_chargeback" | "approved_qty_chargeback" or "approved_ap_quantity_variance" (based on chargeback reason_code) |

For approved chargebacks:
- If reason_code is "Underage Quantity", primary_reason is "approved_qty_chargeback".
- If reason_code is "AP Quantity Variance", primary_reason is "approved_ap_quantity_variance".

4. Financials per invoice:
- `approved_chargeback_amount` = sum of chargeback (basis_quantity * unit_cost)
  for approved chargebacks on this invoice.
- `pending_chargeback_amount` = sum of chargeback values for pending chargebacks.
- `net_release_amount` = invoice_total - approved_chargeback_amount (when
  release decision is "release_net_after_approved_chargeback"), otherwise 0.

5. When determining `receipt_ids_in_scope` for an invoice, include all receipts
   for the invoice's PO, not just the receipt_id on the invoice record. But
   exclude receipts that belong to other invoices targeting the same PO
   (duplicate receipt handling).

6. `excluded_same_po_receipt_ids`: receipts for the same PO that are already
   attached to a different invoice and should not be counted twice.

## Receiving exceptions (AP release file)

For each receipt in scope:

| Exception code | Trigger |
|----------------|---------|
| `Underage Quantity` | received_qty < ordered_qty for any line |
| `Severe Unmatched Quantity` | ABS(received_qty - billed_qty) >= 50 or >= 50% of ordered_qty |
| `Inspection Hold` | Any receipt line has inspection_status "pending" or "failed" |
| `AP Quantity Variance` | An invoice for this PO has a hold_code of "QTY_VARIANCE" |

Where multiple conditions apply, include all matching codes.

Chargeback_status:
- "approved" if all chargebacks for this receipt are approved
- "pending_quality_review" if any chargeback is pending_quality_review
- "not_applicable" if no chargebacks exist

Resolution_status:
- "net_release_ready" if chargeback_status is "approved" and the receipt is
  otherwise clean
- "hold_for_quality_review" if chargeback_status is "pending_quality_review"
- "accepted_no_receiving_exception" if no exception codes and chargeback_status
  is "not_applicable"
- "missing_receipt" if no receipt exists for the PO

## Summary totals (AP release file)

- `approved_chargeback_total` = sum of approved_chargeback_amount across all invoices
- `pending_chargeback_total` = sum of pending_chargeback_amount across all invoices
- `net_release_total` = sum of net_release_amount across all invoices

## Evidence recording

When the template asks for source record IDs or evidence, list every record ID
you used from each endpoint. Include IDs from all endpoints consulted, not just
the ones that produced a positive result.

For example, if you checked 3 POs, 2 receipts, 1 contract, 5 risk events, and
2 invoices to produce the answer, include all those IDs in the evidence list.
Sort the combined list ascending.
