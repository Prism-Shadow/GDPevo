# ProcureOps Task Group 006 — Solver SKILL

## 1. Environment

- **Base URL**: `http://34.46.77.124:8006` (from `environment_access.md`). Never use localhost/127.0.0.1.
- **Endpoints**: `/programs`, `/suppliers`, `/items`, `/contracts`, `/purchase_requisitions`, `/purchase_orders`, `/receipts`, `/ap/invoices`, `/ap/payments`, `/approval_events`, `/budget_snapshots`, `/vendor_risk_events`.
- Accept JSON responses; all IDs and status fields come from the API, not from task payloads.

## 2. Source Precedence

1. **ProcureOps API** — authoritative for all record values (statuses, amounts, dates, quantities, supplier names, risk ratings, approval states).
2. **Task payload** (memo/JSON packet) — provides target IDs (which records to review), business-control parameters (tax rate, currency, opening balance assumptions), and any local registers (chargeback register). Use these to scope your API queries, *not* to override API values.
3. **Answer template** — defines the output shape, enum sets, sort orders, and required keys. Match it exactly.

When a payload and API conflict, the API wins for record data; the payload wins for task scoping instructions.

## 3. ID Conventions

| Prefix | Entity |
|--------|--------|
| `PRG-*` | Program |
| `SUP-*` | Supplier |
| `REQ-*` | Purchase Requisition |
| `PO-*` | Purchase Order |
| `CR-*` | Contract |
| `RCV-*` | Receipt |
| `AP-*` | AP Invoice |
| `APR-*` | Approval Event |
| `BUD-*` | Budget Snapshot |
| `VRE-*` | Vendor Risk Event |
| `CB-*` | Chargeback |
| `PK-*` | Packing Slip |
| `WH-*` | Warehouse |
| `MCR-*` | Modular Change Request |

## 4. Output Format Rules (Apply to Every Task)

- **JSON only** — no prose outside the object.
- **USD amounts**: round to 2 decimal places (cents), unless the template specifies a different precision.
- **Lists**: sort IDs ascending (lexicographic) unless the template explicitly says "set; evaluator sorts." When in doubt, sort ascending.
- **Null vs empty**: `null` for absent scalars (`commercial_basis_id`, `hold_code`); `[]` for absent lists (empty receipt arrays, empty risk event arrays).
- **Booleans**: lowercase `true`/`false`.
- **Enums**: use the exact casing from the template's allowed-values list.
- **Date format**: `YYYY-MM-DD` strings.
- **As-of-date filtering**: only include records with dates ≤ `as_of_date` (or `close_date` / `review_as_of`). Future-dated records are out of scope.

## 5. Reusable Business Rules

### 5.1 Nomination Readiness Blockers (train_001 pattern)

Allowed blocker codes (snake_case, sorted ascending):
- `ap_hold` — invoice for this line is on hold (status ≠ approved/paid)
- `late_due_date` — PO/receipt due date is past
- `missing_contract` — no active contract links this SKU to the nominated supplier
- `open_supplier_risk` — one or more open vendor-risk events for the supplier
- `pending_receipt` — no receipt exists for the PO
- `supplier_watch` — supplier risk rating is "watch" (informational; not a hard block alone)
- `none` — no blockers

**Nomination decision mapping**:
- `hold` — any critical blocker (missing_contract, pending_receipt, late_due_date) OR multiple compounding issues
- `conditional_nomination` — supplier has watch risk or AP hold but contract + receipt exist
- `nominate` — no blockers, or only `none`

**Readiness status** (per line):
- `not_ready` → line is on hold
- `at_risk` → conditional_nomination
- `ready` → nominate

**Overall readiness**: worst status across all lines (`not_ready` > `at_risk` > `ready`).

**Committee action**:
- `next_owner`: `ap_team` if any line has ap_hold; `buyer` if any line has missing_contract; `program_owner` if budget is the primary issue; `finance_ops` or `quality_ops` per blocker context.
- `send_to_committee`: `"yes"` only if there are conditional or ready suppliers AND no critical holds blocking all lines; otherwise `"no"`.
- Supplier lists: partition by `nomination_decision` (nominate → nominate_now, conditional → conditional, hold → hold).

### 5.2 Receiving Reconciliation (train_002 pattern)

**Line reconciliation formulas**:
```
short_qty_vs_po       = ordered_qty - received_qty           (integer)
unreceived_billed_qty  = max(0, billed_qty - received_qty)    (integer)
receipt_completion_ratio = received_qty / ordered_qty         (4 decimal places)
contract_price_match   = (po_unit_price == contract_unit_price == invoice_unit_price)
```

**Financials**:
```
received_goods_value   = received_qty * po_unit_price         (round to cents)
unreceived_goods_value = short_qty_vs_po * po_unit_price      (round to cents)
invoice_total          = invoice_subtotal + invoice_freight + invoice_tax
```

**Invoice status determination**:
- `on_hold` — when hold_code is present on the API invoice record
- `approved` — when no hold and three-way match passes
- `pending_receipt` — when no receipt exists for the PO

**Exception codes** (PascalCase, set order):
- `INVOICE_QTY_EXCEEDS_RECEIPT` — billed_qty > received_qty
- `PARTIAL_RECEIPT` — received_qty < ordered_qty
- `SUPPLIER_WATCH_RISK` — supplier has open risk events
- `PRICE_MISMATCH` — unit prices don't match across PO/contract/invoice
- `DAMAGE_REJECTION` — rejected_qty > 0
- `NO_EXCEPTION` — everything clean

**Decision mapping**:
- Receipt complete + no exceptions → `release_full_invoice`
- Partial receipt + qty variance → `accept_partial_hold_variance`
- Damage → `reject_batch` or `manual_recount_required`

### 5.3 AP Close Reconciliation (train_003 pattern)

**Per-invoice formulas**:
```
quantity_variance      = quantity_billed - quantity_received   (2 decimals)
quantity_variance_pct  = (quantity_variance / quantity_billed) * 100   (1 decimal)
net_balance_impact     = invoice_total - scheduled_payment_amount  (2 decimals)
```

**Hold/release decision**:
- `RELEASE` when: invoice is approved, no quantity variance, three-way match passes, payment scheduled
- `HOLD` when: any variance, missing receipt, invoice on hold, or no payment scheduled
- `release_to_payment = true` iff hold_decision == "RELEASE"

**Vendor balance**:
```
close_balance = opening_balance + invoice_total - scheduled_payments   (2 decimals)
```
- `opening_balance` defaults to `0.00` unless the task payload specifies otherwise.
- `held_invoice_total` = sum of invoice_totals where hold_decision == "HOLD"
- `releasable_invoice_total` = sum of invoice_totals where hold_decision == "RELEASE"
- Balance status: `FULLY_SCHEDULED` when close_balance == 0; `OPEN_HELD` when held_invoice_total > 0; `OPEN_APPROVED` when releasable but not fully scheduled.

**Program summary**: group invoice_decisions by program_id; sum counts and amounts per program.
**total_close_balance**: sum of all `net_balance_impact` across invoices (or sum of all `close_balance` across suppliers; they should match).

### 5.4 Change Control (train_004 pattern)

**Contract check**:
```
headroom_before_change = ceiling_amount - noncancelled_subtotal
requested_subtotal      = requested_quantity * unit_price
headroom_after_change   = headroom_before_change - requested_subtotal
ceiling_ok              = headroom_after_change >= 0
```
- `noncancelled_subtotal`: sum of (qty × unit_price) for all POs under the contract that are NOT cancelled. Exclude cancelled POs.

**Budget check**:
```
requested_tax           = requested_subtotal * (tax_rate_percent / 100)   (round to cents)
requested_total         = requested_subtotal + requested_tax              (freight only if memo provides it)
budget_after_change     = remaining_budget - requested_total
budget_ok               = budget_after_change >= 0
max_quantity_with_current_budget = floor(remaining_budget / (unit_price * (1 + tax_rate_percent / 100)))
```
- `remaining_budget` = `budget_cap - committed_amount` (from budget_snapshot API)

**Approval check**:
- `approval_ok = true` only when the latest approval event action is in the payload's `approval_good_actions` list (typically `["approved"]`).
- Other actions (`submitted`, `pending`, `rejected`) → `approval_ok = false`.

**Supplier risk check**:
- `supplier_risk_ok = true` unless there are **severe** open risk events. A "watch" rating alone does not block.
- Separate `open_event_ids` (all open) from `severe_open_event_ids` (only severe).

**Overall decision**: combine the four checks. If `budget_ok` and `approval_ok` both fail → `hold_for_budget_and_approval`. If only one fails → the corresponding single-hold variant. If `supplier_risk_ok` is false → `hold_for_supplier_risk`. All pass → `release_amendment`.

**Required actions**: derived from which checks fail:
- budget fail → `raise_budget_exception_or_reduce_quantity`
- approval fail → `obtain_final_requisition_approval`
- supplier risk fail → `resolve_supplier_risk_hold`
- all pass → `["none"]`

### 5.5 AP Release with Chargebacks (train_005 pattern)

**Chargeback amount**: `basis_quantity × unit_cost` (from the local chargeback register, not the API).

**Per-invoice release decision**:
```
net_release_amount = invoice_total - approved_chargeback_amount   (2 decimals)
```
- Only subtract **approved** chargebacks. Pending chargebacks do not reduce the net release amount.
- `approved_chargeback_amount` = sum of chargeback amounts where status == `approved` for that invoice.
- `pending_chargeback_amount` = sum of chargeback amounts where status == `pending_quality_review` for that invoice.

**Decision mapping**:
- Has approved chargebacks, everything else clear → `release_net_after_approved_chargeback`
- Has pending quality review → `hold_pending_quality_chargeback`
- No receipt exists → `hold_missing_receipt`
- Receipt exists, no issues → release

**Receiving exceptions**:
- Query the receipts endpoint for each receipt_id. Exception codes come from receipt inspection data (PascalCase: `Underage Quantity`, `Severe Unmatched Quantity`, `Inspection Hold`, `AP Quantity Variance`).
- `chargeback_status`: from chargeback register (`approved`, `pending_quality_review`, or `not_applicable` if no chargeback entry).
- `resolution_status`: `net_release_ready` if approved chargeback with no pending issues; `hold_for_quality_review` if pending; `missing_receipt` if no receipt for the PO; `accepted_no_receiving_exception` if clean.

**Missing receipt pattern**: When a PO has no receipt, emit a receiving_exception entry with:
```json
{"receipt_id": "MISSING:PO-XXXX", "po_id": "PO-XXXX", "exception_codes": [], "chargeback_status": "not_applicable", "resolution_status": "missing_receipt"}
```

**Summary totals**:
```
approved_chargeback_total = sum of all approved chargeback amounts
pending_chargeback_total  = sum of all pending chargeback amounts
net_release_total         = sum of net_release_amount across all release decisions
```

## 6. Arithmetic Checks (Post-Computation Validation)

Before finalizing any answer, verify:
- **Sum coherence**: subtotals should sum to totals (`invoice_subtotal + freight + tax == invoice_total`).
- **Balance identity**: per-supplier `close_balance` should equal `opening_balance + invoice_total - scheduled_payments`.
- **Cross-check**: `total_close_balance` (sum of close_balances) should equal sum of `net_balance_impact` across invoices.
- **Quantity logic**: `received_qty + rejected_qty ≤ ordered_qty`; `short_qty_vs_po = ordered_qty - received_qty`; `unreceived_billed_qty ≤ short_qty_vs_po` when billed_qty ≤ ordered_qty.
- **Completion ratio**: must be in [0, 1].
- **Headroom**: `headroom_after_change = headroom_before_change - requested_subtotal`; verify `ceiling_amount - noncancelled_subtotal - requested_subtotal == headroom_after_change`.
- **Budget**: `budget_after_change = remaining_budget - requested_total`; if `budget_ok` is false, `budget_after_change` must be negative.
- **Chargeback netting**: `net_release_amount = invoice_total - approved_chargeback_amount`. Pending chargebacks do NOT reduce net_release_amount.
- **Variance pct**: `(variance / billed) * 100`, rounded to 1 decimal. Division by zero → 0.0 when billed_qty is 0.

## 7. Output Schema Pitfalls

- **`commercial_basis_id`**: use `null` (JSON null, not the string "null") when no contract links the SKU to the supplier.
- **`hold_code`**: use `null` when the invoice is not on hold. Use the exact hold code string from the API otherwise.
- **`severe_open_event_ids`**: a separate list from `open_event_ids`. Only include severe-rated events. A "watch" rating is not severe.
- **`excluded_same_po_receipt_ids`**: receipts on the same PO that are NOT part of the current review scope. List them explicitly; empty array if none.
- **`receipt_ids_in_scope`**: receipts actually being reviewed for this invoice.
- **`blocker_codes`**: always sorted ascending. Always use the exact snake_case strings from the allowed list (e.g., `late_due_date`, not `late_due` or `LATE_DUE_DATE`).
- **`exception_codes`**: PascalCase for receiving/invoice exceptions (`INVOICE_QTY_EXCEEDS_RECEIPT`, `Underage Quantity`). Case must match the template exactly.
- **`evidence.endpoint_record_ids`**: include every entity ID you queried from the API (contracts, POs, receipts, invoices, suppliers, items, risk events, budget snapshots). These are the "source record IDs you used."
- **`task_payloads_reviewed`**: list the relative paths of all payload files you read.

## 8. Task-Type Quick Index

| Template pattern | Task type | Key endpoints to query | Special local data |
|---|---|---|---|
| `nomination_lines`, `committee_action` | Sourcing readiness | programs, suppliers, items, contracts, requisitions, purchase_orders, receipts, invoices, vendor_risk_events | Memo names package anchors |
| `line_reconciliation`, `invoice_review` | Receiving closeout | purchase_orders, receipts, invoices, contracts, suppliers, vendor_risk_events | Memo names batch ID |
| `invoice_decisions`, `vendor_balances` | AP close | invoices, purchase_orders, receipts, payments, suppliers, budget_snapshots | Memo names invoice IDs; opening_balance defaults to 0 |
| `contract_check`, `program_budget_check` | Change control | contracts, purchase_orders, programs, requisitions, approval_events, budget_snapshots, suppliers, vendor_risk_events | JSON memo with tax rate, approval_good_actions |
| `release_decisions`, `receiving_exceptions` | AP release | purchase_orders, receipts, invoices, suppliers | JSON packet with chargeback register (local source for chargeback amounts) |

## 9. Exclusion Rules

- **Future records**: Any record with a date after `as_of_date`/`close_date`/`review_as_of` is out of scope.
- **Cancelled POs**: Exclude from contract noncancelled_subtotal and from active PO lists. Track separately as `excluded_cancelled_po_ids` when the template calls for it.
- **Unrelated programs/suppliers**: Only include records linked to the target program(s) or supplier(s) named in the task payload.
- **Non-target invoices/receipts**: When the task names specific invoice IDs or receipt IDs, do not include others in the answer, even if they belong to the same PO/program.
