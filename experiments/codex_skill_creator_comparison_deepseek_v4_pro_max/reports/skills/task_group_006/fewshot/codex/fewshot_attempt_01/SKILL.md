---
name: procureops-finops
description: Structured analysis of ProcureOps procurement and financial-operations data through a shared REST API. Use when the task is to produce a machine-readable JSON answer (reconciliation, nomination, change-control, AP close, or receiving-release file) from ProcureOps API records and task-local memos. The API exposes suppliers, items, programs, contracts, purchase requisitions, purchase orders, receipts, AP invoices, AP payments, approvals, budget snapshots, and vendor risk events. All amounts are in USD.
---

# ProcureOps FinOps Analysis

## Quick start

1. Read the task prompt and any task-local payload files (memos, templates, registers).
2. Pull all relevant endpoint data from `<TASK_ENV_BASE_URL>` in a single batch of parallel fetches.
3. Cross-reference records across endpoints using the entity relationship map.
4. Apply the calculation patterns below to produce the required numeric values.
5. Return only valid JSON matching the supplied answer template. No prose outside the JSON.

## Endpoints

Fetch all relevant endpoints in parallel the first time. Re-fetch only when additional data is needed.

- `GET /manifest` -- record counts, anchor IDs, environment metadata
- `GET /suppliers` -- supplier profiles, risk ratings, payment terms
- `GET /items` -- SKU catalog, preferred suppliers, standard costs
- `GET /programs` -- budget caps, committed amounts, owners, status
- `GET /contracts` -- pricing, ceilings, suppliers, status
- `GET /purchase_requisitions` -- demand signals, quantities, approval status
- `GET /purchase_orders` -- orders with lines, totals, requisition and contract links
- `GET /receipts` -- warehouse receipts with line-level received/rejected quantities
- `GET /ap/invoices` -- supplier invoices, hold codes, receipt linkage
- `GET /ap/payments` -- scheduled/released/blocked payments against invoices
- `GET /approvals` -- requisition and PO approval events
- `GET /budget_snapshots` -- point-in-time budget snapshots
- `GET /vendor_risk_events` -- supplier risk events with severity and status

Full field schemas: [references/api_models.md](references/api_models.md).

## Cross-referencing rules

When a task identifies specific entities (programs, SKUs, POs, receipts, invoices), narrow API results to those entities before building the answer. Follow the relationship chains:

- **Supplier lookup**: Join via `supplier_id` on contracts, POs, receipts, invoices, payments, risk events.
- **Contract lookup**: Join via `contract_id` on POs. Match by `sku` + `supplier_id` + `program_id` when `contract_id` is null on a PO.
- **PO chain**: `requisition_id` links to requisitions; `program_id` links to programs; `contract_id` links to contracts.
- **Receipt chain**: `po_id` links to POs; `supplier_id` links to suppliers.
- **Invoice chain**: `po_id` links to POs; `receipt_id` links to receipts (may be null); `supplier_id` links to suppliers.
- **Payment chain**: `invoice_id` links to invoices; `supplier_id` links to suppliers.
- **Approval chain**: `object_id` links to requisitions or POs when `object_type` matches.
- **Risk chain**: `supplier_id` links to suppliers; `related_object_id` links to POs.
- **Budget chain**: `program_id` links to programs.

## Calculation patterns

See [references/api_models.md](references/api_models.md) for detailed formulas. Key patterns:

### Receipt reconciliation

Sum `quantity_received` across all receipts for a given PO line. `received_qty` is the sum; `rejected_qty` is the sum of rejected. `short_qty_vs_po = ordered_qty - received_qty`. `unreceived_billed_qty = billed_qty - received_qty` (clamped to 0 minimum). `receipt_completion_ratio = received_qty / ordered_qty`.

### Three-way match

For each PO line compare ordered, received, and billed quantities. A variance triggers a hold when `billed_qty > received_qty`. Invoice status `on_hold` with `hold_code == "QTY_VARIANCE"` confirms this.

### Contract ceiling

Sum non-cancelled PO subtotals under the contract. `headroom = ceiling_amount - noncancelled_subtotal`. `ceiling_ok` when headroom covers the requested change.

### Program budget

Use budget snapshot matching the task's as_of_date when available. `remaining = budget_cap - committed_amount`. Budget is not ok when the requested total (subtotal + tax) exceeds remaining.

### AP close reconciliation

For each supplier in scope, `close_balance = opening_balance + invoice_total - scheduled_payments`. Only payments with `status == "scheduled"` count; `released` and `blocked` do not. `scheduled_payment_amount` per invoice is the amount from the matching payment record(s). Split `held_invoice_total` and `releasable_invoice_total` by invoice status.

### Chargeback netting

`net_release_amount = invoice_total - approved_chargeback_amount`. When pending chargebacks exist, `net_release_amount = 0` regardless of approved chargebacks.

### Approval check

Find the latest approval event for the requisition by `event_date`. `approval_ok` is true only when the latest action is `"approved"`. If the latest action is `"submitted"`, `"returned"`, `"rejected"`, or `"escalated"`, the requisition is not approved.

### Supplier risk

Check supplier `risk_rating` and open risk events. `supplier_risk_ok` is false only when the supplier has `risk_rating == "watch"` AND at least one open event with `severity == "high"`. All open risk events should be listed; monitoring events should be listed as well.

## Blocker code rules

Derive blocker codes from API evidence:

- `missing_contract` -- PO has `contract_id == null` and no active contract exists for that SKU/supplier/program
- `supplier_watch` -- supplier `risk_rating == "watch"` (with or without severe events)
- `open_supplier_risk` -- any open risk event exists for the supplier
- `ap_hold` -- invoice `status == "on_hold"` or `status == "pending_receipt"`
- `pending_receipt` -- PO status is `"open"` or `"partial_receipt"` and expected receipt is not fully recorded
- `late_due_date` -- PO `due_date` is before `as_of_date` and PO status is not `"received"` or `"cancelled"`
- `none` -- none of the above apply

Sort blocker codes ascending alphabetically per nomination line.

## Nomination readiness

`readiness_status` per line:
- `ready` -- no blockers
- `at_risk` -- supplier_watch only (no other blockers)
- `not_ready` -- any other blocker present

`overall_readiness` for the program:
- `ready` -- all lines are `ready`
- `at_risk` -- no `not_ready` lines, but at least one `at_risk`
- `not_ready` -- any line is `not_ready`

## Decision rules

### Sourcing committee action

- `nominate_now` -- readiness is `ready`
- `conditional_nomination` -- readiness is `at_risk`
- `hold` -- readiness is `not_ready`
- `send_to_committee` is `"yes"` when any line is `at_risk` or `not_ready`, `"no"` otherwise
- `next_owner` defaults to `"buyer"` unless action is blocked by AP or quality controls, in which case use `"ap_team"` or `"quality_ops"` as appropriate

### Invoice hold/release

- `HOLD` when any quantity or receipt variance exists (billed > received, or no receipt)
- `RELEASE` when three-way match passes and a scheduled payment exists
- `hold_code` from the invoice record; null when released
- `reason_codes` from the template's allowed set; sort alphabetically

### Receiving disposition

- `accept_partial_hold_variance` -- receipt exists, partial receipt, quantity variance present
- Keep invoice on hold when there is a QTY_VARIANCE or unreceived-billed gap
- Request credit or remaining delivery from supplier for the shortage

### Change-control decision

- `release_amendment` -- all checks pass
- `hold_for_budget_and_approval` -- both budget_ok and approval_ok are false
- `hold_for_budget` -- only budget_ok is false
- `hold_for_approval` -- only approval_ok is false
- `hold_for_supplier_risk` -- only supplier_risk_ok is false
- `reject_contract_mismatch` -- ceiling_ok is false or contract is not active

### AP release file decisions

- `release_net_after_approved_chargeback` -- approved chargeback exists, no pending chargeback
- `hold_missing_receipt` -- no receipts found for the PO
- `hold_pending_quality_chargeback` -- pending chargeback exists

## Output formatting

- Return only the JSON object. No markdown fences, no prose, no trailing text.
- All USD amounts: round to 2 decimal places (`round(x, 2)`).
- All ratios: round to 4 decimal places unless the template specifies otherwise.
- All percentages: round to 1 decimal place.
- List fields: treat as sets unless the template specifies sorting. Sort ID lists ascending (string sort). Sort codes/reason lists ascending.
- Use `null` for absent values (not `""` or `"null"`), except when the template explicitly expects a string.
- `program_budget_check.max_quantity_with_current_budget`: integer floor of the maximum feasible quantity.
- `"as_of_date"` comparisons: exclude records dated strictly after the cutoff.
