# ProcureOps Business Rules

This reference defines the domain logic for procurement operations decisions. Each rule family covers a specific analysis dimension. Use exact field paths and enum values as shown.

---

## Three-Way Match

Compare quantities across PO, receipt, and invoice records for each PO line.

### Inputs

- PO: `ordered_qty`, `po_line_id`, `sku`
- Receipts for that PO: `received_qty`, `rejected_qty` (sum across all receipts)
- Invoices for that PO: `billed_qty`

### Computations

```
short_qty_vs_po     = ordered_qty - received_qty
unreceived_billed_qty = billed_qty - received_qty   (floor at 0)
receipt_completion_ratio = received_qty / ordered_qty

quantity_variance    = billed_qty - received_qty
quantity_variance_pct = (quantity_variance / ordered_qty) * 100
```

### Exception Codes

Assign based on these conditions, checked in order:

| Condition | Exception Code |
|-----------|---------------|
| billed_qty > received_qty AND received_qty > 0 | `INVOICE_QTY_EXCEEDS_RECEIPT` |
| received_qty < ordered_qty | `PARTIAL_RECEIPT` |
| Supplier has open or monitoring risk event | `SUPPLIER_WATCH_RISK` |
| Invoice unit_price != contract unit_price (within rounding tolerance) | `PRICE_MISMATCH` |
| rejected_qty > 0 | `DAMAGE_REJECTION` |
| No exceptions found | `NO_EXCEPTION` |

### AP Reason Codes

For AP close tasks, assign from this set:

- `APPROVED_THREE_WAY_MATCH`: PO qty == receipt qty == billed qty, and invoice status is approved
- `NO_RECEIPT`: No receipt record exists for the PO
- `QTY_VARIANCE`: billed_qty != received_qty
- `SCHEDULED_PAYMENT_FOUND`: A payment exists for this invoice

---

## Contract Ceiling

Check whether a requested incremental buy fits within the contract ceiling.

### Inputs

- Contract: `ceiling_amount`, `unit_price`, `status`
- All POs under this contract: `subtotal` (ordered_qty * unit_price), `status`
- Requested: `requested_quantity`

### Rules

1. **Exclude cancelled POs**. Only sum subtotals for POs where status is not "cancelled".
2. `noncancelled_subtotal` = sum of all noncancelled PO subtotals under the contract.
3. `headroom_before_change` = `ceiling_amount` - `noncancelled_subtotal`.
4. `requested_subtotal` = `requested_quantity * unit_price`.
5. `headroom_after_change` = `headroom_before_change` - `requested_subtotal`.
6. `ceiling_ok` = true when `headroom_after_change >= 0`.

Contract status must be "active" for the change to proceed.

---

## Budget Headroom

Check whether the requested buy fits within the program budget.

### Inputs

- Budget snapshot: `budget_cap`, `committed_amount`
- Requested: `requested_subtotal`, tax rate (from local memo)
- Tax rate field in memo: `tax_rate_percent` (e.g. 7.25 means 7.25%)

### Rules

1. `remaining_budget` = `budget_cap` - `committed_amount`.
2. `requested_tax` = `requested_subtotal * (tax_rate_percent / 100)`, rounded to cents.
3. `requested_total` = `requested_subtotal + requested_tax`, rounded to cents.
4. `budget_after_change` = `remaining_budget` - `requested_total`, rounded to cents.
5. `budget_ok` = true when `budget_after_change >= 0`.
6. `max_quantity_with_current_budget`: Solve `remaining_budget = qty * unit_price * (1 + tax_rate/100)`. Compute `qty = floor(remaining_budget / (unit_price * (1 + tax_rate/100)))`.

Do not include freight in budget exposure unless the local memo explicitly provides a freight amount.

---

## Supplier Risk

Assess supplier risk from vendor_risk_events.

### Inputs

- Supplier: `supplier_id`, `risk_rating`, `status`
- Vendor risk events for that supplier: `status`, `severity`, `event_id`

### Rules

1. **Open events**: Events where `status` is "open" or "monitoring".
2. **Severe open events**: Open events where `severity` is "severe".
3. `supplier_risk_ok` = true when there are zero severe open events AND the supplier `status` is "active".
4. `has_open_supplier_risk` = true when any open events exist (any severity).
5. A supplier with `risk_rating` = "watch" is a concern but does not by itself make `supplier_risk_ok` false unless severe open events exist.
6. For nomination tasks, the `supplier_watch` blocker applies when `risk_rating` is "watch" regardless of open events.

---

## Approval State

Determine whether a requisition has passed approval.

### Inputs

- Requisition: `requisition_id`
- Approval events for that requisition: `event_id`, `action`, `actor`, `event_date`
- Good-actions list from local memo (e.g. `["approved"]`)

### Rules

1. Find the latest approval event by `event_date` (descending).
2. `approval_ok` = true when the latest event's `action` is in the good-actions list from the memo.
3. If no approval events exist, `approval_ok` = false.

---

## Nomination Readiness (Blocker Codes)

For sourcing nomination tasks, determine blocker codes per package-line SKU.

### Blocker Code Enum

```
missing_contract
supplier_watch
open_supplier_risk
ap_hold
pending_receipt
late_due_date
none
```

### Assignment Rules

Check each condition and assign all matching codes. Use `["none"]` only when no other code applies.

| Condition | Code |
|-----------|------|
| No active contract exists for the SKU-supplier pair | `missing_contract` |
| Supplier `risk_rating` is "watch" | `supplier_watch` |
| Any open or monitoring vendor_risk_event exists for the supplier | `open_supplier_risk` |
| Any invoice for the PO has status "on_hold" | `ap_hold` |
| No receipt exists for the PO, OR invoice status is "pending_receipt" | `pending_receipt` |
| PO `due_date` is before the as_of_date AND received_qty < ordered_qty | `late_due_date` |

### Readiness & Nomination Decision

| Blocker profile | readiness_status | nomination_decision |
|-----------------|-----------------|---------------------|
| Zero blockers (`["none"]`) | `ready` | `nominate` |
| Blockers present but manageable (e.g. ap_hold, supplier_watch, late_due_date but not missing_contract or open_supplier_risk with severe events) | `at_risk` | `conditional_nomination` |
| Has `missing_contract`, `open_supplier_risk` with severe events, `pending_receipt` with zero receipts | `not_ready` | `hold` |

---

## AP Hold / Release

For AP close and invoice-release tasks.

### Hold Decision

| Condition | hold_decision | hold_code |
|-----------|--------------|-----------|
| Three-way match complete AND invoice approved AND no variance | `RELEASE` | null |
| billed_qty > received_qty | `HOLD` | `QTY_VARIANCE` |
| No receipt exists for the PO | `HOLD` | `NO_RECEIPT` |
| Invoice is on_hold for other reasons | `HOLD` | Current hold_code from API |

### Release to Payment

`release_to_payment` = true when hold_decision is `RELEASE` AND no qualifying blockers remain.

### Balance Impact

```
net_balance_impact = invoice_total - scheduled_payment_amount
```

For vendor balances with opening_balance:

```
close_balance = opening_balance + invoice_total - scheduled_payments
```

---

## Receiving Closeout

For receiving-control tasks.

### Dispositions

| Situation | batch_disposition |
|-----------|------------------|
| Shortage with approved chargeback, no damage | `accept_partial_hold_variance` |
| Full match, invoice on hold only for non-receipt reasons | `release_full_invoice` |
| Damage or severe mismatch with no resolution | `reject_batch` |
| Inconsistent counts requiring physical verification | `manual_recount_required` |

### AP Actions

| Situation | ap_action |
|-----------|----------|
| Invoice hold is justified (variance, missing receipt) | `keep_invoice_on_hold` |
| All exceptions cleared, match verified | `release_invoice` |
| Invoice is fraudulent or irreconcilable | `void_invoice` |

---

## Chargeback Handling

For invoice-release tasks that involve chargebacks.

### Inputs

Local chargeback register (from task payload): `chargeback_id`, `invoice_id`, `po_id`, `receipt_id`, `reason_code`, `basis_quantity`, `unit_cost`, `status`

### Rules

1. `chargeback_amount` = `basis_quantity * unit_cost`, rounded to cents.
2. `approved_chargeback_amount`: Sum of chargeback_amounts where status is "approved" for this invoice.
3. `pending_chargeback_amount`: Sum of chargeback_amounts where status is "pending_quality_review" for this invoice.
4. `net_release_amount` = `invoice_total - approved_chargeback_amount` (only when decision is to release after approved chargeback).
5. When chargeback status is "pending_quality_review", the invoice is held pending quality disposition.
6. When no chargeback exists for an invoice, both approved and pending chargeback amounts are 0.0.

### Invoice Release Decisions

| Condition | decision | primary_reason |
|-----------|---------|---------------|
| Approved chargeback covers variance, no pending issues | `release_net_after_approved_chargeback` | `approved_qty_chargeback` or `approved_ap_quantity_variance` |
| Pending quality review on chargeback | `hold_pending_quality_chargeback` | `inspection_hold_pending_chargeback` |
| No receipt on PO, no chargeback | `hold_missing_receipt` | `no_receipt_on_po` |

---

## Change-Control Decision

For modular change requests against a contract.

### Decision Enum

```
release_amendment
hold_for_budget
hold_for_approval
hold_for_supplier_risk
hold_for_budget_and_approval
reject_contract_mismatch
```

### Decision Logic

Check in order and assign the first matching:

1. Contract status is not "active" → `reject_contract_mismatch`
2. `ceiling_ok` is false → `hold_for_budget` (or combined with approval below)
3. `budget_ok` is false AND `approval_ok` is false → `hold_for_budget_and_approval`
4. `budget_ok` is false → `hold_for_budget`
5. `approval_ok` is false → `hold_for_approval`
6. `supplier_risk_ok` is false → `hold_for_supplier_risk`
7. All checks pass → `release_amendment`
