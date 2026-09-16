 # ProcureOps Business Rules
 
 ## General Data Rules
 
 - All currency amounts are USD. Round to 2 decimal places (cents).
 - List fields are treated as sets (unordered) unless the output template specifies sort order.
 - When an output asks for a sorted list, sort ascending lexicographically for string IDs and numerically for numbers.
 - Use `null` (JSON null) for missing optional fields, not empty strings or zeros.
 - Empty lists use `[]`, not null.
 
 ## Cross-Endpoint Navigation
 
 The API has no query parameters, filters, or joins. Fetch full result sets and filter/slice in memory.
 
 Common navigation paths:
 
 | From | To | Via |
 |---|---|---|
 | Purchase order | Contract | `po.contract_id` |
 | Purchase order | Supplier | `po.supplier_id` |
 | Purchase order | Program | `po.program_id` |
 | Purchase order | Requisition | `po.requisition_id` |
 | Receipt | Purchase order | `receipt.po_id` |
 | Invoice | Purchase order | `invoice.po_id` |
 | Invoice | Receipt | `invoice.receipt_id` |
 | Payment | Invoice | `payment.invoice_id` |
 | Payment | Supplier | `payment.supplier_id` |
 | Approval event | Object | `approval.object_id` + `object_type` |
 | Budget snapshot | Program | `snapshot.program_id` |
 | Risk event | Supplier | `event.supplier_id` |
 | Item | Preferred supplier | `item.preferred_supplier_id` |
 | Contract | Item | `contract.sku` |
 | Contract | Supplier | `contract.supplier_id` |
 | Contract | Program | `contract.program_id` |
 
 ## PO-to-Contract Matching
 
 A PO may have `contract_id` null. That means no contract backs the PO. Contract IDs use the pattern `CR-` prefix.
 
 When computing contract noncancelled subtotal:
 1. Find all POs with matching `contract_id`.
 2. Exclude POs with status `cancelled`.
 3. Sum the `subtotal` of remaining POs.
 
 Contract ceiling headroom = `ceiling_amount` − noncancelled subtotal.
 
 ## PO Status
 
 - `open`: No receipts yet registered.
 - `partial_receipt`: At least one receipt exists, but not all quantity received.
 - `received`: All ordered quantity has been received.
 - `cancelled`: PO is void. Exclude from contract and budget calculations.
 
 ## Receipt Reconciliation
 
 For a given PO line:
 - `ordered_qty` = PO `lines[po_line_id].quantity`
 - `received_qty` = sum of `quantity_received` across all receipts for the same po_id and po_line_id, excluding any receipts that are post-as_of_date
 - `rejected_qty` = sum of `quantity_rejected` across all receipts for the same po_id and po_line_id
 - `short_qty_vs_po` = ordered_qty − received_qty
 - `receipt_completion_ratio` = received_qty / ordered_qty (rounded to 4 decimal places)
 
 For invoices against a PO:
 - `billed_qty` = sum of `quantity_billed` per po_line_id from the invoice lines
 - `unreceived_billed_qty` = billed_qty − received_qty (clamped to 0 minimum if billed < received)
 
 ## Invoice Hold Codes
 
 | Code | Meaning | Hold Decision |
 |---|---|---|
 | `QTY_VARIANCE` | Billed quantity differs from received | HOLD |
 | `PRICE_VARIANCE` | Invoice unit price differs from PO/contract | HOLD |
 | `NO_RECEIPT` | Invoice exists but no receipt | HOLD |
 | `null` | No hold code; invoice is clean | Check other conditions |
 
 ## Three-Way Match
 
 An invoice passes three-way match when:
 1. There is at least one receipt for the same PO.
 2. The billed quantity equals the received quantity (per PO line).
 3. The invoice unit price matches the PO/contract unit price.
 
 Only approved invoices with a three-way match are eligible for release. A scheduled payment for the invoice does not override hold status; it only reduces the net close balance.
 
 ## Budget Headroom
 
 ```
 headroom = program.budget_cap − program.committed_amount
 ```
 
 When evaluating a change request that would add new spend:
 - `requested_subtotal` = requested_quantity × contract.unit_price
 - `requested_tax` = requested_subtotal × tax_rate_percent ÷ 100
 - `requested_total` = requested_subtotal + requested_tax
 - `budget_after_change` = remaining_budget − requested_total
 - `budget_ok` is false if `budget_after_change` is negative
 
 Budget snapshots should be matched by `program_id` and `snapshot_date` closest to the review date. Use the snapshot's `committed_amount` when contracts and POs need budget context.
 
 ## Supplier Risk
 
 | risk_rating | Meaning |
 |---|---|
 | `low` | Clean supplier |
 | `medium` | Moderate concern; not a blocker |
 | `watch` | Elevated attention; context-only unless accompanied by open high-severity events |
 | `high` | Blocked supplier |
 
 A risk event blocks when:
 - `status` is `open` (not closed, not monitoring) as of the review date AND
 - `severity` is `high`
 
 Monitoring events (`status` = `monitoring`) are noted but not blocking. Closed events are ignored.
 
 For nomination/sourcing blockers:
 - `open_supplier_risk`: Any open risk event for the supplier, regardless of severity.
 - `supplier_watch`: Supplier has `risk_rating` = `watch` and no open high-severity events.
 
 ## Approval Rules
 
 For a given requisition or other object:
 1. Collect all approval events where `object_id` matches.
 2. Find the event with the latest `event_date`.
 3. If its `action` is `approved`, the object is approved (`approval_ok` = true).
 4. If its `action` is `submitted` or `returned`, the object is not fully approved (`approval_ok` = false).
 
 ## Nomination Readiness (Sourcing)
 
 For each package line SKU, evaluate blockers:
 
 | Code | Condition |
 |---|---|
 | `missing_contract` | PO contract_id is null |
 | `supplier_watch` | Supplier risk_rating is `watch` without open high-severity events |
 | `open_supplier_risk` | Any open risk event exists for the supplier as of as_of_date |
 | `ap_hold` | Any invoice for the PO has status `on_hold` or `pending_receipt` |
 | `pending_receipt` | Sum of received quantities across all receipts < PO ordered quantity |
 | `late_due_date` | PO due_date is before as_of_date |
 | `none` | No blockers found |
 
 Readiness per line:
 - `ready`: blocker_codes is `["none"]`
 - `at_risk`: has blockers but none are `missing_contract` or `open_supplier_risk`
 - `not_ready`: has `missing_contract` or `open_supplier_risk` or `late_due_date`
 
 Nomination decision:
 - `nominate`: readiness is `ready`
 - `conditional_nomination`: readiness is `at_risk`
 - `hold`: readiness is `not_ready`
 
 Program overall readiness:
 - `ready`: all lines are `nominate`
 - `at_risk`: at least one conditional but no holds
 - `not_ready`: any line is `hold`
 
 ## AP Close Reconciliation
 
 For each target invoice:
 - `quantity_billed` = invoice.lines[].quantity_billed
 - `quantity_received` = sum of receipt line `quantity_received` for matching po_id and po_line_id; 0.00 if no receipt
 - `quantity_variance` = quantity_billed − quantity_received
 - `quantity_variance_pct` = (quantity_variance / PO ordered quantity) × 100, rounded to 1 decimal
 
 Reason codes:
 - `APPROVED_THREE_WAY_MATCH`: Invoice passes three-way match
 - `NO_RECEIPT`: No receipt exists for the PO
 - `QTY_VARIANCE`: Billed quantity differs from received
 - `SCHEDULED_PAYMENT_FOUND`: A payment is scheduled for the invoice
 
 Vendor balance (per supplier in the close slice):
 - `opening_balance` = provided by task (usually 0.00 for close-slice)
 - `invoice_total` = sum of invoice.totals for the supplier across target invoices
 - `scheduled_payments` = sum of payment.amount for the supplier through the cutoff date
 - `held_invoice_total` = sum of totals for invoices where hold_decision is HOLD
 - `releasable_invoice_total` = sum of totals for invoices where hold_decision is RELEASE
 - `close_balance` = opening_balance + invoice_total − scheduled_payments
 
 ## Change Control (Contract Amendment)
 
 When evaluating a modular change request against a contract:
 
 1. **Contract check**: Noncancelled POs against the contract determine headroom. `ceiling_ok` is false if `headroom_after_change` is negative.
 2. **Budget check**: Use the program-level budget snapshot. `budget_ok` is false if `budget_after_change` is negative. `max_quantity_with_current_budget` = floor(remaining_budget / (contract.unit_price × (1 + tax_rate/100))).
 3. **Approval check**: Latest approval event for the source requisition. `approval_ok` is true only when latest action is `approved`.
 4. **Supplier risk check**: `supplier_risk_ok` is false only when open high-severity events exist.
 
 Decision matrix:
 
 | Conditions | Decision |
 |---|---|
 | All checks pass | `release_amendment` |
 | Budget fails, approval passes, risk passes | `hold_for_budget` |
 | Budget passes, approval fails, risk passes | `hold_for_approval` |
 | Budget fails, approval fails, risk passes | `hold_for_budget_and_approval` |
 | Supplier risk fails | `hold_for_supplier_risk` |
 | Contract ceiling fails | `reject_contract_mismatch` |
 
 Required actions derive from failing checks:
 - Budget fail → `raise_budget_exception_or_reduce_quantity`
 - Approval fail → `obtain_final_requisition_approval`
 - Risk fail → `resolve_supplier_risk_hold`
 - All pass → `none`
 
 ## AP Release / Receiving Exception Review
 
 When reconciling invoices against receipts for release decisions:
 
 - Match invoices to receipts by `po_id`.
 - Exclude receipts on the same PO that belong to different invoices (marked as `excluded_same_po_receipt_ids`).
 - For each invoice, check chargeback register for pre-approved or pending offsets.
 
 Receiving exception codes:
 - `Underage Quantity`: received_qty < ordered_qty
 - `Severe Unmatched Quantity`: received_qty < 50% of ordered_qty
 - `Inspection Hold`: PO has an open quality risk event
 - `AP Quantity Variance`: invoice billed_qty differs from received_qty
 
 Release decision flow:
 1. If no receipt exists → `hold_missing_receipt` / `no_receipt_on_po`
 2. If a pending quality chargeback exists → `hold_pending_quality_chargeback` / `inspection_hold_pending_chargeback`
 3. If an approved chargeback exists → `release_net_after_approved_chargeback` with `net_release_amount = invoice_total − approved_chargeback_amount`
 
 Net release totals:
 - `approved_chargeback_amount` = sum of chargebacks with status `approved` for the invoice
 - `pending_chargeback_amount` = sum of chargebacks with status `pending_quality_review`
 - `net_release_amount` = invoice_total − approved_chargeback_amount (for released invoices) or 0.00 (for held)
