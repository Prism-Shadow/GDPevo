## Endpoints

Base URL is provided at runtime as `<TASK_ENV_BASE_URL>`. All endpoints return
JSON with `count` and `results`. No authentication is required.

### GET /manifest
Returns environment metadata (`record_counts`, `data_file`, `anchor_ids`). Use
`record_counts` to estimate dataset size. Do not rely on `anchor_ids` as task
scope; always pull full lists and filter by relevant IDs.

### GET /suppliers
Supplier master. Fields: `supplier_id`, `name`, `status` (active|quality_hold|
inactive), `risk_rating` (low|medium|watch|high|severe), `payment_terms`,
`region`.

### GET /items
SKU catalog. Fields: `sku`, `description`, `category`, `uom`, `standard_cost`,
`preferred_supplier_id`, `active`.

### GET /programs
Program records. Fields: `program_id`, `name`, `owner`, `status`, `priority`,
`budget_cap`, `committed_amount`, `cost_center`, `region`.

### GET /contracts
Contract records. Fields: `contract_id`, `supplier_id`, `sku`, `program_id`,
`status` (active|draft|expired|cancelled), `price_type` (fixed|indexed|
not_to_exceed), `unit_price`, `ceiling_amount`, `buyer`, `effective_date`,
`expiry_date`.

### GET /purchase_requisitions
Requisitions. Fields: `requisition_id`, `sku`, `program_id`, `quantity`,
`requester`, `status` (converted|approved|submitted|returned|draft), `priority`,
`need_by`.

### GET /purchase_orders
PO records. Fields: `po_id`, `supplier_id`, `program_id`, `contract_id`
(nullable — null means no contract), `requisition_id`, `buyer`, `status`
(open|partial_receipt|received|cancelled), `currency`, `order_date`,
`due_date`, `ship_to`, `subtotal`, `tax`, `total`, `lines[]` where each line
has `line_id`, `sku`, `description`, `quantity`, `unit_price`.

When computing contract usage, exclude cancelled POs. A null `contract_id`
signals missing-contract risk for nomination/change-control tasks.

### GET /receipts
Receiving records. Fields: `receipt_id`, `po_id`, `supplier_id`, `warehouse_id`,
`status` (accepted|accepted_with_note|pending_inspection|rejected),
`receipt_date`, `receiver`, `packing_slip`, `lines[]` where each line has
`po_line_id`, `sku`, `quantity_received`, `quantity_rejected`,
`inspection_status` (passed|failed|pending).

Multiple receipts can exist per PO. Sum received quantities across all
receipts for a PO line during reconciliation.

### GET /ap/invoices
AP invoice records. Fields: `invoice_id`, `po_id`, `receipt_id` (nullable),
`supplier_id`, `status` (approved|on_hold|pending_receipt|paid|voided),
`hold_code` (nullable string), `currency`, `invoice_date`, `subtotal`,
`freight`, `tax`, `total`, `lines[]` where each line has `po_line_id`, `sku`,
`quantity_billed`, `unit_price`.

### GET /ap/payments
Payment records. Fields: `payment_id`, `invoice_id`, `supplier_id`, `amount`,
`status` (scheduled|released|blocked|cleared), `scheduled_date`, `currency`.

For close balances, include payments with `scheduled` or `released` status
within the relevant window. `blocked` payments do not reduce balance.

### GET /approvals
Approval event log. Fields: `event_id`, `object_id`, `object_type`
(requisition|purchase_order|invoice|contract), `action` (submitted|approved|
returned|rejected), `actor`, `event_date`, `note_code`.

For requisition approval checks, find the latest event for that requisition_id;
only `approved` is considered fully approved.

### GET /budget_snapshots
Budget snapshots. Fields: `snapshot_id`, `program_id`, `snapshot_date`,
`budget_cap`, `committed_amount`, `pending_invoice_amount`, `currency`.

Use the latest snapshot for the target program. Primary headroom is
`budget_cap - committed_amount`. `pending_invoice_amount` provides context.

### GET /vendor_risk_events
Supplier risk events. Fields: `event_id`, `supplier_id`, `event_type`,
`severity` (low|medium|high|severe), `status` (open|monitoring|closed),
`event_date`, `related_object_id`.

For readiness checks, filter to open or monitoring for the target supplier.
Severe open events are hard blockers. Lower-severity open events contribute to
`supplier_watch` or `open_supplier_risk` codes. Monitoring events are contextual
unless severe.

## Lookup Patterns

| Goal | Filter |
|------|--------|
| POs for supplier+program | po_id by supplier_id or program_id |
| Receipts for a PO | receipts by po_id |
| Invoice for PO/receipt | invoices by po_id, check receipt_id |
| Payments for invoice | payments by invoice_id |
| Contract for SKU+program | contracts by sku+program_id, active only |
| Risk events for supplier | risk events by supplier_id, open+monitoring |
| Approval for requisition | approvals by object_id, type=requisition, latest |
| Budget for program | budget_snapshots by program_id, latest |
