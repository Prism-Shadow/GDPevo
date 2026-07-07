# ProcureOps Operational Decision Skill

## API Basics
- **Base URL:** `http://127.0.0.1:8006`
- **System of record:** The ProcureOps API is authoritative. Local memos and packets provide target IDs and business context, but actual values, statuses, and relationships must come from the API.
- **Endpoints:**
  - `/suppliers`
  - `/items`
  - `/contracts`
  - `/purchase_orders`
  - `/receipts`
  - `/ap/invoices`
  - `/ap/payments`
  - `/budget_snapshots`
  - `/vendor_risk_events`
  - `/approvals`

All endpoints return JSON lists of records unless noted otherwise.

## General Output Conventions
- Return **only** the JSON object requested by the task. No prose outside the JSON.
- Follow the task-local `answer_template.json` exactly for keys and structure.
- **Currency:** USD, rounded to **2 decimal cents**.
- **Percentages:** Round to 1 decimal place unless the template says otherwise.
- **Ratios:** Use 4 decimal places when specified (e.g., `receipt_completion_ratio`).
- **Lists:** Sort ascending alphabetically unless the template explicitly says "set" or specifies another order.
- **Dates:** Use `YYYY-MM-DD` format.
- **Nulls:** Use `null` (not empty string) for missing optional fields.

## Cross-Cutting Business Rules

### Readiness and Blocking Logic
- `ready`: no blockers, all evidence present.
- `at_risk`: blockers exist but are not all fatal (e.g., `supplier_watch` with no severe risk event, AP hold with clear resolution path).
- `not_ready`: fatal blockers exist (e.g., `missing_contract`, `late_due_date`, `open_supplier_risk` with severe event, `pending_receipt` with no receipt evidence).
- **Overall readiness** for a program or packet:
  - `not_ready` if any line is `not_ready`.
  - `at_risk` if any line is `at_risk` and none are `not_ready`.
  - `ready` only if all lines are `ready`.

### Supplier Risk Evaluation
- Query `/vendor_risk_events` filtered by `supplier_id`.
- A `watch` rating is **context only** and does not block unless the task explicitly requires it.
- A supplier-risk hold requires an **open severe event** (`severity: "severe"` or equivalent) to be considered fatal.
- `supplier_risk_ok` is `true` if no severe open events exist, even if watch-rated or non-severe events are open.
- `open_supplier_risk_event_ids` must include **all** open or monitoring events as of the review date, sorted ascending.

### Purchase Order and Receipt Relationships
- One PO can have multiple receipts. One receipt can cover multiple PO lines.
- Receipts reference a `po_id`. Match receipts to invoices via the PO, not by direct receipt-to-invoice linkage unless the data provides it.
- When evaluating an invoice, sum **all** receipts tied to the same PO for `quantity_received`.
- **Exclude cancelled POs** from contract usage, budget committed amounts, and receipt scope. A PO is cancelled if its status is `cancelled` or similar.

### Three-Way Match Rules
1. **Quantity check:** Compare `quantity_billed` (from invoice) to `quantity_received` (sum of receipts for the PO).
2. **Price check:** Compare `invoice_unit_price` to `po_unit_price` and `contract_unit_price`.
3. **PO status check:** Verify the PO is not cancelled.
- If all match within tolerance (usually exact for these tasks), reason code is `APPROVED_THREE_WAY_MATCH`.
- If billed > received: `QTY_VARIANCE` or `INVOICE_QTY_EXCEEDS_RECEIPT`.
- If no receipt exists for the PO: `NO_RECEIPT`.
- If a scheduled payment is already recorded: `SCHEDULED_PAYMENT_FOUND`.

### Invoice Hold and Release Decisions
- `hold_decision`: `RELEASE` only when three-way match passes, no severe risk, and no pending approvals.
- `hold_decision`: `HOLD` otherwise. Record the primary `hold_code`:
  - `NO_RECEIPT` when `quantity_received == 0`.
  - `QTY_VARIANCE` when billed ≠ received.
  - Other codes as specified by the template.
- `release_to_payment`: `true` only when `hold_decision == "RELEASE"`.
- `quantity_variance = quantity_billed - quantity_received` (can be negative; round to 2 decimals).
- `quantity_variance_pct = (quantity_variance / quantity_billed) * 100` (round to 1 decimal; use billed qty as denominator).

### Chargeback and Net Release Logic
- An `approved` chargeback reduces the releasable amount.
- `net_release_amount = invoice_total - approved_chargeback_amount`.
- If a chargeback is `pending_quality_review`, the invoice stays on hold.
- If no receipt exists for the PO, decision is `hold_missing_receipt` regardless of chargebacks.
- A receipt with `Inspection Hold` or pending quality review blocks release even if the AP ledger shows approved.
- `excluded_same_po_receipt_ids` lists receipts tied to the same PO but scoped to a different invoice (e.g., duplicate receipts).

## Calculation Patterns

### Contract Ceiling Check
- `noncancelled_subtotal` = sum of line subtotals for all non-cancelled POs under the contract.
- `headroom_before_change = ceiling_amount - noncancelled_subtotal`.
- `requested_subtotal = requested_quantity * unit_price`.
- `headroom_after_change = headroom_before_change - requested_subtotal`.
- `ceiling_ok = headroom_after_change >= 0`.
- **Contract exposure is line subtotal only** (before tax and freight).

### Program Budget Check
- `remaining_budget = budget_cap - committed_amount`.
- `requested_tax = requested_subtotal * (tax_rate_percent / 100)`.
- `requested_total = requested_subtotal + requested_tax + freight_if_provided`.
- `budget_after_change = remaining_budget - requested_total`.
- `budget_ok = budget_after_change >= 0`.
- `max_quantity_with_current_budget = floor(remaining_budget / (unit_price * (1 + tax_rate_percent / 100)))`.
- **Budget exposure includes tax** (and freight only if the memo provides it).

### Vendor Balance Reconciliation
- `opening_balance` is given by the task (often `0.00` for a slice).
- `close_balance = opening_balance + invoice_total - scheduled_payments`.
- `held_invoice_total` = sum of invoice totals where `hold_decision == "HOLD"`.
- `releasable_invoice_total` = sum of invoice totals where `hold_decision == "RELEASE"` and not yet scheduled.
- `balance_status`:
  - `FULLY_SCHEDULED` if `close_balance == 0` and all invoices are scheduled for payment.
  - `OPEN_HELD` if `held_invoice_total > 0`.
  - `OPEN_APPROVED` if releasable invoices exist but are not yet scheduled.

### Receipt Reconciliation
- `short_qty_vs_po = ordered_qty - received_qty`.
- `unreceived_billed_qty = max(0, billed_qty - received_qty)`.
- `receipt_completion_ratio = received_qty / ordered_qty` (4 decimal places).
- `received_goods_value = received_qty * po_unit_price`.
- `unreceived_goods_value = short_qty_vs_po * po_unit_price`.

## Approval State Evaluation
- Query `/approvals` by `requisition_id` or related record.
- `approval_ok = true` only if the **latest** event's `action` is in the memo's `approval_good_actions` list (commonly `["approved"]`).
- If the latest action is `submitted`, `pending`, etc., `approval_ok = false`.
- Use the **latest event by date** (and event ID if dates tie).

## Nomination and Committee Actions
- `nomination_decision` per line:
  - `nominate` if `readiness_status == "ready"`.
  - `conditional_nomination` if `readiness_status == "at_risk"`.
  - `hold` if `readiness_status == "not_ready"`.
- `committee_action` aggregates by supplier:
  - `nominate_now_supplier_ids`: suppliers with all lines ready.
  - `conditional_supplier_ids`: suppliers with at least one at-risk line and no not-ready lines.
  - `hold_supplier_ids`: suppliers with any not-ready line.
- `next_owner` routing:
  - `ap_team` when the primary blockers are AP holds or invoice exceptions.
  - `program_owner` when blockers are program-level (budget, late due date).
  - `quality_ops` when blockers are receipt or inspection related.
  - `buyer` when blockers are supplier or contract related.
- `send_to_committee`: `"no"` when all lines are hold (nothing to nominate), `"yes"` when any line is ready or conditional.

## Common Pitfalls
1. **Using memo data over API data.** Always verify status, quantities, and amounts from the API. Memos may be stale.
2. **Forgetting to sort.** Most list fields must be ascending. The evaluator often sorts values before comparing.
3. **Including cancelled POs.** Always filter out cancelled POs from contract usage and budget committed amounts.
4. **Mismatched tax inclusion.** Contract checks use subtotal only; budget checks include tax (and memo-provided freight).
5. **Incorrect quantity received.** Sum all receipts for the PO, not just one receipt line.
6. **Null vs empty list.** Use `[]` for empty lists, `null` for absent single values. Do not return `"null"` strings.
7. **Rounding at the wrong time.** Round only at final output; keep full precision during intermediate calculations to avoid cent drift.
8. **Missing evidence IDs.** Include all API record IDs used in `endpoint_record_ids` or equivalent evidence fields.
9. **Approval date ambiguity.** When multiple approval events exist, always pick the latest by `event_date`, then by highest `event_id` if tied.
10. **PO-73xx alias confusion.** If a memo references a generated or alias receipt ID that does not exist in the API, use the available shared IDs as instructed and note the exclusion.

## Decision Tree Quick Reference

| Condition | Decision |
|-----------|----------|
| Billed qty == Received qty, no risk, PO active | `RELEASE` / `nominate` |
| Billed qty > Received qty, receipt exists | `HOLD` (`QTY_VARIANCE`) / `conditional_nomination` |
| No receipt for PO | `HOLD` (`NO_RECEIPT`) / `hold` |
| Open severe supplier risk event | `HOLD` / `hold` |
| Budget after change < 0 | `hold_for_budget` |
| Approval not final | `hold_for_approval` |
| Budget < 0 AND Approval not final | `hold_for_budget_and_approval` |
| Approved chargeback, receipt OK | `release_net_after_approved_chargeback` |
| Pending quality chargeback | `hold_pending_quality_chargeback` |

## Source Precedence
1. **Primary:** ProcureOps API live records.
2. **Secondary:** Task-local memos and packets (for target IDs, business rules like tax rates, approval good actions).
3. **Tertiary:** `answer_template.json` (for output schema and enums).

When API data contradicts a memo, trust the API and log the discrepancy implicitly through the calculated result.
