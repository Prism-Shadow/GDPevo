# ProcureOps API Reference

## Base Configuration

- Base URL: `<TASK_ENV_BASE_URL>`
- Auth: None
- Content-Type: `application/json`

## Collections

| Endpoint | Description |
|---|---|
| `GET /manifest` | List all available collections. |
| `GET /suppliers` | Supplier master data (id, name, risk_rating, status). |
| `GET /items` | Item/SKU master (id, description, unit_of_measure). |
| `GET /programs` | Program records (id, name, owner, budget_cap). |
| `GET /contracts` | Contract records (id, supplier_id, program_id, status, unit_price, ceiling_amount, price_type). |
| `GET /purchase_requisitions` | Requisitions (id, program_id, sku, quantity, status). |
| `GET /purchase_orders` | POs with line items (id, program_id, supplier_id, contract_id, status, lines with sku, qty, unit_price). |
| `GET /receipts` | Receipt records (id, po_id, receipt_date, lines with sku, received_qty, rejected_qty). |
| `GET /ap/invoices` | AP invoices (id, po_id, supplier_id, status, hold_code, subtotal, freight, tax, total). |
| `GET /ap/payments` | Scheduled/executed payments (id, invoice_id, supplier_id, amount, scheduled_date, status). |
| `GET /approvals` | Approval events (id, requisition_id, action, actor, event_date). |
| `GET /budget_snapshots` | Budget snapshots (id, program_id, budget_cap, committed_amount, snapshot_date). |
| `GET /vendor_risk_events` | Supplier risk events (id, supplier_id, severity, status, event_date, description). |

## Query Filters

- Exact match: `?field=value` on any top-level or nested field.
- Date range: `?start=YYYY-MM-DD&end=YYYY-MM-DD` on date collections (receipts, invoices, payments, approvals).
- ID lookup: `/<collection>/<id>` returns a single record.
- Combined: `?program_id=PRG-AX17&status=open` chains multiple filters.

## Common Record Shapes

### Purchase Order
```
{ "id": "string", "program_id": "string", "supplier_id": "string", "contract_id": "string", "status": "string", "order_date": "string", "lines": [ { "line_id": "integer", "sku": "string", "quantity": "integer", "unit_price": "number", "description": "string" } ] }
```

### Receipt
```
{ "id": "string", "po_id": "string", "receipt_date": "string", "warehouse_id": "string", "packing_slip": "string", "receiver": "string", "lines": [ { "line_id": "integer", "sku": "string", "received_qty": "integer", "rejected_qty": "integer" } ] }
```

### AP Invoice
```
{ "id": "string", "po_id": "string", "supplier_id": "string", "status": "string", "hold_code": "string|null", "subtotal": "number", "freight": "number", "tax": "number", "total": "number", "lines": [ { "line_id": "integer", "sku": "string", "quantity": "integer", "unit_price": "number" } ] }
```

### Approval
```
{ "id": "string", "requisition_id": "string", "action": "string", "actor": "string", "event_date": "string" }
```

### Vendor Risk Event
```
{ "id": "string", "supplier_id": "string", "severity": "string", "status": "string", "event_date": "string", "description": "string" }
```

### Budget Snapshot
```
{ "id": "string", "program_id": "string", "budget_cap": "number", "committed_amount": "number", "snapshot_date": "string" }
```

## Known Enum Values

### PO Status
- `open`, `closed`, `cancelled`, `partially_received`

### Invoice Status
- `paid`, `unpaid`, `held`, `void`

### Receipt Status
- `posted`, `pending`

### Contract Status
- `active`, `expired`, `cancelled`

### Risk Event Status
- `open`, `closed`, `monitoring`

### Hold Codes
- `QTY_VARIANCE`, `PRICE_MISMATCH`, `NO_RECEIPT`, `SUPPLIER_RISK`, `DAMAGE`, `PENDING_APPROVAL`, `null`

### Approval Actions
- `approved`, `pending`, `rejected`, `returned`

### Risk Severities
- `low`, `medium`, `high`, `severe`
