# ProcureOps API field map

Base URL from the prompt — commonly `http://127.0.0.1:8006`; identical mirror at
`http://127.0.0.1:8056`. All endpoints are read-only `GET`, returning JSON. List
endpoints return `{"count": <n>, "results": [ ... ]}`. Single-record endpoints
return the bare object. Query filters match a field exactly (case-insensitive),
including fields nested inside list values; date-range `start=`/`end=` filter the
collection's primary date field.

## Table of contents
- Programs, Budget snapshots
- Suppliers, Vendor risk events
- Items
- Contracts
- Purchase requisitions, Approval events
- Purchase orders
- Receipts
- AP invoices, AP payments
- Enum value sets
- Filter keys that work
- Derivation cross-reference

## /programs , /programs/<program_id>
Fields: `program_id, name, owner, status, priority, region, cost_center,
budget_cap, committed_amount`.
- Budget headroom = `budget_cap - committed_amount`.

## /budget_snapshots , /budget_snapshots/<snapshot_id>
Fields: `snapshot_id, program_id, snapshot_date, currency, budget_cap,
committed_amount, pending_invoice_amount`.
- One per program; agrees with the program record. `snapshot_id` like `BUD-<program>`.
- Headroom uses `budget_cap - committed_amount`; do NOT subtract
  `pending_invoice_amount`.

## /suppliers , /suppliers/<supplier_id>
Fields: `supplier_id, name, status, risk_rating, region, payment_terms`.
- `risk_rating ∈ {low, watch, high}`; `status` typically `active`.
- `name` is the human-readable supplier name (use for `supplier_name` fields).

## /vendor_risk_events , /vendor_risk_events/<event_id>
Fields: `event_id, supplier_id, event_type, severity, status, event_date,
related_object_id`.
- `status ∈ {open, monitoring, closed}` — "open OR monitoring" counts as active;
  `closed` is excluded.
- `severity ∈ {low, medium, high}`; "severe" = `high`.
- `event_type ∈ {bank_change, duplicate_invoice_review, invoice_variance,
  late_delivery, quality_hold}` (duplicate_invoice_review = the duplicate-invoice
  signal).
- Filter: `?supplier_id=<id>`; scope by `event_date <= as_of`.

## /items , /items/<sku>
Fields: `sku, description, category, uom, standard_cost, preferred_supplier_id,
active`.
- `standard_cost` is a reference cost, NOT the contracted price; use contract/PO/
  invoice unit_price for money math.

## /contracts , /contracts/<contract_id>
Fields: `contract_id, program_id, supplier_id, sku, price_type, unit_price,
ceiling_amount, status, effective_date, expiry_date, buyer`.
- `price_type` e.g. `fixed`; `status` e.g. `active`.
- `ceiling_amount` is the contract spend ceiling (subtotal basis, pre-tax/freight).

## /purchase_requisitions , /purchase_requisitions/<requisition_id>
Requisition records; approvals reference them via `object_id`.

## /approval_events , /approval_events/<event_id>
Fields: `event_id, object_id, object_type, action, actor, event_date, note_code`.
- IMPORTANT: filter on `?object_id=<REQ id>` (NOT `requisition_id`). `object_type`
  e.g. `requisition`.
- `action ∈ {submitted, approved, returned, escalated}`. The "latest" event is the
  one with the max `event_date`. "Approval OK" only when the latest action is
  `approved` (or whichever actions the memo lists as good).

## /purchase_orders , /purchase_orders/<po_id>
Fields: `po_id, program_id, supplier_id, contract_id, requisition_id, buyer,
ship_to, order_date, due_date, status, currency, subtotal, tax, total, lines[]`.
- Each line: `line_id, sku, description, quantity, unit_price`.
- `status ∈ {open, confirmed, partial_receipt, received, closed, cancelled}`.
- PO `total = subtotal + tax` (NO freight on POs).
- `contract_id` may be null. Filter: `?program_id=`, `?supplier_id=`, `?contract_id=`.

## /receipts , /receipts/<receipt_id>
Fields: `receipt_id, po_id, supplier_id, warehouse_id, receipt_date, packing_slip,
receiver, status, lines[]`.
- Each line: `po_line_id, sku, quantity_received, quantity_rejected,
  inspection_status`.
- `status ∈ {accepted, accepted_with_note, inspection_hold}`;
  `inspection_status` e.g. `passed`.
- A PO can have MULTIPLE receipts (`?po_id=<id>` to get all). The in-scope receipt
  for an invoice is the one the invoice/register references; others on the same PO
  are "excluded same-po receipts".

## /ap/invoices , /ap/invoices/<invoice_id>
Fields: `invoice_id, po_id, receipt_id, supplier_id, invoice_date, status,
hold_code, currency, subtotal, freight, tax, total, lines[]`.
- Each line: `po_line_id, sku, quantity_billed, unit_price`.
- `status ∈ {entered, pending_receipt, on_hold, approved, paid}`.
- `hold_code ∈ {null, NO_RECEIPT, PRICE_VARIANCE, QTY_VARIANCE, SUPPLIER_REVIEW}`.
- Invoice `total = subtotal + freight + tax` (freight IS included, unlike PO).
- `receipt_id` null ⇒ no receipt ⇒ NO_RECEIPT hold. Filter: `?supplier_id=`,
  `?po_id=`, `?program_id=`; date scope by `invoice_date`.

## /ap/payments , /ap/payments/<payment_id>
Fields: `payment_id, invoice_id, supplier_id, amount, currency, scheduled_date,
status`.
- `status ∈ {scheduled, released, ...}`. A payment offsets an invoice's close
  balance when `invoice_id` matches a target invoice AND `scheduled_date <= cutoff`.
- Filter: `?supplier_id=`, `?invoice_id=`; date scope by `scheduled_date`.

## Enum value sets (quick reference)
- PO status: `open, confirmed, partial_receipt, received, closed, cancelled`.
- Invoice status: `entered, pending_receipt, on_hold, approved, paid`.
- Invoice hold_code: `null, NO_RECEIPT, PRICE_VARIANCE, QTY_VARIANCE, SUPPLIER_REVIEW`.
- Receipt status: `accepted, accepted_with_note, inspection_hold`.
- Risk status: `open, monitoring, closed`; risk severity: `low, medium, high`.
- Approval action: `submitted, approved, returned, escalated`.
- Supplier risk_rating: `low, watch, high`.

(These are the ProcureOps-internal values. The answer templates often define their
OWN enum strings — map the ProcureOps status to the template's allowed enum; never
invent values not in the template.)

## Filter keys that work (verified)
| Endpoint | Useful exact-match filters |
| --- | --- |
| /purchase_orders | program_id, supplier_id, contract_id |
| /ap/invoices | supplier_id, po_id, program_id; start/end on invoice_date |
| /ap/payments | supplier_id, invoice_id; start/end on scheduled_date |
| /receipts | po_id, supplier_id; start/end on receipt_date |
| /vendor_risk_events | supplier_id; start/end on event_date |
| /approval_events | object_id (the requisition id); start/end on event_date |
| /budget_snapshots | program_id |
| /contracts | program_id, supplier_id, sku |

## Derivation cross-reference
| Answer concept | Records / formula |
| --- | --- |
| budget headroom / remaining_budget | program or budget_snapshot: cap − committed |
| contract noncancelled_subtotal | Σ subtotal of non-cancelled POs on the contract |
| received_qty | Σ quantity_received over accepted receipt lines for the PO line |
| short_qty_vs_po | ordered − received |
| unreceived_billed / quantity_variance | billed − received |
| receipt_completion_ratio | received / ordered (4 dp) |
| quantity_variance_pct | (billed − received) / ordered × 100 (1 dp) |
| received_goods_value | received_qty × unit_price |
| unreceived_goods_value | (billed − received) × unit_price |
| invoice_total | invoice subtotal + freight + tax |
| scheduled_payment_amount | Σ matching payments, scheduled_date ≤ cutoff |
| net_balance_impact | invoice_total − scheduled_payment_amount |
| close_balance | opening + invoice_total − scheduled_payments |
| open supplier risk events | status ∈ {open, monitoring} AND event_date ≤ as_of |
| approval_ok | latest (max event_date) approval action == approved |
| chargeback amount | basis_quantity × unit_cost (from local register) |
| net_release_amount | invoice_total − approved_chargeback_amount |
| max_quantity_with_budget | floor(remaining / (unit_price × (1 + tax_rate))) |
