# ProcureOps API record fields

All amounts are USD. Date fields are `YYYY-MM-DD`. List endpoints return
`{"count": n, "results": [...]}`; id endpoints return the bare object.

## /programs  (key: program_id)
`program_id, name, owner, status, priority, region, cost_center, budget_cap,
committed_amount`. `budget_cap` and `committed_amount` mirror the program's
budget snapshot. Statuses seen: active.

## /budget_snapshots  (key: snapshot_id; filter by program_id)
`snapshot_id, program_id, snapshot_date, currency, budget_cap, committed_amount,
pending_invoice_amount`. **Headroom = budget_cap − committed_amount.** Ignore
`pending_invoice_amount` for headroom. Snapshot id pattern: `BUD-<program_id>`.

## /suppliers  (key: supplier_id)
`supplier_id, name, status, risk_rating, region, payment_terms`.
- `status` ∈ {active, quality_hold}.
- `risk_rating` ∈ {low, medium, high, watch}. `watch` is a soft flag
  ("supplier_watch") — context only unless an *open* event is found.

## /items  (key: sku)
`sku, description, category, uom, standard_cost, active, preferred_supplier_id`.

## /contracts  (key: contract_id; filter by program_id, supplier_id, sku)
`contract_id, program_id, supplier_id, sku, status, price_type, unit_price,
ceiling_amount, effective_date, expiry_date, buyer`.
- `status` active/expired etc.; `price_type` e.g. fixed.
- A line "matches contract price" when its `unit_price == contract.unit_price`.

## /purchase_requisitions  (key: requisition_id; filter by program_id)
`requisition_id, program_id, sku, quantity, requester, priority, need_by,
status`. `status` e.g. converted.

## /purchase_orders  (key: po_id; filter by program_id, supplier_id, contract_id)
`po_id, program_id, supplier_id, contract_id (nullable), requisition_id, buyer,
status, order_date, due_date, ship_to, currency, subtotal, tax, total, lines[]`.
- `lines[]`: `{line_id, sku, description, quantity, unit_price}`.
- `status` ∈ {open, confirmed, partial_receipt, received, closed, cancelled}.
- **Exclude `cancelled` POs from contract usage / commitment sums.**
- `subtotal` = Σ(quantity×unit_price); `total` = subtotal + tax (freight is on
  the invoice, not the PO).

## /receipts  (key: receipt_id; filter by po_id; date field receipt_date)
`receipt_id, po_id, supplier_id, warehouse_id, receipt_date, packing_slip,
receiver, status, lines[]`.
- `lines[]`: `{po_line_id, sku, quantity_received, quantity_rejected,
  inspection_status}`.
- `status` ∈ {accepted, accepted_with_note, inspection_hold}.
- `inspection_status` ∈ {passed, variance}.
- A PO can have MORE THAN ONE receipt — fetch them all with
  `?po_id=` and aggregate `quantity_received`, but respect task scoping (a task
  may name one receipt and treat the rest as out-of-scope duplicates).

## /ap/invoices  (key: invoice_id; filter by supplier_id, po_id; date invoice_date)
`invoice_id, po_id, supplier_id, receipt_id (nullable), invoice_date, status,
hold_code (nullable), currency, subtotal, tax, freight, total, lines[]`.
- `lines[]`: `{po_line_id, sku, quantity_billed, unit_price}`.
- `status` ∈ {entered, pending_receipt, on_hold, approved, paid}.
- `hold_code` ∈ {null, NO_RECEIPT, QTY_VARIANCE, PRICE_VARIANCE, SUPPLIER_REVIEW}.
- `total` = subtotal + tax + freight (authoritative — use it directly).

## /ap/payments  (key: payment_id; filter by supplier_id, invoice_id; date scheduled_date)
`payment_id, invoice_id, supplier_id, amount, currency, scheduled_date, status`.
- `status` ∈ {scheduled, released, blocked}.
- A scheduled payment counts toward "scheduled payments" only if
  `scheduled_date <=` the task cutoff.

## /approval_events  (key: event_id; filter by object_id, object_type)
`event_id, object_id, object_type, action, actor, event_date, note_code`.
- **Filter by `object_id` (e.g. a requisition id), NOT `requisition_id`.**
- `action` ∈ {submitted, approved, escalated, returned}. The approval gate is
  satisfied only when the **latest** (max event_date) event has
  `action == approved`. Pick the latest by event_date for `latest_*` fields.

## /vendor_risk_events  (key: event_id; filter by supplier_id; date event_date)
`event_id, supplier_id, status, severity, event_type, event_date,
related_object_id`.
- `status` ∈ {open, monitoring, closed}. `severity` ∈ {low, medium, high}.
- `event_type` ∈ {invoice_variance, quality_hold, late_delivery, bank_change,
  duplicate_invoice_review}.
- **"Open as of date"** = status in {open, monitoring} AND event_date <= as_of.
- **"Severe open"** = the above AND severity == high.
