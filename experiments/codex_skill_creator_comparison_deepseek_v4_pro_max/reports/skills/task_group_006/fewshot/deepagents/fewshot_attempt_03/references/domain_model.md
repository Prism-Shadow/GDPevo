## Entity Map

Treat every ID as joinable across endpoints. The primary entity graph:

```text
Supplier
  supplier_id

Item (SKU)
  sku, preferred_supplier_id -> Supplier

Program
  program_id, owner

Contract
  contract_id, supplier_id -> Supplier, sku -> Item, program_id -> Program

Requisition
  requisition_id, sku -> Item, program_id -> Program

Purchase Order
  po_id, supplier_id -> Supplier, program_id -> Program
  contract_id -> Contract (nullable)
  requisition_id -> Requisition
  lines[].sku -> Item

Receipt
  receipt_id, po_id -> Purchase Order, supplier_id -> Supplier
  lines[].po_line_id matches PO lines, lines[].sku -> Item

Invoice
  invoice_id, po_id -> Purchase Order, receipt_id -> Receipt (nullable)
  supplier_id -> Supplier
  lines[].po_line_id matches PO lines, lines[].sku -> Item

Payment
  payment_id, invoice_id -> Invoice, supplier_id -> Supplier

Approval Event
  event_id, object_id -> Requisition|PO|Invoice|Contract

Budget Snapshot
  snapshot_id, program_id -> Program

Vendor Risk Event
  event_id, supplier_id -> Supplier, related_object_id -> PO (typically)
```

## Key Concepts

**Three-way match:** Invoice quantity <= receipt quantity, invoice unit_price
matches PO/contract unit_price. An invoice with a matching receipt where all
three align is `approved`. Deviations trigger holds or exception codes.

**Contract ceiling:** `ceiling_amount` on a contract acts as a spending cap.
Non-cancelled PO subtotals accumulate against it. Headroom = ceiling minus sum
of non-cancelled PO subtotals. For fixed-price contracts, only the subtotal
(before tax/freight) counts against the ceiling. For indexed/not_to_exceed,
same treatment applies.

**Budget headroom:** Latest budget_snapshot for the program. Computed as
`budget_cap - committed_amount`. When a new buy is proposed, compute the
incremental total (subtotal + tax) and check against remaining headroom.
Freight is only included in budget exposure if the task explicitly provides
freight for that line.

**Tax calculation:** When computing estimated tax for a proposed buy, use
`subtotal * (tax_rate_percent / 100)`.

**Supplier risk rating vs risk events:** The `risk_rating` on the supplier
record is a static classification. Open vendor_risk_events are the dynamic
signal; filter by supplier_id with status open or monitoring. A supplier with
`risk_rating: watch` and no open events is at-risk but not blocked. An open
severe event always blocks.

**Requisition approval:** For change-control and nomination tasks, check
whether the source requisition has a final `approved` action in the approval
log. `submitted` and `returned` are not sufficient.

**Invoice status codes:**
| Status | Meaning |
|--------|---------|
| `approved` | Three-way match passed, releasable |
| `on_hold` | Has a hold_code issue (QTY_VARIANCE, PRICE_VARIANCE, etc.) |
| `pending_receipt` | No receipt exists yet for the PO |
| `paid` | Payment completed |
| `voided` | Cancelled invoice |

**Receipt status codes:**
| Status | Meaning |
|--------|---------|
| `accepted` | Clean receipt, all lines passed |
| `accepted_with_note` | Receipt accepted with variance noted |
| `pending_inspection` | Still under quality review |
| `rejected` | Units rejected |

**Payment status codes:**
| Status | Meaning |
|--------|---------|
| `scheduled` | Payment planned but not yet executed |
| `released` | Payment authorized for processing |
| `blocked` | Payment is held/stuck |
| `cleared` | Payment finalized |

**Blocker codes (nomination tasks):**
| Code | Trigger |
|------|---------|
| `missing_contract` | PO has null contract_id |
| `supplier_watch` | Supplier risk_rating is watch, no severe open events |
| `open_supplier_risk` | Supplier has open risk events (non-severe) |
| `ap_hold` | Invoice status is on_hold |
| `pending_receipt` | Invoice status is pending_receipt or no receipt exists |
| `late_due_date` | PO due_date is before as_of_date and PO not fully received |
| `none` | No blockers |

## Cross-Entity Reconciliation Patterns

**Invoice-to-receipt variance:** quantity_billed from invoice lines vs sum of
quantity_received across all receipts for that PO line.

**Invoice-to-PO variance:** invoice unit_price vs PO unit_price vs contract
unit_price. Contract price match means they all agree. A mismatch is an
exception (PRICE_MISMATCH code).

**PO completion:** Sum received quantities across all receipts for a PO line
divided by ordered quantity gives the receipt_completion_ratio.

**Chargeback netting:** When approved chargebacks exist, the net release amount
is `invoice_total - approved_chargeback_amount`. Pending chargebacks do not
reduce the release amount — the invoice stays held until resolved.

**Multiple receipts on one PO:** When a PO has more than one receipt, check
which receipt the invoice is linked to (`invoice.receipt_id`). Exclude
non-matching same-PO receipts from the reconciliation scope for that invoice,
but note them in excluded_receipt_ids. Sum only matching receipts for per-PO
billed vs received calculations.
