# ProcureOps API & data model reference

Base URL `http://127.0.0.1:8056` (mirror `http://127.0.0.1:8006`). Read-only GET,
JSON. List endpoints return `{"count": n, "results": [...]}`; `/<collection>/<id>`
returns the bare object.

## Endpoints and id keys

| Collection | List / by-id | id field | Primary date (for start/end) |
|---|---|---|---|
| Programs | `/programs`, `/programs/<id>` | `program_id` | — |
| Suppliers | `/suppliers`, `/suppliers/<id>` | `supplier_id` | — |
| Items | `/items`, `/items/<sku>` | `sku` | — |
| Contracts | `/contracts`, `/contracts/<id>` | `contract_id` | `effective_date` |
| Requisitions | `/purchase_requisitions`, `/.../<id>` | `requisition_id` | — |
| Purchase orders | `/purchase_orders`, `/.../<id>` | `po_id` | `order_date` |
| Receipts | `/receipts`, `/.../<id>` | `receipt_id` | `receipt_date` |
| AP invoices | `/ap/invoices`, `/.../<id>` | `invoice_id` | `invoice_date` |
| AP payments | `/ap/payments`, `/.../<id>` | `payment_id` | `scheduled_date` |
| Approval events | `/approval_events`, `/.../<id>` | `event_id` | `event_date` |
| Budget snapshots | `/budget_snapshots`, `/.../<id>` | `snapshot_id` | `snapshot_date` |
| Vendor risk events | `/vendor_risk_events`, `/.../<id>` | `event_id` | `event_date` |

Filters match a field exactly, case-insensitive, including inside list values
(so `/ap/invoices?sku=LMP-228` matches an invoice whose line has that sku).

## Record shapes (fields you actually use)

- **program**: `program_id, name, owner, budget_cap, committed_amount, status,
  priority, cost_center, region`.
- **budget_snapshot**: `snapshot_id, program_id, snapshot_date, budget_cap,
  committed_amount, pending_invoice_amount, currency`. (Headroom uses cap and
  committed; `pending_invoice_amount` is NOT used for headroom.)
- **supplier**: `supplier_id, name, status, risk_rating (low|watch|...),
  payment_terms, region`.
- **item**: `sku, description, category, standard_cost, preferred_supplier_id,
  uom, active`. The `sku` IS the record id (`/items/<sku>`).
- **contract**: `contract_id, program_id, supplier_id, sku, price_type
  (fixed|...), unit_price, ceiling_amount, status (active|...), effective_date,
  expiry_date, buyer`.
- **purchase_order**: `po_id, program_id, supplier_id, contract_id (may be null),
  requisition_id, status (partial_receipt|confirmed|cancelled|closed|...),
  lines:[{line_id, sku, quantity, unit_price, description}], subtotal, tax,
  total, order_date, due_date, ship_to, buyer, currency`.
- **receipt**: `receipt_id, po_id, supplier_id, warehouse_id, receipt_date,
  packing_slip, receiver, status (accepted|accepted_with_note|inspection_hold|
  ...), lines:[{po_line_id, sku, quantity_received, quantity_rejected,
  inspection_status}]`.
- **ap_invoice**: `invoice_id, po_id, supplier_id, receipt_id (may be null),
  status (approved|on_hold|pending_receipt|paid|...), hold_code (QTY_VARIANCE|
  PRICE_VARIANCE|NO_RECEIPT|null), lines:[{po_line_id, sku, quantity_billed,
  unit_price}], subtotal, freight, tax, total, invoice_date, currency`.
- **payment**: `payment_id, invoice_id, supplier_id, amount, scheduled_date,
  status (scheduled|released|...), currency`.
- **approval_event**: `event_id, object_id (e.g. a requisition id), action
  (submitted|approved|...), actor, event_date`.
- **vendor_risk_event**: `event_id, supplier_id, event_type, severity (low|
  medium|high|critical), status (open|monitoring|closed), event_date,
  related_object_id`.

## Join map

- PO → program (`program_id`), supplier (`supplier_id`), contract
  (`contract_id`, may be null ⇒ "missing_contract"), requisition.
- Receipt → PO (`po_id`); a PO can have **several** receipts.
- Invoice → PO (`po_id`) and to a specific receipt (`receipt_id`, may be null);
  a PO can have **several** invoices. Use `invoice.receipt_id` for that
  invoice's received qty, not the union of all receipts on the PO.
- Payment → invoice (`invoice_id`) and supplier. Match by invoice id.
- Approval → object (`object_id`, e.g. the source requisition).
- Risk → supplier (`supplier_id`).
- Contract usage → all POs with that `contract_id` (exclude cancelled for ceiling).

## Join gotchas (verified)
- **Invoice received-qty = its own linked receipt**, not all PO receipts. A PO
  with two receipts (one per invoice) must not double-count.
- **`contract_id` null on a PO ⇒ no commercial basis** ⇒ `missing_contract`
  blocker and `commercial_basis_id = null`.
- **Payment-to-invoice is by invoice id AND date cutoff (inclusive)**; a
  supplier's other scheduled payments do not net against an unrelated invoice.
- **Risk events filter by supplier**, then by status (open/monitoring) and date.
- Some anchors named in a memo may not exist in the shared data (e.g. "PO-73xx"
  families). Use the generated/aliased ids the packet provides instead, and
  classify the stale alias note as a *supporting-only* source.

## Field-by-field SOP checklist
1. Skeleton from `answer_template.json` (every leaf, enum, ordering, precision).
2. Scope: as-of/cutoff date, program(s), anchors, opening balances, tax rate,
   "good actions", netting definitions — from prompt + memo.
3. Fetch anchors by id; expand by program/PO/supplier filters.
4. Derive each field with the verified formula (SKILL.md "Business rules").
5. Apply date scoping (inclusive) on every `as of <date>` list.
6. Conventions: cents; set vs sorted; exact enum spelling; passthrough verbatim.
7. Run the "Mistakes the blind pass made" self-check.
8. Emit only the JSON object.
