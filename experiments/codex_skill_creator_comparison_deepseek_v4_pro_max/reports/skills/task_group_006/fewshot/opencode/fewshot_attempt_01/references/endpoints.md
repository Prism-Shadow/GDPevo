# ProcureOps API Endpoints

All endpoints are GET-only, return JSON arrays (except `/manifest` which returns a single object), and require no authentication. The base URL is supplied as `<TASK_ENV_BASE_URL>`.

## /manifest

Returns API metadata. Fetch first to confirm available endpoints and data version.

## /suppliers

Each supplier record includes:

- `supplier_id` (string, primary key)
- `supplier_name` (string)
- `status` (string, e.g. "active", "inactive")
- `risk_rating` (string, e.g. "watch", "preferred", "restricted", "severe")

## /items

Each item record includes:

- `sku` or `item_id` (string, primary key)
- `item_name` or `description` (string)

## /programs

Each program record includes:

- `program_id` (string, primary key)
- `program_name` (string)
- `owner` (string)
- `status` (string)

## /contracts

Each contract record includes:

- `contract_id` (string, primary key)
- `supplier_id` (string)
- `sku` or `item_id` (string)
- `status` (string, e.g. "active", "expired", "cancelled")
- `price_type` (string, e.g. "fixed", "variable")
- `unit_price` (number, USD)
- `ceiling_amount` (number, USD)

## /purchase_requisitions

Each requisition record includes:

- `requisition_id` (string, primary key)
- `program_id` (string)
- `sku` or `item_id` (string)
- `status` (string)

## /purchase_orders

Each PO record includes:

- `po_id` (string, primary key)
- `program_id` (string)
- `supplier_id` (string)
- `contract_id` (string, nullable)
- `sku` or `item_id` (string)
- `status` (string, e.g. "open", "partial_receipt", "received", "cancelled")
- `po_line_id` (integer, for multi-line POs)
- `ordered_qty` (integer)
- `unit_price` (number, USD)
- `due_date` (date string)
- `subtotal` (number, USD, computed as ordered_qty * unit_price)

A single PO may have multiple line items distinguished by `po_line_id`.

## /receipts

Each receipt record includes:

- `receipt_id` (string, primary key)
- `po_id` (string)
- `warehouse_id` (string)
- `receipt_date` (date string)
- `received_qty` (integer)
- `rejected_qty` (integer)
- `packing_slip` (string)
- `receiver` (string)
- `status` (string, e.g. "accepted", "pending", "rejected")

Receipt records may be per-PO-line or per-PO. When multiple receipts exist for one PO, sum quantities across all non-cancelled receipts.

## /ap/invoices

Each invoice record includes:

- `invoice_id` (string, primary key)
- `po_id` (string)
- `supplier_id` (string)
- `status` (string, e.g. "approved", "on_hold", "pending_receipt", "void")
- `hold_code` (string or null, e.g. "QTY_VARIANCE", "NO_RECEIPT")
- `billed_qty` (integer or number)
- `invoice_subtotal` (number, USD)
- `invoice_freight` (number, USD)
- `invoice_tax` (number, USD)
- `invoice_total` (number, USD)

One PO may have multiple invoices.

## /ap/payments

Each payment record includes:

- `payment_id` (string, primary key)
- `invoice_id` (string)
- `supplier_id` (string)
- `scheduled_amount` (number, USD)
- `payment_date` or `scheduled_date` (date string)
- `status` (string)

Payments scheduled through a given date represent committed outflows.

## /approvals

Each approval event includes:

- `event_id` (string, primary key)
- `requisition_id` (string)
- `action` (string, e.g. "submitted", "approved", "rejected")
- `actor` (string)
- `event_date` (date string)

The latest event (by date) for a given requisition determines its current approval state.

## /budget_snapshots

Each snapshot includes:

- `snapshot_id` (string, primary key)
- `program_id` (string)
- `budget_cap` (number, USD)
- `committed_amount` (number, USD)
- `as_of_date` (date string)
- `currency` (string, typically "USD")

## /vendor_risk_events

Each event includes:

- `event_id` (string, primary key, prefixed "VRE-")
- `supplier_id` (string)
- `status` (string, e.g. "open", "monitoring", "closed")
- `severity` (string, e.g. "severe", "moderate", "minor")
- `event_date` (date string)

Only open or monitoring events are relevant for risk checks. An event is "open" when `status` is "open" or "monitoring"; it is "severe" when `severity` is "severe".
