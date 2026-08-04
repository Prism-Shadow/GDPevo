## ProcureOps API endpoint reference

All endpoints are read-only GET operations under the base URL supplied by the runner as `<TASK_ENV_BASE_URL>`. No authentication is required.

### Collections

| Endpoint | Description |
|---|---|
| `/manifest` | API manifest — lists available collections and their schemas |
| `/suppliers` | Supplier master data (ID, name, status, risk_rating) |
| `/items` | Item / SKU catalog (SKU, description, unit_of_measure) |
| `/programs` | Program master data (ID, name, owner, budget) |
| `/contracts` | Contract records (ID, supplier_id, program_id, status, price_type, unit_price, ceiling_amount) |
| `/purchase_requisitions` | Purchase requisitions (ID, program_id, supplier_id, sku, quantity, status) |
| `/purchase_orders` | Purchase orders (ID, program_id, supplier_id, contract_id, requisition_id, status, lines with sku/quantity/unit_price) |
| `/receipts` | Receiving records (ID, po_id, receipt_date, warehouse, status, lines with sku/quantity_received/quantity_rejected) |
| `/ap/invoices` | AP invoices (ID, po_id, supplier_id, status, hold_code, lines with sku/quantity/unit_price, freight, tax) |
| `/ap/payments` | Scheduled or completed payments (ID, invoice_id, supplier_id, amount, scheduled_date) |
| `/approvals` | Approval events (ID, requisition_id, action, actor, event_date) |
| `/budget_snapshots` | Budget snapshots (ID, program_id, budget_cap, committed_amount, snapshot_date) |
| `/vendor_risk_events` | Vendor risk events (ID, supplier_id, severity, status, description) |

### Query patterns

**Fetch by ID**:
```
GET /purchase_orders/PO-AX17-4481
GET /ap/invoices/AP-LUMA-7714
GET /contracts/CR-LMP-228
```

**Exact-match filter** (any top-level or nested field):
```
GET /purchase_orders?program_id=PRG-AX17
GET /ap/invoices?supplier_id=SUP-LUMA
GET /vendor_risk_events?supplier_id=SUP-LUMA&status=open
GET /receipts?po_id=PO-AX17-4481
```

**Date range** (date-indexed collections only):
```
GET /ap/payments?start=2026-01-01&end=2026-06-30
GET /receipts?start=2026-06-01&end=2026-06-02
```

### Response shapes

Responses are JSON arrays of records. Each record has an `id` field and collection-specific fields. Nested objects (e.g., PO lines inside a purchase order, invoice lines inside an invoice) are included inline. Consult the live manifest for the exact schema of each collection.

### Operational notes

- All date fields use `YYYY-MM-DD` format.
- All monetary fields are in USD and should be treated as numbers (not strings).
- Status fields vary by collection: consult the manifest for allowed values.
- Receipt and invoice line quantities may be fractional; round to 2 decimal places when computing variances.
- Cancelled POs are excluded from contract ceiling calculations unless the task explicitly includes them.
- Payments with a `scheduled_date` through the task cutoff date reduce the close balance; future-dated payments do not.
