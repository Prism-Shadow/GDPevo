---
name: procureops-json-solver
description: Solve ProcureOps task-environment questions that require a strict JSON answer from purchasing, receiving, AP invoice/payment, supplier-risk, budget, approval, contract, sourcing nomination, change-control, or chargeback records. Use this when a prompt mentions the ProcureOps API, TASK_ENV_BASE_URL, purchase orders, receipts, AP holds, supplier risk, contract amendments, release files, or answer_template.json.
---

# ProcureOps JSON Solver

## Core Workflow

1. Read the user prompt, every local payload, and `answer_template.json` before fetching records. Treat the template as the output contract: required keys, enum spellings, sorting rules, precision, nullability, and whether list fields are sets.
2. Extract the task slice from the payloads: target dates, program IDs, PO IDs, receipt IDs, invoice IDs, requisition IDs, contract IDs, supplier IDs, SKUs, quantities, tax rates, and any local registers or notes.
3. Fetch ProcureOps records from the base URL supplied by the runner. The local memo usually names anchors; the API is the system of record unless the prompt explicitly makes a local payload authoritative for a control table such as a chargeback register.
4. Join records through IDs, calculate fields from source records, and classify decisions using the controlled values in the template. Do not rely on narrative shortcuts when a source record can verify the value.
5. Return only the final JSON object. Use JSON numbers for amounts and quantities, `null` where the template permits null, and no prose outside the object.

The helper script can snapshot the public API without external dependencies:

```bash
python scripts/fetch_procureops.py "$TASK_ENV_BASE_URL" /tmp/procureops_snapshot.json
```

If the runner provides the base URL only in the prompt, substitute that literal URL. If the helper is inconvenient, use direct `GET` requests to the same endpoints.

## Endpoint Map

Use these endpoint families and build dictionaries by their primary IDs:

- `/suppliers`: `supplier_id`, name, status, risk rating, payment terms.
- `/items`: SKU metadata, preferred supplier, standard cost.
- `/programs`: `program_id`, owner, status, budget fields.
- `/budget_snapshots`: dated program budget snapshots; prefer the latest snapshot on or before the task date when dates matter.
- `/contracts`: `contract_id`, supplier, program, SKU, status, price type, unit price, ceiling.
- `/purchase_requisitions`: requisition status, requester, quantity, SKU, need-by date.
- `/approvals`: approval events by `object_type` and `object_id`; sort by event date then event ID for latest state.
- `/purchase_orders`: PO header, requisition, contract, supplier, program, due date, status, line quantities, prices, subtotal, tax, total.
- `/receipts`: receipt header plus received and rejected quantities by PO line/SKU.
- `/ap/invoices`: invoice header, status, hold code, freight/tax/total, PO, receipt, and billed line quantities.
- `/ap/payments`: scheduled or posted payments by invoice, supplier, amount, date, and status.
- `/vendor_risk_events`: supplier risk events with date, status, severity, type, and related object.

Always filter by the task slice before aggregating. For as-of tasks, exclude source events after the as-of date unless the prompt asks for a future horizon. For payment close tasks, include only payments whose status and scheduled date satisfy the memo's close horizon.

## Numeric Discipline

Use exact arithmetic for money where practical, then round final USD values to cents. Keep ratios and percentages at the precision specified by the template.

Common formulas:

- `budget_headroom = budget_cap - committed_amount`.
- `receipt_completion_ratio = received_qty / ordered_qty` when ordered quantity is nonzero.
- `short_qty_vs_po = max(ordered_qty - received_qty, 0)`.
- `unreceived_billed_qty = max(billed_qty - received_qty, 0)`.
- `quantity_variance = quantity_billed - quantity_received`.
- `quantity_variance_pct = quantity_variance / po_ordered_quantity * 100`.
- `received_goods_value = received_qty * applicable_unit_price`.
- `unreceived_goods_value = unreceived_billed_qty * applicable_unit_price`.
- `close_balance = opening_balance + invoice_total - scheduled_payments`.
- `net_balance_impact = invoice_total - scheduled_payment_amount`.
- `contract_headroom_before = ceiling_amount - sum(noncancelled_po_subtotals_for_contract)`.
- `requested_subtotal = requested_quantity * contract_or_po_unit_price`.
- `requested_tax = requested_subtotal * tax_rate_percent / 100` unless the prompt says otherwise.
- `requested_total = requested_subtotal + requested_tax + prompt-provided freight`.
- `budget_after_change = remaining_budget - requested_total`.
- `max_quantity_with_current_budget = floor(remaining_budget / (unit_price * (1 + tax_rate_percent / 100)))` when tax applies per unit.
- `chargeback_amount = basis_quantity * unit_cost`; `net_release_amount = invoice_total - approved_chargeback_amount` only for release decisions.

## Reconciliation Rules

### PO, Receipt, and AP Lines

Match PO, receipt, and invoice lines by `po_id` plus `po_line_id` or SKU. If a task names a specific receipt, use that receipt for receipt-scoped fields. If a task names a PO but no receipt exists in the target set, represent the missing receipt exactly as the template directs.

For each target PO line:

- Ordered quantity and PO unit price come from the PO line.
- Received and rejected quantities come from in-scope receipt lines.
- Billed quantity and invoice unit price come from in-scope invoice lines.
- Contract unit price comes from the PO contract or a matching active contract by contract ID, supplier, program, and SKU.
- Contract price match is true only when the required source prices agree after normal money rounding.

Invoice exceptions are evidence-based. Use controlled codes from the template:

- Quantity exceeds receipt when billed quantity is greater than received quantity.
- Partial receipt when received quantity is less than ordered quantity or the PO is in a partial-receipt state.
- Price mismatch when invoice, PO, and contract unit prices do not agree.
- Damage or inspection exceptions when receipt lines show rejected quantities or inspection/hold status.
- Supplier watch risk when supplier risk rating is watch or the template treats watch status as an exception.
- No exception only when none of the applicable exception tests fire.

### AP Close and Vendor Balances

For invoice-level close decisions, use only target invoices. Join each invoice to its PO, supplier, receipt if present, and scheduled payments within the close horizon.

- Hold invoices with no receipt, pending receipt, explicit hold status, or positive quantity variance.
- Release invoices that have an approved three-way match and no blocking variance.
- Add `NO_RECEIPT`, `QTY_VARIANCE`, `APPROVED_THREE_WAY_MATCH`, and `SCHEDULED_PAYMENT_FOUND` only when the underlying source records prove them.
- Vendor balances are grouped by supplier across the target invoice slice, not across the entire ledger, unless the prompt says otherwise.
- Program summaries are grouped by target invoice program. Held totals come from held invoices; released totals come from released invoices. Net close balance should reflect unpaid or held exposure after scheduled payments.

### Sourcing Nomination Readiness

For sourcing packets, the local memo identifies package anchors, but the API selects supplier, requisition, contract, PO, receipt, invoice, approval, budget, and risk evidence.

For each nominated line:

- Select the supplier from the package PO or other source record named by the task.
- Use the package requisition as the primary requisition.
- Use the PO contract as commercial basis; if missing, search for a matching active contract by supplier, program, and SKU before returning null.
- Receipt evidence includes in-scope receipts on or before the as-of date.
- Invoice exception evidence includes in-scope AP invoices on or before the as-of date with hold, pending-receipt, missing-receipt, price, or quantity exceptions.
- Risk event evidence includes supplier risk events on or before the as-of date whose status is open or monitoring.

Classify blockers from source facts:

- `missing_contract`: no active commercial basis for the line.
- `supplier_watch`: supplier risk rating is watch when the template tracks watch status separately.
- `open_supplier_risk`: open or monitoring supplier-risk event exists.
- `ap_hold`: AP invoice is explicitly on hold.
- `pending_receipt`: no qualifying receipt exists, or the invoice/PO is blocked for missing receipt.
- `late_due_date`: PO due date misses the requisition need-by date, or the prompt defines lateness relative to the as-of date.
- `none`: only when no other blocker applies.

Use a conservative readiness ladder. Hard blockers such as missing contract, pending receipt, severe supplier risk, or late need-by delivery make the line `not_ready` and normally `hold`. Softer blockers such as watch risk or AP holds can make the line `at_risk` and `conditional_nomination` when no hard blocker exists. A line with no blockers is `ready` and can be nominated. Program readiness is the worst line readiness. Committee send/no-send and next owner should follow the highest-impact unresolved blocker: AP issues to AP, commercial basis and PO timing to buyer, budget to finance or program owner, and supplier quality/risk to quality operations.

### Contract Change Control

For amendment or modular-change tasks, verify contract identity first. If the requested contract does not match the requested supplier, program, and SKU, use the template's contract-mismatch decision.

Otherwise:

- Sum noncancelled PO subtotals for the contract to compute existing contract usage.
- Exclude cancelled POs and list them separately when requested.
- Compute contract ceiling headroom before and after the requested change.
- Use the latest budget snapshot on or before the memo date. Program budget exposure is line subtotal plus tax, and freight only when the memo provides freight.
- Determine the latest approval event for the source requisition. Approval is OK only when the latest action is in the prompt's allowed good actions, usually `approved`.
- Risk is OK when the supplier is active and has no open severe risk event, unless the prompt sets a stricter rule. Watch rating alone is context when the memo says so.
- Required actions should be the sorted set of unresolved blockers, or `none` only when there are no blockers.
- Choose the decision by blocker combination: release when all checks pass; hold for budget, approval, supplier risk, or the available combined decision when multiple blockers apply.

### Receiving/AP Release and Chargebacks

When a local packet includes a chargeback register, treat it as authoritative for chargeback reason, basis quantity, unit cost, and approval status. Still use ProcureOps for PO, receipt, and AP invoice totals and record existence.

For each target invoice:

- Identify the PO from the invoice record and the target packet.
- Include receipt IDs in scope only when the packet names them or the prompt directs inclusion. List other same-PO receipts as excluded when the template asks.
- If no in-scope receipt exists for a target PO, use the template's missing-receipt representation and hold the invoice.
- Approved chargebacks reduce the release amount. Pending chargebacks do not release net payment; hold the invoice for quality or control review.
- Inspection-hold receipts and pending-quality chargebacks should drive a hold decision even when AP status appears approved.
- Follow-up actions should be the sorted set implied by unresolved missing receipt, pending quality review, duplicate or excluded receipt handling, and approved netting work.

## Output Checks

Before finalizing:

- Compare the output object against `answer_template.json` key by key.
- Sort every list the template says to sort; otherwise treat set fields as duplicate-free.
- Use exact enum strings from the template, including case and underscores.
- Include source record IDs and local payload filenames only when the template asks for evidence.
- Do not include source records outside the target slice in totals, queues, or evidence unless the field specifically asks for excluded or supporting records.
- Recompute totals from the row-level output and confirm they match summaries.
- Return only valid JSON.
