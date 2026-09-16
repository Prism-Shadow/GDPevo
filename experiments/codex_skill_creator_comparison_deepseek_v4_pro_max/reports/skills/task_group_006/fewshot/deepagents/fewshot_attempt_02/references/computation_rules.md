# ProcureOps Computation Rules

All amounts in USD, rounded to 2 decimal places with Python `round(x, 2)`.

## Financial Formulas

### Program Budget Headroom

```
remaining = budget_cap - committed_amount
budget_headroom = max(remaining, 0)  // used for readiness assessment
```

Source: `/budget_snapshots` (preferred) or `/programs` (fallback). Use the budget snapshot that matches the task's close/review date.

### Contract Ceiling Headroom

```
noncancelled_subtotal = sum(PO.subtotal for PO in contract POs where PO.status != "cancelled")
headroom_before_change = ceiling_amount - noncancelled_subtotal
requested_subtotal = requested_quantity * unit_price
headroom_after_change = headroom_before_change - requested_subtotal
ceiling_ok = headroom_after_change >= 0
```

### After-Change Budget

```
requested_total = requested_subtotal + round(requested_subtotal * tax_rate_pct / 100, 2)
budget_after_change = remaining_budget - requested_total
budget_ok = budget_after_change >= 0
max_quantity_with_current_budget = floor(remaining_budget / (unit_price * (1 + tax_rate_pct / 100)))
```

Tax rate defaults to 7.25% unless the change memo specifies a different rate.

### Receipt Line Computations

```
receipt_completion_ratio = round(received_qty / ordered_qty, 4)
short_qty_vs_po = ordered_qty - received_qty
unreceived_billed_qty = max(billed_qty - received_qty, 0)
received_goods_value = received_qty * po_unit_price
unreceived_goods_value = (ordered_qty - received_qty) * po_unit_price
invoice_freight = invoice.freight (0 if absent)
invoice_tax = invoice.tax (0 if absent)
invoice_total = invoice.total
```

### AP Close Computations

```
quantity_variance = quantity_billed - quantity_received
quantity_variance_pct = round(quantity_variance / ordered_qty * 100, 1)
scheduled_payment_amount = sum(payment.amount for payment in invoice payments where payment.status in ("scheduled", "released"))
net_balance_impact = invoice_total - scheduled_payment_amount
held_invoice_total = sum(invoice_total for invoices with hold_decision == "HOLD")
releasable_invoice_total = sum(invoice_total for invoices with hold_decision == "RELEASE")
close_balance = opening_balance + invoice_total - scheduled_payments
```

### Chargeback Computations

```
chargeback_amount = basis_quantity * unit_cost
net_release_amount = invoice_total - approved_chargeback_amount
```

Chargeback amounts come from the local chargeback register, not from ProcureOps. Use the register's `basis_quantity * unit_cost` formula.

## Exception Code Catalogue

### Invoice Exception Codes (receiving closeout)

| Code | Condition |
|---|---|
| `INVOICE_QTY_EXCEEDS_RECEIPT` | billed_qty > received_qty for any line |
| `PARTIAL_RECEIPT` | received_qty < ordered_qty for any line |
| `SUPPLIER_WATCH_RISK` | supplier risk_rating == "watch" AND has open risk events |
| `PRICE_MISMATCH` | invoice unit_price != contract unit_price for any line |
| `DAMAGE_REJECTION` | any receipt line has quantity_rejected > 0 |
| `NO_EXCEPTION` | none of the above conditions apply |

### Reason Codes (AP close)

| Code | Condition |
|---|---|
| `APPROVED_THREE_WAY_MATCH` | invoice approved, receipt exists, qty matches, payment scheduled |
| `NO_RECEIPT` | no receipt record exists for the invoice's PO |
| `QTY_VARIANCE` | quantity_billed != quantity_received |
| `SCHEDULED_PAYMENT_FOUND` | at least one payment (scheduled or released) exists for the invoice |

### Blocker Codes (nomination readiness)

| Code | Condition |
|---|---|
| `missing_contract` | No active contract for the SKU-program-supplier combination |
| `supplier_watch` | supplier risk_rating == "watch" |
| `open_supplier_risk` | supplier has open or monitoring risk events as of the as-of date |
| `ap_hold` | An invoice for the SKU's PO has status `on_hold` or `pending_receipt` |
| `pending_receipt` | PO status is not `received` and no receipts exist |
| `late_due_date` | PO due_date is before the as_of_date |
| `none` | No blockers |

### Receiving Exception Codes (AP release)

| Code | Condition |
|---|---|
| `Underage Quantity` | received_qty < ordered_qty |
| `Severe Unmatched Quantity` | received_qty is substantially below ordered_qty or billed_qty (e.g. 90+ units short) |
| `Inspection Hold` | receipt inspection_status is not `passed` or chargeback is pending quality review |
| `AP Quantity Variance` | billed_qty != received_qty |

## Data Selection Rules

### As-of Date Filtering

When the task specifies an as-of date:
- Include receipts with `receipt_date <= as_of_date`
- Include invoices with `invoice_date <= as_of_date`
- Include risk events with `event_date <= as_of_date`
- Include approval events with `event_date <= as_of_date`
- Include budget snapshots with `snapshot_date == as_of_date` (exact match preferred)
- Include payments with `scheduled_date` through the close horizon (if specified)

### Risk Event Selection

- **Open/active risk**: `status == "open"` OR `status == "monitoring"`
- **Severe risk**: `severity == "high"` OR `severity == "critical"`
- **Supplier watch rating alone does not block** unless the task rules explicitly treat it as a blocker. In nomination readiness, `supplier_watch` is a blocker. In change-control, only severe open events block.

### Approval Rules

- Find the **latest** approval event for a requisition by `max(event_date)` among events with `object_id == requisition_id`.
- Only `action == "approved"` passes. All other actions (`submitted`, `returned`, `rejected`) mean approval is not complete.

### Invoice Hold/Release Decision

- `RELEASE`: invoice status is `approved`, three-way match passes (receipt exists, quantities match, unit prices match), and a scheduled/released payment exists.
- `HOLD`: any of invoice status is `on_hold` or `pending_receipt`, no receipt exists, quantity variance exists, or no payment is scheduled.

### Cancelled PO Exclusion

When summing PO totals for contract ceiling or program budget:
- Exclude POs with `status == "cancelled"`.
- Include all other POs regardless of status.

### Receipt Deduplication

- A single PO may have multiple receipts. Include only the receipts explicitly named in the task memo/packet.
- When excluding same-PO receipts, list all receipts for the PO that are not among the target receipt IDs.

## Sorting Rules

- **String IDs sorted ascending**: lexicographic (standard ASCII/Unicode sort). `AP-00001` comes before `AP-00002`, `PO-00031` before `PO-AX17-4481`.
- **Numbers sorted ascending**: numeric sort.
- **Set fields**: output in any order; the evaluator normalizes.
- **Template-specified ordering**: follow the template exactly (e.g., "sort by po_line_id ascending").
