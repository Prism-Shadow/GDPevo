# ProcureOps API Endpoints

Base URL: provided as `TASK_ENV_BASE_URL` (typically `http://localhost:9006`).
No authentication. Every endpoint returns `{"count": <int>, "results": [...]}`.

## Endpoint list

| Endpoint | Returns |
|----------|---------|
| `/suppliers` | All supplier records |
| `/items` | All item/SKU records |
| `/programs` | All program records |
| `/contracts` | All contract records |
| `/purchase_requisitions` | All requisition records |
| `/purchase_orders` | All purchase order records (with lines) |
| `/receipts` | All receipt records (with lines) |
| `/ap/invoices` | All AP invoice records (with lines) |
| `/ap/payments` | All scheduled payment records |
| `/approvals` | All approval event records |
| `/budget_snapshots` | All budget snapshot records |
| `/vendor_risk_events` | All vendor risk event records |
| `/manifest` | Environment metadata (anchor IDs, seed, record counts) |

## Entity schemas

### Supplier (`/suppliers`)

```json
{
  "supplier_id": "SUP-LUMA",
  "name": "LumaPro Industrial",
  "status": "active | quality_hold",
  "risk_rating": "low | medium | watch | high",
  "payment_terms": "NET15 | NET30 | NET45 | NET60",
  "region": "US | DE | JP | MX | SE"
}
```

### Program (`/programs`)

```json
{
  "program_id": "PRG-AX17",
  "name": "Axis refresh line 17",
  "owner": "Elena Marsh",
  "status": "active",
  "priority": "high | medium | low",
  "budget_cap": 285000.0,
  "committed_amount": 216430.4,
  "cost_center": "CC-410",
  "region": "North America",
  "currency": "USD"
}
```

### Budget Snapshot (`/budget_snapshots`)

```json
{
  "snapshot_id": "BUD-PRG-AX17",
  "program_id": "PRG-AX17",
  "snapshot_date": "2026-06-01",
  "budget_cap": 285000.0,
  "committed_amount": 216430.4,
  "pending_invoice_amount": 224946.47,
  "currency": "USD"
}
```

Use `budget_cap - committed_amount` as remaining budget.  The
`pending_invoice_amount` is informational and should not be subtracted
from budget again (it overlaps with committed amounts).

### Contract (`/contracts`)

```json
{
  "contract_id": "CR-LMP-228",
  "program_id": "PRG-AX17",
  "supplier_id": "SUP-LUMA",
  "sku": "LMP-228",
  "status": "active | expired | terminated",
  "price_type": "fixed | variable",
  "unit_price": 84.50,
  "ceiling_amount": 185000.0,
  "buyer": "Nora Fields",
  "effective_date": "2025-11-01",
  "expiry_date": "2026-12-31"
}
```

Contract ceiling check: sum the `subtotal` of all POs referencing this
contract whose status is **not** `cancelled`.  Exclude cancelled POs from
the usage calculation unless the task instructions explicitly say otherwise.

### Purchase Requisition (`/purchase_requisitions`)

```json
{
  "requisition_id": "REQ-AX17-141",
  "program_id": "PRG-AX17",
  "sku": "LMP-228",
  "quantity": 240,
  "requester": "Elena Marsh",
  "status": "converted | submitted | approved | rejected",
  "priority": "high",
  "need_by": "2026-06-18"
}
```

### Purchase Order (`/purchase_orders`)

```json
{
  "po_id": "PO-AX17-4481",
  "program_id": "PRG-AX17",
  "supplier_id": "SUP-LUMA",
  "contract_id": "CR-LMP-228 | null",
  "requisition_id": "REQ-AX17-141",
  "buyer": "Nora Fields",
  "status": "open | confirmed | received | partial_receipt | closed | cancelled",
  "order_date": "2026-05-16",
  "due_date": "2026-06-14",
  "ship_to": "WH-BLUE | WH-GOLD | WH-SILVER",
  "subtotal": 20280.0,
  "tax": 1470.30,
  "total": 21750.30,
  "currency": "USD",
  "lines": [
    {
      "line_id": 1,
      "sku": "LMP-228",
      "description": "LumaPro sealed lamp module",
      "quantity": 240,
      "unit_price": 84.50
    }
  ]
}
```

Key PO status meanings:
- `open`: PO issued, no activity yet.
- `confirmed`: PO acknowledged, no receipts yet.
- `partial_receipt`: some but not all lines fully received.
- `received`: all lines fully received.
- `closed`: fulfilled and closed.
- `cancelled`: voided (exclude from contract ceiling and budget calculations).

`total` = `subtotal + tax`.  Freight is only on invoices, not on POs.

### Receipt (`/receipts`)

```json
{
  "receipt_id": "RCV-BLUE-14",
  "po_id": "PO-AX17-4481",
  "supplier_id": "SUP-LUMA",
  "warehouse_id": "WH-BLUE",
  "receiver": "M. Webb",
  "receipt_date": "2026-05-30",
  "packing_slip": "PK-LUMA-5831",
  "status": "accepted | accepted_with_note | inspection_hold",
  "lines": [
    {
      "po_line_id": 1,
      "sku": "LMP-228",
      "quantity_received": 216,
      "quantity_rejected": 0,
      "inspection_status": "passed | variance"
    }
  ]
}
```

Multiple receipts can exist for a single PO.  Sum `quantity_received`
across all receipts for a PO line to get the total received for that line.

### AP Invoice (`/ap/invoices`)

```json
{
  "invoice_id": "AP-LUMA-7714",
  "po_id": "PO-AX17-4481",
  "supplier_id": "SUP-LUMA",
  "receipt_id": "RCV-BLUE-14 | null",
  "status": "entered | approved | on_hold | pending_receipt | paid",
  "hold_code": "QTY_VARIANCE | NO_RECEIPT | PRICE_VARIANCE | SUPPLIER_REVIEW | null",
  "invoice_date": "2026-06-01",
  "subtotal": 20280.0,
  "freight": 320.0,
  "tax": 1470.30,
  "total": 22070.3,
  "currency": "USD",
  "lines": [
    {
      "po_line_id": 1,
      "sku": "LMP-228",
      "quantity_billed": 240,
      "unit_price": 84.50
    }
  ]
}
```

`total` = `subtotal + freight + tax`.  When freight is zero, total =
subtotal + tax.  The PO's `total` omits freight, so invoice total will
typically be higher than PO total when freight is charged.

### AP Payment (`/ap/payments`)

```json
{
  "payment_id": "PAY-00001",
  "invoice_id": "AP-HEXEL-3309",
  "supplier_id": "SUP-HEXEL",
  "amount": 28909.24,
  "scheduled_date": "2026-06-30",
  "status": "scheduled | blocked | released",
  "currency": "USD"
}
```

Only `scheduled` or `released` payments through the task's close date
(or the user-specified horizon) count toward reducing a supplier balance.

### Approval Event (`/approvals`)

```json
{
  "event_id": "APR-00001",
  "object_id": "REQ-AX17-141",
  "object_type": "requisition",
  "action": "submitted | approved | rejected",
  "actor": "Compliance Desk",
  "note_code": "EXPEDITE | null",
  "event_date": "2026-05-02"
}
```

For a requisition, the latest event by date determines whether it is
approved.  If the latest action is `submitted`, the requisition is not
yet approved.

### Vendor Risk Event (`/vendor_risk_events`)

```json
{
  "event_id": "VRE-00009",
  "supplier_id": "SUP-VANTIX",
  "event_type": "quality_incident | bank_change | regulatory_flag | shipment_delay | ...",
  "severity": "low | medium | high | critical",
  "status": "open | monitoring | closed",
  "event_date": "2026-04-30",
  "related_object_id": "PO-AX17-4519 | null"
}
```

An event is active (should be flagged) when its status is `open` (any
severity) or `monitoring` (watch-level or higher).  Closed events are
historical only.  When a supplier has a `watch` risk rating, treat that
as a flag even if no individual open event is severe.

### Item (`/items`)

```json
{
  "sku": "LMP-228",
  "description": "Sealed lamp module",
  "category": "electrical | mechanical | sensor | ...",
  "unit_of_measure": "EA"
}
```

Items are mapped to POs, receipts, invoices, and contracts through the
`sku` field.
