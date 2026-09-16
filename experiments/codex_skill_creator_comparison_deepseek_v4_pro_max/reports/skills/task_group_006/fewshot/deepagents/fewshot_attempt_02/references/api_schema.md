# ProcureOps API Full Record Schema

All endpoints return `{"count": <int>, "results": [<records>]}`. Every GET is unauthenticated.

## /suppliers

| Field | Type | Description |
|---|---|---|
| `supplier_id` | string | Primary key, e.g. `SUP-LUMA` |
| `name` | string | Display name |
| `status` | string | `active`, `quality_hold`, `suspended` |
| `risk_rating` | string | `low`, `medium`, `watch`, `high` |
| `payment_terms` | string | e.g. `NET30`, `NET45`, `NET60`, `NET15` |
| `region` | string | e.g. `US`, `DE`, `JP`, `MX`, `SE` |

## /items

| Field | Type | Description |
|---|---|---|
| `sku` | string | Item stock keeping unit |
| `description` | string | Human-readable description |
| `active` | boolean | Whether the item is active |
| `category` | string | `electrical`, `controls`, `seals`, `hydraulics`, `fasteners`, `packaging` |
| `preferred_supplier_id` | string | Links to `/suppliers` |
| `standard_cost` | number | Standard unit cost in USD |
| `uom` | string | Unit of measure: `EA`, `KIT`, `BOX`, `M` |

## /programs

| Field | Type | Description |
|---|---|---|
| `program_id` | string | Primary key, e.g. `PRG-AX17` |
| `name` | string | Display name |
| `owner` | string | Program owner name |
| `budget_cap` | number | Total budget ceiling in USD |
| `committed_amount` | number | Currently committed spend in USD |
| `cost_center` | string | e.g. `CC-410` |
| `priority` | string | `critical`, `high`, `medium`, `low` |
| `region` | string | e.g. `North America`, `EMEA`, `APAC` |
| `status` | string | `active`, `planning`, `closed` |

## /contracts

| Field | Type | Description |
|---|---|---|
| `contract_id` | string | Primary key |
| `supplier_id` | string | Links to `/suppliers` |
| `program_id` | string | Links to `/programs` |
| `sku` | string | Links to `/items` |
| `unit_price` | number | Contract unit price in USD |
| `ceiling_amount` | number | Total contract ceiling in USD |
| `price_type` | string | `fixed`, `indexed`, `not_to_exceed` |
| `status` | string | `active`, `expired`, `cancelled` |
| `buyer` | string | Buyer name |
| `effective_date` | string | `YYYY-MM-DD` |
| `expiry_date` | string | `YYYY-MM-DD` |

## /purchase_requisitions

| Field | Type | Description |
|---|---|---|
| `requisition_id` | string | Primary key |
| `program_id` | string | Links to `/programs` |
| `sku` | string | Links to `/items` |
| `quantity` | number | Requested quantity |
| `status` | string | `approved`, `converted`, `submitted`, `returned`, `draft` |
| `requester` | string | Person who raised the requisition |
| `need_by` | string | `YYYY-MM-DD` required date |
| `priority` | string | `critical`, `high`, `medium`, `low` |

## /purchase_orders

| Field | Type | Description |
|---|---|---|
| `po_id` | string | Primary key |
| `requisition_id` | string | Links to `/purchase_requisitions` (may be null) |
| `program_id` | string | Links to `/programs` |
| `supplier_id` | string | Links to `/suppliers` |
| `contract_id` | string or null | Links to `/contracts` |
| `lines[]` | array | Line items (see below) |
| `status` | string | `open`, `partial_receipt`, `received`, `cancelled` |
| `subtotal` | number | Sum of line extensions in USD |
| `tax` | number | Tax amount in USD |
| `total` | number | subtotal + tax in USD |
| `currency` | string | Always `USD` |
| `order_date` | string | `YYYY-MM-DD` |
| `due_date` | string | `YYYY-MM-DD` |
| `buyer` | string | Buyer name |
| `ship_to` | string | Warehouse code |

### PO Line Object

| Field | Type | Description |
|---|---|---|
| `line_id` | integer | Line number within the PO |
| `sku` | string | Item SKU |
| `description` | string | Line description |
| `quantity` | number | Ordered quantity |
| `unit_price` | number | Line unit price in USD |

## /receipts

| Field | Type | Description |
|---|---|---|
| `receipt_id` | string | Primary key |
| `po_id` | string | Links to `/purchase_orders` |
| `supplier_id` | string | Links to `/suppliers` |
| `lines[]` | array | Receipt line items (see below) |
| `status` | string | `accepted`, `accepted_with_note`, `pending_inspection` |
| `receipt_date` | string | `YYYY-MM-DD` |
| `warehouse_id` | string | Receiving warehouse |
| `receiver` | string | Receiver name |
| `packing_slip` | string | Packing slip number (may be null) |

### Receipt Line Object

| Field | Type | Description |
|---|---|---|
| `po_line_id` | integer | Matches PO line_id |
| `sku` | string | Item SKU |
| `quantity_received` | number | Quantity accepted |
| `quantity_rejected` | number | Quantity rejected |
| `inspection_status` | string | `passed`, `failed`, `pending` |

## /ap/invoices

| Field | Type | Description |
|---|---|---|
| `invoice_id` | string | Primary key |
| `po_id` | string | Links to `/purchase_orders` |
| `supplier_id` | string | Links to `/suppliers` |
| `receipt_id` | string or null | Links to `/receipts` |
| `lines[]` | array | Invoice line items (see below) |
| `status` | string | `approved`, `on_hold`, `pending_receipt`, `voided` |
| `hold_code` | string or null | `QTY_VARIANCE`, `NO_RECEIPT`, `PRICE_VARIANCE`, `DAMAGE_HOLD`, `INCOMPLETE_DOCS` |
| `subtotal` | number | Line subtotal in USD |
| `freight` | number | Freight charge in USD |
| `tax` | number | Tax amount in USD |
| `total` | number | subtotal + freight + tax in USD |
| `currency` | string | Always `USD` |
| `invoice_date` | string | `YYYY-MM-DD` |

### Invoice Line Object

| Field | Type | Description |
|---|---|---|
| `po_line_id` | integer | Matches PO line_id |
| `sku` | string | Item SKU |
| `quantity_billed` | number | Billed quantity |
| `unit_price` | number | Billed unit price in USD |

## /ap/payments

| Field | Type | Description |
|---|---|---|
| `payment_id` | string | Primary key |
| `invoice_id` | string | Links to `/ap/invoices` |
| `supplier_id` | string | Links to `/suppliers` |
| `amount` | number | Payment amount in USD |
| `scheduled_date` | string | `YYYY-MM-DD` |
| `status` | string | `scheduled`, `released`, `blocked`, `paid` |
| `currency` | string | Always `USD` |

## /approvals

| Field | Type | Description |
|---|---|---|
| `event_id` | string | Primary key |
| `object_id` | string | The record being approved (requisition_id when object_type is `requisition`) |
| `object_type` | string | `requisition` (primary type used) |
| `action` | string | `submitted`, `approved`, `returned`, `rejected` |
| `actor` | string | Approver name |
| `event_date` | string | `YYYY-MM-DD` |
| `note_code` | string | e.g. `EXPEDITE`, `CAPEX_CHECK`, `NORMAL_REVIEW`, `MISSING_QUOTE`, `BUDGET_OK` |

## /budget_snapshots

| Field | Type | Description |
|---|---|---|
| `snapshot_id` | string | Primary key |
| `program_id` | string | Links to `/programs` |
| `budget_cap` | number | Budget ceiling at snapshot in USD |
| `committed_amount` | number | Committed spend at snapshot in USD |
| `pending_invoice_amount` | number | Pending invoice total at snapshot in USD |
| `snapshot_date` | string | `YYYY-MM-DD` |
| `currency` | string | Always `USD` |

## /vendor_risk_events

| Field | Type | Description |
|---|---|---|
| `event_id` | string | Primary key, e.g. `VRE-00005` |
| `supplier_id` | string | Links to `/suppliers` |
| `event_type` | string | `bank_change`, `quality_hold`, `late_delivery`, `invoice_variance`, `duplicate_invoice_review` |
| `severity` | string | `low`, `medium`, `high`, `critical` |
| `status` | string | `open`, `monitoring`, `closed` |
| `event_date` | string | `YYYY-MM-DD` |
| `related_object_id` | string | PO or other record tied to the event |
