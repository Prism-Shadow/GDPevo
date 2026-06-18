# Exception / blocker code decision tables

These tables encode the verified mapping between record facts and the controlled
codes the templates ask for. The codes' exact spelling comes from the template's
`allowed_values`; use whatever set that template lists.

## Receiving exception codes (per receipt vs its PO line)

Let `ordered` = PO line quantity, `received` = receipt line `quantity_received`,
`billed` = invoice line `quantity_billed`.

| Condition | Code(s) emitted |
|---|---|
| `received < ordered` (any shortfall) | `Underage Quantity` |
| Receiving shortfall is **material** (≥ ~10% of ordered, or a large absolute gap) | `Severe Unmatched Quantity` **in addition to** `Underage Quantity` |
| Receipt `status == inspection_hold` (or chargeback `pending_quality_review`) | `Inspection Hold` |
| `billed > received` but **no ordered-vs-received shortfall** (`received == ordered`) | `AP Quantity Variance` (NOT severe-unmatched) |
| No issues | (no codes / `NO_EXCEPTION`) |

### Verified threshold evidence (why ~10% counts as severe)
- Short 24 of 240 (10.0%) → emitted **both** `Underage Quantity` AND
  `Severe Unmatched Quantity`.
- Short 99 of 291 (34.0%) → emitted **both** as well.
- Received 88 of 88 (0% short) with billed 92 → emitted **only**
  `AP Quantity Variance` (no underage, no severe).

So: a genuine receiving shortfall ≥ ~10% of ordered is "severe". A pure
over-bill with a fully received line is just an AP quantity variance. The blind
pass's error was emitting only `Underage Quantity` at 10–34% short and missing
`Severe Unmatched Quantity`. When in doubt on a shortfall ≥ 10%, include both.

### Receiving resolution_status
| Situation | resolution_status |
|---|---|
| Approved chargeback, receipt accepted | `net_release_ready` |
| Inspection hold / pending-quality chargeback | `hold_for_quality_review` |
| Clean receipt, no exception | `accepted_no_receiving_exception` |
| No receipt exists on the PO | `missing_receipt` (use receipt_id sentinel `MISSING:<po_id>`, not null) |

## AP invoice review exception codes

| Condition | Code |
|---|---|
| `billed > received` (with a receipt) | `INVOICE_QTY_EXCEEDS_RECEIPT` |
| `received < ordered` (line not fully received) | `PARTIAL_RECEIPT` |
| Supplier `risk_rating == watch` | `SUPPLIER_WATCH_RISK` |
| PO/contract/invoice unit prices disagree | `PRICE_MISMATCH` |
| `quantity_rejected > 0` | `DAMAGE_REJECTION` |
| none of the above | `NO_EXCEPTION` |

## Nomination blocker codes (per line, as of as_of_date)

| Blocker | Fires when |
|---|---|
| `missing_contract` | PO `contract_id` is null / no active commercial basis for the sku |
| `supplier_watch` | supplier `risk_rating == watch` (context-only rating) |
| `open_supplier_risk` | ≥1 vendor_risk_event open/monitoring, `event_date ≤ as_of` |
| `ap_hold` | ≥1 in-scope invoice with status **`on_hold`** (NOT `pending_receipt`) |
| `pending_receipt` | **ZERO** receipts on the PO as of as_of (partial receipt does NOT fire this) |
| `late_due_date` | PO `due_date < as_of` while still unfulfilled |
| `none` | no blockers |

Sort blocker lists ascending unless the template says "set". The two traps:
`ap_hold` needs status `on_hold` (a `pending_receipt`/`NO_RECEIPT` invoice is an
*exception id* but not an `ap_hold`); `pending_receipt` needs **no** receipt at
all (a partial accepted receipt is evidence, not a pending-receipt blocker).

## AP close / release decision and reason codes

### Close (hold/release) — `invoice_decisions`
| Invoice status | hold_decision | release_to_payment | quantity reason |
|---|---|---|---|
| `approved` | `RELEASE` | true | `APPROVED_THREE_WAY_MATCH` |
| `on_hold` (QTY_VARIANCE) | `HOLD` | false | `QTY_VARIANCE` |
| `pending_receipt` / `NO_RECEIPT` | `HOLD` | false | `NO_RECEIPT` (sole qty reason) |
Add `SCHEDULED_PAYMENT_FOUND` when a payment matches invoice id and
`scheduled_date ≤ cutoff`. Reason lists sorted alphabetically.

### Release file — `release_decisions`
| Situation | decision | primary_reason |
|---|---|---|
| Approved Underage chargeback | `release_net_after_approved_chargeback` | `approved_qty_chargeback` |
| Approved AP-quantity-variance chargeback | `release_net_after_approved_chargeback` | `approved_ap_quantity_variance` |
| Pending-quality chargeback / inspection hold | `hold_pending_quality_chargeback` | `inspection_hold_pending_chargeback` |
| No receipt on PO | `hold_missing_receipt` | `no_receipt_on_po` |

Chargeback amount = `basis_quantity × unit_cost` (local register is
authoritative). `net_release_amount = invoice_total − approved_chargeback_amount`
for releases, else 0. Pending chargebacks populate `pending_chargeback_amount`
only.

## Vendor balance_status
| Condition | balance_status |
|---|---|
| close_balance ≈ 0 because fully scheduled within cutoff | `FULLY_SCHEDULED` |
| held, unscheduled, balance open | `OPEN_HELD` |
| approved/releasable but not yet scheduled | `OPEN_APPROVED` |

## Change-control decision (amendment file)
Decision is driven by which checks fail (each independent):
- contract `ceiling_ok` false ⇒ contract-mismatch family.
- `budget_ok` false ⇒ `hold_for_budget`.
- `approval_ok` false ⇒ `hold_for_approval`.
- both budget+approval fail ⇒ `hold_for_budget_and_approval`.
- open **severe** supplier risk ⇒ `hold_for_supplier_risk` (watch alone does not).
- all pass ⇒ `release_amendment`.
`blocker_count` = number of failing checks; `ready_to_release` = (count == 0).
`required_actions` map one-to-one to the failed checks, sorted ascending:
`obtain_final_requisition_approval`, `raise_budget_exception_or_reduce_quantity`,
`resolve_supplier_risk_hold`, or `none`.
