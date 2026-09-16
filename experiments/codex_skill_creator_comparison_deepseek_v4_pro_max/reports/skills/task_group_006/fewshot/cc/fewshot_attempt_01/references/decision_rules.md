# ProcureOps Decision Rules

Operational rules that transform raw API data into analyst decisions.
Apply these in the order presented; later rules refine earlier ones.

---

## 1. Sourcing Nomination Readiness

A **nomination line** evaluates whether a supplier-SKU pair is ready for
committee release.  For each target SKU:

### 1a. Identify the supplier

Use the PO that matches the target requisition and SKU.  The PO's
`supplier_id` is the nominated supplier.  If multiple POs exist for the
same requisition-SKU pair, use the one named in the memo; if not named,
use the most recent non-cancelled PO by `order_date`.

### 1b. Commercial basis

If the PO has a non-null `contract_id`, that contract is the commercial
basis.  Otherwise `commercial_basis_id` is `null` and the line gets a
`missing_contract` blocker.

### 1c. Receipt evidence

Collect all receipts whose `po_id` matches the target PO and whose
`receipt_date` is on or before the as-of date.  The receipt IDs form the
`receipt_evidence_ids` list.  An empty list means no goods have been
received — this produces a `pending_receipt` blocker.

### 1d. Invoice exceptions

Collect all invoices whose `po_id` matches the target PO and whose
`invoice_date` is on or before the as-of date.  Invoices with status
`on_hold` or `pending_receipt` are exceptions (include their IDs in
`invoice_exception_ids`).  Any `on_hold` invoice also produces an
`ap_hold` blocker.

### 1e. Supplier risk

Pull all vendor risk events for the supplier whose status is `open` or
`monitoring` and whose `event_date` is on or before the as-of date.
Include their IDs in `risk_event_ids`.

Risk-driven blockers:
- If any open event exists (regardless of severity): `open_supplier_risk`.
- If the supplier's `risk_rating` is `watch` or `high` (even without
  open events): `supplier_watch`.

### 1f. Due-date check

If the PO's `due_date` is before the as-of date and the PO status is
not `received` or `closed`: `late_due_date`.

### 1g. Blockers and readiness

| Condition | Blocker code |
|-----------|-------------|
| No contract on PO | `missing_contract` |
| Supplier rating watch/high, no open severe | `supplier_watch` |
| Any open risk event for supplier | `open_supplier_risk` |
| Any on-hold invoice for this PO | `ap_hold` |
| No receipt exists for this PO before as-of | `pending_receipt` |
| PO due-date past as-of, not received/closed | `late_due_date` |
| No blockers | `none` |

**Readiness status:**
- `ready`: no blockers, or only `none`.
- `at_risk`: blockers like `supplier_watch` or `ap_hold` that are
  mitigable — the line can be conditionally nominated.
- `not_ready`: blockers like `missing_contract`, `open_supplier_risk`,
  `late_due_date`, or `pending_receipt` — the line must be held.

**Nomination decision:**
- `nominate`: readiness is `ready`.
- `conditional_nomination`: readiness is `at_risk`.
- `hold`: readiness is `not_ready`.

### 1h. Committee action

- `nominate_now_supplier_ids`: suppliers with at least one `nominate` line.
- `conditional_supplier_ids`: suppliers with `conditional_nomination` only.
- `hold_supplier_ids`: suppliers with `hold` only.
- `next_owner`: which team owns the next step based on the dominant
  blocker (`ap_team` for AP holds, `buyer` for missing contracts,
  `quality_ops` for risk events, `finance_ops` for budget issues,
  `program_owner` otherwise).
- `send_to_committee`: `"yes"` only if at least one line is `nominate`;
  otherwise `"no"`.

### 1i. Program summary

- `budget_headroom_usd` = snapshot `budget_cap` minus `committed_amount`
  for the target program, from the latest snapshot on or before the
  as-of date.
- `overall_readiness`: lowest readiness of any line (`ready` if all
  ready, `at_risk` if any at_risk and none not_ready, `not_ready`
  otherwise).

---

## 2. Receiving-Control Closeout

Given a target receipt (batch) ID:

### 2a. Inspection summary

Pull the receipt, its PO, the PO's program, supplier, and warehouse.
Fields come directly from the receipt and related records.

### 2b. Line reconciliation

For each PO line:
- `ordered_qty` = PO line `quantity`.
- `received_qty` = sum of `quantity_received` across all receipts for
  this PO line on or before the review date.
- `rejected_qty` = sum of `quantity_rejected` across those receipts.
- `billed_qty` = sum of `quantity_billed` across all invoices for this
  PO line on or before the review date.
- `short_qty_vs_po` = `ordered_qty - received_qty` (positive means
  shortfall).
- `unreceived_billed_qty` = `billed_qty - received_qty` (positive means
  billed for goods not received).
- `receipt_completion_ratio` = `received_qty / ordered_qty` (rounded to
  4 decimal places).
- `contract_price_match`: true when the contract (if any) has the same
  `unit_price` as the PO and the invoice line.

### 2c. Invoice review

For the invoice tied to the receipt:
- `invoice_id`, `invoice_status`, `hold_code` come from the invoice.
- `receipt_status` = the receipt's `status`.
- `po_status` = the PO's `status`.

Exception codes (add all that apply):
| Condition | Code |
|-----------|------|
| billed_qty > received_qty for any line | `INVOICE_QTY_EXCEEDS_RECEIPT` |
| received_qty < ordered_qty for any line | `PARTIAL_RECEIPT` |
| supplier risk_rating is watch or higher | `SUPPLIER_WATCH_RISK` |
| invoice unit_price != PO unit_price (or contract unit_price if fixed) | `PRICE_MISMATCH` |
| any rejection (rejected_qty > 0) | `DAMAGE_REJECTION` |
| None of the above | `NO_EXCEPTION` |

### 2d. Financials

- `received_goods_value` = `received_qty * po_unit_price` (summed across
  lines).
- `unreceived_goods_value` = `(ordered_qty - received_qty) * po_unit_price`.
- `invoice_subtotal`, `invoice_freight`, `invoice_tax`, `invoice_total`
  come from the invoice.

### 2e. Decision

Based on the exception set:

**Batch disposition:**
- `accept_partial_hold_variance`: partial receipt with invoice > receipt,
  but supplier risk is not critical — release with chargeback.
- `release_full_invoice`: no exceptions — pay in full.
- `reject_batch`: severe quality issues or critical supplier risk.
- `manual_recount_required`: inspection hold with discrepancies.

**AP action:**
- `keep_invoice_on_hold`: any unresolved exception.
- `release_invoice`: all exceptions resolved or nettable.
- `void_invoice`: irreconcilable (rare — usually severe damage or fraud).

**Receiving action:**
- `record_shortage_follow_up`: under-received relative to PO.
- `no_receiving_action`: fully received with no issues.
- `reject_all_units`: quality rejection needed.

**Supplier action:**
- `request_credit_or_remaining_delivery`: when billed > received.
- `no_supplier_action`: no variance.
- `supplier_debit_for_damage`: damage rejection exists.

---

## 3. AP Close-Desk Reconciliation

For a named set of invoices as of a close date:

### 3a. Opening-balance rule

Unless the task provides an explicit opening balance, use `0.00 USD` for
each supplier in the slice.  The task's close memo is the authority.

### 3b. Invoice-level decision

For each target invoice:
- `hold_decision`: `"RELEASE"` if invoice status is `approved` with no
  quantity or receipt problems; otherwise `"HOLD"`.
- `release_to_payment`: `true` only when `hold_decision` is `"RELEASE"`.
- `quantity_billed` = sum of invoice line `quantity_billed`.
- `quantity_received` = sum of `quantity_received` from receipts for the
  same PO.  Use `0.00` when no receipt exists.
- `quantity_variance` = `quantity_billed - quantity_received`.
- `quantity_variance_pct` = `(quantity_variance / PO line quantity) *
  100`, rounded to 1 decimal.
- `scheduled_payment_amount` = sum of payment amounts for this invoice
  with status `scheduled` or `released` and `scheduled_date` on or before
  the task's payment horizon (default 2026-06-30).
- `net_balance_impact` = `invoice_total - scheduled_payment_amount`.

Reason codes (add all that apply):
| Condition | Code |
|-----------|------|
| Three-way match passes (qty match + price match + receipt exists) | `APPROVED_THREE_WAY_MATCH` |
| No receipt exists for the PO | `NO_RECEIPT` |
| billed_qty != received_qty | `QTY_VARIANCE` |
| A payment is scheduled for this invoice | `SCHEDULED_PAYMENT_FOUND` |

### 3c. Vendor balances

Group invoices by supplier.  For each supplier:
- `opening_balance` = from task memo (default 0.00).
- `invoice_total` = sum of all target invoice totals.
- `scheduled_payments` = sum of scheduled payment amounts.
- `held_invoice_total` = sum of totals where `hold_decision` is `"HOLD"`.
- `releasable_invoice_total` = sum of totals where `hold_decision` is
  `"RELEASE"`.
- `close_balance` = `opening_balance + invoice_total - scheduled_payments`.
- `balance_status`:
  - `"FULLY_SCHEDULED"`: close_balance == 0.
  - `"OPEN_APPROVED"`: close_balance > 0 and all invoices are releasable.
  - `"OPEN_HELD"`: close_balance > 0 and some invoices are held.

### 3d. Program summary

Group by program.  For each:
- `invoice_count`, `invoice_total`, `held_total`, `released_total`.
- `net_close_balance` = `held_total` (released invoices are already paid
  or scheduled, so they don't contribute to open balance).

### 3e. Queues and totals

- `payment_hold_queue`: invoice IDs where `hold_decision` is `"HOLD"`
  (sorted ascending).
- `payment_release_queue`: invoice IDs where `hold_decision` is
  `"RELEASE"` (sorted ascending).
- `total_close_balance` = sum of `close_balance` for all suppliers.

---

## 4. Change-Control Decision

For a modular change request against a contract:

### 4a. Contract check

- Pull the contract by ID.  Verify `status` is `active`.
- `unit_price` from the contract (for `fixed` contracts this is
  authoritative).
- `ceiling_amount` from the contract.
- `noncancelled_subtotal`: sum PO `subtotal` for all POs referencing the
  contract where `status != "cancelled"`.
- `headroom_before_change` = `ceiling_amount - noncancelled_subtotal`.
- `requested_subtotal` = `requested_quantity * contract_unit_price`.
- `headroom_after_change` = `headroom_before_change - requested_subtotal`.
- `ceiling_ok`: true when `headroom_after_change >= 0`.

### 4b. Budget check

- Use the latest budget snapshot for the program.
- `budget_cap`, `committed_amount`, `remaining_budget` =
  `budget_cap - committed_amount`.
- `requested_tax` = `requested_subtotal * tax_rate` (tax rate from the
  change memo, typically 7.25%).
- `requested_total` = `requested_subtotal + requested_tax` (add freight
  only if the memo provides a freight amount).
- `budget_after_change` = `remaining_budget - requested_total`.
- `budget_ok`: true when `budget_after_change >= 0`.
- `max_quantity_with_current_budget` = floor of
  `remaining_budget / (unit_price * (1 + tax_rate))`.

### 4c. Approval check

- Find the latest approval event for the source requisition by
  `event_date`.
- `latest_action` from that event.  If it is `"submitted"`, the
  requisition is not yet approved (`approval_ok = false`).
  If `"approved"`, `approval_ok = true`.

### 4d. Supplier risk check

- Pull supplier by ID, check `status` and `risk_rating`.
- Collect open risk events for the supplier (`status == "open"` or
  `"monitoring"`).
- `severe_open_event_ids`: events with severity `"high"` or `"critical"`.
- `supplier_risk_ok`: true when there are zero `severe_open_event_ids`
  and the supplier status is not `quality_hold`.

### 4e. Decision

Combine all checks:
| Condition | Decision |
|-----------|----------|
| Contract mismatch (wrong supplier, SKU, or expired) | `reject_contract_mismatch` |
| Budget failed, approval failed | `hold_for_budget_and_approval` |
| Budget failed only | `hold_for_budget` |
| Approval failed only | `hold_for_approval` |
| Supplier risk failed only | `hold_for_supplier_risk` |
| All checks pass | `release_amendment` |

### 4f. Required actions

A list of action codes based on failing checks:
- Approval failed: `"obtain_final_requisition_approval"`.
- Budget failed: `"raise_budget_exception_or_reduce_quantity"`.
- Supplier risk failed: `"resolve_supplier_risk_hold"`.
- All pass: `"none"`.
Sort the list ascending.

### 4g. Summary

- `blocker_count`: number of failing checks.
- `currency`: `"USD"`.
- `ready_to_release`: `true` only when `blocker_count == 0`.

---

## 5. Receiving/AP Exception Release

Given a local packet with target POs, receipts, invoices, and an optional
chargeback register:

### 5a. Authoritative sources

The API is the system of record for POs, receipts, and invoices.
The local chargeback register (in the packet) is the authoritative source
for approved or pending chargeback amounts.  The packet's release
request notes are supporting context only — do not use them to override
API data.

### 5b. For each target invoice

1. Find the matching PO, then all receipts for that PO.
2. Determine which receipts are in scope:
   - The receipt named in the invoice's `receipt_id` field.
   - Any other receipt from the same PO that is referenced in the
     chargeback register for this invoice.
   - A receipt whose `receipt_date` is on or before the review as-of date.
3. `excluded_same_po_receipt_ids`: any receipt for the same PO that is
   NOT in scope (e.g., belongs to a different invoice, later date, or is
   irrelevant to this review).  Include only receipts that actually exist
   in the API — do not fabricate IDs.

**Decision:**
| Condition | Decision | Primary Reason |
|-----------|----------|----------------|
| Approved chargeback exists for qty variance | `release_net_after_approved_chargeback` | `approved_qty_chargeback` |
| Approved AP qty variance chargeback exists | `release_net_after_approved_chargeback` | `approved_ap_quantity_variance` |
| No receipt exists for the PO | `hold_missing_receipt` | `no_receipt_on_po` |
| Chargeback is pending quality review | `hold_pending_quality_chargeback` | `inspection_hold_pending_chargeback` |

**Dollar amounts:**
- `invoice_total`: from the API invoice.
- `approved_chargeback_amount`: sum of chargeback entries in the local
  register for this invoice with status `"approved"`.  Each entry's value
  = `basis_quantity * unit_cost`.
- `pending_chargeback_amount`: sum for status `"pending_quality_review"`.
- `net_release_amount`: `invoice_total - approved_chargeback_amount` when
  releasing; `0.00` when holding.
  Round to cents after each computation.

### 5c. Receiving exceptions

For each receipt in scope:
- `exception_codes`: based on the receipt and chargeback data.
  - `"Underage Quantity"`: received < PO ordered and a qty chargeback exists.
  - `"Severe Unmatched Quantity"`: the shortfall is large (e.g., > 10% of
    PO quantity) or the receipt is on inspection hold with variance.
  - `"Inspection Hold"`: receipt status is `inspection_hold`.
  - `"AP Quantity Variance"`: invoice billed != received.
- `chargeback_status`: from the local register (`"approved"`,
  `"pending_quality_review"`, or `"not_applicable"`).
- `resolution_status`:
  - `"net_release_ready"`: approved chargeback covers the shortfall.
  - `"hold_for_quality_review"`: pending chargeback or inspection hold.
  - `"accepted_no_receiving_exception"`: no issues.
  - `"missing_receipt"`: (use receipt ID `MISSING:<po_id>`) when no
    receipt exists.

### 5d. Summary

- `release_invoice_ids`: invoices with a release decision.
- `hold_invoice_ids`: invoices with a hold decision.
- `approved_chargeback_total`: sum of all approved chargebacks.
- `pending_chargeback_total`: sum of all pending chargebacks.
- `net_release_total`: sum of `net_release_amount` for release decisions.
- `authoritative_sources`: list the sources that drove decisions (always
  include the API endpoints used and `local_chargeback_register`).
- `supporting_only_sources`: sources that provided context but not the
  primary decision basis (e.g. `ap_release_request_note`).
- `followup_actions`: one action per unresolved issue
  (e.g. `ask_receiving_for_vantix_receipt`,
  `route_po00031_quality_review`, `post_approved_chargeback_netting`).

---

## General rules

### Set ordering
When a template says an evaluator treats a list as a set (no inherent
order), always sort the values ascending (alphabetically for strings,
numerically for numbers) in your output.  This ensures deterministic
matching.

### Date cutoffs
When the prompt or a local memo specifies an as-of date, only include
records whose date is on or before that date.  Specifically:
- Receipts: `receipt_date <= as_of_date`.
- Invoices: `invoice_date <= as_of_date`.
- Risk events: `event_date <= as_of_date`.
- Payments: `scheduled_date <= horizon_date` (the horizon is the as-of
  date or an explicit end-of-month like 2026-06-30).
- Approval events: always pull the latest by `event_date` regardless of
  cutoff — the latest event represents the current state.

### Contract price authority
When a contract is `fixed`, the contract's `unit_price` is the benchmark
for price matching.  When `variable`, the PO unit price is the benchmark.
When no contract exists, compare invoice price to PO price.

### Cancelled POs
Always exclude `cancelled` POs from contract ceiling computation and
from budget committed-amount calculations.  Include `open`, `confirmed`,
`partial_receipt`, `received`, and `closed` POs.

### Receipt aggregation
When multiple receipts exist for the same PO line, sum their
`quantity_received` and `quantity_rejected`.  Do not double-count receipts
that postdate the as-of cutoff.

### Payment horizon
For AP close tasks, use the last day of the month containing the close
date (e.g., 2026-06-30 for a 2026-06-01 close date) as the payment
horizon, unless the task explicitly says otherwise.
