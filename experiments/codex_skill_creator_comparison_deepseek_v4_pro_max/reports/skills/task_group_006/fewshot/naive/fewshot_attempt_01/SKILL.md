---
name: procureops-solver
description: Solve ProcureOps procurement tasks by querying the shared REST API, cross-referencing operational records, and producing structured JSON answers using local answer templates.
---

# ProcureOps Solver

## Overview

This skill guides solving procurement-domain tasks backed by a shared ProcureOps
REST API. Every task provides local payloads (memos, packets, templates) that
name anchor IDs; the API is the system of record for all operational data.
Answers must be pure JSON matching the task's `answer_template.json`.

## The ProcureOps API

The runner supplies the base URL as `<TASK_ENV_BASE_URL>`. All endpoints are
read-only GET. No authentication is required.

| Endpoint | Returns |
|----------|---------|
| `/health` | Liveness check |
| `/manifest` | Endpoint listing / schema hints |
| `/suppliers` | Supplier records (id, name, status, risk_rating) |
| `/items` | Item / SKU records |
| `/programs` | Program records (id, owner, budget_cap) |
| `/contracts` | Contract records (id, program_id, supplier_id, sku, price_type, unit_price, ceiling_amount, status) |
| `/purchase_requisitions` | Requisition records (id, program_id, sku, supplier_id, status) |
| `/purchase_orders` | PO records (id, program_id, requisition_id, contract_id, supplier_id, lines with sku/qty/unit_price, status) |
| `/receipts` | Receipt records (id, po_id, receipt_date, lines with sku/qty received/rejected, status) |
| `/ap/invoices` | Invoice records (id, po_id, supplier_id, lines with sku/qty/unit_price, subtotal, freight, tax, total, status, hold_code) |
| `/ap/payments` | Scheduled/executed payment records (invoice_id, amount, status) |
| `/approvals` | Approval event records (requisition_id or contract_id, action, actor, event_date) |
| `/budget_snapshots` | Budget snapshot records (program_id, budget_cap, committed_amount) |
| `/vendor_risk_events` | Vendor risk event records (supplier_id, severity, status) |

### Query conventions

- Many endpoints accept query parameters. Start with a bare GET to inspect all
  records, or filter by known IDs when supported.
- IDs follow predictable prefixes: `SUP-` (supplier), `PRG-` (program),
  `CR-` (contract), `REQ-` (requisition), `PO-` (PO), `RCV-` (receipt),
  `AP-` (invoice), `VRE-` (vendor risk event), `APR-` (approval event),
  `BUD-` (budget snapshot), `CB-` (chargeback).
- Cross-reference records by following foreign-key fields:
  - `supplier_id` on contracts, POs, receipts, invoices, risk events
  - `program_id` on contracts, POs, requisitions, budget snapshots
  - `contract_id` on POs
  - `po_id` on receipts, invoices
  - `requisition_id` on POs, approvals
  - `invoice_id` on payments
  - `sku` on items, contracts, requisitions, PO lines, receipt lines, invoice lines

### Program scoping

When a task targets specific programs, scope all API lookups to records
associated with those programs. A PO belongs to a program either directly
through its `program_id` field or through its linked contract or requisition.
An invoice belongs to a program through its PO.

## Domain Model: Procurement Lifecycle

```
Contract -- PO -- Receipt -- Invoice -- Payment
   |          |        |           |
   --- SKU ---+--------+-----------+

Requisition -- PO -- Approval events

Budget Snapshot --- Program (committed = sum of non-cancelled PO subtotals)

Vendor Risk Events --- Supplier
```

Key relationships:

- **Contract** establishes pricing (unit_price, price_type) and a spending
  ceiling for a supplier+SKU+program combination.
- **Purchase Order** places an order under a contract or requisition with
  line-item quantities. PO statuses: `open`, `partial_receipt`,
  `fully_received`, `cancelled`.
- **Receipt** confirms delivery. One PO can have multiple receipts. Receipt
  statuses: `accepted`, `pending_inspection`. Receipt lines record quantities
  received and rejected.
- **Invoice** requests payment. Invoice statuses: `approved`, `on_hold`,
  `pending_receipt`, `paid`. Hold codes: `QTY_VARIANCE`, `NO_RECEIPT`,
  `PRICE_MISMATCH`, `DAMAGE_REJECTION`.
- **Payment** records scheduled or executed payments against invoices.
- **Approval events** track workflow state for requisitions and contracts.
  A requisition must reach `approved` status before the associated PO is
  fully cleared for sourcing.
- **Budget snapshots** track program spending: `committed_amount` is the sum
  of subtotals from non-cancelled POs under that program.
- **Vendor risk events** track supplier-level issues. Severity: `severe`,
  `moderate`, `watch`. Status: `open`, `closed`, `monitoring`. A supplier's
  `risk_rating` on the supplier record itself is a summary (e.g., `watch`,
  `clean`, `flagged`).

## Common Workflows

### 1. Sourcing Nomination Readiness

For each line SKU in a nomination packet:

**Supplier identification**: Trace from the requisition or PO to find the
selected supplier. The requisition's `supplier_id` or the PO's `supplier_id`
is the nominated supplier.

**Contract check**: Look up contracts by `program_id` + `sku` + `supplier_id`.
A SKU with an active contract has `commercial_basis_id` set. Missing contract
adds `missing_contract` blocker.

**Receipt evidence**: Find receipts linked to the SKU's POs by matching
`po_id` and receipt-line `sku`. Receipt existence provides evidence.

**Invoice exceptions**: Find invoices linked to the SKU's POs. Check invoice
`status` and `hold_code`. An `on_hold` or `pending_receipt` invoice adds
`ap_hold` or `pending_receipt` blockers.

**Risk events**: Find open or monitoring risk events for the supplier
(`/vendor_risk_events` filtered by `supplier_id`). Open events add
`open_supplier_risk`. A supplier with `risk_rating` of `watch` or `flagged`
adds `supplier_watch`.

**Due date check**: Compare the PO or requisition delivery date against the
task's `as_of_date`. Late items add `late_due_date`.

**Budget headroom**: From `/budget_snapshots`, compute
`remaining_budget = budget_cap - committed_amount`.

**Readiness decision** per line:
- `ready`: No blockers.
- `at_risk`: Only `supplier_watch` or other minor blockers present.
- `not_ready`: Any of `missing_contract`, `open_supplier_risk`, `ap_hold`,
  `pending_receipt`, `late_due_date` present.

**Nomination decision** per line:
- `nominate`: readiness is `ready`
- `conditional_nomination`: readiness is `at_risk`
- `hold`: readiness is `not_ready`

**Committee action**: `send_to_committee` is `yes` only when at least one line
is `nominate` or `conditional_nomination`. `next_owner` is the team that can
resolve the most severe blocker (`ap_team` for AP holds, `buyer` for missing
contracts, `quality_ops` for receipt issues, `program_owner` for budget).

### 2. Receiving-Control Closeout

Given a receipt batch ID:

**Inspection summary**: Pull the receipt record to get `po_id`, `receipt_date`,
`warehouse_id`, `packing_slip`, `receiver`. Trace to PO for `supplier_id` and
`program_id`. Trace to supplier for `supplier_name`.

**Line reconciliation** for each PO line referenced by the receipt:
- `ordered_qty` from PO line
- `received_qty` from receipt line (sum across all receipts for the same PO)
- `rejected_qty` from receipt line
- `billed_qty` from invoice line (sum across all invoices for the same PO)
- `short_qty_vs_po` = ordered_qty - received_qty
- `unreceived_billed_qty` = max(0, billed_qty - received_qty)
- `receipt_completion_ratio` = received_qty / ordered_qty (round to 4 decimals)
- `po_unit_price` from PO line
- `contract_unit_price` from the linked contract
- `invoice_unit_price` from the invoice line
- `contract_price_match` = true when contract_unit_price equals invoice_unit_price

**Invoice review**: Check the invoice linked to the receipt batch:
- `exception_codes` derive from the data:
  - `INVOICE_QTY_EXCEEDS_RECEIPT` when billed_qty > received_qty
  - `PARTIAL_RECEIPT` when received_qty < ordered_qty
  - `SUPPLIER_WATCH_RISK` when supplier has open risk events or watch rating
  - `PRICE_MISMATCH` when contract and invoice unit prices differ
  - `DAMAGE_REJECTION` when rejected_qty > 0

**Financials**:
- `received_goods_value` = received_qty * po_unit_price
- `unreceived_goods_value` = short_qty_vs_po * po_unit_price
- `invoice_subtotal`, `invoice_freight`, `invoice_tax`, `invoice_total` from
  invoice record

**Decision logic**:
- `batch_disposition`:
  - `release_full_invoice` when receipt complete and no exceptions
  - `accept_partial_hold_variance` when quantity variances but no damage
  - `reject_batch` when rejected_qty > 0 (damage)
  - `manual_recount_required` when variance is unexplained
- `ap_action`:
  - `release_invoice` when no exceptions
  - `keep_invoice_on_hold` when exceptions exist
  - `void_invoice` for extreme cases
- `receiving_action`:
  - `record_shortage_follow_up` when short_qty_vs_po > 0
  - `no_receiving_action` when quantities match
  - `reject_all_units` when rejected_qty > 0
- `supplier_action`:
  - `request_credit_or_remaining_delivery` when short or unreceived-billed
  - `no_supplier_action` when no discrepancy
  - `supplier_debit_for_damage` when rejected_qty > 0

### 3. AP Close Desk Reconciliation

Given specific invoice IDs and a close date:

**Invoice decisions** (one per invoice):
- Pull the invoice, its PO, all receipts for that PO, and any scheduled payments.
- `hold_decision`:
  - `RELEASE` when three-way match holds: qty_billed == qty_received, invoice
    status is `approved`, and no unresolved exceptions.
  - `HOLD` when qty_billed > qty_received, no receipt exists, or invoice is
    `on_hold`/`pending_receipt`.
- `quantity_billed` from invoice line
- `quantity_received` = sum of received qty from all receipts for the PO
- `quantity_variance` = quantity_billed - quantity_received
- `quantity_variance_pct` = (|quantity_variance| / ordered_qty) * 100, rounded
  to 1 decimal
- `scheduled_payment_amount` = sum of payment amounts for this invoice through
  the close period; 0.00 if none.
- `net_balance_impact` = invoice_total - scheduled_payment_amount
- `release_to_payment` = true when hold_decision is RELEASE
- `hold_code` = invoice's hold_code field, or null when releasing
- `reason_codes`:
  - `APPROVED_THREE_WAY_MATCH` when quantities match and invoice is approved
  - `QTY_VARIANCE` when quantity_variance > 0
  - `NO_RECEIPT` when quantity_received == 0
  - `SCHEDULED_PAYMENT_FOUND` when scheduled_payment_amount > 0

**Vendor balances** (one per supplier):
- Group invoice decisions by supplier.
- `opening_balance` = 0.00 unless the task specifies otherwise.
- `invoice_total` = sum of invoice totals for this supplier in the slice
- `scheduled_payments` = sum of scheduled payment amounts
- `held_invoice_total` = sum of invoice totals for HOLD decisions
- `releasable_invoice_total` = sum of invoice totals for RELEASE decisions
- `close_balance` = opening_balance + invoice_total - scheduled_payments
- `balance_status`:
  - `FULLY_SCHEDULED` when close_balance == 0 and no held invoices
  - `OPEN_HELD` when held_invoice_total > 0
  - `OPEN_APPROVED` when close_balance > 0 but all invoices released

**Program summary**: Group by program_id. `held_total` = sum of HOLD invoice
totals; `released_total` = sum of RELEASE invoice totals.

**Queues**: `payment_hold_queue` = invoice_ids with HOLD decisions.
`payment_release_queue` = invoice_ids with RELEASE decisions.

**total_close_balance**: Sum of all vendor close_balances.

### 4. Change-Control Decision

Given a change memo specifying contract, SKU, supplier, program, and
requested incremental quantity:

**Contract check**:
- `noncancelled_subtotal`: Sum PO subtotals (qty * unit_price per line) for
  all POs under this contract, **excluding** `cancelled` POs.
- `headroom_before_change` = ceiling_amount - noncancelled_subtotal
- `requested_subtotal` = requested_quantity * contract unit_price
- `headroom_after_change` = headroom_before_change - requested_subtotal
- `ceiling_ok` = headroom_after_change >= 0

**Program budget check**:
- From `/budget_snapshots` for the program: `budget_cap`, `committed_amount`.
- `remaining_budget` = budget_cap - committed_amount
- `requested_tax` = requested_subtotal * (tax_rate_percent / 100)
- `requested_total` = requested_subtotal + requested_tax
- `budget_after_change` = remaining_budget - requested_total
- `budget_ok` = budget_after_change >= 0
- `max_quantity_with_current_budget` = floor(remaining_budget / (unit_price *
  (1 + tax_rate / 100)))

**Approval check**:
- Find the latest approval event for the source requisition, sorted by
  `event_date` descending.
- `approval_ok` = true when latest action is `approved`.

**Supplier risk check**:
- Find open risk events for the supplier (status == `"open"`).
- `supplier_risk_ok` = true when no open severe events exist. Supplier on
  "watch" alone does not block; only an open event with severity `"severe"`
  makes `supplier_risk_ok` false.

**Overall decision**:
- `release_amendment`: all checks pass
- `hold_for_budget`: only budget_ok is false
- `hold_for_approval`: only approval_ok is false
- `hold_for_supplier_risk`: only supplier_risk_ok is false
- `hold_for_budget_and_approval`: both budget_ok and approval_ok are false
- `reject_contract_mismatch`: ceiling_ok is false

**required_actions**: Derived from failing checks. Include
`obtain_final_requisition_approval` when approval_ok is false,
`raise_budget_exception_or_reduce_quantity` when budget_ok is false,
`resolve_supplier_risk_hold` when supplier_risk_ok is false.
`none` when all pass.

### 5. Receiving / AP Release File

Given target PO, receipt, and invoice IDs plus a local chargeback register:

**Release decisions** (one per invoice):
- Match each invoice to its PO, then find all receipts for that PO.
- `receipt_ids_in_scope`: receipts from the task's target receipt list.
- `excluded_same_po_receipt_ids`: receipts for same PO not in the target list.
- Check the local chargeback register:
  - `approved_chargeback_amount` = sum of basis_qty * unit_cost for chargebacks
    with status `approved` for this invoice.
  - `pending_chargeback_amount` = sum of basis_qty * unit_cost for chargebacks
    with status `pending_quality_review` for this invoice.
- `net_release_amount` = invoice_total - approved_chargeback_amount (when
  releasing); 0.00 otherwise.

**Decision** per invoice:
- `release_net_after_approved_chargeback`: approved chargebacks exist, no
  pending ones. Primary reason: `approved_qty_chargeback` or
  `approved_ap_quantity_variance`.
- `hold_missing_receipt`: no receipt at all for the PO. Primary reason:
  `no_receipt_on_po`.
- `hold_pending_quality_chargeback`: pending chargebacks in quality review.
  Primary reason: `inspection_hold_pending_chargeback`.

**Receiving exceptions** (one per receipt in scope, plus missing-receipt
pseudo-entries for POs with no receipts):
- `exception_codes` from chargeback register and receipt data:
  - `Inspection Hold` when chargeback is pending_quality_review
  - `Severe Unmatched Quantity` when variance is significant
  - `Underage Quantity` when received < ordered
  - `AP Quantity Variance` when billed != received
- `chargeback_status`: `approved`, `pending_quality_review`, or `not_applicable`
- `resolution_status`:
  - `net_release_ready` when approved chargeback exists, no pending
  - `hold_for_quality_review` when pending chargeback exists
  - `accepted_no_receiving_exception` when no chargeback and receipt is clean
  - `missing_receipt` when no receipt exists for the PO

## Calculation Reference

### Quantity formulas

| Formula | Definition |
|---------|------------|
| `short_qty_vs_po` | ordered_qty - received_qty |
| `unreceived_billed_qty` | max(0, billed_qty - received_qty) |
| `quantity_variance` | quantity_billed - quantity_received |
| `quantity_variance_pct` | (abs(quantity_variance) / ordered_qty) * 100 |
| `receipt_completion_ratio` | received_qty / ordered_qty |

### Dollar amount formulas (all rounded to cents)

| Formula | Definition |
|---------|------------|
| `received_goods_value` | received_qty * po_unit_price |
| `unreceived_goods_value` | short_qty_vs_po * po_unit_price |
| `net_balance_impact` | invoice_total - scheduled_payment_amount |
| `close_balance` | opening_balance + invoice_total - scheduled_payments |
| `noncancelled_subtotal` | sum(qty * unit_price) for POs where status != "cancelled" |
| `headroom_before_change` | ceiling_amount - noncancelled_subtotal |
| `headroom_after_change` | headroom_before_change - requested_subtotal |
| `remaining_budget` | budget_cap - committed_amount |
| `requested_tax` | requested_subtotal * (tax_rate_percent / 100) |
| `requested_total` | requested_subtotal + requested_tax |
| `budget_after_change` | remaining_budget - requested_total |
| `max_quantity_with_current_budget` | floor(remaining_budget / (unit_price * (1 + tax_rate/100))) |
| `chargeback_amount` | basis_quantity * unit_cost |
| `net_release_amount` | invoice_total - approved_chargeback_amount (when releasing) |

## Data Conventions

- **USD rounding**: Every dollar amount rounded to exactly 2 decimal places
  using standard rounding (half-up).
- **List sorting**: When the template specifies "sorted ascending", sort ID
  strings lexicographically ascending, numbers numerically ascending. When the
  template says "set", treat as unordered; follow the template's declared sort.
- **Null vs missing**: Use `null` (JSON null) for absent fields, not empty
  strings. Use `[]` for empty lists, `0.00` for zero dollar amounts.
- **Dates**: Format as `YYYY-MM-DD` strings.
- **Enums**: Use exact enum strings from the answer template. Do not invent new
  values.
- **Boolean fields**: Use JSON `true` / `false`, not strings.
- **Reason codes and exception codes**: Sort alphabetically within each list.

### Record status reference

- **Invoice statuses**: `approved`, `on_hold`, `pending_receipt`, `paid`, `void`
- **Receipt statuses**: `accepted`, `pending_inspection`, `rejected`
- **PO statuses**: `open`, `partial_receipt`, `fully_received`, `cancelled`
- **Contract statuses**: `active`, `expired`, `cancelled`
- **Supplier risk ratings**: `clean`, `watch`, `flagged`, `blocked`
- **Vendor risk event severity**: `severe`, `moderate`, `watch`
- **Vendor risk event status**: `open`, `closed`, `monitoring`

## Solving a New Task

1. **Read the prompt** to understand the task type and which API endpoints are
   in play. Identify the `<TASK_ENV_BASE_URL>` placeholder.
2. **Read every payload file** in `input/payloads/`. These name the specific
   anchor IDs (programs, POs, receipts, invoices, suppliers, contracts, SKUs).
3. **Read the answer template** (`answer_template.json`) to know exactly what
   keys, types, enums, and sorting rules the output must follow.
4. **Query the API**: Start by fetching the endpoints most likely to contain
   the anchor IDs. Follow foreign keys to pull related records. Fetch
   supporting endpoints (suppliers, programs, budget snapshots, risk events)
   for context.
5. **Cross-reference**: Join records by `program_id`, `supplier_id`, `po_id`,
   `contract_id`, `sku` as needed.
6. **Apply the workflow rules** from this skill for the task type.
7. **Compute derived values** using the formulas above.
8. **Produce JSON** matching the template shape, with correct types, enum
   values, sorting, and rounding.
9. **Return only JSON** -- no markdown fences, no prose outside the object.

## Common Pitfalls

- **Cancelled POs**: Exclude POs with status `cancelled` when computing
  contract usage subtotals and budget commitments.
- **Multiple receipts per PO**: Sum receipt quantities across all receipts for
  a PO when computing received_qty, not just the one named in the task.
- **Multiple invoices per PO**: An invoice ID may appear in the task but other
  invoices for the same PO exist in the system. Only act on the target
  invoices unless the template requires broader context.
- **Duplicate receipt IDs**: When a PO has multiple receipts and the task
  targets only one invoice, receipts linked to other invoices on the same PO
  should appear in `excluded_same_po_receipt_ids`.
- **Supplier risk "watch" vs "severe"**: A supplier with risk_rating `watch`
  or `flagged` is contextual but not automatically blocking for all decisions.
  For nomination readiness, any open risk event adds `open_supplier_risk`.
  For change-control, only open events with severity `severe` block release.
- **Opening balance**: Unless the task specifies otherwise, treat the opening
  AP balance as 0.00 for the target suppliers within the task's slice.
- **Scheduled payments**: Only payments scheduled through the task's effective
  period reduce the close balance.
- **Tax and freight in change control**: Tax applies to the line subtotal only.
  Freight is excluded from contract ceiling exposure unless the change memo
  explicitly provides a freight amount.
