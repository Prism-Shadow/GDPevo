# API Record Schemas

Each endpoint returns `{"count": N, "results": [...]}`. The schemas below document the shape of each object in the results array. Fields marked `?` are nullable and may be absent or null.

## GET /suppliers

| Field | Type | Description |
|---|---|---|
| supplier_id | string | Primary key |
| name | string | Supplier display name |
| status | string | active, inactive, suspended, or blocked |
| risk_rating | string | low, medium, watch, or high |
| payment_terms | string | e.g., NET30, NET45, NET60 |
| region | string | Two-letter region code |

## GET /items

| Field | Type | Description |
|---|---|---|
| sku | string | Primary key; stock keeping unit |
| description | string | Human-readable description |
| category | string | electrical, controls, seals, hydraulics, etc. |
| preferred_supplier_id | string | Default supplier for this item |
| standard_cost | number | Standard cost in USD |
| uom | string | Unit of measure (EA, KIT, etc.) |
| active | boolean | Whether the item is active |

## GET /programs

| Field | Type | Description |
|---|---|---|
| program_id | string | Primary key |
| name | string | Program display name |
| status | string | active, planning, closed |
| priority | string | critical, high, medium, low |
| owner | string | Program owner name |
| cost_center | string | Charge code |
| budget_cap | number | Total budget ceiling in USD |
| committed_amount | number | Amount already committed in USD |
| region | string | Region code |

## GET /purchase_requisitions

| Field | Type | Description |
|---|---|---|
| requisition_id | string | Primary key |
| program_id | string | FK to programs |
| sku | string | Requested item SKU |
| quantity | number | Requested quantity |
| need_by | string | Date needed (YYYY-MM-DD) |
| priority | string | critical, high, medium, low |
| requester | string | Person who raised the requisition |
| status | string | draft, submitted, approved, converted |

## GET /contracts

| Field | Type | Description |
|---|---|---|
| contract_id | string | Primary key |
| program_id | string | FK to programs |
| supplier_id | string | FK to suppliers |
| sku | string | Contracted item SKU |
| status | string | active, draft, expired, terminated |
| price_type | string | fixed, indexed, not_to_exceed |
| unit_price | number | Contract unit price in USD |
| ceiling_amount | number | Maximum spend under this contract in USD |
| effective_date | string | Start date (YYYY-MM-DD) |
| expiry_date | string | End date (YYYY-MM-DD) |
| buyer | string | Buyer responsible for the contract |

## GET /purchase_orders

| Field | Type | Description |
|---|---|---|
| po_id | string | Primary key |
| program_id | string | FK to programs |
| supplier_id | string | FK to suppliers |
| contract_id | string? | FK to contracts; null if spot buy |
| requisition_id | string | FK to purchase_requisitions |
| status | string | open, confirmed, partial_receipt, received, closed, cancelled |
| order_date | string | Date order placed (YYYY-MM-DD) |
| due_date | string | Expected delivery date (YYYY-MM-DD) |
| buyer | string | Buyer name |
| ship_to | string | Warehouse destination code |
| currency | string | Always USD |
| subtotal | number | Sum of (quantity * unit_price) across lines |
| tax | number | Tax amount in USD |
| total | number | subtotal + tax |
| lines | array | Array of line objects (see below) |

### PO Line Object

| Field | Type | Description |
|---|---|---|
| line_id | integer | Line number within the PO |
| sku | string | Item SKU |
| description | string | Line item description |
| quantity | integer | Ordered quantity |
| unit_price | number | Unit price in USD |

## GET /receipts

| Field | Type | Description |
|---|---|---|
| receipt_id | string | Primary key |
| po_id | string | FK to purchase_orders |
| supplier_id | string | FK to suppliers |
| warehouse_id | string | Receiving warehouse code |
| receipt_date | string | Date goods received (YYYY-MM-DD) |
| packing_slip | string | Packing slip reference |
| receiver | string | Person who received the goods |
| status | string | accepted, accepted_with_note, inspection_hold, rejected |
| lines | array | Array of receipt line objects (see below) |

### Receipt Line Object

| Field | Type | Description |
|---|---|---|
| po_line_id | integer | Matches PO line_id |
| sku | string | Item SKU |
| quantity_received | integer | Quantity accepted into inventory |
| quantity_rejected | integer | Quantity rejected (damaged, wrong item, etc.) |
| inspection_status | string | passed, failed, pending |

## GET /ap/invoices

| Field | Type | Description |
|---|---|---|
| invoice_id | string | Primary key |
| po_id | string | FK to purchase_orders |
| supplier_id | string | FK to suppliers |
| receipt_id | string? | FK to receipts; null if no receipt matched |
| status | string | approved, on_hold, pending_receipt, void |
| hold_code | string? | Reason code when status is on_hold; null otherwise |
| invoice_date | string | Invoice date (YYYY-MM-DD) |
| currency | string | Always USD |
| subtotal | number | Sum of (quantity_billed * unit_price) across lines |
| freight | number | Freight charges in USD |
| tax | number | Tax amount in USD |
| total | number | subtotal + freight + tax |
| lines | array | Array of invoice line objects (see below) |

### Invoice Line Object

| Field | Type | Description |
|---|---|---|
| po_line_id | integer | Matches PO line_id |
| sku | string | Item SKU |
| quantity_billed | integer | Quantity the supplier is billing for |
| unit_price | number | Unit price as billed by supplier |

## GET /ap/payments

| Field | Type | Description |
|---|---|---|
| payment_id | string | Primary key |
| invoice_id | string | FK to ap/invoices |
| supplier_id | string | FK to suppliers |
| amount | number | Payment amount in USD |
| scheduled_date | string | Date payment will be made (YYYY-MM-DD) |
| status | string | scheduled, released, paid |
| currency | string | Always USD |

## GET /approvals

| Field | Type | Description |
|---|---|---|
| event_id | string | Primary key |
| object_id | string | The requisition_id or other object being approved |
| object_type | string | requisition, purchase_order, etc. |
| action | string | submitted, approved, rejected, returned |
| actor | string | Person or role performing the action |
| event_date | string | Date of the approval action (YYYY-MM-DD) |
| note_code | string | EXPEDITE, CAPEX_CHECK, NORMAL_REVIEW, etc. |

## GET /budget_snapshots

| Field | Type | Description |
|---|---|---|
| snapshot_id | string | Primary key |
| program_id | string | FK to programs |
| snapshot_date | string | Date of snapshot (YYYY-MM-DD) |
| budget_cap | number | Budget ceiling at snapshot time |
| committed_amount | number | Committed spend at snapshot time |
| pending_invoice_amount | number | Invoiced but not yet paid at snapshot time |
| currency | string | Always USD |

## GET /vendor_risk_events

| Field | Type | Description |
|---|---|---|
| event_id | string | Primary key; format VRE-XXXXX |
| supplier_id | string | FK to suppliers |
| event_type | string | bank_change, quality_hold, late_delivery, invoice_variance, duplicate_invoice_review |
| severity | string | low, medium, high |
| status | string | open, monitoring, closed |
| related_object_id | string | PO or other entity the event relates to |
| event_date | string | Date of event (YYYY-MM-DD) |
