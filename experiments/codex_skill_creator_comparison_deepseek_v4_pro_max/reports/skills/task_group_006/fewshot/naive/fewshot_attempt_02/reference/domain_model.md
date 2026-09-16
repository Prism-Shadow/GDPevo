# ProcureOps Domain Model

## Entity Relationships

The ProcureOps domain is a procurement lifecycle with these core entities and their relationships:

```
Program (program_id)
  ├─ budget_cap, committed_amount, owner, cost_center
  └─ 1:N → PurchaseRequisition (program_id)
              ├─ sku, quantity, status, requester
              └─ 1:N → PurchaseOrder (requisition_id)
                        ├─ contract_id (nullable), supplier_id, program_id
                        ├─ lines: [{po_line_id, sku, quantity, unit_price}]
                        ├─ subtotal, tax, total, status
                        └─ 1:N → Receipt (po_id)
                                  ├─ supplier_id, warehouse_id, receipt_date
                                  ├─ lines: [{po_line_id, sku, quantity_received, quantity_rejected, inspection_status}]
                                  └─ 1:1 → APInvoice (receipt_id, nullable)
                                            ├─ po_id, supplier_id
                                            ├─ lines: [{po_line_id, sku, quantity_billed, unit_price}]
                                            ├─ subtotal, freight, tax, total, status, hold_code
                                            └─ 1:N → Payment (invoice_id)
                                                      └─ amount, scheduled_date, status

Supplier (supplier_id)
  ├─ name, risk_rating, status, payment_terms, region
  └─ 1:N → Contract (supplier_id, sku, program_id)
  │         ├─ ceiling_amount, unit_price, price_type, status
  │         └─ 1:N → PurchaseOrder (contract_id)
  └─ 1:N → VendorRiskEvent (supplier_id)
            ├─ event_type, severity, status, related_object_id, event_date

Item (sku)
  ├─ description, category, preferred_supplier_id, standard_cost, uom, active
  └─ referenced by: Requisition.sku, PO.lines[].sku, Receipt.lines[].sku, Contract.sku

Approval (event_id)
  ├─ object_id (requisition_id), object_type, action, actor, event_date, note_code

BudgetSnapshot (snapshot_id)
  ├─ program_id, budget_cap, committed_amount, pending_invoice_amount, snapshot_date
```

## Traversal Patterns

### From SKU to Full Lineage
1. Look up the item by SKU in `/items`
2. Find the preferred_supplier_id from the item
3. Find all contracts matching supplier_id + SKU in `/contracts`
4. Find all POs matching supplier_id + SKU (or contract_id if contract-linked) in `/purchase_orders`
5. Find all receipts for each PO in `/receipts`
6. Find all invoices for each PO (or receipt_id) in `/ap/invoices`
7. Find all payments for each invoice in `/ap/payments`
8. Find all risk events for the supplier in `/vendor_risk_events`

### From Program to Budget
1. Look up the program in `/programs`
2. Find the latest budget snapshot for that program_id in `/budget_snapshots` (by snapshot_date)
3. Budget headroom = budget_cap - committed_amount
4. Budget after change = budget_cap - committed_amount - requested_total

### From PO to Receipt Reconciliation
1. Look up the PO to get ordered qty and unit_price
2. Find all receipts with matching po_id
3. Sum received qty across all receipts for that PO
4. Short qty = ordered qty - total received qty
5. Receipt completion ratio = total received qty / ordered qty

### From Invoice to Three-Way Match
1. Look up the invoice to get billed qty, invoice unit_price, and po_id
2. Look up the PO to get ordered qty, PO unit_price, and contract_id
3. If contract_id exists, look up the contract to get contract unit_price
4. Look up the receipt (if receipt_id present) to get received qty
5. Compare: billed qty vs received qty (quantity match), invoice unit_price vs PO/contract unit_price (price match)

### From Supplier to Risk Context
1. Look up the supplier to get risk_rating
2. Find all vendor risk events matching supplier_id
3. Filter to open or monitoring status events for active risk
4. Filter to severe (high severity + open) for severe risk check

### From Requisition to Approval State
1. Look up the requisition for status and program context
2. Find all approval events matching object_id = requisition_id
3. The latest event (by event_date) determines current approval state
4. Check if any event has action in the "good actions" set (approved)

## Key Join Fields

| From Entity | Field | To Entity | Field |
|---|---|---|---|
| PurchaseRequisition | program_id | Program | program_id |
| PurchaseRequisition | requisition_id | Approval | object_id |
| PurchaseOrder | requisition_id | PurchaseRequisition | requisition_id |
| PurchaseOrder | program_id | Program | program_id |
| PurchaseOrder | supplier_id | Supplier | supplier_id |
| PurchaseOrder | contract_id | Contract | contract_id |
| Receipt | po_id | PurchaseOrder | po_id |
| Receipt | supplier_id | Supplier | supplier_id |
| APInvoice | po_id | PurchaseOrder | po_id |
| APInvoice | receipt_id | Receipt | receipt_id |
| APInvoice | supplier_id | Supplier | supplier_id |
| Payment | invoice_id | APInvoice | invoice_id |
| Payment | supplier_id | Supplier | supplier_id |
| Contract | supplier_id | Supplier | supplier_id |
| Contract | sku | Item | sku |
| Contract | program_id | Program | program_id |
| VendorRiskEvent | supplier_id | Supplier | supplier_id |
| BudgetSnapshot | program_id | Program | program_id |

## Date Filtering

When the task provides an as_of_date:
- POs: include regardless of date (they define the commitment)
- Receipts: include only those with receipt_date <= as_of_date
- Invoices: include only those with invoice_date <= as_of_date
- Payments: include only those with scheduled_date >= as_of_date and <= 30 days after as_of_date (or use the task-specified payment window)
- Risk events: include open or monitoring events even if dated after as_of_date (they represent active concerns); exclude closed events
- Budget snapshots: use the latest snapshot with snapshot_date <= as_of_date
- Approvals: include all events regardless of date
- Contracts: include regardless of date; filter by status if the task specifies
