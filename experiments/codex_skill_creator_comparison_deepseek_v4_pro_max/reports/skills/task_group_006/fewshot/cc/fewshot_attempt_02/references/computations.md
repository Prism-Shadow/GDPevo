# ProcureOps Computations & Decision Rules

Every numeric value must be computed from API records, not assumed. This
reference covers standard formulas, logic chains, and decision tables used
across ProcureOps tasks.

---

## Receipt & Invoice Reconciliation

### Line-level reconciliation (one PO line at a time)

| Metric | Formula |
|--------|---------|
| ordered_qty | PO lines[].quantity for the matching line_id |
| received_qty | Sum of receipt lines[].quantity_received for all receipts on this PO line as of the as_of_date |
| rejected_qty | Sum of receipt lines[].quantity_rejected for all receipts on this PO line as of the as_of_date |
| billed_qty | Invoice lines[].quantity_billed for the invoice being reviewed |
| short_qty_vs_po | ordered_qty - received_qty (can be negative; never less than 0 in practice) |
| unreceived_billed_qty | billed_qty - received_qty (can be negative but treat floor at 0) |
| receipt_completion_ratio | received_qty / ordered_qty, rounded to 4 decimal places |
| contract_price_match | PO lines[].unit_price == contract.unit_price (for the matching contract) |

When no receipt exists for a PO, received_qty = 0.

### Invoice exception codes

Determine which codes apply to an invoice review:

| Code | Condition |
|------|-----------|
| INVOICE_QTY_EXCEEDS_RECEIPT | billed_qty > received_qty |
| PARTIAL_RECEIPT | received_qty < ordered_qty |
| PRICE_MISMATCH | invoice unit_price != PO unit_price or invoice unit_price != contract unit_price |
| DAMAGE_REJECTION | Any receipt line on the invoice's PO has quantity_rejected > 0 |
| SUPPLIER_WATCH_RISK | Supplier risk_rating is watch or high and has at least one open risk event |
| NO_EXCEPTION | None of the above conditions are met |

### Financials for receiving/invoice review

| Metric | Formula |
|--------|---------|
| received_goods_value | received_qty * po_unit_price |
| unreceived_goods_value | (ordered_qty - received_qty) * po_unit_price |
| invoice_subtotal | From the invoice record |
| invoice_freight | From the invoice record |
| invoice_tax | From the invoice record |
| invoice_total | invoice_subtotal + invoice_freight + invoice_tax |

---

## AP Payment-Hold Reconciliation

### Invoice decision fields

| Metric | Formula |
|--------|---------|
| quantity_billed | invoice.lines[].quantity_billed |
| quantity_received | Sum of all receipt lines[].quantity_received on this PO (0 if no receipt) |
| quantity_variance | quantity_billed - quantity_received |
| quantity_variance_pct | (quantity_variance / PO.lines[].quantity) * 100, rounded to 1 decimal |
| scheduled_payment_amount | Sum of amounts from /ap/payments where invoice_id matches and scheduled_date <= the review horizon (default: 30 days from close_date) |
| net_balance_impact | invoice_total - scheduled_payment_amount |

For invoices that link to a specific receipt via receipt_id, only use that
receipt's quantities. For invoices where receipt_id is null but a receipt on
the same PO exists, use the most recent receipt's quantities.

### Hold or release decision

An invoice is RELEASE when ALL of:
- invoice.status is approved (fully matched, no holds)
- quantity_variance == 0
- Three-way match is verified (PO, receipt, invoice quantities align)

An invoice is HOLD when ANY of:
- invoice.status is on_hold or pending_receipt
- quantity_variance != 0
- No receipt exists (missing three-way match)

### Reason codes per invoice

| Code | Condition |
|------|-----------|
| APPROVED_THREE_WAY_MATCH | status is approved and quantities match |
| NO_RECEIPT | receipt_id is null on invoice |
| QTY_VARIANCE | quantity_billed != quantity_received |
| SCHEDULED_PAYMENT_FOUND | At least one payment exists for this invoice |

### Vendor balance

Per supplier, within the close slice only:

| Metric | Formula |
|--------|---------|
| opening_balance | 0.00 (the close slice treats the opening as zero for target suppliers) |
| invoice_total | Sum of invoice totals for this supplier in the slice |
| scheduled_payments | Sum of payment amounts for this supplier's invoices in the slice |
| held_invoice_total | Sum of totals for invoices with hold_decision == HOLD |
| releasable_invoice_total | Sum of totals for invoices with hold_decision == RELEASE |
| close_balance | opening_balance + invoice_total - scheduled_payments |
| balance_status | FULLY_SCHEDULED if close_balance == 0, OPEN_APPROVED if hold_decision all RELEASE, OPEN_HELD otherwise |

### Program summary

Group invoices by program_id. Compute per program:
- invoice_count: number of invoices
- invoice_total: sum of invoice totals
- held_total: sum of invoice totals where hold_decision == HOLD
- released_total: sum of invoice totals where hold_decision == RELEASE
- net_close_balance: held_total

### Payment queues

- payment_hold_queue: invoice_ids where hold_decision == HOLD, sorted ascending
- payment_release_queue: invoice_ids where hold_decision == RELEASE, sorted ascending

### Total close balance

Sum of net_close_balance across all programs (i.e. total held amount).

---

## Contract Change Control

### Contract ceiling computation

| Metric | Formula |
|--------|---------|
| noncancelled_subtotal | Sum of subtotals of all POs referencing this contract_id where PO status != cancelled |
| headroom_before_change | ceiling_amount - noncancelled_subtotal |
| requested_subtotal | requested_incremental_quantity * contract.unit_price |
| headroom_after_change | headroom_before_change - requested_subtotal |
| ceiling_ok | true if headroom_after_change >= 0 |

### Program budget computation

| Metric | Formula |
|--------|---------|
| remaining_budget | budget_cap - committed_amount |
| requested_tax | requested_subtotal * (tax_rate_percent / 100), rounded to cents |
| requested_total | requested_subtotal + requested_tax (+ freight only if memo provides freight) |
| budget_after_change | remaining_budget - requested_total |
| budget_ok | true if budget_after_change >= 0 |
| max_quantity_with_current_budget | floor(remaining_budget / (contract.unit_price * (1 + tax_rate_percent/100))) |

Use the budget_snapshot with the most recent snapshot_date <= the memo_date.
If multiple snapshots exist for the program, use the latest.

### Approval check

Query /approvals for all events where object_id = source_requisition_id.
Find the latest event (by event_date). An approval is OK only when the
latest action is approved. Actions like submitted, returned, or
rejected are not approved.

### Supplier risk check

A supplier is risk-ok when:
- supplier.status is active (quality_hold or inactive suppliers are not ok)

Unless the business controls explicitly list watch as context-only and only
severe open matters, treat the supplier as risk-ok when there are no open
severe (high or critical) risk events. When the controls say
supplier_watch_rating is context only unless an open severe event is found,
a watch rating alone does not block.

### Decision

Use the first matching rule:

| Condition | Decision |
|-----------|----------|
| Contract not found, wrong supplier, or wrong SKU | reject_contract_mismatch |
| budget_ok == false AND approval_ok == false | hold_for_budget_and_approval |
| budget_ok == false | hold_for_budget |
| approval_ok == false | hold_for_approval |
| supplier_risk_ok == false | hold_for_supplier_risk |
| All checks pass | release_amendment |

---

## Sourcing Nomination Readiness

### Program budget headroom

headroom = budget_cap - committed_amount (from /programs, not /budget_snapshots
unless snapshots are explicitly requested)

### Readiness per nomination line

For each line, compute blocker_codes from:

| Blocker | Condition |
|---------|-----------|
| missing_contract | PO.contract_id is null |
| supplier_watch | Supplier risk_rating is watch |
| open_supplier_risk | Supplier has at least one open or monitoring risk event (status != closed) |
| ap_hold | At least one invoice on the PO has status on_hold |
| pending_receipt | At least one invoice on the PO has status pending_receipt or the PO has zero receipts |
| late_due_date | PO due_date < as_of_date |

If no blockers: blocker_codes = [none].

### Readiness status

| Status | Condition |
|--------|-----------|
| ready | 0 blockers |
| at_risk | 1-2 blockers, none from: late_due_date, pending_receipt |
| not_ready | 3+ blockers OR any of: late_due_date, pending_receipt |

### Nomination decision

| Decision | Condition |
|----------|-----------|
| nominate | readiness_status == ready |
| conditional_nomination | readiness_status == at_risk |
| hold | readiness_status == not_ready |

### Committee action

- nominate_now_supplier_ids: supplier IDs with nominate decisions
- conditional_supplier_ids: supplier IDs with conditional_nomination decisions
- hold_supplier_ids: supplier IDs with hold decisions
- send_to_committee: yes if overall_readiness is ready; otherwise no
- next_owner: the function most needed to resolve blockers -- buyer if
  missing_contract, finance_ops if budget, quality_ops if supplier risk,
  program_owner if late_due_date, ap_team if ap_hold or pending_receipt

---

## AP Release & Exception Review

### Release decision per invoice

| Decision | Primary Reason | Condition |
|----------|---------------|-----------|
| release_net_after_approved_chargeback | approved_qty_chargeback or approved_ap_quantity_variance | Invoice has an approved chargeback that covers the variance; net the release amount |
| hold_pending_quality_chargeback | inspection_hold_pending_chargeback | Chargeback status is pending_quality_review |
| hold_missing_receipt | no_receipt_on_po | No receipt exists for the invoice's PO |

### Net release amount

net_release_amount = invoice_total - approved_chargeback_amount
(but 0.00 for hold decisions)

### Receiving exceptions per receipt

| Exception | Condition |
|-----------|-----------|
| Underage Quantity | received_qty < ordered_qty |
| Severe Unmatched Quantity | received_qty is significantly below ordered_qty (e.g., < 50%) or the receipt is flagged |
| Inspection Hold | receipt status is inspection_hold |
| AP Quantity Variance | billed_qty != received_qty on an invoice linked to this receipt |
| No exceptions | receipt status is accepted or accepted_with_note with matched quantities |

Resolution status:
- net_release_ready: all chargebacks approved
- hold_for_quality_review: chargeback pending quality review
- accepted_no_receiving_exception: no exception codes
- missing_receipt: no receipt exists for the PO

### Sources authority

When a chargeback register exists in the local payload:
- The register is authoritative for chargeback amounts and statuses.
- Use it to determine approved_chargeback_amount and pending_chargeback_amount
  per invoice.
- Chargeback amounts from the register override any computed variance amounts.

When the task provides a stale alias note (like po73xx_alias_note), it is
supporting-only context; do not use it to fabricate IDs or override real API
data.

---

## General financial conventions

- All USD amounts: round to 2 decimal places (cents).
- Ratios (receipt_completion_ratio): round to 4 decimal places.
- Percentages (quantity_variance_pct): round to 1 decimal place.
- Use Python's built-in round() which implements banker's rounding; for
  half-up cents, use Decimal or add 0.001 before rounding.
- Tax computation: round(subtotal * (rate / 100), 2).
- When computing total from component parts, sum the rounded components,
  don't recompute from raw.

## List ordering conventions

- Sets (unordered in template): sort ascending unless template says otherwise.
- The template's ordering field is authoritative: follow it exactly.
- When the template says ordering: set; evaluator sorts values, sort
  ascending.
