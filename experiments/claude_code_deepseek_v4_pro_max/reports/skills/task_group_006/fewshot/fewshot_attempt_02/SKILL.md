# ProcureOps Task Group SKILL

## Environment

- **Base URL**: Use the URL from `environment_access.md` (`GDPEVO_ENV_BASE_URL`). This overrides any `localhost:8006` or `127.0.0.1:8006` references in task text. Do NOT start a local env or run setup scripts.
- **API endpoints**: `/programs`, `/suppliers`, `/items`, `/contracts`, `/purchase_requisitions`, `/purchase_orders`, `/receipts`, `/ap/invoices`, `/ap/payments`, `/approval_events`, `/budget_snapshots`, `/vendor_risk_events`.

## Source Precedence

1. **ProcureOps API is always authoritative** for live operational records (programs, suppliers, items, contracts, requisitions, POs, receipts, invoices, payments, approvals, budgets, vendor risk).
2. **Task payloads** (memos, JSON packets) provide task-specific context — target IDs, business parameters, chargeback registers — but never override API data.
3. **Answer template** (`answer_template.json`) defines the exact output schema. Match it precisely — do not add or omit keys.
4. **as_of_date / as-of cutoff**: Filter API records to those dated on or before the task's cutoff date. Receipts, invoices, approvals, risk events — all are time-gated.

## Field Conventions

- **Currency**: All amounts in USD, rounded to cents (2 decimal places) unless the template specifies a different precision (e.g., `receipt_completion_ratio` uses 4 decimal places).
- **List ordering**: Sort IDs/values ascending unless the template says "set" (then order doesn't matter; the evaluator sorts).
- **Null vs empty**: Use `null` for absent single values (e.g., `commercial_basis_id`, `hold_code`), empty arrays `[]` for absent lists.
- **Dates**: Always `YYYY-MM-DD` string format.
- **Percentages**: Store as numbers, not strings. `quantity_variance_pct` rounds to 1 decimal. `receipt_completion_ratio` rounds to 4 decimals.
- **task_id**: Copy the expected value from the template's `required_value` if specified, or derive from task context.

## Reusable Business Rules

### Contract Checks
- **Noncancelled subtotal**: Sum PO line subtotals for the contract, **excluding cancelled POs**.
- **Headroom before change** = `ceiling_amount` - `noncancelled_subtotal`.
- **Requested subtotal** = `requested_quantity` × `unit_price`.
- **Headroom after change** = `headroom_before_change` - `requested_subtotal`.
- **Contract ceiling exposure** = line subtotal only (before tax and freight).
- **ceiling_ok** = `headroom_after_change >= 0`.

### Budget Checks
- **Budget cap** and **committed_amount** come from the budget snapshot (`/budget_snapshots`).
- **Remaining budget** = `budget_cap` - `committed_amount`.
- **Requested tax** = `requested_subtotal` × `tax_rate_percent / 100`, unless tax rate is 0 or the memo omits tax.
- **Requested total** = `requested_subtotal` + `requested_tax` (add freight only if the memo explicitly provides a freight value).
- **Budget after change** = `remaining_budget` - `requested_total`.
- **budget_ok** = `budget_after_change >= 0`.
- **max_quantity_with_current_budget** = floor( (`remaining_budget` / (1 + tax_rate/100)) / `unit_price` ). Only include tax rate in the denominator if tax applies.

### Approval Check
- `/approval_events` filtered by requisition/program. Look at the **latest event** by date.
- **approval_ok** = `latest_action == "approved"` (NOT "submitted", "pending", or any other state).
- The list of valid approval-good actions is in the task memo's `approval_good_actions` if provided.

### Supplier Risk Check
- Query `/vendor_risk_events` for the supplier. Filter to **open** events (status is not closed/resolved).
- **supplier_risk_ok** = no open **severe** events exist. A "watch" rating alone is NOT a blocker — it's context only.
- **Severe events** are events with a severity field of "high" or "critical".

### Purchase Order Reconciliation
- Fetch all POs for the program/supplier/contract from `/purchase_orders`.
- Cancelled POs: exclude from contract consumption. List them separately under `excluded_cancelled_po_ids`.
- Active/noncancelled POs: list under `included_po_ids`.

### Receipt Reconciliation
- Fetch receipts from `/receipts` for a given PO or batch. Filter to `receipt_date <= as_of_date`.
- **received_qty** = sum of accepted quantities across receipts for the PO line.
- **rejected_qty** = sum of rejected quantities.
- **short_qty_vs_po** = `ordered_qty` - `received_qty`.
- **receipt_completion_ratio** = `received_qty / ordered_qty` (4 decimal places).
- **unreceived_billed_qty** = `billed_qty` - `received_qty` (clamped to ≥ 0 conceptually; if negative there's a data issue).
- **Received goods value** = `received_qty × unit_price`.
- **Unreceived goods value** = `short_qty_vs_po × unit_price`.
- **Contract price match**: true when `po_unit_price == contract_unit_price == invoice_unit_price`, else false.

### Invoice / AP Rules
- Fetch invoices from `/ap/invoices`.
- **quantity_billed** = invoice's billed quantity.
- **quantity_variance** = `quantity_billed` - `quantity_received`.
- **quantity_variance_pct** = (`quantity_variance` / `ordered_qty`) × 100, rounded to 1 decimal.
- **invoice_total** = the full invoiced amount from the API (includes freight + tax).
- **scheduled_payment_amount**: Sum payments from `/ap/payments` for the invoice where `scheduled_date <= as_of_date` (or through the close period, e.g., 2026-06-30). Use 0.00 if no payments scheduled.
- **net_balance_impact** = `invoice_total` - `scheduled_payment_amount`.
- **Invoice statuses**: `approved`, `on_hold`, `pending_receipt`, `paid`.
- **Hold decision**: `RELEASE` when invoice is approved with no variance issues; `HOLD` when there's a hold code, quantity variance, or missing receipt.

### Invoice Exception Codes
- `INVOICE_QTY_EXCEEDS_RECEIPT` — billed > received.
- `PARTIAL_RECEIPT` — receipt exists but received < ordered.
- `SUPPLIER_WATCH_RISK` — supplier has a watch rating (contextual, from risk data).
- `PRICE_MISMATCH` — contract/PO/invoice unit prices don't match.
- `DAMAGE_REJECTION` — rejected_qty > 0.
- `NO_EXCEPTION` — no issues found.

### Chargeback Handling (train_005 pattern)
- A separate chargeback register in the task payload provides approved/pending chargebacks.
- **approved_chargeback_amount** = sum of chargebacks with status `approved` for this invoice.
- **pending_chargeback_amount** = sum of chargebacks with status `pending_quality_review` for this invoice.
- **net_release_amount** = `invoice_total` - `approved_chargeback_amount`. Only positive when there are approved offsets.
- **decision**: `release_net_after_approved_chargeback` when approved chargebacks exist and no pending issues remain; `hold_pending_quality_chargeback` when chargebacks are still pending; `hold_missing_receipt` when no receipt exists.

### Vendor Balance Reconciliation
- **opening_balance**: Use the value stated in the task memo (typically 0.00 for a fresh close slice).
- **invoice_total** = sum of all target invoices for that supplier.
- **scheduled_payments** = sum of scheduled payments for those invoices.
- **close_balance** = `opening_balance` + `invoice_total` - `scheduled_payments`.
- **held_invoice_total** = sum of invoice_totals where hold_decision is HOLD.
- **releasable_invoice_total** = sum of invoice_totals where hold_decision is RELEASE.
- **balance_status**: `FULLY_SCHEDULED` when close_balance == 0, `OPEN_HELD` when held_invoice_total > 0 and releasable == 0, `OPEN_APPROVED` when releasable > 0.

### Blocker Codes (Nomination Readiness)
Sorted ascending. Possible values:
- `missing_contract` — no contract found for the SKU/supplier (commercial_basis_id is null).
- `supplier_watch` — supplier has a watch risk rating.
- `open_supplier_risk` — supplier has open (unresolved) vendor risk events.
- `ap_hold` — invoice is on hold or has exceptions.
- `pending_receipt` — no receipt evidence exists for the PO line.
- `late_due_date` — PO due date is before the as_of_date and not fully received.
- `none` — no blockers.

### Nomination Decision Logic
- **nominate**: No blockers exist; readiness is `ready`.
- **conditional_nomination**: Only minor/warning blockers (e.g., supplier_watch, ap_hold with approved chargeback); readiness is `at_risk`.
- **hold**: Any hard blocker (missing_contract, open_supplier_risk with severe events, pending_receipt for billed invoices, late_due_date); readiness is `not_ready`.

### Committee Action
- `nominate_now_supplier_ids`: suppliers with decision `nominate`.
- `conditional_supplier_ids`: suppliers with decision `conditional_nomination`.
- `hold_supplier_ids`: suppliers with decision `hold`.
- `next_owner`: The team that owns the next action — `buyer` (contract issues), `finance_ops` (budget issues), `quality_ops` (inspection/receiving issues), `program_owner` (none/minor issues), `ap_team` (invoice/payment issues).
- `send_to_committee`: `yes` when any supplier is in `nominate` or `conditional_nomination`; `no` when all are `hold`.

### Decision Composition (Change Control)
- Start with `release_amendment`; downgrade based on failed checks.
- If `!budget_ok && !approval_ok` → `hold_for_budget_and_approval`.
- If `!budget_ok` only → `hold_for_budget`.
- If `!approval_ok` only → `hold_for_approval`.
- If `!supplier_risk_ok` → `hold_for_supplier_risk`.
- If contract ceiling exceeded → `reject_contract_mismatch`.

### Required Actions (Change Control)
Sorted ascending. Derived from failed checks:
- Budget fails → `raise_budget_exception_or_reduce_quantity`.
- Approval fails → `obtain_final_requisition_approval`.
- Supplier risk fails → `resolve_supplier_risk_hold`.
- All clear → `none`.

### Receiving Exception Codes (train_005 pattern)
- `Underage Quantity` — received < ordered.
- `Severe Unmatched Quantity` — large variance or zero receipt.
- `Inspection Hold` — quality review pending.
- `AP Quantity Variance` — billing vs receipt variance.

### Follow-up Actions (train_005 pattern)
- `post_approved_chargeback_netting` — when approved chargebacks exist, net them against payment.
- `route_po00031_quality_review` — when a quality review is pending.
- `ask_receiving_for_vantix_receipt` — when an invoice has no receipt at all.
- `hold_luma_duplicate_receipt_for_separate_invoice` — when a receipt is linked to a different invoice.

## Arithmetic Checks (Validate Before Output)

1. `headroom_before_change - requested_subtotal == headroom_after_change`
2. `remaining_budget - requested_total == budget_after_change`
3. `received_qty + short_qty_vs_po == ordered_qty`
4. `received_goods_value + unreceived_goods_value == ordered_qty × unit_price` (or close within rounding)
5. `invoice_total - scheduled_payment_amount == net_balance_impact`
6. `opening_balance + invoice_total - scheduled_payments == close_balance`
7. `held_invoice_total + releasable_invoice_total == invoice_total` (per supplier)
8. `invoice_total - approved_chargeback_amount == net_release_amount`
9. `approved_chargeback_total` = sum of all approved chargeback amounts across invoices
10. `net_release_total` = sum of all net_release_amounts across invoices
11. Program summary: `held_total + released_total == invoice_total` for that program

## Output Schema Pitfalls

- Always include ALL required top-level keys from the template, even if empty/null.
- Match enum values exactly — case-sensitive. E.g., `"not_ready"` not `"Not Ready"`.
- `blocker_codes`: sorted ascending; use `["none"]` (single-element array) when no blockers, NOT `[]` or `null`.
- `exception_codes`: sorted ascending or treated as set per template. Include `"NO_EXCEPTION"` only when truly no exceptions exist.
- `receipt_evidence_ids`: empty array `[]` when no receipts exist, NOT `null`.
- `commercial_basis_id`: `null` when no contract exists, NOT `""`.
- `hold_code`: `null` when invoice is not on hold, NOT `""`.
- `evidence.endpoint_record_ids`: list all API record IDs you queried to produce the answer, sorted ascending.
- `evidence.task_payloads_reviewed`: list payload file paths you consumed, sorted ascending.

## Exclusion Rules

- Exclude cancelled POs from contract consumption and included_po_ids. List them under excluded_cancelled_po_ids.
- Exclude receipts/invoices/risk events dated after the as_of_date.
- Exclude suppliers not named in the task scope.
- Filter to the specific invoice IDs, PO IDs, or receipt IDs named in the task, unless the template explicitly asks for all related records.
- Do not include narrative explanations — return only the JSON object matching the template.
- Do not include `task_id` values from the train data — derive from the actual task context.

## API Query Pattern

For each task, determine which entities you need, then fetch hierarchically:
1. **Program** → lookup by program_id → get owner, budget info.
2. **Items/SKUs** → identify the SKUs in scope.
3. **Suppliers** → lookup by supplier_id → get name, status, risk_rating.
4. **Contracts** → match by SKU+supplier → get price_type, unit_price, ceiling_amount.
5. **Purchase Requisitions** → filter by program+SKU.
6. **Purchase Orders** → filter by program/contract/requisition → exclude cancelled.
7. **Receipts** → filter by PO → respect as_of_date.
8. **Invoices** (`/ap/invoices`) → filter by PO or invoice_id list.
9. **Payments** (`/ap/payments`) → filter by invoice_id, scheduled through the close date.
10. **Approval Events** → filter by requisition → find latest by date.
11. **Budget Snapshots** → filter by program → get cap and committed.
12. **Vendor Risk Events** → filter by supplier → isolate open events → check severity.

Always verify record linkage: invoice→PO→receipt→contract chains must be consistent. If the API returns an ID that doesn't match the task's scope, confirm it's the right record before using its data.
