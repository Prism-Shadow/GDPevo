# ProcureOps AP Release & Change-Control Skill

## Overview

This skill covers tasks that interact with the ProcureOps API to produce structured JSON decisions for procurement workflows: AP release/hold files, receiving batch reviews, AP close reconciliations, change-control decisions, and nomination readiness packets.

## API Endpoints

The ProcureOps API exposes these endpoints (all return `{count, results}` list envelopes unless noted):

- `/programs` — program metadata including `budget_cap`, `committed_amount`, `owner`, `status`
- `/purchase_orders` — PO records with `lines[{quantity, unit_price, sku}]`, `status`, `contract_id`, `program_id`, `total`, `subtotal`
- `/purchase_requisitions` — requisition records with `status` (`draft` / `submitted` / `approved` / `converted` / `cancelled`), `sku`, `program_id`
- `/receipts` — receipt records with `lines[{quantity_received, quantity_rejected, inspection_status}]`, `status`, `po_id`, `receipt_date`
- `/ap_invoices` — invoice records with `lines[{quantity_billed, unit_price}]`, `status` (`on_hold` / `approved` / `pending_receipt` / `paid`), `hold_code`, `receipt_id`, `total`, `subtotal`, `freight`, `tax`
- `/payments` — payment records with `invoice_id`, `amount`, `status` (`scheduled` / `released` / `blocked`), `scheduled_date`
- `/contracts` — contract records with `sku`, `unit_price`, `ceiling_amount`, `status`, `program_id`, `supplier_id`
- `/budget_snapshots` — budget records with `budget_cap`, `committed_amount`, `pending_invoice_amount`, `program_id`, `snapshot_id`
- `/suppliers` — supplier records with `risk_rating` (`low` / `medium` / `watch` / `high`), `status`, `name`
- `/vendor_risk_events` — risk events with `supplier_id`, `severity` (`low` / `medium` / `high` / `critical`), `status` (`open` / `closed` / `monitoring`), `event_id`
- `/approval_events` — approval workflow events with `object_id`, `object_type`, `action`, `actor`, `event_date`, `event_id`

## Universal Conventions

1. **Task ID**: The JSON output `task_id` must be exactly `train_001` through `train_005` (or the equivalent test task ID). Do not use descriptive strings.
2. **Sorting**: Unless a template specifies otherwise, sort all ID lists ascending alphabetically. This includes `po_ids`, `receipt_ids`, `invoice_ids`, `supplier_ids`, `event_ids`.
3. **Temporal scope**: When a task specifies `as_of_date` or `review_as_of`, only count receipts/invoices/events whose dates are **on or before** that date. Receipts dated after the as-of date do not exist for that review.
4. **Rounding**: Currency amounts to 2 decimals. Percentages to the precision specified in the template (commonly 1 decimal for percentages, 4 for ratios).
5. **Opening balance rule**: For AP close-slice reconciliations that say "Treat the opening balance for target suppliers as 0.00 USD", use exactly `0.0`.
6. **Program scope**: When a task references a specific program (e.g., `PRG-AX17`), always query all records in that program even if the memo only highlights certain POs. Related POs for the same SKU in the same program must be included where the template asks for package or included POs.

## Task-Type Patterns

### 1. Nomination Readiness (train_001 style)

**Goal**: Determine whether SKU lines can proceed to committee nomination.

**Key logic**:
- Identify **all** POs for each target SKU in the program, not just the PO named in the memo.
- `commercial_basis_id` is the contract ID if a contract exists for that SKU/program; otherwise `null`.
- `receipt_evidence_ids`: receipts for those POs with `receipt_date <= as_of_date`.
- `invoice_exception_ids`: invoices for those POs that are `on_hold` or `pending_receipt` as of the review date.
- `risk_event_ids`: **open or monitoring** `vendor_risk_events` for the supplier as of the review date. Do not assume empty just because the supplier rating is `watch`; always check the risk event endpoint.
- `blocker_codes` (sorted ascending): include `missing_contract` when no contract exists; `pending_receipt` when no receipt exists as of the review date; `ap_hold` when an invoice exception exists; `open_supplier_risk` when an open risk event exists; `supplier_watch` when the supplier `risk_rating` is `watch`.
- `readiness_status`: `ready` only if no blockers; `at_risk` if blockers exist but are not fatal; `not_ready` if fatal blockers exist (e.g., no contract for a required commercial basis, or critical open risk).
- `nomination_decision`: `nominate` for `ready`, `conditional_nomination` for `at_risk`, `hold` for `not_ready`.
- `overall_readiness`: reflects the worst line status (if any line is `not_ready` → `not_ready`; if any is `at_risk` → `at_risk`; else `ready`).
- `committee_action`: route `nominate_now` for `ready` suppliers, `conditional` for `at_risk`, `hold` for `not_ready`. `send_to_committee` is typically `yes` unless nothing is ready or conditional.

### 2. Receiving Batch Review (train_002 style)

**Goal**: Evaluate a single receipt batch against its PO, invoice, contract, and supplier risk.

**Key logic**:
- `line_reconciliation`: compute `short_qty_vs_po = ordered_qty - received_qty`, `unreceived_billed_qty = billed_qty - received_qty`, `receipt_completion_ratio = round(received_qty / ordered_qty, 4)`.
- `contract_price_match`: `true` when the PO unit price equals the contract unit price.
- `exception_codes` (set, evaluator sorts): include `INVOICE_QTY_EXCEEDS_RECEIPT` when `billed_qty > received_qty`; `PARTIAL_RECEIPT` when `received_qty < ordered_qty`; `SUPPLIER_WATCH_RISK` when the supplier `risk_rating` is `watch` **and** there is an open risk event (or simply when the rating is `watch` — include it); `PRICE_MISMATCH` when unit prices differ; `DAMAGE_REJECTION` when `quantity_rejected > 0`.
- `batch_disposition`: `accept_partial_hold_variance` when the receipt is accepted but quantities differ; `release_full_invoice` only when everything matches perfectly; `manual_recount_required` for severe discrepancies.
- `ap_action`: `keep_invoice_on_hold` when the invoice has a hold code or variance; `release_invoice` when matched and no holds.
- `receiving_action`: `record_shortage_follow_up` when there is a short quantity; `no_receiving_action` when the receipt is already posted and no further receiving step is needed. The memo text ("closeout review for an already-posted receipt") suggests `record_shortage_follow_up` is appropriate when a shortage exists, because the follow-up still needs to be documented.
- `supplier_action`: `request_credit_or_remaining_delivery` when there is a shortage or variance; `no_supplier_action` when everything is clean.
- `supplier_risk_context`: always query open risk events for the supplier. Include `has_open_supplier_risk: true` and the open event IDs when any exist.

### 3. AP Close Reconciliation (train_003 style)

**Goal**: Reconcile target invoices, compute vendor balances, program summaries, and payment queues.

**Key logic**:
- `invoice_decisions`: one row per target invoice, sorted by `invoice_id` ascending.
- `quantity_received`: from the linked receipt if any; `0.00` if no receipt exists.
- `quantity_variance = round(quantity_billed - quantity_received, 2)`.
- `quantity_variance_pct = round((variance / PO_quantity) * 100, 1)`.
- `hold_decision`: `HOLD` for invoices with `status` in (`on_hold`, `pending_receipt`); `RELEASE` otherwise.
- `release_to_payment`: `true` for approved/matched invoices, even if a scheduled payment already exists. The scheduled payment is a separate fact.
- `reason_codes` (sorted alphabetically):
  - `APPROVED_THREE_WAY_MATCH` when status is `approved` and quantities match.
  - `NO_RECEIPT` when no receipt exists.
  - `QTY_VARIANCE` when `quantity_billed != quantity_received`.
  - `SCHEDULED_PAYMENT_FOUND` when a payment record exists for this invoice.
- `vendor_balances` (sorted by `supplier_id` ascending):
  - `opening_balance = 0.0` per the memo.
  - `invoice_total` = sum of target invoice totals for that supplier.
  - `scheduled_payments` = sum of payment amounts for target invoices of that supplier.
  - `held_invoice_total` = sum of target invoice totals with `status` in (`on_hold`, `pending_receipt`).
  - `releasable_invoice_total` = sum of target invoice totals that are approved/releasable. For a supplier whose invoices are all approved and fully scheduled, this can be the approved total (not zero); the `balance_status` distinguishes the state.
  - `close_balance = round(opening_balance + invoice_total - scheduled_payments, 2)`.
  - `balance_status`:
    - `OPEN_HELD` when `held_invoice_total > 0`.
    - `FULLY_SCHEDULED` when `held_invoice_total == 0` and all approved amounts are covered by scheduled payments.
    - `OPEN_APPROVED` when there are approved invoices not fully scheduled.
- `program_summary` (sorted by `program_id` ascending): aggregate the target invoices by program. `net_close_balance` is the sum of `close_balance` for suppliers in that program.
- `payment_hold_queue`: sorted target invoice IDs with `hold_decision == HOLD`.
- `payment_release_queue`: sorted target invoice IDs with `hold_decision == RELEASE`.
- `total_close_balance`: sum of all supplier `close_balance` values.

### 4. Change-Control Decision (train_004 style)

**Goal**: Determine whether a modular change can be released as a contract amendment.

**Key logic**:
- `contract_check`:
  - `noncancelled_subtotal` = sum of `subtotal` for all POs linked to the contract with `status != cancelled`.
  - `headroom_before_change = ceiling_amount - noncancelled_subtotal`.
  - `requested_subtotal = requested_quantity * unit_price`.
  - `headroom_after_change = headroom_before_change - requested_subtotal`.
  - `ceiling_ok`: `true` when `headroom_after_change >= 0`.
- `program_budget_check`:
  - Use the `budget_snapshots` record for the program.
  - `remaining_budget = budget_cap - committed_amount`.
  - `requested_tax = round(requested_subtotal * tax_rate_percent / 100, 2)`.
  - `requested_total = round(requested_subtotal + requested_tax, 2)`.
  - `budget_after_change = round(remaining_budget - requested_total, 2)`.
  - `budget_ok`: `true` when `budget_after_change >= 0`.
  - `max_quantity_with_current_budget = floor(remaining_budget / (unit_price * (1 + tax_rate)))`.
- `approval_check`:
  - Find all `approval_events` where `object_id == source_requisition_id` and `object_type == requisition`.
  - Use the latest event by `event_date`.
  - `approval_ok`: `true` when `latest_action` is in the good-actions list (typically `["approved"]`).
- `supplier_risk_check`:
  - `open_event_ids`: all open/monitoring risk events for the supplier, sorted ascending.
  - `severe_open_event_ids`: subset with severity in (`high`, `critical`), sorted ascending.
  - `supplier_risk_ok`: `true` when `severe_open_event_ids` is empty.
- `supporting_ids`:
  - `included_po_ids`: all non-cancelled POs under the contract, sorted ascending.
  - `excluded_cancelled_po_ids`: cancelled POs under the contract, sorted ascending.
  - `approval_event_ids`: all approval events for the source requisition, sorted ascending.
- `required_actions` (sorted ascending):
  - `obtain_final_requisition_approval` when `approval_ok == false`.
  - `raise_budget_exception_or_reduce_quantity` when `budget_ok == false` or `ceiling_ok == false`.
  - `resolve_supplier_risk_hold` when `supplier_risk_ok == false`.
  - `none` when no blockers.
- `decision`:
  - `release_amendment` when all checks pass.
  - `hold_for_budget` when only budget fails.
  - `hold_for_approval` when only approval fails.
  - `hold_for_supplier_risk` when only supplier risk fails.
  - `hold_for_budget_and_approval` when both budget and approval fail.
  - `reject_contract_mismatch` when the contract is inactive or the SKU does not match.

### 5. AP Release with Chargebacks (train_005 style)

**Goal**: Build release/hold decisions and receiving exceptions for invoices tied to a program, using both API data and a local chargeback register.

**Key logic**:
- `release_decisions`: one entry per target invoice, sorted by `invoice_id` ascending.
  - `receipt_ids_in_scope`: receipts explicitly linked to the invoice or PO.
  - `excluded_same_po_receipt_ids`: other receipts on the same PO that are **not** in scope for this invoice. Include receipts from the full API, not just the target receipt list in the packet, when they belong to a target PO.
  - `decision`:
    - `release_net_after_approved_chargeback` when an `approved` chargeback exists for the invoice/receipt.
    - `hold_missing_receipt` when the invoice has no receipt and `hold_code` is `NO_RECEIPT`.
    - `hold_pending_quality_chargeback` when a chargeback is `pending_quality_review` and/or the receipt is on `inspection_hold`.
  - `primary_reason`:
    - `approved_qty_chargeback` for approved underage-quantity chargebacks.
    - `approved_ap_quantity_variance` for approved AP-quantity-variance chargebacks.
    - `no_receipt_on_po` for missing receipts.
    - `inspection_hold_pending_chargeback` for pending quality chargebacks.
  - `approved_chargeback_amount` = `basis_quantity * unit_cost` for approved chargebacks; `0.0` otherwise.
  - `pending_chargeback_amount` = `basis_quantity * unit_cost` for pending chargebacks; `0.0` otherwise.
  - `net_release_amount` = `invoice_total - approved_chargeback_amount` for released invoices; `0.0` for held invoices.
- `receiving_exceptions`: one entry per target receipt, sorted by `receipt_id` ascending.
  - `exception_codes` (set, evaluator sorts):
    - `Underage Quantity` when `quantity_received < PO_quantity`.
    - `AP Quantity Variance` when `quantity_billed > quantity_received`.
    - `Inspection Hold` when receipt `status == inspection_hold`.
    - `Severe Unmatched Quantity` when the billed-to-received or PO-to-received discrepancy is very large (use judgment; a billed quantity vastly exceeding received or PO quantity qualifies).
  - `chargeback_status`: `approved`, `pending_quality_review`, or `not_applicable`.
  - `resolution_status`: `net_release_ready` when chargeback is approved; `hold_for_quality_review` when pending; `accepted_no_receiving_exception` when no exception; `missing_receipt` when no receipt exists.
- `summary`:
  - `release_invoice_ids`: target invoices with `release_*` decisions.
  - `hold_invoice_ids`: target invoices with `hold_*` decisions.
  - `approved_chargeback_total`: sum of approved chargeback amounts.
  - `pending_chargeback_total`: sum of pending chargeback amounts.
  - `net_release_total`: sum of `net_release_amount` across all invoices (held ones contribute `0.0`).
  - `authoritative_sources`: `[procureops_po_records, procureops_receipt_records, procureops_ap_records, local_chargeback_register]`.
  - `supporting_only_sources`: `[ap_release_request_note, stale_po73xx_alias_note]`.
  - `followup_actions`: choose from the allowed list based on the issues found. Common selections:
    - `ask_receiving_for_vantix_receipt` when a Vantix invoice lacks a receipt.
    - `hold_luma_duplicate_receipt_for_separate_invoice` when a PO has multiple receipts for different invoices.
    - `route_po00031_quality_review` when a receipt is on inspection hold with a pending chargeback.
    - `post_approved_chargeback_netting` when approved chargebacks exist.

## Common Pitfalls

1. **Forgetting the as-of date filter**: Receipts or invoices with dates after the review date must be excluded from evidence counts.
2. **Omitting related POs**: A memo may highlight one PO, but the same SKU often has multiple POs in the program. Include all non-cancelled POs for contract and budget calculations.
3. **Risk event confusion**: A supplier with `risk_rating: watch` may still have open risk events. Always query `/vendor_risk_events` and include open events in `risk_event_ids` and blocker codes.
4. **Chargeback status**: Distinguish `approved` vs `pending_quality_review` chargebacks. Only `approved` ones reduce the net release amount.
5. **Releasable invoice total**: In vendor balances, approved invoices are releasable even if fully scheduled. Do not zero them out unless the template explicitly says otherwise.
6. **Tax calculation**: For change-control tasks, tax is `round(subtotal * tax_rate_percent / 100, 2)`. Freight is only included if the memo explicitly provides a freight line.
7. **Approval events**: A requisition may have multiple approval events. Use the **latest by event_date**, not just any event.
8. **Max quantity with budget**: Use `floor(remaining_budget / (unit_price * (1 + tax_rate)))`, not a simple division without the tax factor.
9. **Sorting**: Unsorted ID lists are a frequent source of score loss. Sort every list the template describes as ordered.
10. **Exception code scope**: `Severe Unmatched Quantity` is reserved for very large discrepancies (e.g., billed quantity vastly exceeds received quantity). Do not apply it to small variances like 10%.
