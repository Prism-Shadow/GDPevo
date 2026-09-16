 # ProcureOps API Schemas

 All endpoints return `{"count": N, "results": [...]}`. Use the `results` list.

 ## GET /suppliers

 | Field | Type | Description |
 |---|---|---|
 | supplier_id | string | Primary key, e.g. `SUP-LUMA` |
 | name | string | Supplier display name |
 | payment_terms | string | `NET15`, `NET30`, `NET45`, `NET60` |
 | region | string | ISO country code (`US`, `DE`, `JP`, `MX`, `SE`) |
 | risk_rating | string | `low`, `medium`, `watch`, `high` |
 | status | string | `active`, `quality_hold` |

 ## GET /items

 | Field | Type | Description |
 |---|---|---|
 | sku | string | Primary key, e.g. `LMP-228` |
 | active | boolean | Whether the item is active |
 | category | string | `electrical`, `controls`, `seals`, `hydraulics` |
 | description | string | Human-readable name |
 | preferred_supplier_id | string | FK to suppliers |
 | standard_cost | number | Baseline cost in USD |
 | uom | string | Unit of measure (`EA`, `KIT`, `BOX`) |

 ## GET /programs

 | Field | Type | Description |
 |---|---|---|
 | program_id | string | Primary key, e.g. `PRG-AX17` |
 | name | string | Display name |
 | owner | string | Person name |
 | budget_cap | number | Total program budget in USD |
 | committed_amount | number | PO subtotals consumed against budget in USD |
 | cost_center | string | Financial cost center |
 | priority | string | `low`, `medium`, `high`, `critical` |
 | region | string | Geographic region |
 | status | string | `active`, `planning` |

 Budget headroom = `budget_cap` minus `committed_amount`.

 ## GET /contracts

 | Field | Type | Description |
 |---|---|---|
 | contract_id | string | Primary key, e.g. `CR-LMP-228` |
 | sku | string | FK to items |
 | supplier_id | string | FK to suppliers |
 | program_id | string | FK to programs |
 | buyer | string | Person name |
 | unit_price | number | Contract price per unit in USD |
 | ceiling_amount | number | Maximum total spend under the contract |
 | price_type | string | `fixed`, `indexed`, `not_to_exceed` |
 | status | string | `active`, `draft`, `expired` |
 | effective_date | string | Start date (YYYY-MM-DD) |
 | expiry_date | string | End date (YYYY-MM-DD) |

 ## GET /purchase_requisitions

 | Field | Type | Description |
 |---|---|---|
 | requisition_id | string | Primary key, e.g. `REQ-AX17-141` |
 | sku | string | FK to items |
 | program_id | string | FK to programs |
 | quantity | integer | Requested quantity |
 | requester | string | Person name |
 | need_by | string | Required date (YYYY-MM-DD) |
 | priority | string | `low`, `medium`, `high`, `critical` |
 | status | string | `converted`, `approved`, `draft`, `submitted` |

 ## GET /purchase_orders

 | Field | Type | Description |
 |---|---|---|
 | po_id | string | Primary key, e.g. `PO-AX17-4481` |
 | program_id | string | FK to programs |
 | supplier_id | string | FK to suppliers |
 | requisition_id | string | FK to purchase_requisitions |
 | contract_id | string or null | FK to contracts; null when no contract |
 | buyer | string | Person name |
 | ship_to | string | Warehouse code |
 | currency | string | Always `USD` |
 | order_date | string | YYYY-MM-DD |
 | due_date | string | YYYY-MM-DD |
 | status | string | `open`, `partial_receipt`, `received`, `cancelled` |
 | subtotal | number | Sum of lines (quantity times unit_price) before tax |
 | tax | number | Tax amount in USD |
 | total | number | subtotal + tax |
 | lines | array | See below |

 **lines[] schema:**

 | Field | Type | Description |
 |---|---|---|
 | line_id | integer | 1-based index within PO |
 | sku | string | FK to items |
 | description | string | Item display name |
 | quantity | integer | Ordered quantity |
 | unit_price | number | PO unit price in USD |

 PO subtotal = sum over lines of quantity times unit_price.

 ## GET /receipts

 | Field | Type | Description |
 |---|---|---|
 | receipt_id | string | Primary key, e.g. `RCV-BLUE-14` |
 | po_id | string | FK to purchase_orders |
 | supplier_id | string | FK to suppliers |
 | warehouse_id | string | Warehouse code |
 | packing_slip | string | Supplier packing slip reference |
 | receiver | string | Person name |
 | receipt_date | string | YYYY-MM-DD |
 | status | string | `accepted`, `accepted_with_note` |
 | lines | array | See below |

 **lines[] schema:**

 | Field | Type | Description |
 |---|---|---|
 | po_line_id | integer | Maps to purchase_orders.lines[].line_id |
 | sku | string | FK to items |
 | quantity_received | integer | Units accepted into warehouse |
 | quantity_rejected | integer | Units rejected (damage, inspection) |
 | inspection_status | string | `passed` |

 Multiple receipts can exist for the same po_id. Sum receipt line quantities across all relevant receipts when reconciling.

 ## GET /ap/invoices

 | Field | Type | Description |
 |---|---|---|
 | invoice_id | string | Primary key, e.g. `AP-LUMA-7714` |
 | po_id | string | FK to purchase_orders |
 | supplier_id | string | FK to suppliers |
 | receipt_id | string or null | FK to receipts; null when unreceived |
 | currency | string | Always `USD` |
 | invoice_date | string | YYYY-MM-DD |
 | status | string | `approved`, `on_hold`, `pending_receipt` |
 | hold_code | string or null | `QTY_VARIANCE`, `PRICE_VARIANCE`, `NO_RECEIPT`, or null |
 | subtotal | number | Sum of billed lines before tax |
 | freight | number | Freight charge in USD |
 | tax | number | Tax amount in USD |
 | total | number | subtotal + freight + tax |
 | lines | array | See below |

 **lines[] schema:**

 | Field | Type | Description |
 |---|---|---|
 | po_line_id | integer | Maps to PO line |
 | sku | string | FK to items |
 | quantity_billed | integer | Quantity the supplier billed |
 | unit_price | number | Invoice unit price in USD |

 Invoice total = subtotal + freight + tax.

 ## GET /ap/payments

 | Field | Type | Description |
 |---|---|---|
 | payment_id | string | Primary key, e.g. `PAY-00001` |
 | invoice_id | string | FK to ap/invoices |
 | supplier_id | string | FK to suppliers |
 | amount | number | Payment amount in USD |
 | currency | string | Always `USD` |
 | scheduled_date | string | YYYY-MM-DD |
 | status | string | `scheduled`, `released`, `blocked` |

 Scheduled payments reduce close balance. Include payments through the relevant date range. Multiple payments may exist for one invoice.

 ## GET /approvals

 | Field | Type | Description |
 |---|---|---|
 | event_id | string | Primary key, e.g. `APR-00001` |
 | object_id | string | FK to the approved object (e.g. requisition_id) |
 | object_type | string | `requisition` |
 | action | string | `submitted`, `approved`, `returned` |
 | actor | string | Person or role name |
 | event_date | string | YYYY-MM-DD |
 | note_code | string | `EXPEDITE`, `CAPEX_CHECK`, `BUDGET_OK`, `NORMAL_REVIEW`, `MISSING_QUOTE` |

 For approval status, find the latest event (by event_date) for the target object_id. `approved` is the only good action for final approval.

 ## GET /budget_snapshots

 | Field | Type | Description |
 |---|---|---|
 | snapshot_id | string | Primary key, e.g. `BUD-PRG-AX17` |
 | program_id | string | FK to programs |
 | budget_cap | number | Budget ceiling in USD |
 | committed_amount | number | Consumed amount in USD |
 | pending_invoice_amount | number | Unpaid invoice total in USD |
 | currency | string | Always `USD` |
 | snapshot_date | string | YYYY-MM-DD |

 The snapshot_date is the as-of date for the budget picture. Choose the snapshot whose date matches the review date.

 ## GET /vendor_risk_events

 | Field | Type | Description |
 |---|---|---|
 | event_id | string | Primary key, e.g. `VRE-00001` |
 | supplier_id | string | FK to suppliers |
 | event_type | string | `bank_change`, `quality_hold`, `late_delivery`, `invoice_variance`, `duplicate_invoice_review` |
 | severity | string | `low`, `medium`, `high` |
 | status | string | `open`, `closed`, `monitoring` |
 | event_date | string | YYYY-MM-DD |
 | related_object_id | string | FK to a PO or other record |

 Open risk events: `status` is `open` as of the review date. Monitoring events: `status` is `monitoring`. A supplier has an open severe risk when severity is `high` and status is `open`. `watch` rating alone is not a blocker unless accompanied by an open high-severity event.
