# ProcureOps Workflow Reference

## Endpoint Map

- `/items`: SKU metadata, preferred supplier, standard cost, UOM
- `/suppliers`: supplier name, status, region, risk rating, payment terms
- `/programs`: owner, budget cap, committed amount, status, cost center, region
- `/contracts`: contract status, price type, unit price, ceiling, program, SKU, supplier
- `/purchase_requisitions`: request quantity, requester, need-by, status, program, SKU
- `/purchase_orders`: quantities, subtotal, tax, total, due date, status, contract, requisition, supplier, ship-to
- `/receipts`: received/rejected quantities, receipt status, warehouse, packing slip, receiver
- `/ap/invoices`: billed quantities, subtotal, freight, tax, total, status, hold code, receipt, PO, supplier
- `/ap/payments`: scheduled/released/blocked payments with amount and scheduled date
- `/approvals`: approval events with object_id, object_type, action, actor, date
- `/budget_snapshots`: budget cap, committed amount, pending invoice amount, snapshot date
- `/vendor_risk_events`: event status, severity, date, related object, supplier

## Common Formulas

- `budget_headroom = budget_cap - committed_amount`
- `contract_headroom_before = ceiling_amount - noncancelled_subtotal`
- `contract_headroom_after = ceiling_amount - noncancelled_subtotal - requested_subtotal`
- `requested_subtotal = quantity * unit_price`
- `requested_total = requested_subtotal + tax (+ freight only if the memo says to include freight)`
- `budget_after_change = remaining_budget - requested_total`
- `receipt_completion_ratio = received_qty / ordered_qty`
- `short_qty_vs_po = ordered_qty - received_qty`
- `unreceived_billed_qty = billed_qty - received_qty`
- `quantity_variance = billed_qty - received_qty`
- `quantity_variance_pct = quantity_variance / ordered_qty * 100`
- `received_goods_value = received_qty * unit_price`
- `unreceived_goods_value = short_qty_vs_po * unit_price`
- `invoice_total = subtotal + freight + tax`
- `net_balance_impact = invoice_total - scheduled_payment_amount`
- `close_balance = opening_balance + invoice_total - scheduled_payments`
- `approved_chargeback_amount = sum of approved chargebacks in scope`
- `pending_chargeback_amount = sum of pending-quality chargebacks in scope`
- `net_release_amount = invoice_total - approved_chargeback_amount when releasing; 0 when holding`

## Evidence Rules

- Use the memo to find scope, but use the API for truth.
- If the memo labels a note as supporting-only, do not fold it into authoritative totals unless the template explicitly asks for it.
- If the memo or prompt says to exclude cancelled POs, stale aliases, or other subsets, honor that subset exactly.
- Use the prompt's cutoff date when deciding whether a risk event, receipt, approval, or payment is in scope.
- For AP close, if a payment cutoff is named, sum only the payments that fall on or before that cutoff and only the statuses the prompt says to count.
- For approvals, use the latest event for the source requisition.
- For supplier risk, include only open or monitoring events as of the cutoff, and only severe events when the template distinguishes them.
- For PO, receipt, and invoice joins, match on the explicit IDs first, then confirm the line-level SKU and quantity.
- For ordered, received, and billed comparisons, use the PO quantity as the denominator when the template asks for a percentage.

## Ordering Rules

- Sort only when the template says to sort.
- For set-like fields, de-duplicate then sort if the template says sorted; otherwise preserve operational order if it matters.
- Keep `*_ids` lists stable and exact.
