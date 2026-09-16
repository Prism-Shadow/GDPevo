# ProcureOps API Schema Reference

Complete field reference for every ProcureOps REST API endpoint.

All endpoints are GET with no authentication. Responses have shape
.

## /manifest

Returns record counts and anchor IDs for the environment.

| Field | Type | Description |
|-------|------|-------------|
| anchor_ids | string[] | Key IDs guaranteed present in this environment |
| data_file | string | Backing data file name |
| environment | string | Always "ProcureOps" |
| generated_at | string | ISO-8601 timestamp |
| record_counts | object | Per-endpoint record counts |
| seed | integer | Data generation seed |

## /programs

| Field | Type | Description |
|-------|------|-------------|
| program_id | string | Primary key |
| name | string | Human-readable program name |
| owner | string | Program owner name |
| status | string | active, planning, completed, on_hold |
| priority | string | critical, high, medium, low |
| budget_cap | number | Total program budget ceiling (USD) |
| committed_amount | number | Already committed spend (USD) |
| cost_center | string | Finance cost center code |
| region | string | North America, EMEA, APAC |

## /suppliers

| Field | Type | Description |
|-------|------|-------------|
| supplier_id | string | Primary key |
| name | string | Supplier business name |
| status | string | active, quality_hold, inactive |
| risk_rating | string | low, medium, watch, high |
| region | string | Supplier country/region |
| payment_terms | string | NET15, NET30, NET45, NET60 |

## /items

| Field | Type | Description |
|-------|------|-------------|
| sku | string | Primary key |
| description | string | Item description |
| category | string | electrical, controls, seals, hydraulics, mechanical, fasteners |
| uom | string | Unit of measure (EA, KIT) |
| standard_cost | number | Standard cost (USD) |
| preferred_supplier_id | string | FK to suppliers |
| active | boolean | Whether item is active |

## /contracts

| Field | Type | Description |
|-------|------|-------------|
| contract_id | string | Primary key |
| program_id | string | FK to programs |
| supplier_id | string | FK to suppliers |
| sku | string | FK to items |
| status | string | active, expired, draft, terminated, completed |
| price_type | string | fixed, indexed, not_to_exceed |
| unit_price | number | Contract unit price (USD) |
| ceiling_amount | number | Maximum contract spend (USD) |
| buyer | string | Buyer name |
| effective_date | string | Contract start (YYYY-MM-DD) |
| expiry_date | string | Contract end (YYYY-MM-DD) |

## /purchase_requisitions

| Field | Type | Description |
|-------|------|-------------|
| requisition_id | string | Primary key |
| program_id | string | FK to programs |
| sku | string | FK to items |
| quantity | integer | Requested quantity |
| requester | string | Requester name |
| status | string | approved, converted, cancelled, submitted, draft |
| priority | string | critical, high, medium, low |
| need_by | string | Required by date (YYYY-MM-DD) |

## /purchase_orders

| Field | Type | Description |
|-------|------|-------------|
| po_id | string | Primary key |
| program_id | string | FK to programs |
| supplier_id | string | FK to suppliers |
| requisition_id | string | FK to purchase_requisitions |
| contract_id | string | FK to contracts (nullable) |
| status | string | received, partial_receipt, open, cancelled |
| order_date | string | Order date (YYYY-MM-DD) |
| due_date | string | Due date (YYYY-MM-DD) |
| ship_to | string | Warehouse ID |
| currency | string | Always "USD" |
| subtotal | number | Sum of line subtotals |
| tax | number | Tax amount |
| total | number | subtotal + tax |
| buyer | string | Buyer name |
| lines | array | See PO Line below |

### PO Line

| Field | Type | Description |
|-------|------|-------------|
| line_id | integer | Line number within PO |
| sku | string | FK to items |
| description | string | Line item description |
| quantity | integer | Ordered quantity |
| unit_price | number | Unit price (USD) |

## /receipts

| Field | Type | Description |
|-------|------|-------------|
| receipt_id | string | Primary key |
| po_id | string | FK to purchase_orders |
| supplier_id | string | FK to suppliers |
| receipt_date | string | Receipt date (YYYY-MM-DD) |
| status | string | accepted, accepted_with_note, pending_inspection, rejected |
| receiver | string | Receiver name |
| warehouse_id | string | Receiving warehouse |
| packing_slip | string | Packing slip identifier |
| lines | array | See Receipt Line below |

### Receipt Line

| Field | Type | Description |
|-------|------|-------------|
| po_line_id | integer | FK to PO line |
| sku | string | FK to items |
| quantity_received | integer | Units received |
| quantity_rejected | integer | Units rejected |
| inspection_status | string | passed, failed, pending |

## /ap/invoices

| Field | Type | Description |
|-------|------|-------------|
| invoice_id | string | Primary key |
| po_id | string | FK to purchase_orders |
| supplier_id | string | FK to suppliers |
| receipt_id | string | FK to receipts (nullable) |
| status | string | approved, on_hold, pending_receipt, paid, voided |
| hold_code | string | QTY_VARIANCE, NO_RECEIPT, PRICE_MISMATCH, null |
| invoice_date | string | Invoice date (YYYY-MM-DD) |
| currency | string | Always "USD" |
| subtotal | number | Sum of line subtotals |
| freight | number | Freight charges |
| tax | number | Tax amount |
| total | number | subtotal + freight + tax |
| lines | array | See Invoice Line below |

### Invoice Line

| Field | Type | Description |
|-------|------|-------------|
| po_line_id | integer | FK to PO line |
| sku | string | FK to items |
| quantity_billed | integer | Billed quantity |
| unit_price | number | Billed unit price (USD) |

## /ap/payments

| Field | Type | Description |
|-------|------|-------------|
| payment_id | string | Primary key |
| invoice_id | string | FK to ap/invoices |
| supplier_id | string | FK to suppliers |
| amount | number | Payment amount (USD) |
| scheduled_date | string | Scheduled payment date (YYYY-MM-DD) |
| status | string | scheduled, released, paid |
| currency | string | Always "USD" |

## /approvals

| Field | Type | Description |
|-------|------|-------------|
| event_id | string | Primary key |
| object_type | string | requisition, purchase_order, invoice |
| object_id | string | FK to the approved object |
| action | string | submitted, approved, rejected, returned |
| actor | string | Person who took the action |
| event_date | string | Action date (YYYY-MM-DD) |
| note_code | string | EXPEDITE, CAPEX_CHECK, STANDARD, null |

## /budget_snapshots

| Field | Type | Description |
|-------|------|-------------|
| snapshot_id | string | Primary key |
| program_id | string | FK to programs |
| budget_cap | number | Budget ceiling at snapshot time (USD) |
| committed_amount | number | Committed spend at snapshot time (USD) |
| pending_invoice_amount | number | Invoiced but not yet paid (USD) |
| snapshot_date | string | Snapshot date (YYYY-MM-DD) |
| currency | string | Always "USD" |

## /vendor_risk_events

| Field | Type | Description |
|-------|------|-------------|
| event_id | string | Primary key |
| supplier_id | string | FK to suppliers |
| event_type | string | quality_hold, financial_restatement, bank_change, export_control, sanctions_flag |
| severity | string | low, medium, high, critical |
| status | string | open, monitoring, closed |
| event_date | string | Event date (YYYY-MM-DD) |
| related_object_id | string | FK to the affected PO or contract (nullable) |

## Cross-Reference Map

| Join Key | Source Endpoints | Target Endpoints |
|----------|-----------------|------------------|
| program_id | programs | contracts, POs, requisitions, budget_snapshots |
| supplier_id | suppliers | contracts, POs, receipts, invoices, payments, vendor_risk_events |
| po_id | purchase_orders | receipts, invoices, vendor_risk_events.related_object_id |
| sku | items | contracts, PO lines, receipt lines, invoice lines, requisitions |
| invoice_id | ap/invoices | ap/payments |
| contract_id | contracts | purchase_orders |
| requisition_id | purchase_requisitions | purchase_orders, approvals.object_id |
