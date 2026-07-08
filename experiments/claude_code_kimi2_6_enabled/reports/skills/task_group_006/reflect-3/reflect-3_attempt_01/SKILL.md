# ProcureOps Task Group Skill

## 1. Environment & API Usage
- **Base URL**: Use the runner-provided base URL. Do not assume `localhost` or `127.0.0.1`.
- **Endpoints**: `/programs`, `/purchase_orders`, `/purchase_requisitions`, `/receipts`, `/ap_invoices`, `/contracts`, `/suppliers`, `/vendor_risk_events`, `/payments`, `/approval_events`, `/budget_snapshots`, `/items`.
- **Query reliability**: Filtering via query parameters (`?po_id=...`) is unreliable. Fetch the full list (`GET /{endpoint}`) and filter locally in Python.
- **Single-record fetch**: You can also fetch by ID path (`GET /ap_invoices/AP-LUMA-7714`), but bulk fetch is usually faster.
- **Data freshness**: Treat the API as the system of truth. Local memos/packets provide target IDs and narrative context, but live records override static text.

## 2. General Output Conventions
- **Return format**: Return **only** a JSON object matching the provided `answer_template.json`.
- **Currency**: All USD amounts must be rounded to **cents** (2 decimal places). Use standard `round(value, 2)`.
- **Percentages**: Round to the precision specified in the template (e.g., 1 decimal place for `quantity_variance_pct`).
- **Ratios**: Round to the precision specified (e.g., 4 decimal places for `receipt_completion_ratio`). JSON does not require trailing zeros, but the numeric value must be correct.
- **Lists / Sets**: When the template says "set; evaluator sorts values", still sort the list ascending before emitting. For ID lists, sort lexicographically ascending.
- **Task ID**: Use the exact `task_id` string specified in the answer template (e.g., `task_group_006_train_001` or `train_002`).

## 3. Data Relationships & Lookups
| Entity | Key Fields | How to Resolve |
|--------|------------|----------------|
| Program | `program_id` | `/programs` or `/budget_snapshots` |
| PO | `po_id`, `program_id`, `supplier_id`, `contract_id`, `requisition_id` | `/purchase_orders` |
| Requisition | `requisition_id`, `program_id`, `sku` | `/purchase_requisitions` |
| Receipt | `receipt_id`, `po_id`, `supplier_id` | `/receipts` |
| AP Invoice | `invoice_id`, `po_id`, `receipt_id`, `supplier_id`, `status`, `hold_code` | `/ap_invoices` |
| Contract | `contract_id`, `sku`, `program_id`, `ceiling_amount`, `unit_price` | `/contracts` |
| Supplier | `supplier_id`, `name`, `risk_rating`, `status` | `/suppliers` |
| Vendor Risk | `event_id`, `supplier_id`, `severity`, `status` | `/vendor_risk_events` |
| Payment | `payment_id`, `invoice_id`, `supplier_id`, `scheduled_date`, `status` | `/payments` |
| Approval | `event_id`, `object_id` (requisition), `action`, `actor`, `event_date` | `/approval_events` |
| Budget | `snapshot_id`, `program_id`, `budget_cap`, `committed_amount`, `pending_invoice_amount` | `/budget_snapshots` |

## 4. Business Rules by Task Type

### 4.1 Nomination Readiness Packet
- **Program summary**:
  - `owner` = `programs.owner`.
  - `budget_headroom_usd` = `budget_cap - committed_amount` (from `/budget_snapshots`).
  - `overall_readiness`: If any line is `not_ready`, the program is often `at_risk` (not automatically `not_ready`).
- **Nomination line fields**:
  - `selected_supplier_id` = PO's `supplier_id`.
  - `commercial_basis_id` = PO's `contract_id` (may be `null`).
  - `package_po_ids` = all POs for that SKU in the program.
  - `receipt_evidence_ids` = receipts for those POs, filtered to `as_of_date`.
  - `invoice_exception_ids` = AP invoices for those POs with status `on_hold` or `pending_receipt` (or any non-approved status) as of `as_of_date`.
  - `risk_event_ids` = open or monitoring vendor-risk events for the supplier as of `as_of_date`.
  - `blocker_codes` (sorted ascending):
    - `missing_contract` if `contract_id` is `null`.
    - `open_supplier_risk` if any open vendor risk event exists for the supplier (even if unrelated to the PO).
    - `ap_hold` if any invoice for the line's POs has status `on_hold`.
    - `pending_receipt` if no receipt exists for the PO (or PO status is `open` with no receipts).
    - `late_due_date` if `po.due_date < as_of_date`.
    - `none` if no blockers apply.
- **Committee action**:
  - Map each supplier to `nominate_now`, `conditional`, or `hold` based on `nomination_decision`.
  - `send_to_committee` is typically `no` when holds exist, `yes` when all lines are ready or conditional.
  - `next_owner`: choose from `buyer|finance_ops|quality_ops|program_owner|ap_team` based on the dominant blocker type.

### 4.2 Receiving Memo
- **Target batch**: The memo names a specific `receipt_id` (e.g., `RCV-BLUE-14`).
- **Invoice focus**: Use the AP invoice whose `receipt_id` matches the batch (e.g., `AP-LUMA-7714`). Ignore other invoices for the same PO unless they are tied to a different receipt.
- **Line reconciliation**:
  - `ordered_qty` = PO line `quantity`.
  - `received_qty` = receipt line `quantity_received`.
  - `rejected_qty` = receipt line `quantity_rejected`.
  - `billed_qty` = invoice line `quantity_billed`.
  - `short_qty_vs_po` = `ordered_qty - received_qty`.
  - `unreceived_billed_qty` = `billed_qty - received_qty` (or `billed_qty - (received_qty - rejected_qty)`).
  - `receipt_completion_ratio` = `received_qty / ordered_qty`, rounded to 4 decimals.
  - `contract_price_match` = `po_unit_price == contract_unit_price`.
- **Exception codes** (sorted ascending, set semantics):
  - `INVOICE_QTY_EXCEEDS_RECEIPT` if `billed_qty > received_qty`.
  - `PARTIAL_RECEIPT` if PO status is `partial_receipt`.
  - `SUPPLIER_WATCH_RISK` if **any** open vendor risk event exists for the supplier (even on a different PO). Do not omit this.
  - `PRICE_MISMATCH` if `invoice_unit_price != contract_unit_price`.
  - `DAMAGE_REJECTION` if `rejected_qty > 0` or dock notes mention damage.
  - `NO_EXCEPTION` only if none of the above apply.
- **Decision**:
  - `batch_disposition`: `accept_partial_hold_variance` when the receipt is accepted/accepted_with_note but there is a shortage or variance.
  - `ap_action`: `keep_invoice_on_hold` when the invoice has a hold code or the batch has a variance; `release_invoice` only when truly clear.
  - `receiving_action`: `record_shortage_follow_up` when `short_qty_vs_po > 0`; otherwise `no_receiving_action`.
  - `supplier_action`: `request_credit_or_remaining_delivery` when there is a shortage.
- **Evidence**:
  - `endpoint_record_ids` must include **every** API record examined, including the program, contract, PO, receipt, invoice, supplier, and any risk events referenced in `supplier_risk_context`.
  - `task_payloads_reviewed` = list of local payload filenames reviewed (e.g., `receiving_memo.md`).

### 4.3 AP Close Memo
- **Scope**: Reconcile only the invoices named in the memo.
- **Opening balance**: Treat as `0.00` for each target supplier unless the memo states otherwise.
- **Invoice decisions** (sorted by `invoice_id` ascending):
  - `quantity_received`: from the receipt tied to the invoice (`invoice.receipt_id`). If `null`, use `0.00`.
  - `quantity_variance` = `quantity_billed - quantity_received`.
  - `quantity_variance_pct` = `(quantity_variance / PO quantity) * 100`, rounded to 1 decimal.
  - `scheduled_payment_amount`: sum of payments for that specific `invoice_id` with `scheduled_date <= close_date` (or all scheduled payments for the invoice if the memo says "through" the close date). If none, `0.00`.
  - `net_balance_impact` = `invoice_total - scheduled_payment_amount`.
  - `hold_decision`: `HOLD` if invoice status is `on_hold` or `pending_receipt`; `RELEASE` if `approved` or `paid`.
  - `release_to_payment`: `true` only when `hold_decision == RELEASE` and a payment is scheduled.
  - `reason_codes` (alphabetical):
    - `APPROVED_THREE_WAY_MATCH` when invoice qty = receipt qty = PO qty and status is approved.
    - `SCHEDULED_PAYMENT_FOUND` when a payment exists for the invoice.
    - `QTY_VARIANCE` when `quantity_variance != 0`.
    - `NO_RECEIPT` when `receipt_id` is `null`.
- **Vendor balances** (sorted by `supplier_id` ascending):
  - `invoice_total` = sum of target invoice totals for that supplier.
  - `scheduled_payments` = sum of **all** payments for that supplier with `scheduled_date <= close_date` (or as directed by the memo), not just target-invoice payments.
  - `held_invoice_total` = sum of target invoice totals where `hold_decision == HOLD`.
  - `releasable_invoice_total` = sum where `hold_decision == RELEASE`.
  - `close_balance` = `opening_balance + invoice_total - scheduled_payments`.
  - `balance_status`:
    - `FULLY_SCHEDULED` if `close_balance == 0` and all releasable invoices have payments.
    - `OPEN_HELD` if any held invoices remain.
    - `OPEN_APPROVED` if releasable invoices exist but are not fully scheduled.
- **Program summary** (sorted by `program_id` ascending):
  - Aggregate `invoice_count`, `invoice_total`, `held_total`, `released_total`, `net_close_balance` from the invoice decisions.
- **Queues**:
  - `payment_hold_queue` = target invoice IDs with `hold_decision == HOLD`, sorted ascending.
  - `payment_release_queue` = target invoice IDs with `hold_decision == RELEASE`, sorted ascending.
- `total_close_balance` = sum of all `net_balance_impact` values (or sum of vendor `close_balance`s).

### 4.4 Change Memo / Contract Amendment
- **Contract check**:
  - `noncancelled_subtotal` = sum of `subtotal` for all POs linked to the contract with `status != cancelled`.
  - `headroom_before_change` = `ceiling_amount - noncancelled_subtotal`.
  - `requested_subtotal` = `requested_quantity * contract.unit_price`.
  - `headroom_after_change` = `headroom_before_change - requested_subtotal`.
  - `ceiling_ok` = `headroom_after_change >= 0`.
- **Program budget check**:
  - `remaining_budget` = `budget_cap - committed_amount` (from `/budget_snapshots`).
  - `requested_tax` = `requested_subtotal * (tax_rate_percent / 100)`, rounded to cents.
  - `requested_total` = `requested_subtotal + requested_tax`.
  - `budget_after_change` = `remaining_budget - requested_total`.
  - `budget_ok` = `budget_after_change >= 0`.
  - `max_quantity_with_current_budget` = `floor(remaining_budget / (unit_price * (1 + tax_rate/100)))` when tax is part of budget exposure. If tax is not part of exposure, use `floor(remaining_budget / unit_price)`. Follow the memo's `business_controls` note on budget exposure.
- **Approval check**:
  - Look at `/approval_events` filtered by `object_id == source_requisition_id`.
  - `latest_event_id` = the most recent event (by `event_date`).
  - `approval_ok` = `true` only if `latest_action` is in the memo's `approval_good_actions` list (typically `approved`).
- **Supplier risk check**:
  - `open_event_ids` = all vendor risk events for the supplier with `status == open`.
  - `severe_open_event_ids` = subset where `severity == severe` (or `high` depending on schema).
  - `supplier_risk_ok` = `true` if there are **no** severe open events. A medium open event does **not** block the change unless the memo explicitly says otherwise.
- **Decision**:
  - Choose the most specific hold reason:
    - `hold_for_budget_and_approval` when both are false.
    - `hold_for_budget` when only budget fails.
    - `hold_for_approval` when only approval fails.
    - `hold_for_supplier_risk` when supplier risk fails.
    - `release_amendment` when all checks pass.
    - `reject_contract_mismatch` only when the SKU/contract mapping is wrong.
- **Supporting IDs**:
  - `included_po_ids` = non-cancelled POs under the contract, sorted ascending.
  - `excluded_cancelled_po_ids` = cancelled POs under the contract, sorted ascending.
  - `approval_event_ids` = all approval events for the source requisition, sorted ascending.
- **Required actions** (sorted ascending): include `obtain_final_requisition_approval` when `approval_ok == false`, `raise_budget_exception_or_reduce_quantity` when `budget_ok == false`, `resolve_supplier_risk_hold` when `supplier_risk_ok == false`, otherwise `none`.

### 4.5 AP Release / Exception Review
- **Target IDs**: Use exactly the IDs listed in the local packet. Sort each list ascending.
- **Chargebacks**: The local packet includes a `chargeback_register_excerpt`. Use it as the authoritative source for chargeback status and amounts. Compute chargeback amount = `basis_quantity * unit_cost`.
- **Release decisions** (one per target invoice):
  - `receipt_ids_in_scope` = the receipt(s) tied to the invoice (`invoice.receipt_id`). If the invoice has no receipt, use `[]`.
  - `excluded_same_po_receipt_ids` = other receipts for the same PO that are **not** tied to this invoice.
  - `decision`:
    - `release_net_after_approved_chargeback` when the chargeback is `approved` and the receipt is accepted.
    - `hold_pending_quality_chargeback` when the chargeback is `pending_quality_review` or the receipt is on `inspection_hold`.
    - `hold_missing_receipt` when `receipt_id` is `null`.
  - `primary_reason`:
    - `approved_qty_chargeback` for approved underage-quantity chargebacks.
    - `approved_ap_quantity_variance` for approved AP-quantity-variance chargebacks.
    - `inspection_hold_pending_chargeback` for inspection-hold receipts with pending chargebacks.
    - `no_receipt_on_po` when there is no receipt.
  - `approved_chargeback_amount` = sum of approved chargebacks for this invoice/receipt.
  - `pending_chargeback_amount` = sum of pending chargebacks for this invoice/receipt.
  - `net_release_amount` = `invoice_total - approved_chargeback_amount - pending_chargeback_amount`.
- **Receiving exceptions** (one per target receipt):
  - `exception_codes` (sorted ascending):
    - `Underage Quantity` when `received_qty < ordered_qty`.
    - `Inspection Hold` when receipt `status == inspection_hold`.
    - `AP Quantity Variance` when a chargeback reason is `AP Quantity Variance`.
    - `Severe Unmatched Quantity` only when the variance is extreme (use judgment based on template guidance).
  - `chargeback_status`: `approved`, `pending_quality_review`, or `not_applicable`.
  - `resolution_status`:
    - `net_release_ready` for approved chargebacks / accepted receipts.
    - `hold_for_quality_review` for pending quality chargebacks or inspection holds.
    - `missing_receipt` when there is no receipt.
    - `accepted_no_receiving_exception` when the receipt is clean.
- **Summary**:
  - `release_invoice_ids` = invoices with decision `release_net_after_approved_chargeback`, sorted ascending.
  - `hold_invoice_ids` = all other target invoices, sorted ascending.
  - `approved_chargeback_total` = sum of all `approved_chargeback_amount`s across release decisions.
  - `pending_chargeback_total` = sum of all `pending_chargeback_amount`s.
  - `net_release_total` = sum of **all** `net_release_amount`s (including holds), or the sum of release invoices only if the template explicitly says so. When in doubt, include the grand total and note the ambiguity.
  - `authoritative_sources` = include all applicable from the allowed list.
  - `supporting_only_sources` = include all applicable from the allowed list (e.g., `ap_release_request_note`, `stale_po73xx_alias_note`).
  - `followup_actions` = include every applicable action from the allowed list. Common ones:
    - `ask_receiving_for_vantix_receipt` when a target invoice lacks a receipt.
    - `route_po00031_quality_review` when a receipt is on inspection hold with a pending chargeback.
    - `post_approved_chargeback_netting` when there are approved chargebacks.
    - `hold_luma_duplicate_receipt_for_separate_invoice` when a PO has multiple receipts and the current invoice is tied to only one of them (the other receipt may belong to a separate invoice).

## 5. Common Pitfalls
1. **Omitting SUPPLIER_WATCH_RISK**: If a supplier has **any** open vendor risk event, include `SUPPLIER_WATCH_RISK` in receiving-memo exception codes, even if the event is on a different PO.
2. **Unsorted lists**: The evaluator often compares sets, but some fields are compared as ordered lists. Always sort ID lists and enum lists ascending.
3. **Cancelled POs in contract usage**: Exclude `status == cancelled` POs when computing `noncancelled_subtotal` for contract headroom.
4. **Tax in budget exposure**: When the memo says budget exposure includes tax, compute `max_quantity_with_current_budget` using `unit_price * (1 + tax_rate)`.
5. **Payment scope in AP close**: `scheduled_payments` for vendor balances usually means **all** payments for that supplier up to the close date, not just payments for the target invoices.
6. **Quantity received = 0**: When an invoice has `receipt_id == null`, explicitly set `quantity_received` to `0.00`, not `null`.
7. **Evidence completeness**: In receiving memos, include every API record ID that was examined (program, PO, receipt, invoice, contract, supplier, risk events) in `evidence.endpoint_record_ids`.
8. **Duplicate receipts on a PO**: When a PO has multiple receipts and the target invoice is tied to only one, the other receipt is an `excluded_same_po_receipt_id`, and the follow-up action `hold_luma_duplicate_receipt_for_separate_invoice` may be required.
9. **Pending vs. approved chargebacks**: Use the local chargeback register to determine status. Do not infer from the API alone.
10. **Approval event filtering**: Use `object_id == requisition_id` and `object_type == requisition` when looking up approval events.
