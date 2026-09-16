# ProcureOps API Endpoints

Base URL is provided as `<TASK_ENV_BASE_URL>`. All endpoints return JSON. No authentication required.

## Endpoint Catalog

| Endpoint | Description | Key ID fields |
|---|---|---|
| `GET /manifest` | System-level metadata and seed info | — |
| `GET /suppliers` | Supplier/vendor records | `supplier_id` (`SUP-*`), `supplier_name`, `status`, `risk_rating` |
| `GET /items` | Item/SKU catalog | `sku`, `description`, `unit_price` |
| `GET /programs` | Procurement programs | `program_id` (`PRG-*`), `owner`, `budget_cap` |
| `GET /contracts` | Commercial agreements | `contract_id` (`CR-*`), `supplier_id`, `sku`, `price_type`, `unit_price`, `ceiling_amount`, `status` |
| `GET /purchase_requisitions` | Purchase requisitions | `requisition_id` (`REQ-*`), `program_id`, `sku`, `supplier_id`, `status` |
| `GET /purchase_orders` | Purchase orders | `po_id` (`PO-*`), `contract_id`, `program_id`, `supplier_id`, `status`, `lines` (array with `po_line_id`, `sku`, `qty`, `unit_price`) |
| `GET /receipts` | Warehouse receipts | `receipt_id` (`RCV-*`), `po_id`, `batch_id`, `warehouse_id`, `receipt_date`, `packing_slip`, `receiver`, `lines` (array with `po_line_id`, `sku`, `received_qty`, `rejected_qty`, `status`) |
| `GET /ap/invoices` | AP invoices | `invoice_id` (`AP-*`), `po_id`, `supplier_id`, `status`, `hold_code`, `subtotal`, `freight`, `tax`, `total`, `lines` (array with `po_line_id`, `sku`, `billed_qty`, `unit_price`) |
| `GET /ap/payments` | Scheduled/processed payments | `payment_id`, `invoice_id`, `supplier_id`, `amount`, `status`, `schedule_date` |
| `GET /approvals` | Approval workflow events | `event_id` (`APR-*`), `requisition_id`, `action`, `actor`, `event_date` |
| `GET /budget_snapshots` | Program budget snapshots | `snapshot_id` (`BUD-*`), `program_id`, `budget_cap`, `committed_amount` |
| `GET /vendor_risk_events` | Supplier risk events | `event_id` (`VRE-*`), `supplier_id`, `severity`, `status` |

## ID Prefix Conventions

| Prefix | Entity | Example |
|---|---|---|
| `PRG-` | Program | `PRG-AX17` |
| `CR-` | Contract | `CR-LMP-228` |
| `PO-` | Purchase Order | `PO-AX17-4481` |
| `REQ-` | Requisition | `REQ-AX17-141` |
| `RCV-` | Receipt | `RCV-BLUE-14` |
| `AP-` | AP Invoice | `AP-LUMA-7714` |
| `APR-` | Approval Event | `APR-00001` |
| `BUD-` | Budget Snapshot | `BUD-PRG-AX17` |
| `SUP-` | Supplier | `SUP-LUMA` |
| `VRE-` | Vendor Risk Event | `VRE-00005` |
| `CB-` | Chargeback (local) | `CB-AX17-BLUE-14-QTY` |
| `MCR-` | Modular Change Request (local) | `MCR-AX17-TL-228` |

## Cross-Entity Joins

When reconciling records across endpoints, use these natural join keys:

- **PO to Contract**: Match `po.contract_id` = `contract.contract_id`
- **PO to Program**: Match `po.program_id` = `program.program_id`
- **PO to Supplier**: Match `po.supplier_id` = `supplier.supplier_id`
- **Receipt to PO**: Match `receipt.po_id` = `po.po_id`
- **Invoice to PO**: Match `invoice.po_id` = `po.po_id`
- **Invoice to Supplier**: Match `invoice.supplier_id` = `supplier.supplier_id`
- **Payment to Invoice**: Match `payment.invoice_id` = `invoice.invoice_id`
- **Approval to Requisition**: Match `approval.requisition_id` = `requisition.requisition_id`
- **Budget to Program**: Match `budget.program_id` = `program.program_id`
- **Risk to Supplier**: Match `risk.supplier_id` = `supplier.supplier_id`
- **Item to PO/Invoice/Receipt line**: Match by `sku`

## Line-Level Data

POs, receipts, and invoices all carry a `lines` array. Each line object includes:
- `po_line_id`: integer, consistent across PO, receipt, and invoice lines
- `sku`: item identifier
- Quantity fields: `qty` (PO), `received_qty`/`rejected_qty` (receipt), `billed_qty` (invoice)
- `unit_price`: number, may differ between entities (check for price mismatches)

Match lines across entities by `po_line_id` when doing 3-way reconciliation.

## Common Status Values

**PO status**: `open`, `partial_receipt`, `fully_received`, `cancelled`

**Receipt status**: `pending`, `accepted`, `rejected`, `partial_accept`

**Invoice status**: `approved`, `on_hold`, `pending_receipt`, `paid`, `void`

**Invoice hold_code**: `QTY_VARIANCE`, `NO_RECEIPT`, `PRICE_MISMATCH`, `DAMAGE_REJECTION`, or `null`

**Contract status**: `active`, `expired`, `cancelled`

**Supplier status**: `active`, `inactive`, `suspended`

**Supplier risk_rating**: `low`, `watch`, `severe`

## Numeric Conventions

- All monetary values in USD
- Round to cents (2 decimal places)
- Percentages round to 1 decimal place
- Ratios round to 4 decimal places
- Quantities are integers unless the template says otherwise
