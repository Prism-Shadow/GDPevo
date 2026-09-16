 # ProcureOps Business Rules

 ## General Conventions

 - All amounts in USD, rounded to 2 decimal places (cents).
 - List fields are treated as sets unless the task template specifies ordering.
 - Sort list fields ascending when ordering is required.
 - The `as_of_date` (or similar review date) gates receipt, invoice, and risk-event
   inclusion: only records dated on or before the review date count.
 - Cancelled POs are excluded from contract-usage calculations and nominee readiness.
 - A supplier's `risk_rating` of `watch` or `high` is a flag; only `open` or
   `monitoring` events at `high` severity are severe blockers.

 ## Three-Way Match (PO, Receipt, Invoice)

 A three-way match is satisfied when all of these hold for every line:

 1. A receipt exists for the PO with `status` `accepted` or `accepted_with_note`.
 2. The receipt line `quantity_received` >= the invoice line `quantity_billed`.
 3. `invoice_line.unit_price` == `po_line.unit_price` (or within contract terms for
    indexed/not-to-exceed contracts).

 When any condition fails, the invoice is on hold or requires exception review.

 ## Quantity Reconciliation

 For a given PO line across all receipts and invoices:

 - `ordered_qty` = PO line `quantity`
 - `received_qty` = sum of `quantity_received` across all receipts for that PO line
 - `rejected_qty` = sum of `quantity_rejected` across all receipts for that PO line
 - `billed_qty` = sum of `quantity_billed` across all invoices for that PO line
 - `short_qty_vs_po` = `ordered_qty - received_qty`
 - `unreceived_billed_qty` = `billed_qty - received_qty`
 - `receipt_completion_ratio` = `received_qty / ordered_qty` (to 4 decimal places)

 ## Contract Price Matching

 - For `fixed` contracts: `po_line.unit_price` == `contract.unit_price`.
 - For `indexed` or `not_to_exceed`: `po_line.unit_price` <= `contract.unit_price`
   (check business controls for exact tolerance).
 - `contract_price_match` is boolean per line.

 ## Budget Headroom

 From the budget snapshot for a program:

 - `budget_headroom_usd` = `budget_cap - committed_amount`
 - `remaining_budget` = `budget_cap - committed_amount` (same value)
 - `budget_after_change` = `remaining_budget - requested_total` (where
   `requested_total = requested_subtotal + requested_tax`)
 - `budget_ok` is true when `budget_after_change >= 0`
 - `max_quantity_with_current_budget` = floor(`remaining_budget` /
   (`unit_price * (1 + tax_rate)`))
 - Tax is computed as `subtotal * tax_rate_percent / 100`, unless the task
   payload provides a specific freight or tax override.

 ## Contract Headroom

 - `noncancelled_subtotal` = sum of `subtotal` across all POs for the contract
   whose `status` is not `cancelled`.
 - `headroom_before_change` = `ceiling_amount - noncancelled_subtotal`.
 - `requested_subtotal` = `requested_quantity * unit_price`.
 - `headroom_after_change` = `headroom_before_change - requested_subtotal`.
 - `ceiling_ok` is true when `headroom_after_change >= 0`.

 ## Approval Checks

 - Find approval events where `object_id` == the requisition ID and
   `object_type` == `requisition`.
 - The latest event (by `event_date`) determines the current state.
 - `approval_ok` is true when the latest action is `approved`.
 - Approved actions are: `approved`. Actions like `submitted`, `returned`, or
   `rejected` are not approval-ready.

 ## Supplier Risk Context

 - `supplier_risk_rating` comes from the supplier record: `low`, `medium`,
   `watch`, `high`.
 - `has_open_supplier_risk` is true when any vendor risk event for the supplier
   has `status` `open` or `monitoring`.
 - `severe_open_event_ids` are open/monitoring events with `severity` `high`.
 - `supplier_risk_ok` is false only when there is an open severe event, unless
   business controls specify otherwise (e.g., `supplier_watch_rating` is "context
   only unless an open severe event is found").
 - For nomination readiness, all open or monitoring events for the supplier are
   flagged as `risk_event_ids`, regardless of severity.

 ## Sourcing Nomination Readiness

 Determined per package-line SKU:

 **Blocker codes** (pick all that apply, sorted ascending):

 | Code | Condition |
 |---|---|
 | `none` | No blockers apply. |
 | `missing_contract` | PO has `contract_id` null, or contract not `active`. |
 | `supplier_watch` | Supplier `risk_rating` is `watch` or `high` but no open severe events. |
 | `open_supplier_risk` | Any open or monitoring vendor-risk event for that supplier. |
 | `ap_hold` | Any invoice for the PO/supplier has `status` `on_hold`. |
 | `pending_receipt` | No receipt exists for the PO, or receipt `status` is `pending_inspection`. |
 | `late_due_date` | PO `due_date` is before the `as_of_date` and no full receipt exists. |

 **Readiness status** (worst-first):

 - `not_ready`: any of `missing_contract`, `open_supplier_risk`, `pending_receipt`, `late_due_date`, or `ap_hold` with no receipt.
 - `at_risk`: `supplier_watch` or `ap_hold` (with receipt present).
 - `ready`: only `none`.

 **Nomination decision**:

 - `nominate` when `ready`.
 - `conditional_nomination` when `at_risk`.
 - `hold` when `not_ready`.

 **Overall program readiness**: worst status across all nomination lines.

 ## Receiving Exception Codes

 For a batch/PO inspection:

 | Code | Condition |
 |---|---|
 | `NO_EXCEPTION` | All lines match perfectly. |
 | `INVOICE_QTY_EXCEEDS_RECEIPT` | billed_qty > received_qty for any line. |
 | `PARTIAL_RECEIPT` | received_qty < ordered_qty for any line. |
 | `SUPPLIER_WATCH_RISK` | Supplier risk rating `watch` or `high` with open events. |
 | `PRICE_MISMATCH` | Invoice unit price != PO unit price (or contract price mismatch). |
 | `DAMAGE_REJECTION` | rejected_qty > 0. |

 Also for the AP release receiving-exceptions flow:

 | Code | Condition |
 |---|---|
 | `Underage Quantity` | received_qty < ordered_qty. |
 | `Severe Unmatched Quantity` | Large variance (typically >5% of ordered). |
 | `Inspection Hold` | Receipt line `inspection_status` is `on_hold` or `failed`. |
 | `AP Quantity Variance` | billed_qty != received_qty. |

 ## AP Invoice Decision Rules

 **Hold decision**: `HOLD` when:

 - `invoice_status` is `on_hold` or `pending_receipt`.
 - `quantity_variance` != 0 (billed != received).
 - No receipt exists for the PO (`NO_RECEIPT`).

 **Hold decision**: `RELEASE` when:

 - `invoice_status` is `approved`.
 - Three-way match passes (quantity, price, receipt).

 **Reason codes** (alphabetical):

 - `APPROVED_THREE_WAY_MATCH`: All three documents match.
 - `NO_RECEIPT`: No receipt recorded for the PO.
 - `QTY_VARIANCE`: billed_qty != received_qty.
 - `SCHEDULED_PAYMENT_FOUND`: A payment is scheduled for this invoice.

 ## AP Release Decisions (with Chargebacks)

 When a local chargeback register is provided:

 - `release_net_after_approved_chargeback`: chargeback approved, net = total - approved.
 - `hold_pending_quality_chargeback`: chargeback pending quality review.
 - `hold_missing_receipt`: no receipt exists for the PO.

 **Net release amount**: `invoice_total - approved_chargeback_amount` (only
 non-zero when releasing).

 ## Vendor Balance Reconciliation

 For the target invoices within a close slice:

 - `opening_balance` starts at the value specified in the memo (often `0.00`).
 - `invoice_total` = sum of invoice totals for this supplier in scope.
 - `scheduled_payments` = sum of scheduled payment amounts for the supplier's
   in-scope invoices (as of the payment schedule window, typically through
   end-of-month).
 - `held_invoice_total` = sum of held invoice totals.
 - `releasable_invoice_total` = sum of releasable invoice totals.
 - `close_balance` = `opening_balance + invoice_total - scheduled_payments`.

 **Balance status**:

 - `FULLY_SCHEDULED`: close_balance == 0 and no held invoices.
 - `OPEN_HELD`: Any invoices held.
 - `OPEN_APPROVED`: Releasable invoices exist and not fully scheduled.

 ## Change Control Decision Flow

 Determine `decision` by checking these gates in order:

 1. **Contract**: if `ceiling_ok` is false → `reject_contract_mismatch`.
 2. **Budget**: if `budget_ok` is false → includes `hold_for_budget`.
 3. **Approval**: if `approval_ok` is false → includes `hold_for_approval`.
 4. **Supplier risk**: if `supplier_risk_ok` is false → includes
    `hold_for_supplier_risk`.
 5. Combined: `hold_for_budget_and_approval` when both fail.
 6. All pass → `release_amendment`.

 ## Committee Action (Sourcing)

 - `next_owner`: determined by the dominant blocker category.
   - `missing_contract` → `buyer`.
   - `ap_hold` or invoice issues → `ap_team`.
   - `pending_receipt` → `finance_ops`.
   - `open_supplier_risk` → `quality_ops`.
   - `late_due_date` → `program_owner`.
 - `send_to_committee`: `yes` only when all lines are `nominate` with no
   significant blockers; otherwise `no`.

 ## Chargeback Netting

 When a chargeback register is provided as a task payload:

 - `approved_chargeback_amount` = sum of chargeback amounts with
   `status` `approved` for the invoice.
 - `pending_chargeback_amount` = sum of chargeback amounts with
   `status` `pending_quality_review` for the invoice.
 - Chargeback `basis_quantity * unit_cost` is the chargeback value.
 - Only use the local chargeback register; do not derive chargebacks from API
   data.

 ## Evidence and Source Tracking

 When a task asks for evidence or supporting IDs:

 - `endpoint_record_ids`: every API record ID consulted (PO, receipt, invoice,
   contract, supplier, risk event, item, budget snapshot, approval event, etc.)
   as a sorted set.
 - `task_payloads_reviewed`: every local payload file read, listed as the file
   path relative to the task root.
 - `authoritative_sources`: sources of truth for decisions.
 - `supporting_only_sources`: context-only sources not used for binding decisions.
