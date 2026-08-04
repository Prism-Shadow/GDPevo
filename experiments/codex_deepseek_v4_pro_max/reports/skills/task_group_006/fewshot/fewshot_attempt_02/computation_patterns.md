# ProcureOps Computation Patterns

All amounts in USD, rounded to **two decimal places** (cents). Percentages round to **one decimal place**. Ratios round to **four decimal places**.

## Budget Headroom

```
remaining_budget = budget_cap - committed_amount
headroom_after_change = remaining_budget - requested_total
budget_ok = (headroom_after_change >= 0)
max_quantity_with_current_budget = floor(remaining_budget / unit_price)
```

When a budget snapshot is available, prefer the snapshot's `budget_cap` and `committed_amount`. Otherwise use the program record.

## Contract Ceiling

```
noncancelled_subtotal = sum(po.lines.quantity * po.lines.unit_price) for all non-cancelled POs on the contract
headroom_before_change = ceiling_amount - noncancelled_subtotal
headroom_after_change = headroom_before_change - requested_subtotal
ceiling_ok = (headroom_after_change >= 0)
```

Always **exclude cancelled POs** (`status == "cancelled"`) from `noncancelled_subtotal`.

## Quantity Reconciliation (Receiving)

```
short_qty_vs_po = ordered_qty - received_qty
unreceived_billed_qty = billed_qty - received_qty  (cap at 0, never negative)
receipt_completion_ratio = received_qty / ordered_qty
quantity_variance = quantity_billed - quantity_received
quantity_variance_pct = (quantity_variance / ordered_qty) * 100
```

Ensure `unreceived_billed_qty` is never negative. If `received_qty >= billed_qty`, set to `0`.

## Financial Reconciliation

### Goods values

```
received_goods_value = received_qty * unit_price
unreceived_goods_value = short_qty_vs_po * unit_price
```

### Invoice breakout

```
invoice_total = subtotal + freight + tax
```

### Payment and balance

```
scheduled_payment_amount = sum of payment amounts for the invoice through the horizon date supplied by the task (e.g., end of the fiscal month)
net_balance_impact = invoice_total - scheduled_payment_amount
close_balance = opening_balance + invoice_total - scheduled_payment_amount
```

When the task sets `opening_balance` to `0.00`, treat it as a clean-slice reconciliation.

### Chargeback netting

```
net_release_amount = invoice_total - approved_chargeback_amount - pending_chargeback_amount
```

If the chargeback register is provided in a local payload, those amounts are authoritative over API-derived amounts.

## AP Hold / Release Logic

- **RELEASE** when: three-way match passes (PO qty = receipt qty = invoice qty), invoice status is `approved`, and at least one payment is scheduled.
- **HOLD** when: any quantity variance exists, no receipt exists, or invoice status is `on_hold`.
- **Quantity variance** alone (with approved chargeback) → `release_net_after_approved_chargeback`.
- **No receipt** exists for the PO → `hold_missing_receipt`.
- **Inspection hold** with pending quality review → `hold_pending_quality_chargeback`.

## Supplier Balance Status

```
if held_invoice_total > 0 AND releasable_invoice_total == 0: "OPEN_HELD"
if held_invoice_total == 0 AND releasable_invoice_total > 0: "OPEN_APPROVED"
if held_invoice_total == 0 AND releasable_invoice_total == 0: "FULLY_SCHEDULED"
if both > 0: "OPEN_HELD"  (conservative)
```

## Program Summary Aggregation

Group invoice decisions by `program_id`:
- `invoice_count` = count of invoices for the program.
- `invoice_total` = sum of `invoice_total`.
- `held_total` = sum of `invoice_total` where `hold_decision == "HOLD"`.
- `released_total` = sum of `invoice_total` where `hold_decision == "RELEASE"`.
- `net_close_balance` = sum of `net_balance_impact`.

## Readiness Status Derivation

For nomination/decision tasks, derive readiness per line:

```
blockers = []
if no contract_id or contract is null: add "missing_contract"
if supplier risk_rating == "watch": add "supplier_watch"
if any open supplier risk events: add "open_supplier_risk"
if any invoices are on_hold: add "ap_hold"
if received_qty < ordered_qty and status != "fully_received": add "pending_receipt"
if PO due_date is past as_of_date: add "late_due_date"

if blockers is empty: readiness = "ready"
elif only "supplier_watch" (no other blockers): readiness = "at_risk"
else: readiness = "not_ready"
```

## Committee / Nomination Decision

```
if readiness == "ready": decision = "nominate"
elif readiness == "at_risk": decision = "conditional_nomination"
else: decision = "hold"
```
