## When to Use

Use this skill whenever the task involves a **ProcureOps ERP domain** — procurement, receiving, accounts payable, sourcing, change control, or supplier risk within a shared operational API. The skill provides the entity model, record-traversal patterns, calculation conventions, and decision frameworks needed to answer structured JSON tasks.

## ProcureOps Entity Model

Understand the record graph before computing any answer. Every collection is read-only and fetched via GET.

**Core entities and their relationships:**

- **Program** (`/programs`) — budget owner, budget cap, committed amount, cost center, region.
- **Supplier** (`/suppliers`) — risk rating (`low`/`medium`/`watch`/`high`), payment terms, status (`active`/`quality_hold`).
- **Item** (`/items`) — SKU, standard cost, UOM, preferred supplier, category.
- **Contract** (`/contracts`) — ceiling amount, unit price, price type (`fixed`/`indexed`/`not_to_exceed`), effective/expiry dates, linked to one program and one SKU.
- **Purchase Requisition** (`/purchase_requisitions`) — need-by date, quantity, priority, status (`draft`/`approved`/`converted`/`cancelled`).
- **Approval** (`/approvals`) — event log keyed by requisition or other object IDs. Actions include `submitted`, `approved`, `returned`, `escalated`. Sort by `event_date` descending for latest state.
- **Purchase Order** (`/purchase_orders`) — lines with SKU, quantity, unit price; status (`open`/`confirmed`/`partial_receipt`/`received`/`closed`/`cancelled`); linked to requisition, contract, and supplier. Cancelled POs should be excluded from contract-usage and budget-commitment calculations.
- **Receipt** (`/receipts`) — lines with quantity received/rejected, inspection status (`passed`/`variance`), receipt status (`accepted`/`accepted_with_note`/`inspection_hold`); linked to PO and supplier.
- **AP Invoice** (`/ap/invoices`) — lines with quantity billed and unit price; status (`approved`/`on_hold`/`pending_receipt`/`paid`); hold codes (`QTY_VARIANCE`/`PRICE_VARIANCE`/`NO_RECEIPT`/`SUPPLIER_REVIEW`); linked to PO through `po_id` and optionally to a receipt through `receipt_id`.
- **AP Payment** (`/ap/payments`) — scheduled date, amount, status (`scheduled`/`released`/`blocked`); linked to invoice.
- **Budget Snapshot** (`/budget_snapshots`) — point-in-time snapshot with budget cap, committed amount, pending invoice amount; one per program.
- **Vendor Risk Event** (`/vendor_risk_events`) — event date, type, severity (`low`/`medium`/`high`), status (`open`/`monitoring`/`closed`); linked to supplier and optionally a PO.

## API Usage Patterns

Fetch all records from a collection with `GET /<collection>`. Use `GET /<collection>/<id>` for single-record lookups. Query-parameter filters support exact-match on top-level and nested fields; date collections also support `start` and `end` range parameters.

**Prefer fetching all records and filtering client-side.** This avoids missing data due to incomplete server-side filter coverage. Save all collections to local variables and traverse by ID.

## Calculation Conventions

### Currency and Rounding

- All USD amounts are rounded to **2 decimal places** (cents).
- Use `round(value, 2)` for every monetary field.
- Multiply before rounding to preserve precision: `round(qty * unit_price, 2)`.

### Quantities and Ratios

- Receipt completion ratio: `received_qty / ordered_qty`, rounded to **4 decimal places**.
- Quantity variance percentage: `abs(billed_qty - received_qty) / po_qty * 100`, rounded to **1 decimal place**.
- Quantities are integers; round quantity variance to 2 decimals when the template specifies.

### Budget Arithmetic

- **Budget headroom** = `budget_cap - committed_amount`.
- **Contract headroom** = `ceiling_amount - sum(subtotals of non-cancelled POs under that contract)`.
- When computing budget impact of a change request, include tax: `subtotal * (1 + tax_rate)`.
- **Max affordable quantity** = `floor(remaining_budget / (unit_price * (1 + tax_rate)))`.

### Date Filtering: "As Of" Semantics

When a task specifies an `as_of_date`:
- **Receipts**: Include only receipts with `receipt_date <= as_of_date`. Future-dated receipts that have NOT yet occurred are excluded.
- **Invoices**: Include only invoices with `invoice_date <= as_of_date`.
- **Risk events**: Include ALL risk events regardless of event date — risk context is about the current state of the supplier, not just events before the as-of date. Open and monitoring events provide ongoing risk signal.
- **Payments**: Include payments with `scheduled_date` up to the specified window end date (e.g., "through 2026-06-30").

### List and Set Conventions

- Sort ID lists **ascending** alphabetically (standard string sort).
- Treat lists as **sets** — no duplicates, sorted — unless the template explicitly specifies an ordering.
- Use `sorted()` on Python lists of strings.

## Record Traversal Patterns

### From an Invoice to Full Context
```
Invoice → po_id → Purchase Order → program_id, contract_id, supplier_id
Invoice → receipt_id → Receipt → lines (quantity_received)
PO → contract_id → Contract → unit_price, ceiling_amount, status
PO → supplier_id → Supplier → name, risk_rating, status
```

### From a Receipt to Full Context
```
Receipt → po_id → Purchase Order → (same chain as above)
Find invoices referencing this receipt: filter invoices where receipt_id matches
```

### Supplier Risk Context
```
Supplier → filter vendor_risk_events by supplier_id
→ Separate into open, monitoring, closed by status
→ Open events with severity "high" are "severe"
→ Supplier "watch" rating plus any open risk event = elevated concern
```

### Approval State for a Requisition
```
Filter approvals where object_id == requisition_id
Sort by event_date descending → latest event is current state
Look for action "approved" to confirm approval
```

## Decision Frameworks

### Sourcing Nomination Readiness

For each package SKU, evaluate blockers:

| Blocker | Condition |
|---|---|
| `missing_contract` | No active contract for this SKU × program |
| `supplier_watch` | Supplier risk rating is `watch` |
| `open_supplier_risk` | Any open risk event (not monitoring) for this supplier |
| `ap_hold` | Any invoice for this PO with status `on_hold` or `pending_receipt` |
| `pending_receipt` | Sum of received quantities across all receipts < PO ordered quantity |
| `late_due_date` | PO due date is before the as-of date |

Decision mapping:
- `missing_contract` → **hold** / **not_ready**
- `open_supplier_risk` → **conditional_nomination** / **at_risk**
- `supplier_watch` or `ap_hold` or `pending_receipt` (with contract present, no open risk) → **conditional_nomination** / **at_risk**
- No blockers → **nominate** / **ready**

Program budget headroom uses the program record directly: `budget_cap - committed_amount`.

### Receiving Closeout (Invoice Release Decision)

Compare ordered, received, rejected, and billed quantities for each PO line:
- `short_qty_vs_po` = `ordered_qty - received_qty`
- `unreceived_billed_qty` = `billed_qty - received_qty` (capped at 0 minimum)
- `receipt_completion_ratio` = `received_qty / ordered_qty`

Exception codes:
- `INVOICE_QTY_EXCEEDS_RECEIPT` when `billed_qty > received_qty`
- `PARTIAL_RECEIPT` when `received_qty < ordered_qty`
- `SUPPLIER_WATCH_RISK` when the supplier's risk rating is `watch`
- `PRICE_MISMATCH` when PO unit price ≠ contract unit price
- `DAMAGE_REJECTION` when `rejected_qty > 0`

Financial values:
- `received_goods_value` = `received_qty × po_unit_price`
- `unreceived_goods_value` = `unreceived_billed_qty × po_unit_price`

Disposition logic:
- Quantity variance with accepted receipt → `accept_partial_hold_variance`
- Invoice on hold → `keep_invoice_on_hold`
- Shortage → `record_shortage_follow_up`
- Supplier owes remaining → `request_credit_or_remaining_delivery`

### AP Close Reconciliation

For a slice of target invoices:

**Invoice-level**:
- `quantity_received` comes from the receipt linked to the invoice; use `0.00` when no receipt exists
- `quantity_variance` = `quantity_billed - quantity_received`
- `quantity_variance_pct` = `abs(variance) / po_quantity * 100` (1 decimal)
- Hold decision: `HOLD` for `on_hold`/`pending_receipt` statuses; `RELEASE` for `approved`
- `net_balance_impact` = `invoice_total - scheduled_payment_amount`

**Vendor balance** (per supplier, opening balance from task instructions):
- `close_balance` = `opening_balance + invoice_total - scheduled_payments`
- Status: `OPEN_HELD` when held > 0; `OPEN_APPROVED` when releasable > 0 and close_balance > 0; `FULLY_SCHEDULED` when close_balance = 0

**Program summary**:
- `net_close_balance` = `invoice_total - scheduled_payments` (aggregated by program)

**Reason codes** (alphabetical):
- `APPROVED_THREE_WAY_MATCH` — invoice approved, receipt exists, quantity variance ≈ 0
- `NO_RECEIPT` — receipt quantity is 0
- `QTY_VARIANCE` — absolute variance > 0.01
- `SCHEDULED_PAYMENT_FOUND` — a payment exists for this invoice

### Change Control

**Contract check**: Sum subtotals of all non-cancelled POs under the contract. Compare requested subtotal against headroom.

**Budget check**: Use the budget snapshot record. Budget exposure = subtotal × (1 + tax rate). Compare against `budget_cap - committed_amount`.

**Approval check**: Find the latest approval event for the source requisition. Only `action == "approved"` counts as approval OK.

**Supplier risk check**: Only **open** events with **high** severity block the change. Supplier `watch` rating is context only, not a blocker, unless there's an open severe event.

Decision combination logic:
- Both budget and approval fail → `hold_for_budget_and_approval`
- Only budget fails → `hold_for_budget`
- Only approval fails → `hold_for_approval`
- Only supplier risk fails → `hold_for_supplier_risk`
- Contract ceiling exceeded → `reject_contract_mismatch`
- All clear → `release_amendment`

### Receiving/AP Release with Chargebacks

When a task provides a **local chargeback register** alongside API records, the register is an authoritative data source for chargeback amounts and statuses — use it alongside API PO, receipt, and invoice records.

**For each target invoice**:
- Identify the receipt(s) in scope for this invoice (from the chargeback register or invoice `receipt_id`)
- Identify receipts for the same PO that belong to OTHER invoices and list them as `excluded_same_po_receipt_ids`
- Compute chargeback amounts: `basis_quantity × unit_cost`

**Decision**:
- Approved chargeback → `release_net_after_approved_chargeback` with `net_release = invoice_total - approved_chargeback`
- Pending quality chargeback → `hold_pending_quality_chargeback` with `net_release = invoice_total - pending_chargeback`
- No receipt exists → `hold_missing_receipt` with `net_release = 0`

**Receiving exceptions** (per receipt):
- `Underage Quantity` when received < PO ordered
- `Inspection Hold` when receipt status is `inspection_hold`
- `AP Quantity Variance` when a chargeback for this receipt has reason `AP Quantity Variance`
- `Severe Unmatched Quantity` when the shortfall is substantial (use judgment; e.g., >25% of PO quantity)
- Chargeback status comes from the chargeback register
- Resolution status: `net_release_ready` for approved chargebacks; `hold_for_quality_review` for inspection holds with pending chargebacks

**Summary**:
- Separate invoices into release and hold queues
- Sum approved, pending, and net release amounts across all target invoices
- Followup actions cover: asking for missing receipts, routing quality reviews, posting approved chargeback netting, and flagging duplicate same-PO receipts tied to other invoices

## Key Data Quality Rules

1. **Cancelled POs are not committed spend.** Always exclude them when summing contract usage or budget commitments.
2. **A receipt can be for a PO not linked to the invoice's receipt.** When an invoice has `receipt_id = null`, it means no receipt has been matched yet — the invoice is still pending receipt.
3. **Multiple receipts can exist for a single PO.** Each may belong to a different invoice. Always check all receipts for the PO when computing excluded receipt lists.
4. **Supplier risk is cumulative.** Open AND monitoring events both matter. Open events carry more weight than monitoring events. Only high-severity open events are "severe."
5. **Budget snapshots are point-in-time.** Use the snapshot with the most relevant date; the `committed_amount` field in the snapshot may differ from the live program record.
6. **Invoice totals include freight and tax.** Do not recompute total from subtotal alone; use the `total` field from the API record.
7. **Payment statuses matter.** Only `scheduled` and `released` payments reduce balances. `blocked` payments should not be counted as reducing the close balance.
