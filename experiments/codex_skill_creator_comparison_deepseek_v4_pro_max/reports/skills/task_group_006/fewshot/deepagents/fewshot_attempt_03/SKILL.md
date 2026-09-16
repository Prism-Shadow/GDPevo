---
name: procureops
description: "ProcureOps procurement reconciliation tasks: nomination readiness packets, receiving closeout reviews, AP payment-hold reconciliations, modular change-control decisions, and AP release/hold exception reviews. Use when the task references a TASK_ENV_BASE_URL ProcureOps API, a local answer_template.json, and needs to cross-reference purchase orders, receipts, invoices, contracts, suppliers, budgets, approvals, vendor risk events, and local payloads (memos, chargeback registers, release packets) to produce structured JSON decisions. Triggers on procurement-readiness, receiving-control, AP-close, change-control, and AP-release tasks."
---

# ProcureOps Reconciliation

## Overview

This skill covers ProcureOps procurement reconciliation: cross-referencing live API records (POs, receipts, invoices, contracts, suppliers, budgets, approvals, risk events) with local payload files to produce structured JSON answer files following a provided answer template. Five task patterns are documented below; each shares the same API but differs in the entities joined and the decision logic.

## Core Workflow

Every task follows this pattern:

1. Read the task prompt and all local payloads (memos, JSON packets, chargeback registers, answer templates).
2. Fetch all relevant data from `<TASK_ENV_BASE_URL>`. Pull full lists from every needed endpoint and filter in-process.
3. Cross-reference entities using the ID graph in [domain_model.md](references/domain_model.md). Use [api_endpoints.md](references/api_endpoints.md) for field-by-field endpoint documentation and lookup patterns.
4. Populate the answer template exactly. The template's `type` hints, `allowed_values`, `required_keys`, and ordering rules are the authoritative output spec.
5. Return only the JSON object — no prose outside it unless the prompt explicitly says otherwise.

## Task Patterns

### 1. Nomination Readiness Packet

Given a program ID, an as-of date, and a list of package-line SKUs with their POs and requisitions, produce a readiness assessment for each line.

**Entities joined:** Supplier, Item, Program, Contract, PO, Requisition, Receipt, Invoice, Vendor Risk Event, Budget Snapshot.

**Logic per nomination line:**
- Identify the nominated supplier from `po.supplier_id`.
- Check for a contract: if `po.contract_id` is null, add `missing_contract`.
- Check invoice status: `on_hold` triggers `ap_hold`; `pending_receipt` triggers `pending_receipt`.
- Collect receipt IDs on that PO with `receipt_date <= as_of_date`.
- Check risk events: open or monitoring events for the supplier trigger `open_supplier_risk`. If supplier `risk_rating` is watch and no severe open events exist, also add `supplier_watch`.
- Check due date: if `po.due_date < as_of_date` and PO is not fully received, add `late_due_date`.
- Overall readiness: `ready` if empty blockers or only `none`, `at_risk` if only `supplier_watch`, `not_ready` otherwise.
- Nomination decision: `nominate` for ready, `conditional_nomination` for at_risk, `hold` for not_ready.
- Budget headroom: `program.budget_cap - program.committed_amount`.
- `commercial_basis_id`: the active contract ID for the SKU/program, or null if none.

### 2. Receiving Closeout Review

Given a target receipt batch ID and a supporting memo, reconcile received vs ordered vs billed, check the AP hold position, compute dollar exposure, and produce a controlled disposition.

**Entities joined:** Receipt, PO, Contract, Invoice, Supplier, Vendor Risk Event.

**Logic:**
- Pull the receipt by ID, its PO, the contract linked to the PO, invoices on that PO, and supplier risk events.
- Per PO line: ordered_qty from PO lines, received_qty and rejected_qty from receipt lines, billed_qty from invoice lines.
- `short_qty_vs_po = ordered_qty - received_qty`.
- `unreceived_billed_qty = max(0, billed_qty - received_qty)`.
- `receipt_completion_ratio = received_qty / ordered_qty`, rounded to 4 decimal places.
- Compare `po_unit_price`, `contract_unit_price`, `invoice_unit_price` to determine `contract_price_match` (true if all equal).
- Exception codes: `INVOICE_QTY_EXCEEDS_RECEIPT` if billed > received; `PARTIAL_RECEIPT` if received < ordered; `SUPPLIER_WATCH_RISK` if supplier has open risk events; `PRICE_MISMATCH` if prices diverge; `DAMAGE_REJECTION` if rejected_qty > 0; `NO_EXCEPTION` if none apply.
- Financials: `received_goods_value = received_qty * po_unit_price`; `unreceived_goods_value = (ordered_qty - received_qty) * po_unit_price`. Use invoice subtotal, freight, tax, total from the API invoice record.
- Disposition: `accept_partial_hold_variance` if variance exists but receipt accepted; `release_full_invoice` if no variance and three-way match clean; `reject_batch` if rejection exists; `manual_recount_required` only if inspection pending.

### 3. AP Payment-Hold Reconciliation (Close Slice)

Given target invoice IDs, a close date, and a memo setting opening balances to 0 for the slice, produce invoice-level hold/release decisions, supplier balances, and program summaries.

**Entities joined:** Invoice, PO, Receipt, Supplier, Payment, Budget Snapshot.

**Logic:**
- For each target invoice: pull its PO, supplier, all receipts for that PO, and payments for that invoice.
- `quantity_billed` from invoice lines; `quantity_received` from summing all receipt lines for that PO (0.00 if no receipt exists).
- `quantity_variance = quantity_billed - quantity_received`.
- `quantity_variance_pct = (quantity_variance / po_line.quantity) * 100`, rounded to 1 decimal.
- Hold decision: `RELEASE` if invoice status is `approved`; `HOLD` otherwise.
- `release_to_payment`: true only if hold decision is `RELEASE`.
- Reason codes: `APPROVED_THREE_WAY_MATCH` if all three align; `SCHEDULED_PAYMENT_FOUND` if any scheduled/released payment exists for the invoice; `NO_RECEIPT` if no receipt; `QTY_VARIANCE` if quantity mismatch.
- Vendor balances: group by supplier. `opening_balance` is 0.00 per memo. Sum invoice totals, scheduled payments (scheduled or released status only), held totals (HOLD invoices), releasable totals (RELEASE invoices). `close_balance = opening_balance + invoice_total - scheduled_payments`. `balance_status`: `FULLY_SCHEDULED` if close_balance is 0; `OPEN_HELD` if all invoices held; `OPEN_APPROVED` if some releasable.
- Program summary: group by program_id; sum invoice_count, invoice_total, held_total, released_total, net_close_balance.
- `payment_hold_queue`: invoice_ids where hold_decision is `HOLD`.
- `payment_release_queue`: invoice_ids where hold_decision is `RELEASE`.
- `total_close_balance`: sum of all close_balances.

### 4. Modular Change-Control Decision

Given a change memo (JSON) for a contract variant buy, determine whether the amendment can be released.

**Entities joined:** Contract, Program, Budget Snapshot, Requisition, Approval, Supplier, PO, Vendor Risk Event.

**Logic:**
- Contract check: Pull all POs for the contract_id. Exclude cancelled POs. Sum non-cancelled subtotals. `headroom_before_change = ceiling_amount - noncancelled_subtotal`. `requested_subtotal = requested_quantity * contract.unit_price`. `headroom_after_change = headroom_before_change - requested_subtotal`. `ceiling_ok = headroom_after_change >= 0`.
- Budget check: Pull latest budget_snapshot for program. `remaining_budget = budget_cap - committed_amount`. `requested_tax = requested_subtotal * (tax_rate_percent / 100)`. `requested_total = requested_subtotal + requested_tax` (add freight only if the memo provides freight for this line). `budget_after_change = remaining_budget - requested_total`. `budget_ok = budget_after_change >= 0`. `max_quantity_with_current_budget` = floor of `remaining_budget / (unit_price * (1 + tax_rate_percent / 100))`.
- Approval check: Find latest approval event for source requisition. `approval_ok` only if latest action is `approved`.
- Supplier risk: Pull open/monitoring events for supplier. `supplier_risk_ok` = no severe open events.
- Decision: `reject_contract_mismatch` if contract mismatch; `hold_for_budget_and_approval` if both fail; `hold_for_budget` if only budget fails; `hold_for_approval` if only approval fails; `hold_for_supplier_risk` if supplier risk fails; `release_amendment` if all pass.

### 5. AP Release/Hold Exception Review

Given an AP release packet with target POs, receipts, invoices, and a chargeback register, produce per-invoice release/hold decisions with net amounts and per-receipt exception classifications.

**Entities joined:** PO, Receipt, Invoice, Supplier, plus local chargeback register.

**Logic:**
- The local chargeback register is authoritative for chargeback amounts and statuses — use it, not any API field.
- For each invoice: match to its PO and all receipts on that PO. Identify in-scope receipts (those matching `invoice.receipt_id` or all same-PO receipts if no direct match). Exclude same-PO receipts not linked to this invoice.
- Decision: `release_net_after_approved_chargeback` if an approved chargeback exists and all chargebacks are approved; `hold_missing_receipt` if no receipt exists for the PO; `hold_pending_quality_chargeback` if a chargeback is pending quality review.
- Net release: `invoice_total - approved_chargeback_amount` (pending chargebacks do not reduce the release).
- For receiving exceptions: classify each receipt with exception codes (Underage Quantity, Severe Unmatched Quantity, Inspection Hold, AP Quantity Variance) based on inspection status, quantity gaps, and chargeback reason codes.
- Missing receipts represented as `MISSING:<po_id>`.
- Summary: authoritative sources are the API data and local chargeback register. Supporting-only sources are release request notes and alias notes.

## Currency and Rounding

All amounts in USD. Round to cents (2 decimal places) unless the template specifies otherwise. `receipt_completion_ratio` rounds to 4 decimal places. `quantity_variance_pct` rounds to 1 decimal place.

## List Ordering

Sort ID lists ascending unless the template specifies a different order. For set semantics (evaluator sorts), use ascending sort on the primary identifier.

## Resources

- [api_endpoints.md](references/api_endpoints.md) — Field-level documentation for every endpoint, plus lookup patterns for common cross-referencing operations.
- [domain_model.md](references/domain_model.md) — Entity relationship graph, key concepts (three-way match, contract ceiling, budget headroom, blocker codes, status codes), and cross-entity reconciliation patterns.
- [fetch_data.py](scripts/fetch_data.py) — Bulk data fetch helper. Run `python3 scripts/fetch_data.py <TASK_ENV_BASE_URL>` to pull all endpoints into a single JSON file, then load and filter in-process.
