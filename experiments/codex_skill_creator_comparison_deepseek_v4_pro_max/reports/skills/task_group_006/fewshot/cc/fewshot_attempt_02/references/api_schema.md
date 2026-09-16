# ProcureOps API Schema Reference

Each endpoint returns JSON with a top-level "count" and "results" array. Use
GET /<endpoint> to fetch the full collection. All fields may be present on every
record but individual records may omit optional fields or set them to null.

## /suppliers

Supplier master data.

| Field | Type | Notes |
|-------|------|-------|
| supplier_id | string | Primary key |
| name | string | Display name |
| status | enum | active, quality_hold, inactive |
| risk_rating | enum | low, medium, watch, high |
| region | string | Country code (US, DE, JP, MX, SE) |
| payment_terms | string | e.g. NET30, NET45, NET60, NET15 |

## /items

Item/SKU master data.

| Field | Type | Notes |
|-------|------|-------|
| sku | string | Primary key |
| description | string | |
| category | string | electrical, controls, seals, hydraulics, etc. |
| uom | string | Unit of measure (EA, KIT, BOX) |
| standard_cost | number | Standard cost |
| active | boolean | |
| preferred_supplier_id | string | Link to /suppliers |

## /programs

Program-level procurement context.

| Field | Type | Notes |
|-------|------|-------|
| program_id | string | Primary key |
| name | string | |
| owner | string | |
| budget_cap | number | USD |
| committed_amount | number | USD |
| cost_center | string | |
| priority | enum | low, medium, high, critical |
| region | string | |
| status | enum | active, planning, closed |

## /purchase_requisitions

Requisition headers.

| Field | Type | Notes |
|-------|------|-------|
| requisition_id | string | Primary key |
| program_id | string | Link to /programs |
| sku | string | Link to /items |
| quantity | integer | |
| priority | enum | |
| status | enum | converted, approved, draft, returned |
| requester | string | |
| need_by | string | YYYY-MM-DD |

## /purchase_orders

Purchase order headers with line arrays.

| Field | Type | Notes |
|-------|------|-------|
| po_id | string | Primary key |
| program_id | string | Link to /programs |
| supplier_id | string | Link to /suppliers |
| contract_id | string or null | Link to /contracts |
| requisition_id | string | Link to /purchase_requisitions |
| status | enum | open, partial_receipt, received, cancelled, closed |
| order_date | string | YYYY-MM-DD |
| due_date | string | YYYY-MM-DD |
| ship_to | string | Warehouse ID |
| currency | string | Always USD |
| subtotal | number | Sum of line (quantity * unit_price) |
| tax | number | |
| total | number | subtotal + tax (freight is on the invoice, not the PO) |
| buyer | string | |
| lines[] | array | |
| lines[].line_id | integer | |
| lines[].sku | string | |
| lines[].quantity | integer | |
| lines[].unit_price | number | |
| lines[].description | string | |

## /contracts

Contract headers.

| Field | Type | Notes |
|-------|------|-------|
| contract_id | string | Primary key |
| program_id | string | Link to /programs |
| supplier_id | string | Link to /suppliers |
| sku | string | Link to /items |
| status | enum | active, draft, expired |
| price_type | enum | fixed, indexed, not_to_exceed |
| unit_price | number | USD |
| ceiling_amount | number | USD |
| effective_date | string | YYYY-MM-DD |
| expiry_date | string | YYYY-MM-DD |
| buyer | string | |

## /receipts

Warehouse receipt records.

| Field | Type | Notes |
|-------|------|-------|
| receipt_id | string | Primary key |
| po_id | string | Link to /purchase_orders |
| supplier_id | string | Link to /suppliers |
| warehouse_id | string | |
| receipt_date | string | YYYY-MM-DD |
| status | enum | accepted, accepted_with_note, inspection_hold, rejected |
| receiver | string | |
| packing_slip | string | |
| lines[] | array | |
| lines[].po_line_id | integer | Matches PO lines[].line_id |
| lines[].sku | string | |
| lines[].quantity_received | integer | |
| lines[].quantity_rejected | integer | |
| lines[].inspection_status | enum | passed, failed, pending |

## /ap/invoices

Accounts payable invoice records.

| Field | Type | Notes |
|-------|------|-------|
| invoice_id | string | Primary key |
| po_id | string | Link to /purchase_orders |
| receipt_id | string or null | Link to /receipts |
| supplier_id | string | Link to /suppliers |
| status | enum | approved, on_hold, pending_receipt, paid, voided |
| hold_code | string or null | e.g. QTY_VARIANCE, NO_RECEIPT, PRICE_VARIANCE, null |
| invoice_date | string | YYYY-MM-DD |
| currency | string | Always USD |
| subtotal | number | |
| freight | number | |
| tax | number | |
| total | number | subtotal + freight + tax |
| lines[] | array | |
| lines[].po_line_id | integer | |
| lines[].sku | string | |
| lines[].quantity_billed | integer | |
| lines[].unit_price | number | |

## /ap/payments

Scheduled and released payments.

| Field | Type | Notes |
|-------|------|-------|
| payment_id | string | Primary key |
| invoice_id | string | Link to /ap/invoices |
| supplier_id | string | Link to /suppliers |
| amount | number | USD |
| scheduled_date | string | YYYY-MM-DD |
| status | enum | scheduled, released, blocked |
| currency | string | Always USD |

## /approvals

Approval event log for requisitions (and other objects).

| Field | Type | Notes |
|-------|------|-------|
| event_id | string | Primary key |
| object_id | string | The requisition or object approved |
| object_type | string | e.g. requisition |
| action | enum | submitted, approved, returned, rejected |
| actor | string | |
| event_date | string | YYYY-MM-DD |
| note_code | string | e.g. EXPEDITE, CAPEX_CHECK, NORMAL_REVIEW |

## /budget_snapshots

Point-in-time budget state per program.

| Field | Type | Notes |
|-------|------|-------|
| snapshot_id | string | Primary key |
| program_id | string | Link to /programs |
| snapshot_date | string | YYYY-MM-DD |
| budget_cap | number | USD |
| committed_amount | number | USD |
| pending_invoice_amount | number | USD |
| currency | string | Always USD |

## /vendor_risk_events

Supplier risk incident log.

| Field | Type | Notes |
|-------|------|-------|
| event_id | string | Primary key; format VRE-NNNNN |
| supplier_id | string | Link to /suppliers |
| event_type | string | e.g. invoice_variance, bank_change, quality_hold, late_delivery, duplicate_invoice_review |
| severity | enum | low, medium, high, critical |
| status | enum | open, monitoring, closed |
| event_date | string | YYYY-MM-DD |
| related_object_id | string | Typically a PO ID |

## Common patterns

- All ID fields are strings, even numeric-looking ones like line_id.
- Monetary values are in USD and the API returns them to 2 decimal places.
- Dates use YYYY-MM-DD format.
- Null contract_id on a PO means no contract backs the order.
- Null receipt_id on an invoice means no receipt has been posted.
- A single PO can have multiple receipts (partial deliveries).
- A single PO can have multiple invoices (e.g. separate invoices for separate receipts).
