# ProcureOps API Schema Reference

This document describes the shape of every ProcureOps REST API endpoint. Use it when you need to know which fields exist on a record, their types, or how they relate to other records.

All endpoints return `{ "count": <int>, "results": [<record>, ...] }`. There is no pagination; the full dataset is returned in one response.

---

## /suppliers

Each record:

| Field | Type | Description |
|---|---|---|
| `supplier_id` | string | Primary key, e.g. `"SUP-LUMA"` |
| `name` | string | Display name, e.g. `"LumaPro Industrial"` |
| `status` | string | `"active"`, `"quality_hold"`, or other status values |
| `risk_rating` | string | `"low"`, `"medium"`, `"watch"`, or `"high"` |
| `payment_terms` | string | e.g. `"NET30"`, `"NET45"`, `"NET60"` |
| `region` | string | Two-letter code, e.g. `"US"`, `"DE"`, `"JP"` |

---

## /items

Each record:

| Field | Type | Description |
|---|---|---|
| `sku` | string | Primary key, e.g. `"LMP-228"` |
| `description` | string | Human-readable name |
| `category` | string | `"electrical"`, `"controls"`, `"seals"`, `"hydraulics"`, etc. |
| `active` | boolean | Whether the item is active |
| `preferred_supplier_id` | string | Foreign key to `/suppliers` |
| `standard_cost` | number | Standard cost in USD |
| `uom` | string | Unit of measure, e.g. `"EA"`, `"KIT"` |

---

## /programs

Each record:

| Field | Type | Description |
|---|---|---|
| `program_id` | string | Primary key, e.g. `"PRG-AX17"` |
| `name` | string | Display name |
| `owner` | string | Program owner name |
| `status` | string | `"active"` or `"planning"` |
| `priority` | string | `"low"`, `"medium"`, `"high"`, or `"critical"` |
| `budget_cap` | number | Total program budget in USD |
| `committed_amount` | number | Amount already committed in USD |
| `cost_center` | string | e.g. `"CC-410"` |
| `region` | string | `"North America"`, `"EMEA"`, `"APAC"` |

Budget headroom is `budget_cap - committed_amount`.

---

## /contracts

Each record:

| Field | Type | Description |
|---|---|---|
| `contract_id` | string | Primary key, e.g. `"CR-LMP-228"` |
| `program_id` | string | Foreign key to `/programs` |
| `supplier_id` | string | Foreign key to `/suppliers` |
| `sku` | string | Foreign key to `/items` |
| `status` | string | `"active"`, `"draft"`, or `"expired"` |
| `price_type` | string | `"fixed"`, `"indexed"`, or `"not_to_exceed"` |
| `unit_price` | number | Contract unit price in USD |
| `ceiling_amount` | number | Maximum spend under this contract in USD |
| `effective_date` | string | Start date, `YYYY-MM-DD` |
| `expiry_date` | string | End date, `YYYY-MM-DD` |
| `buyer` | string | Buyer name |

---

## /purchase_orders

Each record:

| Field | Type | Description |
|---|---|---|
| `po_id` | string | Primary key, e.g. `"PO-AX17-4481"` |
| `program_id` | string | Foreign key to `/programs` |
| `requisition_id` | string | Foreign key to `/purchase_requisitions` |
| `contract_id` | string or null | Foreign key to `/contracts`; null when no contract |
| `supplier_id` | string | Foreign key to `/suppliers` |
| `status` | string | `"open"`, `"partial_receipt"`, `"received"`, `"cancelled"`, etc. |
| `order_date` | string | `YYYY-MM-DD` |
| `due_date` | string | `YYYY-MM-DD` |
| `subtotal` | number | Sum of line `quantity * unit_price` before tax/freight |
| `tax` | number | Tax amount in USD |
| `total` | number | `subtotal + tax` (freight is on the invoice, not the PO) |
| `currency` | string | `"USD"` |
| `buyer` | string | Buyer name |
| `ship_to` | string | Warehouse code, e.g. `"WH-BLUE"` |
| `lines[]` | array | See PO lines below |

**PO lines:**

| Field | Type | Description |
|---|---|---|
| `line_id` | integer | Line number within the PO |
| `sku` | string | Item SKU |
| `description` | string | Line item description |
| `quantity` | integer | Ordered quantity |
| `unit_price` | number | Unit price in USD |

---

## /receipts

Each record:

| Field | Type | Description |
|---|---|---|
| `receipt_id` | string | Primary key, e.g. `"RCV-BLUE-14"` |
| `po_id` | string | Foreign key to `/purchase_orders` |
| `supplier_id` | string | Foreign key to `/suppliers` |
| `status` | string | `"accepted"`, `"accepted_with_note"`, etc. |
| `receipt_date` | string | `YYYY-MM-DD` |
| `packing_slip` | string | Packing slip identifier |
| `receiver` | string | Name of receiving person |
| `warehouse_id` | string | e.g. `"WH-BLUE"`, `"WH-GOLD"` |
| `lines[]` | array | See receipt lines below |

**Receipt lines:**

| Field | Type | Description |
|---|---|---|
| `po_line_id` | integer | Matches `line_id` on the corresponding PO line |
| `sku` | string | Item SKU |
| `quantity_received` | integer | Quantity accepted |
| `quantity_rejected` | integer | Quantity rejected |
| `inspection_status` | string | `"passed"` or other inspection outcomes |

---

## /ap/invoices

Each record:

| Field | Type | Description |
|---|---|---|
| `invoice_id` | string | Primary key, e.g. `"AP-LUMA-7714"` |
| `po_id` | string | Foreign key to `/purchase_orders` |
| `receipt_id` | string or null | Foreign key to `/receipts`; null when no receipt |
| `supplier_id` | string | Foreign key to `/suppliers` |
| `status` | string | `"approved"`, `"on_hold"`, `"pending_receipt"`, etc. |
| `hold_code` | string or null | `"QTY_VARIANCE"`, `"NO_RECEIPT"`, `"PRICE_VARIANCE"`, or null |
| `invoice_date` | string | `YYYY-MM-DD` |
| `subtotal` | number | Sum of line `quantity_billed * unit_price` |
| `freight` | number | Freight charge in USD |
| `tax` | number | Tax amount in USD |
| `total` | number | `subtotal + freight + tax` |
| `currency` | string | `"USD"` |
| `lines[]` | array | See invoice lines below |

**Invoice lines:**

| Field | Type | Description |
|---|---|---|
| `po_line_id` | integer | Matches `line_id` on the corresponding PO line |
| `sku` | string | Item SKU |
| `quantity_billed` | integer | Quantity the supplier billed for |
| `unit_price` | number | Unit price in USD |

---

## /ap/payments

Each record:

| Field | Type | Description |
|---|---|---|
| `payment_id` | string | Primary key, e.g. `"PAY-00001"` |
| `invoice_id` | string | Foreign key to `/ap/invoices` |
| `supplier_id` | string | Foreign key to `/suppliers` |
| `amount` | number | Payment amount in USD |
| `status` | string | `"scheduled"`, `"released"`, or `"blocked"` |
| `scheduled_date` | string | `YYYY-MM-DD` |
| `currency` | string | `"USD"` |

---

## /approvals

Each record:

| Field | Type | Description |
|---|---|---|
| `event_id` | string | Primary key, e.g. `"APR-00001"` |
| `object_type` | string | `"requisition"` or other approved object types |
| `object_id` | string | ID of the object being approved (e.g. a requisition_id) |
| `action` | string | `"submitted"`, `"approved"`, `"returned"`, etc. |
| `actor` | string | Name of the person who took the action |
| `event_date` | string | `YYYY-MM-DD` |
| `note_code` | string | `"EXPEDITE"`, `"CAPEX_CHECK"`, `"NORMAL_REVIEW"`, `"BUDGET_OK"`, etc. |

To check if a requisition is approved: find all events where `object_type` is `"requisition"` and `object_id` matches the target requisition. The latest event (by `event_date`) determines the current state. An event with `action: "approved"` means approval is complete; `action: "submitted"` or `"returned"` means it is not fully approved.

---

## /budget_snapshots

Each record:

| Field | Type | Description |
|---|---|---|
| `snapshot_id` | string | Primary key, e.g. `"BUD-PRG-AX17"` |
| `program_id` | string | Foreign key to `/programs` |
| `budget_cap` | number | Budget ceiling in USD at snapshot time |
| `committed_amount` | number | Committed spend in USD at snapshot time |
| `pending_invoice_amount` | number | Pending (unpaid) invoice amount in USD |
| `snapshot_date` | string | `YYYY-MM-DD` when the snapshot was taken |
| `currency` | string | `"USD"` |

Budget headroom at snapshot: `budget_cap - committed_amount`. Use snapshot data when the task specifies a particular snapshot_id; otherwise use the live program record.

---

## /purchase_requisitions

Each record:

| Field | Type | Description |
|---|---|---|
| `requisition_id` | string | Primary key, e.g. `"REQ-AX17-141"` |
| `program_id` | string | Foreign key to `/programs` |
| `sku` | string | Foreign key to `/items` |
| `quantity` | integer | Requested quantity |
| `status` | string | `"approved"`, `"converted"`, etc. |
| `requester` | string | Requester name |
| `need_by` | string | `YYYY-MM-DD` |
| `priority` | string | `"low"`, `"medium"`, `"high"`, `"critical"` |

---

## /vendor_risk_events

Each record:

| Field | Type | Description |
|---|---|---|
| `event_id` | string | Primary key, e.g. `"VRE-00005"` |
| `supplier_id` | string | Foreign key to `/suppliers` |
| `event_type` | string | `"bank_change"`, `"late_delivery"`, `"invoice_variance"`, `"quality_hold"`, `"duplicate_invoice_review"` |
| `severity` | string | `"low"`, `"medium"`, or `"high"` |
| `status` | string | `"open"`, `"closed"`, or `"monitoring"` |
| `related_object_id` | string | ID of a related PO or other record |
| `event_date` | string | `YYYY-MM-DD` |

Risk filtering rules:
- `"closed"` events can be ignored for current-state checks
- `"open"` and `"monitoring"` events are active
- `"high"` severity open events are blocking; `"medium"` and `"low"` are contextual
- Events with `event_date` after the task's as_of date had not occurred yet and should be excluded

---

## /manifest

| Field | Type | Description |
|---|---|---|
| `anchor_ids` | array of strings | Key record IDs present in the dataset |
| `record_counts` | object | Counts per endpoint type |
| `generated_at` | string | ISO timestamp of dataset generation |
| `seed` | integer | Dataset seed |
| `data_file` | string | Source filename |
| `environment` | string | `"ProcureOps"` |
