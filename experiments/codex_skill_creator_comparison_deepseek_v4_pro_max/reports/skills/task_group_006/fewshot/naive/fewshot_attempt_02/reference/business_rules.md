# Business Rules

All rules derive from patterns observed across the five training tasks. Apply these systematically; do not deviate for a specific case unless the answer template itself defines a different rule.

## Currency and Rounding

- All amounts in USD.
- Round to 2 decimal places (cents) for all dollar amounts.
- Round percentages to 1 decimal place.
- Round ratios (e.g., receipt_completion_ratio) to 4 decimal places.
- Use standard rounding (round half up).

## Budget Calculations

- **headroom** = budget_cap - committed_amount (from the latest budget snapshot for the program that is dated on or before the as_of_date)
- **remaining budget** = same as headroom
- **budget after change** = headroom - requested_total (where requested_total = requested_subtotal + requested_tax)
- **budget_ok** = budget_after_change >= 0
- **max_quantity_with_current_budget** = floor(headroom / (unit_price * (1 + tax_rate_decimal))), computed only when budget is a blocker
- Tax rate comes from the task's business_controls or memo. If not stated, use the tax rate from the PO or invoice under review.

## Contract Calculations

- **noncancelled_subtotal**: sum the subtotals of all POs linked to this contract whose status is NOT 'cancelled'
- **headroom_before_change** = ceiling_amount - noncancelled_subtotal
- **requested_subtotal** = requested_quantity * contract unit_price
- **headroom_after_change** = headroom_before_change - requested_subtotal
- **ceiling_ok** = headroom_after_change >= 0
- **contract_price_match**: true when invoice unit_price == contract unit_price (within 0.01 tolerance), false otherwise

## Quantity Reconciliation (Three-Way Match)

For a given PO line:

- **ordered_qty**: from the PO line quantity
- **received_qty**: sum of quantity_received across all receipts for this PO, filtered by as_of_date
- **rejected_qty**: sum of quantity_rejected across all receipts for this PO, filtered by as_of_date
- **billed_qty**: from the invoice line quantity_billed
- **short_qty_vs_po** = ordered_qty - received_qty (positive means shortage)
- **unreceived_billed_qty** = billed_qty - received_qty (positive means the supplier billed for goods not yet received)
- **quantity_variance** = billed_qty - received_qty
- **quantity_variance_pct** = (quantity_variance / ordered_qty) * 100, rounded to 1 decimal
- **receipt_completion_ratio** = received_qty / ordered_qty, rounded to 4 decimal places

## Financial Computations

- **received_goods_value** = received_qty * po_unit_price (or contract_unit_price if contract-linked)
- **unreceived_goods_value** = (ordered_qty - received_qty) * po_unit_price
- **invoice_subtotal**: from the invoice record; equals sum of (quantity_billed * unit_price) across invoice lines
- **invoice_total** = invoice_subtotal + invoice_freight + invoice_tax (from the invoice record)
- **net_release_amount** = invoice_total - approved_chargeback_amount (when netting chargebacks)
- **total_close_balance**: sum of net_balance_impact across all invoices in the close slice (or sum of close_balance across vendor_balances)
- **net_balance_impact** = invoice_total - scheduled_payment_amount (for a given invoice, from the vendor's perspective)
- **close_balance** = opening_balance + invoice_total - scheduled_payments (per vendor)
- **scheduled_payment_amount**: for a given invoice, sum the amounts of payments matching that invoice_id with scheduled_date through the payment window (typically end of month, e.g., 2026-06-30)

## Exception Codes

### Invoice Exception Codes

| Code | Condition |
|---|---|
| `INVOICE_QTY_EXCEEDS_RECEIPT` | billed_qty > received_qty for any line on the invoice |
| `PARTIAL_RECEIPT` | received_qty > 0 AND received_qty < ordered_qty |
| `SUPPLIER_WATCH_RISK` | the supplier has risk_rating == 'watch' OR any open risk event for that supplier |
| `PRICE_MISMATCH` | abs(invoice unit_price - contract unit_price) > 0.01 for any line |
| `DAMAGE_REJECTION` | rejected_qty > 0 for any line on the invoice's linked receipt |
| `NO_EXCEPTION` | none of the above conditions apply |

### Blocker Codes (Nomination Readiness)

| Code | Condition |
|---|---|
| `missing_contract` | PO has no contract_id (contract_id is null) OR contract status is not 'active' |
| `supplier_watch` | supplier risk_rating == 'watch' |
| `open_supplier_risk` | any open risk event for the supplier with severity >= 'medium' |
| `ap_hold` | any invoice for this PO/SKU has status == 'on_hold' or 'pending_receipt' |
| `pending_receipt` | received_qty < ordered_qty (partial or no receipt) |
| `late_due_date` | PO due_date < as_of_date and PO status != 'closed' and PO status != 'received' |
| `none` | no blockers apply |

### Receiving Exception Codes

| Code | Condition |
|---|---|
| `Underage Quantity` | received_qty < ordered_qty (PO shortfall) |
| `Severe Unmatched Quantity` | unreceived_billed_qty > 0 AND received_qty < ordered_qty |
| `Inspection Hold` | receipt status == 'inspection_hold' |
| `AP Quantity Variance` | quantity_variance != 0 on the linked invoice |

### AP Close Reason Codes

| Code | Condition |
|---|---|
| `APPROVED_THREE_WAY_MATCH` | invoice status is 'approved' AND received_qty == billed_qty AND price matches contract/PO |
| `NO_RECEIPT` | receipt_id is null on the invoice AND no receipt exists for the PO before the invoice date |
| `QTY_VARIANCE` | billed_qty != received_qty |
| `SCHEDULED_PAYMENT_FOUND` | a payment exists for this invoice with scheduled_date through the close window |

## Readiness Determination

### Per-Line Readiness (Nomination)

- **not_ready**: any of missing_contract, open_supplier_risk, pending_receipt, late_due_date is present in blocker_codes
- **at_risk**: no not_ready blockers, but supplier_watch or ap_hold is present
- **ready**: only none in blocker_codes

### Overall Program Readiness

- **not_ready**: any nomination line is not_ready
- **at_risk**: no line is not_ready, but at least one line is at_risk
- **ready**: all lines are ready

## Nomination Decision Rules

For each SKU line:

- **nominate**: readiness_status == 'ready' AND no blockers beyond none
- **conditional_nomination**: readiness_status == 'at_risk'
- **hold**: readiness_status == 'not_ready'

## Committee Action Rules

- **nominate_now_supplier_ids**: suppliers whose lines all have nomination_decision == 'nominate'
- **conditional_supplier_ids**: suppliers with at least one line at conditional_nomination and none at hold
- **hold_supplier_ids**: suppliers with at least one line at hold
- **next_owner**: determined by the primary blocker category:
  - ap_team if primary blocker is ap_hold
  - finance_ops if primary blocker is budget-related
  - quality_ops if primary blocker is open_supplier_risk
  - buyer if primary blocker is missing_contract or late_due_date
  - program_owner otherwise
- **send_to_committee**: 'yes' if any line is ready (nominate) AND at least one line is hold; otherwise 'no'

## Invoice Hold/Release Decisions (AP Close)

For each invoice:

- **hold_decision**: 'HOLD' if invoice_status is 'on_hold' or 'pending_receipt'; 'RELEASE' if invoice_status is 'approved'
- **release_to_payment**: true if hold_decision == 'RELEASE' AND a payment is already scheduled; false otherwise
- **reason_codes**: collect all matching codes from the AP Close reason code table, sort alphabetically

## Chargeback Decision Logic

- **release_net_after_approved_chargeback**: chargeback exists with status 'approved'; net the chargeback amount from invoice_total
- **hold_missing_receipt**: no receipt exists for the invoice's PO
- **hold_pending_quality_chargeback**: chargeback exists with status 'pending_quality_review'
- **approved_chargeback_amount**: sum of (basis_quantity * unit_cost) for chargebacks with status 'approved' matching this invoice+PO+receipt
- **pending_chargeback_amount**: sum of (basis_quantity * unit_cost) for chargebacks with status 'pending_quality_review'
- **net_release_amount**: invoice_total - approved_chargeback_amount (0 if hold decision)

## Supplier Risk Assessment

- **supplier_status**: from the supplier record
- **supplier_risk_rating**: from the supplier record
- **open_event_ids**: vendor risk events for this supplier with status in ('open', 'monitoring'), sorted ascending
- **severe_open_event_ids**: subset of open_event_ids where severity == 'high' AND status == 'open'
- **supplier_risk_ok**: true if severe_open_event_ids is empty, false otherwise
- **has_open_supplier_risk**: true if open_event_ids is non-empty
- Risk event status (open/monitoring) determines inclusion; event_date does not filter risk events

## Approval Check Rules

- **latest_event_id/action/actor/event_date**: from the approval event with the latest event_date for the given requisition_id
- **approval_ok**: true if any approval event for this requisition has action in the good actions set (default: ['approved'])
- Approval events are linked to requisitions via object_id == requisition_id where object_type == 'requisition'

## Vendor Balance Reconciliation

- **opening_balance**: use 0.00 unless the task provides an opening balance figure
- **close_balance** = opening_balance + sum of invoice_totals for the vendor - sum of scheduled_payments for the vendor (within the slice)
- **balance_status**:
  - `FULLY_SCHEDULED`: close_balance == 0.00
  - `OPEN_APPROVED`: close_balance > 0 AND all vendor invoices have hold_decision == 'RELEASE'
  - `OPEN_HELD`: close_balance > 0 AND at least one vendor invoice has hold_decision == 'HOLD'

## Change Request Decision

Determine the decision by combining checks in priority order:

1. If contract_check.ceiling_ok is false: `reject_contract_mismatch`
2. If approval_check.approval_ok is false AND program_budget_check.budget_ok is false: `hold_for_budget_and_approval`
3. If approval_check.approval_ok is false only: `hold_for_approval`
4. If program_budget_check.budget_ok is false only: `hold_for_budget`
5. If supplier_risk_check.supplier_risk_ok is false: `hold_for_supplier_risk`
6. If all checks pass: `release_amendment`

## Required Actions (Change Request)

| Action | Condition |
|---|---|
| `obtain_final_requisition_approval` | approval_ok is false |
| `raise_budget_exception_or_reduce_quantity` | budget_ok is false |
| `resolve_supplier_risk_hold` | supplier_risk_ok is false |
| `none` | all checks pass |

Sort required_actions ascending.

## Supporting IDs Collection

- **included_po_ids**: all POs linked to the contract, excluding cancelled ones. Include all non-cancelled statuses (confirmed, partial_receipt, received, closed, open).
- **excluded_cancelled_po_ids**: all POs linked to the contract with status == 'cancelled'
- **approval_event_ids**: all approval events for the source requisition

## Evidence Attribution

- Record the IDs of every API record consulted: programs, contracts, POs, receipts, invoices, payments, approvals, budget snapshots, vendor risk events, suppliers, items, requisitions.
- For task_payloads_reviewed, list the exact file paths under input/payloads/ that were read.
- For authoritative_sources, list the categories of records used (e.g., 'procureops_po_records', 'procureops_receipt_records', 'procureops_ap_records', 'local_chargeback_register').
- For supporting_only_sources, list non-authoritative payloads (e.g., 'ap_release_request_note', 'stale_po73xx_alias_note').

## Followup Actions (Receiving/AP Release)

| Action | Condition |
|---|---|
| `ask_receiving_for_missing_receipt` | a PO has no receipt and the supplier is known |
| `hold_duplicate_receipt_for_separate_invoice` | multiple receipts exist for the same PO, one tied to a different invoice |
| `route_quality_review_for_held_receipt` | a receipt is in inspection_hold |
| `post_approved_chargeback_netting` | any invoice has an approved chargeback |

## Blockers in Summary

- **blocker_count**: count of required_actions that are not 'none'
- **ready_to_release**: true if blocker_count == 0 AND decision == 'release_amendment'
- **currency**: always 'USD'

## Receipt/AP Release Decision Logic

For each invoice in the release packet:

- **primary_reason**:
  - `approved_qty_chargeback`: chargeback approved for quantity variance, net release possible
  - `approved_ap_quantity_variance`: chargeback approved for AP quantity variance, net release possible
  - `no_receipt_on_po`: no receipt exists for the PO
  - `inspection_hold_pending_chargeback`: receipt is in inspection_hold with pending chargeback

- **receipt_ids_in_scope**: receipt IDs tied to this invoice (from chargeback register or API). Include the receipt_id from the invoice record and any receipt from the chargeback register matching this invoice+PO.
- **excluded_same_po_receipt_ids**: receipts for the same PO that are not tied to the current invoice and are dated after the as_of_date or belong to a different invoice. Sort ascending.

- **receiving_exceptions.resolution_status**:
  - `net_release_ready`: chargeback approved and no inspection hold
  - `hold_for_quality_review`: receipt in inspection_hold or pending chargeback
  - `accepted_no_receiving_exception`: receipt accepted with no exception codes
  - `missing_receipt`: no receipt exists; use receipt_id 'MISSING:{po_id}' as a sentinel

- **chargeback_status**: 'approved' if all matching chargebacks are approved; 'pending_quality_review' if any is pending; 'not_applicable' if no receipt exists
