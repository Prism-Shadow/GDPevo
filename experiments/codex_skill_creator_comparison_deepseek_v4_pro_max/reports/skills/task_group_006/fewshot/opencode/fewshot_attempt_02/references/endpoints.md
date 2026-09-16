# ProcureOps API Endpoint Reference

Every endpoint returns a JSON object with `count` (integer) and `results` (array
of records). The base URL is provided by the task, typically as
`<TASK_ENV_BASE_URL>`. No authentication is required.

## /programs

| Field | Type | Description |
|-------|------|-------------|
| program_id | string | Primary key, e.g. "PRG-AX17" |
| name | string | Human-readable program name |
| owner | string | Responsible person |
| status | string | "active", "planning", "closed" |
| priority | string | "low", "medium", "high", "critical" |
| region | string | "North America", "EMEA", "APAC" |
| cost_center | string | e.g. "CC-410" |
| budget_cap | number | Total program budget in USD |
| committed_amount | number | Already committed spend in USD |

Note: The program records are summary-level. For a point-in-time budget check,
use `/budget_snapshots` which provides snapshot_date detail.

## /suppliers

| Field | Type | Description |
|-------|------|-------------|
| supplier_id | string | Primary key, e.g. "SUP-LUMA" |
| name | string | Supplier display name |
| status | string | "active", "quality_hold", "inactive" |
| risk_rating | string | "low", "medium", "watch", "high" |
| payment_terms | string | e.g. "NET30", "NET45" |
| region | string | "US", "DE", "JP", "MX", "SE" |

## /items

| Field | Type | Description |
|-------|------|-------------|
| sku | string | Primary key, e.g. "LMP-228" |
| description | string | Item description |
| category | string | "electrical", "controls", "seals", "hydraulics" |
| active | boolean | Whether this item is currently active |
| preferred_supplier_id | string | FK to suppliers.supplier_id |
| standard_cost | number | Standard cost in USD |
| uom | string | Unit of measure: "EA", "KIT", "BOX" |

## /contracts

| Field | Type | Description |
|-------|------|-------------|
| contract_id | string | Primary key, e.g. "CR-LMP-228" |
| sku | string | FK to items.sku |
| supplier_id | string | FK to suppliers.supplier_id |
| program_id | string | FK to programs.program_id |
| buyer | string | Contract owner |
| status | string | "active", "draft", "expired", "cancelled" |
| price_type | string | "fixed", "indexed", "not_to_exceed" |
| unit_price | number | Contract unit price in USD |
| ceiling_amount | number | Maximum spend under this contract in USD |
| effective_date | string | YYYY-MM-DD start date |
| expiry_date | string | YYYY-MM-DD end date |

## /purchase_requisitions

| Field | Type | Description |
|-------|------|-------------|
| requisition_id | string | Primary key, e.g. "REQ-AX17-141" |
| sku | string | FK to items.sku |
| program_id | string | FK to programs.program_id |
| quantity | integer | Requested quantity |
| requester | string | Person who submitted the requisition |
| need_by | string | YYYY-MM-DD delivery need date |
| priority | string | "low", "medium", "high", "critical" |
| status | string | "submitted", "approved", "converted", "rejected" |

## /purchase_orders

| Field | Type | Description |
|-------|------|-------------|
| po_id | string | Primary key, e.g. "PO-AX17-4481" |
| program_id | string | FK to programs.program_id |
| requisition_id | string | FK to purchase_requisitions.requisition_id |
| contract_id | string | FK to contracts.contract_id |
| supplier_id | string | FK to suppliers.supplier_id |
| buyer | string | PO buyer |
| status | string | "open", "partial_receipt", "fully_received", "cancelled" |
| currency | string | Always "USD" in this environment |
| ship_to | string | Warehouse code, e.g. "WH-BLUE" |
| order_date | string | YYYY-MM-DD |
| due_date | string | YYYY-MM-DD |
| subtotal | number | Sum of line (qty * unit_price) |
| tax | number | Tax amount |
| total | number | subtotal + tax |
| lines | array | PO line items |

Each PO line:

| Field | Type | Description |
|-------|------|-------------|
| line_id | integer | Line number within the PO |
| sku | string | FK to items.sku |
| description | string | Item description |
| quantity | integer | Ordered quantity |
| unit_price | number | Unit price in USD |

## /receipts

| Field | Type | Description |
|-------|------|-------------|
| receipt_id | string | Primary key, e.g. "RCV-BLUE-14" |
| po_id | string | FK to purchase_orders.po_id |
| supplier_id | string | FK to suppliers.supplier_id |
| warehouse_id | string | Receiving warehouse, e.g. "WH-BLUE" |
| receiver | string | Person who received the goods |
| receipt_date | string | YYYY-MM-DD |
| status | string | "accepted", "accepted_with_note", "rejected" |
| packing_slip | string | Packing slip identifier |
| lines | array | Receipt line items |

Each receipt line:

| Field | Type | Description |
|-------|------|-------------|
| po_line_id | integer | Matches purchase_orders.lines.line_id |
| sku | string | FK to items.sku |
| quantity_received | integer | Quantity accepted at dock |
| quantity_rejected | integer | Quantity rejected at inspection |
| inspection_status | string | "passed", "failed", "pending" |

## /ap/invoices

| Field | Type | Description |
|-------|------|-------------|
| invoice_id | string | Primary key, e.g. "AP-LUMA-7714" |
| po_id | string | FK to purchase_orders.po_id |
| receipt_id | string | FK to receipts.receipt_id (may differ from task scope) |
| supplier_id | string | FK to suppliers.supplier_id |
| status | string | "approved", "on_hold", "pending_receipt", "paid" |
| hold_code | string or null | "QTY_VARIANCE", "NO_RECEIPT", null |
| currency | string | Always "USD" |
| invoice_date | string | YYYY-MM-DD |
| subtotal | number | Sum of line (qty * unit_price) |
| freight | number | Freight charges |
| tax | number | Tax amount |
| total | number | subtotal + freight + tax |
| lines | array | Invoice line items |

Each invoice line:

| Field | Type | Description |
|-------|------|-------------|
| po_line_id | integer | Matches purchase_orders.lines.line_id |
| sku | string | FK to items.sku |
| quantity_billed | integer | Quantity on the invoice |
| unit_price | number | Unit price on the invoice |

Note: invoice.receipt_id is the receipt recorded in AP at invoice entry time.
The task scope may include additional receipts for the same PO that should be
considered in reconciliation.

## /ap/payments

| Field | Type | Description |
|-------|------|-------------|
| payment_id | string | Primary key, e.g. "PAY-00001" |
| invoice_id | string | FK to ap/invoices.invoice_id |
| supplier_id | string | FK to suppliers.supplier_id |
| amount | number | Payment amount in USD |
| currency | string | Always "USD" |
| scheduled_date | string | YYYY-MM-DD scheduled payment date |
| status | string | "scheduled", "released", "blocked", "paid" |

For AP close-desk tasks, sum scheduled amounts for each target invoice.
When the task sets a date window (e.g., "through 2026-06-30"), include only
payments with scheduled_date within that window.

## /approvals

| Field | Type | Description |
|-------|------|-------------|
| event_id | string | Primary key, e.g. "APR-00001" |
| object_id | string | FK to the object being approved (often a requisition_id) |
| object_type | string | "requisition", "purchase_order", "invoice" |
| action | string | "submitted", "approved", "rejected", "returned" |
| actor | string | Person or role who performed the action |
| event_date | string | YYYY-MM-DD |
| note_code | string | Internal note code, e.g. "EXPEDITE", "CAPEX_CHECK" |

To find approval state for a requisition, filter by object_id matching the
requisition_id. The latest event (by event_date, then by event_id for ties)
determines the current state. The task's business controls may define which
actions count as "good" (e.g., only "approved").

## /budget_snapshots

| Field | Type | Description |
|-------|------|-------------|
| snapshot_id | string | Primary key, e.g. "BUD-PRG-AX17" |
| program_id | string | FK to programs.program_id |
| snapshot_date | string | YYYY-MM-DD of the snapshot |
| budget_cap | number | Total budget cap at snapshot time |
| committed_amount | number | Committed amount at snapshot time |
| pending_invoice_amount | number | Pending but not yet committed |
| currency | string | Always "USD" |

When a task specifies an as_of_date, use the snapshot whose snapshot_date
matches (or is closest before) that date.

## /vendor_risk_events

| Field | Type | Description |
|-------|------|-------------|
| event_id | string | Primary key, e.g. "VRE-00005" |
| supplier_id | string | FK to suppliers.supplier_id |
| related_object_id | string | Associated PO ID or other object |
| event_type | string | "bank_change", "quality_hold", "late_delivery", "invoice_variance", "duplicate_invoice_review" |
| severity | string | "low", "medium", "high" |
| status | string | "open", "monitoring", "closed" |
| event_date | string | YYYY-MM-DD |

For supplier risk checks, treat "open" and "monitoring" events as active.
Treat "closed" events as resolved. A "severe" event means severity="high".

## Relationships at a glance

```
programs.program_id
  -> contracts.program_id
  -> purchase_orders.program_id
  -> purchase_requisitions.program_id
  -> budget_snapshots.program_id

suppliers.supplier_id
  -> items.preferred_supplier_id (informational only)
  -> contracts.supplier_id
  -> purchase_orders.supplier_id
  -> receipts.supplier_id
  -> ap/invoices.supplier_id
  -> ap/payments.supplier_id
  -> vendor_risk_events.supplier_id

items.sku
  -> contracts.sku
  -> purchase_requisitions.sku
  -> purchase_orders.lines[].sku
  -> receipts.lines[].sku
  -> ap/invoices.lines[].sku

contracts.contract_id
  -> purchase_orders.contract_id

purchase_requisitions.requisition_id
  -> purchase_orders.requisition_id
  -> approvals.object_id (where object_type="requisition")

purchase_orders.po_id
  -> receipts.po_id
  -> ap/invoices.po_id
  -> vendor_risk_events.related_object_id

ap/invoices.invoice_id
  -> ap/payments.invoice_id
