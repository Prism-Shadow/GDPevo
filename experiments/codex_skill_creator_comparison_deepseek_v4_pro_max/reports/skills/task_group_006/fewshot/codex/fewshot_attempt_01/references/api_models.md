# ProcureOps API Reference

## Base URL

The API runs at `<TASK_ENV_BASE_URL>`, set by the task runner. No authentication required.

## Endpoints

Each endpoint returns `{"count": N, "results": [...]}`. All lists are unsorted from the API unless noted.

### GET /manifest

```json
{
  "anchor_ids": ["string"],
  "data_file": "string",
  "environment": "ProcureOps",
  "generated_at": "YYYY-MM-DDThh:mm:ssZ",
  "record_counts": {
    "ap_invoices": 47,
    "approval_events": 36,
    "budget_snapshots": 10,
    "contracts": 17,
    "items": 32,
    "payments": 27,
    "programs": 10,
    "purchase_orders": 57,
    "purchase_requisitions": 37,
    "receipts": 28,
    "suppliers": 14,
    "vendor_risk_events": 35
  },
  "seed": 6006
}
```

### GET /suppliers

```json
{
  "supplier_id": "SUP-XXXX",
  "name": "string",
  "region": "US|DE|JP|MX|SE",
  "status": "active|quality_hold|inactive",
  "risk_rating": "low|medium|high|watch",
  "payment_terms": "NET15|NET30|NET45|NET60"
}
```

### GET /items

```json
{
  "sku": "string",
  "description": "string",
  "category": "electrical|controls|seals|hydraulics",
  "uom": "EA|KIT|BOX|M",
  "standard_cost": 0.0,
  "preferred_supplier_id": "SUP-XXXX",
  "active": true
}
```

### GET /programs

```json
{
  "program_id": "PRG-XXXX",
  "name": "string",
  "status": "active|planning|closed",
  "priority": "critical|high|medium|low",
  "region": "North America|EMEA|APAC",
  "owner": "string",
  "cost_center": "CC-NNN",
  "budget_cap": 0.0,
  "committed_amount": 0.0
}
```

The budget_cap field on the program record is the program's total budget ceiling. Calculate remaining budget as `budget_cap - committed_amount`. Note that budget_snapshots provide a point-in-time view you should prefer when one exists for the task's as_of_date.

### GET /contracts

```json
{
  "contract_id": "CR-XXXX",
  "supplier_id": "SUP-XXXX",
  "program_id": "PRG-XXXX",
  "sku": "string",
  "status": "active|expired|draft|cancelled",
  "price_type": "fixed|indexed|not_to_exceed",
  "buyer": "string",
  "unit_price": 0.0,
  "ceiling_amount": 0.0,
  "effective_date": "YYYY-MM-DD",
  "expiry_date": "YYYY-MM-DD"
}
```

When computing contract headroom, sum non-cancelled PO subtotals linked to the contract_id and subtract from ceiling_amount. Exclude POs where `status == "cancelled"`.

### GET /purchase_requisitions

```json
{
  "requisition_id": "REQ-XXXX",
  "sku": "string",
  "program_id": "PRG-XXXX",
  "quantity": 0,
  "requester": "string",
  "priority": "critical|high|medium|low",
  "need_by": "YYYY-MM-DD",
  "status": "draft|submitted|approved|rejected|converted"
}
```

### GET /purchase_orders

```json
{
  "po_id": "PO-XXXX",
  "program_id": "PRG-XXXX",
  "requisition_id": "REQ-XXXX",
  "contract_id": "CR-XXXX|null",
  "supplier_id": "SUP-XXXX",
  "buyer": "string",
  "ship_to": "WH-XXXX",
  "status": "open|received|partial_receipt|cancelled",
  "currency": "USD",
  "order_date": "YYYY-MM-DD",
  "due_date": "YYYY-MM-DD",
  "subtotal": 0.0,
  "tax": 0.0,
  "total": 0.0,
  "lines": [
    {
      "line_id": 1,
      "sku": "string",
      "description": "string",
      "quantity": 0,
      "unit_price": 0.0
    }
  ]
}
```

PO total = subtotal + tax. Freight is on the invoice, not the PO.

### GET /receipts

```json
{
  "receipt_id": "RCV-XXXX",
  "po_id": "PO-XXXX",
  "supplier_id": "SUP-XXXX",
  "warehouse_id": "WH-XXXX",
  "status": "accepted|accepted_with_note|inspection_hold|rejected",
  "receipt_date": "YYYY-MM-DD",
  "packing_slip": "string",
  "receiver": "string",
  "lines": [
    {
      "po_line_id": 1,
      "sku": "string",
      "quantity_received": 0,
      "quantity_rejected": 0,
      "inspection_status": "passed|failed|pending"
    }
  ]
}
```

When computing total received quantity for a PO line, sum `quantity_received` across all receipts for that PO. Receipt `status == "inspection_hold"` means the goods are physically received but quality disposition is pending.

### GET /ap/invoices

```json
{
  "invoice_id": "AP-XXXX",
  "po_id": "PO-XXXX",
  "supplier_id": "SUP-XXXX",
  "receipt_id": "RCV-XXXX|null",
  "status": "approved|on_hold|pending_receipt|paid|voided",
  "hold_code": "QTY_VARIANCE|PRICE_VARIANCE|NO_RECEIPT|DUPLICATE|null",
  "currency": "USD",
  "invoice_date": "YYYY-MM-DD",
  "subtotal": 0.0,
  "freight": 0.0,
  "tax": 0.0,
  "total": 0.0,
  "lines": [
    {
      "po_line_id": 1,
      "sku": "string",
      "quantity_billed": 0,
      "unit_price": 0.0
    }
  ]
}
```

Invoice total = subtotal + freight + tax.

### GET /ap/payments

```json
{
  "payment_id": "PAY-XXXX",
  "invoice_id": "AP-XXXX",
  "supplier_id": "SUP-XXXX",
  "amount": 0.0,
  "currency": "USD",
  "status": "scheduled|released|blocked",
  "scheduled_date": "YYYY-MM-DD"
}
```

A scheduled payment reduces the close balance for a supplier. Blocked payments do not count as scheduled.

### GET /approvals

```json
{
  "event_id": "APR-XXXX",
  "object_id": "REQ-XXXX|PO-XXXX|...",
  "object_type": "requisition|purchase_order|...",
  "action": "submitted|approved|returned|rejected|escalated",
  "actor": "string",
  "event_date": "YYYY-MM-DD",
  "note_code": "EXPEDITE|CAPEX_CHECK|NORMAL_REVIEW|BUDGET_OK|MISSING_QUOTE"
}
```

To check if a requisition is approved, find the latest approval event for that requisition_id by event_date. Only `action == "approved"` counts as approved.

### GET /budget_snapshots

```json
{
  "snapshot_id": "BUD-PRG-XXXX",
  "program_id": "PRG-XXXX",
  "snapshot_date": "YYYY-MM-DD",
  "budget_cap": 0.0,
  "committed_amount": 0.0,
  "pending_invoice_amount": 0.0,
  "currency": "USD"
}
```

Budget snapshots provide a point-in-time view. Remaining budget = `budget_cap - committed_amount`. `pending_invoice_amount` is the total of invoices not yet fully paid for that program.

### GET /vendor_risk_events

```json
{
  "event_id": "VRE-XXXX",
  "supplier_id": "SUP-XXXX",
  "event_type": "bank_change|quality_hold|late_delivery|invoice_variance|duplicate_invoice_review",
  "status": "open|closed|monitoring",
  "severity": "low|medium|high",
  "related_object_id": "PO-XXXX",
  "event_date": "YYYY-MM-DD"
}
```

For risk assessment, filter events by supplier_id. "open" status events are active risks. "monitoring" events are informational but should be noted. A "severe" event means severity == "high". Supplier risk_rating == "watch" on the supplier record is a separate signal from individual risk events.

## Entity Relationship Map

```
Program (program_id) 1──N Purchase Order (program_id, requisition_id)
Program (program_id) 1──N Purchase Requisition (program_id)
Program (program_id) 1──N Contract (program_id)
Program (program_id) 1──N Budget Snapshot (program_id)

Item (sku) 1──1 Preferred Supplier (preferred_supplier_id)
Item (sku) 1──N Purchase Requisition (sku)
Item (sku) 1──N PO Line (sku)
Item (sku) 1──N Contract (sku)

Supplier (supplier_id) 1──N Contract (supplier_id)
Supplier (supplier_id) 1──N Purchase Order (supplier_id)
Supplier (supplier_id) 1──N Receipt (supplier_id)
Supplier (supplier_id) 1──N AP Invoice (supplier_id)
Supplier (supplier_id) 1──N AP Payment (supplier_id)
Supplier (supplier_id) 1──N Vendor Risk Event (supplier_id)

Contract (contract_id) 1──N Purchase Order (contract_id)

Requisition (requisition_id) 1──N Purchase Order (requisition_id)
Requisition (requisition_id) 1──N Approval Event (object_id where object_type=="requisition")

Purchase Order (po_id) 1──N Receipt (po_id)
Purchase Order (po_id) 1──N AP Invoice (po_id)

Receipt (receipt_id) 1──N AP Invoice (receipt_id)

AP Invoice (invoice_id) 1──N AP Payment (invoice_id)
```

## Key Calculation Patterns

### Three-Way Match
Compare PO quantity, receipt quantity, and invoice quantity for a given PO line:
- quantity_variance = billed_qty - received_qty
- variance_pct = (quantity_variance / po_ordered_qty) * 100

### Contract Ceiling Check
1. Find all POs linked to contract_id
2. Exclude cancelled POs
3. Sum subtotals of remaining POs -> noncancelled_subtotal
4. headroom = ceiling_amount - noncancelled_subtotal
5. headroom_after_change = headroom - requested_subtotal
6. ceiling_ok = headroom_after_change >= 0

### Budget Check
1. Get budget snapshot for program_id (prefer snapshot_date matching as_of_date)
2. remaining = budget_cap - committed_amount
3. requested_total = requested_subtotal + tax (tax = requested_subtotal * tax_rate_percent / 100)
4. budget_after_change = remaining - requested_total
5. budget_ok = budget_after_change >= 0
6. max_quantity_with_current_budget = floor(remaining / (unit_price * (1 + tax_rate/100)))

### Vendor Balance Reconciliation
For each supplier in scope:
- opening_balance: given by task (often 0.00 for a slice)
- invoice_total: sum of all scoped invoice totals
- scheduled_payments: sum of invoice amounts where payment status is "scheduled" (not "blocked" or "released")
- held_invoice_total: sum of invoices on hold
- releasable_invoice_total: sum of approved invoices not yet fully scheduled
- close_balance = opening_balance + invoice_total - scheduled_payments

### Chargeback Netting
Net release amount = invoice_total - approved_chargeback_amount. Pending chargebacks reduce net to 0.

### Budget Headroom
For program summary: budget_headroom = budget_cap - committed_amount. This differs from remaining budget in the snapshot in that committed_amount on the program record may differ from the snapshot.

## Status Value Dictionaries

### PO Status
- `open`: No receipts posted
- `partial_receipt`: Some but not all quantity received
- `received`: Full quantity received
- `cancelled`: Order cancelled

### Invoice Status
- `approved`: Ready for payment
- `on_hold`: Blocked (check hold_code)
- `pending_receipt`: Waiting for receipt before processing
- `paid`: Fully paid
- `voided`: Cancelled

### Receipt Status
- `accepted`: Clean receipt
- `accepted_with_note`: Accepted but with annotation
- `inspection_hold`: Physically received, quality review pending
- `rejected`: Rejected

### Requisition Status
- `draft`: Not yet submitted
- `submitted`: Awaiting approval
- `approved`: Ready for PO conversion
- `rejected`: Denied
- `converted`: Turned into a PO

### Approval Actions
- `approved`: Final approval granted
- `submitted`: Under review (not yet approved)
- `returned`: Sent back for revision
- `rejected`: Denied
- `escalated`: Routed to higher authority

### Risk Event Status
- `open`: Active, unresolved
- `closed`: Resolved
- `monitoring`: Being watched, not resolved

## List Sorting Conventions

Unless a task template specifies otherwise:
- ID lists: sort ascending alphabetically (string sort)
- SKU lists: sort ascending alphabetically
- Lines in arrays: order by their natural key (e.g., invoice_id, po_line_id, supplier_id)

## Numerical Precision

All USD amounts round to 2 decimal places (cents). Ratios and percentages round to specified precision (typically 4 decimals for ratios, 1 decimal for percentages).
