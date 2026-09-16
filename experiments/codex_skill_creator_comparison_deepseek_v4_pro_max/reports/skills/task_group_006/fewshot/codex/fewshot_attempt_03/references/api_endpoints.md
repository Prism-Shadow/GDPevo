 # ProcureOps API Reference

 Base URL provided as `<TASK_ENV_BASE_URL>` by the task runner. All endpoints return
 JSON with a `count` (integer) and `results` (array of objects). No authentication
 required.

 ## Endpoints

 ### GET /manifest

 Returns environment metadata including anchor IDs, data file name, record counts,
 and seed. Useful for initial orientation.

 | Field | Type | Notes |
 |---|---|---|
 | `anchor_ids` | array | string |
 | `data_file` | string | |
 | `environment` | string | |
 | `generated_at` | string | ISO8601 |
 | `record_counts` | object | |
 | `seed` | integer | |

 ### GET /suppliers

 Supplier master data. 14 records.

 | Field | Type | Notes |
 |---|---|---|
 | `supplier_id` | string | Primary key, e.g. `SUP-LUMA` |
 | `name` | string | e.g. "LumaPro Industrial" |
 | `status` | string | `active`, `quality_hold`, `suspended` |
 | `risk_rating` | string | `low`, `medium`, `watch`, `high` |
 | `region` | string | `US`, `DE`, `JP`, `MX`, `SE` |
 | `payment_terms` | string | `NET15`, `NET30`, `NET45`, `NET60` |

 ### GET /items

 Item/SKU catalog. 32 records.

 | Field | Type | Notes |
 |---|---|---|
 | `sku` | string | Primary key, e.g. `LMP-228` |
 | `description` | string | |
 | `category` | string | `electrical`, `controls`, `seals`, `hydraulics` |
 | `uom` | string | `EA`, `KIT`, `BOX` |
 | `standard_cost` | number | USD |
 | `preferred_supplier_id` | string | |
 | `active` | boolean | |

 ### GET /programs

 Program master data. 10 records.

 | Field | Type | Notes |
 |---|---|---|
 | `program_id` | string | Primary key, e.g. `PRG-AX17` |
 | `name` | string | |
 | `owner` | string | |
 | `status` | string | `active`, `planning`, `closed` |
 | `priority` | string | `low`, `medium`, `high`, `critical` |
 | `budget_cap` | number | USD |
 | `committed_amount` | number | USD |
 | `cost_center` | string | |
 | `region` | string | |

 ### GET /contracts

 Contracts. 17 records.

 | Field | Type | Notes |
 |---|---|---|
 | `contract_id` | string | Primary key, e.g. `CR-LMP-228` |
 | `program_id` | string | |
 | `supplier_id` | string | |
 | `sku` | string | |
 | `buyer` | string | |
 | `status` | string | `active`, `draft`, `expired`, `cancelled` |
 | `price_type` | string | `fixed`, `indexed`, `not_to_exceed` |
 | `unit_price` | number | USD |
 | `ceiling_amount` | number | USD |
 | `effective_date` | string | YYYY-MM-DD |
 | `expiry_date` | string | YYYY-MM-DD |

 ### GET /purchase_requisitions

 Requisitions. 37 records.

 | Field | Type | Notes |
 |---|---|---|
 | `requisition_id` | string | Primary key, e.g. `REQ-AX17-141` |
 | `program_id` | string | |
 | `sku` | string | |
 | `quantity` | number | |
 | `requester` | string | |
 | `status` | string | `converted`, `approved`, `submitted`, `draft` |
 | `priority` | string | |
 | `need_by` | string | YYYY-MM-DD |

 ### GET /purchase_orders

 Purchase orders. 57 records. Each PO contains a `lines` array.

 | Field | Type | Notes |
 |---|---|---|
 | `po_id` | string | Primary key, e.g. `PO-AX17-4481` |
 | `program_id` | string | |
 | `supplier_id` | string | |
 | `contract_id` | string | nullable |
 | `requisition_id` | string | nullable |
 | `status` | string | `open`, `partial_receipt`, `received`, `cancelled` |
 | `buyer` | string | |
 | `order_date` | string | YYYY-MM-DD |
 | `due_date` | string | YYYY-MM-DD |
 | `ship_to` | string | Warehouse code |
 | `currency` | string | `USD` |
 | `subtotal` | number | |
 | `tax` | number | |
 | `total` | number | |
 | `lines` | array | See PO line schema below |

 **PO line schema:**

 | Field | Type |
 |---|---|
 | `line_id` | integer |
 | `sku` | string |
 | `description` | string |
 | `quantity` | integer |
 | `unit_price` | number, USD |

 ### GET /receipts

 Receipts. 28 records. Each contains a `lines` array.

 | Field | Type | Notes |
 |---|---|---|
 | `receipt_id` | string | Primary key, e.g. `RCV-BLUE-14` |
 | `po_id` | string | |
 | `supplier_id` | string | |
 | `warehouse_id` | string | |
 | `status` | string | `accepted`, `accepted_with_note`, `pending_inspection`, `rejected` |
 | `receiver` | string | |
 | `receipt_date` | string | YYYY-MM-DD |
 | `packing_slip` | string | |
 | `lines` | array | See receipt line schema below |

 **Receipt line schema:**

 | Field | Type |
 |---|---|
 | `po_line_id` | integer |
 | `sku` | string |
 | `quantity_received` | integer |
 | `quantity_rejected` | integer |
 | `inspection_status` | string: `passed`, `failed`, `on_hold` |

 ### GET /ap/invoices

 AP invoices. 47 records. Each can have a `lines` array.

 | Field | Type | Notes |
 |---|---|---|
 | `invoice_id` | string | Primary key, e.g. `AP-LUMA-7714` |
 | `po_id` | string | |
 | `receipt_id` | string | nullable |
 | `supplier_id` | string | |
 | `status` | string | `approved`, `on_hold`, `pending_receipt`, `void` |
 | `hold_code` | string | nullable; `QTY_VARIANCE`, `PRICE_VARIANCE`, `NO_RECEIPT`, etc. |
 | `invoice_date` | string | YYYY-MM-DD |
 | `currency` | string | `USD` |
 | `subtotal` | number | |
 | `freight` | number | |
 | `tax` | number | |
 | `total` | number | |
 | `lines` | array | See invoice line schema below |

 **Invoice line schema:**

 | Field | Type |
 |---|---|
 | `po_line_id` | integer |
 | `sku` | string |
 | `quantity_billed` | integer |
 | `unit_price` | number, USD |

 ### GET /ap/payments

 Payments. 27 records.

 | Field | Type | Notes |
 |---|---|---|
 | `payment_id` | string | Primary key, e.g. `PAY-00001` |
 | `invoice_id` | string | |
 | `supplier_id` | string | |
 | `amount` | number | USD |
 | `currency` | string | |
 | `scheduled_date` | string | YYYY-MM-DD |
 | `status` | string | `scheduled`, `released`, `blocked` |

 ### GET /approvals

 Approval events. 36 records.

 | Field | Type | Notes |
 |---|---|---|
 | `event_id` | string | Primary key, e.g. `APR-00001` |
 | `object_id` | string | Object being approved (requisition ID) |
 | `object_type` | string | `requisition` |
 | `action` | string | `submitted`, `approved`, `returned`, `rejected` |
 | `actor` | string | |
 | `event_date` | string | YYYY-MM-DD |
 | `note_code` | string | `EXPEDITE`, `CAPEX_CHECK`, `NORMAL_REVIEW`, etc. |

 ### GET /budget_snapshots

 Budget snapshots. 10 records.

 | Field | Type | Notes |
 |---|---|---|
 | `snapshot_id` | string | Primary key, e.g. `BUD-PRG-AX17` |
 | `program_id` | string | |
 | `snapshot_date` | string | YYYY-MM-DD |
 | `currency` | string | `USD` |
 | `budget_cap` | number | |
 | `committed_amount` | number | |
 | `pending_invoice_amount` | number | |

 ### GET /vendor_risk_events

 Vendor risk events. 35 records.

 | Field | Type | Notes |
 |---|---|---|
 | `event_id` | string | Primary key, e.g. `VRE-00005` |
 | `supplier_id` | string | |
 | `event_type` | string | `bank_change`, `quality_hold`, `late_delivery`, `invoice_variance`, `duplicate_invoice_review` |
 | `severity` | string | `low`, `medium`, `high` |
 | `status` | string | `open`, `monitoring`, `closed` |
 | `event_date` | string | YYYY-MM-DD |
 | `related_object_id` | string | PO ID |

 ## Cross-Reference Keys

 When joining records, use these links:

 - **Supplier**: `supplier_id` links suppliers to contracts, POs, receipts, invoices, payments, risk events
 - **Program**: `program_id` links programs to requisitions, POs, contracts, budget snapshots
 - **SKU**: `sku` links items to contracts, requisitions, PO lines, receipt lines, invoice lines
 - **PO**: `po_id` links POs to receipts, invoices
 - **Requisition**: `requisition_id` links requisitions to POs, and `object_id` in approvals
 - **Contract**: `contract_id` links contracts to POs
 - **Invoice-Payment**: `invoice_id` links invoices to payments
 - **Receipt-Invoice**: `receipt_id` on invoices points to the associated receipt

 ## API Query Pattern

 Use `curl` for all queries. Results include a `count` and `results` array.
 Filter client-side by iterating `results` and matching by join keys.

 ```bash
 curl -s <TASK_ENV_BASE_URL>/<endpoint>
 curl -s <TASK_ENV_BASE_URL>/<endpoint> | python3 -m json.tool  # for inspection
 ```
