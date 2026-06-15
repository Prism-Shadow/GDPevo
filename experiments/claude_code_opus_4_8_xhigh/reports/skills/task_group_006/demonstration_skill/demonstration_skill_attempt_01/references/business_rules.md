# ProcureOps business rules & derived computations

These are the transferable formulas and decision tables. They are derived from
the data model, not from any one task's answer — apply them to whatever anchors
a new task names.

## 1. Money & rounding
- Use the record's own `total / subtotal / tax / freight` fields verbatim; they
  are authoritative and already rounded. Only compute when the template asks for
  a value the record does not store (variance, headroom, netting).
- Round money to 2 decimals. `receipt_completion_ratio` → 4 decimals.
  `quantity_variance_pct` → 1 decimal. Quantities are integers in the data but a
  template may ask you to emit them as `x.00`.

## 2. Budget headroom (program)
```
remaining_budget = budget_cap − committed_amount
```
Source from the program record or its budget snapshot (`BUD-<program_id>`); they
agree. Do NOT subtract pending_invoice_amount.

`budget_after_change = remaining_budget − requested_total`, where
`requested_total = requested_subtotal + requested_tax` (+ freight only if the
memo supplies freight). `requested_tax = requested_subtotal × tax_rate`.
`budget_ok = budget_after_change >= 0`.

`max_quantity_with_current_budget = floor(remaining_budget / (unit_price ×
(1 + tax_rate)))` — the largest integer quantity whose subtotal+tax still fits
in remaining budget.

## 3. Contract ceiling headroom
```
noncancelled_subtotal = Σ subtotal over POs on the contract where status != "cancelled"
headroom_before_change = ceiling_amount − noncancelled_subtotal
requested_subtotal     = requested_quantity × contract.unit_price
headroom_after_change  = headroom_before_change − requested_subtotal
ceiling_ok             = headroom_after_change >= 0
```
Get the POs with `/purchase_orders?contract_id=<id>`. `included_po_ids` = the
non-cancelled ones (sorted); `excluded_cancelled_po_ids` = the cancelled ones.

## 4. Quantity / price reconciliation (PO line ↔ receipts ↔ invoice)
For each PO line:
```
ordered_qty   = PO line.quantity
received_qty   = Σ receipt line.quantity_received over in-scope receipts of that PO line
rejected_qty   = Σ receipt line.quantity_rejected
billed_qty     = Σ invoice line.quantity_billed
short_qty_vs_po       = ordered_qty − received_qty
unreceived_billed_qty = max(0, billed_qty − received_qty)
receipt_completion_ratio = round(received_qty / ordered_qty, 4)
quantity_variance     = billed_qty − received_qty
quantity_variance_pct = round(quantity_variance / ordered_qty × 100, 1)
```
Prices: `po_unit_price` from PO line, `contract_unit_price` from contract,
`invoice_unit_price` from invoice line. `contract_price_match =
(invoice_unit_price == contract_unit_price)` (and PO price too when relevant).
If no receipt exists: received_qty = 0, variance = billed, pct = 100.0.

Financials (receiving task):
```
received_goods_value   = received_qty × po_unit_price
unreceived_goods_value = unreceived_billed_qty × po_unit_price
invoice_subtotal/freight/tax/total = the invoice record's own fields
```

## 5. Vendor risk "open as of date"
```
open_events = [e for e in risk_events(supplier)
               if e.status in {open, monitoring} and e.event_date <= as_of]
severe_open = [e for e in open_events if e.severity == "high"]
supplier_risk_ok = (no severe_open)   # a watch rating / medium open event is
                                      # context, not a hard block, unless the
                                      # template's blocker list says otherwise
has_open_supplier_risk = len(open_events) > 0
```
List event ids sorted ascending.

## 6. Approval gate
Fetch `/approval_events?object_id=<requisition_id>`. Take the latest by
event_date for `latest_event_id/action/actor/event_date`.
`approval_ok = (latest action == "approved")` — or the action is in the memo's
`approval_good_actions`. submitted/escalated/returned ⇒ not approved.

## 7. Scheduled-payment offset (AP close)
A payment reduces a supplier's close balance only if `payment.status` is
scheduled/released AND `scheduled_date <= cutoff` (memo's, e.g. month-end).
`scheduled_payment_amount` for an invoice = sum of its matching payments'
`amount`. `net_balance_impact = invoice_total − scheduled_payment_amount`.

## 8. Chargeback netting (AP release)
From the local chargeback register (supporting data; the API has no chargebacks):
```
amount(row) = basis_quantity × unit_cost
approved_chargeback_amount = Σ amount over rows with status == "approved"
pending_chargeback_amount  = Σ amount over rows with status in {pending_quality_review, ...}
net_release_amount = invoice_total − approved_chargeback_amount   (if releasable)
```
A pending chargeback forces a HOLD: net_release_amount = 0.

---

# Decision tables

## A. Nomination decision (per line)
Compute blocker_codes first, then map:
- `none` blockers → `nominate` / readiness `ready`.
- Only "soft" blockers (`supplier_watch`, and a single open non-severe risk that
  the desk tolerates) → `conditional_nomination` / `at_risk`.
- Any hard blocker (`missing_contract`, `pending_receipt`, `ap_hold`,
  `late_due_date`, severe `open_supplier_risk`) → `hold` / `not_ready`.

Blocker codes (emit the ones that apply, sorted ascending):
- `missing_contract` — PO has `contract_id == null` (no commercial basis).
- `supplier_watch` — supplier.risk_rating == "watch".
- `open_supplier_risk` — supplier has an open/monitoring risk event as of date.
- `ap_hold` — an invoice on the line is `on_hold` (or has a hold_code).
- `pending_receipt` — invoice/PO awaiting receipt, or no accepted receipt yet.
- `late_due_date` — PO due_date is past / inconsistent with need-by as of date.
- `none` — when nothing applies.

`commercial_basis_id` = the contract id if one exists, else null.

Committee roll-up: bucket selected suppliers into
`nominate_now / conditional / hold` by their worst line decision.
`send_to_committee = "yes"` only if at least one supplier is nominate-ready and
nothing program-level blocks; otherwise "no". `next_owner` = the team that owns
the top remaining blocker (ap_team for AP holds, quality_ops for quality holds,
buyer for missing contract, finance_ops for budget, program_owner otherwise).
`overall_readiness` = worst line readiness across the package.

## B. Receiving / AP reconciliation
`invoice_status`, `hold_code` come straight from the invoice record.
`receipt_status` from the receipt; `po_status` from the PO.
Exception codes (set; evaluator sorts) — include each that applies:
- `INVOICE_QTY_EXCEEDS_RECEIPT` — billed_qty > received_qty.
- `PARTIAL_RECEIPT` — received_qty < ordered_qty (po status partial_receipt).
- `SUPPLIER_WATCH_RISK` — supplier.risk_rating == "watch" / open risk.
- `PRICE_MISMATCH` — invoice_unit_price != contract_unit_price.
- `DAMAGE_REJECTION` — quantity_rejected > 0 / inspection variance.
- `NO_EXCEPTION` — only when none of the above.

Disposition mapping:
- short receipt + qty variance hold → `accept_partial_hold_variance`,
  ap `keep_invoice_on_hold`, receiving `record_shortage_follow_up`,
  supplier `request_credit_or_remaining_delivery`.
- clean three-way match → `release_full_invoice`, ap `release_invoice`,
  receiving `no_receiving_action`, supplier `no_supplier_action`.
- damage/rejection → `reject_batch` / supplier `supplier_debit_for_damage`.
- ambiguous counts → `manual_recount_required`.

## C. AP close hold/release (per invoice)
```
hold_decision = RELEASE if invoice.status == "approved" (clean 3-way match)
              else HOLD
release_to_payment = (hold_decision == RELEASE)
hold_code = invoice.hold_code (null when released)
```
reason_codes (alphabetical):
- `APPROVED_THREE_WAY_MATCH` — status approved, qty variance 0.
- `NO_RECEIPT` — no receipt / status pending_receipt.
- `QTY_VARIANCE` — billed != received.
- `SCHEDULED_PAYMENT_FOUND` — a qualifying scheduled payment exists.

Vendor balance: `close_balance = opening_balance + invoice_total −
scheduled_payments`. `balance_status` = FULLY_SCHEDULED (close_balance≈0 via
schedule), OPEN_HELD (held, unpaid), OPEN_APPROVED (approved, unscheduled).
Program/total roll-ups sum the per-invoice held/released figures. The hold and
release queues are the invoice ids in each bucket, sorted ascending.

## D. Change-control decision (single object)
Run the contract check (§3), budget check (§2), approval check (§6), supplier
risk check (§5). Then:
```
ceiling_ok & budget_ok & approval_ok & supplier_risk_ok      → release_amendment
contract mismatch (sku/price/contract not matching the buy)  → reject_contract_mismatch
!budget_ok & !approval_ok                                    → hold_for_budget_and_approval
!budget_ok only                                              → hold_for_budget
!approval_ok only                                            → hold_for_approval
severe open supplier risk                                    → hold_for_supplier_risk
```
required_actions (sorted; `none` if clear):
`raise_budget_exception_or_reduce_quantity` (budget fail),
`obtain_final_requisition_approval` (approval fail),
`resolve_supplier_risk_hold` (severe risk). `blocker_count` = number of failed
gates; `ready_to_release = (blocker_count == 0)`.

## E. AP release / chargeback netting (per invoice)
```
no receipt on PO                                  → hold_missing_receipt /
                                                    no_receipt_on_po, net 0,
                                                    receipt_id "MISSING:<po_id>"
receipt in inspection_hold + pending chargeback   → hold_pending_quality_chargeback /
                                                    inspection_hold_pending_chargeback, net 0
approved chargeback present                        → release_net_after_approved_chargeback /
                                                    approved_qty_chargeback or
                                                    approved_ap_quantity_variance,
                                                    net = invoice_total − approved_cb
```
`receipt_ids_in_scope` = the receipt(s) named/used; other receipts on the same
PO → `excluded_same_po_receipt_ids` (hold the duplicate for its own invoice).
Receiving exception codes per receipt (set): `Underage Quantity` (received <
ordered), `Severe Unmatched Quantity` (large shortfall / large chargeback
basis), `Inspection Hold` (receipt.status == inspection_hold), `AP Quantity
Variance` (billed > received with an AP-variance chargeback).
`resolution_status` ∈ {net_release_ready, hold_for_quality_review,
accepted_no_receiving_exception, missing_receipt}.

Summary source classification (when the template asks):
- `authoritative_sources`: the ProcureOps endpoints you used
  (procureops_po_records / _receipt_records / _ap_records) plus
  local_chargeback_register (the register IS authoritative for chargebacks —
  the API has none).
- `supporting_only_sources`: free-text request notes and stale alias notes
  (e.g. a "PO-73xx" alias that does not exist in the API). They never override
  API data; treat as context. When a memo's id is not in the API, use the
  available shared id it maps to and record the alias note as supporting-only.
