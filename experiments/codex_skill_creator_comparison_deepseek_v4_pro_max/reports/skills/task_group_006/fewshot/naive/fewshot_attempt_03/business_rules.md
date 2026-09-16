# ProcureOps Business Rules Reference

Quick-reference card for formulas, codes, and decision logic.

## Three-Way Match Formulas

| Computation | Formula |
|---|---|
| short_qty_vs_po | ordered_qty - received_qty |
| unreceived_billed_qty | max(0, billed_qty - received_qty) |
| receipt_completion_ratio | received_qty / ordered_qty (4 decimal places) |
| contract_price_match | po_unit_price == contract_unit_price && po_unit_price == invoice_unit_price |
| received_goods_value | received_qty * contract_unit_price |
| unreceived_goods_value | (ordered_qty - received_qty) * contract_unit_price |
| invoice_total | invoice_subtotal + invoice_freight + invoice_tax |

## Exception Codes

### Invoice Exception Codes (Three-Way Match)

| Code | Condition |
|---|---|
| INVOICE_QTY_EXCEEDS_RECEIPT | billed_qty > received_qty |
| PARTIAL_RECEIPT | received_qty < ordered_qty |
| PRICE_MISMATCH | contract_price_match is false |
| DAMAGE_REJECTION | rejected_qty > 0 |
| NO_EXCEPTION | all checks pass |
| SUPPLIER_WATCH_RISK | supplier has open risk events |

### Sourcing Nomination Blockers

missing_contract, supplier_watch, open_supplier_risk, ap_hold, pending_receipt, late_due_date, none

### AP Reason Codes

APPROVED_THREE_WAY_MATCH, NO_RECEIPT, QTY_VARIANCE, SCHEDULED_PAYMENT_FOUND

### Receiving Exception Codes

Underage Quantity, Severe Unmatched Quantity, Inspection Hold, AP Quantity Variance

## Contract Ceiling

```
noncancelled_subtotal = sum(PO subtotal for all POs on contract where status != "cancelled")
headroom_before_change = ceiling_amount - noncancelled_subtotal
requested_subtotal = requested_quantity * unit_price
headroom_after_change = headroom_before_change - requested_subtotal
ceiling_ok = headroom_after_change >= 0
```

## Program Budget

```
remaining_budget = budget_cap - committed_amount
requested_tax = requested_subtotal * (tax_rate_percent / 100)
requested_total = requested_subtotal + requested_tax (+ freight only if memo provides it)
budget_after_change = remaining_budget - requested_total
budget_ok = budget_after_change >= 0
max_quantity = floor(remaining_budget / (unit_price * (1 + tax_rate_percent / 100)))
```

## Approval Check

- Fetch approval events for the source requisition from /approvals
- Sort by event_date descending; take the latest
- approval_ok = (latest action is in approval_good_actions list)

## Supplier Risk Check

- Fetch vendor_risk_events for the supplier
- Filter for open/monitoring status
- supplier_risk_ok is false only when a severe open event exists
- Include all open event IDs regardless of severity

## AP Hold/Release

| Decision | Condition |
|---|---|
| RELEASE | Receipt exists, quantities match, payment scheduled |
| HOLD | No receipt (NO_RECEIPT) or billed_qty > received_qty (QTY_VARIANCE) |

```
quantity_variance = quantity_billed - quantity_received
quantity_variance_pct = (quantity_variance / po_ordered_qty) * 100  (1 decimal)
net_balance_impact = invoice_total - scheduled_payment_amount
```

## Vendor Balance

```
close_balance = opening_balance + invoice_total - scheduled_payments
balance_status:
  FULLY_SCHEDULED: close_balance == 0, all invoices released
  OPEN_APPROVED:   close_balance > 0, all invoices released
  OPEN_HELD:       at least one invoice held
```

## Chargeback Netting

- Approved chargeback: net_release_amount = invoice_total - approved_chargeback_amount
- Pending chargeback: net_release_amount = 0.0, invoice held
- Receipt matching: use receipt named in chargeback register; exclude other receipts on same PO

## Decision Composition

### Change Control
- Single failures: hold_for_budget, hold_for_approval, hold_for_supplier_risk
- Budget + approval: hold_for_budget_and_approval
- Contract ceiling failure: reject_contract_mismatch
- All clear: release_amendment

### Sourcing Nomination
- No blockers: nominate (ready)
- Blockers present but not severe: conditional_nomination (at_risk)
- Severe blockers (missing_contract, open_supplier_risk, no receipt): hold (not_ready)

### Receiving Closeout
- accept_partial_hold_variance: receipt exists, quantity short, invoice held
- release_full_invoice: full receipt match, invoice released
- reject_batch: severe mismatch or damage
- manual_recount_required: unresolved quantity discrepancy

### AP Release
- release_net_after_approved_chargeback: approved chargeback exists
- hold_missing_receipt: no receipt on PO
- hold_pending_quality_chargeback: chargeback pending quality review

## Required Actions (Change Control)

obtain_final_requisition_approval, raise_budget_exception_or_reduce_quantity, resolve_supplier_risk_hold, none
