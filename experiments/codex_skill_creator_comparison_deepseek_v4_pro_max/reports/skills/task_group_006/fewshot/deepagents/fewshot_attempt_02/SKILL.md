---
name: procurops-agent
description: "Complete procurement-operations analysis agent for the ProcureOps REST API. Queries suppliers, items, programs, contracts, purchase requisitions, purchase orders, receipts, AP invoices, AP payments, approvals, budget snapshots, and vendor risk events from a shared task-environment API, then cross-references records by foreign key to produce structured JSON answers for sourcing nomination readiness, receiving closeouts, AP close reconciliation, change-control decisions, and AP release/hold files. Use when the task provides a local memo or packet naming target program/supplier/PO/receipt/invoice IDs and expects a ProcureOps-backed JSON answer that follows an answer template."
license: MIT
compatibility: designed for deepagents-code
---

# ProcureOps Agent

## Overview

This skill covers five core ProcureOps workflows — nomination readiness, receiving closeout, AP close reconciliation, change-control decisions, and AP release files — all of which follow the same basic pattern: read a local memo or packet, fetch ProcureOps API records, cross-reference them by foreign key, compute financials, and populate a structured JSON template.

## The General Pattern

Every ProcureOps task follows these steps:

1. **Read local payloads** — Open every file the task provides under `input/payloads/`. At least one file names target IDs (programs, POs, receipts, invoices); at least one is a JSON template describing the required output shape.
2. **Fetch API records** — Call the ProcureOps endpoints listed below. Retrieve everything the template references: programs, suppliers, items, contracts, POs, requisitions, receipts, invoices, payments, approval events, budget snapshots, and vendor risk events.
3. **Cross-reference by foreign key** — Trace relationships across records. Common paths include:
   - Program → Contracts, POs, Budget snapshots, Requisitions
   - Supplier → Contracts, POs, Invoices, Risk events
   - SKU → Items, Contracts, POs, Requisitions
   - Contract → POs (sum noncancelled subtotals for ceiling headroom)
   - PO → Receipts (sum received per line), Invoices (match by po_id)
   - Requisition → Approval events (latest event per requisition)
   - Invoice → Payments (scheduled amounts reduce close balance)
   - Receipt → Invoices (matched by PO + receipt_id)
4. **Compute financials** — See [computation_rules.md](references/computation_rules.md) for the full calculation catalogue. Every USD amount is rounded to 2 decimal places.
5. **Fill the template** — Match the output to the answer template. Respect template ordering rules: lists are sets unless the template specifies sorting; sort ID lists ascending; use the exact enum values and key names the template defines.

## API Endpoints

All endpoints are unauthenticated GET requests against `<TASK_ENV_BASE_URL>`. Each returns `{"count": N, "results": [...]}`.

| Endpoint | Key fields | Primary use |
|---|---|---|
| `/manifest` | anchor_ids, record_counts | Confirms environment identity; do not use for answer data |
| `/suppliers` | supplier_id, name, status, risk_rating, payment_terms, region | Supplier identity, risk context |
| `/items` | sku, description, active, category, preferred_supplier_id, standard_cost | Item identity, preferred supplier |
| `/programs` | program_id, name, owner, budget_cap, committed_amount, status, priority | Program context, budget |
| `/contracts` | contract_id, supplier_id, program_id, sku, unit_price, ceiling_amount, price_type, status | Contract commercial basis |
| `/purchase_requisitions` | requisition_id, program_id, sku, quantity, status, requester, need_by | Sourcing origin, approval source |
| `/purchase_orders` | po_id, requisition_id, program_id, supplier_id, contract_id, lines[], status, subtotal, tax, total, due_date | Order detail, line-level qty/price |
| `/receipts` | receipt_id, po_id, supplier_id, lines[], status, receipt_date, warehouse_id, receiver, packing_slip | Receiving evidence |
| `/ap/invoices` | invoice_id, po_id, supplier_id, receipt_id, lines[], status, hold_code, subtotal, freight, tax, total | Billing records, AP holds |
| `/ap/payments` | payment_id, invoice_id, supplier_id, amount, scheduled_date, status | Scheduled/released payments |
| `/approvals` | event_id, object_id, object_type, action, actor, event_date, note_code | Approval workflow state |
| `/budget_snapshots` | snapshot_id, program_id, budget_cap, committed_amount, pending_invoice_amount | Budget state at snapshot |
| `/vendor_risk_events` | event_id, supplier_id, event_type, severity, status, event_date, related_object_id | Supplier risk context |

For the full record schema of every endpoint, see [api_schema.md](references/api_schema.md).

## Foreign-Key Reference Table

| From field | Links to | On endpoint |
|---|---|---|
| `supplier_id` | `supplier_id` | suppliers, contracts, purchase_orders, receipts, ap/invoices, ap/payments, vendor_risk_events |
| `program_id` | `program_id` | programs, contracts, purchase_orders, purchase_requisitions, budget_snapshots |
| `contract_id` | `contract_id` | contracts, purchase_orders |
| `requisition_id` | `requisition_id` | purchase_requisitions, purchase_orders |
| `po_id` | `po_id` | purchase_orders, receipts, ap/invoices |
| `receipt_id` | `receipt_id` | receipts, ap/invoices |
| `invoice_id` | `invoice_id` | ap/invoices, ap/payments |
| `sku` | `sku` | items, contracts, purchase_orders (lines), receipts (lines), ap/invoices (lines), purchase_requisitions |
| `object_id` | `requisition_id` | approvals (when object_type is "requisition") |
| `event_id` | — | approvals, vendor_risk_events (self-contained) |

## Common Workflow Details

### Sourcing Nomination Readiness

Identify target SKUs from the memo. For each SKU:
- Find the item and its preferred supplier.
- Find requisitions, POs, and contracts for that program-SKU combination.
- Check receipt evidence: receipts against target POs as of the as-of date.
- Check invoice exceptions: invoices linked to target POs as of the as-of date.
- Check supplier risk: open or monitoring risk events for the selected supplier as of the as-of date.
- Determine blockers: missing contract, supplier watch rating, open supplier risk events, AP holds (invoice status `on_hold` or `pending_receipt`), pending receipts, and late due dates (PO due_date before as_of_date).
- Compute budget headroom: `budget_cap - committed_amount` from the program's budget snapshot.

### Receiving Closeout

Target a single batch receipt. Pull the receipt, its PO, contract, supplier, invoices, and risk events. Compare line-level:
- `ordered_qty` vs `received_qty` → `short_qty_vs_po`, `receipt_completion_ratio`
- `received_qty` vs `billed_qty` → `unreceived_billed_qty`
- Unit prices against the contract → `contract_price_match`
- Invoice status and hold code → see [computation_rules.md](references/computation_rules.md) for the full exception code catalogue

### AP Close Reconciliation

Iterate the target invoices only. For each:
- Determine whether a receipt exists (quantity_received = 0 if no receipt).
- Match payments: sum scheduled or released payments for the invoice through the close horizon.
- Compute `net_balance_impact = invoice_total - scheduled_payment_amount`.
- Decide hold/release: `RELEASE` when three-way match passes and payment is scheduled; `HOLD` when quantity variance, no receipt, or invoice on hold.
- Build supplier-level balances: `opening_balance + invoice_total - scheduled_payments = close_balance`.

### Change-Control Decision

Validate contract, budget, approvals, and supplier risk. For contract: sum noncancelled PO subtotals, compute headroom before and after the change request. For budget: use the latest budget snapshot, compute remaining budget, check after-change budget. For approvals: find the latest approval event for the source requisition; "approved" is the only passing action. For supplier risk: open severe events block; watch rating alone does not block.

### AP Release File

Combine ProcureOps records with a local chargeback register. For each invoice:
- Match receipts in scope and identify excluded same-PO receipts.
- Compute chargeback amounts: `chargeback_basis_quantity * unit_cost`.
- Apply the chargeback status: approved chargebacks reduce net release; pending chargebacks hold the invoice.
- No receipt on a PO → `hold_missing_receipt`.

## Template Filling Rules

- **Lists as sets**: Unless the template says "sorted ascending" or specifies ordering, treat list fields as unordered sets. The evaluator sorts values.
- **Sort ascending**: When the template requires sorting, sort string IDs lexicographically ascending, numbers numerically ascending.
- **Currency**: All monetary amounts in USD, rounded to 2 decimal places with `round(x, 2)`.
- **Dates**: All dates in `YYYY-MM-DD` format.
- **Nulls**: Use JSON `null` when a field is absent (e.g., missing contract_id, missing receipt_id). Use `0.0` for zero monetary amounts, `0` for zero counts.
- **Enum values**: Use the exact string values the template defines. Do not paraphrase or invent new codes.

## References

- [api_schema.md](references/api_schema.md) — Complete field-level schema for every ProcureOps endpoint
- [computation_rules.md](references/computation_rules.md) — Financial formulas, business rules, exception code catalogues, and data selection rules
