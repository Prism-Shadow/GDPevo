# ProcureOps API Guide

Read this when you need the exact endpoints, filter behavior, response shape, or
record schemas to pull source data for a task.

## Base URL and shape

- Base: `http://127.0.0.1:8056` (mirror `http://127.0.0.1:8006` serves identical
  data; if the prompt names a different port, the base above still works).
- All requests are HTTP GET, read-only JSON.
- `GET /health` → `{ok, seed, service}`. `GET /manifest` → record counts, anchor ids,
  seed. Use the manifest early to sanity-check that the data you expect exists.
- A **list** response is `{"count": <n>, "results": [ ... ]}`. A **single-id** fetch
  (`/collection/<id>`) returns the bare record object (no wrapper).

## Collections

```
/programs                /programs/<program_id>
/suppliers               /suppliers/<supplier_id>
/items                   /items/<sku>
/contracts               /contracts/<contract_id>
/purchase_requisitions   /purchase_requisitions/<requisition_id>
/purchase_orders         /purchase_orders/<po_id>
/receipts                /receipts/<receipt_id>
/ap/invoices             /ap/invoices/<invoice_id>
/ap/payments             /ap/payments/<payment_id>
/approval_events         /approval_events/<event_id>
/budget_snapshots        /budget_snapshots/<snapshot_id>
/vendor_risk_events      /vendor_risk_events/<event_id>
```

## Filtering

- Query-string filters match a field **exactly** and **case-insensitively**, including
  fields nested inside list values on a record. Common, reliable filters:
  - `/budget_snapshots?program_id=PRG-AX17`
  - `/purchase_orders?program_id=PRG-...` , `/purchase_orders?supplier_id=SUP-...`
  - `/ap/invoices?supplier_id=SUP-...` , `/ap/invoices?po_id=PO-...`
  - `/ap/payments?supplier_id=SUP-...` , `/ap/payments?invoice_id=AP-...`
  - `/receipts?po_id=PO-...` , `/receipts?supplier_id=SUP-...`
  - `/vendor_risk_events?supplier_id=SUP-...`
- **Date-range filters** `start=` and `end=` apply to each collection's primary date
  field: `receipts.receipt_date`, `ap_invoices.invoice_date`,
  `payments.scheduled_date`, `vendor_risk_events.event_date`, etc. Both bounds are
  inclusive.
- Prefer **filter + verify** over a single bare id when you must enumerate everything
  tied to a parent (e.g. "all receipts for this PO", "all invoices for this PO"). A
  by-id fetch of one record can hide siblings that change the answer.

## Record schemas (the fields that actually drive answers)

### programs
`program_id, name, owner, status, priority, budget_cap, committed_amount,
cost_center, region`. Note: the program record carries `budget_cap` and
`committed_amount` directly, but the **budget_snapshot** is the dated source of truth
for budget math (see below).

### budget_snapshots
`snapshot_id, program_id, snapshot_date, budget_cap, committed_amount,
pending_invoice_amount, currency`. One snapshot per program in this dataset.
- **Remaining / headroom uses `committed_amount`, NOT `pending_invoice_amount`.**
  `remaining_budget = budget_cap - committed_amount`. `pending_invoice_amount` is a
  separate exposure figure and is a distractor for headroom.

### contracts
`contract_id, status, price_type (fixed/...), unit_price, ceiling_amount, ...`.
Contract `unit_price` is the commercial basis used for `contract_unit_price` and for
contract-ceiling exposure math.

### purchase_orders
`po_id, program_id, supplier_id, contract_id, status, due_date, order_date,
requisition_id, ship_to, lines[{line_id, sku, quantity, unit_price, description}],
subtotal, tax, total`.
- Statuses seen: `open, confirmed, partial_receipt, closed, cancelled`.
- **`contract_id` may be null** → no commercial basis → `missing_contract` blocker.
- Ordered qty for a line = `lines[].quantity`. Line subtotal = quantity * unit_price.

### receipts
`receipt_id, po_id, supplier_id, warehouse_id, receipt_date, packing_slip, receiver,
status, lines[{po_line_id, sku, quantity_received, quantity_rejected,
inspection_status}]`.
- Statuses seen: `accepted, accepted_with_note, inspection_hold`.
- A PO with zero receipt rows = nothing received.

### ap/invoices
`invoice_id, po_id, supplier_id, receipt_id, status, hold_code, invoice_date,
currency, freight, tax, subtotal, total, lines[{po_line_id, sku, quantity_billed,
unit_price}]`.
- Statuses seen: `approved, on_hold, pending_receipt, paid`.
- `hold_code` values seen: `QTY_VARIANCE, PRICE_VARIANCE, NO_RECEIPT, null`.
- **Key distinction:** `status == "on_hold"` is a genuine AP hold. A
  `pending_receipt` status (often paired with `hold_code == "NO_RECEIPT"`) is NOT an
  AP hold — it is a missing-receipt condition. Do not treat every non-null hold_code
  as an AP hold. (See mistakes.md M1.)

### ap/payments
`payment_id, invoice_id, supplier_id, amount, scheduled_date, status, currency`.
- Statuses seen: `scheduled, released`.
- A payment belongs to exactly one invoice via `invoice_id`. Match payments to an
  invoice by `invoice_id`, never by supplier alone. (See mistakes.md M2.)

### approval_events
`event_id, ... action, actor, event_date ...`, tied to a requisition.
- Actions seen include `submitted, approved`. "Approved" requires an event whose
  action is literally `approved`; a requisition whose own status is `converted` is NOT
  evidence of an approval event. Take the **latest** event by `event_date`.

### vendor_risk_events
`event_id, supplier_id, event_type, severity (low/medium/high), status, event_date,
related_object_id`.
- Statuses: `open, monitoring, closed`.
- **"Open or monitoring as of <as_of>"** = `status in {open, monitoring}` AND
  `event_date <= as_of_date`. Closed events are always excluded.
- **"Severe open event"** = `status == open` AND `severity == "high"`. A `watch`
  supplier rating or a `medium` open event is context only, not a severe blocker.

### suppliers
`supplier_id, name, status, risk_rating (e.g. low/watch/...), ...`. `risk_rating ==
"watch"` drives the `supplier_watch` blocker / `SUPPLIER_WATCH_RISK` exception, but is
context-only for "severe" gating.
