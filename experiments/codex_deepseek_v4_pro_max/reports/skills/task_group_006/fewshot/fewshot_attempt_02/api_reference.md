# ProcureOps API Reference

## Base and authentication

Base URL is provided by the runner as `<TASK_ENV_BASE_URL>`. No authentication headers are required.

## Endpoints

All endpoints are read-only `GET`. Each collection supports:
- `GET /<collection>` — list all records.
- `GET /<collection>/<id>` — fetch a single record by its ID field.
- `GET /<collection>?field=value` — exact-match filter on any top-level or nested field.
- `GET /<collection>?start=YYYY-MM-DD&end=YYYY-MM-DD` — date-range filter (for collections with date fields).

### 1. `GET /manifest`
Returns metadata about the available collections and their field schemas. Call this first when the environment is unfamiliar.

### 2. `GET /suppliers`
| Field | Type | Description |
|---|---|---|
| `id` | string | Supplier ID (e.g., `SUP-NAME`). |
| `name` | string | Legal name. |
| `status` | string | `active`, `inactive`, `suspended`. |
| `risk_rating` | string | `clear`, `watch`, `severe`. |

### 3. `GET /items`
| Field | Type | Description |
|---|---|---|
| `id` | string | SKU/item ID (e.g., `SKU-CODE`). |
| `description` | string | Item description. |
| `unit_of_measure` | string | e.g., `each`. |

### 4. `GET /programs`
| Field | Type | Description |
|---|---|---|
| `id` | string | Program ID (e.g., `PRG-NAME`). |
| `name` | string | Program name. |
| `owner` | string | Program owner name. |
| `budget_cap` | number | Total budget ceiling in USD. |
| `committed_amount` | number | Committed spend to date in USD. |

### 5. `GET /contracts`
| Field | Type | Description |
|---|---|---|
| `id` | string | Contract ID (e.g., `CR-SKU-CODE`). |
| `supplier_id` | string | Linked supplier. |
| `item_id` / `sku` | string | Contracted item. |
| `status` | string | `active`, `expired`, `terminated`. |
| `price_type` | string | `fixed`, `variable`. |
| `unit_price` | number | Negotiated price per unit. |
| `ceiling_amount` | number | Contract spending cap. |

### 6. `GET /purchase_requisitions`
| Field | Type | Description |
|---|---|---|
| `id` | string | Requisition ID (e.g., `REQ-PRG-NNNN`). |
| `program_id` | string | Owning program. |
| `item_id` / `sku` | string | Requested item. |
| `supplier_id` | string | Nominated supplier. |
| `status` | string | `draft`, `submitted`, `approved`, `rejected`. |

### 7. `GET /purchase_orders`
| Field | Type | Description |
|---|---|---|
| `id` | string | PO ID (e.g., `PO-PRG-NNNN`). |
| `program_id` | string | Owning program. |
| `contract_id` | string | Governing contract (nullable). |
| `supplier_id` | string | Supplier. |
| `status` | string | `open`, `partial_receipt`, `fully_received`, `cancelled`, `closed`. |
| `lines` | array | PO line items with `line_id`, `sku`, `quantity`, `unit_price`. |

### 8. `GET /receipts`
| Field | Type | Description |
|---|---|---|
| `id` | string | Receipt ID (e.g., `RCV-WH-NN`). |
| `po_id` | string | Source PO. |
| `supplier_id` | string | Supplier. |
| `warehouse_id` | string | Receiving warehouse. |
| `receipt_date` | string | Date received (`YYYY-MM-DD`). |
| `status` | string | `accepted`, `pending_inspection`, `rejected`. |
| `lines` | array | Received line items with `po_line_id`, `sku`, `received_qty`, `rejected_qty`. |
| `packing_slip` | string | Packing slip reference. |
| `receiver` | string | Name of receiving clerk. |

### 9. `GET /ap/invoices`
| Field | Type | Description |
|---|---|---|
| `id` | string | Invoice ID (e.g., `AP-SUPPLIER-NNNN`). |
| `po_id` | string | Source PO. |
| `supplier_id` | string | Supplier. |
| `program_id` | string | Program (nullable). |
| `status` | string | `approved`, `on_hold`, `paid`, `void`. |
| `hold_code` | string or null | Reason for hold (e.g., `QTY_VARIANCE`). |
| `subtotal` | number | Line-item total. |
| `freight` | number | Freight charges. |
| `tax` | number | Tax amount. |
| `total` | number | Subtotal + freight + tax. |
| `lines` | array | Invoice line items with `sku`, `quantity_billed`, `unit_price`. |

### 10. `GET /ap/payments`
| Field | Type | Description |
|---|---|---|
| `id` | string | Payment ID. |
| `invoice_id` | string | Settled invoice. |
| `amount` | number | Payment amount. |
| `scheduled_date` | string | When payment is due or was made. |
| `status` | string | `scheduled`, `paid`. |

### 11. `GET /approvals`
| Field | Type | Description |
|---|---|---|
| `id` | string | Approval event ID (e.g., `APR-NNNNN`). |
| `requisition_id` | string | Linked requisition. |
| `action` | string | `submitted`, `approved`, `rejected`. |
| `actor` | string | Person or desk that performed the action. |
| `event_date` | string | Date of the action. |

### 12. `GET /budget_snapshots`
| Field | Type | Description |
|---|---|---|
| `id` | string | Snapshot ID. |
| `program_id` | string | Program. |
| `budget_cap` | number | Snapshot budget ceiling. |
| `committed_amount` | number | Snapshot committed spend. |
| `snapshot_date` | string | Date of snapshot. |

### 13. `GET /vendor_risk_events`
| Field | Type | Description |
|---|---|---|
| `id` | string | Event ID (e.g., `VRE-NNNNN`). |
| `supplier_id` | string | Affected supplier. |
| `severity` | string | `low`, `medium`, `high`, `critical`. |
| `status` | string | `open`, `monitoring`, `closed`, `resolved`. |
| `event_date` | string | When the event was recorded. |

## Filter syntax

- Exact match on top-level fields: `GET /purchase_orders?supplier_id=SUP-NAME`
- Exact match on nested fields: `GET /purchase_orders?lines.sku=SKU-CODE`
- Date range (collections with date fields): `GET /receipts?start=YYYY-05-01&end=YYYY-06-01`
- Multiple filters (AND semantics): `GET /ap/invoices?supplier_id=SUP-NAME&status=on_hold`

## ID format conventions

| Entity | Prefix | Example |
|---|---|---|
| Programs | `PRG-` | `PRG-NAME` |
| Suppliers | `SUP-` | `SUP-NAME` |
| Items/SKUs | varies | `SKU-CODE` |
| Contracts | `CR-` | `CR-SKU-CODE` |
| Requisitions | `REQ-` | `REQ-PRG-NNNN` |
| Purchase Orders | `PO-` | `PO-PRG-NNNN` |
| Receipts | `RCV-` | `RCV-WH-NN` |
| Invoices | `AP-` | `AP-SUPPLIER-NNNN` |
| Payments | `PMT-` | `PMT-NNNNN` |
| Approvals | `APR-` | `APR-NNNNN` |
| Vendor Risk Events | `VRE-` | `VRE-NNNNN` |
| Budget Snapshots | `BS-` | `BS-NNNNN` |
| Chargebacks | `CB-` | `CB-PRG-SKU-REASON` |
